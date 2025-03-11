import os
import sys
import importlib
import subprocess

def run_static_analysis():
    """Run basic static analysis on Python files"""
    print("Running static analysis...")
    import_errors = []
    syntax_errors = []

    # Find all Python files
    python_files = []
    for root, _, files in os.walk('.'):
        if 'venv' in root or '.git' in root or 'python-deriv-api' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    # Check each file for syntax and import errors
    for file_path in python_files:
        print(f"Checking {file_path}")
        try:
            with open(file_path, 'r') as f:
                source = f.read()
            # Check for syntax errors
            compile(source, file_path, 'exec')

            # Check for import errors (by attempting to import the module)
            module_path = file_path.replace('/', '.').replace('\\', '.').replace('.py', '')
            if module_path.startswith('.'):
                module_path = module_path[1:]
            try:
                # Skip actual import for test files to avoid running them
                if not file_path.startswith('./tests/'):
                    __import__(module_path)
            except ImportError as e:
                import_errors.append((file_path, str(e)))
        except SyntaxError as e:
            syntax_errors.append((file_path, str(e)))

    # Print results
    if syntax_errors:
        print("\nSyntax Errors:")
        for file_path, error in syntax_errors:
            print(f"  {file_path}: {error}")

    if import_errors:
        print("\nImport Errors:")
        for file_path, error in import_errors:
            print(f"  {file_path}: {error}")

    return not (syntax_errors or import_errors)

def run_tests():
    """Run unit tests"""
    print("\nRunning unit tests...")
    result = subprocess.run(['pytest', '-v'], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    return result.returncode == 0

if __name__ == "__main__":
    print("=== Running Code Quality Checks ===")
    static_check_passed = run_static_analysis()
    test_passed = run_tests()

    if static_check_passed and test_passed:
        print("\n✅ All checks passed!")
        sys.exit(0)
    else:
        print("\n❌ Some checks failed!")
        sys.exit(1)