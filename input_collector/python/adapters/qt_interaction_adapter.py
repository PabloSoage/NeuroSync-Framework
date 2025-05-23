"""
Qt Interaction Adapter module.

This module provides an adapter that bridges between the UI framework (PyQt5) 
and the framework-independent interaction service layer.
"""

import logging
import threading
import time
from typing import Dict, List, Any, Optional, Tuple, Set, Callable

from PyQt5.QtCore import QMetaObject, Qt, QObject, pyqtSlot, QTimer, QEventLoop

class QtInteractionAdapter:
    """
    Adapter for PyQt5 UI components to the interaction service.
    
    This adapter ensures that all UI framework-specific operations 
    are performed in a thread-safe manner and properly isolated from
    the core service layer.
    """
    
    def __init__(self):
        """Initialize the adapter."""
        self.app_coordinator = None
        self.ui_manager = None
        self.logging_manager = None
        self.collector_manager = None
        self.event_processor = None
        
        # Lock for thread safety on operations
        self._lock = threading.Lock()
        
        logging.info("Qt interaction adapter created")
    
    def initialize(self, app_coordinator, ui_manager, logging_manager, 
                 collector_manager, event_processor) -> bool:
        """
        Initialize the adapter with application components.
        
        Args:
            app_coordinator: Application coordinator
            ui_manager: UI manager
            logging_manager: Logging manager
            collector_manager: Collector manager
            event_processor: Event processor
            
        Returns:
            bool: True if successful
        """
        try:
            self.app_coordinator = app_coordinator
            self.ui_manager = ui_manager
            self.logging_manager = logging_manager
            self.collector_manager = collector_manager
            self.event_processor = event_processor
            
            logging.info("Qt interaction adapter initialized")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize Qt interaction adapter: {e}")
            return False
    
    def _execute_safely(self, func, *args, **kwargs):
        """
        Execute a function safely, ensuring it runs on the main thread.
        
        Args:
            func: The function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
        """
        # Create a timer in the current thread
        timer = QTimer()
        # Create an event loop in the current thread
        loop = QEventLoop()
        # Variable to store the result
        result_container = {"result": None, "done": False, "exception": None}
        
        # Function to be executed in the main thread
        def execute_function():
            try:
                result_container["result"] = func(*args, **kwargs)
                result_container["done"] = True
            except Exception as e:
                result_container["exception"] = e
                result_container["done"] = True
            finally:
                loop.quit()
        
        # Connect the timer to the function
        timer.timeout.connect(execute_function)
        # Set timer to fire once
        timer.setSingleShot(True)
        # Start the timer with a short timeout
        timer.start(0)
        # Wait for the function to complete
        loop.exec_()
        
        # Check if an exception occurred
        if result_container["exception"]:
            raise result_container["exception"]
        
        # Return the result
        return result_container["result"]
    
    #
    # Recording control methods
    #
    
    def start_recording(self) -> bool:
        """
        Start recording input events.
        
        Returns:
            bool: True if successful
        """
        with self._lock:
            # Get current state
            prev_state = self.app_coordinator.is_recording if self.app_coordinator else False
            
            # Only attempt to start if not already recording
            if not prev_state:
                try:
                    # Use our thread-safe execution function
                    self._execute_safely(self.app_coordinator.toggle_recording)
                    
                    # Wait a brief moment for state to update
                    time.sleep(0.1)
                    
                    # Check if recording state changed
                    current_state = self.app_coordinator.is_recording if self.app_coordinator else False
                    return current_state
                except Exception as e:
                    logging.error(f"Error starting recording: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                # Already recording
                return True  # Return success since it's in the desired state
    
    def stop_recording(self) -> bool:
        """
        Stop recording input events.
        
        Returns:
            bool: True if successful
        """
        with self._lock:
            # Get current state
            prev_state = self.app_coordinator.is_recording if self.app_coordinator else False
            
            # Only attempt to stop if currently recording
            if prev_state:
                try:
                    # Use our thread-safe execution function
                    self._execute_safely(self.app_coordinator.toggle_recording)
                    
                    # Wait a brief moment for state to update
                    time.sleep(0.1)
                    
                    # Check if recording state changed
                    current_state = self.app_coordinator.is_recording if self.app_coordinator else True
                    return not current_state
                except Exception as e:
                    logging.error(f"Error stopping recording: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                # Not recording
                return True  # Return success since it's in the desired state
    
    def toggle_recording(self) -> Tuple[bool, bool]:
        """
        Toggle recording state.
        
        Returns:
            Tuple of (success, is_recording)
        """
        with self._lock:
            # Get current state
            prev_state = self.app_coordinator.is_recording if self.app_coordinator else False
            
            try:
                # Use our thread-safe execution function
                self._execute_safely(self.app_coordinator.toggle_recording)
                
                # Wait a brief moment for state to update
                time.sleep(0.1)
                
                # Get new state
                current_state = self.app_coordinator.is_recording if self.app_coordinator else prev_state
                
                # Return success and new state
                return True, current_state
            except Exception as e:
                logging.error(f"Error toggling recording: {e}")
                import traceback
                traceback.print_exc()
                return False, prev_state
    
    def is_recording(self) -> bool:
        """
        Check if recording is active.
        
        Returns:
            bool: True if recording is active
        """
        return self.app_coordinator.is_recording if self.app_coordinator else False
    
    #
    # UI methods
    #
    
    def set_csv_path(self, filepath: str) -> bool:
        """
        Set the CSV path in the UI.
        
        Args:
            filepath: Path to the CSV file
            
        Returns:
            bool: True if successful
        """
        if not self.ui_manager:
            return False
            
        try:
            self.ui_manager.set_csv_path(filepath)
            return True
        except Exception as e:
            logging.error(f"Error setting CSV path in UI: {e}")
            return False
    
    def scan_controllers(self) -> List[Dict[str, Any]]:
        """
        Scan for controllers.
        
        Returns:
            List of controller info dictionaries
        """
        if not self.collector_manager:
            return []
            
        try:
            ps4_collector = self.collector_manager.get_collector("ps4_controller")
            if ps4_collector:
                return ps4_collector.scan_controllers()
            return []
        except Exception as e:
            logging.error(f"Error scanning controllers: {e}")
            return []
    
    def connect_controller(self, index: int) -> bool:
        """
        Connect to a controller.
        
        Args:
            index: Controller index
            
        Returns:
            bool: True if successful
        """
        if not self.collector_manager:
            return False
            
        try:
            ps4_collector = self.collector_manager.get_collector("ps4_controller")
            if ps4_collector:
                return ps4_collector.connect_to_controller(index)
            return False
        except Exception as e:
            logging.error(f"Error connecting to controller: {e}")
            return False
    
    def switch_collector(self, collector_type: str) -> bool:
        """
        Switch to a different input collector.
        
        Args:
            collector_type: Type identifier for the collector
            
        Returns:
            bool: True if successful
        """
        if not self.app_coordinator:
            return False
            
        success, _ = self._ensure_main_thread(self.app_coordinator, "switch_collector", collector_type)
        return success
    
    def set_mouse_tracking_mode(self, mode: str, direction_only: bool = None) -> bool:
        """
        Set the mouse tracking mode.
        
        Args:
            mode: The tracking mode to use
            direction_only: Whether to use direction-only mode
            
        Returns:
            bool: True if successful
        """
        if not self.ui_manager:
            return False
            
        try:
            # Update direction-only mode first if specified
            if direction_only is not None:
                self.ui_manager.set_direction_only_mode(direction_only)
                
            # Set tracking mode in UI
            self.ui_manager.set_tracking_mode(mode)
            
            # Apply mode change through coordinator
            if self.app_coordinator:
                success, _ = self._ensure_main_thread(self.app_coordinator, "set_mouse_tracking_mode", mode)
                return success
            return True
        except Exception as e:
            logging.error(f"Error setting mouse tracking mode: {e}")
            return False
    
    def set_mouse_settings(self, delta_smoothing: Optional[float] = None, 
                         joystick_sensitivity: Optional[float] = None,
                         angle_grouping: Optional[int] = None) -> bool:
        """
        Set mouse tracking settings.
        
        Args:
            delta_smoothing: Smoothing factor for delta tracking
            joystick_sensitivity: Sensitivity for joystick tracking
            angle_grouping: Angle grouping in degrees
            
        Returns:
            bool: True if successful
        """
        if not self.ui_manager:
            return False
            
        try:
            # Update UI settings
            if delta_smoothing is not None:
                self.ui_manager.set_delta_smoothing(delta_smoothing)
                
            if joystick_sensitivity is not None:
                self.ui_manager.set_joystick_sensitivity(joystick_sensitivity)
                
            if angle_grouping is not None:
                self.ui_manager.set_angle_grouping(angle_grouping)
                
            # Apply settings
            if self.app_coordinator:
                success, _ = self._ensure_main_thread(self.app_coordinator, "apply_mouse_settings")
                return success
            return True
        except Exception as e:
            logging.error(f"Error setting mouse settings: {e}")
            return False
    
    def get_mouse_settings(self) -> Dict[str, Any]:
        """
        Get current mouse tracking settings.
        
        Returns:
            Dict[str, Any]: Dictionary with mouse settings
        """
        if not self.ui_manager:
            return {"error": "UI manager not available"}
            
        try:
            return {
                "tracking_mode": self.ui_manager.get_tracking_mode(),
                "direction_only": self.ui_manager.is_direction_only_mode(),
                "delta_smoothing": self.ui_manager.get_delta_smoothing(),
                "joystick_sensitivity": self.ui_manager.get_joystick_sensitivity(),
                "angle_grouping": self.ui_manager.get_angle_grouping()
            }
        except Exception as e:
            logging.error(f"Error getting mouse settings: {e}")
            return {"error": str(e)}
    
    def get_tracked_keys(self) -> List[str]:
        """
        Get the list of currently tracked keys.
        
        Returns:
            List[str]: List of tracked keys
        """
        if not self.app_coordinator:
            return []
            
        try:
            return self.app_coordinator.get_tracked_keys()
        except Exception as e:
            logging.error(f"Error getting tracked keys: {e}")
            return []
    
    def toggle_edit_mode(self) -> Tuple[bool, bool]:
        """
        Toggle key/button edit mode.
        
        Returns:
            Tuple of (success, is_edit_mode)
        """
        if not self.app_coordinator:
            return False, False
            
        # Get current state
        prev_state = self.app_coordinator.edit_mode if self.app_coordinator else False
        
        # Toggle edit mode
        success, _ = self._ensure_main_thread(self.app_coordinator, "toggle_edit_mode")
        
        # Get new state
        current_state = self.app_coordinator.edit_mode if self.app_coordinator else prev_state
        
        # Return success and new state
        return success, current_state
    
    def is_edit_mode(self) -> bool:
        """
        Check if edit mode is active.
        
        Returns:
            bool: True if edit mode is active
        """
        return self.app_coordinator.edit_mode if self.app_coordinator else False
    
    def add_tracked_key(self, key: str) -> bool:
        """
        Add a key to the tracked keys list.
        
        Args:
            key: Key to add
            
        Returns:
            bool: True if successful
        """
        if not self.app_coordinator:
            return False
            
        # Simulate what handle_key_edit does
        success, _ = self._ensure_main_thread(self.app_coordinator, "handle_key_edit", key)
        return success
    
    def remove_tracked_key(self, key: str) -> bool:
        """
        Remove a key from the tracked keys list.
        
        Args:
            key: Key to remove
            
        Returns:
            bool: True if successful
        """
        if not self.app_coordinator:
            return False
            
        # Simulate what handle_key_edit does
        success, _ = self._ensure_main_thread(self.app_coordinator, "handle_key_edit", key)
        return success
    
    def toggle_button_tracking(self, button_id: str, track: bool) -> bool:
        """
        Toggle tracking for a mouse button.
        
        Args:
            button_id: Button identifier
            track: Whether to track the button
            
        Returns:
            bool: True if successful
        """
        if not self.app_coordinator:
            return False
            
        success, _ = self._ensure_main_thread(self.app_coordinator, "handle_button_edit", button_id, track)
        return success
    
    def toggle_fullscreen(self) -> bool:
        """
        Toggle fullscreen mode.
        
        Returns:
            bool: True if successful
        """
        if not self.ui_manager:
            return False
            
        try:
            # Use the UI manager's toggle_fullscreen signal
            self.ui_manager.toggle_fullscreen.emit()
            return True
        except Exception as e:
            logging.error(f"Error toggling fullscreen: {e}")
            return False
