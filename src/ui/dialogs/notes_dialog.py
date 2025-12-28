from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, 
    QDialogButtonBox, QMessageBox
)
from PyQt6.QtCore import Qt

class NotesDialog(QDialog):
    def __init__(self, notes="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sefer Notları")
        self.setMinimumSize(400, 300)
        self.notes = notes
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Sefer Notları (Max 1000 karakter):"))
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.notes)
        self.text_edit.textChanged.connect(self._check_limit)
        layout.addWidget(self.text_edit)
        
        self.char_count_label = QLabel(f"{len(self.notes)}/1000")
        self.char_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.char_count_label)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _check_limit(self):
        text = self.text_edit.toPlainText()
        if len(text) > 1000:
            text = text[:1000]
            self.text_edit.setPlainText(text)
            cursor = self.text_edit.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.text_edit.setTextCursor(cursor)
        
        self.char_count_label.setText(f"{len(text)}/1000")
        self.notes = text
        
    def get_notes(self):
        return self.notes
