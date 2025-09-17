# Tahsilat - Payment Reporting Automation Tool

A desktop application for automated daily and monthly payment report generation for real estate development companies.

## 🚀 Features

### 📊 Data Import
- Supports CSV, XLSX, JSON file formats
- Manual table entry (Excel-like grid)
- Automatic data validation and error checking
- Multi-sheet support (for XLSX)

### 💱 Currency Conversion
- Automatic TL→USD conversion using official TCMB exchange rates
- Uses exchange rate from one day before payment date
- Local JSON caching for performance optimization
- Manual exchange rate entry support

### 💾 Local Storage
- All data stored locally in JSON format
- Daily backup (snapshot) system
- Data recovery and backup management
- Automatic data cleanup

### 📈 Report Generation
- Daily USD distribution (by customer and project)
- Weekly summary (by project)
- Monthly channel distribution (by project and payment channel)
- Daily timeline (daily totals within month)
- Payment type summary (TL and USD totals)

### 📄 Output Formats
- Excel (.xlsx) - Single sheet, formatted tables
- PDF - Professional report format
- Word (.docx) - Editable document format

### 🎯 Smart Detection
- Automatic payment channel detection (from "Account Name")
- Automatic project name grouping
- Currency type and conversion need detection
- Payment type categorization

## 🛠️ Installation

### Requirements
- Python 3.11+
- Windows 10/11 (tested)

### Steps
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

## 📖 Usage

### 1. Data Import
- Click "Select File" button
- Choose CSV, XLSX or JSON file
- Select file format (auto-detected)
- Select sheet for XLSX (if needed)
- Click "Import" button

### 2. Manual Data Entry
- Switch to "Manual Entry" tab
- Enter data in table
- Add new rows with "Add Row"
- Data is automatically saved

### 3. Report Generation
- Select date range
- Choose desired report type:
  - Daily Report - Daily distribution by customer and project
  - Weekly Report - Weekly summary by project
  - Monthly Report - Monthly distribution by channel and project
  - All Reports - All formats (Excel, PDF, Word)

### 4. Data Management
- Refresh - Reload data
- Export - Save data as JSON/CSV
- Daily Backup - Create instant backup

## 📊 Sample Report Formats

### Daily USD Distribution
| Customer | Project | Monday | Tuesday | ... | Total |
|----------|---------|---------|---------|-----|-------|
| John Doe | PROJECT_A | $8,502 | | | $8,502 |

### Monthly Channel Distribution
| Channel | PROJECT_A USD | PROJECT_B USD |
|---------|---------------|---------------|
| BANK_A | $296,556 | |
| OFFICE | $15,000 | $8,501 |

## 🔧 Technical Details

### Project Structure
```
tahsilat/
├── main.py              # Main application entry point
├── ui_main.py           # PySide6 GUI application
├── data_import.py       # Data import module
├── currency.py          # TCMB exchange rate module
├── storage.py           # JSON local storage
├── report_generator.py  # Report generation module
├── requirements.txt     # Python dependencies
├── sample_data.csv      # Sample CSV data
└── README.md           # This file
```

### Supported Data Fields
- Customer Name - Customer information
- Date - Payment date (various formats)
- Project Name - Project information
- Account Name - For payment channel detection
- Amount Paid - Payment amount
- Currency Paid - Currency (TL/USD)
- Exchange Rate - Exchange rate (manual entry)
- Payment Status - Payment status

### Exchange Rate Integration
- TCMB XML API usage
- Daily automatic rate fetching
- Local JSON caching
- Manual rate entry in case of errors

## 🐛 Troubleshooting

### Common Issues
- File cannot be read - Check file format
- Exchange rate cannot be retrieved - Check internet connection
- Report cannot be generated - Check output folder write permissions

### Log Files
The application keeps detailed log records. Check console output in case of errors.

## 📝 License
This project is licensed under the MIT License.

## 🤝 Contributing
1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support
Create an issue for questions or contact support.
