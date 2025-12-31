"""
Discrepancy Widget - Compare ship and shore (B/L) figures.
Displays parcel cards with calculated discrepancies for Loading and Discharging operations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QGroupBox, QScrollArea, QFrame, QGridLayout, QSizePolicy, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDoubleValidator, QAction

from typing import Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from models import Voyage, Parcel


class ParcelDiscrepancyCard(QFrame):
    """
    Card displaying discrepancy calculations for a single parcel.
    
    Includes:
    - Header: Parcel Name - Receiver
    - B/L Figure (editable input)
    - Ship Figure W/O VEF (from MT AIR)
    - All calculated differences
    """
    
    bl_figure_changed = pyqtSignal(str, float)  # parcel_id, value
    protest_requested = pyqtSignal(str, str)  # parcel_id, operation_type ("loading" or "discharging")
    
    def __init__(self, parcel: 'Parcel', ship_figure: float, vef: float, parent=None):
        super().__init__(parent)
        self.parcel = parcel
        self.ship_figure = ship_figure  # MT AIR total for this parcel
        self.vef = vef
        self.bl_figure = 0.0
        self.operation_type = "loading"  # Default for Loading OPS cards
        
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        self.setMinimumWidth(320)
        self.setMaximumWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self._init_ui()
    
    def _show_context_menu(self, pos):
        """Show context menu with Protest option."""
        menu = QMenu(self)
        protest_action = QAction("📋 Protest", self)
        protest_action.triggered.connect(lambda: self.protest_requested.emit(self.parcel.id, self.operation_type))
        menu.addAction(protest_action)
        menu.exec(self.mapToGlobal(pos))
    
    def _get_contrast_color(self, hex_color: str) -> str:
        """Get contrasting text color based on background brightness."""
        c = QColor(hex_color)
        lum = 0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF()
        return "#000000" if lum > 0.5 else "#ffffff"
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Get parcel color
        color = self.parcel.color or "#3B82F6"
        text_color = self._get_contrast_color(color)
        
        # Header: Parcel Name - Receiver
        header_text = f"{self.parcel.name}"
        if self.parcel.receiver:
            header_text += f" - {self.parcel.receiver}"
        
        header = QLabel(header_text)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"""
            background-color: {color}; 
            color: {text_color}; 
            font-weight: bold; 
            font-size: 10pt;
            padding: 8px;
            border-bottom: 1px solid #333;
        """)
        layout.addWidget(header)
        
        # Secondary header: Gross Metric Tons (in air)
        sub_header = QLabel("Gross Metric Tons (in air)")
        sub_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_header.setStyleSheet("""
            background-color: #e0e0e0; 
            color: #333; 
            font-weight: bold;
            font-size: 9pt;
            padding: 4px;
            border-bottom: 1px solid #999;
        """)
        layout.addWidget(sub_header)
        
        # Data grid
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setSpacing(2)
        
        row = 0
        
        # Row styling
        label_style = "font-size: 9pt; padding: 3px;"
        value_style = "font-size: 9pt; font-weight: bold; padding: 3px; text-align: right;"
        
        # B/L Figure (Input)
        lbl = QLabel("B/L Figure")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        
        self.bl_input = QLineEdit()
        self.bl_input.setValidator(QDoubleValidator(0, 999999.999, 3))
        self.bl_input.setPlaceholderText("0.000")
        self.bl_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.bl_input.setStyleSheet("font-size: 9pt; font-weight: bold; padding: 3px;")
        self.bl_input.textChanged.connect(self._on_bl_changed)
        self.bl_input.editingFinished.connect(self._format_bl_input)
        grid.addWidget(self.bl_input, row, 1)
        row += 1
        
        # Ship Figure W/O VEF
        lbl = QLabel("Ship Figure W/O VEF")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        self.ship_wo_vef_label = QLabel(f"{self.ship_figure:.3f}")
        self.ship_wo_vef_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.ship_wo_vef_label.setStyleSheet(value_style)
        grid.addWidget(self.ship_wo_vef_label, row, 1)
        row += 1
        
        # Quantity Difference W/O VEF
        lbl = QLabel("Quantity Difference W/O VEF")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        self.diff_wo_vef_label = QLabel("0.000")
        self.diff_wo_vef_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.diff_wo_vef_label.setStyleSheet(value_style)
        grid.addWidget(self.diff_wo_vef_label, row, 1)
        row += 1
        
        # Difference W/O VEF ‰
        lbl = QLabel("Difference W/O VEF ‰")
        lbl.setStyleSheet(label_style + "color: #dc2626;")  # Red text
        grid.addWidget(lbl, row, 0)
        self.diff_pct_wo_vef_label = QLabel("0.000")
        self.diff_pct_wo_vef_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.diff_pct_wo_vef_label.setStyleSheet(value_style + "color: #dc2626;")
        grid.addWidget(self.diff_pct_wo_vef_label, row, 1)
        row += 1
        
        # Ship Figure with VEF
        lbl = QLabel("Ship Figure with VEF")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        ship_with_vef = self.ship_figure * self.vef
        self.ship_with_vef_label = QLabel(f"{ship_with_vef:.3f}")
        self.ship_with_vef_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.ship_with_vef_label.setStyleSheet(value_style)
        grid.addWidget(self.ship_with_vef_label, row, 1)
        row += 1
        
        # Quantity Difference with VEF
        lbl = QLabel("Quantity Difference with VEF")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        self.diff_with_vef_label = QLabel("0.000")
        self.diff_with_vef_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.diff_with_vef_label.setStyleSheet(value_style)
        grid.addWidget(self.diff_with_vef_label, row, 1)
        row += 1
        
        # Difference with VEF ‰
        lbl = QLabel("Difference with VEF ‰")
        lbl.setStyleSheet(label_style + "color: #dc2626;")
        grid.addWidget(lbl, row, 0)
        self.diff_pct_with_vef_label = QLabel("0.000")
        self.diff_pct_with_vef_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.diff_pct_with_vef_label.setStyleSheet(value_style + "color: #dc2626;")
        grid.addWidget(self.diff_pct_with_vef_label, row, 1)
        
        layout.addWidget(grid_widget)
    
    def _on_bl_changed(self, text: str):
        """Handle B/L figure input change."""
        try:
            self.bl_figure = float(text) if text else 0.0
        except ValueError:
            self.bl_figure = 0.0
        
        self._recalculate()
        self.bl_figure_changed.emit(self.parcel.id, self.bl_figure)
    
    def _format_bl_input(self):
        """Format B/L input to 3 decimal places when editing finished."""
        text = self.bl_input.text()
        if text:
            try:
                value = float(text)
                self.bl_input.setText(f"{value:.3f}")
            except ValueError:
                pass
    
    def _recalculate(self):
        """Recalculate all discrepancy values."""
        bl = self.bl_figure
        ship_wo = self.ship_figure
        ship_with = ship_wo * self.vef
        
        # Differences
        diff_wo = bl - ship_wo
        diff_with = bl - ship_with
        
        # Per mille (‰) = (diff / bl) * 1000
        diff_pct_wo = (diff_wo / bl) * 1000 if bl != 0 else 0.0
        diff_pct_with = (diff_with / bl) * 1000 if bl != 0 else 0.0
        
        # Update labels
        self.diff_wo_vef_label.setText(f"{diff_wo:.3f}")
        self.diff_pct_wo_vef_label.setText(f"{diff_pct_wo:.3f}")
        self.ship_with_vef_label.setText(f"{ship_with:.3f}")
        self.diff_with_vef_label.setText(f"{diff_with:.3f}")
        self.diff_pct_with_vef_label.setText(f"{diff_pct_with:.3f}")
        
        # Apply color coding to Difference with VEF ‰ based on absolute value
        # |value| >= 3: RED, 2-3: ORANGE, 0-2: GREEN
        abs_diff = abs(diff_pct_with)
        if abs_diff >= 3:
            color = "#dc2626"  # Red - Critical
        elif abs_diff >= 2:
            color = "#f97316"  # Orange - Warning
        else:
            color = "#22c55e"  # Green - Good
        
        # Apply styling to the Difference with VEF ‰ label
        self.diff_pct_with_vef_label.setStyleSheet(
            f"font-size: 9pt; font-weight: bold; padding: 3px; text-align: right; color: {color};"
        )
    
    def update_ship_figure(self, ship_figure: float, vef: float):
        """Update ship figure and VEF, then recalculate."""
        self.ship_figure = ship_figure
        self.vef = vef
        self.ship_wo_vef_label.setText(f"{ship_figure:.3f}")
        self._recalculate()
    
    def set_bl_figure(self, value: float):
        """Set B/L figure programmatically."""
        self.bl_input.setText(f"{value:.3f}")


class DischargingDiscrepancyCard(QFrame):
    """
    Card displaying discharging discrepancy calculations for a single parcel.
    
    12-row layout:
    1. B/L Figure (from Loading card)
    2. Ship Figure Loading Port (user input)
    3. Ship Arrival Figure (from MT AIR)
    4. Ship Arrival Figure with VEF (#3 / VEF)
    5. Transit Loss (#2 - #3)
    6. Arrival-BL diff W/O VEF ‰
    7. Arrival-BL diff VEF ‰
    8. Outturn Figure (user input)
    9. Outturn-BL Diff
    10. Outturn-BL Diff ‰
    11. Outturn-Ship Arrival Diff (VEF)
    12. Outturn-Ship Arrival Diff ‰
    """
    
    ship_loading_changed = pyqtSignal(str, float)  # parcel_id, value
    outturn_changed = pyqtSignal(str, float)  # parcel_id, value
    protest_requested = pyqtSignal(str, str)  # parcel_id, operation_type
    
    def __init__(self, parcel: 'Parcel', ship_arrival_figure: float, vef: float, bl_figure: float = 0.0, parent=None):
        super().__init__(parent)
        self.parcel = parcel
        self.ship_arrival = ship_arrival_figure  # MT AIR total
        self.vef = vef
        self.bl_figure = bl_figure  # From Loading card
        self.ship_loading = 0.0  # User input
        self.outturn = 0.0  # User input
        self.operation_type = "discharging"  # For Discharging OPS cards
        
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        self.setMinimumWidth(320)
        self.setMaximumWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self._init_ui()
    
    def _show_context_menu(self, pos):
        """Show context menu with Protest option."""
        menu = QMenu(self)
        protest_action = QAction("📋 Protest", self)
        protest_action.triggered.connect(lambda: self.protest_requested.emit(self.parcel.id, self.operation_type))
        menu.addAction(protest_action)
        menu.exec(self.mapToGlobal(pos))
    
    def _get_contrast_color(self, hex_color: str) -> str:
        """Get contrasting text color based on background brightness."""
        c = QColor(hex_color)
        lum = 0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF()
        return "#000000" if lum > 0.5 else "#ffffff"
    
    def _apply_permille_color(self, label: QLabel, value: float):
        """Apply color coding to permille labels."""
        abs_val = abs(value)
        if abs_val >= 3:
            color = "#dc2626"  # Red
        elif abs_val >= 2:
            color = "#f97316"  # Orange
        else:
            color = "#22c55e"  # Green
        label.setStyleSheet(f"font-size: 9pt; font-weight: bold; padding: 3px; color: {color};")
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Get parcel color
        color = self.parcel.color or "#3B82F6"
        text_color = self._get_contrast_color(color)
        
        # Header
        header_text = f"{self.parcel.name}"
        if self.parcel.receiver:
            header_text += f" - {self.parcel.receiver}"
        
        header = QLabel(header_text)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"""
            background-color: {color}; 
            color: {text_color}; 
            font-weight: bold; 
            font-size: 10pt;
            padding: 6px;
            border-bottom: 1px solid #333;
        """)
        layout.addWidget(header)
        
        # Sub header
        sub_header = QLabel("DISCHARGING - Gross MT (air)")
        sub_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_header.setStyleSheet("""
            background-color: #fee2e2; 
            color: #991b1b; 
            font-weight: bold;
            font-size: 9pt;
            padding: 3px;
            border-bottom: 1px solid #999;
        """)
        layout.addWidget(sub_header)
        
        # Data grid
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setSpacing(2)
        
        row = 0
        label_style = "font-size: 8pt; padding: 2px;"
        value_style = "font-size: 8pt; font-weight: bold; padding: 2px;"
        
        # Row 1: B/L Figure (from Loading)
        lbl = QLabel("1. B/L Figure")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        self.bl_label = QLabel(f"{self.bl_figure:.3f}")
        self.bl_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.bl_label.setStyleSheet(value_style)
        grid.addWidget(self.bl_label, row, 1)
        row += 1
        
        # Row 2: Ship Figure Loading Port (input)
        lbl = QLabel("2. Ship Figure Loading Port (W VEF)")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        self.ship_loading_input = QLineEdit()
        self.ship_loading_input.setValidator(QDoubleValidator(0, 999999.999, 3))
        self.ship_loading_input.setPlaceholderText("0.000")
        self.ship_loading_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.ship_loading_input.setStyleSheet("font-size: 8pt; font-weight: bold; padding: 2px;")
        self.ship_loading_input.textChanged.connect(self._on_ship_loading_changed)
        self.ship_loading_input.editingFinished.connect(self._format_ship_loading_input)
        grid.addWidget(self.ship_loading_input, row, 1)
        row += 1
        
        # Row 3: Ship Arrival Figure
        lbl = QLabel("3. Ship Arrival Figure")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        self.ship_arrival_label = QLabel(f"{self.ship_arrival:.3f}")
        self.ship_arrival_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.ship_arrival_label.setStyleSheet(value_style)
        grid.addWidget(self.ship_arrival_label, row, 1)
        row += 1
        
        # Row 4: Ship Arrival with VEF
        lbl = QLabel("4. Ship Arrival with VEF")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        self.ship_arrival_vef_label = QLabel("0.000")
        self.ship_arrival_vef_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.ship_arrival_vef_label.setStyleSheet(value_style)
        grid.addWidget(self.ship_arrival_vef_label, row, 1)
        row += 1
        
        # Row 5: Transit Loss
        lbl = QLabel("5. Transit Loss")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        self.transit_loss_label = QLabel("0.000")
        self.transit_loss_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.transit_loss_label.setStyleSheet(value_style)
        grid.addWidget(self.transit_loss_label, row, 1)
        row += 1
        
        # Row 6: Arrival-BL diff W/O VEF ‰
        lbl = QLabel("6. Arrival-BL diff W/O VEF ‰")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        self.arrival_bl_wo_vef_label = QLabel("0.000")
        self.arrival_bl_wo_vef_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.arrival_bl_wo_vef_label, row, 1)
        row += 1
        
        # Row 7: Arrival-BL diff VEF ‰
        lbl = QLabel("7. Arrival-BL diff VEF ‰")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        self.arrival_bl_vef_label = QLabel("0.000")
        self.arrival_bl_vef_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.arrival_bl_vef_label, row, 1)
        row += 1
        
        # Row 8: Outturn Figure (input)
        lbl = QLabel("8. OUTTURN FIGURE")
        lbl.setStyleSheet(label_style + "font-weight: bold;")
        grid.addWidget(lbl, row, 0)
        self.outturn_input = QLineEdit()
        self.outturn_input.setValidator(QDoubleValidator(0, 999999.999, 3))
        self.outturn_input.setPlaceholderText("0.000")
        self.outturn_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.outturn_input.setStyleSheet("font-size: 8pt; font-weight: bold; padding: 2px;")
        self.outturn_input.textChanged.connect(self._on_outturn_changed)
        self.outturn_input.editingFinished.connect(self._format_outturn_input)
        grid.addWidget(self.outturn_input, row, 1)
        row += 1
        
        # Row 9: Outturn-BL Diff
        lbl = QLabel("9. OUTTURN-BL DIFF")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        self.outturn_bl_diff_label = QLabel("0.000")
        self.outturn_bl_diff_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.outturn_bl_diff_label.setStyleSheet(value_style)
        grid.addWidget(self.outturn_bl_diff_label, row, 1)
        row += 1
        
        # Row 10: Outturn-BL Diff ‰
        lbl = QLabel("10. OUTTURN-BL DIFF ‰")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        self.outturn_bl_diff_pct_label = QLabel("0.000")
        self.outturn_bl_diff_pct_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.outturn_bl_diff_pct_label, row, 1)
        row += 1
        
        # Row 11: Outturn-Ship Arrival Diff (VEF)
        lbl = QLabel("11. OUTTURN-SHIP ARRIVAL DIFF")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        self.outturn_arrival_diff_label = QLabel("0.000")
        self.outturn_arrival_diff_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.outturn_arrival_diff_label.setStyleSheet(value_style)
        grid.addWidget(self.outturn_arrival_diff_label, row, 1)
        row += 1
        
        # Row 12: Outturn-Ship Arrival Diff ‰
        lbl = QLabel("12. OUTTURN-ARRIVAL DIFF ‰")
        lbl.setStyleSheet(label_style)
        grid.addWidget(lbl, row, 0)
        self.outturn_arrival_diff_pct_label = QLabel("0.000")
        self.outturn_arrival_diff_pct_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.outturn_arrival_diff_pct_label, row, 1)
        
        layout.addWidget(grid_widget)
        self._recalculate()
    
    def _on_ship_loading_changed(self, text: str):
        """Handle Ship Figure Loading Port input change."""
        try:
            self.ship_loading = float(text) if text else 0.0
        except ValueError:
            self.ship_loading = 0.0
        self._recalculate()
        self.ship_loading_changed.emit(self.parcel.id, self.ship_loading)
    
    def _on_outturn_changed(self, text: str):
        """Handle Outturn Figure input change."""
        try:
            self.outturn = float(text) if text else 0.0
        except ValueError:
            self.outturn = 0.0
        self._recalculate()
        self.outturn_changed.emit(self.parcel.id, self.outturn)
    
    def _format_ship_loading_input(self):
        """Format Ship Loading input to 3 decimal places when editing finished."""
        text = self.ship_loading_input.text()
        if text:
            try:
                value = float(text)
                self.ship_loading_input.setText(f"{value:.3f}")
            except ValueError:
                pass
    
    def _format_outturn_input(self):
        """Format Outturn input to 3 decimal places when editing finished."""
        text = self.outturn_input.text()
        if text:
            try:
                value = float(text)
                self.outturn_input.setText(f"{value:.3f}")
            except ValueError:
                pass
    
    def _recalculate(self):
        """Recalculate all discharging discrepancy values."""
        bl = self.bl_figure                    # Row 1
        ship_load = self.ship_loading          # Row 2
        ship_arrival = self.ship_arrival       # Row 3
        vef = self.vef if self.vef != 0 else 1.0
        
        # Row 4: Ship Arrival with VEF = #3 / VEF
        ship_arrival_vef = ship_arrival / vef
        
        # Row 5: Transit Loss = #3 - #2 (Ship Arrival - Ship Loading)
        transit_loss = ship_arrival - ship_load
        
        # Row 6: Arrival-BL diff W/O VEF ‰ = ((#1 - #3) / #1) * 1000
        arrival_bl_wo_pct = ((bl - ship_arrival) / bl) * 1000 if bl != 0 else 0.0
        
        # Row 7: Arrival-BL diff VEF ‰ = ((#1 - #4) / #1) * 1000
        arrival_bl_vef_pct = ((bl - ship_arrival_vef) / bl) * 1000 if bl != 0 else 0.0
        
        outturn = self.outturn                 # Row 8
        
        # Row 9: Outturn-BL Diff = #1 - #8
        outturn_bl_diff = bl - outturn
        
        # Row 10: Outturn-BL Diff ‰ = (#9 / #1) * 1000
        outturn_bl_diff_pct = (outturn_bl_diff / bl) * 1000 if bl != 0 else 0.0
        
        # Row 11: Outturn-Ship Arrival Diff (VEF) = #8 - #4
        outturn_arrival_diff = outturn - ship_arrival_vef
        
        # Row 12: Outturn-Ship Arrival Diff ‰ = (#11 / #4) * 1000
        outturn_arrival_diff_pct = (outturn_arrival_diff / ship_arrival_vef) * 1000 if ship_arrival_vef != 0 else 0.0
        
        # Update labels
        self.ship_arrival_vef_label.setText(f"{ship_arrival_vef:.3f}")
        self.transit_loss_label.setText(f"{transit_loss:.3f}")
        self.arrival_bl_wo_vef_label.setText(f"{arrival_bl_wo_pct:.3f}")
        self.arrival_bl_vef_label.setText(f"{arrival_bl_vef_pct:.3f}")
        self.outturn_bl_diff_label.setText(f"{outturn_bl_diff:.3f}")
        self.outturn_bl_diff_pct_label.setText(f"{outturn_bl_diff_pct:.3f}")
        self.outturn_arrival_diff_label.setText(f"{outturn_arrival_diff:.3f}")
        self.outturn_arrival_diff_pct_label.setText(f"{outturn_arrival_diff_pct:.3f}")
        
        # Apply color coding to ‰ labels
        self._apply_permille_color(self.arrival_bl_wo_vef_label, arrival_bl_wo_pct)
        self._apply_permille_color(self.arrival_bl_vef_label, arrival_bl_vef_pct)
        self._apply_permille_color(self.outturn_bl_diff_pct_label, outturn_bl_diff_pct)
        self._apply_permille_color(self.outturn_arrival_diff_pct_label, outturn_arrival_diff_pct)
    
    def update_bl_figure(self, bl_figure: float):
        """Update B/L figure from Loading card."""
        self.bl_figure = bl_figure
        self.bl_label.setText(f"{bl_figure:.3f}")
        self._recalculate()
    
    def update_ship_arrival(self, ship_arrival: float, vef: float):
        """Update ship arrival figure and VEF."""
        self.ship_arrival = ship_arrival
        self.vef = vef
        self.ship_arrival_label.setText(f"{ship_arrival:.3f}")
        self._recalculate()
    
    def set_ship_loading(self, value: float):
        """Set Ship Figure Loading Port programmatically."""
        self.ship_loading_input.setText(f"{value:.3f}")
    
    def set_outturn(self, value: float):
        """Set Outturn Figure programmatically."""
        self.outturn_input.setText(f"{value:.3f}")

class DiscrepancyWidget(QWidget):
    """
    Main widget for Discrepancy/Protests tab.
    Contains Loading Ops and Discharging Ops sections.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.voyage: Optional['Voyage'] = None
        self.loading_cards: Dict[str, ParcelDiscrepancyCard] = {}
        self.discharging_cards: Dict[str, DischargingDiscrepancyCard] = {}
        
        self._init_ui()
    
    def _init_ui(self):
        from PyQt6.QtWidgets import QSplitter
        from PyQt6.QtCore import QSettings
        import os
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)
        
        # Create splitter for resizable sections
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        
        # Loading Ops Section
        loading_group = QGroupBox("⬇️ LOADING OPS")
        loading_group.setStyleSheet("""
            QGroupBox {
                font-size: 12pt;
                font-weight: bold;
                border: 2px solid #22c55e;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #22c55e;
            }
        """)
        loading_layout = QVBoxLayout(loading_group)
        
        self.loading_scroll = QScrollArea()
        self.loading_scroll.setWidgetResizable(True)
        self.loading_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.loading_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.loading_container = QWidget()
        self.loading_flow = QHBoxLayout(self.loading_container)
        self.loading_flow.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.loading_flow.setSpacing(15)
        self.loading_flow.addStretch()
        
        self.loading_scroll.setWidget(self.loading_container)
        loading_layout.addWidget(self.loading_scroll)
        self.splitter.addWidget(loading_group)
        
        # Discharging Ops Section
        discharging_group = QGroupBox("⬆️ DISCHARGING OPS")
        discharging_group.setStyleSheet("""
            QGroupBox {
                font-size: 12pt;
                font-weight: bold;
                border: 2px solid #ef4444;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #ef4444;
            }
        """)
        discharging_layout = QVBoxLayout(discharging_group)
        
        self.discharging_scroll = QScrollArea()
        self.discharging_scroll.setWidgetResizable(True)
        self.discharging_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.discharging_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.discharging_container = QWidget()
        self.discharging_flow = QHBoxLayout(self.discharging_container)
        self.discharging_flow.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.discharging_flow.setSpacing(15)
        self.discharging_flow.addStretch()
        
        self.discharging_scroll.setWidget(self.discharging_container)
        discharging_layout.addWidget(self.discharging_scroll)
        self.splitter.addWidget(discharging_group)
        
        # Add splitter to layout
        layout.addWidget(self.splitter)
        
        # Connect splitter moved signal to save state
        self.splitter.splitterMoved.connect(self._save_splitter_state)
        
        # Restore saved splitter state
        self._restore_splitter_state()
    
    def _get_settings_path(self) -> str:
        """Get path to VoyageExplorer.ini settings file."""
        import os
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                           'data', 'config', 'VoyageExplorer.ini')
    
    def _save_splitter_state(self):
        """Save splitter state to VoyageExplorer.ini."""
        from PyQt6.QtCore import QSettings
        settings = QSettings(self._get_settings_path(), QSettings.Format.IniFormat)
        settings.setValue("discrepancy_splitter_state", self.splitter.saveState())
    
    def _restore_splitter_state(self):
        """Restore splitter state from VoyageExplorer.ini."""
        from PyQt6.QtCore import QSettings
        settings = QSettings(self._get_settings_path(), QSettings.Format.IniFormat)
        state = settings.value("discrepancy_splitter_state")
        if state:
            self.splitter.restoreState(state)
    
    def set_voyage(self, voyage: 'Voyage'):
        """Set the voyage and refresh parcel cards."""
        self.voyage = voyage
        self._refresh_cards()
    
    def _get_parcel_mt_air(self, parcel_id: str) -> float:
        """Calculate total MT AIR for a parcel from tank readings."""
        if not self.voyage:
            return 0.0
        
        total = 0.0
        for reading in self.voyage.tank_readings.values():
            if reading.parcel_id == parcel_id:
                total += reading.mt_air if reading.mt_air else 0.0
        return total
    
    def _clear_layout(self, layout: QHBoxLayout):
        """Clear all widgets from layout except stretch."""
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
    
    def _refresh_cards(self):
        """Refresh parcel cards for both sections."""
        self._clear_layout(self.loading_flow)
        self._clear_layout(self.discharging_flow)
        self.loading_cards.clear()
        self.discharging_cards.clear()
        
        if not self.voyage or not self.voyage.parcels:
            return
        
        vef = self.voyage.vef if self.voyage.vef else 1.0
        
        for parcel in self.voyage.parcels:
            ship_figure = self._get_parcel_mt_air(parcel.id)
            
            # Create card for Loading section
            loading_card = ParcelDiscrepancyCard(parcel, ship_figure, vef)
            # Load saved B/L value
            if parcel.bl_loading:
                loading_card.set_bl_figure(parcel.bl_loading)
            # Connect signal to save B/L value and update Discharging card
            loading_card.bl_figure_changed.connect(self._on_loading_bl_changed)
            self.loading_flow.insertWidget(self.loading_flow.count() - 1, loading_card)
            self.loading_cards[parcel.id] = loading_card
            
            # Create card for Discharging section (new 12-row layout)
            bl_from_loading = parcel.bl_loading if parcel.bl_loading else 0.0
            discharging_card = DischargingDiscrepancyCard(parcel, ship_figure, vef, bl_from_loading)
            # Load saved values
            if parcel.ship_figure_loading:
                discharging_card.set_ship_loading(parcel.ship_figure_loading)
            if parcel.outturn_figure:
                discharging_card.set_outturn(parcel.outturn_figure)
            # Connect signals to save values
            discharging_card.ship_loading_changed.connect(self._on_ship_loading_changed)
            discharging_card.outturn_changed.connect(self._on_outturn_changed)
            self.discharging_flow.insertWidget(self.discharging_flow.count() - 1, discharging_card)
            self.discharging_cards[parcel.id] = discharging_card
    
    def _on_loading_bl_changed(self, parcel_id: str, bl_value: float):
        """Handle B/L figure change in Loading section - save to parcel and update Discharging."""
        if not self.voyage:
            return
        for parcel in self.voyage.parcels:
            if parcel.id == parcel_id:
                parcel.bl_loading = bl_value
                break
        
        # Update corresponding Discharging card's B/L figure
        if parcel_id in self.discharging_cards:
            self.discharging_cards[parcel_id].update_bl_figure(bl_value)
    
    def _on_ship_loading_changed(self, parcel_id: str, value: float):
        """Handle Ship Figure Loading Port change - save to parcel."""
        if not self.voyage:
            return
        for parcel in self.voyage.parcels:
            if parcel.id == parcel_id:
                parcel.ship_figure_loading = value
                break
    
    def _on_outturn_changed(self, parcel_id: str, value: float):
        """Handle Outturn Figure change - save to parcel."""
        if not self.voyage:
            return
        for parcel in self.voyage.parcels:
            if parcel.id == parcel_id:
                parcel.outturn_figure = value
                break
    
    def refresh_data(self):
        """Refresh ship figures from current voyage data."""
        if not self.voyage:
            return
        
        vef = self.voyage.vef if self.voyage.vef else 1.0
        
        for parcel in self.voyage.parcels:
            ship_figure = self._get_parcel_mt_air(parcel.id)
            
            if parcel.id in self.loading_cards:
                self.loading_cards[parcel.id].update_ship_figure(ship_figure, vef)
            
            if parcel.id in self.discharging_cards:
                self.discharging_cards[parcel.id].update_ship_arrival(ship_figure, vef)
