"""
Interfaces package for input collector.

Provides the core interfaces used throughout the application to ensure
proper abstraction, loose coupling and maintainability.
"""

from .collector_interface import InputData, AbstractInputCollector
from .ui_visualizer_interface import AbstractVisualizerProvider, AbstractVisualizerController
from .visualizer_interface import AbstractVisualizer

__all__ = [
    'InputData', 
    'AbstractInputCollector',
    'AbstractVisualizer',
    'AbstractVisualizerProvider',
    'AbstractVisualizerController'
]
