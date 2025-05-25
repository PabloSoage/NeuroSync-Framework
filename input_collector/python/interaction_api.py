"""
Interaction API for the input collector.

This provides a clean interface for controlling the input collector application.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Callable

from .core.event_system import EventType, subscribe, unsubscribe
from .interfaces import InputData
from .services.interaction_service import InteractionService

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InputCollectorAPI:
    """
    Main API for controlling the input collector.
    
    This class provides methods to control the application and access real-time events.
    """
    
    # Dictionary of registered event callbacks
    _event_callbacks = {}
    _next_callback_id = 1
    
    # Constants for validation
    MOUSE_SETTING_RANGES = {
        "delta_smoothing": (0, 90),
        "joystick_sensitivity": (10, 200),
        "angle_grouping": (1, 60)
    }
    
    @classmethod
    def initialize(cls, app_coordinator, ui_manager, logging_manager, collector_manager, event_processor):
        """
        Initialize the API with application components.
        
        Args:
            app_coordinator: The application coordinator
            ui_manager: The UI manager
            logging_manager: The logging manager
            collector_manager: The collector manager
            event_processor: The event processor
        """
        # Initialize the service with the components
        service = InteractionService.get_instance()
        components = {
            'app_coordinator': app_coordinator,
            'ui_manager': ui_manager,
            'logging_manager': logging_manager,
            'collector_manager': collector_manager,
            'event_processor': event_processor
        }
        service.initialize(components)
        
        # Subscribe to core events
        from .core.event_system import EventType, subscribe
        subscribe(EventType.INPUT, cls._on_input_event)
        subscribe(EventType.STATE_CHANGE, cls._on_state_change)
        subscribe(EventType.RECORDING_STARTED, cls._on_recording_started)
        subscribe(EventType.RECORDING_STOPPED, cls._on_recording_stopped)
        
        logger.info("Interaction API initialized")
    
    @classmethod
    def get_last_operation_status(cls) -> Dict[str, Any]:
        """Get the status of the last operation."""
        service = InteractionService.get_instance()
        return service.get_last_status()
    
    #
    # Event handling methods
    #
    
    @classmethod
    def _on_input_event(cls, event: InputData) -> None:
        """Handle input events."""
        # Skip key_release events to match GUI behavior
        if hasattr(event, 'event_type') and event.event_type == 'key_release':
            return
            
        # Notify all registered event callbacks
        cls._notify_event_callbacks(event)
    
    @classmethod
    def _on_state_change(cls, state: Dict[str, Any]) -> None:
        """Handle state change events."""
        # Notify all registered event callbacks
        cls._notify_event_callbacks(state)
    
    @classmethod
    def _on_recording_started(cls, data: Any) -> None:
        """Handle recording started events."""
        state = {"event_type": "recording_started", "timestamp": data}
        cls._notify_event_callbacks(state)
    
    @classmethod
    def _on_recording_stopped(cls, data: Any) -> None:
        """Handle recording stopped events."""
        state = {"event_type": "recording_stopped", "timestamp": data}
        cls._notify_event_callbacks(state)
    
    @classmethod
    def _notify_event_callbacks(cls, event: Any) -> None:
        """Notify all registered event callbacks."""
        # Make a copy of the callbacks to avoid modification during iteration
        callbacks = list(cls._event_callbacks.values())
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
    
    #
    # Public API methods
    #
    
    @classmethod
    def start_recording(cls) -> bool:
        """
        Start recording input events.
        
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.start_recording()
    
    @classmethod
    def stop_recording(cls) -> bool:
        """
        Stop recording input events.
        
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.stop_recording()
    
    @classmethod
    def toggle_recording(cls) -> bool:
        """
        Toggle recording state.
        
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.toggle_recording()
    
    @classmethod
    def is_recording(cls) -> bool:
        """
        Check if recording is active.
        
        Returns:
            bool: True if recording is active
        """
        service = InteractionService.get_instance()
        return service.is_recording()
    
    @classmethod
    def enable_json_logging(cls, enabled: bool = True) -> bool:
        """
        Enable or disable JSON logging.
        
        Args:
            enabled: Whether to enable JSON logging
            
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        
        # Parse boolean parameter to handle string values like "True"/"False" from web API
        enabled = cls._parse_bool(enabled)
        
        # Llamada original
        success = service.enable_json_logging(enabled)
        
        if success:
            # Update UI checkbox state
            ui_manager = service.get_component('ui_manager')
            if ui_manager and 'log_checkbox' in ui_manager.components:
                # Block signals to prevent recursion
                ui_manager.components['log_checkbox'].blockSignals(True)
                ui_manager.components['log_checkbox'].setChecked(enabled)
                ui_manager.components['log_checkbox'].blockSignals(False)
        
        # Ajustar mensaje según el parámetro
        service._set_status(success, f"JSON logging {'enabled' if enabled else 'disabled'}")
        return success

    @classmethod
    def enable_csv_logging(cls, enabled: bool = True, filepath: Optional[str] = None) -> bool:
        """
        Enable or disable CSV logging.
        
        Args:
            enabled: Whether to enable CSV logging
            filepath: Path for CSV file (required when enabling if not previously set)
            
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        
        # Parse boolean parameter to handle string values like "True"/"False" from web API
        enabled = cls._parse_bool(enabled)
        
        # Llamada original
        success = service.enable_csv_logging(enabled, filepath)
        
        if success:
            # Update UI checkbox state
            ui_manager = service.get_component('ui_manager')
            if ui_manager and 'csv_checkbox' in ui_manager.components:
                # Block signals to prevent recursion
                ui_manager.components['csv_checkbox'].blockSignals(True)
                ui_manager.components['csv_checkbox'].setChecked(enabled)
                ui_manager.components['csv_checkbox'].blockSignals(False)
    
        # Ajustar mensaje según el parámetro
        service._set_status(success, f"CSV logging {'enabled' if enabled else 'disabled'}")
        return success

    @classmethod
    def set_csv_path(cls, filepath: str) -> bool:
        """
        Set the CSV logging file path.
        
        Args:
            filepath: Path for CSV file
            
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.set_csv_path(filepath)
    
    @classmethod
    def get_logging_state(cls) -> Dict[str, Any]:
        """
        Get current logging configuration.
        
        Returns:
            Dict with logging state information
        """
        service = InteractionService.get_instance()
        return service.get_logging_state()
    
    @classmethod
    def get_available_collectors(cls) -> List[Dict[str, str]]:
        """
        Get list of available collectors.
        
        Returns:
            List of collector information dictionaries
        """
        service = InteractionService.get_instance()
        return service.get_available_collectors()
    
    @classmethod
    def switch_collector(cls, collector_type: str) -> bool:
        """
        Switch to a different input collector.
        
        Args:
            collector_type: Type identifier for the collector
            
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.switch_collector(collector_type)
    
    @classmethod
    def get_current_collector(cls) -> Dict[str, Any]:
        """
        Get information about the current collector.
        
        Returns:
            Dict with collector information
        """
        service = InteractionService.get_instance()
        return service.get_current_collector()
    
    @classmethod
    def scan_controllers(cls) -> List[Dict[str, Any]]:
        """
        Scan for available controllers.
        
        Returns:
            List of controller information dictionaries
        """
        service = InteractionService.get_instance()
        return service.scan_controllers()
    
    @classmethod
    def connect_controller(cls, index: int) -> bool:
        """
        Connect to a specific controller by index.
        
        Args:
            index: Controller index from scan_controllers()
            
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.connect_controller(index)

    @staticmethod
    def _parse_bool(val):
        """Convert string 'True'/'False' or numeric to proper bool."""
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val)

    @classmethod
    def get_available_tracking_modes(cls, direction_only: bool = None) -> List[str]:
        """
        Get available tracking modes based on direction_only setting.
        
        Args:
            direction_only: Whether direction-only mode is enabled
            
        Returns:
            List[str]: Available tracking modes
        """
        service = InteractionService.get_instance()
        ui_manager = service.get_component('ui_manager')
        
        # If direction_only is explicitly provided, use it regardless of UI state
        # Otherwise, get the current UI state
        if direction_only is None and ui_manager:
            direction_only = ui_manager.is_direction_only_mode()
            
        # normalize string params
        direction_only = cls._parse_bool(direction_only)
        
        # Return appropriate modes based on direction_only parameter
        if direction_only:
            return ["axis", "angle"]
        else:
            return ["joystick", "delta", "angle"]
    
    @classmethod
    def set_mouse_tracking_mode(cls, mode: str, direction_only: Optional[bool] = None) -> bool:
        """
        Set the mouse tracking mode.
        
        Args:
            mode: The tracking mode to use
            direction_only: Whether to use direction-only mode
            
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        ui_manager = service.get_component('ui_manager')
        app_coordinator = service.get_component('app_coordinator')
        
        # normalize string params
        direction_only = cls._parse_bool(direction_only)
        
        if not ui_manager or not app_coordinator:
            service._set_status(False, "Required components not available")
            return False
            
        try:
            # Get current direction-only status
            current_dir_only = ui_manager.is_direction_only_mode()
            
            # If direction_only parameter is provided and different from current state,
            # update it first
            if direction_only is not None and direction_only != current_dir_only:
                # Update the direction only checkbox in UI
                ui_manager.set_direction_only_checkbox(direction_only)
                # Emit signal to update tracking modes
                ui_manager.update_tracking_mode.emit()
            
            # Validate the mode based on updated direction_only setting
            updated_dir_only = ui_manager.is_direction_only_mode()
            valid_modes = cls.get_available_tracking_modes(updated_dir_only)
            
            if mode not in valid_modes:
                service._set_status(False, f"Invalid tracking mode '{mode}' for direction_only={updated_dir_only}. Valid modes: {valid_modes}")
                return False
            
            # Update tracking modes in UI and set the new mode
            ui_manager.update_tracking_modes(
                valid_modes,
                mode,
                "axis" if updated_dir_only else "joystick"
            )
            
            # Apply mode to collector via app coordinator
            app_coordinator.set_mouse_tracking_mode(mode)
            
            service._set_status(True, f"Mouse tracking mode set to {mode} (direction-only: {updated_dir_only})")
            return True
        except Exception as e:
            service._set_status(False, f"Error setting mouse tracking mode: {e}")
            logger.error(f"Error setting mouse tracking mode: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @classmethod
    def set_mouse_settings(cls, delta_smoothing: Optional[float] = None, 
                         joystick_sensitivity: Optional[float] = None,
                         angle_grouping: Optional[int] = None) -> bool:
        """
        Set mouse tracking settings.
        
        Args:
            delta_smoothing: Smoothing factor for delta tracking (0-100)
            joystick_sensitivity: Sensitivity for joystick tracking (0-100)
            angle_grouping: Angle grouping in degrees (1-60)
            
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        ui_manager = service.get_component('ui_manager')
        app_coordinator = service.get_component('app_coordinator')
        
        if not ui_manager or not app_coordinator:
            service._set_status(False, "Required components not available")
            return False
            
        try:
            # Convert parameters to correct types
            if delta_smoothing is not None:
                delta_smoothing = float(delta_smoothing)
                
            if joystick_sensitivity is not None:
                joystick_sensitivity = float(joystick_sensitivity)
                
            if angle_grouping is not None:
                angle_grouping = int(angle_grouping)
            
            # Validate input ranges
            if delta_smoothing is not None:
                min_val, max_val = cls.MOUSE_SETTING_RANGES["delta_smoothing"]
                if not min_val <= delta_smoothing <= max_val:
                    service._set_status(False, f"Delta smoothing must be between {min_val} and {max_val}")
                    return False
                
            if joystick_sensitivity is not None:
                min_val, max_val = cls.MOUSE_SETTING_RANGES["joystick_sensitivity"]
                if not min_val <= joystick_sensitivity <= max_val:
                    service._set_status(False, f"Joystick sensitivity must be between {min_val} and {max_val}")
                    return False
                
            if angle_grouping is not None:
                min_val, max_val = cls.MOUSE_SETTING_RANGES["angle_grouping"]
                if not min_val <= angle_grouping <= max_val:
                    service._set_status(False, f"Angle grouping must be between {min_val} and {max_val}")
                    return False
            
            # Update UI settings - use proper methods that actually exist in the UIManager
            # Use indirect approach with the appropriate slider widgets rather than direct methods
            if delta_smoothing is not None:
                # Instead of ui_manager.set_delta_smoothing()
                # Update the slider value directly if accessible
                delta_slider = ui_manager.components.get('delta_smoothing_slider')
                if delta_slider and hasattr(delta_slider, 'setValue'):
                    delta_slider.setValue(int(delta_smoothing))
                    # Force update of any value labels
                    if hasattr(ui_manager, '_update_angle_grouping_label'):
                        ui_manager._update_angle_grouping_label()
                
            if joystick_sensitivity is not None:
                # Instead of ui_manager.set_joystick_sensitivity()
                joystick_slider = ui_manager.components.get('sensitivity_slider')
                if joystick_slider and hasattr(joystick_slider, 'setValue'):
                    joystick_slider.setValue(int(joystick_sensitivity))
                    # No corresponding update method for joystick sensitivity
                
            if angle_grouping is not None:
                # Instead of ui_manager.set_angle_grouping()
                angle_slider = ui_manager.components.get('angle_grouping_slider')
                if angle_slider and hasattr(angle_slider, 'setValue'):
                    angle_slider.setValue(int(angle_grouping))
                    # Call the update method that exists
                    if hasattr(ui_manager, '_update_angle_grouping_label'):
                        ui_manager._update_angle_grouping_label()
                
            # Apply settings to collector via app coordinator
            app_coordinator.apply_mouse_settings()
            
            # Create status message with actual values set
            values_msg = []
            if delta_smoothing is not None:
                values_msg.append(f"Delta smoothing: {int(delta_smoothing)}/90")
            if joystick_sensitivity is not None:
                values_msg.append(f"Joystick sensitivity: {int(joystick_sensitivity)}/200")
            if angle_grouping is not None:
                angle_values = 360 // int(angle_grouping)
                values_msg.append(f"Angle grouping: {int(angle_grouping)}° ({angle_values} values)")
                
            service._set_status(True, f"Mouse settings updated: {', '.join(values_msg)}")
            return True
        except Exception as e:
            service._set_status(False, f"Error setting mouse settings: {e}")
            logger.error(f"Error setting mouse settings: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @classmethod
    def get_mouse_settings(cls) -> Dict[str, Any]:
        """
        Get current mouse tracking settings.
        
        Returns:
            Dict with mouse settings
        """
        service = InteractionService.get_instance()
        ui_manager = service.get_component('ui_manager')
        
        if not ui_manager:
            return {"error": "UI manager not available"}
            
        try:
            return {
                "tracking_mode": ui_manager.get_tracking_mode(),
                "direction_only": ui_manager.is_direction_only_mode(),
                "delta_smoothing": ui_manager.get_delta_smoothing(),
                "joystick_sensitivity": ui_manager.get_joystick_sensitivity(),
                "angle_grouping": ui_manager.get_angle_grouping(),
                "available_tracking_modes": cls.get_available_tracking_modes()
            }
        except Exception as e:
            logger.error(f"Error getting mouse settings: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    @classmethod
    def get_tracked_keys(cls) -> List[str]:
        """
        Get list of tracked keys.
        
        Returns:
            List of tracked keys
        """
        service = InteractionService.get_instance()
        app_coordinator = service.get_component('app_coordinator')
        
        if not app_coordinator:
            return []
            
        try:
            return app_coordinator.get_tracked_keys()
        except Exception as e:
            logger.error(f"Error getting tracked keys: {e}")
            return []
    
    @classmethod
    def toggle_edit_mode(cls) -> bool:
        """
        Toggle key/button edit mode.
        
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        app_coordinator = service.get_component('app_coordinator')
        
        if not app_coordinator:
            service._set_status(False, "App coordinator not available")
            return False
            
        try:
            # Check if recording is active - can't toggle edit mode during recording
            if app_coordinator.is_recording:
                service._set_status(False, "Cannot edit keys while recording. Stop recording first.")
                return False
                
            # Store previous edit mode state
            prev_state = app_coordinator.edit_mode
            
            # Toggle edit mode
            app_coordinator.toggle_edit_mode()
            
            # Check if state changed
            current_state = app_coordinator.edit_mode
            if current_state != prev_state:
                new_state = "enabled" if current_state else "disabled"
                service._set_status(True, f"Edit mode {new_state}")
                return True
            else:
                service._set_status(False, f"Failed to toggle edit mode. May already be in desired state.")
                return False
                
        except Exception as e:
            service._set_status(False, f"Error toggling edit mode: {e}")
            logger.error(f"Error toggling edit mode: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @classmethod
    def is_edit_mode(cls) -> bool:
        """
        Check if edit mode is active.
        
        Returns:
            bool: True if edit mode is active
        """
        service = InteractionService.get_instance()
        app_coordinator = service.get_component('app_coordinator')
        
        if not app_coordinator:
            return False
            
        return app_coordinator.edit_mode
    
    @classmethod
    def add_tracked_key(cls, key: str) -> bool:
        """
        Add a key to tracked keys list.
        
        Args:
            key: Key to track
            
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        app_coordinator = service.get_component('app_coordinator')
        
        if not app_coordinator:
            service._set_status(False, "App coordinator not available")
            return False
        
        # Sólo en modo edición
        if not app_coordinator.edit_mode:
            service._set_status(False, "Cannot add key: edit mode is disabled")
            return False
            
        try:
            # Check if recording is active - can't edit keys during recording
            if app_coordinator.is_recording:
                service._set_status(False, "Cannot edit keys while recording. Stop recording first.")
                return False
            
            # Check if already in tracked keys
            if key in app_coordinator.get_tracked_keys():
                service._set_status(True, f"Key {key} is already being tracked")
                return True
            
            # Enable edit mode if not already in edit mode
            was_in_edit_mode = app_coordinator.edit_mode
            if not was_in_edit_mode:
                # Enable edit mode temporarily
                app_coordinator.toggle_edit_mode()
                
                # Check if edit mode was enabled successfully
                if not app_coordinator.edit_mode:
                    service._set_status(False, "Failed to enable edit mode")
                    return False
                
            # Add key
            app_coordinator.handle_key_edit(key)
            
            # Check if key was added
            if key in app_coordinator.get_tracked_keys():
                service._set_status(True, f"Added tracked key: {key}")
                
                # Exit edit mode if we enabled it
                if not was_in_edit_mode and app_coordinator.edit_mode:
                    app_coordinator.toggle_edit_mode()
                    
                return True
            else:
                service._set_status(False, f"Failed to add key: {key}")
                
                # Exit edit mode if we enabled it
                if not was_in_edit_mode and app_coordinator.edit_mode:
                    app_coordinator.toggle_edit_mode()
                    
                return False
                
        except Exception as e:
            service._set_status(False, f"Error adding tracked key: {e}")
            logger.error(f"Error adding tracked key: {e}")
            import traceback
            traceback.print_exc()
            
            # Clean up edit mode if needed
            if 'was_in_edit_mode' in locals() and not was_in_edit_mode:
                try:
                    if app_coordinator.edit_mode:
                        app_coordinator.toggle_edit_mode()
                except:
                    pass
                
            return False
    
    @classmethod
    def remove_tracked_key(cls, key: str) -> bool:
        """
        Remove a key from tracked keys list.
        
        Args:
            key: Key to untrack
            
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        app_coordinator = service.get_component('app_coordinator')
        
        if not app_coordinator:
            service._set_status(False, "App coordinator not available")
            return False
        
        # Sólo en modo edición
        if not app_coordinator.edit_mode:
            service._set_status(False, "Cannot remove key: edit mode is disabled")
            return False
            
        try:
            # Check if recording is active - can't edit keys during recording
            if app_coordinator.is_recording:
                service._set_status(False, "Cannot edit keys while recording. Stop recording first.")
                return False
                
            # Check if key is tracked
            if key not in app_coordinator.get_tracked_keys():
                service._set_status(False, f"Key {key} is not being tracked")
                return False
                
            # Don't allow removing F9/media_play_pause
            if key.lower() == "key.media_play_pause".lower():
                service._set_status(False, "Cannot remove F9/media_play_pause key (required for recording toggle)")
                return False
                
            # Enable edit mode temporarily
            was_in_edit_mode = app_coordinator.edit_mode
            if not was_in_edit_mode:
                app_coordinator.toggle_edit_mode()
                
                # Check if edit mode was enabled successfully
                if not app_coordinator.edit_mode:
                    service._set_status(False, "Failed to enable edit mode")
                    return False
                
            # Remove key
            app_coordinator.handle_key_edit(key)
            
            # Check if key was removed
            if key not in app_coordinator.get_tracked_keys():
                service._set_status(True, f"Removed tracked key: {key}")
                
                # Exit edit mode if we enabled it
                if not was_in_edit_mode and app_coordinator.edit_mode:
                    app_coordinator.toggle_edit_mode()
                    
                return True
            else:
                service._set_status(False, f"Failed to remove key: {key}")
                
                # Exit edit mode if we enabled it
                if not was_in_edit_mode and app_coordinator.edit_mode:
                    app_coordinator.toggle_edit_mode()
                    
                return False
                
        except Exception as e:
            service._set_status(False, f"Error removing tracked key: {e}")
            logger.error(f"Error removing tracked key: {e}")
            import traceback
            traceback.print_exc()
            
            # Clean up edit mode if needed
            if 'was_in_edit_mode' in locals() and not was_in_edit_mode:
                try:
                    if app_coordinator.edit_mode:
                        app_coordinator.toggle_edit_mode()
                except:
                    pass
                
            return False
    
    @classmethod
    def toggle_button_tracking(cls, button_id: str, track: bool) -> bool:
        """
        Toggle tracking for a mouse button.

        Args:
            button_id: Button identifier
            track: Whether to track the button

        Returns:
            bool: True if successful
        """
        # normalize string params
        track = cls._parse_bool(track)
        
        # Delegate to the add/remove methods which handle edit mode,
        # recording checks and actual toggling in the coordinator
        if track:
            return cls.add_tracked_key(button_id)
        else:
            return cls.remove_tracked_key(button_id)

    @classmethod
    def toggle_fullscreen(cls) -> bool:
        """
        Toggle fullscreen mode.
        
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        ui_manager = service.get_component('ui_manager')
        
        if not ui_manager:
            service._set_status(False, "UI manager not available")
            return False
            
        try:
            # Send signal to toggle fullscreen
            ui_manager.toggle_fullscreen.emit()
            service._set_status(True, "Toggled fullscreen mode")
            return True
        except Exception as e:
            service._set_status(False, f"Error toggling fullscreen: {e}")
            logger.error(f"Error toggling fullscreen: {e}")
            return False
    
    @classmethod
    def get_application_state(cls) -> Dict[str, Any]:
        """
        Get comprehensive application state.
        
        Returns:
            Dict with application state
        """
        service = InteractionService.get_instance()
        
        # Get components
        app_coordinator = service.get_component('app_coordinator')
        collector_manager = service.get_component('collector_manager')
        
        if not app_coordinator or not collector_manager:
            return {"error": "Required components not available"}
            
        try:
            # Get collector information
            collector_info = cls.get_current_collector()
            
            # Get recording state
            recording = cls.is_recording()
            
            # Get edit mode state
            edit_mode = cls.is_edit_mode()
            
            # Get tracked keys
            tracked_keys = cls.get_tracked_keys()
            
            # Get mouse settings
            mouse_settings = cls.get_mouse_settings()
            
            # Get logging state
            logging_state = cls.get_logging_state()
            
            # Get active keys
            active_keys = collector_manager.get_active_keys()
            
            return {
                "collector": collector_info,
                "recording": recording,
                "edit_mode": edit_mode,
                "tracked_keys": tracked_keys,
                "active_keys": active_keys,
                "mouse_settings": mouse_settings,
                "logging": logging_state
            }
        except Exception as e:
            logger.error(f"Error getting application state: {e}")
            return {"error": str(e)}
    
    @classmethod
    def register_event_callback(cls, callback: Callable[[Any], None]) -> int:
        """
        Register a callback for real-time events.
        
        Args:
            callback: Function to call when events occur
            
        Returns:
            int: Callback ID for unregistering
        """
        callback_id = cls._next_callback_id
        cls._event_callbacks[callback_id] = callback
        cls._next_callback_id += 1
        return callback_id
    
    @classmethod
    def unregister_event_callback(cls, callback_id: int) -> bool:
        """
        Unregister an event callback.
        
        Args:
            callback_id: ID of the callback to unregister
            
        Returns:
            bool: True if successful
        """
        if callback_id in cls._event_callbacks:
            del cls._event_callbacks[callback_id]
            return True
        return False
