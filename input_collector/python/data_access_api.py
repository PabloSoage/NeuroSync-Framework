"""
API for accessing real-time input data.

This module provides a clean interface for accessing input events and state
with minimal overhead.
"""

from typing import Dict, List, Any, Optional, Tuple, Callable

from .interfaces.collector_interface import InputData
from .services.data_access_service import DataAccessService


class InputDataAPI:
    """
    Main API for accessing input data.

    This class provides methods to access real-time input events and state.
    """

    @staticmethod
    def get_current_event() -> Optional[InputData]:
        """
        Get the most recent input event.

        Returns:
            The most recent input event or None if no events
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_current_event()

    @staticmethod
    def get_key_events(max_count: Optional[int] = None) -> List[InputData]:
        """
        Get recent key events.

        Args:
            max_count: Maximum number of events to return

        Returns:
            List of recent key events
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_key_events(max_count)

    @staticmethod
    def get_mouse_movement_events(max_count: Optional[int] = None) -> List[InputData]:
        """
        Get recent mouse movement events.

        Args:
            max_count: Maximum number of events to return

        Returns:
            List of recent mouse movement events
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_mouse_movement_events(max_count)

    @staticmethod
    def get_mouse_button_events(max_count: Optional[int] = None) -> List[InputData]:
        """
        Get recent mouse button events.

        Args:
            max_count: Maximum number of events to return

        Returns:
            List of recent mouse button events
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_mouse_button_events(max_count)

    @staticmethod
    def get_controller_events(max_count: Optional[int] = None) -> List[InputData]:
        """
        Get recent controller events.

        Args:
            max_count: Maximum number of events to return

        Returns:
            List of recent controller events
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_controller_events(max_count)

    @staticmethod
    def get_active_keys() -> List[str]:
        """
        Get currently active keys.

        Returns:
            List of active key names
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_active_keys()

    @staticmethod
    def is_key_active(key: str) -> bool:
        """
        Check if a specific key is active.

        Args:
            key: Key name to check

        Returns:
            True if key is active, False otherwise
        """
        data_access = DataAccessService.get_instance()
        return data_access.is_key_active(key)

    @staticmethod
    def get_mouse_position() -> Tuple[float, float]:
        """
        Get current mouse position.

        Returns:
            Tuple of (x, y) coordinates
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_mouse_position()

    @staticmethod
    def get_mouse_button_state(button: str) -> bool:
        """
        Get state of a specific mouse button.

        Args:
            button: Button name ('left', 'right', 'middle')

        Returns:
            True if button is pressed, False otherwise
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_mouse_button_state(button)

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        """
        Get the current input metadata.

        Returns:
            Dictionary with metadata
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_metadata()

    @staticmethod
    def register_event_callback(callback: Callable[[InputData], None]) -> int:
        """
        Register a callback function to be called when new data arrives.

        Args:
            callback: Function to call with (event)

        Returns:
            Callback ID for later unregistering
        """
        data_access = DataAccessService.get_instance()
        return data_access.register_callback(callback)

    @staticmethod
    def unregister_event_callback(callback_id: int) -> bool:
        """
        Unregister a previously registered callback.

        Args:
            callback_id: ID of the callback to remove

        Returns:
            True if successful, False otherwise
        """
        data_access = DataAccessService.get_instance()
        return data_access.unregister_callback(callback_id)

    @staticmethod
    def is_mouse_moving() -> bool:
        """
        Check if the mouse is currently moving.

        Returns:
            True if mouse is moving, False otherwise
        """
        data_access = DataAccessService.get_instance()
        metadata = data_access.get_metadata()
        return metadata.get("is_mouse_moving", False)

    @staticmethod
    def get_mouse_direction() -> Optional[str]:
        """
        Get current mouse movement direction.

        Returns:
            Direction string or None if not moving
        """
        data_access = DataAccessService.get_instance()
        metadata = data_access.get_metadata()
        return metadata.get("mouse_direction")

    @staticmethod
    def is_controller_connected() -> bool:
        """
        Check if a controller is connected.

        Returns:
            True if controller is connected, False otherwise
        """
        data_access = DataAccessService.get_instance()
        metadata = data_access.get_metadata()
        return metadata.get("controller_connected", False)

    @staticmethod
    def get_controller_name() -> str:
        """
        Get name of connected controller.

        Returns:
            Controller name or empty string if none connected
        """
        data_access = DataAccessService.get_instance()
        metadata = data_access.get_metadata()
        return metadata.get("controller_name", "")
