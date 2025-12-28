"""
Excel-like table widget.
Provides keyboard navigation standardization (Enter moves down).
"""

from PyQt6.QtWidgets import QTableWidget, QAbstractItemView, QAbstractItemDelegate
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent


class ExcelTableWidget(QTableWidget):
    """
    QTableWidget with Excel-like navigation.
    - Enter key moves selection down after editing (instead of staying in cell)
    - Enter key also moves down when just navigating (no editing)
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending_move = False
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events for navigation when NOT editing."""
        # Check for Enter/Return keys
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Only handle if we are NOT currently editing
            # When editing, the editor handles Enter and triggers closeEditor
            if self.state() != QAbstractItemView.State.EditingState:
                # Skip if modifier keys are pressed
                if not (event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)):
                    row = self.currentRow()
                    col = self.currentColumn()
                    if row < self.rowCount() - 1:
                        self.setCurrentCell(row + 1, col)
                    event.accept()
                    return
        
        super().keyPressEvent(event)
    
    def closeEditor(self, editor, hint):
        """
        Called when editing finishes (e.g. user pressed Enter in the editor).
        We want to move down after editing closes.
        """
        # Call super first to commit data
        super().closeEditor(editor, hint)
        
        # We enforce move down unless it was Tab (EditNextItem) or Shift+Tab (EditPreviousItem)
        if hint == QAbstractItemDelegate.EndEditHint.EditNextItem:
            # Tab key - default behavior moves right
            pass
        elif hint == QAbstractItemDelegate.EndEditHint.EditPreviousItem:
            # Shift+Tab - default behavior moves left
            pass
        else:
            # For Enter (SubmitModelCache) or click-away, move down
            # Use flag to prevent multiple moves
            if not self._pending_move:
                self._pending_move = True
                QTimer.singleShot(0, self._move_selection_down)
            
    def _move_selection_down(self):
        """Move selection down one row."""
        self._pending_move = False
        row = self.currentRow()
        col = self.currentColumn()
        
        if row < self.rowCount() - 1:
            self.setCurrentCell(row + 1, col)
