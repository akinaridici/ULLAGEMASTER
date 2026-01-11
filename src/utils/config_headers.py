"""
Configuration manager for Report Headers (Company Info).
Handles reading/writing to COMPANYINFO.ini in Data/Config directory.
"""

import configparser
import os
from pathlib import Path
from typing import Dict

# Reuse existing robust path logic
from utils.data_manager import get_data_dir

# Default Values matching current hardcoded strings
DEFAULT_CONFIG = {
    "ULLAGE_REPORT": {
        "title_line_1": "INTEGRATED MANAGEMENT SYSTEM MANUAL",
        "title_line_2": "Chapter 7.5",
        "title_line_3": "ULLAGE REPORT & TEMPERATURE LOG",
        "issue_no": "02",
        "issue_date": "01/11/2024",
        "rev_no": "0",
        "page_format": "Page: 1" # Used as prefix or format
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
        "mode": "IMAGE",  # IMAGE or TEXT
        "text_content": "Battal\nMarine",
        "image_filename": "LOGO.PNG"
    }
}

def get_header_config_path() -> Path:
    """Get path to COMPANYINFO.ini."""
    return get_data_dir() / "config" / "COMPANYINFO.ini"

def load_header_config() -> Dict:
    """
    Load header configuration from INI file.
    Returns a dictionary structure matching DEFAULT_CONFIG.
    Creates default file if it doesn't exist.
    """
    config_path = get_header_config_path()
    config = configparser.ConfigParser()
    
    # Load defaults first
    config.read_dict(DEFAULT_CONFIG)
    
    # Read file if exists
    if config_path.exists():
        try:
            config.read(str(config_path), encoding='utf-8')
        except Exception as e:
            print(f"Error reading header config: {e}")
    else:
        # Create default file
        save_header_config(config)
        
    # Convert to dict
    result = {}
    for section in config.sections():
        result[section] = dict(config[section])
        
    return result

def save_header_config(data) -> bool:
    """
    Save configuration to INI file.
    Args:
        data: Dict or ConfigParser object
    """
    config_path = get_header_config_path()
    
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if isinstance(data, configparser.ConfigParser):
            config = data
        else:
            config = configparser.ConfigParser()
            config.read_dict(data)
            
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)
        return True
    except Exception as e:
        print(f"Error saving header config: {e}")
        return False
