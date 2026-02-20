"""
JavaScript/TypeScript Language Plugin
Combines parser, fixer, and configuration for JS/TS projects
"""
from typing import List
from .base import LanguagePlugin
from .javascript_parser import JavaScriptParser
from .javascript_fixer import JavaScriptFixer
from ..models import ErrorInfo


class JavaScriptPlugin(LanguagePlugin):
    """JavaScript/TypeScript language support"""
    
    def __init__(self):
        self.parser = JavaScriptParser()
        self.fixer = JavaScriptFixer()
    
    def get_name(self) -> str:
        return "javascript"
    
    def get_docker_image(self) -> str:
        return "rift-agent-node:latest"
    
    def get_test_command(self) -> List[str]:
        # Jest is most common, but could detect from package.json
        return ['npm', 'test', '--', '--ci', '--colors', '--passWithNoTests']
    
    def parse_errors(self, test_output: str, repo_path: str) -> List[ErrorInfo]:
        return self.parser.parse_errors(test_output, repo_path)
    
    def fix_error(self, error: ErrorInfo) -> bool:
        return self.fixer.fix_error(error)
    
    def get_file_extensions(self) -> List[str]:
        return ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']
