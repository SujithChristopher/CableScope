"""
Arduino CLI Manager
Handles automatic download, installation, and management of Arduino CLI
"""

import os
import sys
import platform
import zipfile
import tarfile
import shutil
import requests
from pathlib import Path
from typing import Optional, Tuple
from PySide6.QtCore import QThread, Signal, QObject

class ArduinoCliDownloader(QThread):
    """Thread for downloading Arduino CLI"""
    
    # Signals
    download_progress = Signal(int)  # Progress percentage
    download_status = Signal(str)    # Status message
    download_complete = Signal(bool, str)  # Success, message
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://downloads.arduino.cc/arduino-cli"
        self.version = "latest"  # Can be pinned to specific version if needed
        
    def run(self):
        """Download and install Arduino CLI"""
        try:
            # Determine platform and architecture
            platform_info = self._get_platform_info()
            if not platform_info:
                self.download_complete.emit(False, "Unsupported platform")
                return
                
            # Get download URL
            download_url = self._get_download_url(platform_info)
            if not download_url:
                self.download_complete.emit(False, "Could not determine download URL")
                return
                
            # Download and install
            install_path = self._download_and_install(download_url, platform_info)
            if install_path:
                self.download_complete.emit(True, f"Arduino CLI installed to: {install_path}")
            else:
                self.download_complete.emit(False, "Installation failed")
                
        except Exception as e:
            self.download_complete.emit(False, f"Download failed: {str(e)}")
    
    def _get_platform_info(self) -> Optional[dict]:
        """Get platform-specific information for download"""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Map platform names
        if system == "windows":
            platform_name = "Windows"
            extension = "zip"
        elif system == "darwin":
            platform_name = "macOS" 
            extension = "tar.gz"
        elif system == "linux":
            platform_name = "Linux"
            extension = "tar.gz"
        else:
            return None
            
        # Map architectures
        if machine in ["x86_64", "amd64"]:
            arch = "64bit"
        elif machine in ["i386", "i686", "x86"]:
            arch = "32bit"
        elif machine in ["aarch64", "arm64"]:
            arch = "ARM64"
        elif machine.startswith("arm"):
            arch = "ARMv7"
        else:
            arch = "64bit"  # Default to 64bit
            
        return {
            "platform": platform_name,
            "arch": arch,
            "extension": extension,
            "executable": "arduino-cli.exe" if system == "windows" else "arduino-cli"
        }
    
    def _get_download_url(self, platform_info: dict) -> Optional[str]:
        """Get the download URL for the platform"""
        try:
            # Get latest release info from GitHub API
            api_url = "https://api.github.com/repos/arduino/arduino-cli/releases/latest"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            
            # Find matching asset
            target_name = f"arduino-cli_{release_data['tag_name']}_{platform_info['platform']}_{platform_info['arch']}.{platform_info['extension']}"
            
            for asset in release_data['assets']:
                if asset['name'] == target_name:
                    return asset['browser_download_url']
                    
            # Fallback: try without version in name
            fallback_name = f"arduino-cli_{platform_info['platform']}_{platform_info['arch']}.{platform_info['extension']}"
            for asset in release_data['assets']:
                if fallback_name in asset['name']:
                    return asset['browser_download_url']
                    
            return None
            
        except Exception as e:
            print(f"Error getting download URL: {e}")
            return None
    
    def _download_and_install(self, url: str, platform_info: dict) -> Optional[str]:
        """Download and install Arduino CLI"""
        try:
            # Create installation directory
            install_dir = self._get_install_directory()
            install_dir.mkdir(parents=True, exist_ok=True)
            
            # Download file
            self.download_status.emit("Downloading Arduino CLI...")
            filename = url.split('/')[-1]
            download_path = install_dir / filename
            
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.download_progress.emit(progress)
            
            # Extract archive
            self.download_status.emit("Extracting Arduino CLI...")
            if platform_info['extension'] == 'zip':
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    zip_ref.extractall(install_dir)
            else:  # tar.gz
                with tarfile.open(download_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(install_dir)
            
            # Find executable
            executable_path = install_dir / platform_info['executable']
            if not executable_path.exists():
                # Look for executable in subdirectories
                for root, dirs, files in os.walk(install_dir):
                    if platform_info['executable'] in files:
                        executable_path = Path(root) / platform_info['executable']
                        break
            
            if executable_path.exists():
                # Make executable on Unix-like systems
                if platform.system() != "Windows":
                    os.chmod(executable_path, 0o755)
                
                # Clean up download
                download_path.unlink(missing_ok=True)
                
                return str(executable_path)
            else:
                return None
                
        except Exception as e:
            print(f"Error during download/install: {e}")
            return None
    
    def _get_install_directory(self) -> Path:
        """Get the installation directory for Arduino CLI"""
        if platform.system() == "Windows":
            base_dir = Path(os.environ.get('APPDATA', ''))
        elif platform.system() == "Darwin":
            base_dir = Path.home() / "Library" / "Application Support"
        else:  # Linux
            base_dir = Path.home() / ".config"
            
        return base_dir / "CableScope" / "tools" / "arduino-cli"


class ArduinoCliManager(QObject):
    """Manages Arduino CLI installation and usage"""
    
    # Signals
    installation_required = Signal()
    installation_complete = Signal(str)  # Path to arduino-cli
    installation_failed = Signal(str)    # Error message
    
    def __init__(self):
        super().__init__()
        self.arduino_cli_path: Optional[str] = None
        self.downloader: Optional[ArduinoCliDownloader] = None
        
    def get_arduino_cli_path(self) -> Optional[str]:
        """Get path to Arduino CLI executable, download if necessary"""
        if self.arduino_cli_path and Path(self.arduino_cli_path).exists():
            return self.arduino_cli_path
            
        # Check system PATH
        system_cli = self._find_system_arduino_cli()
        if system_cli:
            self.arduino_cli_path = system_cli
            return system_cli
            
        # Check local installation
        local_cli = self._find_local_arduino_cli()
        if local_cli:
            self.arduino_cli_path = local_cli
            return local_cli
            
        # Need to download
        return None
    
    def install_arduino_cli(self):
        """Download and install Arduino CLI"""
        if self.downloader and self.downloader.isRunning():
            return  # Already downloading
            
        self.downloader = ArduinoCliDownloader()
        self.downloader.download_complete.connect(self._on_download_complete)
        self.downloader.start()
    
    def _find_system_arduino_cli(self) -> Optional[str]:
        """Find Arduino CLI in system PATH"""
        executable_name = "arduino-cli.exe" if platform.system() == "Windows" else "arduino-cli"
        
        # Check PATH
        for path in os.environ.get("PATH", "").split(os.pathsep):
            executable_path = Path(path) / executable_name
            if executable_path.exists() and executable_path.is_file():
                return str(executable_path)
        
        # Check common installation locations
        common_paths = []
        if platform.system() == "Windows":
            common_paths = [
                Path.home() / "AppData" / "Local" / "Arduino15" / "arduino-cli.exe",
                Path("C:") / "Program Files" / "Arduino CLI" / "arduino-cli.exe",
                Path("C:") / "arduino-cli" / "arduino-cli.exe",
            ]
        elif platform.system() == "Darwin":
            common_paths = [
                Path("/usr/local/bin/arduino-cli"),
                Path("/opt/homebrew/bin/arduino-cli"),
                Path.home() / "bin" / "arduino-cli",
            ]
        else:  # Linux
            common_paths = [
                Path("/usr/local/bin/arduino-cli"),
                Path("/usr/bin/arduino-cli"),
                Path.home() / "bin" / "arduino-cli",
            ]
        
        for path in common_paths:
            if path.exists() and path.is_file():
                return str(path)
        
        return None
    
    def _find_local_arduino_cli(self) -> Optional[str]:
        """Find locally installed Arduino CLI"""
        install_dir = self._get_local_install_directory()
        if not install_dir.exists():
            return None
            
        executable_name = "arduino-cli.exe" if platform.system() == "Windows" else "arduino-cli"
        
        # Look in installation directory and subdirectories
        for root, dirs, files in os.walk(install_dir):
            if executable_name in files:
                executable_path = Path(root) / executable_name
                if executable_path.is_file():
                    return str(executable_path)
        
        return None
    
    def _get_local_install_directory(self) -> Path:
        """Get local installation directory"""
        if platform.system() == "Windows":
            base_dir = Path(os.environ.get('APPDATA', ''))
        elif platform.system() == "Darwin":
            base_dir = Path.home() / "Library" / "Application Support"
        else:  # Linux
            base_dir = Path.home() / ".config"
            
        return base_dir / "CableScope" / "tools" / "arduino-cli"
    
    def _on_download_complete(self, success: bool, message: str):
        """Handle download completion"""
        if success:
            # Find the installed executable
            cli_path = self._find_local_arduino_cli()
            if cli_path:
                self.arduino_cli_path = cli_path
                self.installation_complete.emit(cli_path)
            else:
                self.installation_failed.emit("Installation completed but executable not found")
        else:
            self.installation_failed.emit(message)
    
    def verify_installation(self, cli_path: str) -> Tuple[bool, str]:
        """Verify Arduino CLI installation"""
        try:
            import subprocess
            result = subprocess.run([cli_path, "version"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, f"Arduino CLI {version}"
            else:
                return False, f"Arduino CLI not working: {result.stderr}"
                
        except Exception as e:
            return False, f"Error verifying Arduino CLI: {str(e)}"