"""
Header Setup Dialog - Configure Report Headers.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QPushButton, QFormLayout, 
    QMessageBox
)
from PyQt6.QtCore import Qt
from utils.config_manager import get_config
from i18n import t

class HeaderSetupDialog(QDialog):
    """
    Dialog to configure Report Headers (Ullage Report & Protest Letter).
    PERSISTENCE: Stores data in 'data/config/UllageMaster.ini' via ConfigManager.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("headers", "menu"))
        self.setMinimumSize(500, 400)
        
        self.config = get_config()
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Explanation
        info_label = QLabel(
            "Configure header information for generating PDF reports."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #94a3b8; font-style: italic;")
        layout.addWidget(info_label)
        
        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._create_ullage_tab(), "Ullage Report")
        tabs.addTab(self._create_protest_tab(), "Protest Letter")
        layout.addWidget(tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self.save_data)
        save_btn.setStyleSheet("background-color: #0d9488; color: white; font-weight: bold;")
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
    def _create_ullage_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        
        self.ullage_line1 = QLineEdit()
        self.ullage_line2 = QLineEdit()
        self.ullage_line3 = QLineEdit()
        self.ullage_issue_no = QLineEdit()
        self.ullage_issue_date = QLineEdit()
        self.ullage_rev_no = QLineEdit()
        self.ullage_page_fmt = QLineEdit()
        
        form.addRow("Title Line 1:", self.ullage_line1)
        form.addRow("Title Line 2:", self.ullage_line2)
        form.addRow("Title Line 3:", self.ullage_line3)
        form.addRow("Issue No:", self.ullage_issue_no)
        form.addRow("Issue Date:", self.ullage_issue_date)
        form.addRow("Rev No:", self.ullage_rev_no)
        form.addRow("Page Format:", self.ullage_page_fmt)
            
        return widget
        
    def _create_protest_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        
        self.protest_line1 = QLineEdit()
        self.protest_line2 = QLineEdit()
        self.protest_doc_title = QLineEdit()
        self.protest_issue_no = QLineEdit()
        self.protest_issue_date = QLineEdit()
        self.protest_rev_no = QLineEdit()
        self.protest_rev_date = QLineEdit()
        
        form.addRow("Title Line 1:", self.protest_line1)
        form.addRow("Title Line 2:", self.protest_line2)
        form.addRow("Doc Title:", self.protest_doc_title)
        form.addRow("Issue No:", self.protest_issue_no)
        form.addRow("Issue Date:", self.protest_issue_date)
        form.addRow("Rev No:", self.protest_rev_no)
        form.addRow("Rev Date:", self.protest_rev_date)
            
        return widget
        
    def load_data(self):
        """Load data from ConfigManager into fields."""
        # Ullage Report
        ullage_data = self.config.get_section("ULLAGE_REPORT")
        self.ullage_line1.setText(ullage_data.get("title_line_1", ""))
        self.ullage_line2.setText(ullage_data.get("title_line_2", ""))
        self.ullage_line3.setText(ullage_data.get("title_line_3", ""))
        self.ullage_issue_no.setText(ullage_data.get("issue_no", ""))
        self.ullage_issue_date.setText(ullage_data.get("issue_date", ""))
        self.ullage_rev_no.setText(ullage_data.get("rev_no", ""))
        self.ullage_page_fmt.setText(ullage_data.get("page_format", ""))
        
        # Protest Letter
        protest_data = self.config.get_section("PROTEST_REPORT")
        self.protest_line1.setText(protest_data.get("title_line_1", ""))
        self.protest_line2.setText(protest_data.get("title_line_2", ""))
        self.protest_doc_title.setText(protest_data.get("doc_title", ""))
        self.protest_issue_no.setText(protest_data.get("issue_no", ""))
        self.protest_issue_date.setText(protest_data.get("issue_date", ""))
        self.protest_rev_no.setText(protest_data.get("rev_no", ""))
        self.protest_rev_date.setText(protest_data.get("rev_date", ""))

    def save_data(self):
        """Save data to ConfigManager."""
        
        # Ullage Report Section
        self.config.set_section("ULLAGE_REPORT", {
            "title_line_1": self.ullage_line1.text(),
            "title_line_2": self.ullage_line2.text(),
            "title_line_3": self.ullage_line3.text(),
            "issue_no": self.ullage_issue_no.text(),
            "issue_date": self.ullage_issue_date.text(),
            "rev_no": self.ullage_rev_no.text(),
            "page_format": self.ullage_page_fmt.text()
        })
        
        # Protest Report Section
        self.config.set_section("PROTEST_REPORT", {
            "title_line_1": self.protest_line1.text(),
            "title_line_2": self.protest_line2.text(),
            "doc_title": self.protest_doc_title.text(),
            "issue_no": self.protest_issue_no.text(),
            "issue_date": self.protest_issue_date.text(),
            "rev_no": self.protest_rev_no.text(),
            "rev_date": self.protest_rev_date.text()
        })
        
        QMessageBox.information(self, "Saved", "Configuration saved successfully.")
        self.accept()
