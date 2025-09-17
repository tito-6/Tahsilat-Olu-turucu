"""
Data import module for handling various file formats
Supports CSV, XLSX, JSON and manual table input
"""

import pandas as pd
import json
import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class PaymentData:
    """Represents a single payment record"""
    
    def __init__(self, data: Dict[str, Any], amount_column: str = None, currency_column: str = None):
        self.customer_name = data.get('Müşteri Adı Soyadı', '')
        self.date = self._parse_date(data.get('Tarih', ''))
        self.project_name = data.get('Proje Adı', '') or 'Genel Proje'
        self.account_name = data.get('Hesap Adı', '')
        # Use selected columns if provided, else fallback to default
        amount_key = amount_column if amount_column else 'Ödenen Tutar'
        currency_key = currency_column if currency_column else 'Ödenen Döviz'
        self.original_amount = self._parse_amount(self._get_dynamic_value(data, amount_key))
        self.currency = data.get(currency_key, 'TL')
        self.exchange_rate = self._parse_amount(self._get_dynamic_value(data, 'Ödenen Kur'))
        self.payment_status = data.get('Ödeme Durumu', '')
        
        # Convert all non-USD currencies to USD
        self.amount, self.usd_amount, self.conversion_rate, self.conversion_date = self._convert_to_usd()
        
        # For backward compatibility, set amount to USD equivalent
        # This ensures all calculations use USD amounts
        if self.usd_amount > 0:
            self.amount = self.usd_amount
        
        # Payment type/collection method
        self.tahsilat_sekli = data.get('Tahsilat Şekli', '')
        
        # Check-specific fields
        self.original_cek_tutari = self._parse_amount(self._get_dynamic_value(data, 'Çek Tutarı'))
        self.cek_vade_tarihi = self._parse_date(data.get('Çek Vade Tarihi', ''))
        
        # Detect if this is a check payment - ONLY from explicit check indicators
        self.is_check_payment = (
            self.tahsilat_sekli.upper() == 'ÇEK' or
            self.tahsilat_sekli.upper() == 'CEK' or
            self.tahsilat_sekli.upper() == 'CHECK' or
            (self.original_cek_tutari > 0 and data.get('Çek Vade Tarihi', '') != '')
        )
        
        # If it's a check payment but no specific check amount, use the main amount
        if self.is_check_payment and self.original_cek_tutari == 0:
            self.original_cek_tutari = self.original_amount
        
        # Convert check amount to USD if it's a check payment
        if self.is_check_payment and self.original_cek_tutari > 0:
            self.cek_tutari, self.cek_usd_amount, self.cek_conversion_rate, self.cek_conversion_date = self._convert_check_to_usd()
        else:
            self.cek_tutari = 0.0
            self.cek_usd_amount = 0.0
            self.cek_conversion_rate = 0.0
            self.cek_conversion_date = None
        
        # If no check maturity date but is check payment, calculate default (6 months later)
        if self.is_check_payment and not self.cek_vade_tarihi and self.date:
            self.cek_vade_tarihi = self.date + timedelta(days=180)  # 6 months default
        
        # Derived fields
        self.payment_channel = self._detect_payment_channel()
        self.is_tl_payment = self._detect_currency()
        self.payment_type = self._detect_payment_type()
        
        # Update tahsilat_sekli with detected payment type if not already set or if it's 'Diğer'
        if not self.tahsilat_sekli or self.tahsilat_sekli == 'Diğer':
            self.tahsilat_sekli = self.payment_type
        
    def _parse_date(self, date_value: Any) -> Optional[datetime]:
        """Parse date from various formats"""
        if not date_value or str(date_value).lower() in ['nan', 'none', '']:
            return None
        
        # Check for pandas NaN values
        try:
            import pandas as pd
            if pd.isna(date_value):
                return None
        except:
            pass
        
        if isinstance(date_value, datetime):
            return date_value
        
        # Try common date formats
        date_formats = [
            '%Y-%m-%d',
            '%d.%m.%Y',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d.%m.%y',
            '%d/%m/%y',
            '%d.%m.%Y %H:%M:%S',
            '%d/%m/%Y %H:%M:%S'
        ]
        
        date_str = str(date_value).strip()
        
        # Handle special cases
        if date_str.lower() in ['nan', 'none', '']:
            return None
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try pandas date parsing as fallback
        try:
            import pandas as pd
            parsed_date = pd.to_datetime(date_str, errors='coerce')
            if not pd.isna(parsed_date):
                return parsed_date.to_pydatetime()
        except:
            pass
        
        logger.warning(f"Could not parse date: {date_value}")
        return None
    
    def _parse_amount(self, amount_value: Any) -> float:
        """Parse amount from various formats"""
        if not amount_value:
            return 0.0
        
        if isinstance(amount_value, (int, float)):
            return float(amount_value)
        
        # Convert to string and clean up
        amount_str = str(amount_value).strip()
        
        # Handle empty or null values
        if not amount_str or amount_str.lower() in ['nan', 'none', 'null', '']:
            return 0.0
        
        # Remove common separators and currency symbols
        amount_str = amount_str.replace(',', '').replace(' ', '').replace('₺', '').replace('$', '').replace('€', '')
        
        # Extract number from strings like "Ödenen Tutar(?:9,835,209.80)" or "Ödenen Tutar(Σ:11,059,172.00)"
        if '(' in amount_str and ('?:' in amount_str or 'Σ:' in amount_str):
            try:
                # Extract the part after ?: or Σ:
                if '?:' in amount_str:
                    start = amount_str.find('?:') + 2
                else:
                    start = amount_str.find('Σ:') + 2
                end = amount_str.find(')', start)
                if end == -1:
                    end = len(amount_str)
                amount_str = amount_str[start:end]
            except:
                pass
        
        try:
            return float(amount_str)
        except ValueError:
            logger.warning(f"Could not parse amount: {amount_value}")
            return 0.0
    
    def _detect_payment_channel(self) -> str:
        """Detect payment channel from account name with robust Turkish character handling"""
        if not self.account_name:
            return 'Bilinmeyen'
        
        account_upper = self.account_name.upper()
        
        # More robust channel detection with multiple character variations
        # Handle Turkish character encoding issues (ş, ç, ı, etc.)
        
        # LOCATION_B detection - check for various spellings
        if any(keyword in account_upper for keyword in ['LOCATION_B', 'KUYUMCU KENT', 'KUYUMCU_KENT']):
            return 'LOCATION_B'
        
        # ÇARŞI detection - handle multiple character encodings
        elif any(keyword in account_upper for keyword in [
            'ÇARŞI', 'CARSI', 'ÇARÞI', 'CARÞI', 'CARŞI', 'ÇARSI'
        ]):
            return 'ÇARŞI'
        
        # OFİS detection
        elif any(keyword in account_upper for keyword in [
            'OFİS', 'LOCATION_C', 'OFÝS', 'MERKEZ', 'OFFICE'
        ]):
            return 'OFİS'
        
        # BANKA HAVALESİ detection
        elif any(keyword in account_upper for keyword in [
            'YAPI KREDİ', 'YAPI KREDI', 'YAPIKREDÝ', 'YAPIKREDI',
            'HAVALE', 'TRANSFER', 'BANKA'
        ]):
            return 'BANKA HAVALESİ'
        
        # KAPAKLI (office location)
        elif 'KAPAKLI' in account_upper:
            return 'OFİS'
        
        # ÇEK detection with kasa types
        elif any(cek_keyword in account_upper for cek_keyword in ['ÇEK', 'CEK', 'CHECK']):
            if 'A KASA' in account_upper or 'A_KASA' in account_upper:
                return 'A KASA ÇEK'
            elif 'B KASA' in account_upper or 'B_KASA' in account_upper:
                return 'B KASA ÇEK'
            else:
                return 'ÇEK'
        
        # NAKİT detection
        elif any(keyword in account_upper for keyword in [
            'NAKIT', 'NAKİT', 'NAKÝT', 'CASH'
        ]):
            return 'NAKİT'
        
        # If none of the above patterns match, return 'Diğer'
        return 'Diğer'
    
    def _detect_payment_type(self) -> str:
        """Detect payment type from Tahsilat Şekli and account name"""
        if not self.tahsilat_sekli and not self.account_name:
            return 'Diğer'
        
        # Check Tahsilat Şekli field first, but only if it's not 'Diğer' or empty
        if self.tahsilat_sekli and self.tahsilat_sekli != 'Diğer':
            tahsilat_upper = self.tahsilat_sekli.upper()
            if 'NAKİT' in tahsilat_upper or 'NAKIT' in tahsilat_upper:
                return 'Nakit'
            elif 'BANKA' in tahsilat_upper or 'HAVALE' in tahsilat_upper:
                return 'BANK_TRANSFER'
            elif 'ÇEK' in tahsilat_upper or 'CEK' in tahsilat_upper:
                return 'Çek'
        
        # Check account name as fallback
        account_upper = self.account_name.upper() if self.account_name else ''
        
        # Debug logging
        logger.info(f"Payment type detection - Account: '{self.account_name}' -> '{account_upper}'")
        
        # Check for Yapı Kredi with more comprehensive patterns
        if any(keyword in account_upper for keyword in [
            'YAPI KREDİ', 'YAPI KREDI', 'YAPIKREDÝ', 'YAPIKREDI', 'YAPI'
        ]):
            logger.info(f"Detected Yapı Kredi payment: {self.account_name}")
            return 'BANK_TRANSFER'
        elif 'KASA' in account_upper and 'NAKİT' not in account_upper:
            return 'Nakit'  # Kasa accounts are usually cash
        elif self.is_check_payment:
            return 'Çek'
        elif any(keyword in account_upper for keyword in [
            'HAVALE', 'TRANSFER', 'BANKA', 'GARANTI', 'İŞ BANKASI'
        ]):
            return 'BANK_TRANSFER'
        
        # Default to BANK_TRANSFER for TL payments from bank accounts
        if self.is_tl_payment and account_upper:
            logger.info(f"Defaulting TL payment to BANK_TRANSFER: {self.account_name}")
            return 'BANK_TRANSFER'
        
        return 'Diğer'
    
    def _get_dynamic_value(self, data: Dict[str, Any], base_key: str, custom_key: str = None) -> Any:
        """Get value from data dict, handling dynamic column names with parentheses"""
        # First try exact match
        if base_key in data:
            return data[base_key]
        
        # Then try to find keys that start with the base key
        for key in data.keys():
            if key.startswith(base_key):
                return data[key]
        
        # If a custom key is provided, try that as well
        if custom_key and custom_key in data:
            return data[custom_key]
        
        # Return default value
        return 0 if 'Tutar' in base_key or 'Kur' in base_key else ''
    
    def _convert_to_usd(self) -> Tuple[float, float, float, Optional[datetime]]:
        """Convert payment amount to USD if not already USD"""
        if not self.original_amount or self.original_amount <= 0:
            return 0.0, 0.0, 0.0, None
        
        # If already USD, return as is
        if self.currency.upper() in ['USD', 'US DOLLAR', 'DOLLAR', 'DOLAR']:
            return self.original_amount, self.original_amount, 1.0, self.date
        
        # If no date, can't convert
        if not self.date:
            return self.original_amount, 0.0, 0.0, None
        
        # For TL payments (or any non-USD currency), convert to USD
        # The currency.py module already handles using exchange rate from day before payment date
        try:
            # Import currency converter
            from currency import convert_payment_to_usd
            
            # Convert to USD using exchange rate from day before payment date
            usd_amount, rate = convert_payment_to_usd(self.original_amount, self.date)
            
            # Handle conversion results
            if usd_amount and usd_amount > 0 and rate and rate > 0:
                return self.original_amount, usd_amount, rate, self.date
            else:
                # Conversion failed, return original amount
                logger.warning(f"Failed to convert {self.currency} {self.original_amount} to USD for {self.customer_name} on {self.date}")
                return self.original_amount, 0.0, 0.0, None
                
        except Exception as e:
            logger.warning(f"Failed to convert {self.currency} to USD for {self.customer_name}: {e}")
            return self.original_amount, 0.0, 0.0, None
    
    def _convert_check_to_usd(self) -> Tuple[float, float, float, Optional[datetime]]:
        """Convert check amount to USD if not already USD"""
        if not self.original_cek_tutari or self.original_cek_tutari <= 0:
            return 0.0, 0.0, 0.0, None
        
        # If already USD, return as is
        if self.currency.upper() in ['USD', 'US DOLLAR', 'DOLLAR', 'DOLAR']:
            return self.original_cek_tutari, self.original_cek_tutari, 1.0, self.cek_vade_tarihi or self.date
        
        # Use check maturity date for conversion, fallback to payment date
        conversion_date = self.cek_vade_tarihi or self.date
        if not conversion_date:
            return self.original_cek_tutari, 0.0, 0.0, None
        
        try:
            # Import currency converter
            from currency import convert_payment_to_usd
            
            # Convert to USD
            usd_amount, rate = convert_payment_to_usd(self.original_cek_tutari, conversion_date)
            
            # Handle conversion results
            if usd_amount and usd_amount > 0 and rate and rate > 0:
                return self.original_cek_tutari, usd_amount, rate, conversion_date
            else:
                # Conversion failed, return original amount
                return self.original_cek_tutari, 0.0, 0.0, None
                
        except Exception as e:
            logger.warning(f"Failed to convert check amount {self.currency} to USD for {self.customer_name}: {e}")
            return self.original_cek_tutari, 0.0, 0.0, None
    
    def _detect_currency(self) -> bool:
        """Detect if this is a TL payment based on currency field and account name"""
        # First check the currency field
        if self.currency.upper() in ['TL', 'TRY', 'TURKISH LIRA', 'TÜRK LİRASI']:
            return True
        elif self.currency.upper() in ['USD', 'US DOLLAR', 'DOLLAR', 'DOLAR']:
            return False
        
        # If currency field is unclear, check account name
        if self.account_name:
            account_lower = self.account_name.lower()
            # Check for TL indicators
            if any(keyword in account_lower for keyword in ['tl', 'türk lirası', 'turk lirasi', 'lira']):
                return True
            # Check for USD indicators
            elif any(keyword in account_lower for keyword in ['usd', 'dolar', 'dollar', '$']):
                return False
        
        # Default to TL if unclear
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'customer_name': self.customer_name,
            'date': self.date.isoformat() if self.date else None,
            'project_name': self.project_name,
            'account_name': self.account_name,
            'amount': self.amount,
            'currency': self.currency,
            'exchange_rate': self.exchange_rate,
            'payment_status': self.payment_status,
            'payment_channel': self.payment_channel,
            'is_tl_payment': self.is_tl_payment,
            'tahsilat_sekli': self.tahsilat_sekli,
            'cek_tutari': self.cek_tutari,
            'cek_vade_tarihi': self.cek_vade_tarihi.isoformat() if self.cek_vade_tarihi else None,
            'is_check_payment': self.is_check_payment,
            'payment_type': self.payment_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaymentData':
        """Create PaymentData from dictionary"""
        # Convert the stored format back to the format expected by __init__
        init_data = {
            'Müşteri Adı Soyadı': data.get('customer_name', ''),
            'Tarih': data.get('date', ''),
            'Proje Adı': data.get('project_name', ''),
            'Hesap Adı': data.get('account_name', ''),
            'Ödenen Tutar': data.get('amount', 0.0),
            'Ödenen Döviz': data.get('currency', 'TL'),
            'Ödenen Kur': data.get('exchange_rate', 0.0),
            'Ödeme Durumu': data.get('payment_status', ''),
            'Tahsilat Şekli': data.get('tahsilat_sekli', ''),
            'Çek Tutarı': data.get('cek_tutari', 0.0),
            'Çek Vade Tarihi': data.get('cek_vade_tarihi', '')
        }
        
        # Convert date string back to datetime
        if data.get('date'):
            try:
                init_data['Tarih'] = datetime.fromisoformat(data['date'])
            except:
                init_data['Tarih'] = data['date']
        
        # Convert check maturity date
        if data.get('cek_vade_tarihi'):
            try:
                init_data['Çek Vade Tarihi'] = datetime.fromisoformat(data['cek_vade_tarihi'])
            except:
                init_data['Çek Vade Tarihi'] = data['cek_vade_tarihi']
        
        return cls(init_data)

class DataImporter:
    """Handles importing payment data from various sources"""
    
    def __init__(self):
        self.required_fields = [
            'Müşteri Adı Soyadı',
            'Tarih',
            'Hesap Adı',
            'Ödenen Tutar'
        ]
        
        # Optional fields for better functionality
        self.optional_fields = [
            'Proje Adı',
            'Tahsilat Şekli',
            'Çek Tutarı',
            'Çek Vade Tarihi',
            'Ödenen Döviz',
            'Ödenen Kur',
            'Ödeme Durumu'
        ]
        
        # Alternative field names that might be used (including encoding issues)
        self.alternative_fields = {
            'Müşteri Adı Soyadı': ['Müşteri', 'Customer', 'Ad Soyad', 'İsim', 'Müþteri Adý Soyadý', 'Müþteri Adý', 'Müþteri'],
            'Tarih': ['Date', 'Tarih', 'Ödeme Tarihi'],
            'Proje Adı': ['Proje', 'Project', 'Proje Adı', 'Proje Adý'],
            'Hesap Adı': ['Hesap', 'Account', 'Hesap Adı', 'Kanal', 'Hesap Adý'],
            'Ödenen Tutar': ['Ödenen Tutar', 'Tutar', 'Amount', 'Miktar', 'Para', 
                            'Ödenen Tutar(Σ:11,059,172.00)', 'Ödenen Tutar(?:7,549,753.57)',
                            'Alacak Tutarı(Σ:1,145,366.37)', 'Alacak Tutarý(?:1,062,821.62)'],
            'Tahsilat Şekli': ['Tahsilat Sekli', 'Payment Type', 'Ödeme Türü', 'Ödeme Şekli', 'Collection Method', 'Tahsilat Þekli'],
            'Çek Tutarı': ['Cek Tutari', 'Check Amount', 'Çek Miktarı', 'Çek Tutarý'],
            'Çek Vade Tarihi': ['Cek Vade Tarihi', 'Check Maturity Date', 'Vade Tarihi', 'Maturity Date', 'Çek Vade Tarihi'],
            'Ödenen Döviz': ['Döviz', 'Currency', 'Ödenen Döviz', 'Ödenen Döviz'],
            'Ödenen Kur': ['Kur', 'Exchange Rate', 'Ödenen Kur', 'Ödenen Kur(?:44.63)'],
            'Ödeme Durumu': ['Payment Status', 'Ödeme Durumu', 'Ödeme Durumu']
        }
    
    def import_csv(self, file_path: str, amount_column: str = None, currency_column: str = None) -> List[PaymentData]:
        """Import data from CSV file with multiple encoding attempts"""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-16']
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                logger.info(f"Successfully read CSV with encoding: {encoding}")
                return self._process_dataframe(df, amount_column, currency_column)
            except UnicodeDecodeError:
                logger.warning(f"Failed to read with encoding: {encoding}")
                continue
            except Exception as e:
                logger.error(f"Failed to read CSV file with {encoding}: {e}")
                continue
        
        # If all encodings fail, try with error handling
        try:
            df = pd.read_csv(file_path, encoding='utf-8', errors='replace')
            logger.warning("Reading CSV with error replacement")
            return self._process_dataframe(df, amount_column, currency_column)
        except Exception as e:
            logger.error(f"Failed to import CSV: {e}")
            raise
    
    def import_xlsx(self, file_path: str, sheet_name: Optional[str] = None, amount_column: str = None, currency_column: str = None) -> List[PaymentData]:
        """Import data from XLSX file with enhanced error handling"""
        try:
            # First validate file
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                return []
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error(f"File is empty: {file_path}")
                return []
            
            # Try different engines
            engines = ['openpyxl', 'xlrd']
            df = None
            
            for engine in engines:
                try:
                    if sheet_name:
                        df = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine)
                    else:
                        df = pd.read_excel(file_path, engine=engine)
                    
                    logger.info(f"Successfully read Excel file with engine: {engine}")
                    break
                    
                except Exception as engine_error:
                    logger.warning(f"Engine {engine} failed: {engine_error}")
                    continue
            
            if df is None:
                logger.error("All Excel engines failed to read the file")
                return []
            
            return self._process_dataframe(df, amount_column, currency_column)
            
        except Exception as e:
            logger.error(f"Failed to import XLSX: {e}")
            return []
    
    def import_json(self, file_path: str, amount_column: str = None, currency_column: str = None) -> List[PaymentData]:
        """Import data from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                return [PaymentData(item, amount_column, currency_column) for item in data]
            else:
                logger.error("JSON file should contain a list of payment records")
                raise ValueError("Invalid JSON format")
        except Exception as e:
            logger.error(f"Failed to import JSON: {e}")
            raise
    
    def import_manual_data(self, data: List[Dict[str, Any]]) -> List[PaymentData]:
        """Import data from manual table input"""
        try:
            return [PaymentData(item) for item in data]
        except Exception as e:
            logger.error(f"Failed to import manual data: {e}")
            raise
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to match expected field names"""
        column_mapping = {}
        
        for col in df.columns:
            col_str = str(col).strip()
            # Check if this column matches any of our required fields
            for required_field, alternatives in self.alternative_fields.items():
                # Check exact match first
                if col_str == required_field:
                    column_mapping[col] = required_field
                    break
                # Check if column is in alternatives list
                elif col_str in alternatives:
                    column_mapping[col] = required_field
                    break
                # Check if column starts with the required field (for dynamic column names with parentheses)
                elif col_str.startswith(required_field):
                    column_mapping[col] = required_field
                    break
        
        # Rename columns
        if column_mapping:
            df = df.rename(columns=column_mapping)
            logger.info(f"Normalized columns: {column_mapping}")
        
        return df
    
    def _process_dataframe(self, df: pd.DataFrame, amount_column: str = None, currency_column: str = None) -> List[PaymentData]:
        """Process pandas DataFrame into PaymentData objects"""
        # Normalize column names first
        df = self._normalize_columns(df)
        
        # Validate required fields
        missing_fields = [field for field in self.required_fields if field not in df.columns]
        if missing_fields:
            logger.warning(f"Missing required fields: {missing_fields}")
            logger.info(f"Available columns: {list(df.columns)}")
        
        # Convert DataFrame to list of dictionaries
        data_list = df.to_dict('records')
        
        # Create PaymentData objects
        payments = []
        for i, row in enumerate(data_list):
            try:
                payment = PaymentData(row, amount_column, currency_column)
                payments.append(payment)
            except Exception as e:
                logger.warning(f"Failed to process row {i}: {e}")
                continue
        
        logger.info(f"Successfully imported {len(payments)} payment records")
        return payments
    
    def check_duplicates(self, new_payments: List[PaymentData], existing_payments: List[PaymentData]) -> Tuple[List[PaymentData], List[Dict]]:
        """Check for duplicate payments based on EXACT amount AND EXACT date only"""
        unique_payments = []
        duplicates = []
        
        for new_payment in new_payments:
            is_duplicate = False
            duplicate_info = None
            
            # Check against existing payments - ONLY amount and date matter
            for existing_payment in existing_payments:
                if (new_payment.amount == existing_payment.amount and  # EXACT same amount
                    new_payment.date and existing_payment.date and
                    new_payment.date.date() == existing_payment.date.date()):  # EXACT same date
                    
                    is_duplicate = True
                    duplicate_info = {
                        'new_payment': new_payment,
                        'existing_payment': existing_payment,
                        'reason': f'Aynı tarih ({new_payment.date.strftime("%d.%m.%Y") if new_payment.date else "N/A"}) ve aynı tutar ({new_payment.amount:,.2f} {new_payment.currency})'
                    }
                    break
            
            if not is_duplicate:
                # Also check against other new payments in this batch - ONLY amount and date
                for other_payment in unique_payments:
                    if (new_payment.amount == other_payment.amount and  # EXACT same amount
                        new_payment.date and other_payment.date and
                        new_payment.date.date() == other_payment.date.date()):  # EXACT same date
                        
                        is_duplicate = True
                        duplicate_info = {
                            'new_payment': new_payment,
                            'existing_payment': other_payment,
                            'reason': f'Aynı batch içinde tekrar: Aynı tarih ({new_payment.date.strftime("%d.%m.%Y") if new_payment.date else "N/A"}) ve aynı tutar ({new_payment.amount:,.2f} {new_payment.currency})'
                        }
                        break
            
            if is_duplicate:
                duplicates.append(duplicate_info)
            else:
                unique_payments.append(new_payment)
        
        return unique_payments, duplicates
    
    def validate_data(self, payments: List[PaymentData]) -> Tuple[List[PaymentData], List[str]]:
        """Validate payment data and return valid payments with warnings"""
        valid_payments = []
        warnings = []
        
        for i, payment in enumerate(payments):
            payment_warnings = []
            
            # Check required fields
            if not payment.customer_name:
                payment_warnings.append("Missing customer name")
            
            if not payment.date:
                payment_warnings.append("Missing or invalid date")
            
            if not payment.project_name:
                payment_warnings.append("Missing project name")
            
            if payment.amount <= 0:
                payment_warnings.append("Invalid amount")
            
            if payment_warnings:
                warnings.append(f"Row {i+1}: {', '.join(payment_warnings)}")
            else:
                valid_payments.append(payment)
        
        return valid_payments, warnings
    
    def get_available_sheets(self, xlsx_path: str) -> List[str]:
        """Get list of available sheets in XLSX file"""
        try:
            # First check if file exists and is readable
            if not os.path.exists(xlsx_path):
                logger.error(f"File does not exist: {xlsx_path}")
                return []
            
            # Check file size
            file_size = os.path.getsize(xlsx_path)
            if file_size == 0:
                logger.error(f"File is empty: {xlsx_path}")
                return []
            
            # Try different engines in order of preference
            engines = ['openpyxl', 'xlrd']
            
            for engine in engines:
                try:
                    xl_file = pd.ExcelFile(xlsx_path, engine=engine)
                    logger.info(f"Successfully opened Excel file with engine: {engine}")
                    return xl_file.sheet_names
                except Exception as engine_error:
                    logger.warning(f"Engine {engine} failed: {engine_error}")
                    continue
            
            # If all engines fail, try to read as CSV
            logger.warning("All Excel engines failed, file might not be a valid Excel file")
            return []
            
        except Exception as e:
            logger.error(f"Failed to read XLSX sheets: {e}")
            return []
    
    def detect_file_format(self, file_path: str) -> str:
        """Detect file format based on extension"""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension == '.csv':
            return 'csv'
        elif extension in ['.xlsx', '.xls']:
            return 'xlsx'
        elif extension == '.json':
            return 'json'
        else:
            raise ValueError(f"Unsupported file format: {extension}")
    
    def validate_excel_file(self, file_path: str) -> tuple[bool, str]:
        """Validate if an Excel file is readable"""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return False, "Dosya bulunamadı."
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False, "Dosya boş."
            
            # Check file signature for Excel files
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(8)
                    # XLSX files start with ZIP signature
                    if not header[:4] == b'PK\x03\x04':
                        return False, "Dosya geçerli bir Excel dosyası değil. Lütfen .xlsx formatında kaydedin."
            except Exception:
                return False, "Dosya okunamadı."
            
            # Try to open with pandas
            engines = ['openpyxl', 'xlrd']
            for engine in engines:
                try:
                    pd.read_excel(file_path, engine=engine, nrows=1)  # Just read first row
                    return True, f"Dosya {engine} motoru ile başarıyla okunabilir."
                except Exception as e:
                    continue
            
            return False, "Dosya hiçbir Excel motoruyla okunamadı. CSV formatında kaydetmeyi deneyin."
            
        except Exception as e:
            return False, f"Dosya doğrulama hatası: {str(e)}"

# Convenience functions
def import_payments(file_path: str, sheet_name: Optional[str] = None) -> List[PaymentData]:
    """Import payments from file with automatic format detection"""
    importer = DataImporter()
    file_format = importer.detect_file_format(file_path)
    
    if file_format == 'csv':
        return importer.import_csv(file_path)
    elif file_format == 'xlsx':
        return importer.import_xlsx(file_path, sheet_name)
    elif file_format == 'json':
        return importer.import_json(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_format}")

def validate_payment_data(payments: List[PaymentData]) -> Tuple[List[PaymentData], List[str]]:
    """Validate payment data"""
    importer = DataImporter()
    return importer.validate_data(payments)
