"""
Error Handler for CableScope Motor Control
Provides centralized error handling and logging
"""

import sys
import traceback
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox


class ErrorHandler(QObject):
    """Centralized error handling and logging"""
    
    # Signals
    error_occurred = Signal(str, str)  # error_type, message
    warning_occurred = Signal(str)     # message
    
    def __init__(self, log_dir: Optional[str] = None):
        super().__init__()
        
        # Set log directory
        if log_dir is None:
            self.log_dir = Path.home() / "CableScope" / "logs"
        else:
            self.log_dir = Path(log_dir)
        
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Install exception hook
        sys.excepthook = self.handle_exception
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_file = self.log_dir / f"cablescope_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        self.logger.error(f"Uncaught exception: {error_msg}")
        self.error_occurred.emit("UnhandledException", str(exc_value))
        
        # Show error dialog
        QMessageBox.critical(
            None, 
            "Unhandled Exception", 
            f"An unexpected error occurred:\n\n{exc_value}\n\nCheck the log file for details."
        )
    
    def log_error(self, error_type: str, message: str, exception: Optional[Exception] = None):
        """Log an error with optional exception details"""
        if exception:
            self.logger.error(f"{error_type}: {message} - {str(exception)}")
            if hasattr(exception, '__traceback__') and exception.__traceback__:
                traceback_str = "".join(traceback.format_tb(exception.__traceback__))
                self.logger.error(f"Traceback: {traceback_str}")
        else:
            self.logger.error(f"{error_type}: {message}")
        
        self.error_occurred.emit(error_type, message)
    
    def log_warning(self, message: str):
        """Log a warning"""
        self.logger.warning(message)
        self.warning_occurred.emit(message)
    
    def log_info(self, message: str):
        """Log an info message"""
        self.logger.info(message)
    
    def log_debug(self, message: str):
        """Log a debug message"""
        self.logger.debug(message)
    
    def show_error_dialog(self, title: str, message: str, details: Optional[str] = None):
        """Show error dialog to user"""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if details:
            msg_box.setDetailedText(details)
        
        msg_box.exec()
    
    def show_warning_dialog(self, title: str, message: str):
        """Show warning dialog to user"""
        QMessageBox.warning(None, title, message)
    
    def show_info_dialog(self, title: str, message: str):
        """Show info dialog to user"""
        QMessageBox.information(None, title, message)