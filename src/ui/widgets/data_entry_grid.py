"""
DataEntryGrid - A reusable table widget with copy-paste support.
Allows users to paste data from Excel or other spreadsheet applications.
"""

from typing import List, Optional, Callable
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout,
    QPushButton, QWidget, QHeaderView, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QColor


class DataEntryGrid(QTableWidget):
    """
    A table widget that supports copy-paste from spreadsheets.
    
    Features:
    - Paste multi-line tab-separated data (Ctrl+V)
    - Copy selected cells (Ctrl+C)
    - Validation of numeric data
    - Dynamic row management
    """
    
    data_changed = pyqtSignal()  # Emitted when data is modified
    
    def __init__(
        self,
        columns: List[str],
        parent: Optional[QWidget] = None,
        numeric_columns: Optional[List[int]] = None
    ):
        """
        Initialize the data entry grid.
        
        Args:
            columns: List of column header names
            parent: Parent widget
            numeric_columns: List of column indices that should be numeric (default: all)
        """
        super().__init__(parent)
        
        self.column_names = columns
        self.numeric_columns = numeric_columns if numeric_columns is not None else list(range(len(columns)))
        
        self._setup_table()
    
    def _setup_table(self):
        """Set up the table structure."""
        self.setColumnCount(len(self.column_names))
        self.setHorizontalHeaderLabels(self.column_names)
        
        # Set up header
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(len(self.column_names)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        
        # Start with some empty rows
        self.setRowCount(20)
        
        # Style - Removal of hardcoded background and light colors
        # Most of these are now handled by the GLOBAL_STYLESHEET in styles.py
        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
            QTableWidget {
                gridline-color: #334155;
            }
            QTableWidget::item:selected {
                background-color: #0c4a6e;
                color: white;
            }
        """)
    
    def keyPressEvent(self, event):
        """Handle key press events for copy/paste."""
        if event.matches(QKeySequence.StandardKey.Paste):
            self._handle_paste()
        elif event.matches(QKeySequence.StandardKey.Copy):
            self._handle_copy()
        elif event.key() == Qt.Key.Key_Delete:
            self._handle_delete()
        else:
            super().keyPressEvent(event)
    
    def _handle_paste(self):
        """Handle paste from clipboard."""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        
        if not text:
            return
        
        # Parse clipboard data (tab-separated, newline for rows)
        lines = text.strip().split('\n')
        if not lines:
            return
        
        # Get current cell position
        current_row = self.currentRow()
        current_col = self.currentColumn()
        
        if current_row < 0:
            current_row = 0
        if current_col < 0:
            current_col = 0
        
        # Ensure enough rows
        needed_rows = current_row + len(lines)
        if needed_rows > self.rowCount():
            self.setRowCount(needed_rows + 10)  # Add some buffer
        
        # Paste data
        errors = []
        for row_offset, line in enumerate(lines):
            cells = line.split('\t')
            for col_offset, value in enumerate(cells):
                target_col = current_col + col_offset
                if target_col >= self.columnCount():
                    continue
                
                target_row = current_row + row_offset
                value = value.strip()
                
                # Validate numeric columns
                if target_col in self.numeric_columns and value:
                    try:
                        float(value.replace(',', '.'))
                    except ValueError:
                        errors.append(f"Row {target_row + 1}, Col {self.column_names[target_col]}: '{value}' is not a number")
                        continue
                
                item = QTableWidgetItem(value.replace(',', '.'))
                self.setItem(target_row, target_col, item)
        
        if errors:
            QMessageBox.warning(
                self,
                "Paste Warnings",
                f"Some values were skipped:\n" + "\n".join(errors[:10])
            )
        
        self.data_changed.emit()
    
    def _handle_copy(self):
        """Handle copy to clipboard."""
        selection = self.selectedRanges()
        if not selection:
            return
        
        # Get the first selection range
        range_ = selection[0]
        
        lines = []
        for row in range(range_.topRow(), range_.bottomRow() + 1):
            row_data = []
            for col in range(range_.leftColumn(), range_.rightColumn() + 1):
                item = self.item(row, col)
                row_data.append(item.text() if item else "")
            lines.append("\t".join(row_data))
        
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(lines))
    
    def _handle_delete(self):
        """Handle delete key - clear selected cells."""
        for item in self.selectedItems():
            item.setText("")
        self.data_changed.emit()
    
    def get_data(self) -> List[List[str]]:
        """
        Get all non-empty data from the table.
        
        Returns:
            List of rows, where each row is a list of cell values.
        """
        data = []
        for row in range(self.rowCount()):
            row_data = []
            is_empty = True
            for col in range(self.columnCount()):
                item = self.item(row, col)
                value = item.text() if item else ""
                row_data.append(value)
                if value:
                    is_empty = False
            
            if not is_empty:
                data.append(row_data)
        
        return data
    
    def set_data(self, data: List[List[str]]):
        """
        Set data into the table.
        
        Args:
            data: List of rows, where each row is a list of cell values.
        """
        self.setRowCount(max(len(data) + 10, 20))
        
        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                if col_idx < self.columnCount():
                    self.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
        
        self.data_changed.emit()
    
    def clear_data(self):
        """Clear all data from the table."""
        self.clearContents()
        self.setRowCount(20)
        self.data_changed.emit()
    
    def get_row_count_with_data(self) -> int:
        """Get the number of rows that have data."""
        return len(self.get_data())
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate the table data.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        data = self.get_data()
        
        if not data:
            return False, "No data entered"
        
        for row_idx, row_data in enumerate(data):
            for col_idx in self.numeric_columns:
                if col_idx < len(row_data):
                    value = row_data[col_idx]
                    if value:
                        try:
                            float(value)
                        except ValueError:
                            return False, f"Row {row_idx + 1}, {self.column_names[col_idx]}: '{value}' is not a valid number"
        
        return True, ""


class DataEntryWidget(QWidget):
    """
    A complete data entry widget with grid and control buttons.
    """
    
    def __init__(
        self,
        columns: List[str],
        parent: Optional[QWidget] = None,
        show_buttons: bool = True
    ):
        super().__init__(parent)
        
        self.grid = DataEntryGrid(columns, self)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(self.grid)
        
        if show_buttons:
            btn_layout = QHBoxLayout()
            
            clear_btn = QPushButton("Clear All")
            clear_btn.clicked.connect(self.grid.clear_data)
            btn_layout.addWidget(clear_btn)
            
            btn_layout.addStretch()
            
            add_rows_btn = QPushButton("Add 10 Rows")
            add_rows_btn.clicked.connect(lambda: self.grid.setRowCount(self.grid.rowCount() + 10))
            btn_layout.addWidget(add_rows_btn)
            
            layout.addLayout(btn_layout)
    
    def get_data(self) -> List[List[str]]:
        return self.grid.get_data()
    
    def set_data(self, data: List[List[str]]):
        self.grid.set_data(data)
    
    def validate(self) -> tuple[bool, str]:
        return self.grid.validate()
