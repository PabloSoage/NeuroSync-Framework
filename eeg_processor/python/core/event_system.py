"""
Event system for coordinating interactions between API and GUI components.

This module provides a comprehensive event system for decoupled communication
throughout the EEG processor application, similar to the pattern used in
input_collector module.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Callable, Any, Optional, Set


class EventType(Enum):
    """Types of events that can be triggered in the EEG processor."""

    # Connection events
    BOARD_CONNECT = auto()
    BOARD_DISCONNECT = auto()
    STREAM_START = auto()
    STREAM_STOP = auto()
    CONNECTION_STATUS_CHANGED = auto()

    # Processing events
    FILTER_APPLY = auto()
    FILTER_SETTINGS_CHANGED = auto()
    PROCESSING_COMPLETED = auto()
    METRICS_CALCULATED = auto()

    # Visualization events
    VISUALIZATION_START = auto()
    VISUALIZATION_STOP = auto()
    BRAIN_MAP_SHOW = auto()
    BRAIN_MAP_HIDE = auto()
    VISUALIZATION_STATUS_CHANGED = auto()

    # Recording events
    RECORDING_START = auto()
    RECORDING_STOP = auto()
    MARKER_INSERT = auto()
    RECORDING_STATUS_CHANGED = auto()

    # Streaming events
    STREAMER_ADD = auto()
    STREAMER_REMOVE = auto()
    STREAMERS_CHANGED = auto()

    # Advanced processing events
    ICA_COMPUTE = auto()
    ICA_COMPLETED = auto()
    WAVELET_COMPUTE = auto()
    WAVELET_COMPLETED = auto()
    DOWNSAMPLE_APPLY = auto()
    DOWNSAMPLE_COMPLETED = auto()

    # MNE events
    MNE_CONVERT = auto()
    MNE_CONVERSION_COMPLETED = auto()
    MNE_PLOT = auto()
    MNE_PLOT_COMPLETED = auto()

    # Data events
    DATA_UPDATED = auto()
    METADATA_UPDATED = auto()
    BOARD_INFO_UPDATED = auto()

    # UI State events
    UI_UPDATE_STATUS = auto()
    UI_UPDATE_CONTROLS = auto()
    UI_UPDATE_PANELS = auto()
    UI_ENABLE_CONTROLS = auto()
    UI_DISABLE_CONTROLS = auto()

    # System events
    SYSTEM_STATUS_CHANGED = auto()
    ERROR_OCCURRED = auto()
    WARNING_OCCURRED = auto()
    INFO_MESSAGE = auto()

    # Configuration events
    CONFIG_CHANGED = auto()
    BOARD_CONFIG_SENT = auto()
    DEVICE_CONFIG_RESPONSE = auto()

    # Channel events
    CHANNEL_SELECTION_CHANGED = auto()
    CHANNEL_DATA_UPDATED = auto()


@dataclass
class Event:
    """Represents an event in the system."""

    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    timestamp: float = field(default_factory=time.time)


class EventDispatcher:
    """
    Central event dispatcher for coordinating interactions.

    This class manages event publishing and subscription, allowing
    different components to communicate without tight coupling.
    """

    _instance: Optional["EventDispatcher"] = None
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "EventDispatcher":
        """Get the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = EventDispatcher()
            return cls._instance

    def __init__(self) -> None:
        """Initialize the event dispatcher."""
        if EventDispatcher._instance is not None:
            raise RuntimeError("EventDispatcher is a singleton. Use get_instance()")

        self._subscribers: Dict[EventType, Set[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._last_events: Dict[EventType, Event] = {}

        logging.info("Event dispatcher initialized")

    def subscribe(
        self, event_type: EventType, callback: Callable[[Event], None]
    ) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = set()
            self._subscribers[event_type].add(callback)

            # If there's a last event of this type, send it to the new subscriber
            if event_type in self._last_events:
                try:
                    callback(self._last_events[event_type])
                except Exception as e:
                    logging.error(
                        f"Error in late subscriber callback for {event_type}: {e}"
                    )

        logging.debug(f"Subscribed to {event_type}")

    def unsubscribe(
        self, event_type: EventType, callback: Callable[[Event], None]
    ) -> None:
        """
        Unsubscribe from an event type.

        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to remove from subscribers
        """
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].discard(callback)
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]

        logging.debug(f"Unsubscribed from {event_type}")

    def dispatch(self, event: Event) -> None:
        """
        Dispatch an event to all subscribers.

        Args:
            event: Event to dispatch
        """
        with self._lock:
            # Add to history
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)

            # Store as last event of this type
            self._last_events[event.event_type] = event

            # Get subscribers (make a copy to avoid issues if modified during iteration)
            subscribers = self._subscribers.get(event.event_type, set()).copy()

        # Call subscribers outside the lock to avoid deadlocks
        for callback in subscribers:
            try:
                # Execute callback in a separate thread to avoid blocking main thread
                import threading
                thread = threading.Thread(
                    target=self._safe_callback_wrapper,
                    args=(callback, event),
                    daemon=True
                )
                thread.start()
            except Exception as e:
                logging.error(f"Error dispatching event {event.event_type}: {e}")

        logging.debug(f"Dispatched event {event.event_type}")

    def _safe_callback_wrapper(self, callback: Callable, event: Event) -> None:
        """Safely execute callback in thread."""
        try:
            callback(event)
        except Exception as e:
            logging.error(f"Error in event callback for {event.event_type}: {e}")
            import traceback
            logging.error(f"Callback traceback: {traceback.format_exc()}")

    def dispatch_event(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        source: str = "unknown",
    ) -> None:
        """
        Convenience method to dispatch an event.

        Args:
            event_type: Type of event
            data: Event data
            source: Source of the event
        """
        event = Event(event_type=event_type, data=data or {}, source=source)
        self.dispatch(event)

    def get_last_event(self, event_type: EventType) -> Optional[Event]:
        """
        Get the last event of a specific type.

        Args:
            event_type: Type of event to get

        Returns:
            Last event of that type, or None if no event was dispatched
        """
        with self._lock:
            return self._last_events.get(event_type)

    def get_event_history(
        self, event_type: Optional[EventType] = None, limit: int = 100
    ) -> List[Event]:
        """
        Get recent event history.

        Args:
            event_type: Filter by event type (optional)
            limit: Maximum number of events to return

        Returns:
            List of recent events
        """
        with self._lock:
            events = self._event_history.copy()

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[-limit:]

    def clear_history(self) -> None:
        """Clear the event history."""
        with self._lock:
            self._event_history.clear()
            self._last_events.clear()
        logging.info("Event history cleared")

    def get_subscriber_count(self, event_type: EventType) -> int:
        """
        Get the number of subscribers for an event type.

        Args:
            event_type: Type of event

        Returns:
            Number of subscribers
        """
        with self._lock:
            return len(self._subscribers.get(event_type, set()))

    def get_all_event_types(self) -> List[EventType]:
        """
        Get all event types that have subscribers.

        Returns:
            List of event types with subscribers
        """
        with self._lock:
            return list(self._subscribers.keys())


# Legacy class name for compatibility
class EventSystem(EventDispatcher):
    """Legacy alias for EventDispatcher."""

    pass


# Global instance and convenience functions
_dispatcher: Optional[EventDispatcher] = None


def get_dispatcher() -> EventDispatcher:
    """Get the global event dispatcher instance."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = EventDispatcher.get_instance()
    return _dispatcher


def dispatch(
    event_type: EventType, data: Optional[Dict[str, Any]] = None, source: str = "api"
) -> None:
    """
    Convenience function to dispatch an event.

    Args:
        event_type: Type of event
        data: Event data
        source: Source of the event
    """
    get_dispatcher().dispatch_event(event_type, data, source)


def subscribe(event_type: EventType, callback: Callable[[Event], None]) -> None:
    """
    Convenience function to subscribe to an event.

    Args:
        event_type: Type of event to subscribe to
        callback: Function to call when event occurs
    """
    get_dispatcher().subscribe(event_type, callback)


def unsubscribe(event_type: EventType, callback: Callable[[Event], None]) -> None:
    """
    Convenience function to unsubscribe from an event.

    Args:
        event_type: Type of event to unsubscribe from
        callback: Function to remove from subscribers
    """
    get_dispatcher().unsubscribe(event_type, callback)


def get_last_event(event_type: EventType) -> Optional[Event]:
    """
    Convenience function to get the last event of a specific type.

    Args:
        event_type: Type of event to get

    Returns:
        Last event of that type, or None if no event was dispatched
    """
    return get_dispatcher().get_last_event(event_type)


def clear_event_history() -> None:
    """Convenience function to clear event history."""
    get_dispatcher().clear_history()
