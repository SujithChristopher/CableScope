"""
Firmware Tab for CableScope Motor Control
Firmware upload and management functionality
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QComboBox, QLabel, QLineEdit, QTextEdit,
    QFileDialog, QMessageBox, QProgressBar, QCheckBox
)
from PySide6.QtCore import Signal, Slot, Qt, QThread, QTimer
from PySide6.QtGui import QFont
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional


class FirmwareUploadWorker(QThread):
    """Worker thread for firmware upload"""
    
    upload_started = Signal()
    upload_progress = Signal(str)  # Status message
    upload_completed = Signal(bool, str)  # Success, message
    
    def __init__(self, arduino_cli_path: str, firmware_path: str, port: str, board_type: str):
        super().__init__()
        self.arduino_cli_path = arduino_cli_path
        self.firmware_path = firmware_path
        self.port = port
        self.board_type = board_type
    
    def run(self):
        """Run firmware upload process"""
        try:
            self.upload_started.emit()
            
            # Compile command
            compile_cmd = [
                self.arduino_cli_path,
                "compile",
                "--fqbn", self.board_type,
                self.firmware_path
            ]
            
            self.upload_progress.emit("Compiling firmware...")
            
            # Run compile
            compile_result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if compile_result.returncode != 0:
                self.upload_completed.emit(False, f"Compile failed: {compile_result.stderr}")
                return
            
            self.upload_progress.emit("Compilation successful, uploading...")
            
            # Upload command
            upload_cmd = [
                self.arduino_cli_path,
                "upload",
                "--fqbn", self.board_type,
                "--port", self.port,
                self.firmware_path
            ]
            
            # Run upload
            upload_result = subprocess.run(
                upload_cmd,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )
            
            if upload_result.returncode == 0:
                self.upload_completed.emit(True, "Firmware uploaded successfully!")
            else:
                self.upload_completed.emit(False, f"Upload failed: {upload_result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.upload_completed.emit(False, "Upload timed out")
        except Exception as e:
            self.upload_completed.emit(False, f"Upload error: {str(e)}")


class FirmwareTab(QWidget):
    """Firmware upload and management tab"""
    
    # Signals
    firmware_upload_requested = Signal(str, str)  # firmware_path, board_type
    firmware_path_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.arduino_cli_path = "arduino-cli.exe"
        self.firmware_path = ""
        self.selected_port = ""
        self.board_type = "teensy:avr:teensy41"
        
        # Upload worker
        self.upload_worker = None
        self.is_uploading = False
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Arduino CLI setup
        cli_group = self.create_cli_group()
        layout.addWidget(cli_group)
        
        # Firmware selection
        firmware_group = self.create_firmware_group()
        layout.addWidget(firmware_group)
        
        # Board and port selection
        board_group = self.create_board_group()
        layout.addWidget(board_group)
        
        # Upload controls
        upload_group = self.create_upload_group()
        layout.addWidget(upload_group)
        
        # Upload log
        log_group = self.create_log_group()
        layout.addWidget(log_group, 1)  # Give log area most space
    
    def create_cli_group(self) -> QGroupBox:
        """Create Arduino CLI setup group"""
        group = QGroupBox("Arduino CLI Configuration")
        layout = QGridLayout(group)
        
        # Arduino CLI path
        layout.addWidget(QLabel("Arduino CLI Path:"), 0, 0)
        self.cli_path_edit = QLineEdit()
        self.cli_path_edit.setText(self.arduino_cli_path)
        self.cli_path_edit.textChanged.connect(self.on_cli_path_changed)
        layout.addWidget(self.cli_path_edit, 0, 1)
        
        # Browse button
        self.browse_cli_button = QPushButton("Browse")
        self.browse_cli_button.clicked.connect(self.browse_arduino_cli)
        layout.addWidget(self.browse_cli_button, 0, 2)
        
        # Test CLI button
        self.test_cli_button = QPushButton("Test CLI")
        self.test_cli_button.clicked.connect(self.test_arduino_cli)
        layout.addWidget(self.test_cli_button, 0, 3)
        
        # CLI status
        layout.addWidget(QLabel("Status:"), 1, 0)
        self.cli_status_label = QLabel("Not tested")
        self.cli_status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.cli_status_label, 1, 1, 1, 3)
        
        return group
    
    def create_firmware_group(self) -> QGroupBox:
        """Create firmware selection group"""
        group = QGroupBox("Firmware Selection")
        layout = QGridLayout(group)
        
        # Firmware path
        layout.addWidget(QLabel("Firmware File:"), 0, 0)
        self.firmware_path_edit = QLineEdit()
        self.firmware_path_edit.setReadOnly(True)
        layout.addWidget(self.firmware_path_edit, 0, 1)
        
        # Browse button
        self.browse_firmware_button = QPushButton("Browse")
        self.browse_firmware_button.clicked.connect(self.browse_firmware)
        layout.addWidget(self.browse_firmware_button, 0, 2)
        
        # Use default checkbox
        self.use_default_checkbox = QCheckBox("Use default firmware (firmware/firmware.ino)")
        self.use_default_checkbox.setChecked(True)
        self.use_default_checkbox.toggled.connect(self.on_use_default_toggled)
        layout.addWidget(self.use_default_checkbox, 1, 0, 1, 3)
        
        return group
    
    def create_board_group(self) -> QGroupBox:
        """Create board and port selection group"""
        group = QGroupBox("Board Configuration")
        layout = QGridLayout(group)
        
        # Board type
        layout.addWidget(QLabel("Board Type:"), 0, 0)
        self.board_combo = QComboBox()
        self.board_combo.addItems([
            "teensy:avr:teensy41",
            "teensy:avr:teensy40",
            "teensy:avr:teensy36",
            "teensy:avr:teensy32",
            "teensy:avr:teensy31",
            "arduino:avr:uno",
            "arduino:avr:nano",
            "arduino:avr:mega"
        ])
        self.board_combo.setCurrentText(self.board_type)
        self.board_combo.currentTextChanged.connect(self.on_board_changed)
        layout.addWidget(self.board_combo, 0, 1)
        
        # Port selection
        layout.addWidget(QLabel("Upload Port:"), 1, 0)
        self.port_combo = QComboBox()
        layout.addWidget(self.port_combo, 1, 1)
        
        # Refresh ports button
        self.refresh_ports_button = QPushButton("Refresh Ports")
        self.refresh_ports_button.clicked.connect(self.refresh_ports)
        layout.addWidget(self.refresh_ports_button, 1, 2)
        
        return group
    
    def create_upload_group(self) -> QGroupBox:
        """Create upload control group"""
        group = QGroupBox("Upload Control")
        layout = QVBoxLayout(group)
        
        # Upload button
        self.upload_button = QPushButton("Upload Firmware")
        self.upload_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.upload_button.clicked.connect(self.start_upload)
        layout.addWidget(self.upload_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.upload_status_label = QLabel("Ready to upload")
        layout.addWidget(self.upload_status_label)
        
        return group
    
    def create_log_group(self) -> QGroupBox:
        """Create upload log group"""
        group = QGroupBox("Upload Log")
        layout = QVBoxLayout(group)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.log_text.setFont(font)
        layout.addWidget(self.log_text)
        
        # Clear log button
        clear_button = QPushButton("Clear Log")
        clear_button.clicked.connect(self.clear_log)
        layout.addWidget(clear_button)
        
        return group
    
    def setup_connections(self):
        """Setup signal connections"""
        pass  # Connections already set up in create methods
    
    def load_configuration(self, config: Dict[str, Any]):
        """Load configuration settings"""
        try:
            firmware_config = config.get("firmware", {})
            
            # Arduino CLI path
            cli_path = firmware_config.get("arduino_cli_path", "arduino-cli.exe")
            self.arduino_cli_path = cli_path
            self.cli_path_edit.setText(cli_path)
            
            # Board type
            board_type = firmware_config.get("board_type", "teensy:avr:teensy41")
            self.board_type = board_type
            if board_type in [self.board_combo.itemText(i) for i in range(self.board_combo.count())]:
                self.board_combo.setCurrentText(board_type)
            
            # Firmware path
            firmware_path = firmware_config.get("firmware_path", "")
            if firmware_path and os.path.exists(firmware_path):
                self.firmware_path = firmware_path
                self.firmware_path_edit.setText(firmware_path)
                self.use_default_checkbox.setChecked(False)
            else:
                self.set_default_firmware_path()
            
            # Refresh ports
            self.refresh_ports()
            
        except Exception as e:
            print(f"Error loading firmware tab configuration: {e}")
    
    def set_default_firmware_path(self):
        """Set default firmware path"""
        try:
            # Relative to the python_gui directory
            current_dir = Path(__file__).parent.parent.parent
            default_path = current_dir.parent / "firmware" / "firmware.ino"
            
            if default_path.exists():
                self.firmware_path = str(default_path)
                self.firmware_path_edit.setText(str(default_path))
                self.add_log_message(f"Using default firmware: {default_path}")
            else:
                self.add_log_message(f"Warning: Default firmware not found at {default_path}")
                
        except Exception as e:
            self.add_log_message(f"Error setting default firmware path: {e}")
    
    def refresh_ports(self):
        """Refresh available COM ports"""
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            
            current_selection = self.port_combo.currentText()
            self.port_combo.clear()
            
            port_names = [port.device for port in ports]
            self.port_combo.addItems(port_names)
            
            # Restore selection if possible
            if current_selection in port_names:
                self.port_combo.setCurrentText(current_selection)
            
            self.add_log_message(f"Found {len(port_names)} COM ports: {', '.join(port_names)}")
            
        except Exception as e:
            self.add_log_message(f"Error refreshing ports: {e}")
    
    def add_log_message(self, message: str):
        """Add message to upload log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    # Event handlers
    @Slot(str)
    def on_cli_path_changed(self, path: str):
        """Handle Arduino CLI path change"""
        self.arduino_cli_path = path
        self.cli_status_label.setText("Not tested")
        self.cli_status_label.setStyleSheet("color: gray;")
    
    @Slot(str)
    def on_board_changed(self, board_type: str):
        """Handle board type change"""
        self.board_type = board_type
    
    @Slot(bool)
    def on_use_default_toggled(self, checked: bool):
        """Handle use default firmware toggle"""
        if checked:
            self.set_default_firmware_path()
            self.browse_firmware_button.setEnabled(False)
        else:
            self.browse_firmware_button.setEnabled(True)
    
    @Slot()
    def browse_arduino_cli(self):
        """Browse for Arduino CLI executable"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Arduino CLI Executable",
            "", "Executable Files (*.exe);;All Files (*)"
        )
        
        if filename:
            self.arduino_cli_path = filename
            self.cli_path_edit.setText(filename)
            self.add_log_message(f"Arduino CLI path set to: {filename}")
    
    @Slot()
    def browse_firmware(self):
        """Browse for firmware file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Firmware File",
            "", "Arduino Sketches (*.ino);;All Files (*)"
        )
        
        if filename:
            self.firmware_path = filename
            self.firmware_path_edit.setText(filename)
            self.firmware_path_changed.emit(filename)
            self.add_log_message(f"Firmware path set to: {filename}")
    
    @Slot()
    def test_arduino_cli(self):
        """Test Arduino CLI installation"""
        try:
            result = subprocess.run([self.arduino_cli_path, "version"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.cli_status_label.setText("Arduino CLI OK")
                self.cli_status_label.setStyleSheet("color: green; font-weight: bold;")
                self.add_log_message(f"Arduino CLI test successful: {result.stdout.strip()}")
            else:
                self.cli_status_label.setText("Arduino CLI Error")
                self.cli_status_label.setStyleSheet("color: red; font-weight: bold;")
                self.add_log_message(f"Arduino CLI test failed: {result.stderr}")
                
        except FileNotFoundError:
            self.cli_status_label.setText("Arduino CLI Not Found")
            self.cli_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.add_log_message("Arduino CLI executable not found")
        except Exception as e:
            self.cli_status_label.setText("Test Failed")
            self.cli_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.add_log_message(f"Arduino CLI test error: {e}")
    
    @Slot()
    def start_upload(self):
        """Start firmware upload process"""
        # Validation
        if not self.firmware_path or not os.path.exists(self.firmware_path):
            QMessageBox.warning(self, "Upload Error", "Please select a valid firmware file.")
            return
        
        if not self.port_combo.currentText():
            QMessageBox.warning(self, "Upload Error", "Please select a COM port.")
            return
        
        if self.is_uploading:
            QMessageBox.information(self, "Upload", "Upload already in progress.")
            return
        
        # Confirm upload
        reply = QMessageBox.question(
            self, "Confirm Upload",
            f"Upload firmware to {self.port_combo.currentText()}?\n\n"
            f"Firmware: {Path(self.firmware_path).name}\n"
            f"Board: {self.board_type}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Start upload worker
        self.upload_worker = FirmwareUploadWorker(
            self.arduino_cli_path,
            self.firmware_path,
            self.port_combo.currentText(),
            self.board_type
        )
        
        self.upload_worker.upload_started.connect(self.on_upload_started)
        self.upload_worker.upload_progress.connect(self.on_upload_progress)
        self.upload_worker.upload_completed.connect(self.on_upload_completed)
        
        self.upload_worker.start()
    
    @Slot()
    def on_upload_started(self):
        """Handle upload start"""
        self.is_uploading = True
        self.upload_button.setEnabled(False)
        self.upload_button.setText("Uploading...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.upload_status_label.setText("Upload in progress...")
        self.add_log_message("Starting firmware upload...")
    
    @Slot(str)
    def on_upload_progress(self, message: str):
        """Handle upload progress update"""
        self.upload_status_label.setText(message)
        self.add_log_message(message)
    
    @Slot(bool, str)
    def on_upload_completed(self, success: bool, message: str):
        """Handle upload completion"""
        self.is_uploading = False
        self.upload_button.setEnabled(True)
        self.upload_button.setText("Upload Firmware")
        self.progress_bar.setVisible(False)
        
        if success:
            self.upload_status_label.setText("Upload successful!")
            self.upload_status_label.setStyleSheet("color: green; font-weight: bold;")
            QMessageBox.information(self, "Upload Complete", message)
        else:
            self.upload_status_label.setText("Upload failed!")
            self.upload_status_label.setStyleSheet("color: red; font-weight: bold;")
            QMessageBox.critical(self, "Upload Failed", message)
        
        self.add_log_message(message)
        
        # Clean up worker
        if self.upload_worker:
            self.upload_worker.deleteLater()
            self.upload_worker = None
    
    @Slot()
    def clear_log(self):
        """Clear the upload log"""
        self.log_text.clear()
        self.add_log_message("Log cleared")