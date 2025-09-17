#!/usr/bin/env python3
"""Debug script to check payment data and check payment detection"""

from storage import PaymentStorage
from data_import import PaymentData
from datetime import datetime

def debug_payments():
    """Debug payment data and check detection"""
    print("🔍 Debugging Payment Data...")
    
    # Load payments
    storage = PaymentStorage()
    payments = storage.load_payments()
    
    print(f"📊 Total payments loaded: {len(payments)}")
    
    if not payments:
        print("❌ No payments found!")
        return
    
    # Check sample payment
    sample = payments[0]
    print(f"\n📋 Sample payment fields:")
    for key, value in sample.__dict__.items():
        print(f"  {key}: {value}")
    
    # Check for check payments
    check_payments = []
    tahsilat_sekli_payments = []
    
    for payment in payments:
        # Check if it's a check payment
        if getattr(payment, 'is_check_payment', False):
            check_payments.append(payment)
        
        # Check tahsilat sekli
        tahsilat_sekli = getattr(payment, 'tahsilat_sekli', '')
        if tahsilat_sekli and tahsilat_sekli.upper() in ['ÇEK', 'CEK', 'CHECK']:
            tahsilat_sekli_payments.append(payment)
    
    print(f"\n✅ Check payments detected: {len(check_payments)}")
    print(f"✅ Tahsilat Şekli = 'Çek' payments: {len(tahsilat_sekli_payments)}")
    
    # Show sample check payments
    if check_payments:
        print(f"\n📝 Sample check payment:")
        sample_check = check_payments[0]
        print(f"  Customer: {sample_check.customer_name}")
        print(f"  Amount: {sample_check.amount}")
        print(f"  Tahsilat Şekli: {getattr(sample_check, 'tahsilat_sekli', 'N/A')}")
        print(f"  Check Amount: {getattr(sample_check, 'cek_tutari', 0)}")
        print(f"  Is Check Payment: {getattr(sample_check, 'is_check_payment', False)}")
    
    # Check payment channels for check detection
    print(f"\n🔍 Payment channels analysis:")
    channels = {}
    for payment in payments[:10]:  # Check first 10
        channel = getattr(payment, 'payment_channel', 'Unknown')
        channels[channel] = channels.get(channel, 0) + 1
        print(f"  {payment.customer_name}: {channel}")
    
    print(f"\n📈 Channel distribution:")
    for channel, count in channels.items():
        print(f"  {channel}: {count}")

if __name__ == "__main__":
    debug_payments()
