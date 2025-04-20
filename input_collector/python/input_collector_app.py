"""
Input collector application module.

This module provides the main application for collecting, visualizing, and
logging keyboard and mouse inputs in real-time with a graphical user interface using PyQt5.
"""

import sys
import time
import os
from typing import List, Dict, Optional, Callable, Any
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QAction
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot

from .interfaces import InputData, AbstractInputCollector
from .collectors import KeyboardMouseCollector

# Import new modular components
from .ui import UIManager, VisualizerManager
from .logging import LoggingManager
from .processing import EventProcessor

# Import PS4 controller with fallback
try:
    from .collectors.ps4_controller import PS4ControllerCollector, is_sdl2_available
    HAVE_PS4_SUPPORT = is_sdl2_available()
    if HAVE_PS4_SUPPORT:
        print("SDL2 detected successfully. PS4 controller support is available.")
    else:
        print("SDL2 could not be properly initialized. PS4 controller support will be disabled.")
except ImportError as e:
    print(f"PS4 controller support disabled: {e}")
    print("To enable PS4 controller support, install required packages with:")
    print("pip install pysdl2 pysdl2-dll")
    HAVE_PS4_SUPPORT = False


class CollectorManager:
    """
    Manages input collectors and their interactions with visualizers.
    
    This class handles the creation, configuration, and management of input collectors,
    as well as coordinating the flow of input events to the appropriate visualizers.
    """
    
    def __init__(self):
        """Initialize the collector manager."""
        self.collectors = {}
        self.current_collector = None
        self.current_collector_type = None
        self.visualizers = []
        self.tracked_keys = []
        self.event_callbacks = []
        
        # Initialize collectors
        self._initialize_collectors()
    
    def _initialize_collectors(self) -> None:
        """Initialize available input collectors."""
        # Always add keyboard/mouse collector
        self.add_collector("keyboard_mouse", KeyboardMouseCollector())
        
        # Add PS4 controller if available
        if HAVE_PS4_SUPPORT:
            try:
                print("Attempting to initialize PS4 controller...")
                ps4_collector = PS4ControllerCollector()
                self.add_collector("ps4_controller", ps4_collector)
                print("PS4 controller collector initialized successfully.")
            except Exception as e:
                print(f"Error initializing PS4 controller: {e}")
                import traceback
                traceback.print_exc()
        
        # Set default collector
        self.set_current_collector("keyboard_mouse")
    
    def add_collector(self, collector_type: str, collector: AbstractInputCollector) -> None:
        """
        Add a collector to the manager.
        
        Args:
            collector_type: Type identifier for the collector
            collector: The collector instance
        """
        self.collectors[collector_type] = collector
        collector.on_event(self._handle_input_event)
    
    def set_current_collector(self, collector_type: str) -> bool:
        """
        Set the current active collector.
        
        Args:
            collector_type: Type identifier for the collector to activate
            
        Returns:
            bool: True if successful, False otherwise
        """
        if collector_type not in self.collectors:
            return False
        
        self.current_collector_type = collector_type
        self.current_collector = self.collectors[collector_type]
        
        # Update tracked keys
        if self.tracked_keys:
            self.current_collector.set_supported_keys(self.tracked_keys)
        
        # Update visualizers for the new collector
        self._update_visualizers()
        
        return True
    
    def get_available_collectors(self) -> List[Dict[str, str]]:
        """
        Get a list of available collectors.
        
        Returns:
            List[Dict[str, str]]: List of collector information dictionaries
        """
        return [
            {"type": collector_type, "name": self._get_collector_display_name(collector_type)}
            for collector_type in self.collectors
        ]
    
    def _get_collector_display_name(self, collector_type: str) -> str:
        """Get a user-friendly display name for a collector type."""
        display_names = {
            "keyboard_mouse": "Keyboard & Mouse",
            "ps4_controller": "PS4 Controller"
        }
        return display_names.get(collector_type, collector_type)
    
    def start_capture(self) -> None:
        """Start capturing with the current collector."""
        if self.current_collector:
            self.current_collector.start_capture()
    
    def stop_capture(self) -> None:
        """Stop capturing with the current collector."""
        if self.current_collector:
            self.current_collector.stop_capture()
    
    def register_visualizer(self, visualizer) -> None:
        """
        Register a visualizer to receive updates from the collectors.
        
        Args:
            visualizer: The visualizer to register
        """
        if visualizer not in self.visualizers:
            self.visualizers.append(visualizer)
            
        # Update the visualizer with the current collector's capabilities
        self._update_visualizer(visualizer)
    
    def unregister_visualizer(self, visualizer) -> None:
        """
        Unregister a visualizer.
        
        Args:
            visualizer: The visualizer to unregister
        """
        if visualizer in self.visualizers:
            self.visualizers.remove(visualizer)
    
    def _update_visualizers(self) -> None:
        """Update all registered visualizers with the current collector."""
        for visualizer in self.visualizers:
            self._update_visualizer(visualizer)
    
    def _update_visualizer(self, visualizer) -> None:
        """
        Update a single visualizer with the current collector's information.
        
        Args:
            visualizer: The visualizer to update
        """
        if not self.current_collector:
            return
        
        # Set capabilities
        capabilities = self.current_collector.get_capabilities()
        if hasattr(visualizer, "set_collector_capabilities"):
            visualizer.set_collector_capabilities(capabilities)
    
    def set_tracked_keys(self, keys: List[str]) -> None:
        """
        Set the keys to be tracked by collectors.
        
        Args:
            keys: List of keys to track
        """
        self.tracked_keys = keys
        if self.current_collector:
            self.current_collector.set_supported_keys(keys)
    
    def get_active_keys(self) -> List[str]:
        """
        Get the currently active keys from the current collector.
        
        Returns:
            List[str]: List of active keys
        """
        if self.current_collector:
            return self.current_collector.get_active_keys()
        return []
    
    def _handle_input_event(self, event: InputData) -> None:
        """
        Handle input events from collectors.
        
        Args:
            event: The input event to process
        """
        # Update visualizers
        for visualizer in self.visualizers:
            # Only update visualizers that support the current collector type
            if (hasattr(visualizer, "supports_collector") and 
                visualizer.supports_collector(self.current_collector_type)):
                visualizer.update(event)
        
        # Notify callbacks
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event callback: {e}")
    
    def on_event(self, callback: Callable[[InputData], None]) -> None:
        """
        Register a callback for input events.
        
        Args:
            callback: Function to call when an input event occurs
        """
        if callback not in self.event_callbacks:
            self.event_callbacks.append(callback)
    
    def remove_event_handler(self, callback: Callable[[InputData], None]) -> None:
        """
        Remove an event callback.
        
        Args:
            callback: The callback to remove
        """
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)
    
    def get_current_collector_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of the current collector.
        
        Returns:
            Dict[str, Any]: Dictionary of capabilities
        """
        if self.current_collector:
            return self.current_collector.get_capabilities()
        return {}
    
    def get_current_collector_type(self) -> str:
        """
        Get the type of the current collector.
        
        Returns:
            str: Collector type identifier
        """
        return self.current_collector_type if self.current_collector_type else ""
    
    def get_collector(self, collector_type: str) -> Optional[AbstractInputCollector]:
        """
        Get a specific collector by type.
        
        Args:
            collector_type: The type of collector to get
            
        Returns:
            Optional[AbstractInputCollector]: The collector instance or None if not found
        """
        return self.collectors.get(collector_type)
    
    def get_current_collector(self) -> Optional[AbstractInputCollector]:
        """
        Get the current collector.
        
        Returns:
            Optional[AbstractInputCollector]: The current collector instance
        """
        return self.current_collector


class InputCollectorApp(QMainWindow):
    """
    Main application for input collection and visualization.

    This class integrates the different components (collector manager, UI manager,
    logging manager, etc.) into a cohesive application.
    """

    # Signal for event handling between threads
    event_received = pyqtSignal(object)

    def __init__(self) -> None:
        """Initialize the application."""
        super().__init__()

        # Define app theme colors
        self.dark_bg = "#2D2D30"
        self.dark_frame_bg = "#252526"
        self.text_color = "#E0E0E0"
        self.accent_color = "#007ACC"
        self.success_color = "#5FB878"
        self.warning_color = "#FFAA33"
        self.error_color = "#FF5555"

        # Application state
        self.is_recording = False
        self.is_fullscreen = False
        self.edit_keys_mode = False
        self.tracked_keys = [
            "w", "a", "s", "d", "q", "e", "f", "m", "c", "b", "1", "2", "3", "4",
            "Key.space", "Key.shift", "Key.media_play_pause", "Button.left", "Button.right",
        ]
        self.last_toggle_time = None
        self.f9_key_down = False
        
        # Set window properties
        self.setWindowTitle("Input Collector")
        self.setGeometry(100, 100, 1200, 700)
        self.setMinimumSize(1050, 650)

        # Initialize core components in proper order
        print("Initializing core components...")
        self.collector_manager = CollectorManager()
        self.event_processor = EventProcessor()
        self.logging_manager = LoggingManager()
        
        # Initialize UI components
        print("Creating UI Manager...")
        self.ui_manager = UIManager(self)
        
        # Get available collectors FIRST, before setting up components
        collectors = self.collector_manager.get_available_collectors()
        print(f"Available collectors: {collectors}")
        
        # Setup components - this creates the visualizer_manager
        print("Setting up components...")
        self._setup_components()
        
        # IMPORTANT: Connect signals AFTER setup_components
        print("Connecting signals...")
        self._connect_signals()
        
        # Use a timer for UI initialization to ensure UI is ready
        print("Starting UI initialization timer...")
        QTimer.singleShot(100, lambda: self._initialize_ui(collectors))
        
        # Setup keyboard shortcuts
        self._setup_shortcuts()

    def _initialize_ui(self, collectors: List[Dict[str, str]]) -> None:
        """Initialize UI with collectors and update visuals."""
        print(f"_initialize_ui called with {len(collectors)} collectors")
        
        # Update collector list in UI
        self.ui_manager.update_collector_list(collectors)
        
        # Force a UI update before setting the collector
        QApplication.processEvents()
        
        # Set the current collector in UI
        current_type = self.collector_manager.get_current_collector_type()
        print(f"Setting current collector to: {current_type}")
        self.ui_manager.select_collector(current_type)
        
        # Update UI for current collector
        self._update_ui_for_collector()
        
        # Schedule one more update to ensure UI is fully ready
        QTimer.singleShot(200, self._check_ui_state)

    def _check_ui_state(self) -> None:
        """Verify UI state after initialization."""
        print("Checking UI state...")
        # Access combobox directly for debugging
        collector_selector = self.ui_manager.components.get('collector_selector')
        if collector_selector:
            print(f"Collector selector has {collector_selector.count()} items")
            for i in range(collector_selector.count()):
                print(f"  Item {i}: {collector_selector.itemText(i)} (data: {collector_selector.itemData(i)})")
            
            # If the combobox is empty, try one more time to populate it
            if collector_selector.count() == 0:
                print("WARNING: Collector selector is empty, trying to repopulate...")
                collectors = self.collector_manager.get_available_collectors()
                print(f"Repopulating with {len(collectors)} collectors")
                self.ui_manager.update_collector_list(collectors)
                self.ui_manager.select_collector(self.collector_manager.get_current_collector_type())
        else:
            print("ERROR: Collector selector component not found!")

    def _connect_signals(self) -> None:
        """Connect component signals and slots."""
        # Connect event handling signals
        self.event_received.connect(self._on_event_received)
        self.collector_manager.on_event(self._on_collector_event)
        self.event_processor.toggle_recording_requested.connect(self._toggle_recording)
        
        # Connect UI action signals
        self.ui_manager.toggle_recording.connect(self._toggle_recording)
        self.ui_manager.toggle_json_logging.connect(self._toggle_json_logging)
        self.ui_manager.toggle_csv_logging.connect(self._toggle_csv_logging)
        self.ui_manager.select_csv_path.connect(self._select_csv_path)
        self.ui_manager.switch_collector.connect(self._switch_collector)
        self.ui_manager.scan_controllers.connect(self._scan_controllers)
        self.ui_manager.toggle_edit_mode.connect(self._toggle_edit_mode)
        self.ui_manager.update_tracking_mode.connect(self._update_tracking_modes)
        self.ui_manager.set_mouse_tracking_mode.connect(self._set_mouse_tracking_mode)
        self.ui_manager.apply_mouse_settings.connect(self._apply_mouse_settings)
        self.ui_manager.toggle_fullscreen.connect(self._toggle_fullscreen)
        self.ui_manager.mouse_button_toggled.connect(self._on_mouse_button_toggled)
        self.ui_manager.capture_scroll_changed.connect(self._on_capture_scroll_changed)
        
        # Connect visualizer signals
        self.visualizer_manager.key_clicked.connect(self._on_key_clicked)
        self.visualizer_manager.button_toggled.connect(self._on_button_toggled)
        
        # Connect logging signals
        self.logging_manager.status_message.connect(self.ui_manager.log_status)

    def _setup_components(self) -> None:
        """Set up and initialize all application components."""
        # Get screen dimensions for mouse tracking
        screen_rect = QApplication.desktop().screenGeometry()
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()
        
        # Create visualizer manager with parent
        self.visualizer_manager = VisualizerManager(self)
        
        # Get visualizer instances
        keyboard_viz = self.visualizer_manager.get_keyboard_visualizer()
        mouse_viz = self.visualizer_manager.get_mouse_visualizer()
        mouse_buttons = self.visualizer_manager.get_mouse_buttons_selector()
        
        # Add visualizers to UI layout
        self.ui_manager.set_visualizers(keyboard_viz, mouse_viz, mouse_buttons)
        
        # Register visualizers with collector manager
        self.collector_manager.register_visualizer(keyboard_viz)
        self.collector_manager.register_visualizer(mouse_viz)
        self.collector_manager.register_visualizer(mouse_buttons)
        
        # Set tracked keys
        self.collector_manager.set_tracked_keys(self.tracked_keys)
        self.visualizer_manager.set_tracked_keys(self.tracked_keys)
        
        # Set up keyboard mouse collector with screen dimensions
        keyboard_mouse_collector = self.collector_manager.get_collector("keyboard_mouse")
        if keyboard_mouse_collector:
            if hasattr(keyboard_mouse_collector, "set_screen_dimensions"):
                keyboard_mouse_collector.set_screen_dimensions(screen_width, screen_height)
            
            if hasattr(keyboard_mouse_collector, "set_joystick_sensitivity"):
                keyboard_mouse_collector.set_joystick_sensitivity(0.1)
            
            # Initialize default mouse tracking mode
            self._set_mouse_tracking_mode("axis")
        
        # Start periodic UI updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_active_keys_display)
        self.update_timer.start(100)

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts for the application."""
        # F9 key for toggling recording
        f9_shortcut = QAction("Toggle Recording", self)
        f9_shortcut.setShortcut("F9")
        f9_shortcut.triggered.connect(self._toggle_recording)
        self.addAction(f9_shortcut)

        # F11 for fullscreen
        f11_shortcut = QAction("Fullscreen", self)
        f11_shortcut.setShortcut("F11")
        f11_shortcut.triggered.connect(self._toggle_fullscreen)
        self.addAction(f11_shortcut)

        # Escape to exit fullscreen
        esc_shortcut = QAction("Exit Fullscreen", self)
        esc_shortcut.setShortcut("Esc")
        esc_shortcut.triggered.connect(self._exit_fullscreen)
        self.addAction(esc_shortcut)

    def _on_collector_event(self, event: InputData) -> None:
        """Handle events from the collector manager."""
        # Forward to event processor via signal to ensure thread safety
        self.event_received.emit(event)

    @pyqtSlot(object)
    def _on_event_received(self, event: InputData) -> None:
        """Process input events in the main thread."""
        # Update active keys display
        self._update_active_keys_display()
        
        # Get current collector type
        collector_type = self.collector_manager.get_current_collector_type()
        
        # Process the event using the event processor
        result = self.event_processor.process_event(event, collector_type)
        
        # Handle special toggle_recording event
        if event.event_type == "toggle_recording":
            if not self.f9_key_down:
                self._toggle_recording()
                self.f9_key_down = True
            return
            
        # Handle F9 key release
        if event.event_type == "key_release" and event.key == "Key.media_play_pause":
            self.f9_key_down = False
            return
        
        # Don't process further if we're not recording
        if not self.is_recording:
            return
        
        # Log the event if needed
        if result["should_log"]:
            # Display event in UI
            self.ui_manager.log_status(result["display_text"])
            
            # Log to files if enabled
            self.logging_manager.log_event(event, collector_type)

    def _toggle_recording(self) -> None:
        """Toggle recording state."""
        current_time = time.time()
        if self.last_toggle_time and (current_time - self.last_toggle_time) < 0.2:
            return  # Throttle rapid toggles

        self.last_toggle_time = current_time
        
        if self.is_recording:
            # Stop recording
            self.collector_manager.stop_capture()
            self.is_recording = False
            
            # Update UI
            self.ui_manager.update_recording_state(False)
            self.ui_manager.log_status("Recording stopped", self.warning_color)
            
            # Stop logging
            self.logging_manager.stop_recording()
            
        else:
            # Start recording
            # Initialize CSV file if needed
            if self.logging_manager.log_to_csv:
                # Get current tracking mode
                tracking_mode = self.ui_manager.get_tracking_mode()
                direction_only = self.ui_manager.is_direction_only_mode()
                
                # Create headers for CSV based on tracked keys and mode
                self.logging_manager.initialize_csv_file(
                    None,  # Let CSV logger generate headers
                    self.tracked_keys,
                    tracking_mode,
                    direction_only
                )
            
            # Start capturing
            self.collector_manager.start_capture()
            self.is_recording = True
            
            # Update UI
            self.ui_manager.update_recording_state(True)
            self.ui_manager.log_status("Recording started", self.success_color)
            
            # Start logging
            self.logging_manager.start_recording()
        
        # Force update the UI
        QApplication.processEvents()

    def _toggle_json_logging(self, enabled: bool) -> None:
        """Toggle JSON logging."""
        self.logging_manager.set_json_logging(enabled)
    
    def _toggle_csv_logging(self, enabled: bool) -> None:
        """Toggle CSV logging."""
        if enabled:
            # First time enabling, prompt for CSV path
            if not self.logging_manager.csv_logger.filepath:
                self._select_csv_path()
        
        self.logging_manager.set_csv_logging(enabled)

    def _select_csv_path(self) -> None:
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
            self.logging_manager.csv_logger.set_filepath(csv_path)
            self.ui_manager.set_csv_path(csv_path)
            self.ui_manager.log_status(f"CSV file path set: {csv_path}")

    def _toggle_edit_mode(self) -> None:
        """Toggle key editing mode."""
        # Don't allow edit mode when recording
        if self.is_recording:
            self.ui_manager.log_status("Cannot edit keys while recording", self.warning_color)
            return
        
        self.edit_keys_mode = not self.edit_keys_mode
        
        # Actualizar el estado del botón visualmente
        edit_keys_button = self.ui_manager.components.get('edit_keys_button')
        if (edit_keys_button):
            edit_keys_button.setChecked(self.edit_keys_mode)
            if self.edit_keys_mode:
                edit_keys_button.setText("Finish Editing")
                edit_keys_button.setStyleSheet(f"background-color: {self.success_color}; color: white;")
            else:
                edit_keys_button.setText("Edit Keys") 
                edit_keys_button.setStyleSheet(f"background-color: {self.accent_color}; color: white;")
        
        # Activar el modo de edición en los visualizadores
        # Importante: Hacer log antes para depuración
        print(f"Setting edit mode: {self.edit_keys_mode}")
        self.visualizer_manager.set_edit_mode(self.edit_keys_mode)
        
        # Mensaje UI
        if self.edit_keys_mode:
            self.ui_manager.log_status(
                "Click on keys or mouse buttons to add/remove them from tracking",
                self.success_color,
            )
        else:
            self.ui_manager.log_status("Key editing finished", self.accent_color)

    def _on_key_clicked(self, key: str) -> None:
        """Handle clicks on keyboard keys."""
        # Depuración mejorada
        print(f"Key clicked: {key}, edit_mode: {self.edit_keys_mode}")
        
        if not self.edit_keys_mode:
            print("Ignoring key click - not in edit mode")
            return
        
        # Normalize special keys
        if key.lower() == "space":
            key = "Key.space"
        elif key.lower() == "shift":
            key = "Key.shift"
        elif key.lower() == "f9":
            key = "Key.media_play_pause"
            
        # Check if key is already tracked
        key_in_tracked = any(tracked.lower() == key.lower() for tracked in self.tracked_keys)
        print(f"Key {key} is {'already' if key_in_tracked else 'not'} tracked")
        
        # Toggle key in tracked_keys list
        if key_in_tracked:
            # Don't allow removing F9/media_play_pause
            if key.lower() == "key.media_play_pause".lower():
                self.ui_manager.log_status(
                    "Cannot remove F9/media_play_pause key", 
                    self.warning_color
                )
                return
                
            # Remove key
            for tracked in self.tracked_keys.copy():
                if tracked.lower() == key.lower():
                    self.tracked_keys.remove(tracked)
                    print(f"Removed key: {key} from tracked keys")
                    break
            self.ui_manager.log_status(f"Removed key: {key}")
        else:
            # Add key
            self.tracked_keys.append(key)
            print(f"Added key: {key} to tracked keys")
            self.ui_manager.log_status(f"Added key: {key}")
            
        # Update key list and visualization
        print(f"Updating tracked keys: {self.tracked_keys}")
        self.collector_manager.set_tracked_keys(self.tracked_keys)
        self.visualizer_manager.set_tracked_keys(self.tracked_keys)

    def _on_button_toggled(self, button_id: str, is_tracked: bool) -> None:
        """Handle toggling of mouse buttons in the selector."""
        if not self.edit_keys_mode:
            return
            
        # Handle special case for scroll
        if button_id == "Button.scroll":
            self.ui_manager.set_scroll_tracking(is_tracked)
            self.ui_manager.log_status(
                f"Scroll tracking {'enabled' if is_tracked else 'disabled'}",
                self.success_color if is_tracked else self.warning_color,
            )
            return
            
        # For other buttons, update tracked keys list
        if is_tracked:
            # Add button if not already in list
            if button_id not in self.tracked_keys:
                self.tracked_keys.append(button_id)
                self.ui_manager.log_status(f"Added tracking for {button_id}", self.success_color)
        else:
            # Remove button if in list
            if button_id in self.tracked_keys:
                self.tracked_keys.remove(button_id)
                self.ui_manager.log_status(f"Removed tracking for {button_id}", self.warning_color)
                
        # Update collector and visualization
        self.collector_manager.set_tracked_keys(self.tracked_keys)
        self.visualizer_manager.set_tracked_keys(self.tracked_keys)

    def _on_mouse_button_toggled(self, button_id: str, is_tracked: bool) -> None:
        """Handle toggling of mouse buttons from UI."""
        self._on_button_toggled(button_id, is_tracked)

    def _on_capture_scroll_changed(self, enabled: bool) -> None:
        """Handle scroll tracking toggle from UI."""
        self.visualizer_manager.set_scroll_tracking(enabled)
        
        # Update tracking status if this represents a change in button tracking
        button_id = "Button.scroll"
        is_tracked = button_id in self.tracked_keys
        
        # Ensure scroll button state is consistent with checkbox
        if enabled and not is_tracked:
            self.tracked_keys.append(button_id)
            self.collector_manager.set_tracked_keys(self.tracked_keys)
        elif not enabled and is_tracked:
            self.tracked_keys.remove(button_id)
            self.collector_manager.set_tracked_keys(self.tracked_keys)
            
        # Update visualizers
        self.visualizer_manager.set_tracked_keys(self.tracked_keys)

    def _update_tracking_modes(self) -> None:
        """Update available tracking modes based on Direction Only checkbox."""
        direction_only = self.ui_manager.is_direction_only_mode()
        current_mode = self.ui_manager.get_tracking_mode()
        
        # Update UI with appropriate modes
        if direction_only:
            valid_modes = ["axis", "angle"]
            default_mode = "axis"
        else:
            valid_modes = ["joystick", "delta", "angle"]
            default_mode = "joystick"
            
        self.ui_manager.update_tracking_modes(valid_modes, current_mode, default_mode)
        
        # Apply the currently selected mode
        self._set_mouse_tracking_mode(self.ui_manager.get_tracking_mode())

    def _set_mouse_tracking_mode(self, mode: str) -> None:
        """Change the mouse tracking mode."""
        # Don't allow changing mode when recording
        if self.is_recording:
            self.ui_manager.log_status("Cannot change tracking mode while recording", self.warning_color)
            return
            
        direction_only = self.ui_manager.is_direction_only_mode()
        angle_grouping = self.ui_manager.get_angle_grouping()
        
        # Update collector's tracking mode
        collector = self.collector_manager.get_current_collector()
        if collector and hasattr(collector, "set_mouse_tracking_mode"):
            collector.set_mouse_tracking_mode(mode, direction_only, angle_grouping)
            self.ui_manager.log_status(f"Mouse tracking mode set to: {mode}", self.accent_color)
            
            # Additional info messages
            if mode == "axis":
                self.ui_manager.log_status(
                    "Axis mode shows membership values for N, S, E, W directions", 
                    "#AAAAAA"
                )
            elif mode == "angle" and direction_only:
                self.ui_manager.log_status(
                    f"Angle mode using {angle_grouping}° grouping ({360 // angle_grouping} values)",
                    "#AAAAAA",
                )

    def _apply_mouse_settings(self) -> None:
        """Apply mouse settings to the current collector."""
        collector = self.collector_manager.get_current_collector()
        if not collector:
            return
            
        # Apply delta smoothing
        smoothing = self.ui_manager.get_delta_smoothing() / 100.0
        if hasattr(collector, "set_delta_smoothing"):
            collector.set_delta_smoothing(smoothing)
            self.ui_manager.log_status(f"Delta smoothing set to: {smoothing:.2f}")
            
        # Apply joystick sensitivity
        sensitivity = self.ui_manager.get_joystick_sensitivity() / 100.0
        if hasattr(collector, "set_joystick_sensitivity"):
            collector.set_joystick_sensitivity(sensitivity)
            self.ui_manager.log_status(f"Joystick sensitivity set to: {sensitivity:.2f}")
            
        # Apply angle grouping
        angle_grouping = self.ui_manager.get_angle_grouping()
        if hasattr(collector, "set_angle_grouping"):
            collector.set_angle_grouping(angle_grouping)
            self.ui_manager.log_status(
                f"Angle grouping set to: {angle_grouping}° ({360 // angle_grouping} values)"
            )
            
        # Log scroll capture status
        self.ui_manager.log_status(
            f"Scroll data capture: {'Enabled' if self.ui_manager.is_scroll_tracking_enabled() else 'Disabled'}"
        )
        
        # Re-apply current tracking mode to ensure all settings are updated
        self._set_mouse_tracking_mode(self.ui_manager.get_tracking_mode())

    def _scan_controllers(self) -> None:
        """Scan for SDL controllers and show a selection dialog."""
        ps4_collector = self.collector_manager.get_collector("ps4_controller")
        if not ps4_collector:
            QMessageBox.warning(
                self,
                "SDL Not Available",
                "SDL2 is not available. Make sure pysdl2 and pysdl2-dll are installed."
            )
            return
            
        # Show scanning message
        self.ui_manager.log_status("Scanning for controllers...", self.warning_color)
        QApplication.processEvents()
        
        try:
            # Scan for controllers
            controllers = ps4_collector.scan_controllers()
            
            if not controllers:
                QMessageBox.information(
                    self,
                    "No Controllers Found",
                    "No SDL game controllers were detected.\n\n"
                    "Make sure your controller is connected and properly recognized by your system."
                )
                self.ui_manager.log_status("No controllers found", self.error_color)
                
                # Fall back to keyboard/mouse mode if we're currently trying to use PS4
                if self.collector_manager.get_current_collector_type() == "ps4_controller":
                    self.ui_manager.log_status(
                        "Falling back to Keyboard & Mouse mode", 
                        self.warning_color
                    )
                    self._force_keyboard_mouse_mode()
                return
                
            # Handle controller selection
            self._handle_controller_selection(controllers, ps4_collector)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            QMessageBox.critical(
                self,
                "Error Scanning Controllers",
                f"An error occurred while scanning for controllers: {str(e)}"
            )
            self.ui_manager.log_status(f"Controller scan error: {str(e)}", self.error_color)
            
            # Fall back to keyboard/mouse mode on error
            if self.collector_manager.get_current_collector_type() == "ps4_controller":
                self.ui_manager.log_status(
                    "Falling back to Keyboard & Mouse mode",
                    self.warning_color
                )
                self._force_keyboard_mouse_mode()

    def _handle_controller_selection(self, controllers, ps4_collector) -> None:
        """Handle controller selection after scanning."""
        # If we have only one controller, connect to it directly
        if len(controllers) == 1:
            controller = controllers[0]
            success = ps4_collector.connect_to_controller(controller["index"])
            if success:
                self.ui_manager.log_status(
                    f"Connected to: {controller['name']}", 
                    self.success_color
                )
                # Switch to PS4 controller mode if not already there
                self._select_collector_by_type("ps4_controller")
            else:
                self.ui_manager.log_status(
                    f"Failed to connect to: {controller['name']}", 
                    self.error_color
                )
                # Fall back to keyboard/mouse mode if connection failed
                if self.collector_manager.get_current_collector_type() == "ps4_controller":
                    self._force_keyboard_mouse_mode()
            return
        
        # If we have multiple controllers, show a selection dialog
        self._show_controller_selection_dialog(controllers, ps4_collector)

    def _show_controller_selection_dialog(self, controllers, ps4_collector) -> None:
        """Show dialog for selecting between multiple controllers."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QListWidgetItem, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Controller")
        layout = QVBoxLayout()
        
        # Instructions label
        layout.addWidget(QLabel("Select a controller to use:"))
        
        # List of controllers
        controller_list = QListWidget()
        for controller in controllers:
            item_text = f"{controller['name']} {'(PS4)' if controller['is_ps4'] else ''}"
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
                self.ui_manager.log_status(
                    f"Connected to: {controller_name}", 
                    self.success_color
                )
                
                # Switch to PS4 controller mode
                self._select_collector_by_type("ps4_controller")
            else:
                self.ui_manager.log_status(
                    "Failed to connect to controller", 
                    self.error_color
                )
                # Fall back to keyboard/mouse mode if connection failed
                if self.collector_manager.get_current_collector_type() == "ps4_controller":
                    self._force_keyboard_mouse_mode()

    def _select_collector_by_type(self, collector_type: str) -> None:
        """Select a collector in the UI by its type."""
        self.ui_manager.select_collector_by_type(collector_type)

    def _switch_collector(self, collector_name: str) -> None:
        """Switch between input collectors."""
        # Stop current collector if recording
        if self.is_recording:
            self._toggle_recording()
            
        # Get collector type from UI
        collector_type = self.ui_manager.get_current_collector_data()
        if not collector_type:
            self.ui_manager.log_status(f"Collector '{collector_name}' not found", self.error_color)
            return
            
        # Handle PS4 controller special case
        if collector_type == "ps4_controller":
            if not self._handle_ps4_controller_switch():
                return
                
        # Switch collector using manager
        success = self.collector_manager.set_current_collector(collector_type)
        
        if success:
            # Update UI based on collector capabilities
            self._update_ui_for_collector()
            
            # Log the change
            self.ui_manager.log_status(f"Switched to {collector_name} collector", self.accent_color)
        else:
            self.ui_manager.log_status(f"Failed to switch to {collector_name} collector", self.error_color)
            # Revert to keyboard/mouse
            self._force_keyboard_mouse_mode()

    def _handle_ps4_controller_switch(self) -> bool:
        """Handle special case for switching to PS4 controller."""
        # Check if PS4 controller is available
        if not HAVE_PS4_SUPPORT:
            QMessageBox.warning(
                self,
                "PS4 Controller Not Available",
                "PySDL2 is not installed or could not be initialized.\n\n"
                "Install with: pip install pysdl2 pysdl2-dll",
            )
            
            # Revert to keyboard/mouse
            self._force_keyboard_mouse_mode()
            return False
            
        # Check if we have an active controller connection
        ps4_collector = self.collector_manager.get_collector("ps4_controller")
        if ps4_collector and not ps4_collector.controller:
            response = QMessageBox.question(
                self,
                "No Controller Connected",
                "No controller is currently connected. Would you like to scan for controllers now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            
            if response == QMessageBox.Yes:
                # Explicitly scan for controllers
                self._scan_controllers()
                # If we still don't have a controller after scanning, revert to keyboard/mouse
                if not ps4_collector.controller:
                    self.ui_manager.log_status(
                        "No controller found, reverting to Keyboard & Mouse", 
                        self.warning_color
                    )
                    self._force_keyboard_mouse_mode()
                    return False
            else:
                # User declined to scan, revert to keyboard/mouse
                self.ui_manager.log_status(
                    "Controller scan declined, staying with Keyboard & Mouse",
                    self.warning_color,
                )
                self._force_keyboard_mouse_mode()
                return False
                
        return True

    def _force_keyboard_mouse_mode(self) -> None:
        """Force switch to keyboard/mouse mode safely."""
        print("Forcing switch to keyboard/mouse mode")
        
        # Use collector manager to switch collectors
        success = self.collector_manager.set_current_collector("keyboard_mouse")
        
        if success:
            # Update UI state - use blockSignals to prevent triggering the switch event
            collector_selector = self.ui_manager.components.get('collector_selector')
            if collector_selector:
                collector_selector.blockSignals(True)
                self.ui_manager.select_collector_by_type("keyboard_mouse")
                collector_selector.blockSignals(False)
            
            # Update UI based on collector capabilities
            self._update_ui_for_collector()
            
            # Log the change
            self.ui_manager.log_status("Switched to Keyboard & Mouse mode", self.warning_color)
        else:
            self.ui_manager.log_status("Failed to switch to keyboard/mouse mode", self.error_color)
            
        # Process pending events to ensure UI updates
        QApplication.processEvents()

    def _update_ui_for_collector(self) -> None:
        """Update UI elements based on current collector capabilities."""
        collector_type = self.collector_manager.get_current_collector_type()
        capabilities = self.collector_manager.get_current_collector_capabilities()
        
        # Update UI based on collector capabilities
        self.ui_manager.update_ui_for_collector(collector_type, capabilities)
        
        # Update visualizers based on collector type and capabilities
        self.visualizer_manager.update_for_collector(collector_type, capabilities)

    def _update_active_keys_display(self) -> None:
        """Update the active keys display."""
        active_keys = self.collector_manager.get_active_keys()
        self.ui_manager.update_active_keys_display(active_keys)

    def _toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.showFullScreen()
        else:
            self.showNormal()
            
        # Force update visualizers after size change
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
        self.visualizer_manager.force_update()

    def run(self) -> None:
        """Run the application."""
        self.show()

    def closeEvent(self, event) -> None:
        """Handle application close event."""
        # Stop collectors
        if self.is_recording:
            self.collector_manager.stop_capture()
            
        # Close log files
        self.logging_manager.close_all()
        
        # Accept the close event
        event.accept()


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
