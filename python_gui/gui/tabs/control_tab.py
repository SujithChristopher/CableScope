"""
Control Tab for CableScope Motor Control
Provides motor control interface and connection management
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QComboBox, QDoubleSpinBox, QLabel, QLineEdit,
    QSlider, QLCDNumber, QProgressBar, QCheckBox, QSpacerItem,
    QSizePolicy, QMessageBox
)
from PySide6.QtCore import Signal, Slot, Qt, QTimer
from PySide6.QtGui import QFont, QPalette
from typing import Dict, Any, List, Optional
import time


class ControlTab(QWidget):
    """Main control interface tab"""
    
    # Signals
    torque_command_requested = Signal(float)
    connection_requested = Signal(str)
    disconnection_requested = Signal()
    data_acquisition_start_requested = Signal()
    data_acquisition_stop_requested = Signal()
    emergency_stop_requested = Signal()
    
    def __init__(self):
        super().__init__()
        
        # State variables
        self.is_connected = False
        self.is_data_acquisition_active = False
        self.current_torque = 0.0
        self.current_angle = 0.0
        self.max_torque = 5.0
        self.torque_step = 0.1
        
        # Available ports
        self.available_ports = []
        
        self.setup_ui()
        self.setup_connections()
        self.update_ui_state()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Connection group
        connection_group = self.create_connection_group()
        layout.addWidget(connection_group)
        
        # Control group
        control_group = self.create_control_group()
        layout.addWidget(control_group)
        
        # Status group
        status_group = self.create_status_group()
        layout.addWidget(status_group)
        
        # Data acquisition group
        data_group = self.create_data_acquisition_group()
        layout.addWidget(data_group)
        
        # Emergency controls
        emergency_group = self.create_emergency_group()
        layout.addWidget(emergency_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def create_connection_group(self) -> QGroupBox:
        """Create connection management group"""
        group = QGroupBox("Connection")
        layout = QGridLayout(group)
        
        # Port selection
        layout.addWidget(QLabel("COM Port:"), 0, 0)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        layout.addWidget(self.port_combo, 0, 1)
        
        # Connection buttons
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.on_connect_clicked)
        layout.addWidget(self.connect_button, 0, 2)
        
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.on_disconnect_clicked)
        layout.addWidget(self.disconnect_button, 0, 3)
        
        # Connection status
        layout.addWidget(QLabel("Status:"), 1, 0)
        self.connection_status_label = QLabel("Disconnected")
        self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.connection_status_label, 1, 1, 1, 3)
        
        return group
    
    def create_control_group(self) -> QGroupBox:
        """Create motor control group"""
        group = QGroupBox("Motor Control")
        layout = QGridLayout(group)
        
        # Torque input methods
        layout.addWidget(QLabel("Desired Torque (Nm):"), 0, 0)
        
        # Spinbox for precise input
        self.torque_spinbox = QDoubleSpinBox()
        self.torque_spinbox.setRange(-self.max_torque, self.max_torque)
        self.torque_spinbox.setSingleStep(self.torque_step)
        self.torque_spinbox.setDecimals(3)
        self.torque_spinbox.setValue(0.0)
        self.torque_spinbox.setSuffix(" Nm")
        self.torque_spinbox.valueChanged.connect(self.on_torque_spinbox_changed)
        layout.addWidget(self.torque_spinbox, 0, 1)
        
        # Slider for quick adjustment
        self.torque_slider = QSlider(Qt.Orientation.Horizontal)
        self.torque_slider.setRange(int(-self.max_torque * 1000), int(self.max_torque * 1000))
        self.torque_slider.setValue(0)
        self.torque_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.torque_slider.setTickInterval(int(self.max_torque * 100))  # Every 0.5 Nm
        self.torque_slider.valueChanged.connect(self.on_torque_slider_changed)
        layout.addWidget(QLabel("Quick Adjust:"), 1, 0)
        layout.addWidget(self.torque_slider, 1, 1, 1, 3)
        
        # Preset buttons
        preset_layout = QHBoxLayout()
        preset_values = [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0]
        
        for value in preset_values:
            btn = QPushButton(f"{value:+.1f}")
            btn.setMaximumWidth(60)
            btn.clicked.connect(lambda checked, v=value: self.set_torque_value(v))
            preset_layout.addWidget(btn)
        
        layout.addWidget(QLabel("Presets:"), 2, 0)
        layout.addLayout(preset_layout, 2, 1, 1, 3)
        
        # Send command button
        self.send_torque_button = QPushButton("Send Torque Command")
        self.send_torque_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.send_torque_button.clicked.connect(self.on_send_torque_clicked)
        layout.addWidget(self.send_torque_button, 3, 0, 1, 4)
        
        # Max torque setting
        layout.addWidget(QLabel("Max Torque Limit:"), 4, 0)
        self.max_torque_spinbox = QDoubleSpinBox()
        self.max_torque_spinbox.setRange(0.1, 10.0)
        self.max_torque_spinbox.setValue(self.max_torque)
        self.max_torque_spinbox.setSuffix(" Nm")
        self.max_torque_spinbox.valueChanged.connect(self.on_max_torque_changed)
        layout.addWidget(self.max_torque_spinbox, 4, 1)
        
        return group
    
    def create_status_group(self) -> QGroupBox:
        """Create current status display group"""
        group = QGroupBox("Current Status")
        layout = QGridLayout(group)
        
        # Current torque display
        layout.addWidget(QLabel("Measured Torque:"), 0, 0)
        self.current_torque_lcd = QLCDNumber()
        self.current_torque_lcd.setDigitCount(6)
        self.current_torque_lcd.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.current_torque_lcd.display(0.000)
        layout.addWidget(self.current_torque_lcd, 0, 1)
        layout.addWidget(QLabel("Nm"), 0, 2)
        
        # Current angle display
        layout.addWidget(QLabel("Motor Angle:"), 1, 0)
        self.current_angle_lcd = QLCDNumber()
        self.current_angle_lcd.setDigitCount(7)
        self.current_angle_lcd.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.current_angle_lcd.display(0.00)
        layout.addWidget(self.current_angle_lcd, 1, 1)
        layout.addWidget(QLabel("°"), 1, 2)
        
        # Command status
        layout.addWidget(QLabel("Last Command:"), 2, 0)
        self.last_command_label = QLabel("None")
        layout.addWidget(self.last_command_label, 2, 1, 1, 2)
        
        # Data rate
        layout.addWidget(QLabel("Data Rate:"), 3, 0)
        self.data_rate_label = QLabel("0.0 Hz")
        layout.addWidget(self.data_rate_label, 3, 1, 1, 2)
        
        return group
    
    def create_data_acquisition_group(self) -> QGroupBox:
        """Create data acquisition control group"""
        group = QGroupBox("Data Acquisition")
        layout = QGridLayout(group)
        
        # Start/Stop buttons
        self.start_data_button = QPushButton("Start Data Acquisition")
        self.start_data_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.start_data_button.clicked.connect(self.on_start_data_clicked)
        layout.addWidget(self.start_data_button, 0, 0)
        
        self.stop_data_button = QPushButton("Stop Data Acquisition")
        self.stop_data_button.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        self.stop_data_button.clicked.connect(self.on_stop_data_clicked)
        layout.addWidget(self.stop_data_button, 0, 1)
        
        # Auto-start option
        self.auto_start_checkbox = QCheckBox("Auto-start on connection")
        layout.addWidget(self.auto_start_checkbox, 1, 0, 1, 2)
        
        # Data acquisition status
        layout.addWidget(QLabel("Status:"), 2, 0)
        self.data_status_label = QLabel("Stopped")
        self.data_status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.data_status_label, 2, 1)
        
        return group
    
    def create_emergency_group(self) -> QGroupBox:
        """Create emergency control group"""
        group = QGroupBox("Emergency Controls")
        layout = QHBoxLayout(group)
        
        # Emergency stop button
        self.emergency_stop_button = QPushButton("EMERGENCY STOP")
        self.emergency_stop_button.setStyleSheet(
            "background-color: #F44336; color: white; font-weight: bold; "
            "font-size: 16px; padding: 10px; border-radius: 5px;"
        )
        self.emergency_stop_button.clicked.connect(self.on_emergency_stop_clicked)
        layout.addWidget(self.emergency_stop_button)
        
        # Zero torque button
        self.zero_torque_button = QPushButton("Zero Torque")
        self.zero_torque_button.clicked.connect(self.on_zero_torque_clicked)
        layout.addWidget(self.zero_torque_button)
        
        return group
    
    def setup_connections(self):
        """Setup internal signal connections"""
        pass  # All connections are already set up in create methods
    
    def update_ui_state(self):
        """Update UI state based on current conditions"""
        # Connection-dependent controls
        self.send_torque_button.setEnabled(self.is_connected)
        self.torque_spinbox.setEnabled(self.is_connected)
        self.torque_slider.setEnabled(self.is_connected)
        self.start_data_button.setEnabled(self.is_connected and not self.is_data_acquisition_active)
        self.stop_data_button.setEnabled(self.is_connected and self.is_data_acquisition_active)
        
        # Connection button states
        self.connect_button.setEnabled(not self.is_connected and len(self.available_ports) > 0)
        self.disconnect_button.setEnabled(self.is_connected)
        
        # Emergency controls are always enabled when connected
        self.emergency_stop_button.setEnabled(self.is_connected)
        self.zero_torque_button.setEnabled(self.is_connected)
    
    # Configuration methods
    def load_configuration(self, config: Dict[str, Any]):
        """Load configuration settings"""
        try:
            # Load motor control settings
            motor_config = config.get("motor_control", {})
            self.max_torque = motor_config.get("max_torque", 5.0)
            self.torque_step = motor_config.get("torque_step", 0.1)
            
            # Update UI
            self.max_torque_spinbox.setValue(self.max_torque)
            self.torque_spinbox.setRange(-self.max_torque, self.max_torque)
            self.torque_spinbox.setSingleStep(self.torque_step)
            self.torque_slider.setRange(int(-self.max_torque * 1000), int(self.max_torque * 1000))
            
            # Load data acquisition settings
            data_config = config.get("data_acquisition", {})
            auto_start = data_config.get("auto_start", False)
            self.auto_start_checkbox.setChecked(auto_start)
            
        except Exception as e:
            print(f"Error loading control tab configuration: {e}")
    
    def save_configuration(self) -> Dict[str, Any]:
        """Save current configuration settings"""
        return {
            "motor_control": {
                "max_torque": self.max_torque,
                "torque_step": self.torque_step,
                "default_torque": self.torque_spinbox.value()
            },
            "data_acquisition": {
                "auto_start": self.auto_start_checkbox.isChecked()
            }
        }
    
    # Slot methods
    @Slot()
    def on_connect_clicked(self):
        """Handle connect button click"""
        selected_port = self.port_combo.currentText()
        if selected_port:
            self.connection_requested.emit(selected_port)
    
    @Slot()
    def on_disconnect_clicked(self):
        """Handle disconnect button click"""
        self.disconnection_requested.emit()
    
    @Slot(float)
    def on_torque_spinbox_changed(self, value: float):
        """Handle torque spinbox value change"""
        # Update slider to match
        self.torque_slider.blockSignals(True)
        self.torque_slider.setValue(int(value * 1000))
        self.torque_slider.blockSignals(False)
    
    @Slot(int)
    def on_torque_slider_changed(self, value: int):
        """Handle torque slider value change"""
        torque_value = value / 1000.0
        # Update spinbox to match
        self.torque_spinbox.blockSignals(True)
        self.torque_spinbox.setValue(torque_value)
        self.torque_spinbox.blockSignals(False)
    
    @Slot()
    def on_send_torque_clicked(self):
        """Handle send torque button click"""
        torque_value = self.torque_spinbox.value()
        self.torque_command_requested.emit(torque_value)
        self.last_command_label.setText(f"{torque_value:.3f} Nm at {time.strftime('%H:%M:%S')}")
    
    @Slot(float)
    def on_max_torque_changed(self, value: float):
        """Handle max torque limit change"""
        self.max_torque = value
        
        # Update ranges
        self.torque_spinbox.setRange(-value, value)
        self.torque_slider.setRange(int(-value * 1000), int(value * 1000))
        
        # Clamp current value if necessary
        current_value = self.torque_spinbox.value()
        if abs(current_value) > value:
            self.set_torque_value(0.0)
    
    @Slot()
    def on_start_data_clicked(self):
        """Handle start data acquisition button click"""
        self.data_acquisition_start_requested.emit()
    
    @Slot()
    def on_stop_data_clicked(self):
        """Handle stop data acquisition button click"""
        self.data_acquisition_stop_requested.emit()
    
    @Slot()
    def on_emergency_stop_clicked(self):
        """Handle emergency stop button click"""
        reply = QMessageBox.question(
            self, "Emergency Stop",
            "This will immediately set motor torque to zero and stop data acquisition.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.emergency_stop_requested.emit()
    
    @Slot()
    def on_zero_torque_clicked(self):
        """Handle zero torque button click"""
        self.set_torque_value(0.0)
        self.torque_command_requested.emit(0.0)
    
    # Public methods for external control
    def set_torque_value(self, torque: float):
        """Set the torque value in both spinbox and slider"""
        torque = max(-self.max_torque, min(self.max_torque, torque))
        
        self.torque_spinbox.blockSignals(True)
        self.torque_slider.blockSignals(True)
        
        self.torque_spinbox.setValue(torque)
        self.torque_slider.setValue(int(torque * 1000))
        
        self.torque_spinbox.blockSignals(False)
        self.torque_slider.blockSignals(False)
    
    def set_connection_status(self, connected: bool):
        """Set connection status"""
        self.is_connected = connected
        
        if connected:
            self.connection_status_label.setText("Connected")
            self.connection_status_label.setStyleSheet("color: green; font-weight: bold;")
            
            # Auto-start data acquisition if enabled
            if self.auto_start_checkbox.isChecked():
                QTimer.singleShot(1000, self.data_acquisition_start_requested.emit)  # Delay 1 second
        else:
            self.connection_status_label.setText("Disconnected")
            self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
        
        self.update_ui_state()
    
    def set_data_acquisition_active(self, active: bool):
        """Set data acquisition status"""
        self.is_data_acquisition_active = active
        
        if active:
            self.data_status_label.setText("Running")
            self.data_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.data_status_label.setText("Stopped")
            self.data_status_label.setStyleSheet("color: red; font-weight: bold;")
        
        self.update_ui_state()
    
    def update_available_ports(self, ports: List[str]):
        """Update available COM ports"""
        self.available_ports = ports
        
        # Save current selection
        current_selection = self.port_combo.currentText()
        
        # Update combo box
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        
        # Restore selection if possible
        if current_selection in ports:
            self.port_combo.setCurrentText(current_selection)
        
        self.update_ui_state()
    
    def update_current_values(self, data: Dict[str, float]):
        """Update current torque and angle displays"""
        if "torque" in data:
            self.current_torque = data["torque"]
            self.current_torque_lcd.display(f"{self.current_torque:.3f}")
        
        if "angle" in data:
            self.current_angle = data["angle"]
            self.current_angle_lcd.display(f"{self.current_angle:.2f}")
    
    def update_data_rate(self, rate: float):
        """Update data reception rate display"""
        self.data_rate_label.setText(f"{rate:.1f} Hz")
    
    def reset_controls(self):
        """Reset all controls to default state"""
        self.set_torque_value(0.0)
        self.last_command_label.setText("None")
        self.current_torque_lcd.display(0.000)
        self.current_angle_lcd.display(0.00)
        self.data_rate_label.setText("0.0 Hz")
    
    def emergency_stop(self):
        """Emergency stop - reset torque to zero"""
        self.set_torque_value(0.0)
        self.last_command_label.setText("EMERGENCY STOP - 0.000 Nm")