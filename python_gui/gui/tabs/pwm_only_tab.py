"""
PWM Only Tab for CableScope Motor Control
Simple PWM firmware testing with real-time angle plotting and data recording
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QComboBox, QLabel, QTextEdit, QFileDialog,
    QMessageBox, QProgressBar, QLCDNumber, QSplitter
)
from PySide6.QtCore import Signal, Slot, Qt, QThread, QTimer
from PySide6.QtGui import QFont
import pyqtgraph as pg
import numpy as np
import subprocess
import os
import time
import csv
import serial
import serial.tools.list_ports
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class SerialReaderWorker(QThread):
    """Worker thread for reading serial data from PWM firmware"""

    data_received = Signal(dict)  # {pwm: float, angle: float, timestamp: float}
    error_occurred = Signal(str)
    connection_lost = Signal()

    def __init__(self, port: str, baud_rate: int = 9600):
        super().__init__()
        self.port = port
        self.baud_rate = baud_rate
        self.serial_connection = None
        self.running = False

    def run(self):
        """Run serial reading loop"""
        try:
            # Open serial connection
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=1.0
            )

            # Wait for Arduino to reset
            time.sleep(2.0)

            self.running = True

            while self.running:
                try:
                    if self.serial_connection.in_waiting > 0:
                        line = self.serial_connection.readline().decode('utf-8').strip()

                        # Skip header lines and empty lines
                        if not line or '=' in line or line.startswith('PWM,'):
                            continue

                        # Parse CSV format: PWM,AngleDeg
                        parts = line.split(',')
                        if len(parts) == 2:
                            try:
                                pwm = float(parts[0])
                                angle = float(parts[1])
                                timestamp = time.time()

                                data = {
                                    'pwm': pwm,
                                    'angle': angle,
                                    'timestamp': timestamp
                                }

                                self.data_received.emit(data)

                            except ValueError:
                                # Skip malformed data
                                pass

                    # Small delay to prevent CPU hogging
                    time.sleep(0.01)

                except serial.SerialException as e:
                    self.error_occurred.emit(f"Serial error: {e}")
                    self.connection_lost.emit()
                    break
                except Exception as e:
                    self.error_occurred.emit(f"Read error: {e}")

        except serial.SerialException as e:
            self.error_occurred.emit(f"Failed to open port: {e}")
        except Exception as e:
            self.error_occurred.emit(f"Serial reader error: {e}")
        finally:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()

    def stop(self):
        """Stop the serial reader"""
        self.running = False


class FirmwareUploadWorker(QThread):
    """Worker thread for uploading PWM firmware"""

    upload_started = Signal()
    upload_progress = Signal(str)
    upload_completed = Signal(bool, str)

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

            # Compile firmware
            self.upload_progress.emit("Compiling firmware...")

            compile_cmd = [
                self.arduino_cli_path,
                "compile",
                "--fqbn", self.board_type,
                self.firmware_path
            ]

            compile_result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if compile_result.returncode != 0:
                self.upload_completed.emit(False, f"Compile failed: {compile_result.stderr}")
                return

            self.upload_progress.emit("Compilation successful, uploading...")

            # Upload firmware
            upload_cmd = [
                self.arduino_cli_path,
                "upload",
                "--fqbn", self.board_type,
                "--port", self.port,
                self.firmware_path
            ]

            upload_result = subprocess.run(
                upload_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if upload_result.returncode == 0:
                self.upload_completed.emit(True, "Firmware uploaded successfully!")
            else:
                self.upload_completed.emit(False, f"Upload failed: {upload_result.stderr}")

        except subprocess.TimeoutExpired:
            self.upload_completed.emit(False, "Upload timed out")
        except Exception as e:
            self.upload_completed.emit(False, f"Upload error: {str(e)}")


class PWMOnlyTab(QWidget):
    """PWM Only tab for simple PWM firmware testing"""

    def __init__(self):
        super().__init__()

        # Configuration
        self.arduino_cli_path = "arduino-cli.exe"
        self.board_type = "teensy:avr:teensy41"
        self.selected_port = ""
        self.baud_rate = 9600

        # State
        self.is_connected = False
        self.is_recording = False
        self.serial_worker = None
        self.upload_worker = None

        # Data storage
        self.data_buffer = {"pwm": [], "angle": [], "time": [], "timestamp": []}
        self.buffer_size = 1000
        self.recording_start_time = None
        self.recording_file = None
        self.recording_writer = None

        # Plot configuration
        self.time_window = 30.0  # Show 30 seconds of data

        # Available firmware types mapped to firmware_resources types
        self.firmware_types = {
            "PWM Constant (700 for 24h)": "pwm_constant",
            "PWM On/Off (700/410, 3.5s each)": "pwm_on_off"
        }

        self.setup_ui()
        self.setup_plots()
        self.setup_connections()
        self.refresh_ports()

        # Setup plot update timer
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plots)
        self.plot_timer.start(50)  # 20Hz plot updates

    def setup_ui(self):
        """Setup the user interface"""
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left panel - Controls
        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)

        # Right panel - Plots
        plot_panel = self.create_plot_panel()
        splitter.addWidget(plot_panel)

        # Set splitter sizes
        splitter.setSizes([400, 600])

    def create_control_panel(self) -> QWidget:
        """Create the control panel"""
        panel = QWidget()
        panel.setMaximumWidth(450)
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        # Firmware selection group
        firmware_group = self.create_firmware_group()
        layout.addWidget(firmware_group)

        # Connection group
        connection_group = self.create_connection_group()
        layout.addWidget(connection_group)

        # Current values group
        values_group = self.create_values_group()
        layout.addWidget(values_group)

        # Recording group
        recording_group = self.create_recording_group()
        layout.addWidget(recording_group)

        # Upload log
        log_group = self.create_log_group()
        layout.addWidget(log_group, 1)  # Give log most space

        return panel

    def create_plot_panel(self) -> QWidget:
        """Create the plot panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(5)

        # Plot controls
        controls = self.create_plot_controls()
        layout.addWidget(controls)

        # Plot area
        plot_area = self.create_plot_area()
        layout.addWidget(plot_area, 1)

        return panel

    def create_firmware_group(self) -> QGroupBox:
        """Create firmware selection and upload group"""
        group = QGroupBox("PWM Firmware Selection")
        layout = QGridLayout(group)

        # Firmware type selection
        layout.addWidget(QLabel("Firmware Type:"), 0, 0)
        self.firmware_combo = QComboBox()
        for display_name in self.firmware_types.keys():
            self.firmware_combo.addItem(display_name)
        layout.addWidget(self.firmware_combo, 0, 1, 1, 2)

        # Board type
        layout.addWidget(QLabel("Board Type:"), 1, 0)
        self.board_combo = QComboBox()
        self.board_combo.addItems([
            "teensy:avr:teensy41",
            "teensy:avr:teensy40",
            "arduino:avr:mega",
            "arduino:avr:uno"
        ])
        self.board_combo.setCurrentText(self.board_type)
        self.board_combo.currentTextChanged.connect(self.on_board_changed)
        layout.addWidget(self.board_combo, 1, 1, 1, 2)

        # Upload port selection
        layout.addWidget(QLabel("Upload Port:"), 2, 0)
        self.upload_port_combo = QComboBox()
        layout.addWidget(self.upload_port_combo, 2, 1)

        # Refresh ports button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_ports)
        layout.addWidget(refresh_button, 2, 2)

        # Upload button
        self.upload_button = QPushButton("Upload Firmware")
        self.upload_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.upload_button.clicked.connect(self.start_upload)
        layout.addWidget(self.upload_button, 3, 0, 1, 3)

        # Upload progress
        self.upload_progress_bar = QProgressBar()
        self.upload_progress_bar.setVisible(False)
        layout.addWidget(self.upload_progress_bar, 4, 0, 1, 3)

        # Upload status
        self.upload_status_label = QLabel("Ready to upload")
        self.upload_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.upload_status_label, 5, 0, 1, 3)

        return group

    def create_connection_group(self) -> QGroupBox:
        """Create connection management group"""
        group = QGroupBox("Serial Connection")
        layout = QGridLayout(group)

        # Port selection
        layout.addWidget(QLabel("COM Port:"), 0, 0)
        self.port_combo = QComboBox()
        layout.addWidget(self.port_combo, 0, 1)

        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_device)
        layout.addWidget(self.connect_button, 0, 2)

        # Disconnect button
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_from_device)
        self.disconnect_button.setEnabled(False)
        layout.addWidget(self.disconnect_button, 1, 2)

        # Connection status
        layout.addWidget(QLabel("Status:"), 1, 0)
        self.connection_status_label = QLabel("Disconnected")
        self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.connection_status_label, 1, 1)

        return group

    def create_values_group(self) -> QGroupBox:
        """Create current values display group"""
        group = QGroupBox("Current Values")
        layout = QGridLayout(group)

        # PWM value
        layout.addWidget(QLabel("PWM:"), 0, 0)
        self.pwm_lcd = QLCDNumber()
        self.pwm_lcd.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.pwm_lcd.setDigitCount(4)
        self.pwm_lcd.display(0)
        layout.addWidget(self.pwm_lcd, 0, 1)

        # Angle value
        layout.addWidget(QLabel("Angle (deg):"), 1, 0)
        self.angle_lcd = QLCDNumber()
        self.angle_lcd.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.angle_lcd.setDigitCount(7)
        self.angle_lcd.display(0.0)
        layout.addWidget(self.angle_lcd, 1, 1)

        # Data rate
        layout.addWidget(QLabel("Data Rate:"), 2, 0)
        self.data_rate_label = QLabel("0.0 Hz")
        layout.addWidget(self.data_rate_label, 2, 1)

        # Data count
        layout.addWidget(QLabel("Samples:"), 3, 0)
        self.sample_count_label = QLabel("0")
        layout.addWidget(self.sample_count_label, 3, 1)

        return group

    def create_recording_group(self) -> QGroupBox:
        """Create recording control group"""
        group = QGroupBox("Data Recording")
        layout = QVBoxLayout(group)

        # Recording status
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.recording_status_label = QLabel("Not Recording")
        self.recording_status_label.setStyleSheet("color: gray;")
        status_layout.addWidget(self.recording_status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Recording buttons
        button_layout = QHBoxLayout()

        self.start_recording_button = QPushButton("Start Recording")
        self.start_recording_button.setStyleSheet("background-color: #2563eb; color: white;")
        self.start_recording_button.clicked.connect(self.start_recording)
        self.start_recording_button.setEnabled(False)
        button_layout.addWidget(self.start_recording_button)

        self.stop_recording_button = QPushButton("Stop Recording")
        self.stop_recording_button.setStyleSheet("background-color: #dc2626; color: white;")
        self.stop_recording_button.clicked.connect(self.stop_recording)
        self.stop_recording_button.setEnabled(False)
        button_layout.addWidget(self.stop_recording_button)

        layout.addLayout(button_layout)

        # Recording file path
        self.recording_path_label = QLabel("No file selected")
        self.recording_path_label.setStyleSheet("font-size: 9px; color: gray;")
        self.recording_path_label.setWordWrap(True)
        layout.addWidget(self.recording_path_label)

        return group

    def create_log_group(self) -> QGroupBox:
        """Create log display group"""
        group = QGroupBox("Activity Log")
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

    def create_plot_controls(self) -> QWidget:
        """Create plot control widgets"""
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # Title
        title = QLabel("Real-Time Angle Plot")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        layout.addStretch()

        # Clear plot button
        clear_button = QPushButton("Clear Plot")
        clear_button.clicked.connect(self.clear_plot_data)
        layout.addWidget(clear_button)

        # Reset zoom button
        reset_button = QPushButton("Reset Zoom")
        reset_button.clicked.connect(self.reset_plot_zoom)
        layout.addWidget(reset_button)

        return widget

    def create_plot_area(self) -> QWidget:
        """Create plot area with angle plot"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('left', 'Angle', units='deg')
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()

        layout.addWidget(self.plot_widget)

        return widget

    def setup_plots(self):
        """Setup plot curves"""
        # Angle plot curve
        self.angle_curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#2563eb', width=2),
            name='Angle'
        )

        # Data tracking for rate calculation
        self.last_data_time = None
        self.data_count = 0
        self.rate_calc_start = None

    def setup_connections(self):
        """Setup signal connections"""
        pass  # Connections set up in create methods

    def refresh_ports(self):
        """Refresh available COM ports"""
        try:
            ports = serial.tools.list_ports.comports()
            port_names = [port.device for port in ports]

            # Update both combo boxes
            current_upload = self.upload_port_combo.currentText()
            current_connect = self.port_combo.currentText()

            self.upload_port_combo.clear()
            self.port_combo.clear()

            self.upload_port_combo.addItems(port_names)
            self.port_combo.addItems(port_names)

            # Try to find Teensy port
            teensy_port = self.find_teensy_port(ports)
            if teensy_port:
                self.upload_port_combo.setCurrentText(teensy_port)
                self.port_combo.setCurrentText(teensy_port)
            elif port_names:
                if current_upload in port_names:
                    self.upload_port_combo.setCurrentText(current_upload)
                if current_connect in port_names:
                    self.port_combo.setCurrentText(current_connect)

            self.add_log(f"Found {len(port_names)} COM ports")

        except Exception as e:
            self.add_log(f"Error refreshing ports: {e}")

    def find_teensy_port(self, ports) -> Optional[str]:
        """Find Teensy port from available ports"""
        for port in ports:
            hwid = port.hwid.upper()
            if any(teensy_id in hwid for teensy_id in [
                '16C0:0483',  # Teensy 4.x
                '16C0:0476',  # Teensy 3.x
                'USB VID:PID=16C0'
            ]):
                return port.device
        return None

    def add_log(self, message: str):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def clear_log(self):
        """Clear the log"""
        self.log_text.clear()

    # Firmware upload methods
    @Slot(str)
    def on_board_changed(self, board: str):
        """Handle board type change"""
        self.board_type = board

    def start_upload(self):
        """Start firmware upload"""
        # Disconnect if connected
        if self.is_connected:
            reply = QMessageBox.question(
                self, "Disconnect Required",
                "Serial connection must be closed for upload. Disconnect now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.disconnect_from_device()
            else:
                return

        # Get selected firmware
        firmware_name = self.firmware_combo.currentText()
        firmware_type = self.firmware_types[firmware_name]

        # Create temporary firmware directory using embedded resources
        try:
            from core.firmware_resources import create_firmware_files
            import tempfile

            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix="pwm_firmware_")

            # Get the firmware type directory name for Arduino CLI
            if firmware_type == "pwm_constant":
                dir_name = "PWM_Constant"
            elif firmware_type == "pwm_on_off":
                dir_name = "PWM_On_Off"
            else:
                dir_name = "pwm_firmware"

            firmware_path = Path(temp_dir) / dir_name

            # Create firmware files from embedded resources
            created_files = create_firmware_files(str(firmware_path), firmware_type)

            self.add_log(f"Created temporary firmware: {firmware_path}")

        except Exception as e:
            QMessageBox.critical(self, "Upload Error", f"Failed to create firmware: {e}")
            self.add_log(f"Error creating firmware: {e}")
            return

        # Get port
        port = self.upload_port_combo.currentText()
        if not port:
            QMessageBox.warning(self, "Upload Error", "Please select a COM port")
            return

        # Confirm upload
        reply = QMessageBox.question(
            self, "Confirm Upload",
            f"Upload {firmware_name} to {port}?\n\nBoard: {self.board_type}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Start upload worker
        self.upload_worker = FirmwareUploadWorker(
            self.arduino_cli_path,
            str(firmware_path),
            port,
            self.board_type
        )

        self.upload_worker.upload_started.connect(self.on_upload_started)
        self.upload_worker.upload_progress.connect(self.on_upload_progress)
        self.upload_worker.upload_completed.connect(self.on_upload_completed)

        self.upload_worker.start()

    @Slot()
    def on_upload_started(self):
        """Handle upload start"""
        self.upload_button.setEnabled(False)
        self.upload_button.setText("Uploading...")
        self.upload_progress_bar.setVisible(True)
        self.upload_progress_bar.setRange(0, 0)
        self.upload_status_label.setText("Upload in progress...")
        self.add_log("Starting firmware upload...")

    @Slot(str)
    def on_upload_progress(self, message: str):
        """Handle upload progress"""
        self.upload_status_label.setText(message)
        self.add_log(message)

    @Slot(bool, str)
    def on_upload_completed(self, success: bool, message: str):
        """Handle upload completion"""
        self.upload_button.setEnabled(True)
        self.upload_button.setText("Upload Firmware")
        self.upload_progress_bar.setVisible(False)

        if success:
            self.upload_status_label.setText("Upload successful!")
            self.upload_status_label.setStyleSheet("color: green; font-weight: bold;")
            QMessageBox.information(self, "Upload Complete", message)
        else:
            self.upload_status_label.setText("Upload failed!")
            self.upload_status_label.setStyleSheet("color: red; font-weight: bold;")
            QMessageBox.critical(self, "Upload Failed", message)

        self.add_log(message)

        if self.upload_worker:
            self.upload_worker.deleteLater()
            self.upload_worker = None

    # Connection methods
    def connect_to_device(self):
        """Connect to serial device"""
        port = self.port_combo.currentText()
        if not port:
            QMessageBox.warning(self, "Connection Error", "Please select a COM port")
            return

        try:
            # Start serial worker
            self.serial_worker = SerialReaderWorker(port, self.baud_rate)
            self.serial_worker.data_received.connect(self.on_data_received)
            self.serial_worker.error_occurred.connect(self.on_serial_error)
            self.serial_worker.connection_lost.connect(self.on_connection_lost)
            self.serial_worker.start()

            self.is_connected = True
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.start_recording_button.setEnabled(True)
            self.connection_status_label.setText(f"Connected to {port}")
            self.connection_status_label.setStyleSheet("color: green; font-weight: bold;")

            # Reset data tracking
            self.data_count = 0
            self.rate_calc_start = time.time()

            self.add_log(f"Connected to {port} at {self.baud_rate} baud")

        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect: {e}")
            self.add_log(f"Connection failed: {e}")

    def disconnect_from_device(self):
        """Disconnect from serial device"""
        if self.serial_worker:
            self.serial_worker.stop()
            self.serial_worker.wait()
            self.serial_worker = None

        # Stop recording if active
        if self.is_recording:
            self.stop_recording()

        self.is_connected = False
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.start_recording_button.setEnabled(False)
        self.connection_status_label.setText("Disconnected")
        self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")

        self.add_log("Disconnected from device")

    @Slot(dict)
    def on_data_received(self, data: dict):
        """Handle received data"""
        try:
            # Update displays
            self.pwm_lcd.display(int(data['pwm']))
            self.angle_lcd.display(data['angle'])

            # Calculate relative time
            if self.recording_start_time is None:
                self.recording_start_time = data['timestamp']

            relative_time = data['timestamp'] - self.recording_start_time

            # Add to buffer
            self.data_buffer["pwm"].append(data['pwm'])
            self.data_buffer["angle"].append(data['angle'])
            self.data_buffer["time"].append(relative_time)
            self.data_buffer["timestamp"].append(data['timestamp'])

            # Limit buffer size
            if len(self.data_buffer["pwm"]) > self.buffer_size:
                for key in self.data_buffer:
                    self.data_buffer[key] = self.data_buffer[key][-self.buffer_size:]

            # Update data rate
            self.data_count += 1
            if self.rate_calc_start:
                elapsed = time.time() - self.rate_calc_start
                if elapsed >= 1.0:
                    rate = self.data_count / elapsed
                    self.data_rate_label.setText(f"{rate:.1f} Hz")
                    self.data_count = 0
                    self.rate_calc_start = time.time()

            # Update sample count
            self.sample_count_label.setText(str(len(self.data_buffer["pwm"])))

            # Record data if recording is active
            if self.is_recording and self.recording_writer:
                self.recording_writer.writerow([
                    datetime.fromtimestamp(data['timestamp']).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    f"{relative_time:.3f}",
                    int(data['pwm']),
                    f"{data['angle']:.3f}"
                ])
                self.recording_file.flush()

        except Exception as e:
            self.add_log(f"Error processing data: {e}")

    @Slot(str)
    def on_serial_error(self, error_msg: str):
        """Handle serial error"""
        self.add_log(f"Serial error: {error_msg}")

    @Slot()
    def on_connection_lost(self):
        """Handle connection lost"""
        QMessageBox.warning(self, "Connection Lost", "Serial connection was lost")
        self.disconnect_from_device()

    # Recording methods
    def start_recording(self):
        """Start data recording"""
        try:
            # Create recordings directory
            save_path = Path.home() / "CableScope" / "pwm_recordings"
            save_path.mkdir(parents=True, exist_ok=True)

            # Generate filename
            firmware_name = self.firmware_types[self.firmware_combo.currentText()]
            filename = save_path / f"{firmware_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            # Open file for writing
            self.recording_file = open(filename, 'w', newline='')
            self.recording_writer = csv.writer(self.recording_file)

            # Write header
            self.recording_writer.writerow(['Timestamp', 'Time(s)', 'PWM', 'Angle(deg)'])

            # Reset recording start time
            self.recording_start_time = None

            self.is_recording = True
            self.start_recording_button.setEnabled(False)
            self.stop_recording_button.setEnabled(True)
            self.recording_status_label.setText("Recording...")
            self.recording_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.recording_path_label.setText(str(filename))

            self.add_log(f"Started recording to: {filename}")

        except Exception as e:
            QMessageBox.critical(self, "Recording Error", f"Failed to start recording: {e}")
            self.add_log(f"Recording error: {e}")

    def stop_recording(self):
        """Stop data recording"""
        try:
            if self.recording_file:
                self.recording_file.close()
                self.recording_file = None
                self.recording_writer = None

            self.is_recording = False
            self.start_recording_button.setEnabled(True)
            self.stop_recording_button.setEnabled(False)
            self.recording_status_label.setText("Not Recording")
            self.recording_status_label.setStyleSheet("color: gray;")

            self.add_log("Stopped recording")

        except Exception as e:
            self.add_log(f"Error stopping recording: {e}")

    # Plotting methods
    def update_plots(self):
        """Update plot with current data"""
        try:
            if len(self.data_buffer["time"]) < 2:
                return

            # Get data within time window
            times = np.array(self.data_buffer["time"])
            angles = np.array(self.data_buffer["angle"])

            # Filter to time window
            if len(times) > 0:
                max_time = times[-1]
                min_time = max(0, max_time - self.time_window)

                mask = times >= min_time
                times_filtered = times[mask]
                angles_filtered = angles[mask]

                # Update curve
                self.angle_curve.setData(times_filtered, angles_filtered)

        except Exception as e:
            self.add_log(f"Plot update error: {e}")

    def clear_plot_data(self):
        """Clear plot data"""
        self.data_buffer = {"pwm": [], "angle": [], "time": [], "timestamp": []}
        self.recording_start_time = None
        self.sample_count_label.setText("0")
        self.add_log("Plot data cleared")

    def reset_plot_zoom(self):
        """Reset plot zoom"""
        self.plot_widget.autoRange()
        self.add_log("Plot zoom reset")

    # Configuration methods
    def load_configuration(self, config: Dict[str, Any]):
        """Load configuration"""
        try:
            pwm_config = config.get("pwm_only", {})

            # Arduino CLI path
            firmware_config = config.get("firmware", {})
            cli_path = firmware_config.get("arduino_cli_path", "arduino-cli.exe")
            self.arduino_cli_path = cli_path

            # Board type
            board_type = pwm_config.get("board_type", "teensy:avr:teensy41")
            self.board_type = board_type
            if board_type in [self.board_combo.itemText(i) for i in range(self.board_combo.count())]:
                self.board_combo.setCurrentText(board_type)

            # Time window
            self.time_window = pwm_config.get("time_window", 30.0)

        except Exception as e:
            self.add_log(f"Error loading configuration: {e}")

    def save_configuration(self) -> Dict[str, Any]:
        """Save configuration"""
        return {
            "pwm_only": {
                "board_type": self.board_type,
                "time_window": self.time_window
            }
        }

    def cleanup(self):
        """Cleanup resources"""
        if self.is_connected:
            self.disconnect_from_device()

        if self.is_recording:
            self.stop_recording()
