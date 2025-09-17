"""
Duplicate detection dialog for handling payment duplicates
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTableWidget, QTableWidgetItem, QCheckBox, QTextEdit,
    QTabWidget, QWidget, QScrollArea, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from typing import List, Dict
from datetime import datetime

class DuplicateDetectionDialog(QDialog):
    """Dialog for handling duplicate payment detection"""
    
    def __init__(self, duplicates: List[Dict], parent=None):
        super().__init__(parent)
        self.duplicates = duplicates
        self.selected_duplicates = []
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Tekrarlanan Ödemeler Tespit Edildi")
        self.setModal(True)
        self.resize(1000, 600)
        
        layout = QVBoxLayout(self)
        
        # Title and description
        title_label = QLabel("⚠️ Tekrarlanan Ödemeler Bulundu")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        desc_label = QLabel(
            f"Sisteme aktarmaya çalıştığınız {len(self.duplicates)} ödeme zaten mevcut olabilir.\n"
            "Aşağıdaki listeden hangi ödemelerin sisteme eklenmesini istediğinizi seçin."
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        
        # Create tab widget for better organization
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # Duplicates tab
        duplicates_tab = QWidget()
        duplicates_layout = QVBoxLayout(duplicates_tab)
        
        # Select all/none buttons
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Tümünü Seç")
        select_all_btn.clicked.connect(self.select_all)
        select_none_btn = QPushButton("Hiçbirini Seçme")
        select_none_btn.clicked.connect(self.select_none)
        
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(select_none_btn)
        button_layout.addStretch()
        duplicates_layout.addLayout(button_layout)
        
        # Duplicates table
        self.duplicates_table = QTableWidget()
        self.setup_duplicates_table()
        duplicates_layout.addWidget(self.duplicates_table)
        
        tab_widget.addTab(duplicates_tab, f"Tekrarlananlar ({len(self.duplicates)})")
        
        # Details tab
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        details_content = self.generate_details_text()
        details_text.setPlainText(details_content)
        details_layout.addWidget(details_text)
        
        tab_widget.addTab(details_tab, "Detaylar")
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        import_selected_btn = QPushButton("Seçilenleri İçe Aktar")
        import_selected_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        import_selected_btn.clicked.connect(self.import_selected)
        
        import_all_btn = QPushButton("Tümünü İçe Aktar")
        import_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #212529;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        import_all_btn.clicked.connect(self.import_all)
        
        cancel_btn = QPushButton("İptal")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        action_layout.addWidget(import_selected_btn)
        action_layout.addWidget(import_all_btn)
        action_layout.addStretch()
        action_layout.addWidget(cancel_btn)
        
        layout.addLayout(action_layout)
    
    def setup_duplicates_table(self):
        """Setup the duplicates table"""
        headers = [
            "Seç", "Müşteri", "Tarih", "Tutar", "Döviz", 
            "Proje", "Mevcut Kayıt", "Sebep"
        ]
        
        self.duplicates_table.setColumnCount(len(headers))
        self.duplicates_table.setHorizontalHeaderLabels(headers)
        self.duplicates_table.setRowCount(len(self.duplicates))
        
        for row, duplicate in enumerate(self.duplicates):
            new_payment = duplicate['new_payment']
            existing_payment = duplicate['existing_payment']
            reason = duplicate['reason']
            
            # Checkbox for selection
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            self.duplicates_table.setCellWidget(row, 0, checkbox)
            
            # New payment details
            self.duplicates_table.setItem(row, 1, QTableWidgetItem(new_payment.customer_name))
            self.duplicates_table.setItem(row, 2, QTableWidgetItem(
                new_payment.date.strftime("%d.%m.%Y") if new_payment.date else "N/A"
            ))
            self.duplicates_table.setItem(row, 3, QTableWidgetItem(f"{new_payment.amount:,.2f}"))
            self.duplicates_table.setItem(row, 4, QTableWidgetItem(new_payment.currency))
            self.duplicates_table.setItem(row, 5, QTableWidgetItem(new_payment.project_name))
            
            # Existing payment info
            existing_info = f"{existing_payment.customer_name} - {existing_payment.date.strftime('%d.%m.%Y') if existing_payment.date else 'N/A'} - {existing_payment.amount:,.2f} {existing_payment.currency}"
            existing_item = QTableWidgetItem(existing_info)
            existing_item.setBackground(QColor(255, 243, 205))  # Light yellow background
            self.duplicates_table.setItem(row, 6, existing_item)
            
            # Reason
            reason_item = QTableWidgetItem(reason)
            reason_item.setToolTip(reason)
            self.duplicates_table.setItem(row, 7, reason_item)
        
        # Set column widths
        self.duplicates_table.setColumnWidth(0, 50)   # Checkbox
        self.duplicates_table.setColumnWidth(1, 150)  # Customer
        self.duplicates_table.setColumnWidth(2, 100)  # Date
        self.duplicates_table.setColumnWidth(3, 100)  # Amount
        self.duplicates_table.setColumnWidth(4, 60)   # Currency
        self.duplicates_table.setColumnWidth(5, 80)   # Project
        self.duplicates_table.setColumnWidth(6, 200)  # Existing
        self.duplicates_table.setColumnWidth(7, 250)  # Reason
        
        # Enable alternating row colors
        self.duplicates_table.setAlternatingRowColors(True)
    
    def generate_details_text(self) -> str:
        """Generate detailed text about duplicates"""
        details = "TEKRARLANAN ÖDEMELER DETAY RAPORU\n"
        details += "=" * 50 + "\n\n"
        
        for i, duplicate in enumerate(self.duplicates, 1):
            new_payment = duplicate['new_payment']
            existing_payment = duplicate['existing_payment']
            reason = duplicate['reason']
            
            details += f"{i}. TEKRARLANAN ÖDEME:\n"
            details += f"   Yeni Kayıt:\n"
            details += f"     • Müşteri: {new_payment.customer_name}\n"
            details += f"     • Tarih: {new_payment.date.strftime('%d.%m.%Y %H:%M') if new_payment.date else 'N/A'}\n"
            details += f"     • Tutar: {new_payment.amount:,.2f} {new_payment.currency}\n"
            details += f"     • Proje: {new_payment.project_name}\n"
            details += f"     • Hesap: {new_payment.account_name}\n"
            details += f"\n"
            details += f"   Mevcut Kayıt:\n"
            details += f"     • Müşteri: {existing_payment.customer_name}\n"
            details += f"     • Tarih: {existing_payment.date.strftime('%d.%m.%Y %H:%M') if existing_payment.date else 'N/A'}\n"
            details += f"     • Tutar: {existing_payment.amount:,.2f} {existing_payment.currency}\n"
            details += f"     • Proje: {existing_payment.project_name}\n"
            details += f"     • Hesap: {existing_payment.account_name}\n"
            details += f"\n"
            details += f"   Sebep: {reason}\n"
            details += f"\n" + "-" * 40 + "\n\n"
        
        return details
    
    def select_all(self):
        """Select all duplicates"""
        for row in range(self.duplicates_table.rowCount()):
            checkbox = self.duplicates_table.cellWidget(row, 0)
            checkbox.setChecked(True)
    
    def select_none(self):
        """Deselect all duplicates"""
        for row in range(self.duplicates_table.rowCount()):
            checkbox = self.duplicates_table.cellWidget(row, 0)
            checkbox.setChecked(False)
    
    def get_selected_duplicates(self) -> List[Dict]:
        """Get the selected duplicates"""
        selected = []
        for row in range(self.duplicates_table.rowCount()):
            checkbox = self.duplicates_table.cellWidget(row, 0)
            if checkbox.isChecked():
                selected.append(self.duplicates[row])
        return selected
    
    def import_selected(self):
        """Import only selected duplicates"""
        selected = self.get_selected_duplicates()
        if not selected:
            QMessageBox.warning(self, "Uyarı", "Lütfen içe aktarılacak ödemeleri seçin.")
            return
        
        reply = QMessageBox.question(
            self, "Onay", 
            f"Seçilen {len(selected)} ödeme sisteme eklenecek.\n"
            "Bu işlem geri alınamaz. Devam etmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.selected_duplicates = selected
            self.accept()
    
    def import_all(self):
        """Import all duplicates"""
        reply = QMessageBox.question(
            self, "Onay", 
            f"Tüm {len(self.duplicates)} ödeme sisteme eklenecek.\n"
            "Bu ödemeler zaten sistemde mevcut olabilir.\n"
            "Bu işlem geri alınamaz. Devam etmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.selected_duplicates = self.duplicates
            self.accept()

def show_duplicate_detection_dialog(duplicates: List[Dict], parent=None) -> List[Dict]:
    """Show duplicate detection dialog and return selected duplicates"""
    dialog = DuplicateDetectionDialog(duplicates, parent)
    if dialog.exec() == QDialog.Accepted:
        return dialog.selected_duplicates
    return []
