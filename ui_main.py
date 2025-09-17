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
    QCheckBox, QDialog, QListWidget, QListWidgetItem, QCalendarWidget,
    QSizePolicy, QStackedWidget, QRadioButton
)
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtCore import Qt, QDate, QThread, Signal, QTimer
from PySide6.QtGui import QAction, QIcon, QFont, QPixmap, QColor
import qtawesome as qta

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
    
    def __init__(self, file_path: str, file_format: str, sheet_name: str = None, existing_payments: list = None, amount_column: str = None, currency_column: str = None):
        super().__init__()
        self.file_path = file_path
        self.file_format = file_format
        self.sheet_name = sheet_name
        self.importer = DataImporter()
        self.existing_payments = existing_payments or []
        self.amount_column = amount_column
        self.currency_column = currency_column
    
    def is_duplicate(self, new_payment, existing_payments):
        """Check if a payment is a duplicate based on customer name, amount, and date"""
        for existing_payment in existing_payments:
            if (existing_payment.customer_name == new_payment.customer_name and
                existing_payment.date == new_payment.date and
                abs(existing_payment.amount - new_payment.amount) < 0.01):  # Allow small rounding differences
                return True
        return False
    
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
            
            self.progress.emit(30)
            self.status.emit("Veriler doğrulanıyor...")
            
            # Validate data
            valid_payments, warnings = validate_payment_data(payments)
            
            self.progress.emit(50)
            self.status.emit("Dublicate kontrolü yapılıyor...")
            
            # Check for duplicates
            new_payments = []
            duplicate_count = 0
            
            for payment in valid_payments:
                if self.is_duplicate(payment, self.existing_payments):
                    duplicate_count += 1
                    warnings.append(f"Dublicate bulundu: {payment.customer_name} - {payment.amount} - {payment.date}")
                else:
                    new_payments.append(payment)
            
            if duplicate_count > 0:
                warnings.append(f"Toplam {duplicate_count} dublicate ödeme bulundu ve atlandı")
            
            self.progress.emit(100)
            self.status.emit(f"İçe aktarma tamamlandı - {len(new_payments)} yeni ödeme, {duplicate_count} dublicate")
            
            self.finished.emit(new_payments, warnings)
            
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    """Modern, professional main application window with Turkish interface"""
    
    def __init__(self):
        super().__init__()
        self.storage = PaymentStorage()
        self.report_generator = ReportGenerator()
        self.currency_converter = CurrencyConverter()
        self.current_payments = []
        
        # Central data source for filtering
        self.main_data = None  # Will be populated with pandas DataFrame
        
        # Theme management
        self.is_dark_theme = False  # Start with light theme for better accessibility
        self.theme_settings = self.load_theme_settings()
        
        # Initialize UI components
        self.init_ui()
        
        # Setup responsive behavior and theme
        self.setup_responsive_behavior()
        
        # Load data after UI is fully initialized
        self.load_data()
        self.apply_theme(self.is_dark_theme)
    
    def load_theme_settings(self):
        """Load theme settings from application settings"""
        try:
            from PySide6.QtCore import QSettings
            settings = QSettings("TahsilatApp", "Settings")
            self.is_dark_theme = settings.value("dark_theme", False, bool)
            return settings
        except Exception:
            return None
    
    def save_theme_settings(self):
        """Save current theme settings"""
        if self.theme_settings:
            self.theme_settings.setValue("dark_theme", self.is_dark_theme)
    
    def setup_responsive_behavior(self):
        """Setup responsive window behavior"""
        # Override resize event
        self.original_resize_event = self.resizeEvent
        self.resizeEvent = self.on_window_resize
        
        # Set minimum sizes to prevent UI breaking
        self.setMinimumSize(1200, 800)
        
        # Ensure proper initial sizing
        self.resize(1400, 900)
    
    def on_window_resize(self, event):
        """Handle window resize for responsive behavior"""
        if hasattr(self, 'original_resize_event'):
            self.original_resize_event(event)
    
    def apply_global_stylesheet(self):
        """Apply centralized stylesheet for consistent design across the application"""
        self.setStyleSheet("""
            /* Main Application Styling */
            QMainWindow {
                background-color: #F8F9FA;
                color: #000000;
            }
            
            /* Group Box Styling - Card-like appearance */
            QGroupBox {
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 15px;
                background-color: white;
                font-weight: 600;
                font-size: 14px;
                color: #000000;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                margin-left: 10px;
                color: #000000;
                font-weight: 600;
                background-color: #F8F9FA;
                border-radius: 4px;
                border: 1px solid #DEE2E6;
            }
            
            /* Button Styling - Enhanced modern design */
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #007BFF, stop:1 #0056B3);
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
                min-height: 25px;
                margin: 2px;
                transition: all 0.2s ease;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #0056B3, stop:1 #004085);
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #004085, stop:1 #002752);
            }
            
            /* Input Field Styling - Enhanced for better readability */
            QLineEdit, QComboBox, QDateEdit {
                background-color: white;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 12px; /* Increased padding for better height */
                color: #000000;
                font-size: 15px; /* Increased font size for readability */
                font-weight: 500;
                min-height: 30px; /* Increased min-height */
            }
            
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border-color: #007BFF;
                background-color: #F8F9FA;
                border-width: 2px;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #000000;
                margin-right: 5px;
            }
            
            /* Tab Widget Styling - Enhanced for modern look */
            QTabWidget::pane {
                border: 1px solid #DEE2E6;
                border-radius: 12px;
                background-color: white;
                margin-top: 8px;
                padding: 10px;
            }
            
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #F8F9FA, stop:1 #E9ECEF);
                color: #000000;
                padding: 18px 30px; /* Enhanced padding for better touch targets */
                margin-right: 3px;
                margin-bottom: 2px;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border: 1px solid #DEE2E6;
                border-bottom: none;
                font-weight: 600;
                font-size: 15px; /* Larger font for better readability */
                min-width: 140px; /* Wider tabs for better proportions */
                transition: all 0.2s ease;
            }
            
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #007BFF, stop:1 #0056B3);
                color: white;
                border-color: #007BFF;
            }
            
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #E9ECEF, stop:1 #DEE2E6);
                color: #000000;
            }
            
            /* Table Styling */
            QTableWidget {
                background-color: white;
                alternate-background-color: #F8F9FA;
                gridline-color: #DEE2E6;
                selection-background-color: #E3F2FD;
                color: #000000;
                font-size: 13px;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
            }
            
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #DEE2E6;
            }
            
            QTableWidget::item:selected {
                background-color: #007BFF;
                color: white;
            }
            
            QHeaderView::section {
                background-color: #F8F9FA;
                color: #000000;
                padding: 10px;
                border: 1px solid #DEE2E6;
                font-weight: 600;
                font-size: 13px;
            }
            
            /* Label Styling */
            QLabel {
                color: #000000;
                font-size: 14px; /* Increased default font size for labels */
            }
            
            /* Splitter Styling */
            QSplitter::handle {
                background-color: #DEE2E6;
                width: 2px;
                height: 2px;
            }
            
            QSplitter::handle:hover {
                background-color: #007BFF;
            }
        """)
        
        # Ensure widgets expand naturally without clipping controls
        if hasattr(self, 'tab_widget'):
            self.tab_widget.setMinimumHeight(0)
            try:
                self.tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            except Exception:
                pass
        if hasattr(self, 'report_tabs'):
            self.report_tabs.setMinimumHeight(0)
            try:
                self.report_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            except Exception:
                pass
    
    def init_ui(self):
        """Initialize the modern, professional user interface"""
        self.setWindowTitle("Tahsilat Yönetim Sistemi - Profesyonel Sürüm")
        self.setGeometry(100, 100, 1600, 1000)
        self.setMinimumSize(1400, 900)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout (no margins for toolbar/menubar)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create modern menu bar with Turkish labels
        self.create_modern_menu_bar()
        
        # Create enhanced toolbar with icons
        self.create_modern_toolbar()
        
        # Create responsive main content area
        self.create_responsive_main_content(main_layout)
        
        # Create enhanced status bar
        self.create_enhanced_status_bar()
        
        # Setup window properties
        self.setup_window_properties()
    
    def create_modern_menu_bar(self):
        """Create modern menu bar with proper Turkish labels and keyboard shortcuts"""
        menubar = self.menuBar()
        
        # File menu - Dosya İşlemleri
        file_menu = menubar.addMenu(qta.icon("fa5s.folder"), 'Dosya İşlemleri')
        
        # Import actions
        import_action = QAction(qta.icon("fa5s.upload"), 'Veri İçe Aktar', self)
        import_action.setShortcut('Ctrl+I')
        import_action.setStatusTip('Excel, CSV veya JSON dosyasından veri yükle')
        import_action.triggered.connect(self.import_data)
        file_menu.addAction(import_action)
        
        export_action = QAction(qta.icon('fa5s.download'), 'Veriyi Dışa Aktar', self)
        export_action.setShortcut('Ctrl+E')
        export_action.setStatusTip('Mevcut veriyi farklı formatlarda dışa aktar')
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # Recent files (placeholder for future implementation)
        recent_menu = file_menu.addMenu(qta.icon('fa5s.history'), 'Son Kullanılan Dosyalar')
        no_recent_action = QAction('Henüz dosya yok', self)
        no_recent_action.setEnabled(False)
        recent_menu.addAction(no_recent_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('🚪 Çıkış', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Uygulamadan çık')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Reports menu - Rapor İşlemleri
        reports_menu = menubar.addMenu(qta.icon('fa5s.chart-bar'), 'Rapor İşlemleri')
        
        daily_report_action = QAction(qta.icon('fa5s.calendar-day'), 'Günlük Rapor Üret', self)
        daily_report_action.setShortcut('Ctrl+D')
        daily_report_action.setStatusTip('Seçilen tarih aralığı için günlük rapor oluştur')
        daily_report_action.triggered.connect(self.generate_daily_report)
        reports_menu.addAction(daily_report_action)
        
        weekly_report_action = QAction(qta.icon('fa5s.calendar-week'), 'Haftalık Rapor Üret', self)
        weekly_report_action.setShortcut('Ctrl+W')
        weekly_report_action.setStatusTip('Seçilen tarih aralığı için haftalık rapor oluştur')
        weekly_report_action.triggered.connect(self.generate_weekly_report)
        reports_menu.addAction(weekly_report_action)
        
        monthly_report_action = QAction(qta.icon('fa5s.calendar-alt'), 'Aylık Rapor Üret', self)
        monthly_report_action.setShortcut('Ctrl+M')
        monthly_report_action.setStatusTip('Seçilen tarih aralığı için aylık rapor oluştur')
        monthly_report_action.triggered.connect(self.generate_monthly_report)
        reports_menu.addAction(monthly_report_action)
        
        reports_menu.addSeparator()
        
        all_reports_action = QAction(qta.icon('fa5s.file-alt'), 'Tüm Raporları Üret', self)
        all_reports_action.setShortcut('Ctrl+Shift+R')
        all_reports_action.setStatusTip('Tüm rapor türlerini aynı anda oluştur')
        all_reports_action.triggered.connect(self.generate_all_reports)
        reports_menu.addAction(all_reports_action)
        
        # Tools menu - Araçlar ve Yardımcılar
        tools_menu = menubar.addMenu(qta.icon('fa5s.tools'), 'Araçlar')
        
        currency_action = QAction(qta.icon('fa5s.exchange-alt'), 'Döviz Kurları', self)
        currency_action.setShortcut('Ctrl+U')
        currency_action.setStatusTip('Güncel döviz kurlarını görüntüle ve yönet')
        currency_action.triggered.connect(self.show_currency_rates)
        tools_menu.addAction(currency_action)
        
        snapshot_action = QAction('💾 Veri Yedeği Oluştur', self)
        snapshot_action.setShortcut('Ctrl+B')
        snapshot_action.setStatusTip('Mevcut verinin yedeğini oluştur')
        snapshot_action.triggered.connect(self.create_snapshot)
        tools_menu.addAction(snapshot_action)
    
        tools_menu.addSeparator()
        
        # Data management tools
        validate_action = QAction(qta.icon("fa5s.check"), 'Veri Doğrulaması', self)
        validate_action.setStatusTip('Yüklenen verilerin doğruluğunu kontrol et')
        # validate_action.triggered.connect(self.validate_data)  # To be implemented
        tools_menu.addAction(validate_action)
        
        # Settings menu - Ayarlar ve Kişiselleştirme
        settings_menu = menubar.addMenu(qta.icon("fa5s.cog"), 'Ayarlar')
        
        # Theme submenu
        theme_menu = settings_menu.addMenu(qta.icon("fa5s.palette"), 'Tema Seçimi')
        
        light_theme_action = QAction(qta.icon("fa5s.sun"), 'Açık Tema', self)
        light_theme_action.setCheckable(True)
        light_theme_action.setChecked(not self.is_dark_theme)
        light_theme_action.triggered.connect(lambda: self.set_theme(False))
        theme_menu.addAction(light_theme_action)
        
        dark_theme_action = QAction(qta.icon("fa5s.moon"), 'Koyu Tema', self)
        dark_theme_action.setCheckable(True)
        dark_theme_action.setChecked(self.is_dark_theme)
        dark_theme_action.triggered.connect(lambda: self.set_theme(True))
        theme_menu.addAction(dark_theme_action)
        
        # Store theme actions for updates
        self.light_theme_action = light_theme_action
        self.dark_theme_action = dark_theme_action
        
        settings_menu.addSeparator()
        
        clear_data_action = QAction(qta.icon("fa5s.trash"), 'Veri Deposunu Temizle', self)
        clear_data_action.setStatusTip('Tüm kayıtlı verileri temizle (geri alınamaz)')
        clear_data_action.triggered.connect(self.clear_storage_data)
        settings_menu.addAction(clear_data_action)
        
        settings_menu.addSeparator()
        
        # Export options
        pdf_export_action = QAction(qta.icon("fa5s.file-alt"), 'PDF Olarak Dışa Aktar', self)
        pdf_export_action.setShortcut('Ctrl+P')
        pdf_export_action.setStatusTip('Mevcut raporu PDF formatında kaydet')
        pdf_export_action.triggered.connect(self.export_as_pdf)
        settings_menu.addAction(pdf_export_action)
        
        # Help menu - Yardım ve Bilgi
        help_menu = menubar.addMenu(qta.icon("fa5s.question-circle"), 'Yardım')
        
        about_action = QAction(qta.icon("fa5s.info-circle"), 'Hakkında', self)
        about_action.setStatusTip('Uygulama hakkında bilgi')
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
        shortcuts_action = QAction(qta.icon("fa5s.keyboard"), 'Klavye Kısayolları', self)
        shortcuts_action.setStatusTip('Kullanılabilir klavye kısayollarını göster')
        shortcuts_action.triggered.connect(self.show_shortcuts_dialog)
        help_menu.addAction(shortcuts_action)
    
    def create_modern_toolbar(self):
        """Create CLEAN toolbar with NO DUPLICATE buttons - UNIFIED APPROACH"""
        toolbar = QToolBar("Ana Araç Çubuğu")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)
        
        # Quick import action
        import_action = QAction("📥", self)
        import_action.setText("Veri İçe Aktar")
        import_action.setShortcut("Ctrl+I")
        import_action.setStatusTip("Hızlı veri içe aktarma")
        import_action.triggered.connect(self.import_data)
        toolbar.addAction(import_action)
        
        toolbar.addSeparator()
        
        # SINGLE UNIFIED REPORT BUTTON - NO MORE DUPLICATES
        unified_report_action = QAction(qta.icon('fa5s.chart-bar', color='#000000'), "Rapor Oluştur", self)
        unified_report_action.setShortcut("Ctrl+R")
        unified_report_action.setStatusTip("Tüm rapor seçenekleri için birleşik dialog")
        unified_report_action.triggered.connect(self.show_unified_report_dialog)
        toolbar.addAction(unified_report_action)
        
        toolbar.addSeparator()
        
        # Advanced filter action - DISABLED (replaced with in-place Excel-like filtering)
        # filter_action = QAction("🔍", self)
        # filter_action.setText("Gelişmiş Filtre")
        # filter_action.setShortcut("Ctrl+F")
        # filter_action.setStatusTip("Excel benzeri gelişmiş filtreleme")
        # filter_action.triggered.connect(self.show_advanced_filter)
        # toolbar.addAction(filter_action)
        
        toolbar.addSeparator()
        
        # Data management tools
        refresh_action = QAction("🔄", self)
        refresh_action.setText("Yenile")
        refresh_action.setShortcut("F5")
        refresh_action.setStatusTip("Veriyi yenile")
        refresh_action.triggered.connect(self.refresh_data)
        toolbar.addAction(refresh_action)
        
        export_action = QAction("📤", self)
        export_action.setText("Dışa Aktar")
        export_action.setShortcut("Ctrl+E")
        export_action.setStatusTip("Veriyi dışa aktar")
        export_action.triggered.connect(self.export_data)
        toolbar.addAction(export_action)
        
        toolbar.addSeparator()
        
        # Theme toggle in toolbar
        theme_action = QAction(qta.icon('fa5s.moon', color='#000000') if not self.is_dark_theme else qta.icon('fa5s.sun', color='#000000'), "Tema Değiştir", self)
        theme_action.setStatusTip("Açık/Koyu tema arasında geçiş yap")
        theme_action.triggered.connect(self.toggle_theme)
        toolbar.addAction(theme_action)
        self.theme_toolbar_action = theme_action
    
    def create_responsive_main_content(self, main_layout):
        """Create responsive main content area with modern sidebar"""
        # Create main content container
        content_container = QWidget()
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Create modern collapsible sidebar
        self.sidebar = self.create_modern_sidebar()
        content_layout.addWidget(self.sidebar)
        
        # Create main content area
        main_content = self.create_main_content_area()
        content_layout.addWidget(main_content)
        
        # Add to main layout
        main_layout.addWidget(content_container)
    
    def create_modern_sidebar(self):
        """Create modern collapsible sidebar with navigation"""
        sidebar = QWidget()
        sidebar.setFixedWidth(280)  # Fixed width for consistency
        sidebar.setObjectName("modernSidebar")
        
        # Sidebar styling
        sidebar.setStyleSheet("""
            QWidget#modernSidebar {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #34495E, stop: 1 #2C3E50);
                border-right: 2px solid #7F8C8D;
            }
            QPushButton {
                background: transparent;
                border: none;
                color: white;
                font-size: 14px;
                font-weight: 600;
                padding: 15px 20px;
                text-align: left;
                border-radius: 8px;
                margin: 2px 8px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                border-left: 4px solid #3498DB;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.2);
            }
            QPushButton#activeSection {
                background: rgba(52, 152, 219, 0.3);
                border-left: 4px solid #3498DB;
            }
            QLabel {
                color: #BDC3C7;
                font-size: 12px;
                font-weight: 500;
                padding: 10px 20px 5px 20px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(5)
        
        # Header
        header_label = QLabel("TAHSİLAT YÖNETİMİ")
        header_label.setStyleSheet("""
            color: white;
            font-size: 16px;
            font-weight: 700;
            padding: 20px;
            text-align: center;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            margin: 0 8px 20px 8px;
        """)
        layout.addWidget(header_label)
        
        # Navigation sections
        self.create_sidebar_section(layout, "VERİ YÖNETİMİ", [
            ("Veri İçe Aktar", self.show_import_section),
            ("Veri Tablosu", self.show_data_table_section),
            ("Veri İstatistikleri", self.show_stats_section),
            ("Veri Temizle", self.clear_storage_data)
        ])
        
        self.create_sidebar_section(layout, "RAPOR İŞLEMLERİ", [
            ("Rapor Oluştur", self.show_report_section),
            ("Rapor Önizleme", self.show_preview_section),
            ("Aylık Rapor", self.show_monthly_report_section)
        ])
        
        self.create_sidebar_section(layout, "DÖVİZ DÖNÜŞÜMÜ", [
            ("TL-USD Dönüşüm Detayları", self.show_currency_conversion_details)
        ])
        
        self.create_sidebar_section(layout, "ARAÇLAR", [
            ("Döviz Kurları", self.show_currency_rates),
            ("Takvim", self.show_calendar_section),
            ("Ayarlar", self.show_settings_section)
        ])
        
        # Add stretch to push everything to top
        layout.addStretch()
        
        # Toggle button at bottom
        toggle_btn = QPushButton("◀ Daralt")
        toggle_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 0, 0, 0.3);
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                margin: 0;
                border-radius: 0;
                padding: 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 0.5);
                border-left: none;
            }
        """)
        toggle_btn.clicked.connect(self.toggle_sidebar)
        layout.addWidget(toggle_btn)
        
        return sidebar
    
    def create_sidebar_section(self, layout, title, items):
        """Create a section in the sidebar with title and items"""
        # Section title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #000000;
                font-weight: 700;
                font-size: 13px;
                margin: 10px 0 5px 0;
                padding: 8px 12px;
                background: rgba(240, 242, 245, 0.95);
                border-radius: 6px;
                border: 1px solid rgba(0, 0, 0, 0.15);
            }
        """)
        layout.addWidget(title_label)
        
        # Section items
        for text, callback in items:
            btn = QPushButton(text)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(240, 242, 245, 0.95);
                    color: #000000;
                    border: 1px solid rgba(0, 0, 0, 0.15);
                    border-radius: 6px;
                    padding: 8px 12px;
                    margin: 2px 0;
                    text-align: left;
                    font-weight: 600;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: rgba(74, 144, 226, 0.15);
                    border-color: rgba(74, 144, 226, 0.3);
                    color: #000000;
                }
                QPushButton:pressed {
                    background: rgba(74, 144, 226, 0.25);
                    border-color: rgba(74, 144, 226, 0.5);
                    color: #000000;
                }
            """)
            btn.clicked.connect(callback)
            layout.addWidget(btn)
        
        # Add small spacer
        layout.addSpacing(10)
    
    def create_main_content_area(self):
        """Create the main content area with cards"""
        content_widget = QWidget()
        content_widget.setObjectName("mainContent")
        content_widget.setStyleSheet("""
            QWidget#mainContent {
                background-color: #F1F3F4;
                border-radius: 0;
                border: 1px solid #DEE2E6;
            }
        """)
        
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # Create stacked widget for different sections
        self.content_stack = QStackedWidget()
        layout.addWidget(self.content_stack)
        
        # Add different content pages
        self.content_stack.addWidget(self.create_import_page())
        self.content_stack.addWidget(self.create_stats_page())
        self.content_stack.addWidget(self.create_data_table_page())
        self.content_stack.addWidget(self.create_report_page())
        self.content_stack.addWidget(self.create_preview_page())
        self.content_stack.addWidget(self.create_monthly_report_page())
        
        # Show import page by default
        self.content_stack.setCurrentIndex(0)
        
        return content_widget
    
    def create_import_page(self):
        """Create modern data import page with all controls accessible"""
        page = QWidget()
        page.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
            }
        """)
        main_layout = QVBoxLayout(page)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Header section
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)
        title_label = QLabel("📊 Veri İçe Aktarma")
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #2c3e50;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        self.import_status_label = QLabel("Hazır")
        self.import_status_label.setStyleSheet("font-size: 12px; font-weight: 500; color: #6c757d; background-color: #f8f9fa; padding: 4px 8px; border-radius: 4px; border: 1px solid #dee2e6;")
        header_layout.addWidget(self.import_status_label)
        main_layout.addWidget(header_widget)

        # File selection section
        file_section = QWidget()
        file_layout = QHBoxLayout(file_section)
        file_layout.setSpacing(8)
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Dosya yolunu seçin veya sürükleyip bırakın...")
        self.file_path_edit.setStyleSheet("padding: 12px 16px; border: 2px solid #e9ecef; border-radius: 8px; font-size: 14px; background-color: #f8f9fa;")
        file_layout.addWidget(self.file_path_edit)
        browse_btn = QPushButton("Gözat")
        browse_btn.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #007bff, stop:1 #0056b3); color: white; border: none; border-radius: 8px; padding: 12px 20px; font-weight: 600; font-size: 14px; min-width: 80px;")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        main_layout.addWidget(file_section)

        # Format selection section
        format_section = QWidget()
        format_layout = QHBoxLayout(format_section)
        format_layout.setSpacing(8)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Excel (.xlsx)", "CSV (.csv)", "JSON (.json)"])
        self.format_combo.setStyleSheet("padding: 10px 12px; border: 2px solid #e9ecef; border-radius: 8px; font-size: 14px; background-color: white;")
        format_layout.addWidget(self.format_combo)
        self.sheet_widget = QWidget()
        sheet_layout = QHBoxLayout(self.sheet_widget)
        sheet_layout.setSpacing(8)
        sheet_label = QLabel("Sayfa:")
        sheet_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #495057;")
        sheet_layout.addWidget(sheet_label)
        self.sheet_combo = QComboBox()
        self.sheet_combo.setStyleSheet("padding: 8px 10px; border: 2px solid #e9ecef; border-radius: 6px; font-size: 13px; background-color: white;")
        sheet_layout.addWidget(self.sheet_combo)
        self.sheet_widget.setVisible(False)
        format_layout.addWidget(self.sheet_widget)
        main_layout.addWidget(format_section)

        # Amount/currency column selection
        self.amount_column_combo = QComboBox()
        self.amount_column_combo.setStyleSheet("padding: 8px 10px; border: 2px solid #e9ecef; border-radius: 6px; font-size: 13px; background-color: white;")
        self.amount_column_combo.setMinimumWidth(180)
        main_layout.addWidget(QLabel("Ödeme Tutarı Sütunu:"))
        main_layout.addWidget(self.amount_column_combo)
        self.currency_column_combo = QComboBox()
        self.currency_column_combo.setStyleSheet("padding: 8px 10px; border: 2px solid #e9ecef; border-radius: 6px; font-size: 13px; background-color: white;")
        self.currency_column_combo.setMinimumWidth(180)
        main_layout.addWidget(QLabel("Döviz Sütunu:"))
        main_layout.addWidget(self.currency_column_combo)

        # Import button
        import_btn = QPushButton("Veri İçe Aktar")
        import_btn.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #28a745, stop:1 #1e7e34); color: white; border: none; border-radius: 8px; padding: 14px 20px; font-weight: 600; font-size: 15px;")
        import_btn.clicked.connect(self.start_import)
        main_layout.addWidget(import_btn)

        # Progress section
        progress_section = self.create_progress_section()
        main_layout.addWidget(progress_section)

        # Data preview section
        right_panel = self.create_modern_data_preview()
        main_layout.addWidget(right_panel, stretch=1)  # Make preview expand
        self.import_right_panel = right_panel

        # Process button (initially hidden)
        self.process_btn = QPushButton("✅ Veriyi İşle")
        self.process_btn.setVisible(False)
        self.process_btn.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #17a2b8, stop:1 #138496); color: white; border: none; border-radius: 6px; padding: 10px 16px; font-weight: 600; font-size: 13px;")
        self.process_btn.clicked.connect(self.process_imported_data)
        main_layout.addWidget(self.process_btn)
        return page
    
    def create_import_header(self):
        """Create minimal header section - no blue bar, more space for data"""
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        """)
        
        layout = QHBoxLayout(header_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Minimal title
        title_label = QLabel("📊 Veri İçe Aktarma")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: #2c3e50;
                background: none;
                border: none;
                padding: 0px;
            }
        """)
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # Minimal status indicator
        self.import_status_label = QLabel("Hazır")
        self.import_status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 500;
                color: #6c757d;
                background-color: #f8f9fa;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #dee2e6;
            }
        """)
        layout.addWidget(self.import_status_label)
        
        return header_widget
    
    def create_modern_import_controls(self):
        """Create modern, compact import controls panel"""
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e9ecef;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)  # Reduced margins
        layout.setSpacing(12)  # Reduced spacing
        
        # Section title
        title_label = QLabel("Dosya Seçimi")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #2c3e50;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(title_label)
        
        # File selection section
        file_section = self.create_file_selection_section()
        layout.addWidget(file_section)
        
        # Format selection section
        format_section = self.create_format_selection_section()
        layout.addWidget(format_section)
        
        # Action buttons section
        action_section = self.create_action_buttons_section()
        layout.addWidget(action_section)
        
        # Progress section
        progress_section = self.create_progress_section()
        layout.addWidget(progress_section)
        
        layout.addStretch()
        return panel
    
    def create_file_selection_section(self):
        """Create file selection section"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # File path input
        file_layout = QHBoxLayout()
        file_layout.setSpacing(8)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Dosya yolunu seçin veya sürükleyip bırakın...")
        self.file_path_edit.setStyleSheet("""
            QLineEdit {
                padding: 12px 16px;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                font-size: 14px;
                background-color: #f8f9fa;
            }
            QLineEdit:focus {
                border-color: #007bff;
                background-color: white;
            }
        """)
        file_layout.addWidget(self.file_path_edit)
        
        # Browse button
        browse_btn = QPushButton("Gözat")
        browse_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007bff, stop:1 #0056b3);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 14px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0056b3, stop:1 #004085);
            }
            QPushButton:pressed {
                background: #004085;
            }
        """)
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        
        layout.addLayout(file_layout)
        return section
    
    def create_format_selection_section(self):
        """Create format selection section"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Format label
        format_label = QLabel("Dosya Formatı")
        format_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 600;
                color: #495057;
            }
        """)
        layout.addWidget(format_label)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_layout.setSpacing(8)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Excel (.xlsx)", "CSV (.csv)", "JSON (.json)"])
        self.format_combo.setStyleSheet("""
            QComboBox {
                padding: 10px 12px;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
            }
            QComboBox:focus {
                border-color: #007bff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #6c757d;
                margin-right: 5px;
            }
        """)
        format_layout.addWidget(self.format_combo)
        
        # Sheet selection (for XLSX files)
        self.sheet_widget = QWidget()
        sheet_layout = QHBoxLayout(self.sheet_widget)
        sheet_layout.setContentsMargins(0, 0, 0, 0)
        sheet_layout.setSpacing(8)
        
        sheet_label = QLabel("Sayfa:")
        sheet_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #495057;")
        sheet_layout.addWidget(sheet_label)
        
        self.sheet_combo = QComboBox()
        self.sheet_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 10px;
                border: 2px solid #e9ecef;
                border-radius: 6px;
                font-size: 13px;
                background-color: white;
            }
            QComboBox:focus {
                border-color: #007bff;
            }
        """)
        sheet_layout.addWidget(self.sheet_combo)
        self.sheet_widget.setVisible(False)
        format_layout.addWidget(self.sheet_widget)
        
        layout.addLayout(format_layout)
        # Add dropdowns for selecting amount and currency columns
        self.amount_column_combo = QComboBox()
        self.amount_column_combo.setStyleSheet("""
QComboBox {
    padding: 8px 10px;
    border: 2px solid #e9ecef;
    border-radius: 6px;
    font-size: 13px;
    background-color: white;
}
QComboBox:focus {
    border-color: #007bff;
}
""")
        self.amount_column_combo.setMinimumWidth(180)
        layout.addWidget(QLabel("Ödeme Tutarı Sütunu:"))
        layout.addWidget(self.amount_column_combo)

        self.currency_column_combo = QComboBox()
        self.currency_column_combo.setStyleSheet("""
QComboBox {
    padding: 8px 10px;
    border: 2px solid #e9ecef;
    border-radius: 6px;
    font-size: 13px;
    background-color: white;
}
QComboBox:focus {
    border-color: #007bff;
}
""")
        self.currency_column_combo.setMinimumWidth(180)
        layout.addWidget(QLabel("Döviz Sütunu:"))
        layout.addWidget(self.currency_column_combo)
        return section
    
    def create_action_buttons_section(self):
        """Create action buttons section"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Import button
        import_btn = QPushButton("📥 Veriyi İçe Aktar")
        import_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #1e7e34);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px 20px;
                font-weight: 600;
                font-size: 15px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34ce57, stop:1 #28a745);
            }
            QPushButton:pressed {
                background: #1e7e34;
            }
        """)
        import_btn.clicked.connect(self.start_import)
        layout.addWidget(import_btn)
        
        # Action buttons row
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        
        # Process button (initially hidden)
        self.process_btn = QPushButton("✅ Veriyi İşle")
        self.process_btn.setVisible(False)
        self.process_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #17a2b8, stop:1 #138496);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #20c997, stop:1 #17a2b8);
            }
        """)
        self.process_btn.clicked.connect(self.process_imported_data)
        action_layout.addWidget(self.process_btn)
        
        # Clear button (initially hidden)
        self.clear_btn = QPushButton("🗑️ Temizle")
        self.clear_btn.setVisible(False)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc3545, stop:1 #c82333);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #dc3545);
            }
        """)
        self.clear_btn.clicked.connect(self.clear_data_preview)
        action_layout.addWidget(self.clear_btn)
        
        layout.addLayout(action_layout)
        return section
    
    def create_progress_section(self):
        """Create progress section"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e9ecef;
                border-radius: 8px;
                text-align: center;
                font-weight: 600;
                font-size: 12px;
                background-color: #f8f9fa;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #007bff, stop:1 #0056b3);
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        return section
    
    def create_modern_data_preview(self):
        """Create modern, maximized data preview panel with Excel-like filtering"""
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e9ecef;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)  # Minimal margins for maximum space
        layout.setSpacing(10)  # Reduced spacing
        
        # Advanced filtering controls
        filter_layout = QHBoxLayout()
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Tüm sütunlarda ara...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                font-size: 14px;
                background-color: white;
                min-width: 200px;
            }
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
            }
        """)
        self.search_box.textChanged.connect(self.filter_preview_table)
        filter_layout.addWidget(QLabel("Ara:"))
        filter_layout.addWidget(self.search_box)
        
        # Column filter dropdown
        self.column_filter_combo = QComboBox()
        self.column_filter_combo.addItem("Tüm Sütunlar")
        self.column_filter_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                font-size: 14px;
                background-color: white;
                min-width: 150px;
            }
            QComboBox:focus {
                border-color: #007bff;
            }
        """)
        self.column_filter_combo.currentTextChanged.connect(self.filter_preview_table)
        filter_layout.addWidget(QLabel("Sütun:"))
        filter_layout.addWidget(self.column_filter_combo)
        
        # Advanced filter button
        self.advanced_filter_btn = QPushButton("Gelişmiş Filtre")
        self.advanced_filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.advanced_filter_btn.clicked.connect(self.show_advanced_filter_dialog)
        filter_layout.addWidget(self.advanced_filter_btn)
        
        # Clear filters button
        self.clear_filters_btn = QPushButton("Filtreleri Temizle")
        self.clear_filters_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.clear_filters_btn.clicked.connect(self.clear_preview_filters)
        filter_layout.addWidget(self.clear_filters_btn)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Preview header
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("📋 Veri Önizleme")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #2c3e50;
            }
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Results count
        self.preview_count_label = QLabel("0 kayıt")
        self.preview_count_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 500;
                color: #6c757d;
                background-color: #f8f9fa;
                padding: 6px 12px;
                border-radius: 20px;
                border: 1px solid #e9ecef;
            }
        """)
        header_layout.addWidget(self.preview_count_label)
        
        layout.addLayout(header_layout)
        
        # Data preview table with Excel-like features
        self.data_preview_table = QTableWidget()
        self.data_preview_table.setVisible(False)
        self.data_preview_table.setAlternatingRowColors(True)
        self.data_preview_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.data_preview_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.data_preview_table.setSortingEnabled(True)
        self.data_preview_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.data_preview_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        
        # Enable context menu for Excel-like features
        self.data_preview_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.data_preview_table.customContextMenuRequested.connect(self.show_preview_context_menu)
        
        self.data_preview_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                gridline-color: #f1f3f4;
                font-size: 13px;
                selection-background-color: #e3f2fd;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #f1f3f4;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QTableWidget::item:hover {
                background-color: #f8f9fa;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                padding: 12px 8px;
                border: 1px solid #dee2e6;
                font-weight: 600;
                color: #495057;
                font-size: 13px;
            }
            QHeaderView::section:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e9ecef, stop:1 #dee2e6);
            }
        """)
        layout.addWidget(self.data_preview_table)
        
        # Info messages
        self.preview_info_label = QLabel("")
        self.preview_info_label.setVisible(False)
        self.preview_info_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #d1ecf1, stop:1 #bee5eb);
                color: #0c5460;
                padding: 12px 16px;
                border-radius: 8px;
                border-left: 4px solid #17a2b8;
                font-weight: 500;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.preview_info_label)
        
        # Duplicate info
        self.duplicate_info_label = QLabel("")
        self.duplicate_info_label.setVisible(False)
        self.duplicate_info_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fff3cd, stop:1 #ffeaa7);
                color: #856404;
                padding: 12px 16px;
                border-radius: 8px;
                border-left: 4px solid #ffc107;
                font-weight: 500;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.duplicate_info_label)
        
        # Store original data for filtering
        self.original_preview_data = []
        
        return panel
    
    def update_import_layout_responsiveness(self):
        """Update import layout for different screen sizes"""
        if not hasattr(self, 'import_content_splitter'):
            return
        
        # Get current window size
        window_width = self.width()
        
        # Adjust layout based on window size - prioritize data preview
        if window_width < 1200:
            # Smaller screens - ultra compact left panel
            self.import_left_panel.setMaximumWidth(280)
            self.import_content_splitter.setSizes([280, window_width - 300])
        elif window_width < 1600:
            # Medium screens - compact left panel
            self.import_left_panel.setMaximumWidth(300)
            self.import_content_splitter.setSizes([300, window_width - 320])
        else:
            # Large screens - still compact left panel for maximum data space
            self.import_left_panel.setMaximumWidth(320)
            self.import_content_splitter.setSizes([320, window_width - 340])
    
    def resizeEvent(self, event):
        """Handle window resize events for responsive design"""
        super().resizeEvent(event)
        self.update_import_layout_responsiveness()
    
    def create_data_preview_widget(self):
        """Create data preview widget for import page"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Data preview table
        self.data_preview_table = QTableWidget()
        self.data_preview_table.setVisible(False)
        self.data_preview_table.setAlternatingRowColors(True)
        self.data_preview_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.data_preview_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                gridline-color: #E9ECEF;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #E9ECEF;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
            QHeaderView::section {
                background-color: #F8F9FA;
                padding: 8px;
                border: 1px solid #DEE2E6;
                font-weight: 600;
                color: #495057;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.data_preview_table)
        
        # Preview info label
        self.preview_info_label = QLabel("")
        self.preview_info_label.setVisible(False)
        self.preview_info_label.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                color: #1976D2;
                padding: 8px;
                border-radius: 4px;
                border-left: 4px solid #2196F3;
                font-weight: 600;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.preview_info_label)
        
        # Duplicate information area
        self.duplicate_info_label = QLabel("")
        self.duplicate_info_label.setVisible(False)
        self.duplicate_info_label.setStyleSheet("""
            QLabel {
                background-color: #FFF3CD;
                color: #856404;
                padding: 8px;
                border-radius: 4px;
                border-left: 4px solid #FFC107;
                font-weight: 600;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.duplicate_info_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Process Data button (initially hidden)
        self.process_btn = QPushButton("Veriyi İşle")
        self.process_btn.setMaximumHeight(32)
        self.process_btn.setVisible(False)
        self.process_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px; 
                font-weight: 600;
                background: #28A745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: #34CE57;
            }
        """)
        self.process_btn.setToolTip("Önizlenen veriyi sisteme işler")
        self.process_btn.clicked.connect(self.process_imported_data)
        button_layout.addWidget(self.process_btn)
        
        # Clear Screen button (initially hidden)
        self.clear_btn = QPushButton("Temizle")
        self.clear_btn.setMaximumHeight(32)
        self.clear_btn.setVisible(False)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px; 
                font-weight: 600;
                background: #DC3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: #E74C3C;
            }
        """)
        self.clear_btn.setToolTip("Önizleme ekranını temizler")
        self.clear_btn.clicked.connect(self.clear_data_preview)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        return widget
    
    def create_stats_page(self):
        """Create the statistics page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        
        # Page title
        title = QLabel("Veri İstatistikleri")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: 700;
            color: #2C3E50;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # Stats content will be populated by update_stats_display
        self.stats_content = QLabel("Veri yükleniyor...")
        self.stats_content.setStyleSheet("""
            font-size: 16px;
            color: #7F8C8D;
            padding: 40px;
            background: white;
            border-radius: 12px;
            border: 1px solid #E9ECEF;
        """)
        layout.addWidget(self.stats_content)
        
        layout.addStretch()
        return page
    
    def create_report_page(self):
        """Create the report generation page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        
        # Page title
        title = QLabel("Rapor Oluşturma")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: 700;
            color: #2C3E50;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # Date range card
        date_card = self.create_card("Tarih Aralığı", self.create_date_controls())
        layout.addWidget(date_card)
        
        # Report options card
        options_card = self.create_card("Rapor Seçenekleri", self.create_report_controls())
        layout.addWidget(options_card)
        
        layout.addStretch()
        return page
    
    def create_data_table_page(self):
        """Create the data table page with tab widget"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Page title
        title = QLabel("Veri Tablosu")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: 700;
            color: #2C3E50;
            margin-bottom: 20px;
        """)
        layout.addWidget(title)
        
        # Create tab widget for data table and conversion details
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumHeight(700)
        layout.addWidget(self.tab_widget)
        
        # Create main data table tab
        data_table_widget = QWidget()
        data_table_layout = QVBoxLayout(data_table_widget)
        
        # Create data table
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.setSortingEnabled(True)
        self.data_table.verticalHeader().setVisible(False)
        
        # Enable context menu for advanced features
        self.data_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.data_table.customContextMenuRequested.connect(self.show_table_context_menu)
        
        # Enable Excel-like column header filtering
        self.data_table.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.data_table.horizontalHeader().customContextMenuRequested.connect(self.show_column_filter_menu)
        
        data_table_layout.addWidget(self.data_table)
        
        # Add data table tab
        self.tab_widget.addTab(data_table_widget, "Ana Veri Tablosu")
        
        return page
    
    def create_preview_page(self):
        """Create the report preview page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Page title with buttons
        title_layout = QHBoxLayout()
        
        # Page title
        title = QLabel("Rapor Önizleme")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: 700;
            color: #2C3E50;
            margin-bottom: 20px;
        """)
        title_layout.addWidget(title)
        
        # Add stretch to push buttons to the right
        title_layout.addStretch()
        
        # Print button
        print_btn = QPushButton("Yazdır")
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QPushButton:pressed {
                background-color: #21618C;
            }
        """)
        print_btn.clicked.connect(self.print_current_report)
        title_layout.addWidget(print_btn)
        
        # Export PDF button
        export_pdf_btn = QPushButton("PDF Olarak Kaydet")
        export_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
                min-width: 140px;
                margin-left: 10px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QPushButton:pressed {
                background-color: #A93226;
            }
        """)
        export_pdf_btn.clicked.connect(self.print_to_pdf)
        title_layout.addWidget(export_pdf_btn)
        
        # Export Excel button
        export_excel_btn = QPushButton("Excel Olarak Kaydet")
        export_excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
                min-width: 150px;
                margin-left: 10px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1E8449;
            }
        """)
        export_excel_btn.clicked.connect(self.export_to_excel)
        title_layout.addWidget(export_excel_btn)
        
        layout.addLayout(title_layout)
        
        # Preview content (will be set up later)  
        self.report_tabs = QTabWidget()
        self.report_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #C0C0C0;
                background-color: white;
                border-radius: 8px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background: #F0F0F0;
                border: 1px solid #C0C0C0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
                color: #2C3E50;
                font-weight: 700;
            }
            QTabBar::tab:hover:!selected {
                background: #E8F4FD;
                color: #2C3E50;
            }
        """)
        layout.addWidget(self.report_tabs)
        
        return page
    
    def create_monthly_report_page(self):
        """Create the monthly report page with PROJECT_A, PROJECT_B, and Total tables"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        
        # Page title
        title = QLabel("Aylık Rapor")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: 700;
            color: #2C3E50;
            margin-bottom: 20px;
        """)
        layout.addWidget(title)
        
        # Create scroll area for monthly reports
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container for monthly reports
        self.monthly_reports_container = QWidget()
        self.monthly_reports_layout = QVBoxLayout(self.monthly_reports_container)
        self.monthly_reports_layout.setSpacing(30)
        
        scroll_area.setWidget(self.monthly_reports_container)
        layout.addWidget(scroll_area)
        
        # Initialize monthly reports
        self.update_monthly_reports()
        
        return page
    
    def create_card(self, title, content_widget):
        """Create a modern card widget"""
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet("""
            QWidget#card {
                background: white;
                border-radius: 12px;
                border: 1px solid #E9ECEF;
            }
            QWidget#card:hover {
                border-color: #3498DB;
                border-width: 2px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Card title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: 600;
            color: #2C3E50;
            margin-bottom: 10px;
        """)
        layout.addWidget(title_label)
        
        # Card content
        layout.addWidget(content_widget)
        
        return card
    
    # Sidebar navigation methods
    def show_import_section(self):
        self.content_stack.setCurrentIndex(0)
        
    def show_data_table_section(self):
        self.content_stack.setCurrentIndex(2)
        # Disable currency conversion to prevent freezing
        self.currency_conversion_enabled = False
        # Update data table when switching to this section
        logger.info("Switching to data table section, updating table")
        self.update_data_table()
        
    def show_stats_section(self):
        self.content_stack.setCurrentIndex(3)
        self.update_stats_display()
        
    def show_report_section(self):
        self.content_stack.setCurrentIndex(4)
        
    def show_preview_section(self):
        self.content_stack.setCurrentIndex(4)
        # Completely disable currency conversion for preview tab to prevent freezing
        self.currency_conversion_enabled = False
        # Update preview with current data
        self.update_report_preview()
        
    def show_monthly_report_section(self):
        self.content_stack.setCurrentIndex(5)
        # Disable currency conversion to prevent freezing
        self.currency_conversion_enabled = False
        # Update monthly reports when showing the section
        self.update_monthly_reports()
        
    def show_calendar_section(self):
        # Placeholder for calendar
        pass
        
    def show_settings_section(self):
        # Placeholder for settings
        pass
        
    def toggle_sidebar(self):
        """Toggle sidebar collapsed/expanded state"""
        current_width = self.sidebar.width()
        if current_width > 100:
            # Collapse
            self.sidebar.setFixedWidth(60)
        else:
            # Expand
            self.sidebar.setFixedWidth(280)
    
    def create_import_controls(self):
        """Create import controls widget with optimized layout"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)  # Reduced spacing
        layout.setContentsMargins(10, 10, 10, 10)  # Reduced margins
        
        # Compact file selection row
        file_layout = QHBoxLayout()
        file_layout.setSpacing(8)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Dosya seçiniz...")
        self.file_path_edit.setMaximumHeight(32)  # Reduced height
        file_layout.addWidget(self.file_path_edit)
        
        browse_btn = QPushButton("Gözat")
        browse_btn.setMaximumHeight(32)
        browse_btn.setMaximumWidth(80)  # Fixed width
        browse_btn.clicked.connect(self.browse_file)
        browse_btn.setStyleSheet("""
            QPushButton {
                background: #3498DB;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #2980B9;
            }
        """)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)
        
        # Compact format and sheet selection row
        format_layout = QHBoxLayout()
        format_layout.setSpacing(8)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Excel (.xlsx)", "CSV (.csv)", "JSON (.json)"])
        self.format_combo.setMaximumHeight(32)
        format_layout.addWidget(QLabel("Format:"))
        format_layout.addWidget(self.format_combo)
        
        # Sheet selection (for XLSX files)
        self.sheet_widget = QWidget()
        sheet_layout = QHBoxLayout(self.sheet_widget)
        sheet_layout.setContentsMargins(0, 0, 0, 0)
        sheet_layout.addWidget(QLabel("Sayfa:"))
        self.sheet_combo = QComboBox()
        self.sheet_combo.setMaximumHeight(32)
        sheet_layout.addWidget(self.sheet_combo)
        self.sheet_widget.setVisible(False)
        format_layout.addWidget(self.sheet_widget)
        
        layout.addLayout(format_layout)
        
        # Compact import button
        import_btn = QPushButton("Veri İçe Aktar")
        import_btn.setMaximumHeight(32)
        import_btn.clicked.connect(self.start_import)
        import_btn.setStyleSheet("""
            QPushButton {
                background: #27AE60;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #229954;
            }
        """)
        layout.addWidget(import_btn)
        
        # Compact progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)
        layout.addWidget(self.progress_bar)
        
        # Maximized data preview table
        self.data_preview_table = QTableWidget()
        self.data_preview_table.setVisible(False)
        self.data_preview_table.setAlternatingRowColors(True)
        self.data_preview_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.data_preview_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                gridline-color: #E9ECEF;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #E9ECEF;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
            QHeaderView::section {
                background-color: #F8F9FA;
                padding: 8px;
                border: 1px solid #DEE2E6;
                font-weight: 600;
                color: #495057;
                font-size: 11px;
            }
        """)
        # Remove height restriction - let it expand
        layout.addWidget(self.data_preview_table)
        
        # Preview info label
        self.preview_info_label = QLabel("")
        self.preview_info_label.setVisible(False)
        self.preview_info_label.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                color: #1976D2;
                padding: 10px;
                border-radius: 6px;
                border-left: 4px solid #2196F3;
                font-weight: 600;
            }
        """)
        layout.addWidget(self.preview_info_label)
        
        # Duplicate information area
        self.duplicate_info_label = QLabel("")
        self.duplicate_info_label.setVisible(False)
        self.duplicate_info_label.setStyleSheet("""
            QLabel {
                background-color: #FFF3CD;
                color: #856404;
                padding: 10px;
                border-radius: 6px;
                border-left: 4px solid #FFC107;
                font-weight: 600;
            }
        """)
        layout.addWidget(self.duplicate_info_label)
        
        # Compact action buttons row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Process Data button (initially hidden)
        self.process_btn = QPushButton("Veriyi İşle")
        self.process_btn.setMaximumHeight(32)
        self.process_btn.setVisible(False)
        self.process_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px; 
                font-weight: 600;
                background: #28A745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: #34CE57;
            }
        """)
        self.process_btn.setToolTip("Önizlenen veriyi sisteme işler")
        self.process_btn.clicked.connect(self.process_imported_data)
        button_layout.addWidget(self.process_btn)
        
        # Clear Screen button (initially hidden)
        self.clear_btn = QPushButton("Temizle")
        self.clear_btn.setMaximumHeight(32)
        self.clear_btn.setVisible(False)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px; 
                font-weight: 600;
                background: #DC3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: #E74C3C;
            }
        """)
        self.clear_btn.setToolTip("Önizleme ekranını temizler")
        self.clear_btn.clicked.connect(self.clear_data_preview)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        return widget
    
    def create_date_controls(self):
        """Create date range controls widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Date range
        date_layout = QHBoxLayout()
        
        # Start date
        start_layout = QVBoxLayout()
        start_layout.addWidget(QLabel("Başlangıç Tarihi:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))
        self.start_date_edit.setMinimumHeight(40)
        self.start_date_edit.setCalendarPopup(True)
        start_layout.addWidget(self.start_date_edit)
        date_layout.addLayout(start_layout)
        
        # End date
        end_layout = QVBoxLayout()
        end_layout.addWidget(QLabel("Bitiş Tarihi:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setMinimumHeight(40)
        self.end_date_edit.setCalendarPopup(True)
        end_layout.addWidget(self.end_date_edit)
        date_layout.addLayout(end_layout)
        
        layout.addLayout(date_layout)
        return widget
    
    def create_report_controls(self):
        """Create report generation controls widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Report type selection
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems(["Tüm Raporlar", "Haftalık", "Aylık"])
        self.report_type_combo.setMinimumHeight(40)
        layout.addWidget(self.report_type_combo)
        
        # Generate button
        generate_btn = QPushButton("Rapor Oluştur")
        generate_btn.setMinimumHeight(45)
        generate_btn.clicked.connect(self.generate_report_from_controls)
        generate_btn.setStyleSheet("""
            QPushButton {
                background: #E74C3C;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 700;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #C0392B;
            }
        """)
        layout.addWidget(generate_btn)
        
        return widget
    
    def generate_report_from_controls(self):
        """Generate report based on control selections"""
        report_type_map = {
            "Tüm Raporlar": "all",
            "Haftalık": "weekly", 
            "Aylık": "monthly"
        }
        report_type = report_type_map[self.report_type_combo.currentText()]
        self.generate_report(report_type)
        # Update preview with current data
        self.update_report_preview()
        self.show_preview_section()  # Switch to preview after generating
    
    def update_stats_display(self):
        """Update the statistics display with current data"""
        if hasattr(self, 'stats_content'):
            stats = self.storage.get_statistics()
            
            # Format currency function
            def format_currency(amount, currency_symbol=""):
                """Format currency with proper Turkish number formatting"""
                if amount >= 1_000_000:
                    return f"{currency_symbol}{amount/1_000_000:.1f}M"
                elif amount >= 1_000:
                    return f"{currency_symbol}{amount/1_000:.1f}K"
                else:
                    return f"{currency_symbol}{amount:,.0f}"
            
            # Format currency
            tl_formatted = format_currency(stats['total_amount_tl'], "₺")
            usd_formatted = format_currency(stats['total_amount_usd'], "$")
            
            stats_html = f"""
            <div style="font-family: 'Segoe UI', Arial; font-size: 16px; line-height: 1.8;">
                <div style="margin-bottom: 25px;">
                    <h2>Mali Durum</h2>
                    <p><strong>Toplam Kayıt:</strong> <span style="color: #27AE60; font-size: 18px;">{stats['total_payments']:,} adet</span></p>
                    <p><strong>TL Tutarı:</strong> <span style="color: #3498DB; font-size: 18px;">{tl_formatted}</span></p>
                    <p><strong>USD Tutarı:</strong> <span style="color: #27AE60; font-size: 18px;">{usd_formatted}</span></p>
                </div>
                
                <div style="margin-bottom: 25px;">
                    <h2 style="color: #2C3E50; margin-bottom: 15px;">🏢 Proje Bilgileri</h2>
                    <p><strong>Projeler:</strong> <span style="color: #8E44AD; font-size: 18px;">{stats['projects']}</span></p>
                    <p><strong>Müşteriler:</strong> <span style="color: #8E44AD; font-size: 18px;">{stats['customers']}</span></p>
                </div>
            </div>
            """
            
            if stats['date_range']:
                stats_html += f"""
                <div style="background: rgba(255, 193, 7, 0.1); padding: 15px; border-radius: 8px; border-left: 4px solid #FFC107;">
                    <h3>Veri Aralığı</h3>
                    <p style="margin: 0;">{stats['date_range']['start']} - {stats['date_range']['end']}</p>
                </div>
                """
            
            self.stats_content.setText(stats_html)
            self.stats_content.setTextFormat(Qt.RichText)
    
    def create_modern_left_panel(self):
        """Create modern left control panel with logical grouping and responsive design"""
        panel = QWidget()
        
        # Enhanced panel styling with better visual hierarchy
        panel.setObjectName("leftPanel")
        panel.setStyleSheet("""
            QWidget#leftPanel {
                background-color: #F8F9FA;
                border-radius: 12px;
                border: 1px solid #DEE2E6;
                margin: 5px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(25, 25, 25, 25)  # More generous margins
        layout.setSpacing(25)  # Better visual separation between sections
        
        # DATA IMPORT SECTION with Form Layout for better alignment
        import_group = QGroupBox("📁 Veri İçe Aktarma")
        import_group.setToolTip("Ödeme verilerini Excel, CSV veya JSON formatında içe aktarın")
        from PySide6.QtWidgets import QFormLayout
        import_layout = QFormLayout(import_group)
        import_layout.setContentsMargins(20, 25, 20, 20)
        import_layout.setSpacing(15)
        import_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # File selection with improved layout
        file_label = QLabel("Dosya Seçimi:")
        file_label.setStyleSheet("font-weight: 600; color: #495057; font-size: 14px;")
        
        # File selection container
        file_container = QWidget()
        file_container_layout = QHBoxLayout(file_container)
        file_container_layout.setContentsMargins(0, 0, 0, 0)
        file_container_layout.setSpacing(10)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Excel, CSV veya JSON dosyası seçiniz...")
        self.file_path_edit.setMinimumHeight(50)
        self.file_path_edit.setToolTip("Desteklenen formatlar: .xlsx, .csv, .json")
        file_container_layout.addWidget(self.file_path_edit, 3)
        
        browse_btn = QPushButton("📂 Gözat")
        browse_btn.setMinimumHeight(50)
        browse_btn.setMinimumWidth(100)
        browse_btn.setToolTip("Dosya seçmek için tıklayın")
        browse_btn.clicked.connect(self.browse_file)
        file_container_layout.addWidget(browse_btn, 1)
        
        import_layout.addRow(file_label, file_container)
        
        # File format selection
        format_label = QLabel("Dosya Formatı:")
        format_label.setStyleSheet("font-weight: 600; color: #495057; font-size: 14px;")
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Excel (.xlsx)", "CSV (.csv)", "JSON (.json)"])
        self.format_combo.setMinimumHeight(50)
        self.format_combo.setToolTip("Dosya formatını seçiniz")
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        import_layout.addRow(format_label, self.format_combo)
        
        # Sheet selection (for XLSX) - initially hidden
        sheet_label = QLabel("Çalışma Sayfası:")
        sheet_label.setStyleSheet("font-weight: 600; color: #495057; font-size: 14px;")
        
        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumHeight(50)
        self.sheet_combo.setToolTip("Excel dosyasındaki çalışma sayfasını seçiniz")
        
        # Initially hide sheet selection
        sheet_label.setVisible(False)
        self.sheet_combo.setVisible(False)
        self.sheet_label = sheet_label  # Store reference for show/hide
        
        import_layout.addRow(sheet_label, self.sheet_combo)
        
        # Import button with enhanced styling
        import_btn = QPushButton("📥 Veriyi İçe Aktar")
        import_btn.setMinimumHeight(55)
        import_btn.setStyleSheet("""
            QPushButton {
                font-size: 15px; 
                font-weight: 700;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #007BFF, stop:1 #0056B3);
                border-radius: 8px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #0056B3, stop:1 #004085);
            }
        """)
        import_btn.setToolTip("Seçilen dosyayı sisteme yükler")
        import_btn.clicked.connect(self.start_import)
        import_layout.addRow("", import_btn)
        
        # Compact action buttons row
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setSpacing(8)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Process Data button (initially hidden)
        self.process_btn = QPushButton("Veriyi İşle")
        self.process_btn.setMaximumHeight(32)
        self.process_btn.setVisible(False)
        self.process_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px; 
                font-weight: 600;
                background: #28A745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: #34CE57;
            }
        """)
        self.process_btn.setToolTip("Önizlenen veriyi sisteme işler")
        self.process_btn.clicked.connect(self.process_imported_data)
        button_layout.addWidget(self.process_btn)
        
        # Clear Screen button (initially hidden)
        self.clear_btn = QPushButton("Temizle")
        self.clear_btn.setMaximumHeight(32)
        self.clear_btn.setVisible(False)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px; 
                font-weight: 600;
                background: #DC3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: #E74C3C;
            }
        """)
        self.clear_btn.setToolTip("Önizleme ekranını temizler")
        self.clear_btn.clicked.connect(self.clear_data_preview)
        button_layout.addWidget(self.clear_btn)
        
        import_layout.addRow("", button_widget)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(25)
        import_layout.addRow("", self.progress_bar)
        
        layout.addWidget(import_group)
        
        # DATA PREVIEW SECTION - Maximized for better visibility
        preview_group = QGroupBox("Veri Önizleme")
        preview_group.setToolTip("İçe aktarılan veriyi önizleyin")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(15, 15, 15, 15)  # Reduced margins
        preview_layout.setSpacing(10)  # Reduced spacing
        
        # Data preview table - Maximized
        self.data_preview_table = QTableWidget()
        self.data_preview_table.setVisible(False)
        self.data_preview_table.setAlternatingRowColors(True)
        self.data_preview_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.data_preview_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                gridline-color: #E9ECEF;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #E9ECEF;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
            QHeaderView::section {
                background-color: #F8F9FA;
                padding: 8px;
                border: 1px solid #DEE2E6;
                font-weight: 600;
                color: #495057;
                font-size: 11px;
            }
        """)
        # Remove height restriction - let it expand to use available space
        preview_layout.addWidget(self.data_preview_table)
        
        # Preview info label
        self.preview_info_label = QLabel("")
        self.preview_info_label.setVisible(False)
        self.preview_info_label.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                color: #1976D2;
                padding: 10px;
                border-radius: 6px;
                border-left: 4px solid #2196F3;
                font-weight: 600;
            }
        """)
        preview_layout.addWidget(self.preview_info_label)
        
        layout.addWidget(preview_group)
        
        # DATE RANGE SECTION with Form Layout
        date_group = QGroupBox("Tarih Aralığı Seçimi")
        date_group.setToolTip("Raporlama için tarih aralığını belirleyin")
        date_layout = QFormLayout(date_group)
        date_layout.setContentsMargins(20, 25, 20, 20)
        date_layout.setSpacing(15)
        date_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # Start date with enhanced styling
        start_label = QLabel("Başlangıç Tarihi:")
        start_label.setStyleSheet("font-weight: 600; color: #495057; font-size: 14px;")
        
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setMinimumHeight(50)
        self.start_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.start_date_edit.setToolTip("Rapor başlangıç tarihini seçiniz (Varsayılan: 30 gün öncesi)")
        date_layout.addRow(start_label, self.start_date_edit)
        
        # End date
        end_label = QLabel("Bitiş Tarihi:")
        end_label.setStyleSheet("font-weight: 600; color: #495057; font-size: 14px;")
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setMinimumHeight(50)
        self.end_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.end_date_edit.setToolTip("Rapor bitiş tarihini seçiniz (Varsayılan: Bugün)")
        date_layout.addRow(end_label, self.end_date_edit)
        
        layout.addWidget(date_group)
        
        # REPORT GENERATION SECTION with improved organization
        report_group = QGroupBox("Rapor Üretimi")
        report_group.setToolTip("Farklı formatlarda raporlar oluşturun")
        report_layout = QVBoxLayout(report_group)
        report_layout.setContentsMargins(20, 25, 20, 20)
        report_layout.setSpacing(15)
        
        # Format selection with form layout
        format_container = QWidget()
        format_layout = QFormLayout(format_container)
        format_layout.setContentsMargins(0, 0, 0, 0)
        format_layout.setSpacing(10)
        
        format_label = QLabel("Çıktı Formatı:")
        format_label.setStyleSheet("font-weight: 600; color: #495057; font-size: 14px;")
        
        self.report_format_combo = QComboBox()
        self.report_format_combo.addItems([
            "Excel Çalışma Kitabı (.xlsx)", 
            "PDF Belgesi (.pdf)", 
            "Word Belgesi (.docx)", 
            "Tüm Formatlar"
        ])
        self.report_format_combo.setCurrentIndex(0)  # Default to Excel
        self.report_format_combo.setMinimumHeight(50)
        self.report_format_combo.setToolTip("Rapor çıktı formatını seçiniz")
        format_layout.addRow(format_label, self.report_format_combo)
        
        report_layout.addWidget(format_container)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #DEE2E6; margin: 10px 0;")
        report_layout.addWidget(separator)
        
        # SINGLE UNIFIED REPORT BUTTON - NO MORE DUPLICATES
        button_layout = QVBoxLayout()
        button_layout.setSpacing(15)
        
        # MAIN UNIFIED REPORT BUTTON
        unified_report_btn = QPushButton("Rapor Oluştur")
        unified_report_btn.setMinimumHeight(60)
        unified_report_btn.setToolTip("Tüm rapor türleri için birleşik dialog açar (Günlük, Haftalık, Aylık, Özel)")
        unified_report_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #007BFF, stop:1 #0056B3);
                color: white;
                border: none;
                padding: 15px 20px;
                border-radius: 10px;
                font-weight: 700;
                font-size: 15px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #0056B3, stop:1 #004085);
                transform: translateY(-1px);
            }
        """)
        unified_report_btn.clicked.connect(self.show_unified_report_dialog)
        button_layout.addWidget(unified_report_btn)
        
        report_layout.addLayout(button_layout)
        layout.addWidget(report_group)
        
        # STATISTICS SECTION with enhanced display
        stats_group = QGroupBox("Veri İstatistikleri")
        stats_group.setToolTip("Yüklenen verilerin özet bilgileri")
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.setContentsMargins(20, 25, 20, 20)
        stats_layout.setSpacing(10)
        
        # Enhanced stats display with better formatting
        self.stats_label = QLabel("Veri yükleniyor...")
        self.stats_label.setWordWrap(True)
        self.stats_label.setAlignment(Qt.AlignTop)
        self.stats_label.setStyleSheet("""
            QLabel {
                background-color: white;
                padding: 25px;
                border-radius: 12px;
                border: 1px solid #DEE2E6;
                font-size: 14px;
                line-height: 1.8;
                color: #495057;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        self.stats_label.setMinimumHeight(160)
        self.stats_label.setMaximumHeight(200)
        stats_layout.addWidget(self.stats_label)
        
        layout.addWidget(stats_group)
        
        # Stretch to push everything to top
        layout.addStretch()
        
        return panel
    
    def apply_theme(self, dark_mode=False):
        """Apply light or dark theme to the entire application"""
        if dark_mode:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
    
    def apply_light_theme(self):
        """Apply modern light theme"""
        self.setStyleSheet("""
            /* Main Application - Light Theme */
            QMainWindow {
                background-color: #F8F9FA;
                color: #212529;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            /* Menu Bar */
            QMenuBar {
                background-color: #DEE2E6;
                color: #000000;
                border-bottom: 1px solid #ADB5BD;
                padding: 4px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 12px;
                border-radius: 4px;
                color: #000000;
            }
            QMenuBar::item:selected {
                background-color: #ADB5BD;
                color: #000000;
            }
            QMenu {
                background-color: #F8F9FA;
                color: #000000;
                border: 1px solid #ADB5BD;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 8px 16px;
                border-radius: 4px;
                color: #000000;
            }
            QMenu::item:selected {
                background-color: #E9ECEF;
                color: #000000;
            }
            
            /* Toolbar */
            QToolBar {
                background-color: #DEE2E6;
                border-bottom: 1px solid #ADB5BD;
                spacing: 4px;
                padding: 4px;
            }
            QToolBar QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 8px 12px;
                margin: 2px;
                color: #000000;
            }
            QToolBar QToolButton QIcon {
                color: #000000;
            }
            QToolBar QToolButton:hover {
                background-color: #E9ECEF;
                border-color: #CED4DA;
            }
            QToolBar QToolButton:pressed {
                background-color: #DEE2E6;
            }
            
            /* Group Boxes */
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                color: #495057;
                border: 2px solid #DEE2E6;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 20px;
                background-color: #F8F9FA;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 4px 12px;
                background-color: #F8F9FA;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                color: #495057;
            }
            
            /* Buttons */
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #007BFF, stop:1 #0056B3);
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
                min-height: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #0056B3, stop:1 #004085);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #004085, stop:1 #002752);
            }
            QPushButton:disabled {
                background-color: #6C757D;
                color: #ADB5BD;
            }
            
            /* Input Fields */
            QLineEdit, QComboBox, QDateEdit {
                background-color: #F8F9FA;
                border: 2px solid #CED4DA;
                border-radius: 8px;
                padding: 12px;
                color: #495057;
                font-size: 14px;
                min-height: 30px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border-color: #007BFF;
                background-color: #F8F9FF;
            }
            
            /* Status Bar */
            QStatusBar {
                background-color: #F8F9FA;
                color: #495057;
                border-top: 1px solid #DEE2E6;
                font-weight: 500;
            }
            
            /* Tables */
            QTableWidget {
                background-color: #F8F9FA;
                alternate-background-color: #F8F9FA;
                gridline-color: #DEE2E6;
                color: #495057;
                border: 1px solid #DEE2E6;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #F8F9FA;
                color: #495057;
                padding: 12px 8px;
                border: 1px solid #DEE2E6;
                font-weight: 600;
            }
            
            /* Text Edit Widgets - Report Preview */
            QTextEdit {
                background-color: #F8F9FA;
                color: #495057;
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                padding: 15px;
            }
            QTextEdit:focus {
                border-color: #007BFF;
            }
            
            /* Tabs */
            QTabWidget::pane {
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                background-color: #F8F9FA;
                margin-top: 8px;
            }
            QTabBar::tab {
                background-color: #F8F9FA;
                color: #495057;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid #DEE2E6;
                border-bottom: none;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #F8F9FA;
                color: #007BFF;
                border-bottom: 2px solid #007BFF;
            }
            QTabBar::tab:hover:!selected {
                background-color: #E9ECEF;
            }
        """)
    
    def apply_dark_theme(self):
        """Apply modern dark theme"""
        self.setStyleSheet("""
            /* Main Application - Dark Theme */
            QMainWindow {
                background-color: #1A1A1A;
                color: #E9ECEF;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            /* Menu Bar */
            QMenuBar {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border-bottom: 1px solid #404040;
                padding: 4px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 12px;
                border-radius: 4px;
                color: #FFFFFF;
            }
            QMenuBar::item:selected {
                background-color: #404040;
                color: #FFFFFF;
            }
            QMenu {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 8px 16px;
                border-radius: 4px;
                color: #FFFFFF;
            }
            QMenu::item:selected {
                background-color: #404040;
                color: #FFFFFF;
            }
            
            /* Toolbar */
            QToolBar {
                background-color: #2D2D2D;
                border-bottom: 1px solid #404040;
                spacing: 4px;
                padding: 4px;
            }
            QToolBar QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 8px 12px;
                margin: 2px;
                color: #FFFFFF;
            }
            QToolBar QToolButton QIcon {
                color: #FFFFFF;
            }
            QToolBar QToolButton:hover {
                background-color: #404040;
                border-color: #6C757D;
            }
            QToolBar QToolButton:pressed {
                background-color: #495057;
            }
            
            /* Group Boxes */
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                color: #E9ECEF;
                border: 2px solid #404040;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 20px;
                background-color: #2D2D2D;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 4px 12px;
                background-color: #2D2D2D;
                border: 1px solid #404040;
                border-radius: 6px;
                color: #E9ECEF;
            }
            
            /* Buttons */
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #0D6EFD, stop:1 #084298);
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
                min-height: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #0B5ED7, stop:1 #052C65);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #084298, stop:1 #041E42);
            }
            
            /* Input Fields */
            QLineEdit, QComboBox, QDateEdit {
                background-color: #404040;
                border: 2px solid #6C757D;
                border-radius: 8px;
                padding: 12px;
                color: #E9ECEF;
                font-size: 14px;
                min-height: 30px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border-color: #0D6EFD;
                background-color: #495057;
            }
            
            /* Status Bar */
            QStatusBar {
                background-color: #2D2D2D;
                color: #E9ECEF;
                border-top: 1px solid #404040;
                font-weight: 500;
            }
            
            /* Tables */
            QTableWidget {
                background-color: #2D2D2D;
                alternate-background-color: #404040;
                gridline-color: #6C757D;
                color: #E9ECEF;
                border: 1px solid #404040;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #404040;
                color: #E9ECEF;
                padding: 12px 8px;
                border: 1px solid #6C757D;
                font-weight: 600;
            }
            
            /* Text Edit Widgets - Report Preview */
            QTextEdit {
                background-color: #2D2D2D;
                color: #E9ECEF;
                border: 1px solid #404040;
                border-radius: 8px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                padding: 15px;
            }
            QTextEdit:focus {
                border-color: #0D6EFD;
            }
            
            /* Tabs */
            QTabWidget::pane {
                border: 1px solid #404040;
                border-radius: 8px;
                background-color: #2D2D2D;
                margin-top: 8px;
            }
            QTabBar::tab {
                background-color: #404040;
                color: #E9ECEF;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid #6C757D;
                border-bottom: none;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #2D2D2D;
                color: #0D6EFD;
                border-bottom: 2px solid #0D6EFD;
            }
            QTabBar::tab:hover:!selected {
                background-color: #495057;
            }
        """)
    
    def set_theme(self, dark_mode):
        """Set theme and update UI accordingly"""
        self.is_dark_theme = dark_mode
        self.apply_theme(dark_mode)
        self.save_theme_settings()
        
        # Update theme action states
        if hasattr(self, 'light_theme_action'):
            self.light_theme_action.setChecked(not dark_mode)
        if hasattr(self, 'dark_theme_action'):
            self.dark_theme_action.setChecked(dark_mode)
        if hasattr(self, 'theme_toolbar_action'):
            self.theme_toolbar_action.setIcon(qta.icon('fa5s.moon', color='#000000') if not dark_mode else qta.icon('fa5s.sun', color='#000000'))
            self.theme_toolbar_action.setText("Koyu Tema" if not dark_mode else "Açık Tema")
        
        # Update theme status label
        if hasattr(self, 'theme_status_label'):
            self.theme_status_label.setText("🎨 Koyu Tema" if dark_mode else "🎨 Açık Tema")
        
        # Refresh report preview to apply new theme
        if hasattr(self, 'report_tabs') and hasattr(self, 'current_payments'):
            self.update_report_preview()
    
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        self.set_theme(not self.is_dark_theme)
    
    def get_report_preview_style(self):
        """Get consistent styling for report preview widgets"""
        if self.is_dark_theme:
            return """
                QTextEdit {
                    background-color: #2D2D2D;
                    color: #E9ECEF;
                    border: 1px solid #404040;
                    border-radius: 8px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 14px;
                    padding: 20px;
                    selection-background-color: #0D6EFD;
                    selection-color: #FFFFFF;
                }
            """
        else:
            return """
                QTextEdit {
                    background-color: #F8F9FA;
                    color: #495057;
                    border: 1px solid #DEE2E6;
                    border-radius: 8px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 14px;
                    padding: 20px;
                    selection-background-color: #007BFF;
                    selection-color: #FFFFFF;
                }
            """
    
    def apply_theme_to_html(self, html_content):
        """Apply current theme colors to HTML content"""
        if self.is_dark_theme:
            # Dark theme color replacements
            themed_content = html_content.replace(
                'color: #2c3e50', 'color: #E9ECEF'
            ).replace(
                'color: #34495e', 'color: #CED4DA'
            ).replace(
                'color: #495057', 'color: #E9ECEF'
            ).replace(
                'background-color: white', 'background-color: #2D2D2D'
            ).replace(
                'background-color: #ffffff', 'background-color: #2D2D2D'
            ).replace(
                'background-color: #f8f9fa', 'background-color: #404040'
            ).replace(
                'border: 1px solid #bdc3c7', 'border: 1px solid #6C757D'
            ).replace(
                'border: 1px solid #dee2e6', 'border: 1px solid #6C757D'
            )
        else:
            # Light theme - ensure consistent colors
            themed_content = html_content.replace(
                'color: #2c3e50', 'color: #495057'
            ).replace(
                'color: #34495e', 'color: #6C757D'
            ).replace(
                'background-color: white', 'background-color: #FFFFFF'
            ).replace(
                'background-color: #ffffff', 'background-color: #FFFFFF'
            ).replace(
                'background-color: #f8f9fa', 'background-color: #F8F9FA'
            ).replace(
                'border: 1px solid #bdc3c7', 'border: 1px solid #DEE2E6'
            ).replace(
                'border: 1px solid #dee2e6', 'border: 1px solid #DEE2E6'
            )
        
        return themed_content
    
    def setup_window_properties(self):
        """Setup window properties for better UX"""
        # Set window icon (if available)
        try:
            self.setWindowIcon(QIcon(":/icons/app_icon.png"))
        except:
            pass
        
        # Set window flags for better behavior
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        
        # Center window on screen
        self.center_window()
    
    def center_window(self):
        """Center the window on the screen"""
        try:
            from PySide6.QtGui import QScreen
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.geometry()
                window_geometry = self.geometry()
                x = (screen_geometry.width() - window_geometry.width()) // 2
                y = (screen_geometry.height() - window_geometry.height()) // 2
                self.move(x, y)
        except:
            pass
    
    def create_enhanced_status_bar(self):
        """Create enhanced status bar with modern styling"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add permanent widgets to status bar
        self.status_label = QLabel("Sistem Hazır")
        self.status_bar.addWidget(self.status_label)
        
        # Add progress indicator
        self.status_progress = QProgressBar()
        self.status_progress.setVisible(False)
        self.status_progress.setMaximumWidth(200)
        self.status_bar.addPermanentWidget(self.status_progress)
        
        # Add theme indicator
        theme_label = QLabel("🎨 Açık Tema" if not self.is_dark_theme else "🎨 Koyu Tema")
        self.status_bar.addPermanentWidget(theme_label)
        self.theme_status_label = theme_label
        
        # Store status messages for consistent feedback
        self.status_messages = {
            'ready': "Sistem Hazır | Veri yüklemek için dosya seçin",
            'importing': "Veri içe aktarılıyor...",
            'processing': "Veriler işleniyor...",
            'generating_report': "Rapor oluşturuluyor...",
            'saving': "Dosya kaydediliyor...",
            'completed': "İşlem başarıyla tamamlandı",
            'error': "Hata oluştu",
            'data_loaded': lambda count: f"{count:,} kayıt başarıyla yüklendi"
        }
    
    def show_about_dialog(self):
        """Show about dialog"""
        QMessageBox.about(self, "Hakkında", 
                         "Tahsilat Yönetim Sistemi\n\n"
                         "Profesyonel ödeme raporu yönetim uygulaması\n\n"
                         "Sürüm: 3.0\n"
                         "Geliştirici: Tahsilat Ekibi\n\n"
                         "Bu uygulama modern PySide6 teknolojisi ile geliştirilmiştir.")
    
    def show_shortcuts_dialog(self):
        """Show keyboard shortcuts dialog"""
        shortcuts_text = """
        <h3>Klavye Kısayolları</h3>
        <table>
        <tr><td><b>Ctrl+I</b></td><td>Veri İçe Aktar</td></tr>
        <tr><td><b>Ctrl+E</b></td><td>Veri Dışa Aktar</td></tr>
        <tr><td><b>Ctrl+D</b></td><td>Günlük Rapor</td></tr>
        <tr><td><b>Ctrl+W</b></td><td>Haftalık Rapor</td></tr>
        <tr><td><b>Ctrl+M</b></td><td>Aylık Rapor</td></tr>
        <tr><td><b>Ctrl+Shift+R</b></td><td>Tüm Raporlar</td></tr>
        <tr><td><b>Ctrl+U</b></td><td>Döviz Kurları</td></tr>
        <tr><td><b>Ctrl+B</b></td><td>Veri Yedeği</td></tr>
        <tr><td><b>Ctrl+P</b></td><td>PDF Dışa Aktar</td></tr>
        <tr><td><b>F5</b></td><td>Yenile</td></tr>
        <tr><td><b>Ctrl+Q</b></td><td>Çıkış</td></tr>
        </table>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Klavye Kısayolları")
        msg.setText(shortcuts_text)
        msg.setTextFormat(Qt.RichText)
        msg.exec()
    
    def create_modern_right_panel(self):
        """Create modern right data display panel with enhanced functionality"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Create modern tab widget
        self.tab_widget = QTabWidget()
        # Tab widget styling is now handled by global stylesheet
        self.tab_widget.setMinimumHeight(700)  # Ensure sufficient height
        layout.addWidget(self.tab_widget)
        
        # Data table tab with clean styling
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.setSortingEnabled(True)
        
        # Table styling is now handled by global stylesheet
        
        # Hide row headers to avoid duplication with SIRA NO column
        self.data_table.verticalHeader().setVisible(False)
        
        # Enable context menu for advanced features
        self.data_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.data_table.customContextMenuRequested.connect(self.show_table_context_menu)
        
        # Setup Excel-like filtering
        self._setup_excel_like_filtering(self.data_table)
        
        self.tab_widget.addTab(self.data_table, "Veri Tablosu")
        
        # Report preview tab with sub-tabs - FIXED LAYOUT
        self.report_preview_widget = QWidget()
        self.report_preview_layout = QVBoxLayout(self.report_preview_widget)
        self.report_preview_layout.setContentsMargins(10, 10, 10, 10)
        self.report_preview_layout.setSpacing(10)
        
        # Create modern sub-tab widget for report sheets with FIXED HEIGHT
        self.report_tabs = QTabWidget()
        self.report_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E1E8ED;
                border-radius: 8px;
                background-color: white;
                margin-top: 5px;
            }
            
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #F8F9FA, stop:1 #E9ECEF);
                color: #000000;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid #DEE2E6;
                border-bottom: none;
                font-weight: 600;
                font-size: 13px;
                min-width: 120px;
            }
            
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #28A745, stop:1 #1E7E34);
                color: white;
                border-color: #28A745;
            }
            
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #E9ECEF, stop:1 #DEE2E6);
                color: #000000;
            }
        """)
        
        # CRITICAL FIX: Set maximum height to prevent tabs from taking all space
        self.report_tabs.setMaximumHeight(500)  # Limit tab content height
        self.report_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.report_preview_layout.addWidget(self.report_tabs)
        
        # Add control panel for report preview - ALWAYS VISIBLE
        self.create_report_preview_controls()
        
        self.tab_widget.addTab(self.report_preview_widget, "Rapor Önizleme")
        self.update_report_preview()
        
        # Currency rates tab (main tab, not child dialog)
        self.currency_tab = self.create_currency_rates_tab()
        self.tab_widget.addTab(self.currency_tab, "Döviz Kurları")
        
        # Manual entry tab with clean styling
        self.manual_table = QTableWidget()
        self.manual_table.setAlternatingRowColors(True)
        self.manual_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.manual_table.horizontalHeader().setStretchLastSection(True)
        
        # Table styling is now handled by global stylesheet
        
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
        """Create modern status bar with enhanced feedback"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Enhanced status bar styling
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #F8F9FA, stop:1 #E9ECEF);
                border-top: 2px solid #DEE2E6;
                color: #495057;
                font-weight: 600;
                font-size: 14px;
                padding: 8px 15px;
                min-height: 25px;
            }
        """)
        
        # Add ready status with enhanced message
        self.status_bar.showMessage("Sistem Hazır | Veri yüklemek için dosya seçin veya manuel veri girişi yapın")
        
        # Store status messages for consistent feedback
        self.status_messages = {
            'ready': "Sistem Hazır | Veri yüklemek için dosya seçin",
            'importing': "Veri içe aktarılıyor...",
            'processing': "Veriler işleniyor...",
            'generating_report': "Rapor oluşturuluyor...",
            'saving': "Dosya kaydediliyor...",
            'completed': "İşlem başarıyla tamamlandı",
            'error': "Hata oluştu",
            'data_loaded': lambda count: f"{count:,} kayıt başarıyla yüklendi"
        }
    
    def update_status(self, status_key, *args):
        """Update status bar with predefined messages"""
        if status_key in self.status_messages:
            message = self.status_messages[status_key]
            if callable(message):
                message = message(*args)
            self.status_bar.showMessage(message)
    
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
            self.format_combo.setCurrentText("CSV (.csv)")
            self.sheet_widget.setVisible(False)
        elif extension in ['.xlsx', '.xls']:
            self.format_combo.setCurrentText("Excel (.xlsx)")
            self.sheet_widget.setVisible(True)
            self.load_sheet_names(file_path)
        elif extension == '.json':
            self.format_combo.setCurrentText("JSON (.json)")
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
        """Start data import process - now shows preview instead of direct processing"""
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
        
        # Extract format from combo box text (e.g., "CSV (.csv)" -> "csv")
        format_text = self.format_combo.currentText().lower()
        logger.info(f"Selected format text: '{format_text}'")
        
        if 'csv' in format_text:
            file_format = 'csv'
        elif 'xlsx' in format_text or 'xls' in format_text or 'excel' in format_text:
            file_format = 'xlsx'
        elif 'json' in format_text:
            file_format = 'json'
        else:
            file_format = format_text.split()[0]  # fallback to first word
            logger.warning(f"Unknown format, using fallback: '{file_format}'")
        
        sheet_name = self.sheet_combo.currentText() if self.sheet_widget.isVisible() else None
        
        logger.info(f"File format detected: {file_format}")
        logger.info(f"Sheet name: {sheet_name}")
        
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
        
        # Update status and show progress bar
        self.update_status('importing')
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start import worker for preview
        logger.info("Creating import worker...")
        existing_payments = self.storage.get_all_payments()
        # Get selected columns from dropdowns
        amount_column = self.amount_column_combo.currentText() if hasattr(self, 'amount_column_combo') else None
        currency_column = self.currency_column_combo.currentText() if hasattr(self, 'currency_column_combo') else None
        
        try:
            self.import_worker = ImportWorker(
                file_path, file_format, sheet_name, existing_payments,
                amount_column=amount_column, currency_column=currency_column
            )
        except Exception as e:
            logger.error(f"Failed to create import worker: {e}")
            QMessageBox.critical(self, "İçe Aktarma Hatası", 
                               f"Veri içe aktarma başlatılamadı:\n\n{str(e)}\n\n"
                               f"Lütfen dosya formatını kontrol edin.")
            return
        self.import_worker.progress.connect(self.progress_bar.setValue)
        self.import_worker.status.connect(self.status_bar.showMessage)
        self.import_worker.finished.connect(self.on_import_preview_finished)
        self.import_worker.error.connect(self.on_import_error)
        logger.info("Starting import worker...")
        self.import_worker.start()
    
    def on_import_preview_finished(self, valid_payments: List[PaymentData], warnings: List[str]):
        """Handle import completion - show preview instead of processing"""
        self.progress_bar.setVisible(False)
        self.update_status('ready')
        
        # Store the imported data for processing
        self.preview_payments = valid_payments
        self.preview_warnings = warnings
        
        # Show preview table
        self.show_data_preview(valid_payments, warnings)
        
        # Show process and clear buttons
        self.process_btn.setVisible(True)
        if hasattr(self, 'clear_btn'):
            self.clear_btn.setVisible(True)
        
        # Add a prominent notification
        self.show_processing_notification(len(valid_payments))
        
        # Show success message with clear instructions
        QMessageBox.information(self, "Veri Başarıyla Yüklendi!", 
                               f"✅ Toplam kayıt: {len(valid_payments)}\n"
                               f"⚠️ Uyarı sayısı: {len(warnings)}\n\n"
                               f"📋 Veri önizleme tablosunda görüntüleniyor.\n"
                               f"🔄 Veriyi sisteme eklemek için 'Veriyi İşle' butonuna tıklayın.\n\n"
                               f"💡 İpucu: Veriyi işledikten sonra 'Veri Tablosu' sekmesinde görebilirsiniz.")
    
    def show_data_preview(self, payments: List[PaymentData], warnings: List[str]):
        """Show data preview in modern table with full scrolling support"""
        if not payments:
            return
        
        # Store original data for filtering
        self.original_preview_data = payments
        
        # Show preview table and info
        self.data_preview_table.setVisible(True)
        self.preview_info_label.setVisible(True)
        self.duplicate_info_label.setVisible(True)
        
        # Set up table columns
        columns = ['Müşteri', 'Proje', 'Tutar', 'Tarih', 'Tahsilat Şekli', 'Hesap']
        self.data_preview_table.setColumnCount(len(columns))
        self.data_preview_table.setHorizontalHeaderLabels(columns)
        
        # Update column filter dropdown
        self.column_filter_combo.clear()
        self.column_filter_combo.addItem("Tüm Sütunlar")
        self.column_filter_combo.addItems(columns)
        
        # Populate table with ALL records (no 100 record limit)
        self.data_preview_table.setRowCount(len(payments))
        
        for i, payment in enumerate(payments):
            # Convert payment amount to USD if needed
            if payment.currency == "TL":
                try:
                    from currency import get_usd_rate_for_date
                    rate = get_usd_rate_for_date(payment.date)
                    if rate and rate > 0:
                        usd_amount = payment.amount / rate
                    else:
                        usd_amount = payment.amount / 41.0  # Default rate
                except:
                    usd_amount = payment.amount / 41.0  # Default rate
            else:
                usd_amount = payment.amount  # Already USD
            
            self.data_preview_table.setItem(i, 0, QTableWidgetItem(payment.customer_name or ""))
            self.data_preview_table.setItem(i, 1, QTableWidgetItem(payment.project_name or ""))
            self.data_preview_table.setItem(i, 2, QTableWidgetItem(f"${usd_amount:,.2f}"))
            self.data_preview_table.setItem(i, 3, QTableWidgetItem(payment.date.strftime("%d.%m.%Y") if payment.date else ""))
            self.data_preview_table.setItem(i, 4, QTableWidgetItem(payment.tahsilat_sekli or ""))
            self.data_preview_table.setItem(i, 5, QTableWidgetItem(payment.account_name or ""))
        
        # Update preview count
        if hasattr(self, 'preview_count_label'):
            self.preview_count_label.setText(f"{len(payments)} kayıt")
        
        # Resize columns to content
        self.data_preview_table.resizeColumnsToContents()
        
        # Set column widths for better readability
        self.data_preview_table.setColumnWidth(0, 200)  # Müşteri
        self.data_preview_table.setColumnWidth(1, 150)  # Proje
        self.data_preview_table.setColumnWidth(2, 120)  # Tutar
        self.data_preview_table.setColumnWidth(3, 100)  # Tarih
        self.data_preview_table.setColumnWidth(4, 120)  # Tahsilat Şekli
        self.data_preview_table.setColumnWidth(5, 200)  # Hesap
        
        # Count duplicates from warnings
        duplicate_count = 0
        duplicate_details = []
        for warning in warnings:
            if "Dublicate bulundu:" in warning:
                duplicate_count += 1
                # Extract duplicate details
                detail = warning.replace("Dublicate bulundu: ", "")
                duplicate_details.append(detail)
        
        # Update info label with duplicate information
        info_text = f"{len(payments)} yeni kayıt yüklendi ('Ödenen Tutar' ve 'Ödenen Döviz' kullanılarak)"
        if duplicate_count > 0:
            info_text += f" | {duplicate_count} dublicate atlandı"
        if len(payments) > 50:
            info_text += f" (İlk 50 kayıt gösteriliyor)"
        if warnings and duplicate_count == 0:
            info_text += f" | {len(warnings)} uyarı"
        
        self.preview_info_label.setText(info_text)
        
        # Update duplicate information label
        if duplicate_count > 0:
            duplicate_text = f"🔄 {duplicate_count} dublicate ödeme bulundu ve atlandı:\n"
            # Show first 5 duplicates
            for i, detail in enumerate(duplicate_details[:5]):
                duplicate_text += f"• {detail}\n"
            if len(duplicate_details) > 5:
                duplicate_text += f"... ve {len(duplicate_details) - 5} tane daha"
            self.duplicate_info_label.setText(duplicate_text.strip())
        else:
            self.duplicate_info_label.setText("Dublicate ödeme bulunamadı")
    
    def process_imported_data(self):
        """Process the previewed data into the system"""
        if not hasattr(self, 'preview_payments') or not self.preview_payments:
            QMessageBox.warning(self, "Uyarı", "İşlenecek veri bulunamadı.")
            return
        
        # Process the data using the original import finished method
        self.on_import_finished(self.preview_payments, self.preview_warnings)
        
        # Show success message
        QMessageBox.information(self, "Veri İşlendi!", 
                               f"✅ {len(self.preview_payments)} kayıt başarıyla sisteme eklendi!\n\n"
                               f"📊 Veriyi görmek için 'Veri Tablosu' sekmesine geçin.")
        
        # Hide preview elements
        self.data_preview_table.setVisible(False)
        self.preview_info_label.setVisible(False)
        self.process_btn.setVisible(False)
        if hasattr(self, 'clear_btn'):
            self.clear_btn.setVisible(False)
        if hasattr(self, 'processing_notification'):
            self.processing_notification.setVisible(False)
        
        # Clear preview data
        self.preview_payments = None
        self.preview_warnings = None
    
    def clear_data_preview(self):
        """Clear the data preview"""
        self.data_preview_table.setVisible(False)
        self.preview_info_label.setVisible(False)
        self.duplicate_info_label.setVisible(False)
        self.process_btn.setVisible(False)
        if hasattr(self, 'clear_btn'):
            self.clear_btn.setVisible(False)
        
        # Clear preview data
        self.preview_payments = None
        self.preview_warnings = None
        self.original_preview_data = []
    
    def show_processing_notification(self, record_count: int):
        """Show a prominent notification that data is ready to be processed"""
        # Create a notification widget if it doesn't exist
        if not hasattr(self, 'processing_notification'):
            self.processing_notification = QLabel()
            self.processing_notification.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                               stop:0 #FFC107, stop:1 #FF9800);
                    color: #212529;
                    font-size: 14px;
                    font-weight: 700;
                    padding: 12px 20px;
                    border: 2px solid #FF8F00;
                    border-radius: 8px;
                    margin: 5px;
                }
            """)
            self.processing_notification.setAlignment(Qt.AlignCenter)
            self.processing_notification.setVisible(False)
            
            # Add to the import section layout
            if hasattr(self, 'import_layout'):
                self.import_layout.addRow("", self.processing_notification)
        
        # Show the notification
        self.processing_notification.setText(
            f"🔄 {record_count} kayıt önizleme tablosunda hazır! "
            f"Veriyi sisteme eklemek için 'Veriyi İşle' butonuna tıklayın."
        )
        self.processing_notification.setVisible(True)
    
    def on_format_changed(self, format_text: str):
        """Handle format combo box change to show/hide sheet selection"""
        if hasattr(self, 'sheet_widget'):
            if 'xlsx' in format_text.lower() or 'excel' in format_text.lower():
                self.sheet_widget.setVisible(True)
            else:
                self.sheet_widget.setVisible(False)
    
    def filter_preview_table(self):
        """Filter the preview table based on search text and column selection"""
        if not hasattr(self, 'original_preview_data') or not self.original_preview_data:
            return
        
        # Prevent recursion by checking if we're already filtering
        if hasattr(self, '_filtering_in_progress') and self._filtering_in_progress:
            return
        
        self._filtering_in_progress = True
        
        try:
            search_text = self.search_box.text().lower()
            selected_column = self.column_filter_combo.currentText()
            
            if not search_text:
                # Show all data without calling show_data_preview to avoid recursion
                self._populate_preview_table(self.original_preview_data)
                return
        
            # Filter data
            filtered_payments = []
            for payment in self.original_preview_data:
                match_found = False
                
                if selected_column == "Tüm Sütunlar":
                    # Search in all columns
                    searchable_text = f"{payment.customer_name or ''} {payment.project_name or ''} {payment.usd_amount} USD {payment.date.strftime('%d.%m.%Y') if payment.date else ''} {payment.tahsilat_sekli or ''} {payment.account_name or ''}".lower()
                    match_found = search_text in searchable_text
                else:
                    # Search in specific column
                    if selected_column == "Müşteri":
                        searchable_text = (payment.customer_name or "").lower()
                    elif selected_column == "Proje":
                        searchable_text = (payment.project_name or "").lower()
                    elif selected_column == "Tutar":
                        searchable_text = f"{payment.usd_amount} USD".lower()
                    elif selected_column == "Tarih":
                        searchable_text = payment.date.strftime('%d.%m.%Y') if payment.date else ""
                    elif selected_column == "Tahsilat Şekli":
                        searchable_text = (payment.tahsilat_sekli or "").lower()
                    elif selected_column == "Hesap":
                        searchable_text = (payment.account_name or "").lower()
                    
                    match_found = search_text in searchable_text
                
                if match_found:
                    filtered_payments.append(payment)
            
            # Update table with filtered data
            self._populate_preview_table(filtered_payments)
            
        finally:
            self._filtering_in_progress = False
    
    def _populate_preview_table(self, payments: List[PaymentData]):
        """Populate the preview table with payment data without triggering recursion"""
        if not payments:
            return
        
        # Update table with data
        self.data_preview_table.setRowCount(len(payments))
        
        for i, payment in enumerate(payments):
            # Use the already converted USD amount from PaymentData
            usd_amount = payment.usd_amount if payment.usd_amount > 0 else payment.amount
            
            self.data_preview_table.setItem(i, 0, QTableWidgetItem(payment.customer_name or ""))
            self.data_preview_table.setItem(i, 1, QTableWidgetItem(payment.project_name or ""))
            self.data_preview_table.setItem(i, 2, QTableWidgetItem(f"${usd_amount:,.2f}"))
            self.data_preview_table.setItem(i, 3, QTableWidgetItem(payment.date.strftime("%d.%m.%Y") if payment.date else ""))
            self.data_preview_table.setItem(i, 4, QTableWidgetItem(payment.tahsilat_sekli or ""))
            self.data_preview_table.setItem(i, 5, QTableWidgetItem(payment.account_name or ""))
        
        # Update count
        if hasattr(self, 'original_preview_data') and self.original_preview_data:
            self.preview_count_label.setText(f"{len(payments)} / {len(self.original_preview_data)} kayıt")
    
    def clear_preview_filters(self):
        """Clear all preview filters and show all data"""
        self.search_box.clear()
        self.column_filter_combo.setCurrentText("Tüm Sütunlar")
        if hasattr(self, 'original_preview_data') and self.original_preview_data:
            self._populate_preview_table(self.original_preview_data)
    
    def show_advanced_filter_dialog(self):
        """Show advanced filter dialog for preview data"""
        if not hasattr(self, 'original_preview_data') or not self.original_preview_data:
            QMessageBox.warning(self, "Uyarı", "Önce veri yükleyin")
            return
        
        from advanced_filter_dialog import AdvancedFilterDialog
        dialog = AdvancedFilterDialog(self.original_preview_data, self)
        if dialog.exec_() == QDialog.Accepted:
            filtered_payments = dialog.get_filtered_payments()
            self.show_data_preview(filtered_payments, [])
    
    def show_preview_context_menu(self, position):
        """Show context menu for preview table with Excel-like features"""
        if self.data_preview_table.itemAt(position) is None:
            return
        
        menu = QMenu(self)
        
        # Copy actions
        copy_action = menu.addAction("Kopyala")
        copy_action.triggered.connect(self.copy_selected_preview_cells)
        
        copy_row_action = menu.addAction("Satırı Kopyala")
        copy_row_action.triggered.connect(self.copy_selected_preview_row)
        
        # Select actions
        select_all_action = menu.addAction("Tümünü Seç")
        select_all_action.triggered.connect(self.select_all_preview_rows)
        
        # Sort actions
        sort_asc_action = menu.addAction("A-Z Sırala")
        sort_asc_action.triggered.connect(lambda: self.sort_preview_column(True))
        
        sort_desc_action = menu.addAction("Z-A Sırala")
        sort_desc_action.triggered.connect(lambda: self.sort_preview_column(False))
        
        menu.exec_(self.data_preview_table.mapToGlobal(position))
    
    def copy_selected_preview_cells(self):
        """Copy selected cells to clipboard"""
        selected_items = self.data_preview_table.selectedItems()
        if not selected_items:
            return
        
        # Group items by row
        rows = {}
        for item in selected_items:
            row = item.row()
            col = item.column()
            if row not in rows:
                rows[row] = {}
            rows[row][col] = item.text()
        
        # Create clipboard text
        clipboard_text = ""
        for row in sorted(rows.keys()):
            row_text = []
            for col in sorted(rows[row].keys()):
                row_text.append(rows[row][col])
            clipboard_text += "\t".join(row_text) + "\n"
        
        QApplication.clipboard().setText(clipboard_text.strip())
    
    def copy_selected_preview_row(self):
        """Copy selected row to clipboard"""
        current_row = self.data_preview_table.currentRow()
        if current_row < 0:
            return
        
        row_text = []
        for col in range(self.data_preview_table.columnCount()):
            item = self.data_preview_table.item(current_row, col)
            row_text.append(item.text() if item else "")
        
        QApplication.clipboard().setText("\t".join(row_text))
    
    def select_all_preview_rows(self):
        """Select all rows in preview table"""
        self.data_preview_table.selectAll()
    
    def sort_preview_column(self, ascending=True):
        """Sort preview table by current column"""
        current_col = self.data_preview_table.currentColumn()
        if current_col < 0:
            return
        
        self.data_preview_table.sortItems(current_col, Qt.AscendingOrder if ascending else Qt.DescendingOrder)
    
    def on_import_finished(self, valid_payments: List[PaymentData], warnings: List[str]):
        """Handle import completion with duplicate detection"""
        self.progress_bar.setVisible(False)
        
        # Update status with successful import
        if valid_payments:
            self.update_status('data_loaded', len(valid_payments))
        
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
            
            # Update monthly reports
            self.update_monthly_reports()
            
            # Create weekly tabs for new data
            self.create_weekly_tabs_for_new_data(all_payments_to_import)
            
            # Show summary message
            message = f"{len(all_payments_to_import)} kayıt başarıyla içe aktarıldı\n\n"
            message += "✓ 'Ödenen Tutar' ve 'Ödenen Döviz' sütunları kullanılarak işlendi\n"
            message += "✓ Haftalık raporlarda ödenen tutarlar gösterilecektir"
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
        
        # Populate main_data DataFrame
        self._populate_main_data()
        
        # Update data table with loaded data
        self.update_data_table()
        self.update_statistics()
        # Update report preview when data is loaded
        self.update_report_preview()
        
        # Debug: Check if data table exists and has data
        if hasattr(self, 'data_table') and self.data_table:
            logger.info(f"Data table exists with {self.data_table.rowCount()} rows and {self.data_table.columnCount()} columns")
        else:
            logger.warning("Data table not found or not initialized")
    
    def update_data_table(self):
        """Update the data table with current payments including conversion details"""
        logger.info("update_data_table called")
        
        # Check if data table exists (UI might not be fully initialized yet)
        if not hasattr(self, 'data_table') or not self.data_table:
            logger.warning("Data table not found, skipping update")
            return
            
        if not self.current_payments:
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            return
            
        # If main_data is available, use it for filtering
        if self.main_data is not None and not self.main_data.empty:
            logger.info("Using main_data DataFrame for table update")
            self._refresh_table_view(self.main_data)
            return
        else:
            logger.info("main_data not available, using original method")
        
        # Initialize currency conversion cache if not exists
        if not hasattr(self, 'currency_cache'):
            self.currency_cache = {}
        
        # Check if currency conversion is disabled to prevent freezing
        if not hasattr(self, 'currency_conversion_enabled'):
            self.currency_conversion_enabled = False
        
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
            amount_item = QTableWidgetItem(f"${payment.usd_amount:,.2f}")
            amount_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 5, amount_item)
            
            # Currency
            currency_item = QTableWidgetItem(payment.currency)
            currency_item.setForeground(QColor(33, 37, 41))
            self.data_table.setItem(row, 6, currency_item)
            
            # USD Equivalent - Convert based on actual payment amount and currency
            if payment.currency == "TL":
                # Convert TL to USD using rate from one day before payment date
                try:
                    from currency import get_usd_rate_for_date
                    rate = get_usd_rate_for_date(payment.date)
                    if rate and rate > 0:
                        usd_amount = payment.amount / rate
                        conversion_rate = rate
                    else:
                        # Fallback to recent rate
                        from datetime import datetime, timedelta
                        for days_back in range(1, 30):
                            check_date = payment.date - timedelta(days=days_back)
                            rate = get_usd_rate_for_date(check_date)
                            if rate and rate > 0:
                                usd_amount = payment.amount / rate
                                conversion_rate = rate
                                break
                        else:
                            usd_amount = payment.amount / 41.0  # Default rate
                            conversion_rate = 41.0
                except Exception as e:
                    logger.error(f"Currency conversion failed: {e}")
                    usd_amount = payment.amount / 41.0  # Default rate
                    conversion_rate = 41.0
                
                # Highlight TL conversions
                usd_item = QTableWidgetItem(f"${usd_amount:,.2f}")
                usd_item.setBackground(QColor(230, 243, 255))  # Light blue
            else:
                # Already USD, no conversion needed
                usd_amount = payment.amount
                conversion_rate = 1.0
                usd_item = QTableWidgetItem(f"${usd_amount:,.2f}")
            
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
        
        # Setup Excel-like header filters
        self._setup_excel_header_filters(self.data_table)
    
    def update_monthly_reports(self):
        """Update monthly reports with current payment data"""
        if not hasattr(self, 'monthly_reports_layout'):
            return
            
        # Clear existing reports
        for i in reversed(range(self.monthly_reports_layout.count())):
            child = self.monthly_reports_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        if not self.current_payments:
            return
            
        # Group payments by month and year
        monthly_data = {}
        for payment in self.current_payments:
            if payment.date:
                month_key = payment.date.strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = []
                monthly_data[month_key].append(payment)
        
        # Create report for each month
        for month_key in sorted(monthly_data.keys()):
            month_payments = monthly_data[month_key]
            month_name = month_payments[0].date.strftime('%B %Y')
            
            # Create month report widget
            month_widget = self.create_monthly_report_widget(month_name, month_payments)
            self.monthly_reports_layout.addWidget(month_widget)
    
    def create_monthly_report_widget(self, month_name, payments):
        """Create a comprehensive monthly report widget with all analysis tables"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 12px;
                border: 1px solid #E9ECEF;
                margin: 10px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Month title
        title = QLabel(f"{month_name.upper()} AYI TAHSİLATLAR")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: 700;
            color: #2C3E50;
            padding: 15px;
            background: #F8F9FA;
            border-radius: 8px;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # Create scroll area for all tables
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container for all tables
        tables_container = QWidget()
        tables_layout = QVBoxLayout(tables_container)
        tables_layout.setSpacing(30)
        
        # 1. Customer-Date Table (Müşteri Tarih Tablosu)
        customer_date_table = self.create_monthly_customer_date_table(payments, month_name)
        tables_layout.addWidget(customer_date_table)
        
        # 2. Check Payments Table (Çek Tahsilatları)
        check_table = self.create_monthly_check_payments_table(payments, month_name)
        tables_layout.addWidget(check_table)
        
        # 3. Payment Type Analysis (Ödeme Tipi Analizi)
        payment_analysis = self.create_monthly_payment_analysis(payments, month_name)
        tables_layout.addWidget(payment_analysis)
        
        # 4. Project Totals (Proje Toplamları)
        project_totals = self.create_monthly_project_totals(payments, month_name)
        tables_layout.addWidget(project_totals)
        
        # 5. Location Analysis (Lokasyon Analizi)
        location_analysis = self.create_monthly_location_analysis(payments, month_name)
        tables_layout.addWidget(location_analysis)
        
        scroll_area.setWidget(tables_container)
        layout.addWidget(scroll_area)
        
        return widget
    
    def create_monthly_customer_date_table(self, payments, month_name):
        """Create monthly customer-date table showing individual payments"""
        if not payments:
            # Return empty table with message
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setSpacing(10)
            
            title_label = QLabel("HAFTANIN TÜM ÖDEMELERİ")
            title_label.setStyleSheet("""
                font-size: 16px;
                font-weight: 600;
                color: #2C3E50;
                text-align: center;
                padding: 10px;
                background: #E3F2FD;
                border-radius: 6px;
            """)
            container_layout.addWidget(title_label)
            
            message_label = QLabel("Bu ayda ödeme verisi yok")
            message_label.setStyleSheet("""
                font-size: 14px;
                color: #6C757D;
                text-align: center;
                padding: 20px;
                background: #F8F9FA;
                border-radius: 6px;
            """)
            container_layout.addWidget(message_label)
            
            return container
            
        # Get unique dates in the month
        dates = sorted(list(set(payment.date for payment in payments if payment.date)))
        if not dates:
            # Return empty table with message
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setSpacing(10)
            
            title_label = QLabel("HAFTANIN TÜM ÖDEMELERİ")
            title_label.setStyleSheet("""
                font-size: 16px;
                font-weight: 600;
                color: #2C3E50;
                text-align: center;
                padding: 10px;
                background: #E3F2FD;
                border-radius: 6px;
            """)
            container_layout.addWidget(title_label)
            
            message_label = QLabel("Bu ayda geçerli tarihli ödeme verisi yok")
            message_label.setStyleSheet("""
                font-size: 14px;
                color: #6C757D;
                text-align: center;
                padding: 20px;
                background: #F8F9FA;
                border-radius: 6px;
            """)
            container_layout.addWidget(message_label)
            
            return container
            
        # Create table widget
        table = QTableWidget()
        table.setColumnCount(len(dates) + 3)  # Customer, Project, dates, Total
        table.setRowCount(len(payments))
        
        # Set headers
        headers = ["MÜŞTERİ ADI SOYADI", "PROJE"] + [date.strftime("%d.%m.%Y") for date in dates] + ["GENEL TOPLAM"]
        table.setHorizontalHeaderLabels(headers)
        
        # Group payments by customer and project
        grouped_payments = {}
        for payment in payments:
            key = (payment.customer_name, payment.project_name)
            if key not in grouped_payments:
                grouped_payments[key] = {}
            if payment.date:
                grouped_payments[key][payment.date] = payment.usd_amount
        
        # Populate table
        row = 0
        for (customer, project), date_amounts in grouped_payments.items():
            # Customer name
            customer_item = QTableWidgetItem(customer)
            table.setItem(row, 0, customer_item)
            
            # Project name
            project_item = QTableWidgetItem(project)
            table.setItem(row, 1, project_item)
            
            # Date columns
            total_amount = 0
            for col, date in enumerate(dates, 2):
                amount = date_amounts.get(date, 0)
                if amount > 0:
                    amount_item = QTableWidgetItem(f"${amount:,.2f}")
                    total_amount += amount
                else:
                    amount_item = QTableWidgetItem("")
                table.setItem(row, col, amount_item)
            
            # Total column
            if total_amount > 0:
                total_item = QTableWidgetItem(f"${total_amount:,.2f}")
                total_item.setFont(QFont("Arial", 10, QFont.Bold))
            else:
                total_item = QTableWidgetItem("$0.00")
            table.setItem(row, len(dates) + 2, total_item)
            
            row += 1
        
        # Add totals row
        table.insertRow(row)
        total_customer_item = QTableWidgetItem("HAFTA TOPLAMI")
        total_customer_item.setFont(QFont("Arial", 10, QFont.Bold))
        table.setItem(row, 0, total_customer_item)
        
        total_project_item = QTableWidgetItem("")
        table.setItem(row, 1, total_project_item)
        
        # Calculate totals for each date
        for col, date in enumerate(dates, 2):
            date_total = sum(date_amounts.get(date, 0) for date_amounts in grouped_payments.values())
            if date_total > 0:
                total_item = QTableWidgetItem(f"${date_total:,.2f}")
                total_item.setFont(QFont("Arial", 10, QFont.Bold))
            else:
                total_item = QTableWidgetItem("")
            table.setItem(row, col, total_item)
        
        # Grand total
        grand_total = sum(sum(date_amounts.values()) for date_amounts in grouped_payments.values())
        grand_total_item = QTableWidgetItem(f"${grand_total:,.2f}")
        grand_total_item.setFont(QFont("Arial", 10, QFont.Bold))
        table.setItem(row, len(dates) + 2, grand_total_item)
        
        # Style the table
        table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                background: white;
                gridline-color: #DEE2E6;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QHeaderView::section {
                background: #F8F9FA;
                border: 1px solid #DEE2E6;
                padding: 8px;
                font-weight: 600;
                color: #495057;
            }
        """)
        
        # Set column widths
        table.setColumnWidth(0, 200)
        table.setColumnWidth(1, 150)
        for col in range(2, len(dates) + 2):
            table.setColumnWidth(col, 100)
        table.setColumnWidth(len(dates) + 2, 120)
        
        # Create container with title
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(10)
        
        # Title
        title_label = QLabel("HAFTANIN TÜM ÖDEMELERİ")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #2C3E50;
            text-align: center;
            padding: 10px;
            background: #E3F2FD;
            border-radius: 6px;
        """)
        container_layout.addWidget(title_label)
        container_layout.addWidget(table)
        
        return container
    
    def create_monthly_check_payments_table(self, payments, month_name):
        """Create monthly check payments table"""
        check_payments = [p for p in payments if p.is_check_payment]
        
        if not check_payments:
            # Create empty table with message
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setSpacing(10)
            
            title_label = QLabel("ÇEK TAHSİLATLARI")
            title_label.setStyleSheet("""
                font-size: 16px;
                font-weight: 600;
                color: #2C3E50;
                text-align: center;
                padding: 10px;
                background: #E3F2FD;
                border-radius: 6px;
            """)
            container_layout.addWidget(title_label)
            
            message_label = QLabel("Bu hafta çek tahsilatı yok")
            message_label.setStyleSheet("""
                font-size: 14px;
                color: #6C757D;
                text-align: center;
                padding: 20px;
                background: #F8F9FA;
                border-radius: 6px;
            """)
            container_layout.addWidget(message_label)
            
            return container
        
        # Create table for check payments
        table = QTableWidget()
        table.setColumnCount(5)  # Customer, Project, TL Amount, USD Amount, Maturity Date
        table.setRowCount(len(check_payments))
        
        # Set headers
        headers = ["MÜŞTERİ ADI SOYADI", "PROJE", "ÇEK TUTARI (TL)", "ÇEK TUTARI (USD)", "VADE TARİHİ"]
        table.setHorizontalHeaderLabels(headers)
        
        # Populate table
        for row, payment in enumerate(check_payments):
            table.setItem(row, 0, QTableWidgetItem(payment.customer_name))
            table.setItem(row, 1, QTableWidgetItem(payment.project_name))
            
            # TL Amount
            table.setItem(row, 2, QTableWidgetItem(f"₺{payment.cek_tutari:,.2f}"))
            
            # USD Amount - convert using maturity date rate if available
            usd_amount = 0
            if payment.cek_vade_tarihi:
                # Try to get exchange rate for maturity date
                try:
                    from currency import get_usd_rate_for_date
                    rate = get_usd_rate_for_date(payment.cek_vade_tarihi)
                    if rate and rate > 0:
                        usd_amount = payment.cek_tutari / rate
                    else:
                        # Fallback to payment date rate
                        if payment.date:
                            rate = get_usd_rate_for_date(payment.date)
                            if rate and rate > 0:
                                usd_amount = payment.cek_tutari / rate
                except Exception as e:
                    logger.warning(f"Failed to convert check amount to USD: {e}")
            
            table.setItem(row, 3, QTableWidgetItem(f"${usd_amount:,.2f}" if usd_amount > 0 else "-"))
            table.setItem(row, 4, QTableWidgetItem(payment.cek_vade_tarihi.strftime("%d.%m.%Y") if payment.cek_vade_tarihi else ""))
        
        # Style the table
        table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                background: white;
                gridline-color: #DEE2E6;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QHeaderView::section {
                background: #F8F9FA;
                border: 1px solid #DEE2E6;
                padding: 8px;
                font-weight: 600;
                color: #495057;
            }
        """)
        
        # Set column widths
        table.setColumnWidth(0, 200)
        table.setColumnWidth(1, 150)
        table.setColumnWidth(2, 120)
        table.setColumnWidth(3, 120)
        
        # Create container with title
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(10)
        
        # Title
        title_label = QLabel("ÇEK TAHSİLATLARI")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #2C3E50;
            text-align: center;
            padding: 10px;
            background: #E3F2FD;
            border-radius: 6px;
        """)
        container_layout.addWidget(title_label)
        container_layout.addWidget(table)
        
        return container
    
    def create_monthly_payment_analysis(self, payments, month_name):
        """Create monthly payment type analysis table"""
        if not payments:
            # Return empty table with message
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setSpacing(10)
            
            title_label = QLabel("ÖDEME TİPİ ANALİZİ")
            title_label.setStyleSheet("""
                font-size: 16px;
                font-weight: 600;
                color: #2C3E50;
                text-align: center;
                padding: 10px;
                background: #E3F2FD;
                border-radius: 6px;
            """)
            container_layout.addWidget(title_label)
            
            message_label = QLabel("Bu ayda ödeme verisi yok")
            message_label.setStyleSheet("""
                font-size: 14px;
                color: #6C757D;
                text-align: center;
                padding: 20px;
                background: #F8F9FA;
                border-radius: 6px;
            """)
            container_layout.addWidget(message_label)
            
            return container
            
        # Calculate totals by payment type
        payment_types = ["BANK_TRANSFER", "Nakit", "Çek"]
        totals_original = {}
        totals_usd = {}
        
        for payment_type in payment_types:
            totals_original[payment_type] = 0
            totals_usd[payment_type] = 0
            
            for payment in payments:
                # Convert payment amount to USD if needed
                if payment.currency == "TL":
                    try:
                        from currency import get_usd_rate_for_date
                        rate = get_usd_rate_for_date(payment.date)
                        if rate and rate > 0:
                            usd_amount = payment.amount / rate
                        else:
                            usd_amount = payment.amount / 41.0  # Default rate
                    except:
                        usd_amount = payment.amount / 41.0  # Default rate
                else:
                    usd_amount = payment.amount  # Already USD
                
                # Determine payment type using the same logic as weekly tables
                if payment_type == "Çek":
                    if payment.is_check_payment:
                        totals_original[payment_type] += payment.amount
                        totals_usd[payment_type] += usd_amount
                elif payment_type == "Nakit":
                    if (payment.tahsilat_sekli == "Nakit" or 
                        payment.payment_channel == "NAKİT" or
                        "KASA" in (payment.account_name or "").upper()):
                        totals_original[payment_type] += payment.amount
                        totals_usd[payment_type] += usd_amount
                elif payment_type == "BANK_TRANSFER":
                    if (payment.payment_channel == "BANKA HAVALESİ" or
                        "YAPI" in (payment.account_name or "").upper() or
                        "HAVALE" in (payment.account_name or "").upper() or
                        "TRANSFER" in (payment.account_name or "").upper() or
                        (payment.tahsilat_sekli == "BANK_TRANSFER" and not payment.is_check_payment)):
                        totals_original[payment_type] += payment.amount
                        totals_usd[payment_type] += usd_amount
        
        # Create table widget
        table = QTableWidget()
        table.setColumnCount(3)
        table.setRowCount(4)  # 3 payment types + total
        
        # Set headers
        headers = ["Ödeme Nedeni", "Orijinal Tutar", "USD Eşdeğeri"]
        table.setHorizontalHeaderLabels(headers)
        
        # Populate table
        for i, payment_type in enumerate(payment_types):
            # Payment type
            type_item = QTableWidgetItem(payment_type)
            type_item.setFont(QFont("Arial", 10, QFont.Bold))
            table.setItem(i, 0, type_item)
            
            # Original amount
            original_amount = totals_original[payment_type]
            if original_amount > 0:
                original_item = QTableWidgetItem(f"{original_amount:,.2f}")
            else:
                original_item = QTableWidgetItem("0.00")
            table.setItem(i, 1, original_item)
            
            # USD amount
            usd_amount = totals_usd[payment_type]
            if usd_amount > 0:
                usd_item = QTableWidgetItem(f"$ {usd_amount:,.2f}")
            else:
                usd_item = QTableWidgetItem("$ 0.00")
            table.setItem(i, 2, usd_item)
        
        # Total row
        total_original = sum(totals_original.values())
        total_usd = sum(totals_usd.values())
        
        total_type_item = QTableWidgetItem("Genel Toplam")
        total_type_item.setFont(QFont("Arial", 10, QFont.Bold))
        table.setItem(3, 0, total_type_item)
        
        total_original_item = QTableWidgetItem(f"{total_original:,.2f}")
        total_original_item.setFont(QFont("Arial", 10, QFont.Bold))
        table.setItem(3, 1, total_original_item)
        
        total_usd_item = QTableWidgetItem(f"$ {total_usd:,.2f}")
        total_usd_item.setFont(QFont("Arial", 10, QFont.Bold))
        table.setItem(3, 2, total_usd_item)
        
        # Style the table
        table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                background: white;
                gridline-color: #DEE2E6;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QHeaderView::section {
                background: #F8F9FA;
                border: 1px solid #DEE2E6;
                padding: 8px;
                font-weight: 600;
                color: #495057;
            }
        """)
        
        # Highlight total row
        for col in range(3):
            item = table.item(3, col)
            if item:
                item.setBackground(QColor(255, 255, 0, 100))  # Light yellow
        
        # Set column widths
        table.setColumnWidth(0, 150)
        table.setColumnWidth(1, 120)
        table.setColumnWidth(2, 120)
        
        # Create container with title
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(10)
        
        # Title
        title_label = QLabel("ÖDEME TİPİ ANALİZİ")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #2C3E50;
            text-align: center;
            padding: 10px;
            background: #E3F2FD;
            border-radius: 6px;
        """)
        container_layout.addWidget(title_label)
        container_layout.addWidget(table)
        
        return container
    
    def create_monthly_project_totals(self, payments, month_name):
        """Create monthly project totals analysis"""
        if not payments:
            # Return empty table with message
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setSpacing(10)
            
            title_label = QLabel("PROJE TOPLAMLARI")
            title_label.setStyleSheet("""
                font-size: 16px;
                font-weight: 600;
                color: #2C3E50;
                text-align: center;
                padding: 10px;
                background: #E3F2FD;
                border-radius: 6px;
            """)
            container_layout.addWidget(title_label)
            
            message_label = QLabel("Bu ayda ödeme verisi yok")
            message_label.setStyleSheet("""
                font-size: 14px;
                color: #6C757D;
                text-align: center;
                padding: 20px;
                background: #F8F9FA;
                border-radius: 6px;
            """)
            container_layout.addWidget(message_label)
            
            return container
            
        # Group payments by project
        project_totals = {}
        for payment in payments:
            project = payment.project_name or "Diğer"
            if project not in project_totals:
                project_totals[project] = {'tl': 0, 'usd': 0}
            
            if payment.currency == "TL":
                project_totals[project]['tl'] += payment.original_amount
            else:
                project_totals[project]['usd'] += payment.usd_amount
        
        # Create table widget
        table = QTableWidget()
        table.setColumnCount(3)
        table.setRowCount(len(project_totals) + 1)  # Projects + total
        
        # Set headers
        headers = ["Proje", "Toplam TL", "Toplam USD"]
        table.setHorizontalHeaderLabels(headers)
        
        # Populate table
        row = 0
        total_tl = 0
        total_usd = 0
        
        for project, amounts in project_totals.items():
            # Project name
            project_item = QTableWidgetItem(project)
            table.setItem(row, 0, project_item)
            
            # TL amount
            tl_amount = amounts['tl']
            if tl_amount > 0:
                tl_item = QTableWidgetItem(f"₺ {tl_amount:,.2f}")
            else:
                tl_item = QTableWidgetItem("₺ 0.00")
            table.setItem(row, 1, tl_item)
            
            # USD amount
            usd_amount = amounts['usd']
            if usd_amount > 0:
                usd_item = QTableWidgetItem(f"$ {usd_amount:,.2f}")
            else:
                usd_item = QTableWidgetItem("$ 0.00")
            table.setItem(row, 2, usd_item)
            
            total_tl += tl_amount
            total_usd += usd_amount
            row += 1
        
        # Total row
        total_project_item = QTableWidgetItem("Genel Toplam")
        total_project_item.setFont(QFont("Arial", 10, QFont.Bold))
        table.setItem(row, 0, total_project_item)
        
        total_tl_item = QTableWidgetItem(f"₺ {total_tl:,.2f}")
        total_tl_item.setFont(QFont("Arial", 10, QFont.Bold))
        table.setItem(row, 1, total_tl_item)
        
        total_usd_item = QTableWidgetItem(f"$ {total_usd:,.2f}")
        total_usd_item.setFont(QFont("Arial", 10, QFont.Bold))
        table.setItem(row, 2, total_usd_item)
        
        # Style the table
        table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                background: white;
                gridline-color: #DEE2E6;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QHeaderView::section {
                background: #F8F9FA;
                border: 1px solid #DEE2E6;
                padding: 8px;
                font-weight: 600;
                color: #495057;
            }
        """)
        
        # Highlight total row
        for col in range(3):
            item = table.item(row, col)
            if item:
                item.setBackground(QColor(255, 255, 0, 100))  # Light yellow
        
        # Set column widths
        table.setColumnWidth(0, 200)
        table.setColumnWidth(1, 120)
        table.setColumnWidth(2, 120)
        
        # Create container with title
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(10)
        
        # Title
        title_label = QLabel("PROJE TOPLAMLARI")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #2C3E50;
            text-align: center;
            padding: 10px;
            background: #E3F2FD;
            border-radius: 6px;
        """)
        container_layout.addWidget(title_label)
        container_layout.addWidget(table)
        
        return container
    
    def create_monthly_location_analysis(self, payments, month_name):
        """Create monthly location analysis table"""
        if not payments:
            # Return empty table with message
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setSpacing(10)
            
            title_label = QLabel("LOKASYON ANALİZİ")
            title_label.setStyleSheet("""
                font-size: 16px;
                font-weight: 600;
                color: #2C3E50;
                text-align: center;
                padding: 10px;
                background: #E3F2FD;
                border-radius: 6px;
            """)
            container_layout.addWidget(title_label)
            
            message_label = QLabel("Bu ayda ödeme verisi yok")
            message_label.setStyleSheet("""
                font-size: 14px;
                color: #6C757D;
                text-align: center;
                padding: 20px;
                background: #F8F9FA;
                border-radius: 6px;
            """)
            container_layout.addWidget(message_label)
            
            return container
            
        # Group payments by location (account_name)
        location_totals = {}
        for payment in payments:
            location = payment.account_name or "Diğer"
            if location not in location_totals:
                location_totals[location] = {'tl': 0, 'usd': 0}
            
            if payment.currency == "TL":
                location_totals[location]['tl'] += payment.original_amount
            else:
                location_totals[location]['usd'] += payment.usd_amount
        
        # Create table widget
        table = QTableWidget()
        table.setColumnCount(3)
        table.setRowCount(len(location_totals) + 1)  # Locations + total
        
        # Set headers
        headers = ["Lokasyon", "Toplam TL", "Toplam USD"]
        table.setHorizontalHeaderLabels(headers)
        
        # Populate table
        row = 0
        total_tl = 0
        total_usd = 0
        
        for location, amounts in location_totals.items():
            # Location name
            location_item = QTableWidgetItem(location)
            table.setItem(row, 0, location_item)
            
            # TL amount
            tl_amount = amounts['tl']
            if tl_amount > 0:
                tl_item = QTableWidgetItem(f"₺ {tl_amount:,.2f}")
            else:
                tl_item = QTableWidgetItem("₺ 0.00")
            table.setItem(row, 1, tl_item)
            
            # USD amount
            usd_amount = amounts['usd']
            if usd_amount > 0:
                usd_item = QTableWidgetItem(f"$ {usd_amount:,.2f}")
            else:
                usd_item = QTableWidgetItem("$ 0.00")
            table.setItem(row, 2, usd_item)
            
            total_tl += tl_amount
            total_usd += usd_amount
            row += 1
        
        # Total row
        total_location_item = QTableWidgetItem("Genel Toplam")
        total_location_item.setFont(QFont("Arial", 10, QFont.Bold))
        table.setItem(row, 0, total_location_item)
        
        total_tl_item = QTableWidgetItem(f"₺ {total_tl:,.2f}")
        total_tl_item.setFont(QFont("Arial", 10, QFont.Bold))
        table.setItem(row, 1, total_tl_item)
        
        total_usd_item = QTableWidgetItem(f"$ {total_usd:,.2f}")
        total_usd_item.setFont(QFont("Arial", 10, QFont.Bold))
        table.setItem(row, 2, total_usd_item)
        
        # Style the table
        table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                background: white;
                gridline-color: #DEE2E6;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QHeaderView::section {
                background: #F8F9FA;
                border: 1px solid #DEE2E6;
                padding: 8px;
                font-weight: 600;
                color: #495057;
            }
        """)
        
        # Highlight total row
        for col in range(3):
            item = table.item(row, col)
            if item:
                item.setBackground(QColor(255, 255, 0, 100))  # Light yellow
        
        # Set column widths
        table.setColumnWidth(0, 200)
        table.setColumnWidth(1, 120)
        table.setColumnWidth(2, 120)
        
        # Create container with title
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(10)
        
        # Title
        title_label = QLabel("LOKASYON ANALİZİ")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #2C3E50;
            text-align: center;
            padding: 10px;
            background: #E3F2FD;
            border-radius: 6px;
        """)
        container_layout.addWidget(title_label)
        container_layout.addWidget(table)
        
        return container
    
    def create_payment_type_table(self, payments, project_filter, title):
        """Create a payment type table for specific project or total"""
        # Filter payments by project
        if project_filter == "PROJECT_A":
            filtered_payments = [p for p in payments if p.project_name and "KUYUM" in p.project_name.upper()]
        elif project_filter == "PROJECT_B":
            filtered_payments = [p for p in payments if p.project_name and "SANAYİ" in p.project_name.upper()]
        else:  # TOTAL
            filtered_payments = payments
        
        # Create table widget
        table = QTableWidget()
        table.setColumnCount(3)
        table.setRowCount(4)  # BANK_TRANSFER, Nakit, Çek, Total
        
        # Set headers
        headers = ["Ödeme Nedeni", "Orijinal Tutar", "USD Eşdeğeri"]
        table.setHorizontalHeaderLabels(headers)
        
        # Calculate totals by payment type
        payment_types = ["BANK_TRANSFER", "Nakit", "Çek"]
        totals_original = {}
        totals_usd = {}
        
        for payment_type in payment_types:
            totals_original[payment_type] = 0
            totals_usd[payment_type] = 0
            
            for payment in filtered_payments:
                # Determine payment type based on proper logic
                if payment_type == "Çek":
                    # Check payments are identified by is_check_payment flag
                    if payment.is_check_payment:
                        # Use original check amount and USD equivalent
                        if payment.original_cek_tutari > 0:
                            totals_original[payment_type] += payment.original_cek_tutari
                        if payment.cek_usd_amount > 0:
                            totals_usd[payment_type] += payment.cek_usd_amount
                        elif payment.usd_amount > 0:
                            totals_usd[payment_type] += payment.usd_amount
                elif payment_type == "Nakit":
                    # Cash payments - check both tahsilat_sekli and payment_channel
                    if (payment.tahsilat_sekli == "Nakit" or 
                        payment.payment_channel == "NAKİT" or
                        "KASA" in (payment.account_name or "").upper()):
                        totals_original[payment_type] += payment.original_amount
                        if payment.usd_amount > 0:
                            totals_usd[payment_type] += payment.usd_amount
                elif payment_type == "BANK_TRANSFER":
                    # Bank transfer payments - check payment_channel for proper mapping
                    if (payment.payment_channel == "BANKA HAVALESİ" or
                        "YAPI" in (payment.account_name or "").upper() or
                        "HAVALE" in (payment.account_name or "").upper() or
                        "TRANSFER" in (payment.account_name or "").upper() or
                        (payment.tahsilat_sekli == "BANK_TRANSFER" and not payment.is_check_payment)):
                        totals_original[payment_type] += payment.original_amount
                        if payment.usd_amount > 0:
                            totals_usd[payment_type] += payment.usd_amount
        
        # Populate table
        for i, payment_type in enumerate(payment_types):
            # Payment type
            type_item = QTableWidgetItem(payment_type)
            type_item.setFont(QFont("Arial", 10, QFont.Bold))
            table.setItem(i, 0, type_item)
            
            # Original amount
            original_amount = totals_original[payment_type]
            if original_amount > 0:
                original_item = QTableWidgetItem(f"{original_amount:,.2f}")
            else:
                original_item = QTableWidgetItem("")
            table.setItem(i, 1, original_item)
            
            # USD amount
            usd_amount = totals_usd[payment_type]
            if usd_amount > 0:
                usd_item = QTableWidgetItem(f"$ {usd_amount:,.2f}")
            else:
                usd_item = QTableWidgetItem("")
            table.setItem(i, 2, usd_item)
        
        # Total row
        total_original = sum(totals_original.values())
        total_usd = sum(totals_usd.values())
        
        total_type_item = QTableWidgetItem("Genel Toplam" if project_filter == "TOTAL" else "Toplam")
        total_type_item.setFont(QFont("Arial", 10, QFont.Bold))
        table.setItem(3, 0, total_type_item)
        
        if total_original > 0:
            total_original_item = QTableWidgetItem(f"{total_original:,.2f}")
        else:
            total_original_item = QTableWidgetItem("-")
        table.setItem(3, 1, total_original_item)
        
        if total_usd > 0:
            total_usd_item = QTableWidgetItem(f"$ {total_usd:,.2f}")
        else:
            total_usd_item = QTableWidgetItem("$ -")
        table.setItem(3, 2, total_usd_item)
        
        # Style the table
        table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                background: white;
                gridline-color: #DEE2E6;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QHeaderView::section {
                background: #F8F9FA;
                border: 1px solid #DEE2E6;
                padding: 8px;
                font-weight: 600;
                color: #495057;
            }
        """)
        
        # Highlight total row
        if project_filter == "TOTAL":
            for col in range(3):
                item = table.item(3, col)
                if item:
                    item.setBackground(QColor(255, 255, 0, 100))  # Light yellow
        
        # Set column widths
        table.setColumnWidth(0, 150)
        table.setColumnWidth(1, 120)
        table.setColumnWidth(2, 120)
        
        # Create container with title
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(10)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #2C3E50;
            text-align: center;
            padding: 10px;
            background: #E9ECEF;
            border-radius: 6px;
        """)
        container_layout.addWidget(title_label)
        container_layout.addWidget(table)
        
        return container
    
    def create_weekly_tabs_for_new_data(self, new_payments):
        """Create weekly tabs for newly imported data"""
        if not hasattr(self, 'report_tabs'):
            return
            
        # Group new payments by week
        weekly_data = {}
        for payment in new_payments:
            if payment.date:
                # Get Monday of the week
                monday = payment.date - timedelta(days=payment.date.weekday())
                week_key = monday.strftime('%Y-%m-%d')
                if week_key not in weekly_data:
                    weekly_data[week_key] = []
                weekly_data[week_key].append(payment)
        
        # Create tabs for each week
        for week_key in sorted(weekly_data.keys()):
            week_payments = weekly_data[week_key]
            week_start = datetime.strptime(week_key, '%Y-%m-%d').date()
            week_end = week_start + timedelta(days=6)
            
            # Check if tab already exists
            tab_name = f"Hafta {week_start.strftime('%d.%m')} - {week_end.strftime('%d.%m')}"
            tab_exists = False
            for i in range(self.report_tabs.count()):
                if self.report_tabs.tabText(i) == tab_name:
                    tab_exists = True
                    break
            
            if not tab_exists:
                # Create new weekly tab
                weekly_widget = self.create_weekly_report_widget(week_start, week_end, week_payments)
                self.report_tabs.addTab(weekly_widget, tab_name)
    
    def create_weekly_report_widget(self, week_start, week_end, payments):
        """Create a weekly report widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Week title
        title = QLabel(f"{week_start.strftime('%d.%m.%Y')} - {week_end.strftime('%d.%m.%Y')} Haftası")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: 700;
            color: #2C3E50;
            padding: 15px;
            background: #F8F9FA;
            border-radius: 8px;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # Create daily breakdown table
        daily_table = QTableWidget()
        daily_table.setColumnCount(8)  # Customer + 7 days
        daily_table.setRowCount(len(set(p.customer_name for p in payments if p.customer_name)))
        
        # Set headers
        headers = ["Müşteri Adı"] + [f"{week_start + timedelta(days=i):%d.%m}" for i in range(7)]
        daily_table.setHorizontalHeaderLabels(headers)
        
        # Group payments by customer and day
        customer_data = {}
        for payment in payments:
            if payment.customer_name and payment.date:
                customer = payment.customer_name
                # Ensure both dates are datetime objects for proper subtraction
                import datetime as dt_module
                if isinstance(payment.date, dt_module.date) and not isinstance(payment.date, dt_module.datetime):
                    payment_date = dt_module.datetime.combine(payment.date, dt_module.time())
                else:
                    payment_date = payment.date
                
                if isinstance(week_start, dt_module.date) and not isinstance(week_start, dt_module.datetime):
                    week_start_dt = dt_module.datetime.combine(week_start, dt_module.time())
                else:
                    week_start_dt = week_start
                
                day_index = (payment_date - week_start_dt).days
                
                if customer not in customer_data:
                    customer_data[customer] = [0] * 7
                
                if 0 <= day_index < 7:
                    # Use the already converted USD amount from PaymentData
                    usd_amount = payment.usd_amount if payment.usd_amount > 0 else payment.amount
                    customer_data[customer][day_index] += usd_amount
        
        # Populate table
        row = 0
        for customer, daily_amounts in customer_data.items():
            # Customer name
            customer_item = QTableWidgetItem(customer)
            daily_table.setItem(row, 0, customer_item)
            
            # Daily amounts
            for day in range(7):
                amount = daily_amounts[day]
                if amount > 0:
                    amount_item = QTableWidgetItem(f"$ {amount:,.2f}")
                else:
                    amount_item = QTableWidgetItem("")
                daily_table.setItem(row, day + 1, amount_item)
            
            row += 1
        
        # Style the table
        daily_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                background: white;
                gridline-color: #DEE2E6;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QHeaderView::section {
                background: #F8F9FA;
                border: 1px solid #DEE2E6;
                padding: 8px;
                font-weight: 600;
                color: #495057;
            }
        """)
        
        # Set column widths
        daily_table.setColumnWidth(0, 200)  # Customer name
        for i in range(1, 8):
            daily_table.setColumnWidth(i, 100)  # Daily columns
        
        layout.addWidget(daily_table)
        
        return widget
    
    def show_table_context_menu(self, position):
        """Show context menu for table operations with Excel-like features"""
        menu = QMenu(self)
        
        # Copy actions
        copy_action = menu.addAction("📋 Kopyala")
        copy_action.triggered.connect(self.copy_selected_cells)
        
        copy_row_action = menu.addAction("📋 Satırı Kopyala")
        copy_row_action.triggered.connect(self.copy_selected_row)
        
        copy_all_action = menu.addAction("📋 Tümünü Kopyala")
        copy_all_action.triggered.connect(self.copy_all_data)
        
        menu.addSeparator()
        
        # Select actions
        select_all_action = menu.addAction("✅ Tümünü Seç")
        select_all_action.triggered.connect(self.select_all_rows)
        
        select_none_action = menu.addAction("❌ Seçimi Kaldır")
        select_none_action.triggered.connect(self.clear_selection)
        
        menu.addSeparator()
        
        # Sort actions
        sort_asc_action = menu.addAction("🔢 A-Z Sırala")
        sort_asc_action.triggered.connect(lambda: self.sort_current_column(True))
        
        sort_desc_action = menu.addAction("🔢 Z-A Sırala")
        sort_desc_action.triggered.connect(lambda: self.sort_current_column(False))
        
        menu.addSeparator()
        
        # Filter actions
        clear_filter_action = menu.addAction("🔍 Filtreleri Temizle")
        clear_filter_action.triggered.connect(self.clear_filters)
        
        advanced_filter_action = menu.addAction("🔍 Gelişmiş Filtre")
        advanced_filter_action.triggered.connect(self.show_advanced_filter)
        
        menu.addSeparator()
        
        # Delete actions
        delete_selected_action = menu.addAction("🗑️ Seçili Satırları Sil")
        delete_selected_action.triggered.connect(self.delete_selected_rows)
        
        menu.addSeparator()
        
        # Export actions
        export_filtered_action = menu.addAction("📤 Veriyi Dışa Aktar")
        export_filtered_action.triggered.connect(self.export_filtered_data)
        
        menu.exec(self.data_table.mapToGlobal(position))
    
    def show_column_filter_menu(self, position):
        """Show Excel-like column filter menu"""
        # Get the column index
        column = self.data_table.horizontalHeader().logicalIndexAt(position)
        if column < 0:
            return
        
        # Get column name
        column_name = self.data_table.horizontalHeaderItem(column).text() if self.data_table.horizontalHeaderItem(column) else f"Kolon {column + 1}"
        
        menu = QMenu(self)
        menu.setTitle(f"Filtrele: {column_name}")
        
        # Get unique values for this column
        unique_values = set()
        for row in range(self.data_table.rowCount()):
            item = self.data_table.item(row, column)
            if item and item.text().strip():
                unique_values.add(item.text().strip())
        
        # Sort values
        sorted_values = sorted(unique_values)
        
        # Add "Tümünü Seç" option
        select_all_action = QAction("✓ Tümünü Seç", self)
        select_all_action.triggered.connect(lambda: self.filter_column_by_values(column, sorted_values))
        menu.addAction(select_all_action)
        
        # Add "Tümünü Temizle" option
        clear_all_action = QAction("✗ Tümünü Temizle", self)
        clear_all_action.triggered.connect(lambda: self.filter_column_by_values(column, []))
        menu.addAction(clear_all_action)
        
        menu.addSeparator()
        
        # Add individual value filters
        for value in sorted_values[:20]:  # Limit to first 20 values for performance
            action = QAction(f"• {value}", self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, val=value: self.toggle_column_filter(column, val))
            menu.addAction(action)
        
        if len(sorted_values) > 20:
            more_action = QAction(f"... ve {len(sorted_values) - 20} tane daha", self)
            more_action.setEnabled(False)
            menu.addAction(more_action)
        
        menu.exec(self.data_table.horizontalHeader().mapToGlobal(position))
    
    def filter_column_by_values(self, column, values):
        """Filter table by column values"""
        # This is a simplified implementation
        # In a real implementation, you would filter the underlying data model
        pass
    
    def toggle_column_filter(self, column, value):
        """Toggle column filter for a specific value"""
        # This is a simplified implementation
        # In a real implementation, you would toggle the filter state
        pass
    
    def copy_selected_cells(self):
        """Copy selected cells to clipboard"""
        selected_items = self.data_table.selectedItems()
        if not selected_items:
            return
        
        # Group items by row
        rows = {}
        for item in selected_items:
            row = item.row()
            col = item.column()
            if row not in rows:
                rows[row] = {}
            rows[row][col] = item.text()
        
        # Create clipboard text
        clipboard_text = ""
        for row in sorted(rows.keys()):
            row_text = []
            for col in sorted(rows[row].keys()):
                row_text.append(rows[row][col])
            clipboard_text += "\t".join(row_text) + "\n"
        
        QApplication.clipboard().setText(clipboard_text.strip())
    
    def copy_selected_row(self):
        """Copy selected row to clipboard"""
        current_row = self.data_table.currentRow()
        if current_row < 0:
            return
        
        row_text = []
        for col in range(self.data_table.columnCount()):
            item = self.data_table.item(current_row, col)
            row_text.append(item.text() if item else "")
        
        QApplication.clipboard().setText("\t".join(row_text))
    
    def copy_all_data(self):
        """Copy all table data to clipboard"""
        all_text = ""
        for row in range(self.data_table.rowCount()):
            row_text = []
            for col in range(self.data_table.columnCount()):
                item = self.data_table.item(row, col)
                row_text.append(item.text() if item else "")
            all_text += "\t".join(row_text) + "\n"
        
        QApplication.clipboard().setText(all_text.strip())
    
    def select_all_rows(self):
        """Select all rows in the table"""
        self.data_table.selectAll()
    
    def clear_selection(self):
        """Clear current selection"""
        self.data_table.clearSelection()
    
    def sort_current_column(self, ascending=True):
        """Sort table by current column"""
        current_col = self.data_table.currentColumn()
        if current_col < 0:
            return
        
        self.data_table.sortItems(current_col, Qt.AscendingOrder if ascending else Qt.DescendingOrder)
    
    def show_advanced_filter(self):
        """Show advanced filter dialog with comprehensive Excel-like filtering"""
        dialog = AdvancedFilterDialog(self.current_payments, self)
        dialog.filter_applied.connect(self.on_advanced_filter_applied)
        if dialog.exec() == QDialog.Accepted:
            filtered_payments = dialog.get_filtered_payments()
            self.display_filtered_data(filtered_payments)
    
    def on_advanced_filter_applied(self, filtered_payments):
        """Handle advanced filter applied signal"""
        self.display_filtered_data(filtered_payments)
    
    def clear_filters(self):
        """Clear all filters and show all data"""
        # Clear column filters
        if hasattr(self, '_column_filters'):
            self._column_filters.clear()
        
        # Reset to show all data
        if self.main_data is not None and not self.main_data.empty:
            self._refresh_table_view(self.main_data)
        else:
            self.update_data_table()
            
        QMessageBox.information(self, "Başarılı", "Tüm filtreler temizlendi")
    
    def display_filtered_data(self, filtered_payments):
        """Display filtered data in the table"""
        self.current_payments = filtered_payments
        self.update_data_table()
        
        # Show filter status
        total_count = len(self.storage.get_all_payments())
        filtered_count = len(filtered_payments)
        QMessageBox.information(
            self, 
            "Filtre Uygulandı", 
            f"Filtreleme tamamlandı!\n\n"
            f"Toplam kayıt: {total_count}\n"
            f"Filtrelenmiş kayıt: {filtered_count}\n"
            f"Gösterilen: {filtered_count}"
        )
    
    
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
                        'Ödenen Tutar': payment.usd_amount,
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
        
        # Update main_data DataFrame
        self._populate_main_data()
        
        self.update_data_table()
        self.update_statistics()
    
    def update_statistics(self):
        """Update statistics display"""
        stats = self.storage.get_statistics()
        
        stats_text = f"""VERİ İSTATİSTİKLERİ
{'='*30}

Genel Bilgiler:
   • Toplam Ödeme: {stats['total_payments']:,} kayıt
   • Toplam TL Tutar: {stats['total_amount_tl']:,.2f} TL
   • Toplam USD Tutar: {stats['total_amount_usd']:,.2f} USD

Proje Bilgileri:
   • Proje Sayısı: {stats['projects']} proje
   • Müşteri Sayısı: {stats['customers']} müşteri
   • Kanal Sayısı: {stats['channels']} kanal
        """
        
        if stats['date_range']:
            stats_text += f"""
Tarih Aralığı:
   • Başlangıç: {stats['date_range']['start']}
   • Bitiş: {stats['date_range']['end']}
            """
        
        # Create a modern, card-style stats display with better visual hierarchy
        # Enhanced number formatting for better readability
        def format_currency(amount, currency_symbol=""):
            """Format currency with proper Turkish number formatting"""
            if amount >= 1_000_000:
                return f"{currency_symbol}{amount/1_000_000:.1f}M"
            elif amount >= 1_000:
                return f"{currency_symbol}{amount/1_000:.1f}K"
            else:
                return f"{currency_symbol}{amount:,.0f}"
        
        tl_formatted = format_currency(stats['total_amount_tl']) + " TL"
        usd_formatted = format_currency(stats['total_amount_usd'], "$")
        
        stats_html = f"""
        <div style="font-family: 'Segoe UI', Arial; font-size: 14px; line-height: 1.9;">
            <div style="margin-bottom: 20px; padding: 15px; background: linear-gradient(135deg, rgba(74, 144, 226, 0.1), rgba(74, 144, 226, 0.05)); border-radius: 12px; border-left: 4px solid #4A90E2; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="color: #2C3E50; font-weight: 800; font-size: 16px; margin-bottom: 12px; display: flex; align-items: center;">
                    Mali Durum Özeti
                </div>
                <div style="color: #495057; margin-bottom: 8px; display: flex; justify-content: space-between;">
                    <span>Toplam Kayıt:</span>
                    <strong style="color: #28A745; font-size: 15px;">{stats['total_payments']:,} adet</strong>
                </div>
                <div style="color: #495057; margin-bottom: 8px; display: flex; justify-content: space-between;">
                    <span>TL Tutarı:</span>
                    <strong style="color: #007BFF; font-size: 15px;">{tl_formatted}</strong>
                </div>
                <div style="color: #495057; display: flex; justify-content: space-between;">
                    <span>USD Tutarı:</span>
                    <strong style="color: #28A745; font-size: 15px;">{usd_formatted}</strong>
                </div>
            </div>
            
            <div style="margin-bottom: 20px; padding: 15px; background: linear-gradient(135deg, rgba(40, 167, 69, 0.1), rgba(40, 167, 69, 0.05)); border-radius: 12px; border-left: 4px solid #28A745; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="color: #2C3E50; font-weight: 800; font-size: 16px; margin-bottom: 12px;">
                    🏢 Proje ve Müşteri Bilgileri
                </div>
                <div style="color: #495057; display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; gap: 20px;">
                        <div style="text-align: center;">
                            <div style="color: #6610F2; font-weight: 700; font-size: 18px;">{stats['projects']}</div>
                            <div style="font-size: 12px; color: #6C757D;">Proje</div>
                        </div>
                        <div style="width: 1px; height: 30px; background-color: #DEE2E6;"></div>
                        <div style="text-align: center;">
                            <div style="color: #6610F2; font-weight: 700; font-size: 18px;">{stats['customers']}</div>
                            <div style="font-size: 12px; color: #6C757D;">Müşteri</div>
                        </div>
                    </div>
                </div>
            </div>
        """
        
        if stats['date_range']:
            stats_html += f"""
            <div style="padding: 12px; background-color: rgba(255, 193, 7, 0.1); border-radius: 8px; border-left: 4px solid #FFC107;">
                <div style="color: #2C3E50; font-weight: 700; font-size: 14px; margin-bottom: 8px;">📅 Veri Aralığı</div>
                <div style="color: #495057; font-size: 12px;">{stats['date_range']['start']} - {stats['date_range']['end']}</div>
            </div>
            """
        
        stats_html += "</div>"
        # Update stats in the new UI if the stats content exists
        if hasattr(self, 'stats_content'):
            self.update_stats_display()
    
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
        """Create the main currency rates tab with clean design"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Apply clean, consistent styling
        tab_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                color: #495057;
            }
        """)
        
        # Simple, clean title section
        title_layout = QHBoxLayout()
        title_label = QLabel("TCMB Döviz Kurları")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #495057;
                background: #F8F9FA;
                padding: 15px;
                border-radius: 6px;
                border: 1px solid #DEE2E6;
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
        
        # Use flexible sizing instead of fixed pixels
        main_splitter.setStretchFactor(0, 1)  # Controls take 1 part
        main_splitter.setStretchFactor(1, 3)  # Display takes 3 parts
        
        # Status and progress
        status_layout = QVBoxLayout()
        
        self.currency_progress_bar = QProgressBar()
        self.currency_progress_bar.setVisible(False)
        status_layout.addWidget(self.currency_progress_bar)
        
        self.currency_status_label = QLabel("Hazır")
        self.currency_status_label.setStyleSheet("""
            QLabel {
                background-color: #D4EDDA;
                color: #155724;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #C3E6CB;
                margin: 5px;
                font-weight: 600;
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
        """Create the currency control panel with clean design"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Apply clean, consistent styling
        panel.setStyleSheet("""
            QWidget {
                background-color: #F8F9FA;
                color: #495057;
                border-radius: 6px;
                border: 1px solid #DEE2E6;
            }
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                color: #495057;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                color: #495057;
                subcontrol-origin: margin;
                left: 10px;
                padding: 5px 10px;
                background-color: #F8F9FA;
                border-radius: 4px;
                border: 1px solid #DEE2E6;
            }
            QLabel {
                color: #495057;
                font-size: 13px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #007BFF, stop:1 #0056B3);
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #0056B3, stop:1 #004085);
            }
            QDateEdit {
                background-color: white;
                border: 1px solid #DEE2E6;
                border-radius: 4px;
                padding: 8px;
                color: #495057;
                font-size: 13px;
            }
            QDateEdit:focus {
                border-color: #007BFF;
            }
        """)
        
        # Date range selection
        date_group = QGroupBox("Tarih Aralığı Seçimi")
        date_layout = QVBoxLayout(date_group)
        date_layout.setSpacing(15)  # Better spacing within group
        
        # Start date
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Başlangıç:"))
        self.currency_start_date = QDateEdit()
        self.currency_start_date.setDate(QDate.currentDate().addMonths(-1))
        self.currency_start_date.setCalendarPopup(True)
        start_layout.addWidget(self.currency_start_date)
        date_layout.addLayout(start_layout)
        
        # End date
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("Bitiş:"))
        self.currency_end_date = QDateEdit()
        self.currency_end_date.setDate(QDate.currentDate())
        self.currency_end_date.setCalendarPopup(True)
        end_layout.addWidget(self.currency_end_date)
        date_layout.addLayout(end_layout)
        
        # Quick selection buttons with clean styling
        quick_layout = QVBoxLayout()
        quick_layout.setSpacing(8)
        
        today_btn = QPushButton("Bugün")
        today_btn.clicked.connect(lambda: self.set_currency_date_range_and_show_rate(0))
        
        week_btn = QPushButton("Bu Hafta")
        week_btn.clicked.connect(lambda: self.set_currency_date_range_and_show_rate(7))
        
        month_btn = QPushButton("Bu Ay")
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
                background-color: #E3F2FD;
                color: #1565C0;
                padding: 15px;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                text-align: center;
                border: 1px solid #BBDEFB;
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
                background-color: white;
                color: #495057;
                padding: 12px;
                border-radius: 6px;
                border: 1px solid #DEE2E6;
                font-size: 13px;
                line-height: 1.4;
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
        
        # Tab widget for different views with clean styling
        self.currency_tab_widget = QTabWidget()
        self.currency_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E1E8ED;
                border-radius: 8px;
                background-color: white;
                margin-top: 5px;
            }
            
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #F8F9FA, stop:1 #E9ECEF);
                color: #495057;
                padding: 15px 25px; /* Increased padding for better spacing */
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid #DEE2E6;
                border-bottom: none;
                font-weight: 600;
                font-size: 14px; /* Slightly increased font size */
                min-width: 130px; /* Increased min-width */
            }
            
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #28A745, stop:1 #1E7E34);
                color: white;
                border-color: #28A745;
            }
            
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #E9ECEF, stop:1 #DEE2E6);
                color: #2C3E50;
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
        
        # Calendar widget with clean styling
        self.currency_calendar = QCalendarWidget()
        self.currency_calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: white;
                color: #495057;
                alternate-background-color: #F8F9FA;
                font-size: 13px;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
            }
            QCalendarWidget QTableView {
                selection-background-color: #007BFF;
                selection-color: white;
                background-color: white;
                color: #495057;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #F8F9FA;
                border-bottom: 1px solid #DEE2E6;
            }
            QCalendarWidget QToolButton {
                background-color: #007BFF;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 4px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: white;
                color: #495057;
                selection-background-color: #007BFF;
            }
        """)
        self.currency_calendar.selectionChanged.connect(self.on_currency_date_selected)
        layout.addWidget(self.currency_calendar)
        
        # Selected date info
        self.currency_date_info_label = QLabel("Tarih seçin...")
        self.currency_date_info_label.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                color: #1565C0;
                padding: 12px;
                border-radius: 6px;
                border: 1px solid #BBDEFB;
                font-weight: 600;
                font-size: 14px;
                margin: 8px;
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
        
        # Clean table styling
        self.currency_rates_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #F8F9FA;
                gridline-color: #DEE2E6;
                selection-background-color: #E3F2FD;
                color: #495057;
                font-size: 13px;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #DEE2E6;
            }
            QTableWidget::item:selected {
                background-color: #007BFF;
                color: white;
            }
            QHeaderView::section {
                background-color: #F8F9FA;
                color: #495057;
                padding: 10px;
                border: 1px solid #DEE2E6;
                font-weight: 600;
                font-size: 13px;
            }
        """)
        
        self.currency_rates_table.setAlternatingRowColors(True)
        self.currency_rates_table.setSortingEnabled(True)
        self.currency_rates_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.currency_rates_table)
        
        self.currency_tab_widget.addTab(tab, "Tablo Görünümü")
    
    def show_currency_rates(self):
        """Switch to currency rates tab"""
        # Safety check - only proceed if tab_widget exists
        if not hasattr(self, 'tab_widget'):
            return
            
        # Find and switch to the currency rates tab
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "Döviz Kurları":
                self.tab_widget.setCurrentIndex(i)
                break
    
    def show_currency_conversion_details(self):
        """Show TL to USD conversion details"""
        logger.info("show_currency_conversion_details called")
        
        # Switch to data table page first
        self.show_data_table_section()
        
        # Wait a moment for the page to initialize
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._create_conversion_tab_after_delay)
    
    def _create_conversion_tab_after_delay(self):
        """Create conversion tab after data table page is initialized"""
        # Safety check - only proceed if tab_widget exists
        if not hasattr(self, 'tab_widget'):
            logger.warning("tab_widget still not found after delay")
            return
            
        # Find and switch to the conversion details tab
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "TL-USD Dönüşüm Detayları":
                logger.info("Found existing conversion tab, switching to it")
                self.tab_widget.setCurrentIndex(i)
                return
        
        # If tab doesn't exist, create it
        logger.info("Creating new conversion tab")
        self.create_currency_conversion_tab()
        
        # Switch to the newly created tab
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "TL-USD Dönüşüm Detayları":
                logger.info("Switching to newly created conversion tab")
                self.tab_widget.setCurrentIndex(i)
                break
    
    def create_currency_conversion_tab(self):
        """Create the TL-USD conversion details tab"""
        # Create the main widget
        conversion_widget = QWidget()
        layout = QVBoxLayout(conversion_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("TL-USD DÖNÜŞÜM DETAYLARI")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: 600;
            color: #2C3E50;
            text-align: center;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 8px;
            margin-bottom: 10px;
        """)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel("Bu tablo, TL hesap adına sahip tüm ödemeleri gösterir. Dönüştürme başarısız olan ödemeler için USD eşdeğeri 'N/A' olarak görünür.")
        desc_label.setStyleSheet("""
            font-size: 12px;
            color: #6C757D;
            text-align: center;
            padding: 10px;
            background: #F8F9FA;
            border-radius: 6px;
            margin-bottom: 15px;
        """)
        layout.addWidget(desc_label)
        
        # Create the conversion details table
        self.conversion_table = QTableWidget()
        self.conversion_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                gridline-color: #E0E0E0;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #F0F0F0;
            }
            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                color: #333;
                padding: 10px;
                border: none;
                border-right: 1px solid #E0E0E0;
                border-bottom: 1px solid #E0E0E0;
                font-weight: 600;
                font-size: 11px;
            }
        """)
        
        # Set up table columns
        headers = [
            "SIRA NO",
            "MÜŞTERİ ADI",
            "PROJE ADI", 
            "ÖDEME TARİHİ",
            "ORİJİNAL TUTAR (TL)",
            "DÖNÜŞTÜRÜLEN TUTAR (USD)",
            "DÖVİZ KURU",
            "KUR TARİHİ",
            "KUR KAYNAĞI"
        ]
        
        self.conversion_table.setColumnCount(len(headers))
        self.conversion_table.setHorizontalHeaderLabels(headers)
        
        # Populate the table with conversion data
        self.populate_conversion_table()
        
        # Set column widths
        self.conversion_table.setColumnWidth(0, 60)   # SIRA NO
        self.conversion_table.setColumnWidth(1, 150)  # MÜŞTERİ ADI
        self.conversion_table.setColumnWidth(2, 120)  # PROJE ADI
        self.conversion_table.setColumnWidth(3, 100)  # ÖDEME TARİHİ
        self.conversion_table.setColumnWidth(4, 120)  # ORİJİNAL TUTAR (TL)
        self.conversion_table.setColumnWidth(5, 120)  # DÖNÜŞTÜRÜLEN TUTAR (USD)
        self.conversion_table.setColumnWidth(6, 80)   # DÖVİZ KURU
        self.conversion_table.setColumnWidth(7, 100)  # KUR TARİHİ
        self.conversion_table.setColumnWidth(8, 100)  # KUR KAYNAĞI
        
        # Enable sorting
        self.conversion_table.setSortingEnabled(True)
        
        # Add table to layout
        layout.addWidget(self.conversion_table)
        
        # Add summary label
        self.conversion_summary_label = QLabel("Dönüştürülen ödeme sayısı: 0")
        self.conversion_summary_label.setStyleSheet("""
            font-size: 12px;
            color: #495057;
            text-align: center;
            padding: 8px;
            background: #E9ECEF;
            border-radius: 4px;
            margin-bottom: 10px;
        """)
        layout.addWidget(self.conversion_summary_label)
        
        # Add refresh button
        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1E7E34;
            }
        """)
        refresh_btn.clicked.connect(self.populate_conversion_table)
        layout.addWidget(refresh_btn)
        
        # Add the tab to the main tab widget
        self.tab_widget.addTab(conversion_widget, "TL-USD Dönüşüm Detayları")
    
    def populate_conversion_table(self):
        """Populate the conversion details table"""
        logger.info("populate_conversion_table called")
        
        if not self.current_payments:
            logger.info("No current payments, clearing table")
            self.conversion_table.setRowCount(0)
            return
        
        # Filter payments that were actually converted from TL to USD
        # These are payments from TL accounts that were successfully converted
        converted_payments = []
        tl_accounts_found = []
        for payment in self.current_payments:
            # Debug logging
            if payment.account_name and "TL" in payment.account_name.upper():
                tl_accounts_found.append(payment.account_name)
                logger.info(f"Found TL account: {payment.account_name}, usd_amount: {payment.usd_amount}, conversion_rate: {payment.conversion_rate}")
            
            # Show ALL payments from TL accounts (regardless of conversion success)
            if (payment.account_name and 
                "TL" in payment.account_name.upper()):
                converted_payments.append(payment)
        
        logger.info(f"Total TL accounts found: {len(tl_accounts_found)}")
        logger.info(f"TL accounts: {tl_accounts_found}")
        
        logger.info(f"Found {len(converted_payments)} TL payments (showing all TL accounts)")
        
        # Set row count
        self.conversion_table.setRowCount(len(converted_payments))
        
        # Populate table
        for i, payment in enumerate(converted_payments):
            # SIRA NO
            self.conversion_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            
            # MÜŞTERİ ADI
            self.conversion_table.setItem(i, 1, QTableWidgetItem(payment.customer_name or ""))
            
            # PROJE ADI
            self.conversion_table.setItem(i, 2, QTableWidgetItem(payment.project_name or ""))
            
            # ÖDEME TARİHİ
            date_str = payment.date.strftime("%d.%m.%Y") if payment.date else ""
            self.conversion_table.setItem(i, 3, QTableWidgetItem(date_str))
            
            # ORİJİNAL TUTAR (TL)
            tl_amount = f"₺{payment.original_amount:,.2f}"
            self.conversion_table.setItem(i, 4, QTableWidgetItem(tl_amount))
            
            # DÖNÜŞTÜRÜLEN TUTAR (USD) - Use pre-calculated values
            usd_amount = payment.usd_amount
            exchange_rate = payment.conversion_rate
            rate_date = payment.conversion_date or payment.date
            rate_source = "TCMB"
            
            usd_amount_str = f"${usd_amount:,.2f}" if usd_amount > 0 else "N/A"
            self.conversion_table.setItem(i, 5, QTableWidgetItem(usd_amount_str))
            
            # DÖVİZ KURU
            if exchange_rate and exchange_rate > 0:
                rate_str = f"{exchange_rate:.4f}"
            else:
                rate_str = "N/A"
            self.conversion_table.setItem(i, 6, QTableWidgetItem(rate_str))
            
            # KUR TARİHİ
            if rate_date:
                rate_date_str = rate_date.strftime("%d.%m.%Y") if hasattr(rate_date, 'strftime') else str(rate_date)
            else:
                rate_date_str = "N/A"
            self.conversion_table.setItem(i, 7, QTableWidgetItem(rate_date_str))
            
            # KUR KAYNAĞI
            self.conversion_table.setItem(i, 8, QTableWidgetItem(rate_source))
        
        # Resize columns to content
        self.conversion_table.resizeColumnsToContents()
        
        # Update summary label
        if hasattr(self, 'conversion_summary_label'):
            self.conversion_summary_label.setText(f"Dönüştürülen ödeme sayısı: {len(converted_payments)}")
    
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
            # Enhanced display with better visual hierarchy
            rate_html = f"""
            <div style="text-align: center; font-family: 'Segoe UI', Arial;">
                <div style="color: #495057; font-size: 14px; font-weight: 600; margin-bottom: 8px;">USD/TL</div>
                <div style="color: #007BFF; font-size: 24px; font-weight: 700; margin-bottom: 8px;">{current_rate:.4f}</div>
                <div style="color: #6C757D; font-size: 12px;">({rate_date})</div>
            </div>
            """
            self.current_rate_label.setText(rate_html)
        else:
            error_html = """
            <div style="text-align: center; font-family: 'Segoe UI', Arial;">
                <div style="color: #DC3545; font-size: 14px; font-weight: 600;">Kur Bulunamadı</div>
                <div style="color: #6C757D; font-size: 12px; margin-top: 5px;">Lütfen kurları yenileyin</div>
            </div>
            """
            self.current_rate_label.setText(error_html)
    
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
        """Create ALWAYS VISIBLE control panel for report preview - FIXED LAYOUT"""
        controls_widget = QWidget()
        controls_widget.setStyleSheet("""
            QWidget {
                background-color: #F8F9FA;
                border: 2px solid #28A745;
                border-radius: 8px;
                margin: 5px;
                padding: 15px;
            }
        """)
        
        # FORCE FIXED SIZE - NO EXPANSION
        controls_widget.setFixedHeight(80)
        controls_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setSpacing(10)
        controls_layout.setContentsMargins(10, 10, 10, 10)
        
        # Date range info - COMPACT
        self.preview_date_label = QLabel("📅 Rapor Önizleme Kontrolleri")
        self.preview_date_label.setStyleSheet("""
            QLabel {
                color: #28A745;
                font-size: 12px;
                font-weight: 600;
                padding: 5px 10px;
                background-color: #F8F9FA;
                border-radius: 4px;
                border: 1px solid #28A745;
            }
        """)
        controls_layout.addWidget(self.preview_date_label)
        
        controls_layout.addStretch()
        
        # COMPACT BUTTONS - SMALLER SIZE
        # Refresh button
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(40, 40)
        refresh_btn.setToolTip("Yenile")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #6C757D;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #5A6268;
            }
        """)
        refresh_btn.clicked.connect(self.update_report_preview)
        controls_layout.addWidget(refresh_btn)
        
        # Print button
        print_btn = QPushButton("🖨️")
        print_btn.setFixedSize(40, 40)
        print_btn.setToolTip("Yazdır")
        print_btn.setStyleSheet("""
            QPushButton {
                background: #17A2B8;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #138496;
            }
        """)
        print_btn.clicked.connect(self.print_current_report)
        controls_layout.addWidget(print_btn)
        
        # PDF button
        pdf_btn = QPushButton("📄")
        pdf_btn.setFixedSize(40, 40)
        pdf_btn.setToolTip("PDF Kaydet")
        pdf_btn.setStyleSheet("""
            QPushButton {
                background: #FFC107;
                color: #212529;
                border: none;
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #E0A800;
            }
        """)
        pdf_btn.clicked.connect(self.print_to_pdf)
        controls_layout.addWidget(pdf_btn)
        
        # Excel button
        excel_btn = QPushButton("📊")
        excel_btn.setFixedSize(40, 40)
        excel_btn.setToolTip("Excel Kaydet")
        excel_btn.setStyleSheet("""
            QPushButton {
                background: #28A745;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        excel_btn.clicked.connect(self.export_tab_to_excel)
        controls_layout.addWidget(excel_btn)
        
        # Export button - MAIN ACTION
        export_btn = QPushButton("📤 Dışa Aktar")
        export_btn.setFixedHeight(40)
        export_btn.setMinimumWidth(120)
        export_btn.setStyleSheet("""
            QPushButton {
                background: #007BFF;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 15px;
            }
            QPushButton:hover {
                background: #0056B3;
            }
        """)
        export_btn.clicked.connect(self.export_preview_report)
        controls_layout.addWidget(export_btn)
        
        # ADD TO LAYOUT - ALWAYS AT BOTTOM
        self.report_preview_layout.addWidget(controls_widget)
    
    def show_unified_report_dialog(self):
        """Show UNIFIED report dialog - NO MORE DUPLICATES"""
        dialog = QDialog(self)
        dialog.setWindowTitle("📊 Rapor Oluştur")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("📊 Rapor Türü Seçimi")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #007BFF;
                padding: 10px;
                background-color: #F8F9FA;
                border-radius: 8px;
                border: 2px solid #007BFF;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Report type selection
        type_group = QGroupBox("Rapor Türü")
        type_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #495057;
                border: 2px solid #DEE2E6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 5px 10px;
                background-color: white;
                border-radius: 4px;
            }
        """)
        type_layout = QVBoxLayout(type_group)
        
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            "📈 Günlük Rapor", 
            "📊 Haftalık Rapor", 
            "📅 Aylık Rapor", 
            "📋 Tüm Raporlar",
            "🎯 Özel Tarih Aralığı"
        ])
        self.report_type_combo.setStyleSheet("""
            QComboBox {
                padding: 10px;
                font-size: 14px;
                border: 2px solid #007BFF;
                border-radius: 6px;
                background-color: white;
            }
        """)
        type_layout.addWidget(self.report_type_combo)
        layout.addWidget(type_group)
        
        # Date range selection (for custom reports)
        date_group = QGroupBox("Tarih Aralığı")
        date_group.setStyleSheet(type_group.styleSheet())
        date_layout = QHBoxLayout(date_group)
        
        date_layout.addWidget(QLabel("Başlangıç:"))
        self.dialog_start_date = QDateEdit()
        self.dialog_start_date.setDate(QDate.currentDate().addDays(-7))
        self.dialog_start_date.setStyleSheet("""
            QDateEdit {
                padding: 8px;
                font-size: 13px;
                border: 2px solid #28A745;
                border-radius: 6px;
            }
        """)
        date_layout.addWidget(self.dialog_start_date)
        
        date_layout.addWidget(QLabel("Bitiş:"))
        self.dialog_end_date = QDateEdit()
        self.dialog_end_date.setDate(QDate.currentDate())
        self.dialog_end_date.setStyleSheet(self.dialog_start_date.styleSheet())
        date_layout.addWidget(self.dialog_end_date)
        
        layout.addWidget(date_group)
        
        # Format selection
        format_group = QGroupBox("Çıktı Formatı")
        format_group.setStyleSheet(type_group.styleSheet())
        format_layout = QVBoxLayout(format_group)
        
        self.dialog_format_combo = QComboBox()
        self.dialog_format_combo.addItems([
            "📊 Excel (.xlsx)",
            "📄 PDF (.pdf)", 
            "📝 Word (.docx)",
            "📋 CSV (.csv)"
        ])
        self.dialog_format_combo.setStyleSheet(self.report_type_combo.styleSheet())
        format_layout.addWidget(self.dialog_format_combo)
        layout.addWidget(format_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("❌ İptal")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #6C757D;
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #5A6268;
            }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        button_layout.addStretch()
        
        generate_btn = QPushButton("🚀 Rapor Oluştur")
        generate_btn.setStyleSheet("""
            QPushButton {
                background: #007BFF;
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #0056B3;
            }
        """)
        generate_btn.clicked.connect(lambda: self.process_unified_report(dialog))
        button_layout.addWidget(generate_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def process_unified_report(self, dialog):
        """Process the unified report generation"""
        try:
            report_type = self.report_type_combo.currentText()
            output_format = self.dialog_format_combo.currentText()
            
            # Determine date range based on report type
            if "Günlük" in report_type:
                self.generate_daily_report()
            elif "Haftalık" in report_type:
                self.generate_weekly_report()
            elif "Aylık" in report_type:
                self.generate_monthly_report()
            elif "Tüm Raporlar" in report_type:
                self.generate_all_reports()
            elif "Özel" in report_type:
                start_date = self.dialog_start_date.date().toPython()
                end_date = self.dialog_end_date.date().toPython()
                self.generate_custom_report(start_date, end_date, output_format)
            
            dialog.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Rapor oluşturma hatası: {e}")
    
    def generate_custom_report(self, start_date, end_date, output_format):
        """Generate custom date range report"""
        try:
            # Filter payments by date range
            filtered_payments = [
                p for p in self.current_payments 
                if p.date and start_date <= p.date <= end_date
            ]
            
            if not filtered_payments:
                QMessageBox.warning(self, "Uyarı", "Seçilen tarih aralığında veri bulunamadı")
                return
            
            # Generate report based on format
            extension = output_format.split('(')[1].replace(')', '')
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Özel Rapor Kaydet", 
                f"ozel_rapor_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}{extension}",
                f"{output_format.split('(')[0].strip()} Files (*{extension})"
            )
            
            if file_path:
                if extension == ".xlsx":
                    self.report_generator.export_to_excel(filtered_payments, start_date, end_date, file_path)
                elif extension == ".pdf":
                    self.report_generator.export_to_pdf(filtered_payments, start_date, end_date, file_path)
                elif extension == ".docx":
                    self.report_generator.export_to_word(filtered_payments, start_date, end_date, file_path)
                
                QMessageBox.information(self, "Başarılı", f"Özel rapor oluşturuldu: {file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Özel rapor oluşturma hatası: {e}")
    
    def get_button_style(self, style_type="primary"):
        """Get modern button style based on type"""
        styles = {
            "primary": """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                               stop:0 #4A90E2, stop:1 #357ABD);
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 14px;
                    min-height: 25px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                               stop:0 #5BA0F2, stop:1 #458ACD);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                               stop:0 #3A80D2, stop:1 #2A6AAD);
                }
            """,
            "success": """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                               stop:0 #28A745, stop:1 #1E7E34);
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 14px;
                    min-height: 25px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                               stop:0 #34CE57, stop:1 #2A9544);
                }
            """,
            "warning": """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                               stop:0 #FFC107, stop:1 #E0A800);
                    color: #212529;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 14px;
                    min-height: 25px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                               stop:0 #FFD54F, stop:1 #F0B800);
                }
            """,
            "secondary": """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                               stop:0 #F8F9FA, stop:1 #E9ECEF);
                    color: #000000;
                    border: 1px solid #DEE2E6;
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 14px;
                    min-height: 25px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                               stop:0 #E9ECEF, stop:1 #DEE2E6);
                    border-color: #ADB5BD;
                }
            """
        }
        return styles.get(style_type, styles["primary"])
    
    
    def get_dark_theme_styles(self):
        """Get dark theme styles for sidebar"""
        return """
            QGroupBox {
                font-weight: 700;
                font-size: 15px;
                color: white;
                border: 2px solid #4A90E2;
                border-radius: 12px;
                margin-top: 15px;
                margin-bottom: 10px;
                padding-top: 20px;
                padding-left: 15px;
                padding-right: 15px;
                padding-bottom: 15px;
                background-color: rgba(52, 73, 94, 0.3);
            }
            QGroupBox::title {
                color: #5BA0F2;
                subcontrol-origin: margin;
                left: 15px;
                padding: 5px 10px 5px 10px;
                background-color: #2C3E50;
                border-radius: 6px;
                font-weight: 700;
                font-size: 14px;
            }
            QLabel {
                color: #ECF0F1;
                font-size: 13px;
                font-weight: 500;
            }
            QLineEdit {
                background-color: #34495E;
                border: 2px solid #4A90E2;
                border-radius: 6px;
                padding: 8px;
                color: white;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #5BA0F2;
                background-color: #3A4A5E;
            }
            QComboBox {
                background-color: #34495E;
                border: 2px solid #4A90E2;
                border-radius: 6px;
                padding: 8px;
                color: white;
                font-size: 13px;
            }
            QComboBox:focus {
                border-color: #5BA0F2;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #4A90E2, stop:1 #357ABD);
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #5BA0F2, stop:1 #458ACD);
            }
            QDateEdit {
                background-color: #34495E;
                border: 2px solid #4A90E2;
                border-radius: 6px;
                padding: 8px;
                color: white;
                font-size: 13px;
            }
            QTextEdit {
                background-color: #34495E;
                border: 2px solid #4A90E2;
                border-radius: 6px;
                color: #ECF0F1;
                font-size: 12px;
            }
            QCalendarWidget {
                background-color: #34495E;
                color: white;
                border: 2px solid #4A90E2;
                border-radius: 8px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #2C3E50;
                border-bottom: 1px solid #4A90E2;
            }
            QCalendarWidget QToolButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 4px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: #34495E;
                color: white;
                selection-background-color: #4A90E2;
            }
        """
    
    def get_light_theme_styles(self):
        """Get light theme styles for sidebar"""
        return """
            QGroupBox {
                font-weight: 700;
                font-size: 15px;
                color: #2C3E50;
                border: 2px solid #4A90E2;
                border-radius: 12px;
                margin-top: 15px;
                margin-bottom: 10px;
                padding-top: 20px;
                padding-left: 15px;
                padding-right: 15px;
                padding-bottom: 15px;
                background-color: rgba(248, 249, 250, 0.8);
            }
            QGroupBox::title {
                color: #4A90E2;
                subcontrol-origin: margin;
                left: 15px;
                padding: 5px 10px 5px 10px;
                background-color: white;
                border-radius: 6px;
                font-weight: 700;
                font-size: 14px;
                border: 1px solid #E9ECEF;
            }
            QLabel {
                color: #2C3E50;
                font-size: 13px;
                font-weight: 500;
            }
            QLineEdit {
                background-color: white;
                border: 2px solid #4A90E2;
                border-radius: 6px;
                padding: 8px;
                color: #2C3E50;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #5BA0F2;
                background-color: #F8F9FA;
            }
            QComboBox {
                background-color: white;
                border: 2px solid #4A90E2;
                border-radius: 6px;
                padding: 8px;
                color: #2C3E50;
                font-size: 13px;
            }
            QComboBox:focus {
                border-color: #5BA0F2;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #4A90E2, stop:1 #357ABD);
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                           stop:0 #5BA0F2, stop:1 #458ACD);
            }
            QDateEdit {
                background-color: white;
                border: 2px solid #4A90E2;
                border-radius: 6px;
                padding: 8px;
                color: #2C3E50;
                font-size: 13px;
            }
            QTextEdit {
                background-color: white;
                border: 2px solid #4A90E2;
                border-radius: 6px;
                color: #2C3E50;
                font-size: 12px;
            }
            QCalendarWidget {
                background-color: white;
                color: #2C3E50;
                border: 2px solid #4A90E2;
                border-radius: 8px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #F8F9FA;
                border-bottom: 1px solid #4A90E2;
            }
            QCalendarWidget QToolButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 4px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: white;
                color: #2C3E50;
                selection-background-color: #4A90E2;
                selection-color: white;
            }
        """
    
    def update_report_preview(self):
        """Update the report preview with tabbed interface"""
        try:
            # Clear existing tabs
            self.report_tabs.clear()
            
            if not self.current_payments:
                # Show theme-aware empty state
                empty_widget = QTextEdit()
                empty_widget.setReadOnly(True)
                
                # Theme-aware colors
                title_color = "#6C757D" if not self.is_dark_theme else "#ADB5BD"
                text_color = "#495057" if not self.is_dark_theme else "#E9ECEF"
                secondary_color = "#6C757D" if not self.is_dark_theme else "#CED4DA"
                bg_color = "#F8F9FA" if not self.is_dark_theme else "#404040"
                
                empty_html = f"""
                <div style="font-family: 'Segoe UI', Arial, sans-serif; padding: 40px; text-align: center;">
                    <h2>Rapor Önizleme</h2>
                    <p style="color: {text_color}; font-size: 18px; margin-bottom: 30px;">
                        Rapor önizlemesi için önce veri yükleyin veya manuel giriş yapın.
                    </p>
                    <div style="background-color: {bg_color}; padding: 25px; border-radius: 12px; margin: 30px auto; max-width: 500px;">
                        <h4>Nasıl Başlanır:</h4>
                        <ol style="text-align: left; color: {secondary_color}; font-size: 16px; line-height: 1.6;">
                            <li style="margin-bottom: 10px;">📥 Sol panelden "Veri İçe Aktar" ile dosya yükleyin</li>
                            <li style="margin-bottom: 10px;">📅 Tarih aralığını belirleyin</li>
                            <li style="margin-bottom: 10px;">📊 Rapor türünü seçin ve oluşturun</li>
                            <li>👁️ Bu sekmede önizlemeyi görüntüleyin</li>
                        </ol>
                    </div>
                    <p style="color: {secondary_color}; font-size: 14px; margin-top: 25px;">
                        💡 İpucu: Hızlı başlangıç için araç çubuğundaki "📥 Veri İçe Aktar" butonunu kullanabilirsiniz.
                    </p>
                </div>
                """
                
                empty_widget.setHtml(empty_html)
                empty_widget.setStyleSheet(self.get_report_preview_style())
                self.report_tabs.addTab(empty_widget, "📋 Başlangıç")
                return
            
            # Get date range from current data
            dates = [p.date for p in self.current_payments if p.date]
            if not dates:
                return
            
            start_date = min(dates)
            end_date = max(dates)
            
            # Update date label (with safety check)
            if hasattr(self, 'preview_date_label'):
                self.preview_date_label.setText(f"Tarih Aralığı: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
            
            # Generate HTML preview
            from report_generator import ReportGenerator
            report_gen = ReportGenerator()
            
            html_sheets = report_gen.generate_html_preview(self.current_payments, start_date, end_date)
            
            # Create tabs for each sheet with theme-aware styling
            for sheet_name, html_content in html_sheets.items():
                text_widget = QTextEdit()
                text_widget.setReadOnly(True)
                
                # Apply theme-aware HTML content
                themed_content = self.apply_theme_to_html(html_content)
                text_widget.setHtml(themed_content)
                
                # Ensure consistent styling with data table
                text_widget.setStyleSheet(self.get_report_preview_style())
                
                self.report_tabs.addTab(text_widget, sheet_name)
            
        except Exception as e:
            logger.error(f"Failed to update report preview: {e}")
            error_widget = QTextEdit()
            error_widget.setReadOnly(True)
            
            # Create theme-aware error message
            error_color = "#DC3545" if not self.is_dark_theme else "#F5C6CB"
            text_color = "#495057" if not self.is_dark_theme else "#E9ECEF"
            secondary_color = "#6C757D" if not self.is_dark_theme else "#ADB5BD"
            
            error_html = f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; padding: 30px; text-align: center;">
                <h2 style="color: {error_color}; margin-bottom: 20px;">⚠️ Hata Oluştu</h2>
                <p style="color: {text_color}; font-size: 16px; margin-bottom: 15px;">
                    Rapor önizleme güncellenirken hata oluştu: {e}
                </p>
                <p style="color: {secondary_color}; font-size: 14px;">
                    Lütfen veri yüklü olduğundan ve geçerli tarih aralığı seçildiğinden emin olun.
                </p>
                <div style="margin-top: 25px; padding: 15px; background-color: {'#F8F9FA' if not self.is_dark_theme else '#404040'}; border-radius: 8px;">
                    <h4>Çözüm Önerileri:</h4>
                    <ul style="color: {secondary_color}; text-align: left; display: inline-block;">
                        <li>Veri İçe Aktarma sekmesinden dosya yükleyin</li>
                        <li>Tarih aralığının doğru seçildiğini kontrol edin</li>
                        <li>Sayfayı yenileyip tekrar deneyin</li>
                    </ul>
            </div>
            </div>
            """
            
            error_widget.setHtml(error_html)
            error_widget.setStyleSheet(self.get_report_preview_style())
            self.report_tabs.addTab(error_widget, "⚠️ Hata")
    
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
        """Export current report as PDF with orientation options"""
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
            
            # Ask for orientation
            orientation_dialog = QDialog(self)
            orientation_dialog.setWindowTitle("PDF Yönlendirme Seçimi")
            orientation_dialog.setModal(True)
            orientation_dialog.resize(300, 150)
            
            layout = QVBoxLayout(orientation_dialog)
            
            # Title
            title_label = QLabel("PDF yönlendirmesini seçiniz:")
            title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
            layout.addWidget(title_label)
            
            # Orientation options
            orientation_group = QGroupBox("Yönlendirme")
            orientation_layout = QVBoxLayout(orientation_group)
            
            landscape_radio = QRadioButton("Yatay (Landscape) - Geniş tablolar için önerilen")
            portrait_radio = QRadioButton("Dikey (Portrait) - Kompakt görünüm için")
            landscape_radio.setChecked(True)  # Default to landscape
            
            orientation_layout.addWidget(landscape_radio)
            orientation_layout.addWidget(portrait_radio)
            layout.addWidget(orientation_group)
            
            # Buttons
            button_layout = QHBoxLayout()
            ok_button = QPushButton("Tamam")
            cancel_button = QPushButton("İptal")
            
            ok_button.clicked.connect(orientation_dialog.accept)
            cancel_button.clicked.connect(orientation_dialog.reject)
            
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            if orientation_dialog.exec() != QDialog.Accepted:
                return
            
            # Get selected orientation
            orientation = "landscape" if landscape_radio.isChecked() else "portrait"
            
            # Ask for file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, "PDF Olarak Kaydet", 
                f"tahsilat_raporu_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf",
                "PDF Files (*.pdf)"
            )
            
            if file_path:
                # Generate PDF using report generator with selected orientation
                self.report_generator.export_to_pdf(self.current_payments, start_date, end_date, file_path, orientation)
                QMessageBox.information(self, "Başarılı", f"PDF raporu oluşturuldu: {file_path}")
                
        except Exception as e:
            logger.error(f"Failed to export as PDF: {e}")
            QMessageBox.critical(self, "Hata", f"PDF dışa aktarma hatası: {e}")
    
    def export_to_excel(self):
        """Export current report as Excel with exact same format as application"""
        try:
            if not self.current_payments:
                QMessageBox.warning(self, "Uyarı", "Excel dışa aktarmak için veri bulunamadı.")
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
                self, "Excel Olarak Kaydet", 
                f"tahsilat_raporu_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if file_path:
                # Generate Excel using report generator - this creates the exact same report as the application
                self.report_generator.export_to_excel(self.current_payments, start_date, end_date, file_path)
                QMessageBox.information(self, "Başarılı", f"Excel raporu oluşturuldu: {file_path}")
                
        except Exception as e:
            logger.error(f"Failed to export as Excel: {e}")
            QMessageBox.critical(self, "Hata", f"Excel dışa aktarma hatası: {e}")

    def _setup_excel_header_filters(self, table_widget):
        """Setup Excel-like header filtering for a QTableWidget"""
        # Connect column header clicks to filtering
        header = table_widget.horizontalHeader()
        header.sectionClicked.connect(self._show_filter_menu)
        
        # Store reference to the table widget
        self._filtered_table = table_widget
        
        # Initialize filter state
        self._column_filters = {}
        self._search_filters = {}
        
    def _show_filter_menu(self, column_index):
        """Show Excel-like filter menu for a column"""
        from PySide6.QtWidgets import QMenu, QLineEdit, QCheckBox, QAction, QWidgetAction
        from PySide6.QtCore import Qt
        
        # First, sort the table by the clicked column
        self._filtered_table.sortItems(column_index)
        
        # Create menu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 4px;
                min-width: 200px;
            }
            QMenu::item {
                padding: 6px 12px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #e3f2fd;
            }
        """)
        
        # Add search bar
        search_widget = QLineEdit()
        search_widget.setPlaceholderText("Ara...")
        search_widget.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                font-size: 12px;
            }
        """)
        search_widget.textChanged.connect(lambda text: self._filter_table_by_text(text, column_index))
        
        search_action = QWidgetAction(menu)
        search_action.setDefaultWidget(search_widget)
        menu.addAction(search_action)
        
        # Add separator
        menu.addSeparator()
        
        # Get unique values for this column
        unique_values = self._get_unique_column_values(column_index)
        
        # Add "Select All" option
        select_all_action = QAction("(Tümünü Seç)", self)
        select_all_action.triggered.connect(lambda: self._select_all_column_values(column_index))
        menu.addAction(select_all_action)
        
        # Add "Clear All" option
        clear_all_action = QAction("(Tümünü Temizle)", self)
        clear_all_action.triggered.connect(lambda: self._clear_all_column_values(column_index))
        menu.addAction(clear_all_action)
        
        # Add separator
        menu.addSeparator()
        
        # Add checkboxes for each unique value
        for value in sorted(unique_values, key=str):
            if value:  # Skip empty values
                checkbox = QCheckBox(str(value))
                checkbox.setChecked(True)  # All values selected by default
                
                # Connect to both old and new filtering systems
                checkbox.stateChanged.connect(lambda state, val=value: self._toggle_column_filter(column_index, val, state == Qt.Checked))
                
                # Also connect to the new DataFrame-based filtering
                column_name = self._get_column_name_by_index(column_index)
                if column_name:
                    checkbox.stateChanged.connect(lambda state, col=column_name, val=value: self._update_table_from_filter(col))
                
                checkbox_action = QWidgetAction(menu)
                checkbox_action.setDefaultWidget(checkbox)
                menu.addAction(checkbox_action)
        
        # Show menu below the clicked column header
        header = self._filtered_table.horizontalHeader()
        header_rect = header.sectionPosition(column_index)
        header_height = header.height()
        menu_pos = header.mapToGlobal(header_rect, header_height)
        menu.exec(menu_pos)
        
    def _get_unique_column_values(self, column_index):
        """Get unique non-empty values for a column"""
        values = set()
        for row in range(self._filtered_table.rowCount()):
            item = self._filtered_table.item(row, column_index)
            if item and item.text().strip():
                values.add(item.text().strip())
        return list(values)
        
    def _filter_table_by_text(self, text, column_index):
        """Filter table rows based on search text in a specific column"""
        from turkish_utils import turkish_lower, turkish_contains
        
        search_text = turkish_lower(text).strip()
        
        for row in range(self._filtered_table.rowCount()):
            item = self._filtered_table.item(row, column_index)
            if item:
                cell_text = item.text()
                # Show row if search text is empty or found in cell (with Turkish case handling)
                should_show = not search_text or turkish_contains(cell_text, search_text)
                self._filtered_table.setRowHidden(row, not should_show)
                
    def _toggle_column_filter(self, column_index, value, checked):
        """Toggle filter for a specific column value"""
        if column_index not in self._column_filters:
            self._column_filters[column_index] = set()
            
        if checked:
            self._column_filters[column_index].add(value)
        else:
            self._column_filters[column_index].discard(value)
            
        # Apply both old and new filtering systems
        self._apply_column_filters()
        
        # Also apply DataFrame-based filtering
        column_name = self._get_column_name_by_index(column_index)
        if column_name:
            self._update_table_from_filter(column_name)
        
    def _select_all_column_values(self, column_index):
        """Select all values for a column"""
        unique_values = self._get_unique_column_values(column_index)
        if column_index not in self._column_filters:
            self._column_filters[column_index] = set()
        self._column_filters[column_index].update(unique_values)
        self._apply_column_filters()
        
        # Also apply DataFrame-based filtering
        column_name = self._get_column_name_by_index(column_index)
        if column_name:
            self._update_table_from_filter(column_name)
        
    def _clear_all_column_values(self, column_index):
        """Clear all values for a column"""
        if column_index in self._column_filters:
            self._column_filters[column_index].clear()
        self._apply_column_filters()
        
        # Also apply DataFrame-based filtering
        column_name = self._get_column_name_by_index(column_index)
        if column_name:
            self._update_table_from_filter(column_name)
        
    def _apply_column_filters(self):
        """Apply all column filters to the table"""
        from turkish_utils import turkish_equals
        
        for row in range(self._filtered_table.rowCount()):
            should_show = True
            
            # Check each column filter
            for column_index, allowed_values in self._column_filters.items():
                if allowed_values:  # Only apply filter if values are selected
                    item = self._filtered_table.item(row, column_index)
                    if item:
                        cell_value = item.text().strip()
                        # Check if cell value matches any allowed value (with Turkish case handling)
                        if not any(turkish_equals(cell_value, allowed_value) for allowed_value in allowed_values):
                            should_show = False
                            break
                            
            self._filtered_table.setRowHidden(row, not should_show)

    def _apply_column_filter(self, column_name, selected_values):
        """Core filtering function that performs filtering on the DataFrame"""
        if self.main_data is None:
            return self.main_data
            
        # If all items are selected or "Tümünü Seç" is in the list, return original data
        if not selected_values or "Tümünü Seç" in selected_values:
            return self.main_data
        
        # Use pandas isin() to filter efficiently
        return self.main_data[self.main_data[column_name].isin(selected_values)]

    def _refresh_table_view(self, filtered_dataframe):
        """Update the QTableWidget with filtered DataFrame data"""
        logger.info(f"Refreshing table view with DataFrame shape: {filtered_dataframe.shape if filtered_dataframe is not None else 'None'}")
        
        if filtered_dataframe is None or filtered_dataframe.empty:
            self.data_table.setRowCount(0)
            logger.info("DataFrame is empty, clearing table")
            return
            
        # Clear existing content
        self.data_table.setRowCount(0)
        
        # Get column names from the DataFrame
        columns = filtered_dataframe.columns.tolist()
        
        # Set up table structure
        self.data_table.setColumnCount(len(columns))
        self.data_table.setHorizontalHeaderLabels(columns)
        
        # Repopulate with filtered data
        row_count = len(filtered_dataframe.index)
        self.data_table.setRowCount(row_count)
        
        # Populate table with filtered data
        for i, (_, row) in enumerate(filtered_dataframe.iterrows()):
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setForeground(QColor(33, 37, 41))
                self.data_table.setItem(i, j, item)
        
        # Set proper column widths (updated for new columns)
        self.data_table.setColumnWidth(0, 70)   # SIRA NO
        self.data_table.setColumnWidth(1, 200)  # Müşteri Adı Soyadı
        self.data_table.setColumnWidth(2, 100)  # Tarih
        self.data_table.setColumnWidth(3, 150)  # Proje Adı
        self.data_table.setColumnWidth(4, 150)  # Hesap Adı
        self.data_table.setColumnWidth(5, 180)  # Ödenen Tutar (Orijinal)
        self.data_table.setColumnWidth(6, 80)   # Ödenen Döviz
        self.data_table.setColumnWidth(7, 120)  # USD Eşdeğeri
        self.data_table.setColumnWidth(8, 100)  # Döviz Kuru
        self.data_table.setColumnWidth(9, 120)  # Tahsilat Şekli
        self.data_table.setColumnWidth(10, 120) # Ödeme Durumu
        self.data_table.setColumnWidth(11, 180) # Çek Tutarı (Orijinal)
        self.data_table.setColumnWidth(12, 120) # Çek USD Eşdeğeri
        self.data_table.setColumnWidth(13, 120) # Çek Vade Tarihi

    def _update_table_from_filter(self, column_name):
        """Update table based on current filter selections for a column"""
        if not hasattr(self, '_column_filters') or self.main_data is None:
            return
            
        # Get currently selected values for this column
        selected_values = []
        for col_index, values in self._column_filters.items():
            col_name = self._get_column_name_by_index(col_index)
            if col_name == column_name:
                selected_values = list(values)
                break
        
        # Apply the filter
        filtered_data = self._apply_column_filter(column_name, selected_values)
        
        # Update the table view
        self._refresh_table_view(filtered_data)

    def _populate_main_data(self):
        """Populate the main_data DataFrame from current_payments"""
        import pandas as pd
        
        logger.info(f"Populating main_data with {len(self.current_payments)} payments")
        
        if not self.current_payments:
            self.main_data = pd.DataFrame()
            logger.info("No payments to populate, creating empty DataFrame")
            return
            
        # Convert payment data to DataFrame
        data = []
        for i, payment in enumerate(self.current_payments):
            # Show original amount and currency
            original_amount_str = f"{payment.original_amount:,.2f} {payment.currency}"
            
            # Show USD equivalent
            usd_amount_str = f"${payment.usd_amount:,.2f}" if payment.usd_amount > 0 else "N/A"
            
            # Show conversion rate if available
            conversion_rate_str = f"{payment.conversion_rate:.4f}" if payment.conversion_rate > 0 else "N/A"
            
            # Show check amount (original currency)
            check_amount_str = ""
            if payment.is_check_payment and payment.original_cek_tutari > 0:
                check_amount_str = f"{payment.original_cek_tutari:,.2f} {payment.currency}"
            
            # Show check USD equivalent
            check_usd_str = f"${payment.cek_usd_amount:,.2f}" if payment.cek_usd_amount > 0 else ""
            
            row_data = {
                'SIRA NO': i + 1,
                'Müşteri Adı Soyadı': payment.customer_name,
                'Tarih': payment.date.strftime("%d.%m.%Y") if payment.date else "",
                'Proje Adı': payment.project_name,
                'Hesap Adı': payment.account_name,
                'Ödenen Tutar (Orijinal)': original_amount_str,
                'Ödenen Döviz': payment.currency,
                'USD Eşdeğeri': usd_amount_str,
                'Döviz Kuru': conversion_rate_str,
                'Tahsilat Şekli': payment.tahsilat_sekli,
                'Ödeme Durumu': payment.payment_status,
                'Çek Tutarı (Orijinal)': check_amount_str,
                'Çek USD Eşdeğeri': check_usd_str,
                'Çek Vade Tarihi': payment.cek_vade_tarihi.strftime("%d.%m.%Y") if payment.cek_vade_tarihi else ""
            }
            data.append(row_data)
        
        self.main_data = pd.DataFrame(data)
        logger.info(f"Created main_data DataFrame with shape: {self.main_data.shape}")

    def _get_column_name_by_index(self, column_index):
        """Get column name by index for DataFrame filtering"""
        if self.main_data is None or self.main_data.empty:
            return None
            
        columns = self.main_data.columns.tolist()
        if 0 <= column_index < len(columns):
            return columns[column_index]
        return None


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
