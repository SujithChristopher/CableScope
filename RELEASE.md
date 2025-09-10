# CableScope Release Guide

This document describes how to create and manage releases for CableScope Motor Control System.

## 🏗️ Build System Overview

The CableScope project uses an automated build system that:

- **Bundles firmware** with the Python GUI application
- **Auto-downloads Arduino CLI** on first run (no manual installation needed)
- **Creates standalone executables** for Windows, macOS, and Linux
- **Automatically creates releases** when tags are pushed to GitHub

## 🚀 Creating a Release

### Method 1: Automated Release (Recommended)

1. **Test locally** (optional but recommended):
   ```bash
   python build.py
   ```

2. **Create and push a version tag**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. **GitHub Actions will automatically**:
   - Build for Windows, macOS, and Linux
   - Create release packages
   - Generate release notes
   - Publish the release

### Method 2: Manual Release

1. **Go to GitHub repository** → Releases → "Create a new release"

2. **Create a new tag** (e.g., `v1.0.0`)

3. **Fill in release information**:
   - Release title: `CableScope v1.0.0`
   - Description: See template below

4. **Publish release** - this will trigger the build process

## 📦 What Gets Built

Each release creates **standalone executables** containing:

### ✅ Bundled Components
- **Complete Python GUI** with all dependencies
- **Firmware files** (firmware.ino, angle_motor.ino) 
- **All Python libraries** (PySide6, pyqtgraph, etc.)
- **Configuration templates**
- **Documentation**

### 📥 Auto-Downloaded (First Run)
- **Arduino CLI** - automatically downloaded based on user's platform
- **Arduino board definitions** - installed as needed
- **User configuration files** - created in user directory

## 🖥️ Platform Support

| Platform | Package Format | Executable Name | Notes |
|----------|---------------|-----------------|-------|
| Windows  | `.zip`        | `CableScope.exe` | No console window |
| macOS    | `.zip`        | `CableScope.app` | App bundle format |
| Linux    | `.tar.gz`     | `CableScope`     | Standalone binary |

## 📋 Release Checklist

Before creating a release:

- [ ] **Test firmware** - verify communication protocol works
- [ ] **Test GUI functionality** - all tabs and controls working
- [ ] **Test CSV recording** - verify both desired and actual torque columns
- [ ] **Test Arduino CLI auto-download** - verify download works on clean system
- [ ] **Update version numbers** in relevant files
- [ ] **Update CHANGELOG** or release notes
- [ ] **Verify hardware pin assignments** match documentation

## 📝 Release Notes Template

```markdown
## CableScope Motor Control System v1.0.0

### 🚀 What's New
- Complete motor control system with real-time plotting
- Arduino CLI auto-download functionality - no manual setup required
- Enhanced CSV recording with desired vs actual torque tracking
- Unified control and plotting interface
- Improved communication protocol with checksums
- Teensy 4.1 support with optimized pin assignments

### 📦 Installation
1. Download the package for your platform:
   - **Windows**: CableScope-Windows-x64.zip
   - **Linux**: CableScope-Linux-x64.tar.gz  
   - **macOS**: CableScope-macOS-x64.zip

2. Extract and run:
   - **Windows**: Run `CableScope.exe`
   - **macOS**: Run `CableScope.app`
   - **Linux**: Run `./CableScope`

3. **First run**: Arduino CLI will be automatically downloaded

### 🔧 Hardware Requirements
- **Teensy 4.1** (recommended) or Arduino variants
- **HX711 torque sensor** (pins 32/33)
- **Quadrature encoder** (pins 27/28) 
- **Motor driver** with PWM control (pins 8/9/10)

### 📖 Documentation
- Complete setup guide in README.md
- Hardware wiring diagrams included
- Configuration examples provided

### 🐛 Bug Reports
Report issues at: https://github.com/your-repo/issues

### 🎯 Known Limitations
- Arduino CLI requires internet connection for first download
- Some antivirus software may flag the executable (false positive)
```

## 🔧 Development Builds

For testing during development:

```bash
# Install PyInstaller
pip install pyinstaller

# Run local build script
python build.py

# Or build manually
cd python_gui
pyinstaller cablescope.spec --clean --noconfirm
```

## 🏷️ Version Numbering

CableScope follows semantic versioning:

- **Major** (v2.0.0): Breaking changes, major new features
- **Minor** (v1.1.0): New features, backwards compatible  
- **Patch** (v1.0.1): Bug fixes, small improvements

## 📁 File Structure in Release

```
CableScope/
├── CableScope.exe          # Main executable
├── firmware/               # Bundled firmware files
│   ├── firmware.ino
│   └── angle_motor.ino
├── gui/                    # GUI resources
├── _internal/              # Python runtime and libraries
└── README.txt              # Quick start guide
```

## 🚨 Troubleshooting Releases

### Build Failures
1. Check GitHub Actions logs
2. Verify all dependencies in requirements.txt
3. Test locally with `python build.py`
4. Check PyInstaller spec file

### Download Issues  
1. Verify Arduino CLI manager handles all platforms
2. Test internet connectivity requirements
3. Check GitHub API rate limits

### User Issues
1. Most issues are Arduino CLI related - check auto-download
2. Verify hardware connections match documentation
3. Check configuration file generation

## 🔄 Release Maintenance

- **Security updates**: Update dependencies regularly
- **Arduino CLI updates**: Manager automatically gets latest version
- **Platform compatibility**: Test on target systems
- **Documentation**: Keep README and hardware guides current

---

**Questions?** Contact the development team or create an issue on GitHub.