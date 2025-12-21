"""
Template Report Export Module.
Copies a user-provided XLSM template, injects grid data, and saves as a new file.
"""

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Optional

try:
    import openpyxl
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

if TYPE_CHECKING:
    from ..models.voyage import Voyage


def get_template_path() -> Path:
    """Get the path to the TEMPLATE directory."""
    # Template folder is in the application root directory
    app_dir = Path(__file__).parent.parent.parent  # src/export -> src -> app_root
    return app_dir / "TEMPLATE" / "TEMPLATE.XLSM"


def export_template_report(voyage: 'Voyage', output_path: str, column_keys: list) -> bool:
    """
    Export grid data to a copy of the XLSM template.
    
    Args:
        voyage: The voyage containing tank readings data.
        output_path: Path where the new file will be saved.
        column_keys: List of column keys matching the grid order.
        
    Returns:
        True if successful, False otherwise.
    """
    if not OPENPYXL_AVAILABLE:
        print("openpyxl not available. Install with: pip install openpyxl")
        return False
    
    template_path = get_template_path()
    
    if not template_path.exists():
        print(f"Template not found: {template_path}")
        return False
    
    try:
        # Copy template to output path
        shutil.copy2(str(template_path), output_path)
        
        # Open the copy (keep_vba=True preserves macros)
        wb = load_workbook(output_path, keep_vba=True)
        
        # Check if DATA sheet exists
        if "DATA" not in wb.sheetnames:
            print("DATA sheet not found in template. Creating it.")
            wb.create_sheet("DATA")
        
        ws = wb["DATA"]
        
        # Write headers (row 1)
        for col_idx, key in enumerate(column_keys, start=1):
            ws.cell(row=1, column=col_idx, value=key.upper())
        
        # Write data (row 2 onwards)
        row_idx = 2
        for tank_id, reading in voyage.tank_readings.items():
            for col_idx, key in enumerate(column_keys, start=1):
                value = _get_reading_value(reading, key, voyage)
                ws.cell(row=row_idx, column=col_idx, value=value)
            row_idx += 1
        
        wb.save(output_path)
        wb.close()
        
        return True
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error exporting template report: {e}")
        return False


def _get_reading_value(reading, key: str, voyage: 'Voyage'):
    """Get a value from reading by key, with special handling for some fields."""
    # Direct attribute access for most keys
    if hasattr(reading, key):
        return getattr(reading, key, None)
    
    # Special cases
    if key == "tank_id":
        return reading.tank_id
    elif key == "parcel":
        return reading.parcel_id or ""
    elif key == "grade":
        # Get grade from parcel
        if reading.parcel_id and reading.parcel_id != "SLOP":
            for p in voyage.parcels:
                if p.id == reading.parcel_id:
                    return p.name
        return "SLOP" if reading.parcel_id == "SLOP" else ""
    elif key == "receiver":
        # Get receiver from parcel
        if reading.parcel_id and reading.parcel_id != "SLOP":
            for p in voyage.parcels:
                if p.id == reading.parcel_id:
                    return p.receiver
        return ""
    elif key == "temp":
        return reading.temp_celsius
    elif key == "ullage":
        return reading.ullage
    
    return None
