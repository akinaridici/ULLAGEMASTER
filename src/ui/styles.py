"""
Professional UI Theme for UllageMaster.
Defines colors, fonts, and global stylesheet.
"""

from PyQt6.QtGui import QColor

# --- Color Palette (Dark Theme) ---
# Window & Panels
COLOR_WINDOW_BG = "#0f172a"       # Slate 900 (Deepest background)
COLOR_PANEL_BG = "#1e293b"        # Slate 800 (Panel background)
COLOR_TEXT_PRIMARY = "#f1f5f9"    # Slate 100 (Bright text)
COLOR_TEXT_SECONDARY = "#94a3b8"  # Slate 400 (Muted text)

# Table Colors
# Input cells: Dark Slate
COLOR_CELL_INPUT = QColor(30, 41, 59)    # Slate 800
# Calculated cells: Darker Slate
COLOR_CELL_CALCULATED = QColor(15, 23, 42) # Slate 900
# Text in cells: White
COLOR_CELL_TEXT = QColor(241, 245, 249)  # Slate 100

# Header Colors
COLOR_TABLE_HEADER = "#334155"    # Slate 700
COLOR_HEADER_TEXT = "#ffffff"     # White

# Accents
COLOR_ACCENT = "#38bdf8"          # Sky 400 (Bright blue accent)
COLOR_BUTTON_BG = "#3b82f6"       # Blue 500
COLOR_BUTTON_HOVER = "#60a5fa"    # Blue 400
COLOR_DANGER = "#ef4444"          # Red 500
COLOR_WARNING_HIGH = "#eab308"    # Yellow 500
COLOR_WARNING_LOW = "#f97316"     # Orange 500

# --- Global Stylesheet ---
GLOBAL_STYLESHEET = """
/* Main Window & Defaults */
QMainWindow, QDialog {
    background-color: #0f172a;
}

QWidget {
    font-family: "Segoe UI", "Roboto", sans-serif;
    font-size: 10pt;
    color: #f1f5f9;
}

/* Group Boxes */
QGroupBox {
    background-color: #1e293b;
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
    color: #38bdf8;
}

/* Inputs (LineEdits, SpinBoxes) */
QLineEdit, QDoubleSpinBox, QSpinBox {
    background-color: #0f172a; /* Dark background */
    color: #f1f5f9;            /* Light text */
    border: 1px solid #475569;
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: #0ea5e9;
    selection-color: #ffffff;
    font-weight: 500;
}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
    border: 2px solid #38bdf8;
    background-color: #1e293b;
}
QLineEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled {
    background-color: #334155;
    color: #94a3b8;
    border: 1px solid #334155;
}

/* Labels */
QLabel {
    color: #cbd5e1;
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
    background-color: #334155;
    color: #64748b;
}

/* Table Widget */
QTableWidget {
    background-color: #0f172a; /* Dark Grid Background */
    gridline-color: #334155;   /* Subtle Grid Lines */
    border: 1px solid #475569;
    border-radius: 4px;
    selection-background-color: #0c4a6e; /* Dark Blue Selection */
    selection-color: #ffffff;
    font-size: 11px;
    color: #f1f5f9;
}
QTableWidget::item {
    padding: 4px;
    border-bottom: 1px solid #1e293b;
    background-color: transparent; /* Use delegate/model background */
}
QTableWidget::item:selected {
    background-color: #0c4a6e;
    color: white;
}
QTableWidget::item:focus {
    border: 1px solid #38bdf8;
    outline: none;
}

/* Cell Editor - thin border for better text visibility */
QTableWidget QLineEdit {
    border: 1px solid #38bdf8;
    background-color: #1e293b;
    color: #38bdf8;
    padding: 1px 2px;
    font-size: 11px;
}

/* Table Header */
QHeaderView::section {
    background-color: #1e293b;
    color: #e2e8f0;
    padding: 6px;
    border: none;
    border-right: 1px solid #334155;
    border-bottom: 2px solid #38bdf8;
    font-weight: bold;
    text-transform: uppercase;
    font-size: 10px;
}

/* Scrollbars - Dark */
QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 12px;
    margin: 0px;
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
QScrollBar:add-line:vertical, QScrollBar:sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #0f172a;
    height: 12px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #475569;
    min-width: 20px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar:handle:horizontal:hover {
    background: #64748b;
}
QScrollBar:add-line:horizontal, QScrollBar:sub-line:horizontal {
    width: 0px;
}

/* Menus */
QMenuBar {
    background-color: #1e293b;
    color: #f1f5f9;
}
QMenuBar::item:selected {
    background-color: #334155;
}
QMenu {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #475569;
}
QMenu::item:selected {
    background-color: #334155;
}
"""
