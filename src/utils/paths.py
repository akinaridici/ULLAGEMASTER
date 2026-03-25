"""
Centralized path resolution for UllageMaster.

This module is the SINGLE SOURCE OF TRUTH for determining the application
root directory and all derived paths. It handles both normal Python execution
and PyInstaller frozen executables.

All other modules should import path functions from here instead of
computing paths independently.
"""

import sys
import tempfile
from pathlib import Path


def get_app_root() -> Path:
    """Get the application root directory.

    Supports:
    - Normal Python execution (returns project root above src/)
    - PyInstaller frozen EXE (returns directory containing the EXE)
    - Network share execution

    Returns:
        Path to the application root directory.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE — use directory containing the executable
        return Path(sys.executable).parent
    else:
        # Running from source — this file is at src/utils/paths.py
        # Go up: utils → src → project root
        return Path(__file__).resolve().parent.parent.parent


def get_data_dir() -> Path:
    """Get the path to the data/ directory.

    Returns:
        Path to app_root/data
    """
    return get_app_root() / "data"


def get_config_dir() -> Path:
    """Get the path to the data/config/ directory.

    Creates the directory if it doesn't exist.

    Returns:
        Path to app_root/data/config
    """
    config_dir = get_data_dir() / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_reports_dir() -> Path:
    """Get the path to the REPORTS/ directory.

    Creates the directory if it doesn't exist.
    Falls back to a temp directory if creation fails (e.g., read-only share).

    Returns:
        Path to the reports directory.
    """
    reports_dir = get_app_root() / "REPORTS"
    try:
        reports_dir.mkdir(exist_ok=True)
    except Exception:
        reports_dir = Path(tempfile.gettempdir()) / "UllageMaster_Reports"
        reports_dir.mkdir(exist_ok=True)
    return reports_dir


def get_voyages_dir() -> Path:
    """Get the path to the VOYAGES/ directory.

    Creates the directory if it doesn't exist.
    Falls back to a temp directory if creation fails.

    Returns:
        Path to the voyages directory.
    """
    voyages_dir = get_app_root() / "VOYAGES"
    try:
        voyages_dir.mkdir(exist_ok=True)
    except Exception:
        voyages_dir = Path(tempfile.gettempdir()) / "UllageMaster_Voyages"
        voyages_dir.mkdir(exist_ok=True)
    return voyages_dir


def get_template_path() -> Path:
    """Get the path to the XLSM template file.

    Checks both TEMPLATE/ and template/ (case-insensitive fallback).

    Returns:
        Path to TEMPLATE/TEMPLATE.XLSM (may not exist).
    """
    app_root = get_app_root()
    template_path = app_root / "TEMPLATE" / "TEMPLATE.XLSM"
    if not template_path.exists():
        template_path = app_root / "template" / "TEMPLATE.XLSM"
    return template_path


def get_logo_path() -> Path:
    """Get the path to the company logo image.

    Returns:
        Path to data/config/company_logo/LOGO.PNG (may not exist).
    """
    return get_config_dir() / "company_logo" / "LOGO.PNG"
