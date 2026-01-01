"""
Voyage Explorer Widget for listing and previewing voyage files.
"""

import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QSplitter, QTextEdit, QPushButton, QFrame, QMessageBox,
    QScrollArea, QSizePolicy, QAbstractItemView, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QRect, QSettings, QEvent
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QAction, QKeySequence

from models import ShipConfig
from models.voyage import Voyage
from models.stowage_plan import StowagePlan
from .cargo_legend_widget import CARGO_COLORS
from .flow_layout import FlowLayout

class ParcelSummaryCard(QLabel):
    """
    Visual card for parcel details in totals view (Chip style).
    
    Displays:
    - Cargo Name
    - Receiver (in parentheses)
    - Quantity (MT)
    - Background color matching the cargo
    - Auto-contrasted text color (black/white)
    """
    def __init__(self, name, qty, receiver, color, parent=None):
        super().__init__(parent)
        
        # Calculate contrast color
        c = QColor(color)
        brightness = (c.red() * 299 + c.green() * 587 + c.blue() * 114) / 1000
        text_color = "#000000" if brightness > 128 else "#FFFFFF"
        
        text = f"{name}"
        if receiver and receiver != "Genel":
            text += f" ({receiver})"
        text += f": {qty:.3f} MT"
        
        self.setText(text)
        # Enable text selection with mouse for copy
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setCursor(Qt.CursorShape.IBeamCursor)
        self.setStyleSheet(f"""
            ParcelSummaryCard {{
                background-color: {color};
                color: {text_color};
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 10pt;
            }}
        """)


class PreviewShipSchematic(QWidget):
    """
    Lightweight read-only ship schematic for preview.
    
    Draws a simplified grid of tanks to show the cargo distribution
    without the full interactivity of the main Stowage Planner.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ship_config = None
        self.plan = None
        self.setMinimumHeight(200)
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(), 
            QSizePolicy.Policy.Expanding
        )
        
    def set_data(self, ship_config: ShipConfig, plan: StowagePlan):
        self.ship_config = ship_config
        self.plan = plan
        self.update()
        
    def paintEvent(self, event):
        if not self.ship_config:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate grid
        # Assuming similar layout logic: Pairs of P/S tanks
        tanks = self.ship_config.tanks
        if not tanks:
            return
            
        # Group by row
        rows = {} # row_idx -> {side: tank}
        for i, tank in enumerate(tanks):
            r = (i // 2) + 1
            side = 'P' if i % 2 == 0 else 'S'
            if r not in rows: rows[r] = {}
            rows[r][side] = tank
            
        # Draw settings
        margin = 10
        spacing = 5
        
        # Layout calculation
        sorted_row_nums = sorted(rows.keys())
        max_row = max(sorted_row_nums)
        num_cols = len(sorted_row_nums)
        
        # Available area
        w = self.width() - 2 * margin
        h = self.height() - 2 * margin
        
        # Cell size
        cell_w = (w - (num_cols - 1) * spacing) / num_cols
        cell_h = (h - spacing) / 2 # 2 rows (P/S)
        
        # Clamp cell size to reasonable aspect ratio or max size
        cell_w = min(cell_w, 120)
        cell_h = min(cell_h, 80)
        
        # Center the grid
        total_grid_w = num_cols * cell_w + (num_cols - 1) * spacing
        start_x = margin + (w - total_grid_w) / 2
        
        font = painter.font()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        
        for r_num in sorted_row_nums:
            col_idx = max_row - r_num # 0 for max row, N-1 for row 1
            x = start_x + col_idx * (cell_w + spacing)
            
            # Port (Top)
            if 'P' in rows[r_num]:
                tank = rows[r_num]['P']
                self._draw_tank(painter, tank, x, margin, cell_w, cell_h)
                
            # Starboard (Bottom)
            if 'S' in rows[r_num]:
                tank = rows[r_num]['S']
                self._draw_tank(painter, tank, x, margin + cell_h + spacing, cell_w, cell_h)

    def _draw_tank(self, painter, tank, x, y, w, h):
        # Determine color
        fill_color = QColor("#E0E0E0") # Default gray
        
        if self.plan:
            assign = self.plan.get_assignment(tank.id)
            if assign:
                # Find color in plan cargo list
                c_color = None
                for i, cargo in enumerate(self.plan.cargo_requests):
                    if cargo.unique_id == assign.cargo.unique_id:
                        if cargo.custom_color:
                            c_color = cargo.custom_color
                        else:
                            # Use default palette
                            idx = i % len(CARGO_COLORS)
                            c_color = CARGO_COLORS[idx]
                        break
                
                if c_color:
                    fill_color = QColor(c_color)
        
        rect = (int(x), int(y), int(w), int(h))
        q_rect = QRect(int(x), int(y), int(w), int(h))
        
        # Draw background
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.setBrush(QBrush(fill_color))
        painter.drawRect(q_rect)
        
        # Draw Text
        text_lines = [f"[{tank.id}]"]
        if self.plan:
            assign = self.plan.get_assignment(tank.id)
            if assign:
                c_name = assign.cargo.cargo_type
                rec = assign.cargo.get_receiver_names()
                
                text_lines.append(c_name)
                if rec:
                    text_lines.append(f"({rec})")
        
        painter.setPen(QColor("black" if fill_color.lightness() > 128 else "white"))
        
        # Use smaller font for details
        f = painter.font()
        f.setPointSize(7)
        painter.setFont(f)
        
        painter.drawText(q_rect.adjusted(2, 2, -2, -2), 
                        Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, 
                        "\n".join(text_lines))


class VoyageExplorerWidget(QWidget):
    """Widget to list and preview voyage files."""
    
    voyage_loaded = pyqtSignal(str) # Emits filepath
    
    def __init__(self, ship_config: ShipConfig, parent=None):
        super().__init__(parent)
        self.ship_config = ship_config
        self.voyage_dir = os.path.join(os.getcwd(), 'VOYAGES')
        self.current_path = None
        self._init_ui()
        self.restore_state()
        self.refresh_list()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === Left Panel: List ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("Saved Voyages"))
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self._show_context_menu)
        self.file_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.file_list.itemDoubleClicked.connect(lambda item: self._on_load_clicked())
        left_layout.addWidget(self.file_list)
        
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self.refresh_list)
        left_layout.addWidget(refresh_btn)
        
        self.splitter.addWidget(left_widget)
        
        # === Right Panel: Preview ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        # Splitter for Resizable Sections
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 1. Notes Section (Editable)
        notes_widget = QWidget()
        notes_layout = QVBoxLayout(notes_widget)
        notes_layout.setContentsMargins(0, 0, 0, 0)
        
        notes_header_layout = QHBoxLayout()
        notes_header_layout.addWidget(QLabel("Voyage Notes:"))
        notes_header_layout.addStretch()
        
        self.save_note_btn = QPushButton("Save Note")
        self.save_note_btn.setFixedSize(90, 24)
        self.save_note_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f766e; color: white; border: none; border-radius: 3px;
                font-size: 9pt;
            }
            QPushButton:hover { background-color: #115e59; }
            QPushButton:disabled { background-color: #cbd5e1; color: #94a3b8; }
        """)
        self.save_note_btn.clicked.connect(self._on_save_note_clicked)
        self.save_note_btn.setEnabled(False)
        notes_header_layout.addWidget(self.save_note_btn)
        
        notes_layout.addLayout(notes_header_layout)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Enter voyage notes here...")
        self.notes_edit.setStyleSheet("background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155;")
        notes_layout.addWidget(self.notes_edit)
        
        self.right_splitter.addWidget(notes_widget)
        
        # 2. Cargo Summary Section
        totals_widget = QWidget()
        totals_layout_container = QVBoxLayout(totals_widget)
        totals_layout_container.setContentsMargins(0, 0, 0, 0)
        self.totals_label = QLabel("Cargoes:")
        totals_layout_container.addWidget(self.totals_label)
        
        self.totals_scroll = QScrollArea()
        self.totals_scroll.setWidgetResizable(True)
        self.totals_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.totals_scroll.setMinimumHeight(100)
        self.totals_scroll.setStyleSheet("background: transparent;")
        
        self.totals_container = QWidget()
        self.totals_container.setStyleSheet("background: transparent;")
        self.totals_layout = FlowLayout(self.totals_container)
        self.totals_layout.setContentsMargins(0, 0, 0, 0)
        self.totals_layout.setSpacing(10)
        
        self.totals_scroll.setWidget(self.totals_container)
        totals_layout_container.addWidget(self.totals_scroll)
        self.right_splitter.addWidget(totals_widget)
        
        # 3. Ship Preview Section
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(QLabel("Stowage Preview:"))
        self.schematic_preview = PreviewShipSchematic()
        preview_layout.addWidget(self.schematic_preview)
        self.right_splitter.addWidget(preview_widget)
        
        # Set initial sizes/stretch
        self.right_splitter.setStretchFactor(0, 1) # Notes
        self.right_splitter.setStretchFactor(1, 1) # Totals
        self.right_splitter.setStretchFactor(2, 3) # Preview (Existing big part)
        self.right_splitter.setCollapsible(0, False)
        self.right_splitter.setCollapsible(1, False)
        self.right_splitter.setCollapsible(2, False)
        
        right_layout.addWidget(self.right_splitter)
        
        # Load Button (Fixed)
        self.load_btn = QPushButton("Load This Voyage")
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb; color: white; 
                font-size: 12pt; font-weight: bold; padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:disabled { background-color: #94a3b8; }
        """)
        self.load_btn.clicked.connect(self._on_load_clicked)
        self.load_btn.setEnabled(False)
        right_layout.addWidget(self.load_btn)
        
        self.splitter.addWidget(right_widget)
        self.splitter.setSizes([300, 700])
        
        layout.addWidget(self.splitter)

    def set_ship_config(self, config: ShipConfig):
        """Update ship configuration."""
        self.ship_config = config
        self.schematic_preview.set_data(config, None)

    def refresh_list(self):
        """Reload file list."""
        self.file_list.clear()
        if not os.path.exists(self.voyage_dir):
            os.makedirs(self.voyage_dir, exist_ok=True)
            
        files = [f for f in os.listdir(self.voyage_dir) if f.endswith('.voyage')]
        # Sort by filename descending (Largest/Newest number first)
        files.sort(reverse=True)
        
        for f in files:
            self.file_list.addItem(f)
            
    def _on_selection_changed(self):
        items = self.file_list.selectedItems()
        if not items:
            self._clear_preview()
            return
            
        filename = items[0].text()
        filepath = os.path.join(self.voyage_dir, filename)
        self._load_preview(filepath)
        
    def _clear_preview(self):
        self.notes_edit.clear()
        self.notes_edit.setDisabled(True)
        self.save_note_btn.setEnabled(False)
        
        # Clear totals
        self._clear_totals()
        
        self.schematic_preview.set_data(self.ship_config, None)
        self.load_btn.setEnabled(False)
        self.current_path = None
    
    def _clear_totals(self):
        # Remove all items from totals layout
        while self.totals_layout.count():
            item = self.totals_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def refresh_preview(self):
        """Re-load preview for currently selected file (used when switching back to tab after save)."""
        if self.current_path and os.path.exists(self.current_path):
            self._load_preview(self.current_path)

    def _load_preview(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract info safely
            v_data = data.get('voyage', {})
            s_data = data.get('stowage_plan', {})
            notes = v_data.get('notes', "")
            
            # Notes
            self.notes_edit.setDisabled(False)
            self.notes_edit.setText(notes)
            self.save_note_btn.setEnabled(True)
            
            # Cargo Summary - Use stowage plan for quantities, voyage parcels for colors
            self._clear_totals()
            parcels_data = v_data.get('parcels', [])
            
            # Build parcel color map from voyage parcels
            parcel_colors = {}
            for p in parcels_data:
                key = (p.get('name', ''), p.get('receiver', ''))
                parcel_colors[key] = p.get('color', '#E0E0E0')
            
            if s_data and 'cargo_requests' in s_data:
                cargos = s_data['cargo_requests']
                for i, c in enumerate(cargos):
                    name = c.get('cargo_type', 'Unknown')
                    qty = c.get('quantity', 0)
                    density = c.get('density', 0.85)
                    
                    # Calculate MT Air
                    mt_air = qty * (density - 0.0011)
                    
                    # Parse receivers
                    receivers_list = c.get('receivers', [])
                    rec_names = [r.get('name', '') for r in receivers_list]
                    rec = ", ".join(rec_names) if rec_names else ""
                    
                    # Get color from voyage parcels if available, otherwise use palette
                    color = parcel_colors.get((name, rec), CARGO_COLORS[i % len(CARGO_COLORS)])
                    if 'custom_color' in c and c['custom_color']:
                        color = c['custom_color']
                    
                    card = ParcelSummaryCard(name, mt_air, rec, color)
                    self.totals_layout.addWidget(card)
            else:
                lbl = QLabel("No plan data available")
                lbl.setStyleSheet("color: #64748b; font-style: italic;")
                self.totals_layout.addWidget(lbl)
                
            # Preview Schematic
            plan = None
            if s_data:
                plan = StowagePlan.from_dict(s_data)
            self.schematic_preview.set_data(self.ship_config, plan)
            
            self.load_btn.setEnabled(True)
            self.current_path = filepath
            
        except Exception as e:
            self._clear_preview()
            self.notes_edit.setText(f"Could not read file:\n{e}")

    def _on_save_note_clicked(self):
        """Save the editable note content back to the voyage file."""
        if not self.current_path or not os.path.exists(self.current_path):
            return
            
        try:
            # Read existing data
            with open(self.current_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Update notes
            new_notes = self.notes_edit.toPlainText()
            if 'voyage' in data:
                data['voyage']['notes'] = new_notes
            else:
                # Should not happen if structure is valid, but handle safely
                data['voyage'] = {'notes': new_notes}
                
            # Write back
            with open(self.current_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            # Visual feedback (Could also be a status bar message)
            QMessageBox.information(self, "Info", "Voyage note updated successfully.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving note:\n{e}")

    def _on_load_clicked(self):
        if hasattr(self, 'current_path') and self.current_path:
            self.voyage_loaded.emit(self.current_path)

    def save_state(self):
        """Save UI state"""
        config_dir = os.path.join(os.getcwd(), 'data', 'config')
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, 'VoyageExplorer.ini')
        
        settings = QSettings(config_path, QSettings.Format.IniFormat)
        settings.setValue("splitter_state", self.right_splitter.saveState())
        settings.setValue("main_splitter_state", self.splitter.saveState())
        
    def restore_state(self):
        """Restore UI state"""
        config_path = os.path.join(os.getcwd(), 'data', 'config', 'VoyageExplorer.ini')
        if not os.path.exists(config_path):
            return
            
        settings = QSettings(config_path, QSettings.Format.IniFormat)
        state = settings.value("splitter_state")
        if state:
            self.right_splitter.restoreState(state)
            
        main_state = settings.value("main_splitter_state")
        if main_state:
            self.splitter.restoreState(main_state)
        if main_state:
            self.splitter.restoreState(main_state)
            
    def _show_context_menu(self, pos):
        """Show context menu for list items."""
        items = self.file_list.selectedItems()
        if not items:
            return
            
        menu = QMenu(self)
        remove_action = QAction("❌ Remove from List", self)
        remove_action.setShortcut(QKeySequence("Delete"))
        remove_action.triggered.connect(self._remove_selected_voyages)
        menu.addAction(remove_action)
        
        menu.exec(self.file_list.mapToGlobal(pos))
        
    def _remove_selected_voyages(self):
        """Remove selected items from the list widget (files remain on disk)."""
        items = self.file_list.selectedItems()
        if not items:
            return
            
        selected_filenames = [item.text() for item in items]
        
        # Check if current preview is among removed items
        if self.current_path:
            current_filename = os.path.basename(self.current_path)
            if current_filename in selected_filenames:
                self._clear_preview()
        
        # Remove items
        for item in items:
            self.file_list.takeItem(self.file_list.row(item))
            
    def keyPressEvent(self, event):
        """Handle Delete key to remove items."""
        if event.key() == Qt.Key.Key_Delete:
            if self.file_list.hasFocus():
                self._remove_selected_voyages()
                event.accept()
                return
        super().keyPressEvent(event)
