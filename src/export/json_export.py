"""
JSON export for Stowage Plan.
"""

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.voyage import Voyage


def export_stowage_plan(voyage: 'Voyage', filepath: str) -> bool:
    """
    Export voyage data as a structured JSON stowage plan.
    
    Args:
        voyage: Voyage object with all tank readings
        filepath: Output file path
        
    Returns:
        True if successful
    """
    try:
        # Build stowage plan structure
        stowage_plan = {
            "voyage": {
                "number": voyage.voyage_number,
                "port": voyage.port,
                "terminal": voyage.terminal,
                "date": voyage.date
            },
            "vef": voyage.vef,
            "drafts": {
                "aft": voyage.drafts.aft,
                "fwd": voyage.drafts.fwd,
                "trim": voyage.drafts.trim
            },
            "officers": {
                "chief_officer": voyage.chief_officer,
                "master": voyage.master
            },
            "tanks": [],
            "totals": {
                "gsv": voyage.total_gsv,
                "mt": voyage.total_mt
            }
        }
        
        # Add tank data
        for tank_id, reading in voyage.tank_readings.items():
            tank_data = {
                "id": tank_id,
                "parcel": reading.parcel,
                "grade": reading.grade,
                "receiver": reading.receiver,
                "ullage": reading.ullage,
                "fill_percent": reading.fill_percent,
                "tov": round(reading.tov, 3),
                "trim_correction": round(reading.trim_correction, 3),
                "gov": round(reading.gov, 3),
                "temp": reading.temp_celsius,
                "vcf": round(reading.vcf, 5),
                "gsv": round(reading.gsv, 3),
                "density_vac": reading.density_vac,
                "density_air": round(reading.density_air, 3),
                "mt_air": round(reading.mt_air, 3),
                "mt_vac": round(reading.mt_vac, 3),
                "discrepancy": round(reading.discrepancy, 3),
                "warning": reading.warning
            }
            stowage_plan["tanks"].append(tank_data)
        
        # Write JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(stowage_plan, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error exporting stowage plan: {e}")
        return False
