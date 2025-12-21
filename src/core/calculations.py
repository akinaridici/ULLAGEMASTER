"""
Core calculation engine for cargo operations.
Combines interpolation, VCF, and density calculations.
"""

from typing import Optional, Tuple
from enum import Enum
import pandas as pd

from .interpolation import linear_interpolate, reverse_interpolate, bilinear_interpolate
from .astm_54b import calculate_vcf
from .density import vac_to_air


class LevelWarning(Enum):
    """Tank fill level warning types."""
    NONE = "normal"
    LOW = "low"           # < 65% - Slosh effect
    HIGH = "high"         # > 95%
    HIGH_HIGH = "high_high"  # >= 98% - Critical


# Warning thresholds (percentage)
THRESHOLD_LOW = 65.0
THRESHOLD_HIGH = 95.0
THRESHOLD_HIGH_HIGH = 98.0


def calculate_tov(ullage: float, ullage_table: pd.DataFrame) -> float:
    """
    Calculate Total Observed Volume from ullage reading.
    
    Args:
        ullage: Ullage reading in cm
        ullage_table: DataFrame with 'ullage_cm' and 'volume_m3' columns
        
    Returns:
        Volume in m³
    """
    return linear_interpolate(ullage_table, 'ullage_cm', 'volume_m3', ullage)


def calculate_ullage_from_volume(volume: float, ullage_table: pd.DataFrame) -> float:
    """
    Reverse lookup: find ullage from target volume.
    
    Args:
        volume: Target volume in m³
        ullage_table: DataFrame with 'ullage_cm' and 'volume_m3' columns
        
    Returns:
        Ullage in cm
    """
    return reverse_interpolate(ullage_table, 'ullage_cm', 'volume_m3', volume)


def calculate_fill_percent(volume: float, capacity: float) -> float:
    """
    Calculate fill percentage.
    
    Args:
        volume: Current volume in m³
        capacity: Tank capacity in m³
        
    Returns:
        Fill percentage (0-100)
    """
    if capacity <= 0:
        return 0.0
    return (volume / capacity) * 100.0


def calculate_ullage_from_percent(percent: float, capacity: float, ullage_table: pd.DataFrame) -> float:
    """
    Calculate ullage from fill percentage.
    
    Args:
        percent: Fill percentage (0-100)
        capacity: Tank capacity in m³
        ullage_table: Ullage lookup table
        
    Returns:
        Ullage in cm
    """
    target_volume = (percent / 100.0) * capacity
    return calculate_ullage_from_volume(target_volume, ullage_table)


def apply_trim_correction(
    tov: float,
    ullage: float,
    trim: float,
    trim_table: pd.DataFrame
) -> Tuple[float, float]:
    """
    Apply trim correction to volume.
    
    Args:
        tov: Total Observed Volume in m³
        ullage: Ullage reading in cm
        trim: Ship trim in meters (positive = stern down)
        trim_table: Trim correction table with 'ullage_cm', 'trim_m', 'correction_m3'
        
    Returns:
        Tuple of (corrected_volume, trim_correction)
    """
    correction = bilinear_interpolate(
        trim_table,
        'ullage_cm', 'trim_m', 'correction_m3',
        ullage, trim
    )
    corrected_volume = tov + correction
    return corrected_volume, correction


def get_trim_correction(
    ullage_mm: float,
    trim: float,
    trim_table: pd.DataFrame
) -> float:
    """
    Get trim correction value to apply to ullage (in mm).
    
    IMPORTANT: Configuration tables store all correction values in millimeters (mm).
    The UI displays values in centimeters (cm), so callers must convert (mm / 10).
    
    Args:
        ullage_mm: Ullage reading in mm
        trim: Ship trim in meters (negative = stern deeper)
        trim_table: Trim correction table with 'ullage_mm' or 'ullage_cm', 
                   'trim_m', and correction column (values in mm)
        
    Returns:
        Trim correction in mm (to be added to ullage)
    """
    # Determine the ullage column name
    if 'ullage_mm' in trim_table.columns:
        ullage_col = 'ullage_mm'
        ullage_value = ullage_mm
    else:
        ullage_col = 'ullage_cm'
        ullage_value = ullage_mm / 10.0  # Convert mm to cm
    
    # Determine the correction column name
    if 'correction_mm' in trim_table.columns:
        corr_col = 'correction_mm'
    elif 'correction_m3' in trim_table.columns:
        corr_col = 'correction_m3'
    else:
        # Default - assume first non-ullage, non-trim column
        corr_col = [c for c in trim_table.columns if c not in [ullage_col, 'trim_m']][0]
    
    correction = bilinear_interpolate(
        trim_table,
        ullage_col, 'trim_m', corr_col,
        ullage_value, trim
    )
    
    return correction


def calculate_gov(tov: float, trim_correction: float) -> float:
    """
    Calculate Gross Observed Volume.
    
    Args:
        tov: Total Observed Volume
        trim_correction: Trim correction value
        
    Returns:
        GOV in m³
    """
    return tov + trim_correction


def calculate_gsv(gov: float, vcf: float, vef: float = 1.0) -> float:
    """
    Calculate Gross Standard Volume.
    
    Args:
        gov: Gross Observed Volume in m³
        vcf: Volume Correction Factor
        vef: Vessel Experience Factor (default 1.0)
        
    Returns:
        GSV in m³
    """
    return gov * vcf * vef


def calculate_mass(gsv: float, density: float, in_air: bool = True) -> float:
    """
    Calculate mass from GSV and density.
    
    Args:
        gsv: Gross Standard Volume in m³
        density: Density in kg/m³ or g/cm³ (auto-detected)
        in_air: If True, calculate MT in air; if False, MT in vacuum
        
    Returns:
        Mass in metric tons (MT)
        
    Note:
        g/cm³ = ton/m³ (metric tons per cubic meter)
        So 0.750 g/cm³ means 0.750 tons per m³
    """
    # Auto-detect density unit:
    # If density < 10: g/cm³ (= ton/m³), so MT = GSV(m³) × density(ton/m³)
    # If density >= 10: kg/m³, so MT = GSV × density / 1000
    if density < 10:  # g/cm³ = ton/m³
        mass_mt = gsv * density
    else:  # kg/m³
        mass_mt = gsv * density / 1000.0
    return mass_mt


def get_level_warning(fill_percent: float) -> LevelWarning:
    """
    Get the appropriate warning level for a fill percentage.
    
    Args:
        fill_percent: Tank fill percentage (0-100)
        
    Returns:
        LevelWarning enum value
    """
    if fill_percent >= THRESHOLD_HIGH_HIGH:
        return LevelWarning.HIGH_HIGH
    elif fill_percent > THRESHOLD_HIGH:
        return LevelWarning.HIGH
    elif fill_percent < THRESHOLD_LOW:
        return LevelWarning.LOW
    else:
        return LevelWarning.NONE


def calculate_tank_full(
    ullage: float,
    temp_celsius: float,
    density_vac: float,
    capacity: float,
    ullage_table: pd.DataFrame,
    trim_table: pd.DataFrame,
    trim: float = 0.0,
    vef: float = 1.0
) -> dict:
    """
    Perform full calculation for a single tank.
    
    Args:
        ullage: Ullage reading in cm
        temp_celsius: Cargo temperature in °C
        density_vac: Vacuum density in kg/m³
        capacity: Tank capacity in m³
        ullage_table: Ullage lookup table
        trim_table: Trim correction table
        trim: Ship trim in meters
        vef: Vessel Experience Factor
        
    Returns:
        Dictionary with all calculated values
    """
    # Step 1: Ullage → TOV
    tov = calculate_tov(ullage, ullage_table)
    
    # Step 2: Apply trim correction
    gov, trim_correction = apply_trim_correction(tov, ullage, trim, trim_table)
    
    # Step 3: Calculate VCF
    vcf = calculate_vcf(temp_celsius, density_vac)
    
    # Step 4: Calculate GSV
    gsv = calculate_gsv(gov, vcf, vef)
    
    # Step 5: Convert density
    density_air = vac_to_air(density_vac)
    
    # Step 6: Calculate mass
    mt_air = calculate_mass(gsv, density_air)
    mt_vac = calculate_mass(gsv, density_vac)
    
    # Step 7: Fill percentage and warnings
    fill_percent = calculate_fill_percent(tov, capacity)
    warning = get_level_warning(fill_percent)
    
    return {
        'ullage': ullage,
        'tov': tov,
        'trim_correction': trim_correction,
        'gov': gov,
        'vcf': vcf,
        'gsv': gsv,
        'density_vac': density_vac,
        'density_air': density_air,
        'mt_air': mt_air,
        'mt_vac': mt_vac,
        'fill_percent': fill_percent,
        'warning': warning,
        'temp': temp_celsius,
    }
