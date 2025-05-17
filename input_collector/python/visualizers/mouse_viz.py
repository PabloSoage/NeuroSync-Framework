"""
Mouse visualization module.

This module provides visualization components for mouse input events,
displaying mouse movement and button states in a joystick-like interface using PyQt5.
"""

import math
from typing import Dict, Any

from PyQt5.QtCore import Qt, QPoint, QRect, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygon
from PyQt5.QtWidgets import QWidget, QSizePolicy, QVBoxLayout, QLabel, QFrame

from .visualizer_base import BaseVisualizer


class MouseVisualizer(BaseVisualizer):
    """
    Visualizes mouse input events with joystick-like representation.

    This class creates a visual representation of mouse movement and input state
    using a joystick-like display. It shows movement direction, speed, mouse button
    states, and scroll events in real-time.
    """

    def __init__(self, parent=None) -> None:
        """
        Initialize the mouse visualizer.
        """
        super().__init__(parent)

        # Define dark theme colors
        self.dark_bg = QColor("#2D2D30")
        self.dark_frame_bg = QColor("#252526")
        self.text_color = QColor("#E0E0E0")
        self.accent_color = QColor("#007ACC")
        self.highlight_color = QColor("#3E3E42")

        # Set size policy and minimum size - aumentar el tamaño mínimo para evitar recortes
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(300, 300)  # Aumentar la altura mínima

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Canvas takes most of the space - aumentar la proporción
        self.canvas = Canvas(self)
        layout.addWidget(self.canvas, 5)  # Aumentar proporción

        # Info label
        self.info_label = QLabel("Mouse: Not moving")
        self.info_label.setStyleSheet(
            f"background-color: #252526; color: {self.text_color.name()}; padding: 5px;"
        )
        self.info_label.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        layout.addWidget(self.info_label, 0)

        # Button status label
        self.button_label = QLabel("Buttons: None")
        self.button_label.setStyleSheet(
            f"background-color: #252526; color: {self.text_color.name()}; padding: 5px;"
        )
        self.button_label.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        layout.addWidget(self.button_label, 0)
        
        # Set which collectors this visualizer supports
        self.supported_collectors = ["keyboard_mouse"]

    def update(self, input_data=None) -> None:
        """
        Update the mouse visualization based on input data.

        Args:
            input_data: Input event data containing mouse state information
        """
        if input_data is not None:
            # Update canvas
            self.canvas.update_state(input_data)

            # Update info text based on tracking mode
            tracking_mode = getattr(input_data, "mouse_tracking_mode", "joystick")
            is_moving = getattr(input_data, "is_moving", False)

            status_text = f"Mouse: {'Moving' if is_moving else 'Not moving'}"

            if tracking_mode == "delta":
                if is_moving:
                    pass
                    
                if input_data.direction:
                    pass
                    
                if (
                    hasattr(input_data, "wheel_direction")
                    and input_data.wheel_direction
                ):
                    pass

            elif tracking_mode == "angle":
                # Handle direction-only angle mode
                if hasattr(input_data, "direction_only") and input_data.direction_only:
                    pass
                else:
                    pass

            elif tracking_mode == "axis":
                # Axis mode with membership values
                if is_moving and hasattr(input_data, "north"):
                    pass

            else:  # joystick mode
                if input_data.direction and is_moving:
                    pass
                    
                if is_moving and hasattr(input_data, "speed"):
                    pass

            if hasattr(input_data, "wheel_direction") and input_data.wheel_direction:
                status_text += f" | Wheel:{input_data.wheel_direction}"

            self.info_label.setText(status_text)

            # Update button text
            button_states = []
            if (
                hasattr(self.canvas, "left_button_pressed")
                and self.canvas.left_button_pressed
            ):
                button_states.append("Left")
            if (
                hasattr(self.canvas, "right_button_pressed")
                and self.canvas.right_button_pressed
            ):
                button_states.append("Right")
            if (
                hasattr(self.canvas, "middle_button_pressed")
                and self.canvas.middle_button_pressed
            ):
                button_states.append("Middle")

            button_text = "Buttons: " + (
                ", ".join(button_states) if button_states else "None"
            )
            self.button_label.setText(button_text)

        super().update()

    def force_update(self) -> None:
        """Force a redraw of the visualization"""
        self.canvas.update()
        self.update()

    def sizeHint(self) -> QSize:
        """Suggested size for the widget"""
        return QSize(400, 350)
    
    def set_collector_capabilities(self, capabilities: Dict[str, Any]) -> None:
        """Configure the visualizer based on collector capabilities."""
        super().set_collector_capabilities(capabilities)
        # We could adjust the visualization based on capabilities
        self.setVisible(capabilities.get("supports_mouse_movement", False))


class Canvas(QWidget):
    """The actual mouse visualization canvas"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(300, 270)  # Aumentado a 270 para mejor visualización

        # Define dark theme colors
        self.dark_bg = QColor("#1E1E1E")
        self.accent_color = QColor("#007ACC")
        self.text_color = QColor("#E0E0E0")
        self.highlight_color = QColor("#5FB878")

        # Mouse state
        self.mouse_x = 0
        self.mouse_y = 0
        self.rel_x = 0.0
        self.rel_y = 0.0
        self.movement_direction = None
        self.left_button_pressed = False
        self.right_button_pressed = False
        self.middle_button_pressed = False
        self.is_moving = False
        self.speed = 0.0
        self.speed_x = 0.0
        self.speed_y = 0.0
        self.wheel_direction = None

        # Delta tracking fields
        self.delta_x = 0.0
        self.delta_y = 0.0
        self.delta_magnitude = 0.0
        self.delta_angle = 0.0
        self.tracking_mode = "joystick"

        # Direction-only fields
        self.direction_only = False
        self.discrete_angle = 0
        self.north = 0.0
        self.south = 0.0
        self.east = 0.0
        self.west = 0.0

    def update_state(self, input_data):
        """Update the visualization state based on input data"""
        # Handle mouse click events
        if input_data.event_type == "mouse_click":
            if input_data.button_pressed:
                if "left" in input_data.button_pressed.lower():
                    self.left_button_pressed = True
                elif "right" in input_data.button_pressed.lower():
                    self.right_button_pressed = True
                elif "middle" in input_data.button_pressed.lower():
                    self.middle_button_pressed = True
            else:
                # Button release
                if "left" in str(input_data):
                    self.left_button_pressed = False
                elif "right" in str(input_data):
                    self.right_button_pressed = False
                elif "middle" in str(input_data):
                    self.middle_button_pressed = False
                else:
                    self.left_button_pressed = False
                    self.right_button_pressed = False
                    self.middle_button_pressed = False

        # Handle mouse scroll events - SIMPLIFIED LOGIC FOR WHEEL VISUALIZATION
        if input_data.event_type == "mouse_scroll":
            # Always update wheel direction based on event direction
            # If the scroll is being tracked, we'll receive events with non-None directions
            # If the scroll event is a reset event, direction will be None
            self.wheel_direction = input_data.direction
            
            # Debug print to verify we're setting wheel direction correctly
            if input_data.direction:
                print(f"Setting wheel direction to: {input_data.direction}")
            elif input_data.direction is None:
                print("Resetting wheel direction to None")

        # Handle actual coordinates and movement state
        if input_data.rel_x is not None and input_data.rel_y is not None:
            self.rel_x = input_data.rel_x
            self.rel_y = input_data.rel_y

        # Update movement state
        if input_data.event_type == "mouse_move":
            self.movement_direction = input_data.direction
            if input_data.is_moving is not None:
                self.is_moving = input_data.is_moving

            # Update speeds if provided and movement is happening
            if self.is_moving and input_data.speed is not None:
                self.speed = input_data.speed
                if input_data.speed_x is not None:
                    self.speed_x = input_data.speed_x
                if input_data.speed_y is not None:
                    self.speed_y = input_data.speed_y

        # Update with delta tracking data if available
        if (
            hasattr(input_data, "mouse_delta_x")
            and input_data.mouse_delta_x is not None
        ):
            self.delta_x = input_data.mouse_delta_x
        if (
            hasattr(input_data, "mouse_delta_y")
            and input_data.mouse_delta_y is not None
        ):
            self.delta_y = input_data.mouse_delta_y
        if (
            hasattr(input_data, "mouse_delta_magnitude")
            and input_data.mouse_delta_magnitude is not None
        ):
            self.delta_magnitude = input_data.mouse_delta_magnitude
        if (
            hasattr(input_data, "mouse_delta_angle")
            and input_data.mouse_delta_angle is not None
        ):
            self.delta_angle = input_data.mouse_delta_angle
        if (
            hasattr(input_data, "mouse_tracking_mode")
            and input_data.mouse_tracking_mode is not None
        ):
            self.tracking_mode = input_data.mouse_tracking_mode

        # Update direction-only flag and related fields
        if hasattr(input_data, "direction_only"):
            self.direction_only = input_data.direction_only
        if (
            hasattr(input_data, "discrete_angle")
            and input_data.discrete_angle is not None
        ):
            self.discrete_angle = input_data.discrete_angle
        if hasattr(input_data, "north") and input_data.north is not None:
            self.north = input_data.north
            self.south = input_data.south if hasattr(input_data, "south") else 0
            self.east = input_data.east if hasattr(input_data, "east") else 0
            self.west = input_data.west if hasattr(input_data, "west") else 0

        self.update()  # Request repaint

    def paintEvent(self, event):
        """Paint the mouse visualization"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Fill background
        painter.fillRect(self.rect(), self.dark_bg)

        # Calculate joystick circle radius
        radius = min(self.width(), self.height()) * 0.25

        # Calculate center coordinates
        center_x = self.width() / 2
        center_y = self.height() / 2

        # Draw joystick area background
        pen = QPen(self.accent_color, 1)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.drawEllipse(
            QPoint(int(center_x), int(center_y)), int(radius), int(radius)
        )

        # Draw coordinate axes
        pen = QPen(QColor(85, 85, 85), 1, Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(
            int(center_x - radius), int(center_y), int(center_x + radius), int(center_y)
        )
        painter.drawLine(
            int(center_x), int(center_y - radius), int(center_x), int(center_y + radius)
        )

        # Draw center indicator
        pen = QPen(QColor(85, 85, 85), 1)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(62, 62, 66)))
        painter.drawEllipse(QPoint(int(center_x), int(center_y)), 5, 5)

        # Draw axis labels
        font = QFont("Consolas", max(9, min(11, int(self.width() / 40))))
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255)))

        # Right label (X+)
        painter.drawText(int(center_x + radius + 5), int(center_y), "X+")
        # Left label (X-)
        painter.drawText(int(center_x - radius - 25), int(center_y), "X-")
        # Top label (Y-)
        painter.drawText(int(center_x - 10), int(center_y - radius - 10), "Y-")
        # Bottom label (Y+)
        painter.drawText(int(center_x - 10), int(center_y + radius + 20), "Y+")

        # Calculate joystick position
        joystick_x = center_x + (self.rel_x * radius)
        joystick_y = center_y + (self.rel_y * radius)

        # Calculate joystick magnitude (distance from center)
        joystick_magnitude = math.sqrt(self.rel_x**2 + self.rel_y**2)

        # Visual indicator for when at the edge
        if joystick_magnitude > 0.95:
            # Use a slightly larger handle at the edge
            handle_radius = radius * 0.12
            handle_outline_width = 2
            handle_outline_color = QColor(255, 85, 85)
        else:
            handle_radius = radius * 0.1
            handle_outline_width = 1
            handle_outline_color = QColor(255, 255, 255)

        # Update handle color based on button state - improve right click contrast with green
        handle_fill = (
            QColor(255, 85, 85)  # Red for left button
            if self.left_button_pressed
            else (
                QColor(95, 184, 120)  # Change from blue-ish to green for right button
                if self.right_button_pressed
                else (
                    QColor(170, 85, 170)  # Keep purple for middle button
                    if self.middle_button_pressed
                    else self.accent_color  # Default blue
                )
            )
        )

        # Draw direction line if moving
        if self.is_moving and self.movement_direction:
            pen = QPen(QColor(95, 184, 120), 2)
            painter.setPen(pen)
            painter.drawLine(
                int(center_x), int(center_y), int(joystick_x), int(joystick_y)
            )

        # Draw joystick handle
        pen = QPen(handle_outline_color, handle_outline_width)
        painter.setPen(pen)
        painter.setBrush(QBrush(handle_fill))
        painter.drawEllipse(
            QPoint(int(joystick_x), int(joystick_y)),
            int(handle_radius),
            int(handle_radius),
        )

        # Draw wheel indicator if needed
        if self.wheel_direction:
            wheel_y_offset = -15 if self.wheel_direction == "up" else 15
            wheel_color = (
                QColor(95, 184, 120)
                if self.wheel_direction == "up"
                else QColor(255, 85, 85)
            )

            points = QPolygon(
                [
                    QPoint(int(joystick_x - 10), int(joystick_y + wheel_y_offset)),
                    QPoint(int(joystick_x), int(joystick_y + wheel_y_offset * 2)),
                    QPoint(int(joystick_x + 10), int(joystick_y + wheel_y_offset)),
                ]
            )

            pen = QPen(QColor(255, 255, 255), 1)
            painter.setPen(pen)
            painter.setBrush(QBrush(wheel_color))
            painter.drawPolygon(points)

        # Draw coordinate text based on tracking mode
        font = QFont("Consolas", max(8, min(9, int(self.width() / 55))))
        painter.setFont(font)
        painter.setPen(QPen(self.text_color))

        if self.tracking_mode == "delta":
            text = f"Delta: ({self.delta_x:.2f}, {self.delta_y:.2f})"
        elif self.tracking_mode == "angle":
            if self.direction_only:
                text = f"Discrete Angle: {self.discrete_angle}°"
            else:
                text = f"Angle: {self.delta_angle:.1f}° Mag: {self.delta_magnitude:.1f}"
        elif self.tracking_mode == "axis":
            text = f"N:{self.north:.1f} S:{self.south:.1f} E:{self.east:.1f} W:{self.west:.1f}"
        else:  # joystick mode
            text = f"Rel: ({self.rel_x:.2f}, {self.rel_y:.2f})"

        # Create text rectangle
        text_rect = QRect(0, int(center_y + radius + 30), self.width(), 20)
        painter.drawText(text_rect, Qt.AlignCenter, text)
