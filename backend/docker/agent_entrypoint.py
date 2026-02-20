#!/usr/bin/env python3
"""
Enhanced Agent Entrypoint for Docker Container
Runs tests in complete isolation with enhanced error detection
"""
import sys
import subprocess
import json
import os
import time


def install_dependencies():
    """Install project dependencies"""
    if os.path.exists('requirements.txt'):
        print("📦 Installing dependencies...")
        start = time.time()
        
        result = subprocess.run(
            ['pip', 'install', '--user', '--no-cache-dir', '-r', 'requirements.txt'],
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=300
        )
        
        elapsed = time.time() - start
        
        if result.returncode == 0:
            print(f"✅ Dependencies installed in {elapsed:.1f}s")
            return True
        else:
            print(f"⚠️ Dependency installation had warnings: {result.stderr[:200]}")
            return True  # Continue anyway
    
    elif os.path.exists('package.json'):
        print("📦 Detected Node.js project (package.json)")
        # Could add npm support here
        return False
    
    else:
        print("⚠️ No requirements.txt found, skipping dependency installation")
        return True


def run_tests():
    """Run pytest with enhanced output"""
    print("🧪 Running tests...")
    start = time.time()
    
    result = subprocess.run(
        ['python', '-m', 'pytest', '--maxfail=10', '-v', '--tb=short', '--color=yes'],
        capture_output=True,
        encoding='utf-8',
        errors='replace',
        timeout=120
    )
    
    elapsed = time.time() - start
    
    if result.returncode == 0:
        print(f"✅ All tests passed in {elapsed:.1f}s")
    else:
        print(f"❌ Tests failed (exit code {result.returncode}) after {elapsed:.1f}s")
    
    return result


def main():
    """
    Main entrypoint for Docker agent
    Expected to run inside /workspace directory
    """
    print("🐳 Docker Agent Starting...")
    print(f"📂 Working directory: {os.getcwd()}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    
    try:
        # Step 1: Install dependencies
        if not install_dependencies():
            return {
                'success': False,
                'error': 'Unsupported project type',
                'stdout': '',
                'stderr': 'Only Python projects with requirements.txt are supported',
                'returncode': 1
            }
        
        # Step 2: Run tests
        result = run_tests()
        
        # Step 3: Return results as JSON
        output = {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
        
        # Print JSON to stdout for host to capture
        print("\n=== AGENT OUTPUT ===")
        print(json.dumps(output))
        print("=== END OUTPUT ===")
        
        return output
        
    except subprocess.TimeoutExpired:
        error = {
            'success': False,
            'error': 'Test execution timed out',
            'stdout': '',
            'stderr': 'Tests took longer than 120 seconds',
            'returncode': 124
        }
        print(json.dumps(error))
        return error
        
    except Exception as e:
        error = {
            'success': False,
            'error': str(e),
            'stdout': '',
            'stderr': str(e),
            'returncode': 1
        }
        print(json.dumps(error))
        return error


if __name__ == '__main__':
    result = main()
    sys.exit(0 if result.get('success', False) else 1)
