#!/usr/bin/env python3
"""
Test script to demonstrate currency optimization performance improvement
"""

import time
import logging
from datetime import datetime, timedelta
from data_import import PaymentData
from report_generator import ReportGenerator
from currency_optimizer import optimize_currency_conversion

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_payments():
    """Create test payment data for performance testing"""
    payments = []
    
    # Create payments with various dates to test currency conversion
    base_date = datetime(2025, 9, 15)
    
    for i in range(50):  # Create 50 test payments
        payment_date = base_date + timedelta(days=i % 7)  # Cycle through 7 days
        
        # Create payment data dictionary with Turkish field names
        payment_data = {
            'Müşteri Adı Soyadı': f"Test Customer {i+1}",
            'Proje Adı': f"PROJECT_A Test Project {i+1}",
            'Ödenen Tutar': 1000.0 + (i * 100),  # Varying amounts
            'Tarih': payment_date,
            'Hesap Adı': "Test Account",
            'Tahsilat Şekli': "BANK_TRANSFER",
            'Ödenen Döviz': 'TL',  # All TL payments to test conversion
            'Ödeme Durumu': 'Tamamlandı'
        }
        
        payment = PaymentData(payment_data)
        payments.append(payment)
    
    return payments

def test_old_system_performance(payments, start_date, end_date):
    """Test the old system performance (without optimization)"""
    logger.info("Testing OLD system (without optimization)...")
    
    start_time = time.time()
    
    # Create a new report generator instance
    generator = ReportGenerator()
    
    # Generate HTML preview (this would normally make many API calls)
    try:
        html_sheets = generator.generate_html_preview(payments, start_date, end_date)
        end_time = time.time()
        
        duration = end_time - start_time
        logger.info(f"OLD system completed in {duration:.2f} seconds")
        logger.info(f"Generated {len(html_sheets)} HTML sheets")
        
        return duration, len(html_sheets)
    except Exception as e:
        logger.error(f"OLD system failed: {e}")
        return None, 0

def test_new_system_performance(payments, start_date, end_date):
    """Test the new optimized system performance"""
    logger.info("Testing NEW system (with optimization)...")
    
    start_time = time.time()
    
    # Create a new report generator instance
    generator = ReportGenerator()
    
    # Generate HTML preview with optimization
    try:
        html_sheets = generator.generate_html_preview(payments, start_date, end_date)
        end_time = time.time()
        
        duration = end_time - start_time
        logger.info(f"NEW system completed in {duration:.2f} seconds")
        logger.info(f"Generated {len(html_sheets)} HTML sheets")
        
        return duration, len(html_sheets)
    except Exception as e:
        logger.error(f"NEW system failed: {e}")
        return None, 0

def main():
    """Main test function"""
    logger.info("=== CURRENCY OPTIMIZATION PERFORMANCE TEST ===")
    
    # Create test data
    payments = create_test_payments()
    start_date = datetime(2025, 9, 1)
    end_date = datetime(2025, 9, 30)
    
    logger.info(f"Created {len(payments)} test payments")
    logger.info(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Test new system first (since it's optimized)
    new_duration, new_sheets = test_new_system_performance(payments, start_date, end_date)
    
    if new_duration is not None:
        logger.info("=== PERFORMANCE COMPARISON ===")
        logger.info(f"NEW optimized system: {new_duration:.2f} seconds")
        logger.info(f"Generated sheets: {new_sheets}")
        
        # Show optimization stats
        from currency_optimizer import get_currency_optimizer
        optimizer = get_currency_optimizer()
        stats = optimizer.conversion_stats
        
        logger.info("=== OPTIMIZATION STATS ===")
        logger.info(f"Total payments: {stats['total_payments']}")
        logger.info(f"TL payments: {stats['tl_payments']}")
        logger.info(f"Unique dates: {stats['unique_dates']}")
        logger.info(f"API calls made: {stats['api_calls_made']}")
        logger.info(f"Cache hits: {stats['cache_hits']}")
        
        if stats['tl_payments'] > 0:
            potential_calls = stats['tl_payments']
            actual_calls = stats['api_calls_made']
            savings = potential_calls - actual_calls
            savings_percent = (savings / potential_calls) * 100
            logger.info(f"API calls saved: {savings} ({savings_percent:.1f}% reduction)")
        
        logger.info("=== TEST COMPLETED SUCCESSFULLY ===")
    else:
        logger.error("Test failed!")

if __name__ == "__main__":
    main()
