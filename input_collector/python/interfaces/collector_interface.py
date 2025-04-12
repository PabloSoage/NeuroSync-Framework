"""
Interfaces and data structures for input collection.

This module defines the core data structures and interfaces used for input collection,
event representation and processing throughout the application.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable, Union, Tuple
import time
from abc import ABC, abstractmethod

@dataclass
class InputData:
    """
    Data structure for representing input events.
    
    This class encapsulates all data related to keyboard and mouse input events,
    including timestamps, position information, movement details, and active keys.
    
    Attributes:
        timestamp: The time when the event occurred, in seconds since epoch
        event_type: Type of event ('key_press', 'key_release', 'mouse_move', etc.)
        key: The key involved in a keyboard event (optional)
        mouse_x: X-coordinate of mouse position (optional)
        mouse_y: Y-coordinate of mouse position (optional)
        button_pressed: Mouse button that was pressed, e.g. 'Button.left' (optional)
        direction: Direction of movement or scroll ('X+', 'Y-', 'up', 'down', etc.)
        speed: Overall movement speed in pixels per second (optional)
        speed_x: Speed along X axis in pixels per second (optional)
        speed_y: Speed along Y axis in pixels per second (optional)
        rel_x: Relative X position from center (-1.0 to 1.0, joystick-like)
        rel_y: Relative Y position from center (-1.0 to 1.0, joystick-like)
        is_moving: Whether the mouse is considered to be in motion
        active_keys: List of all currently active keys
    """
    timestamp: float
    event_type: str  # 'key_press', 'key_release', 'mouse_move', 'mouse_click', 'mouse_scroll', 'none'
    key: Optional[str] = None
    mouse_x: Optional[float] = None
    mouse_y: Optional[float] = None
    button_pressed: Optional[str] = None  # 'Button.left', 'Button.right', 'Button.middle', etc.
    direction: Optional[str] = None  # For mouse movement: 'X+', 'X-', 'Y+', 'Y-', or combinations; For scroll: 'up', 'down'
    # Mouse tracking fields:
    speed: Optional[float] = None  # Overall speed (pixels per second)
    speed_x: Optional[float] = None  # Speed along X axis
    speed_y: Optional[float] = None  # Speed along Y axis
    rel_x: Optional[float] = None  # Relative position from center (-1.0 to 1.0, joystick-like)
    rel_y: Optional[float] = None  # Relative position from center (-1.0 to 1.0, joystick-like)
    is_moving: Optional[bool] = None  # Whether the mouse is considered to be in motion
    active_keys: List[str] = None  # List of all currently active keys
    
    def __post_init__(self) -> None:
        """
        Initialize default values after instance creation.
        
        Ensures that active_keys is always initialized as a list.
        """
        # Initialize active_keys as empty list if not provided
        if self.active_keys is None:
            self.active_keys = []

class AbstractInputCollector(ABC):
    """
    Abstract interface for input collectors.
    
    This abstract class defines the interface that all input collectors must implement.
    Input collectors are responsible for capturing, processing, and providing access to
    keyboard and mouse input events.
    """
    
    @abstractmethod
    def start_capture(self) -> None:
        """
        Start capturing input events.
        
        Begins the collection of input events from the system. After calling this method,
        events should be collected and made available through other methods.
        """
        pass
    
    @abstractmethod
    def stop_capture(self) -> None:
        """
        Stop capturing input events.
        
        Stops the collection of input events. No new events should be collected after
        calling this method until start_capture() is called again.
        """
        pass
    
    @abstractmethod
    def get_input_event(self) -> InputData:
        """
        Get the most recent input event.
        
        Returns:
            InputData: The most recent input event, or a placeholder event if none available.
        """
        pass
    
    @abstractmethod
    def on_event(self, callback: Callable[[InputData], None]) -> None:
        """
        Register a callback for input events.
        
        Args:
            callback: Function to be called when a new input event is processed.
                     The function should accept an InputData instance as its argument.
        """
        pass
    
    @abstractmethod
    def set_supported_keys(self, keys: List[str]) -> None:
        """
        Set the keys to be tracked by the collector.
        
        Args:
            keys: List of key identifiers (strings) to be tracked.
        """
        pass
    
    @abstractmethod
    def get_events_since(self, timestamp: float) -> List[InputData]:
        """
        Get all events since a specific timestamp.
        
        Args:
            timestamp: Time (in seconds since epoch) to retrieve events from.
            
        Returns:
            List[InputData]: List of input events that occurred since the given timestamp.
        """
        pass
    
    @abstractmethod
    def clear_events(self) -> None:
        """
        Clear all stored events.
        
        Removes all events from the collector's history, keeping the current state.
        """
        pass