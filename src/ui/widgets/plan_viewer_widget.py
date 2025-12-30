"""
Plan viewer widget for displaying stowage plan comparison.
Ported from STOWAGEMASTER with adaptations for ULLAGEMASTER.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from typing import Optional, List

from models.stowage_plan import StowagePlan, StowageCargo


class PlanViewerWidget(QWidget):
    """Widget for visualizing stowage plan - requested vs loaded comparison."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_plan: Optional[StowagePlan] = None
        self.cargo_colors: List[str] = []
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Comparison table
        self.comparison_table = QTableWidget()
        self.comparison_table.setColumnCount(6)
        self.comparison_table.setHorizontalHeaderLabels([
            "Yük Tipi", "Alıcı(lar)", "Sipariş (m³)", "Yüklenen (m³)", "Fark (m³)", "Durum"
        ])
        self.comparison_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.comparison_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.comparison_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.comparison_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.comparison_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.comparison_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.comparison_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.comparison_table, 1)
        
        # Summary row
        summary_layout = QHBoxLayout()
        summary_layout.setContentsMargins(0, 0, 0, 0)
        
        self.summary_label_left = QLabel("Henüz plan oluşturulmadı")
        self.summary_label_left.setWordWrap(False)
        summary_layout.addWidget(self.summary_label_left)
        
        summary_layout.addStretch()
        
        self.summary_label_right = QLabel("")
        self.summary_label_right.setWordWrap(False)
        summary_layout.addWidget(self.summary_label_right)
        
        layout.addLayout(summary_layout, 0)
    
    def display_plan(self, plan: StowagePlan, cargo_colors: List[str] = None, total_capacity: float = 0):
        """Display a stowage plan.
        
        Args:
            plan: StowagePlan to display
            cargo_colors: List of hex colors matching cargo_requests order
            total_capacity: Total ship capacity in m³
            
        Updates:
            - Comparison table (Requested vs Loaded)
            - Summary labels (Capacity, Fulfillment %)
        """
        self.current_plan = plan
        self.cargo_colors = cargo_colors or []
        
        if not plan:
            self.clear_display()
            return
        
        # Calculate totals
        total_loaded = sum(a.quantity_loaded for a in plan.assignments.values())
        total_requested = sum(c.quantity for c in plan.cargo_requests)
        
        utilization = (total_loaded / total_capacity * 100) if total_capacity > 0 else 0
        fulfillment = (total_loaded / total_requested * 100) if total_requested > 0 else 0
        
        # Update summary labels
        self.summary_label_left.setText(
            f"<b>Kapasite:</b> {total_capacity:.2f} m³  |  "
            f"<b>Yüklenen:</b> {total_loaded:.2f} m³  |  "
            f"<b>Oran:</b> {utilization:.1f}%"
        )
        self.summary_label_right.setText(
            f"<b>Talep Karşılama:</b> {fulfillment:.1f}%"
        )
        
        # Fill comparison table
        self.comparison_table.setRowCount(len(plan.cargo_requests))
        
        for row, cargo in enumerate(plan.cargo_requests):
            color = self.cargo_colors[row] if row < len(self.cargo_colors) else "#E0E0E0"
            
            # Cargo type
            type_item = QTableWidgetItem(cargo.cargo_type)
            type_item.setBackground(QColor(color))
            self.comparison_table.setItem(row, 0, type_item)
            
            # Receivers
            receiver_item = QTableWidgetItem(cargo.get_receiver_names())
            receiver_item.setBackground(QColor(color))
            self.comparison_table.setItem(row, 1, receiver_item)
            
            # Requested
            requested = cargo.quantity
            requested_item = QTableWidgetItem(f"{requested:.2f}")
            requested_item.setBackground(QColor(color))
            self.comparison_table.setItem(row, 2, requested_item)
            
            # Loaded
            loaded = plan.get_cargo_total_loaded(cargo.unique_id)
            loaded_item = QTableWidgetItem(f"{loaded:.2f}")
            loaded_item.setBackground(QColor(color))
            self.comparison_table.setItem(row, 3, loaded_item)
            
            # Difference
            diff = loaded - requested
            diff_item = QTableWidgetItem(f"{diff:+.2f}")
            if abs(diff) < 0.01:
                diff_item.setBackground(QColor("#96CEB4"))  # Green
            elif diff < 0:
                diff_item.setBackground(QColor("#FFEAA7"))  # Yellow
            else:
                diff_item.setBackground(QColor("#FF6B6B"))  # Red
            self.comparison_table.setItem(row, 4, diff_item)
            
            # Status
            if abs(diff) < 0.01:
                status = "✓ Tamamlandı"
                status_item = QTableWidgetItem(status)
                status_item.setBackground(QColor("#96CEB4"))
            elif diff < 0:
                pct = (loaded / requested * 100) if requested > 0 else 0
                status = f"Eksik ({pct:.1f}%)"
                status_item = QTableWidgetItem(status)
                status_item.setBackground(QColor("#FFEAA7"))
            else:
                pct = (diff / requested * 100) if requested > 0 else 0
                status = f"Fazla ({pct:.1f}%)"
                status_item = QTableWidgetItem(status)
                status_item.setBackground(QColor("#FF6B6B"))
            
            self.comparison_table.setItem(row, 5, status_item)
        
        self.comparison_table.resizeRowsToContents()
    
    def clear_display(self):
        """Clear the display."""
        self.summary_label_left.setText("Henüz plan oluşturulmadı")
        self.summary_label_right.setText("")
        self.comparison_table.setRowCount(0)
