"""
Company Logo Setup Dialog.
"""

import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QRadioButton, QWidget, QFileDialog, QMessageBox,
    QGroupBox, QPlainTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from utils.config_manager import get_config
from utils.data_manager import get_data_dir
from i18n import t

class LogoSetupDialog(QDialog):
    """
    Dialog to configure Company Logo (Image vs Text).
    PERSISTENCE: Stores settings in 'data/config/UllageMaster.ini' via ConfigManager.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("logo", "menu"))
        self.setMinimumSize(450, 400)
        
        self.config = get_config()
        self.logo_dir = get_data_dir() / "config" / "company_logo"
        self.logo_dir.mkdir(parents=True, exist_ok=True)
        self.current_logo_path = self.logo_dir / "LOGO.PNG"
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Mode Selection
        mode_group = QGroupBox("Logo Mode")
        mode_layout = QHBoxLayout(mode_group)
        
        self.radio_image = QRadioButton("Use Image (PNG)")
        self.radio_text = QRadioButton("Use Text Label")
        
        self.radio_image.toggled.connect(self._toggle_mode)
        self.radio_text.toggled.connect(self._toggle_mode)
        
        mode_layout.addWidget(self.radio_image)
        mode_layout.addWidget(self.radio_text)
        main_layout.addWidget(mode_group)
        
        # Image Settings Section
        self.image_widget = QWidget()
        img_layout = QVBoxLayout(self.image_widget)
        
        info_lbl = QLabel(
            "Recommended: Transparent PNG.\n"
            "Aspect Ratio: Square or Landscape.\n"
            "Min Resolution: 300x300px."
        )
        info_lbl.setStyleSheet("color: #64748b; font-style: italic;")
        img_layout.addWidget(info_lbl)
        
        # Preview Area
        self.preview_lbl = QLabel("No Image")
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_lbl.setMinimumHeight(150)
        self.preview_lbl.setStyleSheet("border: 2px dashed #cbd5e1; background-color: #f1f5f9;")
        img_layout.addWidget(self.preview_lbl)
        
        browse_btn = QPushButton("Browse Image...")
        browse_btn.clicked.connect(self._browse_image)
        img_layout.addWidget(browse_btn)
        
        main_layout.addWidget(self.image_widget)
        
        # Text Settings Section
        self.text_widget = QWidget()
        txt_layout = QVBoxLayout(self.text_widget)
        
        txt_layout.addWidget(QLabel("Company Name (use Enter for new line):"))
        self.text_input = QPlainTextEdit()
        self.text_input.setMaximumHeight(100)
        txt_layout.addWidget(self.text_input)
        
        main_layout.addWidget(self.text_widget)
        
        # Bottom Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_data)
        save_btn.setStyleSheet("background-color: #0d9488; color: white; font-weight: bold; padding: 6px;")
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        main_layout.addStretch()
        main_layout.addLayout(btn_layout)

    def _toggle_mode(self):
        """Toggle visibility between image and text widgets."""
        is_image = self.radio_image.isChecked()
        self.image_widget.setVisible(is_image)
        self.text_widget.setVisible(not is_image)

    def _browse_image(self):
        """Browse for logo image file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Logo Image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            try:
                shutil.copy2(file_path, self.current_logo_path)
                self.update_image_preview()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import logo: {e}")
        
    def load_data(self):
        """Load settings from ConfigManager."""
        section = self.config.get_section("LOGO_SETTINGS")
        mode = section.get("mode", "IMAGE")
        text_content = section.get("text_content", "Battal\\nMarine").replace("\\n", "\n")
        
        if mode == "IMAGE":
            self.radio_image.setChecked(True)
        else:
            self.radio_text.setChecked(True)
            
        self.text_input.setPlainText(text_content)
        
        # Load image preview if exists
        self.update_image_preview()
        self._toggle_mode()

    def update_image_preview(self):
        """Update logo image preview."""
        if self.current_logo_path.exists():
            pixmap = QPixmap(str(self.current_logo_path))
            if not pixmap.isNull():
                self.preview_lbl.setPixmap(pixmap.scaled(
                    self.preview_lbl.size(), 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                ))
            else:
                self.preview_lbl.setText("Invalid Image")
        else:
            self.preview_lbl.setText("No Image Selected")

    def save_data(self):
        """Save settings to ConfigManager."""
        mode = "IMAGE" if self.radio_image.isChecked() else "TEXT"
        text_content = self.text_input.toPlainText().replace("\n", "\\n")
        
        self.config.set_section("LOGO_SETTINGS", {
            "mode": mode,
            "text_content": text_content,
            "image_filename": "LOGO.PNG"
        })
        
        QMessageBox.information(self, "Saved", "Logo settings saved successfully.")
        self.accept()

