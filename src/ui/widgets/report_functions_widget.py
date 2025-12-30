from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QGroupBox, QLineEdit, QTextEdit, QFrame, QCheckBox, QPushButton, QDateEdit,
    QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from datetime import datetime

class ReportFunctionsWidget(QWidget):
    """
    Widget to host report generation functions and settings.
    Includes data entry for Report Header/Footer details.
    """
    request_generate_total = pyqtSignal()
    request_generate_selected = pyqtSignal()  # For Selected Parcels Report

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
        
        # === Report Generation Section (Side by Side) ===
        reports_container = QWidget()
        reports_layout = QHBoxLayout(reports_container)
        reports_layout.setContentsMargins(0, 0, 0, 0)
        reports_layout.setSpacing(15)
        
        # --- LEFT: Parcel Selection + Selected Report ---
        parcel_group = QGroupBox("Parsel Seçimi")
        parcel_layout = QVBoxLayout(parcel_group)
        parcel_layout.setContentsMargins(10, 10, 10, 10)
        
        self.parcel_list = QListWidget()
        self.parcel_list.setMaximumHeight(150)
        # Dark theme styling for better checkbox visibility
        self.parcel_list.setStyleSheet("""
            QListWidget {
                background-color: #2d3748;
                color: #e2e8f0;
                border: 1px solid #4a5568;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #4a5568;
            }
            QListWidget::item:selected {
                background-color: #4299e1;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #3d4f65;
            }
            QListWidget::indicator {
                width: 16px;
                height: 16px;
            }
            QListWidget::indicator:unchecked {
                border: 2px solid #718096;
                background-color: #1a202c;
                border-radius: 3px;
            }
            QListWidget::indicator:checked {
                border: 2px solid #48bb78;
                background-color: #48bb78;
                border-radius: 3px;
            }
        """)
        parcel_layout.addWidget(self.parcel_list)
        
        self.generate_selected_btn = QPushButton("SELECTED PARCELS REPORT")
        self.generate_selected_btn.setMinimumHeight(40)
        self.generate_selected_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_selected_btn.setStyleSheet("""
            QPushButton {
                background-color: #059669; 
                color: white; 
                font-weight: bold; 
                font-size: 11pt;
                border-radius: 6px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #047857;
            }
            QPushButton:pressed {
                background-color: #065f46;
            }
        """)
        self.generate_selected_btn.clicked.connect(self._on_generate_selected_clicked)
        parcel_layout.addWidget(self.generate_selected_btn)
        
        reports_layout.addWidget(parcel_group, stretch=2)
        
        # --- RIGHT: Total Ullage Report ---
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
        action_layout.addStretch()  # Push button to top
        
        reports_layout.addWidget(action_group, stretch=1)
        
        layout.addWidget(reports_container)
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

    def _on_generate_selected_clicked(self):
        """Emit signal for selected parcels report generation."""
        self.request_generate_selected.emit()

    def _on_all_parcels_toggled(self, item):
        """Handle ALL PARCELS checkbox toggle to select/deselect all."""
        if item.data(Qt.ItemDataRole.UserRole) == "__ALL__":
            new_state = item.checkState()
            # Block signals to prevent recursion
            self.parcel_list.blockSignals(True)
            for i in range(1, self.parcel_list.count()):  # Skip first item (ALL)
                self.parcel_list.item(i).setCheckState(new_state)
            self.parcel_list.blockSignals(False)

    def _create_color_icon(self, color_hex: str, size: int = 16):
        """Create a small colored square icon."""
        from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(color_hex))
        return QIcon(pixmap)

    def set_parcels(self, parcels, tanks=None, tank_readings=None):
        """Populate parcel list with checkable items.
        
        Args:
            parcels: List of Parcel objects with 'id', 'name', 'receiver', 'color' attributes.
            tanks: List of Tank objects (optional, for tank name display).
            tank_readings: Dict mapping tank_id to TankReading (optional).
        """
        self.parcel_list.clear()
        
        # Disconnect previous signal if connected
        try:
            self.parcel_list.itemChanged.disconnect(self._on_all_parcels_toggled)
        except:
            pass
        
        # Add "ALL PARCELS" at top
        all_item = QListWidgetItem("ALL PARCELS")
        all_item.setFlags(all_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        all_item.setCheckState(Qt.CheckState.Unchecked)
        all_item.setData(Qt.ItemDataRole.UserRole, "__ALL__")
        # Style differently
        font = all_item.font()
        font.setBold(True)
        all_item.setFont(font)
        self.parcel_list.addItem(all_item)
        
        # Connect toggle handler
        self.parcel_list.itemChanged.connect(self._on_all_parcels_toggled)
        
        # Build tank map: tank_id -> tank name
        tank_map = {}
        if tanks:
            for t in tanks:
                tank_map[t.id] = t.name
        
        # Build parcel -> tank list mapping
        parcel_tanks = {}  # parcel_id -> list of tank names
        if tank_readings:
            for reading in tank_readings.values():
                if reading.parcel_id and reading.parcel_id != "0":
                    if reading.parcel_id not in parcel_tanks:
                        parcel_tanks[reading.parcel_id] = []
                    # Get abbreviated tank name
                    raw_name = tank_map.get(reading.tank_id, reading.tank_id)
                    abbrev = raw_name.upper().replace("COT", "").replace("TANK", "").replace("NO", "").replace(".", "").replace(" ", "")
                    abbrev = abbrev.replace("STARBOARD", "S").replace("PORT", "P").replace("CENTER", "C")
                    parcel_tanks[reading.parcel_id].append(abbrev)
        
        for parcel in parcels:
            # Skip SLOP (id=0)
            if parcel.id == "0":
                continue
            
            # Format: "Grade Receiver (Tank1-Tank2-Tank3)"
            grade = parcel.name or ""
            receiver = parcel.receiver or ""
            tank_list = parcel_tanks.get(parcel.id, [])
            tank_str = "-".join(tank_list) if tank_list else ""
            
            if tank_str:
                display = f"{grade} {receiver} ({tank_str})"
            else:
                display = f"{grade} {receiver}"
            
            item = QListWidgetItem(display.strip())
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, parcel.id)  # Store parcel ID
            
            # Add color icon
            parcel_color = getattr(parcel, 'color', '#3B82F6')
            item.setIcon(self._create_color_icon(parcel_color))
            
            self.parcel_list.addItem(item)

    def get_selected_parcel_ids(self):
        """Return list of checked parcel IDs (excluding ALL PARCELS item)."""
        selected = []
        for i in range(self.parcel_list.count()):
            item = self.parcel_list.item(i)
            parcel_id = item.data(Qt.ItemDataRole.UserRole)
            # Skip the ALL item
            if parcel_id == "__ALL__":
                continue
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(parcel_id)
        return selected
