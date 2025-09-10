"""
Enhanced Status Bar for CableScope Motor Control
"""

from PySide6.QtWidgets import QStatusBar, QLabel, QProgressBar, QPushButton, QWidget, QHBoxLayout
from PySide6.QtCore import QTimer, Signal, Slot
from PySide6.QtGui import QFont
import time
from typing import Optional, Dict, Any


class EnhancedStatusBar(QStatusBar):
    """Enhanced status bar with connection, data, and recording status"""
    
    def __init__(self):
        super().__init__()
        
        # Status tracking
        self.is_connected = False
        self.is_data_acquisition_active = False
        self.is_recording = False
        self.data_count = 0
        self.data_rate = 0.0
        self.last_torque_command = 0.0
        self.last_command_time = None
        
        self.setup_ui()
        self.setup_timer()
    
    def setup_ui(self):
        """Setup status bar widgets"""
        # Connection status
        self.connection_label = QLabel("Disconnected")
        self.connection_label.setStyleSheet("color: red; font-weight: bold; padding: 2px 8px;")
        self.addWidget(self.connection_label)
        
        # Separator
        self.addWidget(self._create_separator())
        
        # Data acquisition status
        self.data_status_label = QLabel("Data: Stopped")
        self.data_status_label.setStyleSheet("color: red; padding: 2px 8px;")
        self.addWidget(self.data_status_label)
        
        # Data rate
        self.data_rate_label = QLabel("0.0 Hz")
        self.data_rate_label.setStyleSheet("padding: 2px 8px;")
        self.addWidget(self.data_rate_label)
        
        # Separator
        self.addWidget(self._create_separator())
        
        # Current values
        self.torque_label = QLabel("T: 0.000 Nm")
        self.torque_label.setStyleSheet("padding: 2px 8px; font-family: monospace;")
        self.addWidget(self.torque_label)
        
        self.angle_label = QLabel("A: 0.00°")
        self.angle_label.setStyleSheet("padding: 2px 8px; font-family: monospace;")
        self.addWidget(self.angle_label)
        
        # Separator
        self.addWidget(self._create_separator())
        
        # Recording status
        self.recording_label = QLabel("Not Recording")
        self.recording_label.setStyleSheet("color: gray; padding: 2px 8px;")
        self.addWidget(self.recording_label)
        
        # Permanent widgets (right side)
        # Last command info
        self.last_command_label = QLabel("Last Cmd: None")
        self.last_command_label.setStyleSheet("padding: 2px 8px; font-family: monospace;")
        self.addPermanentWidget(self.last_command_label)
        
        # Data count
        self.data_count_label = QLabel("Data: 0")
        self.data_count_label.setStyleSheet("padding: 2px 8px;")
        self.addPermanentWidget(self.data_count_label)
    
    def _create_separator(self) -> QLabel:
        """Create a visual separator"""
        sep = QLabel("|")
        sep.setStyleSheet("color: gray; padding: 0px 4px;")
        return sep
    
    def setup_timer(self):
        """Setup update timer"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_displays)
        self.update_timer.start(1000)  # Update every second
    
    def set_connection_status(self, connected: bool, port: str = ""):
        """Set connection status"""
        self.is_connected = connected
        
        if connected:
            self.connection_label.setText(f"Connected: {port}")
            self.connection_label.setStyleSheet("color: green; font-weight: bold; padding: 2px 8px;")
        else:
            self.connection_label.setText("Disconnected")
            self.connection_label.setStyleSheet("color: red; font-weight: bold; padding: 2px 8px;")
    
    def set_data_acquisition_status(self, active: bool):
        """Set data acquisition status"""
        self.is_data_acquisition_active = active
        
        if active:
            self.data_status_label.setText("Data: Running")
            self.data_status_label.setStyleSheet("color: green; padding: 2px 8px; font-weight: bold;")
        else:
            self.data_status_label.setText("Data: Stopped")
            self.data_status_label.setStyleSheet("color: red; padding: 2px 8px;")
    
    def set_recording_status(self, recording: bool, filename: str = ""):
        """Set recording status"""
        self.is_recording = recording
        
        if recording:
            if filename:
                from pathlib import Path
                filename = Path(filename).name
                self.recording_label.setText(f"Recording: {filename}")
            else:
                self.recording_label.setText("Recording")
            self.recording_label.setStyleSheet("color: red; font-weight: bold; padding: 2px 8px;")
        else:
            self.recording_label.setText("Not Recording")
            self.recording_label.setStyleSheet("color: gray; padding: 2px 8px;")
    
    def update_current_values(self, data: Dict[str, float]):
        """Update current torque and angle values"""
        if "torque" in data:
            self.torque_label.setText(f"T: {data['torque']:.3f} Nm")
        
        if "angle" in data:
            self.angle_label.setText(f"A: {data['angle']:.2f}°")
    
    def set_last_torque_command(self, torque: float):
        """Set last torque command"""
        self.last_torque_command = torque
        self.last_command_time = time.time()
        self.last_command_label.setText(f"Last Cmd: {torque:.3f} Nm")
    
    def set_last_command_time(self):
        """Update last command time (for acknowledgments)"""
        self.last_command_time = time.time()
    
    def increment_data_count(self):
        """Increment data packet count"""
        self.data_count += 1
    
    def update_data_rate(self, rate: float):
        """Update data reception rate"""
        self.data_rate = rate
        self.data_rate_label.setText(f"{rate:.1f} Hz")
    
    def update_displays(self):
        """Update time-dependent displays"""
        try:
            # Update data count
            self.data_count_label.setText(f"Data: {self.data_count}")
            
            # Update last command time indicator
            if self.last_command_time:
                time_since_command = time.time() - self.last_command_time
                if time_since_command < 5.0:  # Show for 5 seconds
                    self.last_command_label.setStyleSheet("padding: 2px 8px; font-family: monospace; color: green;")
                else:
                    self.last_command_label.setStyleSheet("padding: 2px 8px; font-family: monospace; color: black;")
        except RecursionError:
            print("RecursionError in status bar update_displays - skipping update")
        except Exception as e:
            print(f"Error in status bar update_displays: {e}")
    
    def show_message(self, message: str, timeout: int = 2000):
        """Show temporary message"""
        try:
            super().showMessage(message, timeout)
        except RecursionError:
            print(f"RecursionError in show_message: {message}")
        except Exception as e:
            print(f"Error in show_message: {e} - Message: {message}")
    
    def set_theme(self, is_dark: bool):
        """Update status bar theme"""
        if is_dark:
            base_style = "color: #f8fafc; background-color: #1e293b;"
            separator_style = "color: #64748b;"
        else:
            base_style = "color: #0f172a; background-color: #f8fafc;"
            separator_style = "color: #94a3b8;"
        
        self.setStyleSheet(f"QStatusBar {{ {base_style} }}")
        
        # Update separator colors
        for i in range(self.count()):
            widget = self.widget(i)
            if isinstance(widget, QLabel) and widget.text() == "|":
                widget.setStyleSheet(f"{separator_style} padding: 0px 4px;")
    
    def reset_counters(self):
        """Reset all counters"""
        self.data_count = 0
        self.data_rate = 0.0
        self.last_torque_command = 0.0
        self.last_command_time = None
        
        self.data_count_label.setText("Data: 0")
        self.data_rate_label.setText("0.0 Hz")
        self.last_command_label.setText("Last Cmd: None")
        self.torque_label.setText("T: 0.000 Nm")
        self.angle_label.setText("A: 0.00°")