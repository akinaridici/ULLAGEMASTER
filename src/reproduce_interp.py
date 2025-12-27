
import pandas as pd
import numpy as np

def linear_interpolate(table: pd.DataFrame, x_col: str, y_col: str, x_value: float) -> float:
    # COPIED FROM src/core/interpolation.py for isolation
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
    # BUG HYPOTHESIS: This assumption fails if x_arr is descending
    lower_bool = x_arr <= x_value
    upper_bool = x_arr >= x_value
    
    # Debug info
    # print(f"Searching for {x_value}")
    # print(f"Array: {x_arr}")
    
    if not np.any(lower_bool) or not np.any(upper_bool):
        print(f"FAILED to find neighbors in array: {x_arr}")
        return 0.0

    lower_idx = np.where(lower_bool)[0][-1]
    upper_idx = np.where(upper_bool)[0][0]
    
    print(f"Indices found: Lower={lower_idx} (Val={x_arr[lower_idx]}), Upper={upper_idx} (Val={x_arr[upper_idx]})")
    
    x0, x1 = x_arr[lower_idx], x_arr[upper_idx]
    y0, y1 = y_arr[lower_idx], y_arr[upper_idx]
    
    if x1 == x0:
        return float(y0)
    
    y_value = y0 + (x_value - x0) * (y1 - y0) / (x1 - x0)
    return float(y_value)

def test_reverse_lookup():
    # Setup Table: Ullage 0 -> Vol 1000; Ullage 100 -> Vol 500
    # Sorted by Ullage (standard)
    df = pd.DataFrame({
        'ullage_cm': [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        'volume_m3': [1000, 950, 900, 850, 800, 750, 700, 650, 600, 550, 500]
    })
    
    # Test Reverse: Find Ullage for Volume 925 (Should be 15 cm)
    target_vol = 925
    print(f"Testing lookup: Vol={target_vol} -> Expected Ullage=15")
    
    try:
        # In reverse_interpolate, we swap columns: x=volume_m3, y=ullage_cm
        result = linear_interpolate(df, 'volume_m3', 'ullage_cm', target_vol)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_reverse_lookup()
