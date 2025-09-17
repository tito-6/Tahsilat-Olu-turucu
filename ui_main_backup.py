"""
Main GUI application using PySide6
Provides desktop interface for payment reporting automation
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QPushButton, QLabel, QLineEdit, QDateEdit, 
    QFileDialog, QMessageBox, QTabWidget, QTableWidget, 
    QTableWidgetItem, QComboBox, QTextEdit, QProgressBar,
    QGroupBox, QSplitter, QHeaderView, QAbstractItemView,
    QMenuBar, QMenu, QStatusBar, QToolBar, QFrame, QScrollArea,
    QCheckBox, QDialog, QListWidget, QListWidgetItem, QCalendarWidget
)
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtCore import Qt, QDate, QThread, Signal, QTimer
from PySide6.QtGui import QAction, QIcon, QFont, QPixmap, QColor

from data_import import DataImporter, PaymentData, validate_payment_data
from storage import PaymentStorage
from report_generator import ReportGenerator, generate_all_reports
from currency import CurrencyConverter
from validation import validator, error_handler, validate_file, validate_dates
from data_validation_dialog import show_validation_dialog
from advanced_filter_dialog import AdvancedFilterDialog
import logging

logger = logging.getLogger(__name__)

class ImportWorker(QThread):
    """Worker thread for data import operations"""
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(list, list)  # valid_payments, warnings
    error = Signal(str)
    
    def __init__(self, file_path: str, file_format: str, sheet_name: str = None):
        super().__init__()
        self.file_path = file_path
        self.file_format = file_format
        self.sheet_name = sheet_name
        self.importer = DataImporter()
    
    def run(self):
        try:
            self.status.emit("Dosya okunuyor...")
            self.progress.emit(10)
            
            # Import data based on format
            if self.file_format == 'csv':
                payments = self.importer.import_csv(self.file_path)
            elif self.file_format == 'xlsx':
                payments = self.importer.import_xlsx(self.file_path, self.sheet_name)
            elif self.file_format == 'json':
                payments = self.importer.import_json(self.file_path)
            else:
                raise ValueError(f"Desteklenmeyen dosya formatı: {self.file_format}")
            
            self.progress.emit(50)
            self.status.emit("Veriler doğrulanıyor...")
            
            # Validate data
            valid_payments, warnings = validate_payment_data(payments)
            
            self.progress.emit(100)
            self.status.emit("İçe aktarma tamamlandı")
            
            self.finished.emit(valid_payments, warnings)
            
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.storage = PaymentStorage()
        self.report_generator = ReportGenerator()
        self.currency_converter = CurrencyConverter()
        self.current_payments = []
        
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Tahsilat - Ödeme Raporlama Otomasyonu")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create main content area
        self.create_main_content(main_layout)
        
        # Create status bar
        self.create_status_bar()
        
        # Apply styles
        self.apply_styles()
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('Dosya')
        
        import_action = QAction('Veri İçe Aktar', self)
        import_action.setShortcut('Ctrl+I')
        import_action.triggered.connect(self.import_data)
        file_menu.addAction(import_action)
        
        export_action = QAction('Veri Dışa Aktar', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Çıkış', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Reports menu
        reports_menu = menubar.addMenu('Raporlar')
        
        daily_report_action = QAction('Günlük Rapor', self)
        daily_report_action.triggered.connect(self.generate_daily_report)
        reports_menu.addAction(daily_report_action)
        
        monthly_report_action = QAction('Aylık Rapor', self)
        monthly_report_action.triggered.connect(self.generate_monthly_report)
        reports_menu.addAction(monthly_report_action)
        
        all_reports_action = QAction('Tüm Raporlar', self)
        all_reports_action.triggered.connect(self.generate_all_reports)
        reports_menu.addAction(all_reports_action)
        
        # Tools menu
        tools_menu = menubar.addMenu('Araçlar')
        
        currency_action = QAction('Döviz Kurları', self)
        currency_action.triggered.connect(self.show_currency_rates)
        tools_menu.addAction(currency_action)
        
        snapshot_action = QAction('Günlük Yedekleme', self)
        snapshot_action.triggered.connect(self.create_snapshot)
        tools_menu.addAction(snapshot_action)
        
        # Settings menu
        settings_menu = menubar.addMenu('Ayarlar')
        
        clear_data_action = QAction('Veri Depolamayı Temizle', self)
        clear_data_action.triggered.connect(self.clear_storage_data)
        settings_menu.addAction(clear_data_action)
        
        settings_menu.addSeparator()
        
        # Add PDF export option
        pdf_export_action = QAction('PDF Olarak Dışa Aktar', self)
        pdf_export_action.triggered.connect(self.export_as_pdf)
        settings_menu.addAction(pdf_export_action)
    
    def create_toolbar(self):
        """Create toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Import button
        import_btn = QPushButton("Veri İçe Aktar")
        import_btn.clicked.connect(self.import_data)
        toolbar.addWidget(import_btn)
        
        # Export button
        export_btn = QPushButton("Rapor Oluştur")
        export_btn.clicked.connect(self.generate_all_reports)
        toolbar.addWidget(export_btn)
        
        toolbar.addSeparator()
        
        # Refresh button
        refresh_btn = QPushButton("Yenile")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)
    
    def create_main_content(self, main_layout):
        """Create main content area"""
        # Create splitter for main content
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Data import and controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Data display and reports
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 1000])
    
    def create_left_panel(self):
        """Create left control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # File import section
        import_group = QGroupBox("Veri İçe Aktarma")
        import_layout = QVBoxLayout(import_group)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Dosya yolu seçin...")
        file_layout.addWidget(self.file_path_edit)
        
        browse_btn = QPushButton("Gözat")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        import_layout.addLayout(file_layout)
        
        # File format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["CSV", "XLSX", "JSON"])
        format_layout.addWidget(self.format_combo)
        import_layout.addLayout(format_layout)
        
        # Sheet selection (for XLSX)
        self.sheet_widget = QWidget()
        self.sheet_layout = QHBoxLayout(self.sheet_widget)
        self.sheet_layout.addWidget(QLabel("Sayfa:"))
        self.sheet_combo = QComboBox()
        self.sheet_layout.addWidget(self.sheet_combo)
        self.sheet_widget.setVisible(False)
        import_layout.addWidget(self.sheet_widget)
        
        # Import button
        import_btn = QPushButton("İçe Aktar")
        import_btn.clicked.connect(self.start_import)
        import_layout.addWidget(import_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        import_layout.addWidget(self.progress_bar)
        
        layout.addWidget(import_group)
        
        # Date range selection
        date_group = QGroupBox("Tarih Aralığı")
        date_layout = QGridLayout(date_group)
        
        date_layout.addWidget(QLabel("Başlangıç:"), 0, 0)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))
        self.start_date_edit.setCalendarPopup(True)
        date_layout.addWidget(self.start_date_edit, 0, 1)
        
        date_layout.addWidget(QLabel("Bitiş:"), 1, 0)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        date_layout.addWidget(self.end_date_edit, 1, 1)
        
        layout.addWidget(date_group)
        
        # Report generation
        report_group = QGroupBox("Rapor Oluşturma")
        report_layout = QVBoxLayout(report_group)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.report_format_combo = QComboBox()
        self.report_format_combo.addItems(["Excel (.xlsx)", "PDF (.pdf)", "Word (.docx)", "Tümü"])
        self.report_format_combo.setCurrentIndex(0)  # Default to Excel
        format_layout.addWidget(self.report_format_combo)
        report_layout.addLayout(format_layout)
        
        daily_btn = QPushButton("Günlük Rapor")
        daily_btn.clicked.connect(self.generate_daily_report)
        report_layout.addWidget(daily_btn)
        
        weekly_btn = QPushButton("Haftalık Rapor")
        weekly_btn.clicked.connect(self.generate_weekly_report)
        report_layout.addWidget(weekly_btn)
        
        monthly_btn = QPushButton("Aylık Rapor")
        monthly_btn.clicked.connect(self.generate_monthly_report)
        report_layout.addWidget(monthly_btn)
        
        all_btn = QPushButton("Tüm Raporlar")
        all_btn.clicked.connect(self.generate_all_reports)
        report_layout.addWidget(all_btn)
        
        layout.addWidget(report_group)
        
        # Statistics
        stats_group = QGroupBox("İstatistikler")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(150)
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        
        layout.addWidget(stats_group)
        
        # Stretch to push everything to top
        layout.addStretch()
        
        return panel
    
    def create_right_panel(self):
        """Create right data display panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Data table tab
        # Create data table with advanced features
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.setSortingEnabled(True)
        
        # Hide row headers to avoid duplication with SIRA NO column
        self.data_table.verticalHeader().setVisible(False)
        
        # Enable context menu for advanced features
        self.data_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.data_table.customContextMenuRequested.connect(self.show_table_context_menu)
        self.tab_widget.addTab(self.data_table, "Veri Tablosu")
        
        # Report preview tab with sub-tabs
        self.report_preview_widget = QWidget()
        self.report_preview_layout = QVBoxLayout(self.report_preview_widget)
        
        # Create sub-tab widget for report sheets
        self.report_tabs = QTabWidget()
        self.report_preview_layout.addWidget(self.report_tabs)
        
        # Add control panel for report preview
        self.create_report_preview_controls()
        
        self.tab_widget.addTab(self.report_preview_widget, "Rapor Önizleme")
        self.update_report_preview()
        
        # Currency rates tab (main tab, not child dialog)
        self.currency_tab = self.create_currency_rates_tab()
        self.tab_widget.addTab(self.currency_tab, "Döviz Kurları")
        
        # Manual entry tab
        self.manual_table = QTableWidget()
        self.manual_table.setAlternatingRowColors(True)
        self.manual_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.manual_table.horizontalHeader().setStretchLastSection(True)
        self.tab_widget.addTab(self.manual_table, "Manuel Giriş")
        
        # Setup manual entry table
        self.setup_manual_table()
        
        return panel
    
    def setup_manual_table(self):
        """Setup manual entry table"""
        headers = [
            "Müşteri Adı Soyadı", "Tarih", "Proje Adı", "Hesap Adı",
            "Ödenen Tutar", "Ödenen Döviz", "Ödenen Kur", "Ödeme Durumu"
        ]
        self.manual_table.setColumnCount(len(headers))
        self.manual_table.setHorizontalHeaderLabels(headers)
        
        # Add empty row
        self.manual_table.insertRow(0)
        for col in range(len(headers)):
            self.manual_table.setItem(0, col, QTableWidgetItem(""))
        
        # Add button to save manual entry
        add_row_btn = QPushButton("Satır Ekle")
        add_row_btn.clicked.connect(self.add_manual_row)
        self.manual_table.setCellWidget(0, len(headers), add_row_btn)
    
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Hazır")
    
    def apply_styles(self):
        """Apply custom styles to the application"""
        style = """
        QMainWindow {
            background-color: #f8f9fa;
            color: #212529;
        }
        
        QGroupBox {
            font-weight: bold;
            font-size: 12px;
            color: #495057;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            margin-top: 1ex;
            padding-top: 15px;
            background-color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 8px 0 8px;
            background-color: #f8f9fa;
            color: #495057;
        }
        
        QPushButton {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 11px;
            min-height: 20px;
        }
        QPushButton:hover {
            background-color: #0056b3;
        }
        QPushButton:pressed {
            background-color: #004085;
        }
        QPushButton:disabled {
            background-color: #6c757d;
            color: #adb5bd;
        }
        
        QTableWidget {
            gridline-color: #dee2e6;
            background-color: #ffffff;
            alternate-background-color: #f8f9fa;
            color: #212529;
            border: 1px solid #dee2e6;
            border-radius: 4px;
        }
        QTableWidget::item {
            padding: 8px;
            border-bottom: 1px solid #dee2e6;
        }
        QTableWidget::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        QTableWidget::item:alternate {
            background-color: #f8f9fa;
        }
        
        QHeaderView::section {
            background-color: #e9ecef;
            color: #212529;
            padding: 12px 8px;
            border: 1px solid #dee2e6;
            font-weight: bold;
            font-size: 11px;
            text-align: center;
        }
        QHeaderView::section:horizontal {
            border-right: 1px solid #dee2e6;
            min-height: 30px;
        }
        QHeaderView::section:vertical {
            border-bottom: 1px solid #dee2e6;
            min-width: 50px;
        }
        QHeaderView::section:first {
            background-color: #d1ecf1;
            color: #0c5460;
        }
        
        QLineEdit {
            background-color: #ffffff;
            color: #212529;
            border: 2px solid #ced4da;
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 11px;
        }
        QLineEdit:focus {
            border-color: #007bff;
            outline: none;
        }
        
        QComboBox {
            background-color: #ffffff;
            color: #212529;
            border: 2px solid #ced4da;
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 11px;
            min-height: 20px;
        }
        QComboBox:focus {
            border-color: #007bff;
        }
        QComboBox::drop-down {
            border: none;
            background-color: #ffffff;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #6c757d;
            margin-right: 8px;
        }
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #212529;
            border: 1px solid #ced4da;
            selection-background-color: #e3f2fd;
            selection-color: #1976d2;
        }
        QComboBox QAbstractItemView::item {
            padding: 8px;
            border-bottom: 1px solid #dee2e6;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: #f8f9fa;
        }
        
        QDateEdit {
            background-color: #ffffff;
            color: #212529;
            border: 2px solid #ced4da;
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 11px;
        }
        QDateEdit:focus {
            border-color: #007bff;
        }
        
        QTextEdit {
            background-color: #ffffff;
            color: #212529;
            border: 2px solid #ced4da;
            border-radius: 4px;
            padding: 8px;
            font-size: 11px;
        }
        QTextEdit:focus {
            border-color: #007bff;
        }
        
        QLabel {
            color: #495057;
            font-size: 11px;
        }
        
        QProgressBar {
            border: 2px solid #dee2e6;
            border-radius: 4px;
            text-align: center;
            background-color: #e9ecef;
            color: #495057;
            font-weight: bold;
        }
        QProgressBar::chunk {
            background-color: #28a745;
            border-radius: 2px;
        }
        
        QTabWidget::pane {
            border: 1px solid #dee2e6;
            background-color: #ffffff;
        }
        QTabBar::tab {
            background-color: #e9ecef;
            color: #495057;
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #ffffff;
            color: #007bff;
            border-bottom: 2px solid #007bff;
        }
        QTabBar::tab:hover {
            background-color: #f8f9fa;
        }
        
        QMenuBar {
            background-color: #ffffff;
            color: #495057;
            border-bottom: 1px solid #dee2e6;
        }
        QMenuBar::item {
            padding: 8px 16px;
            background-color: transparent;
        }
        QMenuBar::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        
        QMenu {
            background-color: #ffffff;
            color: #495057;
            border: 1px solid #dee2e6;
        }
        QMenu::item {
            padding: 8px 20px;
        }
        QMenu::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        
        QStatusBar {
            background-color: #f8f9fa;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
        }
        
        QToolBar {
            background-color: #ffffff;
            border-bottom: 1px solid #dee2e6;
            spacing: 3px;
        }
        """
        self.setStyleSheet(style)
    
    def import_data(self):
        """Import data from file"""
        self.browse_file()
    
    def browse_file(self):
        """Browse for file to import"""
        logger.info("Browse file button clicked")
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Dosya Seç", "", 
                "CSV Files (*.csv);;Excel Files (*.xlsx *.xls);;JSON Files (*.json);;All Files (*)"
            )
            if file_path:
                logger.info(f"File selected: {file_path}")
                self.file_path_edit.setText(file_path)
                self.detect_file_format(file_path)
            else:
                logger.info("No file selected")
        except Exception as e:
            logger.error(f"Error in browse_file: {e}")
            QMessageBox.critical(self, "Hata", f"Dosya seçme hatası: {e}")
    
    def detect_file_format(self, file_path: str):
        """Detect file format and update UI accordingly"""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension == '.csv':
            self.format_combo.setCurrentText("CSV")
            self.sheet_widget.setVisible(False)
        elif extension in ['.xlsx', '.xls']:
            self.format_combo.setCurrentText("XLSX")
            self.sheet_widget.setVisible(True)
            self.load_sheet_names(file_path)
        elif extension == '.json':
            self.format_combo.setCurrentText("JSON")
            self.sheet_widget.setVisible(False)
    
    def load_sheet_names(self, file_path: str):
        """Load sheet names for XLSX files"""
        try:
            importer = DataImporter()
            sheets = importer.get_available_sheets(file_path)
            self.sheet_combo.clear()
            self.sheet_combo.addItems(sheets)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Sayfa isimleri yüklenemedi: {e}")
    
    def start_import(self):
        """Start data import process"""
        logger.info("Import button clicked")
        file_path = self.file_path_edit.text()
        logger.info(f"File path: {file_path}")
        
        # Validate file path
        is_valid, error_msg = validate_file(file_path)
        if not is_valid:
            logger.error(f"File validation failed: {error_msg}")
            QMessageBox.warning(self, "Hata", f"Dosya hatası: {error_msg}")
            return
        
        logger.info("File validation passed")
        
        file_format = self.format_combo.currentText().lower()
        sheet_name = self.sheet_combo.currentText() if self.sheet_widget.isVisible() else None
        
        # Validate Excel files before import
        if file_format == 'xlsx':
            from data_import import DataImporter
            importer = DataImporter()
            is_valid, message = importer.validate_excel_file(file_path)
            
            if not is_valid:
                QMessageBox.critical(self, "Excel Dosyası Hatası", 
                                   f"Excel dosyası okunamadı:\n\n{message}\n\n"
                                   "Çözüm önerileri:\n"
                                   "• Dosyayı Excel'de açıp .xlsx formatında yeniden kaydedin\n"
                                   "• CSV formatında kaydetmeyi deneyin\n"
                                   "• Dosyanın bozuk olmadığından emin olun")
                return
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start import worker
        self.import_worker = ImportWorker(file_path, file_format, sheet_name)
        self.import_worker.progress.connect(self.progress_bar.setValue)
        self.import_worker.status.connect(self.status_bar.showMessage)
        self.import_worker.finished.connect(self.on_import_finished)
        self.import_worker.error.connect(self.on_import_error)
        self.import_worker.start()
    
    def on_import_finished(self, valid_payments: List[PaymentData], warnings: List[str]):
        """Handle import completion with duplicate detection"""
        self.progress_bar.setVisible(False)
        
        if not valid_payments:
            if warnings:
                show_validation_dialog(self, [], warnings)
            else:
                QMessageBox.warning(self, "Uyarı", "İçe aktarılacak geçerli veri bulunamadı")
            return
        
        # Check for duplicates
        from data_import import DataImporter
        importer = DataImporter()
        existing_payments = self.storage.get_all_payments()
        unique_payments, duplicates = importer.check_duplicates(valid_payments, existing_payments)
        
        if duplicates:
            # Show duplicate detection dialog
            from duplicate_detection_dialog import show_duplicate_detection_dialog
            selected_duplicates = show_duplicate_detection_dialog(duplicates, self)
            
            # Add selected duplicates back to unique payments
            for duplicate_info in selected_duplicates:
                unique_payments.append(duplicate_info['new_payment'])
        
        # Check for check payments without maturity dates
        check_payments_without_maturity = []
        for payment in unique_payments:
            if payment.is_check_payment and not payment.cek_vade_tarihi:
                check_payments_without_maturity.append(payment)
        
        # Handle missing check maturity dates
        if check_payments_without_maturity:
            from check_maturity_dialog import show_check_maturity_dialog
            
            # Convert payments to dict format for dialog
            check_data = []
            for payment in check_payments_without_maturity:
                check_data.append({
                    'customer_name': payment.customer_name,
                    'project_name': payment.project_name,
                    'date': payment.date,
                    'cek_tutari': payment.cek_tutari,
                    'amount': payment.amount
                })
            
            maturity_dates = show_check_maturity_dialog(check_data, self)
            
            if maturity_dates:
                # Update payments with entered maturity dates
                for i, payment in enumerate(check_payments_without_maturity):
                    if i in maturity_dates:
                        payment.cek_vade_tarihi = maturity_dates[i]
            else:
                # User cancelled, don't import check payments
                unique_payments = [p for p in unique_payments if not (p.is_check_payment and not p.cek_vade_tarihi)]
                if not unique_payments:
                    QMessageBox.information(self, "İptal", "Çek vade tarihleri girilmediği için içe aktarma iptal edildi.")
                    return
        
        # Show validation dialog for all payments (unique + selected duplicates)
        all_payments_to_import = unique_payments
        if warnings or all_payments_to_import:
            show_validation_dialog(self, all_payments_to_import, warnings)
        
        if all_payments_to_import:
            # Add to storage
            self.storage.add_payments(all_payments_to_import)
            
            # Update display
            self.load_data()
            
            # Show summary message
            message = f"{len(all_payments_to_import)} kayıt başarıyla içe aktarıldı"
            if duplicates:
                skipped_duplicates = len(duplicates) - len(selected_duplicates)
                if skipped_duplicates > 0:
                    message += f"\n{skipped_duplicates} tekrarlanan kayıt atlandı"
            if check_payments_without_maturity:
                message += f"\n{len(check_payments_without_maturity)} çek için vade tarihi girildi"
            
            QMessageBox.information(self, "Başarılı", message)
        else:
            QMessageBox.warning(self, "Uyarı", "İçe aktarılacak geçerli veri bulunamadı")
    
    def show_warnings_dialog(self, warnings: List[str]):
        """Show warnings in a professional, scrollable dialog"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Veri İçe Aktarma Uyarıları")
        dialog.setIcon(QMessageBox.Warning)
        
        # Create a scrollable text area for warnings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumSize(600, 400)
        scroll_area.setMaximumSize(800, 600)
        
        # Create text widget for warnings
        text_widget = QTextEdit()
        text_widget.setReadOnly(True)
        text_widget.setPlainText("Uyarılar:\n\n" + "\n".join(warnings))
        text_widget.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                line-height: 1.4;
            }
        """)
        
        scroll_area.setWidget(text_widget)
        
        # Create custom layout
        layout = QVBoxLayout()
        layout.addWidget(scroll_area)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("Kopyala")
        copy_btn.clicked.connect(lambda: self.copy_warnings_to_clipboard(warnings))
        button_layout.addWidget(copy_btn)
        
        button_layout.addStretch()
        
        ok_btn = QPushButton("Tamam")
        ok_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        
        # Set the custom layout
        dialog.setLayout(layout)
        
        # Show dialog
        dialog.exec()
    
    def copy_warnings_to_clipboard(self, warnings: List[str]):
        """Copy warnings to clipboard"""
        from PySide6.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        clipboard.setText("Uyarılar:\n\n" + "\n".join(warnings))
        QMessageBox.information(self, "Kopyalandı", "Uyarılar panoya kopyalandı")
    
    def on_import_error(self, error_msg: str):
        """Handle import error"""
        self.progress_bar.setVisible(False)
        # Use error handler for better error messages
        formatted_error = error_handler.handle_import_error(Exception(error_msg), self.file_path_edit.text())
        QMessageBox.critical(self, "Hata", formatted_error)
    
    def load_data(self):
        """Load data from storage and update display"""
        self.current_payments = self.storage.get_all_payments()
        logger.info(f"Loaded {len(self.current_payments)} payments from storage")
        self.update_data_table()
        self.update_statistics()
        self.update_report_preview()
    
    def update_data_table(self):
        """Update the data table with current payments including conversion details"""
        if not self.current_payments:
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            return
        
        # Define enhanced columns with conversion information
        enhanced_columns = [
            'SIRA NO',
            'Müşteri Adı Soyadı', 
            'Tarih',
            'Proje Adı',
            'Hesap Adı',
            'Ödenen Tutar',
            'Ödenen Döviz', 
            'USD Karşılığı',
            'Döviz Kuru',
            'Tahsilat Şekli',
            'Çek Tutarı',
            'Çek Vade Tarihi',
            'Ödeme Durumu',
            'Ödeme Kanalı'
        ]
        
        self.data_table.setColumnCount(len(enhanced_columns))
        self.data_table.setHorizontalHeaderLabels(enhanced_columns)
        self.data_table.setRowCount(len(self.current_payments))
        
        # Populate table with enhanced data
        for row, payment in enumerate(self.current_payments):
            # SIRA NO
            sira_item = QTableWidgetItem(str(row + 1))
            sira_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 0, sira_item)
            
            # Customer Name
            customer_item = QTableWidgetItem(payment.customer_name)
            customer_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 1, customer_item)
            
            # Date
            date_str = payment.date.strftime("%d.%m.%Y") if payment.date else ""
            date_item = QTableWidgetItem(date_str)
            date_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 2, date_item)
            
            # Project
            project_item = QTableWidgetItem(payment.project_name)
            project_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 3, project_item)
            
            # Account
            account_item = QTableWidgetItem(payment.account_name)
            account_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 4, account_item)
            
            # Original Amount
            amount_item = QTableWidgetItem(f"{payment.amount:,.2f}")
            amount_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 5, amount_item)
            
            # Currency
            currency_item = QTableWidgetItem(payment.currency)
            currency_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 6, currency_item)
            
            # USD Equivalent (calculate if TL)
            if payment.is_tl_payment and payment.date:
                from currency import convert_payment_to_usd
                usd_amount, rate = convert_payment_to_usd(payment.amount, payment.date)
                usd_item = QTableWidgetItem(f"${usd_amount:,.2f}")
                # Highlight TL conversions
                usd_item.setBackground(QColor(230, 243, 255))  # Light blue
                conversion_rate = rate if rate else 0
            else:
                usd_amount = payment.amount
                usd_item = QTableWidgetItem(f"${usd_amount:,.2f}")
                conversion_rate = 1.0
            
            usd_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 7, usd_item)
            
            # Exchange Rate
            rate_item = QTableWidgetItem(f"{conversion_rate:.4f}")
            rate_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 8, rate_item)
            
            # Tahsilat Şekli (Collection Method)
            tahsilat_sekli = getattr(payment, 'tahsilat_sekli', '')
            tahsilat_item = QTableWidgetItem(tahsilat_sekli)
            if tahsilat_sekli.upper() in ['ÇEK', 'CEK', 'CHECK']:
                tahsilat_item.setBackground(QColor(255, 248, 220))  # Light yellow for check payments
                tahsilat_item.setForeground(QColor(184, 134, 11))   # Dark yellow text
            else:
                tahsilat_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 9, tahsilat_item)
            
            # Check Amount
            check_amount = payment.cek_tutari if hasattr(payment, 'cek_tutari') and payment.cek_tutari > 0 else 0
            if check_amount > 0:
                check_item = QTableWidgetItem(f"₺{check_amount:,.2f}")
                check_item.setBackground(QColor(255, 248, 220))  # Light yellow for check payments
            else:
                check_item = QTableWidgetItem("-")
            check_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 10, check_item)
            
            # Check Maturity Date
            if hasattr(payment, 'cek_vade_tarihi') and payment.cek_vade_tarihi:
                maturity_date_str = payment.cek_vade_tarihi.strftime("%d.%m.%Y")
                maturity_item = QTableWidgetItem(maturity_date_str)
                maturity_item.setBackground(QColor(255, 248, 220))  # Light yellow for check payments
            else:
                maturity_item = QTableWidgetItem("-")
            maturity_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 11, maturity_item)
            
            # Payment Status
            status_item = QTableWidgetItem(payment.payment_status)
            status_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 12, status_item)
            
            # Payment Channel
            channel_item = QTableWidgetItem(payment.payment_channel)
            channel_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 13, channel_item)
        
        # Set proper column widths
        self.data_table.setColumnWidth(0, 70)   # SIRA NO
        self.data_table.setColumnWidth(1, 200)  # Customer
        self.data_table.setColumnWidth(2, 100)  # Date
        self.data_table.setColumnWidth(3, 80)   # Project
        self.data_table.setColumnWidth(4, 150)  # Account
        self.data_table.setColumnWidth(5, 120)  # Amount
        self.data_table.setColumnWidth(6, 80)   # Currency
        self.data_table.setColumnWidth(7, 120)  # USD
        self.data_table.setColumnWidth(8, 100)  # Rate
        self.data_table.setColumnWidth(9, 120)  # Tahsilat Şekli
        self.data_table.setColumnWidth(10, 120) # Check Amount
        self.data_table.setColumnWidth(11, 120) # Check Maturity Date
        self.data_table.setColumnWidth(12, 120) # Status
        self.data_table.setColumnWidth(13, 150) # Channel
        
        # Set alternating row colors
        self.data_table.setAlternatingRowColors(True)
        
        # Enable sorting
        self.data_table.setSortingEnabled(True)
    
    def show_table_context_menu(self, position):
        """Show context menu for table operations"""
        menu = QMenu(self)
        
        # Filter actions
        filter_action = menu.addAction("Gelişmiş Filtre")
        filter_action.triggered.connect(self.show_advanced_filter)
        
        clear_filter_action = menu.addAction("Filtreleri Temizle")
        clear_filter_action.triggered.connect(self.clear_filters)
        
        menu.addSeparator()
        
        # Delete actions
        delete_selected_action = menu.addAction("Seçili Satırları Sil")
        delete_selected_action.triggered.connect(self.delete_selected_rows)
        
        menu.addSeparator()
        
        # Export actions
        export_filtered_action = menu.addAction("Filtrelenmiş Veriyi Dışa Aktar")
        export_filtered_action.triggered.connect(self.export_filtered_data)
        
        menu.exec(self.data_table.mapToGlobal(position))
    
    def show_advanced_filter(self):
        """Show advanced filter dialog"""
        dialog = AdvancedFilterDialog(self.current_payments, self)
        if dialog.exec() == QDialog.Accepted:
            filtered_payments = dialog.get_filtered_payments()
            self.display_filtered_data(filtered_payments)
    
    def clear_filters(self):
        """Clear all filters and show all data"""
        self.update_data_table()
        QMessageBox.information(self, "Başarılı", "Tüm filtreler temizlendi")
    
    def delete_selected_rows(self):
        """Delete selected rows with confirmation"""
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen silmek istediğiniz satırları seçin")
            return
        
        reply = QMessageBox.question(
            self, "Onay", 
            f"Seçili {len(selected_rows)} kayıt silinecek.\n"
            "Bu işlem geri alınamaz. Devam etmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Remove payments from storage
            rows_to_delete = sorted(selected_rows, reverse=True)
            for row in rows_to_delete:
                if row < len(self.current_payments):
                    payment_to_delete = self.current_payments[row]
                    self.storage.remove_payment(payment_to_delete)
            
            # Refresh data
            self.load_data()
            QMessageBox.information(self, "Başarılı", f"{len(selected_rows)} kayıt silindi")
    
    def export_filtered_data(self):
        """Export currently displayed (filtered) data"""
        if not self.current_payments:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak veri bulunamadı")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Filtrelenmiş Veriyi Dışa Aktar", 
            f"filtered_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                # Create a simple export of current data
                import pandas as pd
                data = []
                for i, payment in enumerate(self.current_payments, 1):
                    data.append({
                        'SIRA NO': i,
                        'Müşteri Adı Soyadı': payment.customer_name,
                        'Tarih': payment.date.strftime('%d.%m.%Y') if payment.date else '',
                        'Proje Adı': payment.project_name,
                        'Hesap Adı': payment.account_name,
                        'Ödenen Tutar': payment.amount,
                        'Ödenen Döviz': payment.currency,
                        'Ödeme Durumu': payment.payment_status,
                        'Ödeme Kanalı': payment.payment_channel
                    })
                
                df = pd.DataFrame(data)
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "Başarılı", f"Veriler şuraya aktarıldı: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dışa aktarma hatası: {e}")
    
    def display_filtered_data(self, filtered_payments):
        """Display filtered payment data"""
        self.current_payments = filtered_payments
        self.update_data_table()
        self.update_statistics()
    
    def update_statistics(self):
        """Update statistics display"""
        stats = self.storage.get_statistics()
        
        stats_text = f"""📊 VERİ İSTATİSTİKLERİ
{'='*30}

📈 Genel Bilgiler:
   • Toplam Ödeme: {stats['total_payments']:,} kayıt
   • Toplam TL Tutar: {stats['total_amount_tl']:,.2f} TL
   • Toplam USD Tutar: {stats['total_amount_usd']:,.2f} USD

🏢 Proje Bilgileri:
   • Proje Sayısı: {stats['projects']} proje
   • Müşteri Sayısı: {stats['customers']} müşteri
   • Kanal Sayısı: {stats['channels']} kanal
        """
        
        if stats['date_range']:
            stats_text += f"""
📅 Tarih Aralığı:
   • Başlangıç: {stats['date_range']['start']}
   • Bitiş: {stats['date_range']['end']}
            """
        
        self.stats_text.setPlainText(stats_text.strip())
    
    def refresh_data(self):
        """Refresh data from storage"""
        self.load_data()
        self.status_bar.showMessage("Veriler yenilendi")
    
    def add_manual_row(self):
        """Add new row to manual entry table"""
        row_count = self.manual_table.rowCount()
        self.manual_table.insertRow(row_count)
        
        # Copy format from first row
        for col in range(self.manual_table.columnCount() - 1):  # Exclude button column
            self.manual_table.setItem(row_count, col, QTableWidgetItem(""))
    
    def generate_daily_report(self):
        """Generate daily report"""
        self.generate_report("daily")
    
    def generate_weekly_report(self):
        """Generate weekly report"""
        self.generate_report("weekly")
    
    def generate_monthly_report(self):
        """Generate monthly report"""
        self.generate_report("monthly")
    
    def generate_all_reports(self):
        """Generate all reports"""
        self.generate_report("all")
    
    def generate_report(self, report_type: str):
        """Generate specified report type"""
        if not self.current_payments:
            QMessageBox.warning(self, "Uyarı", "Rapor oluşturmak için veri bulunamadı")
            return
        
        start_date = self.start_date_edit.date().toPython()
        end_date = self.end_date_edit.date().toPython()
        
        # Convert to datetime for consistent handling
        import datetime as dt_module
        if isinstance(start_date, dt_module.date) and not isinstance(start_date, dt_module.datetime):
            start_date = dt_module.datetime.combine(start_date, dt_module.datetime.min.time())
        if isinstance(end_date, dt_module.date) and not isinstance(end_date, dt_module.datetime):
            end_date = dt_module.datetime.combine(end_date, dt_module.datetime.min.time())
        
        # Validate date range
        is_valid, error_msg = validate_dates(start_date, end_date)
        if not is_valid:
            QMessageBox.warning(self, "Hata", f"Tarih aralığı hatası: {error_msg}")
            return
        
        # Filter payments by date range
        filtered_payments = [
            p for p in self.current_payments 
            if p.date and start_date <= p.date <= end_date
        ]
        
        if not filtered_payments:
            QMessageBox.warning(self, "Uyarı", "Seçilen tarih aralığında veri bulunamadı")
            return
        
        try:
            # Get selected format
            selected_format = self.report_format_combo.currentText()
            
            if selected_format == "Tümü" or report_type == "all":
                # Generate all formats
                output_dir = QFileDialog.getExistingDirectory(self, "Rapor Klasörü Seç")
                if output_dir:
                    reports = generate_all_reports(filtered_payments, start_date, end_date, output_dir)
                    QMessageBox.information(self, "Başarılı", f"Tüm formatlar oluşturuldu:\n{chr(10).join(reports.values())}")
            else:
                # Generate single format based on selection
                if selected_format.startswith("Excel"):
                    extension = ".xlsx"
                    file_filter = "Excel Files (*.xlsx)"
                elif selected_format.startswith("PDF"):
                    extension = ".pdf"
                    file_filter = "PDF Files (*.pdf)"
                elif selected_format.startswith("Word"):
                    extension = ".docx"
                    file_filter = "Word Files (*.docx)"
                else:
                    extension = ".xlsx"
                    file_filter = "Excel Files (*.xlsx)"
                
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Rapor Kaydet", f"tahsilat_raporu_{report_type}{extension}",
                    file_filter
                )
                if file_path:
                    if extension == ".xlsx":
                        self.report_generator.export_to_excel(filtered_payments, start_date, end_date, file_path)
                    elif extension == ".pdf":
                        self.report_generator.export_to_pdf(filtered_payments, start_date, end_date, file_path)
                    elif extension == ".docx":
                        self.report_generator.export_to_word(filtered_payments, start_date, end_date, file_path)
                    
                    QMessageBox.information(self, "Başarılı", f"Rapor oluşturuldu: {file_path}")
        
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Rapor oluşturma hatası: {e}")
    
    def export_data(self):
        """Export data to external file"""
        if not self.current_payments:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak veri bulunamadı")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Veri Dışa Aktar", "tahsilat_veri.json",
            "JSON Files (*.json);;CSV Files (*.csv)"
        )
        if file_path:
            try:
                self.storage.export_data(file_path, Path(file_path).suffix[1:])
                QMessageBox.information(self, "Başarılı", f"Veri dışa aktarıldı: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dışa aktarma hatası: {e}")
    
    def create_currency_rates_tab(self):
        """Create the main currency rates tab"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Title section
        title_layout = QHBoxLayout()
        title_label = QLabel("TCMB Döviz Kurları Takvimi")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #1976d2;
                background: white;
                padding: 15px;
                border-radius: 8px;
                border: 2px solid #e3f2fd;
                margin: 10px;
            }
        """)
        title_layout.addWidget(title_label)
        layout.addLayout(title_layout)
        
        # Main content splitter
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # Left panel - Controls
        left_panel = self.create_currency_control_panel()
        main_splitter.addWidget(left_panel)
        
        # Right panel - Calendar and rates
        right_panel = self.create_currency_display_panel()
        main_splitter.addWidget(right_panel)
        
        main_splitter.setSizes([400, 800])
        
        # Status and progress
        status_layout = QVBoxLayout()
        
        self.currency_progress_bar = QProgressBar()
        self.currency_progress_bar.setVisible(False)
        status_layout.addWidget(self.currency_progress_bar)
        
        self.currency_status_label = QLabel("Hazır")
        self.currency_status_label.setStyleSheet("""
            QLabel {
                background-color: #d4edda;
                color: #155724;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #c3e6cb;
                margin: 5px;
            }
        """)
        status_layout.addWidget(self.currency_status_label)
        
        layout.addLayout(status_layout)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Kurları Yenile")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #218838);
                color: white;
                font-weight: bold;
                padding: 12px 24px;
                border-radius: 8px;
                border: none;
                margin: 5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34ce57, stop:1 #28a745);
            }
        """)
        refresh_btn.clicked.connect(self.refresh_currency_rates)
        
        export_btn = QPushButton("Excel'e Aktar")
        export_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #17a2b8, stop:1 #138496);
                color: white;
                font-weight: bold;
                padding: 12px 24px;
                border-radius: 8px;
                border: none;
                margin: 5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #20c0d7, stop:1 #17a2b8);
            }
        """)
        export_btn.clicked.connect(self.export_currency_rates)
        
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(export_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Initialize currency data
        self.currency_rates_data = {}
        self.load_cached_currency_rates()
        
        return tab_widget
    
    def create_currency_control_panel(self):
        """Create the currency control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Date range selection
        date_group = QGroupBox("Tarih Aralığı Seçimi")
        date_layout = QVBoxLayout(date_group)
        
        # Start date
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Başlangıç:"))
        self.currency_start_date = QDateEdit()
        self.currency_start_date.setDate(QDate.currentDate().addMonths(-1))
        self.currency_start_date.setCalendarPopup(True)
        self.currency_start_date.setStyleSheet("""
            QDateEdit {
                padding: 8px;
                border: 2px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                font-size: 12px;
                font-weight: bold;
            }
            QDateEdit:focus {
                border-color: #007bff;
            }
        """)
        start_layout.addWidget(self.currency_start_date)
        date_layout.addLayout(start_layout)
        
        # End date
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("Bitiş:"))
        self.currency_end_date = QDateEdit()
        self.currency_end_date.setDate(QDate.currentDate())
        self.currency_end_date.setCalendarPopup(True)
        self.currency_end_date.setStyleSheet(self.currency_start_date.styleSheet())
        end_layout.addWidget(self.currency_end_date)
        date_layout.addLayout(end_layout)
        
        # Quick selection buttons with clear, bold text
        quick_layout = QVBoxLayout()
        
        today_btn = QPushButton("Bugün")
        today_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 12px 20px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                margin: 3px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        today_btn.clicked.connect(lambda: self.set_currency_date_range_and_show_rate(0))
        
        week_btn = QPushButton("Bu Hafta")
        week_btn.setStyleSheet(today_btn.styleSheet())
        week_btn.clicked.connect(lambda: self.set_currency_date_range_and_show_rate(7))
        
        month_btn = QPushButton("Bu Ay")
        month_btn.setStyleSheet(today_btn.styleSheet())
        month_btn.clicked.connect(lambda: self.set_currency_date_range_and_show_rate(30))
        
        quick_layout.addWidget(today_btn)
        quick_layout.addWidget(week_btn)
        quick_layout.addWidget(month_btn)
        
        date_layout.addLayout(quick_layout)
        layout.addWidget(date_group)
        
        # Current rate display
        current_rate_group = QGroupBox("Güncel Kur")
        current_rate_layout = QVBoxLayout(current_rate_group)
        
        self.current_rate_label = QLabel("Yükleniyor...")
        self.current_rate_label.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                color: #1565c0;
                padding: 20px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                border: 2px solid #2196f3;
            }
        """)
        self.current_rate_label.setAlignment(Qt.AlignCenter)
        current_rate_layout.addWidget(self.current_rate_label)
        
        layout.addWidget(current_rate_group)
        
        # Statistics
        stats_group = QGroupBox("İstatistikler")
        stats_layout = QVBoxLayout(stats_group)
        
        self.currency_stats_label = QLabel("Yükleniyor...")
        self.currency_stats_label.setWordWrap(True)
        self.currency_stats_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                border: 1px solid #dee2e6;
                font-size: 12px;
                line-height: 1.5;
            }
        """)
        stats_layout.addWidget(self.currency_stats_label)
        
        layout.addWidget(stats_group)
        
        layout.addStretch()
        return panel
    
    def create_currency_display_panel(self):
        """Create the currency display panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Tab widget for different views
        self.currency_tab_widget = QTabWidget()
        self.currency_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ced4da;
                background-color: white;
            }
            QTabBar::tab {
                background: #f8f9fa;
                border: 1px solid #ced4da;
                padding: 12px 20px;
                margin-right: 2px;
                font-weight: bold;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
                color: #007bff;
            }
        """)
        
        # Calendar view
        self.create_currency_calendar_view()
        
        # Table view
        self.create_currency_table_view()
        
        layout.addWidget(self.currency_tab_widget)
        return panel
    
    def create_currency_calendar_view(self):
        """Create currency calendar view"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Month navigation
        nav_layout = QHBoxLayout()
        
        self.prev_month_btn = QPushButton("◀ Önceki Ay")
        self.prev_month_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 15px;
                font-weight: bold;
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        self.prev_month_btn.clicked.connect(self.prev_currency_month)
        
        self.currency_month_label = QLabel()
        self.currency_month_label.setAlignment(Qt.AlignCenter)
        self.currency_month_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #495057;
                padding: 10px;
            }
        """)
        
        self.next_month_btn = QPushButton("Sonraki Ay ▶")
        self.next_month_btn.setStyleSheet(self.prev_month_btn.styleSheet())
        self.next_month_btn.clicked.connect(self.next_currency_month)
        
        nav_layout.addWidget(self.prev_month_btn)
        nav_layout.addWidget(self.currency_month_label)
        nav_layout.addWidget(self.next_month_btn)
        
        layout.addLayout(nav_layout)
        
        # Calendar widget
        self.currency_calendar = QCalendarWidget()
        self.currency_calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
                font-size: 12px;
            }
            QCalendarWidget QTableView {
                selection-background-color: #007bff;
                selection-color: white;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #495057;
            }
        """)
        self.currency_calendar.selectionChanged.connect(self.on_currency_date_selected)
        layout.addWidget(self.currency_calendar)
        
        # Selected date info
        self.currency_date_info_label = QLabel("Tarih seçin...")
        self.currency_date_info_label.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                color: #1565c0;
                padding: 15px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                margin: 10px;
            }
        """)
        layout.addWidget(self.currency_date_info_label)
        
        self.currency_tab_widget.addTab(tab, "Takvim Görünümü")
    
    def create_currency_table_view(self):
        """Create currency table view"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Table
        self.currency_rates_table = QTableWidget()
        self.currency_rates_table.setColumnCount(4)
        self.currency_rates_table.setHorizontalHeaderLabels([
            "Tarih", "USD/TL Kuru", "Değişim", "Durum"
        ])
        
        # Style the table
        self.currency_rates_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
                gridline-color: #dee2e6;
                selection-background-color: #e3f2fd;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #dee2e6;
            }
            QHeaderView::section {
                background-color: #495057;
                color: white;
                padding: 12px;
                border: 1px solid #343a40;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        
        self.currency_rates_table.setAlternatingRowColors(True)
        self.currency_rates_table.setSortingEnabled(True)
        self.currency_rates_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.currency_rates_table)
        
        self.currency_tab_widget.addTab(tab, "Tablo Görünümü")
    
    def show_currency_rates(self):
        """Switch to currency rates tab"""
        # Find and switch to the currency rates tab
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "Döviz Kurları":
                self.tab_widget.setCurrentIndex(i)
                break
    
    def create_snapshot(self):
        """Create daily snapshot"""
        try:
            snapshot_path = self.storage.create_daily_snapshot()
            QMessageBox.information(self, "Başarılı", f"Günlük yedekleme oluşturuldu: {snapshot_path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Yedekleme hatası: {e}")
    
    # Currency rates tab methods
    def load_cached_currency_rates(self):
        """Load cached currency rates"""
        self.currency_rates_data = self.currency_converter.get_cached_rates()
        self.update_currency_displays()
    
    def update_currency_displays(self):
        """Update all currency displays"""
        self.update_current_rate_display()
        self.update_currency_statistics()
        self.update_currency_table()
        self.update_currency_month_label()
    
    def update_current_rate_display(self):
        """Update current rate display"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Try to get today's rate, or the most recent rate
        current_rate = None
        if today in self.currency_rates_data:
            current_rate = self.currency_rates_data[today]
            rate_date = "Bugün"
        else:
            # Get the most recent rate
            if self.currency_rates_data:
                sorted_dates = sorted(self.currency_rates_data.keys(), reverse=True)
                latest_date = sorted_dates[0]
                current_rate = self.currency_rates_data[latest_date]
                rate_date_obj = datetime.strptime(latest_date, '%Y-%m-%d')
                rate_date = rate_date_obj.strftime('%d.%m.%Y')
        
        if current_rate:
            self.current_rate_label.setText(f"USD/TL\n{current_rate:.4f}\n({rate_date})")
        else:
            self.current_rate_label.setText("Kur Bulunamadı\nLütfen kurları yenileyin")
    
    def update_currency_statistics(self):
        """Update currency statistics"""
        if not self.currency_rates_data:
            self.currency_stats_label.setText("İstatistikler\n\nHenüz veri yok")
            return
        
        rates = list(self.currency_rates_data.values())
        if not rates:
            return
        
        min_rate = min(rates)
        max_rate = max(rates)
        avg_rate = sum(rates) / len(rates)
        total_days = len(rates)
        
        stats_text = f"""İstatistikler

En Yüksek: {max_rate:.4f} TL
En Düşük: {min_rate:.4f} TL
Ortalama: {avg_rate:.4f} TL
Toplam Gün: {total_days}
Fark: {max_rate - min_rate:.4f} TL"""
        
        self.currency_stats_label.setText(stats_text)
    
    def update_currency_table(self):
        """Update currency rates table"""
        if not self.currency_rates_data:
            self.currency_rates_table.setRowCount(0)
            return
        
        sorted_items = sorted(self.currency_rates_data.items(), reverse=True)
        self.currency_rates_table.setRowCount(len(sorted_items))
        
        previous_rate = None
        for row, (date_str, rate) in enumerate(sorted_items):
            # Date
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d.%m.%Y')
            self.currency_rates_table.setItem(row, 0, QTableWidgetItem(formatted_date))
            
            # Rate
            rate_item = QTableWidgetItem(f"{rate:.4f}")
            self.currency_rates_table.setItem(row, 1, rate_item)
            
            # Change
            if previous_rate is not None:
                change = rate - previous_rate
                change_item = QTableWidgetItem(f"{change:+.4f}")
                if change > 0:
                    change_item.setBackground(QColor(212, 237, 218))  # Green
                    change_item.setForeground(QColor(21, 87, 36))
                elif change < 0:
                    change_item.setBackground(QColor(248, 215, 218))  # Red
                    change_item.setForeground(QColor(114, 28, 36))
                else:
                    change_item.setBackground(QColor(255, 243, 205))  # Yellow
                    change_item.setForeground(QColor(133, 100, 4))
                
                self.currency_rates_table.setItem(row, 2, change_item)
            else:
                self.currency_rates_table.setItem(row, 2, QTableWidgetItem("-"))
            
            # Status
            status_item = QTableWidgetItem("Mevcut")
            status_item.setBackground(QColor(212, 237, 218))
            status_item.setForeground(QColor(21, 87, 36))
            self.currency_rates_table.setItem(row, 3, status_item)
            
            previous_rate = rate
        
        # Resize columns
        self.currency_rates_table.resizeColumnsToContents()
    
    def update_currency_month_label(self):
        """Update currency month label"""
        selected_date = self.currency_calendar.selectedDate()
        month_names = [
            "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
        ]
        month_name = month_names[selected_date.month() - 1]
        self.currency_month_label.setText(f"{month_name} {selected_date.year()}")
    
    def set_currency_date_range_and_show_rate(self, days_back):
        """Set date range and show actual rate for the period"""
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-days_back)
        self.currency_start_date.setDate(start_date)
        self.currency_end_date.setDate(end_date)
        
        # Show the rate for the end date (most recent)
        end_date_str = end_date.toString("yyyy-MM-dd")
        
        if end_date_str in self.currency_rates_data:
            rate = self.currency_rates_data[end_date_str]
            period_name = "Bugün" if days_back == 0 else f"Son {days_back} gün"
            self.current_rate_label.setText(f"USD/TL ({period_name})\n{rate:.4f}")
            self.currency_status_label.setText(f"{period_name} kuru gösteriliyor: {rate:.4f}")
        else:
            # Find the most recent available rate
            available_dates = [d for d in self.currency_rates_data.keys() if d <= end_date_str]
            if available_dates:
                latest_date = max(available_dates)
                rate = self.currency_rates_data[latest_date]
                date_obj = datetime.strptime(latest_date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d.%m.%Y')
                self.current_rate_label.setText(f"USD/TL (En Son)\n{rate:.4f}\n({formatted_date})")
                self.currency_status_label.setText(f"En son kur gösteriliyor: {formatted_date}")
            else:
                self.current_rate_label.setText("Kur Bulunamadı\nLütfen kurları yenileyin")
                self.currency_status_label.setText("Kur verisi bulunamadı")
    
    def prev_currency_month(self):
        """Go to previous month"""
        current_date = self.currency_calendar.selectedDate()
        new_date = current_date.addMonths(-1)
        self.currency_calendar.setSelectedDate(new_date)
        self.update_currency_month_label()
    
    def next_currency_month(self):
        """Go to next month"""
        current_date = self.currency_calendar.selectedDate()
        new_date = current_date.addMonths(1)
        self.currency_calendar.setSelectedDate(new_date)
        self.update_currency_month_label()
    
    def on_currency_date_selected(self):
        """Handle currency date selection"""
        selected_date = self.currency_calendar.selectedDate()
        date_str = selected_date.toString("yyyy-MM-dd")
        
        if date_str in self.currency_rates_data:
            rate = self.currency_rates_data[date_str]
            self.currency_date_info_label.setText(
                f"{selected_date.toString('dd.MM.yyyy')}\n"
                f"USD/TL: {rate:.4f}\n"
                f"Kur mevcut"
            )
            self.currency_date_info_label.setStyleSheet("""
                QLabel {
                    background-color: #d4edda;
                    color: #155724;
                    padding: 15px;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 14px;
                    margin: 10px;
                }
            """)
        else:
            self.currency_date_info_label.setText(
                f"{selected_date.toString('dd.MM.yyyy')}\n"
                f"Kur mevcut değil\n"
                f"Kurları yenileyin"
            )
            self.currency_date_info_label.setStyleSheet("""
                QLabel {
                    background-color: #f8d7da;
                    color: #721c24;
                    padding: 15px;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 14px;
                    margin: 10px;
                }
            """)
    
    def refresh_currency_rates(self):
        """Refresh currency rates for selected date range"""
        start_date = self.currency_start_date.date().toPython()
        end_date = self.currency_end_date.date().toPython()
        
        if start_date > end_date:
            QMessageBox.warning(self, "Uyarı", "Başlangıç tarihi bitiş tarihinden sonra olamaz!")
            return
        
        # Show progress
        self.currency_progress_bar.setVisible(True)
        self.currency_progress_bar.setValue(0)
        self.currency_status_label.setText("Kurlar getiriliyor...")
        
        # Fetch rates in a simple loop (for now, can be improved with threading later)
        current_date = start_date
        total_days = (end_date - start_date).days + 1
        processed = 0
        
        try:
            while current_date <= end_date:
                try:
                    # Try to get rate, with weekend fallback
                    rate = self.get_rate_with_weekend_fallback(current_date)
                    if rate:
                        date_str = current_date.strftime('%Y-%m-%d')
                        self.currency_rates_data[date_str] = rate
                        
                except Exception as e:
                    logger.warning(f"Failed to get rate for {current_date}: {e}")
                
                processed += 1
                progress = int((processed / total_days) * 100)
                self.currency_progress_bar.setValue(progress)
                
                # Process events to keep UI responsive
                QApplication.processEvents()
                
                current_date += timedelta(days=1)
            
            self.currency_progress_bar.setVisible(False)
            self.currency_status_label.setText("Kurlar başarıyla güncellendi!")
            self.update_currency_displays()
            
            QMessageBox.information(self, "Başarılı", 
                                   f"Toplam {len(self.currency_rates_data)} kur güncellendi!")
            
        except Exception as e:
            self.currency_progress_bar.setVisible(False)
            self.currency_status_label.setText(f"Hata: {str(e)}")
            QMessageBox.critical(self, "Hata", f"Kur güncelleme hatası: {str(e)}")
    
    def get_rate_with_weekend_fallback(self, target_date):
        """Get rate with weekend fallback - use last available rate if weekend"""
        try:
            # First try to get the rate for the exact date
            rate = self.currency_converter.get_usd_rate(target_date)
            if rate:
                return rate
            
            # If no rate available (weekend/holiday), look for the last available rate
            check_date = target_date - timedelta(days=1)
            max_lookback = 7  # Look back up to 7 days
            
            for i in range(max_lookback):
                try:
                    rate = self.currency_converter.get_usd_rate(check_date)
                    if rate:
                        logger.info(f"Using fallback rate from {check_date} for {target_date}")
                        return rate
                except:
                    pass
                
                check_date -= timedelta(days=1)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting rate for {target_date}: {e}")
            return None
    
    def export_currency_rates(self):
        """Export currency rates to Excel"""
        if not self.currency_rates_data:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak kur verisi bulunamadı!")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Kur Verilerini Dışa Aktar",
            f"doviz_kurlari_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                import pandas as pd
                
                # Prepare data
                data = []
                sorted_items = sorted(self.currency_rates_data.items())
                previous_rate = None
                
                for date_str, rate in sorted_items:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    change = rate - previous_rate if previous_rate is not None else 0
                    
                    data.append({
                        'Tarih': date_obj.strftime('%d.%m.%Y'),
                        'USD_TL_Kuru': rate,
                        'Değişim': change,
                        'Yüzde_Değişim': (change / previous_rate * 100) if previous_rate else 0
                    })
                    
                    previous_rate = rate
                
                # Create DataFrame and export
                df = pd.DataFrame(data)
                df.to_excel(file_path, index=False, sheet_name='Döviz Kurları')
                
                QMessageBox.information(self, "Başarılı", 
                                       f"Kur verileri başarıyla dışa aktarıldı:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dışa aktarma hatası: {str(e)}")
    
    def create_report_preview_controls(self):
        """Create control panel for report preview"""
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        
        # Refresh button
        refresh_btn = QPushButton("Önizlemeyi Yenile")
        refresh_btn.clicked.connect(self.update_report_preview)
        controls_layout.addWidget(refresh_btn)
        
        # Date range info
        self.preview_date_label = QLabel("Tarih aralığı seçin ve rapor oluşturun")
        controls_layout.addWidget(self.preview_date_label)
        
        controls_layout.addStretch()
        
        # Print button
        print_btn = QPushButton("Yazdır")
        print_btn.clicked.connect(self.print_current_report)
        controls_layout.addWidget(print_btn)
        
        # Print to PDF button
        pdf_btn = QPushButton("PDF Kaydet")
        pdf_btn.clicked.connect(self.print_to_pdf)
        controls_layout.addWidget(pdf_btn)
        
        # Export to Excel button
        excel_btn = QPushButton("Excel Kaydet")
        excel_btn.clicked.connect(self.export_tab_to_excel)
        controls_layout.addWidget(excel_btn)
        
        # Export button
        export_btn = QPushButton("Önizlenen Raporu Dışa Aktar")
        export_btn.clicked.connect(self.export_preview_report)
        controls_layout.addWidget(export_btn)
        
        self.report_preview_layout.addWidget(controls_widget)
    
    def update_report_preview(self):
        """Update the report preview with tabbed interface"""
        try:
            # Clear existing tabs
            self.report_tabs.clear()
            
            if not self.current_payments:
                # Show empty state
                empty_widget = QTextEdit()
                empty_widget.setReadOnly(True)
                empty_widget.setHtml("""
                <div style="font-family: Arial, sans-serif; padding: 20px; text-align: center;">
                    <h2 style="color: #7f8c8d;">Rapor Önizleme</h2>
                    <p style="color: #95a5a6; font-size: 16px;">
                        Rapor önizlemesi için önce veri yükleyin veya içe aktarın.
                    </p>
                    <div style="background-color: #ecf0f1; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <h4 style="color: #2c3e50;">Nasıl Başlanır:</h4>
                        <ol style="text-align: left; color: #34495e;">
                            <li>Veri İçe Aktarma sekmesinden dosya yükleyin</li>
                            <li>Manuel Veri Girişi sekmesinden veri ekleyin</li>
                            <li>Tarih aralığı seçin ve rapor oluşturun</li>
                        </ol>
                    </div>
                </div>
                """)
                self.report_tabs.addTab(empty_widget, "Başlangıç")
                return
            
            # Get date range from current data
            dates = [p.date for p in self.current_payments if p.date]
            if not dates:
                return
            
            start_date = min(dates)
            end_date = max(dates)
            
            # Update date label
            self.preview_date_label.setText(f"Tarih Aralığı: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
            
            # Generate HTML preview
            from report_generator import ReportGenerator
            report_gen = ReportGenerator()
            
            html_sheets = report_gen.generate_html_preview(self.current_payments, start_date, end_date)
            
            # Create tabs for each sheet
            for sheet_name, html_content in html_sheets.items():
                text_widget = QTextEdit()
                text_widget.setReadOnly(True)
                text_widget.setHtml(html_content)
                self.report_tabs.addTab(text_widget, sheet_name)
            
        except Exception as e:
            logger.error(f"Failed to update report preview: {e}")
            error_widget = QTextEdit()
            error_widget.setReadOnly(True)
            error_widget.setHtml(f"""
            <div style="font-family: Arial, sans-serif; padding: 20px; text-align: center;">
                <h2 style="color: #e74c3c;">Hata</h2>
                <p>Rapor önizleme güncellenirken hata oluştu: {e}</p>
                <p style="color: #7f8c8d;">Lütfen veri yüklü olduğundan ve geçerli tarih aralığı seçildiğinden emin olun.</p>
            </div>
            """)
            self.report_tabs.addTab(error_widget, "Hata")
    
    def export_preview_report(self):
        """Export the currently previewed report with format selection"""
        try:
            if not self.current_payments:
                QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak rapor verisi bulunamadı.")
                return
            
            # Get date range
            dates = [p.date for p in self.current_payments if p.date]
            if not dates:
                QMessageBox.warning(self, "Uyarı", "Geçerli tarih verisi bulunamadı.")
                return
            
            start_date = min(dates)
            end_date = max(dates)
            
            # Ask user for export format
            from PySide6.QtWidgets import QInputDialog
            format_options = ["Excel (.xlsx)", "PDF (.pdf)", "Word (.docx)", "Tüm Formatlar"]
            
            selected_format, ok = QInputDialog.getItem(
                self, "Format Seçin", "Hangi formatta dışa aktarmak istiyorsunuz?",
                format_options, 0, False
            )
            
            if not ok:
                return
            
            if selected_format == "Tüm Formatlar":
                # Export all formats
                output_dir = QFileDialog.getExistingDirectory(self, "Klasör Seçin")
                if output_dir:
                    reports = generate_all_reports(self.current_payments, start_date, end_date, output_dir)
                    QMessageBox.information(self, "Başarılı", f"Tüm formatlar oluşturuldu:\n{chr(10).join(reports.values())}")
            else:
                # Export single format
                if selected_format.startswith("Excel"):
                    extension = ".xlsx"
                    file_filter = "Excel Files (*.xlsx)"
                elif selected_format.startswith("PDF"):
                    extension = ".pdf"
                    file_filter = "PDF Files (*.pdf)"
                elif selected_format.startswith("Word"):
                    extension = ".docx"
                    file_filter = "Word Files (*.docx)"
                else:
                    extension = ".xlsx"
                    file_filter = "Excel Files (*.xlsx)"
                
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Rapor Kaydet", 
                    f"tahsilat_raporu_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}{extension}",
                    file_filter
                )
                
                if file_path:
                    if extension == ".xlsx":
                        self.report_generator.export_to_excel(self.current_payments, start_date, end_date, file_path)
                    elif extension == ".pdf":
                        self.report_generator.export_to_pdf(self.current_payments, start_date, end_date, file_path)
                    elif extension == ".docx":
                        self.report_generator.export_to_word(self.current_payments, start_date, end_date, file_path)
                    
                    QMessageBox.information(self, "Başarılı", f"Rapor oluşturuldu: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export preview report: {e}")
            QMessageBox.critical(self, "Hata", f"Rapor dışa aktarılırken hata oluştu: {e}")
    
    def export_tab_to_excel(self):
        """Export current tab to Excel with exact UI format"""
        try:
            current_widget = self.report_tabs.currentWidget()
            if not current_widget:
                QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak rapor bulunamadı.")
                return
            
            current_tab_name = self.report_tabs.tabText(self.report_tabs.currentIndex())
            
            # Get save file path
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Excel Dosyasını Kaydet",
                f"rapor_{current_tab_name.replace('.', '').replace('-', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if file_path:
                # Get the current date range
                dates = [p.date for p in self.current_payments if p.date]
                if not dates:
                    QMessageBox.warning(self, "Uyarı", "Tarih bilgisi bulunamadı.")
                    return
                    
                start_date = min(dates)
                end_date = max(dates)
                
                # Get the current tab index to determine which week to export
                current_tab_index = self.report_tabs.currentIndex()
                
                # Use report generator to create proper Excel export for this specific tab
                from report_generator import ReportGenerator
                report_gen = ReportGenerator()
                
                # Generate the weekly data
                customer_date_table = report_gen.generate_customer_date_table(
                    self.current_payments, start_date, end_date
                )
                customer_check_table = report_gen.generate_customer_check_table(
                    self.current_payments, start_date, end_date
                )
                
                if customer_date_table:
                    sorted_weeks = sorted(customer_date_table.keys())
                    
                    # Get the specific week data for the current tab
                    if current_tab_index < len(sorted_weeks):
                        week_start = sorted_weeks[current_tab_index]
                        week_data = customer_date_table[week_start]
                        check_data = customer_check_table.get(week_start) if customer_check_table else None
                        
                        # Create Excel workbook with the same format as the main export
                        import xlsxwriter
                        workbook = xlsxwriter.Workbook(file_path)
                        
                        # Use the same export logic but for a single week
                        report_gen._export_single_week_to_excel(
                            workbook, current_tab_name[:31], week_data, check_data, 
                            self.current_payments, start_date, end_date
                        )
                        
                        workbook.close()
                        
                        QMessageBox.information(
                            self, 
                            "Başarılı", 
                            f"Rapor sekmesi Excel dosyasına aktarıldı:\n{file_path}"
                        )
                    else:
                        QMessageBox.warning(self, "Uyarı", "Sekme verisi bulunamadı.")
                else:
                    QMessageBox.warning(self, "Uyarı", "Rapor verisi bulunamadı.")
                
        except Exception as e:
            logger.error(f"Failed to export tab to Excel: {e}")
            QMessageBox.critical(self, "Hata", f"Sekme Excel'e aktarılamadı: {e}")
    
    def print_current_report(self):
        """Print the currently displayed report"""
        try:
            current_widget = self.report_tabs.currentWidget()
            if not current_widget:
                QMessageBox.warning(self, "Uyarı", "Yazdırılacak rapor bulunamadı.")
                return
            
            # Create a printer dialog
            from PySide6.QtPrintSupport import QPrinter, QPrintDialog
            from PySide6.QtGui import QTextDocument
            
            printer = QPrinter()
            # Set basic printer properties without complex enums
            printer.setOutputFormat(QPrinter.OutputFormat.NativeFormat)
            
            print_dialog = QPrintDialog(printer, self)
            print_dialog.setWindowTitle("Rapor Yazdır")
            
            if print_dialog.exec() == QPrintDialog.Accepted:
                # Create a text document from the HTML content
                doc = QTextDocument()
                doc.setHtml(current_widget.toHtml())
                
                # Print the document
                doc.print_(printer)
                
                QMessageBox.information(self, "Başarılı", "Rapor yazdırıldı.")
            
        except Exception as e:
            logger.error(f"Failed to print report: {e}")
            QMessageBox.critical(self, "Hata", f"Rapor yazdırılırken hata oluştu: {e}")
    
    def print_to_pdf(self):
        """Print current report tab to PDF"""
        try:
            current_widget = self.report_tabs.currentWidget()
            if not current_widget:
                QMessageBox.warning(self, "Uyarı", "PDF'e yazdırılacak rapor bulunamadı.")
                return
            
            # Get current tab name for filename
            current_tab_name = self.report_tabs.tabText(self.report_tabs.currentIndex())
            
            # Ask for file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, "PDF Olarak Kaydet", 
                f"rapor_{current_tab_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "PDF Files (*.pdf)"
            )
            
            if file_path:
                # Create a printer for PDF output
                printer = QPrinter()
                printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                printer.setOutputFileName(file_path)
                
                # Create a text document from the HTML content
                from PySide6.QtGui import QTextDocument
                doc = QTextDocument()
                doc.setHtml(current_widget.toHtml())
                
                # Print to PDF
                doc.print_(printer)
                
                QMessageBox.information(self, "Başarılı", f"Rapor PDF olarak kaydedildi: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to print to PDF: {e}")
            QMessageBox.critical(self, "Hata", f"PDF yazdırma hatası: {e}")
    
    def clear_storage_data(self):
        """Clear all stored data from the application"""
        try:
            # Show confirmation dialog
            reply = QMessageBox.question(
                self, 
                'Veri Temizleme Onayı', 
                'Tüm veri depolaması temizlenecek. Bu işlem geri alınamaz.\n\nDevam etmek istediğinizden emin misiniz?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Clear storage
                self.storage.clear_all_data()
                
                # Clear current payments
                self.current_payments = []
                
                # Update UI
                self.update_data_table()
                self.update_report_preview()
                
                # Show success message
                QMessageBox.information(
                    self, 
                    'Başarılı', 
                    'Tüm veri depolaması başarıyla temizlendi.'
                )
                
                logger.info("Storage data cleared by user")
                
        except Exception as e:
            logger.error(f"Failed to clear storage data: {e}")
            QMessageBox.critical(self, "Hata", f"Veri temizlenirken hata oluştu: {e}")
    
    def export_as_pdf(self):
        """Export current report as PDF"""
        try:
            if not self.current_payments:
                QMessageBox.warning(self, "Uyarı", "PDF dışa aktarmak için veri bulunamadı.")
                return
            
            # Get date range
            dates = [p.date for p in self.current_payments if p.date]
            if not dates:
                QMessageBox.warning(self, "Uyarı", "Geçerli tarih verisi bulunamadı.")
                return
            
            start_date = min(dates)
            end_date = max(dates)
            
            # Ask for file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, "PDF Olarak Kaydet", 
                f"tahsilat_raporu_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf",
                "PDF Files (*.pdf)"
            )
            
            if file_path:
                # Generate PDF using report generator
                self.report_generator.export_to_pdf(self.current_payments, start_date, end_date, file_path)
                QMessageBox.information(self, "Başarılı", f"PDF raporu oluşturuldu: {file_path}")
                
        except Exception as e:
            logger.error(f"Failed to export as PDF: {e}")
            QMessageBox.critical(self, "Hata", f"PDF dışa aktarma hatası: {e}")


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Payment Reporting System")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Payment Reporting")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
