import os
import subprocess
import json
import threading
import time
import sys
import venv  # Still needed for fallback local execution
from typing import List, Dict
from app.models import ErrorInfo, FixResult, AgentResponse, ErrorType
from app.parser import ErrorParser
from app.fixer import FixEngine
from app.git_utils import GitHandler
from app.docker_executor import DockerExecutor
from app.config import WORKSPACE_DIR, RESULTS_FILE, TEST_COMMAND
from app.languages import detect_language, get_language_plugin, LanguagePlugin


class DockerRunner:
    """Main orchestrator for the AI DevOps agent"""
    
    def __init__(self, repo_url: str, team: str, leader: str, max_retries: int = 5, ws_manager=None, run_id=None):
        self.repo_url = repo_url
        self.team = team
        self.leader = leader
        self.max_retries = max_retries
        self.ws_manager = ws_manager
        self.run_id = run_id
        
        # Initialize components
        self.git_handler = GitHandler(WORKSPACE_DIR)
        self.parser = ErrorParser()  # Legacy Python parser (fallback)
        self.fixer: FixEngine = None  # Legacy Python fixer (fallback)
        
        # Language plugin system
        self.language = None
        self.language_plugin: LanguagePlugin = None
        self.docker_executor = None  # Will be initialized after language detection
        
        # Project type detection
        self.project_type = None  # 'python', 'javascript', or 'unknown'
        self.test_command = None
        self.use_docker = True  # Use Docker by default
        
        # Tracking
        self.fixes: List[FixResult] = []
        self.total_failures = 0
        self.iterations = 0
    
    def _emit_progress(self, status: str, message: str, data: dict = None):
        """Emit progress update via WebSocket"""
        if self.ws_manager and self.run_id:
            self.ws_manager.send_progress_sync(self.run_id, status, message, data)
        print(f"📡 {message}")
    
    def run(self) -> AgentResponse:
        """Main execution flow"""
        try:
            self._emit_progress("info", f"🔍 Starting AI DevOps Agent for {self.repo_url}")
            print(f"Starting AI DevOps Agent for {self.repo_url}")
            
            # Step 1: Clone repository
            self._emit_progress("cloning", "📥 Cloning repository...")
            repo_path = self.git_handler.clone_repo(self.repo_url)
            self.fixer = FixEngine(repo_path)
            self._emit_progress("success", "✅ Repository cloned successfully")
            
            # Step 1.5: Detect language and load plugin
            self._emit_progress("analyzing", "🔍 Detecting project type...")
            self.language = detect_language(repo_path)
            self.language_plugin = get_language_plugin(self.language)
            self._detect_project_type(repo_path)  # Keep for compatibility
            self._emit_progress("info", f"📋 Detected {self.language} project")
            
            # Check JavaScript project configuration
            if self.language in ['javascript', 'typescript']:
                self._check_javascript_config(repo_path)
            
            # Initialize DockerExecutor with language-specific image
            docker_image = self.language_plugin.get_docker_image()
            self.docker_executor = DockerExecutor(image_name=docker_image)
            print(f"🐳 Using Docker image: {docker_image}")
            
            # Step 2: Check Docker availability
            if self.docker_executor.check_docker_available():
                self._emit_progress("docker", "🐳 Docker detected, using containerized execution")
                self.use_docker = True
                
                # Ensure Docker image is built
                if not self.docker_executor.check_image_exists():
                    self._emit_progress("docker", "🔨 Building Docker image (one-time setup)...")
                    
                    # Determine Dockerfile based on language
                    dockerfile_map = {
                        'python': 'docker/Dockerfile.agent',
                        'javascript': 'docker/Dockerfile.agent.node',
                        'typescript': 'docker/Dockerfile.agent.node',
                    }
                    dockerfile_path = dockerfile_map.get(self.language, 'docker/Dockerfile.agent')
                    
                    if self.docker_executor.build_image(dockerfile_path=dockerfile_path):
                        self._emit_progress("success", "✅ Docker image ready")
                    else:
                        self._emit_progress("warning", "⚠️ Docker build failed, falling back to local execution")
                        self.use_docker = False
            else:
                self._emit_progress("warning", "⚠️ Docker not available, using local execution")
                self.use_docker = False
            
            # Step 3: Create new branch
            self._emit_progress("info", "🌿 Creating feature branch...")
            branch_name = self.git_handler.create_branch(self.team, self.leader)
            self._emit_progress("success", f"✅ Branch created: {branch_name}")
            
            # Step 4: Iterative fix loop
            for iteration in range(self.max_retries):
                self.iterations = iteration + 1
                print(f"\n=== Iteration {self.iterations} ===")
                self._emit_progress("testing", f"🧪 Running tests (Iteration {self.iterations}/{self.max_retries})...")
                
                # Run tests
                test_output = self._run_tests(repo_path)
                
                # Parse errors using language plugin
                errors = self.language_plugin.parse_errors(test_output, repo_path=repo_path)
                
                if not errors:
                    print("No errors found! Tests passed.")
                    self._emit_progress("success", "✅ All tests passed!")
                    break
                
                print(f"Found {len(errors)} errors")
                self.total_failures = len(errors)
                self._emit_progress("warning", f"⚠️ Found {len(errors)} error(s) to fix")
                
                # Apply fixes
                self._emit_progress("fixing", f"🔧 Applying fixes to {len(errors)} error(s)...")
                fixed_count = 0
                for error in errors:
                    if self._apply_and_commit_fix(error):
                        fixed_count += 1
                
                print(f"Applied {fixed_count} fixes in iteration {self.iterations}")
                self._emit_progress("info", f"✅ Applied {fixed_count} fix(es) in iteration {self.iterations}")
                
                # If no fixes were applied, break to avoid infinite loop
                if fixed_count == 0:
                    print("No fixes could be applied. Stopping.")
                    self._emit_progress("error", "❌ No fixes could be applied. Stopping iterations.")
                    break
            
            # Step 5: Push branch (only if fixes were applied)
            if len(self.fixes) > 0:
                self._emit_progress("pushing", "📤 Pushing changes to GitHub...")
                try:
                    self.git_handler.push_branch(branch_name)
                    self._emit_progress("success", f"✅ Branch pushed: {branch_name}")
                except Exception as e:
                    self._emit_progress("error", f"❌ Failed to push branch: {str(e)}")
                    print(f"Error pushing branch: {e}")
            else:
                self._emit_progress("warning", "⚠️ No fixes were applied, skipping push")
                print("No fixes applied, skipping push")
            
            # Step 6: Generate response
            self._emit_progress("completing", "📊 Generating final report...")
            response = self._generate_response(branch_name)
            self._emit_progress("completed", f"✅ Agent run completed! Status: {response.status}", {
                "status": response.status,
                "total_fixes": response.total_fixes,
                "total_failures": response.total_failures,
                "iterations": response.iterations,
                "branch": branch_name
            })
            
            # Step 7: Save results.json
            self._save_results(response)
            
            return response
        finally:
            # Always cleanup Git resources to release file handles
            if hasattr(self, 'git_handler'):
                self.git_handler.close()
    
    def _check_javascript_config(self, repo_path: str):
        """Check JavaScript project configuration and adjust test strategy"""
        package_json_path = os.path.join(repo_path, 'package.json')
        
        if not os.path.exists(package_json_path):
            return
        
        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
            
            scripts = package_data.get('scripts', {})
            
            # Check if test script exists
            if 'test' not in scripts:
                print("⚠️  No test script found in package.json")
                self._emit_progress("warning", "⚠️ No test script configured")
                
                # Check for alternative scripts
                if 'lint' in scripts:
                    print("✓ Found lint script, will use for code analysis")
                    self._emit_progress("info", "📋 Using ESLint for code analysis")
                    # Update plugin's test command to use lint
                    from app.languages.javascript_plugin import JavaScriptPlugin
                    if isinstance(self.language_plugin, JavaScriptPlugin):
                        # Override test command to use lint
                        self.test_command = ['npm', 'run', 'lint']
                        print(f"📋 Updated test command: {' '.join(self.test_command)}")
                elif 'build' in scripts:
                    print("✓ Found build script, will use for error detection")
                    self._emit_progress("info", "📋 Using build for error detection")
                    self.test_command = ['npm', 'run', 'build']
                else:
                    print("⚠️  No test, lint, or build scripts found")
                    self._emit_progress("warning", "⚠️ No testable scripts found in package.json")
            else:
                test_script = scripts['test']
                print(f"✓ Found test script: {test_script}")
                
                # Check if it's a placeholder
                if 'no test' in test_script.lower() or 'echo' in test_script.lower():
                    print("⚠️  Test script is a placeholder")
                    self._emit_progress("warning", "⚠️ Test script is not configured")
                    
                    # Try lint as fallback
                    if 'lint' in scripts:
                        print("✓ Falling back to lint script")
                        self.test_command = ['npm', 'run', 'lint']
                    
        except Exception as e:
            print(f"⚠️  Error reading package.json: {e}")
    
    def _detect_project_type(self, repo_path: str):
        """Detect if project is Python or JavaScript/React (legacy, kept for compatibility)"""
        # Note: Language detection now happens via language plugin
        # This method is kept for backward compatibility
        self.project_type = self.language  # Use detected language
        
        # Use language plugin's test command
        if self.language_plugin:
            self.test_command = self.language_plugin.get_test_command()
            print(f"📋 Using test command from {self.language} plugin: {' '.join(self.test_command)}")
        else:
            # Fallback to old detection logic
            package_json = os.path.join(repo_path, 'package.json')
            requirements_txt = os.path.join(repo_path, 'requirements.txt')
            
            if os.path.exists(package_json):
                self.project_type = 'javascript'
                self.test_command = ['npm', 'test', '--', '--passWithNoTests']
                print("📦 Detected JavaScript/React project (package.json found)")
            elif os.path.exists(requirements_txt):
                self.project_type = 'python'
                self.test_command = ['pytest', '--maxfail=10', '-v']
                print("🐍 Detected Python project (requirements.txt found)")
            else:
                # Default to Python with pytest
                self.project_type = 'unknown'
                self.test_command = ['pytest', '--maxfail=10', '-v']
                print("⚠️  Could not detect project type, defaulting to Python/pytest")
    
    def _create_venv(self, repo_path: str):
        """Create a virtual environment for the Python project"""
        self.venv_path = os.path.join(repo_path, '.venv')
        
        # Check if venv already exists
        if os.path.exists(self.venv_path):
            print(f"Virtual environment already exists at {self.venv_path}")
        else:
            print(f"Creating virtual environment at {self.venv_path}...")
            try:
                venv.create(self.venv_path, with_pip=True)
                print("✅ Virtual environment created successfully")
            except Exception as e:
                print(f"⚠️  Error creating venv: {e}, will use system Python")
                self.venv_path = None
                self.venv_python = None
                return
        
        # Set path to venv's python executable
        if sys.platform == "win32":
            self.venv_python = os.path.join(self.venv_path, 'Scripts', 'python.exe')
        else:
            self.venv_python = os.path.join(self.venv_path, 'bin', 'python')
        
        print(f"✅ Using Python: {self.venv_python}")
    
    def _install_dependencies(self, repo_path: str):
        """Install dependencies based on project type"""
        if self.project_type == 'javascript':
            package_json = os.path.join(repo_path, 'package.json')
            if os.path.exists(package_json):
                print("Installing npm dependencies...")
                try:
                    # Run npm install (shell=True for Windows to find npm in PATH)
                    result = subprocess.run(
                        'npm install',
                        cwd=repo_path,
                        capture_output=True,
                        encoding='utf-8',
                        errors='replace',
                        shell=True,
                        timeout=300  # 5 minute timeout
                    )
                    if result.returncode == 0:
                        print("✅ npm dependencies installed successfully")
                    else:
                        print(f"⚠️  npm install had warnings: {result.stderr[:200]}")
                except subprocess.TimeoutExpired:
                    print("❌ npm install timed out")
                except Exception as e:
                    print(f"❌ Error installing npm dependencies: {e}")
        elif self.project_type == 'python':
            requirements_file = os.path.join(repo_path, 'requirements.txt')
            if os.path.exists(requirements_file):
                print("Installing pip dependencies in virtual environment...")
                try:
                    # Use venv's pip if available, otherwise system pip
                    pip_cmd = [self.venv_python, '-m', 'pip'] if self.venv_python else ['pip']
                    
                    subprocess.run(
                        pip_cmd + ['install', '-r', 'requirements.txt'],
                        cwd=repo_path,
                        capture_output=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=300  # 5 minute timeout
                    )
                    print("✅ Dependencies installed successfully in isolated environment")
                except subprocess.TimeoutExpired:
                    print("❌ Dependency installation timed out")
                except Exception as e:
                    print(f"❌ Error installing dependencies: {e}")
        else:
            print("⚠️  No dependencies file found, skipping installation")
    
    def _run_tests(self, repo_path: str) -> str:
        """Run tests using Docker container or local execution"""
        
        # Use Docker if available (for any language that has Docker support)
        if self.use_docker:
            return self._run_tests_docker(repo_path)
        else:
            return self._run_tests_local(repo_path)
    
    def _run_tests_docker(self, repo_path: str) -> str:
        """Run tests in Docker container (preferred method)"""
        print(f"🐳 Running tests in Docker container...")
        
        # Flag to track if process is still running
        process_running = {'status': True}
        
        # Function to send periodic progress updates
        def send_progress_updates():
            elapsed = 0
            while process_running['status'] and elapsed < 180:
                time.sleep(15)  # Send update every 15 seconds
                elapsed += 15
                if process_running['status']:
                    self._emit_progress("info", f"⏳ Container still running... ({elapsed}s elapsed)")
        
        # Start progress update thread
        progress_thread = threading.Thread(target=send_progress_updates, daemon=True)
        progress_thread.start()
        
        try:
            # Run tests in Docker container
            output, returncode = self.docker_executor.run_tests_in_container(repo_path)
            
            # Log test result
            if returncode == 0:
                print("✅ Tests passed in container")
                self._emit_progress("success", "✅ Tests completed successfully")
            else:
                print(f"❌ Tests failed with exit code {returncode}")
                self._emit_progress("info", f"📋 Tests completed with {returncode} failures")
            
            return output
            
        except Exception as e:
            print(f"❌ Docker execution error: {e}")
            self._emit_progress("error", f"❌ Docker error: {str(e)}")
            print("⚠️  Falling back to local execution...")
            self.use_docker = False
            return self._run_tests_local(repo_path)
            
        finally:
            process_running['status'] = False
    
    def _run_tests_local(self, repo_path: str) -> str:
        """Run tests locally (fallback method)"""
        print(f"💻 Running tests locally...")
        test_cmd_str = ' '.join(self.test_command) if self.test_command else 'pytest'
        print(f"Command: {test_cmd_str}")
        
        # Flag to track if process is still running
        process_running = {'status': True}
        
        # Function to send periodic progress updates
        def send_progress_updates():
            elapsed = 0
            while process_running['status'] and elapsed < 120:
                time.sleep(10)  # Send update every 10 seconds
                elapsed += 10
                if process_running['status']:
                    self._emit_progress("info", f"⏳ Tests still running... ({elapsed}s elapsed)")
        
        # Start progress update thread
        progress_thread = threading.Thread(target=send_progress_updates, daemon=True)
        progress_thread.start()
        
        try:
            # Get test command from language plugin
            if self.language_plugin:
                cmd = self.language_plugin.get_test_command()
                print(f"Using language plugin command: {' '.join(cmd)}")
            # Fallback to project_type detection
            elif self.project_type == 'python':
                cmd = ['python', '-m', 'pytest', '--maxfail=10', '-v', '--tb=short']
            elif self.project_type == 'javascript':
                cmd = self.test_command if self.test_command else ['npm', 'test']
            else:
                cmd = self.test_command if self.test_command else ['pytest', '--maxfail=10', '-v']
            
            # Use Popen for better control
            process = subprocess.Popen(
                cmd,
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace',
                shell=(self.project_type == 'javascript'),
                bufsize=1
            )
            
            # Wait for process with timeout
            try:
                stdout, stderr = process.communicate(timeout=120)
                returncode = process.returncode
            except subprocess.TimeoutExpired:
                print("⏱️  Test execution timed out (120s limit), terminating process...")
                process.kill()
                stdout, stderr = process.communicate()
                self._emit_progress("warning", "⚠️ Test execution timed out")
                return ""
            finally:
                process_running['status'] = False
            
            # Combine stdout and stderr
            output = stdout + "\n" + stderr
            
            # Log test result
            if returncode == 0:
                print("✅ Tests passed")
                self._emit_progress("success", "✅ Tests completed successfully")
            else:
                print(f"❌ Tests failed with exit code {returncode}")
                self._emit_progress("info", f"📋 Tests completed with {returncode} failures")
            
            return output
        except Exception as e:
            process_running['status'] = False
            print(f"❌ Error running tests: {e}")
            self._emit_progress("error", f"❌ Error running tests: {str(e)}")
            return ""
        finally:
            process_running['status'] = False
    
    def _apply_and_commit_fix(self, error: ErrorInfo) -> bool:
        """Apply fix and commit if successful"""
        print(f"Attempting to fix {error.type} in {error.file}:{error.line}")
        self._emit_progress("fixing", f"🔧 Fixing {error.type.value} in {os.path.basename(error.file)}:{error.line}")
        
        # Apply fix using language plugin
        success = self.language_plugin.fix_error(error)
        
        if success:
            # Commit the fix
            try:
                commit_message = self.git_handler.commit_fix(
                    error.file,
                    error.type.value,
                    error.line,
                    error.message
                )
                
                self._emit_progress("success", f"✅ Fixed {error.type.value} in {os.path.basename(error.file)}:{error.line}")
                
                # Track the fix
                self.fixes.append(FixResult(
                    file=error.file,
                    line=error.line,
                    type=error.type.value,
                    commit_message=commit_message,
                    status="Fixed"
                ))
                
                print(f"✓ Fixed and committed")
                return True
            except Exception as e:
                print(f"Error committing fix: {e}")
                return False
        else:
            # Track failed fix
            self.fixes.append(FixResult(
                file=error.file,
                line=error.line,
                type=error.type.value,
                commit_message="",
                status="Failed"
            ))
            print(f"✗ Could not apply fix")
            return False
    
    def _generate_response(self, branch_name: str) -> AgentResponse:
        """Generate final response"""
        # Count successful fixes
        successful_fixes = sum(1 for fix in self.fixes if fix.status == "Fixed")
        
        # Determine overall status
        status = "PASSED" if successful_fixes > 0 and successful_fixes == len(self.fixes) else "PARTIAL"
        if successful_fixes == 0:
            status = "FAILED"
        
        return AgentResponse(
            repo=self.repo_url,
            branch=branch_name,
            total_failures=self.total_failures,
            total_fixes=successful_fixes,
            iterations=self.iterations,
            status=status,
            fixes=self.fixes
        )
    
    def _save_results(self, response: AgentResponse):
        """Save results to results.json"""
        try:
            with open(RESULTS_FILE, 'w') as f:
                json.dump(response.dict(), f, indent=2)
            print(f"Results saved to {RESULTS_FILE}")
        except Exception as e:
            print(f"Error saving results: {e}")
