#!/usr/bin/env python3
"""
Validation script to verify test environment is properly configured
"""

import sys
import importlib.util

def check_module(module_name):
    """Check if a module can be imported"""
    spec = importlib.util.find_spec(module_name)
    if spec is not None:
        print(f"✅ {module_name}: Available")
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, '__version__'):
                print(f"   Version: {module.__version__}")
        except Exception as e:
            print(f"   Warning: Could not import (spec exists): {e}")
        return True
    else:
        print(f"❌ {module_name}: Not found")
        return False

def validate_test_file():
    """Validate the integration test file syntax"""
    import ast
    test_file = "/Users/andrewmorton/Documents/GitHub/kimi/tests/test_integration.py"
    try:
        with open(test_file, 'r') as f:
            ast.parse(f.read())
        print(f"✅ test_integration.py: Syntax valid")
        return True
    except SyntaxError as e:
        print(f"❌ test_integration.py: Syntax error - {e}")
        return False

def main():
    print("="*70)
    print("Kimi Integration Test Environment Validation")
    print("="*70)

    print("\n1. Python Environment:")
    print(f"   Python: {sys.version}")
    print(f"   Executable: {sys.executable}")

    print("\n2. Required Modules:")
    pytest_ok = check_module("pytest")
    pytest_asyncio_ok = check_module("pytest_asyncio")
    httpx_ok = check_module("httpx")

    print("\n3. Test File Validation:")
    test_file_ok = validate_test_file()

    print("\n4. Standard Library:")
    check_module("asyncio")
    check_module("json")
    check_module("tempfile")

    print("\n" + "="*70)
    print("Summary:")
    print("="*70)

    all_ok = pytest_ok and pytest_asyncio_ok and httpx_ok and test_file_ok

    if all_ok:
        print("✅ ALL CHECKS PASSED - Ready to run tests")
        print("\nTo run tests:")
        print("  pytest tests/test_integration.py -v")
    else:
        print("⚠️  SOME CHECKS FAILED")
        if not pytest_ok or not pytest_asyncio_ok:
            print("\nTo install missing dependencies:")
            print("  pip install pytest pytest-asyncio")
        if not httpx_ok:
            print("  pip install httpx")

    print("="*70)

    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
