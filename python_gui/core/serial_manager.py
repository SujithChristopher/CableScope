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
    DATA_PACKET_SIZE = 9  # 1 byte cmd + 4 bytes torque + 4 bytes angle
    ACK_BYTE = 0xAA
    
    # Signals
    connection_changed = Signal(bool)  # Connected/disconnected
    data_received = Signal(dict)       # {"torque": float, "angle": float}
    error_occurred = Signal(str)       # Error message
    ports_updated = Signal(list)       # Available ports list
    command_acknowledged = Signal()     # Command ACK received
    
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
            return [port.device for port in ports if port.device]
        except RecursionError:
            # Handle recursion error specifically to prevent infinite loops
            print("RecursionError occurred while scanning ports - returning empty list")
            return []
        except Exception as e:
            self.error_occurred.emit(f"Error scanning ports: {e}")
            return []
    
    def scan_ports(self):
        """Scan for available ports and emit signal if changed"""
        if not self._scanning_enabled:
            return
            
        try:
            current_ports = self.get_available_ports()
            if current_ports != self._last_ports:
                self._last_ports = current_ports
                self.ports_updated.emit(current_ports)
        except RecursionError:
            print("RecursionError in scan_ports - skipping scan")
        except Exception as e:
            try:
                self.error_occurred.emit(f"Error during port scan: {e}")
            except:
                print(f"Error during port scan: {e}")
    
    def disable_scanning(self):
        """Disable port scanning (for shutdown)"""
        self._scanning_enabled = False
    
    def connect_to_port(self, port: str, baud_rate: int = 115200, timeout: float = 1.0) -> bool:
        """Connect to a serial port"""
        if self.is_connected:
            self.disconnect()
        
        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baud_rate,
                timeout=timeout,
                write_timeout=timeout
            )
            
            # Wait for connection to stabilize
            time.sleep(0.5)
            
            # Clear any existing data in buffers
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            
            # Test connection by sending a small torque command
            test_success = self.send_torque_command(0.0)
            
            if test_success:
                self.is_connected = True
                self.current_port = port
                self.baud_rate = baud_rate
                self.timeout = timeout
                self.connection_changed.emit(True)
                return True
            else:
                self.serial_port.close()
                self.serial_port = None
                self.error_occurred.emit(f"Failed to communicate with device on {port}")
                return False
            
        except serial.SerialException as e:
            self.error_occurred.emit(f"Failed to connect to {port}: {e}")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error connecting to {port}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from current port"""
        if self.serial_port and self.serial_port.is_open:
            try:
                # Send zero torque command before disconnecting
                self.send_torque_command(0.0)
                time.sleep(0.1)
                self.serial_port.close()
            except Exception as e:
                self.error_occurred.emit(f"Error closing port: {e}")
        
        self.serial_port = None
        self.is_connected = False
        self.current_port = ""
        self.connection_changed.emit(False)
    
    def send_torque_command(self, torque: float) -> bool:
        """Send torque command to the firmware"""
        if not self.is_connected or not self.serial_port:
            return False
        
        try:
            # Create command packet: Header(2) + Command(1) + Torque(4)
            packet = bytearray()
            packet.append(self.HEADER1)
            packet.append(self.HEADER2)
            packet.append(self.CMD_SET_TORQUE)
            
            # Pack torque as float (little-endian)
            torque_bytes = struct.pack('<f', torque)
            packet.extend(torque_bytes)
            
            # Send packet
            self.serial_port.write(packet)
            self.last_torque_command = torque
            
            # Wait for acknowledgment (with timeout)
            start_time = time.time()
            while time.time() - start_time < 0.5:  # 500ms timeout
                if self.serial_port.in_waiting >= 3:
                    ack_data = self.serial_port.read(3)
                    if (len(ack_data) == 3 and 
                        ack_data[0] == self.HEADER1 and 
                        ack_data[1] == self.HEADER2 and 
                        ack_data[2] == self.ACK_BYTE):
                        self.command_acknowledged.emit()
                        return True
                time.sleep(0.01)
            
            self.error_occurred.emit("Torque command acknowledgment timeout")
            return False
            
        except Exception as e:
            self.error_occurred.emit(f"Error sending torque command: {e}")
            return False
    
    def read_data_packet(self) -> Optional[Dict[str, float]]:
        """Read a data packet from the firmware"""
        if not self.is_connected or not self.serial_port:
            return None
        
        try:
            # Check if enough data is available
            if self.serial_port.in_waiting < 12:  # Full packet size
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
            
            # Read remaining packet data
            remaining_data = self.serial_port.read(packet_size)
            if len(remaining_data) != packet_size:
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
            
            # Verify checksum (simplified - using two's complement)
            received_checksum = remaining_data[9] if len(remaining_data) > 9 else 0
            calculated_checksum = 0
            for byte in header_data[2:] + remaining_data[:-1]:
                calculated_checksum += byte
            calculated_checksum = (~calculated_checksum + 1) & 0xFF
            
            if received_checksum != calculated_checksum:
                self.error_occurred.emit("Data packet checksum verification failed")
                return None
            
            # Update statistics
            self._data_count += 1
            self.last_data_time = time.time()
            
            return {"torque": float(torque), "angle": float(angle)}
            
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
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.01)  # 10ms delay
                
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