"""
Core package for input collector.

Contains the core event system used for decoupled communication
throughout the application and with external integrations. This system
provides a framework-independent event dispatcher that allows different
components (UI, API, services) to communicate without tight coupling,
supporting both synchronous event dispatch and subscription management.
"""

from .event_system import (
    EventType,
    EventDispatcher,
    get_dispatcher,
    dispatch,
    subscribe,
    unsubscribe,
)

__all__ = [
    "EventType",
    "EventDispatcher",
    "get_dispatcher",
    "dispatch",
    "subscribe",
    "unsubscribe",
]
