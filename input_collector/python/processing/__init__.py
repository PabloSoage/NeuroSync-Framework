"""
Processing package for input events.

Contains modules for processing, formatting, and transforming input events
from various input sources including keyboards, mice, and game controllers.
Provides specialized event processors that handle display formatting, logging
preparation, special event detection, and coordinate transformations for
different input tracking modes and visualization requirements.
"""

from .event_processor import EventProcessor

__all__ = [
    "EventProcessor",
]
