from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QGroupBox, QLineEdit, QTextEdit, QFrame, QCheckBox, QPushButton, QDateEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from datetime import datetime

class ReportFunctionsWidget(QWidget):
    """
    Widget to host report generation functions and settings.
    Includes data entry for Report Header/Footer details.
    """
    request_generate_total = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # === Report Information Group ===
        info_group = QGroupBox("Rapor Bilgileri")
        info_layout = QGridLayout(info_group)
        info_layout.setVerticalSpacing(10)
        info_layout.setHorizontalSpacing(15)
        
        # Row 0: Port & Terminal
        self.port_edit = QLineEdit()
        self.terminal_edit = QLineEdit()
        
        info_layout.addWidget(QLabel("Actual Port:"), 0, 0)
        info_layout.addWidget(self.port_edit, 0, 1)
        info_layout.addWidget(QLabel("Actual Terminal:"), 0, 2)
        info_layout.addWidget(self.terminal_edit, 0, 3)
        
        # Row 1: MMC & Type
        self.mmc_edit = QLineEdit()
        self.report_type_edit = QLineEdit()
        
        info_layout.addWidget(QLabel("MMC NO:"), 1, 0)
        info_layout.addWidget(self.mmc_edit, 1, 1)
        info_layout.addWidget(QLabel("Report Type:"), 1, 2)
        info_layout.addWidget(self.report_type_edit, 1, 3)
        
        # Row 2: Cargo & Receiver
        self.cargo_edit = QLineEdit()
        self.receiver_edit = QLineEdit()
        
        info_layout.addWidget(QLabel("Cargo:"), 2, 0)
        info_layout.addWidget(self.cargo_edit, 2, 1)
        info_layout.addWidget(QLabel("Receiver:"), 2, 2)
        info_layout.addWidget(self.receiver_edit, 2, 3)
        
        # Row 3: Drafts (Read Only) - Order matches Ullage tab: Aft left, Fwd right
        self.draft_aft_edit = QLineEdit()
        self.draft_aft_edit.setReadOnly(True)
        
        self.draft_fwd_edit = QLineEdit()
        self.draft_fwd_edit.setReadOnly(True)
        
        info_layout.addWidget(QLabel("Draft Aft (m):"), 3, 0)
        info_layout.addWidget(self.draft_aft_edit, 3, 1)
        info_layout.addWidget(QLabel("Draft Fwd (m):"), 3, 2)
        info_layout.addWidget(self.draft_fwd_edit, 3, 3)
        
        # Row 4: Date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd-MM-yyyy")
        self.date_edit.setDate(QDate.currentDate())  # Default to today
        
        info_layout.addWidget(QLabel("Date:"), 4, 0)
        info_layout.addWidget(self.date_edit, 4, 1)
        
        # Row 5: Remarks
        self.remarks_edit = QTextEdit()
        self.remarks_edit.setMaximumHeight(80)
        
        info_layout.addWidget(QLabel("Remarks:"), 5, 0)
        info_layout.addWidget(self.remarks_edit, 5, 1, 1, 3) # Span 3 cols
        
        layout.addWidget(info_group)
        
        # === Generation Actions ===
        action_group = QGroupBox("Rapor Oluştur")
        action_layout = QVBoxLayout(action_group)
        action_layout.setContentsMargins(15, 15, 15, 15)
        
        self.generate_btn = QPushButton("TOTAL ULLAGE REPORT")
        self.generate_btn.setMinimumHeight(40)
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5; 
                color: white; 
                font-weight: bold; 
                font-size: 11pt;
                border-radius: 6px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
            QPushButton:pressed {
                background-color: #3730a3;
            }
        """)
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        
        action_layout.addWidget(self.generate_btn)
        
        layout.addWidget(action_group)
        layout.addStretch()

    def _on_generate_clicked(self):
        """Emit signal for report generation."""
        self.request_generate_total.emit()

    def update_drafts(self, fwd: float, aft: float):
        """Update read-only draft displays related to the current voyage."""
        self.draft_fwd_edit.setText(f"{fwd:.2f}")
        self.draft_aft_edit.setText(f"{aft:.2f}")

    def get_report_data(self) -> dict:
        """Retrieve all data input from this widget."""
        return {
            'port': self.port_edit.text(),
            'terminal': self.terminal_edit.text(),
            'mmc_no': self.mmc_edit.text(),
            'report_type': self.report_type_edit.text(),
            'cargo': self.cargo_edit.text(),
            'receiver': self.receiver_edit.text(),
            'draft_fwd': self.draft_fwd_edit.text(),
            'draft_aft': self.draft_aft_edit.text(),
            'date': self.date_edit.date().toString("dd-MM-yyyy"),
            'remarks': self.remarks_edit.toPlainText()
        }

