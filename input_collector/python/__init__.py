"""
Python package for the Input Collector application.

This package contains modules for collecting, processing and visualizing input events
from keyboard and mouse devices.
"""
from .collectors import KeyboardMouseCollector
from .input_collector_app import InputCollectorApp, run_collector_app
from .interfaces import InputData, AbstractInputCollector
from .visualizers import KeyboardVisualizer, MouseVisualizer

__all__ = ['InputCollectorApp', 'run_collector_app']