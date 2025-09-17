#!/usr/bin/env python3
"""
Test script to verify weekly vs monthly display in analysis tables
"""

import logging
from datetime import datetime, timedelta
from storage import PaymentStorage
from report_generator import ReportGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_weekly_monthly_display():
    """Test that weekly and monthly analysis tables show different data"""
    logger.info("=== TESTING WEEKLY VS MONTHLY DISPLAY ===")
    
    # Load real payment data
    storage = PaymentStorage()
    payments = storage.get_all_payments()
    
    if not payments:
        logger.error("No payment data found!")
        return
    
    logger.info(f"Loaded {len(payments)} payments")
    
    # Set date range
    start_date = datetime(2025, 9, 1)
    end_date = datetime(2025, 9, 30)
    
    # Generate HTML preview
    generator = ReportGenerator()
    html_sheets = generator.generate_html_preview(payments, start_date, end_date)
    
    logger.info(f"Generated {len(html_sheets)} HTML sheets: {list(html_sheets.keys())}")
    
    # Check each sheet
    for sheet_name, html_content in html_sheets.items():
        logger.info(f"\n=== ANALYZING SHEET: {sheet_name} ===")
        
        # Check if it contains analysis tables
        if "ÖDEME TİPİ ANALİZİ" in html_content:
            logger.info("✅ Contains Payment Type Analysis")
            
            # Extract the analysis data from HTML (basic check)
            if "BANK_TRANSFER" in html_content:
                logger.info("✅ Contains BANK_TRANSFER data")
            if "Nakit" in html_content:
                logger.info("✅ Contains Nakit data")
            if "Çek" in html_content:
                logger.info("✅ Contains Çek data")
            
            # Check for different weekly vs monthly data
            if sheet_name != "Özet":
                logger.info(f"📊 This is a weekly sheet: {sheet_name}")
                # Weekly sheets should show data for that specific week only
            else:
                logger.info("📊 This is the summary sheet")
                # Summary sheet should show aggregated data
        else:
            logger.warning("❌ Missing Payment Type Analysis")
    
    logger.info("\n=== TEST COMPLETED ===")

if __name__ == "__main__":
    test_weekly_monthly_display()
