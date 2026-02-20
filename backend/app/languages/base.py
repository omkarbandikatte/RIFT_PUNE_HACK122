"""
Language Plugin Architecture
Base classes and interfaces for multi-language support
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
from ..models import ErrorInfo, ErrorType


class LanguagePlugin(ABC):
    """Base class for language-specific plugins"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Return language name"""
        pass
    
    @abstractmethod
    def get_docker_image(self) -> str:
        """Return Docker image name for this language"""
        pass
    
    @abstractmethod
    def get_test_command(self) -> List[str]:
        """Return default test command"""
        pass
    
    @abstractmethod
    def parse_errors(self, test_output: str, repo_path: str) -> List[ErrorInfo]:
        """Parse test output and extract errors"""
        pass
    
    @abstractmethod
    def fix_error(self, error: ErrorInfo) -> bool:
        """Apply fix for detected error"""
        pass
    
    @abstractmethod
    def get_file_extensions(self) -> List[str]:
        """Return file extensions for this language"""
        pass
