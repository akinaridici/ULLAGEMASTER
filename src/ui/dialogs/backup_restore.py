"""
Backup/Restore Dialogs.
UI components for the backup and restore workflow.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFileDialog, QMessageBox,
    QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt
from pathlib import Path

from utils.backup_manager import (
    create_backup, restore_backup, verify_password, get_default_backup_dir
)
from ui.styles import COLOR_TEXT_SECONDARY, COLOR_DANGER

class BackupDialog(QDialog):
    """Dialog for creating a backup."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Backup Configuration")
        self.setMinimumWidth(500)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Info
        info = QLabel(
            "This will save your current Ship Configuration and Company Logo "
            "to a backup folder."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Path selection
        path_group = QGroupBox("Target Directory")
        path_layout = QHBoxLayout(path_group)
        
        self.path_edit = QLineEdit()
        self.path_edit.setText(str(get_default_backup_dir()))
        path_layout.addWidget(self.path_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        path_layout.addWidget(browse_btn)
        
        layout.addWidget(path_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        backup_btn = QPushButton("Create Backup")
        # Green-ish styling for save action
        backup_btn.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
        backup_btn.clicked.connect(self._perform_backup)
        btn_layout.addWidget(backup_btn)
        
        layout.addLayout(btn_layout)
        
    def _browse(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Backup Directory", self.path_edit.text()
        )
        if dir_path:
            self.path_edit.setText(dir_path)
            
    def _perform_backup(self):
        target_dir = self.path_edit.text()
        if not target_dir:
            return
            
        success, msg = create_backup(target_dir)
        
        if success:
            QMessageBox.information(self, "Backup Successful", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "Backup Failed", msg)


class RestoreDialog(QDialog):
    """Dialog for restoring from backup."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Restore Configuration")
        self.setMinimumWidth(500)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Warning
        warning = QLabel(
            "⚠️ WARNING: Restore will OVERWRITE your current configuration.\n"
            "This action cannot be undone."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(f"color: {COLOR_DANGER}; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(warning)
        
        # Path selection
        path_group = QGroupBox("Source Directory")
        path_layout = QHBoxLayout(path_group)
        
        self.path_edit = QLineEdit()
        self.path_edit.setText(str(get_default_backup_dir()))
        path_layout.addWidget(self.path_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        path_layout.addWidget(browse_btn)
        
        layout.addWidget(path_group)
        
        # Password
        pass_group = QGroupBox("Security Verification")
        pass_layout = QFormLayout(pass_group)
        
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_edit.setPlaceholderText("Enter Administrator Password")
        pass_layout.addRow("Password:", self.pass_edit)
        
        layout.addWidget(pass_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        restore_btn = QPushButton("RESTORE")
        restore_btn.setStyleSheet(f"background-color: {COLOR_DANGER}; color: white; font-weight: bold;")
        restore_btn.clicked.connect(self._perform_restore)
        btn_layout.addWidget(restore_btn)
        
        layout.addLayout(btn_layout)
        
    def _browse(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Backup Source", self.path_edit.text()
        )
        if dir_path:
            self.path_edit.setText(dir_path)
            
    def _perform_restore(self):
        # 1. Verify Password
        password = self.pass_edit.text()
        if not verify_password(password):
            QMessageBox.warning(self, "Access Denied", "Incorrect Password!")
            self.pass_edit.clear()
            self.pass_edit.setFocus()
            return
            
        # 2. Confirm Action
        confirm = QMessageBox.question(
            self, "Confirm Restore",
            "Are you sure you want to overwrite your current configuration?\n\n"
            "Current settings will be lost forever.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirm != QMessageBox.StandardButton.Yes:
            return
            
        # 3. Perform Restore
        source_dir = self.path_edit.text()
        success, msg = restore_backup(source_dir)
        
        if success:
            QMessageBox.information(self, "Restore Successful", msg + "\n\nPlease restart the application.")
            self.accept()
        else:
            QMessageBox.critical(self, "Restore Failed", msg)
