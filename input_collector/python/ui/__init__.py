"""
UI package for the input collector application.

Contains the user interface components used for visualizing and interacting
with input data from various sources including keyboards, mice, and game
controllers. Includes the UIManager for overall UI control, layout management,
and user interaction handling, along with the VisualizerManager for coordinating
various input visualization components and managing their lifecycle, updates,
and display modes across different collector types.
"""

from .ui_manager import UIManager
from .visualizer_manager import VisualizerManager

__all__ = [
    "UIManager",
    "VisualizerManager",
]
