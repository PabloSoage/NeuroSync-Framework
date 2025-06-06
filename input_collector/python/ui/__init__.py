"""
UI package for the input collector application.

This package contains the user interface components used for visualizing and
interacting with input data. It includes the UIManager for overall UI control
and the VisualizerManager for managing various input visualization components.
"""

from .ui_manager import UIManager
from .visualizer_manager import VisualizerManager

__all__ = ["UIManager", "VisualizerManager"]
