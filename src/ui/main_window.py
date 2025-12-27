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
from PyQt6.QtCore import Qt, QSize, QSettings
from PyQt6.QtGui import QColor, QFont, QAction, QKeySequence, QKeyEvent, QBrush

from i18n import t, set_language, get_current_language
from models import ShipConfig, Tank, TankReading, Voyage, DraftReadings
from core import (
    calculate_tov, calculate_fill_percent, calculate_ullage_from_percent,
    apply_trim_correction, calculate_vcf, calculate_gsv, calculate_mass,
    get_level_warning, LevelWarning, vac_to_air
)
from export import (
    export_stowage_plan, export_ascii_report, 
    export_to_excel, export_to_pdf, generate_stowage_plan,
    export_template_report, get_template_path
)
from ui.dialogs import ShipSetupDialog, ShipSetupWizard, PreferencesDialog
from utils import config_exists, load_config, save_config
import pandas as pd

from .styles import (
    COLOR_CELL_INPUT, COLOR_CELL_CALCULATED, COLOR_CELL_TEXT,
    COLOR_DANGER, COLOR_WARNING_HIGH, COLOR_WARNING_LOW, COLOR_WINDOW_BG
)
from .widgets.delegates import TankGridDelegate
from .widgets.flow_layout import FlowLayout

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
    # Only Ullage, Temp, and Parcel are user-editable
    COLUMNS = [
        ("tank_id", "Tank", 60, False, False),
        ("parcel", "Parcel", 70, True, False),        # Dropdown
        ("grade", "Grade", 100, False, False),        # Auto from parcel
        ("receiver", "Receiver", 100, False, False),  # Auto from parcel
        ("receiver_tank", "Tank No", 60, False, False),
        ("ullage", "Ullage", 70, True, True),         # User input
        ("temp", "Temp", 60, True, True),             # User input
        ("fill_percent", "% Fill", 60, True, True),   # Editable - bidirectional with Ullage
        ("trim_corr", "Trim Corr", 70, False, True),
        ("corrected_ullage", "Corr Ullage", 80, False, True),
        ("tov", "TOV", 90, False, True),
        ("therm_corr", "Therm.Corr", 80, False, True),  # Thermal correction factor
        ("gov", "GOV", 90, False, True),                # TOV * Therm.Corr
        ("vcf", "VCF", 80, False, True),
        ("gsv", "GSV", 90, False, True),              # GSV = GOV * VCF
        ("density_vac", "VAC Dens", 80, False, True), # Auto from parcel
        ("mt_vac", "MT(VAC)", 90, False, True),       # MT(VAC) = GSV * VAC Dens
        ("density_air", "Air Dens", 80, False, True),
        ("mt_air", "MT (Air)", 90, False, True),
        ("tank_id_end", "Tank", 60, False, False),    # Duplicate tank column for visibility
    ]
    
    def __init__(self):
        super().__init__()
        
        # Data
        self.ship_config: Optional[ShipConfig] = None
        self.tanks: Dict[str, Tank] = {}
        self.voyage: Optional[Voyage] = None
        self.tank_table = None
        
        # Persistence
        self.settings = QSettings("UllageMaster", "UllageMaster")
        self.last_dir = self.settings.value("last_dir", "")
        
        # Setup UI
        self.setWindowTitle("UllageMaster - Tanker Cargo Calculator")
        self.setMinimumSize(1400, 800)
        
        self._create_menu()
        self._create_central_widget()
        self._create_status_bar()
        
        # Load default or create new
        self._init_default_data()
    
    def _update_last_dir(self, filepath: str):
        """Update last used directory in settings."""
        if not filepath:
            return
        self.last_dir = str(Path(filepath).parent)
        self.settings.setValue("last_dir", self.last_dir)

    
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
        
        parcels_action = QAction("Edit Parcels...", self)
        parcels_action.triggered.connect(self._edit_parcels)
        file_menu.addAction(parcels_action)
        
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
        
        visual_action = QAction("Visual Stowage Plan (PDF)", self)
        visual_action.triggered.connect(lambda: self._export("visual"))
        export_menu.addAction(visual_action)
        
        export_menu.addSeparator()
        
        template_action = QAction("Template Report (XLSM)", self)
        template_action.triggered.connect(self._export_template_report)
        export_menu.addAction(template_action)
        
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
        
        settings_menu.addSeparator()
        
        import_config_action = QAction("Import Configuration...", self)
        import_config_action.triggered.connect(self._import_config)
        settings_menu.addAction(import_config_action)
        
        delete_config_action = QAction("Delete Configuration (Fresh Start)", self)
        delete_config_action.triggered.connect(self._delete_config)
        settings_menu.addAction(delete_config_action)
        
        settings_menu.addSeparator()
        
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
        layout.setContentsMargins(10, 5, 10, 10)  # Reduced top margin
        layout.setSpacing(5)  # Tighter spacing between elements
        
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
        group = QGroupBox("")
        layout = QGridLayout(group)
        layout.setContentsMargins(5, 2, 5, 2)  # Tighter margins
        layout.setVerticalSpacing(2)  # Minimal vertical spacing
        
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
        self.date_edit.setText(datetime.now().strftime("%d-%m-%Y"))
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
        self.draft_aft_spin.setSingleStep(0.25)
        self.draft_aft_spin.valueChanged.connect(self._on_draft_changed)
        layout.addWidget(self.draft_aft_spin, 1, 3)
        
        layout.addWidget(QLabel(t("draft_fwd", "header")), 1, 4)
        self.draft_fwd_spin = QDoubleSpinBox()
        self.draft_fwd_spin.setDecimals(2)
        self.draft_fwd_spin.setRange(0, 30)
        self.draft_fwd_spin.setSingleStep(0.25)
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
        table.itemSelectionChanged.connect(self._update_selection_stats)
        
        # Enable editing - but NOT on selection change (allows multiselect)
        table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked |
            QAbstractItemView.EditTrigger.AnyKeyPressed |
            QAbstractItemView.EditTrigger.EditKeyPressed
        )
        
        # Connect signals
        table.cellChanged.connect(self._on_cell_changed)
        
        # Style header
        header = table.horizontalHeader()
        header.setStyleSheet(
            "QHeaderView::section { background-color: #4472C4; color: white; font-weight: bold; }"
        )
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setMinimumSectionSize(50) # Ensure columns don't get too small to click
        
        # Install event filter for bulk input
        table.installEventFilter(self)
        
        # Enable context menu
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_context_menu)
        
        # Apply custom delegate for row separators
        # table.setItemDelegate(TankGridDelegate(table)) # Global delegate
        # However, we might want to keep default delegates for editors...
        # QStyledItemDelegate handles editors fine via createEditor.
        delegate = TankGridDelegate(table)
        table.setItemDelegate(delegate)
        
        return table
    
    def eventFilter(self, obj, event):
        """Handle key events for bulk input on selected cells."""
        if obj == self.tank_table and event.type() == event.Type.KeyPress:
            # Handle Ctrl+C for multi-cell copy
            if event.matches(QKeySequence.StandardKey.Copy):
                self._handle_copy()
                return True
            
            selected = self.tank_table.selectedItems()
            # print(f"DEBUG: Key {repr(event.text())} Selected {len(selected)}")
            if len(selected) > 1:
                # Multiple cells selected - handle bulk input
                text = event.text()
                # Check for printable characters (numbers, dot, comma, minus, plus)
                # This handles both main keyboard and numpad
                if text and (text.isalnum() or text in ".-+,"):
                     self._handle_bulk_input(selected, text)
                     return True
        return super().eventFilter(obj, event)
    
    def _handle_copy(self):
        """Handle Ctrl+C - copy selected cells to clipboard in Excel-compatible format."""
        selection = self.tank_table.selectedRanges()
        if not selection:
            return
        
        # Combine all selection ranges
        all_rows = set()
        all_cols = set()
        for range_ in selection:
            for row in range(range_.topRow(), range_.bottomRow() + 1):
                all_rows.add(row)
            for col in range(range_.leftColumn(), range_.rightColumn() + 1):
                all_cols.add(col)
        
        # Sort to maintain order
        rows = sorted(all_rows)
        cols = sorted(all_cols)
        
        # Build tab-separated text
        lines = []
        for row in rows:
            row_data = []
            for col in cols:
                item = self.tank_table.item(row, col)
                row_data.append(item.text() if item else "")
            lines.append("\t".join(row_data))
        
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(lines))
        
        # Show feedback
        cell_count = len(rows) * len(cols)
        self.status_bar.showMessage(f"Copied {cell_count} cells to clipboard")
    
    def _handle_bulk_input(self, selected_items, initial_char=""):
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
        
        # Prompt for value (dialog opens empty, user types full value)
        if is_numeric:
            text, ok = QInputDialog.getText(
                self, f"Bulk Input - {header}",
                f"Enter value for all {len(selected_items)} selected cells:"
            )
            if ok and text:
                try:
                    value = float(text)
                except ValueError:
                    QMessageBox.warning(self, "Invalid Input", "Please enter a valid number.")
                    return
            else:
                return
        else:
            value, ok = QInputDialog.getText(
                self, f"Bulk Input - {header}",
                f"Enter value for all {len(selected_items)} selected cells:"
            )
            if not ok:
                return
        
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
        group = QGroupBox("")
        main_layout = QVBoxLayout(group)
        main_layout.setContentsMargins(5, 2, 5, 2)  # Tighter margins
        main_layout.setSpacing(2)  # Minimal spacing
        
        # Row 1: Grand totals and officers
        top_row = QHBoxLayout()
        
        # Totals
        top_row.addWidget(QLabel(t("total_gsv", "footer")))
        self.total_gsv_label = QLabel("0.000")
        self.total_gsv_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        top_row.addWidget(self.total_gsv_label)
        
        top_row.addSpacing(30)
        
        top_row.addWidget(QLabel(t("total_mt", "footer")))
        self.total_mt_label = QLabel("0.000")
        self.total_mt_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        top_row.addWidget(self.total_mt_label)
        
        top_row.addStretch()
        
        # Officers
        top_row.addWidget(QLabel(t("chief_officer", "footer")))
        self.chief_officer_edit = QLineEdit()
        self.chief_officer_edit.setMaximumWidth(150)
        self.chief_officer_edit.editingFinished.connect(self._save_officer_names)
        top_row.addWidget(self.chief_officer_edit)
        
        top_row.addWidget(QLabel(t("master", "footer")))
        self.master_edit = QLineEdit()
        self.master_edit.setMaximumWidth(150)
        self.master_edit.editingFinished.connect(self._save_officer_names)
        top_row.addWidget(self.master_edit)
        
        main_layout.addLayout(top_row)
        
        # Separator between officers and parcel summary
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #475569; max-height: 1px;")
        main_layout.addWidget(separator)
        
        # Row 2: Parcel summary (MT AIR per parcel) - Flow layout for wrapping
        self.parcel_summary_container = QWidget()
        self.parcel_summary_layout = FlowLayout(self.parcel_summary_container)
        self.parcel_summary_layout.setContentsMargins(0, 2, 0, 0)  # Small top margin after separator
        
        # Add label
        self.parcel_summary_layout.addWidget(QLabel("Parcel Totals (MT Air):"))
        
        main_layout.addWidget(self.parcel_summary_container)
        
        # Store parcel labels for dynamic updates
        self.parcel_mt_labels = {}  # {parcel_id: QLabel}
        
        return group
    
    def _create_status_bar(self):
        """Create status bar with selection stats."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add selection stats labels
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 0, 20, 0)
        
        self.sel_total_label = QLabel("SELECTED TOTAL: 0.000")
        self.sel_total_label.setStyleSheet("font-weight: bold; color: #38bdf8; margin-right: 15px;")
        
        self.sel_avg_label = QLabel("SELECTED AVERAGE: 0.000") 
        self.sel_avg_label.setStyleSheet("font-weight: bold; color: #38bdf8;")
        
        stats_layout.addWidget(self.sel_total_label)
        stats_layout.addWidget(self.sel_avg_label)
        
        self.status_bar.addPermanentWidget(stats_widget)
        self.status_bar.showMessage("Ready")
    
    def _init_default_data(self):
        """Initialize with default ship configuration."""
        # Single load pattern: try to load config directly
        self.ship_config = load_config()
        
        if self.ship_config and self.ship_config.tanks:
            # Config loaded successfully
            self.status_bar.showMessage(f"Loaded ship config: {self.ship_config.ship_name}")
            self._load_tank_tables()
            # Load officer names from config
            self.chief_officer_edit.setText(self.ship_config.chief_officer)
            self.master_edit.setText(self.ship_config.master)
        else:
            # No config or empty - show setup wizard
            self._show_first_time_setup()
        
        # Create voyage
        self.voyage = Voyage.create_new("001/2024", "EXAMPLE PORT", "EXAMPLE TERMINAL")
        
        # Populate grid
        self._populate_grid()
    
    def _show_first_time_setup(self):
        """Show the ship configuration wizard for first-time setup."""
        from ui.dialogs import ShipSetupWizard
        from PyQt6.QtWidgets import QWizard
        
        wizard = ShipSetupWizard(self)
        if wizard.exec() == QWizard.DialogCode.Accepted:
            self.ship_config = wizard.get_config()
            if self.ship_config:
                # Save the new config
                save_config(self.ship_config)
                # Load tank objects
                self._load_tank_tables()
                self.status_bar.showMessage(f"Ship configured: {self.ship_config.ship_name}")
        else:
            # User cancelled - create empty config for now
            self.ship_config = ShipConfig.create_empty("New Ship")
    
    def _get_config_path(self) -> Path:
        """Get path to ship config file."""
        # Get the data/config directory relative to src
        src_dir = Path(__file__).parent.parent
        config_dir = src_dir.parent / "data" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "ship_config.json"
    
    def _load_tank_tables(self):
        """Load ullage and trim tables for all tanks from embedded JSON data."""
        if not self.ship_config:
            return
        
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
            
            # Load ullage table from embedded data
            if tank_config.ullage_table:
                # Convert list of dicts to DataFrame
                df = pd.DataFrame(tank_config.ullage_table)
                # Ensure correct column names (ullage_cm for calculations)
                if 'ullage_mm' in df.columns:
                    df['ullage_cm'] = df['ullage_mm'] / 10.0
                tank.ullage_table = df
                # Use stored capacity if set, otherwise derive from ullage table max
                if tank_config.capacity_m3 > 0:
                    tank.capacity_m3 = tank_config.capacity_m3
                elif tank.has_ullage_table():
                    tank.capacity_m3 = tank.get_max_volume()
            
            # Load trim table from embedded data
            if tank_config.trim_table:
                df = pd.DataFrame(tank_config.trim_table)
                if 'ullage_mm' in df.columns:
                    df['ullage_cm'] = df['ullage_mm'] / 10.0
                tank.trim_table = df
            
            # Load thermal table from embedded data
            if tank_config.thermal_table:
                df = pd.DataFrame(tank_config.thermal_table)
                if 'temp_c' in df.columns:
                    df = df.sort_values('temp_c').reset_index(drop=True)
                tank.thermal_table = df
    
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
            
            # Populate tables from config
            if hasattr(tank, 'set_ullage_table'):
                tank.set_ullage_table(tank_config.ullage_table)
            if hasattr(tank, 'set_trim_table'):
                tank.set_trim_table(tank_config.trim_table)
            if hasattr(tank, 'set_thermal_table'):
                tank.set_thermal_table(tank_config.thermal_table)
            
            # Create TankReading if not exists
            if tank_config.id not in self.voyage.tank_readings:
                self.voyage.add_reading(TankReading(tank_id=tank_config.id))
            
            # Force recalculate to update derived values (GOV, Therm.Corr) with latest logic
            self._recalculate_tank(row, tank_config.id)
            
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
                            item.setText(f"{value:.1f}" if isinstance(value, (int, float)) else str(value))
                        elif key == "fill_percent":
                            item.setText(f"{value:.1f}" if isinstance(value, float) else str(value))
                        elif key in ("temp", "corrected_ullage", "trim_corr"):
                             item.setText(f"{value:.1f}" if isinstance(value, float) else str(value))
                        elif key in ("density_vac", "density_air"):
                            item.setText(f"{value:.4f}" if isinstance(value, float) else str(value))
                        elif key == "vcf":
                            item.setText(f"{value:.5f}" if isinstance(value, float) else str(value))
                        elif key == "therm_corr":
                            item.setText(f"{value:.6f}" if isinstance(value, float) else str(value))
                        else:
                            item.setText(f"{value:.3f}" if isinstance(value, float) else str(value))
                    else:
                        item.setText(str(value))
                
                # Set cell properties
                item.setForeground(COLOR_TEXT)  # Set black text color
                
                # Get parcel-based background color
                parcel_color = self._get_parcel_bg_color(reading.parcel_id, is_input and key != "parcel")
                item.setData(Qt.ItemDataRole.BackgroundRole, QBrush(parcel_color))
                
                # Parcel column should be read-only to force context menu usage
                if not (is_input and key != "parcel"):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                self.tank_table.setItem(row, col, item)
        
        self.tank_table.blockSignals(False)
    
    def _get_parcel_bg_color(self, parcel_id: str, is_input_cell: bool) -> QColor:
        """Get background color for a cell based on its parcel.
        
        Returns a tinted color based on the parcel's color.
        Input cells get a lighter tint, calculated cells get a slightly stronger tint.
        """
        if not parcel_id:
            # No parcel assigned - use default colors
            return COLOR_INPUT if is_input_cell else COLOR_CALCULATED
        
        # Get parcel color
        if parcel_id == "0":  # SLOP
            base_color = QColor("#9CA3AF")  # Gray
        else:
            parcel = self._get_parcel(parcel_id)
            if parcel and parcel.color:
                base_color = QColor(parcel.color)
            else:
                return COLOR_INPUT if is_input_cell else COLOR_CALCULATED
        
        # Create tinted version (lighter for better readability)
        # Input cells: lighter tint, Calculated cells: slightly stronger
        if is_input_cell:
            # Lighter tint for input cells (blend with white)
            alpha = 0.40  # 40% parcel color, 60% white
        else:
            # Stronger tint for calculated cells
            alpha = 0.50  # 50% parcel color, 50% white
        
        r = int(base_color.red() * alpha + 15 * (1 - alpha)) # Blend with #0f172a (approx 15, 23, 42)
        g = int(base_color.green() * alpha + 23 * (1 - alpha))
        b = int(base_color.blue() * alpha + 42 * (1 - alpha))
        
        return QColor(r, g, b)

    def _get_reading_value(self, reading: TankReading, key: str):
        """Get value from reading based on column key."""
        if key == "tank_id_end":
            return reading.tank_id
        # Get parcel for deriving grade/receiver
        parcel = None
        grade = ""
        receiver = ""
        
        if reading.parcel_id:
            if reading.parcel_id == "0":
                grade = "SLOP"
                receiver = ""
            else:
                parcel = self._get_parcel(reading.parcel_id)
                if parcel:
                    grade = parcel.name
                    receiver = parcel.receiver
        
        mapping = {
            "tank_id": reading.tank_id,
            "parcel": reading.parcel_id,  # Shows "0" for SLOP
            "grade": grade,
            "receiver": receiver,
            "receiver_tank": reading.tank_id,  # Default to tank_id
            "ullage": reading.ullage,
            "fill_percent": reading.fill_percent,
            "trim_corr": reading.trim_correction,
            "corrected_ullage": reading.corrected_ullage,
            "tov": reading.tov,
            "therm_corr": reading.therm_corr,
            "gov": reading.gov,
            "temp": reading.temp_celsius,
            "vcf": reading.vcf,
            "density_vac": reading.density_vac,
            "mt_vac": reading.mt_vac,
            "density_air": reading.density_air,
            "gsv": reading.gsv,
            "mt_air": reading.mt_air,
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
            reading.parcel_id = str(value) if value else ""
            # Sync density from parcel
            parcel = self._get_parcel(reading.parcel_id)
            if parcel:
                reading.density_vac = parcel.density_vac
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
            # NOTE: User inputs ullage in cm, config tables use mm
            # Track whether user entered ullage or fill% to avoid overwriting their input
            user_entered_fill_percent = reading.fill_percent is not None and reading.ullage is None
            
            if reading.ullage is not None:
                measured_ullage_cm = reading.ullage  # User input is in cm
                measured_ullage_mm = measured_ullage_cm * 10  # Convert to mm for table lookup
            elif reading.fill_percent is not None:
                # Calculate ullage from fill percent first (returns cm from table)
                measured_ullage_cm = calculate_ullage_from_percent(
                    reading.fill_percent, tank.capacity_m3, tank.ullage_table
                )
                reading.ullage = measured_ullage_cm
                measured_ullage_mm = measured_ullage_cm * 10
            else:
                measured_ullage_mm = None
            
            if measured_ullage_mm is not None:
                # Apply trim correction to ullage
                trim = self.draft_fwd_spin.value() - self.draft_aft_spin.value()
                if tank.has_trim_table():
                    # Get trim correction value in mm (config tables store values in mm)
                    from core.calculations import get_trim_correction
                    trim_corr_mm = get_trim_correction(
                        measured_ullage_mm, trim, tank.trim_table
                    )
                    # Store in cm for display (mm / 10)
                    reading.trim_correction = trim_corr_mm / 10.0
                    corrected_ullage_mm = measured_ullage_mm + trim_corr_mm
                else:
                    reading.trim_correction = 0
                    corrected_ullage_mm = measured_ullage_mm
                
                # Store corrected ullage in cm for display
                reading.corrected_ullage = corrected_ullage_mm / 10  # mm → cm
                
                # Calculate TOV from corrected ullage (table uses mm, so convert)
                reading.tov = calculate_tov(corrected_ullage_mm / 10, tank.ullage_table)  # cm for lookup
                
                # Thermal correction (from table if available, else 1.0)
                if reading.temp_celsius is not None:
                    reading.therm_corr = tank.get_thermal_factor(reading.temp_celsius)
                else:
                    reading.therm_corr = 1.0
                
                # GOV = TOV * Therm.Corr
                reading.gov = reading.tov * reading.therm_corr
                
                # Only recalculate fill% if user entered ullage (not when they entered fill%)
                if not user_entered_fill_percent:
                    reading.fill_percent = calculate_fill_percent(reading.tov, tank.capacity_m3)
                
                # VCF and GSV - only calculate when we have fresh GOV
                if reading.temp_celsius and reading.density_vac:
                    reading.vcf = calculate_vcf(reading.temp_celsius, reading.density_vac)
                    
                    # Rounding to match display and standard practice so GSV = GOV * VCF matches visual check
                    # GOV -> 3 decimal places
                    # VCF -> 5 decimal places
                    gov_rounded = round(reading.gov, 3)
                    vcf_rounded = round(reading.vcf, 5)
                    
                    reading.gsv = gov_rounded * vcf_rounded  # GSV = GOV * VCF
                    
                    # Air density = Vac Density - 0.0011 (for g/cm³) or - 1.1 (for kg/m³)
                    if reading.density_vac < 10:  # g/cm³ format
                        reading.density_air = reading.density_vac - 0.0011
                    else:  # kg/m³ format
                        reading.density_air = reading.density_vac - 1.1
                    
                    reading.mt_air = calculate_mass(reading.gsv, reading.density_air)
                    reading.mt_vac = calculate_mass(reading.gsv, reading.density_vac)
            
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
        """Update row with calculated values and apply parcel-based colors.
        
        NOTE: Signals are blocked to prevent recursion loops (update -> signal -> recalc -> update).
        We preserve the original blocking state to avoid interfering with callers who may have
        already blocked signals (e.g., _populate_grid).
        """
        # Preserve original blocking state
        was_blocked = self.tank_table.signalsBlocked()
        self.tank_table.blockSignals(True)
        try:
            for col, (key, _, _, is_input, is_numeric) in enumerate(self.COLUMNS):
                item = self.tank_table.item(row, col)
                if not item:
                    continue
                
                # Update background color based on parcel (for ALL cells)
                parcel_color = self._get_parcel_bg_color(reading.parcel_id, is_input and key != "parcel")
                item.setData(Qt.ItemDataRole.BackgroundRole, QBrush(parcel_color))
                
                # Only update text for non-input columns (except ullage, fill_percent, parcel)
                # AND update inputs if they are calculated/derived to keep UI in sync
                # We update EVERYTHING to ensure consistency
                
                value = self._get_reading_value(reading, key)
                if value is not None:
                    if is_numeric:
                        if key == "ullage":
                            item.setText(f"{value:.1f}" if isinstance(value, (int, float)) else str(value))
                        elif key == "vcf":
                            item.setText(f"{value:.5f}")
                        elif key == "therm_corr":
                            item.setText(f"{value:.6f}")
                        elif key in ("density_vac", "density_air"):
                            item.setText(f"{value:.4f}")
                        elif key in ("fill_percent", "temp", "corrected_ullage", "trim_corr"):
                            item.setText(f"{value:.1f}")
                        else:
                            item.setText(f"{value:.3f}")
                    else:
                        item.setText(str(value))
        finally:
            # Restore original blocking state, not unconditionally unblock
            self.tank_table.blockSignals(was_blocked)

    
    def _update_totals(self):
        """Update total GSV and MT, plus per-parcel MT AIR."""
        if not self.voyage:
            return
        
        self.voyage.calculate_totals()
        self.total_gsv_label.setText(f"{self.voyage.total_gsv:.3f}")
        self.total_mt_label.setText(f"{self.voyage.total_mt:.3f}")
        
        # Calculate per-parcel MT AIR totals
        parcel_totals = {}  # {parcel_id: {name, receiver, mt_air}}
        
        for reading in self.voyage.tank_readings.values():
            pid = reading.parcel_id
            if not pid:
                continue
            
            if pid not in parcel_totals:
                # Get parcel name and receiver
                if pid == "0":
                    name = "SLOP"
                    receiver = ""
                else:
                    name = pid
                    receiver = ""
                    for p in self.voyage.parcels:
                        if p.id == pid:
                            name = p.name or pid
                            receiver = p.receiver or ""
                            break
                parcel_totals[pid] = {'name': name, 'receiver': receiver, 'mt_air': 0.0}
            
            parcel_totals[pid]['mt_air'] += reading.mt_air or 0.0
        
        # Clear existing parcel labels (except the header label at index 0)
        # Note: We now use layout.count() and takeAt() on the container's layout
        while self.parcel_summary_layout.count() > 1:
            item = self.parcel_summary_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        
        # Remove stored labels
        self.parcel_mt_labels.clear()
        
        # Add parcel labels
        for pid, data in parcel_totals.items():
            # Format: "Grade (Receiver): MT value" or "Grade: MT value" if no receiver
            if data['receiver']:
                label_text = f"{data['name']} ({data['receiver']}): {data['mt_air']:.3f} MT"
            else:
                label_text = f"{data['name']}: {data['mt_air']:.3f} MT"
            # Retrieve parcel object to get color
            parcel_color = "#9CA3AF" # Default gray for Slop
            text_color = "black"
            
            if pid != "0":
                 for p in self.voyage.parcels:
                    if p.id == pid:
                        if p.color:
                            parcel_color = p.color
                        break
            
            label = QLabel(label_text)
            # Styling: colored box with padding, rounded corners, and black text
            label.setStyleSheet(f"""
                background-color: {parcel_color}; 
                color: black;
                font-weight: bold; 
                padding: 4px 8px; 
                border-radius: 4px;
                margin-left: 10px;
            """)
            self.parcel_summary_layout.addWidget(label)
            self.parcel_mt_labels[pid] = label
    
    def _on_draft_changed(self):
        """Handle draft value change."""
        trim = self.draft_fwd_spin.value() - self.draft_aft_spin.value()
        self.trim_label.setText(f"{trim:+.2f} m")
        self._recalculate_all()
    
    def _recalculate_all(self):
        """Recalculate all tanks."""
        for row in range(self.tank_table.rowCount()):
            tank_id_item = self.tank_table.item(row, 0)
            if tank_id_item:
                self._recalculate_tank(row, tank_id_item.text())
    
    def _save_officer_names(self):
        """Save officer names to ship config whenever they change."""
        if not self.ship_config:
            return
        
        chief_officer = self.chief_officer_edit.text().strip()
        master = self.master_edit.text().strip()
        
        # Only save if changed
        if self.ship_config.chief_officer != chief_officer or self.ship_config.master != master:
            self.ship_config.chief_officer = chief_officer
            self.ship_config.master = master
            save_config(self.ship_config)
            self.status_bar.showMessage("Officer names saved", 2000)
    
    # Menu actions
    def _new_voyage(self):
        """Create new voyage."""
        self.voyage = Voyage.create_new("", "", "")
        self.port_edit.clear()
        self.terminal_edit.clear()
        self.voyage_edit.clear()
        self.date_edit.setText(datetime.now().strftime("%d-%m-%Y"))
        self._populate_grid()
        self.status_bar.showMessage("New voyage created")
    
    def _open_voyage(self):
        """Open existing voyage."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Voyage", self.last_dir, "JSON Files (*.json)"
        )
        if filepath:
            self._update_last_dir(filepath)
            try:
                self.voyage = Voyage.load_from_json(filepath)
                
                # Block signals to prevent premature recalculations during load
                self.port_edit.blockSignals(True)
                self.terminal_edit.blockSignals(True)
                self.voyage_edit.blockSignals(True)
                self.date_edit.blockSignals(True)
                self.vef_spin.blockSignals(True)
                self.draft_aft_spin.blockSignals(True)
                self.draft_fwd_spin.blockSignals(True)
                
                self.port_edit.setText(self.voyage.port)
                self.terminal_edit.setText(self.voyage.terminal)
                self.voyage_edit.setText(self.voyage.voyage_number)
                self.date_edit.setText(self.voyage.date)
                self.vef_spin.setValue(self.voyage.vef)
                self.draft_aft_spin.setValue(self.voyage.drafts.aft)
                self.draft_fwd_spin.setValue(self.voyage.drafts.fwd)
                
                # Unblock signals after setting values
                self.port_edit.blockSignals(False)
                self.terminal_edit.blockSignals(False)
                self.voyage_edit.blockSignals(False)
                self.date_edit.blockSignals(False)
                self.vef_spin.blockSignals(False)
                self.draft_aft_spin.blockSignals(False)
                self.draft_fwd_spin.blockSignals(False)
                
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
            self, "Save Voyage", self.last_dir, "JSON Files (*.json)"
        )
        if filepath:
            self._update_last_dir(filepath)
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
        
        # Prepare default filename for export
        default_file = ""
        if format_type == "visual":
            default_file = f"stowage_plan_{self.voyage.voyage_number.replace('/', '-')}.pdf"
        
        # Combine last_dir with default_file if provided
        initial_path = str(Path(self.last_dir) / default_file) if default_file else self.last_dir
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, f"Export to {format_type.upper()}", initial_path, filters.get(format_type, "*.*")
        )
        
        if filepath:
            self._update_last_dir(filepath)
            try:
                if format_type == "excel":
                    export_to_excel(self.voyage, filepath)
                elif format_type == "pdf":
                    export_to_pdf(self.voyage, filepath)
                    self.status_bar.showMessage(f"Exported to: {filepath}")
                elif format_type == "ascii":
                    export_ascii_report(self.voyage, filepath)
                    self.status_bar.showMessage(f"Exported to: {filepath}")
                elif format_type == "json":
                    success = export_stowage_plan(self.voyage, filepath)
                    if success:
                        self.status_bar.showMessage(f"Exported to JSON: {filepath}")
                        QMessageBox.information(self, t("success", "dialog"), f"Exported to {filepath}")
                    else:
                        QMessageBox.warning(self, t("error", "dialog"), "Export failed")
                elif format_type == "visual":
                    success = generate_stowage_plan(self.voyage, filepath, 
                                                  self.ship_config.ship_name if self.ship_config else "")
                    if success:
                        self.status_bar.showMessage(f"Exported Visual Stowage: {filepath}")
                        QMessageBox.information(self, t("success", "dialog"), f"Exported to {filepath}")
                    else:
                        QMessageBox.warning(self, t("error", "dialog"), "Export failed")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")
    
    def _export_template_report(self):
        """Export grid data to a copy of the XLSM template."""
        if not self.voyage:
            QMessageBox.warning(self, "Warning", "No voyage data to export")
            return
        
        # Check if template exists
        template_path = get_template_path()
        if not template_path.exists():
            QMessageBox.warning(
                self, "Template Not Found",
                f"Template file not found:\n{template_path}\n\n"
                "Please place your TEMPLATE.XLSM file in the TEMPLATE folder."
            )
            return
        
        # Prompt for save location
        default_name = f"{self.voyage.voyage_number.replace('/', '-')}_report.xlsm"
        initial_path = str(Path(self.last_dir) / default_name)
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Template Report", 
            initial_path, 
            "Excel Macro Files (*.xlsm)"
        )
        
        if not filepath:
            return
        
        self._update_last_dir(filepath)

        
        # Get column keys from COLUMNS definition
        column_keys = [col[0] for col in self.COLUMNS]
        
        # Get draft values
        draft_aft = self.draft_aft_spin.value()
        draft_fwd = self.draft_fwd_spin.value()
        
        success = export_template_report(self.voyage, filepath, column_keys, draft_aft, draft_fwd)
        
        if success:
            self.status_bar.showMessage(f"Exported Template Report: {filepath}")
            QMessageBox.information(self, t("success", "dialog"), f"Exported to {filepath}")
        else:
            QMessageBox.warning(self, t("error", "dialog"), "Export failed. Check console for details.")
    
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
        from ui.dialogs import ConfigEditorDialog
        
        # If config exists and has tanks, show editor; otherwise show wizard
        if self.ship_config and self.ship_config.tanks:
            dialog = ConfigEditorDialog(self.ship_config, self)
            if dialog.exec():
                # Reload tanks from updated config
                self._load_tank_tables()
                self._populate_grid()
                self._recalculate_all()
                self.status_bar.showMessage(f"Configuration updated: {self.ship_config.ship_name}")
        else:
            # No config - show wizard
            self._show_first_time_setup()
            if self.ship_config:
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
    
    def _import_config(self):
        """Import configuration from an external JSON file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Configuration", self.last_dir, "JSON Files (*.json)"
        )
        if filepath:
            self._update_last_dir(filepath)
            try:
                imported_config = ShipConfig.load_from_json(filepath)
                if imported_config and imported_config.tanks:
                    # Confirm import
                    reply = QMessageBox.question(
                        self, "Import Configuration",
                        f"Import configuration for '{imported_config.ship_name}' "
                        f"with {len(imported_config.tanks)} tanks?\n\n"
                        "This will replace your current configuration.",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self.ship_config = imported_config
                        save_config(self.ship_config)
                        self.tanks.clear()
                        self._load_tank_tables()
                        self._populate_grid()
                        self._recalculate_all()
                        self.status_bar.showMessage(
                            f"Imported configuration: {self.ship_config.ship_name}"
                        )
                else:
                    QMessageBox.warning(
                        self, "Import Error",
                        "The selected file does not contain a valid ship configuration."
                    )
            except Exception as e:
                QMessageBox.critical(
                    self, "Import Error",
                    f"Failed to import configuration:\n{e}"
                )
    
    def _delete_config(self):
        """Delete current configuration and start fresh."""
        reply = QMessageBox.warning(
            self, "Delete Configuration",
            "Are you sure you want to delete the current configuration?\n\n"
            "This will remove all ship and tank data and cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            from utils import delete_config
            if delete_config():
                # Clear current data
                self.ship_config = None
                self.tanks.clear()
                self.voyage = None
                
                # Show wizard for fresh start
                self._show_first_time_setup()
                
                if self.ship_config:
                    self.voyage = Voyage.create_new("001/2024", "", "")
                    self._populate_grid()
                    self.status_bar.showMessage("Configuration deleted. New configuration created.")
                else:
                    self.status_bar.showMessage("Configuration deleted.")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete configuration.")
    
    def _show_context_menu(self, position):
        """Show context menu for the table."""
        index = self.tank_table.indexAt(position)
        if not index.isValid():
            return
        
        row = index.row()
        col = index.column()
        
        # Check if it's the parcel column
        parcel_col_idx = -1
        for i, (key, _, _, _, _) in enumerate(self.COLUMNS):
            if key == "parcel":
                parcel_col_idx = i
                break
        
        if col == parcel_col_idx:
            menu = QMenu(self)
            
            # Add "Select Parcel" section
            menu.addSection("Select Parcel")
            
            # Add option to clear
            action_clear = menu.addAction("None (Clear)")
            action_clear.triggered.connect(lambda: self._on_parcel_selected(row, ""))
            
            # Add SLOP option (always available, stored as "0")
            menu.addSeparator()
            action_slop = menu.addAction("SLOP")
            action_slop.triggered.connect(lambda: self._on_parcel_selected(row, "0"))
            
            if self.voyage and self.voyage.parcels:
                menu.addSeparator()
                for parcel in self.voyage.parcels:
                    # Show "ID - Grade (Receiver)" or just "ID - Grade" if no receiver
                    if parcel.receiver:
                        label = f"{parcel.id} - {parcel.name} ({parcel.receiver})"
                    else:
                        label = f"{parcel.id} - {parcel.name}"
                    action = menu.addAction(label)
                    # Use default parameter to capture loop variable
                    action.triggered.connect(lambda checked, r=row, p=parcel.id: self._on_parcel_selected(r, p))
            else:
                menu.addAction("No parcels defined").setEnabled(False)
                
            menu.addSeparator()
            action_edit = menu.addAction("Edit Parcels...")
            action_edit.triggered.connect(self._edit_parcels)
            
            menu.exec(self.tank_table.viewport().mapToGlobal(position))
    
    def _edit_parcels(self):
        """Edit voyage parcels."""
        from ui.dialogs import ParcelSetupDialog
        
        if not self.voyage:
            self.voyage = Voyage.create_new("001/2024", "", "")
        
        dialog = ParcelSetupDialog(self.voyage.parcels, self)
        if dialog.exec():
            self.voyage.parcels = dialog.get_parcels()
            self._update_parcel_dropdowns()
            self.status_bar.showMessage(f"Updated {len(self.voyage.parcels)} parcels")
    
    def _update_parcel_dropdowns(self):
        """Update parcel display in the grid."""
        # Refresh grid to show current parcel data
        self._populate_grid()
    
    def _get_parcel(self, parcel_id: str):
        """Get parcel by ID."""
        if not self.voyage or not parcel_id:
            return None
        for p in self.voyage.parcels:
            if p.id == parcel_id:
                return p
        return None
    
    def _on_parcel_selected(self, row: int, parcel_id: str):
        """Handle parcel selection - auto-populate related fields or clear row."""
        if not self.voyage:
            return
        
        tank_id_item = self.tank_table.item(row, 0)
        if not tank_id_item:
            return
        
        tank_id = tank_id_item.text()
        reading = self.voyage.get_reading(tank_id)
        if not reading:
            return
        
        if not parcel_id:  # "None (Clear)" selected - clear entire row
            reading.parcel_id = ""
            reading.density_vac = None
            reading.ullage = None
            reading.temp_celsius = None
            reading.fill_percent = None
            reading.tov = 0.0
            reading.trim_correction = 0.0
            reading.corrected_ullage = None
            reading.therm_corr = 1.0
            reading.gov = 0.0
            reading.vcf = 1.0
            reading.gsv = 0.0
            reading.density_air = 0.0
            reading.mt_air = 0.0
            reading.mt_vac = 0.0
            reading.discrepancy = 0.0
            self._update_row(row, reading)
            return
        
        reading.parcel_id = parcel_id
        
        if parcel_id == "0":  # SLOP parcel
            # Use slop density from ship config
            if self.ship_config:
                reading.density_vac = getattr(self.ship_config, 'slop_density', 0.85)
            else:
                reading.density_vac = 0.85
        else:
            parcel = self._get_parcel(parcel_id)
            if parcel:
                reading.density_vac = parcel.density_vac
        
        self._recalculate_tank(row, tank_id)
        self._update_row(row, reading)
    
    def _update_selection_stats(self):
        """Update status bar with sum/avg of selected numeric cells."""
        selected_items = self.tank_table.selectedItems()
        
        total = 0.0
        count = 0
        
        for item in selected_items:
            try:
                # Basic float parsing
                val = float(item.text())
                total += val
                count += 1
            except ValueError:
                continue
                
        if count > 0:
            avg = total / count
            self.sel_total_label.setText(f"SELECTED TOTAL: {total:.3f}")
            self.sel_avg_label.setText(f"SELECTED AVERAGE: {avg:.3f}")
        else:
            self.sel_total_label.setText("SELECTED TOTAL: 0.000")
            self.sel_avg_label.setText("SELECTED AVERAGE: 0.000")

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
