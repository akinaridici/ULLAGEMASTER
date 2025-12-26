"""
Voyage model for storing voyage data and calculations.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict

from .tank import TankReading
from .parcel import Parcel


@dataclass
class DraftReadings:
    """Ship draft readings."""
    aft: float = 0.0
    fwd: float = 0.0
    
    @property
    def trim(self) -> float:
        """Calculate trim (positive = stern down)."""
        return self.aft - self.fwd


@dataclass
class Voyage:
    """
    Represents a cargo operation voyage.
    """
    voyage_number: str
    date: str  # ISO format: YYYY-MM-DD
    port: str
    terminal: str
    
    # Vessel data
    vef: float = 1.0000
    drafts: DraftReadings = field(default_factory=DraftReadings)
    
    # Officer information
    chief_officer: str = ""
    master: str = ""
    
    # Parcels defined for this voyage
    parcels: List[Parcel] = field(default_factory=list)
    
    # Tank readings
    tank_readings: Dict[str, TankReading] = field(default_factory=dict)
    
    # Totals (calculated)
    total_gsv: float = 0.0
    total_mt: float = 0.0
    
    def add_reading(self, reading: TankReading) -> None:
        """Add or update a tank reading."""
        self.tank_readings[reading.tank_id] = reading
    
    def get_reading(self, tank_id: str) -> Optional[TankReading]:
        """Get reading for a specific tank."""
        return self.tank_readings.get(tank_id)
    
    def calculate_totals(self) -> None:
        """Calculate total GSV and MT from all tank readings."""
        self.total_gsv = sum(r.gsv for r in self.tank_readings.values())
        self.total_mt = sum(r.mt_air for r in self.tank_readings.values())
    
    def get_discrepancy_loading(self, shore_figure: float) -> float:
        """Calculate loading discrepancy percentage."""
        if shore_figure == 0:
            return 0.0
        return ((self.total_mt - shore_figure) / shore_figure) * 100
    
    def to_dict(self) -> dict:
        """Convert voyage to dictionary for serialization."""
        return {
            'voyage_number': self.voyage_number,
            'date': self.date,
            'port': self.port,
            'terminal': self.terminal,
            'vef': self.vef,
            'drafts': {
                'aft': self.drafts.aft,
                'fwd': self.drafts.fwd,
                'trim': self.drafts.trim
            },
            'chief_officer': self.chief_officer,
            'master': self.master,
            'parcels': [p.to_dict() for p in self.parcels],
            'tank_readings': {
                tank_id: reading.to_dict() 
                for tank_id, reading in self.tank_readings.items()
            },
            'totals': {
                'gsv': self.total_gsv,
                'mt': self.total_mt
            }
        }
    
    def save_to_json(self, filepath: str) -> None:
        """Save voyage to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Voyage':
        """Create voyage from dictionary."""
        voyage = cls(
            voyage_number=data['voyage_number'],
            date=data['date'],
            port=data['port'],
            terminal=data['terminal'],
            vef=data.get('vef', 1.0),
            chief_officer=data.get('chief_officer', ''),
            master=data.get('master', '')
        )
        
        # Load drafts
        if 'drafts' in data:
            voyage.drafts = DraftReadings(
                aft=data['drafts'].get('aft', 0.0),
                fwd=data['drafts'].get('fwd', 0.0)
            )
        
        # Load parcels
        for parcel_data in data.get('parcels', []):
            voyage.parcels.append(Parcel.from_dict(parcel_data))
        
        # Load tank readings
        for tank_id, reading_data in data.get('tank_readings', {}).items():
            voyage.add_reading(TankReading.from_dict(reading_data))
        
        # Load totals
        if 'totals' in data:
            voyage.total_gsv = data['totals'].get('gsv', 0.0)
            voyage.total_mt = data['totals'].get('mt', 0.0)
        
        return voyage
    
    @classmethod
    def load_from_json(cls, filepath: str) -> 'Voyage':
        """Load voyage from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def create_new(cls, voyage_number: str, port: str, terminal: str) -> 'Voyage':
        """Create a new voyage with current date."""
        return cls(
            voyage_number=voyage_number,
            date=datetime.now().strftime('%d-%m-%Y'),
            port=port,
            terminal=terminal
        )
