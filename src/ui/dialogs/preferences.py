"""
Preferences Dialog - Application settings.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QDoubleSpinBox, QPushButton,
    QGroupBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt

from i18n import t, set_language, get_available_languages, get_current_language


class PreferencesDialog(QDialog):
    """Dialog for application preferences."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(t("title", "settings"))
        self.setMinimumWidth(400)
        
        self._setup_ui()
        self._load_current_settings()
    
    def _setup_ui(self):
        """Create dialog UI."""
        layout = QVBoxLayout(self)
        
        # Language section
        lang_group = QGroupBox(t("language", "settings"))
        lang_layout = QFormLayout(lang_group)
        
        self.lang_combo = QComboBox()
        for code, name in get_available_languages().items():
            self.lang_combo.addItem(name, code)
        
        lang_layout.addRow("Language / Dil:", self.lang_combo)
        layout.addWidget(lang_group)
        
        # Unit system section
        unit_group = QGroupBox(t("unit_system", "settings"))
        unit_layout = QVBoxLayout(unit_group)
        
        self.unit_button_group = QButtonGroup(self)
        
        self.metric_radio = QRadioButton(t("metric", "settings"))
        self.imperial_radio = QRadioButton(t("imperial", "settings"))
        
        self.unit_button_group.addButton(self.metric_radio, 0)
        self.unit_button_group.addButton(self.imperial_radio, 1)
        
        unit_layout.addWidget(self.metric_radio)
        unit_layout.addWidget(self.imperial_radio)
        
        layout.addWidget(unit_group)
        
        # Default values section
        defaults_group = QGroupBox("Default Values")
        defaults_layout = QFormLayout(defaults_group)
        
        self.default_vef_spin = QDoubleSpinBox()
        self.default_vef_spin.setDecimals(5)
        self.default_vef_spin.setRange(0.9, 1.1)
        self.default_vef_spin.setValue(1.0)
        self.default_vef_spin.setSingleStep(0.00001)
        defaults_layout.addRow(t("default_vef", "settings"), self.default_vef_spin)
        
        self.default_temp_spin = QDoubleSpinBox()
        self.default_temp_spin.setDecimals(1)
        self.default_temp_spin.setRange(-20, 100)
        self.default_temp_spin.setValue(15.0)
        self.default_temp_spin.setSuffix(" °C")
        defaults_layout.addRow("Default Temperature:", self.default_temp_spin)
        
        self.default_density_spin = QDoubleSpinBox()
        self.default_density_spin.setDecimals(1)
        self.default_density_spin.setRange(600, 1100)
        self.default_density_spin.setValue(850.0)
        self.default_density_spin.setSuffix(" kg/m³")
        defaults_layout.addRow("Default Density:", self.default_density_spin)
        
        layout.addWidget(defaults_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton(t("save", "dialogs"))
        save_btn.clicked.connect(self._save_and_close)
        
        cancel_btn = QPushButton(t("cancel", "dialogs"))
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _load_current_settings(self):
        """Load current settings into UI."""
        # Set current language
        current_lang = get_current_language()
        index = self.lang_combo.findData(current_lang)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)
        
        # Set unit system (default to metric)
        self.metric_radio.setChecked(True)
    
    def _save_and_close(self):
        """Save settings and close dialog."""
        # Apply language change
        new_lang = self.lang_combo.currentData()
        if new_lang:
            set_language(new_lang)
        
        # TODO: Save other settings to config file
        
        self.accept()
    
    def get_settings(self) -> dict:
        """Get current settings."""
        return {
            "language": self.lang_combo.currentData(),
            "unit_system": "metric" if self.metric_radio.isChecked() else "imperial",
            "default_vef": self.default_vef_spin.value(),
            "default_temp": self.default_temp_spin.value(),
            "default_density": self.default_density_spin.value(),
        }
