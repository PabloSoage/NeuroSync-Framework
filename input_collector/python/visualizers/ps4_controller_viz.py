"""
PS4 controller visualization module.

This module provides visualization components for PS4 controller input events,
displaying a virtual controller with joysticks and button states.
"""

from typing import Dict, List, Optional, Set, Tuple

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen

from .visualizer_base import BaseVisualizer
from ..interfaces import InputData


class PS4ControllerVisualizer(BaseVisualizer):
    """
    Visualizer for PS4 controller input.
    
    This class displays a visual representation of the PS4 controller,
    showing the state of buttons and joysticks in real-time.
    """
    
    def __init__(self, parent=None) -> None:
        """Initialize the PS4 controller visualizer."""
        super().__init__(parent)
        
        # Set supported collector types
        self.supported_collectors = ["ps4_controller"]
        
        # Controller dimensions and layout
        self.setMinimumSize(500, 300)
        
        # Button state tracking
        self.active_buttons: Set[str] = set()
        self.tracked_buttons: Set[str] = set()
        
        # Joystick positions: [left_x, left_y, right_x, right_y]
        self.joystick_positions = [0.0, 0.0, 0.0, 0.0]
        
        # Trigger values: [L2, R2]
        self.trigger_values = [0.0, 0.0]
        
        # Colors
        self.bg_color = QColor(40, 40, 45)
        self.controller_color = QColor(50, 50, 55)
        self.button_color = QColor(70, 70, 75)
        self.active_color = QColor(0, 114, 206)  # PlayStation blue
        self.inactive_color = QColor(80, 80, 85)
        self.joystick_color = QColor(30, 30, 35)
        self.joystick_active_color = QColor(0, 114, 206)
        self.text_color = QColor(200, 200, 210)
        
        # Define button mapping (button_name: (x, y, width, height))
        # Coordinates are relative (0-100) to make resizing easier
        self.button_positions: Dict[str, Tuple[float, float, float, float]] = {
            "Cross": (75, 55, 6, 6),  # Cross button (bottom button)
            "Circle": (82, 48, 6, 6),  # Circle button (right button)
            "Square": (68, 48, 6, 6),  # Square button (left button)
            "Triangle": (75, 41, 6, 6),  # Triangle button (top button)
            
            "DPad_Up": (32, 41, 6, 6),  # D-Pad Up
            "DPad_Right": (39, 48, 6, 6),  # D-Pad Right
            "DPad_Down": (32, 55, 6, 6),  # D-Pad Down
            "DPad_Left": (25, 48, 6, 6),  # D-Pad Left
            
            "Share": (32, 30, 8, 4),  # Share button
            "Options": (68, 30, 8, 4),  # Options button
            "PS": (50, 48, 8, 8),  # PS button
            "Touchpad": (50, 30, 16, 8),  # Touchpad
            
            "L1": (25, 20, 12, 5),  # L1 button
            "R1": (75, 20, 12, 5),  # R1 button
            
            "L3": (32, 65, 6, 6),  # Left stick press
            "R3": (68, 65, 6, 6),  # Right stick press
        }
        
        # Define joystick positions: (center_x, center_y, radius)
        self.joystick_layout = {
            "LeftStick": (32, 65, 10),   # Left joystick: (x, y, radius)
            "RightStick": (68, 65, 10),  # Right joystick: (x, y, radius)
        }
        
        # Define trigger positions: (x, y, width, height)
        self.trigger_layout = {
            "L2_Trigger": (25, 12, 12, 5),  # L2 trigger
            "R2_Trigger": (75, 12, 12, 5),  # R2 trigger
        }
        
        # Flag for safe rendering
        self.initialized = True
    
    def update(self, input_data: Optional[InputData] = None) -> None:
        """
        Update the visualization based on input data.
        
        Args:
            input_data: Input event data containing controller state
        """
        if not input_data:
            super().update()
            return
        
        try:
            # Update active buttons based on input data
            if hasattr(input_data, 'active_keys') and input_data.active_keys:
                self.active_buttons = set(input_data.active_keys)
            
            # Update joystick positions
            if input_data.event_type == "axis_motion":
                if hasattr(input_data, 'key'):
                    if input_data.key == "LeftStick_X" and input_data.rel_x is not None:
                        self.joystick_positions[0] = input_data.rel_x
                    elif input_data.key == "LeftStick_Y" and input_data.rel_y is not None:
                        self.joystick_positions[1] = input_data.rel_y
                    elif input_data.key == "RightStick_X" and input_data.rel_x is not None:
                        self.joystick_positions[2] = input_data.rel_x
                    elif input_data.key == "RightStick_Y" and input_data.rel_y is not None:
                        self.joystick_positions[3] = input_data.rel_y
                    elif input_data.key == "L2_Trigger" and input_data.rel_x is not None:
                        self.trigger_values[0] = input_data.rel_x
                    elif input_data.key == "R2_Trigger" and input_data.rel_x is not None:
                        self.trigger_values[1] = input_data.rel_x
            
            # Trigger a repaint
            self.repaint()
            
        except Exception as e:
            print(f"Error updating PS4 controller visualization: {e}")
            import traceback
            traceback.print_exc()
    
    def set_tracked_keys(self, keys: List[str]) -> None:
        """
        Set which buttons are tracked/highlighted.
        
        Args:
            keys: List of button names to track
        """
        try:
            self.tracked_buttons = set()
            
            for key in keys:
                # Add PS4 controller specific buttons
                if any(btn in key for btn in ["Cross", "Circle", "Square", "Triangle", "L1", "R1", 
                                            "DPad", "Share", "Options", "PS", "L3", "R3", "L2_Trigger", "R2_Trigger",
                                            "LeftStick", "RightStick"]):
                    self.tracked_buttons.add(key)
            
            # Update display
            self.update()
        
        except Exception as e:
            print(f"Error setting tracked keys in PS4 visualizer: {e}")
    
    def paintEvent(self, event) -> None:
        """Paint the PS4 controller visualization."""
        try:
            # Safety check to prevent crashes
            if not hasattr(self, 'initialized') or not self.initialized:
                return
                
            # Create painter
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Get dimensions
            w = self.width()
            h = self.height()
            
            # Draw background
            painter.fillRect(self.rect(), self.bg_color)
            
            # Draw controller outline
            controller_rect = QRectF(w * 0.05, h * 0.05, w * 0.9, h * 0.9)
            painter.setBrush(QBrush(self.controller_color))
            painter.setPen(QPen(QColor(60, 60, 65), 2))
            painter.drawRoundedRect(controller_rect, 15, 15)
            
            # Helper function to convert relative coordinates to actual coordinates
            def rel_to_actual(x, y, width, height):
                """Convert relative coordinates (0-100) to actual widget coordinates."""
                return (
                    int(x * w / 100), 
                    int(y * h / 100),
                    int(width * w / 100), 
                    int(height * h / 100)
                )
            
            # Draw triggers
            for trigger_name, (x, y, width, height) in self.trigger_layout.items():
                tx, ty, tw, th = rel_to_actual(x, y, width, height)
                trigger_rect = QRectF(tx, ty, tw, th)
                
                # Determine if trigger is active and tracked
                is_active = trigger_name in self.active_buttons
                is_tracked = trigger_name in self.tracked_buttons
                
                # Get trigger value (0.0 to 1.0)
                trigger_value = 0.0
                if trigger_name == "L2_Trigger":
                    trigger_value = self.trigger_values[0]
                elif trigger_name == "R2_Trigger":
                    trigger_value = self.trigger_values[1]
                
                # Draw trigger base
                painter.setBrush(QBrush(self.button_color))
                painter.setPen(QPen(QColor(80, 80, 85), 1))
                painter.drawRoundedRect(trigger_rect, 3, 3)
                
                # Draw trigger fill based on value
                if trigger_value > 0.02 and is_tracked:  # Small threshold to avoid drawing for tiny values
                    fill_width = tw * trigger_value
                    fill_rect = QRectF(tx, ty, fill_width, th)
                    painter.setBrush(QBrush(self.joystick_active_color))
                    painter.setPen(Qt.NoPen)
                    painter.drawRoundedRect(fill_rect, 3, 3)
                
                # Draw trigger label
                painter.setPen(self.text_color)
                font = painter.font()
                font.setPointSize(8)
                painter.setFont(font)
                trigger_label = trigger_name.replace("_Trigger", "")
                painter.drawText(trigger_rect, Qt.AlignCenter, trigger_label)
            
            # Draw buttons
            for btn_name, (x, y, width, height) in self.button_positions.items():
                bx, by, bw, bh = rel_to_actual(x, y, width, height)
                button_rect = QRectF(bx, by, bw, bh)
                
                # Determine if button is active and tracked
                is_active = btn_name in self.active_buttons
                is_tracked = btn_name in self.tracked_buttons
                
                # Choose button color based on state
                if is_active and is_tracked:
                    # Button is pressed and tracked
                    button_fill = self.active_color
                    pen_color = QColor(100, 160, 255)  # Lighter blue border
                elif is_tracked:
                    # Button is tracked but not pressed
                    button_fill = self.button_color
                    pen_color = QColor(0, 114, 206)  # PlayStation blue border
                else:
                    # Button is not tracked
                    button_fill = self.inactive_color
                    pen_color = QColor(90, 90, 95)  # Subtle border
                
                # Draw button
                painter.setBrush(QBrush(button_fill))
                painter.setPen(QPen(pen_color, 1))
                
                # Special handling for PS button (circle shape)
                if btn_name == "PS":
                    # Use QRectF for PS button ellipse
                    painter.drawEllipse(button_rect)
                else:
                    # Round corners more for trigger buttons
                    corner_radius = 5 if "Options" in btn_name or "Share" in btn_name or "Touchpad" in btn_name else 3
                    painter.drawRoundedRect(button_rect, corner_radius, corner_radius)
                
                # Draw button label
                painter.setPen(self.text_color)
                font = painter.font()
                
                # Adjust font size based on button size
                if btn_name in ["Cross", "Circle", "Square", "Triangle"]:
                    font.setPointSize(9)
                    # Map button names to symbols
                    symbol_map = {
                        "Cross": "×",
                        "Circle": "○",
                        "Square": "□",
                        "Triangle": "△"
                    }
                    label = symbol_map.get(btn_name, btn_name)
                elif btn_name == "PS":
                    font.setPointSize(7)
                    label = "PS"
                elif btn_name.startswith("DPad"):
                    # For D-Pad, show arrow symbols
                    font.setPointSize(8)
                    arrow_map = {
                        "DPad_Up": "↑",
                        "DPad_Right": "→",
                        "DPad_Down": "↓",
                        "DPad_Left": "←"
                    }
                    label = arrow_map.get(btn_name, btn_name.replace("DPad_", ""))
                else:
                    # For other buttons, show abbreviated label
                    font.setPointSize(7)
                    label_map = {
                        "Options": "OPT",
                        "Share": "SHR",
                        "Touchpad": "PAD",
                        "L1": "L1",
                        "R1": "R1",
                        "L3": "L3",
                        "R3": "R3"
                    }
                    label = label_map.get(btn_name, btn_name)
                
                painter.setFont(font)
                painter.drawText(button_rect, Qt.AlignCenter, label)
            
            # Draw joysticks
            for stick_name, (center_x, center_y, radius) in self.joystick_layout.items():
                # Convert relative coordinates - fixing the unpacking error
                cx, cy, r, _ = rel_to_actual(center_x, center_y, radius, radius)
                
                # Get joystick position values
                x_value = 0.0
                y_value = 0.0
                is_tracked = False
                
                if stick_name == "LeftStick":
                    x_value = self.joystick_positions[0]
                    y_value = self.joystick_positions[1]
                    is_tracked = "LeftStick_X" in self.tracked_buttons or "LeftStick_Y" in self.tracked_buttons
                elif stick_name == "RightStick":
                    x_value = self.joystick_positions[2]
                    y_value = self.joystick_positions[3]
                    is_tracked = "RightStick_X" in self.tracked_buttons or "RightStick_Y" in self.tracked_buttons
                
                # Draw joystick base
                base_color = self.joystick_color
                if is_tracked:
                    base_color = QColor(60, 60, 65)
                
                painter.setBrush(QBrush(base_color))
                painter.setPen(QPen(QColor(70, 70, 75), 1))
                
                # Use QRectF for joystick base ellipse
                base_rect = QRectF(cx - r, cy - r, r * 2, r * 2)
                painter.drawEllipse(base_rect)
                
                # Calculate joystick nub position
                nub_radius = r * 0.6
                offset_x = x_value * (r - nub_radius * 0.8)
                offset_y = y_value * (r - nub_radius * 0.8)
                nub_x = cx + offset_x
                nub_y = cy + offset_y
                
                # Draw joystick nub
                nub_color = self.joystick_active_color if is_tracked else QColor(100, 100, 105)
                if abs(x_value) > 0.1 or abs(y_value) > 0.1:
                    # Highlight when moved
                    nub_color = QColor(30, 144, 255) if is_tracked else QColor(130, 130, 135)
                
                painter.setBrush(QBrush(nub_color))
                painter.setPen(QPen(QColor(90, 90, 95), 1))
                
                # Use QRectF for joystick nub ellipse
                nub_rect = QRectF(nub_x - nub_radius, nub_y - nub_radius, nub_radius * 2, nub_radius * 2)
                painter.drawEllipse(nub_rect)
                
                # Draw label
                label = "L" if stick_name == "LeftStick" else "R"
                painter.setPen(self.text_color)
                font = painter.font()
                font.setPointSize(7)
                painter.setFont(font)
                painter.drawText(QRectF(nub_x - nub_radius, nub_y - nub_radius, nub_radius * 2, nub_radius * 2), 
                                Qt.AlignCenter, label)
            
            # End painting
            painter.end()
            
        except Exception as e:
            print(f"Error painting PS4 controller visualizer: {e}")
            import traceback
            traceback.print_exc()
    
    def force_update(self) -> None:
        """Force an update of the visualization."""
        try:
            self.update()
        except Exception as e:
            print(f"Error forcing update of PS4 controller visualizer: {e}")
