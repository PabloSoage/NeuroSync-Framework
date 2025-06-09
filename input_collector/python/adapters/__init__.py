"""
Adapters package for input collector.

Contains adapter classes that bridge between UI frameworks and the
framework-independent core services, ensuring proper isolation and
thread-safe communication between different layers of the application.
"""

from .qt_interaction_adapter import QtInteractionAdapter

__all__ = [
    "QtInteractionAdapter",
]
