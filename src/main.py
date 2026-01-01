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
from PyQt6.QtGui import QPalette, QColor
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
    
    # Set application icon
    from PyQt6.QtGui import QIcon
    import os
    
    if getattr(sys, 'frozen', False):
        # In PyInstaller bundle
        bundle_dir = sys._MEIPASS
    else:
        # In Normal python
        bundle_dir = str(Path(__file__).parent.parent) # src -> root
        
    icon_path = os.path.join(bundle_dir, 'assets', 'icon.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Set style
    app.setStyle("Fusion")
    
    # Force dark theme palette (overrides system theme)
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(15, 23, 42))        # Slate 900
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(241, 245, 249)) # Slate 100
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(30, 41, 59))          # Slate 800
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(51, 65, 85)) # Slate 700
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(30, 41, 59))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(241, 245, 249))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(241, 245, 249))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(51, 65, 85))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(241, 245, 249))
    dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(56, 189, 248))        # Sky 400
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(59, 130, 246))   # Blue 500
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(dark_palette)
    
    # Apply professional theme stylesheet
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
