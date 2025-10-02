"""
Main Window for CableScope Motor Control
Central GUI component with tabbed interface
"""

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QWidget, 
    QMenuBar, QMenu, QStatusBar, QMessageBox, QApplication
)
from PySide6.QtCore import QTimer, Signal, Slot, Qt
from PySide6.QtGui import QAction, QKeySequence, QIcon
from typing import Dict, Any, Optional
import numpy as np
from pathlib import Path

# Core imports
from core.config_manager import ConfigManager
from core.serial_manager import SerialCommunicationManager
from core.error_handler import ErrorHandler

# GUI imports
from gui.tabs.control_plots_tab import ControlPlotsTab
from gui.tabs.settings_tab import SettingsTab
from gui.tabs.firmware_tab import FirmwareTab
from gui.widgets.status_bar import EnhancedStatusBar
from gui.styles.theme import ThemeManager


class MainWindow(QMainWindow):
    """Main application window with tabbed interface"""
    
    # Signals
    window_closing = Signal()
    
    def __init__(self):
        super().__init__()
        
        # Initialize core components
        self.config_manager = ConfigManager()
        self.serial_manager = SerialCommunicationManager()
        self.error_handler = ErrorHandler()
        self.theme_manager = ThemeManager()
        
        # Application state
        self.is_data_acquisition_active = False
        self.current_data = {"torque": 0.0, "angle": 0.0, "pwm": 0.0}
        self.data_buffer = {"torque": [], "angle": [], "pwm": [], "time": []}
        self.buffer_size = 1000
        self._loading_configuration = False  # Flag to prevent recursion
        
        # Setup UI
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_status_bar()
        self.load_configuration()
        self.apply_theme()
        
        # Setup connections AFTER all components are initialized
        self.setup_connections()
        
        # Start systems
        self.start_systems()
    
    def setup_ui(self):
        """Setup the main user interface"""
        # Window properties
        self.setWindowTitle("CableScope Motor Control")
        self.setMinimumSize(1000, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.control_plots_tab = ControlPlotsTab()
        self.settings_tab = SettingsTab()
        self.firmware_tab = FirmwareTab()
        
        # Add tabs
        self.tab_widget.addTab(self.control_plots_tab, "Control & Plots")
        self.tab_widget.addTab(self.settings_tab, "Settings")
        self.tab_widget.addTab(self.firmware_tab, "Firmware")
        
        # Set initial tab
        self.tab_widget.setCurrentIndex(0)
    
    def setup_menu_bar(self):
        """Setup application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # New session
        new_action = QAction("New Session", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_session)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        # Import/Export configuration
        import_config_action = QAction("Import Configuration...", self)
        import_config_action.setShortcut(QKeySequence.StandardKey.Open)
        import_config_action.triggered.connect(self.import_configuration)
        file_menu.addAction(import_config_action)
        
        export_config_action = QAction("Export Configuration...", self)
        export_config_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        export_config_action.triggered.connect(self.export_configuration)
        file_menu.addAction(export_config_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Control menu
        control_menu = menubar.addMenu("Control")
        
        # Start/Stop data acquisition
        self.start_action = QAction("Start Data Acquisition", self)
        self.start_action.setShortcut("F5")
        self.start_action.triggered.connect(self.start_data_acquisition)
        control_menu.addAction(self.start_action)
        
        self.stop_action = QAction("Stop Data Acquisition", self)
        self.stop_action.setShortcut("F6")
        self.stop_action.triggered.connect(self.stop_data_acquisition)
        self.stop_action.setEnabled(False)
        control_menu.addAction(self.stop_action)
        
        control_menu.addSeparator()
        
        # Emergency stop
        emergency_stop_action = QAction("Emergency Stop", self)
        emergency_stop_action.setShortcut("Ctrl+E")
        emergency_stop_action.triggered.connect(self.emergency_stop)
        control_menu.addAction(emergency_stop_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        # Theme toggle
        toggle_theme_action = QAction("Toggle Theme", self)
        toggle_theme_action.setShortcut("Ctrl+T")
        toggle_theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(toggle_theme_action)
        
        # Reset plots
        reset_plots_action = QAction("Reset All Plots", self)
        reset_plots_action.setShortcut("Ctrl+R")
        reset_plots_action.triggered.connect(self.reset_plots)
        view_menu.addAction(reset_plots_action)
        
        # Clear data
        clear_data_action = QAction("Clear Data Buffer", self)
        clear_data_action.setShortcut("Ctrl+L")
        clear_data_action.triggered.connect(self.clear_data_buffer)
        view_menu.addAction(clear_data_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        # Refresh ports
        refresh_ports_action = QAction("Refresh COM Ports", self)
        refresh_ports_action.triggered.connect(self.serial_manager.force_scan_ports)
        tools_menu.addAction(refresh_ports_action)
        
        # Connection test
        test_connection_action = QAction("Test Connection", self)
        test_connection_action.triggered.connect(self.test_connection)
        tools_menu.addAction(test_connection_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        # About
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_status_bar(self):
        """Setup enhanced status bar"""
        self.enhanced_status_bar = EnhancedStatusBar()
        self.setStatusBar(self.enhanced_status_bar)
    
    def setup_connections(self):
        """Setup signal connections between components"""
        print("DEBUG: Setting up signal connections...")
        
        # Serial manager connections
        self.serial_manager.connection_changed.connect(self.on_connection_changed)
        self.serial_manager.data_received.connect(self.on_data_received)
        self.serial_manager.error_occurred.connect(self.on_serial_error)
        self.serial_manager.ports_updated.connect(self.on_ports_updated)
        self.serial_manager.command_acknowledged.connect(self.on_command_acknowledged)
        self.serial_manager.firmware_mode_detected.connect(self.on_firmware_mode_detected)

        print("DEBUG: Serial manager signals connected")

        # Error handler connections
        self.error_handler.error_occurred.connect(self.on_error_occurred)
        self.error_handler.warning_occurred.connect(self.on_warning_occurred)

        # Control & Plots tab connections
        self.control_plots_tab.torque_command_requested.connect(self.send_torque_command)
        self.control_plots_tab.connection_requested.connect(self.connect_to_port)
        self.control_plots_tab.disconnection_requested.connect(self.disconnect_from_port)
        self.control_plots_tab.data_acquisition_start_requested.connect(self.start_data_acquisition)
        self.control_plots_tab.data_acquisition_stop_requested.connect(self.stop_data_acquisition)
        self.control_plots_tab.emergency_stop_requested.connect(self.emergency_stop)
        self.control_plots_tab.plot_settings_changed.connect(self.on_plot_settings_changed)
        self.control_plots_tab.recording_start_requested.connect(self.start_recording)
        self.control_plots_tab.recording_stop_requested.connect(self.stop_recording)
        self.control_plots_tab.refresh_ports_requested.connect(self.serial_manager.force_scan_ports)

        # Connect command acknowledgment to UI feedback
        self.serial_manager.command_acknowledged.connect(self.control_plots_tab.on_command_acknowledged)
        
        # Settings tab connections  
        self.settings_tab.configuration_changed.connect(self.on_configuration_changed)
        self.settings_tab.configuration_saved.connect(self.save_configuration)
        
        # Firmware tab connections
        self.firmware_tab.firmware_upload_requested.connect(self.upload_firmware)
        self.firmware_tab.firmware_path_changed.connect(self.on_firmware_path_changed)
    
    def load_configuration(self):
        """Load application configuration"""
        try:
            # Prevent recursion during configuration loading
            if self._loading_configuration:
                return
            self._loading_configuration = True
            
            # Load config
            config = self.config_manager.load_config()
            
            # Apply window settings
            ui_config = self.config_manager.get_ui_config()
            window_size = ui_config.get("window_size", [1000, 700])
            self.resize(*window_size)
            
            # Set buffer size
            data_config = self.config_manager.get_data_acquisition_config()
            self.buffer_size = data_config.get("buffer_size", 1000)
            
            # Pass configuration to tabs
            self.control_plots_tab.load_configuration(config)
            self.settings_tab.load_configuration(config)
            self.firmware_tab.load_configuration(config)
            
        except Exception as e:
            self.error_handler.log_error("ConfigurationLoad", f"Failed to load configuration: {e}")
        finally:
            self._loading_configuration = False
    
    def apply_theme(self):
        """Apply current theme to the application"""
        try:
            ui_config = self.config_manager.get_ui_config()
            theme = ui_config.get("theme", "dark")
            self.theme_manager.apply_theme(self, theme)
        except Exception as e:
            self.error_handler.log_warning(f"Failed to apply theme: {e}")
    
    def start_systems(self):
        """Start background systems"""
        print("DEBUG: Starting systems...")
        
        # Clear any previous port cache to ensure fresh scan
        self.serial_manager._last_ports = []
        print("DEBUG: Cleared port cache")
        
        # Ensure scanning is enabled
        self.serial_manager.enable_scanning()
        
        # Start port scanning
        print("DEBUG: Initial port scan...")
        self.serial_manager.scan_ports()
        
        # Force initial population of port list
        print("DEBUG: Force scanning ports for initial population...")
        self.serial_manager.force_scan_ports()
        
        # Setup data update timer
        self.data_update_timer = QTimer()
        self.data_update_timer.timeout.connect(self.update_displays)
        self.data_update_timer.start(50)  # 20 Hz update rate
        
        # Setup periodic port scanning timer
        self.port_scan_timer = QTimer()
        self.port_scan_timer.timeout.connect(self.serial_manager.scan_ports)
        self.port_scan_timer.start(3000)  # Scan every 3 seconds
        print("DEBUG: Port scanning timer started")
    
    # Data acquisition methods
    def start_data_acquisition(self):
        """Start data acquisition"""
        if self.is_data_acquisition_active:
            return
        
        if not self.serial_manager.is_connected:
            QMessageBox.warning(self, "Connection Required", 
                              "Please connect to a device before starting data acquisition.")
            return
        
        try:
            # Start data reading
            if self.serial_manager.start_data_reading():
                self.is_data_acquisition_active = True
                
                # Update UI
                self.start_action.setEnabled(False)
                self.stop_action.setEnabled(True)
                self.control_plots_tab.set_data_acquisition_active(True)
                
                # Update status
                self.enhanced_status_bar.set_data_acquisition_status(True)
                self.enhanced_status_bar.show_message("Data acquisition started", 3000)
                
                self.error_handler.log_info("Data acquisition started")
            else:
                self.error_handler.log_error("DataAcquisition", "Failed to start data reading")
                
        except Exception as e:
            self.error_handler.log_error("DataAcquisition", f"Error starting data acquisition: {e}")
    
    def stop_data_acquisition(self):
        """Stop data acquisition"""
        if not self.is_data_acquisition_active:
            return
        
        try:
            self.is_data_acquisition_active = False
            
            # Update UI
            self.start_action.setEnabled(True)
            self.stop_action.setEnabled(False)
            self.control_plots_tab.set_data_acquisition_active(False)
            
            # Stop recording if active
            self.control_plots_tab.stop_recording()
            
            # Update status
            self.enhanced_status_bar.set_data_acquisition_status(False)
            self.enhanced_status_bar.show_message("Data acquisition stopped", 3000)
            
            self.error_handler.log_info("Data acquisition stopped")
            
        except Exception as e:
            self.error_handler.log_error("DataAcquisition", f"Error stopping data acquisition: {e}")
    
    def stop_data_acquisition_silent(self):
        """Stop data acquisition without showing status messages"""
        if not self.is_data_acquisition_active:
            return
        
        try:
            self.is_data_acquisition_active = False
            
            # Update UI
            self.start_action.setEnabled(True)
            self.stop_action.setEnabled(False)
            self.control_plots_tab.set_data_acquisition_active(False)
            
            # Stop recording if active
            self.control_plots_tab.stop_recording()
            
            # Update status (without messages)
            self.enhanced_status_bar.set_data_acquisition_status(False)
            
            self.error_handler.log_info("Data acquisition stopped")
            
        except Exception as e:
            self.error_handler.log_error("DataAcquisition", f"Error stopping data acquisition: {e}")
    
    def emergency_stop(self):
        """Emergency stop - immediately set torque to zero and stop data acquisition"""
        try:
            # Send zero torque command
            self.serial_manager.send_torque_command(0.0)
            
            # Stop data acquisition
            self.stop_data_acquisition()
            
            # Update control tab
            self.control_plots_tab.emergency_stop()
            
            # Show message
            QMessageBox.information(self, "Emergency Stop", 
                                  "Emergency stop activated. Motor torque set to zero.")
            
            self.error_handler.log_info("Emergency stop activated")
            
        except Exception as e:
            self.error_handler.log_error("EmergencyStop", f"Error during emergency stop: {e}")
            QMessageBox.critical(self, "Emergency Stop Error", 
                               f"Error during emergency stop: {e}")
    
    # Connection methods
    def connect_to_port(self, port: str):
        """Connect to specified port"""
        print(f"DEBUG: Main window connect_to_port called with port: {port}")
        try:
            serial_config = self.config_manager.get_serial_config()
            baud_rate = serial_config.get("baud_rate", 115200)
            timeout = serial_config.get("timeout", 1.0)
            
            print(f"DEBUG: Attempting connection with baud_rate: {baud_rate}, timeout: {timeout}")
            
            if self.serial_manager.connect_to_port(port, baud_rate, timeout):
                self.config_manager.set_serial_port(port)
                self.error_handler.log_info(f"Connected to {port}")
                print(f"DEBUG: Successfully connected to {port}")
            else:
                print(f"DEBUG: Failed to connect to {port}")
            
        except Exception as e:
            print(f"DEBUG: Exception in connect_to_port: {e}")
            self.error_handler.log_error("Connection", f"Error connecting to {port}: {e}")
    
    def disconnect_from_port(self):
        """Disconnect from current port"""
        try:
            if self.is_data_acquisition_active:
                self.stop_data_acquisition()
            
            self.serial_manager.disconnect()
            self.error_handler.log_info("Disconnected from serial port")
            
        except Exception as e:
            self.error_handler.log_error("Connection", f"Error disconnecting: {e}")
    
    def test_connection(self):
        """Test current connection"""
        if not self.serial_manager.is_connected:
            QMessageBox.information(self, "Connection Test", "No active connection to test.")
            return
        
        try:
            # Send test command
            success = self.serial_manager.send_torque_command(0.0)
            
            if success:
                info = self.serial_manager.get_connection_info()
                message = (f"Connection test successful!\n\n"
                          f"Port: {info['port']}\n"
                          f"Baud Rate: {info['baud_rate']}\n"
                          f"Data Rate: {info['data_rate']:.1f} Hz")
                QMessageBox.information(self, "Connection Test", message)
            else:
                QMessageBox.warning(self, "Connection Test", "Connection test failed.")
                
        except Exception as e:
            QMessageBox.critical(self, "Connection Test", f"Connection test error: {e}")
    
    # Command methods
    def send_torque_command(self, torque: float):
        """Send torque command to device"""
        try:
            if self.serial_manager.send_torque_command(torque):
                self.enhanced_status_bar.set_last_torque_command(torque)
            
        except Exception as e:
            self.error_handler.log_error("TorqueCommand", f"Error sending torque command: {e}")
    
    # Data methods
    def update_displays(self):
        """Update all displays with current data"""
        if self.current_data:
            # Update control tab
            self.control_plots_tab.update_current_values(self.current_data)
            
            # Update status bar
            self.enhanced_status_bar.update_current_values(self.current_data)
    
    def clear_data_buffer(self):
        """Clear the data buffer"""
        self.data_buffer = {"torque": [], "angle": [], "pwm": [], "time": []}
        self.control_plots_tab.clear_all_data()
        self.enhanced_status_bar.show_message("Data buffer cleared", 2000)
    
    def reset_plots(self):
        """Reset all plot zoom and ranges"""
        self.control_plots_tab.reset_all_plots()
        self.enhanced_status_bar.show_message("Plot ranges reset", 2000)
    
    # Recording methods
    def start_recording(self, filename: str):
        """Start data recording"""
        try:
            # Implementation will be added in data recording functionality
            pass
        except Exception as e:
            self.error_handler.log_error("Recording", f"Error starting recording: {e}")
    
    def stop_recording(self):
        """Stop data recording"""
        try:
            # Implementation will be added in data recording functionality
            pass
        except Exception as e:
            self.error_handler.log_error("Recording", f"Error stopping recording: {e}")
    
    # Configuration methods
    def save_configuration(self):
        """Save current configuration"""
        try:
            # Get current window size
            size = self.size()
            self.config_manager.set_window_size(size.width(), size.height())
            
            # Save from tabs
            self.settings_tab.save_configuration()
            
            # Save firmware tab configuration (Arduino CLI path, etc.)
            firmware_config = self.firmware_tab.save_configuration()
            if firmware_config:
                current_config = self.config_manager.get_full_config()
                current_config.update(firmware_config)
                self.config_manager.save_config(current_config)
            
            self.enhanced_status_bar.show_message("Configuration saved", 2000)
            
        except Exception as e:
            self.error_handler.log_error("Configuration", f"Error saving configuration: {e}")
    
    def save_configuration_silent(self):
        """Save current configuration without showing status messages"""
        try:
            # Get current window size  
            size = self.size()
            self.config_manager.set_window_size(size.width(), size.height())
            
            # Save firmware tab configuration (Arduino CLI path, etc.) 
            firmware_config = self.firmware_tab.save_configuration()
            current_config = self.config_manager.get_full_config()
            if firmware_config:
                current_config.update(firmware_config)
            
            # Save configuration directly without going through settings tab to avoid recursion
            self.config_manager.save_config(current_config)
            
        except RecursionError:
            print("RecursionError in save_configuration_silent - skipping save")
        except Exception as e:
            try:
                self.error_handler.log_error("Configuration", f"Error saving configuration: {e}")
            except:
                print(f"Error saving configuration: {e}")
    
    def import_configuration(self):
        """Import configuration from file"""
        self.settings_tab.import_configuration()
    
    def export_configuration(self):
        """Export configuration to file"""
        self.settings_tab.export_configuration()
    
    def new_session(self):
        """Start a new session"""
        reply = QMessageBox.question(self, "New Session", 
                                   "Start a new session? This will clear all current data.",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Stop data acquisition
            if self.is_data_acquisition_active:
                self.stop_data_acquisition()
            
            # Clear data
            self.clear_data_buffer()
            
            # Reset controls
            self.control_plots_tab.reset_controls()
            
            self.enhanced_status_bar.show_message("New session started", 3000)
    
    # Theme methods
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        try:
            ui_config = self.config_manager.get_ui_config()
            current_theme = ui_config.get("theme", "dark")
            new_theme = "light" if current_theme == "dark" else "dark"
            
            self.config_manager.set_theme(new_theme)
            self.theme_manager.apply_theme(self, new_theme)
            
            self.enhanced_status_bar.show_message(f"Theme changed to {new_theme}", 2000)
            
        except Exception as e:
            self.error_handler.log_error("Theme", f"Error toggling theme: {e}")
    
    # Firmware methods
    def upload_firmware(self, firmware_path: str, board_type: str):
        """Upload firmware to device"""
        try:
            # Implementation will be added in firmware upload functionality
            pass
        except Exception as e:
            self.error_handler.log_error("Firmware", f"Error uploading firmware: {e}")
    
    # Signal handlers
    @Slot(bool)
    def on_connection_changed(self, connected: bool):
        """Handle connection status change"""
        self.control_plots_tab.set_connection_status(connected)
        self.enhanced_status_bar.set_connection_status(
            connected, 
            self.serial_manager.current_port if connected else ""
        )
        
        if not connected and self.is_data_acquisition_active:
            self.stop_data_acquisition()
    
    @Slot(list)
    def on_ports_updated(self, ports: list):
        """Handle available ports update"""
        print(f"DEBUG: Main window received ports_updated signal with: {ports}")
        self.control_plots_tab.update_available_ports(ports)
    
    @Slot(dict)
    def on_data_received(self, data: dict):
        """Handle new data from device"""
        try:
            # Update current data
            self.current_data = data.copy()
            
            # Add to buffer
            import time
            current_time = time.time()
            
            self.data_buffer["torque"].append(data["torque"])
            self.data_buffer["angle"].append(data["angle"])
            self.data_buffer["pwm"].append(data.get("pwm", 0.0))  # Handle legacy data without PWM
            self.data_buffer["time"].append(current_time)

            # Limit buffer size
            if len(self.data_buffer["torque"]) > self.buffer_size:
                self.data_buffer["torque"] = self.data_buffer["torque"][-self.buffer_size:]
                self.data_buffer["angle"] = self.data_buffer["angle"][-self.buffer_size:]
                self.data_buffer["pwm"] = self.data_buffer["pwm"][-self.buffer_size:]
                self.data_buffer["time"] = self.data_buffer["time"][-self.buffer_size:]
            
            # Update plotting tab
            self.control_plots_tab.update_data(self.data_buffer)
            
            # Update status bar
            self.enhanced_status_bar.increment_data_count()
            
        except Exception as e:
            self.error_handler.log_error("DataProcessing", f"Error processing received data: {e}")
    
    @Slot(str)
    def on_serial_error(self, error_msg: str):
        """Handle serial communication error"""
        try:
            self.enhanced_status_bar.show_message(f"Serial Error: {error_msg}", 5000)
        except RecursionError:
            # Prevent recursion in error handling
            print(f"Serial Error (recursion prevented): {error_msg}")
        except Exception:
            # Catch any other exceptions to prevent cascading errors
            print(f"Serial Error (exception in handler): {error_msg}")
    
    @Slot()
    def on_command_acknowledged(self):
        """Handle command acknowledgment"""
        self.enhanced_status_bar.set_last_command_time()

    @Slot(str)
    def on_firmware_mode_detected(self, mode: str):
        """Handle firmware mode detection"""
        print(f"DEBUG: Firmware mode detected: {mode}")
        # Update control tab with firmware mode
        if hasattr(self, 'control_plots_tab'):
            self.control_plots_tab.set_firmware_mode(mode)
        # Show notification to user
        mode_display = "Interactive Control" if mode == "interactive" else "Random Torque (Autonomous)"
        self.enhanced_status_bar.show_message(f"Firmware Mode: {mode_display}", 5000)

    @Slot(str, str)
    def on_error_occurred(self, error_type: str, message: str):
        """Handle error from error handler"""
        try:
            self.enhanced_status_bar.show_message(f"Error: {message}", 5000)
        except RecursionError:
            # Prevent recursion in error handling
            print(f"Error (recursion prevented): {error_type}: {message}")
        except Exception:
            # Catch any other exceptions to prevent cascading errors
            print(f"Error (exception in handler): {error_type}: {message}")
    
    @Slot(str)
    def on_warning_occurred(self, message: str):
        """Handle warning from error handler"""
        try:
            self.enhanced_status_bar.show_message(f"Warning: {message}", 3000)
        except RecursionError:
            # Prevent recursion in error handling
            print(f"Warning (recursion prevented): {message}")
        except Exception:
            # Catch any other exceptions to prevent cascading errors
            print(f"Warning (exception in handler): {message}")
    
    @Slot(dict)
    def on_configuration_changed(self, config: dict):
        """Handle configuration change"""
        # Prevent recursion during configuration loading
        if self._loading_configuration:
            return
        # Reload configuration in all tabs
        self.load_configuration()
    
    @Slot(dict)
    def on_plot_settings_changed(self, settings: dict):
        """Handle plot settings change"""
        # Update plotting configuration
        pass
    
    @Slot(str)
    def on_firmware_path_changed(self, path: str):
        """Handle firmware path change"""
        self.config_manager.set_firmware_path(path)
    
    # Utility methods
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About CableScope",
            "CableScope Motor Control v1.0\n\n"
            "A comprehensive motor control and data acquisition system\n"
            "for cable-driven robotic applications.\n\n"
            "Built with PySide6 and PyQtGraph\n"
            "© 2024 Cable Robotics"
        )
    
    def closeEvent(self, event):
        """Handle application close"""
        try:
            # Emit closing signal
            self.window_closing.emit()
            
            # Stop all timers first
            if hasattr(self, 'data_update_timer'):
                self.data_update_timer.stop()
            if hasattr(self, 'port_scan_timer'):
                self.port_scan_timer.stop()
            
            # Cleanup tabs
            if hasattr(self, 'control_plots_tab'):
                self.control_plots_tab.cleanup()
            
            # Stop data acquisition
            if self.is_data_acquisition_active:
                self.stop_data_acquisition_silent()
            
            # Send zero torque command before closing
            if hasattr(self, 'serial_manager') and self.serial_manager.is_connected:
                try:
                    self.serial_manager.send_torque_command(0.0)
                    import time
                    time.sleep(0.1)  # Allow time for command to be sent
                except:
                    pass  # Ignore errors during shutdown
            
            # Save configuration (without showing status messages)
            self.save_configuration_silent()
            
            # Disconnect serial
            if hasattr(self, 'serial_manager'):
                self.serial_manager.disconnect()
            
            # Disable port scanning only at the very end to prevent recursion
            if hasattr(self, 'serial_manager'):
                self.serial_manager.disable_scanning()
            
            # Force quit application
            QApplication.instance().quit()
            
            # Accept the close event
            event.accept()
            
        except Exception as e:
            try:
                self.error_handler.log_error("Shutdown", f"Error during application shutdown: {e}")
            except:
                print(f"Error during application shutdown: {e}")
            
            # Force quit even if there are errors
            QApplication.instance().quit()
            event.accept()