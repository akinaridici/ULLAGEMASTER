"""
Ship Setup Dialog - Configure ship tanks and upload Excel template.
"""

from pathlib import Path
from typing import Optional, Dict
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox, QGroupBox, QTabWidget, QWidget, QScrollArea,
    QWizard, QWizardPage, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from models import ShipConfig, TankConfig
from i18n import t
from utils import generate_ship_template, get_template_filename, parse_ship_template


class ShipSetupWizard(QWizard):
    """Wizard for initial ship setup - generates template and imports data."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Ship Configuration Wizard")
        self.setMinimumSize(600, 500)
        
        # Data
        self.ship_name = ""
        self.tank_count = 6
        self.include_thermal = True
        self.template_path = ""
        self.config: Optional[ShipConfig] = None
        
        # Add pages
        self.addPage(ShipInfoPage(self))
        self.addPage(GenerateTemplatePage(self))
        self.addPage(ImportTemplatePage(self))
        
    def get_config(self) -> Optional[ShipConfig]:
        """Get the resulting ship configuration."""
        return self.config


class ShipInfoPage(QWizardPage):
    """Page 1: Enter ship name and tank count."""
    
    def __init__(self, wizard: ShipSetupWizard):
        super().__init__()
        self.wizard = wizard
        
        self.setTitle("Ship Information")
        self.setSubTitle("Enter your ship details to generate a configuration template.")
        
        layout = QFormLayout(self)
        
        # Ship name
        self.ship_name_edit = QLineEdit()
        self.ship_name_edit.setPlaceholderText("e.g., M/T EXAMPLE")
        layout.addRow("Ship Name:", self.ship_name_edit)
        
        # Tank pairs
        self.tank_pairs_spin = QSpinBox()
        self.tank_pairs_spin.setRange(1, 15)
        self.tank_pairs_spin.setValue(6)
        layout.addRow("Number of Tank Pairs:", self.tank_pairs_spin)
        
        # Info label
        info = QLabel(
            "Each tank pair includes Port (P) and Starboard (S) tanks.\n"
            "Example: 6 pairs = 12 main tanks + 2 slop tanks = 14 total."
        )
        info.setStyleSheet("color: #666; font-style: italic;")
        layout.addRow(info)
        
        # Include thermal correction
        self.thermal_check = QCheckBox("Include Thermal Correction tables")
        self.thermal_check.setChecked(True)
        self.thermal_check.setToolTip(
            "Thermal correction accounts for tank volume changes\n"
            "due to steel temperature (optional for some ships)."
        )
        layout.addRow(self.thermal_check)
        
        # Default VEF
        self.vef_spin = QDoubleSpinBox()
        self.vef_spin.setDecimals(5)
        self.vef_spin.setRange(0.9, 1.1)
        self.vef_spin.setValue(1.0)
        layout.addRow("Default V.E.F.:", self.vef_spin)
        
        # Register fields
        self.registerField("ship_name*", self.ship_name_edit)
        self.registerField("tank_pairs", self.tank_pairs_spin)
    
    def validatePage(self) -> bool:
        """Validate and save data."""
        self.wizard.ship_name = self.ship_name_edit.text().strip()
        self.wizard.tank_count = self.tank_pairs_spin.value()
        self.wizard.include_thermal = self.thermal_check.isChecked()
        
        if not self.wizard.ship_name:
            QMessageBox.warning(self, "Validation", "Please enter a ship name.")
            return False
        
        return True


class GenerateTemplatePage(QWizardPage):
    """Page 2: Generate and download template."""
    
    def __init__(self, wizard: ShipSetupWizard):
        super().__init__()
        self.wizard = wizard
        self.template_generated = False
        
        self.setTitle("Generate Template")
        self.setSubTitle("Generate an Excel template to fill in your ship's calibration data.")
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Click 'Generate Template' to create an Excel file with:\n\n"
            "• ULLAGE_TABLES - Enter ullage (mm) and volume (m³) for each tank\n"
            "• TRIM_CORRECTION - Enter trim correction factors\n"
            "• THERMAL_CORRECTION - Enter thermal expansion data (optional)\n\n"
            "Fill in this template with your ship's calibration data,\n"
            "then proceed to the next step to import it."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        layout.addSpacing(20)
        
        # Generate button
        self.generate_btn = QPushButton("📄 Generate Template")
        self.generate_btn.setStyleSheet("font-size: 14px; padding: 10px;")
        self.generate_btn.clicked.connect(self._generate_template)
        layout.addWidget(self.generate_btn)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Skip info
        skip_info = QLabel(
            "If you already have a completed template, proceed to the next step."
        )
        skip_info.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(skip_info)
    
    def _generate_template(self):
        """Generate the Excel template."""
        # Get tank IDs
        tank_ids = []
        for i in range(1, self.wizard.tank_count + 1):
            tank_ids.append(f"{i}P")
            tank_ids.append(f"{i}S")
        tank_ids.extend(["SlopP", "SlopS"])
        
        # Get save path
        default_name = get_template_filename(self.wizard.ship_name)
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Template As",
            default_name,
            "Excel Files (*.xlsx)"
        )
        
        if not filepath:
            return
        
        # Generate
        success = generate_ship_template(
            self.wizard.ship_name,
            tank_ids,
            filepath,
            include_thermal=self.wizard.include_thermal
        )
        
        if success:
            self.wizard.template_path = filepath
            self.template_generated = True
            self.status_label.setText(f"✓ Template saved: {Path(filepath).name}")
            self.generate_btn.setText("📄 Regenerate Template")
            
            QMessageBox.information(
                self,
                "Template Generated",
                f"Template saved to:\n{filepath}\n\n"
                "Please fill in the calibration data and proceed to the next step to import it."
            )
        else:
            QMessageBox.critical(self, "Error", "Failed to generate template.")


class ImportTemplatePage(QWizardPage):
    """Page 3: Import completed template."""
    
    def __init__(self, wizard: ShipSetupWizard):
        super().__init__()
        self.wizard = wizard
        self.import_success = False
        
        self.setTitle("Import Template")
        self.setSubTitle("Upload your completed Excel template to configure the ship.")
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "After filling in the template with your ship's calibration data,\n"
            "click 'Import Template' to load the data into UllageMaster."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        layout.addSpacing(20)
        
        # Import button
        self.import_btn = QPushButton("📥 Import Completed Template")
        self.import_btn.setStyleSheet("font-size: 14px; padding: 10px;")
        self.import_btn.clicked.connect(self._import_template)
        layout.addWidget(self.import_btn)
        
        # Status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        # Summary table
        self.summary_group = QGroupBox("Import Summary")
        self.summary_group.setVisible(False)
        summary_layout = QVBoxLayout(self.summary_group)
        
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(4)
        self.summary_table.setHorizontalHeaderLabels(["Tank", "Ullage Table", "Trim Table", "Thermal"])
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        summary_layout.addWidget(self.summary_table)
        
        layout.addWidget(self.summary_group)
        layout.addStretch()
    
    def _import_template(self):
        """Import the completed template."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Completed Template",
            "",
            "Excel Files (*.xlsx)"
        )
        
        if not filepath:
            return
        
        # Parse template
        result = parse_ship_template(filepath)
        
        if not result.success:
            QMessageBox.critical(
                self,
                "Import Error",
                f"Failed to parse template:\n{result.error_message}"
            )
            return
        
        if not result.tank_ids:
            QMessageBox.warning(
                self,
                "No Data",
                "No tank data found in the template.\n"
                "Please ensure the ULLAGE_TABLES sheet contains data."
            )
            return
        
        # Create ShipConfig
        config = ShipConfig(
            ship_name=self.wizard.ship_name,
            tank_pairs=self.wizard.tank_count,
            default_vef=1.0
        )
        
        # Add tanks with data
        for tank_id in result.tank_ids:
            tank_config = TankConfig(
                id=tank_id,
                name=f"Tank {tank_id}",
                capacity_m3=0.0
            )
            
            # Get capacity from ullage table (max volume)
            if tank_id in result.ullage_tables:
                df = result.ullage_tables[tank_id]
                tank_config.capacity_m3 = float(df['volume_m3'].max())
            
            # Get capacity from thermal data if available
            if tank_id in result.thermal_data:
                thermal = result.thermal_data[tank_id]
                if thermal.get('capacity'):
                    tank_config.capacity_m3 = thermal['capacity']
            
            config.add_tank(tank_config)
        
        # Store parsed data in wizard for later use
        self.wizard.config = config
        self.wizard.parsed_result = result
        
        # Update summary
        self._show_summary(result)
        
        self.import_success = True
        self.status_label.setText("✓ Template imported successfully!")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
    
    def _show_summary(self, result):
        """Show import summary."""
        self.summary_group.setVisible(True)
        self.summary_table.setRowCount(len(result.tank_ids))
        
        for row, tank_id in enumerate(result.tank_ids):
            self.summary_table.setItem(row, 0, QTableWidgetItem(tank_id))
            
            # Ullage table status
            has_ullage = tank_id in result.ullage_tables
            item = QTableWidgetItem("✓" if has_ullage else "✗")
            item.setForeground(QColor("green" if has_ullage else "red"))
            self.summary_table.setItem(row, 1, item)
            
            # Trim table status
            has_trim = tank_id in result.trim_tables
            item = QTableWidgetItem("✓" if has_trim else "-")
            item.setForeground(QColor("green" if has_trim else "gray"))
            self.summary_table.setItem(row, 2, item)
            
            # Thermal data status
            has_thermal = tank_id in result.thermal_data
            item = QTableWidgetItem("✓" if has_thermal else "-")
            item.setForeground(QColor("green" if has_thermal else "gray"))
            self.summary_table.setItem(row, 3, item)
    
    def validatePage(self) -> bool:
        """Validate import before finishing."""
        if not self.import_success:
            reply = QMessageBox.question(
                self,
                "No Import",
                "You haven't imported a template yet.\n"
                "Do you want to continue without importing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            return reply == QMessageBox.StandardButton.Yes
        
        return True


# Keep old dialog for backward compatibility
class ShipSetupDialog(QDialog):
    """Dialog for configuring ship and tank settings (legacy mode)."""
    
    def __init__(self, parent=None, config: Optional[ShipConfig] = None):
        super().__init__(parent)
        self.config = config or ShipConfig.create_default("New Ship", 6)
        self.parsed_data = None
        
        self.setWindowTitle(t("ship_setup_title", "dialogs"))
        self.setMinimumSize(800, 600)
        
        self._setup_ui()
        self._populate_from_config()
    
    def _setup_ui(self):
        """Create dialog UI."""
        layout = QVBoxLayout(self)
        
        # Ship info section
        ship_group = QGroupBox("Ship Information")
        ship_layout = QFormLayout(ship_group)
        
        self.ship_name_edit = QLineEdit()
        ship_layout.addRow(t("ship_name", "dialogs"), self.ship_name_edit)
        
        self.tank_pairs_spin = QSpinBox()
        self.tank_pairs_spin.setRange(1, 15)
        self.tank_pairs_spin.setValue(6)
        self.tank_pairs_spin.valueChanged.connect(self._on_tank_pairs_changed)
        ship_layout.addRow(t("tank_pairs", "dialogs"), self.tank_pairs_spin)
        
        self.default_vef_spin = QDoubleSpinBox()
        self.default_vef_spin.setDecimals(5)
        self.default_vef_spin.setRange(0.9, 1.1)
        self.default_vef_spin.setValue(1.0)
        ship_layout.addRow("Default V.E.F.", self.default_vef_spin)
        
        layout.addWidget(ship_group)
        
        # Template section
        template_group = QGroupBox("Calibration Data")
        template_layout = QVBoxLayout(template_group)
        
        template_info = QLabel(
            "Use the template workflow to import all tank calibration data at once:"
        )
        template_layout.addWidget(template_info)
        
        btn_layout = QHBoxLayout()
        
        self.generate_btn = QPushButton("📄 Generate Blank Template")
        self.generate_btn.clicked.connect(self._generate_template)
        btn_layout.addWidget(self.generate_btn)
        
        self.import_btn = QPushButton("📥 Import Completed Template")
        self.import_btn.clicked.connect(self._import_template)
        btn_layout.addWidget(self.import_btn)
        
        template_layout.addLayout(btn_layout)
        
        self.template_status = QLabel("")
        template_layout.addWidget(self.template_status)
        
        layout.addWidget(template_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton(t("save", "dialogs"))
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton(t("cancel", "dialogs"))
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _populate_from_config(self):
        """Populate UI from config."""
        self.ship_name_edit.setText(self.config.ship_name)
        self.tank_pairs_spin.setValue(self.config.tank_pairs)
        self.default_vef_spin.setValue(self.config.default_vef)
    
    def _on_tank_pairs_changed(self, value: int):
        """Handle tank pairs change."""
        old_config = self.config
        self.config = ShipConfig.create_default(old_config.ship_name, value)
        self.config.default_vef = old_config.default_vef
    
    def _generate_template(self):
        """Generate blank template."""
        tank_ids = []
        for i in range(1, self.tank_pairs_spin.value() + 1):
            tank_ids.append(f"{i}P")
            tank_ids.append(f"{i}S")
        tank_ids.extend(["SlopP", "SlopS"])
        
        ship_name = self.ship_name_edit.text() or "Ship"
        default_name = get_template_filename(ship_name)
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Template As", default_name, "Excel Files (*.xlsx)"
        )
        
        if filepath:
            success = generate_ship_template(ship_name, tank_ids, filepath)
            if success:
                self.template_status.setText(f"✓ Template saved: {Path(filepath).name}")
                self.template_status.setStyleSheet("color: green;")
                QMessageBox.information(
                    self, "Success",
                    f"Template saved to:\n{filepath}\n\n"
                    "Fill in the data and import it back."
                )
            else:
                QMessageBox.critical(self, "Error", "Failed to generate template.")
    
    def _import_template(self):
        """Import completed template."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Completed Template", "", "Excel Files (*.xlsx)"
        )
        
        if not filepath:
            return
        
        result = parse_ship_template(filepath)
        
        if not result.success:
            QMessageBox.critical(self, "Error", f"Import failed:\n{result.error_message}")
            return
        
        if not result.tank_ids:
            QMessageBox.warning(self, "No Data", "No tank data found in template.")
            return
        
        # Update config
        self.config.ship_name = self.ship_name_edit.text()
        self.config.tanks = []
        
        for tank_id in result.tank_ids:
            capacity = 0.0
            if tank_id in result.ullage_tables:
                capacity = float(result.ullage_tables[tank_id]['volume_m3'].max())
            
            self.config.add_tank(TankConfig(
                id=tank_id,
                name=f"Tank {tank_id}",
                capacity_m3=capacity
            ))
        
        self.parsed_data = result
        
        self.template_status.setText(f"✓ Imported {len(result.tank_ids)} tanks")
        self.template_status.setStyleSheet("color: green; font-weight: bold;")
        
        QMessageBox.information(
            self, "Import Complete",
            f"Imported data for {len(result.tank_ids)} tanks.\n"
            "Click Save to apply the configuration."
        )
    
    def get_config(self) -> ShipConfig:
        """Get the updated configuration."""
        self.config.ship_name = self.ship_name_edit.text()
        self.config.default_vef = self.default_vef_spin.value()
        return self.config
    
    def get_parsed_data(self):
        """Get the parsed template data."""
        return self.parsed_data
