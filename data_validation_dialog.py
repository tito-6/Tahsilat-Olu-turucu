"""
Professional data validation dialog for Tahsilat application
Shows detailed validation results with better UX
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTextEdit, QScrollArea, QTabWidget, QTableWidget, 
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QGroupBox, QProgressBar, QWidget
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QTextCursor
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataValidationDialog(QDialog):
    """Professional dialog for showing data validation results"""
    
    def __init__(self, parent=None, valid_payments=None, warnings=None, errors=None):
        super().__init__(parent)
        self.valid_payments = valid_payments or []
        self.warnings = warnings or []
        self.errors = errors or []
        
        self.setWindowTitle("Veri Doğrulama Sonuçları")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.setMaximumSize(1200, 800)
        
        self.init_ui()
        self.populate_data()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Summary info
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background-color: #ecf0f1;
                border-radius: 5px;
            }
        """)
        header_layout.addWidget(self.summary_label)
        
        layout.addLayout(header_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Valid data tab
        self.create_valid_data_tab()
        
        # Warnings tab
        self.create_warnings_tab()
        
        # Errors tab
        self.create_errors_tab()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.export_btn = QPushButton("Geçerli Verileri Dışa Aktar")
        self.export_btn.clicked.connect(self.export_valid_data)
        button_layout.addWidget(self.export_btn)
        
        self.close_btn = QPushButton("Kapat")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def create_valid_data_tab(self):
        """Create tab for valid data"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Valid data table
        self.valid_table = QTableWidget()
        self.valid_table.setAlternatingRowColors(True)
        self.valid_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.valid_table.horizontalHeader().setStretchLastSection(True)
        self.valid_table.setSortingEnabled(True)
        
        layout.addWidget(self.valid_table)
        
        self.tab_widget.addTab(tab, f"Geçerli Veriler ({len(self.valid_payments)})")
    
    def create_warnings_tab(self):
        """Create tab for warnings"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Warnings text area
        self.warnings_text = QTextEdit()
        self.warnings_text.setReadOnly(True)
        self.warnings_text.setStyleSheet("""
            QTextEdit {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
        """)
        
        layout.addWidget(self.warnings_text)
        
        # Copy button
        copy_btn = QPushButton("Uyarıları Kopyala")
        copy_btn.clicked.connect(self.copy_warnings)
        layout.addWidget(copy_btn)
        
        self.tab_widget.addTab(tab, f"Uyarılar ({len(self.warnings)})")
    
    def create_errors_tab(self):
        """Create tab for errors"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Errors text area
        self.errors_text = QTextEdit()
        self.errors_text.setReadOnly(True)
        self.errors_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
        """)
        
        layout.addWidget(self.errors_text)
        
        # Copy button
        copy_btn = QPushButton("Hataları Kopyala")
        copy_btn.clicked.connect(self.copy_errors)
        layout.addWidget(copy_btn)
        
        self.tab_widget.addTab(tab, f"Hatalar ({len(self.errors)})")
    
    def populate_data(self):
        """Populate the dialog with data"""
        # Update summary
        total = len(self.valid_payments) + len(self.warnings) + len(self.errors)
        summary_text = f"""
        📊 Toplam Kayıt: {total} | 
        ✅ Geçerli: {len(self.valid_payments)} | 
        ⚠️ Uyarı: {len(self.warnings)} | 
        ❌ Hata: {len(self.errors)}
        """
        self.summary_label.setText(summary_text)
        
        # Populate valid data table
        if self.valid_payments:
            self.populate_valid_table()
        
        # Populate warnings
        if self.warnings:
            self.warnings_text.setPlainText("\n".join(self.warnings))
        
        # Populate errors
        if self.errors:
            self.errors_text.setPlainText("\n".join(self.errors))
    
    def populate_valid_table(self):
        """Populate the valid data table"""
        if not self.valid_payments:
            return
        
        # Get all unique keys from payment data
        all_keys = set()
        for payment in self.valid_payments:
            all_keys.update(payment.to_dict().keys())
        
        columns = sorted(list(all_keys))
        self.valid_table.setColumnCount(len(columns))
        self.valid_table.setHorizontalHeaderLabels(columns)
        self.valid_table.setRowCount(len(self.valid_payments))
        
        # Populate table
        for row, payment in enumerate(self.valid_payments):
            payment_dict = payment.to_dict()
            for col, key in enumerate(columns):
                value = payment_dict.get(key, "")
                if isinstance(value, datetime):
                    value = value.strftime("%d.%m.%Y")
                elif isinstance(value, float):
                    value = f"{value:,.2f}"
                else:
                    value = str(value)
                
                item = QTableWidgetItem(value)
                self.valid_table.setItem(row, col, item)
    
    def copy_warnings(self):
        """Copy warnings to clipboard"""
        from PySide6.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        clipboard.setText("\n".join(self.warnings))
        QMessageBox.information(self, "Kopyalandı", "Uyarılar panoya kopyalandı")
    
    def copy_errors(self):
        """Copy errors to clipboard"""
        from PySide6.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        clipboard.setText("\n".join(self.errors))
        QMessageBox.information(self, "Kopyalandı", "Hatalar panoya kopyalandı")
    
    def export_valid_data(self):
        """Export valid data to file"""
        if not self.valid_payments:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak geçerli veri yok")
            return
        
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Geçerli Verileri Kaydet", "gecerli_veriler.json",
            "JSON Files (*.json);;CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                from storage import PaymentStorage
                storage = PaymentStorage("temp_export")
                storage.add_payments(self.valid_payments)
                storage.export_data(file_path, file_path.split('.')[-1])
                QMessageBox.information(self, "Başarılı", f"Veriler kaydedildi: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dışa aktarma hatası: {e}")

def show_validation_dialog(parent, valid_payments, warnings, errors=None):
    """Show validation dialog with data"""
    dialog = DataValidationDialog(parent, valid_payments, warnings, errors)
    return dialog.exec()
