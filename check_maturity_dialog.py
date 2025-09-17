he tahe data t"""
Dialog for handling check maturity dates
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QPushButton, QMessageBox, QDateEdit,
    QHeaderView, QAbstractItemView, QSplitter, QTextEdit,
    QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)

class CheckMaturityDialog(QDialog):
    """Dialog for entering check maturity dates"""
    
    def __init__(self, check_payments: List, parent=None):
        super().__init__(parent)
        self.check_payments = check_payments
        self.maturity_dates = {}  # Store user-entered dates
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Çek Vade Tarihleri")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Çek Vade Tarihleri Eksik")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Explanation
        explanation = QLabel(
            "Aşağıdaki çek ödemeleri için vade tarihi bulunamadı. "
            "Lütfen her çek için vade tarihini girin. Varsayılan olarak "
            "ödeme tarihinden 6 ay sonrası önerilmiştir."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color: #666; margin: 10px 0;")
        layout.addWidget(explanation)
        
        # Create splitter for table and details
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left side - table
        table_widget = self.create_table_widget()
        splitter.addWidget(table_widget)
        
        # Right side - details and actions
        details_widget = self.create_details_widget()
        splitter.addWidget(details_widget)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 2)  # Table gets more space
        splitter.setStretchFactor(1, 1)  # Details gets less space
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.auto_fill_btn = QPushButton("Tümünü Otomatik Doldur (6 Ay)")
        self.auto_fill_btn.clicked.connect(self.auto_fill_all)
        button_layout.addWidget(self.auto_fill_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("İptal")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("Tamam")
        self.ok_btn.clicked.connect(self.accept_dates)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
        
        # Apply styles
        self.apply_styles()
        
    def create_table_widget(self) -> QGroupBox:
        """Create the table widget for check payments"""
        group = QGroupBox("Çek Ödemeleri")
        layout = QVBoxLayout(group)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Müşteri", "Proje", "Ödeme Tarihi", "Çek Tutarı", 
            "Önerilen Vade", "Vade Tarihi"
        ])
        
        # Configure table
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        # Populate table
        self.populate_table()
        
        layout.addWidget(self.table)
        return group
        
    def create_details_widget(self) -> QGroupBox:
        """Create the details and actions widget"""
        group = QGroupBox("Detaylar ve İşlemler")
        layout = QVBoxLayout(group)
        
        # Statistics
        stats_group = QGroupBox("İstatistikler")
        stats_layout = QFormLayout(stats_group)
        
        total_checks = len(self.check_payments)
        total_amount = sum(p.get('cek_tutari', p.get('amount', 0)) for p in self.check_payments)
        
        stats_layout.addRow("Toplam Çek Sayısı:", QLabel(str(total_checks)))
        stats_layout.addRow("Toplam Tutar:", QLabel(f"₺{total_amount:,.2f}"))
        
        layout.addWidget(stats_group)
        
        # Instructions
        instructions = QTextEdit()
        instructions.setReadOnly(True)
        instructions.setMaximumHeight(150)
        instructions.setHtml("""
        <h4>Kullanım Talimatları:</h4>
        <ul>
        <li><b>Vade Tarihi:</b> Her satırdaki tarih alanına tıklayarak vade tarihini seçin</li>
        <li><b>Otomatik Doldur:</b> Tüm çekler için otomatik olarak 6 ay sonrasını ayarlar</li>
        <li><b>Önerilen Tarih:</b> Sistem önerisi olarak ödeme tarihinden 6 ay sonrası gösterilir</li>
        <li><b>Önemli:</b> Vade tarihi, çekin USD karşılığını hesaplamak için kullanılır</li>
        </ul>
        """)
        
        layout.addWidget(instructions)
        
        return group
        
    def populate_table(self):
        """Populate the table with check payment data"""
        self.table.setRowCount(len(self.check_payments))
        
        for row, payment in enumerate(self.check_payments):
            # Customer name
            customer_item = QTableWidgetItem(payment.get('customer_name', ''))
            customer_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 0, customer_item)
            
            # Project
            project_item = QTableWidgetItem(payment.get('project_name', ''))
            project_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 1, project_item)
            
            # Payment date
            payment_date = payment.get('date', datetime.now())
            if isinstance(payment_date, str):
                payment_date = datetime.fromisoformat(payment_date)
            
            date_item = QTableWidgetItem(payment_date.strftime('%d.%m.%Y'))
            date_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 2, date_item)
            
            # Check amount
            check_amount = payment.get('cek_tutari', payment.get('amount', 0))
            amount_item = QTableWidgetItem(f"₺{check_amount:,.2f}")
            amount_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 3, amount_item)
            
            # Suggested maturity date (6 months later)
            suggested_date = payment_date + timedelta(days=180)
            suggested_item = QTableWidgetItem(suggested_date.strftime('%d.%m.%Y'))
            suggested_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 4, suggested_item)
            
            # Maturity date input
            date_edit = QDateEdit()
            date_edit.setDate(QDate(suggested_date))
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat('dd.MM.yyyy')
            
            # Store reference to payment
            date_edit.setProperty('payment_index', row)
            date_edit.dateChanged.connect(self.on_date_changed)
            
            self.table.setCellWidget(row, 5, date_edit)
            
            # Initialize with suggested date
            self.maturity_dates[row] = suggested_date
            
    def on_date_changed(self, date: QDate):
        """Handle date change in date edit"""
        sender = self.sender()
        if sender:
            payment_index = sender.property('payment_index')
            python_date = date.toPython()
            self.maturity_dates[payment_index] = datetime.combine(python_date, datetime.min.time())
            
    def auto_fill_all(self):
        """Auto-fill all maturity dates with 6 months after payment date"""
        for row in range(self.table.rowCount()):
            payment = self.check_payments[row]
            payment_date = payment.get('date', datetime.now())
            if isinstance(payment_date, str):
                payment_date = datetime.fromisoformat(payment_date)
            
            suggested_date = payment_date + timedelta(days=180)
            
            # Update the date edit widget
            date_edit = self.table.cellWidget(row, 5)
            if date_edit:
                date_edit.setDate(QDate(suggested_date))
            
            self.maturity_dates[row] = suggested_date
            
        QMessageBox.information(self, "Başarılı", 
                               "Tüm çek vade tarihleri otomatik olarak dolduruldu (6 ay sonrası).")
        
    def accept_dates(self):
        """Accept the entered dates and close dialog"""
        # Validate all dates are entered
        missing_dates = []
        for row in range(len(self.check_payments)):
            if row not in self.maturity_dates:
                customer = self.check_payments[row].get('customer_name', f'Satır {row+1}')
                missing_dates.append(customer)
                
        if missing_dates:
            QMessageBox.warning(self, "Eksik Tarih", 
                               f"Aşağıdaki çekler için vade tarihi girilmedi:\n\n" +
                               "\n".join(missing_dates[:5]) +
                               ("\n..." if len(missing_dates) > 5 else ""))
            return
            
        # Validate dates are reasonable (not in the past, not too far future)
        today = datetime.now()
        invalid_dates = []
        
        for row, maturity_date in self.maturity_dates.items():
            customer = self.check_payments[row].get('customer_name', f'Satır {row+1}')
            payment_date = self.check_payments[row].get('date', today)
            if isinstance(payment_date, str):
                payment_date = datetime.fromisoformat(payment_date)
                
            if maturity_date < payment_date:
                invalid_dates.append(f"{customer}: Vade tarihi ödeme tarihinden önce olamaz")
            elif (maturity_date - payment_date).days > 730:  # More than 2 years
                invalid_dates.append(f"{customer}: Vade tarihi çok uzak (2 yıldan fazla)")
                
        if invalid_dates:
            QMessageBox.warning(self, "Geçersiz Tarih", 
                               "Aşağıdaki tarihlerde sorun var:\n\n" +
                               "\n".join(invalid_dates[:3]) +
                               ("\n..." if len(invalid_dates) > 3 else ""))
            return
            
        self.accept()
        
    def get_maturity_dates(self) -> Dict[int, datetime]:
        """Get the entered maturity dates"""
        return self.maturity_dates
        
    def apply_styles(self):
        """Apply custom styles to the dialog"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #f8f9fa;
            }
            
            QTableWidget {
                gridline-color: #dee2e6;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #007bff;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            
            QHeaderView::section {
                background-color: #e9ecef;
                padding: 8px;
                border: 1px solid #dee2e6;
                font-weight: bold;
                color: #495057;
            }
            
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                min-width: 100px;
            }
            
            QPushButton:hover {
                background-color: #0056b3;
            }
            
            QPushButton:pressed {
                background-color: #004085;
            }
            
            QPushButton#cancel_btn {
                background-color: #6c757d;
            }
            
            QPushButton#cancel_btn:hover {
                background-color: #545b62;
            }
            
            QDateEdit {
                padding: 6px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
            }
            
            QDateEdit:focus {
                border-color: #007bff;
                outline: none;
            }
            
            QTextEdit {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
                padding: 10px;
            }
        """)


def show_check_maturity_dialog(check_payments: List, parent=None) -> Optional[Dict[int, datetime]]:
    """Show the check maturity dialog and return entered dates"""
    dialog = CheckMaturityDialog(check_payments, parent)
    
    if dialog.exec() == QDialog.Accepted:
        return dialog.get_maturity_dates()
    
    return None
