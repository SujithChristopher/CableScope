"""
Configuration Manager for CableScope Motor Control
Handles loading, saving, and managing application configuration
"""

import os
import toml
from pathlib import Path
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal


class ConfigManager(QObject):
    """Manages application configuration and settings"""
    
    # Signals
    config_changed = Signal()
    
    def __init__(self, config_dir: Optional[str] = None):
        super().__init__()
        
        # Set config directory
        if config_dir is None:
            self.config_dir = Path.home() / "CableScope"
        else:
            self.config_dir = Path(config_dir)
        
        self.config_file = self.config_dir / "config.toml"
        self._config = {}
        
        # Default configuration
        self.default_config = {
            "serial": {
                "baud_rate": 115200,
                "timeout": 1.0,
                "port": ""
            },
            "motor_control": {
                "max_torque": 40.0,
                "torque_step": 0.1,
                "default_torque": 0.0
            },
            "data_acquisition": {
                "buffer_size": 1000,
                "auto_start": False
            },
            "plotting": {
                "time_window": 10,  # seconds
                "update_rate": 50,  # ms
                "y_limits": {
                    "torque": [-10.0, 10.0],
                    "angle": [-360.0, 360.0]
                }
            },
            "recording": {
                "auto_timestamp": True,
                "save_directory": str(Path.home() / "CableScope" / "recordings"),
                "file_format": "csv"
            },
            "ui": {
                "theme": "dark",
                "window_size": [1200, 800],
                "always_on_top": False
            },
            "firmware": {
                "arduino_cli_path": "arduino-cli.exe",
                "board_type": "teensy:avr:teensy41",
                "firmware_path": str(Path(__file__).parent.parent.parent / "firmware" / "firmware.ino")
            }
        }
    
    def ensure_config_exists(self):
        """Ensure configuration directory and file exist"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.config_file.exists():
            self.save_config(self.default_config)
        
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    self._config = toml.load(f)
                
                # Merge with defaults for missing keys
                self._merge_with_defaults()
            else:
                self._config = self.default_config.copy()
            
            return self._config
            
        except Exception as e:
            print(f"Error loading config: {e}")
            self._config = self.default_config.copy()
            return self._config
    
    def save_config(self, config: Optional[Dict[str, Any]] = None):
        """Save configuration to file"""
        try:
            if config is not None:
                self._config = config
            
            with open(self.config_file, 'w') as f:
                toml.dump(self._config, f)
            
            self.config_changed.emit()
            
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def _merge_with_defaults(self):
        """Merge current config with defaults for missing keys"""
        def merge_dicts(default: dict, current: dict) -> dict:
            """Recursively merge dictionaries"""
            for key, value in default.items():
                if key not in current:
                    current[key] = value
                elif isinstance(value, dict) and isinstance(current[key], dict):
                    merge_dicts(value, current[key])
            return current
        
        self._config = merge_dicts(self.default_config, self._config)
    
    # Getter methods for specific configuration sections
    def get_serial_config(self) -> Dict[str, Any]:
        """Get serial communication configuration"""
        return self._config.get("serial", {})
    
    def get_motor_config(self) -> Dict[str, Any]:
        """Get motor control configuration"""
        return self._config.get("motor_control", {})
    
    def get_data_acquisition_config(self) -> Dict[str, Any]:
        """Get data acquisition configuration"""
        return self._config.get("data_acquisition", {})
    
    def get_plotting_config(self) -> Dict[str, Any]:
        """Get plotting configuration"""
        return self._config.get("plotting", {})
    
    def get_recording_config(self) -> Dict[str, Any]:
        """Get recording configuration"""
        return self._config.get("recording", {})
    
    def get_ui_config(self) -> Dict[str, Any]:
        """Get UI configuration"""
        return self._config.get("ui", {})
    
    def get_firmware_config(self) -> Dict[str, Any]:
        """Get firmware configuration"""
        return self._config.get("firmware", {})
    
    # Setter methods for specific values
    def set_serial_port(self, port: str):
        """Set serial port"""
        self._config.setdefault("serial", {})["port"] = port
        self.save_config()
    
    def set_baud_rate(self, baud_rate: int):
        """Set baud rate"""
        self._config.setdefault("serial", {})["baud_rate"] = baud_rate
        self.save_config()
    
    def set_max_torque(self, max_torque: float):
        """Set maximum torque limit"""
        self._config.setdefault("motor_control", {})["max_torque"] = max_torque
        self.save_config()
    
    def set_time_window(self, seconds: int):
        """Set plotting time window"""
        self._config.setdefault("plotting", {})["time_window"] = seconds
        self.save_config()
    
    def set_theme(self, theme: str):
        """Set UI theme"""
        self._config.setdefault("ui", {})["theme"] = theme
        self.save_config()
    
    def set_window_size(self, width: int, height: int):
        """Set window size"""
        self._config.setdefault("ui", {})["window_size"] = [width, height]
        self.save_config()
    
    def set_recording_directory(self, directory: str):
        """Set recording save directory"""
        self._config.setdefault("recording", {})["save_directory"] = directory
        self.save_config()
    
    def set_firmware_path(self, path: str):
        """Set firmware file path"""
        self._config.setdefault("firmware", {})["firmware_path"] = path
        self.save_config()
    
    def set_arduino_cli_path(self, path: str):
        """Set arduino-cli executable path"""
        self._config.setdefault("firmware", {})["arduino_cli_path"] = path
        self.save_config()
    
    # Utility methods
    def get_config_dir(self) -> Path:
        """Get configuration directory path"""
        return self.config_dir
    
    def get_full_config(self) -> Dict[str, Any]:
        """Get complete configuration dictionary"""
        return self._config.copy()
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self._config = self.default_config.copy()
        self.save_config()
    
    def import_config(self, file_path: str) -> bool:
        """Import configuration from file"""
        try:
            with open(file_path, 'r') as f:
                imported_config = toml.load(f)
            
            # Merge with current config
            self._config.update(imported_config)
            self._merge_with_defaults()
            self.save_config()
            
            return True
            
        except Exception as e:
            print(f"Error importing config: {e}")
            return False
    
    def export_config(self, file_path: str) -> bool:
        """Export configuration to file"""
        try:
            with open(file_path, 'w') as f:
                toml.dump(self._config, f)
            
            return True
            
        except Exception as e:
            print(f"Error exporting config: {e}")
            return False