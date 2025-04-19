"""
UI factory for the integrated BCI system.

This module provides factory methods for creating consistent UI components.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QPushButton, QCheckBox, QRadioButton, QLineEdit, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor


class UIFactory:
    """
    Factory class for creating UI components with consistent styling.
    
    This class follows the Factory pattern to centralize UI component creation
    and ensure consistent styling throughout the application.
    """
    
    # Color scheme
    DARK_BG = "#2D2D30"
    DARK_FRAME_BG = "#252526" 
    TEXT_COLOR = "#E0E0E0"
    ACCENT_COLOR = "#007ACC"
    SUCCESS_COLOR = "#5FB878"
    WARNING_COLOR = "#FFAA33"
    ERROR_COLOR = "#FF5555"
    
    @classmethod
    def create_control_panel(cls, title="Controls"):
        """Create a standard control panel group box."""
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        return group, layout
    
    @classmethod
    def create_status_display(cls, status_items=None):
        """
        Create a status display with multiple status items.
        
        Args:
            status_items: Dictionary of status item labels and initial values
            
        Returns:
            tuple: (widget, layout, status_labels_dict)
        """
        if status_items is None:
            status_items = {}
            
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        status_labels = {}
        
        for label_text, initial_value in status_items.items():
            item_layout = QHBoxLayout()
            item_layout.addWidget(QLabel(f"{label_text}:"))
            
            status_label = QLabel(initial_value)
            item_layout.addWidget(status_label)
            
            status_labels[label_text] = status_label
            layout.addLayout(item_layout)
            
        # Add stretch to push everything to the left
        layout.addStretch(1)
        
        return widget, layout, status_labels
    
    @classmethod
    def create_recording_controls(cls):
        """
        Create recording control elements.
        
        Returns:
            tuple: (widget, layout, record_button, status_label)
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        record_button = QPushButton("Start Recording")
        record_button.setMinimumWidth(150)
        record_button.setStyleSheet(f"background-color: #228822;")
        layout.addWidget(record_button)
        
        status_label = QLabel("Not Recording")
        layout.addWidget(status_label)
        
        # Add stretch to push everything to the left
        layout.addStretch(1)
        
        return widget, layout, record_button, status_label
    
    @classmethod
    def create_file_selector(cls, label_text="File:"):
        """
        Create a file selection control.
        
        Returns:
            tuple: (widget, layout, line_edit, browse_button)
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(QLabel(label_text))
        
        line_edit = QLineEdit()
        line_edit.setReadOnly(True)
        layout.addWidget(line_edit, 1)
        
        browse_button = QPushButton("Browse...")
        layout.addWidget(browse_button)
        
        return widget, layout, line_edit, browse_button
    
    @classmethod
    def create_option_group(cls, title, options=None):
        """
        Create a group of checkboxes or radio buttons.
        
        Args:
            title: Group title
            options: Dictionary mapping option IDs to display names
            
        Returns:
            tuple: (widget, layout, options_dict)
        """
        if options is None:
            options = {}
            
        group = QGroupBox(title)
        layout = QHBoxLayout(group)
        
        options_dict = {}
        
        for option_id, option_name in options.items():
            checkbox = QCheckBox(option_name)
            layout.addWidget(checkbox)
            options_dict[option_id] = checkbox
            
        # Add stretch to prevent excessive spacing
        layout.addStretch(1)
        
        return group, layout, options_dict
    
    @classmethod
    def create_radio_group(cls, title, options=None, vertical=False):
        """
        Create a group of radio buttons.
        
        Args:
            title: Group title
            options: Dictionary mapping option IDs to display names
            vertical: Whether to arrange buttons vertically
            
        Returns:
            tuple: (widget, layout, options_dict)
        """
        if options is None:
            options = {}
            
        group = QGroupBox(title)
        
        if vertical:
            layout = QVBoxLayout(group)
        else:
            layout = QHBoxLayout(group)
            
        options_dict = {}
        
        for option_id, option_name in options.items():
            radio = QRadioButton(option_name)
            layout.addWidget(radio)
            options_dict[option_id] = radio
            
        # Add stretch to prevent excessive spacing
        layout.addStretch(1)
        
        return group, layout, options_dict
    
    @classmethod
    def create_scrollable_container(cls, target_widget):
        """
        Create a scrollable container for a widget.
        
        Args:
            target_widget: Widget to make scrollable
            
        Returns:
            QScrollArea: Scroll area containing the widget
        """
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create container for the target widget
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.addWidget(target_widget)
        
        # Add widget to scroll area
        scroll_area.setWidget(scroll_widget)
        
        return scroll_area
