"""
Control & Plots Tab for CableScope Motor Control
Merged interface combining motor control and real-time plotting
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QComboBox, QDoubleSpinBox, QLabel, QLineEdit,
    QSlider, QLCDNumber, QProgressBar, QCheckBox, QSpacerItem,
    QSizePolicy, QMessageBox, QSplitter, QSpinBox, QFileDialog
)
from PySide6.QtCore import Signal, Slot, Qt, QTimer
from PySide6.QtGui import QFont, QPalette
import pyqtgraph as pg
import numpy as np
from typing import Dict, Any, List, Optional
import time
from datetime import datetime
import csv
from pathlib import Path


class ControlPlotsTab(QWidget):
    """Merged control and plotting interface tab"""
    
    # Signals
    torque_command_requested = Signal(float)
    connection_requested = Signal(str)
    disconnection_requested = Signal()
    data_acquisition_start_requested = Signal()
    data_acquisition_stop_requested = Signal()
    emergency_stop_requested = Signal()
    plot_settings_changed = Signal(dict)
    recording_start_requested = Signal(str)
    recording_stop_requested = Signal()
    refresh_ports_requested = Signal()
    
    def __init__(self):
        super().__init__()
        
        # Control state variables
        self.is_connected = False
        self.is_data_acquisition_active = False
        self.current_torque = 0.0
        self.current_angle = 0.0
        self.max_torque = 5.0
        self.torque_step = 0.1
        self.available_ports = []
        
        # Plot configuration
        self.time_window = 10.0
        self.update_rate = 50
        self.buffer_size = 1000
        
        # Data storage
        self.data_buffer = {"torque": [], "angle": [], "time": []}
        self.plot_data = {"torque": {"x": [], "y": []}, "angle": {"x": [], "y": []}}
        
        # Recording state
        self.is_recording = False
        self.recording_file = None
        self.recording_writer = None
        self.recording_start_time = None
        
        # Plot styling
        self.plot_colors = {
            "torque": "#2563eb",  # Blue
            "angle": "#dc2626"    # Red
        }
        
        self.setup_ui()
        self.setup_plots()
        self.setup_connections()
        self.update_ui_state()
        
        # Setup update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plots)
        self.update_timer.start(self.update_rate)
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create main splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)
        
        # Left panel - Controls
        control_panel = self.create_control_panel()
        main_splitter.addWidget(control_panel)
        
        # Right panel - Plots
        plot_panel = self.create_plot_panel()
        main_splitter.addWidget(plot_panel)
        
        # Set splitter sizes (control panel: 400px, plots: rest)
        main_splitter.setSizes([400, 600])
    
    def create_control_panel(self) -> QWidget:
        """Create the control panel with all motor control functionality"""
        panel = QWidget()
        panel.setMaximumWidth(400)
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Connection group
        connection_group = self.create_connection_group()
        layout.addWidget(connection_group)
        
        # Motor control group
        control_group = self.create_control_group()
        layout.addWidget(control_group)
        
        # Status group
        status_group = self.create_status_group()
        layout.addWidget(status_group)
        
        # Data acquisition group
        data_group = self.create_data_acquisition_group()
        layout.addWidget(data_group)
        
        # Recording group
        recording_group = self.create_recording_group()
        layout.addWidget(recording_group)
        
        # Emergency controls
        emergency_group = self.create_emergency_group()
        layout.addWidget(emergency_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        return panel
    
    def create_plot_panel(self) -> QWidget:
        """Create the plot panel with controls and plots"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Plot controls (minimal)
        plot_controls = self.create_plot_controls()
        layout.addWidget(plot_controls)
        
        # Plot area
        plot_area = self.create_plot_area()
        layout.addWidget(plot_area, 1)  # Give plots most of the space
        
        return panel
    
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
        
        # Refresh ports button
        self.refresh_ports_button = QPushButton("Refresh")
        self.refresh_ports_button.clicked.connect(self.on_refresh_ports_clicked)
        layout.addWidget(self.refresh_ports_button, 1, 2)
        
        # Connection status
        layout.addWidget(QLabel("Status:"), 1, 0)
        self.connection_status_label = QLabel("Disconnected")
        self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.connection_status_label, 1, 1, 1, 2)  # Span 2 columns
        
        return group
    
    def create_control_group(self) -> QGroupBox:
        """Create motor control group"""
        group = QGroupBox("Motor Control")
        layout = QGridLayout(group)
        
        # Torque input methods
        layout.addWidget(QLabel("Desired Torque (Nm):"), 0, 0, 1, 2)
        
        # Spinbox for precise input
        self.torque_spinbox = QDoubleSpinBox()
        self.torque_spinbox.setRange(-self.max_torque, self.max_torque)
        self.torque_spinbox.setSingleStep(self.torque_step)
        self.torque_spinbox.setDecimals(3)
        self.torque_spinbox.setValue(0.0)
        self.torque_spinbox.setSuffix(" Nm")
        self.torque_spinbox.valueChanged.connect(self.on_torque_spinbox_changed)
        layout.addWidget(self.torque_spinbox, 1, 0, 1, 2)
        
        # Slider for quick adjustment
        self.torque_slider = QSlider(Qt.Orientation.Horizontal)
        self.torque_slider.setRange(int(-self.max_torque * 1000), int(self.max_torque * 1000))
        self.torque_slider.setValue(0)
        self.torque_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.torque_slider.setTickInterval(int(self.max_torque * 100))
        self.torque_slider.valueChanged.connect(self.on_torque_slider_changed)
        layout.addWidget(self.torque_slider, 2, 0, 1, 2)
        
        # Preset buttons (smaller grid)
        preset_layout = QGridLayout()
        preset_values = [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0]
        
        for i, value in enumerate(preset_values):
            btn = QPushButton(f"{value:+.1f}")
            btn.setMaximumWidth(50)
            btn.clicked.connect(lambda checked, v=value: self.set_torque_value(v))
            row, col = i // 4, i % 4
            preset_layout.addWidget(btn, row, col)
        
        layout.addWidget(QLabel("Presets:"), 3, 0)
        layout.addLayout(preset_layout, 4, 0, 1, 2)
        
        # Send command button
        self.send_torque_button = QPushButton("Send Torque Command")
        self.send_torque_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.send_torque_button.clicked.connect(self.on_send_torque_clicked)
        layout.addWidget(self.send_torque_button, 5, 0, 1, 2)
        
        # Max torque setting
        layout.addWidget(QLabel("Max Torque:"), 6, 0)
        self.max_torque_spinbox = QDoubleSpinBox()
        self.max_torque_spinbox.setRange(0.1, 10.0)
        self.max_torque_spinbox.setValue(self.max_torque)
        self.max_torque_spinbox.setSuffix(" Nm")
        self.max_torque_spinbox.valueChanged.connect(self.on_max_torque_changed)
        layout.addWidget(self.max_torque_spinbox, 6, 1)
        
        return group
    
    def create_status_group(self) -> QGroupBox:
        """Create current status display group"""
        group = QGroupBox("Current Status")
        layout = QGridLayout(group)
        
        # Current torque display
        layout.addWidget(QLabel("Torque:"), 0, 0)
        self.current_torque_lcd = QLCDNumber()
        self.current_torque_lcd.setDigitCount(6)
        self.current_torque_lcd.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.current_torque_lcd.display(0.000)
        layout.addWidget(self.current_torque_lcd, 0, 1)
        layout.addWidget(QLabel("Nm"), 0, 2)
        
        # Current angle display
        layout.addWidget(QLabel("Angle:"), 1, 0)
        self.current_angle_lcd = QLCDNumber()
        self.current_angle_lcd.setDigitCount(6)
        self.current_angle_lcd.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.current_angle_lcd.display(0.00)
        layout.addWidget(self.current_angle_lcd, 1, 1)
        layout.addWidget(QLabel("°"), 1, 2)
        
        # Data rate
        layout.addWidget(QLabel("Data Rate:"), 2, 0)
        self.data_rate_label = QLabel("0.0 Hz")
        layout.addWidget(self.data_rate_label, 2, 1, 1, 2)
        
        # Last command with status
        layout.addWidget(QLabel("Last Cmd:"), 3, 0)
        self.last_command_label = QLabel("None")
        self.last_command_label.setWordWrap(True)
        layout.addWidget(self.last_command_label, 3, 1, 1, 2)
        
        # Command status indicator
        layout.addWidget(QLabel("Cmd Status:"), 4, 0)
        self.command_status_label = QLabel("Ready")
        self.command_status_label.setStyleSheet("color: gray; font-weight: bold;")
        layout.addWidget(self.command_status_label, 4, 1, 1, 2)
        
        return group
    
    def create_data_acquisition_group(self) -> QGroupBox:
        """Create data acquisition control group"""
        group = QGroupBox("Data Acquisition")
        layout = QGridLayout(group)
        
        # Start/Stop buttons
        self.start_data_button = QPushButton("Start Data")
        self.start_data_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.start_data_button.clicked.connect(self.on_start_data_clicked)
        layout.addWidget(self.start_data_button, 0, 0)
        
        self.stop_data_button = QPushButton("Stop Data")
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
    
    def create_recording_group(self) -> QGroupBox:
        """Create recording control group"""
        group = QGroupBox("Data Recording")
        layout = QGridLayout(group)
        
        # Recording buttons
        self.start_recording_button = QPushButton("Start Recording")
        self.start_recording_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.start_recording_button.clicked.connect(self.start_recording)
        layout.addWidget(self.start_recording_button, 0, 0)
        
        self.stop_recording_button = QPushButton("Stop Recording")
        self.stop_recording_button.setStyleSheet("background-color: #F44336; color: white; font-weight: bold;")
        self.stop_recording_button.clicked.connect(self.stop_recording)
        self.stop_recording_button.setEnabled(False)
        layout.addWidget(self.stop_recording_button, 0, 1)
        
        # Recording status
        self.recording_status_label = QLabel("Not Recording")
        self.recording_status_label.setWordWrap(True)
        layout.addWidget(self.recording_status_label, 1, 0, 1, 2)
        
        return group
    
    def create_emergency_group(self) -> QGroupBox:
        """Create emergency control group"""
        group = QGroupBox("Emergency Controls")
        layout = QVBoxLayout(group)
        
        # Emergency stop button
        self.emergency_stop_button = QPushButton("EMERGENCY STOP")
        self.emergency_stop_button.setStyleSheet(
            "background-color: #F44336; color: white; font-weight: bold; "
            "font-size: 14px; padding: 8px; border-radius: 5px;"
        )
        self.emergency_stop_button.clicked.connect(self.on_emergency_stop_clicked)
        layout.addWidget(self.emergency_stop_button)
        
        # Zero torque button
        self.zero_torque_button = QPushButton("Zero Torque")
        self.zero_torque_button.clicked.connect(self.on_zero_torque_clicked)
        layout.addWidget(self.zero_torque_button)
        
        return group
    
    def create_plot_controls(self) -> QGroupBox:
        """Create minimal plot control panel"""
        group = QGroupBox("Plot Controls")
        layout = QHBoxLayout(group)
        
        # Time window control
        layout.addWidget(QLabel("Time Window:"))
        self.time_window_spinbox = QDoubleSpinBox()
        self.time_window_spinbox.setRange(1.0, 60.0)
        self.time_window_spinbox.setValue(self.time_window)
        self.time_window_spinbox.setSuffix(" s")
        self.time_window_spinbox.valueChanged.connect(self.on_time_window_changed)
        layout.addWidget(self.time_window_spinbox)
        
        # Auto-scale options
        self.auto_scale_torque_checkbox = QCheckBox("Auto-scale Torque")
        self.auto_scale_torque_checkbox.setChecked(True)
        self.auto_scale_torque_checkbox.toggled.connect(self.on_auto_scale_toggled)
        layout.addWidget(self.auto_scale_torque_checkbox)
        
        self.auto_scale_angle_checkbox = QCheckBox("Auto-scale Angle")
        self.auto_scale_angle_checkbox.setChecked(True)
        self.auto_scale_angle_checkbox.toggled.connect(self.on_auto_scale_toggled)
        layout.addWidget(self.auto_scale_angle_checkbox)
        
        # Clear data button
        self.clear_data_button = QPushButton("Clear Data")
        self.clear_data_button.clicked.connect(self.clear_all_data)
        layout.addWidget(self.clear_data_button)
        
        layout.addStretch()
        
        return group
    
    def create_plot_area(self) -> QWidget:
        """Create the main plotting area"""
        # Use QSplitter for resizable plots
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Torque plot
        self.torque_plot_widget = pg.PlotWidget(title="Motor Torque")
        self.torque_plot_widget.setLabel('left', 'Torque', units='Nm')
        self.torque_plot_widget.setLabel('bottom', 'Time', units='s')
        self.torque_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.torque_plot_widget.setBackground('w')
        
        # Angle plot
        self.angle_plot_widget = pg.PlotWidget(title="Motor Angle")
        self.angle_plot_widget.setLabel('left', 'Angle', units='degrees')
        self.angle_plot_widget.setLabel('bottom', 'Time', units='s')
        self.angle_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.angle_plot_widget.setBackground('w')
        
        splitter.addWidget(self.torque_plot_widget)
        splitter.addWidget(self.angle_plot_widget)
        
        # Set equal sizes
        splitter.setSizes([300, 300])
        
        return splitter
    
    def setup_plots(self):
        """Setup plot curves and styling"""
        # Torque plot curve
        self.torque_curve = self.torque_plot_widget.plot(
            pen=pg.mkPen(color=self.plot_colors["torque"], width=2),
            name="Torque"
        )
        
        # Angle plot curve
        self.angle_curve = self.angle_plot_widget.plot(
            pen=pg.mkPen(color=self.plot_colors["angle"], width=2),
            name="Angle"
        )
    
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
        
        # Recording controls
        self.start_recording_button.setEnabled(self.is_data_acquisition_active and not self.is_recording)
        self.stop_recording_button.setEnabled(self.is_recording)
    
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
            
            # Load plot settings
            plot_config = config.get("plotting", {})
            self.time_window = plot_config.get("time_window", 10.0)
            self.time_window_spinbox.setValue(self.time_window)
            
            self.update_rate = plot_config.get("update_rate", 50)
            self.update_timer.setInterval(self.update_rate)
            
        except Exception as e:
            print(f"Error loading control plots tab configuration: {e}")
    
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
            },
            "plotting": {
                "time_window": self.time_window,
                "update_rate": self.update_rate
            }
        }
    
    # Control event handlers
    @Slot()
    def on_connect_clicked(self):
        """Handle connect button click"""
        print("DEBUG: Connect button clicked")
        selected_port = self.port_combo.currentText()
        print(f"DEBUG: Selected port: {selected_port}")
        if selected_port:
            print(f"DEBUG: Emitting connection_requested signal for {selected_port}")
            self.connection_requested.emit(selected_port)
        else:
            print("DEBUG: No port selected")
    
    @Slot()
    def on_disconnect_clicked(self):
        """Handle disconnect button click"""
        self.disconnection_requested.emit()
    
    @Slot(float)
    def on_torque_spinbox_changed(self, value: float):
        """Handle torque spinbox value change"""
        self.torque_slider.blockSignals(True)
        self.torque_slider.setValue(int(value * 1000))
        self.torque_slider.blockSignals(False)
    
    @Slot(int)
    def on_torque_slider_changed(self, value: int):
        """Handle torque slider value change"""
        torque_value = value / 1000.0
        self.torque_spinbox.blockSignals(True)
        self.torque_spinbox.setValue(torque_value)
        self.torque_spinbox.blockSignals(False)
    
    @Slot()
    def on_send_torque_clicked(self):
        """Handle send torque button click"""
        torque_value = self.torque_spinbox.value()
        self.command_status_label.setText("Sending...")
        self.command_status_label.setStyleSheet("color: orange; font-weight: bold;")
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
    
    @Slot()
    def on_refresh_ports_clicked(self):
        """Handle refresh ports button click"""
        print("DEBUG: Refresh ports button clicked")
        self.refresh_ports_requested.emit()
        print("DEBUG: Refresh ports signal emitted")
    
    # Plot event handlers
    @Slot(float)
    def on_time_window_changed(self, value: float):
        """Handle time window change"""
        self.time_window = value
        self.plot_settings_changed.emit({"time_window": value})
    
    @Slot(bool)
    def on_auto_scale_toggled(self, checked: bool):
        """Handle auto-scale toggle"""
        pass  # Auto-scaling is handled in update_plots method
    
    # Data management methods
    def update_data(self, data_buffer: Dict[str, List[float]]):
        """Update internal data buffer and prepare for plotting"""
        self.data_buffer = data_buffer.copy()
        
        # Convert to relative time for plotting
        if len(self.data_buffer["time"]) > 0:
            current_time = time.time()
            time_data = self.data_buffer["time"]
            
            # Create relative time array (most recent data at time 0, going backward)
            relative_times = [-(current_time - t) for t in time_data]
            
            # Filter data within time window
            window_start = -self.time_window
            
            filtered_indices = [i for i, t in enumerate(relative_times) if t >= window_start]
            
            if filtered_indices:
                # Update plot data
                self.plot_data["torque"]["x"] = [relative_times[i] for i in filtered_indices]
                self.plot_data["torque"]["y"] = [self.data_buffer["torque"][i] for i in filtered_indices]
                
                self.plot_data["angle"]["x"] = [relative_times[i] for i in filtered_indices]
                self.plot_data["angle"]["y"] = [self.data_buffer["angle"][i] for i in filtered_indices]
        
        # Record data if recording is active
        if self.is_recording and self.recording_writer:
            self.record_current_data()
    
    def update_plots(self):
        """Update plot displays"""
        if not self.plot_data["torque"]["x"]:
            return
        
        try:
            # Update torque plot
            self.torque_curve.setData(
                self.plot_data["torque"]["x"],
                self.plot_data["torque"]["y"]
            )
            
            # Update angle plot
            self.angle_curve.setData(
                self.plot_data["angle"]["x"],
                self.plot_data["angle"]["y"]
            )
            
            # Update X-axis ranges to show time window
            self.torque_plot_widget.setXRange(-self.time_window, 0)
            self.angle_plot_widget.setXRange(-self.time_window, 0)
            
            # Auto-scale Y-axes if enabled
            if self.auto_scale_torque_checkbox.isChecked() and self.plot_data["torque"]["y"]:
                y_data = self.plot_data["torque"]["y"]
                y_min, y_max = min(y_data), max(y_data)
                margin = max((y_max - y_min) * 0.1, 0.1)  # 10% margin, minimum 0.1
                self.torque_plot_widget.setYRange(y_min - margin, y_max + margin)
            
            if self.auto_scale_angle_checkbox.isChecked() and self.plot_data["angle"]["y"]:
                y_data = self.plot_data["angle"]["y"]
                y_min, y_max = min(y_data), max(y_data)
                margin = max((y_max - y_min) * 0.1, 1.0)  # 10% margin, minimum 1 degree
                self.angle_plot_widget.setYRange(y_min - margin, y_max + margin)
            
        except Exception as e:
            print(f"Error updating plots: {e}")
    
    # Recording methods
    def start_recording(self):
        """Start data recording"""
        if self.is_recording:
            return
        
        try:
            # Get save location
            default_filename = f"motor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            save_path = Path.home() / "CableScope" / "recordings"
            save_path.mkdir(parents=True, exist_ok=True)
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Recording As",
                str(save_path / default_filename),
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if filename:
                self.recording_file = open(filename, 'w', newline='')
                self.recording_writer = csv.writer(self.recording_file)
                
                # Write header
                self.recording_writer.writerow(['Timestamp', 'Time (s)', 'Torque (Nm)', 'Angle (deg)'])
                
                self.is_recording = True
                self.recording_start_time = time.time()
                
                # Update UI
                self.recording_status_label.setText(f"Recording: {Path(filename).name}")
                self.recording_status_label.setStyleSheet("color: red; font-weight: bold;")
                
                self.recording_start_requested.emit(filename)
                self.update_ui_state()
                
        except Exception as e:
            QMessageBox.critical(self, "Recording Error", f"Failed to start recording: {e}")
    
    def stop_recording(self):
        """Stop data recording"""
        if not self.is_recording:
            return
        
        try:
            self.is_recording = False
            
            if self.recording_file:
                self.recording_file.close()
                self.recording_file = None
                self.recording_writer = None
            
            # Update UI
            self.recording_status_label.setText("Not Recording")
            self.recording_status_label.setStyleSheet("color: black; font-weight: normal;")
            
            self.recording_stop_requested.emit()
            self.update_ui_state()
            
            QMessageBox.information(self, "Recording", "Recording stopped successfully.")
            
        except Exception as e:
            QMessageBox.critical(self, "Recording Error", f"Failed to stop recording: {e}")
    
    def record_current_data(self):
        """Record current data point"""
        if not self.data_buffer["time"]:
            return
        
        try:
            # Get the most recent data point
            latest_idx = -1
            
            current_time = self.data_buffer["time"][latest_idx]
            relative_time = current_time - self.recording_start_time
            torque = self.data_buffer["torque"][latest_idx]
            angle = self.data_buffer["angle"][latest_idx]
            
            # Write to CSV
            self.recording_writer.writerow([
                datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                f"{relative_time:.3f}",
                f"{torque:.6f}",
                f"{angle:.3f}"
            ])
            
        except Exception as e:
            print(f"Error recording data: {e}")
    
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
                QTimer.singleShot(1000, self.data_acquisition_start_requested.emit)
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
        print(f"DEBUG: update_available_ports called with: {ports}")
        self.available_ports = ports
        
        # Save current selection
        current_selection = self.port_combo.currentText()
        print(f"DEBUG: Current selection: {current_selection}")
        
        # Update combo box
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        print(f"DEBUG: Added {len(ports)} ports to combo box")
        
        # Auto-select Teensy port if no current selection or if current selection not available
        if not current_selection or current_selection not in ports:
            teensy_port = self.find_teensy_port(ports)
            if teensy_port:
                self.port_combo.setCurrentText(teensy_port)
                print(f"DEBUG: Auto-selected Teensy port: {teensy_port}")
            elif ports:
                # Fallback: select first available port
                self.port_combo.setCurrentText(ports[0])
                print(f"DEBUG: No Teensy found, selected first port: {ports[0]}")
        elif current_selection in ports:
            # Restore previous selection if still available
            self.port_combo.setCurrentText(current_selection)
            print(f"DEBUG: Restored selection: {current_selection}")
        
        self.update_ui_state()
    
    def find_teensy_port(self, ports: List[str]) -> Optional[str]:
        """Find the Teensy port from available ports"""
        # Import here to avoid circular import
        from core.serial_manager import SerialCommunicationManager
        temp_manager = SerialCommunicationManager()
        return temp_manager.find_teensy_port(ports)
    
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
    
    def set_command_status(self, status: str, color: str = "gray"):
        """Update command status display"""
        self.command_status_label.setText(status)
        self.command_status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
    
    def on_command_acknowledged(self):
        """Handle command acknowledgment"""
        self.set_command_status("✓ Sent", "green")
    
    def clear_all_data(self):
        """Clear all plot data"""
        self.data_buffer = {"torque": [], "angle": [], "time": []}
        self.plot_data = {"torque": {"x": [], "y": []}, "angle": {"x": [], "y": []}}
        
        # Clear plot curves
        self.torque_curve.setData([], [])
        self.angle_curve.setData([], [])
    
    def reset_all_plots(self):
        """Reset plot zoom and ranges"""
        self.torque_plot_widget.autoRange()
        self.angle_plot_widget.autoRange()
    
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
    
    def cleanup(self):
        """Cleanup resources when closing"""
        try:
            # Stop update timer
            if hasattr(self, 'update_timer'):
                self.update_timer.stop()
            
            # Stop recording if active
            if self.is_recording:
                self.stop_recording()
                
        except Exception as e:
            print(f"Error during cleanup: {e}")