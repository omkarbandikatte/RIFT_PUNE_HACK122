"""
Docker Container Executor
Runs tests in isolated Docker containers with auto-cleanup
"""
import os
import subprocess
import json
import re
from typing import Dict, Tuple


class DockerExecutor:
    """Execute tests in isolated Docker containers"""
    
    def __init__(self, image_name: str = "rift-agent:latest"):
        self.image_name = image_name
        self.container_name_prefix = "rift-agent"
    
    def check_docker_available(self) -> bool:
        """Check if Docker is installed and running"""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def build_image(self, dockerfile_path: str = "docker/Dockerfile.agent") -> bool:
        """Build the agent Docker image"""
        print(f"🐳 Building Docker image: {self.image_name}")
        
        try:
            result = subprocess.run(
                ['docker', 'build', '-f', dockerfile_path, '-t', self.image_name, '.'],
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=300,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            if result.returncode == 0:
                print(f"✅ Docker image built successfully")
                return True
            else:
                print(f"❌ Docker build failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Docker build timed out (5 minutes)")
            return False
        except Exception as e:
            print(f"❌ Docker build error: {e}")
            return False
    
    def check_image_exists(self) -> bool:
        """Check if the agent image exists"""
        try:
            result = subprocess.run(
                ['docker', 'images', '-q', self.image_name],
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=5
            )
            return bool(result.stdout.strip())
        except:
            return False
    
    def run_tests_in_container(self, repo_path: str) -> Tuple[str, int]:
        """
        Run tests in Docker container
        
        Args:
            repo_path: Absolute path to repository on host
            
        Returns:
            Tuple of (output, return_code)
        """
        # Ensure image exists
        if not self.check_image_exists():
            print("⚠️  Docker image not found, building...")
            if not self.build_image():
                raise RuntimeError("Failed to build Docker image")
        
        # Convert Windows path to Unix-style for Docker
        repo_path_unix = repo_path.replace('\\', '/')
        
        # Generate unique container name
        import time
        container_name = f"{self.container_name_prefix}-{int(time.time())}"
        
        print(f"🐳 Starting Docker container: {container_name}")
        print(f"📁 Mounting: {repo_path} -> /workspace")
        
        # Docker run command
        # Note: For JavaScript projects, we need network access for npm to work
        # For Python, we kept --network none and --read-only for security
        is_node = self.image_name == 'rift-agent-node:latest'
        
        docker_cmd = [
            'docker', 'run',
            '--rm',  # Auto-remove container after exit
            '--name', container_name,
            '-v', f'{repo_path_unix}:/workspace',  # Mount repo
            '--workdir', '/workspace',
            '--memory', '1g',  # Increased for npm
            '--cpus', '2.0',  # Increased for npm
        ]
        
        # Add tmpfs mounts and restrictions for Python (security)
        if not is_node:
            docker_cmd.extend(['--network', 'none'])  # No network for Python
            docker_cmd.extend(['--read-only'])  # Read-only filesystem
            docker_cmd.extend(['--tmpfs', '/tmp:rw,size=200m'])
            docker_cmd.extend(['--tmpfs', '/home/agent:rw,size=100m'])
        
        docker_cmd.append(self.image_name)
        
        try:
            # Run container
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=180  # 3 minute timeout
            )
            
            # Debug: Print raw container output
            print(f"\n=== CONTAINER STDOUT ===")
            print(result.stdout)
            print(f"=== CONTAINER STDERR ===")
            print(result.stderr)
            print(f"=== CONTAINER EXIT CODE: {result.returncode} ===\n")
            
            # Extract JSON output from stdout
            output = self._extract_json_output(result.stdout, result.stderr)
            
            if output:
                combined = output.get('stdout', '') + '\n' + output.get('stderr', '')
                return combined, output.get('returncode', result.returncode)
            else:
                # Fallback if JSON parsing fails
                combined = result.stdout + '\n' + result.stderr
                return combined, result.returncode
                
        except subprocess.TimeoutExpired:
            print("⏱️  Container execution timed out (3 minutes)")
            # Try to stop the container
            self._stop_container(container_name)
            return "Container execution timed out after 3 minutes", 124
            
        except Exception as e:
            print(f"❌ Container execution error: {e}")
            self._stop_container(container_name)
            return f"Container error: {str(e)}", 1
    
    def _extract_json_output(self, stdout: str, stderr: str) -> Dict:
        """Extract JSON output from container stdout"""
        try:
            # Look for JSON between markers
            if '=== AGENT OUTPUT ===' in stdout:
                start = stdout.find('=== AGENT OUTPUT ===') + len('=== AGENT OUTPUT ===')
                end = stdout.find('=== END OUTPUT ===')
                
                if end > start:
                    json_str = stdout[start:end].strip()
                    return json.loads(json_str)
            
            # Fallback: try to parse entire stdout as JSON
            return json.loads(stdout)
            
        except json.JSONDecodeError:
            # If JSON parsing fails, return raw output
            return {
                'stdout': stdout,
                'stderr': stderr,
                'returncode': 1,
                'success': False
            }
    
    def _stop_container(self, container_name: str):
        """Force stop a container"""
        try:
            subprocess.run(
                ['docker', 'stop', container_name],
                capture_output=True,
                timeout=10
            )
            print(f"🛑 Container {container_name} stopped")
        except:
            pass
    
    def cleanup_old_containers(self):
        """Remove any old agent containers that weren't cleaned up"""
        try:
            # List containers with our prefix
            result = subprocess.run(
                ['docker', 'ps', '-a', '--filter', f'name={self.container_name_prefix}', '-q'],
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            
            container_ids = result.stdout.strip().split('\n')
            
            if container_ids and container_ids[0]:
                print(f"🧹 Cleaning up {len(container_ids)} old containers...")
                subprocess.run(
                    ['docker', 'rm', '-f'] + container_ids,
                    capture_output=True,
                    timeout=30
                )
                print("✅ Old containers removed")
                
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
    
    def get_container_stats(self) -> Dict:
        """Get Docker resource usage stats"""
        try:
            result = subprocess.run(
                ['docker', 'stats', '--no-stream', '--format', '{{json .}}'],
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)
            
        except:
            pass
        
        return {}
