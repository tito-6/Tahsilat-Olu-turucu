#!/usr/bin/env python3
"""
Tahsilat Application Launcher
Simple launcher with error handling and status messages
"""

import sys
import os
import traceback
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_modules = [
        'PySide6',
        'pandas', 
        'openpyxl',
        'xlsxwriter',
        'python_docx',
        'reportlab',
        'requests',
        'bs4',
        'pytz'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            if module == 'python_docx':
                __import__('docx')
            elif module == 'bs4':
                __import__('bs4')
            else:
                __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    return missing_modules

def main():
    """Main launcher function"""
    print("🚀 Tahsilat - Ödeme Raporlama Otomasyonu")
    print("=" * 50)
    
    # Check dependencies
    print("📦 Bağımlılıklar kontrol ediliyor...")
    missing = check_dependencies()
    
    if missing:
        print(f"❌ Eksik modüller: {', '.join(missing)}")
        print("\nLütfen şu komutu çalıştırın:")
        print("pip install -r requirements.txt")
        input("\nDevam etmek için Enter'a basın...")
        return False
    
    print("✅ Tüm bağımlılıklar mevcut")
    
    # Check if main.py exists
    if not os.path.exists("main.py"):
        print("❌ main.py dosyası bulunamadı!")
        input("\nDevam etmek için Enter'a basın...")
        return False
    
    # Create necessary directories
    directories = ["data", "reports", "logs"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("📁 Klasörler hazırlandı")
    
    # Launch application
    print("🎯 Uygulama başlatılıyor...")
    print("=" * 50)
    
    try:
        # Import and run main application
        from main import main as app_main
        app_main()
        return True
    except Exception as e:
        print(f"❌ Uygulama hatası: {e}")
        print("\nDetaylı hata bilgisi:")
        traceback.print_exc()
        input("\nDevam etmek için Enter'a basın...")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
