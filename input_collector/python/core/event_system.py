"""
Core event system for the input collector.

This module provides a framework-independent event system that can be used
by both UI and API consumers.
"""

import threading
import time
from enum import Enum, auto
from typing import Dict, List, Any, Callable, Set, Optional

class EventType(Enum):
    """Types of events that can be emitted by the core system."""
    INPUT = auto()              # Raw input event
    STATE_CHANGE = auto()       # Application state change
    RECORDING_STARTED = auto()  # Recording started
    RECORDING_STOPPED = auto()  # Recording stopped
    EDIT_MODE_CHANGED = auto()  # Edit mode toggled
    COLLECTOR_CHANGED = auto()  # Collector switched
    TRACKED_KEYS_CHANGED = auto() # Tracked keys list changed

class EventDispatcher:
    """
    Core event dispatcher for the input collector.
    
    This class provides a centralized, framework-independent event system.
    UI components and API/websocket handlers can subscribe to events.
    """
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = EventDispatcher()
            return cls._instance
    
    def __init__(self):
        """Initialize the event dispatcher."""
        # Dict of event type -> set of subscribers
        self._subscribers: Dict[EventType, Set[Callable]] = {
            event_type: set() for event_type in EventType
        }
        
        # Last events for late subscribers
        self._last_events: Dict[EventType, Any] = {}
        
        # Lock for thread safety
        self._subscribers_lock = threading.Lock()
    
    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
        """
        with self._subscribers_lock:
            self._subscribers[event_type].add(callback)
            
            # Send last event of this type to new subscriber (for state synchronization)
            if event_type in self._last_events:
                try:
                    callback(self._last_events[event_type])
                except Exception as e:
                    print(f"Error in event callback during catchup: {e}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to unsubscribe
        """
        with self._subscribers_lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
    
    def dispatch(self, event_type: EventType, data: Any) -> None:
        """
        Dispatch an event to all subscribers.
        
        Args:
            event_type: Type of event to dispatch
            data: Event data to send to subscribers
        """
        # Store as last event of this type
        self._last_events[event_type] = data
        
        # Create a copy of subscribers to avoid issues if the list changes during iteration
        with self._subscribers_lock:
            subscribers = list(self._subscribers[event_type])
        
        # Notify all subscribers
        for callback in subscribers:
            try:
                callback(data)
            except Exception as e:
                print(f"Error in event subscriber: {e}")
                import traceback
                traceback.print_exc()

# Convenience functions
def get_dispatcher():
    """Get the event dispatcher instance."""
    return EventDispatcher.get_instance()

def dispatch(event_type: EventType, data: Any) -> None:
    """
    Dispatch an event.
    
    Args:
        event_type: Type of event to dispatch
        data: Event data
    """
    dispatcher = get_dispatcher()
    dispatcher.dispatch(event_type, data)

def subscribe(event_type: EventType, callback: Callable) -> None:
    """
    Subscribe to an event type.
    
    Args:
        event_type: Type of event to subscribe to
        callback: Function to call when event occurs
    """
    dispatcher = get_dispatcher()
    dispatcher.subscribe(event_type, callback)

def unsubscribe(event_type: EventType, callback: Callable) -> None:
    """
    Unsubscribe from an event type.
    
    Args:
        event_type: Type of event to unsubscribe from
        callback: Function to unsubscribe
    """
    dispatcher = get_dispatcher()
    dispatcher.unsubscribe(event_type, callback)
