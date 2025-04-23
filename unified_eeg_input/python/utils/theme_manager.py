"""
Theme manager for unified application.

This module provides theme management for the unified application UI.
"""

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication


class UnifiedThemeManager:
    """
    Manages application theme and styling.
    
    This class provides methods to set and manage different application themes.
    """
    
    def __init__(self):
        """Initialize the theme manager with default colors."""
        # Define theme colors
        self.dark_bg = "#2D2D30"
        self.dark_frame_bg = "#252526"
        self.text_color = "#E0E0E0"
        self.accent_color = "#007ACC"
        self.success_color = "#5FB878"
        self.warning_color = "#FFAA33"
        self.error_color = "#FF5555"
    
    def apply_dark_theme(self, widget):
        """
        Apply the dark theme to the specified widget.
        
        Args:
            widget: The widget to apply the theme to
        """
        palette = QPalette()

        # Set colors
        palette.setColor(QPalette.Window, QColor(self.dark_bg))
        palette.setColor(QPalette.WindowText, QColor(self.text_color))
        palette.setColor(QPalette.Base, QColor(self.dark_frame_bg))
        palette.setColor(QPalette.AlternateBase, QColor(self.dark_bg))
        palette.setColor(QPalette.ToolTipBase, QColor(self.dark_bg))
        palette.setColor(QPalette.ToolTipText, QColor(self.text_color))
        palette.setColor(QPalette.Text, QColor(self.text_color))
        palette.setColor(QPalette.Button, QColor(self.dark_bg))
        palette.setColor(QPalette.ButtonText, QColor(self.text_color))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(self.accent_color))
        palette.setColor(QPalette.Highlight, QColor(self.accent_color))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

        widget.setPalette(palette)

        # Set stylesheet for detailed control
        widget.setStyleSheet(
            f"""
            QMainWindow, QWidget {{ background-color: {self.dark_bg}; color: {self.text_color}; }}
            QGroupBox {{
                border: 1px solid #444;
                margin-top: 0.5em;
                border-radius: 3px;
                padding: 0.5em;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: {self.text_color};
            }}
            QPushButton {{
                background-color: {self.accent_color};
                color: white;
                border: none;
                padding: 4px 8px;
                min-height: 24px;
                border-radius: 2px;
            }}
            QPushButton:pressed {{ background-color: #005599; }}
            QPushButton:hover {{ background-color: #0066aa; }}
            QPushButton:disabled {{
                background-color: #555555;
                color: #999999;
            }}
            QLineEdit, QTextEdit, QListWidget, QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {self.dark_frame_bg};
                color: {self.text_color};
                border: 1px solid #444;
                padding: 2px;
                border-radius: 2px;
            }}
            QTextEdit {{ font-family: 'Consolas', monospace; }}
            QComboBox::drop-down {{ border: 0px; }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
            QSlider::groove:horizontal {{
                border: 1px solid #444;
                height: 8px;
                background: {self.dark_frame_bg};
                margin: 2px 0;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {self.accent_color};
                border: none;
                width: 18px;
                margin: -2px 0;
                border-radius: 4px;
            }}
            QCheckBox::indicator {{
                width: 13px;
                height: 13px;
                border: 1px solid #444;
                border-radius: 2px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.accent_color};
            }}
            QTabWidget::pane {{
                border: 1px solid #444;
                background-color: {self.dark_bg};
            }}
            QTabBar::tab {{
                background-color: {self.dark_frame_bg};
                color: {self.text_color};
                padding: 6px 12px;
                margin-right: 2px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.accent_color};
            }}
            QTabBar::tab:!selected {{
                margin-top: 2px;
            }}
            QScrollArea, QScrollBar {{
                background-color: {self.dark_frame_bg};
                border: 1px solid #444;
            }}
            QLabel {{ color: {self.text_color}; }}
            QRadioButton::indicator {{
                width: 13px;
                height: 13px;
                border-radius: 7px;
                border: 1px solid #444;
            }}
            QRadioButton::indicator:checked {{
                background-color: {self.accent_color};
            }}
        """
        )
