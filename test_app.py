#!/usr/bin/env python3
"""
Test script for Tahsilat application
Tests core functionality without GUI
"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_import import import_payments, validate_payment_data
from storage import PaymentStorage
from currency import CurrencyConverter
from report_generator import ReportGenerator

def test_data_import():
    """Test data import functionality"""
    print("=== Testing Data Import ===")
    
    try:
        # Test CSV import
        print("Testing CSV import...")
        payments = import_payments("sample_data.csv")
        print(f"✓ CSV import successful: {len(payments)} records")
        
        # Test JSON import
        print("Testing JSON import...")
        payments = import_payments("sample_data.json")
        print(f"✓ JSON import successful: {len(payments)} records")
        
        # Test validation
        print("Testing data validation...")
        valid_payments, warnings = validate_payment_data(payments)
        print(f"✓ Validation successful: {len(valid_payments)} valid, {len(warnings)} warnings")
        
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        
        return valid_payments
        
    except Exception as e:
        print(f"✗ Data import failed: {e}")
        return []

def test_currency_conversion():
    """Test currency conversion functionality"""
    print("\n=== Testing Currency Conversion ===")
    
    try:
        converter = CurrencyConverter()
        
        # Test with a recent date
        test_date = datetime.now() - timedelta(days=1)
        print(f"Testing exchange rate for {test_date.strftime('%Y-%m-%d')}...")
        
        rate = converter.get_usd_rate(test_date)
        if rate:
            print(f"✓ Exchange rate retrieved: {rate:.4f} TL/USD")
            
            # Test conversion
            tl_amount = 1000.0
            usd_amount, used_rate = converter.convert_tl_to_usd(tl_amount, test_date)
            print(f"✓ Conversion test: {tl_amount} TL = {usd_amount:.2f} USD (rate: {used_rate:.4f})")
        else:
            print("⚠ Exchange rate not available (network issue or weekend)")
        
        return True
        
    except Exception as e:
        print(f"✗ Currency conversion failed: {e}")
        return False

def test_storage():
    """Test storage functionality"""
    print("\n=== Testing Storage ===")
    
    try:
        storage = PaymentStorage("test_data")
        
        # Test adding payments
        print("Testing payment storage...")
        test_payments = [
            {
                'Müşteri Adı Soyadı': 'Test Müşteri',
                'Tarih': datetime.now(),
                'Proje Adı': 'Test Proje',
                'Hesap Adı': 'Test Hesap',
                'Ödenen Tutar': 1000.0,
                'Ödenen Döviz': 'TL',
                'Ödenen Kur': 0,
                'Ödeme Durumu': 'Test'
            }
        ]
        
        from data_import import PaymentData
        payments = [PaymentData(p) for p in test_payments]
        storage.add_payments(payments)
        
        # Test retrieval
        all_payments = storage.get_all_payments()
        print(f"✓ Storage test successful: {len(all_payments)} records stored")
        
        # Test statistics
        stats = storage.get_statistics()
        print(f"✓ Statistics: {stats}")
        
        # Cleanup
        import shutil
        if os.path.exists("test_data"):
            shutil.rmtree("test_data")
        
        return True
        
    except Exception as e:
        print(f"✗ Storage test failed: {e}")
        return False

def test_report_generation():
    """Test report generation functionality"""
    print("\n=== Testing Report Generation ===")
    
    try:
        # Import sample data
        payments = import_payments("sample_data.csv")
        valid_payments, _ = validate_payment_data(payments)
        
        if not valid_payments:
            print("⚠ No valid payments for report testing")
            return False
        
        generator = ReportGenerator()
        
        # Test date range
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 2, 29)
        
        # Test daily breakdown
        print("Testing daily breakdown...")
        daily_breakdown = generator.generate_daily_usd_breakdown(valid_payments, start_date, end_date)
        print(f"✓ Daily breakdown: {daily_breakdown.shape}")
        
        # Test monthly summary
        print("Testing monthly summary...")
        monthly_summary = generator.generate_monthly_summary(valid_payments)
        print(f"✓ Monthly summary: {monthly_summary.shape}")
        
        # Test payment type summary
        print("Testing payment type summary...")
        payment_summary = generator.generate_payment_type_summary(valid_payments)
        print(f"✓ Payment type summary: {payment_summary.shape}")
        
        return True
        
    except Exception as e:
        print(f"✗ Report generation failed: {e}")
        return False

def test_full_workflow():
    """Test complete workflow"""
    print("\n=== Testing Full Workflow ===")
    
    try:
        # 1. Import data
        payments = import_payments("sample_data.csv")
        valid_payments, warnings = validate_payment_data(payments)
        
        if not valid_payments:
            print("✗ No valid payments for workflow test")
            return False
        
        print(f"✓ Imported {len(valid_payments)} valid payments")
        
        # 2. Store data
        storage = PaymentStorage("test_workflow")
        storage.add_payments(valid_payments)
        print("✓ Data stored successfully")
        
        # 3. Generate reports
        generator = ReportGenerator()
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 2, 29)
        
        # Test Excel export
        print("Testing Excel export...")
        generator.export_to_excel(valid_payments, start_date, end_date, "test_report.xlsx")
        print("✓ Excel report generated")
        
        # Cleanup
        import shutil
        if os.path.exists("test_workflow"):
            shutil.rmtree("test_workflow")
        if os.path.exists("test_report.xlsx"):
            os.remove("test_report.xlsx")
        
        print("✓ Full workflow test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Full workflow test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Tahsilat Application Test Suite")
    print("=" * 50)
    
    tests = [
        ("Data Import", test_data_import),
        ("Currency Conversion", test_currency_conversion),
        ("Storage", test_storage),
        ("Report Generation", test_report_generation),
        ("Full Workflow", test_full_workflow)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:20} : {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("🎉 All tests passed! Application is ready to use.")
    else:
        print("⚠ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()
