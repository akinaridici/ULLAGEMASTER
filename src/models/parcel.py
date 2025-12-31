"""
Parcel Data Model - Represents a cargo parcel in a voyage.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Parcel:
    """
    Represents a cargo parcel with its properties.
    
    Attributes:
        id: Unique parcel identifier (e.g., "1", "2", "3")
        name: Cargo grade name (e.g., "Fuel Oil", "Diesel")
        receiver: Receiver company name
        density_vac: Vacuum density in kg/m³
        color: Hex color for UI display (e.g., "#FF5733")
        bl_loading: B/L figure for loading operations (MT AIR)
        bl_discharging: B/L figure for discharging operations (MT AIR)
    """
    id: str
    name: str = ""
    receiver: str = ""
    density_vac: float = 0.0
    color: str = "#3B82F6"  # Default blue
    bl_loading: float = 0.0  # B/L figure for loading
    bl_discharging: float = 0.0  # B/L figure for discharging
    
    def to_dict(self) -> dict:
        """Convert parcel to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'receiver': self.receiver,
            'density_vac': self.density_vac,
            'color': self.color,
            'bl_loading': self.bl_loading,
            'bl_discharging': self.bl_discharging,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Parcel':
        """Create Parcel from dictionary."""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            receiver=data.get('receiver', ''),
            density_vac=data.get('density_vac', 0.0),
            color=data.get('color', '#3B82F6'),
            bl_loading=data.get('bl_loading', 0.0),
            bl_discharging=data.get('bl_discharging', 0.0),
        )
    
    @classmethod
    def from_stowage_cargo(cls, cargo, parcel_id: str) -> 'Parcel':
        """
        Create Parcel from StowageCargo (converts Stowage Plan data to Ullage Parcel).
        
        Used when transferring data from "Stowage Plan" tab to "Ullage Calculation" tab.
        
        Args:
            cargo: StowageCargo instance containing grade, receiver, and density info.
            parcel_id: ID to assign to the new parcel (e.g., "1", "2").
            
        Returns:
            New Parcel instance populated with stowage cargo data.
        """
        return cls(
            id=parcel_id,
            name=cargo.grade,
            receiver=cargo.receiver,
            density_vac=cargo.density_vac,
            color=cargo.color,
        )
