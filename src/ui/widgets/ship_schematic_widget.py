"""
Ship schematic widget for displaying tanks in grid layout.
Ported from STOWAGEMASTER with adaptations for ULLAGEMASTER's ShipConfig.
"""

from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QVBoxLayout, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, Optional, Callable, Set

from models import ShipConfig, TankConfig
from models.stowage_plan import StowagePlan, TankAssignment
from ui.widgets.draggable_tank_card import DraggableTankCard


class ShipSchematicWidget(QWidget):
    """Widget that displays ship schematic with tanks arranged in grid.
    
    Port/Starboard arrangement with Tank 1 on the right (bow side).
    """
    
    assignment_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plan: Optional[StowagePlan] = None
        self.ship_config: Optional[ShipConfig] = None
        self.tank_cards: Dict[str, DraggableTankCard] = {}  # tank_id -> card
        self.excluded_tanks: Set[str] = set()
        self._cargo_colors: list = []
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 5)
        
        # Main container with grid layout
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(5)
        self.grid_layout.setContentsMargins(5, 2, 5, 5)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.grid_container)
        layout.addStretch()
    
    def set_ship_config(self, config: ShipConfig):
        """Set ship configuration"""
        self.ship_config = config
        if self.plan:
            self.display_tanks()
    
    def set_stowage_plan(self, plan: StowagePlan):
        """Set stowage plan"""
        self.plan = plan
        if self.ship_config:
            self.display_tanks()
    
    def set_cargo_colors(self, colors: list):
        """Set cargo colors for display"""
        self._cargo_colors = colors
    
    def display_tanks(self):
        """Display tanks in grid layout"""
        self._clear_tanks()
        
        if not self.ship_config or not self.ship_config.tanks:
            return
        
        # Group tanks by row (Port/Starboard pairs)
        tank_groups = self._group_tanks_by_row()
        
        if not tank_groups:
            return
        
        # Calculate grid layout - Tank 1 on right (bow side)
        tank_numbers_sorted = sorted(tank_groups.keys())
        max_tank_number = max(tank_groups.keys())
        tank_to_col = {tank_num: max_tank_number - tank_num + 1 for tank_num in tank_numbers_sorted}
        
        # Add tanks to grid (no column headers - tank IDs shown on cards)
        # Add tanks to grid
        for tank_number in tank_numbers_sorted:
            col_pos = tank_to_col[tank_number]
            
            # Port tank (row 1 - top)
            if "port" in tank_groups[tank_number]:
                tank = tank_groups[tank_number]["port"]
                card = self._create_tank_card(tank)
                self.grid_layout.addWidget(card, 1, col_pos)
                self.tank_cards[tank.id] = card
            
            # Starboard tank (row 2 - bottom)
            if "starboard" in tank_groups[tank_number]:
                tank = tank_groups[tank_number]["starboard"]
                card = self._create_tank_card(tank)
                self.grid_layout.addWidget(card, 2, col_pos)
                self.tank_cards[tank.id] = card
    
    def _group_tanks_by_row(self) -> Dict[int, Dict[str, TankConfig]]:
        """Group tanks by row number and side (port/starboard)"""
        groups = {}
        for idx, tank in enumerate(self.ship_config.tanks):
            row_number = (idx // 2) + 1
            side = "port" if idx % 2 == 0 else "starboard"
            if row_number not in groups:
                groups[row_number] = {}
            groups[row_number][side] = tank
        return groups
    
    def _create_tank_card(self, tank: TankConfig) -> DraggableTankCard:
        """Create a tank card for the given tank"""
        assignment = self.plan.get_assignment(tank.id) if self.plan else None
        is_excluded = tank.id in self.excluded_tanks
        
        # Check if locked - find main window
        is_locked = False
        widget = self.parent()
        while widget:
            if hasattr(widget, 'is_tank_locked'):
                is_locked = widget.is_tank_locked(tank.id)
                break
            widget = widget.parent()
        
        # Determine color and utilization
        utilization = 0.0
        color = "#E0E0E0"
        
        if assignment:
            capacity = getattr(tank, 'capacity_m3', 0)
            if capacity > 0:
                utilization = (assignment.quantity_loaded / capacity) * 100
            
            # Find cargo index for color - prioritize custom_color
            if self.plan:
                for i, cargo in enumerate(self.plan.cargo_requests):
                    if cargo.unique_id == assignment.cargo.unique_id:
                        # Priority: custom_color first, then indexed colors
                        if cargo.custom_color:
                            color = cargo.custom_color
                        elif i < len(self._cargo_colors):
                            color = self._cargo_colors[i]
                        break
        
        return DraggableTankCard(
            tank=tank,
            assignment=assignment,
            utilization=utilization,
            color=color,
            is_excluded=is_excluded,
            is_fixed=is_locked
        )
    
    def _clear_tanks(self):
        """Clear all tank cards from grid"""
        while self.grid_layout.count() > 0:
            item = self.grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self.tank_cards.clear()
    
    def refresh(self):
        """Refresh the display"""
        self.display_tanks()
