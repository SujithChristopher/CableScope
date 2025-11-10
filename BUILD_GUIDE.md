# CableScope Build Guide

Complete guide for building CableScope Motor Control as standalone executables for Windows, Linux, and macOS.

## Table of Contents
- [Overview](#overview)
- [Build System Architecture](#build-system-architecture)
- [Local Building](#local-building)
- [CI/CD Pipeline](#cicd-pipeline)
- [Distribution](#distribution)
- [Troubleshooting](#troubleshooting)

## Overview

CableScope uses **PyInstaller** to bundle the Python application and all dependencies into standalone executables. The build system:

- ✅ Bundles all Python dependencies (PySide6, pyqtgraph, pyserial, numpy, etc.)
- ✅ Embeds firmware code directly in the binary (no external files needed)
- ✅ Creates platform-specific executables
- ✅ Supports Windows, Linux, and macOS
- ✅ Auto-downloads Arduino CLI on first run
- ✅ Includes both main firmware and PWM testing firmwares

## Build System Architecture

### Files Involved

```
CableScope/
├── build.py                              # Local build script
├── python_gui/
│   ├── cablescope.spec                  # PyInstaller spec file
│   ├── requirements.txt                  # Python dependencies
│   └── main.py                          # Application entry point
├── .github/
│   └── workflows/
│       ├── build-release.yml            # Release builds (on tags)
│       └── test.yml                     # Continuous testing (on push/PR)
└── firmwares/
    ├── firmware/                        # Main torque control firmware
    ├── PWM_Constant/                    # 24h constant PWM test firmware
    └── PWM_On_Off/                      # PWM on/off cycle test firmware
```

### How It Works

1. **PyInstaller Analysis** (`cablescope.spec`):
   - Scans Python code for imports
   - Identifies all dependencies
   - Embeds firmware code from `core/firmware_resources.py`
   - Excludes unnecessary modules (tkinter, matplotlib, etc.)

2. **Binary Creation**:
   - Creates platform-specific executable
   - Bundles Qt libraries (PySide6)
   - Includes all Python modules
   - No external files needed (firmware embedded)

3. **Distribution Package**:
   - Windows: `CableScope.exe` + DLLs → `.zip`
   - Linux: `CableScope` binary + libs → `.tar.gz`
   - macOS: `CableScope.app` bundle → `.zip`

## Local Building

### Prerequisites

#### All Platforms
```bash
# Python 3.10 or newer
python --version

# Install dependencies
pip install -r python_gui/requirements.txt
pip install pyinstaller
```

#### Linux Additional Setup
```bash
sudo apt-get update
sudo apt-get install -y libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-randr0 libxcb-render-util0
```

### Build Process

#### Method 1: Using build.py (Recommended)

```bash
# Run the complete build pipeline
python build.py
```

This script:
1. ✅ Checks dependencies
2. ✅ Installs requirements
3. ✅ Cleans previous builds
4. ✅ Builds executable with PyInstaller
5. ✅ Verifies build output
6. ✅ Creates distribution archive

#### Method 2: Manual PyInstaller

```bash
cd python_gui
python -m PyInstaller cablescope.spec --clean --noconfirm
```

Output location:
- Executable: `python_gui/dist/CableScope/`
- Archive: Created by `build.py` in project root

### Testing the Build

```bash
# Windows
python_gui\dist\CableScope\CableScope.exe

# Linux/macOS
./python_gui/dist/CableScope/CableScope
```

## CI/CD Pipeline

### Continuous Testing (`test.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests
- Manual dispatch

**What it tests:**
- ✅ Python 3.10, 3.11, 3.12
- ✅ Windows, Linux, macOS
- ✅ All module imports
- ✅ GUI instantiation
- ✅ Firmware resources
- ✅ PWM firmware files exist
- ✅ Quick build test (Windows only)

**Matrix:**
```yaml
matrix:
  os: [windows-latest, ubuntu-latest, macos-latest]
  python-version: ['3.10', '3.11', '3.12']
```

Total: **9 test configurations** (3 OS × 3 Python versions)

### Release Builds (`build-release.yml`)

**Triggers:**
- Git tags matching `v*` (e.g., `v1.0.0`, `v1.2.3`)
- Manual dispatch

**Process:**
1. **Test Stage** (9 configurations)
   - Run all tests on all platforms
   - Must pass before building

2. **Build Stage** (Windows only currently)
   - Build with PyInstaller
   - Create distribution archives
   - Upload as artifacts

3. **Release Stage** (if tagged)
   - Create GitHub release
   - Attach distribution archives
   - Generate release notes

### Creating a Release

```bash
# Tag a version
git tag -a v1.2.0 -m "Release version 1.2.0 with PWM Only tab"
git push origin v1.2.0

# CI/CD automatically:
# 1. Tests on all platforms
# 2. Builds executables
# 3. Creates GitHub release
# 4. Attaches distribution files
```

### Manual Workflow Trigger

Via GitHub UI:
1. Go to **Actions** tab
2. Select workflow (`Build and Release` or `Test CableScope`)
3. Click **Run workflow**
4. Choose branch
5. Click **Run workflow** button

## Distribution

### Windows Distribution

**Contents:**
```
CableScope-Windows-x64.zip
└── CableScope/
    ├── CableScope.exe           # Main executable
    ├── *.dll                    # Qt and Python DLLs
    └── [internal files]         # PyInstaller runtime
```

**Installation:**
1. Extract ZIP to any location
2. Run `CableScope.exe`
3. Arduino CLI auto-downloads on first firmware upload

### Linux Distribution

**Contents:**
```
CableScope-Linux-x64.tar.gz
└── CableScope/
    ├── CableScope               # Main binary
    ├── *.so                     # Shared libraries
    └── [internal files]         # PyInstaller runtime
```

**Installation:**
```bash
tar -xzf CableScope-Linux-x64.tar.gz
cd CableScope
chmod +x CableScope
./CableScope
```

### macOS Distribution

**Contents:**
```
CableScope-macOS-x64.zip
└── CableScope.app/              # Application bundle
    └── Contents/
        └── MacOS/
            └── CableScope       # Main binary
```

**Installation:**
1. Extract ZIP
2. Move `CableScope.app` to Applications
3. Right-click → Open (first time only, for Gatekeeper)

## Firmware Bundling

### Embedded Firmwares

All firmwares are **embedded directly in the executable** via `core/firmware_resources.py`:

1. **Combined Firmware** (`firmware/firmware.ino`)
   - Main torque control with HX711 sensor
   - Real-time data streaming
   - Interactive and random torque modes

2. **PWM Constant** (`firmwares/PWM_Constant/PWM_Constant.ino`)
   - Constant PWM output (default: 700)
   - 24-hour endurance testing
   - 10 Hz data logging

3. **PWM On/Off** (`firmwares/PWM_On_Off/PWM_On_Off.ino`)
   - Alternating PWM (800/410)
   - 5-second intervals
   - 5 cycle testing

### Adding New Firmware

To add a new firmware type:

1. **Add firmware to `core/firmware_resources.py`**:
```python
FIRMWARE_SOURCES = {
    # ... existing firmwares ...
    "new_firmware": {
        "firmware.ino": """
        // Your firmware code here
        """,
    }
}
```

2. **Update `cablescope.spec` if needed**:
```python
hiddenimports=[
    # ... existing imports ...
    'your.new.module',
]
```

3. **Rebuild**:
```bash
python build.py
```

## Troubleshooting

### Build Issues

#### "Module not found" errors
```bash
# Verify all dependencies installed
pip install -r python_gui/requirements.txt
pip list
```

#### PyInstaller fails on Linux
```bash
# Install X11 libraries
sudo apt-get install libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-randr0 libxcb-render-util0
```

#### Large executable size
```bash
# Verify excludes in cablescope.spec
excludes=[
    'tkinter',
    'matplotlib',
    'IPython',
    'jupyter',
    'pytest',
]
```

### Runtime Issues

#### Windows: "Application failed to start"
- Install Visual C++ Redistributable
- Check Windows Defender/Antivirus

#### Linux: "error while loading shared libraries"
```bash
# Install missing libraries
ldd CableScope
sudo apt-get install [missing-library]
```

#### macOS: "CableScope.app is damaged"
```bash
# Remove quarantine attribute
xattr -cr CableScope.app
```

### CI/CD Issues

#### Tests failing
```bash
# Run tests locally first
cd python_gui
python -c "from gui.main_window import MainWindow"
```

#### Build timeout
- Check PyInstaller output
- Verify spec file excludes unnecessary modules
- Consider increasing timeout in workflow

## Performance Optimization

### Reducing Build Size

1. **Exclude unused modules** in `cablescope.spec`:
```python
excludes=[
    'tkinter',
    'matplotlib',
    'IPython',
    'jupyter',
]
```

2. **Use UPX compression**:
```python
upx=True,  # Already enabled
```

3. **Remove debug symbols**:
```python
strip=False,  # Can set to True for smaller size
debug=False,
```

### Build Speed

1. **Use cached dependencies**:
   - GitHub Actions uses pip cache
   - Local: `pip install --cache-dir ./pip_cache`

2. **Skip unnecessary steps**:
   ```bash
   # Quick rebuild (no cleaning)
   cd python_gui
   python -m PyInstaller cablescope.spec --noconfirm
   ```

## Additional Resources

- [PyInstaller Documentation](https://pyinstaller.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [PySide6 Deployment Guide](https://doc.qt.io/qtforpython/deployment.html)

## Version History

- **v1.2.0**: Added PWM Only tab, enhanced CI/CD testing
- **v1.1.0**: Arduino CLI auto-download, embedded firmware
- **v1.0.0**: Initial release with unified interface
