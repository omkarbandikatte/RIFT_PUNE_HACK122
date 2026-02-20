"""
JavaScript/TypeScript Error Parser
Handles Jest, Mocha, Vitest, ESLint errors
"""
import re
import os
from typing import List, Tuple
from ..models import ErrorInfo, ErrorType


class JavaScriptParser:
    """Parse JavaScript/TypeScript test errors"""
    
    def __init__(self):
        # JavaScript error patterns
        self.error_patterns = {
            ErrorType.SYNTAX: [
                r'SyntaxError',
                r'Unexpected token',
                r'Unexpected identifier',
                r'Unexpected end of input',
                r'missing \)',
                r'missing \}',
                r'missing ]',
                r'missing ;',
                r'Unexpected string',
                r'Invalid or unexpected token',
            ],
            ErrorType.TYPE_ERROR: [
                r'TypeError',
                r'Cannot read propert(?:y|ies) .* of undefined',
                r'Cannot read propert(?:y|ies) of null',
                r'is not a function',
                r'is not defined',
                r'Cannot set propert(?:y|ies) of undefined',
                r'undefined is not an object',
            ],
            ErrorType.IMPORT: [
                r'Cannot find module',
                r'Module not found',
                r'Failed to resolve',
                r'Cannot resolve module',
                r'Module .* does not exist',
                r'Unable to resolve path',
            ],
            ErrorType.LOGIC: [
                r'ReferenceError',
                r'RangeError',
                r'Maximum call stack size exceeded',
                r'Infinite loop',
                r'Test timeout',
            ],
            ErrorType.INDENTATION: [
                r'Unexpected indent',
                r'IndentationError',
            ],
        }
        
        # Multiple file path patterns for different test frameworks and linters
        # Jest: at Object.<anonymous> (src/file.js:123:45)
        # ESLint: /path/to/file.js:123:45: error OR /path/file.js  123:45  error
        # ESLint alternate: src/file.js  1:1  error  message
        # Vitest: Error: src/file.ts:123:45
        self.file_line_patterns = [
            # ESLint format with spaces: /path/file.js  1:1  error
            r'^\s*([/\\]?[\w/\\.-]+\.(?:js|ts|jsx|tsx))\s+(\d+):(\d+)\s+(?:error|warning)',
            # Stack trace format
            r'at .*?\(([^:)]+\.(?:js|ts|jsx|tsx)):(\d+):(\d+)\)',
            # Standard colon format: file.js:123:45:
            r'^\s*([/\\]?[\w/\\.-]+\.(?:js|ts|jsx|tsx)):(\d+):(\d+)',
            # Generic error format
            r'Error.*?([/\\]?[\w/\\.-]+\.(?:js|ts|jsx|tsx)):(\d+):(\d+)',
            # Alternate: File: path
            r'File:\s+([/\\]?[\w/\\.-]+\.(?:js|ts|jsx|tsx)):(\d+)',
        ]
        
        # ESLint-specific error type patterns
        self.eslint_patterns = {
            'no-unused-vars': ErrorType.LOGIC,
            'no-undef': ErrorType.LOGIC,
            'semi': ErrorType.SYNTAX,
            'quotes': ErrorType.SYNTAX,
            'indent': ErrorType.INDENTATION,
            'no-console': ErrorType.LINTING,
            'import/': ErrorType.IMPORT,
        }
    
    def parse_errors(self, test_output: str, repo_path: str = None) -> List[ErrorInfo]:
        """Parse Jest/Mocha/Vitest/ESLint test output"""
        errors = []
        lines = test_output.split('\n')
        seen_errors = set()  # Deduplicate
        
        print(f"[JS-PARSER] Parsing errors from test output (repo_path={repo_path})")
        
        # Check for ESLint multi-line format first
        # ESLint format: filename on one line, then indented error lines like:  
        # /workspace/src/App.jsx
        #   1:8  error  'React' is defined but never used  no-unused-vars
        current_file = None
        for i, line in enumerate(lines):
            # Check if this line is a file path (ESLint header)
            if line.strip() and not line.startswith(' ') and re.match(r'^[/\\]?[\w/\\.-]+\.(?:js|ts|jsx|tsx)$', line.strip()):
                current_file = line.strip()
                print(f"[JS-PARSER] Found ESLint file header: {current_file}")
                continue
            
            # Check if this is an indented error line (ESLint error detail)
            if current_file and line.startswith('  ') and ':' in line:
                # Pattern: "  1:8  error  message  rule-name"
                eslint_match = re.match(r'^\s+(\d+):(\d+)\s+(error|warning)\s+(.+?)(?:\s+([a-z/-]+))?$', line)
                if eslint_match:
                    line_num = int(eslint_match.group(1))
                    error_level = eslint_match.group(3)
                    message = eslint_match.group(4).strip()
                    rule = eslint_match.group(5) if eslint_match.group(5) else None
                    
                    print(f"[JS-PARSER] Found ESLint error: {current_file}:{line_num} - {message} ({rule})")
                    
                    # Convert Docker paths
                    file_path = current_file
                    if file_path.startswith('/workspace'):
                        if repo_path:
                            relative_path = file_path[len('/workspace'):].lstrip('/')
                            file_path = os.path.join(repo_path, relative_path)
                            print(f"[JS-PARSER] 🐳 Converted container path: {file_path}")
                        else:
                            print(f"[JS-PARSER] ❌ Skipped (no repo_path)")
                            continue
                    
                    # Skip system files
                    skip_patterns = ['node_modules', 'dist', 'build', '.next', 'coverage']
                    if any(p in file_path for p in skip_patterns):
                        continue
                    
                    # Normalize path
                    if repo_path:
                        file_path = os.path.normpath(file_path)
                    
                    # Determine error type from rule
                    error_type = self._get_eslint_error_type(rule, message)
                    
                    # Deduplicate
                    error_key = f"{file_path}:{line_num}:{error_type.value}"
                    if error_key not in seen_errors:
                        seen_errors.add(error_key)
                        print(f"[JS-PARSER] ✅ {error_type.value}: {file_path}:{line_num}")
                        errors.append(ErrorInfo(
                            file=file_path,
                            line=line_num,
                            type=error_type,
                            message=f"{message} ({rule})" if rule else message
                        ))
                    continue
            
            # Fallback: Try single-line patterns (Jest, Mocha, etc.)
            for pattern in self.file_line_patterns:
                match = re.search(pattern, line)
                if match:
                    file_path = match.group(1)
                    line_num = int(match.group(2))
                    
                    # Convert Docker paths
                    if file_path.startswith('/workspace'):
                        if repo_path:
                            relative_path = file_path[len('/workspace'):].lstrip('/')
                            file_path = os.path.join(repo_path, relative_path)
                        else:
                            continue
                    
                    # Skip system files
                    skip_patterns = ['node_modules', 'dist', 'build', '.next', 'coverage', 'jest-runtime', '/usr/lib', '/usr/local']
                    if any(p in file_path for p in skip_patterns):
                        continue
                    
                    # Normalize path
                    if repo_path:
                        file_path = os.path.normpath(file_path)
                    
                    # Identify error type
                    error_type, message = self._identify_error_type(line, lines[i:min(i+5, len(lines))])
                    
                    if error_type:
                        error_key = f"{file_path}:{line_num}:{error_type.value}"
                        if error_key not in seen_errors:
                            seen_errors.add(error_key)
                            errors.append(ErrorInfo(
                                file=file_path,
                                line=line_num,
                                type=error_type,
                                message=message
                            ))
                    break
        
        print(f"[JS-PARSER] Total errors detected: {len(errors)}")
        return errors
    
    def _get_eslint_error_type(self, rule: str, message: str) -> ErrorType:
        """Map ESLint rule to error type"""
        if not rule:
            return ErrorType.LOGIC
        
        # Check if rule matches known patterns
        if rule in self.eslint_patterns:
            return self.eslint_patterns[rule]
        
        # Fallback patterns
        if 'unused' in rule or 'undef' in rule:
            return ErrorType.LOGIC
        if 'semi' in rule or 'quotes' in rule or 'comma' in rule:
            return ErrorType.SYNTAX
        if 'import' in rule or 'require' in rule:
            return ErrorType.IMPORT
        if 'indent' in rule or 'space' in rule:
            return ErrorType.INDENTATION
        if 'console' in rule or 'debugger' in rule:
            return ErrorType.LINTING
        
        return ErrorType.LOGIC
    
    def _identify_error_type(self, current_line: str, context_lines: List[str]) -> Tuple:
        """Identify JavaScript error type from context"""
        # Combine current line and next few lines for context
        combined_text = '\n'.join(context_lines)
        
        # Check for ESLint rule names first (most specific)
        # ESLint format: file.js  1:1  error  message  rule-name
        eslint_rule_match = re.search(r'([\w/-]+)\s*$', current_line)
        if eslint_rule_match:
            rule_name = eslint_rule_match.group(1)
            # Check if this matches known ESLint rules
            for pattern, error_type in self.eslint_patterns.items():
                if pattern in rule_name:
                    # Extract the full error message
                    message_match = re.search(r'(?:error|warning)\s+(.+?)\s+[\w/-]+\s*$', current_line)
                    if message_match:
                        message = message_match.group(1).strip()
                    else:
                        message = current_line.strip()
                    return error_type, f"{message} ({rule_name})"
        
        # Fall back to generic pattern matching
        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    # Extract error message
                    message_match = re.search(pattern, combined_text, re.IGNORECASE)
                    message = message_match.group(0) if message_match else combined_text[:100]
                    return error_type, message
        
        # If no match found but it looks like an ESLint error, classify as LINTING
        if 'error' in current_line.lower() or 'warning' in current_line.lower():
            return ErrorType.LINTING, current_line.strip()
        
        return ErrorType.UNKNOWN, "Unknown error"
