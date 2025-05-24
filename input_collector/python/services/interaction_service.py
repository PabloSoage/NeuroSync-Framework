"""
Interaction service module.

Provides service-layer interfaces for controlling and interacting with
the input collector application components.
"""
from typing import Dict, List, Optional, Any, Tuple, Callable, Set
import threading
import logging
import time
from ..core.event_system import EventType, dispatch

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
        """Get or create the singleton instance of the service."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = InteractionService()
            return cls._instance
    
    def __init__(self):
        """Initialize the interaction service."""
        self._components = {}
        self._last_status = {"success": False, "message": "Service not initialized"}
        self._initialized = False
        logging.info("Interaction service initialized")
    
    def register_component(self, component_name: str, component: Any) -> None:
        """
        Register an application component with the service.
        
        Args:
            component_name: Name of the component (e.g., 'app_coordinator')
            component: The component instance
        """
        self._components[component_name] = component
        logging.info(f"Component '{component_name}' registered with interaction service")
    
    def get_component(self, component_name: str) -> Any:
        """
        Get a registered component by name.
        
        Args:
            component_name: Name of the component to retrieve
            
        Returns:
            The component instance or None if not found
        """
        return self._components.get(component_name)
    
    def initialize(self, components: Dict[str, Any]) -> bool:
        """
        Initialize the service with application components.
        
        Args:
            components: Dictionary of components to register
            
        Returns:
            bool: True if successful
        """
        try:
            # Register all components
            for name, component in components.items():
                self.register_component(name, component)
                
            self._initialized = True
            self._set_status(True, "Service initialized successfully")
            return True
        except Exception as e:
            self._set_status(False, f"Failed to initialize service: {e}")
            logging.error(f"Failed to initialize interaction service: {e}")
            return False
    
    def _set_status(self, success: bool, message: str) -> None:
        """
        Set the status of the last operation.
        
        Args:
            success: Whether the operation was successful
            message: Status message
        """
        self._last_status = {"success": success, "message": message}
        log_level = logging.INFO if success else logging.ERROR
        logging.log(log_level, f"Interaction status: {message}")
    
    def get_last_status(self) -> Dict[str, Any]:
        """
        Get the status of the last operation.
        
        Returns:
            Dict with status information
        """
        return self._last_status
    
    def _check_initialized(self) -> bool:
        """
        Check if the service is initialized.
        
        Returns:
            bool: True if initialized
        """
        if not self._initialized:
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
            app_coordinator = self.get_component('app_coordinator')
            if not app_coordinator:
                self._set_status(False, "App coordinator not available")
                return False
                
            # Check if already recording
            if app_coordinator.is_recording:
                self._set_status(False, "Already recording")
                return False
                
            # Check for edit mode
            if app_coordinator.edit_mode:
                self._set_status(False, "Cannot start recording while in edit mode")
                return False
                
            # Toggle recording (start)
            app_coordinator.toggle_recording()
            
            # Verify recording started
            if app_coordinator.is_recording:
                self._set_status(True, "Recording started")
                return True
            else:
                self._set_status(False, "Failed to start recording")
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
            app_coordinator = self.get_component('app_coordinator')
            if not app_coordinator:
                self._set_status(False, "App coordinator not available")
                return False
                
            # Check if currently recording
            if not app_coordinator.is_recording:
                self._set_status(False, "Not currently recording")
                return False
                
            # Toggle recording (stop)
            app_coordinator.toggle_recording()
            
            # Verify recording stopped
            if not app_coordinator.is_recording:
                self._set_status(True, "Recording stopped")
                return True
            else:
                self._set_status(False, "Failed to stop recording")
                return False
                
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
            app_coordinator = self.get_component('app_coordinator')
            if not app_coordinator:
                self._set_status(False, "App coordinator not available")
                return False
                
            # Store previous recording state
            prev_state = app_coordinator.is_recording
            
            # Toggle recording
            app_coordinator.toggle_recording()
            
            # Check if state changed
            current_state = app_coordinator.is_recording
            if current_state != prev_state:
                new_state = "started" if current_state else "stopped"
                self._set_status(True, f"Recording {new_state}")
                return True
            else:
                # If state didn't change, there was likely an error
                self._set_status(False, "Failed to toggle recording")
                return False
                
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
            
        app_coordinator = self.get_component('app_coordinator')
        if not app_coordinator:
            return False
            
        return app_coordinator.is_recording
    
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
            logging_manager = self.get_component('logging_manager')
            if not logging_manager:
                self._set_status(False, "Logging manager not available")
                return False
                
            success = logging_manager.set_json_logging(enabled)
            if success:
                self._set_status(True, f"JSON logging {'enabled' if enabled else 'disabled'}")
            else:
                self._set_status(False, f"Failed to {'enable' if enabled else 'disable'} JSON logging")
            return success
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
            logging_manager = self.get_component('logging_manager')
            ui_manager = self.get_component('ui_manager')
            
            if not logging_manager:
                self._set_status(False, "Logging manager not available")
                return False
                
            # If enabling and filepath is provided, set it first
            if enabled and filepath and logging_manager.csv_logger:
                logging_manager.csv_logger.set_filepath(filepath)
                if ui_manager:
                    ui_manager.set_csv_path(filepath)
                
            # Enable/disable CSV logging
            success = logging_manager.set_csv_logging(enabled)
            if success:
                self._set_status(True, f"CSV logging {'enabled' if enabled else 'disabled'}")
            else:
                self._set_status(False, f"Failed to {'enable' if enabled else 'disable'} CSV logging")
            return success
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
            logging_manager = self.get_component('logging_manager')
            ui_manager = self.get_component('ui_manager')
            
            if not logging_manager or not logging_manager.csv_logger:
                self._set_status(False, "Logging manager or CSV logger not available")
                return False
                
            logging_manager.csv_logger.set_filepath(filepath)
            
            if ui_manager:
                ui_manager.set_csv_path(filepath)
                
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
            Dict with logging state information
        """
        if not self._check_initialized():
            return {"error": "Service not initialized"}
            
        try:
            logging_manager = self.get_component('logging_manager')
            if not logging_manager:
                return {"error": "Logging manager not available"}
                
            return {
                "json_logging_enabled": logging_manager.log_to_json,
                "csv_logging_enabled": logging_manager.log_to_csv,
                "csv_path": logging_manager.csv_logger.filepath if logging_manager.csv_logger else ""
            }
        except Exception as e:
            logging.error(f"Error getting logging state: {e}")
            return {"error": str(e)}
    
    #
    # Collector management methods
    #
    
    def get_available_collectors(self) -> List[Dict[str, str]]:
        """
        Get list of available collectors.
        
        Returns:
            List of collector information dictionaries
        """
        if not self._check_initialized():
            return []
            
        try:
            collector_manager = self.get_component('collector_manager')
            if not collector_manager:
                return []
                
            return collector_manager.get_available_collectors()
        except Exception as e:
            logging.error(f"Error getting available collectors: {e}")
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
            app_coordinator = self.get_component('app_coordinator')
            collector_manager = self.get_component('collector_manager')
            
            if not app_coordinator or not collector_manager:
                self._set_status(False, "Required components not available")
                return False
                
            # Get current collector type for comparison
            prev_collector = collector_manager.get_current_collector_type()
            
            # Special handling for PS4 controller
            if collector_type == "ps4_controller":
                # Check if PS4 collector is available
                ps4_collector = collector_manager.get_collector("ps4_controller")
                if not ps4_collector:
                    self._set_status(False, "PS4 controller support not available")
                    return False
                    
                # Check if a controller is already connected
                if not ps4_collector.controller:
                    # Scan for controllers
                    self._set_status(True, "Scanning for controllers...")
                    controllers = ps4_collector.scan_controllers()
                    if not controllers:
                        self._set_status(False, "No controllers found, falling back to keyboard/mouse")
                        # Switch to keyboard/mouse instead
                        app_coordinator.switch_collector("keyboard_mouse")
                        return False
                        
                    self._set_status(True, f"Found {len(controllers)} controller(s), connecting to first one")
                    # Connect to first controller
                    success = ps4_collector.connect_to_controller(controllers[0]["index"])
                    if not success:
                        self._set_status(False, "Failed to connect to controller, falling back to keyboard/mouse")
                        # Switch to keyboard/mouse instead
                        app_coordinator.switch_collector("keyboard_mouse")
                        return False
            
            # Switch collector using the app coordinator
            app_coordinator.switch_collector(collector_type)
            
            # Verify switch was successful by checking current collector type
            current_collector = collector_manager.get_current_collector_type()
            if current_collector == collector_type:
                collector_name = collector_manager._get_collector_display_name(collector_type)
                self._set_status(True, f"Switched to {collector_name} collector")
                return True
            else:
                self._set_status(False, f"Failed to switch to {collector_type} collector")
                return False
                
        except Exception as e:
            self._set_status(False, f"Error switching collector: {e}")
            logging.error(f"Error switching collector: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_current_collector(self) -> Dict[str, Any]:
        """
        Get information about the current collector.
        
        Returns:
            Dict with collector information
        """
        if not self._check_initialized():
            return {"error": "Service not initialized"}
            
        try:
            collector_manager = self.get_component('collector_manager')
            if not collector_manager:
                return {"error": "Collector manager not available"}
                
            collector_type = collector_manager.get_current_collector_type()
            capabilities = collector_manager.get_current_collector_capabilities()
            
            return {
                "type": collector_type,
                "name": collector_manager._get_collector_display_name(collector_type),
                "capabilities": capabilities
            }
        except Exception as e:
            logging.error(f"Error getting current collector: {e}")
            return {"error": str(e)}
    
    def scan_controllers(self) -> List[Dict[str, Any]]:
        """
        Scan for available controllers.
        
        Returns:
            List of controller information dictionaries
        """
        if not self._check_initialized():
            return []
            
        try:
            collector_manager = self.get_component('collector_manager')
            if not collector_manager:
                return []
                
            ps4_collector = collector_manager.get_collector("ps4_controller")
            if ps4_collector:
                return ps4_collector.scan_controllers()
            return []
        except Exception as e:
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
            collector_manager = self.get_component('collector_manager')
            if not collector_manager:
                self._set_status(False, "Collector manager not available")
                return False
                
            ps4_collector = collector_manager.get_collector("ps4_controller")
            if ps4_collector:
                success = ps4_collector.connect_to_controller(index)
                if success:
                    self._set_status(True, "Connected to controller")
                    # Switch to PS4 controller
                    self.switch_collector("ps4_controller")
                else:
                    self._set_status(False, "Failed to connect to controller")
                return success
            else:
                self._set_status(False, "PS4 collector not available")
                return False
                
        except Exception as e:
            self._set_status(False, f"Error connecting to controller: {e}")
            logging.error(f"Error connecting to controller: {e}")
            return False
