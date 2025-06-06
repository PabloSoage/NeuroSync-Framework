"""
Interfaces and data structures for input collection.

This module defines the core data structures and interfaces used for input collection,
event representation and processing throughout the application.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Callable, Dict, Any


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
    button_pressed: Optional[str] = (
        None  # 'Button.left', 'Button.right', 'Button.middle', etc.
    )
    direction: Optional[str] = (
        None  # For mouse movement: 'X+', 'X-', 'Y+', 'Y-', or combinations; For scroll: 'up', 'down'
    )
    # Mouse tracking fields:
    speed: Optional[float] = None  # Overall speed (pixels per second)
    speed_x: Optional[float] = None  # Speed along X axis
    speed_y: Optional[float] = None  # Speed along Y axis
    rel_x: Optional[float] = (
        None  # Relative position from center (-1.0 to 1.0, joystick-like)
    )
    rel_y: Optional[float] = (
        None  # Relative position from center (-1.0 to 1.0, joystick-like)
    )
    is_moving: Optional[bool] = None  # Whether the mouse is considered to be in motion
    active_keys: Optional[List[str]] = None  # List of all currently active keys

    # New delta-based tracking fields
    mouse_delta_x: Optional[float] = None  # Raw mouse movement delta X
    mouse_delta_y: Optional[float] = None  # Raw mouse movement delta Y
    mouse_delta_magnitude: Optional[float] = None  # Total movement magnitude
    mouse_delta_angle: Optional[float] = (
        None  # Movement angle in degrees (0=right, 90=down)
    )
    mouse_tracking_mode: Optional[str] = None  # Which tracking mode is being used

    # New direction-only mode fields
    direction_only: Optional[bool] = None  # Whether direction-only mode is active
    discrete_angle: Optional[int] = None  # Discretized angle value (0-359)
    north: Optional[float] = None  # Membership value for north direction (0.0 to 1.0)
    south: Optional[float] = None  # Membership value for south direction (0.0 to 1.0)
    east: Optional[float] = None  # Membership value for east direction (0.0 to 1.0)
    west: Optional[float] = None  # Membership value for west direction (0.0 to 1.0)

    def __post_init__(self) -> None:
        """
        Initialize default values after instance creation.

        Ensures that active_keys is always initialized as a list.
        """
        # Initialize active_keys as empty list if not provided
        if self.active_keys is None:
            self.active_keys = []

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the input data to a dictionary for JSON serialization.

        Returns:
            Dict[str, Any]: Dictionary representation of this object
        """
        result = {}
        # Include all non-None attributes
        for key, value in self.__dict__.items():
            if value is not None:
                # Special handling for different types
                if isinstance(value, list):
                    result[key] = list(value)  # Create a copy for safety
                elif hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
                    result[key] = value.to_dict()
                else:
                    result[key] = value
        return result


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

    def get_active_keys(self) -> List[str]:
        """
        Get a list of currently active keys or buttons.

        Returns:
            List[str]: List of active keys/buttons
        """
        return []

    def get_collector_type(self) -> str:
        """
        Get the type of this collector.

        Returns:
            str: The collector type identifier (e.g., "keyboard_mouse", "ps4_controller")
        """
        return "abstract"

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of this collector.

        Returns:
            Dict[str, Any]: Dictionary of collector capabilities
        """
        return {
            "supports_mouse_tracking": False,
            "supports_keyboard": False,
            "supports_mouse_buttons": False,
            "supports_mouse_movement": False,
            "supports_mouse_scroll": False,
            "supports_joystick": False,
            "supported_tracking_modes": [],
        }
