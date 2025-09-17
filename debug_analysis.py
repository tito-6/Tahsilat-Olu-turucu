#!/usr/bin/env python3
"""
Debug script to test analysis methods
"""

import sys
import os
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_import import PaymentData
from report_generator import ReportGenerator

def test_analysis_methods():
    """Test the analysis methods to see if they return data"""
    
    # Create sample payment data
    sample_payments = [
        PaymentData({
            'Müşteri Adı Soyadı': 'Burak Bingölo',
            'Tarih': '2025-09-15',
            'Proje Adı': 'COMPANY_B 3. Etap',
            'Hesap Adı': 'Yapı Kredi TL',
            'Ödenen Tutar': 9920.32,
            'Ödenen Döviz': 'USD',
            'Tahsilat Şekli': 'BANK_TRANSFER',
            'Çek Tutarı': 0,
            'Çek Vade Tarihi': ''
        }),
        PaymentData({
            'Müşteri Adı Soyadı': 'Kamer Ergün',
            'Tarih': '2025-09-15',
            'Proje Adı': 'COMPANY_A',
            'Hesap Adı': 'Kasa USD',
            'Ödenen Tutar': 121705.00,
            'Ödenen Döviz': 'USD',
            'Tahsilat Şekli': 'Nakit',
            'Çek Tutarı': 0,
            'Çek Vade Tarihi': ''
        }),
        PaymentData({
            'Müşteri Adı Soyadı': 'Odak Kimya',
            'Tarih': '2025-09-16',
            'Proje Adı': 'COMPANY_A',
            'Hesap Adı': 'Yapı Kredi USD',
            'Ödenen Tutar': 7000.00,
            'Ödenen Döviz': 'USD',
            'Tahsilat Şekli': 'BANK_TRANSFER',
            'Çek Tutarı': 0,
            'Çek Vade Tarihi': ''
        })
    ]
    
    # Test date range
    start_date = datetime(2025, 9, 1)
    end_date = datetime(2025, 9, 30)
    
    # Generate analysis
    generator = ReportGenerator()
    
    print("Testing Payment Type Analysis...")
    payment_analysis = generator.generate_payment_type_analysis(sample_payments, start_date, end_date)
    print(f"Payment Type Analysis: {payment_analysis}")
    
    print("\nTesting Project Totals Analysis...")
    project_analysis = generator.generate_project_totals_analysis(sample_payments, start_date, end_date)
    print(f"Project Totals Analysis: {project_analysis}")
    
    print("\nTesting Location Analysis...")
    location_analysis = generator.generate_location_analysis(sample_payments, start_date, end_date)
    print(f"Location Analysis: {location_analysis}")
    
    print("\nTesting HTML Preview...")
    html_sheets = generator.generate_html_preview(sample_payments, start_date, end_date)
    print(f"HTML Sheets: {list(html_sheets.keys())}")
    
    # Check if analysis tables are in HTML
    for sheet_name, html_content in html_sheets.items():
        if "ÖDEME TİPİ ANALİZİ" in html_content:
            print(f"✅ {sheet_name} contains ÖDEME TİPİ ANALİZİ")
        else:
            print(f"❌ {sheet_name} missing ÖDEME TİPİ ANALİZİ")
            
        if "PROJE TOPLAMLARI" in html_content:
            print(f"✅ {sheet_name} contains PROJE TOPLAMLARI")
        else:
            print(f"❌ {sheet_name} missing PROJE TOPLAMLARI")
            
        if "LOKASYON ANALİZİ" in html_content:
            print(f"✅ {sheet_name} contains LOKASYON ANALİZİ")
        else:
            print(f"❌ {sheet_name} missing LOKASYON ANALİZİ")

if __name__ == "__main__":
    test_analysis_methods()
