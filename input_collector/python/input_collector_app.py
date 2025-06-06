"""
Input collector application module.

This module provides the main application for collecting, visualizing, and
logging keyboard and mouse inputs in real-time with a graphical user interface using PyQt5.
"""

import sys
from typing import List, Dict

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QAction

from .app import AppCoordinator
from .collectors import CollectorManager
from .interaction_api import InputCollectorAPI
from .logging import LoggingManager
from .processing import EventProcessor
# Import new modular components
from .ui import UIManager

# Import PS4 controller with fallback
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

    This class integrates the different components (collector manager, UI manager,
    logging manager, etc.) into a cohesive application.
    """

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
        self.is_fullscreen = False
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
            "Button.right",
        ]

        # Set window properties
        self.setWindowTitle("Input Collector")
        self.setGeometry(100, 100, 1200, 700)
        self.setMinimumSize(1050, 650)

        # Initialize and set up components
        print("Initializing application components...")
        self._initialize_components()

        # Connect signals between components
        print("Connecting component signals...")
        self._connect_signals()

        # Initialize application state
        print("Initializing application state...")
        self._initialize_state()

        # Setup keyboard shortcuts
        print("Setting up shortcuts...")
        self._setup_shortcuts()

    def _initialize_components(self) -> None:
        """Initialize all application components."""
        # Create collector manager first since others depend on it
        print("Creating CollectorManager...")
        self.collector_manager = self._create_collector_manager()

        # Create processing components
        print("Creating EventProcessor...")
        self.event_processor = EventProcessor()

        # Create logging manager
        print("Creating LoggingManager...")
        self.logging_manager = LoggingManager()

        # Create UI manager with this window as parent
        print("Creating UIManager...")
        self.ui_manager = UIManager(self)

        # Create visualizer manager with this window as parent
        print("Creating VisualizerManager...")
        self.visualizer_manager = self._create_visualizer_manager()

        # Create app coordinator last since it depends on all other components
        print("Creating AppCoordinator...")
        self.app_coordinator = AppCoordinator(
            self.collector_manager,
            self.ui_manager,
            self.logging_manager,
            self.event_processor,
        )

        # Initialize interaction API with application components
        print("Initializing Interaction API...")
        InputCollectorAPI.initialize(
            self.app_coordinator,
            self.ui_manager,
            self.logging_manager,
            self.collector_manager,
            self.event_processor,
        )

        # Add state variables for PS4 edit modes
        self._ps4_overlay_edit_mode = False

    def _create_collector_manager(self) -> CollectorManager:
        """Create and initialize the collector manager."""
        # Create collector manager
        collector_manager = CollectorManager()

        # Get screen dimensions for optimized mouse tracking
        screen_rect = QApplication.desktop().screenGeometry()
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()

        # Configure collectors with screen dimensions
        keyboard_mouse_collector = collector_manager.get_collector("keyboard_mouse")
        if keyboard_mouse_collector:
            if hasattr(keyboard_mouse_collector, "set_screen_dimensions"):
                keyboard_mouse_collector.set_screen_dimensions(
                    screen_width, screen_height
                )

            if hasattr(keyboard_mouse_collector, "set_joystick_sensitivity"):
                keyboard_mouse_collector.set_joystick_sensitivity(
                    0.1
                )  # Default sensitivity

        return collector_manager

    def _create_visualizer_manager(self) -> "VisualizerManager":
        """Create and initialize the visualizer manager."""
        from .ui import VisualizerManager

        # Create visualizer manager
        visualizer_manager = VisualizerManager(self)

        # Get visualizer components
        keyboard_viz = visualizer_manager.get_keyboard_visualizer()
        mouse_viz = visualizer_manager.get_mouse_visualizer()
        mouse_buttons = visualizer_manager.get_mouse_buttons_selector()
        ps4_controller_viz = visualizer_manager.get_ps4_controller_visualizer()

        # Add visualizers to UI layout
        self.ui_manager.set_visualizers(
            keyboard_viz, mouse_viz, mouse_buttons, ps4_controller_viz
        )

        # Register visualizers with collector manager
        self.collector_manager.register_visualizer(keyboard_viz)
        self.collector_manager.register_visualizer(mouse_viz)
        self.collector_manager.register_visualizer(mouse_buttons)
        self.collector_manager.register_visualizer(ps4_controller_viz)

        return visualizer_manager

    def _connect_signals(self) -> None:
        """Connect signals between components."""
        # Connect UI action signals to coordinator
        self.ui_manager.toggle_recording.connect(self.app_coordinator.toggle_recording)
        self.ui_manager.toggle_json_logging.connect(self._toggle_json_logging)
        self.ui_manager.toggle_csv_logging.connect(self._toggle_csv_logging)
        self.ui_manager.select_csv_path.connect(self._select_csv_path)
        self.ui_manager.switch_collector.connect(self._switch_collector)
        self.ui_manager.scan_controllers.connect(self._scan_controllers)
        self.ui_manager.toggle_edit_mode.connect(self.app_coordinator.toggle_edit_mode)
        self.ui_manager.update_tracking_mode.connect(self._update_tracking_modes)
        self.ui_manager.set_mouse_tracking_mode.connect(
            self.app_coordinator.set_mouse_tracking_mode
        )
        self.ui_manager.apply_mouse_settings.connect(
            self.app_coordinator.apply_mouse_settings
        )
        self.ui_manager.toggle_fullscreen.connect(self._toggle_fullscreen)
        self.ui_manager.mouse_button_toggled.connect(self._on_mouse_button_toggled)

        # Connect the new PS4 visualization mode toggle
        self.ui_manager.toggle_ps4_viz_mode.connect(self._toggle_ps4_viz_mode)

        # Connect PS4 overlay edit button
        self.ui_manager.toggle_ps4_overlay_edit.connect(self._toggle_ps4_overlay_edit)

        # Connect discard signal for PS4 overlay edits
        self.ui_manager.toggle_ps4_overlay_discard.connect(
            self._discard_ps4_overlay_edits
        )

        # Connect visualizer signals to coordinator
        self.visualizer_manager.key_clicked.connect(
            self.app_coordinator.handle_key_edit
        )
        self.visualizer_manager.button_toggled.connect(
            self.app_coordinator.handle_button_edit
        )

        # Connect coordinator signals to UI
        self.app_coordinator.edit_mode_toggled.connect(self._on_edit_mode_toggled)
        self.app_coordinator.recording_started.connect(self._on_recording_started)
        self.app_coordinator.recording_stopped.connect(self._on_recording_stopped)
        self.app_coordinator.collector_switched.connect(self._on_collector_switched)

        # Connect the new tracked_keys_changed signal to update visualizers
        self.app_coordinator.tracked_keys_changed.connect(self._on_tracked_keys_changed)

        # Connect logging signals
        self.logging_manager.status_message.connect(self.ui_manager.log_status)

        # Start periodic UI updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_active_keys_display)
        self.update_timer.start(100)

    def _initialize_state(self) -> None:
        """Initialize the application state."""
        # Initialize app coordinator with tracked keys
        self.app_coordinator.initialize(self.tracked_keys)

        # Update visualizer tracked keys
        self.visualizer_manager.set_tracked_keys(self.tracked_keys)

        # Set default mouse tracking mode with direction_only enabled and proper angle grouping
        keyboard_mouse_collector = self.collector_manager.get_collector(
            "keyboard_mouse"
        )
        if keyboard_mouse_collector and hasattr(
            keyboard_mouse_collector, "set_mouse_tracking_mode"
        ):
            # Pass True for direction_only and use default angle grouping (10 degrees)
            keyboard_mouse_collector.set_mouse_tracking_mode("axis", True, 10)

            # Don't try to update UI components here, it's too early
            # Instead, delay UI initialization to _initialize_ui

        # Use a timer for UI initialization to ensure UI is ready
        QTimer.singleShot(100, self._initialize_ui)

    def _initialize_ui(self) -> None:
        """Initialize the UI with collectors and update visuals."""
        # Get available collectors
        collectors = self.collector_manager.get_available_collectors()
        print(f"Available collectors: {collectors}")

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

        # Now that UI is initialized, synchronize mouse settings
        QTimer.singleShot(100, self._sync_mouse_settings)

    def _sync_mouse_settings(self) -> None:
        """Synchronize UI settings with initial mouse configuration."""
        try:
            # Make sure the UI elements exist before trying to set values
            if hasattr(self.ui_manager, "set_direction_only_mode"):
                self.ui_manager.set_direction_only_mode(True)

            if hasattr(self.ui_manager, "set_tracking_mode"):
                self.ui_manager.set_tracking_mode("axis")

            # Log the initial setup
            self.ui_manager.log_status(
                "Mouse tracking mode: Axis (Direction-only)", "accent"
            )
        except Exception as e:
            # Don't crash if there's an error, just log it
            print(f"Error synchronizing mouse settings: {e}")

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts for the application."""
        # F9 key for toggling recording
        f9_shortcut = QAction("Toggle Recording", self)
        f9_shortcut.setShortcut("F9")
        f9_shortcut.triggered.connect(self.app_coordinator.toggle_recording)
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
            options=options,
        )

        if csv_path:
            self.logging_manager.csv_logger.set_filepath(csv_path)
            self.ui_manager.set_csv_path(csv_path)
            self.ui_manager.log_status(f"CSV file path set: {csv_path}")

    def _toggle_ps4_viz_mode(self, mode: str) -> None:
        """
        Toggle between PS4 controller visualization modes.

        Args:
            mode: The visualization mode to use ("Image" or "Drawn")
        """
        ps4_visualizer = self.visualizer_manager.get_ps4_controller_visualizer()
        if ps4_visualizer:
            use_image_mode = mode.lower() == "image"

            # If switching to drawn mode while in overlay edit mode, disable edit mode first
            if not use_image_mode and self._ps4_overlay_edit_mode:
                self._toggle_ps4_overlay_edit(False)

            # Toggle image mode in the visualizer
            if hasattr(ps4_visualizer, "toggle_image_mode"):
                current_mode = ps4_visualizer.toggle_image_mode()

                # If the toggle didn't work as expected (e.g., images not loaded), update the UI
                if current_mode != use_image_mode:
                    # Block signals to prevent feedback loop
                    ps4_viz_mode_combo = self.ui_manager.components.get(
                        "ps4_viz_mode_combo"
                    )
                    if ps4_viz_mode_combo:
                        ps4_viz_mode_combo.blockSignals(True)
                        ps4_viz_mode_combo.setCurrentText("Drawn")
                        ps4_viz_mode_combo.blockSignals(False)

                        # Inform the user
                        self.ui_manager.log_status(
                            "Cannot use image mode - images not loaded",
                            self.warning_color,
                        )
                else:
                    # Log the mode change
                    self.ui_manager.log_status(
                        f"PS4 controller visualization mode set to: {mode}",
                        self.accent_color,
                    )

            # Update overlay edit button state - only enabled in image mode
            ps4_edit_overlays = self.ui_manager.components.get("ps4_edit_overlays")
            if ps4_edit_overlays:
                ps4_edit_overlays.setEnabled(use_image_mode)

                if use_image_mode:
                    ps4_edit_overlays.setStyleSheet("")  # Reset to default style
                else:
                    ps4_edit_overlays.setStyleSheet(
                        "background-color: #555555; color: #999999;"
                    )

    def _toggle_ps4_overlay_edit(self, enabled: bool) -> None:
        """
        Toggle PS4 controller overlay edit mode.

        Args:
            enabled: Whether overlay edit mode is enabled
        """
        try:
            # Print debug info
            print(
                f"InputCollectorApp: _toggle_ps4_overlay_edit({enabled}) - Current state: {self._ps4_overlay_edit_mode}"
            )

            # Can't edit overlays while recording
            if self.app_coordinator.is_recording and enabled:
                self.ui_manager.log_status(
                    "Cannot edit overlays while recording", self.warning_color
                )
                self.ui_manager.update_ps4_overlay_edit_state(False)
                return

            # Check if we're in image mode
            ps4_viz_mode_combo = self.ui_manager.components.get("ps4_viz_mode_combo")
            if ps4_viz_mode_combo and ps4_viz_mode_combo.currentText() != "Image":
                self.ui_manager.log_status(
                    "Overlay editing only available in Image mode", self.warning_color
                )
                self.ui_manager.update_ps4_overlay_edit_state(False)
                return

            # Update UI state first
            self.ui_manager.update_ps4_overlay_edit_state(enabled)

            # Get PS4 controller visualizer
            ps4_controller_viz = self.visualizer_manager.get_ps4_controller_visualizer()
            if not ps4_controller_viz:
                print("PS4 controller visualizer not found")
                self.ui_manager.log_status(
                    "PS4 visualizer not available", self.error_color
                )
                return

            # Always use set_edit_mode directly to maintain synchronized state
            ps4_controller_viz.set_edit_mode(enabled)

            # Update internal state to match
            self._ps4_overlay_edit_mode = enabled

            # Log status
            if enabled:
                self.ui_manager.log_status(
                    "PS4 overlay edit mode enabled - drag images to reposition",
                    self.success_color,
                )
            else:
                self.ui_manager.log_status(
                    "PS4 overlay edit mode disabled", self.accent_color
                )

            print(
                f"InputCollectorApp: Overlay edit mode complete, state: {self._ps4_overlay_edit_mode}"
            )

        except Exception as e:
            # Log error and recover safely
            print(f"Error toggling PS4 overlay edit mode: {e}")
            import traceback

            traceback.print_exc()

            # Reset state in UI and app
            self.ui_manager.update_ps4_overlay_edit_state(False)
            self._ps4_overlay_edit_mode = False
            self.ui_manager.log_status(
                f"Error in overlay edit mode: {str(e)}", self.error_color
            )

            # Try to reset visualizer state
            try:
                ps4_controller_viz = (
                    self.visualizer_manager.get_ps4_controller_visualizer()
                )
                if ps4_controller_viz:
                    ps4_controller_viz.set_edit_mode(False)
            except:
                pass

    def _discard_ps4_overlay_edits(self) -> None:
        """
        Discard any unsaved overlay moves and exit edit mode without saving.
        """
        # Get the PS4 controller visualizer
        viz = self.visualizer_manager.get_ps4_controller_visualizer()
        if viz:
            # Prevent JSON save on exit
            viz._should_commit = False
            # Will restore snapshot internally
            viz.set_edit_mode(False)

        # Update application state
        self._ps4_overlay_edit_mode = False
        self.ui_manager.update_ps4_overlay_edit_state(False)
        self.ui_manager.log_status("PS4 overlay edits discarded", self.warning_color)

        # No scroll position capture or restore - let it behave like any other button

    def _on_recording_started(self) -> None:
        """Handle recording started event."""
        # Disable and grey out the edit keys button
        edit_keys_button = self.ui_manager.components.get("edit_keys_button")
        if edit_keys_button:
            # Set disabled style (grey background)
            edit_keys_button.setEnabled(False)
            edit_keys_button.setStyleSheet("background-color: #666666; color: #AAAAAA;")
            print("Edit keys button disabled and greyed out")

        # Also disable PS4 edit overlays button
        ps4_edit_overlays = self.ui_manager.components.get("ps4_edit_overlays")

        # If we were in overlay edit mode, turn it off
        if self._ps4_overlay_edit_mode:
            self._toggle_ps4_overlay_edit(False)

        # Disable the button
        if ps4_edit_overlays:
            ps4_edit_overlays.setEnabled(False)
            ps4_edit_overlays.setStyleSheet(
                "background-color: #666666; color: #AAAAAA;"
            )

    def _on_recording_stopped(self) -> None:
        """Handle recording stopped event."""
        # Re-enable and restore the edit keys button style
        edit_keys_button = self.ui_manager.components.get("edit_keys_button")
        if edit_keys_button:
            edit_keys_button.setEnabled(True)
            # Restore normal style (accent color)
            edit_keys_button.setStyleSheet(
                f"background-color: {self.accent_color}; color: white;"
            )
            print("Edit keys button re-enabled with normal style")

        # Re-enable PS4 edit overlays button if in image mode
        ps4_edit_overlays = self.ui_manager.components.get("ps4_edit_overlays")
        ps4_viz_mode_combo = self.ui_manager.components.get("ps4_viz_mode_combo")

        if ps4_edit_overlays and ps4_viz_mode_combo:
            # Only enable overlay editing in image mode
            is_image_mode = ps4_viz_mode_combo.currentText() == "Image"
            ps4_edit_overlays.setEnabled(is_image_mode)

            if is_image_mode:
                ps4_edit_overlays.setStyleSheet(
                    "background-color: #007ACC; color: white;"
                )
            else:
                ps4_edit_overlays.setStyleSheet(
                    "background-color: #555555; color: #999999;"
                )

    def _on_edit_mode_toggled(self, enabled: bool) -> None:
        """Handle edit mode toggle."""
        try:
            # Debug logs to trace the issue
            print(f"Edit mode toggled: {enabled}")

            # Update visualizer manager state
            self.visualizer_manager.set_edit_mode(enabled)

            # Update UI button state - Edit Keys button
            edit_keys_button = self.ui_manager.components.get("edit_keys_button")
            if edit_keys_button:
                edit_keys_button.setChecked(enabled)

                # Update button appearance
                if enabled:
                    edit_keys_button.setText("Finish Editing")
                    edit_keys_button.setStyleSheet(
                        f"background-color: {self.success_color}; color: white;"
                    )
                else:
                    edit_keys_button.setText("Edit Keys")
                    edit_keys_button.setStyleSheet(
                        f"background-color: {self.accent_color}; color: white;"
                    )

            # Update Record button state - disable when in edit mode
            record_button = self.ui_manager.components.get("record_button")
            if record_button:
                # When editing keys, disable recording
                record_button.setEnabled(not enabled)

                # Update button style based on state
                if enabled:  # Edit mode enabled - disable Record button
                    record_button.setStyleSheet(
                        "background-color: #666666; color: #AAAAAA;"
                    )
                else:  # Edit mode disabled - restore original record button color
                    record_button.setStyleSheet(
                        "background-color: #AA3333; color: white;"
                    )

        except Exception as e:
            print(f"Error in edit mode toggle handler: {e}")
            import traceback

            traceback.print_exc()

    def _switch_collector(self, collector_name: str) -> None:
        """Switch between input collectors."""
        # Get collector type from UI
        collector_type = self.ui_manager.get_current_collector_data()
        if not collector_type:
            self.ui_manager.log_status(
                f"Collector '{collector_name}' not found", self.error_color
            )
            return

        # Handle PS4 controller special case
        if collector_type == "ps4_controller":
            if not self._handle_ps4_controller_switch():
                return

        # Use coordinator to switch collector
        self.app_coordinator.switch_collector(collector_type)

    def _on_collector_switched(self, collector_type: str, capabilities: Dict) -> None:
        """Handle collector switch event."""
        # Update UI based on collector capabilities
        self._update_ui_for_collector()

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

        try:
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
                            self.warning_color,
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
        except Exception as e:
            self.ui_manager.log_status(
                f"Error checking PS4 controller: {e}", self.error_color
            )
            import traceback

            traceback.print_exc()
            self._force_keyboard_mouse_mode()
            return False

        return True

    def _scan_controllers(self) -> None:
        """Scan for SDL controllers and show a selection dialog."""
        ps4_collector = self.collector_manager.get_collector("ps4_controller")
        if not ps4_collector:
            QMessageBox.warning(
                self,
                "SDL Not Available",
                "SDL2 is not available. Make sure pysdl2 and pysdl2-dll are installed.",
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
                    "Make sure your controller is connected and properly recognized by your system.",
                )
                self.ui_manager.log_status("No controllers found", self.error_color)

                # Fall back to keyboard/mouse mode if we're currently trying to use PS4
                if (
                    self.collector_manager.get_current_collector_type()
                    == "ps4_controller"
                ):
                    self.ui_manager.log_status(
                        "Falling back to Keyboard & Mouse mode", self.warning_color
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
                f"An error occurred while scanning for controllers: {str(e)}",
            )
            self.ui_manager.log_status(
                f"Controller scan error: {str(e)}", self.error_color
            )

            # Fall back to keyboard/mouse mode on error
            if self.collector_manager.get_current_collector_type() == "ps4_controller":
                self._force_keyboard_mouse_mode()

    def _handle_controller_selection(self, controllers, ps4_collector) -> None:
        """Handle controller selection after scanning."""
        # If we have only one controller, connect to it directly
        if len(controllers) == 1:
            controller = controllers[0]
            success = ps4_collector.connect_to_controller(controller["index"])
            if success:
                self.ui_manager.log_status(
                    f"Connected to: {controller['name']}", self.success_color
                )
                # Switch to PS4 controller mode if not already there
                self._select_collector_by_type("ps4_controller")
            else:
                self.ui_manager.log_status(
                    f"Failed to connect to: {controller['name']}", self.error_color
                )
                # Fall back to keyboard/mouse mode if connection failed
                if (
                    self.collector_manager.get_current_collector_type()
                    == "ps4_controller"
                ):
                    self._force_keyboard_mouse_mode()
            return

        # If we have multiple controllers, show a selection dialog
        self._show_controller_selection_dialog(controllers, ps4_collector)

    def _show_controller_selection_dialog(self, controllers, ps4_collector) -> None:
        """Show dialog for selecting between multiple controllers."""
        from PyQt5.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QListWidget,
            QDialogButtonBox,
            QListWidgetItem,
            QLabel,
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
                self.ui_manager.log_status(
                    f"Connected to: {controller_name}", self.success_color
                )

                # Switch to PS4 controller mode
                self._select_collector_by_type("ps4_controller")
            else:
                self.ui_manager.log_status(
                    "Failed to connect to controller", self.error_color
                )
                # Fall back to keyboard/mouse mode if connection failed
                if (
                    self.collector_manager.get_current_collector_type()
                    == "ps4_controller"
                ):
                    self._force_keyboard_mouse_mode()

    def _select_collector_by_type(self, collector_type: str) -> None:
        """Select a collector in the UI by its type."""
        self.ui_manager.select_collector_by_type(collector_type)

    def _force_keyboard_mouse_mode(self) -> None:
        """Force switch to keyboard/mouse mode safely."""
        # Use app coordinator to switch collector
        self.app_coordinator.switch_collector("keyboard_mouse")

        # Update UI state - use blockSignals to prevent triggering the switch event
        self.ui_manager.select_collector_by_type("keyboard_mouse")

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
        self.app_coordinator.set_mouse_tracking_mode(
            self.ui_manager.get_tracking_mode()
        )

    def _on_mouse_button_toggled(self, button_id: str, is_tracked: bool) -> None:
        """Handle toggling of mouse buttons from UI."""
        self.app_coordinator.handle_button_edit(button_id, is_tracked)

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

    def _on_tracked_keys_changed(self, tracked_keys: List[str]) -> None:
        """
        Handle changes to tracked keys list.

        Args:
            tracked_keys: The updated list of tracked keys
        """
        # Update visualizers with new tracked keys
        print(f"Updating visualizers with tracked keys: {tracked_keys}")
        self.visualizer_manager.set_tracked_keys(tracked_keys)

        # Force update to refresh the visualization
        self.visualizer_manager.force_update()

    # Add a new method to handle the PS4 visualization mode toggle
    def _toggle_ps4_viz_mode(self, mode: str) -> None:
        """
        Toggle between PS4 controller visualization modes.

        Args:
            mode: The visualization mode to use ("Image" or "Drawn")
        """
        ps4_visualizer = self.visualizer_manager.get_ps4_controller_visualizer()
        if ps4_visualizer:
            use_image_mode = mode.lower() == "image"

            # If switching to drawn mode while in overlay edit mode, disable edit mode first
            if not use_image_mode and self._ps4_overlay_edit_mode:
                self._toggle_ps4_overlay_edit(False)

            # Toggle image mode in the visualizer
            if hasattr(ps4_visualizer, "toggle_image_mode"):
                current_mode = ps4_visualizer.toggle_image_mode()

                # If the toggle didn't work as expected (e.g., images not loaded), update the UI
                if current_mode != use_image_mode:
                    # Block signals to prevent feedback loop
                    ps4_viz_mode_combo = self.ui_manager.components.get(
                        "ps4_viz_mode_combo"
                    )
                    if ps4_viz_mode_combo:
                        ps4_viz_mode_combo.blockSignals(True)
                        ps4_viz_mode_combo.setCurrentText("Drawn")
                        ps4_viz_mode_combo.blockSignals(False)

                        # Inform the user
                        self.ui_manager.log_status(
                            "Cannot use image mode - images not loaded",
                            self.warning_color,
                        )
                else:
                    # Log the mode change
                    self.ui_manager.log_status(
                        f"PS4 controller visualization mode set to: {mode}",
                        self.accent_color,
                    )

            # Update overlay edit button state - only enabled in image mode
            ps4_edit_overlays = self.ui_manager.components.get("ps4_edit_overlays")
            if ps4_edit_overlays:
                ps4_edit_overlays.setEnabled(use_image_mode)

                if use_image_mode:
                    ps4_edit_overlays.setStyleSheet("")  # Reset to default style
                else:
                    ps4_edit_overlays.setStyleSheet(
                        "background-color: #555555; color: #999999;"
                    )

    def run(self) -> None:
        """Run the application."""
        self.show()

    def closeEvent(self, event) -> None:
        """Handle application close event."""
        # Stop collectors
        self.collector_manager.stop_capture()

        # Close log files
        self.logging_manager.close_all()

        # Clean up API integration if it exists
        try:
            from .api_integration import get_api_integration

            api_integration = get_api_integration()
            if api_integration and api_integration.is_registered:
                api_integration.shutdown()
        except:
            pass

        # Clean up interaction API integration if it exists
        try:
            from .interaction_api_integration import get_interaction_api_integration

            interaction_api_integration = get_interaction_api_integration()
            if (
                interaction_api_integration
                and interaction_api_integration.is_registered
            ):
                interaction_api_integration.shutdown()
        except:
            pass

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
