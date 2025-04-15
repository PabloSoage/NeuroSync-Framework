"""
Visualization components for the input collector.

This module provides visual components for displaying and interacting with
input data in real-time using PyQt5.
"""
from .keyboard_viz import KeyboardVisualizer
from .mouse_viz import MouseVisualizer
from .mouse_buttons_selector import MouseButtonsSelector

__all__ = ['KeyboardVisualizer', 'MouseVisualizer', 'MouseButtonsSelector']