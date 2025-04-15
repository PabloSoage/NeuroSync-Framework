"""
Keyboard visualization module.

This module provides visualization components for keyboard input events,
displaying a virtual keyboard with key highlight states using PyQt5.
"""
from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush
from PyQt5.QtCore import Qt, QRect, QSize

from ..interfaces import InputData


class KeyboardVisualizer(QWidget):
    """
    Visualizes keyboard input events with a virtual keyboard display.
    
    This class creates a visual representation of a keyboard and highlights keys
    based on their state (pressed, tracked, etc.). It provides real-time visual
    feedback for keyboard input events.
    """
    
    DEFAULT_KEYBOARD_LAYOUT = [
        ["Esc", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"],
        ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "Backspace"],
        ["Tab", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]", "\\"],
        ["Caps", "A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'", "Enter"],
        ["Shift", "Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "Shift"],
        ["Ctrl", "Win", "Alt", "Space", "Alt", "Menu", "Ctrl"]
    ]
    
    def __init__(self, parent=None) -> None:
        """
        Initialize the keyboard visualizer.
        """
        super().__init__(parent)
        
        # Define dark theme colors
        self.dark_bg = QColor("#2D2D30")
        self.dark_frame_bg = QColor("#252526")
        self.key_bg = QColor("#3E3E42")
        self.key_text = QColor("#E0E0E0")
        self.tracked_key_bg = QColor("#444466")
        self.active_key_bg = QColor("#007ACC")
        self.secondary_key_bg = QColor("#5FB878")
        self.record_key_bg = QColor("#AA3333")
        
        # Store key state
        self.active_keys = set()
        self.tracked_keys = set()
        
        # Key mappings for special keys
        self.key_mappings = {}
        self._create_key_mappings()
        
        # Set size policy and minimum size
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(400, 200)
    
    def _create_key_mappings(self) -> None:
        """Create mappings for special keys"""
        # Map lowercase keys to their labels in the layout
        for row in self.DEFAULT_KEYBOARD_LAYOUT:
            for key in row:
                self.key_mappings[key.lower()] = key
        
        # Add special key mappings
        self.key_mappings["key.space"] = "Space"
        self.key_mappings["space"] = "Space"
        self.key_mappings[" "] = "Space"
        
        self.key_mappings["key.shift"] = "Shift"
        self.key_mappings["key.shift_l"] = "Shift"
        self.key_mappings["key.shift_r"] = "Shift"
        
        self.key_mappings["key.media_play_pause"] = "F9"
        self.key_mappings["key.f9"] = "F9"
    
    def set_tracked_keys(self, keys) -> None:
        """
        Set the list of tracked keys to highlight differently.
        
        Args:
            keys: List of key names to track and highlight
        """
        self.tracked_keys = {k.lower() for k in keys}
        self.update()  # Request a repaint
    
    def update(self, input_data=None) -> None:
        """
        Update the keyboard visualization based on input data.
        
        Updates the visual state of the keyboard based on the input event,
        highlighting pressed keys and tracking active keys.
        
        Args:
            input_data: Input event data containing active keys and event information
        """
        if input_data is not None and hasattr(input_data, 'active_keys') and input_data.active_keys is not None:
            # Clear previous active keys and use the ones from the event
            self.active_keys = set()
            
            # Process active keys
            for key in input_data.active_keys:
                norm_key = key.lower()
                
                # Normalize representation of special keys
                if norm_key == "key.space" or norm_key == " " or norm_key == "space":
                    norm_key = "key.space"
                elif "key.shift" in norm_key or norm_key in ["key.shift", "key.shift_l", "key.shift_r"]:
                    norm_key = "key.shift"
                
                # Add to active keys set
                self.active_keys.add(norm_key)
        
        # Call the base class update method to request a repaint
        super().update()
    
    def paintEvent(self, event) -> None:
        """
        Paint the keyboard layout with appropriate highlighting.
        
        Args:
            event: The paint event
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), self.dark_bg)
        
        # Calculate keyboard dimensions
        width = self.width()
        height = self.height()
        
        # Scale font and key sizes based on available space
        font_size = max(7, min(10, int(width / 55)))
        font = QFont("Segoe UI", font_size)
        painter.setFont(font)
        
        # Calculate key dimensions
        num_rows = len(self.DEFAULT_KEYBOARD_LAYOUT)
        max_keys_in_row = max(len(row) for row in self.DEFAULT_KEYBOARD_LAYOUT)
        
        key_width = max(20, width / (max_keys_in_row + 2))
        key_height = max(10, height / (num_rows + 1))
        
        # Draw keys
        y_offset = key_height / 2
        for row_idx, row in enumerate(self.DEFAULT_KEYBOARD_LAYOUT):
            # Center the row horizontally
            row_width = key_width * (len(row) + (len(row) - 1) * 0.2)
            x_offset = (width - row_width) / 2
            
            for key_label in row:
                # Define key rectangle
                key_width_actual = key_width
                if key_label == "Space":
                    key_width_actual = key_width * 4
                elif key_label in ["Backspace", "Enter"]:
                    key_width_actual = key_width * 1.8
                elif key_label in ["Shift", "Tab"]:
                    key_width_actual = key_width * 1.5
                
                key_rect = QRect(
                    int(x_offset),
                    int(y_offset),
                    int(key_width_actual),
                    int(key_height)
                )
                
                # Determine key color based on state
                key_lower = key_label.lower()
                
                # Default key background
                key_color = self.key_bg
                
                # Special handling for spacebar
                if key_lower == "space":
                    key_color = QColor("#464649")
                
                # Special handling for F9/record key
                if key_lower == "f9":
                    key_color = self.record_key_bg
                
                # Check if the key is tracked
                for tracked_key in self.tracked_keys:
                    if tracked_key.lower() == key_lower or (
                        tracked_key == "key.space" and key_lower == "space"
                    ) or (
                        tracked_key == "key.shift" and key_lower == "shift"
                    ) or (
                        tracked_key == "key.media_play_pause" and key_lower == "f9"
                    ):
                        key_color = self.tracked_key_bg
                        break
                
                # Check if the key is active
                is_active = False
                for active_key in self.active_keys:
                    active_key_lower = active_key.lower()
                    
                    # Handle the spacebar
                    if (active_key_lower in ["key.space", "space", " "] and key_lower == "space"):
                        key_color = self.active_key_bg
                        is_active = True
                        break
                    # Handle the shift key
                    elif (active_key_lower in ["key.shift", "key.shift_l", "key.shift_r"] and key_lower == "shift"):
                        key_color = self.active_key_bg
                        is_active = True
                        break
                    # Handle the media play/pause key (F9)
                    elif (active_key_lower == "key.media_play_pause" and key_lower == "f9"):
                        key_color = QColor("#FF5555")  # Brighter red for active state
                        is_active = True
                        break
                    # Handle regular keys
                    elif active_key_lower == key_lower:
                        is_tracked = key_lower in self.tracked_keys
                        key_color = self.active_key_bg if is_tracked else self.secondary_key_bg
                        is_active = True
                        break
                
                # Draw the key
                pen = QPen(Qt.NoPen)
                if is_active:
                    # Use a sunken effect for active keys
                    offset = 1
                    shadow_rect = key_rect.adjusted(offset, offset, 0, 0)
                    painter.fillRect(shadow_rect, QColor(0, 0, 0, 70))
                
                painter.setPen(pen)
                painter.setBrush(QBrush(key_color))
                painter.drawRect(key_rect)
                
                # Draw key text
                painter.setPen(QPen(self.key_text))
                
                # Special handling for F9 key
                if key_lower == "f9":
                    # Draw the F9 text
                    painter.drawText(key_rect, Qt.AlignCenter, "F9\n(REC)")
                else:
                    # Draw regular key text
                    painter.drawText(key_rect, Qt.AlignCenter, key_label)
                
                # Move to next key
                x_offset += key_width_actual * 1.2
            
            # Move to next row
            y_offset += key_height * 1.2
    
    def sizeHint(self) -> QSize:
        """Suggested size for the widget"""
        return QSize(500, 300)
    
    def force_update(self) -> None:
        """Force a redraw of the keyboard"""
        self.update()