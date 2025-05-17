"""
Data access service module.

Provides real-time access to input data with minimal overhead.
"""

import logging
import threading
import time
from typing import Dict, List, Any, Optional, Tuple, Callable

from ..interfaces.collector_interface import InputData


class DataAccessService:
    """
    Service providing real-time access to input data streams.
    
    This service allows other components to access the current input data
    state without introducing delays in the collection process.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the service."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = DataAccessService()
            return cls._instance
    
    def __init__(self):
        """Initialize the data access service."""
        self._data_lock = threading.Lock()
        self._metadata_lock = threading.Lock()
        
        # Current data - the most recent event
        self._current_event = None
        
        # Event history by type
        self._key_events = []
        self._mouse_movement_events = []
        self._mouse_button_events = []
        self._controller_events = []
        
        # Current state 
        self._active_keys = set()
        self._mouse_position = (0, 0)
        self._mouse_buttons = {
            "left": False,
            "right": False,
            "middle": False
        }
        
        # Input metadata
        self._metadata = {
            "collector_type": "",
            "last_update": 0,
            "is_mouse_moving": False,
            "mouse_direction": None,
            "controller_connected": False,
            "controller_name": ""
        }
        
        # Registered callbacks for data updates
        self._callbacks = []
        self._callback_lock = threading.Lock()
        
        # Maximum event history size
        self._max_history = 100
        
        logging.info("Input data access service initialized")
    
    def update_data(self, event: InputData) -> None:
        """
        Update the current data with a new input event.
        
        Args:
            event: New input event
        """
        with self._data_lock:
            # Update current event
            self._current_event = event
            
            # Update event history by type
            if event.event_type in ["key_press", "key_release"]:
                self._key_events.append(event)
                if len(self._key_events) > self._max_history:
                    self._key_events = self._key_events[-self._max_history:]
            
            elif event.event_type == "mouse_move":
                self._mouse_movement_events.append(event)
                if len(self._mouse_movement_events) > self._max_history:
                    self._mouse_movement_events = self._mouse_movement_events[-self._max_history:]
            
            elif event.event_type == "mouse_click":
                self._mouse_button_events.append(event)
                if len(self._mouse_button_events) > self._max_history:
                    self._mouse_button_events = self._mouse_button_events[-self._max_history:]
            
            elif event.event_type in ["button_press", "button_release", "axis_motion"]:
                self._controller_events.append(event)
                if len(self._controller_events) > self._max_history:
                    self._controller_events = self._controller_events[-self._max_history:]
            
            # Update current state
            if hasattr(event, "active_keys") and event.active_keys is not None:
                self._active_keys = set(event.active_keys)
            
            if hasattr(event, "mouse_x") and hasattr(event, "mouse_y") and \
               event.mouse_x is not None and event.mouse_y is not None:
                self._mouse_position = (event.mouse_x, event.mouse_y)
            
            # Update mouse button state
            if event.event_type == "mouse_click" and hasattr(event, "button_pressed"):
                if event.button_pressed == "Button.left":
                    self._mouse_buttons["left"] = True
                elif event.button_pressed == "Button.right":
                    self._mouse_buttons["right"] = True
                elif event.button_pressed == "Button.middle":
                    self._mouse_buttons["middle"] = True
            
            # Update metadata
            if hasattr(event, "is_moving"):
                self._metadata["is_mouse_moving"] = event.is_moving
            
            if hasattr(event, "direction"):
                self._metadata["mouse_direction"] = event.direction
            
            # Update last update timestamp
            self._metadata["last_update"] = time.time()
        
        # Notify callbacks
        self._notify_callbacks(event)
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Update input metadata.
        
        Args:
            metadata: Dictionary with metadata values
        """
        with self._metadata_lock:
            self._metadata.update(metadata)
    
    def get_current_event(self) -> Optional[InputData]:
        """
        Get the most recent input event.
        
        Returns:
            The most recent input event or None if no events
        """
        with self._data_lock:
            return self._current_event
    
    def get_key_events(self, max_count: int = None) -> List[InputData]:
        """
        Get recent key events.
        
        Args:
            max_count: Maximum number of events to return
            
        Returns:
            List of recent key events
        """
        with self._data_lock:
            if max_count is None:
                return self._key_events.copy()
            return self._key_events[-max_count:].copy()
    
    def get_mouse_movement_events(self, max_count: int = None) -> List[InputData]:
        """
        Get recent mouse movement events.
        
        Args:
            max_count: Maximum number of events to return
            
        Returns:
            List of recent mouse movement events
        """
        with self._data_lock:
            if max_count is None:
                return self._mouse_movement_events.copy()
            return self._mouse_movement_events[-max_count:].copy()
    
    def get_mouse_button_events(self, max_count: int = None) -> List[InputData]:
        """
        Get recent mouse button events.
        
        Args:
            max_count: Maximum number of events to return
            
        Returns:
            List of recent mouse button events
        """
        with self._data_lock:
            if max_count is None:
                return self._mouse_button_events.copy()
            return self._mouse_button_events[-max_count:].copy()
    
    def get_controller_events(self, max_count: int = None) -> List[InputData]:
        """
        Get recent controller events.
        
        Args:
            max_count: Maximum number of events to return
            
        Returns:
            List of recent controller events
        """
        with self._data_lock:
            if max_count is None:
                return self._controller_events.copy()
            return self._controller_events[-max_count:].copy()
    
    def get_active_keys(self) -> List[str]:
        """
        Get currently active keys.
        
        Returns:
            List of active key names
        """
        with self._data_lock:
            return list(self._active_keys)
    
    def is_key_active(self, key: str) -> bool:
        """
        Check if a specific key is active.
        
        Args:
            key: Key name to check
            
        Returns:
            True if key is active, False otherwise
        """
        with self._data_lock:
            return key in self._active_keys
    
    def get_mouse_position(self) -> Tuple[float, float]:
        """
        Get current mouse position.
        
        Returns:
            Tuple of (x, y) coordinates
        """
        with self._data_lock:
            return self._mouse_position
    
    def get_mouse_button_state(self, button: str) -> bool:
        """
        Get state of a specific mouse button.
        
        Args:
            button: Button name ('left', 'right', 'middle')
            
        Returns:
            True if button is pressed, False otherwise
        """
        with self._data_lock:
            return self._mouse_buttons.get(button, False)
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get the current input metadata.
        
        Returns:
            Dictionary with metadata
        """
        with self._metadata_lock:
            return self._metadata.copy()
    
    def register_callback(self, callback: Callable[[InputData], None]) -> int:
        """
        Register a callback function to be called when new data arrives.
        
        Args:
            callback: Function to call with (event)
            
        Returns:
            Callback ID for later unregistering
        """
        with self._callback_lock:
            callback_id = len(self._callbacks)
            self._callbacks.append(callback)
            return callback_id
    
    def unregister_callback(self, callback_id: int) -> bool:
        """
        Unregister a previously registered callback.
        
        Args:
            callback_id: ID of the callback to remove
            
        Returns:
            True if successful, False otherwise
        """
        with self._callback_lock:
            if 0 <= callback_id < len(self._callbacks):
                self._callbacks[callback_id] = None
                return True
            return False
    
    def _notify_callbacks(self, event: InputData) -> None:
        """
        Notify all registered callbacks of new data.
        
        Args:
            event: New input event
        """
        with self._callback_lock:
            for callback in self._callbacks:
                if callback is not None:
                    try:
                        callback(event)
                    except Exception as e:
                        logging.error(f"Error in data access callback: {e}")
