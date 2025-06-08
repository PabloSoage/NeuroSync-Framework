"""
Event system for coordinating interactions between API and GUI components.
"""

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Callable, Any, Optional


class EventType(Enum):
    """Types of events that can be triggered in the EEG processor."""

    # Connection events
    BOARD_CONNECT = "board_connect"
    BOARD_DISCONNECT = "board_disconnect"
    STREAM_START = "stream_start"
    STREAM_STOP = "stream_stop"

    # Processing events
    FILTER_APPLY = "filter_apply"
    VISUALIZATION_START = "visualization_start"
    VISUALIZATION_STOP = "visualization_stop"

    # Recording events
    RECORDING_START = "recording_start"
    RECORDING_STOP = "recording_stop"
    MARKER_INSERT = "marker_insert"

    # Streaming events
    STREAMER_ADD = "streamer_add"
    STREAMER_REMOVE = "streamer_remove"

    # Advanced processing events
    ICA_APPLY = "ica_apply"
    DOWNSAMPLE_APPLY = "downsample_apply"

    # MNE events
    MNE_EXPORT = "mne_export"
    MNE_IMPORT = "mne_import"

    # UI State events
    UI_UPDATE_STATUS = "ui_update_status"
    UI_UPDATE_CONTROLS = "ui_update_controls"


@dataclass
class Event:
    """Represents an event in the system."""

    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    timestamp: float = field(default_factory=lambda: __import__("time").time())


class EventSystem:
    """
    Central event system for coordinating interactions.

    This class manages event publishing and subscription, allowing
    different components to communicate without tight coupling.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "EventSystem":
        """Get the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = EventSystem()
            return cls._instance

    def __init__(self) -> None:
        """Initialize the event system."""
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._lock = threading.Lock()
        self._event_history: List[Event] = []
        self._max_history = 1000

        logging.info("Event system initialized")

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
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

        logging.debug(f"Subscribed to {event_type.value}")

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
                try:
                    self._subscribers[event_type].remove(callback)
                except ValueError:
                    pass

        logging.debug(f"Unsubscribed from {event_type.value}")

    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: Event to publish
        """
        with self._lock:
            # Add to history
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)

            # Notify subscribers
            subscribers = self._subscribers.get(event.event_type, []).copy()

        # Call subscribers outside the lock to avoid deadlocks
        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                logging.error(
                    f"Error in event callback for {event.event_type.value}: {e}"
                )

        logging.debug(f"Published event {event.event_type.value}")

    def publish_event(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        source: str = "unknown",
    ) -> None:
        """
        Convenience method to publish an event.

        Args:
            event_type: Type of event
            data: Event data
            source: Source of the event
        """
        event = Event(event_type=event_type, data=data or {}, source=source)
        self.publish(event)

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
        logging.info("Event history cleared")
