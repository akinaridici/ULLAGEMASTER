"""
Cargo legend widget for displaying and dragging cargos.
Ported from STOWAGEMASTER with simplifications.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea,
    QFrame, QSizePolicy, QMenu, QPushButton, QDialog,
    QFormLayout, QLineEdit, QDoubleSpinBox, QDialogButtonBox,
    QColorDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QMimeData, QByteArray, pyqtSignal
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QColor, QFont
import json
from typing import Optional, List

from models.stowage_plan import StowageCargo, StowagePlan, Receiver


# Vibrant cargo color palette
CARGO_COLORS = [
    "#FF6B6B",  # Red
    "#4ECDC4",  # Teal
    "#45B7D1",  # Blue
    "#96CEB4",  # Green
    "#FFEAA7",  # Yellow
    "#DDA0DD",  # Plum
    "#F7DC6F",  # Gold
    "#BB8FCE",  # Purple
    "#85C1E9",  # Light Blue
    "#F8B500",  # Orange
]


class DraggableCargoCard(QFrame):
    """Draggable card representing a cargo type with remaining quantity display"""
    
    def __init__(self, cargo: StowageCargo, color: str, loaded_qty: float = 0.0, parent=None, legend_widget=None):
        super().__init__(parent)
        self.cargo = cargo
        self.legend_widget = legend_widget
        self.color = color
        self.loaded_qty = loaded_qty
        
        self.setMinimumSize(120, 70)
        self.setMaximumSize(160, 90)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(2)
        self.setStyleSheet(f"background-color: {self.color}; border: 2px solid #333; border-radius: 5px;")
        self.setAcceptDrops(False)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setMouseTracking(True)
        
        self._init_ui()

    def _apply_tint(self, hex_color: str) -> str:
        """Apply 50% blend with dark background to match Ullage Table."""
        if not hex_color or hex_color.upper() == "#E0E0E0":
            return hex_color
        
        c = QColor(hex_color)
        # Blend with #0f172a (15, 23, 42) with 50% alpha
        r = int(c.red() * 0.50 + 15 * 0.50)
        g = int(c.green() * 0.50 + 23 * 0.50)
        b = int(c.blue() * 0.50 + 42 * 0.50)
        
        return QColor(r, g, b).name()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(2)
        
        text_color = self._get_contrast_color(self.color)
        
        # Cargo type name
        name_label = QLabel(self.cargo.cargo_type)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet(f"color: {text_color}; font-weight: bold; font-size: 9pt;")
        name_label.setWordWrap(True)
        name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(name_label)
        
        # Receiver info
        receiver_label = QLabel(self.cargo.get_receiver_names())
        receiver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        receiver_label.setStyleSheet(f"color: {text_color}; font-size: 8pt;")
        receiver_label.setWordWrap(True)
        receiver_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(receiver_label)
        
        # Remaining quantity or "Tamamlandı"
        remaining = self.cargo.quantity - self.loaded_qty
        if remaining < -0.5:
             # Over-planned (Excess)
            excess = abs(remaining)
            qty_text = f"{excess:.0f} m³ fazla"
            qty_style = (
                "color: #fff; font-size: 9pt; font-weight: bold; "
                "background-color: #f59e0b; padding: 2px 4px; "  # Amber-500
                "border-radius: 3px;"
            )
        elif remaining <= 0.5:
            qty_text = "✓ Tamamlandı"
            qty_style = (
                "color: #fff; font-size: 9pt; font-weight: bold; "
                "background-color: #22c55e; padding: 2px 4px; "
                "border-radius: 3px;"
            )
        else:
            qty_text = f"{remaining:.0f} m³ kaldı"
            qty_style = (
                "color: #000; font-size: 9pt; font-weight: bold; "
                "background-color: rgba(255, 255, 255, 0.85); padding: 2px 4px; "
                "border-radius: 3px; border: 1px solid rgba(0, 0, 0, 0.2);"
            )
        
        qty_label = QLabel(qty_text)
        qty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qty_label.setStyleSheet(qty_style)
        qty_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(qty_label)
    
    def _get_contrast_color(self, hex_color: str) -> str:
        """Get contrasting text color based on background brightness"""
        c = QColor(hex_color)
        return "#000000" if c.lightness() > 140 else "#ffffff"
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position().toPoint()
            self.dragging = False
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        
        if not hasattr(self, 'drag_start_position'):
            super().mouseMoveEvent(event)
            return
        
        current_pos = event.position().toPoint()
        drag_distance = (current_pos - self.drag_start_position).manhattanLength()
        if drag_distance < 3:
            super().mouseMoveEvent(event)
            return
        
        if hasattr(self, 'dragging') and self.dragging:
            super().mouseMoveEvent(event)
            return
        
        self.dragging = True
        self._start_drag(event)
        self.dragging = False
        super().mouseMoveEvent(event)
    
    def _start_drag(self, event):
        drag = QDrag(self)
        mime_data = QMimeData()
        
        cargo_data = {
            "cargo_id": self.cargo.unique_id,
            "type": "cargo"
        }
        mime_data.setData("application/x-cargo-id", QByteArray(json.dumps(cargo_data).encode()))
        drag.setMimeData(mime_data)
        
        try:
            pixmap = self.grab()
        except:
            pixmap = QPixmap(self.size())
            pixmap.fill(QColor(self.color))
        
        drag.setPixmap(pixmap)
        hotspot = event.position().toPoint() - self.rect().topLeft()
        drag.setHotSpot(hotspot)
        
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        drag.exec(Qt.DropAction.MoveAction)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        
        if hasattr(self, 'drag_start_position'):
            delattr(self, 'drag_start_position')
    
    def contextMenuEvent(self, event):
        """Handle right-click context menu for color change."""
        from PyQt6.QtWidgets import QMenu, QColorDialog
        from PyQt6.QtGui import QColor
        
        # Find main window first (for proper dialog parenting)
        widget = self.parent()
        main_window = None
        while widget:
            if hasattr(widget, 'stowage_plan'):
                main_window = widget
                break
            widget = widget.parent()
        
        menu = QMenu(self)
        color_action = menu.addAction("🎨 Renk Değiştir")
        
        selected = menu.exec(event.globalPos())
        
        if selected == color_action:
            current_color = self.cargo.custom_color or self.color
            # Use main_window as parent for proper styling
            dialog_parent = main_window if main_window else self
            new_color = QColorDialog.getColor(QColor(current_color), dialog_parent, "Kargo Rengi Seç")
            
            if new_color.isValid():
                # Update cargo's custom color
                self.cargo.custom_color = new_color.name()
                
                # Trigger update via legend widget if available
                if self.legend_widget:
                    self.legend_widget.on_cargo_color_changed(self.cargo)
                elif main_window and hasattr(main_window, '_on_stowage_changed'):
                     # Fallback
                    main_window._on_stowage_changed()


class CargoInputDialog(QDialog):
    """Dialog for adding a new cargo"""
    
    def __init__(self, parent=None, color: str = "#4ECDC4"):
        super().__init__(parent)
        self.selected_color = color
        self.setWindowTitle("Kargo Ekle")
        self.setMinimumWidth(350)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Cargo type
        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText("örn: MOTORIN, FUEL OIL")
        form.addRow("Kargo Tipi:", self.type_edit)
        
        # Receiver
        self.receiver_edit = QLineEdit()
        self.receiver_edit.setPlaceholderText("örn: SHELL, TOTAL")
        form.addRow("Alıcı:", self.receiver_edit)
        
        # Quantity
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setDecimals(0)
        self.qty_spin.setRange(0, 100000)
        self.qty_spin.setSingleStep(100)
        self.qty_spin.setValue(1000)
        self.qty_spin.setSuffix(" m³")
        form.addRow("Miktar:", self.qty_spin)
        
        # Density
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setDecimals(4)
        self.density_spin.setRange(0.5, 1.5)
        self.density_spin.setSingleStep(0.0001)
        self.density_spin.setValue(0.8500)
        form.addRow("VAC Density:", self.density_spin)
        
        # Color
        color_row = QHBoxLayout()
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(30, 30)
        self._update_color_preview()
        color_row.addWidget(self.color_preview)
        
        color_btn = QPushButton("Renk Seç")
        color_btn.clicked.connect(self._choose_color)
        color_row.addWidget(color_btn)
        color_row.addStretch()
        form.addRow("Renk:", color_row)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _update_color_preview(self):
        self.color_preview.setStyleSheet(
            f"background-color: {self.selected_color}; border: 1px solid #475569; border-radius: 5px;"
        )
    
    def _choose_color(self):
        color = QColorDialog.getColor(QColor(self.selected_color), self)
        if color.isValid():
            self.selected_color = color.name()
            self._update_color_preview()
    
    def get_cargo(self) -> StowageCargo:
        receivers = []
        receiver_text = self.receiver_edit.text().strip()
        if receiver_text:
            receivers = [Receiver(name=receiver_text.upper())]
        
        return StowageCargo(
            cargo_type=self.type_edit.text().strip().upper() or "UNKNOWN",
            quantity=self.qty_spin.value(),
            receivers=receivers,
            density=self.density_spin.value(),
            custom_color=self.selected_color,
        )


class CargoLegendWidget(QWidget):
    """Widget displaying draggable cargo cards (no buttons - input from table only)"""
    
    cargos_changed = pyqtSignal()
    cargo_color_changed = pyqtSignal()  # New signal
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stowage_plan: Optional[StowagePlan] = None
        self._color_index = 0
        self._init_ui()

    def on_cargo_color_changed(self, cargo):
        """Handle cargo color change from card."""
        self._refresh_cards()
        self.cargo_color_changed.emit()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Scroll area for cargo cards only (no header, no buttons)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setMinimumHeight(90)
        scroll_area.setMaximumHeight(110)
        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        self.cards_container = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setContentsMargins(5, 5, 5, 5)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.cards_layout.addStretch()
        
        scroll_area.setWidget(self.cards_container)
        layout.addWidget(scroll_area)
        self.scroll_area = scroll_area
    
    def set_stowage_plan(self, plan: StowagePlan):
        """Set the stowage plan and refresh display"""
        self.stowage_plan = plan
        self._refresh_cards()
    
    def update_loaded_quantities(self):
        """Update card displays with current loaded quantities from plan"""
        self._refresh_cards()
    
    def _refresh_cards(self):
        """Refresh cargo card display with current loaded quantities"""
        # Clear existing cards (except stretch)
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        
        if not self.stowage_plan:
            return
        
        # Create cards for each cargo with loaded quantity
        for i, cargo in enumerate(self.stowage_plan.cargo_requests):
            color = cargo.custom_color or CARGO_COLORS[i % len(CARGO_COLORS)]
            loaded_qty = self.stowage_plan.get_cargo_total_loaded(cargo.unique_id)
            # Pass self as legend_widget
            card = DraggableCargoCard(cargo, color, loaded_qty, legend_widget=self)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
    
    def get_cargo_colors(self) -> List[str]:
        """Get list of colors for all cargos"""
        colors = []
        for i, cargo in enumerate(self.stowage_plan.cargo_requests if self.stowage_plan else []):
            colors.append(cargo.custom_color or CARGO_COLORS[i % len(CARGO_COLORS)])
        return colors
