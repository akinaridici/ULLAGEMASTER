from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QGroupBox, QLineEdit, QTextEdit, QFrame, QCheckBox, QPushButton, QDateEdit,
    QListWidget, QListWidgetItem, QComboBox, QCompleter
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QBrush, QLinearGradient
from datetime import datetime

from core.history_manager import get_history_manager


class ShipIconWidget(QWidget):
    """
    A widget that draws a top-down (bird's eye) view of a tanker ship.
    Professional maritime-style icon for the Stowage Plan section.
    Shows hull outline with tank compartments, bow (right), stern (left).
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 90)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get widget dimensions
        w = self.width()
        h = self.height()
        
        # Margins
        margin_x = 15
        margin_y = 12
        
        ship_w = w - 2 * margin_x
        ship_h = h - 2 * margin_y
        
        # Ship dimensions
        x = margin_x
        y = margin_y
        center_y = y + ship_h / 2
        
        bow_len = ship_w * 0.12   # Pointed bow
        stern_len = ship_w * 0.06  # Rounded stern
        body_len = ship_w - bow_len - stern_len
        
        # Colors
        hull_color = QColor("#374151")      # Dark hull outline
        deck_color = QColor("#E5E7EB")      # Light gray deck
        tank_green = QColor("#10B981")      # Emerald green
        tank_orange = QColor("#F59E0B")     # Amber orange
        tank_blue = QColor("#3B82F6")       # Blue
        tank_pink = QColor("#EC4899")       # Pink
        centerline_color = QColor("#9CA3AF") # Gray centerline
        bridge_color = QColor("#6B7280")    # Bridge gray
        
        # =========================
        # 1. HULL OUTLINE (top-down)
        # =========================
        hull_path = QPainterPath()
        
        hull_top = y
        hull_bottom = y + ship_h
        
        # Start at stern top-left
        hull_path.moveTo(x + stern_len * 0.5, hull_top)
        
        # Stern curve (left side - rounded)
        hull_path.cubicTo(
            QPointF(x, hull_top),
            QPointF(x, center_y),
            QPointF(x, center_y)
        )
        hull_path.cubicTo(
            QPointF(x, center_y),
            QPointF(x, hull_bottom),
            QPointF(x + stern_len * 0.5, hull_bottom)
        )
        
        # Bottom edge to bow
        hull_path.lineTo(x + stern_len + body_len, hull_bottom)
        
        # Bow curve (right side - pointed)
        bow_start_x = x + stern_len + body_len
        bow_tip_x = x + ship_w
        
        hull_path.cubicTo(
            QPointF(bow_start_x + bow_len * 0.6, hull_bottom),
            QPointF(bow_tip_x, center_y + ship_h * 0.15),
            QPointF(bow_tip_x, center_y)
        )
        hull_path.cubicTo(
            QPointF(bow_tip_x, center_y - ship_h * 0.15),
            QPointF(bow_start_x + bow_len * 0.6, hull_top),
            QPointF(bow_start_x, hull_top)
        )
        
        # Top edge back to stern
        hull_path.lineTo(x + stern_len * 0.5, hull_top)
        hull_path.closeSubpath()
        
        # Draw hull
        painter.setPen(QPen(hull_color, 2))
        painter.setBrush(QBrush(deck_color))
        painter.drawPath(hull_path)
        
        # =========================
        # 2. CENTERLINE (dashed)
        # =========================
        painter.setPen(QPen(centerline_color, 1, Qt.PenStyle.DashLine))
        painter.drawLine(
            int(x + stern_len * 0.3), int(center_y),
            int(bow_start_x + bow_len * 0.5), int(center_y)
        )
        
        # =========================
        # 3. TANK COMPARTMENTS (Port & Starboard rows)
        # =========================
        tank_count = 6
        tank_area_start = x + stern_len + body_len * 0.08
        tank_area_width = body_len * 0.85
        tank_w = (tank_area_width / tank_count) - 2
        tank_h = ship_h * 0.32
        gap = 1.5
        
        tank_colors = [tank_green, tank_orange, tank_blue, tank_pink, tank_green, tank_orange]
        
        for i in range(tank_count):
            tank_x = tank_area_start + i * (tank_w + 2)
            color = tank_colors[i % len(tank_colors)]
            
            # Port tank (top row)
            port_rect = QRectF(tank_x, center_y - tank_h - gap, tank_w, tank_h)
            painter.setPen(QPen(hull_color.lighter(130), 0.5))
            painter.setBrush(QBrush(color.lighter(115)))
            painter.drawRoundedRect(port_rect, 2, 2)
            
            # Starboard tank (bottom row)
            stbd_rect = QRectF(tank_x, center_y + gap, tank_w, tank_h)
            painter.setBrush(QBrush(color.lighter(115)))
            painter.drawRoundedRect(stbd_rect, 2, 2)
        
        # =========================
        # 4. BRIDGE (stern area)
        # =========================
        bridge_w = body_len * 0.08
        bridge_h = ship_h * 0.5
        bridge_x = x + stern_len * 0.6
        bridge_y = center_y - bridge_h / 2
        
        bridge_rect = QRectF(bridge_x, bridge_y, bridge_w, bridge_h)
        painter.setPen(QPen(hull_color, 1))
        painter.setBrush(QBrush(bridge_color))
        painter.drawRoundedRect(bridge_rect, 2, 2)
        
        # =========================
        # 5. P/S LABELS
        # =========================
        painter.setPen(QPen(QColor("#3B82F6")))  # Blue for Port
        painter.setFont(painter.font())
        font = painter.font()
        font.setBold(True)
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(int(x + stern_len + 3), int(center_y - tank_h - gap - 2), "P")
        
        painter.setPen(QPen(QColor("#10B981")))  # Green for Starboard
        painter.drawText(int(x + stern_len + 3), int(center_y + tank_h + gap + 10), "S")
        
        # =========================
        # 6. BOW/STERN INDICATORS
        # =========================
        painter.setPen(QPen(QColor("#6B7280")))
        font.setPointSize(6)
        painter.setFont(font)
        
        # Bow arrow/label (right)
        painter.drawText(int(bow_tip_x - 8), int(center_y - ship_h * 0.42), "▶")
        
        # Stern label (left)
        painter.drawText(int(x + 2), int(center_y - ship_h * 0.42), "◀")


class ReportFunctionsWidget(QWidget):
    """
    Widget to host report generation functions and settings.
    Includes data entry for Report Header/Footer details with autocomplete.
    """
    request_generate_total = pyqtSignal()
    request_generate_selected = pyqtSignal()  # For Selected Parcels Report
    request_generate_stowage = pyqtSignal()   # For Stowage Plan Report

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history = get_history_manager()
        self._init_ui()
        self._load_history()

    def _create_autocomplete_combo(self) -> QComboBox:
        """Create an editable combobox with autocomplete functionality."""
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setMaxVisibleItems(10)
        
        # Configure completer for substring matching
        completer = combo.completer()
        if completer:
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        # Style the combobox to match dark theme
        combo.setStyleSheet("""
            QComboBox {
                background-color: #2d3748;
                color: #e2e8f0;
                border: 1px solid #4a5568;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 24px;
            }
            QComboBox:focus {
                border: 1px solid #4299e1;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #718096;
                margin-right: 6px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d3748;
                color: #e2e8f0;
                border: 1px solid #4a5568;
                selection-background-color: #4299e1;
            }
        """)
        
        return combo

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # === Report Information Group ===
        info_group = QGroupBox("Report Headers")
        info_layout = QGridLayout(info_group)
        info_layout.setVerticalSpacing(10)
        info_layout.setHorizontalSpacing(15)
        
        # Row 0: Port & Terminal (autocomplete)
        self.port_edit = self._create_autocomplete_combo()
        self.terminal_edit = self._create_autocomplete_combo()
        
        info_layout.addWidget(QLabel("Actual Port:"), 0, 0)
        info_layout.addWidget(self.port_edit, 0, 1)
        info_layout.addWidget(QLabel("Actual Terminal:"), 0, 2)
        info_layout.addWidget(self.terminal_edit, 0, 3)
        
        # Row 1: MMC & Type (autocomplete)
        self.mmc_edit = self._create_autocomplete_combo()
        self.report_type_edit = self._create_autocomplete_combo()
        
        info_layout.addWidget(QLabel("MMC NO:"), 1, 0)
        info_layout.addWidget(self.mmc_edit, 1, 1)
        info_layout.addWidget(QLabel("Report Type:"), 1, 2)
        info_layout.addWidget(self.report_type_edit, 1, 3)
        
        # Row 2: Cargo & Receiver (autocomplete)
        self.cargo_edit = self._create_autocomplete_combo()
        self.receiver_edit = self._create_autocomplete_combo()
        
        info_layout.addWidget(QLabel("Product (cargo):"), 2, 0)
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
        
        # Row 4: Date & SLOP Label
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd-MM-yyyy")
        self.date_edit.setDate(QDate.currentDate())  # Default to today
        
        self.slop_label_edit = QLineEdit()
        self.slop_label_edit.setPlaceholderText("SLOP / WASHING WATER")
        self.slop_label_edit.setText("SLOP")
        
        info_layout.addWidget(QLabel("Date:"), 4, 0)
        info_layout.addWidget(self.date_edit, 4, 1)
        info_layout.addWidget(QLabel("SLOP Label:"), 4, 2)
        info_layout.addWidget(self.slop_label_edit, 4, 3)
        
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
        parcel_group = QGroupBox("Select Parcels")
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
        
        # --- RIGHT: Stowage Plan Report ---
        stowage_group = QGroupBox("Stowage Plan")
        stowage_layout = QVBoxLayout(stowage_group)
        stowage_layout.setContentsMargins(15, 15, 15, 15)
        stowage_layout.setSpacing(10)
        
        # Ship icon widget (symbolic tanker silhouette)
        ship_icon = ShipIconWidget()
        ship_icon.setMinimumHeight(100)
        ship_icon.setMaximumHeight(120)
        stowage_layout.addWidget(ship_icon)
        
        stowage_layout.addStretch()
        
        # Stowage Plan Report button at bottom
        self.generate_stowage_btn = QPushButton("STOWAGE PLAN REPORT")
        self.generate_stowage_btn.setMinimumHeight(40)
        self.generate_stowage_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_stowage_btn.setStyleSheet("""
            QPushButton {
                background-color: #7c3aed; 
                color: white; 
                font-weight: bold; 
                font-size: 11pt;
                border-radius: 6px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #6d28d9;
            }
            QPushButton:pressed {
                background-color: #5b21b6;
            }
        """)
        self.generate_stowage_btn.clicked.connect(self._on_generate_stowage_clicked)
        stowage_layout.addWidget(self.generate_stowage_btn)
        
        reports_layout.addWidget(stowage_group, stretch=1)
        
        layout.addWidget(reports_container)
        layout.addStretch()

    def _load_history(self):
        """Load history from INI file into comboboxes."""
        # Map field names to widgets
        field_widgets = {
            'port': self.port_edit,
            'terminal': self.terminal_edit,
            'mmc_no': self.mmc_edit,
            'report_type': self.report_type_edit,
            'cargo': self.cargo_edit,
            'receiver': self.receiver_edit
        }
        
        for field_name, widget in field_widgets.items():
            entries = self._history.get_history(field_name)
            widget.clear()
            widget.addItems(entries)
            widget.setCurrentText("")  # Start with empty text

    def _save_history(self):
        """Save current field values to history."""
        data = {
            'port': self.port_edit.currentText(),
            'terminal': self.terminal_edit.currentText(),
            'mmc_no': self.mmc_edit.currentText(),
            'report_type': self.report_type_edit.currentText(),
            'cargo': self.cargo_edit.currentText(),
            'receiver': self.receiver_edit.currentText()
        }
        self._history.save_all(data)
        
        # Refresh combobox items to reflect new MRU order
        self._load_history()
        
        # Restore current values after refresh
        self.port_edit.setCurrentText(data['port'])
        self.terminal_edit.setCurrentText(data['terminal'])
        self.mmc_edit.setCurrentText(data['mmc_no'])
        self.report_type_edit.setCurrentText(data['report_type'])
        self.cargo_edit.setCurrentText(data['cargo'])
        self.receiver_edit.setCurrentText(data['receiver'])

    def _on_generate_clicked(self):
        """Emit signal for report generation."""
        self._save_history()
        self.request_generate_total.emit()

    def update_drafts(self, fwd: float, aft: float):
        """Update read-only draft displays related to the current voyage."""
        self.draft_fwd_edit.setText(f"{fwd:.2f}")
        self.draft_aft_edit.setText(f"{aft:.2f}")

    def get_report_data(self) -> dict:
        """Retrieve all data input from this widget."""
        return {
            'port': self.port_edit.currentText(),
            'terminal': self.terminal_edit.currentText(),
            'mmc_no': self.mmc_edit.currentText(),
            'report_type': self.report_type_edit.currentText(),
            'cargo': self.cargo_edit.currentText(),
            'receiver': self.receiver_edit.currentText(),
            'draft_fwd': self.draft_fwd_edit.text(),
            'draft_aft': self.draft_aft_edit.text(),
            'date': self.date_edit.date().toString("dd-MM-yyyy"),
            'remarks': self.remarks_edit.toPlainText(),
            'slop_label': self.slop_label_edit.text() or 'SLOP'
        }

    def _on_generate_selected_clicked(self):
        """Emit signal for selected parcels report generation."""
        self._save_history()
        self.request_generate_selected.emit()

    def _on_generate_stowage_clicked(self):
        """Emit signal for stowage plan report generation."""
        self._save_history()
        self.request_generate_stowage.emit()

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

