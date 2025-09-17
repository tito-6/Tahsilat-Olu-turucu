"""
Validation and error handling module
Provides comprehensive validation for payment data and system operations
"""

import re
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class PaymentValidator:
    """Validates payment data and system operations"""
    
    def __init__(self):
        self.required_fields = [
            'Müşteri Adı Soyadı',
            'Tarih',
            'Proje Adı',
            'Hesap Adı',
            'Ödenen Tutar'
        ]
        
        self.valid_currencies = ['TL', 'TRY', 'TURKISH LIRA', 'USD', 'US DOLLAR']
        self.valid_payment_statuses = ['Ödendi', 'Beklemede', 'İptal', 'Kısmi']
        
        # Turkish name pattern
        self.name_pattern = re.compile(r'^[a-zA-ZçğıöşüÇĞIİÖŞÜ\s]+$')
        
        # Amount pattern (positive numbers with optional decimal)
        self.amount_pattern = re.compile(r'^\d+(\.\d{1,2})?$')
    
    def validate_payment_data(self, payment_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a single payment record
        Returns (is_valid, error_messages)
        """
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in payment_data or not payment_data[field]:
                errors.append(f"Eksik zorunlu alan: {field}")
        
        # Validate customer name
        if 'Müşteri Adı Soyadı' in payment_data:
            customer_name = str(payment_data['Müşteri Adı Soyadı']).strip()
            if not customer_name:
                errors.append("Müşteri adı boş olamaz")
            elif not self.name_pattern.match(customer_name):
                errors.append("Müşteri adı geçersiz karakterler içeriyor")
            elif len(customer_name) < 2:
                errors.append("Müşteri adı çok kısa")
            elif len(customer_name) > 100:
                errors.append("Müşteri adı çok uzun")
        
        # Validate date
        if 'Tarih' in payment_data:
            date_value = payment_data['Tarih']
            if not self._validate_date(date_value):
                errors.append("Geçersiz tarih formatı")
            else:
                # Check if date is not too far in the future
                if isinstance(date_value, datetime):
                    if date_value > datetime.now() + timedelta(days=365):
                        errors.append("Tarih çok ileri bir tarih")
                    elif date_value < datetime(2020, 1, 1):
                        errors.append("Tarih çok eski")
        
        # Validate project name
        if 'Proje Adı' in payment_data:
            project_name = str(payment_data['Proje Adı']).strip()
            if not project_name:
                errors.append("Proje adı boş olamaz")
            elif len(project_name) > 100:
                errors.append("Proje adı çok uzun")
        
        # Validate account name
        if 'Hesap Adı' in payment_data:
            account_name = str(payment_data['Hesap Adı']).strip()
            if not account_name:
                errors.append("Hesap adı boş olamaz")
            elif len(account_name) > 100:
                errors.append("Hesap adı çok uzun")
        
        # Validate amount
        if 'Ödenen Tutar' in payment_data:
            amount = payment_data['Ödenen Tutar']
            if not self._validate_amount(amount):
                errors.append("Geçersiz tutar formatı")
            else:
                amount_value = float(str(amount).replace(',', ''))
                if amount_value < 0:
                    errors.append("Tutar negatif olamaz")
                elif amount_value > 10000000:  # 10 million limit
                    errors.append("Tutar çok yüksek")
                elif amount_value == 0:
                    errors.append("Tutar sıfır olamaz")
        
        # Validate currency
        if 'Ödenen Döviz' in payment_data:
            currency = str(payment_data['Ödenen Döviz']).strip().upper()
            if currency and currency not in self.valid_currencies:
                errors.append(f"Desteklenmeyen döviz türü: {currency}")
        
        # Validate exchange rate
        if 'Ödenen Kur' in payment_data:
            rate = payment_data['Ödenen Kur']
            if rate and not self._validate_exchange_rate(rate):
                errors.append("Geçersiz döviz kuru formatı")
        
        # Validate payment status
        if 'Ödeme Durumu' in payment_data:
            status = str(payment_data['Ödeme Durumu']).strip()
            if status and status not in self.valid_payment_statuses:
                errors.append(f"Geçersiz ödeme durumu: {status}")
        
        return len(errors) == 0, errors
    
    def _validate_date(self, date_value: Any) -> bool:
        """Validate date format and value"""
        if not date_value:
            return False
        
        if isinstance(date_value, datetime):
            return True
        
        # Try to parse as string
        date_str = str(date_value).strip()
        if not date_str:
            return False
        
        # Common date formats
        date_formats = [
            '%Y-%m-%d',
            '%d.%m.%Y',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d.%m.%y',
            '%d/%m/%y'
        ]
        
        for fmt in date_formats:
            try:
                datetime.strptime(date_str, fmt)
                return True
            except ValueError:
                continue
        
        return False
    
    def _validate_amount(self, amount_value: Any) -> bool:
        """Validate amount format and value"""
        if not amount_value:
            return False
        
        if isinstance(amount_value, (int, float)):
            return True
        
        # Try to parse as string
        amount_str = str(amount_value).replace(',', '').replace(' ', '').strip()
        if not amount_str:
            return False
        
        try:
            float(amount_str)
            return True
        except ValueError:
            return False
    
    def _validate_exchange_rate(self, rate_value: Any) -> bool:
        """Validate exchange rate format and value"""
        if not rate_value:
            return True  # Optional field
        
        if isinstance(rate_value, (int, float)):
            return 0 < rate_value < 1000  # Reasonable range
        
        # Try to parse as string
        rate_str = str(rate_value).replace(',', '').strip()
        try:
            rate = float(rate_str)
            return 0 < rate < 1000
        except ValueError:
            return False
    
    def validate_file_path(self, file_path: str) -> Tuple[bool, str]:
        """Validate file path and existence"""
        if not file_path:
            return False, "Dosya yolu boş"
        
        if not os.path.exists(file_path):
            return False, "Dosya bulunamadı"
        
        if not os.path.isfile(file_path):
            return False, "Geçersiz dosya yolu"
        
        # Check file size (max 50MB)
        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:  # 50MB
            return False, "Dosya çok büyük (max 50MB)"
        
        if file_size == 0:
            return False, "Dosya boş"
        
        return True, ""
    
    def validate_date_range(self, start_date: datetime, end_date: datetime) -> Tuple[bool, str]:
        """Validate date range"""
        if not start_date or not end_date:
            return False, "Tarih aralığı boş olamaz"
        
        # Convert date to datetime if needed
        if hasattr(start_date, 'date'):
            start_date = start_date.date()
        if hasattr(end_date, 'date'):
            end_date = end_date.date()
        
        # Convert to datetime for comparison
        import datetime as dt_module
        if isinstance(start_date, dt_module.date) and not isinstance(start_date, dt_module.datetime):
            start_date = dt_module.datetime.combine(start_date, dt_module.datetime.min.time())
        if isinstance(end_date, dt_module.date) and not isinstance(end_date, dt_module.datetime):
            end_date = dt_module.datetime.combine(end_date, dt_module.datetime.min.time())
        
        if start_date > end_date:
            return False, "Başlangıç tarihi bitiş tarihinden sonra olamaz"
        
        if end_date > dt_module.datetime.now() + timedelta(days=365):
            return False, "Bitiş tarihi çok ileri bir tarih"
        
        if start_date < dt_module.datetime(2020, 1, 1):
            return False, "Başlangıç tarihi çok eski"
        
        # Check if range is too large (more than 2 years)
        if (end_date - start_date).days > 730:
            return False, "Tarih aralığı çok geniş (max 2 yıl)"
        
        return True, ""
    
    def validate_export_path(self, file_path: str, file_format: str) -> Tuple[bool, str]:
        """Validate export file path and format"""
        if not file_path:
            return False, "Çıktı dosya yolu boş"
        
        # Check if directory exists and is writable
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            return False, "Çıktı klasörü bulunamadı"
        
        if not os.access(directory, os.W_OK):
            return False, "Çıktı klasörüne yazma izni yok"
        
        # Check file extension
        valid_extensions = {
            'excel': ['.xlsx'],
            'pdf': ['.pdf'],
            'word': ['.docx'],
            'json': ['.json'],
            'csv': ['.csv']
        }
        
        if file_format in valid_extensions:
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in valid_extensions[file_format]:
                return False, f"Geçersiz dosya uzantısı: {file_ext}"
        
        return True, ""

class ErrorHandler:
    """Centralized error handling for the application"""
    
    @staticmethod
    def handle_import_error(error: Exception, file_path: str) -> str:
        """Handle data import errors"""
        error_msg = str(error)
        
        if "No such file or directory" in error_msg:
            return f"Dosya bulunamadı: {file_path}"
        elif "Permission denied" in error_msg:
            return f"Dosyaya erişim izni yok: {file_path}"
        elif "UnicodeDecodeError" in error_msg:
            return f"Dosya kodlama hatası. Lütfen dosyayı UTF-8 formatında kaydedin."
        elif "KeyError" in error_msg:
            return f"Dosyada gerekli sütun bulunamadı: {error_msg}"
        elif "ValueError" in error_msg:
            return f"Veri formatı hatası: {error_msg}"
        else:
            return f"İçe aktarma hatası: {error_msg}"
    
    @staticmethod
    def handle_currency_error(error: Exception) -> str:
        """Handle currency conversion errors"""
        error_msg = str(error)
        
        if "ConnectionError" in error_msg or "Timeout" in error_msg:
            return "İnternet bağlantısı hatası. Döviz kuru alınamadı."
        elif "HTTPError" in error_msg:
            return "TCMB sunucusu hatası. Döviz kuru alınamadı."
        elif "ValueError" in error_msg:
            return "Döviz kuru formatı hatası."
        else:
            return f"Döviz kuru hatası: {error_msg}"
    
    @staticmethod
    def handle_storage_error(error: Exception) -> str:
        """Handle storage errors"""
        error_msg = str(error)
        
        if "Permission denied" in error_msg:
            return "Veri dosyasına yazma izni yok."
        elif "Disk full" in error_msg:
            return "Disk alanı dolu."
        elif "JSON" in error_msg:
            return "Veri formatı hatası."
        else:
            return f"Depolama hatası: {error_msg}"
    
    @staticmethod
    def handle_report_error(error: Exception) -> str:
        """Handle report generation errors"""
        error_msg = str(error)
        
        if "Permission denied" in error_msg:
            return "Rapor dosyasına yazma izni yok."
        elif "Disk full" in error_msg:
            return "Disk alanı dolu."
        elif "openpyxl" in error_msg or "xlsxwriter" in error_msg:
            return "Excel dosyası oluşturma hatası."
        elif "reportlab" in error_msg:
            return "PDF dosyası oluşturma hatası."
        elif "python-docx" in error_msg:
            return "Word dosyası oluşturma hatası."
        else:
            return f"Rapor oluşturma hatası: {error_msg}"

# Global instances
validator = PaymentValidator()
error_handler = ErrorHandler()

def validate_payment(payment_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Convenience function for payment validation"""
    return validator.validate_payment_data(payment_data)

def validate_file(file_path: str) -> Tuple[bool, str]:
    """Convenience function for file validation"""
    return validator.validate_file_path(file_path)

def validate_dates(start_date: datetime, end_date: datetime) -> Tuple[bool, str]:
    """Convenience function for date range validation"""
    return validator.validate_date_range(start_date, end_date)
