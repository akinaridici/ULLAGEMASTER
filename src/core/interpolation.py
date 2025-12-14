"""
Interpolation utilities for ullage and trim table lookups.
Provides linear and bi-linear interpolation functions.
"""

import numpy as np
from typing import Tuple, Optional
import pandas as pd


def linear_interpolate(table: pd.DataFrame, x_col: str, y_col: str, x_value: float) -> float:
    """
    Perform linear interpolation on a table.
    
    Args:
        table: DataFrame with at least two columns
        x_col: Column name for x values (e.g., 'ullage_cm')
        y_col: Column name for y values (e.g., 'volume_m3')
        x_value: The x value to interpolate
        
    Returns:
        Interpolated y value
        
    Raises:
        ValueError: If x_value is outside table range
    """
    x_arr = table[x_col].values
    y_arr = table[y_col].values
    
    # Check bounds
    if x_value < x_arr.min() or x_value > x_arr.max():
        raise ValueError(f"Value {x_value} is outside table range [{x_arr.min()}, {x_arr.max()}]")
    
    # Find exact match
    if x_value in x_arr:
        idx = np.where(x_arr == x_value)[0][0]
        return float(y_arr[idx])
    
    # Find surrounding values
    lower_idx = np.where(x_arr <= x_value)[0][-1]
    upper_idx = np.where(x_arr >= x_value)[0][0]
    
    x0, x1 = x_arr[lower_idx], x_arr[upper_idx]
    y0, y1 = y_arr[lower_idx], y_arr[upper_idx]
    
    # Linear interpolation formula: y = y0 + (x - x0) * (y1 - y0) / (x1 - x0)
    if x1 == x0:
        return float(y0)
    
    y_value = y0 + (x_value - x0) * (y1 - y0) / (x1 - x0)
    return float(y_value)


def reverse_interpolate(table: pd.DataFrame, x_col: str, y_col: str, y_value: float) -> float:
    """
    Reverse interpolation: given a y value, find the corresponding x value.
    Used for converting fill percentage to ullage.
    
    Args:
        table: DataFrame with at least two columns
        x_col: Column name for x values (e.g., 'ullage_cm')
        y_col: Column name for y values (e.g., 'volume_m3')
        y_value: The y value to find x for
        
    Returns:
        Interpolated x value
        
    Raises:
        ValueError: If y_value is outside table range
    """
    # Simply swap x and y for reverse lookup
    return linear_interpolate(table, y_col, x_col, y_value)


def bilinear_interpolate(
    table: pd.DataFrame,
    x_col: str,
    y_col: str,
    z_col: str,
    x_value: float,
    y_value: float
) -> float:
    """
    Perform bi-linear interpolation for trim corrections.
    Given x (ullage) and y (trim), find z (correction factor).
    
    Args:
        table: DataFrame with columns for x, y, and z values
        x_col: Column name for first variable (e.g., 'ullage_cm')
        y_col: Column name for second variable (e.g., 'trim_m')
        z_col: Column name for result (e.g., 'correction_m3')
        x_value: First interpolation value
        y_value: Second interpolation value
        
    Returns:
        Interpolated z value
    """
    x_arr = table[x_col].unique()
    y_arr = table[y_col].unique()
    
    x_arr = np.sort(x_arr)
    y_arr = np.sort(y_arr)
    
    # Clamp to bounds
    x_value = np.clip(x_value, x_arr.min(), x_arr.max())
    y_value = np.clip(y_value, y_arr.min(), y_arr.max())
    
    # Find surrounding x values
    x_lower_vals = x_arr[x_arr <= x_value]
    x_upper_vals = x_arr[x_arr >= x_value]
    x0 = x_lower_vals[-1] if len(x_lower_vals) > 0 else x_arr[0]
    x1 = x_upper_vals[0] if len(x_upper_vals) > 0 else x_arr[-1]
    
    # Find surrounding y values
    y_lower_vals = y_arr[y_arr <= y_value]
    y_upper_vals = y_arr[y_arr >= y_value]
    y0 = y_lower_vals[-1] if len(y_lower_vals) > 0 else y_arr[0]
    y1 = y_upper_vals[0] if len(y_upper_vals) > 0 else y_arr[-1]
    
    # Get the four corner values
    def get_z(x, y):
        mask = (table[x_col] == x) & (table[y_col] == y)
        if mask.any():
            return table.loc[mask, z_col].values[0]
        return 0.0
    
    z00 = get_z(x0, y0)
    z01 = get_z(x0, y1)
    z10 = get_z(x1, y0)
    z11 = get_z(x1, y1)
    
    # Bilinear interpolation
    if x1 == x0:
        t = 0.0
    else:
        t = (x_value - x0) / (x1 - x0)
    
    if y1 == y0:
        u = 0.0
    else:
        u = (y_value - y0) / (y1 - y0)
    
    z = (1 - t) * (1 - u) * z00 + t * (1 - u) * z10 + (1 - t) * u * z01 + t * u * z11
    
    return float(z)
