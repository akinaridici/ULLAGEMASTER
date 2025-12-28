"""
ASTM Table 54B - Volume Correction Factor (VCF) Calculator
Corrects observed volume to standard temperature (15°C).

Based on the formula:
    VCF = exp(-α × ΔT × (1 + 0.8 × α × ΔT))

Where:
    α = thermal expansion coefficient
    ΔT = observed temperature - 15°C
"""

import math
from typing import Tuple

# ASTM 54B Coefficients based on density at 15°C
# These coefficients (K0, K1) are empirical constants derived from ASTM standards
# for different density ranges of petroleum products.
# Format: (min_density, max_density): (K0, K1)
COEFFICIENTS = {
    (0, 770): (346.42278, 0.43884),   # Light products (gasolines)
    (778, 839): (594.5418, 0.0),      # Kerosene/Jet fuel range
    (839, 9999): (186.9696, 0.48618), # Heavy products (fuel oils)
}

# Transition zone (770-778 kg/m³) uses a special polynomial formula
# to smooth the transition between light and medium density products.
TRANSITION_A = -0.0033612
TRANSITION_B = 2680.32


def get_alpha(density_15: float) -> float:
    """
    Calculate the thermal expansion coefficient (α) based on density at 15°C.
    
    Args:
        density_15: Density at 15°C in kg/m³
        
    Returns:
        Thermal expansion coefficient
    """
    # Transition zone (770-778 kg/m³)
    # In this narrow range, a special formula is used to avoid discontinuities.
    if 770 < density_15 < 778:
        alpha = TRANSITION_A + TRANSITION_B / (density_15 ** 2)
        return alpha
    
    # Iterate through standard ranges to find appropriate coefficients
    for (min_d, max_d), (k0, k1) in COEFFICIENTS.items():
        if min_d <= density_15 <= max_d:
            # Alpha formula: (K0 + K1 * density) / density^2
            alpha = (k0 + k1 * density_15) / (density_15 ** 2)
            return alpha
    
    # Default to heavy products if out of range (fallback safety)
    k0, k1 = COEFFICIENTS[(839, 9999)]
    alpha = (k0 + k1 * density_15) / (density_15 ** 2)
    return alpha


def calculate_vcf(temp_celsius: float, density_15: float) -> float:
    """
    Calculate the Volume Correction Factor (VCF) using ASTM Table 54B.
    
    Args:
        temp_celsius: Observed temperature in Celsius
        density_15: Density at 15°C in kg/m³ (or g/cm³ - auto-converted)
        
    Returns:
        Volume Correction Factor (VCF)
        
    Example:
        >>> vcf = calculate_vcf(25.0, 800.0)  # 25°C, 800 kg/m³
        >>> print(f"VCF: {vcf:.5f}")
    """
    # Auto-convert density from g/cm³ to kg/m³ if needed
    # Petroleum products have density 600-1000 kg/m³
    # If value < 10, assume it's in g/cm³ and convert
    if density_15 < 10:
        density_15 = density_15 * 1000
    
    # Calculate temperature difference from 15°C
    delta_t = temp_celsius - 15.0
    
    # Determine alpha (thermal expansion coefficient) based on product density
    alpha = get_alpha(density_15)
    
    # Calculate the exponent for the VCF formula
    # The formula corrects for the non-linear expansion of petroleum products
    exponent = -alpha * delta_t * (1 + 0.8 * alpha * delta_t)
    
    # VCF is the exponential of the calculated factor
    vcf = math.exp(exponent)
    
    return vcf


def density_at_temperature(density_15: float, temp_celsius: float) -> float:
    """
    Calculate density at a given temperature from density at 15°C.
    
    Args:
        density_15: Density at 15°C in kg/m³
        temp_celsius: Target temperature in Celsius
        
    Returns:
        Density at the given temperature
    """
    vcf = calculate_vcf(temp_celsius, density_15)
    # Density changes inversely with VCF
    return density_15 / vcf


# Utility: Convert API gravity to density
def api_to_density(api: float) -> float:
    """
    Convert API gravity to density at 15°C in kg/m³.
    
    Formula: Density = 141.5 / (API + 131.5) * 999.012
    
    Args:
        api: API gravity value
        
    Returns:
        Density in kg/m³ at 15°C
    """
    # Standard formula from ASTM D1250
    specific_gravity = 141.5 / (api + 131.5)
    density = specific_gravity * 999.012  # Convert SG to kg/m³
    return density


def density_to_api(density_15: float) -> float:
    """
    Convert density at 15°C to API gravity.
    
    Args:
        density_15: Density at 15°C in kg/m³
        
    Returns:
        API gravity value
    """
    specific_gravity = density_15 / 999.012
    api = (141.5 / specific_gravity) - 131.5
    return api
