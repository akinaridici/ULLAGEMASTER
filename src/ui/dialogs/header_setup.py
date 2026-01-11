"""
Header Setup Dialog - Configure Report Headers.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QPushButton, QFormLayout, 
    QMessageBox
)
from PyQt6.QtCore import Qt
import os
from utils.config_headers import load_header_config, save_header_config, get_header_config_path

class HeaderSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Report Header Configuration")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.data = load_header_config()
        self.inputs = {}
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Explanation
        info_label = QLabel(
            "Configure header information for generating PDF reports.\n"
            f"Config File: {get_header_config_path()}"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #94a3b8; font-style: italic;")
        layout.addWidget(info_label)
        
        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self.create_ullage_tab(), "Ullage Report")
        tabs.addTab(self.create_protest_tab(), "Protest Letter")
        layout.addWidget(tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        open_folder_btn = QPushButton("📂 Open Config Folder")
        open_folder_btn.clicked.connect(self.open_config_folder)
        
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self.save_config)
        save_btn.setStyleSheet("background-color: #0d9488; color: white; font-weight: bold;")
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(open_folder_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
    def create_ullage_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        self.inputs['ULLAGE_REPORT'] = {}
        
        section = self.data.get('ULLAGE_REPORT', {})
        
        fields = [
            ("title_line_1", "Title Line 1"),
            ("title_line_2", "Title Line 2"),
            ("title_line_3", "Title Line 3"),
            ("issue_no", "Issue No"),
            ("issue_date", "Issue Date"),
            ("rev_no", "Rev No"),
            ("page_format", "Page Format")
        ]
        
        for key, label in fields:
            inp = QLineEdit(section.get(key, ""))
            form.addRow(label + ":", inp)
            self.inputs['ULLAGE_REPORT'][key] = inp
            
        return widget
        
    def create_protest_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        self.inputs['PROTEST_REPORT'] = {}
        
        section = self.data.get('PROTEST_REPORT', {})
        
        fields = [
            ("title_line_1", "Title Line 1"),
            ("title_line_2", "Title Line 2"),
            ("doc_title", "Doc Title"),
            ("issue_no", "Issue No"),
            ("issue_date", "Issue Date"),
            ("rev_no", "Rev No"),
            ("rev_date", "Rev Date")
        ]
        
        for key, label in fields:
            inp = QLineEdit(section.get(key, ""))
            form.addRow(label + ":", inp)
            self.inputs['PROTEST_REPORT'][key] = inp
            
        return widget
        
    def open_config_folder(self):
        path = get_header_config_path().parent
        os.startfile(path)
        
    def save_config(self):
        # Update data from inputs
        for section, fields in self.inputs.items():
            if section not in self.data:
                self.data[section] = {}
            for key, inp in fields.items():
                self.data[section][key] = inp.text()
                
        if save_header_config(self.data):
            QMessageBox.information(self, "Success", "Configuration saved successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to save configuration.")
