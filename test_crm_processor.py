#!/usr/bin/env python3
"""
Test script for CRM Processor
Demonstrates the flexible column detection and data processing capabilities
"""

import pandas as pd
import os
from datetime import datetime, timedelta
from crm_processor import CRMProcessor

def create_test_data():
    """Create various test CSV files with different column arrangements"""
    
    # Test Case 1: Standard format
    test1_data = {
        'Tarih': ['2024-01-15', '2024-01-16', '2024-01-17'],
        'Müşteri Adı Soyadı': ['Ahmet Yılmaz', 'Fatma Demir', 'Mehmet Kaya'],
        'Proje Adı': ['MSM', 'MKM', 'MSM'],
        'Ödenen Tutar': [15000.50, 25000.00, 18000.75],
        'Ödenen Döviz': ['TL', 'TL', 'USD'],
        'Ödeme Kanalı': ['Yapı Kredi TL', 'Çarşı USD', 'Kuyumcukent USD']
    }
    
    df1 = pd.DataFrame(test1_data)
    df1.to_csv('test_standard.csv', index=False, encoding='utf-8')
    print("✅ Created test_standard.csv")
    
    # Test Case 2: Different column names and order
    test2_data = {
        'Payment Date': ['2024-01-18', '2024-01-19', '2024-01-20'],
        'Customer Name': ['Ali Veli', 'Zeynep Arslan', 'Mustafa Özkan'],
        'Project Code': ['Model Sanayi Merkezi', 'Model Kuyum Merkezi', 'Model Sanayi Merkezi'],
        'Amount (TL)': [12000.00, 30000.50, 22000.25],
        'Currency Type': ['Turkish Lira', 'Turkish Lira', 'US Dollar'],
        'Payment Method': ['Garanti TL', 'Ofis Kasa', 'İş Bankası TL']
    }
    
    df2 = pd.DataFrame(test2_data)
    df2.to_csv('test_alternative.csv', index=False, encoding='utf-8')
    print("✅ Created test_alternative.csv")
    
    # Test Case 3: Mixed case and whitespace
    test3_data = {
        '  tarih  ': ['2024-01-21', '2024-01-22', '2024-01-23'],
        'MÜŞTERİ ADI SOYADI': ['Elif Yıldız', 'Hasan Kılıç', 'Ayşe Çelik'],
        'proje adı': ['MSM', 'MKM', 'MSM'],
        'Ödenen Tutar(Σ:11,059,172.00)': [35000.00, 28000.50, 19000.75],
        'ödEnEn dÖvİz': ['TL', 'USD', 'TL'],
        'ÖDEME KANALI': ['Yapı Kredi USD', 'Çarşı USD', 'Kuyumcukent USD']
    }
    
    df3 = pd.DataFrame(test3_data)
    df3.to_csv('test_mixed_case.csv', index=False, encoding='utf-8')
    print("✅ Created test_mixed_case.csv")
    
    # Test Case 4: Missing required column (should fail)
    test4_data = {
        'Date': ['2024-01-24', '2024-01-25'],
        'Customer': ['Test User 1', 'Test User 2'],
        'Amount': [10000.00, 15000.00],
        'Currency': ['TL', 'USD']
        # Missing Project and Payment Channel
    }
    
    df4 = pd.DataFrame(test4_data)
    df4.to_csv('test_missing_columns.csv', index=False, encoding='utf-8')
    print("✅ Created test_missing_columns.csv")
    
    # Test Case 5: Complex data with various formats
    test5_data = {
        'İşlem Tarihi': ['15.01.2024', '16/01/2024', '2024-01-17'],
        'Müşteri Bilgisi': ['Musa Özdoğan', 'Fatma Demir', 'Mehmet Kaya'],
        'Proje Kodu': ['Model Sanayi Merkezi', 'Model Kuyum Merkezi', 'Model Sanayi Merkezi'],
        'Tutar (TL)': ['25,000.50', '30,000.00', '18,500.75'],
        'Para Birimi': ['Türk Lirası', 'Türk Lirası', 'Dolar'],
        'Hesap Adı': ['Yapı Kredi Bankası TL', 'Çarşı Döviz Hesabı', 'Kuyumcukent USD Hesabı']
    }
    
    df5 = pd.DataFrame(test5_data)
    df5.to_csv('test_complex.csv', index=False, encoding='utf-8')
    print("✅ Created test_complex.csv")

def test_processor():
    """Test the CRM processor with various files"""
    processor = CRMProcessor()
    
    test_files = [
        'test_standard.csv',
        'test_alternative.csv', 
        'test_mixed_case.csv',
        'test_missing_columns.csv',
        'test_complex.csv'
    ]
    
    print("\n🧪 Testing CRM Processor")
    print("=" * 50)
    
    for test_file in test_files:
        print(f"\n📁 Processing: {test_file}")
        print("-" * 30)
        
        success, processed_df, errors = processor.process_file(test_file)
        
        if success:
            print(f"✅ Successfully processed {len(processed_df)} records")
            
            # Show sample of processed data
            if not processed_df.empty:
                print("\n📊 Sample processed data:")
                print(processed_df[['date', 'customer_name', 'project_name', 'amount', 'currency', 'payment_channel']].head())
                
                # Generate summary
                summary = processor.generate_summary(processed_df)
                print(f"\n📈 Summary:")
                print(f"   Total Amount: {summary['total_amount']:,.2f}")
                print(f"   Currencies: {summary['currencies']}")
                print(f"   Payment Channels: {summary['payment_channels']}")
                print(f"   Projects: {summary['projects']}")
        else:
            print(f"❌ Processing failed:")
            for error in errors:
                print(f"   {error}")
    
    print(f"\n🎉 Testing completed!")

def cleanup_test_files():
    """Clean up test files"""
    test_files = [
        'test_standard.csv',
        'test_alternative.csv',
        'test_mixed_case.csv', 
        'test_missing_columns.csv',
        'test_complex.csv',
        'processed_crm_data.csv'
    ]
    
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑️ Removed {file}")

def main():
    """Main test function"""
    print("🚀 CRM Processor Test Suite")
    print("=" * 50)
    
    # Create test data
    print("\n📝 Creating test data files...")
    create_test_data()
    
    # Test processor
    test_processor()
    
    # Cleanup
    print("\n🧹 Cleaning up test files...")
    cleanup_test_files()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()
