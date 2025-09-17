#!/usr/bin/env python3
"""
Setup script to automatically import sample data
This will help resolve the "no data found" issue
"""

import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_import import import_payments, validate_payment_data
from storage import PaymentStorage

def setup_sample_data():
    """Import sample data and set up the application"""
    print("🚀 Setting up Tahsilat with sample data...")
    print("=" * 50)
    
    try:
        # Import sample data
        print("📥 Importing sample_data.csv...")
        payments = import_payments("sample_data.csv")
        print(f"✅ Imported {len(payments)} payments")
        
        # Validate data
        print("🔍 Validating data...")
        valid_payments, warnings = validate_payment_data(payments)
        print(f"✅ Valid payments: {len(valid_payments)}")
        
        if warnings:
            print(f"⚠️ Warnings: {len(warnings)}")
        
        # Store data
        print("💾 Storing data...")
        storage = PaymentStorage()
        storage.add_payments(valid_payments)
        print(f"✅ Stored {len(valid_payments)} payments in storage")
        
        # Show statistics
        stats = storage.get_statistics()
        print(f"\n📊 Data Statistics:")
        print(f"   Total payments: {stats['total_payments']}")
        print(f"   Total TL amount: {stats['total_amount_tl']:,.2f}")
        print(f"   Total USD amount: {stats['total_amount_usd']:,.2f}")
        print(f"   Projects: {stats['projects']}")
        print(f"   Customers: {stats['customers']}")
        print(f"   Payment channels: {stats['channels']}")
        
        if stats['date_range']:
            print(f"   Date range: {stats['date_range']['start']} to {stats['date_range']['end']}")
        
        print(f"\n🎉 Sample data setup complete!")
        print(f"📝 You can now generate reports in the application.")
        print(f"📅 Use date range: January 1-31, 2024 for best results")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = setup_sample_data()
    if success:
        print("\n✅ Setup completed successfully!")
        print("🚀 You can now run the application: python main.py")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
    
    sys.exit(0 if success else 1)
