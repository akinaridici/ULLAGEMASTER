"""
Cargo input widget for entering loading requests.
Ported from STOWAGEMASTER with adaptations for ULLAGEMASTER.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,
    QLineEdit, QMessageBox, QDoubleSpinBox,
    QHeaderView, QDialog, QDialogButtonBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import List

from models.stowage_plan import StowageCargo, Receiver


class CargoInputWidget(QWidget):
    """Widget for entering cargo loading requests with table interface."""
    
    cargo_list_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Table for cargo entries
        self.cargo_table = QTableWidget()
        self.cargo_table.setColumnCount(6)
        self.cargo_table.setHorizontalHeaderLabels([
            "Yük Tipi", "Ton", "Density (ton/m³)", "Hacim (m³)", "Alıcı(lar)", ""
        ])
        self.cargo_table.setSortingEnabled(False)
        self.cargo_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cargo_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.cargo_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.cargo_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.cargo_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.cargo_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.cargo_table.setColumnWidth(5, 60)  # Fixed width for edit button
        self.cargo_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.cargo_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.cargo_table, 1)
        
        # Input controls row
        input_group = QHBoxLayout()
        
        self.cargo_type_input = QLineEdit()
        self.cargo_type_input.setPlaceholderText("Yük tipi (örn: Gasoil)")
        input_group.addWidget(self.cargo_type_input)
        
        self.ton_input = QDoubleSpinBox()
        self.ton_input.setMinimum(0.01)
        self.ton_input.setMaximum(1000000)
        self.ton_input.setSuffix(" ton")
        self.ton_input.setDecimals(2)
        self.ton_input.valueChanged.connect(self._calculate_volume)
        input_group.addWidget(self.ton_input)
        
        self.density_input = QDoubleSpinBox()
        self.density_input.setMinimum(0.01)
        self.density_input.setMaximum(10.0)
        self.density_input.setDecimals(4)
        self.density_input.setSingleStep(0.0001)
        self.density_input.setValue(0.8500)
        self.density_input.setToolTip("Yoğunluk (ton/m³)")
        self.density_input.valueChanged.connect(self._calculate_volume)
        input_group.addWidget(self.density_input)
        
        self.volume_label = QLabel("Hacim: 0.00 m³")
        self.volume_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        input_group.addWidget(self.volume_label)
        
        self.receiver_input = QLineEdit()
        self.receiver_input.setPlaceholderText("Alıcı adı")
        input_group.addWidget(self.receiver_input)
        

        
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_cargo)
        input_group.addWidget(add_btn)
        
        remove_btn = QPushButton("Delete")
        remove_btn.clicked.connect(self.remove_selected_cargo)
        input_group.addWidget(remove_btn)
        
        layout.addLayout(input_group, 0)
    
    def _calculate_volume(self):
        """
        Calculate volume from ton and density.
        
        Triggered when Ton or Density input values change.
        Updates the volume label automatically.
        Formula: Volume = Ton / Density
        """
        ton = self.ton_input.value()
        density = self.density_input.value()
        
        if density > 0:
            volume = ton / density
            self.volume_label.setText(f"Hacim: {volume:.2f} m³")
        else:
            self.volume_label.setText("Hacim: 0.00 m³")
    
    def add_cargo(self):
        """Add a new cargo entry."""
        cargo_type = self.cargo_type_input.text().strip().upper()
        ton = self.ton_input.value()
        density = self.density_input.value()
        receiver_text = self.receiver_input.text().strip().upper()
        
        if not cargo_type:
            QMessageBox.warning(self, "Hata", "Lütfen yük tipi girin.")
            return
        
        if ton <= 0:
            QMessageBox.warning(self, "Hata", "Ton miktarı pozitif olmalıdır.")
            return
        
        if density <= 0:
            QMessageBox.warning(self, "Hata", "Yoğunluk pozitif olmalıdır.")
            return
        
        volume = ton / density
        
        receivers = []
        if receiver_text:
            receiver_names = [name.strip() for name in receiver_text.split(',')]
            receivers = [Receiver(name=name) for name in receiver_names if name]
        
        
        # Create cargo object
        cargo = StowageCargo(
            cargo_type=cargo_type,
            quantity=volume,
            receivers=receivers,
            density=density,
        )
        # Store ton for reference
        cargo.ton = ton
        
        # Add to table
        row = self.cargo_table.rowCount()
        self.cargo_table.insertRow(row)
        
        self.cargo_table.setItem(row, 0, QTableWidgetItem(cargo_type))
        self.cargo_table.setItem(row, 1, QTableWidgetItem(f"{ton:.2f}"))
        self.cargo_table.setItem(row, 2, QTableWidgetItem(f"{density:.4f}"))
        self.cargo_table.setItem(row, 3, QTableWidgetItem(f"{volume:.2f}"))
        receiver_str = ", ".join([r.name for r in receivers]) if receivers else "Genel"
        self.cargo_table.setItem(row, 4, QTableWidgetItem(receiver_str))
        
        # Store cargo object in first column
        self.cargo_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, cargo)
        
        # Edit button
        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet("padding: 2px; font-size: 8pt; max-height: 20px;")
        edit_btn.clicked.connect(self._on_edit_clicked)
        self.cargo_table.setCellWidget(row, 5, edit_btn)
        
        # Clear inputs
        self.cargo_type_input.clear()
        self.ton_input.setValue(0.01)
        self.density_input.setValue(0.8500)
        self.volume_label.setText("Hacim: 0.00 m³")
        self.receiver_input.clear()
        
        self.cargo_list_changed.emit()
    
    def _on_edit_clicked(self):
        """Handle edit button click."""
        button = self.sender()
        if not isinstance(button, QPushButton):
            return
        
        for row in range(self.cargo_table.rowCount()):
            if self.cargo_table.cellWidget(row, 5) == button:
                self._edit_cargo(row)
                return
    
    def _edit_cargo(self, row: int):
        """Open edit dialog for cargo at row."""
        cargo_item = self.cargo_table.item(row, 0)
        if not cargo_item:
            return
        
        cargo = cargo_item.data(Qt.ItemDataRole.UserRole)
        if not cargo:
            return
        
        dialog = CargoEditDialog(self, cargo)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated = dialog.get_cargo()
            
            # Update table
            self.cargo_table.setItem(row, 0, QTableWidgetItem(updated.cargo_type))
            ton = getattr(updated, 'ton', updated.quantity * updated.density if updated.density else 0)
            self.cargo_table.setItem(row, 1, QTableWidgetItem(f"{ton:.2f}" if ton else "-"))
            self.cargo_table.setItem(row, 2, QTableWidgetItem(f"{updated.density:.4f}"))
            self.cargo_table.setItem(row, 3, QTableWidgetItem(f"{updated.quantity:.2f}"))
            receiver_str = updated.get_receiver_names()
            self.cargo_table.setItem(row, 4, QTableWidgetItem(receiver_str))
            
            # Update mandatory checkbox
            mandatory_cb = self.cargo_table.cellWidget(row, 5)
            if mandatory_cb:
                mandatory_cb.setChecked(getattr(updated, 'is_mandatory', False))
            
            # Update stored cargo
            self.cargo_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, updated)
            
            self.cargo_list_changed.emit()
    
    def remove_selected_cargo(self):
        """Remove selected cargo entry."""
        current_row = self.cargo_table.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(
                self, "Yük Sil",
                "Bu yükü silmek istediğinizden emin misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.cargo_table.removeRow(current_row)
                self.cargo_list_changed.emit()
        else:
            QMessageBox.warning(self, "Uyarı", "Lütfen silmek istediğiniz yükü seçin.")
    
    def get_cargo_list(self) -> List[StowageCargo]:
        """Get list of all cargo entries."""
        cargo_list = []
        
        for row in range(self.cargo_table.rowCount()):
            cargo_item = self.cargo_table.item(row, 0)
            if cargo_item:
                cargo = cargo_item.data(Qt.ItemDataRole.UserRole)
                if cargo:
                    cargo_list.append(cargo)
        
        return cargo_list
    
    def set_cargo_list(self, cargo_list: List[StowageCargo]):
        """Set cargo list (for loading saved plans)."""
        self.cargo_table.setRowCount(0)
        
        for cargo in cargo_list:
            row = self.cargo_table.rowCount()
            self.cargo_table.insertRow(row)
            
            self.cargo_table.setItem(row, 0, QTableWidgetItem(cargo.cargo_type))
            ton = getattr(cargo, 'ton', cargo.quantity * cargo.density if cargo.density else 0)
            self.cargo_table.setItem(row, 1, QTableWidgetItem(f"{ton:.2f}" if ton else "-"))
            self.cargo_table.setItem(row, 2, QTableWidgetItem(f"{cargo.density:.4f}"))
            self.cargo_table.setItem(row, 3, QTableWidgetItem(f"{cargo.quantity:.2f}"))
            self.cargo_table.setItem(row, 4, QTableWidgetItem(cargo.get_receiver_names()))
            
            self.cargo_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, cargo)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet("padding: 2px; font-size: 8pt; max-height: 20px;")
            edit_btn.clicked.connect(self._on_edit_clicked)
            self.cargo_table.setCellWidget(row, 5, edit_btn)


class CargoEditDialog(QDialog):
    """Dialog for editing a single cargo entry."""
    
    def __init__(self, parent=None, cargo: StowageCargo = None):
        super().__init__(parent)
        self.cargo = cargo or StowageCargo(cargo_type="", quantity=0.0)
        self.setWindowTitle("Yük Düzenle")
        self._init_ui()
        self._load_cargo_data()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Cargo type
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Yük Tipi:"))
        self.cargo_type_input = QLineEdit()
        type_row.addWidget(self.cargo_type_input)
        layout.addLayout(type_row)
        
        # Ton
        ton_row = QHBoxLayout()
        ton_row.addWidget(QLabel("Ton:"))
        self.ton_input = QDoubleSpinBox()
        self.ton_input.setMinimum(0.01)
        self.ton_input.setMaximum(1000000)
        self.ton_input.setSuffix(" ton")
        self.ton_input.setDecimals(2)
        self.ton_input.valueChanged.connect(self._calculate_volume)
        ton_row.addWidget(self.ton_input)
        layout.addLayout(ton_row)
        
        # Density
        density_row = QHBoxLayout()
        density_row.addWidget(QLabel("Density:"))
        self.density_input = QDoubleSpinBox()
        self.density_input.setMinimum(0.01)
        self.density_input.setMaximum(10.0)
        self.density_input.setDecimals(4)
        self.density_input.setSingleStep(0.0001)
        self.density_input.valueChanged.connect(self._calculate_volume)
        density_row.addWidget(self.density_input)
        layout.addLayout(density_row)
        
        # Volume (read-only)
        volume_row = QHBoxLayout()
        volume_row.addWidget(QLabel("Hacim:"))
        self.volume_label = QLabel("0.00 m³")
        self.volume_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        volume_row.addWidget(self.volume_label)
        volume_row.addStretch()
        layout.addLayout(volume_row)
        
        # Receivers
        receiver_row = QHBoxLayout()
        receiver_row.addWidget(QLabel("Alıcı(lar):"))
        self.receiver_input = QLineEdit()
        self.receiver_input.setPlaceholderText("Virgülle ayırın")
        receiver_row.addWidget(self.receiver_input)
        layout.addLayout(receiver_row)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_cargo_data(self):
        """Load cargo data into inputs."""
        self.cargo_type_input.setText(self.cargo.cargo_type)
        
        ton = getattr(self.cargo, 'ton', None)
        if ton:
            self.ton_input.setValue(ton)
        elif self.cargo.quantity and self.cargo.density:
            self.ton_input.setValue(self.cargo.quantity * self.cargo.density)
        else:
            self.ton_input.setValue(0.01)
        
        self.density_input.setValue(self.cargo.density or 0.8500)
        self._calculate_volume()
        
        if self.cargo.receivers:
            self.receiver_input.setText(", ".join([r.name for r in self.cargo.receivers]))
    
    def _calculate_volume(self):
        """Calculate volume from ton and density."""
        ton = self.ton_input.value()
        density = self.density_input.value()
        
        if density > 0:
            volume = ton / density
            self.volume_label.setText(f"{volume:.2f} m³")
        else:
            self.volume_label.setText("0.00 m³")
    
    def get_cargo(self) -> StowageCargo:
        """Get updated cargo object."""
        cargo_type = self.cargo_type_input.text().strip().upper()
        ton = self.ton_input.value()
        density = self.density_input.value()
        receiver_text = self.receiver_input.text().strip()
        
        volume = ton / density if density > 0 else 0.0
        
        receivers = []
        if receiver_text:
            names = [n.strip().upper() for n in receiver_text.split(',')]
            receivers = [Receiver(name=n) for n in names if n]
        
        cargo = StowageCargo(
            cargo_type=cargo_type,
            quantity=volume,
            receivers=receivers,
            density=density,
            unique_id=self.cargo.unique_id,
            custom_color=self.cargo.custom_color,
        )
        cargo.ton = ton
        
        return cargo
