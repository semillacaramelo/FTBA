
import os
import sys
import unittest
import pytest

def run_unit_tests():
    """Run unittest-based tests"""
    print("Running unit tests...")
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    return result.wasSuccessful()

def run_pytest_tests():
    """Run pytest-based tests"""
    print("Running pytest tests...")
    result = pytest.main(['tests', '-v'])
    return result == 0

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

if __name__ == "__main__":
    print("Running test suite for Multi-Agent Forex Trading System")
    
    # Run all tests
    static_success = run_static_analysis()
    unittest_success = run_unit_tests()
    pytest_success = run_pytest_tests()
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Static Analysis: {'PASSED' if static_success else 'FAILED'}")
    print(f"Unit Tests: {'PASSED' if unittest_success else 'FAILED'}")
    print(f"Pytest Tests: {'PASSED' if pytest_success else 'FAILED'}")
    
    # Exit with appropriate status code
    success = static_success and unittest_success and pytest_success
    sys.exit(0 if success else 1)
