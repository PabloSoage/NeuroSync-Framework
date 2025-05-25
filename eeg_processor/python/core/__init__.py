"""
Core functionality for EEG processor.

This package contains core components like event systems and other
shared functionality.
"""

from .event_system import EventSystem, EventType, Event

__all__ = ['EventSystem', 'EventType', 'Event']
