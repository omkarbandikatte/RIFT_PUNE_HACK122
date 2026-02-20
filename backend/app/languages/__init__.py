"""
Language Plugin Registry
Auto-detect language and load appropriate plugin
"""
import os
import glob
from typing import Dict, Type, Optional
from .base import LanguagePlugin
from .python_plugin import PythonPlugin
from .javascript_plugin import JavaScriptPlugin


# Registry of available language plugins
LANGUAGE_REGISTRY: Dict[str, Type[LanguagePlugin]] = {
    'python': PythonPlugin,
    'javascript': JavaScriptPlugin,
    'typescript': JavaScriptPlugin,  # TypeScript uses same plugin as JavaScript
}


def detect_language(repo_path: str) -> str:
    """
    Detect programming language from project files
    
    Args:
        repo_path: Path to repository
        
    Returns:
        Language name (python, javascript, typescript, etc.)
    """
    print(f"🔍 Detecting project language in {repo_path}")
    
    # Language markers (file patterns that indicate language)
    markers = {
        'typescript': ['tsconfig.json'],  # Check TypeScript first (more specific)
        'javascript': ['package.json', 'package-lock.json', 'yarn.lock'],
        'python': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile', 'poetry.lock'],
        'java': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
        'go': ['go.mod', 'go.sum'],
        'rust': ['Cargo.toml', 'Cargo.lock'],
        'ruby': ['Gemfile', 'Gemfile.lock', 'Rakefile'],
        'csharp': ['*.csproj', '*.sln'],
        'php': ['composer.json', 'composer.lock'],
    }
    
    for lang, files in markers.items():
        for marker_file in files:
            if '*' in marker_file:
                # Glob pattern
                pattern = os.path.join(repo_path, marker_file)
                if glob.glob(pattern):
                    print(f"  ✓ Detected {lang} (found {marker_file})")
                    return lang
            else:
                # Exact file match
                file_path = os.path.join(repo_path, marker_file)
                if os.path.exists(file_path):
                    print(f"  ✓ Detected {lang} (found {marker_file})")
                    return lang
    
    # Fallback: Count file extensions
    print("  ⚠️  No marker files found, analyzing file extensions...")
    extension_count = {}
    
    for root, dirs, files in os.walk(repo_path):
        # Skip common dependency folders
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.venv', 'venv', 'dist', 'build', '.git']]
        
        for file in files:
            _, ext = os.path.splitext(file)
            if ext:
                extension_count[ext] = extension_count.get(ext, 0) + 1
    
    # Map extensions to languages
    extension_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.cs': 'csharp',
        '.php': 'php',
    }
    
    max_count = 0
    detected_lang = 'unknown'
    
    for ext, count in extension_count.items():
        if ext in extension_map and count > max_count:
            max_count = count
            detected_lang = extension_map[ext]
    
    if detected_lang != 'unknown':
        print(f"  ✓ Detected {detected_lang} from file extensions (found {max_count} files)")
    else:
        print(f"  ⚠️  Could not detect language, defaulting to Python")
        detected_lang = 'python'
    
    return detected_lang


def get_language_plugin(language: str) -> LanguagePlugin:
    """
    Get language plugin instance
    
    Args:
        language: Language name
        
    Returns:
        Language plugin instance
    """
    plugin_class = LANGUAGE_REGISTRY.get(language)
    
    if plugin_class:
        print(f"📦 Loading {language} plugin")
        return plugin_class()
    else:
        print(f"⚠️  No plugin for {language}, falling back to Python")
        return PythonPlugin()


def get_supported_languages() -> list:
    """Get list of supported languages"""
    return list(LANGUAGE_REGISTRY.keys())


__all__ = [
    'detect_language',
    'get_language_plugin',
    'get_supported_languages',
    'LanguagePlugin',
    'PythonPlugin',
    'JavaScriptPlugin',
]
