"""
Discrepancy Widget - Compare ship and shore (B/L) figures.
Displays parcel cards with calculated discrepancies for Loading and Discharging operations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QGroupBox, QScrollArea, QFrame, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDoubleValidator

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
    
    def __init__(self, parcel: 'Parcel', ship_figure: float, vef: float, parent=None):
        super().__init__(parent)
        self.parcel = parcel
        self.ship_figure = ship_figure  # MT AIR total for this parcel
        self.vef = vef
        self.bl_figure = 0.0
        
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        self.setMinimumWidth(280)
        self.setMaximumWidth(350)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        
        self._init_ui()
    
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
        self.bl_input.setText(f"{value:.3f}" if value else "")


class DiscrepancyWidget(QWidget):
    """
    Main widget for Discrepancy/Protests tab.
    Contains Loading Ops and Discharging Ops sections.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.voyage: Optional['Voyage'] = None
        self.loading_cards: Dict[str, ParcelDiscrepancyCard] = {}
        self.discharging_cards: Dict[str, ParcelDiscrepancyCard] = {}
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Loading Ops Section
        loading_group = QGroupBox("⬆️ LOADING OPS")
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
        self.loading_scroll.setMinimumHeight(280)
        
        self.loading_container = QWidget()
        self.loading_flow = QHBoxLayout(self.loading_container)
        self.loading_flow.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.loading_flow.setSpacing(15)
        self.loading_flow.addStretch()
        
        self.loading_scroll.setWidget(self.loading_container)
        loading_layout.addWidget(self.loading_scroll)
        layout.addWidget(loading_group)
        
        # Discharging Ops Section
        discharging_group = QGroupBox("⬇️ DISCHARGING OPS")
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
        self.discharging_scroll.setMinimumHeight(280)
        
        self.discharging_container = QWidget()
        self.discharging_flow = QHBoxLayout(self.discharging_container)
        self.discharging_flow.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.discharging_flow.setSpacing(15)
        self.discharging_flow.addStretch()
        
        self.discharging_scroll.setWidget(self.discharging_container)
        discharging_layout.addWidget(self.discharging_scroll)
        layout.addWidget(discharging_group)
        
        layout.addStretch()
    
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
            # Connect signal to save B/L value back to parcel
            loading_card.bl_figure_changed.connect(self._on_loading_bl_changed)
            self.loading_flow.insertWidget(self.loading_flow.count() - 1, loading_card)
            self.loading_cards[parcel.id] = loading_card
            
            # Create card for Discharging section
            discharging_card = ParcelDiscrepancyCard(parcel, ship_figure, vef)
            # Load saved B/L value
            if parcel.bl_discharging:
                discharging_card.set_bl_figure(parcel.bl_discharging)
            # Connect signal to save B/L value back to parcel
            discharging_card.bl_figure_changed.connect(self._on_discharging_bl_changed)
            self.discharging_flow.insertWidget(self.discharging_flow.count() - 1, discharging_card)
            self.discharging_cards[parcel.id] = discharging_card
    
    def _on_loading_bl_changed(self, parcel_id: str, bl_value: float):
        """Handle B/L figure change in Loading section - save to parcel."""
        if not self.voyage:
            return
        for parcel in self.voyage.parcels:
            if parcel.id == parcel_id:
                parcel.bl_loading = bl_value
                break
    
    def _on_discharging_bl_changed(self, parcel_id: str, bl_value: float):
        """Handle B/L figure change in Discharging section - save to parcel."""
        if not self.voyage:
            return
        for parcel in self.voyage.parcels:
            if parcel.id == parcel_id:
                parcel.bl_discharging = bl_value
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
                self.discharging_cards[parcel.id].update_ship_figure(ship_figure, vef)

