"""
Event system for the integrated BCI system.

This module provides an event system for communication between components.
"""

from typing import Dict, Any, Callable, List, Set
import logging


class EventSystem:
    """
    Event system for communication between components.
    
    This class implements the Observer pattern to decouple components
    and provide a standardized way for them to communicate.
    """
    
    def __init__(self):
        """Initialize the event system."""
        self._listeners = {}
        
    def subscribe(self, event_type: str, listener: Callable):
        """
        Subscribe a listener to an event type.
        
        Args:
            event_type: Event type to subscribe to
            listener: Callback function to call when event occurs
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = set()
            
        self._listeners[event_type].add(listener)
        logging.debug(f"Subscribed to event '{event_type}': {listener.__name__}")
        
    def unsubscribe(self, event_type: str, listener: Callable):
        """
        Unsubscribe a listener from an event type.
        
        Args:
            event_type: Event type to unsubscribe from
            listener: Callback function to remove
        """
        if event_type in self._listeners and listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)
            logging.debug(f"Unsubscribed from event '{event_type}': {listener.__name__}")
            
            # Clean up empty event types
            if not self._listeners[event_type]:
                del self._listeners[event_type]
                
    def emit(self, event_type: str, data: Any = None):
        """
        Emit an event to all subscribed listeners.
        
        Args:
            event_type: Type of event to emit
            data: Data to pass to listeners
        """
        if event_type in self._listeners:
            # Create a copy to avoid modification during iteration
            listeners = list(self._listeners[event_type])
            
            for listener in listeners:
                try:
                    if data is not None:
                        listener(data)
                    else:
                        listener()
                except Exception as e:
                    logging.error(f"Error in event listener for '{event_type}': {e}")
        
        
class EventTypes:
    """Constants for event types used in the application."""
    
    # Recording events
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"
    
    # EEG events
    EEG_CONNECTED = "eeg_connected"
    EEG_DISCONNECTED = "eeg_disconnected"
    EEG_STREAM_STARTED = "eeg_stream_started"
    EEG_STREAM_STOPPED = "eeg_stream_stopped"
    
    # Input events
    INPUT_STATE_CHANGED = "input_state_changed"
    
    # UI events
    UI_SETTINGS_CHANGED = "ui_settings_changed"
