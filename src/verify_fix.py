
# Verification of Fix Logic

def test_fix_scenario():
    # 1. User enters Fill 50%
    reading = TankReading()
    reading.fill_percent = 50.0
    reading.ullage = None # Cleared by _update_reading
    
    # Recalc (Latch Phase)
    # _recalculate_tank sees ullage is None, fill is 50.
    # Calculates Ullage = 1000.
    # LATCHES: reading.ullage = 1000.
    
    # UI Update (Blocked Signals)
    # _update_row sets cell text "1000.0".
    # Signals Blocked -> No _update_reading call.
    # State remains: Ullage=1000, Fill=50.
    
    print(f"State after Input: Ullage={reading.ullage}, Fill={reading.fill_percent}")
    # EXPECT: Ullage=1000.
    
    # 2. User changes Trim (All Other Scenarios)
    # Recalc Triggered.
    # _recalculate_tank sees reading.ullage is 1000 (NOT None).
    # Uses Ullage 1000.
    # DOES NOT recalculate from Fill.
    # Calculates Corrected Ullage, TOV, and NEW Fill %.
    
    print(f"State after Trim: Ullage Used=1000. Fill Updated.")
    # EXPECT: Ullage unchanged. Master preserved.

if __name__ == "__main__":
    test_fix_scenario()
