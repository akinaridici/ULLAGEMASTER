"""
Density conversion utilities.
Handles conversion between vacuum density and air density.
"""


# Buoyancy correction factor (kg/m³)
# Standards assume density in vacuum for physics but commercial trade uses "weight in air"
BUOYANCY_CORRECTION_KGM3 = 1.1
 
# Same correction in g/cm³ (1.1 / 1000)
BUOYANCY_CORRECTION_GCM3 = 0.0011


def vac_to_air(density_vacuum: float, unit: str = "kg/m3") -> float:
    """
    Convert vacuum density to air density.
    
    Terminals typically provide vacuum density (true mass).
    Commercial transactions require air density (apparent weight in air).
    
    Args:
        density_vacuum: Density in vacuum
        unit: "kg/m3" or "g/cm3"
        
    Returns:
        Density in air
        
    Formula:
        Density_Air = Density_Vacuum - 1.1 (kg/m³)
        Density_Air = Density_Vacuum - 0.0011 (g/cm³)
    """
    if unit.lower() in ("kg/m3", "kg/m³"):
        return density_vacuum - BUOYANCY_CORRECTION_KGM3
    elif unit.lower() in ("g/cm3", "g/cm³"):
        return density_vacuum - BUOYANCY_CORRECTION_GCM3
    else:
        raise ValueError(f"Unknown unit: {unit}. Use 'kg/m3' or 'g/cm3'")


def air_to_vac(density_air: float, unit: str = "kg/m3") -> float:
    """
    Convert air density to vacuum density.
    
    Args:
        density_air: Density in air
        unit: "kg/m3" or "g/cm3"
        
    Returns:
        Density in vacuum
    """
    if unit.lower() in ("kg/m3", "kg/m³"):
        return density_air + BUOYANCY_CORRECTION_KGM3
    elif unit.lower() in ("g/cm3", "g/cm³"):
        return density_air + BUOYANCY_CORRECTION_GCM3
    else:
        raise ValueError(f"Unknown unit: {unit}. Use 'kg/m3' or 'g/cm3'")


def convert_density_unit(value: float, from_unit: str, to_unit: str) -> float:
    """
    Convert density between different units.
    
    Supported units:
        - kg/m3 (kg/m³)
        - g/cm3 (g/cm³)
        - API (API gravity)
        
    Args:
        value: Density value to convert
        from_unit: Source unit
        to_unit: Target unit
        
    Returns:
        Converted density value
    """
    from .astm_54b import api_to_density, density_to_api
    
    # Normalize to kg/m³ first
    if from_unit.lower() in ("kg/m3", "kg/m³"):
        density_kgm3 = value
    elif from_unit.lower() in ("g/cm3", "g/cm³"):
        density_kgm3 = value * 1000.0
    elif from_unit.lower() == "api":
        density_kgm3 = api_to_density(value)
    else:
        raise ValueError(f"Unknown source unit: {from_unit}")
    
    # Convert to target unit
    if to_unit.lower() in ("kg/m3", "kg/m³"):
        return density_kgm3
    elif to_unit.lower() in ("g/cm3", "g/cm³"):
        return density_kgm3 / 1000.0
    elif to_unit.lower() == "api":
        return density_to_api(density_kgm3)
    else:
        raise ValueError(f"Unknown target unit: {to_unit}")
