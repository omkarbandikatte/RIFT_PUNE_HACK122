import re
from typing import List
from app.models import ErrorInfo, ErrorType


class ErrorParser:
    """Parse pytest output and extract structured error information"""
    
    def __init__(self):
        self.error_patterns = {
            ErrorType.SYNTAX: [
                r'SyntaxError',
                r"expected ':'",
                r'invalid syntax',
            ],
            ErrorType.INDENTATION: [
                r'IndentationError',
                r'unexpected indent',
                r'expected an indented block',
            ],
            ErrorType.IMPORT: [
                r'ModuleNotFoundError',
                r'No module named',
            ],
            ErrorType.TYPE_ERROR: [
                r'TypeError',
                r"name '(List|Dict|Set|Tuple|Optional|Union|Any|Callable)' is not defined",  # Specific typing types
                r"name '.*?' is not defined",  # Catches other undefined types
            ],
            ErrorType.LOGIC: [
                r'NameError',  # Now checked AFTER TYPE_ERROR
            ],
            ErrorType.LINTING: [
                r'unused import',
                r'imported but unused',
            ],
        }
        
        # Pattern to extract file and line number
        self.file_line_pattern = r'File "(.*?)", line (\d+)'
    
    def parse_errors(self, test_output: str) -> List[ErrorInfo]:
        """Parse test output and return structured error information"""
        errors = []
        lines = test_output.split('\n')
        
        current_file = None
        current_line = None
        
        for i, line in enumerate(lines):
            # Try to extract file and line number
            file_match = re.search(self.file_line_pattern, line)
            if file_match:
                current_file = file_match.group(1)
                current_line = int(file_match.group(2))
                
                # Skip frozen/built-in Python modules (these are cascade errors)
                if current_file.startswith('<frozen') or current_file.startswith('<'):
                    continue
                
                # Look ahead for error type
                error_type, error_message = self._identify_error_type(
                    line, lines[i:min(i+5, len(lines))]
                )
                
                if error_type and current_file and current_line:
                    errors.append(ErrorInfo(
                        file=current_file,
                        line=current_line,
                        type=error_type,
                        message=error_message
                    ))
                    
        return errors
    
    def _identify_error_type(self, current_line: str, context_lines: List[str]) -> tuple:
        """Identify error type from line and context"""
        # Combine current line and next few lines for context
        combined_text = '\n'.join(context_lines)
        
        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    # Extract error message
                    message_match = re.search(pattern, combined_text, re.IGNORECASE)
                    message = message_match.group(0) if message_match else combined_text[:100]
                    return error_type, message
        
        # If no match found
        return ErrorType.UNKNOWN, "Unknown error"
    
    def parse_pytest_summary(self, output: str) -> dict:
        """Extract summary information from pytest output"""
        summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
        }
        
        # Look for pytest summary line
        summary_pattern = r'(\d+) failed.*?(\d+) passed'
        match = re.search(summary_pattern, output)
        if match:
            summary["failed"] = int(match.group(1))
            summary["passed"] = int(match.group(2))
            summary["total_tests"] = summary["failed"] + summary["passed"]
        
        # Alternative pattern
        failed_only = re.search(r'(\d+) failed', output)
        if failed_only and not match:
            summary["failed"] = int(failed_only.group(1))
        
        passed_only = re.search(r'(\d+) passed', output)
        if passed_only and not match:
            summary["passed"] = int(passed_only.group(1))
            
        return summary
