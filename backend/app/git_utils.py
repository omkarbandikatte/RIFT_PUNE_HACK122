import os
import shutil
import stat
import time
import subprocess
import sys
from git import Repo, GitCommandError
from typing import Optional


def remove_readonly(func, path, excinfo):
    """Error handler for Windows readonly files"""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


class GitHandler:
    """Handle Git operations for the agent"""
    
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.repo: Optional[Repo] = None
        self.repo_path: Optional[str] = None
    
    def _force_remove_windows(self, path: str) -> bool:
        """Force remove directory using Windows-specific commands"""
        if sys.platform != 'win32':
            return False
        
        try:
            # Use Windows rmdir /s /q command which is more aggressive
            subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', path], 
                         check=False, timeout=30, capture_output=True)
            time.sleep(0.5)
            return not os.path.exists(path)
        except Exception as e:
            print(f"Windows force remove failed: {e}")
            return False
    
    def clone_repo(self, repo_url: str) -> str:
        """Clone repository and return local path"""
        # Extract repo name from URL
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        repo_path = os.path.join(self.workspace_dir, repo_name)
        
        # Close any existing Git repository connection
        if self.repo and hasattr(self.repo, 'close'):
            try:
                self.repo.close()
            except:
                pass
        self.repo = None
        
        # ALWAYS start fresh - remove existing directory to avoid stale files
        if os.path.exists(repo_path):
            print(f"Removing existing repository at {repo_path} to start fresh...")
            removed = False
            
            # Attempt 1: Standard shutil with readonly handler
            try:
                shutil.rmtree(repo_path, onerror=remove_readonly)
                time.sleep(0.5)
                if not os.path.exists(repo_path):
                    print(f"✓ Successfully removed old repository")
                    removed = True
            except Exception as e:
                print(f"Standard removal failed: {e}")
            
            # Attempt 2: Windows-specific forceful deletion
            if not removed and sys.platform == 'win32':
                print("Trying Windows force removal...")
                removed = self._force_remove_windows(repo_path)
                if removed:
                    print(f"✓ Successfully removed with Windows command")
            
            # Attempt 3: Rename and ignore (last resort)
            if not removed:
                try:
                    backup_path = f"{repo_path}_old_{int(time.time())}"
                    print(f"⚠️ Could not delete, renaming to {backup_path}")
                    os.rename(repo_path, backup_path)
                    removed = True
                except Exception as e:
                    print(f"Rename failed: {e}")
            
            # If still not removed, fail gracefully
            if os.path.exists(repo_path):
                print(f"⚠️ Warning: Could not fully remove old directory, will try to clone anyway...")
        
        # Clone the repository fresh from GitHub
        print(f"Cloning repository from {repo_url}...")
        try:
            self.repo = Repo.clone_from(repo_url, repo_path)
            self.repo_path = repo_path
            print(f"Repository cloned to {repo_path}")
            return repo_path
        except Exception as e:
            # If clone fails and directory exists, try one more cleanup
            if os.path.exists(repo_path):
                print(f"Clone failed, cleaning up partial clone...")
                try:
                    shutil.rmtree(repo_path, onerror=remove_readonly)
                except:
                    pass
            raise Exception(f"Failed to clone repository: {e}")
    
    def create_branch(self, team: str, leader: str) -> str:
        """Create and checkout new branch with specified naming format"""
        if not self.repo:
            raise ValueError("Repository not initialized")
        
        # Format: TEAM_LEADER_AI_FIX
        branch_name = self._format_branch_name(team, leader)
        
        # Check if branch already exists
        try:
            # Create and checkout new branch
            self.repo.git.checkout('-b', branch_name)
            print(f"Created and checked out branch: {branch_name}")
            return branch_name
        except GitCommandError as e:
            # Branch might already exist, try to check it out
            try:
                self.repo.git.checkout(branch_name)
                print(f"Checked out existing branch: {branch_name}")
                return branch_name
            except GitCommandError:
                # If that fails, create a unique branch name
                import time
                unique_branch = f"{branch_name}_{int(time.time())}"
                self.repo.git.checkout('-b', unique_branch)
                print(f"Created and checked out branch: {unique_branch}")
                return unique_branch
    
    def _format_branch_name(self, team: str, leader: str) -> str:
        """Format branch name according to specification"""
        # Remove spaces and convert to uppercase
        team_clean = team.strip().replace(' ', '_').upper()
        leader_clean = leader.strip().replace(' ', '_').upper()
        
        return f"{team_clean}_{leader_clean}_AI_FIX"
    
    def commit_fix(self, file_path: str, bug_type: str, line: int, message: str) -> str:
        """Commit a fix to the repository"""
        if not self.repo:
            raise ValueError("Repository not initialized")
        
        # Stage the file
        self.repo.index.add([file_path])
        
        # Create commit message
        file_name = os.path.basename(file_path)
        commit_message = f"[AI-AGENT] Fixed {bug_type} error in {file_name} line {line}"
        
        # Commit
        self.repo.index.commit(commit_message)
        print(f"Committed: {commit_message}")
        
        return commit_message
    
    def push_branch(self, branch_name: str) -> bool:
        """Push branch to remote repository"""
        if not self.repo:
            raise ValueError("Repository not initialized")
        
        try:
            # Get the remote (usually 'origin')
            origin = self.repo.remote('origin')
            
            # Push the branch
            origin.push(refspec=f'{branch_name}:{branch_name}')
            print(f"Successfully pushed branch: {branch_name}")
            return True
        except GitCommandError as e:
            print(f"Error pushing branch: {e}")
            return False
    
    def get_repo_name(self) -> str:
        """Get repository name"""
        if self.repo_path:
            return os.path.basename(self.repo_path)
        return "unknown"
    
    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes"""
        if not self.repo:
            return False
        return self.repo.is_dirty()
    
    def close(self):
        """Close Git repository and release file handles"""
        if self.repo:
            try:
                # Close the repository to release file handles
                self.repo.close()
            except:
                pass
            self.repo = None
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.close()
