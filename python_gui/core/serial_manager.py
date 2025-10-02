"""
Serial Communication Manager for CableScope Motor Control
Handles communication with the Arduino/Teensy firmware
"""

import serial
import serial.tools.list_ports
import struct
import time
from typing import List, Optional, Dict, Any, Tuple, Callable
from PySide6.QtCore import QObject, Signal, QTimer, QThread, QRunnable, QThreadPool
import numpy as np


class SerialCommunicationManager(QObject):
    """Manages serial communication with the motor control firmware"""

    # Communication protocol constants
    HEADER1 = 0xFF
    HEADER2 = 0xFF
    CMD_SET_TORQUE = 0x01
    CMD_GET_DATA = 0x02
    DATA_PACKET_SIZE = 13  # 1 byte cmd + 4 bytes torque + 4 bytes angle + 4 bytes PWM
    ACK_BYTE = 0xAA

    # Signals
    connection_changed = Signal(bool)  # Connected/disconnected
    data_received = Signal(dict)       # {"torque": float, "angle": float}
    error_occurred = Signal(str)       # Error message
    ports_updated = Signal(list)       # Available ports list
    command_acknowledged = Signal()     # Command ACK received
    firmware_mode_detected = Signal(str)  # "interactive" or "random_torque" mode detected

    def __init__(self):
        super().__init__()

        # Serial connection
        self.serial_port: Optional[serial.Serial] = None
        self.is_connected = False
        self.current_port = ""
        self.baud_rate = 115200
        self.timeout = 1.0

        # Communication state
        self.last_torque_command = 0.0
        self.last_data_time = time.time()
        self.data_rate = 0.0

        # Firmware mode detection (both use binary protocol, but behave differently)
        self.firmware_mode = "interactive"  # "interactive" or "random_torque"
        self.mode_detection_complete = False
        self.ack_timeout_count = 0  # Count ACK timeouts to detect random_torque firmware
        
        # Port scanning timer
        self.port_scan_timer = QTimer()
        self.port_scan_timer.timeout.connect(self.scan_ports)
        self.port_scan_timer.start(3000)  # Scan every 3 seconds
        
        # Data monitoring
        self.data_monitor_timer = QTimer()
        self.data_monitor_timer.timeout.connect(self.monitor_data_rate)
        self.data_monitor_timer.start(1000)  # Update rate every second
        
        self._last_ports = []
        self._data_count = 0
        self._last_rate_check = time.time()
        
        # Thread pool for non-blocking operations
        self.thread_pool = QThreadPool()
        
        # Port scanning control
        self._scanning_enabled = True
        
        # Initial port scan
        self.scan_ports()
    
    def get_available_ports(self) -> List[str]:
        """Get list of available serial ports"""
        try:
            ports = serial.tools.list_ports.comports()
            available_ports = [port.device for port in ports if port.device]
            print(f"DEBUG: Available ports: {available_ports}")
            for port in ports:
                print(f"DEBUG: Port {port.device}: {port.description} [{port.hwid}]")
            return available_ports
        except RecursionError:
            # Handle recursion error specifically to prevent infinite loops
            print("RecursionError occurred while scanning ports - returning empty list")
            return []
        except Exception as e:
            print(f"DEBUG: Exception in get_available_ports: {e}")
            try:
                self.error_occurred.emit(f"Error scanning ports: {e}")
            except:
                pass
            return []
    
    def find_teensy_port(self, ports: List[str]) -> Optional[str]:
        """Find the Teensy port from a list of ports"""
        try:
            all_ports = serial.tools.list_ports.comports()
            for port in all_ports:
                if port.device in ports:
                    # Check for Teensy VID:PID (16C0:0483 or other Teensy IDs)
                    hwid = port.hwid.upper()
                    if any(teensy_id in hwid for teensy_id in [
                        '16C0:0483',  # Teensy 4.x
                        '16C0:0476',  # Teensy 3.x
                        '16C0:0478',  # Teensy LC
                        'USB VID:PID=16C0'  # Any Teensy
                    ]):
                        print(f"DEBUG: Found Teensy on {port.device}: {port.description}")
                        return port.device
                        
                    # Also check for "USB Serial Device" description as fallback
                    if 'USB SERIAL DEVICE' in port.description.upper() and '16C0' in hwid:
                        print(f"DEBUG: Found USB Serial Device (likely Teensy) on {port.device}")
                        return port.device
                        
        except Exception as e:
            print(f"DEBUG: Error finding Teensy port: {e}")
            
        return None
    
    def scan_ports(self):
        """Scan for available ports and emit signal if changed"""
        if not self._scanning_enabled:
            return
            
        try:
            current_ports = self.get_available_ports()
            print(f"DEBUG: Current ports from scan: {current_ports}")
            print(f"DEBUG: Last known ports: {self._last_ports}")
            
            if current_ports != self._last_ports:
                self._last_ports = current_ports
                print(f"DEBUG: Port list changed, emitting ports_updated signal with: {current_ports}")
                self.ports_updated.emit(current_ports)
            else:
                print(f"DEBUG: Port list unchanged, not emitting signal")
                
        except RecursionError:
            print("RecursionError in scan_ports - skipping scan")
        except Exception as e:
            try:
                self.error_occurred.emit(f"Error during port scan: {e}")
            except:
                print(f"Error during port scan: {e}")
    
    def disable_scanning(self):
        """Disable port scanning (for shutdown)"""
        print("DEBUG: Port scanning disabled")
        self._scanning_enabled = False
    
    def enable_scanning(self):
        """Enable port scanning"""
        print("DEBUG: Port scanning enabled")
        self._scanning_enabled = True
    
    def force_scan_ports(self):
        """Force a port scan regardless of scanning_enabled flag"""
        print("DEBUG: Force scanning ports...")
        try:
            current_ports = self.get_available_ports()
            if current_ports != self._last_ports:
                self._last_ports = current_ports
                self.ports_updated.emit(current_ports)
                print(f"DEBUG: Emitted ports_updated signal with {len(current_ports)} ports")
            else:
                print("DEBUG: Port list unchanged")
        except RecursionError:
            print("RecursionError in force_scan_ports - skipping scan")
        except Exception as e:
            print(f"Error during force port scan: {e}")
    
    def connect_to_port(self, port: str, baud_rate: int = 115200, timeout: float = 1.0) -> bool:
        """Connect to a serial port"""
        print(f"DEBUG: Attempting to connect to {port} at {baud_rate} baud")
        
        if self.is_connected:
            print("DEBUG: Already connected, disconnecting first")
            self.disconnect()
        
        try:
            print(f"DEBUG: Opening serial port {port}")
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baud_rate,
                timeout=timeout,
                write_timeout=timeout
            )
            
            print(f"DEBUG: Serial port opened successfully: {self.serial_port}")
            
            # Wait for connection to stabilize
            print("DEBUG: Waiting for connection to stabilize...")
            time.sleep(1.0)  # Increased delay for Teensy
            
            # Clear any existing data in buffers
            print("DEBUG: Clearing buffers...")
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            
            # Test connection by sending a small torque command
            print("DEBUG: Testing communication with zero torque command...")
            test_success = self.send_torque_command(0.0, force_send=True)

            # Check if this is random_torque firmware (doesn't respond to commands)
            if not test_success:
                print("DEBUG: No ACK received - checking if this is random_torque firmware...")
                # Wait a moment for potential data packets
                time.sleep(0.5)
                # If we received data without sending commands, it's random_torque firmware
                if self.serial_port.in_waiting > 10:
                    print("DEBUG: Detected random_torque firmware (autonomous mode)")
                    self.firmware_mode = "random_torque"
                    self.mode_detection_complete = True
                    test_success = True  # Mark as successful connection
                    self.firmware_mode_detected.emit("random_torque")
                else:
                    print("DEBUG: Communication test failed - no response")
                    self.serial_port.close()
                    self.serial_port = None
                    self.error_occurred.emit(f"Failed to communicate with device on {port}")
                    return False
            else:
                print("DEBUG: ACK received - interactive firmware detected")
                self.firmware_mode = "interactive"
                self.mode_detection_complete = True
                self.firmware_mode_detected.emit("interactive")

            # Connection successful
            print("DEBUG: Communication test successful")
            self.is_connected = True
            self.current_port = port
            self.baud_rate = baud_rate
            self.timeout = timeout
            self.connection_changed.emit(True)
            return True
            
        except serial.SerialException as e:
            print(f"DEBUG: Serial exception: {e}")
            self.error_occurred.emit(f"Failed to connect to {port}: {e}")
            return False
        except Exception as e:
            print(f"DEBUG: Unexpected exception: {e}")
            self.error_occurred.emit(f"Unexpected error connecting to {port}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from current port"""
        if self.serial_port and self.serial_port.is_open:
            try:
                # Send zero torque command before disconnecting (only for interactive mode)
                if self.firmware_mode == "interactive":
                    self.send_torque_command(0.0)
                    time.sleep(0.1)
                self.serial_port.close()
            except Exception as e:
                self.error_occurred.emit(f"Error closing port: {e}")

        self.serial_port = None
        self.is_connected = False
        self.current_port = ""

        # Reset firmware mode detection for next connection
        self.firmware_mode = "interactive"
        self.mode_detection_complete = False
        self.ack_timeout_count = 0

        self.connection_changed.emit(False)
    
    def send_torque_command(self, torque: float, force_send: bool = False) -> bool:
        """Send torque command to the firmware (only for interactive mode)"""
        # Random torque firmware doesn't accept/respond to torque commands
        if self.firmware_mode == "random_torque":
            print("DEBUG: Torque commands not supported in random_torque mode")
            return True  # Return True to avoid errors

        if not force_send and (not self.is_connected or not self.serial_port):
            print(f"DEBUG: Cannot send torque command - connected: {self.is_connected}, port: {self.serial_port}")
            return False

        if not self.serial_port:
            print("DEBUG: No serial port available")
            return False
        
        try:
            print(f"DEBUG: Sending torque command: {torque}")
            
            # Create command packet: Header(2) + Command(1) + Torque(4)
            packet = bytearray()
            packet.append(self.HEADER1)
            packet.append(self.HEADER2)
            packet.append(self.CMD_SET_TORQUE)
            
            # Pack torque as float (little-endian)
            torque_bytes = struct.pack('<f', torque)
            packet.extend(torque_bytes)
            
            print(f"DEBUG: Packet to send: {' '.join(f'0x{b:02X}' for b in packet)}")
            
            # Send packet
            self.serial_port.write(packet)
            self.serial_port.flush()  # Ensure data is sent
            self.last_torque_command = torque
            
            print("DEBUG: Packet sent, waiting for acknowledgment...")
            
            # Wait for acknowledgment (with timeout)
            # Need to parse through potential data packets to find ACK
            start_time = time.time()
            buffer = bytearray()
            
            while time.time() - start_time < 2.0:  # 2 seconds timeout
                if self.serial_port.in_waiting > 0:
                    new_data = self.serial_port.read(self.serial_port.in_waiting)
                    buffer.extend(new_data)
                    print(f"DEBUG: Buffer now contains {len(buffer)} bytes")
                    
                    # Look for ACK pattern in buffer
                    for i in range(len(buffer) - 2):
                        if (buffer[i] == self.HEADER1 and 
                            buffer[i+1] == self.HEADER2 and 
                            buffer[i+2] == self.ACK_BYTE):
                            print(f"DEBUG: Found ACK at position {i}")
                            print("DEBUG: Valid acknowledgment received")
                            self.command_acknowledged.emit()
                            return True
                    
                    # Remove processed data to prevent buffer overflow
                    if len(buffer) > 100:  # Keep last 100 bytes
                        buffer = buffer[-100:]
                        
                time.sleep(0.01)
            
            print("DEBUG: Timeout waiting for acknowledgment")
            self.error_occurred.emit("Torque command acknowledgment timeout")
            return False
            
        except Exception as e:
            print(f"DEBUG: Exception in send_torque_command: {e}")
            self.error_occurred.emit(f"Error sending torque command: {e}")
            return False
    
    def read_data_packet(self) -> Optional[Dict[str, float]]:
        """Read a data packet from the firmware (binary protocol)"""
        if not self.is_connected or not self.serial_port:
            return None

        try:
            # Check if enough data is available
            if self.serial_port.in_waiting < 16:  # Full packet size (header + size + data + checksum)
                return None

            # Read and verify headers
            header_data = self.serial_port.read(3)
            if (len(header_data) != 3 or
                header_data[0] != self.HEADER1 or
                header_data[1] != self.HEADER2):
                # Clear buffer and try again
                self.serial_port.reset_input_buffer()
                return None
            
            packet_size = header_data[2]
            if packet_size != self.DATA_PACKET_SIZE:
                self.serial_port.reset_input_buffer()
                return None
            
            # Read remaining packet data (data + checksum)
            remaining_data = self.serial_port.read(packet_size + 1)  # +1 for checksum
            if len(remaining_data) != packet_size + 1:
                return None
            
            # Extract command type
            command = remaining_data[0]
            if command != self.CMD_GET_DATA:
                return None
            
            # Extract torque (4 bytes)
            torque_bytes = remaining_data[1:5]
            torque = struct.unpack('<f', torque_bytes)[0]
            
            # Extract angle (4 bytes)
            angle_bytes = remaining_data[5:9]
            angle = struct.unpack('<f', angle_bytes)[0]

            # Extract PWM (4 bytes)
            pwm_bytes = remaining_data[9:13]
            pwm = struct.unpack('<f', pwm_bytes)[0]

            # Verify checksum (must match firmware calculation)
            # Firmware calculates checksum for packet[2] through packet[15] (bytes 2-15)
            # This corresponds to: packet_size + remaining_data[:-1]
            received_checksum = remaining_data[13]  # Checksum is at index 13 (14th byte)
            calculated_checksum = 0

            # Add packet size byte (packet[2] in firmware)
            calculated_checksum += packet_size

            # Add remaining data bytes except the checksum itself (packet[3] through packet[15])
            for byte in remaining_data[:13]:  # First 13 bytes (command + torque + angle + pwm)
                calculated_checksum += byte
                
            calculated_checksum = (~calculated_checksum + 1) & 0xFF  # Two's complement
            
            if received_checksum != calculated_checksum:
                print(f"DEBUG: Checksum mismatch - received: 0x{received_checksum:02X}, calculated: 0x{calculated_checksum:02X}")
                print(f"DEBUG: Packet size: 0x{packet_size:02X}")
                print(f"DEBUG: Data bytes: {' '.join(f'0x{b:02X}' for b in remaining_data[:13])}")
                self.error_occurred.emit(f"Data packet checksum verification failed (got 0x{received_checksum:02X}, expected 0x{calculated_checksum:02X})")
                return None
            else:
                print("DEBUG: Checksum verification passed")

            # Update statistics
            self._data_count += 1
            self.last_data_time = time.time()

            return {"torque": float(torque), "angle": float(angle), "pwm": float(pwm)}
            
        except struct.error as e:
            self.error_occurred.emit(f"Error unpacking data: {e}")
            return None
        except Exception as e:
            self.error_occurred.emit(f"Error reading data packet: {e}")
            return None
    
    def start_data_reading(self):
        """Start continuous data reading in a separate thread"""
        if not self.is_connected:
            return False
        
        # Create and start data reading worker
        worker = DataReadingWorker(self)
        worker.data_received.connect(self.data_received.emit)
        worker.error_occurred.connect(self.error_occurred.emit)
        self.thread_pool.start(worker)
        
        return True
    
    def monitor_data_rate(self):
        """Monitor and calculate data reception rate"""
        current_time = time.time()
        time_delta = current_time - self._last_rate_check
        
        if time_delta > 0:
            self.data_rate = self._data_count / time_delta
            self._data_count = 0
            self._last_rate_check = current_time
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get current connection information"""
        return {
            "connected": self.is_connected,
            "port": self.current_port,
            "baud_rate": self.baud_rate,
            "timeout": self.timeout,
            "data_rate": self.data_rate,
            "last_torque_command": self.last_torque_command
        }
    
    def flush_buffers(self):
        """Flush input and output buffers"""
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
            except Exception as e:
                self.error_occurred.emit(f"Error flushing buffers: {e}")
    
    def set_timeout(self, timeout: float):
        """Set read timeout"""
        self.timeout = timeout
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.timeout = timeout
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            if hasattr(self, 'serial_port') and self.serial_port:
                if self.serial_port.is_open:
                    self.send_torque_command(0.0)  # Safe shutdown
                    time.sleep(0.1)
                    self.serial_port.close()
        except Exception:
            pass  # Ignore cleanup errors


class DataReadingWorker(QRunnable):
    """Worker thread for continuous data reading"""
    
    def __init__(self, serial_manager: SerialCommunicationManager):
        super().__init__()
        self.serial_manager = serial_manager
        self.signals = DataReadingSignals()
        self.running = True
    
    @property
    def data_received(self):
        return self.signals.data_received
    
    @property 
    def error_occurred(self):
        return self.signals.error_occurred
    
    def run(self):
        """Main data reading loop"""
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while (self.running and 
               self.serial_manager.is_connected and 
               consecutive_errors < max_consecutive_errors):
            
            try:
                # Read data packet
                data = self.serial_manager.read_data_packet()
                
                if data is not None:
                    self.signals.data_received.emit(data)
                    consecutive_errors = 0  # Reset error counter
                
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors < max_consecutive_errors:
                    time.sleep(0.1)  # Wait longer on errors
                else:
                    self.signals.error_occurred.emit(f"Too many consecutive read errors: {e}")
                    break
    
    def stop(self):
        """Stop the data reading worker"""
        self.running = False


class DataReadingSignals(QObject):
    """Signals for the data reading worker"""
    data_received = Signal(dict)
    error_occurred = Signal(str)