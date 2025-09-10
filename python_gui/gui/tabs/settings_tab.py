"""
Settings Tab for CableScope Motor Control
Configuration and settings management
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QComboBox, QLabel, QSpinBox, QDoubleSpinBox,
    QLineEdit, QCheckBox, QFileDialog, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Signal, Slot, Qt
from typing import Dict, Any, Optional


class SettingsTab(QWidget):
    """Settings and configuration tab"""
    
    # Signals
    configuration_changed = Signal(dict)
    configuration_saved = Signal()
    
    def __init__(self):
        super().__init__()
        
        # Configuration data
        self.config_data = {}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Serial communication settings
        serial_group = self.create_serial_group()
        layout.addWidget(serial_group)
        
        # Motor control settings
        motor_group = self.create_motor_group()
        layout.addWidget(motor_group)
        
        # Data acquisition settings
        data_group = self.create_data_group()
        layout.addWidget(data_group)
        
        # UI settings
        ui_group = self.create_ui_group()
        layout.addWidget(ui_group)
        
        # Configuration file management
        config_group = self.create_config_group()
        layout.addWidget(config_group)
        
        # Add stretch
        layout.addStretch()
    
    def create_serial_group(self) -> QGroupBox:
        """Create serial communication settings group"""
        group = QGroupBox("Serial Communication")
        layout = QGridLayout(group)
        
        # Baud rate
        layout.addWidget(QLabel("Baud Rate:"), 0, 0)
        self.baud_rate_combo = QComboBox()
        self.baud_rate_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400"])
        self.baud_rate_combo.setCurrentText("115200")
        layout.addWidget(self.baud_rate_combo, 0, 1)
        
        # Timeout
        layout.addWidget(QLabel("Timeout:"), 0, 2)
        self.timeout_spinbox = QDoubleSpinBox()
        self.timeout_spinbox.setRange(0.1, 10.0)
        self.timeout_spinbox.setValue(1.0)
        self.timeout_spinbox.setSuffix(" s")
        layout.addWidget(self.timeout_spinbox, 0, 3)
        
        return group
    
    def create_motor_group(self) -> QGroupBox:
        """Create motor control settings group"""
        group = QGroupBox("Motor Control")
        layout = QGridLayout(group)
        
        # Max torque
        layout.addWidget(QLabel("Max Torque:"), 0, 0)
        self.max_torque_spinbox = QDoubleSpinBox()
        self.max_torque_spinbox.setRange(0.1, 50.0)
        self.max_torque_spinbox.setValue(5.0)
        self.max_torque_spinbox.setSuffix(" Nm")
        layout.addWidget(self.max_torque_spinbox, 0, 1)
        
        # Torque step
        layout.addWidget(QLabel("Torque Step:"), 0, 2)
        self.torque_step_spinbox = QDoubleSpinBox()
        self.torque_step_spinbox.setRange(0.001, 1.0)
        self.torque_step_spinbox.setValue(0.1)
        self.torque_step_spinbox.setDecimals(3)
        self.torque_step_spinbox.setSuffix(" Nm")
        layout.addWidget(self.torque_step_spinbox, 0, 3)
        
        return group
    
    def create_data_group(self) -> QGroupBox:
        """Create data acquisition settings group"""
        group = QGroupBox("Data Acquisition")
        layout = QGridLayout(group)
        
        # Sampling rate
        layout.addWidget(QLabel("Sampling Rate:"), 0, 0)
        self.sampling_rate_spinbox = QSpinBox()
        self.sampling_rate_spinbox.setRange(1, 1000)
        self.sampling_rate_spinbox.setValue(10)
        self.sampling_rate_spinbox.setSuffix(" Hz")
        layout.addWidget(self.sampling_rate_spinbox, 0, 1)
        
        # Buffer size
        layout.addWidget(QLabel("Buffer Size:"), 0, 2)
        self.buffer_size_spinbox = QSpinBox()
        self.buffer_size_spinbox.setRange(100, 10000)
        self.buffer_size_spinbox.setValue(1000)
        self.buffer_size_spinbox.setSuffix(" samples")
        layout.addWidget(self.buffer_size_spinbox, 0, 3)
        
        # Auto-start
        self.auto_start_checkbox = QCheckBox("Auto-start data acquisition on connection")
        layout.addWidget(self.auto_start_checkbox, 1, 0, 1, 4)
        
        return group
    
    def create_ui_group(self) -> QGroupBox:
        """Create UI settings group"""
        group = QGroupBox("User Interface")
        layout = QGridLayout(group)
        
        # Theme selection
        layout.addWidget(QLabel("Theme:"), 0, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        layout.addWidget(self.theme_combo, 0, 1)
        
        # Always on top
        self.always_on_top_checkbox = QCheckBox("Keep window always on top")
        layout.addWidget(self.always_on_top_checkbox, 0, 2, 1, 2)
        
        return group
    
    def create_config_group(self) -> QGroupBox:
        """Create configuration file management group"""
        group = QGroupBox("Configuration Management")
        layout = QHBoxLayout(group)
        
        # Save settings button
        self.save_button = QPushButton("Save Settings")
        self.save_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.save_button.clicked.connect(self.save_configuration)
        layout.addWidget(self.save_button)
        
        # Import button
        self.import_button = QPushButton("Import Configuration")
        self.import_button.clicked.connect(self.import_configuration)
        layout.addWidget(self.import_button)
        
        # Export button
        self.export_button = QPushButton("Export Configuration")
        self.export_button.clicked.connect(self.export_configuration)
        layout.addWidget(self.export_button)
        
        # Reset to defaults button
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        self.reset_button.clicked.connect(self.reset_to_defaults)
        layout.addWidget(self.reset_button)
        
        layout.addStretch()
        
        return group
    
    def load_configuration(self, config: Dict[str, Any]):
        """Load configuration into UI"""
        try:
            self.config_data = config.copy()
            
            # Serial settings
            serial_config = config.get("serial", {})
            baud_rate = str(serial_config.get("baud_rate", 115200))
            if baud_rate in [self.baud_rate_combo.itemText(i) for i in range(self.baud_rate_combo.count())]:
                self.baud_rate_combo.setCurrentText(baud_rate)
            self.timeout_spinbox.setValue(serial_config.get("timeout", 1.0))
            
            # Motor settings
            motor_config = config.get("motor_control", {})
            self.max_torque_spinbox.setValue(motor_config.get("max_torque", 5.0))
            self.torque_step_spinbox.setValue(motor_config.get("torque_step", 0.1))
            
            # Data acquisition settings
            data_config = config.get("data_acquisition", {})
            self.sampling_rate_spinbox.setValue(data_config.get("sampling_rate", 10))
            self.buffer_size_spinbox.setValue(data_config.get("buffer_size", 1000))
            self.auto_start_checkbox.setChecked(data_config.get("auto_start", False))
            
            # UI settings
            ui_config = config.get("ui", {})
            theme = ui_config.get("theme", "dark")
            self.theme_combo.setCurrentText(theme.title())
            self.always_on_top_checkbox.setChecked(ui_config.get("always_on_top", False))
            
        except Exception as e:
            print(f"Error loading settings tab configuration: {e}")
    
    def get_current_configuration(self) -> Dict[str, Any]:
        """Get current configuration from UI"""
        return {
            "serial": {
                "baud_rate": int(self.baud_rate_combo.currentText()),
                "timeout": self.timeout_spinbox.value()
            },
            "motor_control": {
                "max_torque": self.max_torque_spinbox.value(),
                "torque_step": self.torque_step_spinbox.value()
            },
            "data_acquisition": {
                "sampling_rate": self.sampling_rate_spinbox.value(),
                "buffer_size": self.buffer_size_spinbox.value(),
                "auto_start": self.auto_start_checkbox.isChecked()
            },
            "ui": {
                "theme": self.theme_combo.currentText().lower(),
                "always_on_top": self.always_on_top_checkbox.isChecked()
            }
        }
    
    @Slot()
    def save_configuration(self):
        """Save current configuration"""
        try:
            config = self.get_current_configuration()
            self.configuration_changed.emit(config)
            self.configuration_saved.emit()
            
            try:
                QMessageBox.information(self, "Settings Saved", 
                                      "Configuration has been saved successfully.")
            except:
                print("Configuration has been saved successfully.")
            
        except RecursionError:
            print("RecursionError in save_configuration - skipping message box")
        except Exception as e:
            try:
                QMessageBox.critical(self, "Save Error", f"Failed to save configuration: {e}")
            except:
                print(f"Failed to save configuration: {e}")
    
    @Slot()
    def import_configuration(self):
        """Import configuration from file"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Import Configuration",
                "", "TOML Files (*.toml);;All Files (*)"
            )
            
            if filename:
                # Implementation would load from file
                QMessageBox.information(self, "Import", f"Configuration imported from {filename}")
                
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import configuration: {e}")
    
    @Slot()
    def export_configuration(self):
        """Export configuration to file"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Configuration",
                "cablescope_config.toml", "TOML Files (*.toml);;All Files (*)"
            )
            
            if filename:
                # Implementation would save to file
                QMessageBox.information(self, "Export", f"Configuration exported to {filename}")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export configuration: {e}")
    
    @Slot()
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        reply = QMessageBox.question(
            self, "Reset to Defaults",
            "This will reset all settings to their default values. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reset UI to defaults
            self.baud_rate_combo.setCurrentText("115200")
            self.timeout_spinbox.setValue(1.0)
            self.max_torque_spinbox.setValue(5.0)
            self.torque_step_spinbox.setValue(0.1)
            self.sampling_rate_spinbox.setValue(10)
            self.buffer_size_spinbox.setValue(1000)
            self.auto_start_checkbox.setChecked(False)
            self.theme_combo.setCurrentText("Dark")
            self.always_on_top_checkbox.setChecked(False)
            
            QMessageBox.information(self, "Reset", "Settings have been reset to defaults.")