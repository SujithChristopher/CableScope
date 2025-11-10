#!/usr/bin/env python3
"""
Local build script for CableScope Motor Control
Test the build process locally before GitHub Actions
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return success status"""
    try:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, check=True, 
                              capture_output=True, text=True)
        print(f"Success: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return False

def check_dependencies():
    """Check if required tools are installed"""
    print("Checking dependencies...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("[FAIL] Python 3.8+ required")
        return False
    print(f"[OK] Python {sys.version.split()[0]}")

    # Check if we can import required modules
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("[FAIL] PyInstaller not found. Install with: pip install pyinstaller")
        return False
    
    return True

def install_requirements():
    """Install Python requirements"""
    print("\nInstalling requirements...")
    requirements_path = Path("python_gui") / "requirements.txt"

    if not requirements_path.exists():
        print(f"[FAIL] Requirements file not found: {requirements_path}")
        return False
    
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)]
    return run_command(cmd)

def clean_build():
    """Clean previous build artifacts"""
    print("\nCleaning build artifacts...")
    
    clean_dirs = [
        Path("python_gui") / "build",
        Path("python_gui") / "dist", 
        Path("python_gui") / "__pycache__",
    ]
    
    for dir_path in clean_dirs:
        if dir_path.exists():
            print(f"Removing {dir_path}")
            shutil.rmtree(dir_path, ignore_errors=True)
    
    # Clean spec files (but keep our main cablescope.spec)
    python_gui_dir = Path("python_gui")
    for spec_file in python_gui_dir.glob("*.spec"):
        if spec_file.name != "cablescope.spec":  # Keep our main spec file
            print(f"Removing {spec_file}")
            spec_file.unlink()
    
    # Clean any leftover archives
    for archive in Path(".").glob("CableScope-*.zip"):
        print(f"Removing {archive}")
        archive.unlink()
        
    for archive in Path(".").glob("CableScope-*.tar.gz"):
        print(f"Removing {archive}")
        archive.unlink()

def build_executable():
    """Build the executable with PyInstaller"""
    print("\nBuilding executable...")
    
    gui_dir = Path("python_gui")
    spec_file = gui_dir / "cablescope.spec"

    if not spec_file.exists():
        print(f"[FAIL] Spec file not found: {spec_file}")
        return False
    
    cmd = [sys.executable, "-m", "PyInstaller", str(spec_file), "--clean", "--noconfirm"]
    return run_command(cmd, cwd=gui_dir)

def create_archive():
    """Create distribution archive"""
    print("\nCreating distribution archive...")
    
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Determine architecture
    if machine in ["x86_64", "amd64"]:
        arch = "x64"
    elif machine in ["i386", "i686", "x86"]:
        arch = "x86"  
    elif machine in ["aarch64", "arm64"]:
        arch = "arm64"
    else:
        arch = "unknown"
    
    dist_dir = Path("python_gui") / "dist" / "CableScope"
    if not dist_dir.exists():
        print(f"[FAIL] Distribution directory not found: {dist_dir}")
        return False
    
    # Create archive name
    if system == "windows":
        archive_name = f"CableScope-Windows-{arch}"
        archive_path = f"{archive_name}.zip"
        
        # Create zip archive
        shutil.make_archive(archive_name, 'zip', dist_dir.parent, dist_dir.name)
        
    elif system == "darwin":
        archive_name = f"CableScope-macOS-{arch}"
        archive_path = f"{archive_name}.zip"
        
        # Create zip archive
        shutil.make_archive(archive_name, 'zip', dist_dir.parent, dist_dir.name)
        
    else:  # Linux and others
        archive_name = f"CableScope-Linux-{arch}"
        archive_path = f"{archive_name}.tar.gz"
        
        # Create tar.gz archive
        shutil.make_archive(archive_name, 'gztar', dist_dir.parent, dist_dir.name)
    
    if Path(archive_path).exists():
        file_size = Path(archive_path).stat().st_size / (1024*1024)  # MB
        print(f"[OK] Created {archive_path} ({file_size:.1f} MB)")
        return True
    else:
        print(f"[FAIL] Failed to create {archive_path}")
        return False

def verify_build():
    """Verify the build works"""
    print("\nVerifying build...")
    
    system = platform.system().lower()
    dist_dir = Path("python_gui") / "dist" / "CableScope"
    
    if system == "windows":
        executable = dist_dir / "CableScope.exe"
    else:
        executable = dist_dir / "CableScope"
    
    if not executable.exists():
        print(f"[FAIL] Executable not found: {executable}")
        return False

    print(f"[OK] Executable found: {executable}")

    # Note: Firmware is now embedded in Python code, no external files needed
    print(f"[OK] Firmware embedded in application (no external files required)")
    
    return True

def main():
    """Main build process"""
    print("CableScope Local Build Script")
    print("=" * 40)
    
    # Change to project root
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    print(f"Working directory: {os.getcwd()}")
    
    # Build steps
    steps = [
        ("Check dependencies", check_dependencies),
        ("Install requirements", install_requirements), 
        ("Clean build", clean_build),
        ("Build executable", build_executable),
        ("Verify build", verify_build),
        ("Create archive", create_archive),
    ]
    
    for step_name, step_func in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        
        if not step_func():
            print(f"[FAIL] Failed at step: {step_name}")
            sys.exit(1)

    print("\n" + "="*60)
    print("Build completed successfully!")
    print("Distribution files created in current directory")
    print("\nTo test the executable:")
    print("   1. Extract the archive")
    print("   2. Run the CableScope executable")
    print("   3. Check that Arduino CLI auto-download works")

if __name__ == "__main__":
    main()