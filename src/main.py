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
    
    # Create the splash screen
    from ui.splash_screen import TankSplashScreen
    from PyQt6.QtCore import QTimer
    splash = TankSplashScreen()
    splash.show()
    
    # Container to keep window reference alive
    context = {"window": None}
    
    def start_loading():
        """Initialize the main window after the event loop has started."""
        # The MainWindow class acts as the central controller for the application
        context["window"] = MainWindow()
        # Connect splash screen finish signal to main window show
        splash.loading_complete.connect(context["window"].show)

    # Defer main window loading to ensure splash is visible first
    QTimer.singleShot(100, start_loading)
    
    # Start the event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
