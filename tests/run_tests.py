#!/usr/bin/env python3
"""
Test runner script for the MemeVerse application.
This script runs all tests and provides a summary of results.
"""

import subprocess
import sys
import os

def run_tests():
    """Run all tests with pytest."""
    print("Running MemeVerse tests...")
    print("=" * 50)
    
    # Run pytest with coverage and verbose output
    try:
        result = subprocess.run([
            'python', '-m', 'pytest', 
            'tests/', 
            '-v', 
            '-r', 's',
            '--tb=short',
            '--disable-warnings',
            '--no-fold-skipped'
        ], check=True, capture_output=True, text=True)
        
        print("Tests completed successfully!")
        print(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print("Tests failed!")
        print(e.stdout)
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("Error: pytest not found. Please install test dependencies:")
        print("pip install -r tests/requirements.txt")
        return False

def run_tests_with_coverage():
    """Run tests with coverage report."""
    print("Running tests with coverage...")
    print("=" * 50)
    
    try:
        # Check if pytest-cov is installed
        subprocess.run(['python', '-m', 'pytest', '--version'], 
                      check=True, capture_output=True)
        
        result = subprocess.run([
            'python', '-m', 'pytest',
            'tests/',
            '--cov=.',
            '--cov-report=term-missing',
            '--cov-report=html:htmlcov',
            '-v',
            '-r', 's',
            '--no-fold-skipped'
        ], check=True, capture_output=True, text=True)
        
        print("Coverage report generated successfully!")
        print("Open htmlcov/index.html to view detailed coverage report.")
        print(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print("Coverage tests failed!")
        print(e.stdout)
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("Error: pytest not found. Please install test dependencies:")
        print("pip install -r tests/requirements.txt")
        return False

def main():
    """Main function to run tests."""
    if len(sys.argv) > 1 and sys.argv[1] == '--coverage':
        success = run_tests_with_coverage()
    else:
        success = run_tests()
    
    if success:
        print("\n" + "=" * 50)
        print("All tests passed! ✅")
        sys.exit(0)
    else:
        print("\n" + "=" * 50)
        print("Some tests failed! ❌")
        sys.exit(1)

if __name__ == '__main__':
    main()
