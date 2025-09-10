# CableScope Motor Control System

A comprehensive Python GUI application for controlling and monitoring cable-driven motor systems, with real-time torque and angle data visualization, recording capabilities, and firmware management.

## Overview

CableScope provides:
- **Real-time Control**: Set desired torque values with immediate response
- **Data Visualization**: Live plotting of torque and angle measurements  
- **Data Recording**: Export measurement data to CSV files
- **Firmware Management**: Upload and manage Arduino/Teensy firmware
- **Robust Communication**: Reliable serial protocol with error handling
- **Modern UI**: Dark/light theme support with intuitive controls

## System Architecture

```
CableScope/
├── firmware/              # Arduino/Teensy firmware
│   └── firmware.ino      # Enhanced firmware with communication protocol
└── python_gui/           # Python GUI application
    ├── main.py           # Application entry point
    ├── launch.py         # Dependency installer and launcher
    ├── requirements.txt  # Python dependencies
    ├── core/             # Core functionality
    │   ├── config_manager.py
    │   ├── serial_manager.py
    │   └── error_handler.py
    ├── gui/              # GUI components
    │   ├── main_window.py
    │   ├── tabs/         # Application tabs
    │   ├── widgets/      # Custom widgets
    │   └── styles/       # Theming
    └── firmware_tools/   # Firmware utilities
```

## Hardware Requirements

### Supported Microcontrollers
- **Teensy 4.1** (recommended)
- **Teensy 4.0**
- **Arduino Mega**
- **Arduino Uno/Nano** (limited functionality)

### Required Hardware Components
- **Torque Sensor**: HX711-based load cell amplifier
- **Encoder**: Quadrature rotary encoder for angle measurement
- **Motor Driver**: PWM-compatible motor controller
- **Motor**: DC motor with torque control capability

### Hardware Connections

#### Teensy 4.1 Pinout
```
Torque Sensor (HX711):
- DOUT → Pin 32
- SCK  → Pin 33
- VCC  → 3.3V
- GND  → GND

Encoder:
- Phase A → Pin 27
- Phase B → Pin 28
- VCC    → 3.3V
- GND    → GND

Motor Control:
- PWM       → Pin 8
- Enable    → Pin 9
- Direction → Pin 10
```

## Software Requirements

### Python Environment
- **Python 3.8+** (3.9 or 3.10 recommended)
- **Operating System**: Windows 10/11, macOS, Linux

### Required Python Packages
- `PySide6>=6.5.0` - GUI framework
- `pyqtgraph>=0.13.0` - Real-time plotting
- `pyserial>=3.5` - Serial communication
- `numpy>=1.21.0` - Numerical computing
- `toml>=0.10.2` - Configuration files

### Arduino Development Environment
- **Arduino CLI** - For firmware compilation and upload
- **Teensy Core** - For Teensy board support (if using Teensy)

## Installation

### Quick Start
1. **Clone/Download** the CableScope project to your computer
2. **Navigate** to the `python_gui` directory
3. **Run** the launcher: `python launch.py`

The launcher will automatically:
- Check Python version compatibility
- Install missing dependencies
- Verify system setup
- Start the application

### Manual Installation
If you prefer to install dependencies manually:

```bash
cd python_gui
pip install -r requirements.txt
python main.py
```

### Arduino CLI Setup
1. **Download** Arduino CLI from [arduino.github.io/arduino-cli](https://arduino.github.io/arduino-cli/)
2. **Place** `arduino-cli.exe` in your system PATH or note the installation path
3. **Configure** the path in CableScope's Firmware tab

For Teensy boards, install Teensyduino:
1. Download from [pjrc.com/teensy/td_download.html](https://www.pjrc.com/teensy/td_download.html)
2. Install following the provided instructions

## Usage Guide

### 1. First Time Setup

#### Upload Firmware
1. Open the **Firmware** tab
2. Connect your Teensy/Arduino via USB
3. Select the correct board type (e.g., `teensy:avr:teensy41`)
4. Choose the COM port
5. Click **"Upload Firmware"**

#### Connect to Device
1. Go to the **Control+Plots** tab (unified interface)
2. Select the COM port from the dropdown (Teensy ports auto-selected by default)
3. Click **"Connect"**
4. Verify connection status shows "Connected"

### 2. Motor Control

#### Basic Torque Control
- **Spinbox**: Enter precise torque values (±5.0 Nm default range)
- **Slider**: Quick adjustment with visual feedback
- **Presets**: Common torque values (-2.0 to +2.0 Nm)
- **Send Command**: Apply the set torque value

#### Safety Features
- **Max Torque Limit**: Configurable safety limit
- **Emergency Stop**: Immediate zero torque command
- **Zero Torque**: Quick return to zero torque

### 3. Data Acquisition

#### Start/Stop Data Collection
1. Ensure device is connected
2. Click **"Start Data Acquisition"**
3. Monitor real-time data and live plots in the unified **Control+Plots** tab

#### Configure Sampling
- **Sampling Rate**: 1-1000 Hz (default: 10 Hz)
- **Buffer Size**: Number of data points to retain
- **Auto-start**: Automatically begin data acquisition on connection

### 4. Real-time Visualization

#### Plot Features
- **Dual Plots**: Separate graphs for torque and angle
- **Time Window**: Configurable display duration (1-60 seconds)
- **Auto-scaling**: Automatic Y-axis adjustment
- **Manual Ranges**: Set fixed Y-axis limits
- **Update Rate**: Configurable refresh rate (10-200 ms)

#### Plot Controls
- **Double-click**: Toggle auto-scaling
- **Right-click**: Reset zoom
- **Mouse wheel**: Zoom in/out
- **Click-drag**: Pan the view

### 5. Data Recording

#### Start Recording
1. In the **Control+Plots** tab
2. Click **"Start Recording"**
3. Choose save location and filename
4. Recording begins immediately

#### Recording Features
- **Enhanced CSV Format**: Timestamp, Time(s), Desired Torque(Nm), Actual Torque(Nm), Angle(deg)
- **Command Tracking**: Records both commanded and measured torque values
- **Auto-timestamping**: Automatic filename generation
- **Real-time Status**: Recording indicator and file info
- **Safe Stopping**: Properly closes files on stop

### 6. Configuration Management

#### Settings Tab
- **Serial Settings**: Baud rate, timeout
- **Motor Limits**: Max torque, step size
- **Data Acquisition**: Sampling rate, buffer size
- **UI Preferences**: Theme, window behavior

#### Save/Load Configuration
- **Auto-save**: Settings automatically saved on change
- **Import/Export**: Share configurations between systems
- **Reset**: Return to factory defaults

## Communication Protocol

### Python to Arduino Commands
```
Command Format: [0xFF][0xFF][CMD][DATA...]

Set Torque Command:
[0xFF][0xFF][0x01][torque_float_4_bytes]
Response: [0xFF][0xFF][0xAA] (ACK)
```

### Arduino to Python Data
```
Data Format: [0xFF][0xFF][SIZE][CMD][DATA...][CHECKSUM]

Data Packet (13 bytes total):
[0xFF][0xFF][0x09][0x02][torque_4_bytes][angle_4_bytes][checksum]
- Sent every 100ms automatically
- Two's complement checksum verification
- Immediate motor response to torque commands
```

### Error Handling
- **Checksums**: Two's complement verification for data integrity
- **Timeouts**: Handle communication failures
- **Retries**: Automatic retry on errors
- **Status Monitoring**: Connection and data rate tracking
- **Auto-detection**: Automatic Teensy port selection via USB VID:PID

## Configuration Files

### Main Configuration (`config.toml`)
Located in `%USERPROFILE%/CableScope/config.toml`:

```toml
[serial]
baud_rate = 115200
timeout = 1.0
port = "COM3"

[motor_control]
max_torque = 5.0
torque_step = 0.1
default_torque = 0.0

[data_acquisition]
sampling_rate = 10
buffer_size = 1000
auto_start = false

[plotting]
time_window = 10
update_rate = 50
y_limits = { torque = [-10.0, 10.0], angle = [-360.0, 360.0] }

[recording]
save_directory = "C:/Users/username/CableScope/recordings"
auto_timestamp = true

[ui]
theme = "dark"
window_size = [1200, 800]

[firmware]
arduino_cli_path = "arduino-cli.exe"
board_type = "teensy:avr:teensy41"
firmware_path = "path/to/firmware.ino"
```

## Troubleshooting

### Connection Issues
1. **Check COM Port**: Verify correct port selection
2. **Driver Installation**: Install USB-Serial drivers
3. **Port Conflicts**: Close other applications using the port
4. **Baud Rate**: Ensure matching baud rates (115200 default)

### Data Issues
1. **Check Wiring**: Verify sensor connections
2. **Power Supply**: Ensure adequate power to sensors
3. **Noise**: Add filtering capacitors if needed
4. **Calibration**: Recalibrate torque sensor if necessary

### Firmware Upload Issues
1. **Arduino CLI**: Verify correct installation and PATH
2. **Board Selection**: Choose correct board type
3. **Bootloader**: Ensure device is in programming mode
4. **Permissions**: Run as administrator if needed

### Performance Issues
1. **Reduce Sampling Rate**: Lower for better performance
2. **Buffer Size**: Reduce if memory is limited
3. **Update Rate**: Increase interval for slower systems
4. **Close Other Apps**: Free system resources

## Development

### Project Structure
The project follows a modular architecture with clear separation of concerns:

- **Core modules**: Handle business logic and hardware communication
- **GUI modules**: Provide user interface components
- **Configuration**: Centralized settings management
- **Error handling**: Comprehensive logging and error recovery

### Extending the System
1. **Add New Sensors**: Modify firmware and create new data fields
2. **Custom Plots**: Create additional visualization tabs
3. **Export Formats**: Add support for different file formats
4. **Communication**: Extend protocol for new commands

### Code Style
- **PEP 8**: Python code formatting
- **Type hints**: Enhanced code documentation
- **Docstrings**: Comprehensive function documentation
- **Error handling**: Robust exception management

## Safety Considerations

### Electrical Safety
- **Power ratings**: Verify all components within specifications
- **Isolation**: Use appropriate electrical isolation
- **Fusing**: Include appropriate fuses and protection
- **Grounding**: Ensure proper electrical grounding

### Mechanical Safety
- **Torque limits**: Set appropriate maximum torque values
- **Emergency stops**: Always include emergency stop capability
- **Mechanical limits**: Install physical stops and limiters
- **Personnel protection**: Ensure operator safety

### Software Safety
- **Bounds checking**: All inputs validated and limited
- **Fail-safe defaults**: System defaults to safe states
- **Error recovery**: Graceful handling of all error conditions
- **Logging**: Comprehensive logging for troubleshooting

## Support and Documentation

### Getting Help
1. **Check this README**: Most common issues covered
2. **Log files**: Located in `%USERPROFILE%/CableScope/logs/`
3. **Configuration**: Review settings in config files
4. **Hardware**: Verify all connections and components

### Contributing
Contributions are welcome! Please:
1. Fork the repository
2. Create feature branches
3. Follow existing code style
4. Add appropriate tests
5. Update documentation

### License
This project is provided as-is for educational and research purposes. Please review and comply with all applicable licenses for dependencies.

## Version History

### v1.0.0 (Current)
- Initial release with complete motor control system
- Real-time plotting and data recording
- Firmware upload functionality
- Modern GUI with theme support
- Comprehensive configuration management

### Planned Features
- **Data Analysis**: Built-in analysis tools
- **Multiple Motors**: Support for multiple motor systems
- **Network Support**: Remote monitoring capabilities
- **Advanced Plotting**: FFT and frequency analysis
- **Scripting**: Automated test sequences

---

**CableScope Motor Control System**  
*A comprehensive solution for cable-driven robotics research and development*