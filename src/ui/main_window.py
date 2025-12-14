"""
Main Window for UllageMaster.
Excel-like grid interface for cargo calculations.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QLineEdit,
    QDoubleSpinBox, QComboBox, QPushButton, QMenuBar, QMenu,
    QStatusBar, QMessageBox, QFileDialog, QGroupBox, QFrame,
    QAbstractItemView, QApplication, QInputDialog
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont, QAction, QKeySequence, QKeyEvent

from i18n import t, set_language, get_current_language
from models import ShipConfig, Tank, TankReading, Voyage, DraftReadings
from core import (
    calculate_tov, calculate_fill_percent, calculate_ullage_from_percent,
    apply_trim_correction, calculate_vcf, calculate_gsv, calculate_mass,
    get_level_warning, LevelWarning, vac_to_air
)
from export import (
    export_stowage_plan, export_ascii_report, 
    export_to_excel, export_to_pdf
)
from ui.dialogs import ShipSetupDialog, PreferencesDialog

from .styles import (
    COLOR_CELL_INPUT, COLOR_CELL_CALCULATED, COLOR_CELL_TEXT,
    COLOR_DANGER, COLOR_WARNING_HIGH, COLOR_WARNING_LOW, COLOR_WINDOW_BG
)

# Legacy naming for compatibility with existing logic
COLOR_INPUT = COLOR_CELL_INPUT
COLOR_CALCULATED = COLOR_CELL_CALCULATED
COLOR_TEXT = COLOR_CELL_TEXT
COLOR_WARNING_CRITICAL = COLOR_DANGER
# Warning colors for traffic light system
COLOR_WARNING_HIGH = QColor(234, 179, 8)   # Yellow 500
COLOR_WARNING_LOW = QColor(249, 115, 22)   # Orange 500


class MainWindow(QMainWindow):
    """Main application window."""
    
    # Column definitions: (key, header, width, is_input, is_numeric)
    COLUMNS = [
        ("tank_id", "Tank", 60, False, False),
        ("parcel", "Parcel", 60, True, False),
        ("grade", "Grade", 100, True, False),
        ("receiver", "Receiver", 100, True, False),
        ("receiver_tank", "Tank No", 60, True, False),
        ("ullage", "Ullage", 70, True, True),
        ("fill_percent", "% Fill", 60, True, True),
        ("trim_corr", "Trim Corr", 70, False, True),
        ("tov", "TOV", 90, False, True),
        ("temp", "Temp", 60, True, True),
        ("vcf", "VCF", 80, False, True),
        ("density_vac", "VAC Dens", 80, True, True),
        ("density_air", "Air Dens", 80, False, True),
        ("gsv", "GSV", 90, False, True),
        ("mt_air", "MT (Air)", 90, False, True),
        ("bl_figure", "B/L Figure", 90, True, True),
        ("discrepancy", "Disc %", 70, False, True),
    ]
    
    def __init__(self):
        super().__init__()
        
        # Data
        self.ship_config: Optional[ShipConfig] = None
        self.tanks: Dict[str, Tank] = {}
        self.voyage: Optional[Voyage] = None
        
        # Setup UI
        self.setWindowTitle("UllageMaster - Tanker Cargo Calculator")
        self.setMinimumSize(1400, 800)
        
        self._create_menu()
        self._create_central_widget()
        self._create_status_bar()
        
        # Load default or create new
        self._init_default_data()
    
    def _create_menu(self):
        """Create menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu(t("file", "menu"))
        
        new_action = QAction(t("new_voyage", "menu"), self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_voyage)
        file_menu.addAction(new_action)
        
        open_action = QAction(t("open_voyage", "menu"), self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_voyage)
        file_menu.addAction(open_action)
        
        save_action = QAction(t("save_voyage", "menu"), self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_voyage)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        # Export submenu
        export_menu = file_menu.addMenu(t("export", "menu"))
        
        excel_action = QAction(t("export_excel", "menu"), self)
        excel_action.triggered.connect(lambda: self._export("excel"))
        export_menu.addAction(excel_action)
        
        pdf_action = QAction(t("export_pdf", "menu"), self)
        pdf_action.triggered.connect(lambda: self._export("pdf"))
        export_menu.addAction(pdf_action)
        
        ascii_action = QAction(t("export_ascii", "menu"), self)
        ascii_action.triggered.connect(lambda: self._export("ascii"))
        export_menu.addAction(ascii_action)
        
        json_action = QAction(t("export_json", "menu"), self)
        json_action.triggered.connect(lambda: self._export("json"))
        export_menu.addAction(json_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(t("exit", "menu"), self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Settings menu
        settings_menu = menubar.addMenu(t("settings", "menu"))
        
        ship_config_action = QAction(t("ship_config", "menu"), self)
        ship_config_action.triggered.connect(self._show_ship_config)
        settings_menu.addAction(ship_config_action)
        
        prefs_action = QAction(t("preferences", "menu"), self)
        prefs_action.triggered.connect(self._show_preferences)
        settings_menu.addAction(prefs_action)
        
        # Help menu
        help_menu = menubar.addMenu(t("help", "menu"))
        
        about_action = QAction(t("about", "menu"), self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_central_widget(self):
        """Create main content area."""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header section
        header = self._create_header()
        layout.addWidget(header)
        
        # Tank grid
        self.tank_table = self._create_tank_grid()
        layout.addWidget(self.tank_table)
        
        # Footer section
        footer = self._create_footer()
        layout.addWidget(footer)
    
    def _create_header(self) -> QWidget:
        """Create header section with voyage info."""
        group = QGroupBox("Voyage Information")
        layout = QGridLayout(group)
        
        # Row 1
        layout.addWidget(QLabel(t("loading_port", "header")), 0, 0)
        self.port_edit = QLineEdit()
        layout.addWidget(self.port_edit, 0, 1)
        
        layout.addWidget(QLabel(t("loading_terminal", "header")), 0, 2)
        self.terminal_edit = QLineEdit()
        layout.addWidget(self.terminal_edit, 0, 3)
        
        layout.addWidget(QLabel(t("voyage_no", "header")), 0, 4)
        self.voyage_edit = QLineEdit()
        layout.addWidget(self.voyage_edit, 0, 5)
        
        layout.addWidget(QLabel(t("date", "header")), 0, 6)
        self.date_edit = QLineEdit()
        self.date_edit.setText(datetime.now().strftime("%Y-%m-%d"))
        layout.addWidget(self.date_edit, 0, 7)
        
        # Row 2
        layout.addWidget(QLabel(t("vef", "header")), 1, 0)
        self.vef_spin = QDoubleSpinBox()
        self.vef_spin.setDecimals(5)
        self.vef_spin.setRange(0.9, 1.1)
        self.vef_spin.setValue(1.0)
        self.vef_spin.setSingleStep(0.00001)
        self.vef_spin.valueChanged.connect(self._recalculate_all)
        layout.addWidget(self.vef_spin, 1, 1)
        
        layout.addWidget(QLabel(t("draft_aft", "header")), 1, 2)
        self.draft_aft_spin = QDoubleSpinBox()
        self.draft_aft_spin.setDecimals(2)
        self.draft_aft_spin.setRange(0, 30)
        self.draft_aft_spin.valueChanged.connect(self._on_draft_changed)
        layout.addWidget(self.draft_aft_spin, 1, 3)
        
        layout.addWidget(QLabel(t("draft_fwd", "header")), 1, 4)
        self.draft_fwd_spin = QDoubleSpinBox()
        self.draft_fwd_spin.setDecimals(2)
        self.draft_fwd_spin.setRange(0, 30)
        self.draft_fwd_spin.valueChanged.connect(self._on_draft_changed)
        layout.addWidget(self.draft_fwd_spin, 1, 5)
        
        layout.addWidget(QLabel(t("trim", "header")), 1, 6)
        self.trim_label = QLabel("0.00 m")
        self.trim_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.trim_label, 1, 7)
        
        return group
    
    def _create_tank_grid(self) -> QTableWidget:
        """Create the main tank data grid."""
        table = QTableWidget()
        
        # Configure table
        table.setColumnCount(len(self.COLUMNS))
        table.setHorizontalHeaderLabels([col[1] for col in self.COLUMNS])
        
        # Set column widths
        for i, (_, _, width, _, _) in enumerate(self.COLUMNS):
            table.setColumnWidth(i, width)
        
        # Configure selection
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        
        # Connect signals
        table.cellChanged.connect(self._on_cell_changed)
        
        # Style header
        header = table.horizontalHeader()
        header.setStyleSheet(
            "QHeaderView::section { background-color: #4472C4; color: white; font-weight: bold; }"
        )
        
        # Install event filter for bulk input
        table.installEventFilter(self)
        
        return table
    
    def eventFilter(self, obj, event):
        """Handle key events for bulk input on selected cells."""
        if obj == self.tank_table and event.type() == event.Type.KeyPress:
            selected = self.tank_table.selectedItems()
            if len(selected) > 1:
                # Multiple cells selected - handle bulk input
                key = event.key()
                if key in (Qt.Key.Key_0, Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3, 
                           Qt.Key.Key_4, Qt.Key.Key_5, Qt.Key.Key_6, Qt.Key.Key_7,
                           Qt.Key.Key_8, Qt.Key.Key_9, Qt.Key.Key_Period):
                    # Numeric key pressed - prompt for value
                    self._handle_bulk_input(selected)
                    return True
        return super().eventFilter(obj, event)
    
    def _handle_bulk_input(self, selected_items):
        """Handle bulk input for multiple selected cells."""
        # Check if all selected cells are in the same column
        columns = set(item.column() for item in selected_items)
        if len(columns) != 1:
            QMessageBox.warning(self, "Bulk Input", 
                "Please select cells in a single column for bulk input.")
            return
        
        col = list(columns)[0]
        key, header, _, is_input, is_numeric = self.COLUMNS[col]
        
        if not is_input:
            QMessageBox.warning(self, "Bulk Input",
                "Cannot edit calculated columns.")
            return
        
        # Prompt for value
        if is_numeric:
            value, ok = QInputDialog.getDouble(
                self, f"Bulk Input - {header}",
                f"Enter value for all {len(selected_items)} selected cells:",
                decimals=2
            )
        else:
            value, ok = QInputDialog.getText(
                self, f"Bulk Input - {header}",
                f"Enter value for all {len(selected_items)} selected cells:"
            )
        
        if ok:
            self.tank_table.blockSignals(True)
            for item in selected_items:
                if is_numeric:
                    item.setText(f"{value:.2f}" if key == "fill_percent" else f"{value:.1f}")
                else:
                    item.setText(str(value))
            self.tank_table.blockSignals(False)
            
            # Recalculate affected rows
            rows = set(item.row() for item in selected_items)
            for row in rows:
                tank_id_item = self.tank_table.item(row, 0)
                if tank_id_item:
                    reading = self.voyage.get_reading(tank_id_item.text())
                    if reading:
                        self._update_reading(reading, key, value)
                        self._recalculate_tank(row, tank_id_item.text())
            
            self.status_bar.showMessage(
                f"Applied {value} to {len(selected_items)} cells")
    
    def _create_footer(self) -> QWidget:
        """Create footer section with totals."""
        group = QGroupBox("Summary")
        layout = QHBoxLayout(group)
        
        # Totals
        layout.addWidget(QLabel(t("total_gsv", "footer")))
        self.total_gsv_label = QLabel("0.000")
        self.total_gsv_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.total_gsv_label)
        
        layout.addSpacing(30)
        
        layout.addWidget(QLabel(t("total_mt", "footer")))
        self.total_mt_label = QLabel("0.000")
        self.total_mt_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.total_mt_label)
        
        layout.addStretch()
        
        # Officers
        layout.addWidget(QLabel(t("chief_officer", "footer")))
        self.chief_officer_edit = QLineEdit()
        self.chief_officer_edit.setMaximumWidth(150)
        layout.addWidget(self.chief_officer_edit)
        
        layout.addWidget(QLabel(t("master", "footer")))
        self.master_edit = QLineEdit()
        self.master_edit.setMaximumWidth(150)
        layout.addWidget(self.master_edit)
        
        return group
    
    def _create_status_bar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _init_default_data(self):
        """Initialize with default ship configuration."""
        # Try to load saved ship config
        config_path = self._get_config_path()
        if config_path.exists():
            try:
                self.ship_config = ShipConfig.load_from_json(str(config_path))
                self.status_bar.showMessage(f"Loaded ship config: {self.ship_config.ship_name}")
                # Load ullage/trim tables
                self._load_tank_tables()
            except Exception as e:
                print(f"Error loading config: {e}")
                self.ship_config = ShipConfig.create_default("M/T EXAMPLE", 6)
        else:
            # Create default ship with 6 tank pairs
            self.ship_config = ShipConfig.create_default("M/T EXAMPLE", 6)
        
        # Create voyage
        self.voyage = Voyage.create_new("001/2024", "EXAMPLE PORT", "EXAMPLE TERMINAL")
        
        # Populate grid
        self._populate_grid()
    
    def _get_config_path(self) -> Path:
        """Get path to ship config file."""
        # Get the data/config directory relative to src
        src_dir = Path(__file__).parent.parent
        config_dir = src_dir.parent / "data" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "ship_config.json"
    
    def _load_tank_tables(self):
        """Load ullage and trim tables for all tanks."""
        for tank_config in self.ship_config.tanks:
            # Create or get tank
            if tank_config.id not in self.tanks:
                tank = Tank(
                    id=tank_config.id,
                    name=tank_config.name,
                    capacity_m3=tank_config.capacity_m3
                )
                self.tanks[tank_config.id] = tank
            else:
                tank = self.tanks[tank_config.id]
            
            # Load tables if paths are set
            if tank_config.ullage_table_path and os.path.exists(tank_config.ullage_table_path):
                tank.load_ullage_table(tank_config.ullage_table_path)
                # Update capacity from table's max volume
                if tank.has_ullage_table():
                    tank.capacity_m3 = tank.get_max_volume()
            if tank_config.trim_table_path and os.path.exists(tank_config.trim_table_path):
                tank.load_trim_table(tank_config.trim_table_path)
    
    def _save_ship_config(self):
        """Save ship config to file."""
        config_path = self._get_config_path()
        self.ship_config.save_to_json(str(config_path))
        self.status_bar.showMessage(f"Ship config saved: {config_path.name}")
    
    def _populate_grid(self):
        """Populate the tank grid with ship configuration."""
        if not self.ship_config:
            return
        
        self.tank_table.blockSignals(True)
        
        # Set row count
        tank_count = len(self.ship_config.tanks)
        self.tank_table.setRowCount(tank_count)
        
        # Populate each row
        for row, tank_config in enumerate(self.ship_config.tanks):
            # Create Tank object only if not exists (preserve loaded tables)
            if tank_config.id not in self.tanks:
                tank = Tank(
                    id=tank_config.id,
                    name=tank_config.name,
                    capacity_m3=tank_config.capacity_m3
                )
                self.tanks[tank_config.id] = tank
            else:
                # Update existing tank's capacity
                tank = self.tanks[tank_config.id]
                tank.capacity_m3 = tank_config.capacity_m3
            
            # Create TankReading if not exists
            if tank_config.id not in self.voyage.tank_readings:
                self.voyage.add_reading(TankReading(tank_id=tank_config.id))
            
            reading = self.voyage.get_reading(tank_config.id)
            
            # Populate cells
            for col, (key, _, _, is_input, is_numeric) in enumerate(self.COLUMNS):
                item = QTableWidgetItem()
                
                # Set value based on key
                value = self._get_reading_value(reading, key)
                if value is not None:
                    if is_numeric:
                        # Format based on column type
                        if key == "ullage":
                            item.setText(f"{int(value)}" if isinstance(value, (int, float)) else str(value))
                        elif key == "fill_percent":
                            item.setText(f"{value:.1f}" if isinstance(value, float) else str(value))
                        elif key == "vcf":
                            item.setText(f"{value:.5f}" if isinstance(value, float) else str(value))
                        else:
                            item.setText(f"{value:.3f}" if isinstance(value, float) else str(value))
                    else:
                        item.setText(str(value))
                
                # Set cell properties
                item.setForeground(COLOR_TEXT)  # Set black text color
                if is_input:
                    item.setBackground(COLOR_INPUT)
                else:
                    item.setBackground(COLOR_CALCULATED)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                self.tank_table.setItem(row, col, item)
        
        self.tank_table.blockSignals(False)
    
    def _get_reading_value(self, reading: TankReading, key: str):
        """Get value from reading based on column key."""
        mapping = {
            "tank_id": reading.tank_id,
            "parcel": reading.parcel,
            "grade": reading.grade,
            "receiver": reading.receiver,
            "receiver_tank": reading.receiver_tank,
            "ullage": reading.ullage,
            "fill_percent": reading.fill_percent,
            "trim_corr": reading.trim_correction,
            "tov": reading.tov,
            "temp": reading.temp_celsius,
            "vcf": reading.vcf,
            "density_vac": reading.density_vac,
            "density_air": reading.density_air,
            "gsv": reading.gsv,
            "mt_air": reading.mt_air,
            "bl_figure": reading.bl_figure,
            "discrepancy": reading.discrepancy,
        }
        return mapping.get(key)
    
    def _on_cell_changed(self, row: int, col: int):
        """Handle cell value change."""
        if not self.voyage:
            return
        
        item = self.tank_table.item(row, col)
        if not item:
            return
        
        tank_id_item = self.tank_table.item(row, 0)
        if not tank_id_item:
            return
        
        tank_id = tank_id_item.text()
        reading = self.voyage.get_reading(tank_id)
        if not reading:
            return
        
        # Get column info
        key, _, _, is_input, is_numeric = self.COLUMNS[col]
        
        if not is_input:
            return
        
        # Update reading
        value = item.text()
        try:
            if is_numeric and value:
                value = float(value)
            self._update_reading(reading, key, value)
            self._recalculate_tank(row, tank_id)
        except ValueError:
            pass
    
    def _update_reading(self, reading: TankReading, key: str, value):
        """Update reading field based on key."""
        if key == "parcel":
            reading.parcel = str(value) if value else ""
        elif key == "grade":
            reading.grade = str(value) if value else ""
        elif key == "receiver":
            reading.receiver = str(value) if value else ""
        elif key == "receiver_tank":
            reading.receiver_tank = str(value) if value else ""
        elif key == "ullage":
            reading.ullage = float(value) if value else None
            # Clear fill_percent so it gets recalculated from ullage
            if reading.ullage is not None:
                reading.fill_percent = None
        elif key == "fill_percent":
            reading.fill_percent = float(value) if value else None
            # Clear ullage so it gets recalculated from fill_percent
            if reading.fill_percent is not None:
                reading.ullage = None
        elif key == "temp":
            reading.temp_celsius = float(value) if value else None
        elif key == "density_vac":
            reading.density_vac = float(value) if value else None
        elif key == "bl_figure":
            reading.bl_figure = float(value) if value else None
    
    def _recalculate_tank(self, row: int, tank_id: str):
        """Recalculate values for a single tank."""
        reading = self.voyage.get_reading(tank_id)
        tank = self.tanks.get(tank_id)
        
        if not reading or not tank:
            self.status_bar.showMessage(f"Tank {tank_id}: No reading or tank data")
            return
        
        # Skip if no ullage table
        if not tank.has_ullage_table():
            self.status_bar.showMessage(f"Tank {tank_id}: No ullage table loaded. Go to Settings > Ship Configuration")
            return
        
        try:
            # Handle dual input (Ullage ↔ Fill%)
            if reading.ullage is not None:
                reading.tov = calculate_tov(reading.ullage, tank.ullage_table)
                reading.fill_percent = calculate_fill_percent(reading.tov, tank.capacity_m3)
            elif reading.fill_percent is not None:
                reading.ullage = calculate_ullage_from_percent(
                    reading.fill_percent, tank.capacity_m3, tank.ullage_table
                )
                reading.tov = calculate_tov(reading.ullage, tank.ullage_table)
            
            # Trim correction
            trim = self.draft_aft_spin.value() - self.draft_fwd_spin.value()
            if tank.has_trim_table() and reading.ullage:
                reading.gov, reading.trim_correction = apply_trim_correction(
                    reading.tov, reading.ullage, trim, tank.trim_table
                )
            else:
                reading.gov = reading.tov
                reading.trim_correction = 0
            
            # VCF and GSV
            if reading.temp_celsius and reading.density_vac:
                reading.vcf = calculate_vcf(reading.temp_celsius, reading.density_vac)
                reading.gsv = calculate_gsv(reading.gov, reading.vcf, self.vef_spin.value())
                reading.density_air = vac_to_air(reading.density_vac)
                reading.mt_air = calculate_mass(reading.gsv, reading.density_air)
                reading.mt_vac = calculate_mass(reading.gsv, reading.density_vac)
            
            # Discrepancy
            if reading.bl_figure and reading.mt_air:
                reading.discrepancy = ((reading.mt_air - reading.bl_figure) / reading.bl_figure) * 100
            
            # Warning
            if reading.fill_percent:
                warning = get_level_warning(reading.fill_percent)
                reading.warning = warning.value
            
            # Update grid
            self._update_row(row, reading)
            self._update_totals()
            
            self.status_bar.showMessage(f"Tank {tank_id}: TOV={reading.tov:.3f} m³")
            
        except Exception as e:
            self.status_bar.showMessage(f"Tank {tank_id}: Calculation error - {e}")
    
    def _update_row(self, row: int, reading: TankReading):
        """Update row with calculated values."""
        self.tank_table.blockSignals(True)
        
        for col, (key, _, _, is_input, is_numeric) in enumerate(self.COLUMNS):
            if is_input and key not in ("ullage", "fill_percent"):
                continue
            
            item = self.tank_table.item(row, col)
            if not item:
                continue
            
            value = self._get_reading_value(reading, key)
            if value is not None:
                if is_numeric:
                    if key == "ullage":
                        item.setText(f"{int(value)}" if isinstance(value, (int, float)) else str(value))
                    elif key == "vcf":
                        item.setText(f"{value:.5f}")
                    elif key == "fill_percent":
                        item.setText(f"{value:.1f}")
                    else:
                        item.setText(f"{value:.3f}")
                else:
                    item.setText(str(value))
            
            # Apply warning color to fill_percent column
            if key == "fill_percent" and reading.warning:
                if reading.warning == "high_high":
                    item.setBackground(COLOR_WARNING_CRITICAL)
                elif reading.warning == "high":
                    item.setBackground(COLOR_WARNING_HIGH)
                elif reading.warning == "low":
                    item.setBackground(COLOR_WARNING_LOW)
                else:
                    item.setBackground(COLOR_INPUT)
        
        self.tank_table.blockSignals(False)
    
    def _update_totals(self):
        """Update total GSV and MT."""
        if not self.voyage:
            return
        
        self.voyage.calculate_totals()
        self.total_gsv_label.setText(f"{self.voyage.total_gsv:.3f}")
        self.total_mt_label.setText(f"{self.voyage.total_mt:.3f}")
    
    def _on_draft_changed(self):
        """Handle draft value change."""
        trim = self.draft_aft_spin.value() - self.draft_fwd_spin.value()
        self.trim_label.setText(f"{trim:+.2f} m")
        self._recalculate_all()
    
    def _recalculate_all(self):
        """Recalculate all tanks."""
        for row in range(self.tank_table.rowCount()):
            tank_id_item = self.tank_table.item(row, 0)
            if tank_id_item:
                self._recalculate_tank(row, tank_id_item.text())
    
    # Menu actions
    def _new_voyage(self):
        """Create new voyage."""
        self.voyage = Voyage.create_new("", "", "")
        self.port_edit.clear()
        self.terminal_edit.clear()
        self.voyage_edit.clear()
        self.date_edit.setText(datetime.now().strftime("%Y-%m-%d"))
        self._populate_grid()
        self.status_bar.showMessage("New voyage created")
    
    def _open_voyage(self):
        """Open existing voyage."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Voyage", "", "JSON Files (*.json)"
        )
        if filepath:
            try:
                self.voyage = Voyage.load_from_json(filepath)
                self.port_edit.setText(self.voyage.port)
                self.terminal_edit.setText(self.voyage.terminal)
                self.voyage_edit.setText(self.voyage.voyage_number)
                self.date_edit.setText(self.voyage.date)
                self.vef_spin.setValue(self.voyage.vef)
                self.draft_aft_spin.setValue(self.voyage.drafts.aft)
                self.draft_fwd_spin.setValue(self.voyage.drafts.fwd)
                self._populate_grid()
                self.status_bar.showMessage(f"Voyage loaded: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load voyage: {e}")
    
    def _save_voyage(self):
        """Save current voyage."""
        if not self.voyage:
            return
        
        # Update voyage from UI
        self.voyage.port = self.port_edit.text()
        self.voyage.terminal = self.terminal_edit.text()
        self.voyage.voyage_number = self.voyage_edit.text()
        self.voyage.date = self.date_edit.text()
        self.voyage.vef = self.vef_spin.value()
        self.voyage.drafts.aft = self.draft_aft_spin.value()
        self.voyage.drafts.fwd = self.draft_fwd_spin.value()
        self.voyage.chief_officer = self.chief_officer_edit.text()
        self.voyage.master = self.master_edit.text()
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Voyage", "", "JSON Files (*.json)"
        )
        if filepath:
            try:
                self.voyage.save_to_json(filepath)
                self.status_bar.showMessage(f"Voyage saved: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save voyage: {e}")
    
    def _export(self, format_type: str):
        """Export voyage data."""
        if not self.voyage:
            return
        
        # Update voyage data
        self._save_voyage_data()
        
        filters = {
            "excel": "Excel Files (*.xlsx)",
            "pdf": "PDF Files (*.pdf)",
            "ascii": "Text Files (*.txt)",
            "json": "JSON Files (*.json)"
        }
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, f"Export to {format_type.upper()}", "", filters.get(format_type, "*.*")
        )
        
        if filepath:
            try:
                if format_type == "excel":
                    export_to_excel(self.voyage, filepath)
                elif format_type == "pdf":
                    export_to_pdf(self.voyage, filepath)
                elif format_type == "ascii":
                    export_ascii_report(self.voyage, filepath)
                elif format_type == "json":
                    export_stowage_plan(self.voyage, filepath)
                
                self.status_bar.showMessage(f"Exported to: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")
    
    def _save_voyage_data(self):
        """Save current UI data to voyage object."""
        if not self.voyage:
            return
        
        self.voyage.port = self.port_edit.text()
        self.voyage.terminal = self.terminal_edit.text()
        self.voyage.voyage_number = self.voyage_edit.text()
        self.voyage.date = self.date_edit.text()
        self.voyage.vef = self.vef_spin.value()
        self.voyage.drafts.aft = self.draft_aft_spin.value()
        self.voyage.drafts.fwd = self.draft_fwd_spin.value()
        self.voyage.chief_officer = self.chief_officer_edit.text()
        self.voyage.master = self.master_edit.text()
        self.voyage.calculate_totals()
    
    def _show_ship_config(self):
        """Show ship configuration dialog."""
        dialog = ShipSetupDialog(self, self.ship_config)
        if dialog.exec():
            # Get updated config
            self.ship_config = dialog.get_config()
            parsed_data = dialog.get_parsed_data()
            
            # Reload tanks with updated config
            for tank_config in self.ship_config.tanks:
                # Create tank if not exists
                if tank_config.id not in self.tanks:
                    tank = Tank(
                        id=tank_config.id,
                        name=tank_config.name,
                        capacity_m3=tank_config.capacity_m3
                    )
                    self.tanks[tank_config.id] = tank
                else:
                    tank = self.tanks[tank_config.id]
                
                tank.capacity_m3 = tank_config.capacity_m3
                
                # Load tables from parsed template data
                if parsed_data:
                    # Load ullage table directly from DataFrame
                    if tank_config.id in parsed_data.ullage_tables:
                        tank.ullage_table = parsed_data.ullage_tables[tank_config.id]
                        # Update capacity from table's max volume
                        if tank.has_ullage_table():
                            tank.capacity_m3 = tank.get_max_volume()
                            tank_config.capacity_m3 = tank.capacity_m3
                    
                    # Load trim table directly from DataFrame
                    if tank_config.id in parsed_data.trim_tables:
                        tank.trim_table = parsed_data.trim_tables[tank_config.id]
                
                # Legacy: Load CSV tables if paths provided
                elif tank_config.ullage_table_path:
                    tank.load_ullage_table(tank_config.ullage_table_path)
                    if tank.has_ullage_table():
                        tank.capacity_m3 = tank.get_max_volume()
                        tank_config.capacity_m3 = tank.capacity_m3
                    
                    if tank_config.trim_table_path:
                        tank.load_trim_table(tank_config.trim_table_path)
            
            # Save config for next startup
            self._save_ship_config()
            
            # Refresh grid
            self._populate_grid()
            self._recalculate_all()
            self.status_bar.showMessage(f"Ship configuration saved: {len(self.ship_config.tanks)} tanks loaded")
    
    def _show_preferences(self):
        """Show preferences dialog."""
        dialog = PreferencesDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            # Apply settings
            if settings.get("language"):
                set_language(settings["language"])
                # Note: Full UI refresh would require restart
                self.status_bar.showMessage(
                    f"Language changed to {settings['language']}. Restart for full effect."
                )
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About UllageMaster",
            "UllageMaster v1.0.0\n\n"
            "Oil Tanker Cargo Calculator\n\n"
            "Features:\n"
            "• Ullage-to-volume conversion\n"
            "• Trim corrections\n"
            "• ASTM 54B VCF calculation\n"
            "• Multi-format export\n"
            "• English/Turkish UI"
        )
