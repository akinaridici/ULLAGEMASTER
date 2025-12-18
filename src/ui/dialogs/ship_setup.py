"""
Ship Setup Wizard - Configure ship tanks via direct data entry.
Replaces the Excel template workflow with a UI-based copy-paste system.
"""

from pathlib import Path
from typing import Optional, Dict, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox, QGroupBox, QTabWidget, QWidget, QScrollArea,
    QWizard, QWizardPage, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from models import ShipConfig, TankConfig
from i18n import t
from ui.widgets import DataEntryGrid


class ShipSetupWizard(QWizard):
    """Wizard for ship configuration - direct data entry without Excel."""
    
    def __init__(self, parent=None, existing_config: Optional[ShipConfig] = None):
        super().__init__(parent)
        
        self.setWindowTitle("Ship Configuration Wizard")
        self.setMinimumSize(900, 700)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        
        # Data storage
        self.config: Optional[ShipConfig] = existing_config
        self.tank_ids: List[str] = []
        
        # Add pages
        self.ship_info_page = ShipInfoPage(self)
        self.tank_setup_page = TankSetupPage(self)
        self.ullage_entry_page = UllageEntryPage(self)
        self.trim_entry_page = TrimEntryPage(self)
        self.thermal_entry_page = ThermalEntryPage(self)
        self.summary_page = SummaryPage(self)
        
        self.addPage(self.ship_info_page)
        self.addPage(self.tank_setup_page)
        self.addPage(self.ullage_entry_page)
        self.addPage(self.trim_entry_page)
        self.addPage(self.thermal_entry_page)
        self.addPage(self.summary_page)
    
    def get_config(self) -> Optional[ShipConfig]:
        """Get the resulting ship configuration."""
        return self.config


class ShipInfoPage(QWizardPage):
    """Page 1: Basic ship information."""
    
    def __init__(self, wizard: ShipSetupWizard):
        super().__init__()
        self.wizard_ref = wizard
        
        self.setTitle("Ship Information")
        self.setSubTitle("Enter your ship's basic information and configuration options.")
        
        layout = QFormLayout(self)
        
        # Ship name
        self.ship_name_edit = QLineEdit()
        self.ship_name_edit.setPlaceholderText("e.g., M/T EXAMPLE")
        layout.addRow("Ship Name:", self.ship_name_edit)
        
        # Default VEF
        self.vef_spin = QDoubleSpinBox()
        self.vef_spin.setDecimals(5)
        self.vef_spin.setRange(0.9, 1.1)
        self.vef_spin.setValue(1.0)
        layout.addRow("Default V.E.F.:", self.vef_spin)
        
        # Separator
        layout.addRow(QLabel(""))
        
        # Trim values configuration (comma-separated)
        trim_group = QGroupBox("Trim Values Configuration")
        trim_layout = QVBoxLayout(trim_group)
        
        trim_info = QLabel(
            "Enter trim values as a comma-separated list.\n"
            "Supports non-uniform steps, e.g.: -3, -2.5, -2, -1.5, -1, -0.75, -0.5, -0.25, 0, +0.25, +0.5, +0.75"
        )
        trim_info.setStyleSheet("color: #666; font-style: italic;")
        trim_layout.addWidget(trim_info)
        
        self.trim_values_edit = QLineEdit()
        self.trim_values_edit.setPlaceholderText("-2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2")
        self.trim_values_edit.setText("-2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2")
        trim_layout.addWidget(self.trim_values_edit)
        
        layout.addRow(trim_group)
        
        # Thermal correction option
        self.thermal_check = QCheckBox("My ship has Thermal Correction tables")
        self.thermal_check.setChecked(False)
        self.thermal_check.setToolTip(
            "If unchecked, thermal correction factor will default to 1.0\n"
            "for all tanks and temperatures."
        )
        layout.addRow(self.thermal_check)
        
        # Slop density
        self.slop_density_spin = QDoubleSpinBox()
        self.slop_density_spin.setDecimals(4)
        self.slop_density_spin.setRange(0.5, 2.0)
        self.slop_density_spin.setValue(0.85)
        self.slop_density_spin.setToolTip("Vacuum density for SLOP parcels")
        layout.addRow("Slop Density (VAC):", self.slop_density_spin)
        
        # Register required field
        self.registerField("ship_name*", self.ship_name_edit)

    def initializePage(self):
        """Load data from existing config if available."""
        config = self.wizard_ref.config
        if config:
            self.ship_name_edit.setText(config.ship_name)
            self.vef_spin.setValue(config.default_vef)
            self.thermal_check.setChecked(config.has_thermal_correction)
            self.slop_density_spin.setValue(getattr(config, 'slop_density', 0.85))
            
            # Trim values
            if config.trim_values:
                trim_str = ", ".join([f"{v:+.2f}" if v > 0 else f"{v}" for v in config.trim_values])
                # Clean up +0.00
                trim_str = trim_str.replace("+0.00", "0")
                self.trim_values_edit.setText(trim_str)
    
    def validatePage(self) -> bool:
        """Validate and save ship info."""
        ship_name = self.ship_name_edit.text().strip()
        if not ship_name:
            QMessageBox.warning(self, "Validation", "Please enter a ship name.")
            return False
        
        # Parse trim values
        trim_text = self.trim_values_edit.text().strip()
        if not trim_text:
            QMessageBox.warning(self, "Validation", "Please enter trim values.")
            return False
        
        try:
            # Parse comma-separated values
            trim_values = []
            for part in trim_text.split(','):
                part = part.strip().replace('+', '')
                if part:
                    trim_values.append(float(part))
            
            if not trim_values:
                raise ValueError("No valid trim values")
            
            # Sort and remove duplicates
            trim_values = sorted(list(set(trim_values)))
            
        except ValueError as e:
            QMessageBox.warning(
                self, "Validation",
                f"Invalid trim values. Please enter numbers separated by commas.\nError: {e}"
            )
            return False
        
        # Create or update config
        if self.wizard_ref.config is None:
            self.wizard_ref.config = ShipConfig.create_empty(ship_name)
        
        self.wizard_ref.config.ship_name = ship_name
        self.wizard_ref.config.default_vef = self.vef_spin.value()
        self.wizard_ref.config.slop_density = self.slop_density_spin.value()
        self.wizard_ref.config.trim_values = trim_values
        self.wizard_ref.config.has_thermal_correction = self.thermal_check.isChecked()
        
        return True


class TankSetupPage(QWizardPage):
    """Page 2: Define tank IDs."""
    
    def __init__(self, wizard: ShipSetupWizard):
        super().__init__()
        self.wizard_ref = wizard
        
        self.setTitle("Tank Configuration")
        self.setSubTitle("Define the tanks on your ship. You can add cargo tanks and slop tanks.")
        
        layout = QVBoxLayout(self)
        
        # Quick setup
        quick_group = QGroupBox("Quick Setup (Cargo Tank Pairs)")
        quick_layout = QHBoxLayout(quick_group)
        
        quick_layout.addWidget(QLabel("Number of cargo tank pairs:"))
        self.pairs_spin = QSpinBox()
        self.pairs_spin.setRange(1, 15)
        self.pairs_spin.setValue(6)
        quick_layout.addWidget(self.pairs_spin)
        
        generate_btn = QPushButton("Generate Tank List")
        generate_btn.clicked.connect(self._generate_tanks)
        quick_layout.addWidget(generate_btn)
        
        quick_layout.addStretch()
        layout.addWidget(quick_group)
        
        # Slop tanks
        slop_group = QGroupBox("Slop Tanks")
        slop_layout = QHBoxLayout(slop_group)
        
        self.slop_check = QCheckBox("Add Slop Tanks")
        self.slop_check.setChecked(True)
        slop_layout.addWidget(self.slop_check)
        
        slop_layout.addWidget(QLabel("Count:"))
        self.slop_count_spin = QSpinBox()
        self.slop_count_spin.setRange(0, 4)
        self.slop_count_spin.setValue(2)
        slop_layout.addWidget(self.slop_count_spin)
        
        slop_layout.addStretch()
        layout.addWidget(slop_group)
        
        # Tank list display
        list_group = QGroupBox("Tank List")
        list_layout = QVBoxLayout(list_group)
        
        self.tank_table = QTableWidget()
        self.tank_table.setColumnCount(3)
        self.tank_table.setHorizontalHeaderLabels(["Tank ID", "Tank Name", "Capacity (m³)"])
        self.tank_table.horizontalHeader().setStretchLastSection(True)
        self.tank_table.setColumnWidth(0, 80)
        self.tank_table.setColumnWidth(1, 150)
        self.tank_table.setColumnWidth(2, 100)
        list_layout.addWidget(self.tank_table)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Row")
        add_btn.clicked.connect(self._add_row)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_row)
        btn_layout.addWidget(remove_btn)
        
        btn_layout.addStretch()
        list_layout.addLayout(btn_layout)
        
        layout.addWidget(list_group)
    
    def _generate_tanks(self):
        """Generate standard tank list."""
        pairs = self.pairs_spin.value()
        
        tanks = []
        for i in range(1, pairs + 1):
            tanks.append((f"{i}P", f"No.{i} Port"))
            tanks.append((f"{i}S", f"No.{i} Starboard"))
        
        if self.slop_check.isChecked():
            slop_count = self.slop_count_spin.value()
            if slop_count >= 1:
                tanks.append(("SlopP", "Slop Port"))
            if slop_count >= 2:
                tanks.append(("SlopS", "Slop Starboard"))
            for i in range(3, slop_count + 1):
                tanks.append((f"Slop{i}", f"Slop {i}"))
        
        self.tank_table.setRowCount(len(tanks))
        for row, (tank_id, tank_name) in enumerate(tanks):
            self.tank_table.setItem(row, 0, QTableWidgetItem(tank_id))
            self.tank_table.setItem(row, 1, QTableWidgetItem(tank_name))
            self.tank_table.setItem(row, 2, QTableWidgetItem("0"))  # Default capacity
    
    def _add_row(self):
        """Add an empty row."""
        self.tank_table.insertRow(self.tank_table.rowCount())
    
    def _remove_row(self):
        """Remove selected row."""
        current = self.tank_table.currentRow()
        if current >= 0:
            self.tank_table.removeRow(current)
    
    def initializePage(self):
        """Initialize the page when shown."""
        # Auto-generate if empty and no config
        if self.tank_table.rowCount() == 0:
            config = self.wizard_ref.config
            if config and config.tanks:
                # Load from config
                self.tank_table.setRowCount(len(config.tanks))
                for row, tank in enumerate(config.tanks):
                    self.tank_table.setItem(row, 0, QTableWidgetItem(tank.id))
                    self.tank_table.setItem(row, 1, QTableWidgetItem(tank.name))
                    self.tank_table.setItem(row, 2, QTableWidgetItem(str(tank.capacity_m3)))
            else:
                self._generate_tanks()
    
    def validatePage(self) -> bool:
        """Validate and save tank configuration."""
        tank_ids = []
        tank_names = {}
        tank_capacities = {}
        
        for row in range(self.tank_table.rowCount()):
            id_item = self.tank_table.item(row, 0)
            name_item = self.tank_table.item(row, 1)
            capacity_item = self.tank_table.item(row, 2)
            
            if id_item and id_item.text().strip():
                tank_id = id_item.text().strip()
                tank_name = name_item.text().strip() if name_item else f"Tank {tank_id}"
                
                try:
                    capacity = float(capacity_item.text()) if capacity_item and capacity_item.text() else 0.0
                except ValueError:
                    capacity = 0.0
                
                if tank_id in tank_ids:
                    QMessageBox.warning(self, "Validation", f"Duplicate tank ID: {tank_id}")
                    return False
                
                tank_ids.append(tank_id)
                tank_names[tank_id] = tank_name
                tank_capacities[tank_id] = capacity
        
        if not tank_ids:
            QMessageBox.warning(self, "Validation", "Please define at least one tank.")
            return False
        
        # Update config
        self.wizard_ref.tank_ids = tank_ids
        self.wizard_ref.config.tank_count = len(tank_ids)
        self.wizard_ref.config.tanks = []
        
        for tank_id in tank_ids:
            tank = TankConfig(
                id=tank_id,
                name=tank_names[tank_id],
                capacity_m3=tank_capacities.get(tank_id, 0.0)
            )
            self.wizard_ref.config.add_tank(tank)
        
        return True


class UllageEntryPage(QWizardPage):
    """Page 3: Enter ullage tables for each tank."""
    
    def __init__(self, wizard: ShipSetupWizard):
        super().__init__()
        self.wizard_ref = wizard
        self.grids: Dict[str, DataEntryGrid] = {}
        
        self.setTitle("Ullage Tables")
        self.setSubTitle(
            "Enter the ullage table for each tank. You can copy-paste data from Excel.\n"
            "Columns: Ullage (mm) and Volume (m³)"
        )
        
        layout = QVBoxLayout(self)
        
        # Instructions
        info = QLabel(
            "💡 Tip: Select the first cell (Ullage column, first row) and press Ctrl+V to paste from Excel."
        )
        info.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        layout.addWidget(info)
        
        # Tab widget for tanks
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Copy to all button
        btn_layout = QHBoxLayout()
        copy_all_btn = QPushButton("Copy First Tank to All")
        copy_all_btn.setToolTip("Copy the ullage table from the first tank to all other tanks")
        copy_all_btn.clicked.connect(self._copy_to_all)
        btn_layout.addWidget(copy_all_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def initializePage(self):
        """Initialize tabs when page is shown."""
        # Clear existing tabs
        self.tab_widget.clear()
        self.grids.clear()
        
        for tank_id in self.wizard_ref.tank_ids:
            grid = DataEntryGrid(["Ullage (mm)", "Volume (m³)"], numeric_columns=[0, 1])
            self.grids[tank_id] = grid
            self.tab_widget.addTab(grid, tank_id)
            
            # Load existing data if available
            tank_config = self.wizard_ref.config.get_tank(tank_id) if self.wizard_ref.config else None
            if tank_config and tank_config.ullage_table:
                data = []
                for row in tank_config.ullage_table:
                    # Convert dict to list [ullage, volume]
                    if 'ullage_mm' in row and 'volume_m3' in row:
                        data.append([str(int(row['ullage_mm'])), str(row['volume_m3'])])
                if data:
                    grid.set_data(data)
    
    def _copy_to_all(self):
        """Copy data from first tank to all others."""
        if not self.wizard_ref.tank_ids:
            return
        
        first_id = self.wizard_ref.tank_ids[0]
        first_data = self.grids[first_id].get_data()
        
        if not first_data:
            QMessageBox.warning(self, "No Data", "First tank has no data to copy.")
            return
        
        for tank_id in self.wizard_ref.tank_ids[1:]:
            self.grids[tank_id].set_data(first_data)
        
        QMessageBox.information(
            self, "Copied",
            f"Copied ullage table from {first_id} to {len(self.wizard_ref.tank_ids) - 1} other tanks."
        )
    
    def validatePage(self) -> bool:
        """Validate and save ullage data."""
        for tank_id, grid in self.grids.items():
            is_valid, error = grid.validate()
            if not is_valid:
                QMessageBox.warning(self, f"Tank {tank_id}", f"Validation error: {error}")
                self.tab_widget.setCurrentWidget(grid)
                return False
            
            # Save data to config
            data = grid.get_data()
            tank = self.wizard_ref.config.get_tank(tank_id)
            if tank:
                tank.ullage_table = []
                for row in data:
                    if len(row) >= 2 and row[0] and row[1]:
                        tank.ullage_table.append({
                            'ullage_mm': float(row[0]),
                            'volume_m3': float(row[1])
                        })
                # Set capacity as max volume
                if tank.ullage_table:
                    tank.capacity_m3 = max(item['volume_m3'] for item in tank.ullage_table)
        
        return True


class TrimEntryPage(QWizardPage):
    """Page 4: Enter trim correction tables for each tank."""
    
    def __init__(self, wizard: ShipSetupWizard):
        super().__init__()
        self.wizard_ref = wizard
        self.grids: Dict[str, DataEntryGrid] = {}
        
        self.setTitle("Trim Correction Tables")
        self.setSubTitle(
            "Enter the trim correction table for each tank.\n"
            "First column is Ullage (mm), then one column per trim value."
        )
        
        layout = QVBoxLayout(self)
        
        # Info
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        layout.addWidget(self.info_label)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Copy button
        btn_layout = QHBoxLayout()
        copy_all_btn = QPushButton("Copy First Tank to All")
        copy_all_btn.clicked.connect(self._copy_to_all)
        btn_layout.addWidget(copy_all_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def initializePage(self):
        """Initialize tabs with dynamic columns based on trim range."""
        self.tab_widget.clear()
        self.grids.clear()
        
        # Get trim values
        trim_values = self.wizard_ref.config.get_trim_values()
        
        # Create column headers
        columns = ["Ullage (mm)"]
        for trim in trim_values:
            if trim >= 0:
                columns.append(f"+{trim:.1f}m")
            else:
                columns.append(f"{trim:.1f}m")
        
        self.info_label.setText(f"💡 Columns: Ullage (mm), then corrections for trims: {columns[1:]}")
        
        for tank_id in self.wizard_ref.tank_ids:
            grid = DataEntryGrid(columns, numeric_columns=list(range(len(columns))))
            self.grids[tank_id] = grid
            self.tab_widget.addTab(grid, tank_id)
            
            # Load existing data
            tank_config = self.wizard_ref.config.get_tank(tank_id) if self.wizard_ref.config else None
            if tank_config and tank_config.trim_table:
                # Need to reconstruct grid rows from flat list of dicts
                # Dict: {ullage_mm, trim_m, correction_m3}
                # We need to map (ullage, trim) -> correction
                
                # First group by ullage
                ullage_map = {}
                for row in tank_config.trim_table:
                    u_mm = int(row['ullage_mm'])
                    if u_mm not in ullage_map:
                        ullage_map[u_mm] = {}
                    ullage_map[u_mm][row['trim_m']] = row['correction_m3']
                
                # Sort ullages
                sorted_ullages = sorted(ullage_map.keys())
                
                grid_data = []
                for u_mm in sorted_ullages:
                    row_data = [str(u_mm)]
                    corrections = ullage_map[u_mm]
                    
                    # Add correction for each column (trim value)
                    for trim_val in trim_values:
                        # Find closest trim match if float precision issue?
                        # Using loose comparison or direct key
                        val = corrections.get(trim_val)
                        if val is None:
                            # Try searching with tolerance?
                            for stored_trim, stored_corr in corrections.items():
                                if abs(stored_trim - trim_val) < 0.01:
                                    val = stored_corr
                                    break
                                    
                        row_data.append(str(val) if val is not None else "")
                    grid_data.append(row_data)
                
                if grid_data:
                    grid.set_data(grid_data)
    
    def _copy_to_all(self):
        """Copy data from first tank to all others."""
        if not self.wizard_ref.tank_ids:
            return
        
        first_id = self.wizard_ref.tank_ids[0]
        first_data = self.grids[first_id].get_data()
        
        if not first_data:
            QMessageBox.warning(self, "No Data", "First tank has no data to copy.")
            return
        
        for tank_id in self.wizard_ref.tank_ids[1:]:
            self.grids[tank_id].set_data(first_data)
        
        QMessageBox.information(
            self, "Copied",
            f"Copied trim table from {first_id} to {len(self.wizard_ref.tank_ids) - 1} other tanks."
        )
    
    def validatePage(self) -> bool:
        """Validate and save trim data."""
        trim_values = self.wizard_ref.config.get_trim_values()
        
        for tank_id, grid in self.grids.items():
            is_valid, error = grid.validate()
            if not is_valid:
                QMessageBox.warning(self, f"Tank {tank_id}", f"Validation error: {error}")
                self.tab_widget.setCurrentWidget(grid)
                return False
            
            # Save data to config
            data = grid.get_data()
            tank = self.wizard_ref.config.get_tank(tank_id)
            if tank:
                tank.trim_table = []
                for row in data:
                    if len(row) >= 2 and row[0]:
                        ullage_mm = float(row[0])
                        for col_idx, trim_val in enumerate(trim_values):
                            if col_idx + 1 < len(row) and row[col_idx + 1]:
                                tank.trim_table.append({
                                    'ullage_mm': ullage_mm,
                                    'trim_m': trim_val,
                                    'correction_m3': float(row[col_idx + 1])
                                })
        
        return True


class ThermalEntryPage(QWizardPage):
    """Page 5: Enter thermal correction tables (optional)."""
    
    def __init__(self, wizard: ShipSetupWizard):
        super().__init__()
        self.wizard_ref = wizard
        self.grids: Dict[str, DataEntryGrid] = {}
        
        self.setTitle("Thermal Correction Tables")
        self.setSubTitle(
            "Enter the thermal correction table for each tank.\n"
            "Columns: Temperature (°C) and Correction Factor"
        )
        
        layout = QVBoxLayout(self)
        
        # Info
        info = QLabel(
            "💡 If you don't have thermal correction data, leave this page empty.\n"
            "A default factor of 1.0 will be used for all temperatures."
        )
        info.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        layout.addWidget(info)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Copy button
        btn_layout = QHBoxLayout()
        copy_all_btn = QPushButton("Copy First Tank to All")
        copy_all_btn.clicked.connect(self._copy_to_all)
        btn_layout.addWidget(copy_all_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def initializePage(self):
        """Initialize tabs - always show content."""
        self.tab_widget.clear()
        self.grids.clear()
        
        # Check if thermal correction is disabled
        if not self.wizard_ref.config.has_thermal_correction:
            # Show info tab explaining why it's empty
            info_widget = QLabel(
                "⚠️ Thermal Correction is DISABLED.\n\n"
                "To enable thermal correction:\n"
                "1. Go back to 'Ship Information' page\n"
                "2. Check 'My ship has Thermal Correction tables'\n"
                "3. Return to this page to enter data\n\n"
                "When disabled, a default factor of 1.0 is used for all tanks."
            )
            info_widget.setStyleSheet(
                "padding: 20px; font-size: 14px; color: #666; background: #fff3cd; border-radius: 8px;"
            )
            info_widget.setWordWrap(True)
            self.tab_widget.addTab(info_widget, "Info")
            return
        
        for tank_id in self.wizard_ref.tank_ids:
            grid = DataEntryGrid(["Temperature (°C)", "Correction Factor"], numeric_columns=[0, 1])
            self.grids[tank_id] = grid
            self.tab_widget.addTab(grid, tank_id)
            
            # Load existing data
            tank_config = self.wizard_ref.config.get_tank(tank_id) if self.wizard_ref.config else None
            if tank_config and tank_config.thermal_table:
                data = []
                for row in tank_config.thermal_table:
                    if 'temp_c' in row and 'corr_factor' in row:
                        data.append([str(int(row['temp_c'])), f"{row['corr_factor']:.6f}"])
                
                if data:
                    grid.set_data(data)
    
    def isComplete(self) -> bool:
        """Allow skipping if thermal is disabled."""
        if not self.wizard_ref.config.has_thermal_correction:
            return True
        return super().isComplete()
    
    def _copy_to_all(self):
        """Copy data from first tank to all others."""
        if not self.wizard_ref.tank_ids:
            return
        
        first_id = self.wizard_ref.tank_ids[0]
        first_data = self.grids[first_id].get_data()
        
        if not first_data:
            QMessageBox.warning(self, "No Data", "First tank has no data to copy.")
            return
        
        for tank_id in self.wizard_ref.tank_ids[1:]:
            self.grids[tank_id].set_data(first_data)
        
        QMessageBox.information(
            self, "Copied",
            f"Copied thermal table from {first_id} to {len(self.wizard_ref.tank_ids) - 1} other tanks."
        )
    
    def validatePage(self) -> bool:
        """Validate and save thermal data."""
        if not self.wizard_ref.config.has_thermal_correction:
            # Set default thermal factor for all tanks
            for tank in self.wizard_ref.config.tanks:
                tank.thermal_table = [{'temp_c': 15.0, 'corr_factor': 1.0}]
            return True
        
        for tank_id, grid in self.grids.items():
            data = grid.get_data()
            tank = self.wizard_ref.config.get_tank(tank_id)
            
            if tank:
                if data:
                    tank.thermal_table = []
                    for row in data:
                        if len(row) >= 2 and row[0] and row[1]:
                            tank.thermal_table.append({
                                'temp_c': float(row[0]),
                                'corr_factor': float(row[1])
                            })
                else:
                    # Default if no data
                    tank.thermal_table = [{'temp_c': 15.0, 'corr_factor': 1.0}]
        
        return True


class SummaryPage(QWizardPage):
    """Page 6: Summary and confirmation."""
    
    def __init__(self, wizard: ShipSetupWizard):
        super().__init__()
        self.wizard_ref = wizard
        
        self.setTitle("Configuration Summary")
        self.setSubTitle("Review your configuration before saving.")
        
        layout = QVBoxLayout(self)
        
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Tank", "Ullage Rows", "Trim Rows", "Thermal"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
    
    def initializePage(self):
        """Populate summary."""
        config = self.wizard_ref.config
        
        # Ship info
        thermal_status = "Yes" if config.has_thermal_correction else "No (using default 1.0)"
        trim_display = ", ".join([f"{v:+.2f}" if v != 0 else "0" for v in config.trim_values[:5]])
        if len(config.trim_values) > 5:
            trim_display += f", ... ({len(config.trim_values)} values)"
        self.summary_label.setText(
            f"<b>Ship Name:</b> {config.ship_name}<br>"
            f"<b>Tank Count:</b> {len(config.tanks)}<br>"
            f"<b>Trim Values:</b> {trim_display}<br>"
            f"<b>Thermal Correction:</b> {thermal_status}<br>"
            f"<b>Default V.E.F.:</b> {config.default_vef}"
        )
        
        # Tank data summary
        self.table.setRowCount(len(config.tanks))
        for row, tank in enumerate(config.tanks):
            self.table.setItem(row, 0, QTableWidgetItem(tank.id))
            self.table.setItem(row, 1, QTableWidgetItem(str(len(tank.ullage_table))))
            self.table.setItem(row, 2, QTableWidgetItem(str(len(tank.trim_table))))
            
            thermal_count = len(tank.thermal_table) if tank.thermal_table else 0
            item = QTableWidgetItem(str(thermal_count) if thermal_count else "Default")
            self.table.setItem(row, 3, item)
    
    def validatePage(self) -> bool:
        """Final validation before saving."""
        config = self.wizard_ref.config
        
        # Check all tanks have data
        for tank in config.tanks:
            if not tank.ullage_table:
                QMessageBox.warning(
                    self, "Missing Data",
                    f"Tank {tank.id} has no ullage table data."
                )
                return False
            if not tank.trim_table:
                QMessageBox.warning(
                    self, "Missing Data",
                    f"Tank {tank.id} has no trim correction data."
                )
                return False
        
        return True


# Keep old dialog signature for backward compatibility
class ShipSetupDialog(QDialog):
    """Legacy dialog wrapper - launches the new wizard."""
    
    def __init__(self, parent=None, config: Optional[ShipConfig] = None):
        super().__init__(parent)
        self.config = config
        self.parsed_data = None
        
        # Just show the wizard
        wizard = ShipSetupWizard(parent, config)
        if wizard.exec() == QWizard.DialogCode.Accepted:
            self.config = wizard.get_config()
            self.accept()
        else:
            self.reject()
    
    def get_config(self) -> ShipConfig:
        return self.config
    
    def get_parsed_data(self):
        return self.parsed_data
