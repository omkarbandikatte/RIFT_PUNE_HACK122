#!/usr/bin/env python3
"""
Node.js Agent Entrypoint for Docker Container
Installs dependencies and runs tests with enhanced output
"""
import sys
import subprocess
import json
import os
import time


def install_dependencies():
    """Install npm dependencies"""
    if os.path.exists('package.json'):
        print("📦 Installing npm dependencies...")
        start = time.time()
        
        # Use npm ci if package-lock.json exists, otherwise npm install
        if os.path.exists('package-lock.json'):
            cmd = ['npm', 'ci', '--prefer-offline', '--no-audit']
            print("  Using npm ci (lockfile found)")
        elif os.path.exists('yarn.lock'):
            cmd = ['yarn', 'install', '--frozen-lockfile', '--prefer-offline']
            print("  Using yarn (yarn.lock found)")
        else:
            cmd = ['npm', 'install', '--prefer-offline', '--no-audit']
            print("  Using npm install")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=300  # 5 minute timeout
        )
        
        elapsed = time.time() - start
        
        if result.returncode == 0:
            print(f"✅ Dependencies installed in {elapsed:.1f}s")
            return True
        else:
            print(f"⚠️ Dependency installation had warnings:")
            print(result.stderr[:500])
            return True  # Continue anyway, tests might still work
    else:
        print("⚠️ No package.json found, skipping dependency installation")
        return False


def run_tests():
    """Run npm test (or lint/build as fallback)"""
    print("🧪 Running tests...")
    start = time.time()
    
    # Check package.json for available scripts
    test_cmd = ['npm', 'test', '--', '--ci', '--colors', '--passWithNoTests']
    
    if os.path.exists('package.json'):
        try:
            with open('package.json', 'r') as f:
                package_data = json.load(f)
            
            scripts = package_data.get('scripts', {})
            
            #Check if test script exists and is not a placeholder
            if 'test' not in scripts:
                print("⚠️  No test script found in package.json")
                
                # Try lint as fallback - use npx to ensure binary is found
                if 'lint' in scripts:
                    print("✓ Using lint script instead")
                    # Extract the actual command (e.g., "eslint .") and prepend npx
                    lint_cmd = scripts['lint']
                    test_cmd = ['npx', '--no-install'] + lint_cmd.split()
                elif 'build' in scripts:
                    print("✓ Using build script instead")
                    test_cmd = ['npm', 'run', 'build']
                else:
                    print("⚠️  No test/lint/build scripts available")
            else:
                test_script = scripts['test']
                # Check if it's a placeholder
                if 'no test' in test_script.lower() or ('echo' in test_script.lower() and 'error' in test_script.lower()):
                    print(f"⚠️  Test script is placeholder: {test_script}")
                    
                    # Try lint as fallback - use npx
                    if 'lint' in scripts:
                        print("✓ Using lint script instead")
                        lint_cmd = scripts['lint']
                        test_cmd = ['npx', '--no-install'] + lint_cmd.split()
                    elif 'build' in scripts:
                        print("✓ Using build script instead")
                        test_cmd = ['npm', 'run', 'build']
        
        except Exception as e:
            print(f"⚠️  Error reading package.json: {e}")
    
    print(f"Running: {' '.join(test_cmd)}")
    
    # Convert to string for shell execution
    cmd_string = ' '.join(test_cmd)
    
    result = subprocess.run(
        cmd_string,
        capture_output=True,
        encoding='utf-8',
        errors='replace',
        timeout=120,  # 2 minute timeout
        shell=True
    )
    
    elapsed = time.time() - start
    
    if result.returncode == 0:
        print(f"✅ All tests passed in {elapsed:.1f}s")
    else:
        print(f"❌ Tests failed (exit code {result.returncode}) after {elapsed:.1f}s")
    
    return result


def main():
    """Main entrypoint"""
    start_time = time.time()
    
    try:
        # Install dependencies
        deps_ok = install_dependencies()
        
        if not deps_ok:
            # No package.json, can't proceed
            output = {
                'stdout': '',
                'stderr': 'No package.json found',
                'returncode': 1,
                'success': False,
                'elapsed': 0
            }
        else:
            # Run tests
            test_result = run_tests()
            
            # Format output
            output = {
                'stdout': test_result.stdout,
                'stderr': test_result.stderr,
                'returncode': test_result.returncode,
                'success': test_result.returncode == 0,
                'elapsed': time.time() - start_time
            }
        
        # Print JSON output between markers for parsing
        print("\n=== AGENT OUTPUT ===")
        print(json.dumps(output, indent=2))
        print("=== END OUTPUT ===")
        
        return output['returncode']
        
    except subprocess.TimeoutExpired as e:
        print(f"\n❌ Command timed out: {e}")
        output = {
            'stdout': '',
            'stderr': f'Command timed out: {e}',
            'returncode': 124,
            'success': False,
            'elapsed': time.time() - start_time
        }
        
        print("\n=== AGENT OUTPUT ===")
        print(json.dumps(output, indent=2))
        print("=== END OUTPUT ===")
        
        return 124
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        output = {
            'stdout': '',
            'stderr': str(e),
            'returncode': 1,
            'success': False,
            'elapsed': time.time() - start_time
        }
        
        print("\n=== AGENT OUTPUT ===")
        print(json.dumps(output, indent=2))
        print("=== END OUTPUT ===")
        
        return 1


if __name__ == '__main__':
    exit(main())
