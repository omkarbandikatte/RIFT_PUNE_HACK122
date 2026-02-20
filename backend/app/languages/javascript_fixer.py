"""
JavaScript/TypeScript Code Fixer
Applies automated fixes for common errors
"""
import re
import os
from ..models import ErrorInfo, ErrorType


class JavaScriptFixer:
    """Fix JavaScript/TypeScript errors"""
    
    def fix_error(self, error: ErrorInfo) -> bool:
        """Apply fix for JavaScript error"""
        
        print(f"Attempting to fix {error.type.value} in {error.file}:{error.line}")
        
        # Verify file exists
        if not os.path.exists(error.file):
            print(f"File not found: {error.file}")
            return False
        
        try:
            if error.type == ErrorType.SYNTAX:
                return self._fix_syntax(error)
            elif error.type == ErrorType.TYPE_ERROR:
                return self._fix_type_error(error)
            elif error.type == ErrorType.IMPORT:
                return self._fix_import(error)
            elif error.type == ErrorType.LOGIC:
                return self._fix_logic(error)
            elif error.type == ErrorType.INDENTATION:
                return self._fix_indentation(error)
            else:
                print(f"  No fixer for error type: {error.type}")
                return False
                
        except Exception as e:
            print(f"  Error during fix: {e}")
            return False
    
    def _fix_syntax(self, error: ErrorInfo) -> bool:
        """Fix JavaScript syntax errors"""
        try:
            with open(error.file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_idx = error.line - 1
            if line_idx >= len(lines):
                return False
                
            line = lines[line_idx]
            original_line = line
            
            # Fix 1: Missing semicolon
            if 'missing ;' in error.message.lower() or 'semicolon' in error.message.lower():
                if not line.rstrip().endswith((';', '{', '}', ',', '//')):
                    lines[line_idx] = line.rstrip() + ';\n'
                    print(f"  ✓ Added semicolon at line {error.line}")
            
            # Fix 2: Missing closing brace
            elif 'missing }' in error.message.lower():
                indent = len(line) - len(line.lstrip())
                lines.insert(line_idx + 1, ' ' * indent + '}\n')
                print(f"  ✓ Added closing brace after line {error.line}")
            
            # Fix 3: Missing closing parenthesis
            elif 'missing )' in error.message.lower():
                lines[line_idx] = line.rstrip() + ')\n'
                print(f"  ✓ Added closing parenthesis at line {error.line}")
            
            # Fix 4: Missing closing bracket
            elif 'missing ]' in error.message.lower():
                lines[line_idx] = line.rstrip() + ']\n'
                print(f"  ✓ Added closing bracket at line {error.line}")
            
            # Fix 5: Unexpected token (often quotes)
            elif 'unexpected token' in error.message.lower() and '"' in line:
                # Try to balance quotes
                if line.count('"') % 2 != 0:
                    lines[line_idx] = line.rstrip() + '";\n'
                    print(f"  ✓ Added closing quote at line {error.line}")
            
            # Fix 6: Unexpected end of input (missing closing braces)
            elif 'unexpected end of input' in error.message.lower():
                # Add closing brace at end
                indent = len(line) - len(line.lstrip())
                lines.append(' ' * max(0, indent - 2) + '}\n')
                print(f"  ✓ Added closing brace at end of file")
            
            # Fix 7: const without assignment
            elif 'const' in line and '=' not in line and ';' in line:
                lines[line_idx] = line.replace('const ', 'let ')
                print(f"  ✓ Changed const to let (no assignment)")
            
            # Check if we made changes
            if lines[line_idx] != original_line or len(lines) != len([l for l in open(error.file)]):
                with open(error.file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
            
            return False
            
        except Exception as e:
            print(f"  ✗ Error fixing syntax: {e}")
            return False
    
    def _fix_type_error(self, error: ErrorInfo) -> bool:
        """Fix JavaScript type errors"""
        try:
            with open(error.file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_idx = error.line - 1
            if line_idx >= len(lines):
                return False
                
            line = lines[line_idx]
            original_line = line
            
            # Fix 1: Cannot read property of undefined/null - Add optional chaining
            if 'cannot read propert' in error.message.lower() and ('undefined' in error.message.lower() or 'null' in error.message.lower()):
                # Replace first dot with optional chaining
                if '.' in line and '?.' not in line and 'console.' not in line:
                    # Find the problematic object access
                    lines[line_idx] = re.sub(r'(\w+)\.(\w+)', r'\1?.\2', line, count=1)
                    print(f"  ✓ Added optional chaining at line {error.line}")
            
            # Fix 2: is not a function
            elif 'is not a function' in error.message.lower():
                # Try to add optional chaining on method calls
                if '(' in line and '?.' not in line:
                    lines[line_idx] = re.sub(r'(\w+)\.(\w+)\(', r'\1?.\2(', line, count=1)
                    print(f"  ✓ Added optional chaining for function call at line {error.line}")
            
            # Fix 3: Variable is not defined - Initialize it
            elif 'is not defined' in error.message.lower():
                var_match = re.search(r"'?(\w+)'? is not defined", error.message)
                if var_match:
                    var_name = var_match.group(1)
                    
                    # Don't initialize if it looks like it should be imported
                    if var_name[0].isupper() or var_name in ['React', 'Vue', 'Angular', 'useState', 'useEffect']:
                        # Looks like it needs an import
                        indent = len(line) - len(line.lstrip())
                        # Try to find existing imports
                        import_line = -1
                        for i in range(min(20, len(lines))):
                            if 'import' in lines[i]:
                                import_line = i
                        
                        if import_line >= 0:
                            # Add import after last import
                            lines.insert(import_line + 1, f"import {var_name} from './{var_name.lower()}';\n")
                            print(f"  ✓ Added missing import for {var_name}")
                        else:
                            # Add import at top
                            lines.insert(0, f"import {var_name} from './{var_name.lower()}';\n")
                            print(f"  ✓ Added missing import for {var_name} at top")
                    else:
                        # Initialize variable
                        indent = len(line) - len(line.lstrip())
                        
                        # Find appropriate location (before current line or at function start)
                        insert_pos = line_idx
                        for i in range(line_idx - 1, max(-1, line_idx - 10), -1):
                            if 'function' in lines[i] or '{' in lines[i]:
                                insert_pos = i + 1
                                break
                        
                        lines.insert(insert_pos, ' ' * indent + f'let {var_name};\n')
                        print(f"  ✓ Initialized undefined variable: {var_name}")
            
            # Check if we made changes
            if lines != open(error.file).readlines():
                with open(error.file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
            
            return False
            
        except Exception as e:
            print(f"  ✗ Error fixing type error: {e}")
            return False
    
    def _fix_import(self, error: ErrorInfo) -> bool:
        """Fix JavaScript import errors"""
        try:
            with open(error.file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_idx = error.line - 1
            if line_idx >= len(lines):
                return False
                
            line = lines[line_idx]
            
            # Comment out problematic import (safer than removing)
            if 'import' in line.lower() or 'require' in line:
                lines[line_idx] = '// ' + line
                print(f"  ✓ Commented out problematic import at line {error.line}")
                
                with open(error.file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
            
            return False
            
        except Exception as e:
            print(f"  ✗ Error fixing import: {e}")
            return False
    
    def _fix_logic(self, error: ErrorInfo) -> bool:
        """Fix JavaScript logic errors"""
        try:
            with open(error.file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_idx = error.line - 1
            if line_idx >= len(lines):
                print(f"  ✗ Line {error.line} out of range (file has {len(lines)} lines)")
                return False
            
            line = lines[line_idx]
            original_line = line
            
            # Fix 1: Missing import (no-undef - variable not defined)
            if 'is not defined' in error.message and 'no-undef' in error.message:
                # Extract variable name from message: "'useState' is not defined"
                match = re.search(r"'([^']+)'", error.message)
                if match:
                    var_name = match.group(1)
                    print(f"  Attempting to add missing import: {var_name}")
                    
                    # Determine which package to import from based on common patterns
                    react_hooks = ['useState', 'useEffect', 'useContext', 'useCallback', 'useMemo', 'useRef', 'useReducer', 'useLayoutEffect']
                    react_functions = ['createContext', 'createElement', 'forwardRef', 'memo', 'lazy', 'Suspense']
                    
                    if var_name in react_hooks or var_name in react_functions:
                        # Add import from 'react'
                        # Find existing React imports or add new one
                        import_added = False
                        for i, import_line in enumerate(lines):
                            # Case 1: import React from 'react'; -> add to destructure
                            if "from 'react'" in import_line or 'from "react"' in import_line:
                                if 'import {' in import_line:
                                    # Already has destructured imports, add to it
                                    # import { useState } from 'react' -> import { useState, useContext } from 'react'
                                    import_line = import_line.replace('} from', f', {var_name}}} from')
                                    lines[i] = import_line
                                    print(f"  ✓ Added {var_name} to existing React imports")
                                    import_added = True
                                    break
                                elif 'import React' in import_line:
                                    # import React from 'react' -> import React, { useState } from 'react'
                                    lines[i] = import_line.replace('import React from', f'import React, {{ {var_name} }} from')
                                    print(f"  ✓ Added {var_name} to React import")
                                    import_added = True
                                    break
                        
                        # No existing React import found, add new one at top
                        if not import_added:
                            # Find first import or add at top
                            insert_pos = 0
                            for i, l in enumerate(lines):
                                if l.strip() and not l.strip().startswith('//'):
                                    insert_pos = i
                                    break
                            
                            lines.insert(insert_pos, f"import {{ {var_name} }} from 'react';\n")
                            print(f"  ✓ Added new React import for {var_name}")
                            import_added = True
                        
                        if import_added:
                            with open(error.file, 'w', encoding='utf-8') as f:
                                f.writelines(lines)
                            return True
                    
                    else:
                        print(f"  ℹ️ Unknown variable {var_name} - cannot determine import source")
                        return False
            
            # Fix 2: Unused variable/import (no-unused-vars)
            elif 'is defined but never used' in error.message or 'is assigned a value but never used' in error.message:
                # Extract variable name from message
                # Example: "'React' is defined but never used"
                match = re.search(r"'([^']+)'", error.message)
                if match:
                    var_name = match.group(1)
                    print(f"  Attempting to remove unused variable: {var_name}")
                    
                    # Case 1: Entire import statement for this variable only
                    # import React from 'react'  -> remove entire line
                    # import { useState } from 'react' -> remove entire line if only variable
                    if 'import' in line:
                        # Check if this is the only import from this line
                        if f'import {var_name}' in line or f'import {{ {var_name} }}' in line:
                            # Remove entire line
                            lines[line_idx] = ''
                            print(f"  ✓ Removed entire import line for {var_name}")
                        else:
                            # Remove just this import from a multi-import line
                            # import { useState, useEffect, React } from 'react'
                            line = line.replace(f', {var_name}', '')
                            line = line.replace(f'{var_name}, ', '')
                            line = line.replace(f'{var_name}', '')
                            # Clean up empty braces
                            line = re.sub(r'{\s*}', '{}', line)
                            if line.strip() == 'import {} from':
                                lines[line_idx] = ''
                            else:
                                lines[line_idx] = line
                            print(f"  ✓ Removed {var_name} from import statement")
                    
                    # Case 2: Variable declaration
                    # const React = require('react')  -> remove entire line
                    elif 'const ' in line or 'let ' in line or 'var ' in line:
                        if var_name in line:
                            # Comment out the line instead of removing (safer)
                            lines[line_idx] = '// ' + line
                            print(f"  ✓ Commented out unused variable declaration: {var_name}")
                    
                    # Case 3: Function parameter or other context
                    else:
                        # Comment out the line
                        lines[line_idx] = '// ' + line
                        print(f"  ✓ Commented out line with unused variable: {var_name}")
                    
                    # Write changes if line was modified
                    if lines[line_idx] != original_line:
                        with open(error.file, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        return True
            
            # Fix 2: Maximum call stack (infinite recursion) - Add guard
            elif 'maximum call stack' in error.message.lower():
                indent = len(line) - len(line.lstrip())
                
                # Add recursion guard
                lines.insert(line_idx, ' ' * indent + 'if (depth > 100) return; // Recursion guard\n')
                print(f"  ✓ Added recursion guard at line {error.line}")
                
                with open(error.file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
            
            # Fix 3: Missing prop validation (react/prop-types)
            elif 'missing in props validation' in error.message.lower():
                # Extract prop name
                match = re.search(r"'([^']+)'", error.message)
                if match:
                    prop_name = match.group(1)
                    # Add PropTypes at the top of component
                    # For now, just document the issue
                    print(f"  ℹ️ Prop validation issue for '{prop_name}' - manual fix recommended")
                return False
            
            # Fix 4: React Hooks issues
            elif 'react hook' in error.message.lower():
                if 'called conditionally' in error.message.lower():
                    print(f"  ℹ️ Hook called conditionally - requires manual restructuring")
                elif 'missing dependencies' in error.message.lower():
                    print(f"  ℹ️ Hook dependencies issue - manual fix recommended")
                return False
            
            return False
            
        except Exception as e:
            print(f"  ✗ Error fixing logic error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _fix_indentation(self, error: ErrorInfo) -> bool:
        """Fix JavaScript indentation errors"""
        try:
            with open(error.file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_idx = error.line - 1
            if line_idx >= len(lines):
                return False
                
            line = lines[line_idx]
            
            # Detect indent style (spaces or tabs)
            indent_char = '  '  # Default 2 spaces
            for l in lines[:20]:
                if l.startswith('    '):
                    indent_char = '    '  # 4 spaces
                    break
                elif l.startswith('\t'):
                    indent_char = '\t'
                    break
            
            # Fix: Align with previous non-empty line
            if line_idx > 0:
                prev_idx = line_idx - 1
                while prev_idx >= 0 and not lines[prev_idx].strip():
                    prev_idx -= 1
                
                if prev_idx >= 0:
                    prev_line = lines[prev_idx]
                    prev_indent = len(prev_line) - len(prev_line.lstrip())
                    
                    # Match indent
                    content = line.lstrip()
                    lines[line_idx] = ' ' * prev_indent + content
                    print(f"  ✓ Fixed indentation at line {error.line}")
                    
                    with open(error.file, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    return True
            
            return False
            
        except Exception as e:
            print(f"  ✗ Error fixing indentation: {e}")
            return False
