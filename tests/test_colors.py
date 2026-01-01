import sys
import os

# Add src to python path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from PyQt6.QtWidgets import QApplication
from ui.widgets.discrepancy_widget import ParcelDiscrepancyCard
from models import Parcel

def verify_colors():
    app = QApplication([])
    
    # Mock Parcel
    p = Parcel(id="p1", name="TestParcel")
    
    # Create Card
    # Ship Figure 1000, VEF 1.0
    card = ParcelDiscrepancyCard(p, ship_figure=1000, vef=1.0)
    
    print("--- Test Case 1: Diff 0 (< 2‰) -> Should be White ---")
    card.set_bl_figure(1000) 
    # Diff = 0, Pct = 0
    # Expected: White (#ffffff)
    style_wo = card.diff_pct_wo_vef_label.styleSheet()
    style_with = card.diff_pct_with_vef_label.styleSheet()
    print(f"Diff Pct: {card.diff_pct_with_vef_label.text()}")
    print(f"Style WO: {style_wo}")
    print(f"Style With: {style_with}")
    
    if "#ffffff" in style_wo and "#ffffff" in style_with:
        print("PASS: Colors are white.\n")
    else:
        print("FAIL: Colors are NOT white.\n")

    print("--- Test Case 2: Diff 2.5 (< 3‰, >= 2‰) -> Should be Orange ---")
    # 2.5/1000 = 2.5‰
    card.update_ship_figure(1002.5, 1.0)
    # Expected: Orange (#f97316)
    style_wo = card.diff_pct_wo_vef_label.styleSheet()
    style_with = card.diff_pct_with_vef_label.styleSheet()
    print(f"Diff Pct: {card.diff_pct_with_vef_label.text()}")
    print(f"Style WO: {style_wo}")
    print(f"Style With: {style_with}")

    if "#f97316" in style_wo and "#f97316" in style_with:
        print("PASS: Colors are orange.\n")
    else:
        print("FAIL: Colors are NOT orange.\n")

    print("--- Test Case 3: Diff 5.0 (>= 3‰) -> Should be Red ---")
    # 5/1000 = 5‰
    card.update_ship_figure(1005.0, 1.0)
    # Expected: Red (#dc2626)
    style_wo = card.diff_pct_wo_vef_label.styleSheet()
    style_with = card.diff_pct_with_vef_label.styleSheet()
    print(f"Diff Pct: {card.diff_pct_with_vef_label.text()}")
    print(f"Style WO: {style_wo}")
    print(f"Style With: {style_with}")

    if "#dc2626" in style_wo and "#dc2626" in style_with:
        print("PASS: Colors are red.\n")
    else:
        print("FAIL: Colors are NOT red.\n")

if __name__ == "__main__":
    verify_colors()
