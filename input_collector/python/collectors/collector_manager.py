"""
Collector manager module.

Provides a central manager for different input collectors.
"""

from typing import Dict, List, Optional, Callable, Any

from .keyboard_mouse import KeyboardMouseCollector
from ..interfaces import InputData, AbstractInputCollector

# Import services (add this new import)
from ..services.data_access_service import DataAccessService

# Import PS4 controller with fallback
try:
    from .ps4_controller import PS4ControllerCollector, is_sdl2_available

    HAVE_PS4_SUPPORT = is_sdl2_available()
except ImportError:
    HAVE_PS4_SUPPORT = False


class CollectorManager:
    """
    Manages input collectors and their interactions with visualizers.

    This class handles the creation, configuration, and management of input collectors,
    as well as coordinating the flow of input events to the appropriate visualizers.
    """

    def __init__(self) -> None:
        """Initialize the collector manager."""
        self.collectors: Dict[str, AbstractInputCollector] = {}
        self.current_collector: Optional[AbstractInputCollector] = None
        self.current_collector_type: Optional[str] = None
        self.visualizers: List[Any] = []
        self.tracked_keys: List[str] = []
        self.event_callbacks: List[Callable[[InputData], None]] = []

        # Get data access service instance
        self.data_access_service = DataAccessService.get_instance()

        # Initialize collectors
        self._initialize_collectors()

    def _initialize_collectors(self) -> None:
        """Initialize available input collectors."""
        # Always add keyboard/mouse collector
        self.add_collector("keyboard_mouse", KeyboardMouseCollector())

        # Add PS4 controller if available
        if HAVE_PS4_SUPPORT:
            try:
                print("Attempting to initialize PS4 controller...")
                ps4_collector = PS4ControllerCollector()
                self.add_collector("ps4_controller", ps4_collector)
                print("PS4 controller collector initialized successfully.")
            except Exception as e:
                print(f"Error initializing PS4 controller: {e}")
                import traceback

                traceback.print_exc()

        # Set default collector
        self.set_current_collector("keyboard_mouse")

    def add_collector(
        self, collector_type: str, collector: AbstractInputCollector
    ) -> None:
        """
        Add a collector to the manager.

        Args:
            collector_type: Type identifier for the collector
            collector: The collector instance
        """
        self.collectors[collector_type] = collector
        collector.on_event(self._handle_input_event)

    def set_current_collector(self, collector_type: str) -> bool:
        """
        Set the current active collector.

        Args:
            collector_type: Type identifier for the collector to activate

        Returns:
            bool: True if successful, False otherwise
        """
        if collector_type not in self.collectors:
            return False

        try:
            # Save previous collector type for rollback
            previous_collector_type = self.current_collector_type
            previous_collector = self.current_collector

            # Attempt to switch collector
            self.current_collector_type = collector_type
            self.current_collector = self.collectors[collector_type]

            # Update tracked keys
            if self.tracked_keys and self.current_collector:
                self.current_collector.set_supported_keys(self.tracked_keys)

            # Update visualizers for the new collector
            self._update_visualizers()

            # Update data access service metadata
            self.data_access_service.update_metadata(
                {
                    "collector_type": collector_type,
                    "controller_connected": collector_type == "ps4_controller"
                    and hasattr(self.current_collector, "controller")
                    and self.current_collector is not None
                    and self.current_collector.controller is not None,
                    "controller_name": (
                        self._get_controller_name()
                        if collector_type == "ps4_controller"
                        else ""
                    ),
                }
            )

            return True

        except Exception as e:
            print(f"Error switching to collector {collector_type}: {e}")
            import traceback

            traceback.print_exc()

            # Rollback to previous collector if we had one
            if hasattr(self, "previous_collector_type") and previous_collector_type:
                print(f"Rolling back to previous collector: {previous_collector_type}")
                self.current_collector_type = previous_collector_type
                self.current_collector = previous_collector

                # Update visualizers to reflect the rollback
                self._update_visualizers()

            return False

    def get_available_collectors(self) -> List[Dict[str, str]]:
        """
        Get a list of available collectors.

        Returns:
            List[Dict[str, str]]: List of collector information dictionaries
        """
        return [
            {
                "type": collector_type,
                "name": self._get_collector_display_name(collector_type),
            }
            for collector_type in self.collectors
        ]

    def _get_collector_display_name(self, collector_type: str) -> str:
        """Get a user-friendly display name for a collector type."""
        display_names = {
            "keyboard_mouse": "Keyboard & Mouse",
            "ps4_controller": "PS4 Controller",
        }
        return display_names.get(collector_type, collector_type)

    def start_capture(self) -> None:
        """Start capturing with the current collector."""
        if self.current_collector:
            self.current_collector.start_capture()

    def stop_capture(self) -> None:
        """Stop capturing with the current collector."""
        if self.current_collector:
            self.current_collector.stop_capture()

    def register_visualizer(self, visualizer: Any) -> None:
        """
        Register a visualizer to receive updates from the collectors.

        Args:
            visualizer: The visualizer to register
        """
        if visualizer not in self.visualizers:
            self.visualizers.append(visualizer)

        # Update the visualizer with the current collector's capabilities
        self._update_visualizer(visualizer)

    def unregister_visualizer(self, visualizer: Any) -> None:
        """
        Unregister a visualizer.

        Args:
            visualizer: The visualizer to unregister
        """
        if visualizer in self.visualizers:
            self.visualizers.remove(visualizer)

    def _update_visualizers(self) -> None:
        """Update all registered visualizers with the current collector."""
        for visualizer in self.visualizers:
            self._update_visualizer(visualizer)

    def _update_visualizer(self, visualizer: Any) -> None:
        """
        Update a single visualizer with the current collector's information.

        Args:
            visualizer: The visualizer to update
        """
        if not self.current_collector:
            return

        # Set capabilities
        capabilities = self.current_collector.get_capabilities()
        if hasattr(visualizer, "set_collector_capabilities"):
            visualizer.set_collector_capabilities(capabilities)

    def set_tracked_keys(self, keys: List[str]) -> None:
        """
        Set the keys to be tracked by collectors.

        Args:
            keys: List of keys to track
        """
        self.tracked_keys = keys
        if self.current_collector:
            self.current_collector.set_supported_keys(keys)

    def get_active_keys(self) -> List[str]:
        """
        Get the currently active keys from the current collector.

        Returns:
            List[str]: List of active keys
        """
        if self.current_collector:
            return self.current_collector.get_active_keys()
        return []

    def _handle_input_event(self, event: InputData) -> None:
        """
        Handle input events from collectors.

        Args:
            event: The input event to process
        """
        # Update the data access service with the new event
        self.data_access_service.update_data(event)

        # Update visualizers
        for visualizer in self.visualizers:
            # Only update visualizers that support the current collector type
            if hasattr(
                visualizer, "supports_collector"
            ) and visualizer.supports_collector(self.current_collector_type):
                visualizer.update(event)

        # Notify callbacks
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event callback: {e}")

    def on_event(self, callback: Callable[[InputData], None]) -> None:
        """
        Register a callback for input events.

        Args:
            callback: Function to call when an input event occurs
        """
        if callback not in self.event_callbacks:
            self.event_callbacks.append(callback)

    def remove_event_handler(self, callback: Callable[[InputData], None]) -> None:
        """
        Remove an event callback.

        Args:
            callback: The callback to remove
        """
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)

    def get_current_collector_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of the current collector.

        Returns:
            Dict[str, Any]: Dictionary of capabilities
        """
        if self.current_collector:
            return self.current_collector.get_capabilities()
        return {}

    def get_current_collector_type(self) -> str:
        """
        Get the type of the current collector.

        Returns:
            str: Collector type identifier
        """
        return self.current_collector_type if self.current_collector_type else ""

    def get_collector(self, collector_type: str) -> Optional[AbstractInputCollector]:
        """
        Get a specific collector by type.

        Args:
            collector_type: The type of collector to get

        Returns:
            Optional[AbstractInputCollector]: The collector instance or None if not found
        """
        return self.collectors.get(collector_type)

    def get_current_collector(self) -> Optional[AbstractInputCollector]:
        """
        Get the current collector.

        Returns:
            Optional[AbstractInputCollector]: The current collector instance
        """
        return self.current_collector

    def _get_controller_name(self) -> str:
        """Get the name of the current controller if any."""
        if (
            self.current_collector
            and self.current_collector_type == "ps4_controller"
            and hasattr(self.current_collector, "controller_name")
        ):
            return self.current_collector.controller_name
        return ""
