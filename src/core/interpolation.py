"""
Interpolation utilities for ullage and trim table lookups.
Provides linear and bi-linear interpolation functions.

Performance notes:
- linear_interpolate uses np.searchsorted for O(log n) lookups.
  Tables are assumed pre-sorted ascending at load time.
- bilinear_interpolate pre-builds a {(x, y): z} dict for O(1) corner lookups
  instead of 4 full DataFrame scans per call.
"""

import numpy as np
from typing import Tuple, Optional
import pandas as pd


def linear_interpolate(table: pd.DataFrame, x_col: str, y_col: str, x_value: float) -> float:
    """
    Perform linear interpolation on a table.
    
    Args:
        table: DataFrame with at least two columns (must be sorted ascending by x_col)
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
    
    # Ensure ascending order for searchsorted.
    # Tables should be pre-sorted at load time, but reverse_interpolate
    # swaps columns which may produce descending x values.
    if len(x_arr) > 1 and x_arr[0] > x_arr[-1]:
        x_arr = x_arr[::-1]
        y_arr = y_arr[::-1]
    
    x_min, x_max = x_arr[0], x_arr[-1]
    
    # Check bounds — extrapolation is NOT supported for safety
    if x_value < x_min or x_value > x_max:
        raise ValueError(f"Value {x_value} is outside table range [{x_min}, {x_max}]")
    
    # Use searchsorted to find insertion point in O(log n)
    idx = np.searchsorted(x_arr, x_value, side='right')
    
    # Exact match at the last element
    if idx >= len(x_arr):
        return float(y_arr[-1])
    
    # Exact match check
    if idx > 0 and x_arr[idx - 1] == x_value:
        return float(y_arr[idx - 1])
    if x_arr[idx] == x_value:
        return float(y_arr[idx])
    
    # Interpolate between x_arr[idx-1] and x_arr[idx]
    lower_idx = idx - 1
    upper_idx = idx
    
    x0, x1 = x_arr[lower_idx], x_arr[upper_idx]
    y0, y1 = y_arr[lower_idx], y_arr[upper_idx]
    
    # Avoid division by zero
    if x1 == x0:
        return float(y0)
    
    # Linear interpolation formula: y = y0 + (x - x0) * (y1 - y0) / (x1 - x0)
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
        Interpolated z value.
    
    Note:
        Performs clamping for outlier values:
        - If x_value is outside the table range, it uses the nearest boundary x.
        - If y_value is outside the table range, it uses the nearest boundary y.
        This ensures the function always returns a safe approximation rather than raising an error.
    """
    # Build sorted unique arrays and a lookup dict for O(1) corner access.
    # This replaces 4 full DataFrame boolean mask scans per call.
    x_arr = np.sort(table[x_col].unique())
    y_arr = np.sort(table[y_col].unique())
    
    # Pre-build {(x, y): z} lookup dict
    z_lookup = {}
    for row in table.itertuples(index=False):
        z_lookup[(getattr(row, x_col), getattr(row, y_col))] = getattr(row, z_col)
    
    # Clamp to bounds
    x_value = np.clip(x_value, x_arr[0], x_arr[-1])
    y_value = np.clip(y_value, y_arr[0], y_arr[-1])
    
    # Find surrounding x values using searchsorted O(log n)
    x_idx = np.searchsorted(x_arr, x_value, side='right')
    x_idx = min(x_idx, len(x_arr) - 1)
    x1 = x_arr[x_idx]
    x0 = x_arr[max(x_idx - 1, 0)]
    # If exact match, x0 == x1 is fine (t will be 0)
    
    # Find surrounding y values using searchsorted O(log n)
    y_idx = np.searchsorted(y_arr, y_value, side='right')
    y_idx = min(y_idx, len(y_arr) - 1)
    y1 = y_arr[y_idx]
    y0 = y_arr[max(y_idx - 1, 0)]
    
    # Get the four corner values via O(1) dict lookup
    z00 = z_lookup.get((x0, y0), 0.0)
    z01 = z_lookup.get((x0, y1), 0.0)
    z10 = z_lookup.get((x1, y0), 0.0)
    z11 = z_lookup.get((x1, y1), 0.0)
    
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

