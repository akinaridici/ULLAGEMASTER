"""
Draggable tank card widget for stowage planning.
Ported from STOWAGEMASTER with simplifications - removed optimizer features.
"""

from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QProgressBar, QMenu
from PyQt6.QtCore import Qt, QMimeData, QByteArray
from PyQt6.QtGui import QDrag, QColor
import json
from typing import Optional

from models import TankConfig
from models.stowage_plan import TankAssignment


class DraggableTankCard(QGroupBox):
    """Tank card widget with drag-and-drop support for stowage planning.
    
    Simplified from STOWAGEMASTER - removed:
    - is_suggested, fit_info (optimizer suggestions)
    - is_planned (optimizer result flag)
    - Pulse animations
    """
    
    def __init__(self, tank: TankConfig, assignment: TankAssignment = None,
                 utilization: float = 0.0, color: str = "#E0E0E0",
                 parent=None, is_excluded: bool = False, is_fixed: bool = False):
        super().__init__(tank.id, parent)
        self.tank = tank
        self.assignment = assignment
        self.utilization = utilization
        self.color = color
        self.is_excluded = is_excluded
        self.is_fixed = is_fixed
        
        self.setMaximumWidth(180)
        self.setMinimumWidth(150)
        self.setAcceptDrops(True)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 5)
        layout.setSpacing(3)
        
        # Capacity info
        capacity = getattr(self.tank, 'capacity_m3', 0)
        info_label = QLabel(f"{capacity:.0f} m³")
        info_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        layout.addWidget(info_label)
        
        if self.assignment:
            # Cargo type with receiver info
            cargo_text = self.assignment.cargo.cargo_type
            receiver_names = self.assignment.cargo.get_receiver_names()
            cargo_text += f"\n({receiver_names})"
            
            cargo_label = QLabel(cargo_text)
            cargo_label.setStyleSheet(
                f"background-color: {self.color}; padding: 3px; "
                f"border-radius: 2px; font-weight: bold;"
            )
            cargo_label.setWordWrap(True)
            layout.addWidget(cargo_label)
            
            # Quantity loaded
            qty_label = QLabel(f"{self.assignment.quantity_loaded:.0f} m³")
            qty_label.setStyleSheet("font-size: 9pt;")
            layout.addWidget(qty_label)
        else:
            empty_label = QLabel("Boş")
            empty_label.setStyleSheet(
                "background-color: #E0E0E0; padding: 3px; border-radius: 2px;"
            )
            layout.addWidget(empty_label)
        
        # Progress bar
        progress = QProgressBar()
        progress.setMinimum(0)
        progress.setMaximum(100)
        progress.setValue(int(self.utilization))
        progress.setFormat(f"{self.utilization:.0f}%")
        progress.setStyleSheet(
            f"QProgressBar::chunk {{ background-color: {self.color}; }}"
        )
        progress.setMaximumHeight(20)
        layout.addWidget(progress)
        
        # Excluded label
        if self.is_excluded:
            excluded_label = QLabel("⚠ Planlama Dışı")
            excluded_label.setStyleSheet(
                "background-color: #FF6B6B; color: white; padding: 2px; "
                "border-radius: 2px; font-weight: bold; font-size: 8pt;"
            )
            excluded_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(excluded_label)
        
        # Fixed label (locked assignment)
        if self.is_fixed:
            fixed_label = QLabel("🔒 Kilitli")
            fixed_label.setStyleSheet(
                "background-color: #FF9500; color: white; padding: 2px; "
                "border-radius: 2px; font-weight: bold; font-size: 8pt;"
            )
            fixed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(fixed_label)
        
        self._update_style()
    
    def _update_style(self):
        """Update visual style based on status"""
        if self.is_excluded:
            self.setStyleSheet("""
                QGroupBox {
                    border: 2px dashed #999999;
                    background-color: #F5F5F5;
                    color: #666666;
                }
                QGroupBox::title {
                    color: #666666;
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0px 3px;
                }
            """)
        else:
            self.setStyleSheet("""
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0px 3px;
                }
            """)
    
    def mousePressEvent(self, event):
        """Handle mouse press for drag start"""
        try:
            if not self or not hasattr(self, 'assignment'):
                return
            
            if self.is_fixed:
                super().mousePressEvent(event)
                return
            
            if event.button() == Qt.MouseButton.LeftButton and self.assignment:
                self.drag_start_position = event.position().toPoint()
                super().mousePressEvent(event)
        except RuntimeError:
            pass
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for drag operation"""
        try:
            if not self or not hasattr(self, 'assignment'):
                return
            
            if not hasattr(self, 'drag_start_position'):
                super().mouseMoveEvent(event)
                return
            
            if not (event.buttons() & Qt.MouseButton.LeftButton):
                super().mouseMoveEvent(event)
                return
            
            if not self.assignment:
                super().mouseMoveEvent(event)
                return
            
            if self.is_fixed:
                super().mouseMoveEvent(event)
                return
            
            # Check if moved enough to start drag
            if ((event.position().toPoint() - self.drag_start_position).manhattanLength() < 10):
                super().mouseMoveEvent(event)
                return
            
            # Create drag
            drag = QDrag(self)
            mime_data = QMimeData()
            
            # Store tank and assignment data
            drag_data = {
                'source_tank_id': self.tank.id,
                'assignment': {
                    'cargo': {
                        'cargo_type': self.assignment.cargo.cargo_type,
                        'quantity': self.assignment.quantity_loaded,
                        'unique_id': self.assignment.cargo.unique_id,
                        'receivers': [r.name for r in self.assignment.cargo.receivers]
                    },
                    'quantity_loaded': self.assignment.quantity_loaded
                }
            }
            
            mime_data.setData("application/x-tank-assignment",
                             QByteArray(json.dumps(drag_data).encode()))
            drag.setMimeData(mime_data)
            
            # Create drag pixmap
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.position().toPoint())
            
            drag.exec(Qt.DropAction.MoveAction)
            super().mouseMoveEvent(event)
        except RuntimeError:
            pass
    
    def dragEnterEvent(self, event):
        """Handle drag enter event"""
        try:
            if (event.mimeData().hasFormat("application/x-tank-assignment") or
                event.mimeData().hasFormat("application/x-cargo-id")):
                if self.is_excluded:
                    event.ignore()
                elif self.is_fixed:
                    event.ignore()
                else:
                    event.acceptProposedAction()
            else:
                event.ignore()
        except RuntimeError:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move event"""
        try:
            if (event.mimeData().hasFormat("application/x-tank-assignment") or
                event.mimeData().hasFormat("application/x-cargo-id")):
                if self.is_excluded or self.is_fixed:
                    event.ignore()
                else:
                    event.acceptProposedAction()
            else:
                event.ignore()
        except RuntimeError:
            event.ignore()
    
    def dropEvent(self, event):
        """Handle drop event"""
        try:
            if not self or not hasattr(self, 'tank'):
                event.ignore()
                return
            
            if self.is_excluded or self.is_fixed:
                event.ignore()
                return
            
            mime = event.mimeData()
            if mime.hasFormat("application/x-tank-assignment"):
                # Tank-to-tank swap
                data = json.loads(mime.data("application/x-tank-assignment").data().decode())
                source_tank_id = data['source_tank_id']
                
                if source_tank_id == self.tank.id:
                    event.ignore()
                    return
                
                # Find main window to handle swap
                widget = self.parent()
                while widget:
                    if hasattr(widget, 'handle_tank_swap'):
                        widget.handle_tank_swap(source_tank_id, self.tank.id)
                        event.acceptProposedAction()
                        return
                    widget = widget.parent()
                
                event.acceptProposedAction()
            elif mime.hasFormat("application/x-cargo-id"):
                # Cargo-to-tank drop from legend
                try:
                    data = json.loads(mime.data("application/x-cargo-id").data().decode())
                    cargo_id = data['cargo_id']
                    
                    # Find main window to handle cargo assignment
                    widget = self
                    while widget:
                        if hasattr(widget, 'handle_cargo_drop'):
                            widget.handle_cargo_drop(cargo_id, self.tank.id)
                            event.acceptProposedAction()
                            return
                        widget = widget.parent()
                    
                    event.acceptProposedAction()
                except Exception as e:
                    print(f"Error in cargo drop: {e}")
                    event.ignore()
            else:
                event.ignore()
        except RuntimeError:
            event.ignore()
    
    def contextMenuEvent(self, event):
        """Handle right-click context menu"""
        try:
            if not self or not hasattr(self, 'tank'):
                return
            
            # Find main window
            widget = self.parent()
            main_window = None
            while widget:
                if hasattr(widget, 'stowage_plan'):
                    main_window = widget
                    break
                widget = widget.parent()
            
            if not main_window:
                return
            
            menu = QMenu(self)
            
            # If tank has assignment
            if self.assignment is not None:
                # Color change option (always available for assigned tanks)
                color_action = menu.addAction("🎨 Renk Değiştir")
                menu.addSeparator()
                
                if self.is_fixed:
                    # Locked tank - show unlock option
                    unlock_action = menu.addAction("🔓 Kilidi Kaldır")
                    menu.addSeparator()
                    empty_action = menu.addAction("Boşalt")
                    
                    selected = menu.exec(event.globalPos())
                    
                    if selected == color_action:
                        self._show_color_picker(main_window)
                    elif selected == unlock_action:
                        if main_window and hasattr(main_window, 'handle_unlock_tank'):
                            main_window.handle_unlock_tank(self.tank.id)
                    elif selected == empty_action:
                        if main_window and hasattr(main_window, 'handle_empty_tank'):
                            main_window.handle_empty_tank(self.tank.id)
                else:
                    # Unlocked tank with assignment - show lock and empty options
                    lock_action = menu.addAction("🔒 Kilitle")
                    menu.addSeparator()
                    empty_action = menu.addAction("Boşalt")
                    
                    selected = menu.exec(event.globalPos())
                    
                    if selected == color_action:
                        self._show_color_picker(main_window)
                    elif selected == lock_action:
                        if main_window and hasattr(main_window, 'handle_lock_tank'):
                            main_window.handle_lock_tank(self.tank.id)
                    elif selected == empty_action:
                        if main_window and hasattr(main_window, 'handle_empty_tank'):
                            main_window.handle_empty_tank(self.tank.id)
            else:
                # Empty tank - show exclusion menu
                if self.is_excluded:
                    action = menu.addAction("✅ Planlamaya Dahil Et")
                else:
                    action = menu.addAction("⚠ Planlama Dışı Bırak")
                
                selected_action = menu.exec(event.globalPos())
                
                if selected_action == action:
                    new_excluded = not self.is_excluded
                    if main_window:
                        main_window.handle_exclude_tank(self.tank.id, new_excluded)
        except RuntimeError:
            pass
    
    def _show_color_picker(self, main_window):
        """Show color picker dialog to change cargo color."""
        from PyQt6.QtWidgets import QColorDialog
        
        if not self.assignment or not self.assignment.cargo:
            return
        
        cargo = self.assignment.cargo
        current_color = cargo.custom_color or "#3B82F6"
        
        color = QColorDialog.getColor(QColor(current_color), self, "Kargo Rengi Seç")
        
        if color.isValid():
            # Update cargo color
            cargo.custom_color = color.name()
            
            # Refresh UI
            if main_window and hasattr(main_window, '_on_stowage_changed'):
                main_window._on_stowage_changed()
