"""
Ship configuration model.
Stores ship information and tank definitions.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class TankConfig:
    """Configuration for a single tank."""
    id: str                     # e.g., "1P", "1S", "SlopP"
    name: str                   # e.g., "No.1 Port"
    capacity_m3: float = 0.0    # Tank capacity in m³
    # Table data stored directly in config (JSON format)
    ullage_table: List[Dict[str, float]] = field(default_factory=list)  # [{ullage_mm, volume_m3}, ...]
    trim_table: List[Dict[str, float]] = field(default_factory=list)    # [{ullage_mm, trim_m, correction_m3}, ...]
    thermal_table: List[Dict[str, float]] = field(default_factory=list) # [{temp_c, corr_factor}, ...]


@dataclass
class ShipConfig:
    """Ship configuration including all tanks."""
    ship_name: str
    tank_count: int  # Total number of tanks (not pairs)
    has_thermal_correction: bool = False
    default_vef: float = 1.0000
    slop_density: float = 0.85  # Default density for SLOP parcels
    # Officer names (persisted across voyages)
    chief_officer: str = ""
    master: str = ""
    # User-defined list of trim values (supports non-uniform steps)
    trim_values: List[float] = field(default_factory=lambda: [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0])
    tanks: List[TankConfig] = field(default_factory=list)
    
    def add_tank(self, tank: TankConfig) -> None:
        """Add a tank to the configuration."""
        self.tanks.append(tank)
    
    def get_tank(self, tank_id: str) -> Optional[TankConfig]:
        """Get a tank by its ID."""
        for tank in self.tanks:
            if tank.id == tank_id:
                return tank
        return None
    
    def get_tank_ids(self) -> List[str]:
        """Get list of all tank IDs."""
        return [tank.id for tank in self.tanks]
    
    def has_complete_config(self) -> bool:
        """
        Check if the configuration is complete and ready for use.
        
        Verifies that:
        1. At least one tank is defined.
        2. All tanks have ullage tables loaded.
        3. All tanks have trim correction tables loaded.
        4. If thermal correction is enabled, all tanks have thermal tables.
        
        Returns:
            True if all requirements are met, False otherwise.
        """
        if not self.tanks:
            return False
        for tank in self.tanks:
            if not tank.ullage_table:
                return False
            # Trim table is also required
            if not tank.trim_table:
                return False
            # Thermal table required only if enabled
            if self.has_thermal_correction and not tank.thermal_table:
                return False
        return True
    
    def get_trim_values(self) -> List[float]:
        """Get list of trim values (for backward compatibility)."""
        return self.trim_values
    
    def save_to_json(self, filepath: str) -> None:
        """Save configuration to JSON file."""
        data = {
            'ship_name': self.ship_name,
            'tank_count': self.tank_count,
            'has_thermal_correction': self.has_thermal_correction,
            'default_vef': self.default_vef,
            'slop_density': self.slop_density,
            'chief_officer': self.chief_officer,
            'master': self.master,
            'trim_values': self.trim_values,
            'tanks': [asdict(tank) for tank in self.tanks]
        }
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_json(cls, filepath: str) -> 'ShipConfig':
        """Load configuration from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle backward compatibility: generate trim_values from min/max/step if not present
        # Old config files only had trim_min, trim_max, and trim_step
        if 'trim_values' in data:
            trim_values = data['trim_values']
        else:
            # Legacy migration: generate list of trim values from range parameters
            trim_min = data.get('trim_min', -2.0)
            trim_max = data.get('trim_max', 2.0)
            trim_step = data.get('trim_step', 0.5)
            trim_values = []
            current = trim_min
            # Use small epsilon for float comparison safety
            while current <= trim_max + 0.0001:
                trim_values.append(round(current, 2))
                current += trim_step
        
        config = cls(
            ship_name=data['ship_name'],
            tank_count=data.get('tank_count', data.get('tank_pairs', 6) * 2),  # Backward compat: pairs -> count
            has_thermal_correction=data.get('has_thermal_correction', False),
            default_vef=data.get('default_vef', 1.0),
            slop_density=data.get('slop_density', 0.85),
            chief_officer=data.get('chief_officer', ''),
            master=data.get('master', ''),
            trim_values=trim_values
        )
        
        for tank_data in data.get('tanks', []):
            tank = TankConfig(
                id=tank_data['id'],
                name=tank_data.get('name', f"Tank {tank_data['id']}"),
                capacity_m3=tank_data.get('capacity_m3', 0.0),
                ullage_table=tank_data.get('ullage_table', []),
                trim_table=tank_data.get('trim_table', []),
                thermal_table=tank_data.get('thermal_table', [])
            )
            config.add_tank(tank)
        
        return config
    
    @classmethod
    def create_empty(cls, ship_name: str = "New Ship") -> 'ShipConfig':
        """Create an empty ship configuration."""
        return cls(ship_name=ship_name, tank_count=0)
