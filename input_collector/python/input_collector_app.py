"""
Input collector application module.

This module provides the main application for collecting, visualizing, and
logging keyboard and mouse inputs in real-time with a graphical user interface using PyQt5.
"""
import sys
import json
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QTextEdit, QCheckBox, QComboBox,
    QFrame, QSplitter, QGroupBox, QListWidget, QSlider, QSpacerItem,
    QSizePolicy, QAction  # Added QAction here instead
)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QPalette, QFont, QTextCursor  # Removed QAction from here
from typing import List, Dict, Optional, Any

from .collectors import KeyboardMouseCollector
from .interfaces import InputData
from .visualizers import KeyboardVisualizer, MouseVisualizer


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
        
        # Setup UI
        self.setWindowTitle("Input Collector")
        self.setGeometry(100, 100, 800, 700)
        self.setMinimumSize(750, 650)
        
        # Set application style
        self._set_dark_theme()
        
        # Create UI components
        self._create_ui()
        
        # Create collector
        self.collector = KeyboardMouseCollector()
        
        # Connect collector callbacks
        self.collector.on_event(self._handle_input_event)
        
        # Connect event signal to slot
        self.event_received.connect(self._process_event)
        
        # Set tracked keys
        self.tracked_keys = [
            "w", "a", "s", "d", "q", "e", "f", "m", "c", "b",
            "1", "2", "3", "4",
            "Key.space", "Key.shift", 
            "Key.media_play_pause"
        ]
        self.collector.set_supported_keys(self.tracked_keys)
        self._update_key_list()
        
        # Set the tracked keys in the keyboard visualizer for highlighting
        self.keyboard_viz.set_tracked_keys(self.tracked_keys)
        
        # Set screen dimensions for velocity-based joystick control
        screen_rect = QApplication.desktop().screenGeometry()
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()
        self.collector.set_screen_dimensions(screen_width, screen_height)
        
        # Set joystick sensitivity
        self.collector.set_joystick_sensitivity(0.1)
        
        # Initialize mouse tracking mode to match UI defaults
        self._set_mouse_tracking_mode(self.tracking_mode_combo.currentText())
        
        # Start timer for periodic UI updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_active_keys_display)
        self.update_timer.start(100)
        
        # Setup shortcuts
        self._setup_shortcuts()
    
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
        self.setStyleSheet(f"""
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
        """)
    
    def _create_ui(self) -> None:
        """Create the application UI components."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Control panel
        control_panel = QHBoxLayout()
        
        # Recording controls
        recording_frame = QHBoxLayout()
        
        self.record_button = QPushButton("Record")
        self.record_button.setStyleSheet(f"background-color: #AA3333; color: white;")
        self.record_button.clicked.connect(self._toggle_recording)
        recording_frame.addWidget(self.record_button)
        
        self.log_checkbox = QCheckBox("Log")
        self.log_checkbox.toggled.connect(self._toggle_logging)
        recording_frame.addWidget(self.log_checkbox)
        
        self.status_label = QLabel("Not Recording")
        recording_frame.addWidget(self.status_label)
        
        control_panel.addLayout(recording_frame)
        control_panel.addStretch(1)
        
        # Key tracking controls
        key_tracking_frame = QHBoxLayout()
        key_tracking_frame.addWidget(QLabel("Key:"))
        
        self.key_entry = QLineEdit()
        self.key_entry.setMaximumWidth(100)
        key_tracking_frame.addWidget(self.key_entry)
        
        add_key_button = QPushButton("Add")
        add_key_button.clicked.connect(self._add_key)
        key_tracking_frame.addWidget(add_key_button)
        
        remove_key_button = QPushButton("Remove")
        remove_key_button.clicked.connect(self._remove_key)
        key_tracking_frame.addWidget(remove_key_button)
        
        control_panel.addLayout(key_tracking_frame)
        control_panel.addStretch(1)
        
        # Mouse tracking mode controls
        mouse_mode_frame = QHBoxLayout()
        
        self.direction_only_check = QCheckBox("Dir Only")
        self.direction_only_check.setChecked(True)
        self.direction_only_check.toggled.connect(self._update_tracking_modes)
        mouse_mode_frame.addWidget(self.direction_only_check)
        
        mouse_mode_frame.addWidget(QLabel("Mode:"))
        
        self.tracking_mode_combo = QComboBox()
        self.tracking_mode_combo.addItems(["angle", "axis"])
        self.tracking_mode_combo.setMinimumWidth(80)
        self.tracking_mode_combo.currentTextChanged.connect(self._set_mouse_tracking_mode)
        mouse_mode_frame.addWidget(self.tracking_mode_combo)
        
        control_panel.addLayout(mouse_mode_frame)
        
        main_layout.addLayout(control_panel)
        
        # Visualization area
        viz_layout = QHBoxLayout()
        
        # Keyboard visualization
        keyboard_group = QGroupBox("Keyboard Input")
        keyboard_layout = QVBoxLayout(keyboard_group)
        self.keyboard_viz = KeyboardVisualizer()
        keyboard_layout.addWidget(self.keyboard_viz)
        viz_layout.addWidget(keyboard_group)
        
        # Mouse visualization
        mouse_group = QGroupBox("Mouse Input")
        mouse_layout = QVBoxLayout(mouse_group)
        self.mouse_viz = MouseVisualizer()
        mouse_layout.addWidget(self.mouse_viz)
        viz_layout.addWidget(mouse_group)
        
        main_layout.addLayout(viz_layout, 1)
        
        # Active keys display
        active_keys_group = QGroupBox("Active Keys")
        active_keys_layout = QVBoxLayout(active_keys_group)
        self.active_keys_label = QLabel("None")
        self.active_keys_label.setAlignment(Qt.AlignCenter)
        active_keys_layout.addWidget(self.active_keys_label)
        main_layout.addWidget(active_keys_group)
        
        # Tracked keys list
        tracked_keys_group = QGroupBox("Tracked Keys")
        tracked_keys_layout = QVBoxLayout(tracked_keys_group)
        self.key_listbox = QListWidget()
        self.key_listbox.setMaximumHeight(100)
        tracked_keys_layout.addWidget(self.key_listbox)
        main_layout.addWidget(tracked_keys_group)
        
        # Status area
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        status_layout.addWidget(self.status_text)
        main_layout.addWidget(status_group)
        
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
        self.angle_grouping_slider.valueChanged.connect(self._update_angle_grouping_display)
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
        
        main_layout.addWidget(settings_group)
    
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
        if self.is_recording:
            # Stop recording
            print("Stopping recording...")
            self.collector.stop_capture()
            self.is_recording = False
            self.record_button.setText("Record")
            self.record_button.setStyleSheet("background-color: #AA3333; color: white;")
            self.status_label.setText("Not Recording")
            self._log_status("Recording stopped", self.warning_color)
            if self.log_file:
                self.log_file.write(f"{{\n\"event\": \"recording_stopped\",\n\"timestamp\": {time.time()}\n}}\n")
                self.log_file.flush()
        else:
            # Start recording
            print("Starting recording...")
            self.collector.start_capture()
            self.is_recording = True
            self.record_button.setText("Stop")
            self.record_button.setStyleSheet("background-color: #CC3333; color: white;")
            self.status_label.setText("RECORDING")
            self._log_status("Recording started", self.success_color)
            if self.log_file:
                self.log_file.write(f"{{\n\"event\": \"recording_started\",\n\"timestamp\": {time.time()}\n}}\n")
                self.log_file.flush()
        
        # Force update the UI
        QApplication.processEvents()
    
    def _toggle_logging(self, checked: bool) -> None:
        """Toggle logging to file."""
        self.log_to_file = checked
        if self.log_to_file:
            # Open log file with timestamp
            current_time = time.time()
            timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime(current_time))
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
    
    def _add_key(self) -> None:
        """Add a key to the tracked keys list."""
        key = self.key_entry.text().strip()
        if key and key not in self.tracked_keys:
            self.tracked_keys.append(key)
            self.collector.set_supported_keys(self.tracked_keys)
            self._update_key_list()
            self.key_entry.clear()
            self._log_status(f"Added key: {key}")
            self.keyboard_viz.set_tracked_keys(self.tracked_keys)
    
    def _remove_key(self) -> None:
        """Remove a key from the tracked keys list."""
        selected_items = self.key_listbox.selectedItems()
        if selected_items:
            key = selected_items[0].text()
            self.tracked_keys.remove(key)
            self.collector.set_supported_keys(self.tracked_keys)
            self._update_key_list()
            self._log_status(f"Removed key: {key}")
            self.keyboard_viz.set_tracked_keys(self.tracked_keys)
    
    def _update_key_list(self) -> None:
        """Update the key list display."""
        self.key_listbox.clear()
        for key in self.tracked_keys:
            self.key_listbox.addItem(key)
    
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
            self.tracking_mode_combo.addItems(["angle", "axis"])
            
            # Set appropriate mode
            if current_mode in ["angle", "axis"]:
                self.tracking_mode_combo.setCurrentText(current_mode)
            else:
                self.tracking_mode_combo.setCurrentText("angle")
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
        direction_only = self.direction_only_check.isChecked()
        angle_grouping = self.angle_grouping_slider.value()
        
        self.collector.set_mouse_tracking_mode(mode, direction_only, angle_grouping)
        self._log_status(f"Mouse tracking mode set to: {mode}", self.accent_color)
        
        # Update display properties based on mode
        if mode == "axis":
            self._log_status("Axis mode shows membership values for N, S, E, W directions", "#AAAAAA")
        elif mode == "angle" and direction_only:
            self._log_status(f"Angle mode using {angle_grouping}° grouping ({360 // angle_grouping} values)", "#AAAAAA")
    
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
        self._log_status(f"Angle grouping set to: {angle_grouping}° ({360 // angle_grouping} values)")
        
        # Log scroll capture status
        self._log_status(f"Scroll data capture: {'Enabled' if self.capture_scroll_check.isChecked() else 'Disabled'}")
        
        # Re-apply current tracking mode to ensure all settings are updated
        self._set_mouse_tracking_mode(self.tracking_mode_combo.currentText())
    
    def _handle_input_event(self, event: InputData) -> None:
        """Handle events from the input collector."""
        # Use signal to safely handle events from collector thread
        self.event_received.emit(event)
    
    @pyqtSlot(object)
    def _process_event(self, event: InputData) -> None:
        """Process input events in the main thread."""
        # Check for special toggle_recording event type first (for F9 key)
        if event.event_type == "toggle_recording":
            self._toggle_recording()
            
            # Highlight the F9 key in the keyboard visualizer
            temp_press_event = InputData(
                timestamp=event.timestamp,
                event_type="key_press",
                key="Key.media_play_pause",
                active_keys=event.active_keys or []
            )
            self.keyboard_viz.update(temp_press_event)
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
            # Only update the visualizer
            self.keyboard_viz.update(event)
            self._update_active_keys_display()
            return
        
        # Handle regular media_play_pause key (from actual media key)
        if (event.event_type == "key_press" and
            event.key and "media_play_pause" in event.key.lower()):
            # Call the toggle method
            self._toggle_recording()
            
            # Update keyboard visualizer
            self.keyboard_viz.update(event)
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
            (event.event_type == "key_press") or
            (event.event_type == "mouse_move" and event.is_moving) or
            (event.event_type == "mouse_click") or
            (event.event_type == "mouse_scroll") or
            (event.button_pressed is not None)
        )
        
        if self.is_recording and should_log:
            event_text = self._format_event_text(event)
            self._log_status(event_text)
            
            # Log to file if enabled
            if self.log_file and self.log_to_file:
                self._log_event_to_file(event)
    
    def _format_event_text(self, event: InputData) -> str:
        """Format event text for UI display based on tracking mode."""
        # Format keyboard info
        keyboard_part = f"Keys: [{', '.join(event.active_keys)}]" if event.active_keys else "Keys: []"
        
        # Format mouse info based on tracking mode
        mouse_parts = []
        tracking_mode = getattr(event, 'mouse_tracking_mode', 'joystick')
        
        # Click info
        if event.event_type == "mouse_click" and event.button_pressed:
            mouse_parts.append(f"Click:{event.button_pressed}")
        elif hasattr(event, 'button_pressed') and event.button_pressed:
            mouse_parts.append(f"Click:{event.button_pressed}")
        
        # Scroll info
        if event.event_type == "mouse_scroll" and event.direction:
            mouse_parts.append(f"Scroll:{event.direction}")
        
        # Movement info - mode specific
        if event.is_moving:
            if tracking_mode == "delta":
                if hasattr(event, 'mouse_delta_x') and hasattr(event, 'mouse_delta_y'):
                    mouse_parts.append(f"Δx:{event.mouse_delta_x:.1f} Δy:{event.mouse_delta_y:.1f}")
                if hasattr(event, 'mouse_delta_magnitude'):
                    mouse_parts.append(f"Mag:{event.mouse_delta_magnitude:.1f}")
                if event.direction:
                    mouse_parts.append(f"Dir:{event.direction}")
            elif tracking_mode == "angle":
                if hasattr(event, 'direction_only') and event.direction_only:
                    if hasattr(event, 'discrete_angle'):
                        mouse_parts.append(f"Angle:{event.discrete_angle}°")
                else:
                    if hasattr(event, 'mouse_delta_angle'):
                        mouse_parts.append(f"Angle:{event.mouse_delta_angle:.1f}°")
                    if hasattr(event, 'mouse_delta_magnitude'):
                        mouse_parts.append(f"Mag:{event.mouse_delta_magnitude:.1f}")
                if event.direction:
                    mouse_parts.append(f"Dir:{event.direction}")
            elif tracking_mode == "axis":
                if hasattr(event, 'north') and hasattr(event, 'south') and hasattr(event, 'east') and hasattr(event, 'west'):
                    mouse_parts.append(f"N:{event.north:.1f} S:{event.south:.1f} E:{event.east:.1f} W:{event.west:.1f}")
            else:  # joystick mode
                if event.direction:
                    mouse_parts.append(f"Dir:{event.direction}")
                if event.speed is not None:
                    mouse_parts.append(f"Speed:{event.speed:.1f}")
        
        # Combine all mouse info
        mouse_part = f"Mouse[{tracking_mode}]: {' | '.join(mouse_parts)}" if mouse_parts else f"Mouse[{tracking_mode}]: Idle"
        
        return f"{keyboard_part} | {mouse_part}"
    
    def _log_event_to_file(self, event: InputData) -> None:
        """Log event to file."""
        try:
            # Determine current tracking mode
            tracking_mode = getattr(event, 'mouse_tracking_mode', 'joystick')
            
            # Convert scroll direction to numeric value
            scroll_value = 0
            if event.event_type == "mouse_scroll" and event.direction is not None:
                scroll_value = 1 if event.direction == "up" else -1
            
            # Create a simplified log structure
            clean_log = {
                "timestamp": event.timestamp,
                "mode": tracking_mode,
                "keyboard": {
                    "keys": event.active_keys or []
                },
                "mouse": {
                    "buttons": [event.button_pressed] if event.button_pressed else []
                }
            }

            # Only include scroll_direction if capture_scroll is enabled or there's actual scrolling
            if self.capture_scroll_check.isChecked() or scroll_value != 0:
                clean_log["mouse"]["scroll_direction"] = scroll_value
            
            # Add tracking mode specific data
            if tracking_mode == "joystick":
                clean_log["mouse"]["rel_x"] = event.rel_x if event.rel_x is not None else 0.0
                clean_log["mouse"]["rel_y"] = event.rel_y if event.rel_y is not None else 0.0
                clean_log["mouse"]["speed"] = event.speed if event.speed is not None else 0.0
            elif tracking_mode == "delta":
                clean_log["mouse"]["delta_x"] = event.mouse_delta_x if hasattr(event, 'mouse_delta_x') else 0.0
                clean_log["mouse"]["delta_y"] = event.mouse_delta_y if hasattr(event, 'mouse_delta_y') else 0.0
            elif tracking_mode == "angle":
                if hasattr(event, 'direction_only') and event.direction_only:
                    clean_log["mouse"]["discrete_angle"] = event.discrete_angle if hasattr(event, 'discrete_angle') else 0
                else:
                    clean_log["mouse"]["angle"] = event.mouse_delta_angle if hasattr(event, 'mouse_delta_angle') else 0.0
                    clean_log["mouse"]["magnitude"] = event.mouse_delta_magnitude if hasattr(event, 'mouse_delta_magnitude') else 0.0
            elif tracking_mode == "axis":
                clean_log["mouse"]["north"] = event.north if hasattr(event, 'north') else 0.0
                clean_log["mouse"]["south"] = event.south if hasattr(event, 'south') else 0.0
                clean_log["mouse"]["east"] = event.east if hasattr(event, 'east') else 0.0
                clean_log["mouse"]["west"] = event.west if hasattr(event, 'west') else 0.0
            
            # Write to file and flush
            self.log_file.write(json.dumps(clean_log) + "\n")
            self.log_file.flush()
        except Exception as e:
            print(f"Error logging to file: {e}")
    
    def _log_status(self, message: str, color: Optional[str] = None) -> None:
        """
        Log a message to the status area.
        
        Args:
            message: The message to log
            color: Optional color for the message (as a hex string)
        """
        # Get current time with millisecond precision
        current_time = time.time()
        timestamp = time.strftime('%H:%M:%S', time.localtime(current_time))
        ms = int((current_time - int(current_time)) * 1000)
        formatted_time = f"{timestamp}.{ms:03d}"
        
        # Format the message with HTML for color
        if color:
            html_message = f"<span style='color: #999999;'>{formatted_time} - </span><span style='color: {color};'>{message}</span>"
        else:
            html_message = f"<span style='color: #999999;'>{formatted_time} - </span>{message}"
        
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
        # Stop collectors and close log file
        if self.is_recording:
            self.collector.stop_capture()
        
        if self.log_file:
            self.log_file.close()
        
        # Accept the close event
        event.accept()


def run_collector_app() -> None:
    """
    Run the input collector application.
    
    Creates and runs the input collector application as a standalone program.
    """
    app = QApplication(sys.argv)
    collector_app = InputCollectorApp()
    collector_app.run()
    sys.exit(app.exec_())