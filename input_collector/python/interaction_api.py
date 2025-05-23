"""
Interaction API for the input collector.

This module provides a clean API for external applications to interact with
and control the input collector's functionality.
"""

from typing import Dict, List, Optional, Any, Tuple

from .services.interaction_service import InteractionService


class InputCollectorAPI:
    """
    API for controlling and interacting with the input collector application.
    
    This class provides static methods to control recording, logging,
    configuration, and other aspects of the input collector application.
    """
    
    @staticmethod
    def _get_service() -> InteractionService:
        """Get the interaction service instance."""
        return InteractionService.get_instance()
    
    @staticmethod
    def initialize(app_coordinator, ui_manager, logging_manager, 
                 collector_manager, event_processor) -> bool:
        """
        Initialize the interaction API with application components.
        
        Args:
            app_coordinator: Application coordinator
            ui_manager: UI manager
            logging_manager: Logging manager
            collector_manager: Collector manager
            event_processor: Event processor
            
        Returns:
            bool: True if initialization was successful
        """
        service = InputCollectorAPI._get_service()
        return service.initialize(
            app_coordinator, ui_manager, logging_manager, 
            collector_manager, event_processor
        )
    
    @staticmethod
    def get_last_operation_status() -> Dict[str, Any]:
        """
        Get status information about the last API operation.
        
        Returns:
            Dict[str, Any]: Status dictionary with 'success' and 'message' keys
        """
        service = InputCollectorAPI._get_service()
        return service.get_last_status()
    
    #
    # Recording control methods
    #
    
    @staticmethod
    def start_recording() -> bool:
        """
        Start recording input events.
        
        Returns:
            bool: True if successful
        """
        service = InputCollectorAPI._get_service()
        return service.start_recording()
    
    @staticmethod
    def stop_recording() -> bool:
        """
        Stop recording input events.
        
        Returns:
            bool: True if successful
        """
        service = InputCollectorAPI._get_service()
        return service.stop_recording()
    
    @staticmethod
    def toggle_recording() -> bool:
        """
        Toggle recording state.
        
        Returns:
            bool: True if successful
        """
        service = InputCollectorAPI._get_service()
        return service.toggle_recording()
    
    @staticmethod
    def is_recording() -> bool:
        """
        Check if recording is active.
        
        Returns:
            bool: True if recording is active
        """
        service = InputCollectorAPI._get_service()
        return service.is_recording()
    
    #
    # Logging configuration methods
    #
    
    @staticmethod
    def enable_json_logging(enabled: bool = True) -> bool:
        """
        Enable or disable JSON logging.
        
        Args:
            enabled: Whether to enable JSON logging
            
        Returns:
            bool: True if successful
        """
        service = InputCollectorAPI._get_service()
        return service.enable_json_logging(enabled)
    
    @staticmethod
    def enable_csv_logging(enabled: bool = True, filepath: Optional[str] = None) -> bool:
        """
        Enable or disable CSV logging.
        
        Args:
            enabled: Whether to enable CSV logging
            filepath: Path for CSV file (required when enabling if not previously set)
            
        Returns:
            bool: True if successful
        """
        service = InputCollectorAPI._get_service()
        return service.enable_csv_logging(enabled, filepath)
    
    @staticmethod
    def set_csv_path(filepath: str) -> bool:
        """
        Set the CSV logging file path.
        
        Args:
            filepath: Path for CSV file
            
        Returns:
            bool: True if successful
        """
        service = InputCollectorAPI._get_service()
        return service.set_csv_path(filepath)
    
    @staticmethod
    def get_logging_state() -> Dict[str, Any]:
        """
        Get current logging configuration.
        
        Returns:
            Dict[str, Any]: Dictionary with logging state
        """
        service = InputCollectorAPI._get_service()
        return service.get_logging_state()
    
    #
    # Collector management methods
    #
    
    @staticmethod
    def get_available_collectors() -> List[Dict[str, str]]:
        """
        Get list of available collectors.
        
        Returns:
            List[Dict[str, str]]: List of collector information dictionaries
        """
        service = InputCollectorAPI._get_service()
        return service.get_available_collectors()
    
    @staticmethod
    def switch_collector(collector_type: str) -> bool:
        """
        Switch to a different input collector.
        
        Args:
            collector_type: Type identifier for the collector
            
        Returns:
            bool: True if successful
        """
        service = InputCollectorAPI._get_service()
        return service.switch_collector(collector_type)
    
    @staticmethod
    def get_current_collector() -> Dict[str, Any]:
        """
        Get information about the current collector.
        
        Returns:
            Dict[str, Any]: Collector information
        """
        service = InputCollectorAPI._get_service()
        return service.get_current_collector()
    
    @staticmethod
    def scan_controllers() -> List[Dict[str, Any]]:
        """
        Scan for available controllers.
        
        Returns:
            List[Dict[str, Any]]: List of controller information
        """
        service = InputCollectorAPI._get_service()
        return service.scan_controllers()
    
    @staticmethod
    def connect_controller(index: int) -> bool:
        """
        Connect to a specific controller by index.
        
        Args:
            index: Controller index from scan_controllers()
            
        Returns:
            bool: True if successful
        """
        service = InputCollectorAPI._get_service()
        return service.connect_controller(index)
    
    #
    # Mouse tracking configuration methods
    #
    
    @staticmethod
    def set_mouse_tracking_mode(mode: str, direction_only: bool = None) -> bool:
        """
        Set the mouse tracking mode.
        
        Args:
            mode: The tracking mode to use ("joystick", "delta", "angle", "axis")
            direction_only: Whether to use direction-only mode
            
        Returns:
            bool: True if successful
        """
        service = InputCollectorAPI._get_service()
        return service.set_mouse_tracking_mode(mode, direction_only)
    
    @staticmethod
    def set_mouse_settings(delta_smoothing: Optional[float] = None, 
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
        service = InputCollectorAPI._get_service()
        return service.set_mouse_settings(delta_smoothing, joystick_sensitivity, angle_grouping)
    
    @staticmethod
    def get_mouse_settings() -> Dict[str, Any]:
        """
        Get current mouse tracking settings.
        
        Returns:
            Dict[str, Any]: Dictionary with mouse settings
        """
        service = InputCollectorAPI._get_service()
        return service.get_mouse_settings()
    
    #
    # Key tracking methods
    #
    
    @staticmethod
    def get_tracked_keys() -> List[str]:
        """
        Get the list of currently tracked keys.
        
        Returns:
            List[str]: List of tracked keys
        """
        service = InputCollectorAPI._get_service()
        return service.get_tracked_keys()
    
    @staticmethod
    def toggle_edit_mode() -> bool:
        """
        Toggle key/button edit mode.
        
        Returns:
            bool: True if successful
        """
        service = InputCollectorAPI._get_service()
        return service.toggle_edit_mode()
    
    @staticmethod
    def is_edit_mode() -> bool:
        """
        Check if edit mode is active.
        
        Returns:
            bool: True if edit mode is active
        """
        service = InputCollectorAPI._get_service()
        return service.is_edit_mode()
    
    @staticmethod
    def add_tracked_key(key: str) -> bool:
        """
        Add a key to the tracked keys list.
        
        Args:
            key: Key to add
            
        Returns:
            bool: True if successful
        """
        service = InputCollectorAPI._get_service()
        return service.add_tracked_key(key)
    
    @staticmethod
    def remove_tracked_key(key: str) -> bool:
        """
        Remove a key from the tracked keys list.
        
        Args:
            key: Key to remove
            
        Returns:
            bool: True if successful
        """
        service = InputCollectorAPI._get_service()
        return service.remove_tracked_key(key)
    
    @staticmethod
    def toggle_button_tracking(button_id: str, track: bool) -> bool:
        """
        Toggle tracking for a mouse button.
        
        Args:
            button_id: Button identifier ("Button.left", "Button.right", "Button.scroll")
            track: Whether to track the button
            
        Returns:
            bool: True if successful
        """
        service = InputCollectorAPI._get_service()
        return service.toggle_button_tracking(button_id, track)
    
    #
    # UI control methods
    #
    
    @staticmethod
    def toggle_fullscreen() -> bool:
        """
        Toggle fullscreen mode.
        
        Returns:
            bool: True if successful
        """
        service = InputCollectorAPI._get_service()
        return service.toggle_fullscreen()
    
    @staticmethod
    def get_application_state() -> Dict[str, Any]:
        """
        Get a comprehensive dictionary of application state.
        
        Returns:
            Dict[str, Any]: Application state
        """
        service = InputCollectorAPI._get_service()
        return service.get_application_state()
