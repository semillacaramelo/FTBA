#!/usr/bin/env python3
"""
Test runner for FTBA application.
Discovers and runs all tests.
"""

import os
import sys
import unittest
import logging
from typing import List, Optional

# Configure logging to avoid test logs cluttering output
logging.basicConfig(level=logging.CRITICAL)

def run_tests(pattern: Optional[str] = None) -> bool:
    """
    Run the test suite.
    
    Args:
        pattern: Optional pattern to filter tests
        
    Returns:
        True if all tests passed, False otherwise
    """
    # Add the current directory to the Python path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    # Discover and run tests
    loader = unittest.TestLoader()
    
    if pattern:
        suite = loader.discover('tests', pattern=pattern)
    else:
        suite = loader.discover('tests')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return True if successful, False otherwise
    return result.wasSuccessful()


def list_tests() -> List[str]:
    """
    List all available tests without running them.
    
    Returns:
        List of test case names
    """
    loader = unittest.TestLoader()
    suite = loader.discover('tests')
    
    test_cases = []
    
    def extract_test_cases(suite_or_case):
        """Extract test cases from a test suite recursively"""
        if hasattr(suite_or_case, '_tests'):
            for test in suite_or_case._tests:
                extract_test_cases(test)
        else:
            test_cases.append(suite_or_case.id())
    
    extract_test_cases(suite)
    return sorted(test_cases)


if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run FTBA tests')
    parser.add_argument('--pattern', '-p', help='Pattern to filter tests')
    parser.add_argument('--list', '-l', action='store_true', help='List available tests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    if args.list:
        # List available tests
        tests = list_tests()
        print(f"Available tests ({len(tests)}):")
        for test in tests:
            print(f"  {test}")
    else:
        # Run tests
        pattern_msg = f" (pattern: {args.pattern})" if args.pattern else ""
        print(f"Running FTBA tests{pattern_msg}...")
        
        success = run_tests(args.pattern)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
