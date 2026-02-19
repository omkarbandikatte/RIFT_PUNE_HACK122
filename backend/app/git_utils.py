import os
from git import Repo, GitCommandError
from typing import Optional


class GitHandler:
    """Handle Git operations for the agent"""
    
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.repo: Optional[Repo] = None
        self.repo_path: Optional[str] = None
    
    def clone_repo(self, repo_url: str) -> str:
        """Clone repository and return local path"""
        # Extract repo name from URL
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        repo_path = os.path.join(self.workspace_dir, repo_name)
        
        # Check if repo already exists
        if os.path.exists(repo_path):
            print(f"Repository already exists at {repo_path}")
            self.repo = Repo(repo_path)
            self.repo_path = repo_path
            return repo_path
        
        # Clone the repository
        print(f"Cloning repository from {repo_url}...")
        self.repo = Repo.clone_from(repo_url, repo_path)
        self.repo_path = repo_path
        print(f"Repository cloned to {repo_path}")
        
        return repo_path
    
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
