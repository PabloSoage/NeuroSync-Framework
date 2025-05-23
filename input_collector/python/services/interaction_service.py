"""
Interaction service module.

Provides service-layer interfaces for controlling and interacting with
the input collector application components.
"""

import logging
import threading
from typing import Dict, List, Optional, Any, Tuple, Callable, Set

# Import necessary components
from ..app.app_coordinator import AppCoordinator
from ..ui.ui_manager import UIManager
from ..logging.logging_manager import LoggingManager
from ..collectors.collector_manager import CollectorManager

class InteractionService:
    """
    Service for controlling and interacting with the input collector application.
    
    This service provides methods to interact with the various components of the 
    application, allowing external control of recording, configuration, and other
    key functionality.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the service."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = InteractionService()
            return cls._instance
    
    def __init__(self):
        """Initialize the interaction service."""
        # Component references - will be set externally
        self._app_coordinator = None
        self._ui_manager = None
        self._logging_manager = None
        self._collector_manager = None
        self._event_processor = None
        
        self._is_initialized = False
        
        # Last operation status
        self._last_status = {
            "success": True,
            "message": "Service initialized"
        }
        
        logging.info("Interaction service initialized")
    
    def initialize(self, app_coordinator: AppCoordinator, ui_manager: UIManager, 
                 logging_manager: LoggingManager, collector_manager: CollectorManager,
                 event_processor: Any) -> bool:
        """
        Initialize the service with application components.
        
        Args:
            app_coordinator: Application coordinator
            ui_manager: UI manager
            logging_manager: Logging manager
            collector_manager: Collector manager
            event_processor: Event processor
            
        Returns:
            bool: True if successful
        """
        if self._is_initialized:
            self._set_status(False, "Service already initialized")
            return False
            
        try:
            self._app_coordinator = app_coordinator
            self._ui_manager = ui_manager
            self._logging_manager = logging_manager
            self._collector_manager = collector_manager
            self._event_processor = event_processor
            
            self._is_initialized = True
            self._set_status(True, "Service initialized successfully")
            return True
        except Exception as e:
            self._set_status(False, f"Initialization error: {e}")
            logging.error(f"Failed to initialize interaction service: {e}")
            return False
    
    def _set_status(self, success: bool, message: str) -> None:
        """
        Set the last operation status.
        
        Args:
            success: Whether the operation was successful
            message: Status message
        """
        self._last_status = {
            "success": success,
            "message": message
        }
        logging.info(f"Interaction status: {message} ({'success' if success else 'failed'})")
    
    def get_last_status(self) -> Dict[str, Any]:
        """
        Get the last operation status.
        
        Returns:
            Dict[str, Any]: Status dictionary with 'success' and 'message' keys
        """
        return self._last_status.copy()
    
    def _check_initialized(self) -> bool:
        """
        Check if the service is initialized.
        
        Returns:
            bool: True if initialized
        """
        if not self._is_initialized:
            self._set_status(False, "Service not initialized")
            return False
        return True
    
    #
    # Recording control methods
    #
    
    def start_recording(self) -> bool:
        """
        Start recording input events.
        
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            # Check if already recording
            if self._app_coordinator.is_recording:
                self._set_status(False, "Already recording")
                return False
                
            # Make sure not in edit mode
            if self._app_coordinator.edit_mode:
                self._set_status(False, "Cannot start recording while in edit mode")
                return False
                
            # Start recording using thread-safe call
            # This is critical - we must use Qt's thread-safe method invocation
            from PyQt5.QtCore import QMetaObject, Qt
            
            # Store the previous recording state
            prev_state = self._app_coordinator.is_recording
            
            try:
                # Use the simpler form of invokeMethod without result_callback
                QMetaObject.invokeMethod(
                    self._app_coordinator,
                    "_toggle_recording_proxy",
                    Qt.BlockingQueuedConnection
                )
                
                # After the method returns, check if state changed
                current_state = self._app_coordinator.is_recording
                recording_started = (not prev_state) and current_state
                
                if recording_started:
                    self._set_status(True, "Recording started")
                    return True
                else:
                    self._set_status(False, "Failed to start recording")
                    return False
                    
            except Exception as e:
                # Try direct call as fallback
                self._app_coordinator.toggle_recording()
                
                # Check if recording state changed
                current_state = self._app_coordinator.is_recording
                recording_started = (not prev_state) and current_state
                
                if recording_started:
                    self._set_status(True, "Recording started")
                    return True
                else:
                    self._set_status(False, f"Failed to start recording: {e}")
                    return False
                
        except Exception as e:
            self._set_status(False, f"Error starting recording: {e}")
            logging.error(f"Error starting recording: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stop_recording(self) -> bool:
        """
        Stop recording input events.
        
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            # Check if currently recording
            if not self._app_coordinator.is_recording:
                self._set_status(False, "Not currently recording")
                return False
                
            # Store the previous recording state
            prev_state = self._app_coordinator.is_recording
            
            try:
                # Use the simpler form of invokeMethod without result_callback
                from PyQt5.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(
                    self._app_coordinator,
                    "_toggle_recording_proxy",
                    Qt.BlockingQueuedConnection
                )
                
                # After the method returns, check if state changed
                current_state = self._app_coordinator.is_recording
                recording_stopped = prev_state and (not current_state)
                
                if recording_stopped:
                    self._set_status(True, "Recording stopped")
                    return True
                else:
                    self._set_status(False, "Failed to stop recording")
                    return False
                    
            except Exception as e:
                # Try direct call as fallback
                self._app_coordinator.toggle_recording()
                
                # Check if recording state changed
                current_state = self._app_coordinator.is_recording
                recording_stopped = prev_state and (not current_state)
                
                if recording_stopped:
                    self._set_status(True, "Recording stopped")
                    return True
                else:
                    self._set_status(False, f"Failed to stop recording: {e}")
                    return False
                
        except Exception as e:
            self._set_status(False, f"Error stopping recording: {e}")
            logging.error(f"Error stopping recording: {e}")
            import traceback
            traceback.print_exc()
            return False

    def toggle_recording(self) -> bool:
        """
        Toggle recording state.
        
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            # Store previous recording state
            prev_state = self._app_coordinator.is_recording
            
            try:
                # Use the simpler form of invokeMethod without result_callback
                from PyQt5.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(
                    self._app_coordinator,
                    "_toggle_recording_proxy",
                    Qt.BlockingQueuedConnection
                )
                
                # After the method returns, check if state changed
                current_state = self._app_coordinator.is_recording
                state_changed = prev_state != current_state
                
                if state_changed:
                    new_state = "started" if current_state else "stopped"
                    self._set_status(True, f"Recording {new_state}")
                    return True
                else:
                    self._set_status(False, "Failed to toggle recording")
                    return False
                    
            except Exception as e:
                # Try direct call as fallback
                self._app_coordinator.toggle_recording()
                
                # Check if state changed
                current_state = self._app_coordinator.is_recording
                state_changed = prev_state != current_state
                
                if state_changed:
                    new_state = "started" if current_state else "stopped"
                    self._set_status(True, f"Recording {new_state}")
                    return True
                else:
                    self._set_status(False, f"Failed to toggle recording: {e}")
                    return False
                
        except Exception as e:
            self._set_status(False, f"Error toggling recording: {e}")
            logging.error(f"Error toggling recording: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def is_recording(self) -> bool:
        """
        Check if recording is active.
        
        Returns:
            bool: True if recording is active
        """
        if not self._check_initialized():
            return False
        return self._app_coordinator.is_recording
    
    #
    # Logging configuration methods
    #
    
    def enable_json_logging(self, enabled: bool = True) -> bool:
        """
        Enable or disable JSON logging.
        
        Args:
            enabled: Whether to enable JSON logging
            
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            result = self._logging_manager.set_json_logging(enabled)
            
            if result:
                state = "enabled" if enabled else "disabled"
                self._set_status(True, f"JSON logging {state}")
            else:
                self._set_status(False, f"Failed to {'' if enabled else 'dis'}able JSON logging")
                
            return result
        except Exception as e:
            self._set_status(False, f"Error configuring JSON logging: {e}")
            logging.error(f"Error configuring JSON logging: {e}")
            return False
    
    def enable_csv_logging(self, enabled: bool = True, filepath: Optional[str] = None) -> bool:
        """
        Enable or disable CSV logging.
        
        Args:
            enabled: Whether to enable CSV logging
            filepath: Path for CSV file (required when enabling if not previously set)
            
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            # If enabling CSV logging, make sure we have a file path
            if enabled and filepath:
                self._logging_manager.csv_logger.set_filepath(filepath)
                if hasattr(self._ui_manager, 'set_csv_path'):
                    self._ui_manager.set_csv_path(filepath)
                    
            # Set logging state
            result = self._logging_manager.set_csv_logging(enabled)
            
            if result:
                state = "enabled" if enabled else "disabled"
                path_info = f" to {filepath}" if enabled and filepath else ""
                self._set_status(True, f"CSV logging {state}{path_info}")
            else:
                self._set_status(False, f"Failed to {'' if enabled else 'dis'}able CSV logging")
                
            return result
        except Exception as e:
            self._set_status(False, f"Error configuring CSV logging: {e}")
            logging.error(f"Error configuring CSV logging: {e}")
            return False
    
    def set_csv_path(self, filepath: str) -> bool:
        """
        Set the CSV logging file path.
        
        Args:
            filepath: Path for CSV file
            
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            self._logging_manager.csv_logger.set_filepath(filepath)
            if hasattr(self._ui_manager, 'set_csv_path'):
                self._ui_manager.set_csv_path(filepath)
                
            self._set_status(True, f"CSV path set to {filepath}")
            return True
        except Exception as e:
            self._set_status(False, f"Error setting CSV path: {e}")
            logging.error(f"Error setting CSV path: {e}")
            return False
    
    def get_logging_state(self) -> Dict[str, Any]:
        """
        Get current logging configuration.
        
        Returns:
            Dict[str, Any]: Dictionary with logging state
        """
        if not self._check_initialized():
            return {"error": "Service not initialized"}
            
        try:
            return {
                "json_logging": self._logging_manager.log_to_json,
                "csv_logging": self._logging_manager.log_to_csv,
                "csv_path": self._logging_manager.csv_logger.filepath if hasattr(
                    self._logging_manager.csv_logger, 'filepath') else None
            }
        except Exception as e:
            self._set_status(False, f"Error getting logging state: {e}")
            logging.error(f"Error getting logging state: {e}")
            return {"error": str(e)}
    
    #
    # Collector management methods
    #
    
    def get_available_collectors(self) -> List[Dict[str, str]]:
        """
        Get list of available collectors.
        
        Returns:
            List[Dict[str, str]]: List of collector information dictionaries
        """
        if not self._check_initialized():
            return []
            
        try:
            collectors = self._collector_manager.get_available_collectors()
            self._set_status(True, f"Found {len(collectors)} available collectors")
            return collectors
        except Exception as e:
            self._set_status(False, f"Error getting collectors: {e}")
            logging.error(f"Error getting collectors: {e}")
            return []
    
    def switch_collector(self, collector_type: str) -> bool:
        """
        Switch to a different input collector.
        
        Args:
            collector_type: Type identifier for the collector
            
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            # Stop recording if active
            was_recording = self._app_coordinator.is_recording
            if was_recording:
                self._app_coordinator.toggle_recording()
                
            # Switch collector
            self._app_coordinator.switch_collector(collector_type)
            
            # Verify the switch
            current_type = self._collector_manager.get_current_collector_type()
            if current_type == collector_type:
                self._set_status(True, f"Switched to {collector_type} collector")
                return True
            else:
                self._set_status(False, f"Failed to switch to {collector_type} collector")
                return False
        except Exception as e:
            self._set_status(False, f"Error switching collector: {e}")
            logging.error(f"Error switching collector: {e}")
            return False
    
    def get_current_collector(self) -> Dict[str, Any]:
        """
        Get information about the current collector.
        
        Returns:
            Dict[str, Any]: Collector information
        """
        if not self._check_initialized():
            return {"error": "Service not initialized"}
            
        try:
            collector_type = self._collector_manager.get_current_collector_type()
            capabilities = self._collector_manager.get_current_collector_capabilities()
            
            return {
                "type": collector_type,
                "name": self._collector_manager._get_collector_display_name(collector_type),
                "capabilities": capabilities
            }
        except Exception as e:
            self._set_status(False, f"Error getting current collector: {e}")
            logging.error(f"Error getting current collector: {e}")
            return {"error": str(e)}
    
    def scan_controllers(self) -> List[Dict[str, Any]]:
        """
        Scan for available controllers.
        
        Returns:
            List[Dict[str, Any]]: List of controller information
        """
        if not self._check_initialized():
            return []
            
        try:
            ps4_collector = self._collector_manager.get_collector("ps4_controller")
            if not ps4_collector:
                self._set_status(False, "PS4 collector not available")
                return []
                
            controllers = ps4_collector.scan_controllers()
            
            self._set_status(True, f"Found {len(controllers)} controllers")
            return controllers
        except Exception as e:
            self._set_status(False, f"Error scanning controllers: {e}")
            logging.error(f"Error scanning controllers: {e}")
            return []
    
    def connect_controller(self, index: int) -> bool:
        """
        Connect to a specific controller by index.
        
        Args:
            index: Controller index from scan_controllers()
            
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            ps4_collector = self._collector_manager.get_collector("ps4_controller")
            if not ps4_collector:
                self._set_status(False, "PS4 collector not available")
                return False
                
            success = ps4_collector.connect_to_controller(index)
            
            if success:
                self._set_status(True, f"Connected to controller {index}")
                
                # Switch to PS4 collector if connection successful
                if self._collector_manager.get_current_collector_type() != "ps4_controller":
                    self.switch_collector("ps4_controller")
            else:
                self._set_status(False, f"Failed to connect to controller {index}")
                
            return success
        except Exception as e:
            self._set_status(False, f"Error connecting to controller: {e}")
            logging.error(f"Error connecting to controller: {e}")
            return False
    
    #
    # Mouse tracking configuration methods
    #
    
    def set_mouse_tracking_mode(self, mode: str, direction_only: bool = None) -> bool:
        """
        Set the mouse tracking mode.
        
        Args:
            mode: The tracking mode to use ("joystick", "delta", "angle", "axis")
            direction_only: Whether to use direction-only mode
            
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            # Get current direction only setting if not specified
            if direction_only is None:
                direction_only = self._ui_manager.is_direction_only_mode()
                
            # Update UI first
            if direction_only is not None:
                self._ui_manager.set_direction_only_mode(direction_only)
                
            self._ui_manager.set_tracking_mode(mode)
            
            # Apply via coordinator
            self._app_coordinator.set_mouse_tracking_mode(mode)
            
            mode_desc = mode + (" (direction-only)" if direction_only else "")
            self._set_status(True, f"Mouse tracking mode set to {mode_desc}")
            return True
        except Exception as e:
            self._set_status(False, f"Error setting mouse tracking mode: {e}")
            logging.error(f"Error setting mouse tracking mode: {e}")
            return False
    
    def set_mouse_settings(self, delta_smoothing: Optional[float] = None, 
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
        if not self._check_initialized():
            return False
            
        try:
            # Update UI settings
            if delta_smoothing is not None:
                self._ui_manager.set_delta_smoothing(delta_smoothing)
                
            if joystick_sensitivity is not None:
                self._ui_manager.set_joystick_sensitivity(joystick_sensitivity)
                
            if angle_grouping is not None:
                self._ui_manager.set_angle_grouping(angle_grouping)
                
            # Apply settings
            self._app_coordinator.apply_mouse_settings()
            
            self._set_status(True, "Mouse settings updated")
            return True
        except Exception as e:
            self._set_status(False, f"Error setting mouse settings: {e}")
            logging.error(f"Error setting mouse settings: {e}")
            return False
    
    def get_mouse_settings(self) -> Dict[str, Any]:
        """
        Get current mouse tracking settings.
        
        Returns:
            Dict[str, Any]: Dictionary with mouse settings
        """
        if not self._check_initialized():
            return {"error": "Service not initialized"}
            
        try:
            return {
                "tracking_mode": self._ui_manager.get_tracking_mode(),
                "direction_only": self._ui_manager.is_direction_only_mode(),
                "delta_smoothing": self._ui_manager.get_delta_smoothing(),
                "joystick_sensitivity": self._ui_manager.get_joystick_sensitivity(),
                "angle_grouping": self._ui_manager.get_angle_grouping()
            }
        except Exception as e:
            self._set_status(False, f"Error getting mouse settings: {e}")
            logging.error(f"Error getting mouse settings: {e}")
            return {"error": str(e)}
    
    #
    # Key tracking methods
    #
    
    def get_tracked_keys(self) -> List[str]:
        """
        Get the list of currently tracked keys.
        
        Returns:
            List[str]: List of tracked keys
        """
        if not self._check_initialized():
            return []
            
        try:
            tracked_keys = self._app_coordinator.get_tracked_keys()
            self._set_status(True, f"Retrieved {len(tracked_keys)} tracked keys")
            return tracked_keys
        except Exception as e:
            self._set_status(False, f"Error getting tracked keys: {e}")
            logging.error(f"Error getting tracked keys: {e}")
            return []
    
    def toggle_edit_mode(self) -> bool:
        """
        Toggle key/button edit mode.
        
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            # Check if recording (cannot edit while recording)
            if self._app_coordinator.is_recording:
                self._set_status(False, "Cannot enter edit mode while recording")
                return False
                
            # Toggle edit mode
            prev_state = self._app_coordinator.edit_mode
            self._app_coordinator.toggle_edit_mode()
            
            # Check if state changed
            if prev_state != self._app_coordinator.edit_mode:
                new_state = "enabled" if self._app_coordinator.edit_mode else "disabled"
                self._set_status(True, f"Edit mode {new_state}")
                return True
            else:
                self._set_status(False, "Failed to toggle edit mode")
                return False
        except Exception as e:
            self._set_status(False, f"Error toggling edit mode: {e}")
            logging.error(f"Error toggling edit mode: {e}")
            return False
    
    def is_edit_mode(self) -> bool:
        """
        Check if edit mode is active.
        
        Returns:
            bool: True if edit mode is active
        """
        if not self._check_initialized():
            return False
        return self._app_coordinator.edit_mode
    
    def add_tracked_key(self, key: str) -> bool:
        """
        Add a key to the tracked keys list.
        
        Args:
            key: Key to add
            
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            # Check if already in edit mode
            if not self._app_coordinator.edit_mode:
                self._set_status(False, "Must be in edit mode to add keys")
                return False
                
            # Normalize key name
            if key.lower() == "space":
                key = "Key.space"
            elif key.lower() == "shift":
                key = "Key.shift"
            elif key.lower() == "f9":
                key = "Key.media_play_pause"
                
            # Check if already tracked
            tracked_keys = self._app_coordinator.get_tracked_keys()
            if any(k.lower() == key.lower() for k in tracked_keys):
                self._set_status(False, f"Key '{key}' is already tracked")
                return False
                
            # Add key via edit handler
            self._app_coordinator.handle_key_edit(key)
            
            # Verify key was added
            new_tracked_keys = self._app_coordinator.get_tracked_keys()
            if any(k.lower() == key.lower() for k in new_tracked_keys):
                self._set_status(True, f"Added key '{key}' to tracked keys")
                return True
            else:
                self._set_status(False, f"Failed to add key '{key}'")
                return False
        except Exception as e:
            self._set_status(False, f"Error adding tracked key: {e}")
            logging.error(f"Error adding tracked key: {e}")
            return False
    
    def remove_tracked_key(self, key: str) -> bool:
        """
        Remove a key from the tracked keys list.
        
        Args:
            key: Key to remove
            
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            # Check if in edit mode
            if not self._app_coordinator.edit_mode:
                self._set_status(False, "Must be in edit mode to remove keys")
                return False
                
            # Normalize key name
            if key.lower() == "space":
                key = "Key.space"
            elif key.lower() == "shift":
                key = "Key.shift"
            elif key.lower() == "f9":
                key = "Key.media_play_pause"
                
            # Check if this is F9/media key which cannot be removed
            if key.lower() == "key.media_play_pause".lower():
                self._set_status(False, "Cannot remove F9/media_play_pause key")
                return False
                
            # Check if key is tracked
            tracked_keys = self._app_coordinator.get_tracked_keys()
            if not any(k.lower() == key.lower() for k in tracked_keys):
                self._set_status(False, f"Key '{key}' is not currently tracked")
                return False
                
            # Remove key via edit handler
            self._app_coordinator.handle_key_edit(key)
            
            # Verify key was removed
            new_tracked_keys = self._app_coordinator.get_tracked_keys()
            if not any(k.lower() == key.lower() for k in new_tracked_keys):
                self._set_status(True, f"Removed key '{key}' from tracked keys")
                return True
            else:
                self._set_status(False, f"Failed to remove key '{key}'")
                return False
        except Exception as e:
            self._set_status(False, f"Error removing tracked key: {e}")
            logging.error(f"Error removing tracked key: {e}")
            return False
    
    def toggle_button_tracking(self, button_id: str, track: bool) -> bool:
        """
        Toggle tracking for a mouse button.
        
        Args:
            button_id: Button identifier ("Button.left", "Button.right", "Button.scroll")
            track: Whether to track the button
            
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            # Check if in edit mode
            if not self._app_coordinator.edit_mode:
                self._set_status(False, "Must be in edit mode to change button tracking")
                return False
                
            # Toggle button tracking
            self._app_coordinator.handle_button_edit(button_id, track)
            
            # Verify tracking state
            tracked_keys = self._app_coordinator.get_tracked_keys()
            is_tracked = button_id in tracked_keys
            
            if is_tracked == track:
                action = "Added" if track else "Removed"
                self._set_status(True, f"{action} tracking for {button_id}")
                return True
            else:
                self._set_status(False, f"Failed to {'add' if track else 'remove'} tracking for {button_id}")
                return False
        except Exception as e:
            self._set_status(False, f"Error toggling button tracking: {e}")
            logging.error(f"Error toggling button tracking: {e}")
            return False
    
    #
    # UI control methods
    #
    
    def toggle_fullscreen(self) -> bool:
        """
        Toggle fullscreen mode.
        
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            # Use the UI manager's toggle_fullscreen signal
            self._ui_manager.toggle_fullscreen.emit()
            self._set_status(True, "Toggled fullscreen mode")
            return True
        except Exception as e:
            self._set_status(False, f"Error toggling fullscreen: {e}")
            logging.error(f"Error toggling fullscreen: {e}")
            return False
    
    def get_application_state(self) -> Dict[str, Any]:
        """
        Get a comprehensive dictionary of application state.
        
        Returns:
            Dict[str, Any]: Application state
        """
        if not self._check_initialized():
            return {"error": "Service not initialized"}
            
        try:
            # Get state from various components
            collector_info = self.get_current_collector()
            logging_state = self.get_logging_state()
            mouse_settings = self.get_mouse_settings()
            tracked_keys = self.get_tracked_keys()
            
            return {
                "recording": self.is_recording(),
                "edit_mode": self.is_edit_mode(),
                "collector": collector_info,
                "logging": logging_state,
                "mouse_settings": mouse_settings,
                "tracked_keys": tracked_keys,
                "tracked_key_count": len(tracked_keys),
                "status": self.get_last_status()
            }
        except Exception as e:
            self._set_status(False, f"Error getting application state: {e}")
            logging.error(f"Error getting application state: {e}")
            return {"error": str(e)}
