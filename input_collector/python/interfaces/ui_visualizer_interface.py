"""
Interface for UI-Visualizer communication.

Defines the interfaces that mediate the relationship between the UI manager and
visualizer components, ensuring loose coupling and clear responsibilities.
"""

from typing import List, Dict, Any, Protocol, runtime_checkable


@runtime_checkable
class AbstractVisualizerProvider(Protocol):
    """
    Interface for components that provide visualizer instances to the UI.

    This interface defines how visualizer components are provided to the UI system,
    allowing the UI to arrange visualizer widgets without directly depending on
    concrete visualizer implementations.
    """

    def get_keyboard_visualizer(self):
        """
        Get the keyboard visualizer component.

        Returns:
            A widget that visualizes keyboard input
        """
        ...

    def get_mouse_visualizer(self):
        """
        Get the mouse visualizer component.

        Returns:
            A widget that visualizes mouse input
        """
        ...

    def get_mouse_buttons_selector(self):
        """
        Get the mouse buttons selector component.

        Returns:
            A widget that shows mouse button selection options
        """
        ...


@runtime_checkable
class AbstractVisualizerController(Protocol):
    """
    Interface for controlling visualizers.

    This interface defines the methods needed to control visualizer behavior,
    allowing the UI to manage visualizers without knowing their concrete implementation.
    """

    def update_for_collector(
        self, collector_type: str, capabilities: Dict[str, Any]
    ) -> None:
        """
        Update visualizers based on collector type and capabilities.

        Args:
            collector_type: Type of the current collector
            capabilities: Dictionary of collector capabilities
        """
        ...

    def set_tracked_keys(self, keys: List[str]) -> None:
        """
        Set which keys/buttons should be highlighted in visualizers.

        Args:
            keys: List of keys/buttons to highlight
        """
        ...

    def set_scroll_tracking(self, enabled: bool) -> None:
        """
        Set whether to track mouse scroll events.

        Args:
            enabled: Whether scroll events should be tracked
        """
        ...

    def set_edit_mode(self, enabled: bool) -> None:
        """
        Set edit mode for all visualizers.

        Args:
            enabled: Whether edit mode should be enabled
        """
        ...

    def force_update(self) -> None:
        """Force update all visualizers."""
        ...
