#!/usr/bin/env python3
"""
CRM Export File Processor
Automatically processes CRM export files (CSV or Excel) containing payment data.
Handles flexible column arrangements and auto-detects columns by name.
"""

import pandas as pd
import sys
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crm_processor.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CRMProcessor:
    """Processes CRM export files with flexible column detection"""
    
    def __init__(self):
        # Define expected columns with multiple possible names
        self.column_mappings = {
            'date': {
                'primary': 'Tarih',
                'alternatives': [
                    'Date', 'DATE', 'tarih', 'TARIH',
                    'Ödeme Tarihi', 'Ödeme Tarih', 'Payment Date',
                    'İşlem Tarihi', 'Transaction Date', 'Tarih (Ödeme)'
                ]
            },
            'customer_name': {
                'primary': 'Müşteri Adı Soyadı',
                'alternatives': [
                    'Müşteri', 'Customer', 'CUSTOMER', 'müşteri',
                    'Ad Soyad', 'Adı Soyadı', 'Name', 'NAME',
                    'Müşteri Adı', 'Client Name', 'İsim', 'isim',
                    'Müşteri Bilgisi', 'Customer Info'
                ]
            },
            'project_name': {
                'primary': 'Proje Adı',
                'alternatives': [
                    'Proje', 'Project', 'PROJECT', 'proje',
                    'Proje Adı', 'Project Name', 'Proje Kodu',
                    'Project Code', 'Proje Bilgisi', 'Project Info',
                    'PROJECT_B', 'PROJECT_A', 'Model Sanayi', 'Model Kuyum'
                ]
            },
            'amount': {
                'primary': 'Ödenen Tutar',
                'alternatives': [
                    'Tutar', 'Amount', 'AMOUNT', 'tutar',
                    'Ödenen Tutar', 'Paid Amount', 'Payment Amount',
                    'Miktar', 'Para', 'Money', 'Tutar (TL)',
                    'Tutar (USD)', 'Amount (TL)', 'Amount (USD)',
                    'Ödenen Miktar', 'Paid Sum', 'Toplam Tutar'
                ]
            },
            'currency': {
                'primary': 'Ödenen Döviz',
                'alternatives': [
                    'Döviz', 'Currency', 'CURRENCY', 'döviz',
                    'Ödenen Döviz', 'Payment Currency', 'Para Birimi',
                    'Currency Type', 'Döviz Türü', 'Para Cinsi',
                    'TL', 'USD', 'EUR', 'TRY', 'Turkish Lira'
                ]
            },
            'payment_channel': {
                'primary': 'Ödeme Kanalı',
                'alternatives': [
                    'Kanal', 'Channel', 'CHANNEL', 'kanal',
                    'Ödeme Kanalı', 'Payment Channel', 'Payment Method',
                    'Ödeme Yöntemi', 'Payment Type', 'Ödeme Türü',
                    'Hesap', 'Account', 'Hesap Adı', 'Account Name',
                    'Banka', 'Bank', 'Yapı Kredi', 'Garanti', 'İş Bankası',
                    'Çarşı', 'LOCATION_B', 'LOCATION_C', 'Kasa', 'Nakit'
                ]
            }
        }
        
        # Payment channel normalization
        self.channel_mappings = {
            'Yapı Kredi TL': 'Yapı Kredi TL',
            'Yapı Kredi USD': 'Yapı Kredi USD',
            'Çarşı USD': 'Çarşı USD',
            'LOCATION_B USD': 'LOCATION_B USD',
            'LOCATION_C Kasa': 'LOCATION_C Kasa',
            'Garanti TL': 'Garanti TL',
            'İş Bankası TL': 'İş Bankası TL',
            'Nakit': 'Nakit',
            'Çek': 'Çek',
            'Havale': 'Havale',
            'Transfer': 'Transfer'
        }
    
    def detect_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Auto-detect columns by name with flexible matching
        Returns mapping of standard names to actual column names
        """
        detected_columns = {}
        available_columns = [col.strip() for col in df.columns]
        
        logger.info(f"Available columns: {available_columns}")
        
        for field_name, field_info in self.column_mappings.items():
            found_column = None
            
            # First try exact match with primary name
            if field_info['primary'] in available_columns:
                found_column = field_info['primary']
            else:
                # Try alternatives with case-insensitive matching
                for alt in field_info['alternatives']:
                    for col in available_columns:
                        if col.lower() == alt.lower():
                            found_column = col
                            break
                    if found_column:
                        break
                
                # Try partial matching for complex cases
                if not found_column:
                    for alt in field_info['alternatives']:
                        for col in available_columns:
                            if alt.lower() in col.lower() or col.lower() in alt.lower():
                                found_column = col
                                break
                        if found_column:
                            break
            
            if found_column:
                detected_columns[field_name] = found_column
                logger.info(f"Detected {field_name}: '{found_column}'")
            else:
                logger.warning(f"Could not detect column for {field_name}")
        
        return detected_columns
    
    def validate_required_columns(self, detected_columns: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Validate that all required columns are detected"""
        required_fields = ['date', 'customer_name', 'project_name', 'amount', 'currency', 'payment_channel']
        missing_fields = []
        
        for field in required_fields:
            if field not in detected_columns:
                missing_fields.append(field)
        
        if missing_fields:
            error_msg = f"Missing required columns: {', '.join(missing_fields)}"
            logger.error(error_msg)
            return False, missing_fields
        
        return True, []
    
    def normalize_data(self, df: pd.DataFrame, detected_columns: Dict[str, str]) -> pd.DataFrame:
        """Normalize and clean the data"""
        normalized_df = df.copy()
        
        # Rename columns to standard names
        column_rename = {v: k for k, v in detected_columns.items()}
        normalized_df = normalized_df.rename(columns=column_rename)
        
        # Clean and normalize data
        for col in normalized_df.columns:
            if normalized_df[col].dtype == 'object':
                normalized_df[col] = normalized_df[col].astype(str).str.strip()
        
        # Normalize payment channels
        if 'payment_channel' in normalized_df.columns:
            normalized_df['payment_channel'] = normalized_df['payment_channel'].apply(
                self.normalize_payment_channel
            )
        
        # Normalize currency
        if 'currency' in normalized_df.columns:
            normalized_df['currency'] = normalized_df['currency'].apply(
                self.normalize_currency
            )
        
        # Parse dates
        if 'date' in normalized_df.columns:
            normalized_df['date'] = normalized_df['date'].apply(self.parse_date)
        
        # Parse amounts
        if 'amount' in normalized_df.columns:
            normalized_df['amount'] = normalized_df['amount'].apply(self.parse_amount)
        
        return normalized_df
    
    def normalize_payment_channel(self, channel: str) -> str:
        """Normalize payment channel names"""
        if pd.isna(channel) or channel == '':
            return 'Bilinmeyen'
        
        channel_str = str(channel).strip()
        
        # Try exact match first
        for standard, variations in self.channel_mappings.items():
            if channel_str == standard:
                return standard
        
        # Try partial matching
        for standard, variations in self.channel_mappings.items():
            if any(var.lower() in channel_str.lower() for var in [standard] + [variations]):
                return standard
        
        # Enhanced keyword matching with robust Turkish character handling
        channel_lower = channel_str.lower()
        
        # LOCATION_B detection
        if any(keyword in channel_lower for keyword in ['LOCATION_B', 'kuyumcu kent', 'kuyumcu_kent']):
            if 'usd' in channel_lower or 'dolar' in channel_lower:
                return 'LOCATION_B USD'
            else:
                return 'LOCATION_B'
        
        # ÇARŞI detection with multiple character encodings
        elif any(keyword in channel_lower for keyword in [
            'çarşı', 'carsi', 'çarþi', 'carþi', 'carşi', 'çarsi'
        ]):
            if 'usd' in channel_lower or 'dolar' in channel_lower:
                return 'ÇARŞI USD'
            else:
                return 'ÇARŞI'
        
        # YAPI KREDI detection
        elif any(keyword in channel_lower for keyword in ['yapı kredi', 'yapi kredi', 'yapikredý']):
            if 'usd' in channel_lower or 'dolar' in channel_lower:
                return 'YAPI KREDİ USD'
            else:
                return 'YAPI KREDİ TL'
        
        # OFİS/KASA detection
        elif any(keyword in channel_lower for keyword in ['LOCATION_C', 'ofiş', 'ofýs', 'kasa', 'office']):
            return 'OFİS KASA'
        
        # Other bank detections
        elif 'garanti' in channel_lower:
            return 'GARANTİ TL'
        elif any(keyword in channel_lower for keyword in ['iş bankası', 'isbank', 'iş bank']):
            return 'İŞ BANKASI TL'
        
        # NAKİT detection
        elif any(keyword in channel_lower for keyword in ['nakit', 'nakiş', 'nakýt', 'cash']):
            return 'NAKİT'
        
        # ÇEK detection
        elif any(keyword in channel_lower for keyword in ['çek', 'cek', 'check']):
            return 'ÇEK'
        
        # HAVALE detection
        elif any(keyword in channel_lower for keyword in ['havale', 'transfer', 'banka']):
            return 'HAVALE'
        
        return channel_str  # Return original if no match found
    
    def normalize_currency(self, currency: str) -> str:
        """Normalize currency names"""
        if pd.isna(currency) or currency == '':
            return 'TL'
        
        currency_str = str(currency).strip().upper()
        
        if currency_str in ['TL', 'TRY', 'TURKISH LIRA', 'TÜRK LİRASI']:
            return 'TL'
        elif currency_str in ['USD', 'US DOLLAR', 'DOLAR', 'DOLAR']:
            return 'USD'
        elif currency_str in ['EUR', 'EURO', 'AVRO']:
            return 'EUR'
        else:
            return currency_str
    
    def parse_date(self, date_value: Any) -> Optional[datetime]:
        """Parse date from various formats"""
        if pd.isna(date_value) or date_value == '':
            return None
        
        if isinstance(date_value, datetime):
            return date_value
        
        date_str = str(date_value).strip()
        
        # Common date formats
        date_formats = [
            '%Y-%m-%d',
            '%d.%m.%Y',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d.%m.%y',
            '%d/%m/%y',
            '%d-%m-%y',
            '%Y-%m-%d %H:%M:%S',
            '%d.%m.%Y %H:%M:%S',
            '%d/%m/%Y %H:%M:%S'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_value}")
        return None
    
    def parse_amount(self, amount_value: Any) -> float:
        """Parse amount from various formats"""
        if pd.isna(amount_value) or amount_value == '':
            return 0.0
        
        if isinstance(amount_value, (int, float)):
            return float(amount_value)
        
        amount_str = str(amount_value).strip()
        
        # Remove common separators and currency symbols
        amount_str = re.sub(r'[,\s₺$€]', '', amount_str)
        
        # Handle empty or null values
        if not amount_str or amount_str.lower() in ['nan', 'none', 'null', '']:
            return 0.0
        
        try:
            return float(amount_str)
        except ValueError:
            logger.warning(f"Could not parse amount: {amount_value}")
            return 0.0
    
    def process_file(self, file_path: str) -> Tuple[bool, pd.DataFrame, List[str]]:
        """
        Process a CRM export file
        Returns: (success, processed_dataframe, error_messages)
        """
        try:
            logger.info(f"Processing file: {file_path}")
            
            # Read file based on extension
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.csv':
                # Try different encodings
                for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        logger.info(f"Successfully read CSV with encoding: {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ValueError("Could not read CSV file with any supported encoding")
            
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path, engine='openpyxl')
                logger.info("Successfully read Excel file")
            
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
            
            logger.info(f"File loaded with {len(df)} rows and {len(df.columns)} columns")
            
            # Detect columns
            detected_columns = self.detect_columns(df)
            
            # Validate required columns
            is_valid, missing_fields = self.validate_required_columns(detected_columns)
            
            if not is_valid:
                error_msg = f"Missing required columns: {', '.join(missing_fields)}"
                logger.error(error_msg)
                return False, pd.DataFrame(), [error_msg]
            
            # Normalize data
            normalized_df = self.normalize_data(df, detected_columns)
            
            # Remove rows with missing critical data
            critical_columns = ['date', 'customer_name', 'amount']
            initial_count = len(normalized_df)
            normalized_df = normalized_df.dropna(subset=critical_columns)
            removed_count = initial_count - len(normalized_df)
            
            if removed_count > 0:
                logger.warning(f"Removed {removed_count} rows with missing critical data")
            
            # Filter out zero amounts
            normalized_df = normalized_df[normalized_df['amount'] > 0]
            
            logger.info(f"Successfully processed {len(normalized_df)} valid payment records")
            
            return True, normalized_df, []
            
        except Exception as e:
            error_msg = f"Error processing file {file_path}: {str(e)}"
            logger.error(error_msg)
            return False, pd.DataFrame(), [error_msg]
    
    def generate_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary statistics for the processed data"""
        if df.empty:
            return {}
        
        summary = {
            'total_records': len(df),
            'total_amount': df['amount'].sum(),
            'date_range': {
                'start': df['date'].min().strftime('%Y-%m-%d') if not df['date'].isna().all() else None,
                'end': df['date'].max().strftime('%Y-%m-%d') if not df['date'].isna().all() else None
            },
            'currencies': df['currency'].value_counts().to_dict(),
            'payment_channels': df['payment_channel'].value_counts().to_dict(),
            'projects': df['project_name'].value_counts().to_dict(),
            'customers': len(df['customer_name'].unique())
        }
        
        return summary
    
    def export_processed_data(self, df: pd.DataFrame, output_path: str, format: str = 'csv') -> bool:
        """Export processed data to file"""
        try:
            if format.lower() == 'csv':
                df.to_csv(output_path, index=False, encoding='utf-8')
            elif format.lower() == 'excel':
                df.to_excel(output_path, index=False, engine='openpyxl')
            else:
                raise ValueError(f"Unsupported output format: {format}")
            
            logger.info(f"Data exported to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            return False

def main():
    """Main function for command line usage"""
    if len(sys.argv) < 2:
        print("Usage: python crm_processor.py <input_file> [output_file]")
        print("Example: python crm_processor.py crm_export.csv processed_data.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'processed_crm_data.csv'
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)
    
    # Process the file
    processor = CRMProcessor()
    success, processed_df, errors = processor.process_file(input_file)
    
    if not success:
        print("❌ Processing failed!")
        for error in errors:
            print(f"   {error}")
        sys.exit(1)
    
    if processed_df.empty:
        print("⚠️ No valid data found in the file")
        sys.exit(1)
    
    # Generate and display summary
    summary = processor.generate_summary(processed_df)
    print("\n📊 Processing Summary:")
    print(f"   Total Records: {summary['total_records']}")
    print(f"   Total Amount: {summary['total_amount']:,.2f}")
    print(f"   Date Range: {summary['date_range']['start']} to {summary['date_range']['end']}")
    print(f"   Currencies: {summary['currencies']}")
    print(f"   Payment Channels: {summary['payment_channels']}")
    print(f"   Projects: {summary['projects']}")
    print(f"   Unique Customers: {summary['customers']}")
    
    # Export processed data
    if processor.export_processed_data(processed_df, output_file):
        print(f"\n✅ Data successfully exported to: {output_file}")
    else:
        print("\n❌ Failed to export data")
        sys.exit(1)

if __name__ == "__main__":
    main()
