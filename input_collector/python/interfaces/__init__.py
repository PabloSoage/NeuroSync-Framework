"""
Interfaces module providing abstract classes and data structures.

This module defines abstract interfaces and data structures used throughout
the application for input collection and event handling.
"""
from .collector_interface import InputData, AbstractInputCollector

__all__ = ['InputData', 'AbstractInputCollector']