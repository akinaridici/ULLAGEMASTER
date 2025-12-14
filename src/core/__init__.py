"""
Core calculation modules for UllageMaster.
"""

from .interpolation import linear_interpolate, reverse_interpolate, bilinear_interpolate
from .astm_54b import calculate_vcf, get_alpha, api_to_density, density_to_api
from .density import vac_to_air, air_to_vac, convert_density_unit
from .calculations import (
    calculate_tov,
    calculate_ullage_from_volume,
    calculate_fill_percent,
    calculate_ullage_from_percent,
    apply_trim_correction,
    calculate_gov,
    calculate_gsv,
    calculate_mass,
    get_level_warning,
    calculate_tank_full,
    LevelWarning,
)

__all__ = [
    # Interpolation
    'linear_interpolate',
    'reverse_interpolate', 
    'bilinear_interpolate',
    # ASTM 54B
    'calculate_vcf',
    'get_alpha',
    'api_to_density',
    'density_to_api',
    # Density
    'vac_to_air',
    'air_to_vac',
    'convert_density_unit',
    # Calculations
    'calculate_tov',
    'calculate_ullage_from_volume',
    'calculate_fill_percent',
    'calculate_ullage_from_percent',
    'apply_trim_correction',
    'calculate_gov',
    'calculate_gsv',
    'calculate_mass',
    'get_level_warning',
    'calculate_tank_full',
    'LevelWarning',
]
