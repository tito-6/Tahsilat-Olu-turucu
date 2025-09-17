#!/usr/bin/env python3
"""
Installation script for Tahsilat application
Installs dependencies and sets up the application
"""

import subprocess
import sys
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 11):
        print("❌ Python 3.11 veya üzeri gerekli!")
        print(f"Mevcut Python sürümü: {sys.version}")
        return False
    print(f"✅ Python sürümü uygun: {sys.version}")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Bağımlılıklar yükleniyor...")
    
    try:
        # Upgrade pip first
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        
        # Install requirements
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        
        print("✅ Bağımlılıklar başarıyla yüklendi!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Bağımlılık yükleme hatası: {e}")
        return False
    except FileNotFoundError:
        print("❌ requirements.txt dosyası bulunamadı!")
        return False

def create_directories():
    """Create necessary directories"""
    print("\n📁 Klasörler oluşturuluyor...")
    
    directories = ["data", "reports", "logs"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ {directory}/ klasörü oluşturuldu")
    
    return True

def test_imports():
    """Test if all modules can be imported"""
    print("\n🧪 Modül testleri...")
    
    modules = [
        "PySide6",
        "pandas",
        "openpyxl",
        "xlsxwriter",
        "python-docx",
        "reportlab",
        "requests",
        "beautifulsoup4",
        "pytz"
    ]
    
    failed_imports = []
    
    for module in modules:
        try:
            if module == "beautifulsoup4":
                __import__("bs4")
            else:
                __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Başarısız modüller: {', '.join(failed_imports)}")
        return False
    
    print("✅ Tüm modüller başarıyla yüklendi!")
    return True

def run_tests():
    """Run application tests"""
    print("\n🧪 Uygulama testleri çalıştırılıyor...")
    
    try:
        result = subprocess.run([sys.executable, "test_app.py"], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Testler başarıyla tamamlandı!")
            print(result.stdout)
            return True
        else:
            print("❌ Testler başarısız!")
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("❌ Testler zaman aşımına uğradı!")
        return False
    except Exception as e:
        print(f"❌ Test çalıştırma hatası: {e}")
        return False

def create_shortcut():
    """Create desktop shortcut (Windows)"""
    if sys.platform == "win32":
        print("\n🔗 Masaüstü kısayolu oluşturuluyor...")
        
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            path = os.path.join(desktop, "Tahsilat.lnk")
            target = os.path.join(os.getcwd(), "main.py")
            wDir = os.getcwd()
            icon = target
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(path)
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = f'"{target}"'
            shortcut.WorkingDirectory = wDir
            shortcut.IconLocation = icon
            shortcut.save()
            
            print("✅ Masaüstü kısayolu oluşturuldu!")
            return True
        except ImportError:
            print("⚠️ Masaüstü kısayolu oluşturulamadı (winshell gerekli)")
            return False
        except Exception as e:
            print(f"⚠️ Masaüstü kısayolu oluşturulamadı: {e}")
            return False
    else:
        print("⚠️ Masaüstü kısayolu sadece Windows'ta destekleniyor")
        return False

def main():
    """Main installation process"""
    print("🚀 Tahsilat Uygulaması Kurulumu")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Create directories
    if not create_directories():
        return False
    
    # Test imports
    if not test_imports():
        return False
    
    # Run tests
    if not run_tests():
        print("⚠️ Testler başarısız, ancak kurulum devam ediyor...")
    
    # Create shortcut
    create_shortcut()
    
    print("\n" + "=" * 50)
    print("🎉 Kurulum tamamlandı!")
    print("\nUygulamayı çalıştırmak için:")
    print("  python main.py")
    print("\nVeya masaüstündeki kısayolu kullanın.")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
