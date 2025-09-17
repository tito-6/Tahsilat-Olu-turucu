#!/usr/bin/env python3
"""
GUI version of CRM Processor
Provides a user-friendly interface for processing CRM export files
"""

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog, QMessageBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QProgressBar, QGroupBox, QSplitter,
    QMenuBar, QMenu, QStatusBar, QToolBar
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QFont

from crm_processor import CRMProcessor

class CRMProcessorWorker(QThread):
    """Worker thread for processing files"""
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(bool, object, list)  # success, dataframe, errors
    error = Signal(str)
    
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.processor = CRMProcessor()
    
    def run(self):
        try:
            self.status.emit("Processing file...")
            self.progress.emit(10)
            
            success, processed_df, errors = self.processor.process_file(self.file_path)
            
            self.progress.emit(100)
            self.status.emit("Processing completed")
            
            self.finished.emit(success, processed_df, errors)
            
        except Exception as e:
            self.error.emit(str(e))

class CRMProcessorGUI(QMainWindow):
    """Main GUI window for CRM Processor"""
    
    def __init__(self):
        super().__init__()
        self.processor = CRMProcessor()
        self.current_data = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("CRM Export Processor")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create main content
        self.create_main_content(main_layout)
        
        # Create status bar
        self.create_status_bar()
        
        # Apply styles
        self.apply_styles()
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        open_action = QAction('Open CRM File', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        export_action = QAction('Export Processed Data', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Open file button
        open_btn = QPushButton("Open CRM File")
        open_btn.clicked.connect(self.open_file)
        toolbar.addWidget(open_btn)
        
        # Export button
        export_btn = QPushButton("Export Data")
        export_btn.clicked.connect(self.export_data)
        toolbar.addWidget(export_btn)
        
        toolbar.addSeparator()
        
        # Process button
        process_btn = QPushButton("Process File")
        process_btn.clicked.connect(self.process_file)
        toolbar.addWidget(process_btn)
    
    def create_main_content(self, main_layout):
        """Create main content area"""
        # Create splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - File selection and controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Data display
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 800])
    
    def create_left_panel(self):
        """Create left control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_group)
        
        # File path display
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setWordWrap(True)
        self.file_path_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: monospace;
            }
        """)
        file_layout.addWidget(self.file_path_label)
        
        # File selection button
        select_btn = QPushButton("Select CRM File")
        select_btn.clicked.connect(self.open_file)
        file_layout.addWidget(select_btn)
        
        layout.addWidget(file_group)
        
        # Processing group
        process_group = QGroupBox("Processing")
        process_layout = QVBoxLayout(process_group)
        
        # Process button
        self.process_btn = QPushButton("Process File")
        self.process_btn.clicked.connect(self.process_file)
        self.process_btn.setEnabled(False)
        process_layout.addWidget(self.process_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        process_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        process_layout.addWidget(self.status_label)
        
        layout.addWidget(process_group)
        
        # Results group
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)
        
        # Results text
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        self.results_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
        
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
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.setSortingEnabled(True)
        self.tab_widget.addTab(self.data_table, "Processed Data")
        
        # Summary tab
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        self.tab_widget.addTab(self.summary_text, "Summary")
        
        return panel
    
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def apply_styles(self):
        """Apply custom styles"""
        style = """
        QMainWindow {
            background-color: #f0f0f0;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QPushButton {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #0056b3;
        }
        QPushButton:pressed {
            background-color: #004085;
        }
        QPushButton:disabled {
            background-color: #6c757d;
        }
        QTableWidget {
            gridline-color: #d0d0d0;
            background-color: white;
            alternate-background-color: #f9f9f9;
        }
        QHeaderView::section {
            background-color: #e9ecef;
            padding: 4px;
            border: 1px solid #d0d0d0;
            font-weight: bold;
        }
        """
        self.setStyleSheet(style)
    
    def open_file(self):
        """Open file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CRM Export File", "",
            "CSV Files (*.csv);;Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        
        if file_path:
            self.current_file = file_path
            self.file_path_label.setText(file_path)
            self.process_btn.setEnabled(True)
            self.status_bar.showMessage(f"Selected: {os.path.basename(file_path)}")
    
    def process_file(self):
        """Process the selected file"""
        if not hasattr(self, 'current_file') or not self.current_file:
            QMessageBox.warning(self, "Warning", "Please select a file first")
            return
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.process_btn.setEnabled(False)
        
        # Start processing worker
        self.worker = CRMProcessorWorker(self.current_file)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.error.connect(self.on_processing_error)
        self.worker.start()
    
    def on_processing_finished(self, success, processed_df, errors):
        """Handle processing completion"""
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        
        if success:
            self.current_data = processed_df
            self.update_data_display(processed_df)
            self.update_summary(processed_df)
            
            # Show results
            results_text = f"✅ Successfully processed {len(processed_df)} records"
            if errors:
                results_text += f"\n⚠️ Warnings: {len(errors)}"
            self.results_text.setPlainText(results_text)
            
            self.status_bar.showMessage(f"Processed {len(processed_df)} records successfully")
        else:
            error_text = "❌ Processing failed:\n" + "\n".join(errors)
            self.results_text.setPlainText(error_text)
            self.status_bar.showMessage("Processing failed")
    
    def on_processing_error(self, error_msg):
        """Handle processing error"""
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        
        error_text = f"❌ Error: {error_msg}"
        self.results_text.setPlainText(error_text)
        self.status_bar.showMessage("Processing error")
    
    def update_data_display(self, df):
        """Update the data table display"""
        if df.empty:
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            return
        
        # Set up table
        self.data_table.setColumnCount(len(df.columns))
        self.data_table.setHorizontalHeaderLabels(df.columns)
        self.data_table.setRowCount(len(df))
        
        # Populate table
        for row in range(len(df)):
            for col in range(len(df.columns)):
                value = df.iloc[row, col]
                if pd.isna(value):
                    value = ""
                else:
                    value = str(value)
                
                item = QTableWidgetItem(value)
                self.data_table.setItem(row, col, item)
    
    def update_summary(self, df):
        """Update the summary display"""
        if df.empty:
            self.summary_text.setPlainText("No data to summarize")
            return
        
        summary = self.processor.generate_summary(df)
        
        summary_text = f"""
📊 PROCESSING SUMMARY
{'='*50}

📈 Basic Statistics:
   Total Records: {summary['total_records']:,}
   Total Amount: {summary['total_amount']:,.2f}
   Unique Customers: {summary['customers']:,}

📅 Date Range:
   Start: {summary['date_range']['start']}
   End: {summary['date_range']['end']}

💰 Currency Distribution:
"""
        
        for currency, count in summary['currencies'].items():
            summary_text += f"   {currency}: {count:,} records\n"
        
        summary_text += f"\n🏦 Payment Channels:\n"
        for channel, count in summary['payment_channels'].items():
            summary_text += f"   {channel}: {count:,} records\n"
        
        summary_text += f"\n🏢 Projects:\n"
        for project, count in summary['projects'].items():
            summary_text += f"   {project}: {count:,} records\n"
        
        self.summary_text.setPlainText(summary_text)
    
    def export_data(self):
        """Export processed data"""
        if self.current_data is None or self.current_data.empty:
            QMessageBox.warning(self, "Warning", "No data to export")
            return
        
        file_path, file_type = QFileDialog.getSaveFileName(
            self, "Export Processed Data", "processed_crm_data",
            "CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        
        if file_path:
            format_type = 'csv' if file_path.endswith('.csv') else 'excel'
            if self.processor.export_processed_data(self.current_data, file_path, format_type):
                QMessageBox.information(self, "Success", f"Data exported to: {file_path}")
            else:
                QMessageBox.critical(self, "Error", "Failed to export data")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About CRM Processor", 
                         "CRM Export Processor v1.0\n\n"
                         "A flexible tool for processing CRM export files\n"
                         "with automatic column detection and data normalization.")
    
    def closeEvent(self, event):
        """Handle application close"""
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()

def main():
    """Main function"""
    app = QApplication(sys.argv)
    app.setApplicationName("CRM Processor")
    app.setApplicationVersion("1.0.0")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = CRMProcessorGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
