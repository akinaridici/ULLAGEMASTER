"""
Data Manager - Handles configuration persistence and data loading.
"""

from pathlib import Path
from typing import Optional, Tuple
import os

from models.ship import ShipConfig


def get_data_dir() -> Path:
    """Get the DATA directory path relative to the application root.
    
    Handles both development mode (running from source) and 
    frozen mode (running as PyInstaller EXE).
    """
    import sys
    
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE - use the directory containing the EXE
        app_root = Path(sys.executable).parent
        frozen_mode = True
    else:
        # Running from source - go up from utils to src, then to app root
        current = Path(__file__).resolve()
        app_root = current.parent.parent.parent
        frozen_mode = False
    
    data_dir = app_root / "data"
    
    # Debug: Write to a log file in the app root
    try:
        debug_log = app_root / "debug_path.txt"
        with open(debug_log, 'w', encoding='utf-8') as f:
            f.write(f"Frozen mode: {frozen_mode}\n")
            f.write(f"sys.executable: {sys.executable}\n")
            f.write(f"app_root: {app_root}\n")
            f.write(f"data_dir: {data_dir}\n")
            f.write(f"data_dir exists: {data_dir.exists()}\n")
            config_path = data_dir / "config" / "ship_config.json"
            f.write(f"config_path: {config_path}\n")
            f.write(f"config_path exists: {config_path.exists()}\n")
    except Exception as e:
        pass  # Ignore debug errors
    
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
