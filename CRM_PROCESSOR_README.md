# CRM Export Processor

A flexible Python program that automatically processes CRM export files (CSV or Excel) containing payment data. The program features intelligent column detection, data normalization, and comprehensive error handling.

## 🚀 Features

### ✅ **Flexible Column Detection**
- **Auto-detects columns by name** regardless of position
- **Handles case sensitivity** and whitespace variations
- **Supports multiple naming conventions** (Turkish/English)
- **Robust pattern matching** for complex column names

### 📊 **Supported Data Fields**
- **Date**: `Tarih`, `Date`, `Payment Date`, `İşlem Tarihi`
- **Customer**: `Müşteri Adı Soyadı`, `Customer Name`, `Ad Soyad`
- **Project**: `Proje Adı`, `Project Name`, `Proje Kodu`
- **Amount**: `Ödenen Tutar`, `Amount`, `Tutar (TL)`
- **Currency**: `Ödenen Döviz`, `Currency`, `Para Birimi`
- **Payment Channel**: `Ödeme Kanalı`, `Payment Method`, `Hesap Adı`

### 🔧 **Data Processing**
- **Multiple date formats** support
- **Currency normalization** (TL, USD, EUR)
- **Payment channel mapping** to standard names
- **Amount parsing** with various separators
- **Data validation** and cleaning

### 📈 **Output Options**
- **CSV export** with UTF-8 encoding
- **Excel export** with formatting
- **Comprehensive summary** statistics
- **Detailed logging** for debugging

## 🛠️ Installation

### Requirements
- Python 3.8+
- pandas
- openpyxl (for Excel support)

### Install Dependencies
```bash
pip install pandas openpyxl
```

## 📖 Usage

### Command Line Interface

#### Basic Usage
```bash
python crm_processor.py input_file.csv [output_file.csv]
```

#### Examples
```bash
# Process CSV file
python crm_processor.py crm_export.csv processed_data.csv

# Process Excel file
python crm_processor.py crm_export.xlsx processed_data.xlsx

# Auto-generate output filename
python crm_processor.py crm_export.csv
```

### GUI Interface

#### Launch GUI
```bash
python crm_processor_gui.py
```

#### GUI Features
- **File browser** for easy file selection
- **Real-time processing** with progress bar
- **Data preview** in table format
- **Summary statistics** display
- **Export functionality** with format selection

### Python API

#### Basic Usage
```python
from crm_processor import CRMProcessor

# Create processor instance
processor = CRMProcessor()

# Process file
success, processed_df, errors = processor.process_file('crm_export.csv')

if success:
    print(f"Processed {len(processed_df)} records")
    
    # Generate summary
    summary = processor.generate_summary(processed_df)
    print(f"Total amount: {summary['total_amount']:,.2f}")
    
    # Export data
    processor.export_processed_data(processed_df, 'output.csv')
else:
    print("Processing failed:", errors)
```

## 🧪 Testing

### Run Test Suite
```bash
python test_crm_processor.py
```

### Test Cases
The test suite includes:
- **Standard format** files
- **Alternative column names**
- **Mixed case** and whitespace
- **Missing required columns**
- **Complex data formats**

## 📊 Supported File Formats

### Input Formats
- **CSV**: Comma-separated values
- **Excel**: .xlsx and .xls files
- **Encodings**: UTF-8, Latin-1, CP1252, ISO-8859-1

### Output Formats
- **CSV**: UTF-8 encoded
- **Excel**: .xlsx with formatting

## 🔍 Column Detection Examples

### Date Columns
```
✅ Tarih
✅ Date
✅ Payment Date
✅ İşlem Tarihi
✅ tarih (case insensitive)
```

### Customer Columns
```
✅ Müşteri Adı Soyadı
✅ Customer Name
✅ Ad Soyad
✅ MÜŞTERİ ADI SOYADI (case insensitive)
```

### Amount Columns
```
✅ Ödenen Tutar
✅ Amount
✅ Tutar (TL)
✅ Ödenen Tutar(Σ:11,059,172.00) (with summary)
```

## 🏦 Payment Channel Mapping

### Standard Channels
- **Yapı Kredi TL** / **Yapı Kredi USD**
- **Çarşı USD** / **Kuyumcukent USD**
- **Ofis Kasa** / **Garanti TL**
- **İş Bankası TL** / **Nakit**
- **Çek** / **Havale**

### Auto-Detection
The processor automatically maps various channel names:
```
"Yapı Kredi Bankası TL" → "Yapı Kredi TL"
"Çarşı Döviz Hesabı" → "Çarşı USD"
"Kuyumcukent USD Hesabı" → "Kuyumcukent USD"
```

## 📈 Summary Statistics

The processor generates comprehensive summaries including:

### Basic Statistics
- Total number of records
- Total amount processed
- Number of unique customers

### Distribution Analysis
- Currency distribution
- Payment channel breakdown
- Project-wise distribution
- Date range analysis

### Example Summary
```
📊 PROCESSING SUMMARY
==================================================

📈 Basic Statistics:
   Total Records: 1,250
   Total Amount: 2,500,000.00
   Unique Customers: 150

📅 Date Range:
   Start: 2024-01-01
   End: 2024-12-31

💰 Currency Distribution:
   TL: 1,000 records
   USD: 250 records

🏦 Payment Channels:
   Yapı Kredi TL: 500 records
   Çarşı USD: 300 records
   Kuyumcukent USD: 200 records
```

## 🚨 Error Handling

### Missing Columns
```
❌ Missing required columns: project_name, payment_channel
```

### Data Validation
```
⚠️ Row 5: Invalid amount format
⚠️ Row 12: Could not parse date
```

### File Format Issues
```
❌ Unsupported file format: .pdf
❌ Could not read CSV file with any supported encoding
```

## 📝 Logging

The processor provides detailed logging:

### Log Levels
- **INFO**: Processing progress and results
- **WARNING**: Data validation issues
- **ERROR**: Critical errors and failures

### Log Output
- **Console**: Real-time processing updates
- **File**: `crm_processor.log` for detailed logs

## 🔧 Configuration

### Custom Column Mappings
```python
processor = CRMProcessor()

# Add custom column mapping
processor.column_mappings['custom_field'] = {
    'primary': 'Custom Field',
    'alternatives': ['Custom', 'Field', 'CustomField']
}
```

### Custom Channel Mappings
```python
# Add custom payment channel
processor.channel_mappings['Custom Bank'] = 'Custom Bank'
```

## 📚 Examples

### Example 1: Standard CRM Export
```csv
Tarih,Müşteri Adı Soyadı,Proje Adı,Ödenen Tutar,Ödenen Döviz,Ödeme Kanalı
2024-01-15,Ahmet Yılmaz,MSM,15000.50,TL,Yapı Kredi TL
2024-01-16,Fatma Demir,MKM,25000.00,USD,Çarşı USD
```

### Example 2: Alternative Format
```csv
Payment Date,Customer Name,Project Code,Amount (TL),Currency Type,Payment Method
2024-01-18,Ali Veli,Model Sanayi Merkezi,12000.00,Turkish Lira,Garanti TL
2024-01-19,Zeynep Arslan,Model Kuyum Merkezi,30000.50,Turkish Lira,Ofis Kasa
```

### Example 3: Complex Format
```csv
İşlem Tarihi,Müşteri Bilgisi,Proje Kodu,Tutar (TL),Para Birimi,Hesap Adı
15.01.2024,Musa Özdoğan,Model Sanayi Merkezi,"25,000.50",Türk Lirası,Yapı Kredi Bankası TL
16/01/2024,Fatma Demir,Model Kuyum Merkezi,"30,000.00",Türk Lirası,Çarşı Döviz Hesabı
```

## 🤝 Contributing

### Adding New Column Mappings
1. Edit `column_mappings` in `CRMProcessor.__init__()`
2. Add new field with primary and alternative names
3. Test with sample data

### Adding New Channel Mappings
1. Edit `channel_mappings` in `CRMProcessor.__init__()`
2. Add standard name and variations
3. Update `normalize_payment_channel()` method

## 📞 Support

### Common Issues
1. **"Missing required columns"**: Check column names match expected patterns
2. **"Could not parse date"**: Verify date format is supported
3. **"Could not parse amount"**: Check amount format and separators

### Debug Mode
Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📄 License

This project is licensed under the MIT License.

---

**🎉 The CRM Processor is ready to handle your CRM export files with maximum flexibility and reliability!**
