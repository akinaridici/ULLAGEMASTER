import sys
import os
import shutil

# Add src to python path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from PyQt6.QtWidgets import QApplication
# Correct Import: voyage_explorer.py is directly in ui/widgets/
from ui.widgets.voyage_explorer import VoyageExplorerWidget
from models import ShipConfig

def verify_list_deletion():
    app = QApplication([])
    
    # Setup test dir
    test_dir = os.path.join(os.getcwd(), 'VOYAGES')
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    # Create dummy voyages
    with open(os.path.join(test_dir, 'test_v1.voyage'), 'w') as f: f.write("{}")
    with open(os.path.join(test_dir, 'test_v2.voyage'), 'w') as f: f.write("{}")
    
    # Init ship config with dummy data
    config = ShipConfig(ship_name="TestShip", tank_count=12)
    widget = VoyageExplorerWidget(config)
    
    # 1. Verify Selection Mode
    if widget.file_list.selectionMode() == widget.file_list.SelectionMode.ExtendedSelection:
        print("PASS: ExtendedSelection enabled.")
    else:
        print("FAIL: Selection mode incorrect.")

    # 2. Select items
    items = []
    # Manually populate list just in case refresh didn't happen yet (though init calls it)
    widget.refresh_list() 
    
    # Find items to select
    for i in range(widget.file_list.count()):
        item = widget.file_list.item(i)
        if "test_v" in item.text():
            item.setSelected(True)
            items.append(item.text())
            
    # Need to manually set current item or focus to simulate selection for some APIs? 
    # But selectedItems() should work
    
    print(f"Selected items: {items}")
    
    # 3. Simulate Removal
    widget._remove_selected_voyages()
    
    # 4. Verify Removed from UI
    remaining = [widget.file_list.item(i).text() for i in range(widget.file_list.count())]
    if not any("test_v" in x for x in remaining):
        print("PASS: Items removed from UI.")
    else:
        print(f"FAIL: Items still in UI: {remaining}")

    # 5. Verify Files Exist
    if os.path.exists(os.path.join(test_dir, 'test_v1.voyage')):
        print("PASS: File 1 exists on disk.")
    else:
        print("FAIL: File 1 deleted!")

    # 6. Verify Refresh
    widget.refresh_list()
    refreshed = [widget.file_list.item(i).text() for i in range(widget.file_list.count())]
    if any("test_v" in x for x in refreshed):
         print("PASS: Items reappeared after refresh.")
    else:
         print("FAIL: Items did not reappear.")
         
    # Clean up
    if os.path.exists(os.path.join(test_dir, 'test_v1.voyage')):
        os.remove(os.path.join(test_dir, 'test_v1.voyage'))
    if os.path.exists(os.path.join(test_dir, 'test_v2.voyage')):
        os.remove(os.path.join(test_dir, 'test_v2.voyage'))

if __name__ == "__main__":
    verify_list_deletion()
