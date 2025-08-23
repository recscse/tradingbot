#!/usr/bin/env python3
"""
Test Runner for Trading Application

Provides easy commands to run different types of tests with appropriate configurations.
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path

def run_command(cmd, description=""):
    """Run a command and handle output"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run tests for trading application")
    parser.add_argument("test_type", choices=[
        "all", "unit", "integration", "performance", "api", "fast", "slow",
        "breakout", "websocket", "accuracy", "e2e", "coverage", "install"
    ], help="Type of tests to run")
    
    parser.add_argument("--parallel", "-p", action="store_true", 
                       help="Run tests in parallel")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--coverage", "-c", action="store_true",
                       help="Generate coverage report")
    parser.add_argument("--html", action="store_true",
                       help="Generate HTML coverage report")
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Test type selection
    if args.test_type == "all":
        # Run all tests
        pass
    elif args.test_type == "unit":
        cmd.extend(["tests/unit/", "-m", "unit"])
    elif args.test_type == "integration":
        cmd.extend(["tests/integration/", "-m", "integration"])
    elif args.test_type == "performance":
        cmd.extend(["tests/performance/", "-m", "performance"])
    elif args.test_type == "api":
        cmd.extend(["tests/api/", "-m", "api"])
    elif args.test_type == "fast":
        cmd.extend(["-m", "fast"])
    elif args.test_type == "slow":
        cmd.extend(["-m", "slow"])
    elif args.test_type == "breakout":
        cmd.extend(["-m", "breakout"])
    elif args.test_type == "websocket":
        cmd.extend(["-m", "websocket"])
    elif args.test_type == "coverage":
        cmd.extend(["--cov=services", "--cov=router", "--cov-report=html", "--cov-report=term"])
    
    elif args.test_type == "accuracy":
        cmd.extend(["tests/accuracy/", "-m", "accuracy"])
    elif args.test_type == "e2e":
        cmd.extend(["tests/e2e/", "-m", "e2e"])
    elif args.test_type == "install":
        # Install test dependencies
        install_cmd = ["pip", "install", "-r", "requirements.txt"]
        return run_command(install_cmd, "Installing test dependencies")
    
    # Add options
    if args.parallel:
        cmd.extend(["-n", "auto"])
    
    if args.verbose:
        cmd.append("-v")
    
    if args.coverage or args.test_type == "coverage":
        cmd.extend(["--cov=services", "--cov=router", "--cov-report=term-missing"])
        if args.html:
            cmd.append("--cov-report=html")
    
    # Run the tests
    success = run_command(cmd, f"Running {args.test_type} tests")
    
    if success:
        print(f"\n[SUCCESS] {args.test_type.title()} tests completed successfully!")
        if args.coverage or args.test_type == "coverage":
            print("\nCoverage report generated!")
            if args.html or args.test_type == "coverage":
                print("HTML coverage report: htmlcov/index.html")
    else:
        print(f"\n[FAILED] {args.test_type.title()} tests failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    # Ensure we're in the right directory
    os.chdir(Path(__file__).parent)
    
    # Print usage information
    print("Trading Application Test Runner")
    print("=" * 50)
    
    # Examples
    examples = """
Examples:
  python run_tests.py all                  # Run all tests
  python run_tests.py unit -v              # Run unit tests with verbose output
  python run_tests.py performance          # Run performance tests
  python run_tests.py breakout             # Run breakout-related tests
  python run_tests.py fast -p              # Run fast tests in parallel
  python run_tests.py coverage --html      # Generate coverage report with HTML
  python run_tests.py install              # Install test dependencies
    """
    
    if len(sys.argv) == 1:
        print(examples)
        sys.exit(1)
    
    sys.exit(main())