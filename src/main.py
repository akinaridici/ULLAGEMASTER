"""
UllageMaster - Main Entry Point
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow


def main():
    """Main entry point for UllageMaster."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("UllageMaster")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("UllageMaster")
    
    # Set style
    app.setStyle("Fusion")
    
    # Apply professional theme
    from ui.styles import GLOBAL_STYLESHEET
    app.setStyleSheet(GLOBAL_STYLESHEET)
    
    # Create and show main window
    # The MainWindow class acts as the central controller for the application
    window = MainWindow()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
