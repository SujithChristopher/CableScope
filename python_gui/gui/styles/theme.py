"""
Theme Manager for CableScope Motor Control
Provides dark and light theme styling
"""

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QObject
from PySide6.QtGui import QPalette, QColor
from typing import Dict, Any


class ThemeManager(QObject):
    """Manages application themes"""
    
    def __init__(self):
        super().__init__()
        self.current_theme = "dark"
        
        # Dark theme colors
        self.dark_theme = {
            "window": "#1e293b",
            "windowText": "#f8fafc",
            "base": "#0f172a",
            "alternateBase": "#334155",
            "toolTipBase": "#475569",
            "toolTipText": "#f8fafc",
            "text": "#f8fafc",
            "button": "#334155",
            "buttonText": "#f8fafc",
            "brightText": "#fbbf24",
            "link": "#3b82f6",
            "highlight": "#3b82f6",
            "highlightedText": "#ffffff",
            "disabled_text": "#64748b",
            "disabled_button": "#1e293b"
        }
        
        # Light theme colors
        self.light_theme = {
            "window": "#f8fafc",
            "windowText": "#0f172a",
            "base": "#ffffff",
            "alternateBase": "#f1f5f9",
            "toolTipBase": "#e2e8f0",
            "toolTipText": "#0f172a",
            "text": "#0f172a",
            "button": "#e2e8f0",
            "buttonText": "#0f172a",
            "brightText": "#dc2626",
            "link": "#2563eb",
            "highlight": "#2563eb",
            "highlightedText": "#ffffff",
            "disabled_text": "#94a3b8",
            "disabled_button": "#f1f5f9"
        }
    
    def apply_theme(self, app_or_widget, theme_name: str = "dark"):
        """Apply theme to application or widget"""
        self.current_theme = theme_name
        
        if theme_name == "dark":
            colors = self.dark_theme
        else:
            colors = self.light_theme
        
        # Create palette
        palette = QPalette()
        
        # Set colors
        palette.setColor(QPalette.ColorRole.Window, QColor(colors["window"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["windowText"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(colors["base"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["alternateBase"]))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors["toolTipBase"]))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors["toolTipText"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(colors["text"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(colors["button"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["buttonText"]))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(colors["brightText"]))
        palette.setColor(QPalette.ColorRole.Link, QColor(colors["link"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["highlight"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["highlightedText"]))
        
        # Disabled colors
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(colors["disabled_text"]))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(colors["disabled_text"]))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, QColor(colors["disabled_button"]))
        
        # Apply palette
        if isinstance(app_or_widget, QApplication):
            app_or_widget.setPalette(palette)
        else:
            app_or_widget.setPalette(palette)
        
        # Apply additional stylesheet for specific widgets
        stylesheet = self.get_widget_stylesheet(theme_name)
        if isinstance(app_or_widget, QApplication):
            app_or_widget.setStyleSheet(stylesheet)
        else:
            app_or_widget.setStyleSheet(stylesheet)
    
    def get_widget_stylesheet(self, theme_name: str = "dark") -> str:
        """Get CSS stylesheet for specific widgets"""
        if theme_name == "dark":
            return self._get_dark_stylesheet()
        else:
            return self._get_light_stylesheet()
    
    def _get_dark_stylesheet(self) -> str:
        """Get dark theme stylesheet"""
        return """
        QMainWindow {
            background-color: #1e293b;
            color: #f8fafc;
        }
        
        QTabWidget::pane {
            border: 1px solid #475569;
            background-color: #1e293b;
        }
        
        QTabWidget::tab-bar {
            alignment: left;
        }
        
        QTabBar::tab {
            background-color: #334155;
            color: #f8fafc;
            border: 1px solid #475569;
            padding: 8px 16px;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background-color: #3b82f6;
            color: #ffffff;
        }
        
        QTabBar::tab:hover {
            background-color: #475569;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #475569;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 5px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        
        QPushButton {
            background-color: #334155;
            border: 1px solid #475569;
            border-radius: 4px;
            padding: 6px 12px;
            color: #f8fafc;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #475569;
        }
        
        QPushButton:pressed {
            background-color: #1e293b;
        }
        
        QPushButton:disabled {
            background-color: #1e293b;
            color: #64748b;
        }
        
        QComboBox {
            background-color: #334155;
            border: 1px solid #475569;
            border-radius: 4px;
            padding: 4px 8px;
            color: #f8fafc;
        }
        
        QComboBox::drop-down {
            border: none;
        }
        
        QComboBox::down-arrow {
            width: 12px;
            height: 12px;
        }
        
        QSpinBox, QDoubleSpinBox {
            background-color: #334155;
            border: 1px solid #475569;
            border-radius: 4px;
            padding: 4px 8px;
            color: #f8fafc;
        }
        
        QLineEdit {
            background-color: #334155;
            border: 1px solid #475569;
            border-radius: 4px;
            padding: 4px 8px;
            color: #f8fafc;
        }
        
        QSlider::groove:horizontal {
            border: 1px solid #475569;
            height: 6px;
            background-color: #1e293b;
            border-radius: 3px;
        }
        
        QSlider::handle:horizontal {
            background-color: #3b82f6;
            border: 1px solid #2563eb;
            width: 16px;
            height: 16px;
            border-radius: 8px;
            margin: -6px 0;
        }
        
        QSlider::sub-page:horizontal {
            background-color: #3b82f6;
            border-radius: 3px;
        }
        
        QLCDNumber {
            background-color: #0f172a;
            border: 1px solid #475569;
            border-radius: 4px;
            color: #22c55e;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }
        
        QCheckBox::indicator:unchecked {
            background-color: #334155;
            border: 1px solid #475569;
            border-radius: 3px;
        }
        
        QCheckBox::indicator:checked {
            background-color: #3b82f6;
            border: 1px solid #2563eb;
            border-radius: 3px;
        }
        
        QStatusBar {
            background-color: #0f172a;
            color: #f8fafc;
            border-top: 1px solid #475569;
        }
        
        QMenuBar {
            background-color: #1e293b;
            color: #f8fafc;
            border-bottom: 1px solid #475569;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 8px;
        }
        
        QMenuBar::item:selected {
            background-color: #334155;
        }
        
        QMenu {
            background-color: #334155;
            color: #f8fafc;
            border: 1px solid #475569;
        }
        
        QMenu::item {
            padding: 4px 16px;
        }
        
        QMenu::item:selected {
            background-color: #3b82f6;
        }
        """
    
    def _get_light_stylesheet(self) -> str:
        """Get light theme stylesheet"""
        return """
        QMainWindow {
            background-color: #f8fafc;
            color: #0f172a;
        }
        
        QTabWidget::pane {
            border: 1px solid #cbd5e1;
            background-color: #f8fafc;
        }
        
        QTabWidget::tab-bar {
            alignment: left;
        }
        
        QTabBar::tab {
            background-color: #e2e8f0;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            padding: 8px 16px;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background-color: #2563eb;
            color: #ffffff;
        }
        
        QTabBar::tab:hover {
            background-color: #cbd5e1;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cbd5e1;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 5px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        
        QPushButton {
            background-color: #e2e8f0;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            padding: 6px 12px;
            color: #0f172a;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #cbd5e1;
        }
        
        QPushButton:pressed {
            background-color: #94a3b8;
        }
        
        QPushButton:disabled {
            background-color: #f1f5f9;
            color: #94a3b8;
        }
        
        QComboBox {
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            padding: 4px 8px;
            color: #0f172a;
        }
        
        QComboBox::drop-down {
            border: none;
        }
        
        QSpinBox, QDoubleSpinBox {
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            padding: 4px 8px;
            color: #0f172a;
        }
        
        QLineEdit {
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            padding: 4px 8px;
            color: #0f172a;
        }
        
        QSlider::groove:horizontal {
            border: 1px solid #cbd5e1;
            height: 6px;
            background-color: #f1f5f9;
            border-radius: 3px;
        }
        
        QSlider::handle:horizontal {
            background-color: #2563eb;
            border: 1px solid #1d4ed8;
            width: 16px;
            height: 16px;
            border-radius: 8px;
            margin: -6px 0;
        }
        
        QSlider::sub-page:horizontal {
            background-color: #2563eb;
            border-radius: 3px;
        }
        
        QLCDNumber {
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            color: #16a34a;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }
        
        QCheckBox::indicator:unchecked {
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 3px;
        }
        
        QCheckBox::indicator:checked {
            background-color: #2563eb;
            border: 1px solid #1d4ed8;
            border-radius: 3px;
        }
        
        QStatusBar {
            background-color: #ffffff;
            color: #0f172a;
            border-top: 1px solid #cbd5e1;
        }
        
        QMenuBar {
            background-color: #f8fafc;
            color: #0f172a;
            border-bottom: 1px solid #cbd5e1;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 8px;
        }
        
        QMenuBar::item:selected {
            background-color: #e2e8f0;
        }
        
        QMenu {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
        }
        
        QMenu::item {
            padding: 4px 16px;
        }
        
        QMenu::item:selected {
            background-color: #2563eb;
            color: #ffffff;
        }
        """
    
    def get_current_theme(self) -> str:
        """Get current theme name"""
        return self.current_theme