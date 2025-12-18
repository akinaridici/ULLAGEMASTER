"""
Custom delegates for table widgets.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QStyledItemDelegate, QComboBox, QWidget
)
from PyQt6.QtCore import Qt, QTimer


class ComboBoxDelegate(QStyledItemDelegate):
    """
    A delegate that provides a ComboBox for editing.
    Used for dropdown columns like Parcel selection.
    """
    
    def __init__(self, options: List[str] = None, parent=None):
        super().__init__(parent)
        self._options = options or []
    
    def set_options(self, options: List[str]):
        """Update the dropdown options."""
        self._options = options
    
    def createEditor(self, parent: QWidget, option, index):
        """Create a ComboBox editor."""
        combo = QComboBox(parent)
        combo.addItems(self._options)
        
        # Use activated instead of currentIndexChanged to only trigger on user interaction
        combo.activated.connect(self._commit_and_close)
        
        return combo
    
    def _commit_and_close(self):
        """Commit data immediately on selection."""
        editor = self.sender()
        self.commitData.emit(editor)
        # Did not emit closeEditor because we are using persistent editors
        # self.closeEditor.emit(editor)
    
    def setEditorData(self, editor: QComboBox, index):
        """Set the current value in the ComboBox."""
        value = index.data(Qt.ItemDataRole.EditRole)
        if value:
            idx = editor.findText(str(value))
            if idx >= 0:
                editor.setCurrentIndex(idx)
    
    def setModelData(self, editor: QComboBox, model, index):
        """Save the selected value to the model."""
        value = editor.currentText()
        model.setData(index, value, Qt.ItemDataRole.EditRole)
    
    def updateEditorGeometry(self, editor, option, index):
        """Set the editor geometry."""
        editor.setGeometry(option.rect)
