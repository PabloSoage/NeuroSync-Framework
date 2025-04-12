from dataclasses import dataclass
from typing import List, Dict, Optional, Callable, Union, Tuple
import time
from abc import ABC, abstractmethod

@dataclass
class InputData:
    """Data structure for input events"""
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
    
    def __post_init__(self):
        # Initialize active_keys as empty list if not provided
        if self.active_keys is None:
            self.active_keys = []

class AbstractInputCollector(ABC):
    """Abstract interface for input collectors"""
    
    @abstractmethod
    def start_capture(self) -> None:
        """Start capturing input events"""
        pass
    
    @abstractmethod
    def stop_capture(self) -> None:
        """Stop capturing input events"""
        pass
    
    @abstractmethod
    def get_input_event(self) -> InputData:
        """Get the most recent input event"""
        pass
    
    @abstractmethod
    def on_event(self, callback: Callable[[InputData], None]) -> None:
        """Register a callback for input events"""
        pass
    
    @abstractmethod
    def set_supported_keys(self, keys: List[str]) -> None:
        """Set the keys to be tracked by the collector"""
        pass
    
    @abstractmethod
    def get_events_since(self, timestamp: float) -> List[InputData]:
        """Get all events since a specific timestamp"""
        pass
    
    @abstractmethod
    def clear_events(self) -> None:
        """Clear all stored events"""
        pass