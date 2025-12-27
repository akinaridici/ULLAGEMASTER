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
    thermal_table: Optional[pd.DataFrame] = field(default=None, repr=False)
    
    def set_ullage_table(self, data: list):
        """Set ullage table from list of dictionaries."""
        if not data:
            self.ullage_table = None
            return
            
        try:
            df = pd.DataFrame(data)
            # Ensure ullage_cm exists
            if 'ullage_cm' not in df.columns and 'ullage_mm' in df.columns:
                df['ullage_cm'] = df['ullage_mm'] / 10.0
            
            if 'ullage_cm' in df.columns:
                df = df.sort_values('ullage_cm').reset_index(drop=True)
                self.ullage_table = df
        except Exception as e:
            print(f"Error setting ullage table for {self.id}: {e}")

    def set_trim_table(self, data: list):
        """Set trim table from list of dictionaries."""
        if not data:
            self.trim_table = None
            return
            
        try:
            df = pd.DataFrame(data)
            self.trim_table = df
        except Exception as e:
            print(f"Error setting trim table for {self.id}: {e}")

    def set_thermal_table(self, data: list):
        """Set thermal table from list of dictionaries."""
        if not data:
            self.thermal_table = None
            return
            
        try:
            df = pd.DataFrame(data)
            if 'temp_c' in df.columns:
                df = df.sort_values('temp_c').reset_index(drop=True)
                self.thermal_table = df
        except Exception as e:
            print(f"Error setting thermal table for {self.id}: {e}")

    def get_thermal_factor(self, temp_c: float) -> float:
        """Get thermal correction factor for a given temperature."""
        if self.thermal_table is None or self.thermal_table.empty:
            return 1.0
            
        try:
            df = self.thermal_table
            
            # Interpolate
            # If exact match
            match = df[df['temp_c'] == temp_c]
            if not match.empty:
                return float(match.iloc[0]['corr_factor'])
            
            # Linear interpolation
            # Sort just in case
            df = df.sort_values('temp_c')
            
            # Find neighbors
            lower = df[df['temp_c'] < temp_c]
            upper = df[df['temp_c'] > temp_c]
            
            if lower.empty:
                return float(df.iloc[0]['corr_factor'])
            if upper.empty:
                return float(df.iloc[-1]['corr_factor'])
                
            x1 = float(lower.iloc[-1]['temp_c'])
            y1 = float(lower.iloc[-1]['corr_factor'])
            x2 = float(upper.iloc[0]['temp_c'])
            y2 = float(upper.iloc[0]['corr_factor'])
            
            # y = y1 + (x - x1) * (y2 - y1) / (x2 - x1)
            factor = y1 + (temp_c - x1) * (y2 - y1) / (x2 - x1)
            return factor
            
        except Exception as e:
            print(f"Error getting thermal factor: {e}")
            return 1.0

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
    parcel_id: str = ""  # Reference to Parcel - grade/receiver/density come from parcel
    
    # Input values (only ullage and temp are user-editable)
    ullage: Optional[float] = None
    temp_celsius: Optional[float] = None
    
    # From parcel (populated automatically when parcel is selected)
    density_vac: Optional[float] = None
    
    # Legacy/optional fields
    fill_percent: Optional[float] = None
    
    # Calculated values (set by calculation engine)
    tov: float = 0.0
    trim_correction: float = 0.0
    corrected_ullage: Optional[float] = None  # Ullage after trim correction
    therm_corr: float = 1.0  # Thermal correction factor (from table or 1.0)
    gov: float = 0.0  # GOV = TOV * therm_corr
    vcf: float = 1.0
    gsv: float = 0.0
    density_air: float = 0.0
    mt_air: float = 0.0
    mt_vac: float = 0.0
    discrepancy: float = 0.0
    warning: str = "normal"
    
    def to_dict(self) -> dict:
        """Convert reading to dictionary."""
        print(f"DEBUG SAVE TankReading: tank_id={self.tank_id}, ullage={self.ullage}, fill_percent={self.fill_percent}", flush=True)
        return {
            'tank_id': self.tank_id,
            'parcel_id': self.parcel_id,
            'ullage': self.ullage,
            'temp_celsius': self.temp_celsius,
            'density_vac': self.density_vac,
            'fill_percent': self.fill_percent,
            'tov': self.tov,
            'trim_correction': self.trim_correction,
            'corrected_ullage': self.corrected_ullage,
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
        reading = cls(**data)
        print(f"DEBUG LOAD TankReading: tank_id={reading.tank_id}, ullage={reading.ullage}, fill_percent={reading.fill_percent}", flush=True)
        return reading
