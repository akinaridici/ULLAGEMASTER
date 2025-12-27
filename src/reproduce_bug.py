
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

# Mock Data Classes
@dataclass
class TankReading:
    ullage: Optional[float] = None
    fill_percent: Optional[float] = None
    tov: float = 0.0
    trim_correction: float = 0.0
    corrected_ullage: Optional[float] = None
    capacity: float = 1000.0

# Mock Tables
ullage_data = []
for i in range(0, 2000, 10): # 0 to 2000 cm
    ullage_data.append({'ullage_cm': float(i), 'volume_m3': 1000.0 - (i * 0.5)}) # Linear 0.5 m3/cm
ullage_table = pd.DataFrame(ullage_data)

trim_data = [] # Simple trim table
# At 500cm ullage, 1m trim -> -5cm correction
trim_table = pd.DataFrame([
    {'ullage_cm': 500, 'trim_m': 1.0, 'correction_m3': -0.1} # Dummy structure, logic usually uses interpolation
])

# Mock Calculation Functions
def calculate_ullage_from_percent(percent, capacity, table):
    target_vol = (percent / 100.0) * capacity
    # Simple linear reverse lookup: Vol = 1000 - 0.5 * ullage -> 0.5 * ullage = 1000 - Vol -> ullage = (1000 - Vol) / 0.5
    return (1000.0 - target_vol) / 0.5

def calculate_fill_percent(volume, capacity):
    return (volume / capacity) * 100.0

def get_trim_correction(measured_mm, trim, table):
    # Mock: Correction = Trim * 10 (mm) 
    return trim * 10.0 

def calculate_tov(corrected_ullage_cm, table):
    # Vol = 1000 - 0.5 * ullage
    return 1000.0 - (0.5 * corrected_ullage_cm)


# The Logic from MainWindow
def recalculate_tank(reading, trim_val, sim_name):
    print(f"\n--- {sim_name} Recalculation (Trim={trim_val}) ---")
    print(f"Input State: Ullage={reading.ullage}, Fill={reading.fill_percent}")
    
    # 1. Determine Measured Ullage
    if reading.ullage is not None:
        measured_ullage_cm = reading.ullage
        print(f"Logic: Used existing Ullage: {measured_ullage_cm}")
    elif reading.fill_percent is not None:
        measured_ullage_cm = calculate_ullage_from_percent(reading.fill_percent, reading.capacity, ullage_table)
        print(f"Logic: Calculated Ullage from Fill%: {measured_ullage_cm}")
        
        # BUG SUSPECT:
        reading.ullage = measured_ullage_cm 
        print(f"Logic: Updated reading.ullage to {reading.ullage}")
    else:
        print("Logic: No input")
        return

    measured_ullage_mm = measured_ullage_cm * 10
    
    # 2. Trim Correction
    trim_corr_mm = get_trim_correction(measured_ullage_mm, trim_val, trim_table)
    reading.trim_correction = trim_corr_mm / 10.0
    
    corrected_ullage_mm = measured_ullage_mm + trim_corr_mm
    reading.corrected_ullage = corrected_ullage_mm / 10.0
    
    # 3. TOV
    reading.tov = calculate_tov(reading.corrected_ullage, ullage_table)
    
    # 4. Fill Percent Update (only if user provided ullage)
    # The check involves tracking "user_entered_fill_percent" outside?
    # In MainWindow it's local variable:
    # user_entered_fill_percent = reading.fill_percent is not None and reading.ullage is None (before update)
    # But wait, if we updated reading.ullage above, this check would fail if repeated?
    
    # Let's say we simulate the loop.
    reading.fill_percent = calculate_fill_percent(reading.tov, reading.capacity)
    
    print(f"Output: MeasUllage={reading.ullage}, CorrUllage={reading.corrected_ullage}, TOV={reading.tov}, Fill={reading.fill_percent}")
    return reading.ullage

def update_reading(reading, key, value):
    print(f"Update: Key={key}, Value={value}")
    if key == "ullage":
        reading.ullage = float(value) if value is not None else None
        if reading.ullage is not None:
            reading.fill_percent = None # Clears fill percent
            print("Update: Cleared fill_percent")
            
def run_simulation():
    # Scenario: User enters 50% Fill.
    reading = TankReading(capacity=1000.0)
    
    # 1. User sets Fill %
    reading.fill_percent = 50.0 
    reading.ullage = None
    
    # 2. First Recalc (Trim 0)
    current_ullage_val = recalculate_tank(reading, 0.0, "Init")
    
    # 3. Signal Loop Simulation: value written to cell -> loop back
    # Cell gets "1000.0" (calculated from 50% -> 500 vol -> ullage=(1000-500)/0.5=1000)
    update_reading(reading, "ullage", current_ullage_val)
    
    # 4. Second Recalc (triggered by update reading)
    recalculate_tank(reading, 0.0, "Post-Signal")
    
    # 5. User changes Trim to 1.0
    # Logic runs again
    recalculate_tank(reading, 1.0, "Trim Change")
    
if __name__ == "__main__":
    run_simulation()
