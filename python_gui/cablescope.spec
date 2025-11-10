# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec file for CableScope Motor Control
Creates standalone executables with all dependencies bundled
"""

import sys
import os
from pathlib import Path

# Get the project root directory
spec_dir = os.path.dirname(os.path.abspath(SPECPATH))
project_root = Path(spec_dir).parent

# Build data files list  
# NOTE: Firmware is now embedded in Python code via firmware_resources.py
# No external firmware files needed for distribution
datas = []

# Analysis: find all Python modules and dependencies
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # PySide6 modules that might not be auto-detected
        'PySide6.QtCore',
        'PySide6.QtGui', 
        'PySide6.QtWidgets',
        # pyqtgraph requirements
        'pyqtgraph',
        # Serial and numpy
        'serial',
        'numpy',
        # HTTP requests
        'requests',
        # File handling
        'toml',
        # Core modules
        'core.config_manager',
        'core.serial_manager',
        'core.error_handler',
        'core.arduino_cli_manager',
        'core.firmware_resources',
        # GUI modules
        'gui.main_window',
        'gui.tabs.control_plots_tab',
        'gui.tabs.pwm_only_tab',
        'gui.tabs.settings_tab',
        'gui.tabs.firmware_tab',
        'gui.widgets.status_bar',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
        'pytest',
        'setuptools',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate entries
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CableScope',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Hide console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Create distribution folder
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CableScope',
)