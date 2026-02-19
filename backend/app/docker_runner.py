import os
import subprocess
import json
from typing import List, Dict
from app.models import ErrorInfo, FixResult, AgentResponse, ErrorType
from app.parser import ErrorParser
from app.fixer import FixEngine
from app.git_utils import GitHandler
from app.config import WORKSPACE_DIR, RESULTS_FILE, TEST_COMMAND


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
        self.parser = ErrorParser()
        self.fixer: FixEngine = None
        
        # Project type detection
        self.project_type = None  # 'python', 'javascript', or 'unknown'
        self.test_command = None
        
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
        self._emit_progress("info", f"🔍 Starting AI DevOps Agent for {self.repo_url}")
        print(f"Starting AI DevOps Agent for {self.repo_url}")
        
        # Step 1: Clone repository
        self._emit_progress("cloning", "📥 Cloning repository...")
        repo_path = self.git_handler.clone_repo(self.repo_url)
        self.fixer = FixEngine(repo_path)
        self._emit_progress("success", "✅ Repository cloned successfully")
        
        # Step 1.5: Detect project type
        self._emit_progress("analyzing", "🔍 Detecting project type...")
        self._detect_project_type(repo_path)
        self._emit_progress("info", f"📋 Detected {self.project_type} project")
        
        # Step 2: Install dependencies
        self._emit_progress("installing", "📦 Installing dependencies...")
        self._install_dependencies(repo_path)
        self._emit_progress("success", "✅ Dependencies installed")
        
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
            
            # Parse errors
            errors = self.parser.parse_errors(test_output)
            
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
        
        # Step 5: Push branch
        self._emit_progress("pushing", "📤 Pushing changes to GitHub...")
        self.git_handler.push_branch(branch_name)
        self._emit_progress("success", f"✅ Branch pushed: {branch_name}")
        
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
    
    def _detect_project_type(self, repo_path: str):
        """Detect if project is Python or JavaScript/React"""
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
                        text=True,
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
                print("Installing pip dependencies from requirements.txt...")
                try:
                    subprocess.run(
                        ['pip', 'install', '-r', 'requirements.txt'],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout
                    )
                    print("✅ Dependencies installed successfully")
                except subprocess.TimeoutExpired:
                    print("❌ Dependency installation timed out")
                except Exception as e:
                    print(f"❌ Error installing dependencies: {e}")
        else:
            print("⚠️  No dependencies file found, skipping installation")
    
    def _run_tests(self, repo_path: str) -> str:
        """Run tests based on project type and return output"""
        test_cmd_str = ' '.join(self.test_command)
        print(f"Running tests with: {test_cmd_str}")
        
        try:
            # Convert command to string for shell execution on Windows
            if self.project_type == 'javascript':
                cmd = ' '.join(self.test_command)
            else:
                cmd = self.test_command
            
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                shell=(self.project_type == 'javascript')  # Use shell for npm on Windows
            )
            
            # Combine stdout and stderr
            output = result.stdout + "\n" + result.stderr
            
            # Log test result
            if result.returncode == 0:
                print("✅ Tests passed")
            else:
                print(f"❌ Tests failed with exit code {result.returncode}")
            
            return output
        except subprocess.TimeoutExpired:
            print("⏱️  Test execution timed out (120s limit)")
            return ""
        except Exception as e:
            print(f"❌ Error running tests: {e}")
            return ""
    
    def _apply_and_commit_fix(self, error: ErrorInfo) -> bool:
        """Apply fix and commit if successful"""
        print(f"Attempting to fix {error.type} in {error.file}:{error.line}")
        self._emit_progress("fixing", f"🔧 Fixing {error.type.value} in {os.path.basename(error.file)}:{error.line}")
        
        # Apply fix
        success = self.fixer.apply_fix(error)
        
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
