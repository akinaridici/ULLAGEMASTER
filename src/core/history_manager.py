"""
History Manager Module

Manages autocomplete history for Report Functions fields.
Stores up to 10 entries per field in an INI file.
Uses MRU (Most Recently Used) ordering with case-insensitive deduplication.
"""

import configparser
from pathlib import Path
from typing import List
import os


class HistoryManager:
    """Manages autocomplete history stored in an INI file."""
    
    MAX_ENTRIES = 10
    
    # Field name mappings for INI sections
    FIELDS = [
        'port',
        'terminal', 
        'mmc_no',
        'report_type',
        'cargo',
        'receiver'
    ]
    
    def __init__(self, ini_path: str = None):
        """
        Initialize the history manager.
        
        Args:
            ini_path: Path to INI file. Defaults to data/report_history.ini
        """
        if ini_path is None:
            # Default path relative to project root
            base_dir = Path(__file__).parent.parent.parent  # src/core -> src -> project root
            self.ini_path = base_dir / "data" / "report_history.ini"
        else:
            self.ini_path = Path(ini_path)
        
        self._config = configparser.ConfigParser()
        self._load()
    
    def _load(self):
        """Load history from INI file."""
        if self.ini_path.exists():
            try:
                self._config.read(self.ini_path, encoding='utf-8')
            except Exception:
                # If file is corrupted, start fresh
                self._config = configparser.ConfigParser()
    
    def _save(self):
        """Save history to INI file."""
        # Ensure directory exists
        self.ini_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.ini_path, 'w', encoding='utf-8') as f:
            self._config.write(f)
    
    def get_history(self, field_name: str) -> List[str]:
        """
        Get history entries for a field.
        
        Args:
            field_name: One of the FIELDS names
            
        Returns:
            List of up to MAX_ENTRIES strings, most recent first
        """
        if field_name not in self._config.sections():
            return []
        
        entries = []
        for i in range(self.MAX_ENTRIES):
            key = str(i)
            if key in self._config[field_name]:
                value = self._config[field_name][key]
                if value:  # Skip empty entries
                    entries.append(value)
        
        return entries
    
    def add_entry(self, field_name: str, value: str):
        """
        Add an entry to field history.
        
        - Moves to top if already exists (MRU)
        - Case-insensitive deduplication
        - Trims to MAX_ENTRIES
        
        Args:
            field_name: One of the FIELDS names
            value: The value to add
        """
        if not value or not value.strip():
            return
        
        value = value.strip()
        
        # Get current history
        entries = self.get_history(field_name)
        
        # Remove existing entry (case-insensitive)
        entries = [e for e in entries if e.lower() != value.lower()]
        
        # Add to top
        entries.insert(0, value)
        
        # Trim to max
        entries = entries[:self.MAX_ENTRIES]
        
        # Ensure section exists
        if field_name not in self._config.sections():
            self._config.add_section(field_name)
        
        # Clear old entries
        for key in list(self._config[field_name].keys()):
            del self._config[field_name][key]
        
        # Write new entries
        for i, entry in enumerate(entries):
            self._config[field_name][str(i)] = entry
        
        self._save()
    
    def save_all(self, data: dict):
        """
        Save multiple field values at once.
        
        Args:
            data: Dict with field_name -> value mappings
        """
        for field_name, value in data.items():
            if field_name in self.FIELDS:
                self.add_entry(field_name, value)


# Singleton instance for easy access
_instance = None

def get_history_manager() -> HistoryManager:
    """Get the singleton HistoryManager instance."""
    global _instance
    if _instance is None:
        _instance = HistoryManager()
    return _instance
