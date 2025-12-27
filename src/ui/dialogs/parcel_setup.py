"""
Parcel Setup Dialog - Define parcels for a voyage.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QColorDialog, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from models import Parcel
from ui.styles import COLOR_TEXT_SECONDARY


class ParcelSetupDialog(QDialog):
    """Dialog for setting up voyage parcels."""
    
    def __init__(self, parcels: List[Parcel] = None, parent=None):
        super().__init__(parent)
        self.parcels = list(parcels) if parcels else []
        
        self.setWindowTitle("Voyage Parcels Setup")
        self.setMinimumSize(700, 400)
        
        self._setup_ui()
        self._load_parcels()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Instructions
        info = QLabel(
            "Define the cargo parcels for this voyage. Each parcel has its own grade, "
            "receiver, density, and display color."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; padding: 5px;")
        layout.addWidget(info)
        
        # Parcel table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "ID", "Cargo Grade", "Receiver", "Density (kg/m³)", "Color"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 80)
        layout.addWidget(self.table)
        
        # Add/Remove buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Parcel")
        add_btn.clicked.connect(self._add_parcel)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_parcel)
        btn_layout.addWidget(remove_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Dialog buttons
        dialog_btns = QHBoxLayout()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._save_and_close)
        dialog_btns.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        dialog_btns.addWidget(cancel_btn)
        
        layout.addLayout(dialog_btns)
    
    def _load_parcels(self):
        """Load existing parcels into the table."""
        self.table.setRowCount(len(self.parcels))
        for row, parcel in enumerate(self.parcels):
            self._set_row(row, parcel)
    
    def _set_row(self, row: int, parcel: Parcel):
        """Set table row from parcel data."""
        # ID
        id_item = QTableWidgetItem(parcel.id)
        self.table.setItem(row, 0, id_item)
        
        # Grade
        grade_item = QTableWidgetItem(parcel.name)
        self.table.setItem(row, 1, grade_item)
        
        # Receiver
        receiver_item = QTableWidgetItem(parcel.receiver)
        self.table.setItem(row, 2, receiver_item)
        
        # Density
        density_item = QTableWidgetItem(f"{parcel.density_vac:.3f}")
        self.table.setItem(row, 3, density_item)
        
        # Color button
        color_btn = QPushButton()
        color_btn.setStyleSheet(f"background-color: {parcel.color}; border: none;")
        color_btn.setProperty("color", parcel.color)
        color_btn.clicked.connect(lambda checked, r=row: self._pick_color(r))
        self.table.setCellWidget(row, 4, color_btn)
    
    def _add_parcel(self):
        """Add a new parcel row."""
        row = self.table.rowCount()
        self.table.setRowCount(row + 1)
        
        # Default parcel
        new_id = str(row + 1)
        colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"]
        color = colors[row % len(colors)]
        
        parcel = Parcel(id=new_id, name="", receiver="", density_vac=0.0, color=color)
        self._set_row(row, parcel)
    
    def _remove_parcel(self):
        """Remove selected parcel rows."""
        rows = set(item.row() for item in self.table.selectedItems())
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)
    
    def _pick_color(self, row: int):
        """Open color picker for a row."""
        btn = self.table.cellWidget(row, 4)
        current_color = QColor(btn.property("color"))
        
        color = QColorDialog.getColor(current_color, self, "Pick Parcel Color")
        if color.isValid():
            hex_color = color.name()
            btn.setStyleSheet(f"background-color: {hex_color}; border: none;")
            btn.setProperty("color", hex_color)
    
    def _save_and_close(self):
        """Validate and save parcels."""
        parcels = []
        ids_seen = set()
        
        for row in range(self.table.rowCount()):
            id_item = self.table.item(row, 0)
            grade_item = self.table.item(row, 1)
            receiver_item = self.table.item(row, 2)
            density_item = self.table.item(row, 3)
            color_btn = self.table.cellWidget(row, 4)
            
            parcel_id = id_item.text().strip() if id_item else ""
            if not parcel_id:
                QMessageBox.warning(self, "Validation", f"Row {row+1}: Parcel ID is required.")
                return
            
            if parcel_id in ids_seen:
                QMessageBox.warning(self, "Validation", f"Duplicate parcel ID: {parcel_id}")
                return
            ids_seen.add(parcel_id)
            
            try:
                density = float(density_item.text()) if density_item and density_item.text() else 0.0
            except ValueError:
                density = 0.0
            
            parcel = Parcel(
                id=parcel_id,
                name=grade_item.text() if grade_item else "",
                receiver=receiver_item.text() if receiver_item else "",
                density_vac=density,
                color=color_btn.property("color") if color_btn else "#3B82F6"
            )
            parcels.append(parcel)
        
        self.parcels = parcels
        self.accept()
    
    def get_parcels(self) -> List[Parcel]:
        """Get the configured parcels."""
        return self.parcels
