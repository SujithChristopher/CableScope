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
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

# Import Arduino CLI manager
from core.arduino_cli_manager import ArduinoCliManager
from core.firmware_resources import get_firmware_content, create_firmware_files


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
            
            # First, install required platforms and libraries
            if not self._install_dependencies():
                return
            
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
    
    def _install_dependencies(self) -> bool:
        """Install required platforms and libraries for the selected board"""
        try:
            # Determine required platform based on board type
            if self.board_type.startswith("teensy:avr:"):
                return self._install_teensy_platform()
            elif self.board_type.startswith("arduino:avr:"):
                # Arduino AVR platform is usually pre-installed
                return True
            else:
                self.upload_progress.emit(f"Unknown platform for board: {self.board_type}")
                return True  # Continue anyway
                
        except Exception as e:
            self.upload_completed.emit(False, f"Platform installation error: {str(e)}")
            return False
    
    def _install_teensy_platform(self) -> bool:
        """Install Teensy platform and required tools"""
        try:
            self.upload_progress.emit("Installing Teensy platform (first time setup)...")
            
            # Update package index first
            update_cmd = [self.arduino_cli_path, "core", "update-index"]
            update_result = subprocess.run(
                update_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if update_result.returncode != 0:
                print(f"Warning: Core update failed: {update_result.stderr}")
            
            # Add Teensy board manager URL
            config_cmd = [
                self.arduino_cli_path, "config", "add", "board_manager.additional_urls",
                "https://www.pjrc.com/teensy/package_teensy_index.json"
            ]
            config_result = subprocess.run(
                config_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if config_result.returncode != 0:
                print(f"Warning: Config update failed: {config_result.stderr}")
                # Try alternative approach - this might already be configured
            
            # Update index again with new URL
            update_cmd2 = [self.arduino_cli_path, "core", "update-index"]
            update_result2 = subprocess.run(
                update_cmd2,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if update_result2.returncode != 0:
                print(f"Warning: Second core update failed: {update_result2.stderr}")
            
            # Install Teensy platform
            self.upload_progress.emit("Downloading Teensy platform...")
            install_cmd = [self.arduino_cli_path, "core", "install", "teensy:avr"]
            install_result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout for download
            )
            
            if install_result.returncode == 0:
                self.upload_progress.emit("Teensy platform installed successfully")
            else:
                # Try to continue anyway - platform might already be installed
                print(f"Platform install result: {install_result.stderr}")
                if "already installed" in install_result.stderr.lower():
                    self.upload_progress.emit("Teensy platform already installed")
                else:
                    self.upload_completed.emit(False, f"Failed to install Teensy platform: {install_result.stderr}")
                    return False
            
            # Install required libraries
            return self._install_required_libraries()
                    
        except subprocess.TimeoutExpired:
            self.upload_completed.emit(False, "Platform installation timed out")
            return False
        except Exception as e:
            self.upload_completed.emit(False, f"Platform installation error: {str(e)}")
            return False
    
    def _install_required_libraries(self) -> bool:
        """Install required libraries for the firmware"""
        try:
            required_libraries = [
                "HX711 ADC",  # For HX711 load cell amplifier
                "Encoder"     # For rotary encoder support
            ]
            
            for library_name in required_libraries:
                self.upload_progress.emit(f"Installing library: {library_name}")
                
                lib_cmd = [self.arduino_cli_path, "lib", "install", library_name]
                lib_result = subprocess.run(
                    lib_cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if lib_result.returncode == 0:
                    self.upload_progress.emit(f"Library '{library_name}' installed successfully")
                else:
                    # Check if already installed
                    if "already installed" in lib_result.stderr.lower() or "already up-to-date" in lib_result.stderr.lower():
                        self.upload_progress.emit(f"Library '{library_name}' already installed")
                    else:
                        print(f"Warning: Failed to install library '{library_name}': {lib_result.stderr}")
                        # Continue anyway - library might be available in a different form
            
            self.upload_progress.emit("Library installation completed")
            return True
            
        except subprocess.TimeoutExpired:
            self.upload_completed.emit(False, "Library installation timed out")
            return False
        except Exception as e:
            self.upload_completed.emit(False, f"Library installation error: {str(e)}")
            return False


class FirmwareTab(QWidget):
    """Firmware upload and management tab"""
    
    # Signals
    firmware_upload_requested = Signal(str, str)  # firmware_path, board_type
    firmware_path_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.arduino_cli_path = ""  # Will be set by manager
        self.firmware_path = ""
        self.selected_port = ""
        self.board_type = "teensy:avr:teensy41"
        
        # Upload worker
        self.upload_worker = None
        self.is_uploading = False
        
        # Temporary firmware management
        self.temp_firmware_dir = None
        self.use_embedded_firmware = True
        
        # Arduino CLI manager
        self.cli_manager = ArduinoCliManager()
        self.cli_manager.installation_complete.connect(self.on_cli_installation_complete)
        self.cli_manager.installation_failed.connect(self.on_cli_installation_failed)
        
        self.setup_ui()
        self.setup_connections()
        
        # Check for Arduino CLI after UI setup
        self.check_arduino_cli()
    
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
        
        # Download button
        self.download_cli_button = QPushButton("Download CLI")
        self.download_cli_button.clicked.connect(self.download_arduino_cli)
        layout.addWidget(self.download_cli_button, 0, 3)
        
        # Test CLI button
        self.test_cli_button = QPushButton("Test CLI")
        self.test_cli_button.clicked.connect(self.test_arduino_cli)
        layout.addWidget(self.test_cli_button, 0, 4)
        
        # CLI status
        layout.addWidget(QLabel("Status:"), 1, 0)
        self.cli_status_label = QLabel("Checking...")
        self.cli_status_label.setStyleSheet("color: orange;")
        layout.addWidget(self.cli_status_label, 1, 1, 1, 4)
        
        # Download progress bar
        self.cli_download_progress = QProgressBar()
        self.cli_download_progress.setVisible(False)
        layout.addWidget(self.cli_download_progress, 2, 0, 1, 5)
        
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
        
        # Use embedded firmware checkbox
        self.use_default_checkbox = QCheckBox("Use embedded firmware (recommended)")
        self.use_default_checkbox.setChecked(True)
        self.use_default_checkbox.toggled.connect(self.on_use_default_toggled)
        layout.addWidget(self.use_default_checkbox, 1, 0, 1, 3)
        
        # Info label about automatic setup
        info_label = QLabel("Note: First upload will automatically install Teensy platform and required libraries")
        info_label.setStyleSheet("color: #666666; font-style: italic; font-size: 9px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label, 2, 0, 1, 3)
        
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
            use_embedded = firmware_config.get("use_embedded_firmware", True)
            
            if use_embedded or not firmware_path or not os.path.exists(firmware_path):
                # Use embedded firmware (default)
                self.set_default_firmware_path()
            else:
                # Use external firmware file
                self.firmware_path = firmware_path
                self.firmware_path_edit.setText(firmware_path)
                self.use_default_checkbox.setChecked(False)
                self.use_embedded_firmware = False
            
            # Refresh ports
            self.refresh_ports()
            
        except Exception as e:
            print(f"Error loading firmware tab configuration: {e}")
    
    def save_configuration(self) -> Dict[str, Any]:
        """Save current configuration settings"""
        return {
            "firmware": {
                "arduino_cli_path": self.arduino_cli_path,
                "board_type": self.board_type,
                "firmware_path": self.firmware_path if not self.use_embedded_firmware else "",
                "use_embedded_firmware": self.use_embedded_firmware
            }
        }
    
    def set_default_firmware_path(self):
        """Set default firmware path using embedded firmware"""
        try:
            self.use_embedded_firmware = True
            
            # Create temporary firmware directory with proper Arduino sketch name
            if not self.temp_firmware_dir:
                # Use a consistent directory name for Arduino CLI compatibility
                temp_base = tempfile.mkdtemp(prefix="cablescope_temp_")
                self.temp_firmware_dir = os.path.join(temp_base, "cablescope_firmware")
            
            # Create firmware files from embedded resources
            created_files = create_firmware_files(self.temp_firmware_dir)
            
            # Set path to the main firmware.ino file
            self.firmware_path = created_files["firmware.ino"]
            self.firmware_path_edit.setText("[Embedded Firmware]")
            self.add_log_message(f"Using embedded firmware (extracted to temporary location)")
            
        except Exception as e:
            self.add_log_message(f"Error setting up embedded firmware: {e}")
            # Fallback: try to use external firmware if it exists
            try:
                current_dir = Path(__file__).parent.parent.parent
                fallback_path = current_dir.parent / "firmware" / "firmware.ino"
                
                if fallback_path.exists():
                    self.firmware_path = str(fallback_path)
                    self.firmware_path_edit.setText(str(fallback_path))
                    self.use_embedded_firmware = False
                    self.add_log_message(f"Fallback: Using external firmware: {fallback_path}")
                else:
                    self.add_log_message(f"Error: No firmware available (embedded failed, external not found)")
                    
            except Exception as fallback_error:
                self.add_log_message(f"Error: Firmware setup failed completely: {fallback_error}")
    
    def refresh_ports(self):
        """Refresh available COM ports"""
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            
            current_selection = self.port_combo.currentText()
            self.port_combo.clear()
            
            port_names = [port.device for port in ports]
            self.port_combo.addItems(port_names)
            
            # Auto-select Teensy port if no current selection or if current selection not available
            if not current_selection or current_selection not in port_names:
                teensy_port = self.find_teensy_port(ports)
                if teensy_port:
                    self.port_combo.setCurrentText(teensy_port)
                    print(f"DEBUG: Auto-selected Teensy port in firmware tab: {teensy_port}")
                elif port_names:
                    # Fallback: select first available port
                    self.port_combo.setCurrentText(port_names[0])
                    print(f"DEBUG: No Teensy found in firmware tab, selected first port: {port_names[0]}")
            elif current_selection in port_names:
                # Restore previous selection if still available
                self.port_combo.setCurrentText(current_selection)
                print(f"DEBUG: Restored firmware port selection: {current_selection}")
            
            self.add_log_message(f"Found {len(port_names)} COM ports: {', '.join(port_names)}")
            
        except Exception as e:
            self.add_log_message(f"Error refreshing ports: {e}")
    
    def find_teensy_port(self, ports):
        """Find the Teensy port from available ports"""
        try:
            for port in ports:
                # Check for Teensy VID:PID (16C0:0483 or other Teensy IDs)
                hwid = port.hwid.upper()
                if any(teensy_id in hwid for teensy_id in [
                    '16C0:0483',  # Teensy 4.x
                    '16C0:0476',  # Teensy 3.x
                    '16C0:0478',  # Teensy LC
                    'USB VID:PID=16C0'  # Any Teensy
                ]):
                    print(f"DEBUG: Found Teensy in firmware tab on {port.device}: {port.description}")
                    return port.device
                    
                # Also check for "USB Serial Device" description as fallback
                if 'USB SERIAL DEVICE' in port.description.upper() and '16C0' in hwid:
                    print(f"DEBUG: Found USB Serial Device (likely Teensy) in firmware tab on {port.device}")
                    return port.device
                    
        except Exception as e:
            print(f"DEBUG: Error finding Teensy port in firmware tab: {e}")
            
        return None
    
    def add_log_message(self, message: str):
        """Add message to upload log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def save_cli_path_to_config(self):
        """Save Arduino CLI path to configuration immediately"""
        try:
            # We need to emit a signal to the main window to save config
            # For now, we'll use a simple approach by accessing parent
            main_window = self.window()
            if hasattr(main_window, 'config_manager'):
                config = main_window.config_manager.get_full_config()
                if 'firmware' not in config:
                    config['firmware'] = {}
                config['firmware']['arduino_cli_path'] = self.arduino_cli_path
                main_window.config_manager.save_config(config)
        except Exception as e:
            print(f"Error saving CLI path to config: {e}")
    
    # Event handlers
    @Slot(str)
    def on_cli_path_changed(self, path: str):
        """Handle Arduino CLI path change"""
        self.arduino_cli_path = path
        self.cli_status_label.setText("Not tested")
        self.cli_status_label.setStyleSheet("color: gray;")
        # Save configuration when CLI path changes
        self.save_cli_path_to_config()
    
    @Slot(str)
    def on_board_changed(self, board_type: str):
        """Handle board type change"""
        self.board_type = board_type
    
    @Slot(bool)
    def on_use_default_toggled(self, checked: bool):
        """Handle use embedded firmware toggle"""
        if checked:
            self.set_default_firmware_path()
            self.browse_firmware_button.setEnabled(False)
        else:
            self.browse_firmware_button.setEnabled(True)
            self.use_embedded_firmware = False
            # Clear current firmware path when switching to external
            if self.firmware_path_edit.text() == "[Embedded Firmware]":
                self.firmware_path_edit.setText("")
                self.firmware_path = ""
    
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
            self.use_embedded_firmware = False
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
                self.download_cli_button.setStyleSheet("")  # Remove any highlighting
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
        
        # Update UI state based on test results
        self.update_cli_ui_state()
    
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
        
        # For embedded firmware, use the directory path; for external firmware, use the file path
        if self.use_embedded_firmware:
            # Arduino CLI needs the sketch directory, not the .ino file
            upload_path = os.path.dirname(self.firmware_path)
        else:
            # For external firmware, Arduino CLI still needs the directory containing the .ino file
            upload_path = os.path.dirname(self.firmware_path)
        
        # Start upload worker
        self.upload_worker = FirmwareUploadWorker(
            self.arduino_cli_path,
            upload_path,
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
    
    # Arduino CLI Management Methods
    def check_arduino_cli(self):
        """Check for Arduino CLI installation"""
        cli_path = self.cli_manager.get_arduino_cli_path()
        
        if cli_path:
            # Arduino CLI found
            self.arduino_cli_path = cli_path
            self.cli_path_edit.setText(cli_path)
            self.test_arduino_cli()
        else:
            # Arduino CLI not found
            self.cli_status_label.setText("Arduino CLI not found - Click 'Download CLI' to install")
            self.cli_status_label.setStyleSheet("color: red;")
            self.download_cli_button.setStyleSheet("background-color: #4CAF50; font-weight: bold;")
    
    @Slot()
    def download_arduino_cli(self):
        """Download and install Arduino CLI"""
        self.download_cli_button.setEnabled(False)
        self.download_cli_button.setText("Downloading...")
        self.cli_download_progress.setVisible(True)
        self.cli_download_progress.setRange(0, 100)
        self.cli_status_label.setText("Downloading Arduino CLI...")
        self.cli_status_label.setStyleSheet("color: orange;")
        
        # Connect downloader signals
        if hasattr(self.cli_manager, 'downloader') and self.cli_manager.downloader:
            self.cli_manager.downloader.download_progress.connect(self.on_cli_download_progress)
            self.cli_manager.downloader.download_status.connect(self.on_cli_download_status)
        
        # Start download
        self.cli_manager.install_arduino_cli()
    
    @Slot(int)
    def on_cli_download_progress(self, progress: int):
        """Handle CLI download progress"""
        self.cli_download_progress.setValue(progress)
    
    @Slot(str)
    def on_cli_download_status(self, status: str):
        """Handle CLI download status"""
        self.cli_status_label.setText(status)
    
    @Slot(str)
    def on_cli_installation_complete(self, cli_path: str):
        """Handle successful CLI installation"""
        self.arduino_cli_path = cli_path
        self.cli_path_edit.setText(cli_path)
        
        # Save the CLI path to config immediately
        self.save_cli_path_to_config()
        
        self.download_cli_button.setEnabled(True)
        self.download_cli_button.setText("Download CLI")
        self.download_cli_button.setStyleSheet("")
        self.cli_download_progress.setVisible(False)
        
        self.cli_status_label.setText(f"Arduino CLI downloaded successfully!")
        self.cli_status_label.setStyleSheet("color: green; font-weight: bold;")
        
        # Test the newly installed CLI
        QTimer.singleShot(1000, self.test_arduino_cli)
    
    @Slot(str)
    def on_cli_installation_failed(self, error_message: str):
        """Handle failed CLI installation"""
        self.download_cli_button.setEnabled(True)
        self.download_cli_button.setText("Download CLI")
        self.download_cli_button.setStyleSheet("background-color: #f44336; font-weight: bold;")
        self.cli_download_progress.setVisible(False)
        
        self.cli_status_label.setText(f"Download failed: {error_message}")
        self.cli_status_label.setStyleSheet("color: red; font-weight: bold;")
        
        QMessageBox.critical(self, "Download Failed", 
                           f"Failed to download Arduino CLI:\n{error_message}\n\n"
                           "You can try again or manually install Arduino CLI.")
    
    def cleanup_temp_files(self):
        """Clean up temporary firmware files"""
        try:
            if self.temp_firmware_dir and Path(self.temp_firmware_dir).exists():
                shutil.rmtree(self.temp_firmware_dir, ignore_errors=True)
                self.add_log_message("Cleaned up temporary firmware files")
                self.temp_firmware_dir = None
        except Exception as e:
            print(f"Error cleaning up temporary firmware files: {e}")
    
    def closeEvent(self, event):
        """Handle tab close event"""
        self.cleanup_temp_files()
        super().closeEvent(event)
    
    def __del__(self):
        """Destructor to clean up resources"""
        self.cleanup_temp_files()
    
    def update_cli_ui_state(self):
        """Update CLI-related UI elements based on current state"""
        has_cli = bool(self.arduino_cli_path and Path(self.arduino_cli_path).exists())
        
        # Enable/disable upload functionality based on CLI availability
        self.upload_button.setEnabled(has_cli and not self.is_uploading)
        
        if not has_cli:
            self.upload_status_label.setText("Arduino CLI required for upload")
            self.upload_status_label.setStyleSheet("color: orange;")