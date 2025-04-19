"""
Mouse buttons selector module.

This module provides a visual component for selecting which mouse buttons to track.
"""

from PyQt5.QtWidgets import QWidget, QSizePolicy, QHBoxLayout
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush
from PyQt5.QtCore import Qt, QRect, QSize, pyqtSignal
from typing import List, Dict, Any

from .visualizer_base import BaseVisualizer


class MouseButton(QWidget):
    """
    Widget representing a mouse button that can be selected/tracked.
    """

    clicked = pyqtSignal(str)  # Signal emitted when button is clicked with button id

    def __init__(self, button_id, label, parent=None):
        """Initialize the mouse button widget."""
        super().__init__(parent)
        self.button_id = button_id
        self.label = label
        self.tracked = False
        self.active = False
        self.edit_mode = False  # Añadir flag para modo edición

        # Define colors
        self.dark_bg = QColor("#2D2D30")
        self.key_bg = QColor("#3E3E42")
        self.key_text = QColor("#E0E0E0")
        self.tracked_key_bg = QColor("#444466")
        self.active_key_bg = QColor("#007ACC")

        # Set size policy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumSize(60, 50)

    def paintEvent(self, event):
        """Paint the button."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Calculate dimensions
        width = self.width()
        height = self.height()

        # Select color based on state
        if self.active:
            bg_color = self.active_key_bg
        elif self.tracked:
            bg_color = self.tracked_key_bg
        else:
            bg_color = self.key_bg

        # Draw button
        rect = QRect(2, 2, width - 4, height - 4)
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 5, 5)

        # Draw text
        painter.setPen(QPen(self.key_text))
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.label)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if (
            event.button() == Qt.LeftButton and self.edit_mode
        ):  # Solo responder en modo edición
            self.clicked.emit(self.button_id)

    def setTracked(self, tracked):
        """Set whether this button is being tracked."""
        if self.tracked != tracked:
            self.tracked = tracked
            self.update()

    def setActive(self, active):
        """Set whether this button is currently active."""
        if self.active != active:
            self.active = active
            self.update()

    def setEditMode(self, edit_mode):
        """Set whether edit mode is active."""
        self.edit_mode = edit_mode
        self.setCursor(Qt.PointingHandCursor if edit_mode else Qt.ArrowCursor)

    def sizeHint(self):
        """Suggested size."""
        return QSize(60, 50)


class MouseButtonsSelector(BaseVisualizer):
    """
    Widget for selecting which mouse buttons to track.
    """

    button_toggled = pyqtSignal(
        str, bool
    )  # Signal emitted when a button is toggled (button_id, is_tracked)

    def __init__(self, parent=None):
        """Initialize the mouse buttons selector."""
        super().__init__(parent)

        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Create buttons
        self.left_button = MouseButton("Button.left", "Left\nClick")
        self.right_button = MouseButton("Button.right", "Right\nClick")
        self.scroll_button = MouseButton("Button.scroll", "Scroll\nWheel")

        # Connect signals
        self.left_button.clicked.connect(self._on_button_clicked)
        self.right_button.clicked.connect(self._on_button_clicked)
        self.scroll_button.clicked.connect(self._on_button_clicked)

        # Add buttons to layout
        layout.addWidget(self.left_button)
        layout.addWidget(self.right_button)
        layout.addWidget(self.scroll_button)

        # Set initial state - typically we want to track left and right clicks by default
        self.left_button.setTracked(True)
        self.right_button.setTracked(True)

        # Set size policy and make el widget más compacto
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMinimumHeight(60)
        self.setMaximumHeight(70)  # Limitar altura máxima
        
        # Set which collectors this visualizer supports
        self.supported_collectors = ["keyboard_mouse"]

    def _on_button_clicked(self, button_id):
        """Handle button clicks."""
        # Find the clicked button
        if button_id == "Button.left":
            button = self.left_button
        elif button_id == "Button.right":
            button = self.right_button
        else:  # scroll
            button = self.scroll_button

        # Toggle tracked state and emit signal
        button.setTracked(not button.tracked)
        self.button_toggled.emit(button_id, button.tracked)

    def setTrackedButtons(self, button_ids):
        """Set which buttons are being tracked."""
        # Convert to lowercase for case-insensitive comparison
        lower_ids = [bid.lower() if isinstance(bid, str) else "" for bid in button_ids]

        # Update button states
        self.left_button.setTracked("button.left".lower() in lower_ids)
        self.right_button.setTracked("button.right".lower() in lower_ids)
        self.scroll_button.setTracked(
            "button.scroll".lower() in lower_ids or "scrollwheel" in lower_ids
        )

    def setActiveButtons(self, active_buttons):
        """Set which buttons are currently active (pressed)."""
        # Convert to lowercase for case-insensitive comparison
        lower_buttons = [
            btn.lower() if isinstance(btn, str) else "" for btn in active_buttons
        ]

        # Update active states
        self.left_button.setActive("button.left".lower() in lower_buttons)
        self.right_button.setActive("button.right".lower() in lower_buttons)
        self.scroll_button.setActive(
            any(scroll in lower_buttons for scroll in ["button.scroll", "scrollwheel"])
        )

    def setEditMode(self, edit_mode):
        """Enable or disable edit mode."""
        # Propagar el modo de edición a todos los botones
        self.left_button.setEditMode(edit_mode)
        self.right_button.setEditMode(edit_mode)
        self.scroll_button.setEditMode(edit_mode)

    def setScrollTracking(self, enabled):
        """Set whether scroll wheel is being tracked."""
        self.scroll_button.setTracked(enabled)

    def isScrollTracked(self):
        """Check if scroll wheel is being tracked."""
        return self.scroll_button.tracked

    def sizeHint(self):
        """Suggested size for the widget."""
        return QSize(200, 60)
    
    def set_edit_mode(self, enabled: bool) -> None:
        """Enable or disable edit mode."""
        super().set_edit_mode(enabled)
        self.setEditMode(enabled)
    
    def set_collector_capabilities(self, capabilities: Dict[str, Any]) -> None:
        """Configure the visualizer based on collector capabilities."""
        super().set_collector_capabilities(capabilities)
        # Hide if the collector doesn't support mouse buttons
        self.setVisible(capabilities.get("supports_mouse_buttons", False))
