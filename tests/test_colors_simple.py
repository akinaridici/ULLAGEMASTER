import sys
import os

# Add src to python path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from PyQt6.QtWidgets import QApplication
from ui.widgets.discrepancy_widget import ParcelDiscrepancyCard
from models import Parcel

def verify_colors():
    app = QApplication([])
    p = Parcel(id="p1", name="TestParcel")
    card = ParcelDiscrepancyCard(p, ship_figure=1000, vef=1.0)
    
    # CASE 1: WHITE
    card.set_bl_figure(1000) 
    s1 = card.diff_pct_wo_vef_label.styleSheet()
    if "#ffffff" in s1:
        print("CASE 1: PASS")
    else:
        print(f"CASE 1: FAIL (Got {s1})")

    # CASE 2: ORANGE
    card.update_ship_figure(1002.5, 1.0)
    s2 = card.diff_pct_wo_vef_label.styleSheet()
    if "#f97316" in s2:
        print("CASE 2: PASS")
    else:
        print(f"CASE 2: FAIL (Got {s2})")

    # CASE 3: RED
    card.update_ship_figure(1005.0, 1.0)
    s3 = card.diff_pct_wo_vef_label.styleSheet()
    if "#dc2626" in s3:
        print("CASE 3: PASS")
    else:
        print(f"CASE 3: FAIL (Got {s3})")

if __name__ == "__main__":
    verify_colors()
