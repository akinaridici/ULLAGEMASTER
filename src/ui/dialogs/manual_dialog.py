"""
User Manual Dialog.
Displays the ASCII-formatted user manual in English and Turkish.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QTextEdit, 
    QDialogButtonBox, QWidget
)
from PyQt6.QtGui import QFont

from ui.manual_content import MANUAL_EN, MANUAL_TR
from i18n import t

class ManualDialog(QDialog):
    """
    Dialog to display the User Manual.
    Uses monospaced font to preserve ASCII formatting.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UllageMaster User Manual / Kullanım Kılavuzu")
        self.setMinimumSize(900, 700)
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Tabs for languages
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # English Tab
        self.tabs.addTab(self._create_text_widget(MANUAL_EN), "English")
        
        # Turkish Tab
        self.tabs.addTab(self._create_text_widget(MANUAL_TR), "Türkçe")
        
        # Close button
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _create_text_widget(self, content: str) -> QTextEdit:
        """Create a read-only text edit with monospaced font."""
        text_edit = QTextEdit()
        text_edit.setPlainText(content)
        text_edit.setReadOnly(True)
        
        # Set monospaced font for ASCII art
        font = QFont("Consolas, 'Courier New', monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        # Dynamic point size calculation might be good, but 10 is safe standard
        font.setPointSize(10)
        text_edit.setFont(font)
        
        return text_edit
