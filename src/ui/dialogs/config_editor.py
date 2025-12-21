"""
Config Editor Dialog - View and edit ship configuration after initial setup.
Allows editing ship name, ullage and trim data, but NOT trim value columns.
"""

from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QPushButton,
    QTabWidget, QWidget, QGroupBox, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt

from models import ShipConfig, TankConfig
from ui.widgets import DataEntryGrid
from utils import save_config


class ConfigEditorDialog(QDialog):
    """Dialog for viewing and editing an existing ship configuration."""
    
    def __init__(self, config: ShipConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.modified = False
        
        self.setWindowTitle(f"Ship Configuration - {config.ship_name}")
        self.setMinimumSize(900, 600)
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Tab 1: Ship Info
        self._create_ship_info_tab()
        
        # Tab 2: Tank Overview
        self._create_tank_overview_tab()
        
        # Tab 3: Ullage Data
        self._create_ullage_tab()
        
        # Tab 4: Trim Data
        self._create_trim_tab()
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self._save_changes)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_ship_info_tab(self):
        """Create the ship info tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Ship name (editable)
        self.ship_name_edit = QLineEdit()
        layout.addRow("Ship Name:", self.ship_name_edit)
        
        # VEF (editable)
        self.vef_spin = QDoubleSpinBox()
        self.vef_spin.setDecimals(5)
        self.vef_spin.setRange(0.9, 1.1)
        layout.addRow("Default V.E.F.:", self.vef_spin)
        
        layout.addRow(QLabel(""))
        
        # Trim values (read-only)
        trim_group = QGroupBox("Trim Values (Read-Only)")
        trim_layout = QVBoxLayout(trim_group)
        
        trim_info = QLabel(
            "Trim values cannot be changed after initial setup.\n"
            "To change trim values, create a new ship configuration."
        )
        trim_info.setStyleSheet("color: #666; font-style: italic;")
        trim_layout.addWidget(trim_info)
        
        self.trim_display = QLabel()
        self.trim_display.setStyleSheet("font-family: monospace; padding: 5px; background: #f0f0f0;")
        self.trim_display.setWordWrap(True)
        trim_layout.addWidget(self.trim_display)
        
        layout.addRow(trim_group)
        
        # Thermal correction (read-only)
        self.thermal_label = QLabel()
        layout.addRow("Thermal Correction:", self.thermal_label)
        
        self.tabs.addTab(widget, "Ship Info")
    
    def _create_tank_overview_tab(self):
        """Create tank overview tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel("Overview of all tanks and their configurations.")
        info.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info)
        
        self.overview_table = QTableWidget()
        self.overview_table.setColumnCount(5)
        self.overview_table.setHorizontalHeaderLabels([
            "Tank ID", "Tank Name", "Capacity (m³)", "Ullage Rows", "Trim Rows"
        ])
        self.overview_table.horizontalHeader().setStretchLastSection(True)
        # Allow editing capacity column only (column 2)
        self.overview_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        layout.addWidget(self.overview_table)
        
        # Help text
        help_label = QLabel("💡 Double-click the Capacity column to edit tank capacity values.")
        help_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(help_label)
        
        self.tabs.addTab(widget, "Tank Overview")
    
    def _create_ullage_tab(self):
        """Create ullage data editing tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel("Select a tank to view/edit its ullage table. You can copy-paste data.")
        info.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info)
        
        self.ullage_tabs = QTabWidget()
        layout.addWidget(self.ullage_tabs)
        
        self.ullage_grids: Dict[str, DataEntryGrid] = {}
        
        self.tabs.addTab(widget, "Ullage Data")
    
    def _create_trim_tab(self):
        """Create trim data editing tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel("Select a tank to view/edit its trim correction data.")
        info.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info)
        
        self.trim_tabs = QTabWidget()
        layout.addWidget(self.trim_tabs)
        
        self.trim_grids: Dict[str, DataEntryGrid] = {}
        
        self.tabs.addTab(widget, "Trim Data")
    
    def _load_data(self):
        """Load data from config into UI."""
        # Ship info
        self.ship_name_edit.setText(self.config.ship_name)
        self.vef_spin.setValue(self.config.default_vef)
        
        # Trim values display
        trim_str = ", ".join([f"{v:+.2f}" if v != 0 else "0" for v in self.config.trim_values])
        self.trim_display.setText(trim_str)
        
        # Thermal status
        thermal_status = "Enabled" if self.config.has_thermal_correction else "Disabled (using 1.0)"
        self.thermal_label.setText(thermal_status)
        
        # Tank overview
        self.overview_table.setRowCount(len(self.config.tanks))
        for row, tank in enumerate(self.config.tanks):
            # Tank ID - read-only
            id_item = QTableWidgetItem(tank.id)
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.overview_table.setItem(row, 0, id_item)
            
            # Tank Name - read-only
            name_item = QTableWidgetItem(tank.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.overview_table.setItem(row, 1, name_item)
            
            # Capacity - EDITABLE
            capacity_item = QTableWidgetItem(f"{tank.capacity_m3:.1f}")
            self.overview_table.setItem(row, 2, capacity_item)
            
            # Ullage Rows - read-only
            ullage_item = QTableWidgetItem(str(len(tank.ullage_table)))
            ullage_item.setFlags(ullage_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.overview_table.setItem(row, 3, ullage_item)
            
            # Trim Rows - read-only
            trim_item = QTableWidgetItem(str(len(tank.trim_table)))
            trim_item.setFlags(trim_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.overview_table.setItem(row, 4, trim_item)
        
        # Ullage grids
        self.ullage_tabs.clear()
        self.ullage_grids.clear()
        for tank in self.config.tanks:
            grid = DataEntryGrid(["Ullage (mm)", "Volume (m³)"], numeric_columns=[0, 1])
            self.ullage_grids[tank.id] = grid
            self.ullage_tabs.addTab(grid, tank.id)
            
            # Load existing data
            if tank.ullage_table:
                data = [[str(row.get('ullage_mm', '')), str(row.get('volume_m3', ''))] 
                        for row in tank.ullage_table]
                grid.set_data(data)
        
        # Trim grids
        self.trim_tabs.clear()
        self.trim_grids.clear()
        
        # Build column headers from trim values
        columns = ["Ullage (mm)"]
        for v in self.config.trim_values:
            if v >= 0:
                columns.append(f"+{v:.1f}m")
            else:
                columns.append(f"{v:.1f}m")
        
        for tank in self.config.tanks:
            grid = DataEntryGrid(columns, numeric_columns=list(range(len(columns))))
            self.trim_grids[tank.id] = grid
            self.trim_tabs.addTab(grid, tank.id)
            
            # Load existing trim data - need to reorganize from flat list to table format
            if tank.trim_table:
                # Group by ullage_mm
                data_by_ullage = {}
                for row in tank.trim_table:
                    ullage_mm = row.get('ullage_mm', 0)
                    trim_m = row.get('trim_m', 0)
                    correction = row.get('correction_m3', 0)
                    
                    if ullage_mm not in data_by_ullage:
                        data_by_ullage[ullage_mm] = {}
                    data_by_ullage[ullage_mm][trim_m] = correction
                
                # Convert to grid format
                grid_data = []
                for ullage_mm in sorted(data_by_ullage.keys()):
                    row_data = [str(int(ullage_mm))]
                    for trim_v in self.config.trim_values:
                        corr = data_by_ullage[ullage_mm].get(trim_v, '')
                        row_data.append(str(corr) if corr != '' else '')
                    grid_data.append(row_data)
                
                if grid_data:
                    grid.set_data(grid_data)
    
    def _save_changes(self):
        """Save changes back to config."""
        # Update ship info
        self.config.ship_name = self.ship_name_edit.text().strip()
        self.config.default_vef = self.vef_spin.value()
        
        # Update ullage tables
        for tank_id, grid in self.ullage_grids.items():
            tank = self.config.get_tank(tank_id)
            if tank:
                data = grid.get_data()
                tank.ullage_table = []
                for row in data:
                    if len(row) >= 2 and row[0] and row[1]:
                        try:
                            tank.ullage_table.append({
                                'ullage_mm': float(row[0]),
                                'volume_m3': float(row[1])
                            })
                        except ValueError:
                            pass
        
        # Update capacity from overview table (user-editable)
        for row in range(self.overview_table.rowCount()):
            tank_id_item = self.overview_table.item(row, 0)
            capacity_item = self.overview_table.item(row, 2)
            if tank_id_item and capacity_item:
                tank = self.config.get_tank(tank_id_item.text())
                if tank:
                    try:
                        user_capacity = float(capacity_item.text())
                        if user_capacity > 0:
                            tank.capacity_m3 = user_capacity
                        elif tank.ullage_table:
                            # Fallback to max volume if user left it at 0
                            tank.capacity_m3 = max(item['volume_m3'] for item in tank.ullage_table)
                    except ValueError:
                        pass
        
        # Update trim tables
        for tank_id, grid in self.trim_grids.items():
            tank = self.config.get_tank(tank_id)
            if tank:
                data = grid.get_data()
                tank.trim_table = []
                for row in data:
                    if len(row) >= 2 and row[0]:
                        try:
                            ullage_mm = float(row[0])
                            for col_idx, trim_val in enumerate(self.config.trim_values):
                                if col_idx + 1 < len(row) and row[col_idx + 1]:
                                    tank.trim_table.append({
                                        'ullage_mm': ullage_mm,
                                        'trim_m': trim_val,
                                        'correction_m3': float(row[col_idx + 1])
                                    })
                        except ValueError:
                            pass
        
        # Save to file
        if save_config(self.config):
            QMessageBox.information(self, "Saved", "Configuration saved successfully.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to save configuration.")
