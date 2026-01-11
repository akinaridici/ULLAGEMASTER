"""
Configuration Manager for UllageMaster.
Handles portable configuration in data/config/UllageMaster.ini.
Replaces Registry (QSettings) and multiple dispersed INI files.
"""

import configparser
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

class ConfigManager:
    _instance = None
    
    # Default Configuration Structure
    DEFAULT_CONFIG = {
        "General": {
            "language": "en",
            "last_dir": "",
            "last_tab": "0",
            "window_geometry": ""  # Reserved for future usage
        },
        "VoyageExplorer": {
            "splitter_state": "",
            "main_splitter_state": ""
        },
        "Discrepancy": {
            "splitter_state": ""
        },
        # From ConfigHeaders / COMPANYINFO.ini
        "ULLAGE_REPORT": {
            "title_line_1": "INTEGRATED MANAGEMENT SYSTEM MANUAL",
            "title_line_2": "Chapter 7.5",
            "title_line_3": "ULLAGE REPORT & TEMPERATURE LOG",
            "issue_no": "02",
            "issue_date": "01/11/2024",
            "rev_no": "0",
            "page_format": "Page: 1"
        },
        "PROTEST_REPORT": {
            "title_line_1": "INTEGRATED MANAGEMENT SYSTEM MANUAL",
            "title_line_2": "Chapter 7.5",
            "doc_title": "LETTER OF PROTEST",
            "issue_no": "2",
            "issue_date": "1.11.2024",
            "rev_no": "0",
            "rev_date": "00/00/0000"
        },
        "LOGO_SETTINGS": {
            "mode": "IMAGE",
            "text_content": "Battal\\nMarine",
            "image_filename": "LOGO.PNG"
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._config = configparser.ConfigParser()
        self._path = self._get_config_path()
        self._load()
        self._initialized = True

    def _get_config_path(self) -> Path:
        """Determine path to UllageMaster.ini."""
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            # src/utils -> src -> root
            base_dir = Path(__file__).parent.parent.parent
            
        config_dir = base_dir / "data" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "UllageMaster.ini"

    def _load(self):
        """Load configuration from file or create with defaults."""
        # Load defaults first
        self._config.read_dict(self.DEFAULT_CONFIG)
        
        if self._path.exists():
            try:
                self._config.read(str(self._path), encoding='utf-8')
            except Exception as e:
                print(f"Error loading config: {e}")
                # Keep defaults if file is corrupt
        else:
            self._save()

    def _save(self):
        """Save current configuration to file."""
        try:
            with open(self._path, 'w', encoding='utf-8') as f:
                self._config.write(f)
        except Exception as e:
            print(f"Error saving config: {e}")

    # --- Generic Accessors ---

    def get_str(self, section: str, key: str, default: str = "") -> str:
        return self._config.get(section, key, fallback=default)

    def set_str(self, section: str, key: str, value: str):
        if section not in self._config:
            self._config.add_section(section)
        self._config.set(section, key, str(value))
        self._save()

    def get_int(self, section: str, key: str, default: int = 0) -> int:
        return self._config.getint(section, key, fallback=default)

    def set_int(self, section: str, key: str, value: int):
        self.set_str(section, key, str(value))

    def get_section(self, section: str) -> Dict[str, str]:
        """Return a section as a dictionary."""
        if section in self._config:
            return dict(self._config[section])
        return {}

    def set_section(self, section: str, data: Dict[str, str]):
        """Update an entire section."""
        if section not in self._config:
            self._config.add_section(section)
        for k, v in data.items():
            self._config.set(section, k, str(v))
        self._save()

# Global accessor
def get_config() -> ConfigManager:
    return ConfigManager()
