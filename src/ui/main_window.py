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
    QAbstractItemView, QApplication, QInputDialog, QTabWidget, QDateEdit
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
from .widgets.voyage_explorer import VoyageExplorerWidget
from .widgets.report_functions_widget import ReportFunctionsWidget
from ui.dialogs.notes_dialog import NotesDialog

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
    
    # Column definitions for the main grid: (key, header, width, is_input, is_numeric)
    # This configuration drives the DataEntryGrid and its delegates.
    # is_input=True means the cell is editable by the user.
    # is_numeric=True triggers number formatting (decimal places).
    COLUMNS = [
        ("tank_id", "Tank", 60, False, False),
        ("parcel", "Parcel", 70, True, False),        # Dropdown selection for cargo parcel
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
        
        # Colorize state
        self.is_colorized: bool = False
        self.original_cargo_colors: Dict[str, str] = {}
        self.original_custom_colors: Dict[str, Optional[str]] = {}
        
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

        notes_action = QAction("Sefer Notları...", self)
        notes_action.triggered.connect(self._edit_notes)
        file_menu.addAction(notes_action)
        
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
        
        # Stowage Plan menu
        stowage_menu = menubar.addMenu("Stowage Plan")
        
        clear_all_action = QAction("Tüm Tankları Boşalt", self)
        clear_all_action.setShortcut("Ctrl+E")
        clear_all_action.triggered.connect(self._clear_all_tanks)
        stowage_menu.addAction(clear_all_action)
        
        stowage_menu.addSeparator()
        
        transfer_action = QAction("➡️ Ullage'a Aktar", self)
        transfer_action.setShortcut("Ctrl+Shift+T")
        transfer_action.triggered.connect(self._transfer_stowage_to_ullage)
        stowage_menu.addAction(transfer_action)
        
        # Ullage Table menu (new)
        ullage_menu = menubar.addMenu("Ullage Table")
        
        parcels_action = QAction("Edit Parcels...", self)
        parcels_action.triggered.connect(self._edit_parcels)
        ullage_menu.addAction(parcels_action)
        
        ullage_menu.addSeparator()
        
        # Export submenu
        export_menu = ullage_menu.addMenu(t("export", "menu"))
        
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
        
        ullage_menu.addSeparator()
        
        transfer_to_stowage_action = QAction("⬅️ Stowage'a Aktar", self)
        transfer_to_stowage_action.setShortcut("Ctrl+Shift+U")
        transfer_to_stowage_action.triggered.connect(self._transfer_ullage_to_stowage)
        ullage_menu.addAction(transfer_to_stowage_action)
        
        # Help menu
        help_menu = menubar.addMenu(t("help", "menu"))
        
        about_action = QAction(t("about", "menu"), self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def closeEvent(self, event):
        """Handle close event."""
        # Save explorer state
        if hasattr(self, 'explorer_tab'):
            self.explorer_tab.save_state()
            
        super().closeEvent(event)
    
    def _calculate_column_min_widths(self):
        """Calculate minimum column widths based on content."""
        if not hasattr(self, 'tank_table'):
            return
        
        # Use Qt's built-in content sizing
        self.tank_table.resizeColumnsToContents()
        
        # Also consider header text width
        header = self.tank_table.horizontalHeader()
        for i in range(self.tank_table.columnCount()):
            # Get content-based width
            content_width = self.tank_table.columnWidth(i)
            # Get header text width (with some padding)
            header_text = self.COLUMNS[i][1] if i < len(self.COLUMNS) else ""
            header_width = header.fontMetrics().horizontalAdvance(header_text) + 20
            # Store the maximum as minimum
            self._column_min_widths[i] = max(content_width, header_width, 40)
    
    def _on_column_resized(self, index: int, old_size: int, new_size: int):
        """Enforce minimum column width when user resizes."""
        if not hasattr(self, '_column_min_widths'):
            return
        
        if index < len(self._column_min_widths):
            min_width = self._column_min_widths[index]
            if new_size < min_width:
                # Reset to minimum - block signals to prevent recursion
                self.tank_table.horizontalHeader().blockSignals(True)
                self.tank_table.setColumnWidth(index, min_width)
                self.tank_table.horizontalHeader().blockSignals(False)

    
    def _create_central_widget(self):
        """Create main content area with tabs."""
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # Tab 1: Voyage Explorer
        self.explorer_tab = VoyageExplorerWidget(self.ship_config)
        self.explorer_tab.voyage_loaded.connect(self._load_voyage_from_file_and_switch)
        self.tab_widget.addTab(self.explorer_tab, "📂 Voyages")

        # Tab 2: Stowage Planning
        self.stowage_tab = self._create_stowage_tab()
        self.tab_widget.addTab(self.stowage_tab, "📋 Stowage Plan")
        
        # Tab 3: Ullage Calculation
        self.ullage_tab = self._create_ullage_tab()
        self.tab_widget.addTab(self.ullage_tab, "📊 Ullage Calculation")
        
        # Tab 4: Report Functions
        self.report_tab = ReportFunctionsWidget()
        self.tab_widget.addTab(self.report_tab, "📑 Report Functions")
        
        # Connect draft changes to report tab
        if hasattr(self, 'draft_fwd_spin') and hasattr(self, 'draft_aft_spin'):
            self.draft_fwd_spin.valueChanged.connect(self._sync_drafts_to_report)
            self.draft_aft_spin.valueChanged.connect(self._sync_drafts_to_report)
            
        # Connect generation signals
        self.report_tab.request_generate_total.connect(self._generate_total_ullage_report)
        self.report_tab.request_generate_selected.connect(self._generate_selected_parcels_report)
            
        # Restore last active tab
        last_tab = self.settings.value("last_tab", 0, type=int)  # Default to Explorer tab
        if last_tab >= self.tab_widget.count():
            last_tab = 0
        self.tab_widget.setCurrentIndex(last_tab)
        
        # Save tab on change
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def _sync_drafts_to_report(self):
        """Sync draft values to report tab."""
        if hasattr(self, 'report_tab') and hasattr(self, 'draft_fwd_spin') and hasattr(self, 'draft_aft_spin'):
            self.report_tab.update_drafts(
                self.draft_fwd_spin.value(),
                self.draft_aft_spin.value()
            )

    def _on_tab_changed(self, index: int):
        """Save last active tab to settings."""
        self.settings.setValue("last_tab", index)

        # Update Report Functions tab if selected (Index 3)
        if index == 3 and hasattr(self, 'report_tab'):
            # Read directly from UI components to get latest values (UI state)
            fwd = self.draft_fwd_spin.value() if hasattr(self, 'draft_fwd_spin') else 0.0
            aft = self.draft_aft_spin.value() if hasattr(self, 'draft_aft_spin') else 0.0
            self.report_tab.update_drafts(fwd, aft)
    
    def _create_stowage_tab(self) -> QWidget:
        """Create the Stowage Planning tab with STOWAGEMASTER-style layout.
        
        Layout:
        ┌─────────────────────────────────────────────────────────────┐
        │  TOP: Kontrol Paneli - Cargo Legend (draggable cards)       │
        ├─────────────────────────────────────────────────────────────┤
        │  MIDDLE: Ship Schematic (tank grid with Port/Starboard)     │
        ├───────────────────────────┬─────────────────────────────────┤
        │  BOTTOM LEFT:              │  BOTTOM RIGHT:                  │
        │  "Yükleme Talepleri"       │  "Yükleme Planı"                │
        └───────────────────────────┴─────────────────────────────────┘
        """
        from PyQt6.QtWidgets import QSplitter, QGroupBox
        from ui.widgets import ShipSchematicWidget, CargoLegendWidget, CargoInputWidget, PlanViewerWidget
        from models import StowagePlan
        
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Main vertical splitter: Top (40%) vs Bottom (60%)
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # === TOP PANEL: Control Panel ===
        top_panel = QGroupBox("Kontrol Paneli")
        top_layout = QVBoxLayout(top_panel)
        top_layout.setContentsMargins(2, 2, 2, 2)
        top_layout.setSpacing(5)
        
        # Cargo legend row with buttons
        legend_button_row = QHBoxLayout()
        
        self.cargo_legend = CargoLegendWidget()
        self.cargo_legend.cargo_color_changed.connect(self._on_stowage_changed)
        legend_button_row.addWidget(self.cargo_legend, 1)
        
        # Right-side buttons
        buttons_col = QVBoxLayout()
        buttons_col.setSpacing(6)
        buttons_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Colorize button (hold to colorize by receiver)
        self.colorize_btn = QPushButton("Colorize")
        self.colorize_btn.setMinimumHeight(35)
        self.colorize_btn.setStyleSheet("""
            font-size: 10pt; font-weight: bold;
            background-color: #8b5cf6; color: white;
            border-radius: 5px; padding: 8px;
        """)
        self.colorize_btn.setToolTip("Basılı tutun: Alıcı adının ilk 4 harfine göre gruplandırır")
        self.colorize_btn.pressed.connect(self._apply_colorize)
        self.colorize_btn.released.connect(self._restore_colorize)
        buttons_col.addWidget(self.colorize_btn)
        
        # %100 Yap button
        self.fill_100_btn = QPushButton("%100 Yap")
        self.fill_100_btn.setMinimumHeight(35)
        self.fill_100_btn.setStyleSheet("""
            font-size: 10pt; font-weight: bold;
            background-color: #f59e0b; color: white;
            border-radius: 5px; padding: 8px;
        """)
        self.fill_100_btn.setToolTip("Tüm yüklü tankları %100 kapasiteye getir")
        self.fill_100_btn.clicked.connect(self._fill_tanks_to_100)
        buttons_col.addWidget(self.fill_100_btn)
        
        legend_button_row.addLayout(buttons_col)
        top_layout.addLayout(legend_button_row)
        
        # Ship schematic widget
        self.ship_schematic = ShipSchematicWidget()
        top_layout.addWidget(self.ship_schematic, 1)
        
        main_splitter.addWidget(top_panel)
        
        # === BOTTOM PANEL: Horizontal splitter for tables ===
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Cargo Input (Yükleme Talepleri)
        left_panel = QGroupBox("Yükleme Talepleri")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(2, 2, 2, 2)
        
        self.cargo_input_widget = CargoInputWidget()
        self.cargo_input_widget.cargo_list_changed.connect(self._on_cargo_input_changed)
        left_layout.addWidget(self.cargo_input_widget)
        
        bottom_splitter.addWidget(left_panel)
        
        # Right: Plan Viewer (Yükleme Planı)
        right_panel = QGroupBox("Yükleme Planı")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(2, 2, 2, 2)
        
        self.plan_viewer_widget = PlanViewerWidget()
        right_layout.addWidget(self.plan_viewer_widget)
        
        bottom_splitter.addWidget(right_panel)
        
        # Set bottom splitter proportions (40% left, 60% right)
        bottom_splitter.setSizes([400, 600])
        
        main_splitter.addWidget(bottom_splitter)
        
        # Set main splitter proportions (40% top, 60% bottom)
        main_splitter.setSizes([320, 480])
        
        main_layout.addWidget(main_splitter)
        
        # Initialize stowage plan and locked tanks
        self.stowage_plan = StowagePlan()
        self.locked_tanks = set()  # Tank IDs that are locked
        
        self.cargo_legend.set_stowage_plan(self.stowage_plan)
        self.ship_schematic.set_stowage_plan(self.stowage_plan)
        
        # Connect signals
        self.cargo_legend.cargos_changed.connect(self._on_stowage_changed)
        self.ship_schematic.assignment_changed.connect(self._on_stowage_changed)
        
        return tab
    
    def _on_cargo_input_changed(self):
        """Handle cargo input table changes - sync to stowage plan and legend."""
        from ui.widgets.cargo_legend_widget import CARGO_COLORS
        
        cargo_list = self.cargo_input_widget.get_cargo_list()
        
        # Assign colors to cargos that don't have one
        for i, cargo in enumerate(cargo_list):
            if not cargo.custom_color:
                cargo.custom_color = CARGO_COLORS[i % len(CARGO_COLORS)]
        
        # Update stowage plan cargo requests
        self.stowage_plan.cargo_requests = cargo_list
        
        # Update cargo legend
        self.cargo_legend.set_stowage_plan(self.stowage_plan)
        
        # Update displays
        self._on_stowage_changed()
    
    def _on_stowage_changed(self):
        """Handle changes to stowage plan."""
        if hasattr(self, 'ship_schematic') and hasattr(self, 'cargo_legend'):
            # Update colors from cargo legend
            self.ship_schematic.set_cargo_colors(self.cargo_legend.get_cargo_colors())
            self.ship_schematic.refresh()
            self.ship_schematic.repaint()  # Force immediate repaint
            
            # Update cargo cards to show remaining quantities
            self.cargo_legend.update_loaded_quantities()
        
        # Update plan viewer
        if hasattr(self, 'plan_viewer_widget') and hasattr(self, 'stowage_plan'):
            total_capacity = 0
            if hasattr(self, 'ship_config') and self.ship_config:
                total_capacity = sum(getattr(t, 'capacity_m3', 0) for t in self.ship_config.tanks)
            self.plan_viewer_widget.display_plan(
                self.stowage_plan,
                self.cargo_legend.get_cargo_colors() if hasattr(self, 'cargo_legend') else [],
                total_capacity
            )
    
    def _init_stowage_with_ship_config(self):
        """Initialize stowage tab with current ship config."""
        if not self.ship_config:
            return
            
        if self.ship_schematic:
            self.ship_schematic.set_ship_config(self.ship_config)
            
        if hasattr(self, 'explorer_tab'):
            self.explorer_tab.set_ship_config(self.ship_config)
            if hasattr(self, 'stowage_plan'):
                self.stowage_plan.ship_name = self.ship_config.ship_name
    
    # --- Drag-Drop Handlers ---
    
    def handle_cargo_drop(self, cargo_id: str, tank_id: str):
        """Handle dropping a cargo onto a tank."""
        from models.stowage_plan import TankAssignment
        
        if not self.stowage_plan:
            return
        
        cargo = self.stowage_plan.get_cargo_by_id(cargo_id)
        if not cargo:
            return
        
        # Get tank capacity
        tank_config = None
        for t in self.ship_config.tanks:
            if t.id == tank_id:
                tank_config = t
                break
        
        if not tank_config:
            return
        
        capacity = getattr(tank_config, 'capacity_m3', 0)
        
        # Create assignment (fill tank to capacity or remaining cargo)
        already_loaded = self.stowage_plan.get_cargo_total_loaded(cargo_id)
        remaining = cargo.quantity - already_loaded
        quantity_to_load = min(capacity, remaining) if remaining > 0 else capacity
        
        assignment = TankAssignment(
            tank_id=tank_id,
            cargo=cargo,
            quantity_loaded=quantity_to_load
        )
        self.stowage_plan.add_assignment(tank_id, assignment)
        
        self._on_stowage_changed()
    
    def handle_tank_swap(self, source_tank_id: str, target_tank_id: str):
        """Handle swapping cargo between two tanks."""
        if not self.stowage_plan:
            return
        
        source_assignment = self.stowage_plan.get_assignment(source_tank_id)
        target_assignment = self.stowage_plan.get_assignment(target_tank_id)
        
        # Swap assignments
        if source_assignment:
            source_assignment.tank_id = target_tank_id
            self.stowage_plan.assignments[target_tank_id] = source_assignment
        else:
            self.stowage_plan.remove_assignment(target_tank_id)
        
        if target_assignment:
            target_assignment.tank_id = source_tank_id
            self.stowage_plan.assignments[source_tank_id] = target_assignment
        else:
            self.stowage_plan.remove_assignment(source_tank_id)
        
        self._on_stowage_changed()
    
    def handle_empty_tank(self, tank_id: str):
        """Handle emptying a tank (removing its assignment)."""
        if not self.stowage_plan:
            return
        
        self.stowage_plan.remove_assignment(tank_id)
        self._on_stowage_changed()
    
    def handle_exclude_tank(self, tank_id: str, exclude: bool):
        """Handle excluding/including a tank from planning."""
        if not self.stowage_plan:
            return
        
        if exclude:
            if tank_id not in self.stowage_plan.excluded_tanks:
                self.stowage_plan.excluded_tanks.append(tank_id)
        else:
            if tank_id in self.stowage_plan.excluded_tanks:
                self.stowage_plan.excluded_tanks.remove(tank_id)
        
        if hasattr(self, 'ship_schematic'):
            self.ship_schematic.excluded_tanks = set(self.stowage_plan.excluded_tanks)
        
        self._on_stowage_changed()
    
    def handle_lock_tank(self, tank_id: str):
        """Handle locking a tank (preserve assignment during clear)."""
        if not hasattr(self, 'locked_tanks'):
            self.locked_tanks = set()
        self.locked_tanks.add(tank_id)
        self._on_stowage_changed()
    
    def handle_unlock_tank(self, tank_id: str):
        """Handle unlocking a tank."""
        if hasattr(self, 'locked_tanks') and tank_id in self.locked_tanks:
            self.locked_tanks.remove(tank_id)
        self._on_stowage_changed()
    
    def is_tank_locked(self, tank_id: str) -> bool:
        """Check if a tank is locked."""
        return hasattr(self, 'locked_tanks') and tank_id in self.locked_tanks
    
    def _clear_all_tanks(self):
        """Clear all tank assignments (CTRL+E)."""
        if not hasattr(self, 'stowage_plan') or not self.stowage_plan:
            QMessageBox.information(self, "Bilgi", "Aktif bir plan bulunmuyor.")
            return
        
        if not self.stowage_plan.assignments:
            QMessageBox.information(self, "Bilgi", "Boşaltılacak tank yok.")
            return
        
        # Check for locked tanks
        has_locked = hasattr(self, 'locked_tanks') and len(self.locked_tanks) > 0
        
        if has_locked:
            # Show dialog with three options
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Tüm Tankları Boşalt")
            msg_box.setText("Kilitli tanklar bulunuyor. Nasıl devam etmek istersiniz?")
            msg_box.setInformativeText(
                f"Toplam {len(self.locked_tanks)} kilitli tank var.\n\n"
                "• Tümünü Boşalt: Tüm tankları (kilitli dahil) boşaltır\n"
                "• Sadece Planlananları Boşalt: Kilitli tankları korur\n"
                "• İptal: İşlemi iptal eder"
            )
            
            clear_all_btn = msg_box.addButton("Tümünü Boşalt", QMessageBox.ButtonRole.AcceptRole)
            clear_planned_btn = msg_box.addButton("Sadece Planlananları", QMessageBox.ButtonRole.AcceptRole)
            cancel_btn = msg_box.addButton("İptal", QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(cancel_btn)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == cancel_btn:
                return
            elif msg_box.clickedButton() == clear_all_btn:
                # Clear all including locked
                self.stowage_plan.assignments.clear()
                self.locked_tanks.clear()
            elif msg_box.clickedButton() == clear_planned_btn:
                # Clear only non-locked
                for tank_id in list(self.stowage_plan.assignments.keys()):
                    if tank_id not in self.locked_tanks:
                        self.stowage_plan.remove_assignment(tank_id)
        else:
            # Simple confirmation
            reply = QMessageBox.question(
                self, "Tüm Tankları Boşalt",
                "Tüm tank atamalarını temizlemek istediğinizden emin misiniz?\n\n"
                "Bu işlem geri alınamaz.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            self.stowage_plan.assignments.clear()
        
        self._on_stowage_changed()
    
    def _fill_tanks_to_100(self):
        """Fill all loaded tanks to 100% capacity while preserving cargo type."""
        from models.stowage_plan import TankAssignment
        
        if not self.stowage_plan or not self.ship_config:
            return
        
        # Check if there are any loaded tanks
        has_loaded_tanks = any(
            self.stowage_plan.get_assignment(tank.id) 
            for tank in self.ship_config.tanks
        )
        
        if not has_loaded_tanks:
            QMessageBox.information(
                self,
                "Bilgi",
                "Yüklü tank bulunamadı."
            )
            return
        
        # Fill each loaded tank to 100%
        filled_count = 0
        for tank in self.ship_config.tanks:
            assignment = self.stowage_plan.get_assignment(tank.id)
            if assignment:
                tank_capacity = getattr(tank, 'capacity_m3', 0)
                if tank_capacity > 0:
                    # Update quantity to tank capacity
                    new_assignment = TankAssignment(
                        tank_id=tank.id,
                        cargo=assignment.cargo,
                        quantity_loaded=tank_capacity
                    )
                    self.stowage_plan.assignments[tank.id] = new_assignment
                    filled_count += 1
        
        # Refresh UI
        self._on_stowage_changed()
        
        # Show confirmation
        QMessageBox.information(
            self,
            "Tamamlandı",
            f"{filled_count} tank %100 kapasiteye getirildi.\n\n"
            f"Not: Bu işlem sipariş miktarını aşabilir."
        )
    
    def _apply_colorize(self):
        """Apply colorization based on receiver name prefixes (on button press)."""
        if not self.stowage_plan or not self.stowage_plan.cargo_requests:
            return
        
        # Store original colors if not already stored
        if not self.is_colorized:
            self._store_original_colors()
        
        # Group cargos by first 4 characters of receiver names
        groups = self._group_cargos_by_receiver_prefix()
        
        # Define color palette for first 5 groups (bright, distinct colors)
        group_colors = [
            "#FF0000",  # Red
            "#0000FF",  # Blue
            "#00FF00",  # Green
            "#FFFF00",  # Yellow
            "#FFA500"   # Orange
        ]
        
        # Apply colors to cargos in first 5 groups
        for group_index, (prefix, cargo_list) in enumerate(groups[:5]):
            color = group_colors[group_index]
            for cargo in cargo_list:
                cargo.custom_color = color
        
        # Refresh displays
        self._on_stowage_changed()
        self.is_colorized = True
    
    def _restore_colorize(self):
        """Restore original colors (on button release)."""
        if not self.is_colorized or not self.stowage_plan:
            return
        
        # Restore original custom_color values
        for cargo in self.stowage_plan.cargo_requests:
            cargo_id = cargo.unique_id
            if cargo_id in self.original_custom_colors:
                cargo.custom_color = self.original_custom_colors[cargo_id]
            else:
                cargo.custom_color = None
        
        # Refresh displays
        self._on_stowage_changed()
        self.is_colorized = False
    
    def _store_original_colors(self):
        """Store original cargo colors before colorization."""
        if not self.stowage_plan:
            return
        
        self.original_cargo_colors.clear()
        self.original_custom_colors.clear()
        
        for cargo in self.stowage_plan.cargo_requests:
            cargo_id = cargo.unique_id
            self.original_custom_colors[cargo_id] = cargo.custom_color
    
    def _group_cargos_by_receiver_prefix(self) -> list:
        """Group cargos by first 4 characters of receiver names.
        
        Returns:
            List of tuples (prefix, cargo_list) sorted by prefix
        """
        if not self.stowage_plan:
            return []
        
        prefix_groups = {}
        
        for cargo in self.stowage_plan.cargo_requests:
            # Get first receiver name (or empty string if no receivers)
            if cargo.receivers and len(cargo.receivers) > 0:
                first_receiver_name = cargo.receivers[0].name
                # Get first 4 characters (pad if shorter)
                prefix = (first_receiver_name[:4] + "    ")[:4].upper()
            else:
                # No receiver - use special prefix
                prefix = "NONE"
            
            if prefix not in prefix_groups:
                prefix_groups[prefix] = []
            prefix_groups[prefix].append(cargo)
        
        # Sort by prefix and return as list of tuples
        sorted_groups = sorted(prefix_groups.items())
        return sorted_groups
    
    def _transfer_stowage_to_ullage(self):
        """Transfer stowage plan to ullage tab as parcels."""
        from models import Parcel
        
        if not self.stowage_plan or not self.stowage_plan.cargo_requests:
            QMessageBox.warning(
                self, "Kargo Yok",
                "Önce stowage planına kargo ekleyin."
            )
            return
        
        # Confirm transfer
        reply = QMessageBox.question(
            self, "Plan Aktar",
            "Bu işlem Ullage sekmesindeki mevcut parselleri değiştirecek.\n"
            "Tank atamaları da uygulanacak.\n\nDevam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Clear existing parcels
        self.voyage.parcels.clear()
        
        # Get colors from cargo legend (always correct)
        cargo_colors = self.cargo_legend.get_cargo_colors() if hasattr(self, 'cargo_legend') else []
        
        # Create parcels from stowage cargos
        cargo_to_parcel = {}  # Map cargo_id -> parcel_id
        for i, cargo in enumerate(self.stowage_plan.cargo_requests):
            parcel_id = str(i + 1)
            # Get color from legend (index-based) or fallback
            color = cargo_colors[i] if i < len(cargo_colors) else (cargo.custom_color or "#3B82F6")
            # Create parcel from cargo
            parcel = Parcel(
                id=parcel_id,
                name=cargo.cargo_type,
                receiver=cargo.get_receiver_names(),
                density_vac=cargo.density,
                color=color
            )
            self.voyage.parcels.append(parcel)
            cargo_to_parcel[cargo.unique_id] = parcel_id
        
        # Apply tank assignments
        for tank_id, assignment in self.stowage_plan.assignments.items():
            if tank_id in self.voyage.tank_readings:
                parcel_id = cargo_to_parcel.get(assignment.cargo.unique_id)
                if parcel_id:
                    reading = self.voyage.tank_readings[tank_id]
                    reading.parcel_id = parcel_id
                    # Also set the VAC density from the cargo
                    reading.density_vac = assignment.cargo.density

        
        # Switch to Ullage tab
        self.tab_widget.setCurrentIndex(2)
        
        # Refresh grid
        self._populate_grid()
        
        QMessageBox.information(
            self, "Aktarım Tamamlandı",
            f"{len(self.stowage_plan.cargo_requests)} parsel ve "
            f"{len(self.stowage_plan.assignments)} tank ataması aktarıldı."
        )
    
    def _transfer_ullage_to_stowage(self):
        """Transfer ullage data to stowage plan (reverse transfer).
        
        Transfers:
        - Parcels -> StowageCargo (with GOV totals as quantity)
        - Tank assignments based on parcel_id
        - Colors from parcels
        - SLOP as separate cargo
        """
        from models.stowage_plan import StowageCargo, TankAssignment, Receiver
        
        # Validate: Check if there are any parcels
        if not self.voyage or not self.voyage.parcels:
            QMessageBox.warning(
                self, "Parsel Yok",
                "Önce Ullage sekmesinde parsel tanımlayın."
            )
            return
        
        # Check if any tanks have parcel assignments
        assigned_tanks = [r for r in self.voyage.tank_readings.values() if r.parcel_id]
        if not assigned_tanks:
            QMessageBox.warning(
                self, "Tank Ataması Yok",
                "Hiçbir tank bir parsele atanmamış.\n"
                "Önce Ullage sekmesinde tankları parsellere atayın."
            )
            return
        
        # Confirm transfer
        reply = QMessageBox.question(
            self, "⬅️ Stowage'a Aktar",
            "Bu işlem Stowage Plan sekmesindeki mevcut verileri silecek ve\n"
            "Ullage verilerinden yeni bir plan oluşturacak.\n\n"
            "Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Clear existing stowage plan
        self.stowage_plan.clear()
        
        # Group tank readings by parcel_id and calculate totals
        parcel_tanks = {}  # {parcel_id: [tank_readings]}
        parcel_totals = {}  # {parcel_id: total_gov}
        
        for tank_id, reading in self.voyage.tank_readings.items():
            if reading.parcel_id:
                pid = reading.parcel_id
                if pid not in parcel_tanks:
                    parcel_tanks[pid] = []
                    parcel_totals[pid] = 0.0
                parcel_tanks[pid].append(reading)
                parcel_totals[pid] += reading.gov if reading.gov else 0.0
        
        # Create StowageCargo for each parcel that has tank assignments
        parcel_to_cargo = {}  # {parcel_id: StowageCargo}
        
        # Handle regular parcels
        for parcel in self.voyage.parcels:
            if parcel.id in parcel_tanks:
                # Create receivers list
                receivers = []
                if parcel.receiver:
                    receivers = [Receiver(name=parcel.receiver)]
                
                cargo = StowageCargo(
                    cargo_type=parcel.name or f"Parcel {parcel.id}",
                    quantity=parcel_totals.get(parcel.id, 0.0),
                    receivers=receivers,
                    density=parcel.density_vac or 0.85,
                    custom_color=parcel.color or "#3B82F6"
                )
                self.stowage_plan.add_cargo(cargo)
                parcel_to_cargo[parcel.id] = cargo
        
        # Handle SLOP (parcel_id = "0") if any tanks are assigned
        if "0" in parcel_tanks:
            slop_cargo = StowageCargo(
                cargo_type="SLOP",
                quantity=parcel_totals.get("0", 0.0),
                receivers=[],
                density=0.85,
                custom_color="#9CA3AF"  # Gray for SLOP
            )
            self.stowage_plan.add_cargo(slop_cargo)
            parcel_to_cargo["0"] = slop_cargo
        
        # Create TankAssignments
        assignment_count = 0
        for tank_id, reading in self.voyage.tank_readings.items():
            if reading.parcel_id and reading.parcel_id in parcel_to_cargo:
                cargo = parcel_to_cargo[reading.parcel_id]
                assignment = TankAssignment(
                    tank_id=tank_id,
                    cargo=cargo,
                    quantity_loaded=reading.gov if reading.gov else 0.0
                )
                self.stowage_plan.add_assignment(tank_id, assignment)
                assignment_count += 1
        
        # Update Stowage Plan UI components
        if hasattr(self, 'cargo_input_widget'):
            self.cargo_input_widget.set_cargo_list(self.stowage_plan.cargo_requests)
        
        if hasattr(self, 'cargo_legend'):
            self.cargo_legend.set_stowage_plan(self.stowage_plan)
        
        if hasattr(self, 'ship_schematic'):
            self.ship_schematic.set_stowage_plan(self.stowage_plan)
        
        # Refresh stowage display
        self._on_stowage_changed()
        
        # Switch to Stowage Plan tab
        self.tab_widget.setCurrentIndex(1)
        
        QMessageBox.information(
            self, "Aktarım Tamamlandı",
            f"{len(self.stowage_plan.cargo_requests)} kargo ve "
            f"{assignment_count} tank ataması Stowage Plan'a aktarıldı."
        )
    
    def _save_stowage_plan(self):
        """Save current stowage plan to JSON file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Stowage Plan Kaydet",
            "data/stowplans/STOWPLAN.json",
            "JSON Files (*.json)"
        )
        if filename:
            self.stowage_plan.save_to_json(filename)
            self.status_bar.showMessage(f"Stowage plan saved: {filename}")
    
    def _load_stowage_plan(self):
        """Load stowage plan from JSON file."""
        from models import StowagePlan
        
        filename, _ = QFileDialog.getOpenFileName(
            self, "Stowage Plan Yükle",
            "data/stowplans",
            "JSON Files (*.json)"
        )
        if filename:
            self.stowage_plan = StowagePlan.load_from_json(filename)
            
            # Update cargo input widget (bottom left table)
            if hasattr(self, 'cargo_input_widget'):
                self.cargo_input_widget.set_cargo_list(self.stowage_plan.cargo_requests)
            
            # Update cargo legend (draggable cards)
            self.cargo_legend.set_stowage_plan(self.stowage_plan)
            
            # Update ship schematic
            self.ship_schematic.set_stowage_plan(self.stowage_plan)
            
            self._on_stowage_changed()
            self.status_bar.showMessage(f"Stowage plan yüklendi: {filename}")

    
    def _create_ullage_tab(self) -> QWidget:
        """Create the Ullage Calculation tab (existing functionality)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
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
        
        return tab
    
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
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)  # Enable dropdown calendar
        self.date_edit.setDisplayFormat("dd-MM-yyyy")
        self.date_edit.setDate(datetime.now())
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
        from .widgets.excel_table import ExcelTableWidget
        table = ExcelTableWidget()
        
        # Configure table
        table.setColumnCount(len(self.COLUMNS))
        table.setHorizontalHeaderLabels([col[1] for col in self.COLUMNS])
        
        # Set initial column widths
        for i, (_, _, width, _, _) in enumerate(self.COLUMNS):
            table.setColumnWidth(i, width)
        
        # Use Interactive mode - allows manual resizing
        # Content-based minimums will be enforced via sectionResized signal
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        for i in range(len(self.COLUMNS)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        # Allow horizontal scroll if content exceeds width
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Initialize minimum widths storage and connect resize signal
        self._column_min_widths = [40] * len(self.COLUMNS)
        header.sectionResized.connect(self._on_column_resized)
        
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
        # Note: ResizeMode already set to Interactive above - do not override here
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
            # Initialize stowage tab with ship config
            self._init_stowage_with_ship_config()
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
                # Initialize stowage tab with ship config
                self._init_stowage_with_ship_config()
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
                # Get parcel-based background color
                parcel_color = self._get_parcel_bg_color(reading.parcel_id, is_input and key != "parcel")
                item.setData(Qt.ItemDataRole.BackgroundRole, QBrush(parcel_color))
                
                # Set text color based on background contrast
                text_color = self._contrast_color(parcel_color)
                item.setForeground(QColor(text_color))
                
                # Parcel column should be read-only to force context menu usage
                if not (is_input and key != "parcel"):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                self.tank_table.setItem(row, col, item)
        
        self.tank_table.blockSignals(False)
        
        # Calculate minimum widths based on content
        self._calculate_column_min_widths()
    
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
        # Return vibrant color without blending/fading
        return base_color

    def _contrast_color(self, bg_color: QColor) -> str:
        """Get contrasting text color (black or white) based on background brightness."""
        # Calculate relative luminance
        # Formula: 0.2126 * R + 0.7152 * G + 0.0722 * B
        lum = 0.2126 * bg_color.redF() + 0.7152 * bg_color.greenF() + 0.0722 * bg_color.blueF()
        return "#000000" if lum > 0.5 else "#ffffff"

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
            
            # Defer recalculation to allow editor to close cleanly
            # This prevents "QAbstractItemView::commitData" errors
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._recalculate_tank(row, tank_id))
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
            
            if pid != "0":
                 for p in self.voyage.parcels:
                    if p.id == pid:
                        if p.color:
                            parcel_color = p.color
                        break
            
            # Determine text color
            text_color = self._contrast_color(QColor(parcel_color))
            
            label = QLabel(label_text)
            # Styling: colored box with padding, rounded corners, and black text
            label.setStyleSheet(f"""
                background-color: {parcel_color}; 
                color: {text_color};
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
        # Sync to Report Functions tab
        self._sync_drafts_to_report()
    
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
            from core.config import save_config
            save_config(self.ship_config)

    def _generate_total_ullage_report(self):
        """Generate the PDF report using manual header data and current voyage readings."""
        if not self.ship_config or not self.voyage:
            QMessageBox.warning(self, "Hata", "Gemi ve Sefer bilgisi bulunamadı.")
            return

        from reporting.pdf_engine import UllagePDFReport
        
        # 1. Collect Data from UI
        ui_data = self.report_tab.get_report_data()
        
        # 2. Vessel Data
        vessel_data = {
            'name': self.ship_config.ship_name
        }
        
        # 3. Voyage Data
        voyage_data = {
            'voyage': self.voyage.voyage_number,
            'port': ui_data['port'],
            'port_to': ui_data['terminal'], 
            'receiver': ui_data['receiver'],
            'date': ui_data['date'],
            'draft_fwd': ui_data['draft_fwd'],
            'draft_aft': ui_data['draft_aft'],
            'cargo': ui_data['cargo'],
            'report_type': ui_data['report_type']
        }
        
        # 4. Tank Data
        tank_data = []
        
        # Map parcel IDs to Names for filtering
        parcel_map = {p.id: p.name.upper().strip() for p in self.voyage.parcels}
        
        for tank in self.ship_config.tanks:
            reading = self.voyage.get_reading(tank.id)
            if not reading:
                continue
                
            # Identify Parcel Name
            parcel_name = parcel_map.get(reading.parcel_id, "")
            
            # Filter: Exclude if Parcel ID is "0" OR Parcel Name is "SLOP"
            if reading.parcel_id == "0" or parcel_name == "SLOP":
                continue
                
            # Format Tank Name
            # User Request: "COT NO 1 STARBOARD" -> "COT 1S"
            raw = tank.name.upper()
            # 1. Standardize Sides
            raw = raw.replace("STARBOARD", "S").replace("PORT", "P").replace("CENTER", "C")
            
            if "SLOP" in raw:
                # Cleaning for SLOP
                # User wants "SLOP P" or "SLOP S"
                # Check for side char
                if "S" in raw.replace("SLOP", ""): 
                    display_name = "SLOP S"
                elif "P" in raw.replace("SLOP", ""): 
                    display_name = "SLOP P"
                else:
                    display_name = "SLOP"
            else:
                # Cleaning for COT
                # Remove "COT", "TANK", "NO", ".", " " (whitespace)
                cleaned = raw.replace("COT", "").replace("TANK", "").replace("NO", "").replace(".", "").replace(" ", "")
                # Result should be "1S", "2P", etc.
                display_name = f"COT {cleaned}"

            # Format Data
            # Helper to format float or empty
            fmt = lambda v, p: f"{v:.{p}f}" if v is not None else ""
            
            row = {
                'name': display_name,
                'ullage_actual': fmt(reading.ullage, 1),
                'ullage_corr': fmt(reading.corrected_ullage, 1),
                'tov': fmt(reading.tov, 3),
                'fw_actual': "0.00", # Placeholder for FW if not in model
                'fw_corr': "0.00",
                'gov': fmt(reading.gov, 3),
                'temp': fmt(reading.temp_celsius, 1),
                'vcf': fmt(reading.vcf, 4),
                'gsv': fmt(reading.gsv, 3),
                'density': fmt(reading.density_vac, 4),
                'w_vac': fmt(reading.mt_vac, 3),
                'w_air': fmt(reading.mt_air, 3)
            }
            tank_data.append(row)
            
        # 5. Overview Data
        # We need to calculate totals for the summary table if PDF engine doesn't do it for summary block.
        # But PDF engine's _build_main_table calculates its own totals.
        # _build_summary_table uses 'overview_data'.
        
        # Calculate totals for summary block
        total_tov = sum(float(r['tov'] or 0) for r in tank_data)
        total_gov = sum(float(r['gov'] or 0) for r in tank_data)
        total_gsv = sum(float(r['gsv'] or 0) for r in tank_data)
        total_mt_vac = sum(float(r['w_vac'] or 0) for r in tank_data)
        total_mt_air = sum(float(r['w_air'] or 0) for r in tank_data)
        
        # Weighted avg VCF and Density?
        # VCF = GSV / GOV
        avg_vcf = (total_gsv / total_gov) if total_gov > 0 else 0
        # Density usually from one parcel or weighted.
        # For 'Total' report, showing one density is ambiguous if multi-grade. 
        # But usually 'Total Report' assumes one main cargo or just totals.
        # Let's pick the density from UI or first tank.
        first_dens = next((r['density'] for r in tank_data if r['density']), "0.0000")
        
        overview_data = {
            'remarks': ui_data['remarks'],
            'mmc_no': ui_data['mmc_no'],
            'product': ui_data['cargo'],
            'density': first_dens,
            'tov': f"{total_tov:.3f}",
            'gov': f"{total_gov:.3f}",
            'average_vcf': f"{avg_vcf:.4f}",
            'gsv': f"{total_gsv:.3f}",
            'mt_vac': f"{total_mt_vac:.3f}",
            'mt_air': f"{total_mt_air:.3f}"
        }
        
        # Generate with Save Dialog and Retry Logic
        default_name = f"{self.voyage.voyage_number} TotalUllage.pdf"
        # Sanitize
        default_name = "".join(c for c in default_name if c.isalnum() or c in (' ', '.', '_', '-')).strip()
        
        output_dir = self.last_dir or os.getcwd()
        initial_path = os.path.join(output_dir, default_name)
        
        from PyQt6.QtWidgets import QFileDialog, QInputDialog, QLineEdit
        
        # prompt user for location/name
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "Toplam Ullage Raporunu Kaydet",
            initial_path,
            "PDF Files (*.pdf)"
        )
        
        if not selected_path:
            return # User cancelled
            
        # Save last dir
        self.last_dir = os.path.dirname(selected_path)
        
        current_path = selected_path
        
        while True:
            try:
                # Generate PDF (if file is locked, PermissionError will be raised here)
                report = UllagePDFReport(current_path, vessel_data, voyage_data, tank_data, overview_data)
                report.generate()
                
                # Open
                os.startfile(current_path)
                break
                
            except PermissionError:
                filename_only = os.path.basename(current_path)
                new_name, ok = QInputDialog.getText(
                    self, 
                    "Dosya Erişim Hatası", 
                    f"'{filename_only}' dosyası şu an açık veya yazma izni yok.\n\nLütfen yeni bir dosya adı giriniz:",
                    QLineEdit.EchoMode.Normal,
                    filename_only
                )
                if ok and new_name:
                    new_name = new_name.strip()
                    if not new_name.lower().endswith('.pdf'):
                        new_name += ".pdf"
                    current_path = os.path.join(os.path.dirname(current_path), new_name)
                    continue
                else:
                    break # User cancelled
            
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Rapor oluşturulurken hata oluştu:\n{str(e)}")
                break

    def _generate_selected_parcels_report(self):
        """Generate the PDF report for selected parcels only."""
        if not self.ship_config or not self.voyage:
            QMessageBox.warning(self, "Hata", "Gemi ve Sefer bilgisi bulunamadı.")
            return

        # Get selected parcel IDs
        selected_ids = self.report_tab.get_selected_parcel_ids()
        if not selected_ids:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir parsel seçiniz.")
            return

        from reporting.pdf_engine import UllagePDFReport
        
        # 1. Collect Data from UI
        ui_data = self.report_tab.get_report_data()
        
        # 2. Vessel Data
        vessel_data = {
            'name': self.ship_config.ship_name
        }
        
        # 3. Voyage Data
        voyage_data = {
            'voyage': self.voyage.voyage_number,
            'port': ui_data['port'],
            'port_to': ui_data['terminal'], 
            'receiver': ui_data['receiver'],
            'date': ui_data['date'],
            'draft_fwd': ui_data['draft_fwd'],
            'draft_aft': ui_data['draft_aft'],
            'cargo': ui_data['cargo'],
            'report_type': ui_data['report_type']
        }
        
        # 4. Tank Data - Filter by selected parcels
        tank_data = []
        
        for tank in self.ship_config.tanks:
            reading = self.voyage.get_reading(tank.id)
            if not reading:
                continue
            
            # Filter: Only include selected parcels
            if reading.parcel_id not in selected_ids:
                continue
                
            # Format Tank Name
            raw = tank.name.upper()
            raw = raw.replace("STARBOARD", "S").replace("PORT", "P").replace("CENTER", "C")
            
            if "SLOP" in raw:
                if "S" in raw.replace("SLOP", ""): 
                    display_name = "SLOP S"
                elif "P" in raw.replace("SLOP", ""): 
                    display_name = "SLOP P"
                else:
                    display_name = "SLOP"
            else:
                cleaned = raw.replace("COT", "").replace("TANK", "").replace("NO", "").replace(".", "").replace(" ", "")
                display_name = f"COT {cleaned}"

            # Format Data
            fmt = lambda v, p: f"{v:.{p}f}" if v is not None else ""
            
            row = {
                'name': display_name,
                'ullage_actual': fmt(reading.ullage, 1),
                'ullage_corr': fmt(reading.corrected_ullage, 1),
                'tov': fmt(reading.tov, 3),
                'gov': fmt(reading.gov, 3),
                'temp': fmt(reading.temp_celsius, 1),
                'vcf': fmt(reading.vcf, 4),
                'gsv': fmt(reading.gsv, 3),
                'density': "",  # Empty for manual entry on printed PDF
                'w_vac': fmt(reading.mt_vac, 3),
                'w_air': fmt(reading.mt_air, 3),
                'fw_actual': '0.00',
                'fw_corr': '0.00'
            }
            tank_data.append(row)
        
        if not tank_data:
            QMessageBox.warning(self, "Uyarı", "Seçilen parsellere ait tank bulunamadı.")
            return
        
        # 5. Vacuum Density - Leave empty for manual entry on printed PDF
        density_str = ""
        
        # 6. Overview/Summary Data
        total_tov = sum(float(t.get('tov', 0) or 0) for t in tank_data)
        total_gov = sum(float(t.get('gov', 0) or 0) for t in tank_data)
        total_gsv = sum(float(t.get('gsv', 0) or 0) for t in tank_data)
        total_mt_vac = sum(float(t.get('w_vac', 0) or 0) for t in tank_data)
        total_mt_air = sum(float(t.get('w_air', 0) or 0) for t in tank_data)
        
        avg_vcf = total_gsv / total_gov if total_gov > 0 else 0
        
        overview_data = {
            'mmc_no': ui_data['mmc_no'],
            'product': ui_data['cargo'],
            'density': density_str,
            'tov': f"{total_tov:.3f}",
            'gov': f"{total_gov:.3f}",
            'average_vcf': f"{avg_vcf:.4f}",
            'gsv': f"{total_gsv:.3f}",
            'mt_vac': f"{total_mt_vac:.3f}",
            'mt_air': f"{total_mt_air:.3f}",
            'remarks': ui_data['remarks']
        }
        
        # Generate with Save Dialog
        default_name = f"{self.voyage.voyage_number} SelectedParcels.pdf"
        default_name = "".join(c for c in default_name if c.isalnum() or c in (' ', '.', '_', '-')).strip()
        
        output_dir = self.last_dir or os.getcwd()
        initial_path = os.path.join(output_dir, default_name)
        
        from PyQt6.QtWidgets import QFileDialog, QInputDialog, QLineEdit
        
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "Seçili Parsel Raporunu Kaydet",
            initial_path,
            "PDF Files (*.pdf)"
        )
        
        if not selected_path:
            return
            
        self.last_dir = os.path.dirname(selected_path)
        
        current_path = selected_path
        
        while True:
            try:
                report = UllagePDFReport(current_path, vessel_data, voyage_data, tank_data, overview_data)
                report.generate()
                
                os.startfile(current_path)
                break
                
            except PermissionError:
                filename_only = os.path.basename(current_path)
                new_name, ok = QInputDialog.getText(
                    self, 
                    "Dosya Erişim Hatası", 
                    f"'{filename_only}' dosyası şu an açık veya yazma izni yok.\n\nLütfen yeni bir dosya adı giriniz:",
                    QLineEdit.EchoMode.Normal,
                    filename_only
                )
                if ok and new_name:
                    new_name = new_name.strip()
                    if not new_name.lower().endswith('.pdf'):
                        new_name += ".pdf"
                    current_path = os.path.join(os.path.dirname(current_path), new_name)
                    continue
                else:
                    break
            
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Rapor oluşturulurken hata oluştu:\n{str(e)}")
                break
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
        # Check if there's existing data
        has_voyage_data = (
            self.voyage and 
            (self.voyage.parcels or 
             any(r.ullage for r in self.voyage.tank_readings.values()))
        )
        has_stowage_data = (
            self.stowage_plan and 
            (self.stowage_plan.cargo_requests or self.stowage_plan.assignments)
        )
        
        if has_voyage_data or has_stowage_data:
            reply = QMessageBox.question(
                self, "Yeni Sefer",
                "Mevcut veriler silinecek.\n"
                "Yeni sefer oluşturmak istediğinizden emin misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Clear stowage plan
        if self.stowage_plan:
            self.stowage_plan.clear()
            self._on_stowage_changed()
        
        # Create new voyage
        self.voyage = Voyage.create_new("", "", "")
        self.port_edit.clear()
        self.terminal_edit.clear()
        self.voyage_edit.clear()
        self.date_edit.setDate(datetime.now())
        self._populate_grid()
        self.status_bar.showMessage("New voyage created")
    
    def _open_voyage(self):
        """Open existing voyage from unified .voyage file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Voyage", self.last_dir, "Voyage Files (*.voyage)"
        )
        if filepath:
            self._load_voyage_from_file(filepath)

    def _load_voyage_from_file_and_switch(self, filepath: str):
        """Load voyage and switch to Stowage Plan tab."""
        if self._load_voyage_from_file(filepath):
            self.tab_widget.setCurrentIndex(1) # Switch to Stowage Plan

    def _load_voyage_from_file(self, filepath: str) -> bool:
        """Load voyage data from file."""
        self._update_last_dir(filepath)
        try:
            import json
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load voyage data
            if 'voyage' in data:
                self.voyage = Voyage.from_dict(data['voyage'])
            else:
                raise ValueError("Invalid voyage file format")
            
            # Load stowage plan if present
            if data.get('stowage_plan'):
                from models.stowage_plan import StowagePlan
                self.stowage_plan = StowagePlan.from_dict(data['stowage_plan'])
                
                # Update Stowage UI
                if hasattr(self, 'cargo_input_widget'):
                    self.cargo_input_widget.set_cargo_list(self.stowage_plan.cargo_requests)
                if hasattr(self, 'cargo_legend'):
                    self.cargo_legend.set_stowage_plan(self.stowage_plan)
                if hasattr(self, 'ship_schematic'):
                    self.ship_schematic.set_stowage_plan(self.stowage_plan)
                self._on_stowage_changed()
            
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
            from PyQt6.QtCore import QDate
            # Parse date string to QDate
            try:
                date_str = self.voyage.date
                if '-' in date_str:
                    d, m, y = date_str.split('-')
                    self.date_edit.setDate(QDate(int(y), int(m), int(d)))
                else:
                    self.date_edit.setDate(datetime.now())
            except:
                self.date_edit.setDate(datetime.now())
            self.vef_spin.setValue(self.voyage.vef)
            self.draft_aft_spin.setValue(self.voyage.drafts.aft)
            self.draft_fwd_spin.setValue(self.voyage.drafts.fwd)
            
            # Load officer info if present
            if hasattr(self, 'chief_officer_edit'):
                self.chief_officer_edit.setText(self.voyage.chief_officer)
            if hasattr(self, 'master_edit'):
                self.master_edit.setText(self.voyage.master)
            
            # Unblock signals after setting values
            self.port_edit.blockSignals(False)
            self.terminal_edit.blockSignals(False)
            self.voyage_edit.blockSignals(False)
            self.date_edit.blockSignals(False)
            self.vef_spin.blockSignals(False)
            self.draft_aft_spin.blockSignals(False)
            self.draft_fwd_spin.blockSignals(False)
            
            self._populate_grid()
            
            # Update Report Functions parcel selector
            if hasattr(self, 'report_tab'):
                self.report_tab.set_parcels(
                    self.voyage.parcels,
                    self.ship_config.tanks if self.ship_config else None,
                    self.voyage.tank_readings
                )
            
            self.status_bar.showMessage(f"Voyage loaded: {filepath}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load voyage: {e}")
            return False

    def _edit_notes(self):
        """Open dialog to edit voyage notes."""
        if not self.voyage:
            return
            
        dialog = NotesDialog(self.voyage.notes, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.voyage.notes = dialog.get_notes()
            self.status_bar.showMessage("Sefer notları güncellendi.")
    
    def _save_voyage(self):
        """Save current voyage with stowage plan to unified .voyage file."""
        if not self.voyage:
            return
        
        # Update voyage from UI
        self.voyage.port = self.port_edit.text()
        self.voyage.terminal = self.terminal_edit.text()
        self.voyage.voyage_number = self.voyage_edit.text()
        self.voyage.date = self.date_edit.date().toString("dd-MM-yyyy")
        self.voyage.vef = self.vef_spin.value()
        self.voyage.drafts.aft = self.draft_aft_spin.value()
        self.voyage.drafts.fwd = self.draft_fwd_spin.value()
        self.voyage.chief_officer = self.chief_officer_edit.text()
        self.voyage.master = self.master_edit.text()
        
        # Create unified save structure
        save_data = {
            "version": "2.0",
            "voyage": self.voyage.to_dict(),
            "stowage_plan": self.stowage_plan.to_dict() if self.stowage_plan else None
        }
        
        # Suggest filename based on voyage number
        suggested_name = self.voyage.voyage_number or "voyage"
        suggested_name = suggested_name.replace("/", "-").replace("\\", "-")
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Voyage", 
            f"{self.last_dir}/{suggested_name}.voyage", 
            "Voyage Files (*.voyage)"
        )
        if filepath:
            # Ensure .voyage extension
            if not filepath.endswith('.voyage'):
                filepath += '.voyage'
            
            self._update_last_dir(filepath)
            try:
                import json
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, indent=2, ensure_ascii=False)
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
        self.voyage.date = self.date_edit.date().toString("dd-MM-yyyy")
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
            # Ask for Admin Password
            password, ok = QInputDialog.getText(
                self, "Admin Password",
                "Attention! Do you really want to reset all ullages, trim corrections?\n"
                "Ask for permission of the Chief Officer and please enter Admin password!",
                QLineEdit.EchoMode.Password
            )
            
            if not ok:
                return
                
            if password != "19771977":
                QMessageBox.critical(self, "Access Denied", "Incorrect password.")
                return

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
