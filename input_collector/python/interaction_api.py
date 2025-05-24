"""
Interaction API for the input collector.

This provides a clean interface for controlling the input collector application.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Callable

from .core.event_system import EventType, subscribe, unsubscribe
from .interfaces import InputData

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InputCollectorAPI:
    """
    Main API for controlling the input collector.
    
    This class provides methods to control the application and access real-time events.
    """
    
    # Static references to application components (set during initialization)
    _app_coordinator = None
    _ui_manager = None
    _logging_manager = None
    _collector_manager = None
    _event_processor = None
    
    # Last operation status
    _last_status = {"success": False, "message": "API not initialized"}
    
    # Dictionary of registered event callbacks
    _event_callbacks = {}
    _next_callback_id = 1
    
    # Constants for validation
    MOUSE_SETTING_RANGES = {
        "delta_smoothing": (0, 100),
        "joystick_sensitivity": (0, 100),
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
        cls._app_coordinator = app_coordinator
        cls._ui_manager = ui_manager
        cls._logging_manager = logging_manager
        cls._collector_manager = collector_manager
        cls._event_processor = event_processor
        
        cls._last_status = {"success": True, "message": "API initialized"}
        
        # Subscribe to core events
        from .core.event_system import EventType, subscribe
        subscribe(EventType.INPUT, cls._on_input_event)
        subscribe(EventType.STATE_CHANGE, cls._on_state_change)
        subscribe(EventType.RECORDING_STARTED, cls._on_recording_started)
        subscribe(EventType.RECORDING_STOPPED, cls._on_recording_stopped)
        
        logger.info("Interaction API initialized")
    
    @classmethod
    def _set_status(cls, success: bool, message: str) -> None:
        """Set the status of the last operation."""
        cls._last_status = {"success": success, "message": message}
        logger.info(f"Interaction status: {message} {'(success)' if success else '(failure)'}")
    
    @classmethod
    def get_last_operation_status(cls) -> Dict[str, Any]:
        """Get the status of the last operation."""
        return cls._last_status
    
    @classmethod
    def _check_initialized(cls) -> bool:
        """Check if the API is initialized."""
        if cls._app_coordinator is None:
            cls._set_status(False, "API not initialized")
            return False
        return True
    
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
        if not cls._check_initialized():
            return False
            
        try:
            # Check if already recording
            if cls.is_recording():
                cls._set_status(False, "Already recording")
                return False
                
            # Make sure not in edit mode
            if cls.is_edit_mode():
                cls._set_status(False, "Cannot start recording while in edit mode")
                return False
                
            # Start recording
            cls._app_coordinator.toggle_recording()
            
            # Check if recording started successfully
            if cls.is_recording():
                cls._set_status(True, "Recording started")
                return True
            else:
                cls._set_status(False, "Failed to start recording")
                return False
                
        except Exception as e:
            cls._set_status(False, f"Error starting recording: {e}")
            logger.error(f"Error starting recording: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @classmethod
    def stop_recording(cls) -> bool:
        """
        Stop recording input events.
        
        Returns:
            bool: True if successful
        """
        if not cls._check_initialized():
            return False
            
        try:
            # Check if currently recording
            if not cls.is_recording():
                cls._set_status(False, "Not currently recording")
                return False
                
            # Stop recording
            cls._app_coordinator.toggle_recording()
            
            # Check if recording stopped successfully
            if not cls.is_recording():
                cls._set_status(True, "Recording stopped")
                return True
            else:
                cls._set_status(False, "Failed to stop recording")
                return False
                
        except Exception as e:
            cls._set_status(False, f"Error stopping recording: {e}")
            logger.error(f"Error stopping recording: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @classmethod
    def toggle_recording(cls) -> bool:
        """
        Toggle recording state.
        
        Returns:
            bool: True if successful
        """
        if not cls._check_initialized():
            return False
            
        try:
            # Store previous recording state
            prev_state = cls.is_recording()
            
            # Toggle recording
            cls._app_coordinator.toggle_recording()
            
            # Check if state changed
            current_state = cls.is_recording()
            if current_state != prev_state:
                new_state = "started" if current_state else "stopped"
                cls._set_status(True, f"Recording {new_state}")
                return True
            else:
                # If state didn't change, there was likely an error
                cls._set_status(False, "Failed to toggle recording")
                return False
                
        except Exception as e:
            cls._set_status(False, f"Error toggling recording: {e}")
            logger.error(f"Error toggling recording: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @classmethod
    def is_recording(cls) -> bool:
        """
        Check if recording is active.
        
        Returns:
            bool: True if recording is active
        """
        if not cls._check_initialized():
            return False
            
        return cls._app_coordinator.is_recording
    
    @classmethod
    def enable_json_logging(cls, enabled: bool = True) -> bool:
        """
        Enable or disable JSON logging.
        
        Args:
            enabled: Whether to enable JSON logging
            
        Returns:
            bool: True if successful
        """
        if not cls._check_initialized():
            return False
            
        try:
            success = cls._logging_manager.set_json_logging(enabled)
            if success:
                cls._set_status(True, f"JSON logging {'enabled' if enabled else 'disabled'}")
            else:
                cls._set_status(False, f"Failed to {'enable' if enabled else 'disable'} JSON logging")
            return success
        except Exception as e:
            cls._set_status(False, f"Error configuring JSON logging: {e}")
            logger.error(f"Error configuring JSON logging: {e}")
            return False
    
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
        if not cls._check_initialized():
            return False
            
        try:
            # If enabling and filepath is provided, set it first
            if enabled and filepath:
                cls.set_csv_path(filepath)
                
            # Enable/disable CSV logging
            success = cls._logging_manager.set_csv_logging(enabled)
            if success:
                cls._set_status(True, f"CSV logging {'enabled' if enabled else 'disabled'}")
            else:
                cls._set_status(False, f"Failed to {'enable' if enabled else 'disable'} CSV logging")
            return success
        except Exception as e:
            cls._set_status(False, f"Error configuring CSV logging: {e}")
            logger.error(f"Error configuring CSV logging: {e}")
            return False
    
    @classmethod
    def set_csv_path(cls, filepath: str) -> bool:
        """
        Set the CSV logging file path.
        
        Args:
            filepath: Path for CSV file
            
        Returns:
            bool: True if successful
        """
        if not cls._check_initialized():
            return False
            
        try:
            cls._logging_manager.csv_logger.set_filepath(filepath)
            cls._ui_manager.set_csv_path(filepath)
            cls._set_status(True, f"CSV path set to {filepath}")
            return True
        except Exception as e:
            cls._set_status(False, f"Error setting CSV path: {e}")
            logger.error(f"Error setting CSV path: {e}")
            return False
    
    @classmethod
    def get_logging_state(cls) -> Dict[str, Any]:
        """
        Get current logging configuration.
        
        Returns:
            Dict with logging state information
        """
        if not cls._check_initialized():
            return {"error": "API not initialized"}
            
        try:
            return {
                "json_logging_enabled": cls._logging_manager.log_to_json,
                "csv_logging_enabled": cls._logging_manager.log_to_csv,
                "csv_path": cls._logging_manager.csv_logger.filepath if cls._logging_manager.csv_logger else ""
            }
        except Exception as e:
            logger.error(f"Error getting logging state: {e}")
            return {"error": str(e)}
    
    @classmethod
    def get_available_collectors(cls) -> List[Dict[str, str]]:
        """
        Get list of available collectors.
        
        Returns:
            List of collector information dictionaries
        """
        if not cls._check_initialized():
            return []
            
        try:
            return cls._collector_manager.get_available_collectors()
        except Exception as e:
            logger.error(f"Error getting available collectors: {e}")
            return []
    
    @classmethod
    def switch_collector(cls, collector_type: str) -> bool:
        """
        Switch to a different input collector.
        
        Args:
            collector_type: Type identifier for the collector
            
        Returns:
            bool: True if successful
        """
        if not cls._check_initialized():
            return False
            
        try:
            # Get current collector type for comparison
            prev_collector = cls._collector_manager.get_current_collector_type()
            
            # Special handling for PS4 controller to match GUI behavior
            if collector_type == "ps4_controller":
                # Check if PS4 collector is available
                ps4_collector = cls._collector_manager.get_collector("ps4_controller")
                if not ps4_collector:
                    cls._set_status(False, "PS4 controller support not available")
                    return False
                    
                # Check if a controller is already connected
                if not ps4_collector.controller:
                    # Scan for controllers
                    controllers = ps4_collector.scan_controllers()
                    if not controllers:
                        cls._set_status(False, "No controllers found, falling back to keyboard/mouse")
                        # Switch to keyboard/mouse instead
                        cls._app_coordinator.switch_collector("keyboard_mouse")
                        return False
                    
                    # Connect to first controller
                    success = ps4_collector.connect_to_controller(controllers[0]["index"])
                    if not success:
                        cls._set_status(False, "Failed to connect to controller, falling back to keyboard/mouse")
                        # Switch to keyboard/mouse instead
                        cls._app_coordinator.switch_collector("keyboard_mouse")
                        return False
            
            # Switch collector using the app coordinator
            cls._app_coordinator.switch_collector(collector_type)
            
            # Verify switch was successful by checking current collector type
            current_collector = cls._collector_manager.get_current_collector_type()
            if current_collector == collector_type:
                cls._set_status(True, f"Switched to {collector_type} collector")
                return True
            else:
                cls._set_status(False, f"Failed to switch to {collector_type} collector")
                return False
                
        except Exception as e:
            cls._set_status(False, f"Error switching collector: {e}")
            logger.error(f"Error switching collector: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @classmethod
    def get_current_collector(cls) -> Dict[str, Any]:
        """
        Get information about the current collector.
        
        Returns:
            Dict with collector information
        """
        if not cls._check_initialized():
            return {"error": "API not initialized"}
            
        try:
            collector_type = cls._collector_manager.get_current_collector_type()
            capabilities = cls._collector_manager.get_current_collector_capabilities()
            
            return {
                "type": collector_type,
                "name": cls._collector_manager._get_collector_display_name(collector_type),
                "capabilities": capabilities
            }
        except Exception as e:
            logger.error(f"Error getting current collector: {e}")
            return {"error": str(e)}
    
    @classmethod
    def scan_controllers(cls) -> List[Dict[str, Any]]:
        """
        Scan for available controllers.
        
        Returns:
            List of controller information dictionaries
        """
        if not cls._check_initialized():
            return []
            
        try:
            ps4_collector = cls._collector_manager.get_collector("ps4_controller")
            if ps4_collector:
                return ps4_collector.scan_controllers()
            return []
        except Exception as e:
            logger.error(f"Error scanning controllers: {e}")
            return []
    
    @classmethod
    def connect_controller(cls, index: int) -> bool:
        """
        Connect to a specific controller by index.
        
        Args:
            index: Controller index from scan_controllers()
            
        Returns:
            bool: True if successful
        """
        if not cls._check_initialized():
            return False
            
        try:
            ps4_collector = cls._collector_manager.get_collector("ps4_controller")
            if ps4_collector:
                success = ps4_collector.connect_to_controller(index)
                if success:
                    cls._set_status(True, "Connected to controller")
                    # Switch to PS4 controller
                    cls.switch_collector("ps4_controller")
                else:
                    cls._set_status(False, "Failed to connect to controller")
                return success
            else:
                cls._set_status(False, "PS4 collector not available")
                return False
                
        except Exception as e:
            cls._set_status(False, f"Error connecting to controller: {e}")
            logger.error(f"Error connecting to controller: {e}")
            return False

    @classmethod
    def get_available_tracking_modes(cls, direction_only: bool = None) -> List[str]:
        """
        Get available tracking modes based on direction_only setting.
        
        Args:
            direction_only: Whether direction-only mode is enabled
            
        Returns:
            List[str]: Available tracking modes
        """
        # If direction_only not specified, get current setting
        if direction_only is None and cls._ui_manager:
            direction_only = cls._ui_manager.is_direction_only_mode()
            
        # Return appropriate modes based on direction_only setting
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
        if not cls._check_initialized():
            return False
            
        try:
            # Validate the mode based on direction_only setting
            current_dir_only = cls._ui_manager.is_direction_only_mode() if direction_only is None else direction_only
            valid_modes = cls.get_available_tracking_modes(current_dir_only)
            
            if mode not in valid_modes:
                cls._set_status(False, f"Invalid tracking mode '{mode}' for direction_only={current_dir_only}. Valid modes: {valid_modes}")
                return False
            
            # Update direction-only mode if specified
            if direction_only is not None:
                cls._ui_manager.set_direction_only_mode(direction_only)
                
            # Set tracking mode in UI
            cls._ui_manager.set_tracking_mode(mode)
            
            # Apply mode to collector via app coordinator
            cls._app_coordinator.set_mouse_tracking_mode(mode)
            
            cls._set_status(True, f"Mouse tracking mode set to {mode}")
            return True
        except Exception as e:
            cls._set_status(False, f"Error setting mouse tracking mode: {e}")
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
        if not cls._check_initialized():
            return False
            
        try:
            # Validate input ranges
            if delta_smoothing is not None:
                min_val, max_val = cls.MOUSE_SETTING_RANGES["delta_smoothing"]
                if not min_val <= delta_smoothing <= max_val:
                    cls._set_status(False, f"Delta smoothing must be between {min_val} and {max_val}")
                    return False
                
            if joystick_sensitivity is not None:
                min_val, max_val = cls.MOUSE_SETTING_RANGES["joystick_sensitivity"]
                if not min_val <= joystick_sensitivity <= max_val:
                    cls._set_status(False, f"Joystick sensitivity must be between {min_val} and {max_val}")
                    return False
                
            if angle_grouping is not None:
                min_val, max_val = cls.MOUSE_SETTING_RANGES["angle_grouping"]
                if not min_val <= angle_grouping <= max_val:
                    cls._set_status(False, f"Angle grouping must be between {min_val} and {max_val}")
                    return False
            
            # Update UI settings - using the correct method names
            if delta_smoothing is not None:
                if hasattr(cls._ui_manager, 'get_delta_smoothing_slider') and cls._ui_manager.get_delta_smoothing_slider():
                    cls._ui_manager.get_delta_smoothing_slider().setValue(int(delta_smoothing))
                
            if joystick_sensitivity is not None:
                if hasattr(cls._ui_manager, 'get_joystick_sensitivity_slider') and cls._ui_manager.get_joystick_sensitivity_slider():
                    cls._ui_manager.get_joystick_sensitivity_slider().setValue(int(joystick_sensitivity))
                
            if angle_grouping is not None:
                if hasattr(cls._ui_manager, 'get_angle_grouping_slider') and cls._ui_manager.get_angle_grouping_slider():
                    cls._ui_manager.get_angle_grouping_slider().setValue(int(angle_grouping))
                
            # Apply settings to collector
            cls._app_coordinator.apply_mouse_settings()
            
            cls._set_status(True, "Mouse settings updated")
            return True
        except Exception as e:
            cls._set_status(False, f"Error setting mouse settings: {e}")
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
        if not cls._check_initialized():
            return {"error": "API not initialized"}
            
        try:
            return {
                "tracking_mode": cls._ui_manager.get_tracking_mode(),
                "direction_only": cls._ui_manager.is_direction_only_mode(),
                "delta_smoothing": cls._ui_manager.get_delta_smoothing(),
                "joystick_sensitivity": cls._ui_manager.get_joystick_sensitivity(),
                "angle_grouping": cls._ui_manager.get_angle_grouping(),
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
        if not cls._check_initialized():
            return []
            
        try:
            return cls._app_coordinator.get_tracked_keys()
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
        if not cls._check_initialized():
            return False
            
        try:
            # Check if recording is active - can't toggle edit mode during recording
            if cls.is_recording():
                cls._set_status(False, "Cannot edit keys while recording")
                return False
                
            # Store previous edit mode state
            prev_state = cls.is_edit_mode()
            
            # Toggle edit mode
            cls._app_coordinator.toggle_edit_mode()
            
            # Check if state changed
            current_state = cls.is_edit_mode()
            if current_state != prev_state:
                new_state = "enabled" if current_state else "disabled"
                cls._set_status(True, f"Edit mode {new_state}")
                return True
            else:
                cls._set_status(False, "Failed to toggle edit mode")
                return False
                
        except Exception as e:
            cls._set_status(False, f"Error toggling edit mode: {e}")
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
        if not cls._check_initialized():
            return False
            
        return cls._app_coordinator.edit_mode
    
    @classmethod
    def add_tracked_key(cls, key: str) -> bool:
        """
        Add a key to tracked keys list.
        
        Args:
            key: Key to track
            
        Returns:
            bool: True if successful
        """
        if not cls._check_initialized():
            return False
            
        try:
            # Check if recording is active - can't edit keys during recording
            if cls.is_recording():
                cls._set_status(False, "Cannot edit keys while recording")
                return False
            
            # Check if already in tracked keys
            if key in cls._app_coordinator.get_tracked_keys():
                cls._set_status(True, f"Key {key} is already being tracked")
                return True
            
            # Enable edit mode temporarily
            was_in_edit_mode = cls.is_edit_mode()
            if not was_in_edit_mode:
                cls._app_coordinator.toggle_edit_mode()
                
            # Add key
            cls._app_coordinator.handle_key_edit(key)
            
            # Check if key was added
            if key in cls._app_coordinator.get_tracked_keys():
                cls._set_status(True, f"Added tracked key: {key}")
                
                # Exit edit mode if we enabled it
                if not was_in_edit_mode and cls.is_edit_mode():
                    cls._app_coordinator.toggle_edit_mode()
                    
                return True
            else:
                cls._set_status(False, f"Failed to add key: {key}")
                
                # Exit edit mode if we enabled it
                if not was_in_edit_mode and cls.is_edit_mode():
                    cls._app_coordinator.toggle_edit_mode()
                    
                return False
                
        except Exception as e:
            cls._set_status(False, f"Error adding tracked key: {e}")
            logger.error(f"Error adding tracked key: {e}")
            import traceback
            traceback.print_exc()
            
            # Clean up edit mode if needed
            if 'was_in_edit_mode' in locals() and not was_in_edit_mode and cls.is_edit_mode():
                try:
                    cls._app_coordinator.toggle_edit_mode()
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
        if not cls._check_initialized():
            return False
            
        try:
            # Check if recording is active - can't edit keys during recording
            if cls.is_recording():
                cls._set_status(False, "Cannot edit keys while recording")
                return False
                
            # Check if key is tracked
            if key not in cls._app_coordinator.get_tracked_keys():
                cls._set_status(False, f"Key {key} is not being tracked")
                return False
                
            # Don't allow removing F9/media_play_pause
            if key.lower() == "key.media_play_pause".lower():
                cls._set_status(False, "Cannot remove F9/media_play_pause key")
                return False
                
            # Enable edit mode temporarily
            was_in_edit_mode = cls.is_edit_mode()
            if not was_in_edit_mode:
                cls._app_coordinator.toggle_edit_mode()
                
            # Remove key
            cls._app_coordinator.handle_key_edit(key)
            
            # Check if key was removed
            if key not in cls._app_coordinator.get_tracked_keys():
                cls._set_status(True, f"Removed tracked key: {key}")
                
                # Exit edit mode if we enabled it
                if not was_in_edit_mode and cls.is_edit_mode():
                    cls._app_coordinator.toggle_edit_mode()
                    
                return True
            else:
                cls._set_status(False, f"Failed to remove key: {key}")
                
                # Exit edit mode if we enabled it
                if not was_in_edit_mode and cls.is_edit_mode():
                    cls._app_coordinator.toggle_edit_mode()
                    
                return False
                
        except Exception as e:
            cls._set_status(False, f"Error removing tracked key: {e}")
            logger.error(f"Error removing tracked key: {e}")
            import traceback
            traceback.print_exc()
            
            # Clean up edit mode if needed
            if 'was_in_edit_mode' in locals() and not was_in_edit_mode and cls.is_edit_mode():
                try:
                    cls._app_coordinator.toggle_edit_mode()
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
        if not cls._check_initialized():
            return False
            
        try:
            # Check if recording is active - can't edit buttons during recording
            if cls.is_recording():
                cls._set_status(False, "Cannot edit buttons while recording")
                return False
                
            # Enable edit mode temporarily
            was_in_edit_mode = cls.is_edit_mode()
            if not was_in_edit_mode:
                cls._app_coordinator.toggle_edit_mode()
            
            # Current state of button tracking
            tracked_keys = cls._app_coordinator.get_tracked_keys()
            is_currently_tracked = button_id in tracked_keys
            
            # Only make changes if needed
            if is_currently_tracked != track:
                # Toggle button tracking
                cls._app_coordinator.handle_button_edit(button_id, track)
                
                # Check if button tracking state changed as expected
                updated_tracked_keys = cls._app_coordinator.get_tracked_keys()
                button_tracked = button_id in updated_tracked_keys
                
                if button_tracked == track:
                    cls._set_status(True, f"Button {button_id} tracking {'enabled' if track else 'disabled'}")
                else:
                    cls._set_status(False, f"Failed to {'enable' if track else 'disable'} tracking for {button_id}")
                    
                    # Exit edit mode if we entered it
                    if not was_in_edit_mode and cls.is_edit_mode():
                        cls._app_coordinator.toggle_edit_mode()
                        
                    return False
            else:
                cls._set_status(True, f"Button {button_id} already {'tracked' if track else 'not tracked'}")
                
            # Exit edit mode if we entered it
            if not was_in_edit_mode and cls.is_edit_mode():
                cls._app_coordinator.toggle_edit_mode()
                
            return True
                
        except Exception as e:
            cls._set_status(False, f"Error toggling button tracking: {e}")
            logger.error(f"Error toggling button tracking: {e}")
            import traceback
            traceback.print_exc()
            
            # Clean up edit mode if needed
            if 'was_in_edit_mode' in locals() and not was_in_edit_mode:
                try:
                    if cls.is_edit_mode():
                        cls._app_coordinator.toggle_edit_mode()
                except:
                    pass
                
            return False
    
    @classmethod
    def toggle_fullscreen(cls) -> bool:
        """
        Toggle fullscreen mode.
        
        Returns:
            bool: True if successful
        """
        if not cls._check_initialized():
            return False
            
        try:
            # Send signal to toggle fullscreen
            cls._ui_manager.toggle_fullscreen.emit()
            cls._set_status(True, "Toggled fullscreen mode")
            return True
        except Exception as e:
            cls._set_status(False, f"Error toggling fullscreen: {e}")
            logger.error(f"Error toggling fullscreen: {e}")
            return False
    
    @classmethod
    def get_application_state(cls) -> Dict[str, Any]:
        """
        Get comprehensive application state.
        
        Returns:
            Dict with application state
        """
        if not cls._check_initialized():
            return {"error": "API not initialized"}
            
        try:
            # Get collector information
            collector_type = cls._collector_manager.get_current_collector_type()
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
            active_keys = cls._collector_manager.get_active_keys()
            
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
