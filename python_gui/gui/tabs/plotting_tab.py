"""
Plotting Tab for CableScope Motor Control
Provides real-time plotting of torque and angle data
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QComboBox, QLabel, QSpinBox, QDoubleSpinBox,
    QCheckBox, QSlider, QTabWidget, QFileDialog, QMessageBox,
    QSplitter
)
from PySide6.QtCore import Signal, Slot, Qt, QTimer
import pyqtgraph as pg
import numpy as np
from typing import Dict, Any, List, Optional
import time
from datetime import datetime
import csv
from pathlib import Path


class PlottingTab(QWidget):
    """Real-time plotting interface"""
    
    # Signals
    plot_settings_changed = Signal(dict)
    recording_start_requested = Signal(str)
    recording_stop_requested = Signal()
    
    def __init__(self):
        super().__init__()
        
        # Plot configuration
        self.time_window = 10.0  # seconds
        self.update_rate = 50    # ms
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
        
        # Setup update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plots)
        self.update_timer.start(self.update_rate)
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Control panel
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)
        
        # Plot area
        plot_area = self.create_plot_area()
        layout.addWidget(plot_area, 1)  # Give plots most of the space
    
    def create_control_panel(self) -> QGroupBox:
        """Create plot control panel"""
        group = QGroupBox("Plot Controls")
        layout = QGridLayout(group)
        
        # Time window control
        layout.addWidget(QLabel("Time Window:"), 0, 0)
        self.time_window_spinbox = QDoubleSpinBox()
        self.time_window_spinbox.setRange(1.0, 60.0)
        self.time_window_spinbox.setValue(self.time_window)
        self.time_window_spinbox.setSuffix(" s")
        self.time_window_spinbox.valueChanged.connect(self.on_time_window_changed)
        layout.addWidget(self.time_window_spinbox, 0, 1)
        
        # Update rate control
        layout.addWidget(QLabel("Update Rate:"), 0, 2)
        self.update_rate_spinbox = QSpinBox()
        self.update_rate_spinbox.setRange(10, 200)
        self.update_rate_spinbox.setValue(self.update_rate)
        self.update_rate_spinbox.setSuffix(" ms")
        self.update_rate_spinbox.valueChanged.connect(self.on_update_rate_changed)
        layout.addWidget(self.update_rate_spinbox, 0, 3)
        
        # Auto-scale options
        self.auto_scale_torque_checkbox = QCheckBox("Auto-scale Torque")
        self.auto_scale_torque_checkbox.setChecked(True)
        self.auto_scale_torque_checkbox.toggled.connect(self.on_auto_scale_toggled)
        layout.addWidget(self.auto_scale_torque_checkbox, 1, 0)
        
        self.auto_scale_angle_checkbox = QCheckBox("Auto-scale Angle")
        self.auto_scale_angle_checkbox.setChecked(True)
        self.auto_scale_angle_checkbox.toggled.connect(self.on_auto_scale_toggled)
        layout.addWidget(self.auto_scale_angle_checkbox, 1, 1)
        
        # Y-axis range controls
        layout.addWidget(QLabel("Torque Range:"), 1, 2)
        self.torque_range_min = QDoubleSpinBox()
        self.torque_range_min.setRange(-50.0, 50.0)
        self.torque_range_min.setValue(-40.0)
        self.torque_range_min.setPrefix("Min: ")
        layout.addWidget(self.torque_range_min, 1, 3)
        
        self.torque_range_max = QDoubleSpinBox()
        self.torque_range_max.setRange(-50.0, 50.0)
        self.torque_range_max.setValue(40.0)
        self.torque_range_max.setPrefix("Max: ")
        layout.addWidget(self.torque_range_max, 1, 4)
        
        layout.addWidget(QLabel("Angle Range:"), 2, 2)
        self.angle_range_min = QDoubleSpinBox()
        self.angle_range_min.setRange(-1800.0, 1800.0)
        self.angle_range_min.setValue(-180.0)
        self.angle_range_min.setPrefix("Min: ")
        layout.addWidget(self.angle_range_min, 2, 3)
        
        self.angle_range_max = QDoubleSpinBox()
        self.angle_range_max.setRange(-1800.0, 1800.0)
        self.angle_range_max.setValue(180.0)
        self.angle_range_max.setPrefix("Max: ")
        layout.addWidget(self.angle_range_max, 2, 4)
        
        # Recording controls
        recording_layout = QHBoxLayout()
        
        self.start_recording_button = QPushButton("Start Recording")
        self.start_recording_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.start_recording_button.clicked.connect(self.start_recording)
        recording_layout.addWidget(self.start_recording_button)
        
        self.stop_recording_button = QPushButton("Stop Recording")
        self.stop_recording_button.setStyleSheet("background-color: #F44336; color: white; font-weight: bold;")
        self.stop_recording_button.clicked.connect(self.stop_recording)
        self.stop_recording_button.setEnabled(False)
        recording_layout.addWidget(self.stop_recording_button)
        
        self.recording_status_label = QLabel("Not Recording")
        recording_layout.addWidget(self.recording_status_label)
        
        recording_layout.addStretch()
        
        # Clear data button
        self.clear_data_button = QPushButton("Clear Data")
        self.clear_data_button.clicked.connect(self.clear_all_data)
        recording_layout.addWidget(self.clear_data_button)
        
        layout.addLayout(recording_layout, 3, 0, 1, 5)
        
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
        splitter.setSizes([400, 400])
        
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
        
        # Add legends
        self.torque_plot_widget.addLegend()
        self.angle_plot_widget.addLegend()
        
        # Set initial ranges
        self.update_plot_ranges()
    
    def setup_connections(self):
        """Setup internal connections"""
        # Connect range controls
        self.torque_range_min.valueChanged.connect(self.update_plot_ranges)
        self.torque_range_max.valueChanged.connect(self.update_plot_ranges)
        self.angle_range_min.valueChanged.connect(self.update_plot_ranges)
        self.angle_range_max.valueChanged.connect(self.update_plot_ranges)
    
    def update_plot_ranges(self):
        """Update plot Y-axis ranges"""
        # Update torque plot range
        if not self.auto_scale_torque_checkbox.isChecked():
            self.torque_plot_widget.setYRange(
                self.torque_range_min.value(),
                self.torque_range_max.value()
            )
        
        # Update angle plot range
        if not self.auto_scale_angle_checkbox.isChecked():
            self.angle_plot_widget.setYRange(
                self.angle_range_min.value(),
                self.angle_range_max.value()
            )
    
    def update_data(self, data_buffer: Dict[str, List[float]]):
        """Update internal data buffer"""
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
                margin = (y_max - y_min) * 0.1  # 10% margin
                self.torque_plot_widget.setYRange(y_min - margin, y_max + margin)
            
            if self.auto_scale_angle_checkbox.isChecked() and self.plot_data["angle"]["y"]:
                y_data = self.plot_data["angle"]["y"]
                y_min, y_max = min(y_data), max(y_data)
                margin = (y_max - y_min) * 0.1  # 10% margin
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
                self.start_recording_button.setEnabled(False)
                self.stop_recording_button.setEnabled(True)
                self.recording_status_label.setText(f"Recording to: {Path(filename).name}")
                self.recording_status_label.setStyleSheet("color: red; font-weight: bold;")
                
                self.recording_start_requested.emit(filename)
                
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
            self.start_recording_button.setEnabled(True)
            self.stop_recording_button.setEnabled(False)
            self.recording_status_label.setText("Recording stopped")
            self.recording_status_label.setStyleSheet("color: black; font-weight: normal;")
            
            self.recording_stop_requested.emit()
            
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
    
    # Configuration methods
    def load_configuration(self, config: Dict[str, Any]):
        """Load configuration settings"""
        try:
            plot_config = config.get("plotting", {})
            
            # Time window
            self.time_window = plot_config.get("time_window", 10.0)
            self.time_window_spinbox.setValue(self.time_window)
            
            # Update rate
            self.update_rate = plot_config.get("update_rate", 50)
            self.update_rate_spinbox.setValue(self.update_rate)
            self.update_timer.setInterval(self.update_rate)
            
            # Y-axis limits
            y_limits = plot_config.get("y_limits", {})
            torque_limits = y_limits.get("torque", [-10.0, 10.0])
            angle_limits = y_limits.get("angle", [-360.0, 360.0])
            
            self.torque_range_min.setValue(torque_limits[0])
            self.torque_range_max.setValue(torque_limits[1])
            self.angle_range_min.setValue(angle_limits[0])
            self.angle_range_max.setValue(angle_limits[1])
            
            self.update_plot_ranges()
            
        except Exception as e:
            print(f"Error loading plotting tab configuration: {e}")
    
    def save_configuration(self) -> Dict[str, Any]:
        """Save current configuration settings"""
        return {
            "plotting": {
                "time_window": self.time_window,
                "update_rate": self.update_rate,
                "y_limits": {
                    "torque": [self.torque_range_min.value(), self.torque_range_max.value()],
                    "angle": [self.angle_range_min.value(), self.angle_range_max.value()]
                }
            }
        }
    
    # Event handlers
    @Slot(float)
    def on_time_window_changed(self, value: float):
        """Handle time window change"""
        self.time_window = value
        self.plot_settings_changed.emit({"time_window": value})
    
    @Slot(int)
    def on_update_rate_changed(self, value: int):
        """Handle update rate change"""
        self.update_rate = value
        self.update_timer.setInterval(value)
        self.plot_settings_changed.emit({"update_rate": value})
    
    @Slot(bool)
    def on_auto_scale_toggled(self, checked: bool):
        """Handle auto-scale toggle"""
        self.update_plot_ranges()
    
    # Public methods
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
        
        # Re-apply fixed ranges if not auto-scaling
        self.update_plot_ranges()
    
    def set_theme(self, is_dark: bool):
        """Update plot theme"""
        if is_dark:
            bg_color = '#1e293b'
            text_color = '#f8fafc'
        else:
            bg_color = 'w'
            text_color = '#0f172a'
        
        # Update plot backgrounds
        self.torque_plot_widget.setBackground(bg_color)
        self.angle_plot_widget.setBackground(bg_color)
    
    def get_current_data_summary(self) -> Dict[str, Any]:
        """Get summary of current data"""
        if not self.data_buffer["torque"]:
            return {}
        
        torque_data = self.data_buffer["torque"]
        angle_data = self.data_buffer["angle"]
        
        return {
            "data_points": len(torque_data),
            "torque": {
                "current": torque_data[-1] if torque_data else 0.0,
                "min": min(torque_data) if torque_data else 0.0,
                "max": max(torque_data) if torque_data else 0.0,
                "avg": sum(torque_data) / len(torque_data) if torque_data else 0.0
            },
            "angle": {
                "current": angle_data[-1] if angle_data else 0.0,
                "min": min(angle_data) if angle_data else 0.0,
                "max": max(angle_data) if angle_data else 0.0,
                "avg": sum(angle_data) / len(angle_data) if angle_data else 0.0
            }
        }