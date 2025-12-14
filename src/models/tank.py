"""
Tank model with ullage and trim tables.
Handles loading CSV tables and performing lookups.
"""

import pandas as pd
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Tank:
    """
    Represents a cargo tank with its tables and current readings.
    """
    id: str
    name: str
    capacity_m3: float
    ullage_table: Optional[pd.DataFrame] = field(default=None, repr=False)
    trim_table: Optional[pd.DataFrame] = field(default=None, repr=False)
    
    def load_ullage_table(self, csv_path: str) -> bool:
        """
        Load ullage table from CSV file.
        
        Expected format:
            ullage_cm,volume_m3
            0,1500.000
            1,1498.750
            ...
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            df = pd.read_csv(csv_path)
            # Validate required columns
            if 'ullage_cm' not in df.columns or 'volume_m3' not in df.columns:
                # Try to handle alternate column names
                if len(df.columns) >= 2:
                    df.columns = ['ullage_cm', 'volume_m3']
            
            # Sort by ullage
            df = df.sort_values('ullage_cm').reset_index(drop=True)
            self.ullage_table = df
            return True
        except Exception as e:
            print(f"Error loading ullage table: {e}")
            return False
    
    def load_trim_table(self, csv_path: str) -> bool:
        """
        Load trim correction table from CSV file.
        
        Expected format:
            ullage_cm,trim_m,correction_m3
            100,-2.0,-5.5
            100,-1.5,-4.2
            ...
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            df = pd.read_csv(csv_path)
            # Validate required columns
            required = ['ullage_cm', 'trim_m', 'correction_m3']
            if not all(col in df.columns for col in required):
                # Try to handle alternate column names
                if len(df.columns) >= 3:
                    df.columns = required
            
            self.trim_table = df
            return True
        except Exception as e:
            print(f"Error loading trim table: {e}")
            return False
    
    def has_ullage_table(self) -> bool:
        """Check if ullage table is loaded."""
        return self.ullage_table is not None and len(self.ullage_table) > 0
    
    def has_trim_table(self) -> bool:
        """Check if trim table is loaded."""
        return self.trim_table is not None and len(self.trim_table) > 0
    
    def get_max_ullage(self) -> float:
        """Get maximum ullage value from table."""
        if not self.has_ullage_table():
            return 0.0
        return float(self.ullage_table['ullage_cm'].max())
    
    def get_min_ullage(self) -> float:
        """Get minimum ullage value from table (usually 0)."""
        if not self.has_ullage_table():
            return 0.0
        return float(self.ullage_table['ullage_cm'].min())
    
    def get_max_volume(self) -> float:
        """Get maximum volume from table (at minimum ullage)."""
        if not self.has_ullage_table():
            return self.capacity_m3
        return float(self.ullage_table['volume_m3'].max())


@dataclass  
class TankReading:
    """
    Current reading for a tank during a voyage.
    """
    tank_id: str
    parcel: str = ""
    grade: str = ""
    receiver: str = ""
    receiver_tank: str = ""
    
    # Input values
    ullage: Optional[float] = None
    fill_percent: Optional[float] = None
    temp_celsius: Optional[float] = None
    density_vac: Optional[float] = None
    bl_figure: Optional[float] = None  # Bill of Lading
    
    # Calculated values (set by calculation engine)
    tov: float = 0.0
    trim_correction: float = 0.0
    gov: float = 0.0
    vcf: float = 1.0
    gsv: float = 0.0
    density_air: float = 0.0
    mt_air: float = 0.0
    mt_vac: float = 0.0
    discrepancy: float = 0.0
    warning: str = "normal"
    
    def to_dict(self) -> dict:
        """Convert reading to dictionary."""
        return {
            'tank_id': self.tank_id,
            'parcel': self.parcel,
            'grade': self.grade,
            'receiver': self.receiver,
            'receiver_tank': self.receiver_tank,
            'ullage': self.ullage,
            'fill_percent': self.fill_percent,
            'temp_celsius': self.temp_celsius,
            'density_vac': self.density_vac,
            'bl_figure': self.bl_figure,
            'tov': self.tov,
            'trim_correction': self.trim_correction,
            'gov': self.gov,
            'vcf': self.vcf,
            'gsv': self.gsv,
            'density_air': self.density_air,
            'mt_air': self.mt_air,
            'mt_vac': self.mt_vac,
            'discrepancy': self.discrepancy,
            'warning': self.warning,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TankReading':
        """Create reading from dictionary."""
        return cls(**data)
