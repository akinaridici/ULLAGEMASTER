"""
Professional UI Theme for UllageMaster.
Defines colors, fonts, and global stylesheet.
"""

from PyQt6.QtGui import QColor

# --- Color Palette ---
# Window & Panels
COLOR_WINDOW_BG = "#1e293b"       # Dark Slate 800
COLOR_PANEL_BG = "#0f172a"        # Dark Slate 900
COLOR_TEXT_PRIMARY = "#f8fafc"    # Slate 50
COLOR_TEXT_SECONDARY = "#94a3b8"  # Slate 400

# Table Colors (Refined)
# Input cells: Subtle Professional Blue
COLOR_CELL_INPUT = QColor(224, 242, 254)  # Sky 100
# Calculated cells: Clean Light Gray
COLOR_CELL_CALCULATED = QColor(241, 245, 249) # Slate 100
# Text in cells: Dark Slate for readability
COLOR_CELL_TEXT = QColor(15, 23, 42)      # Slate 900

# Header Colors
COLOR_TABLE_HEADER = "#334155"    # Slate 700
COLOR_HEADER_TEXT = "#ffffff"     # White

# Accents
COLOR_ACCENT = "#0ea5e9"          # Sky 500 (Focus ring)
COLOR_BUTTON_BG = "#3b82f6"       # Blue 500
COLOR_BUTTON_HOVER = "#2563eb"    # Blue 600
COLOR_DANGER = "#ef4444"          # Red 500
COLOR_WARNING_HIGH = "#eab308"    # Yellow 500
COLOR_WARNING_LOW = "#f97316"     # Orange 500

# --- Global Stylesheet ---
GLOBAL_STYLESHEET = """
/* Main Window & Defaults */
QMainWindow {
    background-color: #1e293b;
}

QWidget {
    font-family: "Segoe UI", "Roboto", sans-serif;
    font-size: 10pt;
    color: #f8fafc;
}

/* Group Boxes */
QGroupBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    margin-top: 1.2em;
    padding-top: 15px;
    padding-bottom: 10px;
    font-weight: bold;
    color: #e2e8f0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    left: 10px;
    color: #38bdf8; /* Accent color for titles */
}

/* Inputs (LineEdits, SpinBoxes) */
QLineEdit, QDoubleSpinBox, QSpinBox {
    background-color: #ffffff;
    color: #0f172a; /* Dark text for inputs */
    border: 1px solid #94a3b8;
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: #0ea5e9;
    selection-color: #ffffff;
    font-weight: 500;
}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
    border: 2px solid #38bdf8;
    background-color: #f0f9ff;
}
QLineEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled {
    background-color: #cbd5e1;
    color: #64748b;
}

/* Labels */
QLabel {
    color: #cbd5e1; /* Slightly muted text for labels */
}

/* Buttons */
QPushButton {
    background-color: #3b82f6;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2563eb;
}
QPushButton:pressed {
    background-color: #1d4ed8;
}
QPushButton:disabled {
    background-color: #64748b;
    color: #cbd5e1;
}

/* Table Widget - The Core Interface */
QTableWidget {
    background-color: #f1f5f9;
    gridline-color: #cbd5e1;
    border: 1px solid #475569;
    border-radius: 4px;
    selection-background-color: #0ea5e9;
    selection-color: #ffffff;
    font-size: 11px; /* Dense data needs slightly smaller font */
    color: #0f172a;
}
QTableWidget::item {
    padding: 4px;
    border-bottom: 1px solid #e2e8f0;
}
QTableWidget::item:selected {
    background-color: #0ea5e9;
    color: white;
}

/* Fix for Table Cell Editors - prevent thick borders/padding from clipping text */
QTableWidget QLineEdit {
    border: none;
    padding: 0px;
    margin: 0px;
    border-radius: 0px;
    background-color: #ffffff;
    color: #0f172a;
}
QTableWidget QLineEdit:focus {
    border: 2px solid #38bdf8; /* Visible focus but minimal padding */
    padding: 0px;
    background-color: #ffffff;
}

/* Table Header */
QHeaderView::section {
    background-color: #334155;
    color: #ffffff;
    padding: 6px;
    border: none;
    border-right: 1px solid #475569;
    border-bottom: 2px solid #38bdf8; /* Accent line under header */
    font-weight: bold;
    text-transform: uppercase;
    font-size: 10px;
}
QHeaderView::section:horizontal {
    border-top: 1px solid #475569;
}
QHeaderView::section:vertical {
    border-left: 1px solid #475569;
}

/* Scrollbars - Clean Modern Look */
QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 12px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #475569;
    min-height: 20px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background: #64748b;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #0f172a;
    height: 12px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:horizontal {
    background: #475569;
    min-width: 20px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background: #64748b;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""
