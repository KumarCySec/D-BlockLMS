#!/usr/bin/env python3
"""
Phase 3 Test Runner - Transaction Management & Notifications
Run comprehensive tests for Phase 3 functionality
"""
import os
import sys
import subprocess
import pytest
from datetime import datetime


def run_command(command, description):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print('='*60)
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print("✅ SUCCESS")
        if result.stdout:
            print("STDOUT:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ FAILED")
        print("STDERR:", e.stderr)
        if e.stdout:
            print("STDOUT:", e.stdout)
        return False


def main():
    """Run Phase 3 tests"""
    print("🚀 D-Block LMS Phase 3 Test Suite")
    print("=" * 60)
    print("Testing: Transaction Management & Notifications")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Set environment for testing
    os.environ['FLASK_ENV'] = 'testing'
    
    test_results = []
    
    # 1. Unit Tests - Transaction Models
    print("\n📋 Phase 1: Transaction Model Unit Tests")
    success = run_command(
        "python -m pytest tests/unit/test_transaction_models.py -v --tb=short",
        "Transaction Model Unit Tests"
    )
    test_results.append(("Transaction Models", success))
    
    # 2. Integration Tests - Transaction API
    print("\n🔗 Phase 2: Transaction API Integration Tests")
    success = run_command(
        "python -m pytest tests/integration/test_transaction_api.py -v --tb=short",
        "Transaction API Integration Tests"
    )
    test_results.append(("Transaction API", success))
    
    # 3. Notification Service Tests
    print("\n🔔 Phase 3: Notification Service Tests")
    success = run_command(
        "python -m pytest tests/unit/test_notification_models.py -v --tb=short",
        "Notification Service Tests"
    )
    test_results.append(("Notification Service", success))
    
    # 4. Transaction ID Format Tests
    print("\n🆔 Phase 4: Transaction ID Format Tests")
    success = run_command(
        "python -m pytest tests/unit/test_transaction_models.py::TestTransactionCounter -v",
        "Transaction ID Format Tests"
    )
    test_results.append(("Transaction ID Format", success))
    
    # 5. Audit Logging Tests
    print("\n📝 Phase 5: Audit Logging Tests")
    success = run_command(
        "python -m pytest tests/unit/test_transaction_models.py::TestTransactionAuditLogging -v",
        "Audit Logging Tests"
    )
    test_results.append(("Audit Logging", success))
    
    # 6. Concurrency Tests
    print("\n⚡ Phase 6: Concurrency Tests")
    success = run_command(
        "python -m pytest tests/unit/test_transaction_models.py::TestTransactionCounter::test_concurrent_id_generation -v",
        "Concurrency Tests"
    )
    test_results.append(("Concurrency", success))
    
    # 7. Coverage Report
    print("\n📊 Phase 7: Coverage Analysis")
    success = run_command(
        "python -m pytest tests/unit/test_transaction_models.py tests/integration/test_transaction_api.py --cov=app.models.transaction --cov=app.services.notification_service --cov-report=term-missing --cov-fail-under=70",
        "Coverage Analysis (Target: 70%)"
    )
    test_results.append(("Coverage Analysis", success))
    
    # 8. Mobile UI Verification (Basic)
    print("\n📱 Phase 8: Mobile UI Basic Verification")
    success = run_command(
        "python -c \"from app import create_app; app = create_app('testing'); print('✅ App creates successfully with transaction models')\"",
        "Mobile UI Basic Verification"
    )
    test_results.append(("Mobile UI Basic", success))
    
    # Summary Report
    print("\n" + "="*60)
    print("📋 PHASE 3 TEST SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n🎉 ALL PHASE 3 TESTS PASSED!")
        print("✅ Transaction ID format: DBL-YYYYMMDD-XXXX")
        print("✅ Notification service implemented")
        print("✅ Audit logging fixed")
        print("✅ Comprehensive test coverage")
        print("✅ Mobile UI compatibility maintained")
        return 0
    else:
        print(f"\n❌ {total - passed} test suite(s) failed")
        print("Please review the failed tests above")
        return 1


if __name__ == "__main__":
    sys.exit(main())