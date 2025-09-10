#!/usr/bin/env python3
"""
CableScope Motor Control - Launch Script
Simple launcher that handles dependencies and starts the application
"""

import sys
import subprocess
import os
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    return True


def check_and_install_dependencies():
    """Check and install required dependencies"""
    required_packages = [
        "PySide6>=6.5.0",
        "pyqtgraph>=0.13.0", 
        "pyserial>=3.5",
        "numpy>=1.21.0",
        "toml>=0.10.2"
    ]
    
    print("Checking dependencies...")
    
    missing_packages = []
    
    for package in required_packages:
        package_name = package.split(">=")[0]
        try:
            __import__(package_name.replace("-", "_").lower())
            print(f"✓ {package_name} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package_name} is missing")
    
    if missing_packages:
        print(f"\nInstalling missing packages: {', '.join(missing_packages)}")
        
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install"
            ] + missing_packages)
            print("✓ All dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            return False
    
    print("✓ All dependencies are satisfied")
    return True


def setup_path():
    """Setup Python path for imports"""
    # Add current directory to Python path
    current_dir = Path(__file__).parent.resolve()
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))


def check_firmware_exists():
    """Check if firmware file exists"""
    current_dir = Path(__file__).parent
    firmware_path = current_dir.parent / "firmware" / "firmware.ino"
    
    if firmware_path.exists():
        print(f"✓ Firmware found at: {firmware_path}")
        return True
    else:
        print(f"⚠ Warning: Firmware not found at: {firmware_path}")
        print("  You can still use the application, but firmware upload won't work")
        return False


def main():
    """Main launcher function"""
    print("=" * 60)
    print("CableScope Motor Control - Starting Application")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Check and install dependencies
    if not check_and_install_dependencies():
        print("Failed to install required dependencies")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Setup Python path
    setup_path()
    
    # Check firmware
    check_firmware_exists()
    
    print("\nStarting CableScope Motor Control...")
    print("=" * 60)
    
    try:
        # Import and run the application
        from main import main as app_main
        return app_main()
        
    except ImportError as e:
        print(f"Error importing application: {e}")
        print("Make sure all files are in the correct location")
        input("Press Enter to exit...")
        sys.exit(1)
    
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())