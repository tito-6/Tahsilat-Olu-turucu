"""
Advanced filter dialog for payment data with comprehensive Excel-like functionality
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTableWidget, QTableWidgetItem, QCheckBox, QTextEdit,
    QTabWidget, QWidget, QScrollArea, QGroupBox, QMessageBox,
    QLineEdit, QComboBox, QDateEdit, QListWidget, QListWidgetItem,
    QSplitter, QFrame, QSpinBox, QDoubleSpinBox, QRadioButton,
    QButtonGroup, QFormLayout, QGridLayout
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont, QColor
import qtawesome as qta
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import re

class AdvancedFilterDialog(QDialog):
    """Advanced filter dialog with comprehensive Excel-like filtering capabilities"""
    
    filter_applied = Signal(list)  # Signal emitted when filters are applied
    
    def __init__(self, payments: List, parent=None):
        super().__init__(parent)
        self.original_payments = payments
        self.filtered_payments = payments.copy()
        self.filters = {}
        self.init_ui()
        self.setup_initial_filters()

    def init_ui(self):
        """Initialize the comprehensive user interface"""
        self.setWindowTitle("Gelişmiş Filtre - Excel Benzeri Filtreleme")
        self.setModal(True)
        self.resize(1200, 800)
        
        # Apply professional styling
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e9ecef;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #007bff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin: 10px 0px;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #495057;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border: 1px solid #ced4da;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e3f2fd, stop:1 #bbdefb);
                border-color: #2196f3;
            }
            QPushButton:pressed {
                background: #1976d2;
                color: white;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Title and description
        title_layout = QHBoxLayout()
        title_label = QLabel("🔍 Gelişmiş Filtre")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Quick stats
        self.stats_label = QLabel(f"Toplam: {len(self.original_payments)} kayıt")
        self.stats_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        title_layout.addWidget(self.stats_label)
        layout.addLayout(title_layout)
        
        # Main content splitter
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # Left panel - Filter controls
        left_panel = self.create_filter_controls_panel()
        main_splitter.addWidget(left_panel)
        
        # Right panel - Preview and results
        right_panel = self.create_preview_panel()
        main_splitter.addWidget(right_panel)
        
        # Set splitter proportions
        main_splitter.setStretchFactor(0, 1)  # Filter controls
        main_splitter.setStretchFactor(1, 2)  # Preview panel
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Clear all filters
        clear_btn = QPushButton("Tüm Filtreleri Temizle")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        clear_btn.clicked.connect(self.clear_all_filters)
        button_layout.addWidget(clear_btn)
        
        # Apply filters
        apply_btn = QPushButton("Filtreleri Uygula")
        apply_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                font-weight: 600;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        apply_btn.clicked.connect(self.apply_filters)
        button_layout.addWidget(apply_btn)
        
        # Cancel
        cancel_btn = QPushButton("İptal")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #c82333;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)

    def create_filter_controls_panel(self):
        """Create the comprehensive filter controls panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create tabbed interface for different filter types
        tab_widget = QTabWidget()
        
        # Column filters tab
        column_tab = self.create_column_filters_tab()
        tab_widget.addTab(column_tab, "Kolon Filtreleri")
        
        # Text filters tab
        text_tab = self.create_text_filters_tab()
        tab_widget.addTab(text_tab, "Metin Filtreleri")
        
        # Number filters tab
        number_tab = self.create_number_filters_tab()
        tab_widget.addTab(number_tab, "Sayı Filtreleri")
        
        # Date filters tab
        date_tab = self.create_date_filters_tab()
        tab_widget.addTab(date_tab, "Tarih Filtreleri")
        
        # Custom filters tab
        custom_tab = self.create_custom_filters_tab()
        tab_widget.addTab(custom_tab, "Özel Filtreler")
        
        layout.addWidget(tab_widget)
        return panel

    def create_column_filters_tab(self):
        """Create column-based filters (Excel-like dropdown filters)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Instructions
        instructions = QLabel("Her kolon için benzersiz değerleri seçin:")
        instructions.setStyleSheet("color: #6c757d; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Scroll area for column filters
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Define columns with their display names
        columns = [
            ('customer_name', 'Müşteri Adı'),
            ('project_name', 'Proje Adı'),
            ('amount', 'Tutar'),
            ('currency', 'Para Birimi'),
            ('date', 'Tarih'),
            ('tahsilat_sekli', 'Tahsilat Şekli'),
            ('account_name', 'Hesap Adı'),
            ('payment_channel', 'Ödeme Kanalı')
        ]
        
        for field, display_name in columns:
            group_box = self.create_column_filter_group(display_name, field)
            scroll_layout.addWidget(group_box)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        return tab

    def create_column_filter_group(self, display_name: str, field: str):
        """Create a collapsible group for column filtering"""
        group_box = QGroupBox(display_name)
        group_layout = QVBoxLayout(group_box)
        group_layout.setContentsMargins(8, 8, 8, 8)
        
        # Search and select all/none
        search_layout = QHBoxLayout()
        search_edit = QLineEdit()
        search_edit.setPlaceholderText(f"{display_name} ara...")
        search_edit.setMaximumHeight(25)
        search_edit.textChanged.connect(lambda text, field=field: self.filter_column_values(field, text))
        search_layout.addWidget(search_edit)
        
        # Select all/none buttons
        select_all_btn = QPushButton("Tümü")
        select_all_btn.setMaximumWidth(50)
        select_all_btn.setMaximumHeight(25)
        select_all_btn.clicked.connect(lambda: self.select_all_column_values(field))
        search_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("Hiçbiri")
        select_none_btn.setMaximumWidth(60)
        select_none_btn.setMaximumHeight(25)
        select_none_btn.clicked.connect(lambda: self.select_none_column_values(field))
        search_layout.addWidget(select_none_btn)
        
        group_layout.addLayout(search_layout)
        
        # Values list
        values_list = QListWidget()
        values_list.setMaximumHeight(120)
        values_list.setSelectionMode(QListWidget.MultiSelection)
        
        # Get unique values for this field
        unique_values = self.get_unique_values(field)
        for value in sorted(unique_values):
            item = QListWidgetItem(str(value) if value is not None else "Boş")
            item.setData(Qt.UserRole, value)
            values_list.addItem(item)
        
        # Store reference to values list
        setattr(self, f"{field}_values_list", values_list)
        group_layout.addWidget(values_list)
        
        return group_box

    def create_text_filters_tab(self):
        """Create text-based filters (contains, starts with, ends with, etc.)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Text filter instructions
        instructions = QLabel("Metin tabanlı filtreleme seçenekleri:")
        instructions.setStyleSheet("color: #6c757d; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Text filter groups
        text_fields = [
            ('customer_name', 'Müşteri Adı'),
            ('project_name', 'Proje Adı'),
            ('tahsilat_sekli', 'Tahsilat Şekli'),
            ('account_name', 'Hesap Adı')
        ]
        
        for field, display_name in text_fields:
            group = self.create_text_filter_group(display_name, field)
            layout.addWidget(group)
        
        layout.addStretch()
        return tab

    def create_text_filter_group(self, display_name: str, field: str):
        """Create text filter group with various text operations"""
        group_box = QGroupBox(display_name)
        group_layout = QFormLayout(group_box)
        
        # Filter type selection
        filter_type_combo = QComboBox()
        filter_type_combo.addItems([
            "İçerir",
            "İle başlar",
            "İle biter",
            "Eşittir",
            "Eşit değildir",
            "Boş",
            "Boş değil"
        ])
        group_layout.addRow("Filtre Türü:", filter_type_combo)
        
        # Value input
        value_edit = QLineEdit()
        value_edit.setPlaceholderText("Değer girin...")
        group_layout.addRow("Değer:", value_edit)
        
        # Case sensitive checkbox
        case_sensitive_cb = QCheckBox("Büyük/küçük harf duyarlı")
        group_layout.addRow("", case_sensitive_cb)
        
        # Store references
        setattr(self, f"{field}_text_type", filter_type_combo)
        setattr(self, f"{field}_text_value", value_edit)
        setattr(self, f"{field}_text_case", case_sensitive_cb)
        
        return group_box

    def create_number_filters_tab(self):
        """Create number-based filters (greater than, less than, between, etc.)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Number filter instructions
        instructions = QLabel("Sayı tabanlı filtreleme seçenekleri:")
        instructions.setStyleSheet("color: #6c757d; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Amount filter group
        amount_group = QGroupBox("Tutar Filtreleri")
        amount_layout = QFormLayout(amount_group)
        
        # Filter type
        amount_type_combo = QComboBox()
        amount_type_combo.addItems([
            "Eşittir",
            "Eşit değildir",
            "Büyüktür",
            "Büyük veya eşittir",
            "Küçüktür",
            "Küçük veya eşittir",
            "Arasında",
            "En büyük 10",
            "En küçük 10",
            "Ortalama üstü",
            "Ortalama altı"
        ])
        amount_layout.addRow("Filtre Türü:", amount_type_combo)
        
        # Value inputs
        value1_layout = QHBoxLayout()
        self.amount_value1 = QDoubleSpinBox()
        self.amount_value1.setRange(0, 999999999)
        self.amount_value1.setDecimals(2)
        value1_layout.addWidget(self.amount_value1)
        
        self.amount_value2 = QDoubleSpinBox()
        self.amount_value2.setRange(0, 999999999)
        self.amount_value2.setDecimals(2)
        value1_layout.addWidget(QLabel("ve"))
        value1_layout.addWidget(self.amount_value2)
        amount_layout.addRow("Değer(ler):", value1_layout)
        
        layout.addWidget(amount_group)
        layout.addStretch()
        return tab

    def create_date_filters_tab(self):
        """Create date-based filters"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Date filter instructions
        instructions = QLabel("Tarih tabanlı filtreleme seçenekleri:")
        instructions.setStyleSheet("color: #6c757d; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Date filter group
        date_group = QGroupBox("Tarih Filtreleri")
        date_layout = QFormLayout(date_group)
        
        # Filter type
        date_type_combo = QComboBox()
        date_type_combo.addItems([
            "Eşittir",
            "Eşit değildir",
            "Öncesi",
            "Sonrası",
            "Arasında",
            "Bugün",
            "Dün",
            "Bu hafta",
            "Geçen hafta",
            "Bu ay",
            "Geçen ay",
            "Bu yıl",
            "Geçen yıl"
        ])
        date_layout.addRow("Filtre Türü:", date_type_combo)
        
        # Date inputs
        date_layout_controls = QHBoxLayout()
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate())
        self.date_from.setCalendarPopup(True)
        date_layout_controls.addWidget(self.date_from)
        
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        date_layout_controls.addWidget(QLabel("ve"))
        date_layout_controls.addWidget(self.date_to)
        date_layout.addRow("Tarih(ler):", date_layout_controls)
        
        layout.addWidget(date_group)
        layout.addStretch()
        return tab

    def create_custom_filters_tab(self):
        """Create custom filters with advanced options"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Custom filter instructions
        instructions = QLabel("Özel filtreleme seçenekleri:")
        instructions.setStyleSheet("color: #6c757d; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Duplicate detection
        duplicate_group = QGroupBox("Tekrar Kontrolü")
        duplicate_layout = QVBoxLayout(duplicate_group)
        
        self.show_duplicates_cb = QCheckBox("Sadece tekrarları göster")
        self.show_uniques_cb = QCheckBox("Sadece benzersizleri göster")
        duplicate_layout.addWidget(self.show_duplicates_cb)
        duplicate_layout.addWidget(self.show_uniques_cb)
        
        layout.addWidget(duplicate_group)
        
        # Top/Bottom filters
        top_bottom_group = QGroupBox("En İyi/En Kötü")
        top_bottom_layout = QFormLayout(top_bottom_group)
        
        self.top_bottom_combo = QComboBox()
        self.top_bottom_combo.addItems(["En yüksek tutarlar", "En düşük tutarlar"])
        top_bottom_layout.addRow("Tür:", self.top_bottom_combo)
        
        self.top_bottom_count = QSpinBox()
        self.top_bottom_count.setRange(1, 100)
        self.top_bottom_count.setValue(10)
        top_bottom_layout.addRow("Adet:", self.top_bottom_count)
        
        layout.addWidget(top_bottom_group)
        
        # Custom SQL-like filters
        sql_group = QGroupBox("Özel Filtre (Gelişmiş)")
        sql_layout = QVBoxLayout(sql_group)
        
        self.custom_filter_edit = QTextEdit()
        self.custom_filter_edit.setPlaceholderText(
            "Özel filtre kriterleri girin...\n"
            "Örnek: customer_name LIKE '%ABC%' AND amount > 1000"
        )
        self.custom_filter_edit.setMaximumHeight(100)
        sql_layout.addWidget(self.custom_filter_edit)
        
        layout.addWidget(sql_group)
        layout.addStretch()
        return tab

    def create_preview_panel(self):
        """Create the preview panel showing filtered results"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Preview header
        header_layout = QHBoxLayout()
        preview_label = QLabel("Filtrelenmiş Veriler")
        preview_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        header_layout.addWidget(preview_label)
        header_layout.addStretch()
        
        # Results count
        self.results_count_label = QLabel(f"Sonuç: {len(self.filtered_payments)} kayıt")
        self.results_count_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        header_layout.addWidget(self.results_count_label)
        layout.addLayout(header_layout)
        
        # Preview table
        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.preview_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                gridline-color: #e9ecef;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #e9ecef;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: 1px solid #dee2e6;
                font-weight: 600;
                color: #495057;
            }
        """)
        
        # Set up table columns
        columns = ['Müşteri', 'Proje', 'Tutar', 'Tarih', 'Tahsilat Şekli', 'Hesap']
        self.preview_table.setColumnCount(len(columns))
        self.preview_table.setHorizontalHeaderLabels(columns)
        
        # Populate with all data initially
        self.update_preview_table()
        layout.addWidget(self.preview_table)
        
        return panel

    def get_unique_values(self, field: str):
        """Get unique values for a field"""
        values = set()
        for payment in self.original_payments:
            value = getattr(payment, field, None)
            if value is not None:
                values.add(value)
        return values

    def filter_column_values(self, field: str, search_text: str):
        """Filter column values based on search text"""
        values_list = getattr(self, f"{field}_values_list", None)
        if not values_list:
            return
        
        for i in range(values_list.count()):
            item = values_list.item(i)
            if item:
                item_text = item.text().lower()
                if search_text.lower() in item_text:
                    item.setHidden(False)
                else:
                    item.setHidden(True)

    def select_all_column_values(self, field: str):
        """Select all values for a column"""
        values_list = getattr(self, f"{field}_values_list", None)
        if values_list:
            values_list.selectAll()

    def select_none_column_values(self, field: str):
        """Deselect all values for a column"""
        values_list = getattr(self, f"{field}_values_list", None)
        if values_list:
            values_list.clearSelection()

    def clear_all_filters(self):
        """Clear all applied filters"""
        self.filters = {}
        self.filtered_payments = self.original_payments.copy()
        self.update_preview_table()
        self.update_stats()

    def apply_filters(self):
        """Apply all configured filters"""
        self.filtered_payments = self.original_payments.copy()
        
        # Apply column filters
        self.apply_column_filters()
        
        # Apply text filters
        self.apply_text_filters()
        
        # Apply number filters
        self.apply_number_filters()
        
        # Apply date filters
        self.apply_date_filters()
        
        # Apply custom filters
        self.apply_custom_filters()
        
        self.update_preview_table()
        self.update_stats()

    def apply_column_filters(self):
        """Apply column-based filters"""
        column_fields = [
            'customer_name', 'project_name', 'amount', 'currency',
            'date', 'tahsilat_sekli', 'account_name', 'payment_channel'
        ]
        
        for field in column_fields:
            values_list = getattr(self, f"{field}_values_list", None)
            if values_list:
                selected_values = []
                for i in range(values_list.count()):
                    item = values_list.item(i)
                    if item and item.isSelected():
                        value = item.data(Qt.UserRole)
                        selected_values.append(value)
                
                if selected_values:
                    self.filtered_payments = [
                        p for p in self.filtered_payments
                        if getattr(p, field, None) in selected_values
                    ]

    def apply_text_filters(self):
        """Apply text-based filters"""
        text_fields = ['customer_name', 'project_name', 'tahsilat_sekli', 'account_name']
        
        for field in text_fields:
            filter_type = getattr(self, f"{field}_text_type", None)
            value_edit = getattr(self, f"{field}_text_value", None)
            case_sensitive = getattr(self, f"{field}_text_case", None)
            
            if filter_type and value_edit and case_sensitive:
                filter_type_text = filter_type.currentText()
                search_value = value_edit.text()
                case_sensitive_flag = case_sensitive.isChecked()
                
                if search_value:
                    self.apply_text_filter(field, filter_type_text, search_value, case_sensitive_flag)

    def apply_text_filter(self, field: str, filter_type: str, value: str, case_sensitive: bool):
        """Apply a single text filter"""
        if not case_sensitive:
            value = value.lower()
        
        if filter_type == "İçerir":
            self.filtered_payments = [
                p for p in self.filtered_payments
                if self.text_contains(getattr(p, field, ""), value, case_sensitive)
            ]
        elif filter_type == "İle başlar":
            self.filtered_payments = [
                p for p in self.filtered_payments
                if self.text_starts_with(getattr(p, field, ""), value, case_sensitive)
            ]
        elif filter_type == "İle biter":
            self.filtered_payments = [
                p for p in self.filtered_payments
                if self.text_ends_with(getattr(p, field, ""), value, case_sensitive)
            ]
        elif filter_type == "Eşittir":
            self.filtered_payments = [
                p for p in self.filtered_payments
                if self.text_equals(getattr(p, field, ""), value, case_sensitive)
            ]
        elif filter_type == "Eşit değildir":
            self.filtered_payments = [
                p for p in self.filtered_payments
                if not self.text_equals(getattr(p, field, ""), value, case_sensitive)
            ]
        elif filter_type == "Boş":
            self.filtered_payments = [
                p for p in self.filtered_payments
                if not getattr(p, field, None) or str(getattr(p, field, "")).strip() == ""
            ]
        elif filter_type == "Boş değil":
            self.filtered_payments = [
                p for p in self.filtered_payments
                if getattr(p, field, None) and str(getattr(p, field, "")).strip() != ""
            ]

    def text_contains(self, text: str, value: str, case_sensitive: bool) -> bool:
        """Check if text contains value"""
        if not case_sensitive:
            text = text.lower()
        return value in text

    def text_starts_with(self, text: str, value: str, case_sensitive: bool) -> bool:
        """Check if text starts with value"""
        if not case_sensitive:
            text = text.lower()
        return text.startswith(value)

    def text_ends_with(self, text: str, value: str, case_sensitive: bool) -> bool:
        """Check if text ends with value"""
        if not case_sensitive:
            text = text.lower()
        return text.endswith(value)

    def text_equals(self, text: str, value: str, case_sensitive: bool) -> bool:
        """Check if text equals value"""
        if not case_sensitive:
            text = text.lower()
        return text == value

    def apply_number_filters(self):
        """Apply number-based filters"""
        # Amount filters
        if hasattr(self, 'amount_value1'):
            filter_type = getattr(self, 'amount_type_combo', None)
            if filter_type:
                filter_type_text = filter_type.currentText()
                value1 = self.amount_value1.value()
                value2 = self.amount_value2.value()
                
                if filter_type_text == "Eşittir":
                    self.filtered_payments = [
                        p for p in self.filtered_payments
                        if abs(p.amount - value1) < 0.01
                    ]
                elif filter_type_text == "Büyüktür":
                    self.filtered_payments = [
                        p for p in self.filtered_payments
                        if p.amount > value1
                    ]
                elif filter_type_text == "Küçüktür":
                    self.filtered_payments = [
                        p for p in self.filtered_payments
                        if p.amount < value1
                    ]
                elif filter_type_text == "Arasında":
                    self.filtered_payments = [
                        p for p in self.filtered_payments
                        if value1 <= p.amount <= value2
                    ]

    def apply_date_filters(self):
        """Apply date-based filters"""
        if hasattr(self, 'date_from'):
            filter_type = getattr(self, 'date_type_combo', None)
            if filter_type:
                filter_type_text = filter_type.currentText()
                from_date = self.date_from.date().toPython()
                to_date = self.date_to.date().toPython()
                
                if filter_type_text == "Eşittir":
                    self.filtered_payments = [
                        p for p in self.filtered_payments
                        if p.date and p.date.date() == from_date
                    ]
                elif filter_type_text == "Öncesi":
                    self.filtered_payments = [
                        p for p in self.filtered_payments
                        if p.date and p.date.date() < from_date
                    ]
                elif filter_type_text == "Sonrası":
                    self.filtered_payments = [
                        p for p in self.filtered_payments
                        if p.date and p.date.date() > from_date
                    ]
                elif filter_type_text == "Arasında":
                    self.filtered_payments = [
                        p for p in self.filtered_payments
                        if p.date and from_date <= p.date.date() <= to_date
                    ]

    def apply_custom_filters(self):
        """Apply custom filters"""
        # Duplicate filters
        if hasattr(self, 'show_duplicates_cb') and self.show_duplicates_cb.isChecked():
            self.filter_duplicates()
        
        if hasattr(self, 'show_uniques_cb') and self.show_uniques_cb.isChecked():
            self.filter_uniques()

    def filter_duplicates(self):
        """Filter to show only duplicate records based on EXACT amount AND EXACT date"""
        # Duplicate detection based on EXACT amount AND EXACT date only
        seen = set()
        duplicates = []
        
        for payment in self.filtered_payments:
            # Only use amount and date for duplicate detection
            # Amount must be exactly the same (to the cent)
            # Date must be exactly the same (same day)
            if payment.date:
                key = (payment.amount, payment.date.date())  # Only amount and date
                if key in seen:
                    duplicates.append(payment)
                else:
                    seen.add(key)
        
        self.filtered_payments = duplicates

    def filter_uniques(self):
        """Filter to show only unique records based on EXACT amount AND EXACT date"""
        seen = set()
        uniques = []
        
        for payment in self.filtered_payments:
            # Only use amount and date for uniqueness check
            if payment.date:
                key = (payment.amount, payment.date.date())  # Only amount and date
                if key not in seen:
                    uniques.append(payment)
                    seen.add(key)
        
        self.filtered_payments = uniques

    def update_preview_table(self):
        """Update the preview table with filtered results"""
        if not self.filtered_payments:
            self.preview_table.setRowCount(0)
            return
        
        # Show first 100 records for performance
        display_count = min(100, len(self.filtered_payments))
        self.preview_table.setRowCount(display_count)
        
        for i, payment in enumerate(self.filtered_payments[:display_count]):
            self.preview_table.setItem(i, 0, QTableWidgetItem(payment.customer_name or ""))
            self.preview_table.setItem(i, 1, QTableWidgetItem(payment.project_name or ""))
            self.preview_table.setItem(i, 2, QTableWidgetItem(f"{payment.amount:,.2f} {payment.currency}"))
            self.preview_table.setItem(i, 3, QTableWidgetItem(payment.date.strftime("%d.%m.%Y") if payment.date else ""))
            self.preview_table.setItem(i, 4, QTableWidgetItem(payment.tahsilat_sekli or ""))
            self.preview_table.setItem(i, 5, QTableWidgetItem(payment.account_name or ""))
        
        self.preview_table.resizeColumnsToContents()

    def update_stats(self):
        """Update statistics display"""
        total_count = len(self.original_payments)
        filtered_count = len(self.filtered_payments)
        
        self.stats_label.setText(f"Toplam: {total_count} | Filtrelenmiş: {filtered_count}")
        self.results_count_label.setText(f"Sonuç: {filtered_count} kayıt")

    def setup_initial_filters(self):
        """Setup initial filter state"""
        self.update_preview_table()
        self.update_stats()

    def get_filtered_payments(self):
        """Get the filtered payments"""
        return self.filtered_payments

    def accept(self):
        """Accept the dialog and emit filter applied signal"""
        self.filter_applied.emit(self.filtered_payments)
        super().accept()
