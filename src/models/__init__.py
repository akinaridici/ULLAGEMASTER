"""
Data models for UllageMaster.
"""

from .ship import ShipConfig, TankConfig
from .tank import Tank, TankReading
from .voyage import Voyage, DraftReadings

__all__ = [
    'ShipConfig',
    'TankConfig',
    'Tank',
    'TankReading',
    'Voyage',
    'DraftReadings',
]
