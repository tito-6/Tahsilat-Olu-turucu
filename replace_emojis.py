#!/usr/bin/env python3
"""
Script to replace emojis with FontAwesome icons in the application
"""

import re
import os

# Emoji to FontAwesome icon mapping
EMOJI_ICON_MAP = {
    # Data and Reports
    '📊': 'qta.icon("fa5s.chart-bar")',
    '📈': 'qta.icon("fa5s.chart-line")',
    '📅': 'qta.icon("fa5s.calendar-alt")',
    '📋': 'qta.icon("fa5s.clipboard-list")',
    '📁': 'qta.icon("fa5s.folder")',
    '📄': 'qta.icon("fa5s.file-alt")',
    '📤': 'qta.icon("fa5s.download")',
    '📥': 'qta.icon("fa5s.upload")',
    
    # Actions and Controls
    '🔍': 'qta.icon("fa5s.search")',
    '✅': 'qta.icon("fa5s.check")',
    '❌': 'qta.icon("fa5s.times")',
    '🗑️': 'qta.icon("fa5s.trash")',
    '🔽': 'qta.icon("fa5s.sort-down")',
    '🔼': 'qta.icon("fa5s.sort-up")',
    '⚙️': 'qta.icon("fa5s.cog")',
    '🛠️': 'qta.icon("fa5s.tools")',
    
    # UI Elements
    '👁️': 'qta.icon("fa5s.eye")',
    '🖨️': 'qta.icon("fa5s.print")',
    '💱': 'qta.icon("fa5s.exchange-alt")',
    '💰': 'qta.icon("fa5s.money-bill-wave")',
    '🏦': 'qta.icon("fa5s.university")',
    
    # Status and Info
    'ℹ️': 'qta.icon("fa5s.info-circle")',
    '❓': 'qta.icon("fa5s.question-circle")',
    '⌨️': 'qta.icon("fa5s.keyboard")',
    '🎨': 'qta.icon("fa5s.palette")',
    '☀️': 'qta.icon("fa5s.sun")',
    '🌙': 'qta.icon("fa5s.moon")',
    
    # Success and Progress
    '🎯': 'qta.icon("fa5s.bullseye")',
    '🚀': 'qta.icon("fa5s.rocket")',
    '💡': 'qta.icon("fa5s.lightbulb")',
    '📝': 'qta.icon("fa5s.edit")',
    '🔧': 'qta.icon("fa5s.wrench")',
    '📚': 'qta.icon("fa5s.book")',
    '🤝': 'qta.icon("fa5s.handshake")',
    '📞': 'qta.icon("fa5s.phone")',
    '🎉': 'qta.icon("fa5s.party-horn")',
}

def replace_emojis_in_file(file_path):
    """Replace emojis with FontAwesome icons in a file"""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Replace emojis in strings
    for emoji, icon_code in EMOJI_ICON_MAP.items():
        # Replace emojis in QAction constructors
        content = re.sub(
            rf"QAction\('{re.escape(emoji)} ([^']+)',",
            f"QAction({icon_code}, '\\1',",
            content
        )
        
        # Replace emojis in addMenu calls
        content = re.sub(
            rf"addMenu\('{re.escape(emoji)} ([^']+)'\)",
            f"addMenu({icon_code}, '\\1')",
            content
        )
        
        # Replace emojis in QPushButton constructors
        content = re.sub(
            rf"QPushButton\('{re.escape(emoji)} ([^']+)'\)",
            f"QPushButton({icon_code}, '\\1')",
            content
        )
        
        # Replace emojis in QLabel text
        content = re.sub(
            rf"QLabel\('{re.escape(emoji)} ([^']+)'\)",
            f"QLabel('\\1')",
            content
        )
        
        # Replace emojis in setText calls
        content = re.sub(
            rf"setText\('{re.escape(emoji)} ([^']+)'\)",
            f"setText('\\1')",
            content
        )
        
        # Replace emojis in setWindowTitle calls
        content = re.sub(
            rf"setWindowTitle\('{re.escape(emoji)} ([^']+)'\)",
            f"setWindowTitle('\\1')",
            content
        )
        
        # Replace emojis in placeholder text
        content = re.sub(
            rf"setPlaceholderText\('{re.escape(emoji)} ([^']+)'\)",
            f"setPlaceholderText('\\1')",
            content
        )
        
        # Replace emojis in f-strings and regular strings
        content = re.sub(
            rf"'{re.escape(emoji)} ([^']+)'",
            f"'\\1'",
            content
        )
        
        # Replace emojis in HTML content
        content = re.sub(
            rf"<h([1-6])[^>]*>{re.escape(emoji)} ([^<]+)</h[1-6]>",
            r"<h\1>\2</h\1>",
            content
        )
    
    # Add qtawesome import if not present
    if 'import qtawesome as qta' not in content and 'qtawesome' in content:
        content = content.replace(
            'from PySide6.QtGui import',
            'from PySide6.QtGui import\nimport qtawesome as qta'
        )
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated: {file_path}")
    else:
        print(f"No changes needed: {file_path}")

def main():
    """Main function to process all Python files"""
    files_to_process = [
        'ui_main.py',
        'advanced_filter_dialog.py',
        'modern_cim_ui.py',
        'currency_calendar_dialog.py',
        'duplicate_detection_dialog.py',
        'data_validation_dialog.py',
        'crm_processor_gui.py'
    ]
    
    for file_path in files_to_process:
        if os.path.exists(file_path):
            replace_emojis_in_file(file_path)
        else:
            print(f"File not found: {file_path}")

if __name__ == "__main__":
    main()
