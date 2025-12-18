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
    """
    id: str
    name: str = ""
    receiver: str = ""
    density_vac: float = 0.0
    color: str = "#3B82F6"  # Default blue
    
    def to_dict(self) -> dict:
        """Convert parcel to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'receiver': self.receiver,
            'density_vac': self.density_vac,
            'color': self.color,
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
        )
