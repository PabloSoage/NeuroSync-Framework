"""
Adapters for bridging between UI frameworks and core services.

This package contains adapter classes that isolate UI framework
dependencies from core services.
"""

from .qt_interaction_adapter import QtInteractionAdapter

__all__ = ["QtInteractionAdapter"]
