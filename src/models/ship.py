"""
Ship configuration model.
Stores ship information and tank definitions.
"""

import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class TankConfig:
    """Configuration for a single tank."""
    id: str                     # e.g., "1P", "1S", "SlopP"
    name: str                   # e.g., "No.1 Port"
    capacity_m3: float          # Tank capacity in m³
    ullage_table_path: str = "" # Path to ullage CSV
    trim_table_path: str = ""   # Path to trim correction CSV


@dataclass
class ShipConfig:
    """Ship configuration including all tanks."""
    ship_name: str
    tank_pairs: int  # Number of tank pairs (6, 8, or 10)
    default_vef: float = 1.0000
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
    
    def save_to_json(self, filepath: str) -> None:
        """Save configuration to JSON file."""
        data = {
            'ship_name': self.ship_name,
            'tank_pairs': self.tank_pairs,
            'default_vef': self.default_vef,
            'tanks': [asdict(tank) for tank in self.tanks]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_json(cls, filepath: str) -> 'ShipConfig':
        """Load configuration from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = cls(
            ship_name=data['ship_name'],
            tank_pairs=data['tank_pairs'],
            default_vef=data.get('default_vef', 1.0)
        )
        
        for tank_data in data.get('tanks', []):
            tank = TankConfig(**tank_data)
            config.add_tank(tank)
        
        return config
    
    @classmethod
    def create_default(cls, ship_name: str, tank_pairs: int = 6) -> 'ShipConfig':
        """Create a default ship configuration with standard tank naming."""
        config = cls(ship_name=ship_name, tank_pairs=tank_pairs)
        
        # Create numbered tanks (Port and Starboard)
        for i in range(1, tank_pairs + 1):
            # Port tank
            config.add_tank(TankConfig(
                id=f"{i}P",
                name=f"No.{i} Port",
                capacity_m3=0.0
            ))
            # Starboard tank
            config.add_tank(TankConfig(
                id=f"{i}S",
                name=f"No.{i} Starboard",
                capacity_m3=0.0
            ))
        
        # Add slop tanks
        config.add_tank(TankConfig(
            id="SlopP",
            name="Slop Port",
            capacity_m3=0.0
        ))
        config.add_tank(TankConfig(
            id="SlopS",
            name="Slop Starboard",
            capacity_m3=0.0
        ))
        
        return config
