"""
CableScope Motor Control GUI
Main entry point for the application

Built following the Wave Craze architecture pattern
"""

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from gui.main_window import MainWindow
from core.config_manager import ConfigManager
from core.error_handler import ErrorHandler


def main():
    """Main application entry point"""
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("CableScope Motor Control")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Cable Robotics")
    
    # Enable high DPI scaling
    app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    
    try:
        # Initialize error handler
        error_handler = ErrorHandler()
        
        # Initialize configuration
        config_manager = ConfigManager()
        config_manager.ensure_config_exists()
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Run application
        return app.exec()
        
    except Exception as e:
        QMessageBox.critical(None, "Application Error", 
                           f"Failed to start application:\n{str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())