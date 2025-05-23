"""
Interaction service module.

Provides service-layer interfaces for controlling and interacting with
the input collector application components.
"""

import logging
import threading
from typing import Dict, List, Optional, Any, Tuple, Callable, Set

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
        self._component_registry = {}
        
        self._is_initialized = False
        
        # Last operation status
        self._last_status = {
            "success": True,
            "message": "Service initialized"
        }
        
        logging.info("Interaction service initialized")
    
    def register_component(self, component_name: str, component: Any) -> None:
        """
        Register a component with the service.
        
        Args:
            component_name: Name of the component
            component: Component instance
        """
        self._component_registry[component_name] = component
    
    def get_component(self, component_name: str) -> Any:
        """
        Get a registered component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            Component instance or None if not found
        """
        return self._component_registry.get(component_name)
    
    def initialize(self, components: Dict[str, Any]) -> bool:
        """
        Initialize the service with application components.
        
        Args:
            components: Dictionary of components
            
        Returns:
            bool: True if successful
        """
        if self._is_initialized:
            self._set_status(False, "Service already initialized")
            return False
            
        try:
            for name, component in components.items():
                self.register_component(name, component)
            
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return False
                
            result = adapter.start_recording()
            if result:
                self._set_status(True, "Recording started")
            else:
                self._set_status(False, "Failed to start recording")
            return result
        except Exception as e:
            self._set_status(False, f"Error starting recording: {e}")
            logging.error(f"Error starting recording: {e}")
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return False
                
            result = adapter.stop_recording()
            if result:
                self._set_status(True, "Recording stopped")
            else:
                self._set_status(False, "Failed to stop recording")
            return result
        except Exception as e:
            self._set_status(False, f"Error stopping recording: {e}")
            logging.error(f"Error stopping recording: {e}")
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return False
                
            result, is_recording = adapter.toggle_recording()
            if result:
                state = "started" if is_recording else "stopped"
                self._set_status(True, f"Recording {state}")
            else:
                self._set_status(False, "Failed to toggle recording")
            return result
        except Exception as e:
            self._set_status(False, f"Error toggling recording: {e}")
            logging.error(f"Error toggling recording: {e}")
            return False
    
    def is_recording(self) -> bool:
        """
        Check if recording is active.
        
        Returns:
            bool: True if recording is active
        """
        if not self._check_initialized():
            return False
            
        try:
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return False
                
            return adapter.is_recording()
        except Exception as e:
            self._set_status(False, f"Error checking recording state: {e}")
            logging.error(f"Error checking recording state: {e}")
            return False
    
    #
    # Logging configuration methods
    #
    
    def enable_json_logging(self, enabled: bool = True) -> bool:
        """
        Enable or disable JSON logging.
        
        Args:
            enabled: Whether to enable JSON logging
            
        Returns:
            bool: True if the operation was successful
        """
        if not self._check_initialized():
            return False
            
        try:
            logging_manager = self.get_component("logging_manager")
            if not logging_manager:
                self._set_status(False, "Logging manager not available")
                return False
                
            result = logging_manager.set_json_logging(enabled)
            
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
            bool: True if the operation was successful
        """
        if not self._check_initialized():
            return False
            
        try:
            logging_manager = self.get_component("logging_manager")
            if not logging_manager:
                self._set_status(False, "Logging manager not available")
                return False
                
            # If enabling CSV logging, make sure we have a file path
            if enabled and filepath:
                logging_manager.csv_logger.set_filepath(filepath)
                
                # Update UI as well via adapter
                adapter = self.get_component("ui_adapter")
                if adapter:
                    adapter.set_csv_path(filepath)
                    
            # Set logging state
            result = logging_manager.set_csv_logging(enabled)
            
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
            logging_manager = self.get_component("logging_manager")
            if not logging_manager:
                self._set_status(False, "Logging manager not available")
                return False
                
            logging_manager.csv_logger.set_filepath(filepath)
            
            # Update UI as well
            adapter = self.get_component("ui_adapter")
            if adapter:
                adapter.set_csv_path(filepath)
                
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
            logging_manager = self.get_component("logging_manager")
            if not logging_manager:
                self._set_status(False, "Logging manager not available")
                return {"error": "Logging manager not available"}
                
            return {
                "json_logging": logging_manager.log_to_json,
                "csv_logging": logging_manager.log_to_csv,
                "csv_path": logging_manager.csv_logger.filepath if hasattr(
                    logging_manager.csv_logger, 'filepath') else None
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
            collector_manager = self.get_component("collector_manager")
            if not collector_manager:
                self._set_status(False, "Collector manager not available")
                return []
                
            collectors = collector_manager.get_available_collectors()
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return False
                
            result = adapter.switch_collector(collector_type)
            if result:
                self._set_status(True, f"Switched to {collector_type} collector")
            else:
                self._set_status(False, f"Failed to switch to {collector_type} collector")
            return result
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
            collector_manager = self.get_component("collector_manager")
            if not collector_manager:
                self._set_status(False, "Collector manager not available")
                return {"error": "Collector manager not available"}
                
            collector_type = collector_manager.get_current_collector_type()
            capabilities = collector_manager.get_current_collector_capabilities()
            
            return {
                "type": collector_type,
                "name": collector_manager._get_collector_display_name(collector_type),
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return []
                
            controllers = adapter.scan_controllers()
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return False
                
            result = adapter.connect_controller(index)
            if result:
                self._set_status(True, f"Connected to controller {index}")
            else:
                self._set_status(False, f"Failed to connect to controller {index}")
            return result
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return False
                
            result = adapter.set_mouse_tracking_mode(mode, direction_only)
            if result:
                mode_desc = mode + (" (direction-only)" if direction_only else "")
                self._set_status(True, f"Mouse tracking mode set to {mode_desc}")
            else:
                self._set_status(False, f"Failed to set mouse tracking mode to {mode}")
            return result
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return False
                
            result = adapter.set_mouse_settings(
                delta_smoothing, joystick_sensitivity, angle_grouping
            )
            if result:
                self._set_status(True, "Mouse settings updated")
            else:
                self._set_status(False, "Failed to update mouse settings")
            return result
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return {"error": "UI adapter not available"}
                
            settings = adapter.get_mouse_settings()
            return settings
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return []
                
            tracked_keys = adapter.get_tracked_keys()
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return False
                
            result, is_edit_mode = adapter.toggle_edit_mode()
            if result:
                new_state = "enabled" if is_edit_mode else "disabled"
                self._set_status(True, f"Edit mode {new_state}")
            else:
                self._set_status(False, "Failed to toggle edit mode")
            return result
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
            
        try:
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return False
                
            return adapter.is_edit_mode()
        except Exception as e:
            self._set_status(False, f"Error checking edit mode: {e}")
            logging.error(f"Error checking edit mode: {e}")
            return False
    
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return False
                
            result = adapter.add_tracked_key(key)
            if result:
                self._set_status(True, f"Added key '{key}' to tracked keys")
            else:
                self._set_status(False, f"Failed to add key '{key}'")
            return result
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return False
                
            result = adapter.remove_tracked_key(key)
            if result:
                self._set_status(True, f"Removed key '{key}' from tracked keys")
            else:
                self._set_status(False, f"Failed to remove key '{key}'")
            return result
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return False
                
            result = adapter.toggle_button_tracking(button_id, track)
            if result:
                action = "Added" if track else "Removed"
                self._set_status(True, f"{action} tracking for {button_id}")
            else:
                self._set_status(False, f"Failed to {'add' if track else 'remove'} tracking for {button_id}")
            return result
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
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return False
                
            result = adapter.toggle_fullscreen()
            if result:
                self._set_status(True, "Toggled fullscreen mode")
            else:
                self._set_status(False, "Failed to toggle fullscreen mode")
            return result
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
            
            adapter = self.get_component("ui_adapter")
            if not adapter:
                self._set_status(False, "UI adapter not available")
                return {"error": "UI adapter not available"}
                
            mouse_settings = adapter.get_mouse_settings()
            tracked_keys = adapter.get_tracked_keys()
            
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
