#!/usr/bin/env python3
"""
Simple Phase 2 Verification Test
"""
import os
import sys
import subprocess

def run_test(command, description):
    """Run a single test command"""
    print(f"\n{'='*50}")
    print(f"Testing: {description}")
    print(f"Command: {command}")
    print('='*50)
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        print(f"Exit Code: {result.returncode}")
        
        if result.stdout:
            print("Output:")
            print(result.stdout)
        
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("Phase 2 Simple Verification Test")
    print("=" * 50)
    
    # Check basic structure
    if not os.path.exists('app'):
        print("Error: app directory not found")
        return False
    
    if not os.path.exists('requirements.txt'):
        print("Error: requirements.txt not found")
        return False
    
    print("✅ Directory structure OK")
    
    # Test 1: Check if we can import the app
    success1 = run_test(
        "python -c 'import sys; sys.path.insert(0, \".\"); from app import create_app; print(\"App import successful\")'",
        "App Import Test"
    )
    
    # Test 2: Check if we can run a simple unit test
    success2 = run_test(
        "python -m pytest tests/unit/test_inventory_models.py::TestDonorModel::test_create_donor -v",
        "Simple Unit Test"
    )
    
    # Test 3: Check cache utilities
    success3 = run_test(
        "python -c 'import sys; sys.path.insert(0, \".\"); from app.utils.cache import CacheService; print(\"Cache service imported\")'",
        "Cache Service Import"
    )
    
    # Test 4: Check search utilities
    success4 = run_test(
        "python -c 'import sys; sys.path.insert(0, \".\"); from app.utils.search import SearchService; print(\"Search service imported\")'",
        "Search Service Import"
    )
    
    # Summary
    tests = [
        ("App Import", success1),
        ("Unit Test", success2),
        ("Cache Service", success3),
        ("Search Service", success4)
    ]
    
    print(f"\n{'='*50}")
    print("SUMMARY")
    print('='*50)
    
    passed = 0
    for name, success in tests:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All basic tests passed!")
        return True
    else:
        print("⚠️ Some tests failed - check the output above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)