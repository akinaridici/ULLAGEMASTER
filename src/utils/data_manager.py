"""
Data Manager - Handles configuration persistence and data loading.
"""

from pathlib import Path
from typing import Optional, Tuple
import os

from models.ship import ShipConfig


def get_data_dir() -> Path:
    """Get the DATA directory path relative to the application root."""
    # Try to find the app root (where main.py is)
    current = Path(__file__).resolve()
    
    # Go up from utils to src, then to app root
    app_root = current.parent.parent.parent
    data_dir = app_root / "data"
    
    return data_dir


def get_config_path() -> Path:
    """Get the path to the ship config JSON file."""
    return get_data_dir() / "config" / "ship_config.json"


def config_exists() -> bool:
    """Check if a ship configuration file exists (quick check, no loading)."""
    config_path = get_config_path()
    if not config_path.exists():
        return False
    # Quick check: file exists and has meaningful size (> 100 bytes)
    return config_path.stat().st_size > 100


def load_config() -> Optional[ShipConfig]:
    """
    Load the ship configuration from the default path.
    
    Returns:
        ShipConfig object if file exists and is valid.
        None if file does not exist or loading fails.
        
    Raises:
        Exceptions are caught internally and printed to stdout.
    """
    config_path = get_config_path()
    if not config_path.exists():
        return None
    
    try:
        return ShipConfig.load_from_json(str(config_path))
    except Exception as e:
        print(f"Error loading config: {e}")
        return None


def save_config(config: ShipConfig) -> bool:
    """
    Save the ship configuration to the default path.
    
    Args:
        config: The ShipConfig object to persist.
        
    Returns:
        True if save was successful, False otherwise.
    """
    try:
        config_path = get_config_path()
        config.save_to_json(str(config_path))
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def delete_config() -> bool:
    """Delete the current ship configuration (for reset)."""
    config_path = get_config_path()
    try:
        if config_path.exists():
            config_path.unlink()
        return True
    except Exception as e:
        print(f"Error deleting config: {e}")
        return False
