# Multi-Language Support Roadmap 🌍

## Current State ✅
- **Python**: Full support with 34 error patterns, 25+ fix strategies
- **JavaScript**: Partial detection (package.json), but no error patterns/fixers yet

## Architecture Overview

The agent follows a **language-agnostic architecture** with language-specific plugins:

```
┌─────────────────────────────────────────┐
│         DockerRunner (Orchestrator)     │
├─────────────────────────────────────────┤
│  - Language Detection                   │
│  - Docker Container Management          │
│  - Test Execution                       │
│  - Git Operations                       │
└─────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌───────────────┐      ┌────────────────┐
│ Language      │      │  Language      │
│ Detector      │      │  Registry      │
└───────────────┘      └────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Python       │     │ JavaScript   │     │ Java         │
│ Plugin       │     │ Plugin       │     │ Plugin       │
├──────────────┤     ├──────────────┤     ├──────────────┤
│ - Parser     │     │ - Parser     │     │ - Parser     │
│ - Fixer      │     │ - Fixer      │     │ - Fixer      │
│ - Dockerfile │     │ - Dockerfile │     │ - Dockerfile │
│ - Test Cmd   │     │ - Test Cmd   │     │ - Test Cmd   │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## Language Plugin Components

Each language needs 4 components:

### 1. **Language Detector** 
Identifies project language from files:
```python
{
    'python': ['requirements.txt', 'setup.py', 'pyproject.toml'],
    'javascript': ['package.json'],
    'typescript': ['package.json', 'tsconfig.json'],
    'java': ['pom.xml', 'build.gradle'],
    'go': ['go.mod'],
    'rust': ['Cargo.toml'],
    'ruby': ['Gemfile'],
    'csharp': ['*.csproj', '*.sln']
}
```

### 2. **Error Parser**
Extract errors from test output:
```python
class LanguageParser(ABC):
    @abstractmethod
    def parse_errors(self, output: str, repo_path: str) -> List[ErrorInfo]
    
    @abstractmethod  
    def get_file_line_patterns(self) -> List[str]
```

### 3. **Code Fixer**
Apply language-specific fixes:
```python
class LanguageFixer(ABC):
    @abstractmethod
    def fix_error(self, error: ErrorInfo) -> bool
    
    @abstractmethod
    def get_supported_patterns(self) -> Dict[ErrorType, List[str]]
```

### 4. **Docker Image**
Container with language runtime + test framework:
```dockerfile
# Python: rift-agent-python:latest
# Node:   rift-agent-node:latest  
# Java:   rift-agent-java:latest
# Go:     rift-agent-go:latest
```

---

## Supported Languages Roadmap

### 🟢 Tier 1 (High Priority)

#### 1. **JavaScript/TypeScript** 
- **Frameworks**: Jest, Mocha, Vitest
- **Error Patterns**:
  - Syntax: Missing semicolons, unclosed braces, undefined variables
  - Type: TypeScript type errors, null/undefined
  - Import: Missing modules, wrong paths
- **Test Command**: `npm test` or `yarn test`
- **Docker Base**: `node:18-slim`
- **Estimated Work**: 2-3 days

#### 2. **Java**
- **Frameworks**: JUnit, TestNG
- **Error Patterns**:
  - Compilation: Missing semicolons, type mismatches
  - Null: NullPointerException fixes
  - Import: Missing imports, wrong packages
- **Test Command**: `mvn test` or `gradle test`
- **Docker Base**: `openjdk:17-slim`
- **Estimated Work**: 3-4 days

### 🟡 Tier 2 (Medium Priority)

#### 3. **Go**
- **Framework**: Built-in `go test`
- **Error Patterns**:
  - Syntax: Missing braces, type errors
  - Import: Unused imports, missing packages
  - Concurrency: Race conditions (harder)
- **Test Command**: `go test ./...`
- **Docker Base**: `golang:1.21-alpine`
- **Estimated Work**: 2-3 days

#### 4. **Rust**
- **Framework**: Built-in `cargo test`
- **Error Patterns**:
  - Ownership: Borrow checker errors
  - Syntax: Missing semicolons, type errors
  - Lifetime: Basic lifetime fixes
- **Test Command**: `cargo test`
- **Docker Base**: `rust:1.75-slim`
- **Estimated Work**: 4-5 days (complex)

### 🔵 Tier 3 (Lower Priority)

#### 5. **Ruby**
- **Framework**: RSpec, Minitest
- **Test Command**: `rspec` or `rake test`
- **Docker Base**: `ruby:3.2-slim`

#### 6. **C#/.NET**
- **Framework**: NUnit, xUnit
- **Test Command**: `dotnet test`
- **Docker Base**: `mcr.microsoft.com/dotnet/sdk:8.0`

#### 7. **PHP**
- **Framework**: PHPUnit
- **Test Command**: `phpunit`
- **Docker Base**: `php:8.2-cli`

---

## Implementation Example: JavaScript/TypeScript

### Step 1: Create Language Registry

**File: `backend/app/languages/__init__.py`**
```python
"""
Language Plugin Registry
Each language has: detector, parser, fixer, docker config
"""
from typing import Dict, Type
from .base import LanguagePlugin
from .python_plugin import PythonPlugin
from .javascript_plugin import JavaScriptPlugin

LANGUAGE_REGISTRY: Dict[str, Type[LanguagePlugin]] = {
    'python': PythonPlugin,
    'javascript': JavaScriptPlugin,
    'typescript': JavaScriptPlugin,  # Same as JS
}

def detect_language(repo_path: str) -> str:
    """Detect language from project files"""
    import os
    
    markers = {
        'python': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile'],
        'javascript': ['package.json'],
        'typescript': ['tsconfig.json'],
        'java': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
        'go': ['go.mod', 'go.sum'],
        'rust': ['Cargo.toml'],
        'ruby': ['Gemfile', 'Rakefile'],
        'csharp': ['*.csproj', '*.sln'],
    }
    
    for lang, files in markers.items():
        for marker_file in files:
            if '*' in marker_file:
                # Glob pattern
                import glob
                if glob.glob(os.path.join(repo_path, marker_file)):
                    return lang
            else:
                if os.path.exists(os.path.join(repo_path, marker_file)):
                    return lang
    
    return 'unknown'

def get_language_plugin(language: str) -> LanguagePlugin:
    """Get language plugin instance"""
    plugin_class = LANGUAGE_REGISTRY.get(language)
    if plugin_class:
        return plugin_class()
    else:
        # Fallback to Python
        return PythonPlugin()
```

### Step 2: Create JavaScript Parser

**File: `backend/app/languages/javascript_parser.py`**
```python
"""
JavaScript/TypeScript Error Parser
Handles Jest, Mocha, ESLint errors
"""
import re
from typing import List
from ..models import ErrorInfo, ErrorType

class JavaScriptParser:
    def __init__(self):
        # JavaScript error patterns
        self.error_patterns = {
            ErrorType.SYNTAX: [
                r'SyntaxError',
                r'Unexpected token',
                r'missing \)',
                r'missing \}',
                r'missing ;',
                r'Unexpected identifier',
            ],
            ErrorType.TYPE_ERROR: [
                r'TypeError',
                r'Cannot read property.*of undefined',
                r'Cannot read properties of null',
                r'is not a function',
                r'is not defined',
            ],
            ErrorType.IMPORT: [
                r'Cannot find module',
                r'Module not found',
                r'Failed to resolve',
                r'Cannot resolve module',
            ],
            ErrorType.LOGIC: [
                r'ReferenceError',
                r'is not defined',
                r'RangeError',
                r'Maximum call stack',
            ],
        }
        
        # File path patterns for JS/TS
        # Jest: at Object.<anonymous> (src/file.js:123:45)
        # ESLint: /path/to/file.js:123:45: error
        self.file_line_patterns = [
            r'at .*?\(([^:]+):(\d+):(\d+)\)',  # Stack trace
            r'^\s*([/\\]?[\w/\\.-]+\.(?:js|ts|jsx|tsx)):(\d+):(\d+)',  # ESLint format
            r'Error in ([^:]+):(\d+)',  # Generic format
        ]
    
    def parse_errors(self, test_output: str, repo_path: str = None) -> List[ErrorInfo]:
        """Parse Jest/Mocha test output"""
        errors = []
        lines = test_output.split('\n')
        
        print(f"[JS-PARSER] Parsing errors from test output")
        
        for i, line in enumerate(lines):
            # Try each file/line pattern
            for pattern in self.file_line_patterns:
                match = re.search(pattern, line)
                if match:
                    current_file = match.group(1)
                    current_line = int(match.group(2))
                    
                    print(f"[JS-PARSER] Found: {current_file}:{current_line}")
                    
                    # Convert paths if needed
                    if current_file.startswith('/workspace'):
                        import os
                        if repo_path:
                            relative = current_file[len('/workspace'):].lstrip('/')
                            current_file = os.path.join(repo_path, relative)
                    
                    # Skip node_modules
                    if 'node_modules' in current_file:
                        continue
                    
                    # Identify error type
                    error_type, message = self._identify_error(
                        line, lines[i:min(i+5, len(lines))]
                    )
                    
                    if error_type:
                        errors.append(ErrorInfo(
                            file=current_file,
                            line=current_line,
                            type=error_type,
                            message=message
                        ))
                    break
        
        print(f"[JS-PARSER] Found {len(errors)} errors")
        return errors
    
    def _identify_error(self, line: str, context: List[str]) -> tuple:
        """Identify JavaScript error type"""
        combined = '\n'.join(context)
        
        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    return error_type, re.search(pattern, combined, re.IGNORECASE).group(0)
        
        return ErrorType.UNKNOWN, "Unknown error"
```

### Step 3: Create JavaScript Fixer

**File: `backend/app/languages/javascript_fixer.py`**
```python
"""
JavaScript/TypeScript Code Fixer
Applies automated fixes for common errors
"""
import re
from ..models import ErrorInfo, ErrorType

class JavaScriptFixer:
    def fix_error(self, error: ErrorInfo) -> bool:
        """Apply fix for JavaScript error"""
        
        if error.type == ErrorType.SYNTAX:
            return self._fix_syntax(error)
        elif error.type == ErrorType.TYPE_ERROR:
            return self._fix_type_error(error)
        elif error.type == ErrorType.IMPORT:
            return self._fix_import(error)
        
        return False
    
    def _fix_syntax(self, error: ErrorInfo) -> bool:
        """Fix JavaScript syntax errors"""
        try:
            with open(error.file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_idx = error.line - 1
            line = lines[line_idx]
            
            # Fix missing semicolon
            if 'missing ;' in error.message.lower():
                if not line.rstrip().endswith((';', '{', '}', ',')):
                    lines[line_idx] = line.rstrip() + ';\n'
                    print(f"  Added semicolon at line {error.line}")
            
            # Fix missing closing brace
            elif 'missing }' in error.message.lower():
                indent = len(line) - len(line.lstrip())
                lines.insert(line_idx + 1, ' ' * indent + '}\n')
                print(f"  Added closing brace after line {error.line}")
            
            # Fix const/let without assignment
            elif 'const' in line and '=' not in line:
                lines[line_idx] = line.replace('const ', 'let ')
                print(f"  Changed const to let (no assignment)")
            
            # Write back
            with open(error.file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return True
            
        except Exception as e:
            print(f"  Error fixing: {e}")
            return False
    
    def _fix_type_error(self, error: ErrorInfo) -> bool:
        """Fix JavaScript type errors"""
        try:
            with open(error.file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_idx = error.line - 1
            line = lines[line_idx]
            
            # Add optional chaining for undefined access
            if 'cannot read property' in error.message.lower():
                # obj.prop -> obj?.prop
                if '.' in line and '?.' not in line:
                    lines[line_idx] = line.replace('.', '?.', 1)
                    print(f"  Added optional chaining at line {error.line}")
            
            # Add null check
            elif 'is not defined' in error.message.lower():
                # Extract variable name
                var_match = re.search(r"'(\w+)' is not defined", error.message)
                if var_match:
                    var_name = var_match.group(1)
                    # Add at beginning of function/block
                    indent = len(line) - len(line.lstrip())
                    lines.insert(line_idx, ' ' * indent + f'const {var_name} = null;\n')
                    print(f"  Initialized undefined variable: {var_name}")
            
            with open(error.file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return True
            
        except Exception as e:
            print(f"  Error fixing: {e}")
            return False
    
    def _fix_import(self, error: ErrorInfo) -> bool:
        """Fix JavaScript import errors"""
        # Comment out missing imports (safer than removing)
        try:
            with open(error.file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            line_idx = error.line - 1
            line = lines[line_idx]
            
            if 'import' in line.lower() or 'require' in line:
                lines[line_idx] = '// ' + line
                print(f"  Commented out problematic import at line {error.line}")
            
            with open(error.file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return True
            
        except Exception as e:
            print(f"  Error fixing: {e}")
            return False
```

### Step 4: Create JavaScript Docker Image

**File: `backend/docker/Dockerfile.agent.node`**
```dockerfile
FROM node:18-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Create non-root user
RUN useradd -m -u 1000 agent && \
    chown -R agent:agent /workspace

# Switch to non-root user
USER agent

# Set environment
ENV NODE_ENV=test
ENV CI=true

# Entrypoint will install deps and run tests
COPY docker/agent_entrypoint_node.py /usr/local/bin/entrypoint.py
RUN chmod +x /usr/local/bin/entrypoint.py

ENTRYPOINT ["python3", "/usr/local/bin/entrypoint.py"]
```

**File: `backend/docker/agent_entrypoint_node.py`**
```python
#!/usr/bin/env python3
"""Node.js Agent Entrypoint"""
import subprocess
import json
import os
import time

def install_dependencies():
    """Install npm dependencies"""
    if os.path.exists('package.json'):
        print("📦 Installing npm dependencies...")
        result = subprocess.run(
            ['npm', 'ci' if os.path.exists('package-lock.json') else 'install'],
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=300
        )
        return result.returncode == 0
    return False

def run_tests():
    """Run npm test"""
    print("🧪 Running tests...")
    result = subprocess.run(
        ['npm', 'test', '--', '--ci', '--colors'],
        capture_output=True,
        encoding='utf-8',
        errors='replace',
        timeout=120
    )
    return result

def main():
    start = time.time()
    
    # Install deps
    deps_ok = install_dependencies()
    
    # Run tests
    test_result = run_tests()
    
    # Format output
    output = {
        'stdout': test_result.stdout,
        'stderr': test_result.stderr,
        'returncode': test_result.returncode,
        'success': test_result.returncode == 0,
        'elapsed': time.time() - start
    }
    
    # Print JSON output between markers
    print("\n=== AGENT OUTPUT ===")
    print(json.dumps(output, indent=2))
    print("=== END OUTPUT ===")
    
    return test_result.returncode

if __name__ == '__main__':
    exit(main())
```

---

## Integration Steps

### 1. Update DockerRunner to use Language Plugins

```python
from app.languages import detect_language, get_language_plugin

class DockerRunner:
    def __init__(self):
        # ...
        self.language = None
        self.language_plugin = None
    
    def run(self):
        # Detect language
        self.language = detect_language(repo_path)
        self.language_plugin = get_language_plugin(self.language)
        
        # Use language-specific parser and fixer
        parser = self.language_plugin.get_parser()
        fixer = self.language_plugin.get_fixer()
        docker_image = self.language_plugin.get_docker_image()
        
        # Run tests with appropriate container
        errors = parser.parse_errors(output, repo_path)
        
        for error in errors:
            fixer.fix_error(error)
```

---

## Testing Priority Order

1. **JavaScript/TypeScript** (most popular with Python)
   - Test with: React, Vue, Next.js repos
   - Common errors: undefined variables, import issues, type errors

2. **Java** (enterprise standard)
   - Test with: Spring Boot, Maven projects
   - Common errors: NullPointerException, compilation errors

3. **Go** (gaining popularity)
   - Test with: Standard Go projects
   - Common errors: unused imports, type errors

---

## Success Metrics per Language

- **Detection Rate**: % of real errors found (vs false positives)
- **Fix Rate**: % of detected errors successfully fixed
- **False Positive Rate**: % of non-repo files incorrectly flagged

Target: 80%+ fix rate, <5% false positive rate

---

## Quick Win: Add JavaScript NOW

To get JavaScript support quickly (1-2 hours):

1. Create `backend/app/languages/` folder
2. Copy the JavaScript parser/fixer code above
3. Build Node Docker image
4. Update docker_runner.py to route JS projects to Node container
5. Test with a simple Jest project

Let me know if you want me to implement JavaScript support now! 🚀
