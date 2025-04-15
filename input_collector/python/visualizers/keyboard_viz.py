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
        [
            "Esc",
            "F1",
            "F2",
            "F3",
            "F4",
            "F5",
            "F6",
            "F7",
            "F8",
            "F9",
            "F10",
            "F11",
            "F12",
        ],
        ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "Backspace"],
        ["Tab", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]", "\\"],
        ["Caps", "A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'", "Enter"],
        ["Shift", "Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "Shift"],
        ["Ctrl", "Win", "Alt", "Space", "Alt", "Menu", "Ctrl"],
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

        # Almacenar información de posición de las teclas para interacción
        self.key_rects = {}

        # Set size policy and minimum size
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumSize(400, 200)  # Aumentado desde 180 a 200 para más altura

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
        if (
            input_data is not None
            and hasattr(input_data, "active_keys")
            and input_data.active_keys is not None
        ):
            # Clear previous active keys and use the ones from the event
            self.active_keys = set()

            # Process active keys
            for key in input_data.active_keys:
                norm_key = key.lower()

                # Normalize representation of special keys
                if norm_key == "key.space" or norm_key == " " or norm_key == "space":
                    norm_key = "key.space"
                elif "key.shift" in norm_key or norm_key in [
                    "key.shift",
                    "key.shift_l",
                    "key.shift_r",
                ]:
                    norm_key = "key.shift"

                # Add to active keys set
                self.active_keys.add(norm_key)

        # Call the base class update method to request a repaint
        super().update()

    def get_key_at_position(self, x, y) -> str:
        """
        Get the key at the specified position.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            The key name at the position, or None if no key is at that position
        """
        for key, rect in self.key_rects.items():
            if rect.contains(x, y):
                return key
        return None

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

        # Ajustar el tamaño para evitar que se corte
        width_padding = (
            width * 0.025
        )  # Reducido desde 0.03 para dar más espacio horizontal
        height_padding = (
            height * 0.05
        )  # Reducido desde 0.06 para dar más espacio vertical
        effective_width = width - (2 * width_padding)
        effective_height = height - (2 * height_padding)

        # Escalar la visualización del teclado - aumentar ancho general
        scale_factor = 0.95  # Aumentado desde 0.92 para hacer el teclado más grande
        effective_width *= scale_factor

        # Scale font and key sizes based on available space
        font_size = max(7, min(10, int(effective_width / 60)))  # Aumentado ligeramente
        font = QFont("Segoe UI", font_size)
        painter.setFont(font)

        # Determinar dimensiones de las teclas
        num_rows = len(self.DEFAULT_KEYBOARD_LAYOUT)
        max_keys_in_row = max(len(row) for row in self.DEFAULT_KEYBOARD_LAYOUT)

        # Calcular el ancho y alto base de las teclas
        base_key_width = effective_width / (max_keys_in_row + 2)
        # Reducir la altura de las teclas, pero no tanto como antes
        base_key_height = min(
            effective_height / (num_rows + 0.6), base_key_width * 0.85
        )  # Aumentado desde 0.8

        # Limpiar el diccionario de rectángulos de teclas
        self.key_rects = {}

        # Dibujar el teclado, centrado en el widget
        y_offset = height_padding

        for row_idx, row in enumerate(self.DEFAULT_KEYBOARD_LAYOUT):
            # Calcular el ancho total de esta fila
            total_row_width = sum(
                [
                    base_key_width
                    * (
                        4
                        if key == "Space"
                        else (
                            2.0
                            if key
                            in ["Backspace", "Enter"]  # Increased width for these keys
                            else 1.5 if key in ["Shift", "Tab"] else 1
                        )
                    )
                    for key in row
                ]
            )

            # Añadir espaciado entre teclas
            total_row_width += (
                base_key_width * 0.15 * (len(row) - 1)
            )  # Reduced spacing between keys

            # Centrar la fila
            x_offset = (width - total_row_width) / 2

            for key_label in row:
                # Determinar ancho de esta tecla
                key_width_actual = base_key_width
                if key_label == "Space":
                    key_width_actual = base_key_width * 4
                elif key_label in ["Backspace", "Enter"]:
                    key_width_actual = base_key_width * 2.0  # Increased from 1.8 to 2.0
                elif key_label in ["Shift", "Tab"]:
                    key_width_actual = base_key_width * 1.5

                # Definir rectángulo de la tecla
                key_rect = QRect(
                    int(x_offset),
                    int(y_offset),
                    int(key_width_actual),
                    int(base_key_height),
                )

                # Guardar el rectángulo para detección de clics
                self.key_rects[key_label] = key_rect

                # Determinar color de la tecla
                key_lower = key_label.lower()

                # Color predeterminado
                key_color = self.key_bg

                # Manejo especial para la barra espaciadora
                if key_lower == "space":
                    key_color = QColor("#464649")

                # Manejo especial para F9/tecla de grabación
                if key_lower == "f9":
                    key_color = self.record_key_bg

                # Verificar si la tecla está siendo tracked
                for tracked_key in self.tracked_keys:
                    if (
                        tracked_key.lower() == key_lower
                        or (tracked_key == "key.space" and key_lower == "space")
                        or (tracked_key == "key.shift" and key_lower == "shift")
                        or (tracked_key == "key.media_play_pause" and key_lower == "f9")
                    ):
                        key_color = self.tracked_key_bg
                        break

                # Verificar si la tecla está activa
                is_active = False
                for active_key in self.active_keys:
                    active_key_lower = active_key.lower()

                    # Manejar la barra espaciadora
                    if (
                        active_key_lower in ["key.space", "space", " "]
                        and key_lower == "space"
                    ):
                        key_color = self.active_key_bg
                        is_active = True
                        break
                    # Manejar la tecla shift
                    elif (
                        active_key_lower in ["key.shift", "key.shift_l", "key.shift_r"]
                        and key_lower == "shift"
                    ):
                        key_color = self.active_key_bg
                        is_active = True
                        break
                    # Manejar la tecla de media play/pause (F9)
                    elif (
                        active_key_lower == "key.media_play_pause" and key_lower == "f9"
                    ):
                        key_color = QColor(
                            "#FF5555"
                        )  # Rojo más brillante para estado activo
                        is_active = True
                        break
                    # Manejar teclas normales
                    elif active_key_lower == key_lower:
                        is_tracked = key_lower in self.tracked_keys
                        key_color = (
                            self.active_key_bg if is_tracked else self.secondary_key_bg
                        )
                        is_active = True
                        break

                # Dibujar la tecla
                pen = QPen(Qt.NoPen)
                if is_active:
                    # Usar efecto hundido para teclas activas
                    offset = 1
                    shadow_rect = key_rect.adjusted(offset, offset, 0, 0)
                    painter.fillRect(shadow_rect, QColor(0, 0, 0, 70))

                painter.setPen(pen)
                painter.setBrush(QBrush(key_color))
                painter.drawRect(key_rect)

                # Dibujar texto de la tecla
                painter.setPen(QPen(self.key_text))

                # Manejo especial para la tecla F9
                if key_lower == "f9":
                    # Dibujar texto F9 con indicación de REC
                    painter.drawText(key_rect, Qt.AlignCenter, "F9\n(REC)")
                else:
                    # Dibujar texto normal
                    painter.drawText(key_rect, Qt.AlignCenter, key_label)

                # Moverse a la siguiente posición
                x_offset += key_width_actual + (
                    base_key_width * 0.15
                )  # Reduced spacing from 0.2 to 0.15

            # Moverse a la siguiente fila con menos espaciado
            y_offset += base_key_height * 1.05  # Reduced from 1.1 to 1.05

    def sizeHint(self) -> QSize:
        """Suggested size for the widget"""
        return QSize(500, 280)  # Aumentado desde 480,260 para sugerir un tamaño mayor

    def minimumSizeHint(self) -> QSize:
        """Minimum suggested size for the widget"""
        return QSize(
            400, 200
        )  # Aumentado desde 400,180 para asegurar suficiente altura

    def force_update(self) -> None:
        """Force a redraw of the keyboard"""
        self.update()
