#!/usr/bin/env python3
"""
Check if COM3 is being used by another process
"""

import serial
import time
import psutil
import os

def check_port_in_use(port):
    """Check if a port is currently in use"""
    print(f"Checking if {port} is in use...")
    
    try:
        # Try to open the port
        test_serial = serial.Serial(
            port=port,
            baudrate=115200,
            timeout=1
        )
        print(f"✓ {port} is available and can be opened")
        test_serial.close()
        return False  # Not in use
        
    except serial.SerialException as e:
        if "Access is denied" in str(e) or "being used by another process" in str(e):
            print(f"✗ {port} is being used by another process: {e}")
            return True  # In use
        else:
            print(f"✗ {port} has other issues: {e}")
            return True
            
    except Exception as e:
        print(f"✗ Unexpected error with {port}: {e}")
        return True

def find_processes_using_serial():
    """Find processes that might be using serial ports"""
    print("\nLooking for processes that might be using serial ports...")
    
    serial_related_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = proc.info['name'].lower()
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            
            # Look for common serial port users
            if any(keyword in name for keyword in ['arduino', 'serial', 'com', 'teensy', 'avrdude', 'platformio']):
                serial_related_processes.append((proc.info['pid'], proc.info['name'], cmdline))
            elif any(keyword in cmdline.lower() for keyword in ['com3', 'serial', 'arduino', 'teensy']):
                serial_related_processes.append((proc.info['pid'], proc.info['name'], cmdline))
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if serial_related_processes:
        print("Found processes that might be using serial ports:")
        for pid, name, cmdline in serial_related_processes:
            print(f"  PID {pid}: {name}")
            print(f"    Command: {cmdline[:100]}{'...' if len(cmdline) > 100 else ''}")
    else:
        print("No obvious serial port processes found")

def main():
    print("COM Port Usage Checker")
    print("=" * 30)
    
    # Check COM3 specifically
    port_in_use = check_port_in_use("COM3")
    
    # Check what processes might be using serial ports
    find_processes_using_serial()
    
    if port_in_use:
        print(f"\n⚠️  COM3 appears to be in use by another application")
        print("Possible solutions:")
        print("1. Close Arduino IDE if it's open")
        print("2. Close any other serial terminal programs")
        print("3. Unplug and replug the Teensy")
        print("4. Check Windows Device Manager for driver issues")
        print("5. Restart the CableScope application")
    else:
        print(f"\n✅ COM3 should be available for CableScope to use")

if __name__ == "__main__":
    main()