"""
Core package for the EEG processor.

This package contains core functionality that is framework-independent
and can be used by any part of the application.
"""

from .event_system import EventType, dispatch, subscribe, unsubscribe

__all__ = ['EventType', 'dispatch', 'subscribe', 'unsubscribe']
