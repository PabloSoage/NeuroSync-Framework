"""
Interfaces package for input collector.

Provides the core interfaces and data structures used throughout the application
to ensure proper abstraction, loose coupling and maintainability. Contains
abstract base classes for input collectors, visualizers, and UI components,
along with the primary data structures for representing input events and
managing communication between different layers of the application.
"""

from .collector_interface import InputData, AbstractInputCollector
from .ui_visualizer_interface import (
    AbstractVisualizerProvider,
    AbstractVisualizerController,
)
from .visualizer_interface import AbstractVisualizer

__all__ = [
    "InputData",
    "AbstractInputCollector",
    "AbstractVisualizer",
    "AbstractVisualizerProvider",
    "AbstractVisualizerController",
]
