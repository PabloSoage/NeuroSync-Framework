"""
Application coordinator module.

Acts as the central coordinator between different components of the application,
handling high-level business logic while delegating specific responsibilities.
"""

from typing import List

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from ..interfaces import InputData
from ..logging import LoggingManager
from ..processing import EventProcessor
from ..ui import UIManager


class AppCoordinator(QObject):
    """
    Central coordinator for the input collector application.
    
    This class manages the high-level flow of the application, coordinating the interactions
    between the collector manager, UI manager, visualizers, logging, and event processing.
    It follows the mediator pattern to reduce coupling between components.
    """
    
    # Signal to safely pass events between threads
    event_received = pyqtSignal(object)
    
    # Signals for application state changes
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    edit_mode_toggled = pyqtSignal(bool)
    collector_switched = pyqtSignal(str, dict)
    
    # New signal for tracked keys updates
    tracked_keys_changed = pyqtSignal(list)
    
    def __init__(self, collector_manager, ui_manager: UIManager, 
                logging_manager: LoggingManager,
                event_processor: EventProcessor) -> None:
        """
        Initialize the application coordinator.
        
        Args:
            collector_manager: The collector manager instance
            ui_manager: The UI manager instance
            logging_manager: The logging manager instance
            event_processor: The event processor instance
        """
        super().__init__()
        
        self.collector_manager = collector_manager
        self.ui_manager = ui_manager
        self.logging_manager = logging_manager
        self.event_processor = event_processor
        
        # App state
        self.is_recording = False
        self.tracked_keys = []
        self.edit_mode = False
        self.f9_key_down = False
        
        # Connect signals
        self.event_received.connect(self._process_event)
        self.event_processor.toggle_recording_requested.connect(self.toggle_recording)
        
        # Register for collector events
        self.collector_manager.on_event(self.on_collector_event)
    
    def initialize(self, tracked_keys: List[str]) -> None:
        """
        Initialize the coordinator with the initial tracked keys.
        
        Args:
            tracked_keys: List of keys to track initially
        """
        self.tracked_keys = tracked_keys
        self.collector_manager.set_tracked_keys(tracked_keys)
    
    def on_collector_event(self, event: InputData) -> None:
        """
        Handle events from the collector manager.
        
        Args:
            event: The input event to handle
        """
        # Forward via signal to ensure thread safety between threads
        self.event_received.emit(event)
    
    @pyqtSlot(object)
    def _process_event(self, event: InputData) -> None:
        """
        Process received events in the main thread.
        
        Args:
            event: The input event to process
        """
        # Update active keys display
        active_keys = self.collector_manager.get_active_keys()
        self.ui_manager.update_active_keys_display(active_keys)
        
        # Handle special events first (recording toggle, etc)
        if self._handle_special_events(event):
            return
            
        # Don't process other events if not recording
        if not self.is_recording:
            return
        
        # Process regular events
        self._process_and_log_event(event)
    
    def _handle_special_events(self, event: InputData) -> bool:
        """
        Handle special input events like recording toggle.
        
        Args:
            event: The input event to process
            
        Returns:
            bool: True if event was handled as special, False otherwise
        """
        # Handle toggle_recording event (F9)
        if event.event_type == "toggle_recording":
            if not self.f9_key_down:
                self.toggle_recording()
                self.f9_key_down = True
            return True
            
        # Handle F9 key release
        if event.event_type == "key_release" and event.key == "Key.media_play_pause":
            self.f9_key_down = False
            return True
            
        return False
    
    def _process_and_log_event(self, event: InputData) -> None:
        """
        Process a regular input event and log it if needed.
        
        Args:
            event: The input event to process
        """
        # Get current collector type
        collector_type = self.collector_manager.get_current_collector_type()
        
        # Process the event to get formatted display text and logging flag
        result = self.event_processor.process_event(event, collector_type)
        
        # Log the event if flagged for logging
        if result["should_log"]:
            # Display in UI
            self.ui_manager.log_status(result["display_text"])
            
            # Log to files if enabled
            self.logging_manager.log_event(event, collector_type)
    
    def toggle_recording(self) -> None:
        """Toggle recording state."""
        # Prevent recording while in edit mode
        if self.edit_mode:
            self.ui_manager.log_status("Cannot start recording while in edit mode", "warning")
            return
        
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()
    
    def _start_recording(self) -> None:
        """Start recording inputs."""
        # Initialize CSV file if needed
        if self.logging_manager.log_to_csv:
            self._initialize_csv_logging()
        
        # Start capturing
        self.collector_manager.start_capture()
        self.is_recording = True
        
        # Update UI
        self.ui_manager.update_recording_state(True)
        self.ui_manager.log_status("Recording started", "success")
        
        # Start logging
        self.logging_manager.start_recording()
        
        # Emit signal
        self.recording_started.emit()
    
    def _stop_recording(self) -> None:
        """Stop recording inputs."""
        # Stop capturing
        self.collector_manager.stop_capture()
        self.is_recording = False
        
        # Update UI
        self.ui_manager.update_recording_state(False)
        self.ui_manager.log_status("Recording stopped", "warning")
        
        # Stop logging
        self.logging_manager.stop_recording()
        
        # Emit signal
        self.recording_stopped.emit()
    
    def _initialize_csv_logging(self) -> None:
        """Initialize CSV logging with appropriate headers."""
        # Get current tracking mode and settings
        tracking_mode = self.ui_manager.get_tracking_mode()
        direction_only = self.ui_manager.is_direction_only_mode()
        
        # Create headers for CSV based on tracked keys and mode
        self.logging_manager.initialize_csv_file(
            None,  # Let CSV logger generate headers
            self.tracked_keys,
            tracking_mode,
            direction_only
        )
    
    def toggle_edit_mode(self) -> None:
        """Toggle key/button editing mode."""
        try:
            # Don't allow edit mode when recording
            if self.is_recording:
                self.ui_manager.log_status("Cannot edit keys while recording", "warning")
                return
            
            self.edit_mode = not self.edit_mode
            print(f"AppCoordinator.toggle_edit_mode() - New state: {self.edit_mode}")
            
            # Emit signal FIRST to ensure UI updates
            self.edit_mode_toggled.emit(self.edit_mode)
            
            # Update UI
            self.ui_manager.update_edit_mode(self.edit_mode)
            
            # Log status
            if self.edit_mode:
                self.ui_manager.log_status(
                    "Click on keys or mouse buttons to add/remove them from tracking",
                    "success",
                )
            else:
                self.ui_manager.log_status("Key editing finished", "accent")
        except Exception as e:
            print(f"Error toggling edit mode: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_key_edit(self, key: str) -> None:
        """
        Handle editing of tracked keys.
        
        Args:
            key: The key to toggle tracking for
        """
        try:
            print(f"AppCoordinator.handle_key_edit({key}) - Edit mode: {self.edit_mode}")
            if not self.edit_mode:
                print("Ignoring key edit - not in edit mode")
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
                        "warning"
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
                
            # Update key list in collectors
            self.collector_manager.set_tracked_keys(self.tracked_keys)
            
            # Emit signal to notify listeners (especially visualizers) about the change
            self.tracked_keys_changed.emit(self.tracked_keys)
            
        except Exception as e:
            print(f"Error handling key edit: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_button_edit(self, button_id: str, is_tracked: bool) -> None:
        """
        Handle editing of tracked mouse buttons.
        
        Args:
            button_id: The button ID to modify
            is_tracked: Whether the button should be tracked
        """
        if not self.edit_mode:
            return
            
        # Handle special case for scroll
        if button_id == "Button.scroll":
            # No longer need to update a separate UI checkbox
            # Just update visualizer directly
            if hasattr(self.ui_manager, 'visualizer_manager'):
                # If UI manager has direct access to visualizer manager
                self.ui_manager.visualizer_manager.set_scroll_tracking(is_tracked)
            
            # Log status message
            self.ui_manager.log_status(
                f"Scroll tracking {'enabled' if is_tracked else 'disabled'}",
                "success" if is_tracked else "warning",
            )
            
            # Update tracking status consistently
            button_in_list = button_id in self.tracked_keys
            if is_tracked and not button_in_list:
                self.tracked_keys.append(button_id)
            elif not is_tracked and button_in_list:
                self.tracked_keys.remove(button_id)
                
            # Update collector
            self.collector_manager.set_tracked_keys(self.tracked_keys)
            
            # Emit signal for tracked keys change
            self.tracked_keys_changed.emit(self.tracked_keys)
            return
            
        # For other buttons, update tracked keys list
        if is_tracked:
            # Add button if not already in list
            if button_id not in self.tracked_keys:
                self.tracked_keys.append(button_id)
                self.ui_manager.log_status(f"Added tracking for {button_id}", "success")
        else:
            # Remove button if in list
            if button_id in self.tracked_keys:
                self.tracked_keys.remove(button_id)
                self.ui_manager.log_status(f"Removed tracking for {button_id}", "warning")
                
        # Update collector
        self.collector_manager.set_tracked_keys(self.tracked_keys)
        
        # Emit signal for tracked keys change
        self.tracked_keys_changed.emit(self.tracked_keys)
    
    def switch_collector(self, collector_type: str) -> None:
        """
        Switch to a different input collector.
        
        Args:
            collector_type: The type identifier for the collector to switch to
        """
        # Stop recording if active
        if self.is_recording:
            self._stop_recording()
        
        # Switch collector
        success = self.collector_manager.set_current_collector(collector_type)
        
        if success:
            # Get collector capabilities
            capabilities = self.collector_manager.get_current_collector_capabilities()
            
            # Emit signal about collector change
            self.collector_switched.emit(collector_type, capabilities)
            
            # Log success message
            collector_name = self.collector_manager._get_collector_display_name(collector_type)
            self.ui_manager.log_status(f"Switched to {collector_name} collector", "accent")
        else:
            # Log failure
            self.ui_manager.log_status(f"Failed to switch to collector: {collector_type}", "error")
    
    def set_mouse_tracking_mode(self, mode: str) -> None:
        """
        Set the mouse tracking mode.
        
        Args:
            mode: The tracking mode to set
        """
        # Don't allow changing mode when recording
        if self.is_recording:
            self.ui_manager.log_status("Cannot change tracking mode while recording", "warning")
            return
            
        # Get current settings
        direction_only = self.ui_manager.is_direction_only_mode()
        angle_grouping = self.ui_manager.get_angle_grouping()
        
        # Update collector's tracking mode
        collector = self.collector_manager.get_current_collector()
        if collector and hasattr(collector, "set_mouse_tracking_mode"):
            collector.set_mouse_tracking_mode(mode, direction_only, angle_grouping)
            self.ui_manager.log_status(f"Mouse tracking mode set to: {mode}", "accent")
    
    def apply_mouse_settings(self) -> None:
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
    
    def get_tracked_keys(self) -> List[str]:
        """
        Get the list of currently tracked keys/buttons.
        
        Returns:
            List[str]: The list of tracked keys and buttons
        """
        return self.tracked_keys
    
    @pyqtSlot()
    def _toggle_recording_proxy(self) -> None:
        """
        Thread-safe proxy for toggle_recording.
        
        This method exists solely to be called via QMetaObject.invokeMethod
        from other threads to ensure thread safety.
        """
        self.toggle_recording()

    def __del__(self) -> None:
        """Cleanup resources when the coordinator is destroyed."""
        try:
            # Unregister from API explorer if we're using it
            if hasattr(self, '_api_integration') and self._api_integration:
                from ..api_integration import get_api_integration
                api_integration = get_api_integration()
                if api_integration and api_integration.is_registered:
                    api_integration.shutdown()
        except:
            pass
