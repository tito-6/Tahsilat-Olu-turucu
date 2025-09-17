"""
Advanced currency rates calendar dialog with beautiful UI
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTableWidget, QTableWidgetItem, QTextEdit, QTabWidget, 
    QWidget, QScrollArea, QGroupBox, QMessageBox, QLineEdit,
    QDateEdit, QCalendarWidget, QSplitter, QFrame, QProgressBar,
    QComboBox, QSpinBox
)
from PySide6.QtCore import Qt, QDate, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap, QPainter
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
import calendar
import requests
from bs4 import BeautifulSoup

class CurrencyFetchWorker(QThread):
    """Worker thread for fetching currency rates"""
    progress = Signal(int)
    status = Signal(str)
    rate_fetched = Signal(str, float)  # date, rate
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, currency_converter, start_date, end_date):
        super().__init__()
        self.currency_converter = currency_converter
        self.start_date = start_date
        self.end_date = end_date
    
    def run(self):
        """Fetch currency rates for date range"""
        try:
            current_date = self.start_date
            total_days = (self.end_date - self.start_date).days + 1
            processed = 0
            
            while current_date <= self.end_date:
                self.status.emit(f"Kur getiriliyor: {current_date.strftime('%d.%m.%Y')}")
                
                try:
                    rate = self.currency_converter.get_usd_rate(current_date)
                    if rate:
                        self.rate_fetched.emit(current_date.strftime('%Y-%m-%d'), rate)
                except Exception as e:
                    self.error.emit(f"Kur alınamadı {current_date.strftime('%d.%m.%Y')}: {str(e)}")
                
                processed += 1
                progress_percent = int((processed / total_days) * 100)
                self.progress.emit(progress_percent)
                
                current_date += timedelta(days=1)
                self.msleep(100)  # Small delay to prevent overwhelming the server
            
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(f"Genel hata: {str(e)}")

class CurrencyCalendarDialog(QDialog):
    """Advanced currency rates calendar with beautiful UI"""
    
    def __init__(self, currency_converter, parent=None):
        super().__init__(parent)
        self.currency_converter = currency_converter
        self.rates_data = {}
        self.init_ui()
        self.load_cached_rates()
        self.setup_calendar_display()
    
    def init_ui(self):
        """Initialize the beautiful user interface"""
        self.setWindowTitle("💰 Döviz Kurları Takvimi - TCMB Resmi Kurları")
        self.setModal(True)
        self.resize(1400, 900)
        
        # Apply beautiful styling
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin: 10px 0px;
                padding-top: 20px;
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
        
        # Title with icon
        title_layout = QHBoxLayout()
        title_label = QLabel("💰 TCMB Döviz Kurları Takvimi")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #1976d2;
                background: white;
                padding: 15px;
                border-radius: 10px;
                border: 2px solid #e3f2fd;
            }
        """)
        title_layout.addWidget(title_label)
        layout.addLayout(title_layout)
        
        # Main content splitter
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # Left panel - Controls
        left_panel = self.create_control_panel()
        main_splitter.addWidget(left_panel)
        
        # Right panel - Calendar and rates
        right_panel = self.create_calendar_panel()
        main_splitter.addWidget(right_panel)
        
        main_splitter.setSizes([400, 1000])
        
        # Status and progress
        status_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Hazır")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #d4edda;
                color: #155724;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #c3e6cb;
            }
        """)
        status_layout.addWidget(self.status_label)
        
        layout.addLayout(status_layout)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Kurları Yenile")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #28a745, stop:1 #218838);
                color: white;
                font-weight: bold;
                padding: 12px 24px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34ce57, stop:1 #28a745);
            }
        """)
        refresh_btn.clicked.connect(self.refresh_rates)
        
        export_btn = QPushButton("📤 Excel'e Aktar")
        export_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #17a2b8, stop:1 #138496);
                color: white;
                font-weight: bold;
                padding: 12px 24px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #20c0d7, stop:1 #17a2b8);
            }
        """)
        export_btn.clicked.connect(self.export_rates)
        
        close_btn = QPushButton("❌ Kapat")
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6c757d, stop:1 #545b62);
                color: white;
                font-weight: bold;
                padding: 12px 24px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7d8a96, stop:1 #6c757d);
            }
        """)
        close_btn.clicked.connect(self.close)
        
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(export_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def create_control_panel(self):
        """Create the left control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Date range selection
        date_group = QGroupBox("📅 Tarih Aralığı Seçimi")
        date_layout = QVBoxLayout(date_group)
        
        # Start date
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Başlangıç:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setCalendarPopup(True)
        self.start_date.setStyleSheet("""
            QDateEdit {
                padding: 8px;
                border: 2px solid #ced4da;
                border-radius: 4px;
                background-color: white;
            }
            QDateEdit:focus {
                border-color: #007bff;
            }
        """)
        start_layout.addWidget(self.start_date)
        date_layout.addLayout(start_layout)
        
        # End date
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("Bitiş:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setStyleSheet(self.start_date.styleSheet())
        end_layout.addWidget(self.end_date)
        date_layout.addLayout(end_layout)
        
        # Quick selection buttons
        quick_layout = QHBoxLayout()
        
        today_btn = QPushButton("Bugün")
        today_btn.clicked.connect(lambda: self.set_date_range(0))
        
        week_btn = QPushButton("Bu Hafta")
        week_btn.clicked.connect(lambda: self.set_date_range(7))
        
        month_btn = QPushButton("Bu Ay")
        month_btn.clicked.connect(lambda: self.set_date_range(30))
        
        quick_layout.addWidget(today_btn)
        quick_layout.addWidget(week_btn)
        quick_layout.addWidget(month_btn)
        
        date_layout.addLayout(quick_layout)
        layout.addWidget(date_group)
        
        # Statistics
        stats_group = QGroupBox("📊 İstatistikler")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_label = QLabel("Yükleniyor...")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #dee2e6;
            }
        """)
        stats_layout.addWidget(self.stats_label)
        
        layout.addWidget(stats_group)
        
        # Rate analysis
        analysis_group = QGroupBox("📈 Kur Analizi")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.analysis_label = QLabel("Analiz bekleniyor...")
        self.analysis_label.setWordWrap(True)
        self.analysis_label.setStyleSheet(self.stats_label.styleSheet())
        analysis_layout.addWidget(self.analysis_label)
        
        layout.addWidget(analysis_group)
        
        layout.addStretch()
        return panel
    
    def create_calendar_panel(self):
        """Create the right calendar panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Tab widget for different views
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ced4da;
                background-color: white;
            }
            QTabBar::tab {
                background: #f8f9fa;
                border: 1px solid #ced4da;
                padding: 10px 20px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
            }
        """)
        
        # Calendar view
        self.create_calendar_view()
        
        # Table view
        self.create_table_view()
        
        # Chart view (placeholder)
        self.create_chart_view()
        
        layout.addWidget(self.tab_widget)
        return panel
    
    def create_calendar_view(self):
        """Create calendar view tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Month navigation
        nav_layout = QHBoxLayout()
        
        self.prev_month_btn = QPushButton("◀ Önceki Ay")
        self.prev_month_btn.clicked.connect(self.prev_month)
        
        self.month_label = QLabel()
        self.month_label.setAlignment(Qt.AlignCenter)
        self.month_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #495057;
                padding: 10px;
            }
        """)
        
        self.next_month_btn = QPushButton("Sonraki Ay ▶")
        self.next_month_btn.clicked.connect(self.next_month)
        
        nav_layout.addWidget(self.prev_month_btn)
        nav_layout.addWidget(self.month_label)
        nav_layout.addWidget(self.next_month_btn)
        
        layout.addLayout(nav_layout)
        
        # Calendar widget
        self.calendar = QCalendarWidget()
        self.calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
            }
            QCalendarWidget QTableView {
                selection-background-color: #007bff;
                selection-color: white;
            }
        """)
        self.calendar.selectionChanged.connect(self.on_date_selected)
        layout.addWidget(self.calendar)
        
        # Selected date info
        self.date_info_label = QLabel("Tarih seçin...")
        self.date_info_label.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                color: #1565c0;
                padding: 15px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.date_info_label)
        
        self.tab_widget.addTab(tab, "📅 Takvim Görünümü")
    
    def create_table_view(self):
        """Create table view tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Table
        self.rates_table = QTableWidget()
        self.rates_table.setColumnCount(4)
        self.rates_table.setHorizontalHeaderLabels([
            "Tarih", "USD/TL Kuru", "Değişim", "Durum"
        ])
        
        # Style the table
        self.rates_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
                gridline-color: #dee2e6;
                selection-background-color: #e3f2fd;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #dee2e6;
            }
            QHeaderView::section {
                background-color: #495057;
                color: white;
                padding: 10px;
                border: 1px solid #343a40;
                font-weight: bold;
            }
        """)
        
        self.rates_table.setAlternatingRowColors(True)
        self.rates_table.setSortingEnabled(True)
        self.rates_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.rates_table)
        
        self.tab_widget.addTab(tab, "📊 Tablo Görünümü")
    
    def create_chart_view(self):
        """Create chart view tab (placeholder)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Placeholder for future chart implementation
        chart_label = QLabel("📈 Grafik Görünümü\n\n(Gelecek sürümde eklenecek)")
        chart_label.setAlignment(Qt.AlignCenter)
        chart_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                color: #6c757d;
                padding: 50px;
                border: 2px dashed #dee2e6;
                border-radius: 10px;
                font-size: 16px;
            }
        """)
        
        layout.addWidget(chart_label)
        self.tab_widget.addTab(tab, "📈 Grafik Görünümü")
    
    def load_cached_rates(self):
        """Load cached currency rates"""
        self.rates_data = self.currency_converter.get_cached_rates()
        self.update_displays()
    
    def setup_calendar_display(self):
        """Setup the calendar display with current month"""
        current_date = QDate.currentDate()
        self.calendar.setSelectedDate(current_date)
        self.update_month_label()
    
    def update_month_label(self):
        """Update month label"""
        selected_date = self.calendar.selectedDate()
        month_names = [
            "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
        ]
        month_name = month_names[selected_date.month() - 1]
        self.month_label.setText(f"{month_name} {selected_date.year()}")
    
    def prev_month(self):
        """Go to previous month"""
        current_date = self.calendar.selectedDate()
        new_date = current_date.addMonths(-1)
        self.calendar.setSelectedDate(new_date)
        self.update_month_label()
    
    def next_month(self):
        """Go to next month"""
        current_date = self.calendar.selectedDate()
        new_date = current_date.addMonths(1)
        self.calendar.setSelectedDate(new_date)
        self.update_month_label()
    
    def on_date_selected(self):
        """Handle date selection"""
        selected_date = self.calendar.selectedDate()
        date_str = selected_date.toString("yyyy-MM-dd")
        
        if date_str in self.rates_data:
            rate = self.rates_data[date_str]
            self.date_info_label.setText(
                f"📅 {selected_date.toString('dd.MM.yyyy')}\n"
                f"💰 USD/TL: {rate:.4f}\n"
                f"✅ Kur mevcut"
            )
            self.date_info_label.setStyleSheet("""
                QLabel {
                    background-color: #d4edda;
                    color: #155724;
                    padding: 15px;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 14px;
                }
            """)
        else:
            self.date_info_label.setText(
                f"📅 {selected_date.toString('dd.MM.yyyy')}\n"
                f"❌ Kur mevcut değil\n"
                f"🔄 Kurları yenileyin"
            )
            self.date_info_label.setStyleSheet("""
                QLabel {
                    background-color: #f8d7da;
                    color: #721c24;
                    padding: 15px;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 14px;
                }
            """)
    
    def set_date_range(self, days_back):
        """Set date range"""
        end_date = QDate.currentDate()
        start_date = end_date.addDays(-days_back)
        self.start_date.setDate(start_date)
        self.end_date.setDate(end_date)
    
    def update_displays(self):
        """Update all displays with current data"""
        self.update_statistics()
        self.update_analysis()
        self.update_table()
        self.on_date_selected()  # Update selected date info
    
    def update_statistics(self):
        """Update statistics display"""
        if not self.rates_data:
            self.stats_label.setText("📊 İstatistikler\n\nHenüz veri yok")
            return
        
        rates = list(self.rates_data.values())
        if not rates:
            return
        
        min_rate = min(rates)
        max_rate = max(rates)
        avg_rate = sum(rates) / len(rates)
        total_days = len(rates)
        
        stats_text = f"""📊 İstatistikler

📈 En Yüksek: {max_rate:.4f} TL
📉 En Düşük: {min_rate:.4f} TL
📊 Ortalama: {avg_rate:.4f} TL
📅 Toplam Gün: {total_days}
📍 Fark: {max_rate - min_rate:.4f} TL
"""
        
        self.stats_label.setText(stats_text)
    
    def update_analysis(self):
        """Update rate analysis"""
        if len(self.rates_data) < 2:
            self.analysis_label.setText("📈 Kur Analizi\n\nYeterli veri yok")
            return
        
        # Get recent rates for trend analysis
        sorted_dates = sorted(self.rates_data.keys())
        recent_rates = [self.rates_data[date] for date in sorted_dates[-7:]]
        
        if len(recent_rates) >= 2:
            trend = "📈 Yükseliş" if recent_rates[-1] > recent_rates[0] else "📉 Düşüş"
            change = abs(recent_rates[-1] - recent_rates[0])
            change_percent = (change / recent_rates[0]) * 100
            
            analysis_text = f"""📈 Kur Analizi

🔍 7 Günlük Trend: {trend}
📊 Değişim: {change:.4f} TL
📈 Yüzde Değişim: %{change_percent:.2f}
📅 Son Kur: {recent_rates[-1]:.4f} TL
"""
        else:
            analysis_text = "📈 Kur Analizi\n\nAnaliz için daha fazla veri gerekli"
        
        self.analysis_label.setText(analysis_text)
    
    def update_table(self):
        """Update rates table"""
        if not self.rates_data:
            self.rates_table.setRowCount(0)
            return
        
        sorted_items = sorted(self.rates_data.items(), reverse=True)
        self.rates_table.setRowCount(len(sorted_items))
        
        previous_rate = None
        for row, (date_str, rate) in enumerate(sorted_items):
            # Date
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d.%m.%Y')
            self.rates_table.setItem(row, 0, QTableWidgetItem(formatted_date))
            
            # Rate
            rate_item = QTableWidgetItem(f"{rate:.4f}")
            self.rates_table.setItem(row, 1, rate_item)
            
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
                
                self.rates_table.setItem(row, 2, change_item)
            else:
                self.rates_table.setItem(row, 2, QTableWidgetItem("-"))
            
            # Status
            status_item = QTableWidgetItem("✅ Mevcut")
            status_item.setBackground(QColor(212, 237, 218))
            status_item.setForeground(QColor(21, 87, 36))
            self.rates_table.setItem(row, 3, status_item)
            
            previous_rate = rate
        
        # Resize columns
        self.rates_table.resizeColumnsToContents()
    
    def refresh_rates(self):
        """Refresh currency rates for selected date range"""
        start_date = self.start_date.date().toPython()
        end_date = self.end_date.date().toPython()
        
        if start_date > end_date:
            QMessageBox.warning(self, "Uyarı", "Başlangıç tarihi bitiş tarihinden sonra olamaz!")
            return
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start worker thread
        self.worker = CurrencyFetchWorker(self.currency_converter, start_date, end_date)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.rate_fetched.connect(self.on_rate_fetched)
        self.worker.finished.connect(self.on_refresh_finished)
        self.worker.error.connect(self.on_refresh_error)
        self.worker.start()
    
    def on_rate_fetched(self, date_str, rate):
        """Handle fetched rate"""
        self.rates_data[date_str] = rate
        
        # Update displays periodically
        if len(self.rates_data) % 5 == 0:  # Update every 5 rates
            self.update_displays()
    
    def on_refresh_finished(self):
        """Handle refresh completion"""
        self.progress_bar.setVisible(False)
        self.status_label.setText("✅ Kurlar başarıyla güncellendi!")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #d4edda;
                color: #155724;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #c3e6cb;
            }
        """)
        
        # Final update
        self.update_displays()
        
        QMessageBox.information(self, "Başarılı", 
                               f"Toplam {len(self.rates_data)} kur başarıyla güncellendi!")
    
    def on_refresh_error(self, error_msg):
        """Handle refresh error"""
        self.status_label.setText(f"❌ Hata: {error_msg}")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #f8d7da;
                color: #721c24;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #f5c6cb;
            }
        """)
    
    def export_rates(self):
        """Export rates to Excel"""
        if not self.rates_data:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak kur verisi bulunamadı!")
            return
        
        from PySide6.QtWidgets import QFileDialog
        
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
                sorted_items = sorted(self.rates_data.items())
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

def show_currency_calendar(currency_converter, parent=None):
    """Show currency calendar dialog"""
    dialog = CurrencyCalendarDialog(currency_converter, parent)
    dialog.exec()
