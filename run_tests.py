"""
Test runner script for the API
"""

import subprocess
import sys
import os

def run_tests():
    """Run all tests with pytest"""
    
    # Set environment variables for testing
    os.environ["TESTING"] = "1"
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

def run_specific_test(test_path):
    """Run a specific test file or test function"""
    
    os.environ["TESTING"] = "1"
    
    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running test: {e}")
        return 1

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_path = sys.argv[1]
        exit_code = run_specific_test(test_path)
    else:
        # Run all tests
        exit_code = run_tests()
    
    sys.exit(exit_code)
