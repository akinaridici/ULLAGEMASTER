"""
Backup Manager Module.
Handles backing up and restoring critical application configuration files.
"""

import shutil
import os
import sys
from pathlib import Path
from typing import Tuple, List

# Constants
BACKUP_PASSWORD = "19771977"

def get_app_root() -> Path:
    """
    Get the application root directory.
    
    Supports:
    - Normal Python execution
    - PyInstaller frozen EXE
    - Network share execution
    """
    if getattr(sys, 'frozen', False):
        # Running as frozen executable - use EXE location
        return Path(sys.executable).parent
    else:
        # src/utils -> src -> root
        return Path(__file__).parent.parent.parent

def get_default_backup_dir() -> Path:
    """Get the default BACKUP directory path. Creates if doesn't exist."""
    backup_dir = get_app_root() / "BACKUP"
    # Create directory if it doesn't exist
    if not backup_dir.exists():
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # If we can't create, return home directory as fallback
            return Path.home() / "UllageMaster_Backup"
    return backup_dir

def safe_copy(source: Path, destination: Path):
    """safely copy file, ensuring parent dirs exist."""
    if not source.exists():
        return
    
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)

def create_backup(target_dir: str) -> Tuple[bool, str]:
    """
    Create a backup of critical files to the target directory.
    
    Files to backup:
    - data/config/ship_config.json
    - assets/company_logo.png
    
    Args:
        target_dir: Directory to save backup files to
        
    Returns:
        (success, message)
    """
    try:
        app_root = get_app_root()
        target_path = Path(target_dir)
        
        # Define files to backup (source_rel_path, dest_rel_path)
        # We preserve structure relative to app root
        files_to_backup = [
            ("data/config/ship_config.json", "ship_config.json"),
            ("assets/company_logo.png", "company_logo.png")
        ]
        
        count = 0
        for src_rel, dest_name in files_to_backup:
            source = app_root / src_rel
            if source.exists():
                dest = target_path / dest_name
                safe_copy(source, dest)
                count += 1
                
        if count == 0:
            return False, "No configuration files found to backup."
            
        return True, f"Backup completed successfully to:\n{target_dir}"
        
    except Exception as e:
        return False, f"Backup failed: {str(e)}"

def restore_backup(source_dir: str) -> Tuple[bool, str]:
    """
    Restore files from backup directory to application folders.
    
    Args:
        source_dir: Directory containing backup files
        
    Returns:
        (success, message)
    """
    try:
        app_root = get_app_root()
        source_path = Path(source_dir)
        
        # Files to restore mapping: backup_name -> system_rel_path
        restore_map = {
            "ship_config.json": "data/config/ship_config.json",
            "company_logo.png": "assets/company_logo.png"
        }
        
        count = 0
        restored_files = []
        
        for backup_name, system_rel in restore_map.items():
            source_file = source_path / backup_name
            if source_file.exists():
                dest_file = app_root / system_rel
                safe_copy(source_file, dest_file)
                count += 1
                restored_files.append(backup_name)
        
        if count == 0:
            return False, "No valid backup files found in selected directory."
            
        return True, f"Restored {count} files successfully:\n" + "\n".join(restored_files)
        
    except Exception as e:
        return False, f"Restore failed: {str(e)}"

def verify_password(password: str) -> bool:
    """Check if provided password matches the restore password."""
    return password == BACKUP_PASSWORD
