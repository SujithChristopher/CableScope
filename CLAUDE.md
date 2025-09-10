# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
- **Primary launcher**: `python python_gui/launch.py` - Handles dependency installation and setup
- **Direct execution**: `python python_gui/main.py` - Run directly if dependencies are installed
- **Install dependencies**: `pip install -r python_gui/requirements.txt`

### Firmware Development
- **Arduino CLI required**: Download from arduino.github.io/arduino-cli or use included `arduino-cli.exe`
- **Firmware compilation**: Use the GUI Firmware tab or Arduino CLI directly
- **Supported boards**: `teensy:avr:teensy41`, `teensy:avr:teensy40`, `arduino:avr:mega`, `arduino:avr:uno`

## Architecture Overview

CableScope is a **dual-component system** combining Arduino/Teensy firmware with a Python GUI for cable-driven motor control:

### Core Components
- **`firmware/firmware.ino`**: Arduino/Teensy firmware handling motor control, sensor reading, and serial communication
- **`python_gui/`**: PySide6-based GUI application with modular architecture

### Key Modules
- **`core/serial_manager.py`**: Handles bidirectional communication protocol with firmware
- **`core/config_manager.py`**: TOML-based configuration management with user settings
- **`gui/main_window.py`**: Main application window with tabbed interface
- **`gui/tabs/`**: Individual application tabs (Control, Plots, Settings, Firmware)
- **`gui/widgets/`**: Custom widgets for motor control and data visualization

### Communication Protocol
The system uses a custom binary protocol over serial:
```
Commands: [0xFF][0xFF][CMD][DATA...]
Data: [0xFF][0xFF][SIZE][CMD][DATA...][CHECKSUM]
```
- **Torque commands**: Set motor torque via CMD_SET_TORQUE (0x01)
- **Data streaming**: Real-time torque/angle data via CMD_GET_DATA (0x02)
- **Error handling**: Checksums, timeouts, and retry mechanisms

### Hardware Interface
- **Torque sensor**: HX711-based load cell amplifier
- **Encoder**: Quadrature rotary encoder for angle measurement  
- **Motor control**: PWM-based motor driver with enable/direction control
- **Microcontroller**: Teensy 4.1 (recommended) or Arduino variants

## Configuration Management

### User Configuration
- **Location**: `%USERPROFILE%/CableScope/config.toml`
- **Auto-creation**: Generated with defaults on first run
- **Settings include**: Serial parameters, motor limits, data acquisition, UI preferences

### Default Configuration Structure
```toml
[serial]
baud_rate = 115200
port = "COM3"

[motor_control] 
max_torque = 5.0
torque_step = 0.1

[data_acquisition]
sampling_rate = 10
buffer_size = 1000

[plotting]
time_window = 10
update_rate = 50
```

## Development Notes

### Dependencies
- **GUI Framework**: PySide6 (Qt6 for Python)
- **Plotting**: pyqtgraph for real-time data visualization
- **Serial**: pyserial for hardware communication
- **Data**: numpy for numerical operations
- **Config**: toml for configuration file handling

### Code Patterns
- **Qt Signals/Slots**: Used throughout for event handling and inter-component communication
- **Threaded operations**: Serial communication runs in separate threads to maintain UI responsiveness
- **Configuration-driven**: All parameters configurable via TOML files
- **Error handling**: Comprehensive error management with user feedback

### File Structure Conventions
- **`core/`**: Business logic and hardware interfaces
- **`gui/`**: User interface components organized by function
- **`firmware_tools/`**: Arduino CLI integration utilities
- **Wave Craze pattern**: Architecture follows established patterns (mentioned in main.py)

### Safety Features
- **Torque limiting**: Configurable maximum torque values
- **Emergency stop**: Immediate motor shutdown capability
- **Input validation**: All user inputs validated and bounded
- **Error recovery**: Graceful handling of communication failures

## Testing and Validation

No automated tests are currently implemented. Manual testing involves:
- **Hardware-in-the-loop**: Testing with actual motor hardware
- **Serial communication**: Verify protocol integrity
- **GUI functionality**: Test all tabs and controls
- **Data accuracy**: Validate sensor readings and motor response