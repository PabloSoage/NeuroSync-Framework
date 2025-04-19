"""
Input collector application module.

This module provides the main application for collecting, visualizing, and
logging keyboard and mouse inputs in real-time with a graphical user interface using PyQt5.
"""

import sys
import json
import time
import os
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QTextEdit,
    QCheckBox,
    QComboBox,
    QFrame,
    QSplitter,
    QGroupBox,
    QListWidget,
    QSlider,
    QSpacerItem,
    QSizePolicy,
    QAction,
    QMessageBox,  # Added QMessageBox
    QFileDialog,  # Added for file selection
)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QPalette, QFont, QTextCursor
from typing import List, Dict, Optional, Any

from .collectors import KeyboardMouseCollector
from .interfaces import InputData, AbstractInputCollector
from .visualizers import KeyboardVisualizer, MouseVisualizer, MouseButtonsSelector

# Import PS4 controller collector with fallback
try:
    from .collectors.ps4_controller import PS4ControllerCollector, is_sdl2_available

    HAVE_PS4_SUPPORT = is_sdl2_available()
    if HAVE_PS4_SUPPORT:
        print("SDL2 detected successfully. PS4 controller support is available.")
    else:
        print(
            "SDL2 could not be properly initialized. PS4 controller support will be disabled."
        )
except ImportError as e:
    print(f"PS4 controller support disabled: {e}")
    print("To enable PS4 controller support, install required packages with:")
    print("pip install pysdl2 pysdl2-dll")
    HAVE_PS4_SUPPORT = False


class InputCollectorApp(QMainWindow):
    """
    Main application for input collection and visualization.

    This class provides a graphical user interface for collecting, visualizing,
    and logging keyboard and mouse inputs in real-time. It integrates the
    input collector and visualizers into a cohesive application.
    """

    # Signal for event handling between threads
    event_received = pyqtSignal(object)

    def __init__(self) -> None:
        """
        Initialize the application.

        Creates the application window, sets up the UI components, and initializes
        the input collector and visualizers.
        """
        super().__init__()

        # Define app theme colors
        self.dark_bg = "#2D2D30"
        self.dark_frame_bg = "#252526"
        self.text_color = "#E0E0E0"
        self.accent_color = "#007ACC"
        self.success_color = "#5FB878"
        self.warning_color = "#FFAA33"
        self.error_color = "#FF5555"

        # App state
        self.is_recording = False
        self.log_to_file = False
        self.log_file = None
        self.is_fullscreen = False
        # Add CSV logging state
        self.log_to_csv = False
        self.csv_file = None
        self.csv_filepath = ""

        # Añadir variable para el modo de edición de teclas
        self.edit_keys_mode = False

        # Setup UI
        self.setWindowTitle("Input Collector")
        self.setGeometry(100, 100, 800, 700)
        self.setMinimumSize(750, 650)

        # Set application style
        self._set_dark_theme()

        # Create UI components
        self._create_ui()

        # Collection mode state
        self.current_collector_type = "keyboard_mouse"
        self.collectors = {}

        # Initialize the keyboard/mouse collector
        self.collectors["keyboard_mouse"] = KeyboardMouseCollector()

        # Initialize PS4 controller if available
        if HAVE_PS4_SUPPORT:
            try:
                print("Attempting to initialize PS4 controller...")
                self.collectors["ps4_controller"] = PS4ControllerCollector()
                print("PS4 controller collector initialized successfully.")
            except Exception as e:
                print(f"Error initializing PS4 controller: {e}")
                import traceback

                traceback.print_exc()
                # Don't show PS4 option if initialization fails
                self.collector_selector.removeItem(
                    self.collector_selector.findText("PS4 Controller")
                )
        elif self.collector_selector.findText("PS4 Controller") >= 0:
            # Remove PS4 option if not available
            print(
                "Removing PS4 Controller option from selector as PySDL2 is not available"
            )
            self.collector_selector.removeItem(
                self.collector_selector.findText("PS4 Controller")
            )

        # Get the active collector
        self.collector = self.collectors[self.current_collector_type]

        # Connect collector callbacks
        self.collector.on_event(self._handle_input_event)

        # Connect event signal to slot
        self.event_received.connect(self._process_event)

        # Set tracked keys
        self.tracked_keys = [
            "w",
            "a",
            "s",
            "d",
            "q",
            "e",
            "f",
            "m",
            "c",
            "b",
            "1",
            "2",
            "3",
            "4",
            "Key.space",
            "Key.shift",
            "Key.media_play_pause",
            "Button.left",
            "Button.right",  # Añadir botones del ratón por defecto
        ]
        self.collector.set_supported_keys(self.tracked_keys)

        # Set the tracked keys in the keyboard visualizer for highlighting
        self.keyboard_viz.set_tracked_keys(self.tracked_keys)

        # Set screen dimensions for velocity-based joystick control
        screen_rect = QApplication.desktop().screenGeometry()
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()
        if hasattr(self.collector, "set_screen_dimensions"):
            self.collector.set_screen_dimensions(screen_width, screen_height)

        # Set joystick sensitivity if supported
        if hasattr(self.collector, "set_joystick_sensitivity"):
            self.collector.set_joystick_sensitivity(0.1)

        # Initialize mouse tracking mode to match UI defaults
        if hasattr(self.collector, "set_mouse_tracking_mode"):
            self._set_mouse_tracking_mode(self.tracking_mode_combo.currentText())

        # Start timer for periodic UI updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_active_keys_display)
        self.update_timer.start(100)

        # Setup shortcuts
        self._setup_shortcuts()

        # Connect scroll checkbox to mouse buttons selector
        self.capture_scroll_check.toggled.connect(self._on_capture_scroll_changed)

        # Initialize mouse buttons selector
        self.mouse_buttons_selector.setTrackedButtons(self.tracked_keys)
        self.mouse_buttons_selector.setScrollTracking(
            self.capture_scroll_check.isChecked()
        )

        # Connect collector selector
        self.collector_selector.currentTextChanged.connect(self._switch_collector)

        self.last_toggle_time = None
        self.f9_key_down = False

    def _set_dark_theme(self) -> None:
        """Set the application to use a dark theme."""
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
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(self.accent_color))
        palette.setColor(QPalette.Highlight, QColor(self.accent_color))
        palette.setColor(QPalette.HighlightedText, Qt.white)

        QApplication.setPalette(palette)

        # Set stylesheet for detailed control
        self.setStyleSheet(
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
            QComboBox:disabled {{
                background-color: #444444;
                color: #888888;
                border: 1px solid #333333;
            }}
            QCheckBox:disabled {{
                color: #888888;
            }}
            QCheckBox::indicator:disabled {{
                border: 1px solid #555555;
                background-color: #444444;
            }}
            QLineEdit, QTextEdit, QListWidget, QComboBox {{
                background-color: {self.dark_frame_bg};
                color: {self.text_color};
                border: 1px solid #444;
                padding: 2px;
                border-radius: 2px;
            }}
            QTextEdit {{ font-family: 'Consolas', monospace; }}
            QComboBox::drop-down {{ border: 0px; }}
            QComboBox::down-arrow {{
                image: url(dropdown.png);
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
            QLabel {{ color: {self.text_color}; }}
        """
        )

    def _create_ui(self) -> None:
        """Create the application UI components."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        self.main_layout = QVBoxLayout(
            central_widget
        )  # Store reference to main_layout as an attribute
        self.main_layout.setSpacing(8)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # Control panel
        control_panel = QHBoxLayout()

        # Recording controls - reorganize into a single horizontal layout
        recording_frame = QHBoxLayout()

        # 1. Record button
        self.record_button = QPushButton("Record")
        self.record_button.setStyleSheet(f"background-color: #AA3333; color: white;")
        self.record_button.clicked.connect(self._toggle_recording)
        recording_frame.addWidget(self.record_button)
        
        # 2. JSON logging checkbox - make accessible as attribute for integrated app
        self.log_checkbox = QCheckBox("Log JSON")
        self.log_checkbox.toggled.connect(self._toggle_logging)
        recording_frame.addWidget(self.log_checkbox)
        
        # 3. CSV logging checkbox - make accessible as attribute for integrated app
        self.csv_checkbox = QCheckBox("Log CSV")
        self.csv_checkbox.toggled.connect(self._toggle_csv_logging)
        recording_frame.addWidget(self.csv_checkbox)
        
        # 4. CSV path controls in a horizontal layout
        self.csv_path_label = QLabel("Path:")
        recording_frame.addWidget(self.csv_path_label)
        
        self.csv_path_field = QLineEdit()
        self.csv_path_field.setPlaceholderText("Select CSV file location...")
        self.csv_path_field.setReadOnly(True)
        recording_frame.addWidget(self.csv_path_field, 1)  # Give the path field horizontal stretch
        
        self.csv_path_button = QPushButton("Browse...")
        self.csv_path_button.clicked.connect(self._select_csv_path)
        recording_frame.addWidget(self.csv_path_button)
        
        # 5. Status label
        self.status_label = QLabel("Not Recording")
        recording_frame.addWidget(self.status_label)

        control_panel.addLayout(recording_frame)
        control_panel.addStretch(1)

        # Add collector selector dropdown before the Edit Keys button
        collector_layout = QHBoxLayout()
        collector_layout.addWidget(QLabel("Input:"))

        self.collector_selector = QComboBox()
        self.collector_selector.addItems(["Keyboard & Mouse", "PS4 Controller"])
        self.collector_selector.setMinimumWidth(120)
        collector_layout.addWidget(self.collector_selector)

        # Añadir botón de escaneo para controladores SDL
        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self._scan_controllers)
        self.scan_button.setFixedWidth(60)  # Hacer el botón más pequeño
        self.scan_button.setStyleSheet("background-color: #444466;")
        collector_layout.addWidget(self.scan_button)

        control_panel.addLayout(collector_layout)

        # Edit keys button - ensure disabled styling will be applied
        self.edit_keys_button = QPushButton("Edit Keys")
        self.edit_keys_button.clicked.connect(self._toggle_edit_mode)
        self.edit_keys_button.setCheckable(True)
        # Don't set custom style here, let it use the global style including disabled state
        control_panel.addWidget(self.edit_keys_button)

        control_panel.addStretch(1)

        # Mouse tracking mode controls
        mouse_mode_frame = QHBoxLayout()

        self.direction_only_check = QCheckBox("Dir Only")
        self.direction_only_check.setChecked(True)
        self.direction_only_check.toggled.connect(self._update_tracking_modes)
        mouse_mode_frame.addWidget(self.direction_only_check)

        mouse_mode_frame.addWidget(QLabel("Mode:"))

        self.tracking_mode_combo = QComboBox()
        self.tracking_mode_combo.addItems(["axis", "angle"])
        self.tracking_mode_combo.setMinimumWidth(80)
        self.tracking_mode_combo.currentTextChanged.connect(
            self._set_mouse_tracking_mode
        )
        mouse_mode_frame.addWidget(self.tracking_mode_combo)

        control_panel.addLayout(mouse_mode_frame)

        self.main_layout.addLayout(control_panel)

        # Visualization area - Ajustar el espacio relativo
        viz_layout = QHBoxLayout()

        # Left side: Keyboard visualization + Mouse buttons
        left_viz_layout = QVBoxLayout()

        # Keyboard visualization
        keyboard_group = QGroupBox("Keyboard Input")
        keyboard_layout = QVBoxLayout(keyboard_group)
        self.keyboard_viz = KeyboardVisualizer()
        # Conectar señales para la edición de teclas
        self.keyboard_viz.mousePressEvent = self._handle_keyboard_viz_click
        keyboard_layout.addWidget(self.keyboard_viz)

        # Añadir selector de botones del ratón debajo del teclado
        mouse_buttons_group = QGroupBox("Mouse Buttons")
        mouse_buttons_layout = QVBoxLayout(mouse_buttons_group)
        self.mouse_buttons_selector = MouseButtonsSelector()
        # Conectar la señal del selector de botones
        self.mouse_buttons_selector.button_toggled.connect(
            self._handle_mouse_button_toggled
        )
        mouse_buttons_layout.addWidget(self.mouse_buttons_selector)

        # Añadir ambos al layout izquierdo
        left_viz_layout.addWidget(keyboard_group, 3)  # Peso mayor para el teclado
        left_viz_layout.addWidget(mouse_buttons_group, 1)  # Peso menor para los botones

        # Mouse visualization (derecha)
        mouse_group = QGroupBox("Mouse Input")
        mouse_layout = QVBoxLayout(mouse_group)
        self.mouse_viz = MouseVisualizer()
        mouse_layout.addWidget(self.mouse_viz)

        # Añadir ambas secciones al layout de visualización
        viz_layout.addLayout(left_viz_layout, 55)  # Asignar 55% del espacio horizontal
        viz_layout.addWidget(mouse_group, 45)  # Asignar 45% del espacio horizontal

        # Dar más peso vertical a la visualización
        self.main_layout.addLayout(
            viz_layout, 4
        )  # Aumentado de 3 a 4 para dar más espacio vertical

        # Active keys display (ahora ya no está el selector de mouse buttons aquí)
        active_keys_group = QGroupBox("Active Keys")
        active_keys_layout = QVBoxLayout(active_keys_group)
        self.active_keys_label = QLabel("None")
        self.active_keys_label.setAlignment(Qt.AlignCenter)
        active_keys_layout.addWidget(self.active_keys_label)
        self.main_layout.addWidget(active_keys_group)

        # Eliminar la sección "Tracked Keys" que ya no es necesaria

        # Status area - reducir aún más para dar más espacio a los visualizadores
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(80)  # Reducido de 100 a 80
        status_layout.addWidget(self.status_text)
        self.main_layout.addWidget(status_group)

        # Mouse settings
        settings_group = QGroupBox("Mouse Settings")
        settings_layout = QVBoxLayout(settings_group)

        # Settings rows
        settings_row1 = QHBoxLayout()

        # Delta smoothing
        delta_layout = QHBoxLayout()
        delta_layout.addWidget(QLabel("Delta Smoothing:"))
        self.delta_smoothing_slider = QSlider(Qt.Horizontal)
        self.delta_smoothing_slider.setRange(0, 90)
        self.delta_smoothing_slider.setValue(50)  # 0.5
        delta_layout.addWidget(self.delta_smoothing_slider)
        settings_row1.addLayout(delta_layout)

        # Joystick sensitivity
        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(QLabel("Joystick Sensitivity:"))
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setRange(10, 200)
        self.sensitivity_slider.setValue(10)  # 0.1
        sensitivity_layout.addWidget(self.sensitivity_slider)
        settings_row1.addLayout(sensitivity_layout)

        settings_layout.addLayout(settings_row1)

        # Settings row 2
        settings_row2 = QHBoxLayout()

        # Angle grouping
        angle_layout = QHBoxLayout()
        angle_layout.addWidget(QLabel("Angle Grouping:"))
        self.angle_grouping_slider = QSlider(Qt.Horizontal)
        self.angle_grouping_slider.setRange(1, 60)
        self.angle_grouping_slider.setValue(10)
        self.angle_grouping_slider.valueChanged.connect(
            self._update_angle_grouping_display
        )
        angle_layout.addWidget(self.angle_grouping_slider)
        self.angle_grouping_label = QLabel("10° (36 values)")
        self.angle_grouping_label.setMinimumWidth(100)
        angle_layout.addWidget(self.angle_grouping_label)
        settings_row2.addLayout(angle_layout)

        # Scroll capture checkbox
        scroll_layout = QHBoxLayout()
        self.capture_scroll_check = QCheckBox("Capture Scroll Data")
        scroll_layout.addWidget(self.capture_scroll_check)
        scroll_layout.addStretch(1)

        # Apply button
        apply_button = QPushButton("Apply Settings")
        apply_button.clicked.connect(self._apply_mouse_settings)
        scroll_layout.addWidget(apply_button)

        settings_row2.addLayout(scroll_layout)
        settings_layout.addLayout(settings_row2)

        self.main_layout.addWidget(settings_group)

    def _scan_controllers(self) -> None:
        """Scan for SDL controllers and show a selection dialog."""
        if "ps4_controller" not in self.collectors:
            QMessageBox.warning(
                self,
                "SDL Not Available",
                "SDL2 is not available. Make sure pysdl2 and pysdl2-dll are installed.",
            )
            return

        # Get PS4 controller collector
        ps4_collector = self.collectors["ps4_controller"]

        # Show scanning message
        self._log_status("Scanning for controllers...", self.warning_color)
        QApplication.processEvents()

        try:
            # Scan for controllers
            controllers = ps4_collector.scan_controllers()

            if not controllers:
                QMessageBox.information(
                    self,
                    "No Controllers Found",
                    "No SDL game controllers were detected.\n\n"
                    "Make sure your controller is connected and properly recognized by your system.",
                )
                self._log_status("No controllers found", self.error_color)

                # Fall back to keyboard/mouse mode
                if self.collector_selector.currentText() == "PS4 Controller":
                    self._log_status(
                        "Falling back to Keyboard & Mouse mode", self.warning_color
                    )
                    self._force_keyboard_mouse_mode()
                return

            # If we have only one controller, connect to it directly
            if len(controllers) == 1:
                controller = controllers[0]
                success = ps4_collector.connect_to_controller(controller["index"])
                if success:
                    self._log_status(
                        f"Connected to: {controller['name']}", self.success_color
                    )
                    # Switch to PS4 controller mode if not already there
                    if self.collector_selector.currentText() != "PS4 Controller":
                        self.collector_selector.setCurrentText("PS4 Controller")
                else:
                    self._log_status(
                        f"Failed to connect to: {controller['name']}", self.error_color
                    )
                    # Fall back to keyboard/mouse mode if connection failed
                    if self.collector_selector.currentText() == "PS4 Controller":
                        self._log_status(
                            "Falling back to Keyboard & Mouse mode", self.warning_color
                        )
                        self._force_keyboard_mouse_mode()
                return

            # If we have multiple controllers, show a selection dialog
            from PyQt5.QtWidgets import (
                QDialog,
                QVBoxLayout,
                QListWidget,
                QDialogButtonBox,
                QListWidgetItem,
            )

            dialog = QDialog(self)
            dialog.setWindowTitle("Select Controller")
            layout = QVBoxLayout()

            # Instructions label
            layout.addWidget(QLabel("Select a controller to use:"))

            # List of controllers
            controller_list = QListWidget()
            for controller in controllers:
                item_text = (
                    f"{controller['name']} {'(PS4)' if controller['is_ps4'] else ''}"
                )
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, controller["index"])
                controller_list.addItem(item)

            layout.addWidget(controller_list)

            # Buttons
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            dialog.setLayout(layout)

            # Show dialog and process result
            if dialog.exec_() == QDialog.Accepted and controller_list.currentItem():
                # Get selected controller index
                controller_index = controller_list.currentItem().data(Qt.UserRole)

                # Connect to selected controller
                success = ps4_collector.connect_to_controller(controller_index)
                if success:
                    controller_name = controller_list.currentItem().text()
                    self._log_status(
                        f"Connected to: {controller_name}", self.success_color
                    )

                    # Switch to PS4 controller mode if not already there
                    if self.collector_selector.currentText() != "PS4 Controller":
                        self.collector_selector.setCurrentText("PS4 Controller")
                else:
                    self._log_status(
                        "Failed to connect to controller", self.error_color
                    )
                    # Fall back to keyboard/mouse mode if connection failed
                    if self.collector_selector.currentText() == "PS4 Controller":
                        self._log_status(
                            "Falling back to Keyboard & Mouse mode", self.warning_color
                        )
                        self._force_keyboard_mouse_mode()

        except Exception as e:
            import traceback

            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Error Scanning Controllers",
                f"An error occurred while scanning for controllers: {str(e)}",
            )
            self._log_status(f"Controller scan error: {str(e)}", self.error_color)

            # Fall back to keyboard/mouse mode on error
            if self.collector_selector.currentText() == "PS4 Controller":
                self._log_status(
                    "Falling back to Keyboard & Mouse mode", self.warning_color
                )
                self._force_keyboard_mouse_mode()

    def _force_keyboard_mouse_mode(self) -> None:
        """Force switch to keyboard/mouse mode safely."""
        # Set current collector type directly
        self.current_collector_type = "keyboard_mouse"
        self.collector = self.collectors["keyboard_mouse"]

        # Update UI state
        self.collector_selector.blockSignals(True)  # Prevent recursion
        self.collector_selector.setCurrentText("Keyboard & Mouse")
        self.collector_selector.blockSignals(False)

        # Connect handler to collector
        for collector in self.collectors.values():
            try:
                if hasattr(collector, "remove_event_handler"):
                    collector.remove_event_handler(self._handle_input_event)
            except:
                pass

        # Add handler to keyboard/mouse collector
        self.collector.on_event(self._handle_input_event)

        # Set tracked keys
        self.collector.set_supported_keys(self.tracked_keys)

        # Update UI based on collector capabilities
        self._update_ui_for_collector()

        # Log the change
        self._log_status("Forced switch to Keyboard & Mouse mode", self.warning_color)

        # Process pending events to ensure UI updates
        QApplication.processEvents()

    def _switch_collector(self, collector_name: str) -> None:
        """
        Switch between input collectors.

        Args:
            collector_name: Name of the collector to switch to
        """
        # Stop current collector
        if self.is_recording:
            self._toggle_recording()

        # Map display name to internal collector type
        collector_map = {
            "Keyboard & Mouse": "keyboard_mouse",
            "PS4 Controller": "ps4_controller",
        }

        new_collector_type = collector_map.get(collector_name)
        if not new_collector_type or new_collector_type not in self.collectors:
            # Invalid collector or not available
            self._log_status(
                f"Collector '{collector_name}' not available", self.error_color
            )

            # Revert to previous selection - use our safe method
            self._force_keyboard_mouse_mode()
            return

        # Check if PS4 controller is available if trying to switch to it
        if new_collector_type == "ps4_controller":
            if not HAVE_PS4_SUPPORT:
                QMessageBox.warning(
                    self,
                    "PS4 Controller Not Available",
                    "PySDL2 is not installed or could not be initialized.\n\n"
                    "Install with: pip install pysdl2 pysdl2-dll",
                )

                # Revert to keyboard/mouse safely
                self._force_keyboard_mouse_mode()
                return

            # If we're switching to PS4 controller and we don't have an active controller connection,
            # ask the user if they want to scan
            ps4_collector = self.collectors["ps4_controller"]
            if not ps4_collector.controller:
                response = QMessageBox.question(
                    self,
                    "No Controller Connected",
                    "No controller is currently connected. Would you like to scan for controllers now?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )

                if response == QMessageBox.Yes:
                    self._scan_controllers()
                    # If we still don't have a controller, revert to keyboard/mouse
                    if not ps4_collector.controller:
                        # No need for more messages - _scan_controllers already handled it
                        return
                else:
                    # User declined to scan, revert to keyboard/mouse
                    self._log_status(
                        "Controller scan declined, staying with Keyboard & Mouse",
                        self.warning_color,
                    )
                    self._force_keyboard_mouse_mode()
                    return

        # Switch collector
        self.current_collector_type = new_collector_type
        self.collector = self.collectors[new_collector_type]

        # Connect event handler to new collector
        for collector in self.collectors.values():
            # Remove old handler from all collectors to avoid duplicates
            try:
                # This is not a standard method in the interface, but attempt it
                # for collectors that might support it
                if hasattr(collector, "remove_event_handler"):
                    collector.remove_event_handler(self._handle_input_event)
            except:
                pass

        # Add handler to current collector
        self.collector.on_event(self._handle_input_event)

        # Set tracked keys for new collector
        self.collector.set_supported_keys(self.tracked_keys)

        # Update UI based on collector capabilities
        self._update_ui_for_collector()

        # Log the change
        self._log_status(f"Switched to {collector_name} collector", self.accent_color)

    def _update_ui_for_collector(self) -> None:
        """Update UI elements based on current collector capabilities."""
        is_keyboard_mouse = self.current_collector_type == "keyboard_mouse"

        # Show/hide scan button based on selected collector
        self.scan_button.setVisible(not is_keyboard_mouse)

        # Show/hide mouse-specific UI elements
        self.tracking_mode_combo.setVisible(is_keyboard_mouse)
        self.direction_only_check.setVisible(is_keyboard_mouse)

        # Update mouse settings group visibility
        for i in range(self.main_layout.count()):
            item = self.main_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QGroupBox):
                if "Mouse Settings" in item.widget().title():
                    item.widget().setVisible(is_keyboard_mouse)

        # Update keyboard visualization
        if is_keyboard_mouse:
            self.keyboard_viz.set_tracked_keys(self.tracked_keys)
            self.keyboard_viz.setVisible(True)
            self.mouse_buttons_selector.setVisible(True)
        else:
            # For PS4 controller, maybe hide keyboard visualizer or adapt it
            # to show controller buttons instead
            self.keyboard_viz.setVisible(False)
            self.mouse_buttons_selector.setVisible(False)

        # Reset active keys display
        self.active_keys_label.setText("None")

    def _toggle_edit_mode(self) -> None:
        """Toggle key editing mode."""
        # Don't allow edit mode when recording
        if self.is_recording:
            self._log_status("Cannot edit keys while recording", self.warning_color)
            self.edit_keys_button.setChecked(False)
            return
            
        self.edit_keys_mode = not self.edit_keys_mode

        if self.edit_keys_mode:
            self.edit_keys_button.setText("Finish Editing")
            self.edit_keys_button.setStyleSheet(
                "background-color: #5FB878; color: white;"
            )
            self._log_status(
                "Click on keys or mouse buttons to add/remove them from tracking",
                self.success_color,
            )
            # Cambiar el cursor para indicar modo de edición
            self.keyboard_viz.setCursor(Qt.PointingHandCursor)
            self.mouse_buttons_selector.setEditMode(True)
        else:
            self.edit_keys_button.setText("Edit Keys")
            # When inactive, use the default style (which will respect disabled state)
            self.edit_keys_button.setStyleSheet("")
            self._log_status("Key editing finished", self.accent_color)
            # Restaurar cursor normal
            self.keyboard_viz.setCursor(Qt.ArrowCursor)
            self.mouse_buttons_selector.setEditMode(False)

    def _handle_keyboard_viz_click(self, event) -> None:
        """Handle clicks on the keyboard visualizer."""
        # Si no estamos en modo edición, usar el comportamiento predeterminado
        if not self.edit_keys_mode:
            QWidget.mousePressEvent(self.keyboard_viz, event)
            return

        # Obtener la tecla en la posición del clic
        key = self.keyboard_viz.get_key_at_position(event.x(), event.y())

        if key:
            key_lower = key.lower()

            # Manejar casos especiales
            if key_lower == "space":
                key = "Key.space"
            elif key_lower == "shift":
                key = "Key.shift"
            elif key_lower == "f9":
                key = "Key.media_play_pause"

            # Verificar si la tecla está en la lista de tracked_keys (ignorar mayúsculas/minúsculas)
            key_in_tracked = any(
                tracked.lower() == key.lower() for tracked in self.tracked_keys
            )

            # Alternar la tecla en la lista de tracked_keys
            if key_in_tracked:
                # No permitir eliminar F9/media_play_pause
                if key.lower() == "key.media_play_pause".lower():
                    self._log_status(
                        "Cannot remove F9/media_play_pause key", self.warning_color
                    )
                    return
                # Eliminar la tecla (necesitamos encontrar la versión exacta en la lista)
                for tracked in self.tracked_keys.copy():
                    if tracked.lower() == key.lower():
                        self.tracked_keys.remove(tracked)
                        break
                self._log_status(f"Removed key: {key}")
            else:
                # Añadir la tecla
                self.tracked_keys.append(key)
                self._log_status(f"Added key: {key}")

            # Actualizar la lista de teclas y la visualización
            self.collector.set_supported_keys(self.tracked_keys)
            self.keyboard_viz.set_tracked_keys(self.tracked_keys)

    def _handle_mouse_button_toggled(self, button_id: str, is_tracked: bool) -> None:
        """Handle toggling of mouse buttons in the selector."""
        if not self.edit_keys_mode:
            # Solo responder en modo de edición
            return

        # Manejar el caso especial del scroll
        if button_id == "Button.scroll":
            self.capture_scroll_check.setChecked(is_tracked)
            self._log_status(
                f"Scroll tracking {'enabled' if is_tracked else 'disabled'}",
                self.success_color if is_tracked else self.warning_color,
            )
            return

        # Para los demás botones, actualizar la lista de teclas trackeadas
        if is_tracked:
            # Añadir el botón si no está ya en la lista
            if button_id not in self.tracked_keys:
                self.tracked_keys.append(button_id)
                self._log_status(f"Added tracking for {button_id}", self.success_color)
        else:
            # Eliminar el botón si está en la lista
            if button_id in self.tracked_keys:
                self.tracked_keys.remove(button_id)
                self._log_status(
                    f"Removed tracking for {button_id}", self.warning_color
                )

        # Actualizar el colector y la visualización
        self.collector.set_supported_keys(self.tracked_keys)
        self.keyboard_viz.set_tracked_keys(self.tracked_keys)
        self.mouse_buttons_selector.setTrackedButtons(self.tracked_keys)

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts for the application."""
        # F9 key for toggling recording
        self.f9_shortcut = QAction("Toggle Recording", self)
        self.f9_shortcut.setShortcut("F9")
        self.f9_shortcut.triggered.connect(self._toggle_recording)
        self.addAction(self.f9_shortcut)

        # F11 for fullscreen
        self.f11_shortcut = QAction("Fullscreen", self)
        self.f11_shortcut.setShortcut("F11")
        self.f11_shortcut.triggered.connect(self._toggle_fullscreen)
        self.addAction(self.f11_shortcut)

        # Escape to exit fullscreen
        self.esc_shortcut = QAction("Exit Fullscreen", self)
        self.esc_shortcut.setShortcut("Esc")
        self.esc_shortcut.triggered.connect(self._exit_fullscreen)
        self.addAction(self.esc_shortcut)

    def _toggle_recording(self) -> None:
        """Toggle recording state."""
        current_time = time.time()
        if (
            self.last_toggle_time and (current_time - self.last_toggle_time) < 0.2
        ):  # 500ms between toggles
            return

        self.last_toggle_time = current_time
        if self.is_recording:
            # Stop recording
            print("Stopping recording...")
            self.collector.stop_capture()
            self.is_recording = False
            self.record_button.setText("Record")
            self.record_button.setStyleSheet("background-color: #AA3333; color: white;")
            self.status_label.setText("Not Recording")
            self._log_status("Recording stopped", self.warning_color)
            
            # Close JSON log file if open
            if self.log_file:
                self.log_file.write(
                    f'{{\n"event": "recording_stopped",\n"timestamp": {time.time()}\n}}\n'
                )
                self.log_file.flush()
            
            # Close CSV file if open
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self._log_status("CSV logging stopped", self.warning_color)
            
            # Re-enable edit keys button and tracking mode controls
            self.edit_keys_button.setEnabled(True)
            self.tracking_mode_combo.setEnabled(True)
            self.direction_only_check.setEnabled(True)
            
            # Reset Edit Keys button style based on its current state
            if self.edit_keys_mode:
                self.edit_keys_button.setStyleSheet("background-color: #5FB878; color: white;")
            else:
                self.edit_keys_button.setStyleSheet("")
            
        else:
            # Start recording
            print("Starting recording...")
            
            # Disable edit keys button and tracking mode controls
            self.edit_keys_button.setEnabled(False)
            self.tracking_mode_combo.setEnabled(False)
            self.direction_only_check.setEnabled(False)
            
            # Initialize CSV file if needed
            if self.log_to_csv:
                if not self._initialize_csv_file():
                    # Failed to initialize CSV file
                    self._log_status("Failed to create CSV log file", self.error_color)
                    return
            
            self.collector.start_capture()
            self.is_recording = True
            self.record_button.setText("Stop")
            self.record_button.setStyleSheet("background-color: #CC3333; color: white;")
            self.status_label.setText("RECORDING")
            self._log_status("Recording started", self.success_color)
            
            # Write to JSON log if enabled
            if self.log_file:
                self.log_file.write(
                    f'{{\n"event": "recording_started",\n"timestamp": {time.time()}\n}}\n'
                )
                self.log_file.flush()

        # Force update the UI
        QApplication.processEvents()

    def _initialize_csv_file(self) -> bool:
        """Initialize the CSV file with headers based on tracked keys and mouse mode."""
        try:
            # If no CSV path is set, ask the user to select one
            if not self.csv_filepath:
                csv_path = self._select_csv_path()
                if not csv_path:
                    self.csv_checkbox.setChecked(False)
                    self._log_status("CSV logging disabled: No file selected", self.warning_color)
                    return False
                self.csv_filepath = csv_path
            
            # Add timestamp to filename if not provided
            if not self.csv_filepath.lower().endswith('.csv'):
                self.csv_filepath += '.csv'
                
            # Always create a fresh CSV file with timestamp
            base_path, extension = os.path.splitext(self.csv_filepath)
            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(time.time()))
            self.csv_filepath = f"{base_path}_{timestamp}{extension}"
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.csv_filepath)), exist_ok=True)
            
            # Open the file for writing
            self.csv_file = open(self.csv_filepath, 'w', newline='')
            
            # Create CSV writer and write headers
            import csv
            self.csv_writer = csv.writer(self.csv_file)
            
            # Create headers based on tracked keys and mouse mode
            headers = ['timestamp']
            
            # Add headers for each tracked key
            for key in sorted(self.tracked_keys):
                # Skip F9/media_play_pause key as requested
                if key == "Key.media_play_pause":
                    continue
                
                # Skip mouse buttons - they will be handled separately
                if key in ["Button.left", "Button.right", "Button.scroll"]:
                    continue
                
                # Format the key name - remove "Key." prefix for special keys
                csv_key_name = key
                if key.startswith("Key."):
                    csv_key_name = key[4:]  # Remove "Key." prefix
                
                # Use key name as header
                headers.append(f"key_{csv_key_name}")
            
            # Add mouse button headers
            if "Button.left" in self.tracked_keys:
                headers.append('mouse_left')
            if "Button.right" in self.tracked_keys:
                headers.append('mouse_right')
            if self.capture_scroll_check.isChecked():
                headers.append('mouse_scroll')
            
            # Add mouse mode specific headers
            tracking_mode = self.tracking_mode_combo.currentText()
            direction_only = self.direction_only_check.isChecked()
            
            if tracking_mode == "joystick":
                headers.extend(['mouse_rel_x', 'mouse_rel_y', 'mouse_speed'])
            elif tracking_mode == "delta":
                headers.extend(['mouse_delta_x', 'mouse_delta_y'])
            elif tracking_mode == "angle":
                if direction_only:
                    headers.append('mouse_discrete_angle')
                else:
                    headers.extend(['mouse_angle', 'mouse_magnitude'])
            elif tracking_mode == "axis":
                headers.extend(['mouse_north', 'mouse_south', 'mouse_east', 'mouse_west'])
            
            # Write headers to CSV
            self.csv_writer.writerow(headers)
            self.csv_file.flush()
            
            # Store the headers for later use when writing data
            self.csv_headers = headers
            
            self._log_status(f"CSV logging to: {self.csv_filepath}", self.success_color)
            return True
            
        except Exception as e:
            self._log_status(f"Error initializing CSV file: {e}", self.error_color)
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
            return False

    def _select_csv_path(self) -> str:
        """Open file dialog to select CSV save location."""
        options = QFileDialog.Options()
        csv_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save CSV File", 
            "", 
            "CSV Files (*.csv);;All Files (*)", 
            options=options
        )
        
        if csv_path:
            self.csv_filepath = csv_path
            # Update the path field in the UI
            self.csv_path_field.setText(csv_path)
            self._log_status(f"CSV file path set: {csv_path}")
            return csv_path
        return ""

    def _toggle_logging(self, checked: bool) -> None:
        """Toggle logging to JSON file."""
        self.log_to_file = checked
        if self.log_to_file:
            # Open log file with timestamp
            current_time = time.time()
            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(current_time))
            filename = f"input_log_{timestamp}.json"
            try:
                self.log_file = open(filename, "w")
                self._log_status(f"Logging to {filename}")
            except Exception as e:
                self._log_status(f"Error opening log file: {e}", self.error_color)
                self.log_checkbox.setChecked(False)
        else:
            # Close log file
            if self.log_file:
                self.log_file.close()
                self.log_file = None
                self._log_status("Logging to file stopped")
    
    def _toggle_csv_logging(self, checked: bool) -> None:
        """Toggle logging to CSV file."""
        self.log_to_csv = checked
        if self.log_to_csv:
            # We'll initialize the CSV file when recording starts
            self._log_status("CSV logging enabled - will create file on recording start")
            
            # If there's no path set, ask the user to select one
            if not self.csv_filepath:
                self._select_csv_path()
        else:
            # Close CSV file if open
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
            self._log_status("CSV logging disabled")

    def _update_tracking_modes(self) -> None:
        """Update available tracking modes based on Direction Only checkbox."""
        direction_only = self.direction_only_check.isChecked()

        # Remember current mode
        current_mode = self.tracking_mode_combo.currentText()

        # Clear combo box
        self.tracking_mode_combo.clear()

        # Add appropriate modes
        if direction_only:
            # Direction-only modes
            self.tracking_mode_combo.addItems(["axis", "angle"])
            # Set appropriate mode
            if current_mode in ["axis", "angle"]:
                self.tracking_mode_combo.setCurrentText(current_mode)
            else:
                self.tracking_mode_combo.setCurrentText("axis")
        else:
            # Standard modes
            self.tracking_mode_combo.addItems(["joystick", "delta", "angle"])
            # Set appropriate mode
            if current_mode in ["joystick", "delta", "angle"]:
                self.tracking_mode_combo.setCurrentText(current_mode)
            else:
                self.tracking_mode_combo.setCurrentText("joystick")

        # Apply the mode
        self._set_mouse_tracking_mode(self.tracking_mode_combo.currentText())

    def _set_mouse_tracking_mode(self, mode: str) -> None:
        """Change the mouse tracking mode."""
        # Don't allow changing mode when recording
        if self.is_recording:
            self._log_status("Cannot change tracking mode while recording", self.warning_color)
            return
            
        direction_only = self.direction_only_check.isChecked()
        angle_grouping = self.angle_grouping_slider.value()

        self.collector.set_mouse_tracking_mode(mode, direction_only, angle_grouping)
        self._log_status(f"Mouse tracking mode set to: {mode}", self.accent_color)

        # Update display properties based on mode
        if mode == "axis":
            self._log_status(
                "Axis mode shows membership values for N, S, E, W directions", "#AAAAAA"
            )
        elif mode == "angle" and direction_only:
            self._log_status(
                f"Angle mode using {angle_grouping}° grouping ({360 // angle_grouping} values)",
                "#AAAAAA",
            )

    def _update_angle_grouping_display(self) -> None:
        """Update the display showing current angle grouping and resulting number of values."""
        grouping = self.angle_grouping_slider.value()
        num_values = 360 // grouping if grouping > 0 else 360
        self.angle_grouping_label.setText(f"{grouping}° ({num_values} values)")

    def _apply_mouse_settings(self) -> None:
        """Apply mouse settings."""
        # Apply delta smoothing
        smoothing = self.delta_smoothing_slider.value() / 100.0
        self.collector.set_delta_smoothing(smoothing)
        self._log_status(f"Delta smoothing set to: {smoothing:.2f}")

        # Apply joystick sensitivity
        sensitivity = self.sensitivity_slider.value() / 100.0
        self.collector.set_joystick_sensitivity(sensitivity)
        self._log_status(f"Joystick sensitivity set to: {sensitivity:.2f}")

        # Apply angle grouping
        angle_grouping = self.angle_grouping_slider.value()
        self.collector.set_angle_grouping(angle_grouping)
        self._log_status(
            f"Angle grouping set to: {angle_grouping}° ({360 // angle_grouping} values)"
        )

        # Log scroll capture status
        self._log_status(
            f"Scroll data capture: {'Enabled' if self.capture_scroll_check.isChecked() else 'Disabled'}"
        )

        # Re-apply current tracking mode to ensure all settings are updated
        self._set_mouse_tracking_mode(self.tracking_mode_combo.currentText())

    def _handle_input_event(self, event: InputData) -> None:
        """Handle events from the input collector."""
        # Use signal to safely handle events from collector thread
        self.event_received.emit(event)

    @pyqtSlot(object)
    def _process_event(self, event: InputData) -> None:
        """Process input events in the main thread."""
        # Handle PS4 controller events differently
        if self.current_collector_type == "ps4_controller":
            # Process PS4 controller events
            if event.event_type in ["button_press", "axis_motion"]:
                # Update visualizers - adapt for PS4 controller visualization
                # For now, just show in active keys display
                self._update_active_keys_display()
                # Handle logging for PS4 controller events
                if self.is_recording and self.log_file and self.log_to_file:
                    self._log_ps4_event_to_file(event)
                # Log to CSV if enabled
                if self.is_recording and self.csv_file and self.log_to_csv:
                    self._log_ps4_event_to_csv(event)
                # Display event in status area
                if self.is_recording:
                    event_text = self._format_ps4_event_text(event)
                    self._log_status(event_text)
            return

        # Existing keyboard/mouse event processing
        # Check for special toggle_recording event type first (for F9 key)
        if event.event_type == "toggle_recording":
            if not self.f9_key_down:
                self._toggle_recording()
                self.f9_key_down = True

            # Highlight the F9 key in the keyboard visualizer
            temp_press_event = InputData(
                timestamp=event.timestamp,
                event_type="key_press",
                key="Key.media_play_pause",
                active_keys=event.active_keys or [],
            )
            self.keyboard_viz.update(temp_press_event)
            return

        # FILTER: Ignore mouse button release events for logging (when button_pressed is None)
        if event.event_type == "mouse_click" and event.button_pressed is None:
            # Only update visualizers but don't log anything
            self.mouse_viz.update(event)
            self._update_active_keys_display()

            # Update mouse buttons selector to remove any highlighted buttons
            self.mouse_buttons_selector.setActiveButtons([])
            return

        # Don't log events if we're not recording
        if not self.is_recording:
            # Still update visualizers, but don't log anything
            if event.event_type in ["key_press", "key_release"]:
                self.keyboard_viz.update(event)
            elif event.event_type in ["mouse_move", "mouse_click", "mouse_scroll"]:
                self.mouse_viz.update(event)

            # Update active keys display
            self._update_active_keys_display()
            return

        # Don't process key_release events for logging
        if event.event_type == "key_release":
            if event.key == "Key.media_play_pause":
                self.f9_key_down = False
            # Only update the visualizer
            self.keyboard_viz.update(event)
            self._update_active_keys_display()
            return

        # FIX: Problema con media_play_pause - evitar que eventos de key_press con media_play_pause
        # activen un nuevo toggle de grabación (porque ya fue manejado por toggle_recording)
        # Solo responder a media_play_pause si viene directo del keyboard_listener, no de eventos internos
        if event.event_type == "key_press" and event.key == "Key.media_play_pause":
            # Ya no llamamos a toggle_recording aquí - este evento es solo para actualizar la visualización
            self.keyboard_viz.update(event)
            return

        # Verificar si los botones del ratón están siendo trackeados antes de procesarlos
        if event.event_type == "mouse_click" and event.button_pressed:
            # Solo procesar botones que estén en la lista de trackeados
            if not any(
                btn.lower() == event.button_pressed.lower() for btn in self.tracked_keys
            ):
                # Si el botón no está en la lista de trackeados, no lo procesamos
                return

        # FIX: Limpiar el button_pressed si no está en la lista de botones trackeados
        # Esto evita que los botones no trackeados aparezcan en los logs durante el movimiento del ratón
        if hasattr(event, "button_pressed") and event.button_pressed:
            if not any(
                btn.lower() == event.button_pressed.lower() for btn in self.tracked_keys
            ):
                event.button_pressed = (
                    None  # Eliminar la referencia al botón no trackeado
                )

        # Similar para scroll - solo procesar si está habilitado
        if (
            event.event_type == "mouse_scroll"
            and not self.capture_scroll_check.isChecked()
        ):
            # No procesar eventos de scroll si no está habilitado
            return

        # Update visualizers immediately
        if event.event_type in ["key_press", "key_release"]:
            self.keyboard_viz.update(event)
        elif event.event_type in ["mouse_move", "mouse_click", "mouse_scroll"]:
            self.mouse_viz.update(event)

        # Update active keys display
        self._update_active_keys_display()

        # Determine if we should log the event
        should_log = (
            (event.event_type == "key_press")
            or (event.event_type == "mouse_move" and event.is_moving)
            or (
                event.event_type == "mouse_click" and event.button_pressed is not None
            )  # Only log press, not release
            or (
                event.event_type == "mouse_scroll" and event.direction is not None
            )  # Only log actual scroll, not reset
            or (event.button_pressed is not None)
        )

        if self.is_recording and should_log:
            event_text = self._format_event_text(event)
            self._log_status(event_text)

            # Log to JSON file if enabled
            if self.log_file and self.log_to_file:
                self._log_event_to_file(event)
            
            # Log to CSV file if enabled
            if self.csv_file and self.log_to_csv:
                self._log_event_to_csv(event)

        # Actualizar el selector de botones del ratón si hay botones presionados
        if hasattr(event, "button_pressed") and event.button_pressed:
            # Solo destacar botones que estén en la lista de trackeados
            if any(
                btn.lower() == event.button_pressed.lower() for btn in self.tracked_keys
            ):
                active_buttons = [event.button_pressed]
                self.mouse_buttons_selector.setActiveButtons(active_buttons)
        else:
            self.mouse_buttons_selector.setActiveButtons([])

    def _format_event_text(self, event: InputData) -> str:
        """Format event text for UI display based on tracking mode."""
        # Format keyboard info
        keyboard_part = (
            f"Keys: [{', '.join(event.active_keys)}]"
            if event.active_keys
            else "Keys: []"
        )

        # Format mouse info based on tracking mode
        mouse_parts = []
        tracking_mode = getattr(event, "mouse_tracking_mode", "joystick")

        # Click info
        if event.event_type == "mouse_click" and event.button_pressed:
            mouse_parts.append(f"Click:{event.button_pressed}")
        elif hasattr(event, "button_pressed") and event.button_pressed:
            mouse_parts.append(f"Click:{event.button_pressed}")

        # Scroll info
        if event.event_type == "mouse_scroll" and event.direction:
            mouse_parts.append(f"Scroll:{event.direction}")

        # Movement info - mode specific
        if event.is_moving:
            if tracking_mode == "delta":
                if hasattr(event, "mouse_delta_x") and hasattr(event, "mouse_delta_y"):
                    mouse_parts.append(
                        f"Δx:{event.mouse_delta_x:.1f} Δy:{event.mouse_delta_y:.1f}"
                    )
                if hasattr(event, "mouse_delta_magnitude"):
                    mouse_parts.append(f"Mag:{event.mouse_delta_magnitude:.1f}")
                if event.direction:
                    mouse_parts.append(f"Dir:{event.direction}")
            elif tracking_mode == "angle":
                if hasattr(event, "direction_only") and event.direction_only:
                    if hasattr(event, "discrete_angle"):
                        mouse_parts.append(f"Angle:{event.discrete_angle}°")
                else:
                    if hasattr(event, "mouse_delta_angle"):
                        mouse_parts.append(f"Angle:{event.mouse_delta_angle:.1f}°")
                    if hasattr(event, "mouse_delta_magnitude"):
                        mouse_parts.append(f"Mag:{event.mouse_delta_magnitude:.1f}")
                if event.direction:
                    mouse_parts.append(f"Dir:{event.direction}")
            elif tracking_mode == "axis":
                if (
                    hasattr(event, "north")
                    and hasattr(event, "south")
                    and hasattr(event, "east")
                    and hasattr(event, "west")
                ):
                    mouse_parts.append(
                        f"N:{event.north:.1f} S:{event.south:.1f} E:{event.east:.1f} W:{event.west:.1f}"
                    )
            else:  # joystick mode
                if event.direction:
                    mouse_parts.append(f"Dir:{event.direction}")
                if event.speed is not None:
                    mouse_parts.append(f"Speed:{event.speed:.1f}")

        # Combine all mouse info
        mouse_part = (
            f"Mouse[{tracking_mode}]: {' | '.join(mouse_parts)}"
            if mouse_parts
            else f"Mouse[{tracking_mode}]: Idle"
        )

        return f"{keyboard_part} | {mouse_part}"

    def _log_event_to_file(self, event: InputData) -> None:
        """Log event to file."""
        try:
            # Determine current tracking mode
            tracking_mode = getattr(event, "mouse_tracking_mode", "joystick")

            # Convert scroll direction to numeric value
            scroll_value = 0
            if event.event_type == "mouse_scroll" and event.direction is not None:
                scroll_value = 1 if event.direction == "up" else -1

            # Create a simplified log structure
            clean_log = {
                "timestamp": event.timestamp,
                "mode": tracking_mode,
                "keyboard": {"keys": event.active_keys or []},
                "mouse": {
                    "buttons": [event.button_pressed] if event.button_pressed else []
                },
            }

            # Only include scroll_direction if capture_scroll is enabled or there's actual scrolling
            if self.capture_scroll_check.isChecked() or scroll_value != 0:
                clean_log["mouse"]["scroll_direction"] = scroll_value

            # Add tracking mode specific data
            if tracking_mode == "joystick":
                clean_log["mouse"]["rel_x"] = (
                    event.rel_x if event.rel_x is not None else 0.0
                )
                clean_log["mouse"]["rel_y"] = (
                    event.rel_y if event.rel_y is not None else 0.0
                )
                clean_log["mouse"]["speed"] = (
                    event.speed if event.speed is not None else 0.0
                )
            elif tracking_mode == "delta":
                clean_log["mouse"]["delta_x"] = (
                    event.mouse_delta_x if hasattr(event, "mouse_delta_x") else 0.0
                )
                clean_log["mouse"]["delta_y"] = (
                    event.mouse_delta_y if hasattr(event, "mouse_delta_y") else 0.0
                )
            elif tracking_mode == "angle":
                if hasattr(event, "direction_only") and event.direction_only:
                    clean_log["mouse"]["discrete_angle"] = (
                        event.discrete_angle if hasattr(event, "discrete_angle") else 0
                    )
                else:
                    clean_log["mouse"]["angle"] = (
                        event.mouse_delta_angle
                        if hasattr(event, "mouse_delta_angle")
                        else 0.0
                    )
                    clean_log["mouse"]["magnitude"] = (
                        event.mouse_delta_magnitude
                        if hasattr(event, "mouse_delta_magnitude")
                        else 0.0
                    )
            elif tracking_mode == "axis":
                clean_log["mouse"]["north"] = (
                    event.north if hasattr(event, "north") else 0.0
                )
                clean_log["mouse"]["south"] = (
                    event.south if hasattr(event, "south") else 0.0
                )
                clean_log["mouse"]["east"] = (
                    event.east if hasattr(event, "east") else 0.0
                )
                clean_log["mouse"]["west"] = (
                    event.west if hasattr(event, "west") else 0.0
                )

            # Write to file and flush
            self.log_file.write(json.dumps(clean_log) + "\n")
            self.log_file.flush()
        except Exception as e:
            print(f"Error logging to file: {e}")

    def _log_event_to_csv(self, event: InputData) -> None:
        """Log event data to CSV file."""
        try:
            import csv
            
            # Create a row with data for each column
            row_data = {}
            
            # Add timestamp
            row_data['timestamp'] = event.timestamp
            
            # Set default values for all columns
            for header in self.csv_headers:
                if header != 'timestamp':
                    row_data[header] = 0
            
            # Process keyboard keys
            for key in event.active_keys:
                # Skip F9/media_play_pause key
                if key == "Key.media_play_pause":
                    continue
                
                # Format the key name for CSV column lookup
                csv_key_name = key
                if key.startswith("Key."):
                    csv_key_name = key[4:]  # Remove "Key." prefix
                
                key_header = f"key_{csv_key_name}"
                
                if key_header in self.csv_headers:
                    row_data[key_header] = 1
            
            # Process mouse buttons
            if hasattr(event, 'button_pressed') and event.button_pressed:
                if event.button_pressed == "Button.left" and 'mouse_left' in self.csv_headers:
                    row_data['mouse_left'] = 1
                elif event.button_pressed == "Button.right" and 'mouse_right' in self.csv_headers:
                    row_data['mouse_right'] = 1
            
            # Process scroll
            if event.event_type == "mouse_scroll" and 'mouse_scroll' in self.csv_headers:
                scroll_value = 0
                if event.direction == "up":
                    scroll_value = 1
                elif event.direction == "down":
                    scroll_value = -1
                row_data['mouse_scroll'] = scroll_value
            
            # Process mouse tracking mode specific data
            tracking_mode = getattr(event, "mouse_tracking_mode", "joystick")
            
            if tracking_mode == "joystick":
                if 'mouse_rel_x' in self.csv_headers:
                    row_data['mouse_rel_x'] = event.rel_x if event.rel_x is not None else 0.0
                if 'mouse_rel_y' in self.csv_headers:
                    row_data['mouse_rel_y'] = event.rel_y if event.rel_y is not None else 0.0
                if 'mouse_speed' in self.csv_headers:
                    row_data['mouse_speed'] = event.speed if event.speed is not None else 0.0
            elif tracking_mode == "delta":
                if 'mouse_delta_x' in self.csv_headers:
                    row_data['mouse_delta_x'] = event.mouse_delta_x if hasattr(event, "mouse_delta_x") else 0.0
                if 'mouse_delta_y' in self.csv_headers:
                    row_data['mouse_delta_y'] = event.mouse_delta_y if hasattr(event, "mouse_delta_y") else 0.0
            elif tracking_mode == "angle":
                direction_only = getattr(event, "direction_only", False)
                if direction_only:
                    if 'mouse_discrete_angle' in self.csv_headers:
                        row_data['mouse_discrete_angle'] = event.discrete_angle if hasattr(event, "discrete_angle") else 0
                else:
                    if 'mouse_angle' in self.csv_headers:
                        row_data['mouse_angle'] = event.mouse_delta_angle if hasattr(event, "mouse_delta_angle") else 0.0
                    if 'mouse_magnitude' in self.csv_headers:
                        row_data['mouse_magnitude'] = event.mouse_delta_magnitude if hasattr(event, "mouse_delta_magnitude") else 0.0
            elif tracking_mode == "axis":
                if 'mouse_north' in self.csv_headers:
                    row_data['mouse_north'] = event.north if hasattr(event, "north") else 0.0
                if 'mouse_south' in self.csv_headers:
                    row_data['mouse_south'] = event.south if hasattr(event, "south") else 0.0
                if 'mouse_east' in self.csv_headers:
                    row_data['mouse_east'] = event.east if hasattr(event, "east") else 0.0
                if 'mouse_west' in self.csv_headers:
                    row_data['mouse_west'] = event.west if hasattr(event, "west") else 0.0
            
            # Create row in same order as headers
            row = [row_data.get(header, '') for header in self.csv_headers]
            
            # Write row to CSV
            self.csv_writer.writerow(row)
            self.csv_file.flush()
            
        except Exception as e:
            self._log_status(f"Error writing to CSV: {e}", self.error_color)

    def _log_status(self, message: str, color: Optional[str] = None) -> None:
        """
        Log a message to the status area.

        Args:
            message: The message to log
            color: Optional color for the message (as a hex string)
        """
        # Get current time with millisecond precision
        current_time = time.time()
        timestamp = time.strftime("%H:%M:%S", time.localtime(current_time))
        ms = int((current_time - int(current_time)) * 1000)
        formatted_time = f"{timestamp}.{ms:03d}"

        # Format the message with HTML for color
        if color:
            html_message = f"<span style='color: #999999;'>{formatted_time} - </span><span style='color: {color};'>{message}</span>"
        else:
            html_message = (
                f"<span style='color: #999999;'>{formatted_time} - </span>{message}"
            )

        # Append the message
        self.status_text.append(html_message)

        # Auto-scroll to bottom
        self.status_text.moveCursor(QTextCursor.End)

    def _update_active_keys_display(self) -> None:
        """Update the active keys display."""
        active = self.collector.get_active_keys()
        if active:
            self.active_keys_label.setText(", ".join(active))
        else:
            self.active_keys_label.setText("None")

    def _toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.showFullScreen()
        else:
            self.showNormal()

        # Force update visualizers
        QTimer.singleShot(200, self._force_update_visualizers)

    def _exit_fullscreen(self) -> None:
        """Exit fullscreen mode."""
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.showNormal()
            # Force update visualizers
            QTimer.singleShot(200, self._force_update_visualizers)

    def _force_update_visualizers(self) -> None:
        """Force update of visualizers."""
        self.keyboard_viz.force_update()
        self.mouse_viz.force_update()

    def resizeEvent(self, event) -> None:
        """Handle resize events."""
        super().resizeEvent(event)
        # Update visualizers after resize
        QTimer.singleShot(100, self._force_update_visualizers)

    def run(self) -> None:
        """Run the application."""
        self.show()

    def closeEvent(self, event) -> None:
        """Handle application close event."""
        # Stop collectors and close log files
        if self.is_recording:
            self.collector.stop_capture()

        if self.log_file:
            self.log_file.close()
            
        if self.csv_file:
            self.csv_file.close()

        # Accept the close event
        event.accept()

    def _on_capture_scroll_changed(self, checked: bool) -> None:
        """Sync scroll capture checkbox state with the mouse buttons selector."""
        self.mouse_buttons_selector.setScrollTracking(checked)
        if self.edit_keys_mode:
            self._log_status(
                f"Scroll tracking {'enabled' if checked else 'disabled'}",
                self.success_color if checked else self.warning_color,
            )

        # Update tracking status if this represents a change in button tracking
        button_id = "Button.scroll"
        is_tracked = button_id in self.tracked_keys

        # Ensure scroll button state is consistent with checkbox
        if checked and not is_tracked:
            # Add to tracked keys
            self.tracked_keys.append(button_id)
            self.collector.set_supported_keys(self.tracked_keys)
        elif not checked and is_tracked:
            # Remove from tracked keys
            self.tracked_keys.remove(button_id)
            self.collector.set_supported_keys(self.tracked_keys)

        # Update the mouse buttons display
        self.mouse_buttons_selector.setTrackedButtons(self.tracked_keys)

    def _format_ps4_event_text(self, event: InputData) -> str:
        """Format PS4 controller event text for display."""
        active_keys = (
            event.active_keys
            if hasattr(event, "active_keys") and event.active_keys
            else []
        )

        if event.event_type == "button_press":
            return f"Controller: Button {event.key} pressed | Active: {', '.join(active_keys)}"
        elif event.event_type == "button_release":
            return f"Controller: Button {event.key} released | Active: {', '.join(active_keys)}"
        elif event.event_type == "axis_motion":
            value = event.rel_x if event.rel_x is not None else event.rel_y
            if value is not None:
                if "Trigger" in event.key:
                    # For triggers, show as percentage
                    return f"Controller: {event.key} at {value*100:.0f}% | Active: {', '.join(active_keys)}"
                else:
                    # For joysticks, show as position
                    if "X" in event.key:
                        y_key = event.key.replace("_X", "_Y")
                        y_value = 0.0
                        # Find the Y value in active collector
                        if hasattr(self.collector, "axis_state"):
                            y_value = self.collector.axis_state.get(y_key, 0.0)
                        direction = ""
                        if abs(value) > 0.1 or abs(y_value) > 0.1:
                            if abs(value) > 0.1:
                                direction += "X+" if value > 0 else "X-"
                            if abs(y_value) > 0.1:
                                direction += "Y+" if y_value > 0 else "Y-"
                        direction_text = f" Dir:{direction}" if direction else ""
                        return f"Controller: {event.key.replace('_X', '')} pos:({value:.2f}, {y_value:.2f}){direction_text} | Active: {', '.join(active_keys)}"
                    else:
                        return f"Controller: {event.key} at {value:.2f} | Active: {', '.join(active_keys)}"

        return f"Controller: {event.event_type} | Active: {', '.join(active_keys)}"

    def _log_ps4_event_to_file(self, event: InputData) -> None:
        """Log PS4 controller event to file."""
        try:
            # Create a simplified log structure for PS4 controller
            clean_log = {
                "timestamp": event.timestamp,
                "device": "ps4_controller",
                "inputs": {"buttons": event.active_keys or []},
            }

            # Add event-specific data
            if event.event_type == "button_press":
                clean_log["event_type"] = "button_press"
                clean_log["button"] = event.key
            elif event.event_type == "axis_motion":
                clean_log["event_type"] = "axis_motion"
                clean_log["axis"] = event.key
                if "Trigger" in event.key:
                    # Trigger value (0 to 1)
                    value = event.rel_x if event.rel_x is not None else 0.0
                    clean_log["value"] = value
                elif "Stick" in event.key:
                    # Get joystick X/Y values
                    if "_X" in event.key:
                        base_name = event.key.replace("_X", "")
                        clean_log["axis"] = base_name

                        # X value
                        x_value = event.rel_x if event.rel_x is not None else 0.0

                        # Find Y value from collector state
                        y_value = 0.0
                        if hasattr(self.collector, "axis_state"):
                            y_key = f"{base_name}_Y"
                            y_value = self.collector.axis_state.get(y_key, 0.0)

                        # Store as position
                        clean_log["position"] = {"x": x_value, "y": y_value}

                        # Calculate magnitude and direction (like mouse tracking)
                        magnitude = math.sqrt(x_value**2 + y_value**2)
                        clean_log["magnitude"] = magnitude

                        # Only include direction if significant movement
                        if magnitude > 0.1:
                            # Calculate angle in degrees (0 = right, 90 = down)
                            angle = math.degrees(math.atan2(y_value, x_value))
                            angle = (angle + 360) % 360
                            clean_log["angle"] = angle

            # Write to file and flush
            self.log_file.write(json.dumps(clean_log) + "\n")
            self.log_file.flush()
        except Exception as e:
            print(f"Error logging PS4 event to file: {e}")

    def _log_ps4_event_to_csv(self, event: InputData) -> None:
        """Log PS4 controller event to CSV file."""
        try:
            import csv
            
            # Create a row with data for each column
            row_data = {}
            
            # Add timestamp
            row_data['timestamp'] = event.timestamp
            
            # Set default values for all columns
            for header in self.csv_headers:
                if header != 'timestamp':
                    row_data[header] = 0
            
            # Process active buttons - with the same formatting as regular keys
            if hasattr(event, 'active_keys') and event.active_keys:
                for key in event.active_keys:
                    # Skip F9/media_play_pause key
                    if key == "Key.media_play_pause":
                        continue
                    
                    # Format the key name for CSV column lookup
                    csv_key_name = key
                    if key.startswith("Key."):
                        csv_key_name = key[4:]  # Remove "Key." prefix
                    
                    key_header = f"key_{csv_key_name}"
                    
                    if key_header in self.csv_headers:
                        row_data[key_header] = 1
            
            # Handle specific PS4 controller event types
            if event.event_type == "axis_motion":
                if hasattr(event, 'key') and hasattr(event, 'rel_x') and event.rel_x is not None:
                    # For joysticks, we store X and Y positions
                    if "_X" in event.key:
                        base_name = event.key.replace("_X", "")
                        header_x = f"controller_{base_name}_x"
                        header_y = f"controller_{base_name}_y"
                        
                        # X value
                        if header_x in self.csv_headers:
                            row_data[header_x] = event.rel_x
                        
                        # Y value (look up from controller state)
                        y_value = 0.0
                        if hasattr(self.collector, "axis_state"):
                            y_key = f"{base_name}_Y"
                            y_value = self.collector.axis_state.get(y_key, 0.0)
                            if header_y in self.csv_headers:
                                row_data[header_y] = y_value
                    else:
                        # For triggers or other single-axis controls
                        header = f"controller_{event.key}"
                        if header in self.csv_headers:
                            row_data[header] = event.rel_x
            
            # Create row in same order as headers
            row = [row_data.get(header, '') for header in self.csv_headers]
            
            # Write row to CSV
            self.csv_writer.writerow(row)
            self.csv_file.flush()
            
        except Exception as e:
            self._log_status(f"Error writing PS4 event to CSV: {e}", self.error_color)


def run_collector_app() -> None:
    """
    Run the input collector application.

    Creates and runs the input collector application as a standalone program.
    """
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    collector_app = InputCollectorApp()
    collector_app.run()
    sys.exit(app.exec_())
