#!/usr/bin/env python
"""
Check dependencies script for FTBA system.
This script verifies that all required dependencies are installed.
"""

import importlib.util
import sys
import subprocess
import os
import pkg_resources

def check_dependency(module_name, package_name=None):
    """
    Check if a Python module is available and provide installation instructions if not.
    
    Args:
        module_name: The name of the module to import
        package_name: The package name to install (if different from module_name)
        
    Returns:
        bool: True if dependency is available, False otherwise
    """
    package_name = package_name or module_name
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            print(f"Error: {module_name} not found. Install with: pip install {package_name}")
            return False
        return True
    except ImportError:
        print(f"Error: {module_name} not found. Install with: pip install {package_name}")
        return False

def check_deriv_api():
    """
    Check specifically for the python-deriv-api package.
    
    Returns:
        bool: True if dependency is available, False otherwise
    """
    try:
        spec = importlib.util.find_spec("deriv_api")
        if spec is None:
            print("\nError: deriv_api module not found.")
            print("To install python-deriv-api:")
            print("  pip install git+https://github.com/deriv-com/python-deriv-api.git#egg=python-deriv-api")
            print("\nAlternatively, run: pip install -e .")
            print("The setup.py file has been updated with the correct dependency.")
            return False
        return True
    except ImportError:
        print("\nError: deriv_api module not found.")
        print("To install python-deriv-api:")
        print("  pip install git+https://github.com/deriv-com/python-deriv-api.git#egg=python-deriv-api")
        print("\nAlternatively, run: pip install -e .")
        print("The setup.py file has been updated with the correct dependency.")
        return False

def main():
    """
    Check all critical dependencies for the FTBA system.
    """
    print("Checking dependencies for FTBA system...")
    
    # Check core dependencies
    dependencies = [
        ("numpy", "numpy>=1.24.3"),
        ("pandas", "pandas>=2.0.2"),
        ("matplotlib", "matplotlib>=3.7.1"),
        ("sklearn", "scikit-learn>=1.3.0"),
        ("statsmodels", "statsmodels>=0.14.0"),
        ("aiohttp", "aiohttp>=3.8.5"),
        ("websockets", "websockets>=11.0.3"),
        ("pymongo", "pymongo>=4.4.1"),
        ("pydantic", "pydantic>=2.1.1"),
    ]

    all_found = True
    for module, package in dependencies:
        if not check_dependency(module, package):
            all_found = False
    
    # Special check for Deriv API
    if not check_deriv_api():
        all_found = False
    
    if all_found:
        print("\nAll dependencies are installed!")
        print("You can run the FTBA system with: python main.py")
        return 0
    else:
        print("\nSome dependencies are missing. Please install them before running the system.")
        print("You can install all dependencies with: pip install -e .")
        return 1

if __name__ == "__main__":
    sys.exit(main())