"""
Python Language Plugin
Wraps existing Python parser and fixer
"""
from typing import List
from .base import LanguagePlugin
from ..parser import ErrorParser
from ..fixer import FixEngine
from ..models import ErrorInfo


class PythonPlugin(LanguagePlugin):
    """Python language support"""
    
    def __init__(self, repo_path: str = None):
        self.parser = ErrorParser()
        self.fixer = FixEngine(repo_path) if repo_path else None
        self.repo_path = repo_path
    
    def get_name(self) -> str:
        return "python"
    
    def get_docker_image(self) -> str:
        return "rift-agent:latest"
    
    def get_test_command(self) -> List[str]:
        return ['python', '-m', 'pytest', '--maxfail=10', '-v', '--tb=short']
    
    def parse_errors(self, test_output: str, repo_path: str) -> List[ErrorInfo]:
        return self.parser.parse_errors(test_output, repo_path)
    
    def fix_error(self, error: ErrorInfo) -> bool:
        # Lazy initialization of fixer if not set
        if self.fixer is None:
            # Extract repo path from error file path if needed
            import os
            if error.file:
                # Assume repo is a few levels up from the error file
                repo_path = os.path.dirname(os.path.dirname(error.file))
                self.fixer = FixEngine(repo_path)
        
        # FixEngine uses apply_fix(), so call that
        return self.fixer.apply_fix(error) if self.fixer else False
    
    def get_file_extensions(self) -> List[str]:
        return ['.py']
