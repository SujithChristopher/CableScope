#!/usr/bin/env python3
"""
Debug script to test serial connection to Teensy
"""

import serial
import serial.tools.list_ports
import time

def list_available_ports():
    """List all available serial ports"""
    print("Available serial ports:")
    ports = serial.tools.list_ports.comports()
    for port in ports:
        print(f"  {port.device}: {port.description} [{port.hwid}]")
    return [port.device for port in ports]

def test_port_connection(port, baud_rate=115200):
    """Test basic connection to a specific port"""
    print(f"\nTesting connection to {port} at {baud_rate} baud...")
    
    try:
        # Try to open the port
        ser = serial.Serial(
            port=port,
            baudrate=baud_rate,
            timeout=2.0,
            write_timeout=2.0
        )
        
        print(f"✓ Successfully opened {port}")
        print(f"  Port info: {ser}")
        
        # Wait for connection to stabilize
        time.sleep(1)
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Try to send a simple test command (0xFF 0xFF 0x01 followed by 4 zero bytes)
        test_command = bytes([0xFF, 0xFF, 0x01, 0x00, 0x00, 0x00, 0x00])
        print(f"Sending test command: {' '.join(f'0x{b:02X}' for b in test_command)}")
        
        ser.write(test_command)
        ser.flush()
        
        # Wait for response
        time.sleep(0.5)
        
        # Check for any response
        bytes_waiting = ser.in_waiting
        print(f"Bytes waiting in buffer: {bytes_waiting}")
        
        if bytes_waiting > 0:
            response = ser.read(bytes_waiting)
            print(f"Response: {' '.join(f'0x{b:02X}' for b in response)}")
        else:
            print("No response received")
        
        ser.close()
        print(f"✓ Successfully closed {port}")
        return True
        
    except serial.SerialException as e:
        print(f"✗ Serial error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def main():
    print("CableScope Serial Connection Debug Tool")
    print("=" * 50)
    
    # List all available ports
    available_ports = list_available_ports()
    
    if not available_ports:
        print("\nNo serial ports found!")
        return
    
    # Test COM6 specifically
    if "COM6" in available_ports:
        print(f"\nCOM6 found in available ports")
        test_port_connection("COM6", 115200)
    else:
        print(f"\nCOM6 not found in available ports")
        print("Available ports:", available_ports)
    
    # Test all available ports
    print(f"\nTesting all available ports:")
    for port in available_ports:
        test_port_connection(port, 115200)
        print("-" * 30)

if __name__ == "__main__":
    main()