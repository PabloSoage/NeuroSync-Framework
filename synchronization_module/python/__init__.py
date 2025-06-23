"""
Python package for the Synchronization Module.

This package provides the core functionality for synchronizing EEG and
input data streams, creating datasets in standard formats, and managing
the unified GUI application.
"""

from .synchronization_app import SynchronizationApp, run_synchronization_app

__all__ = [
    "SynchronizationApp",
    "run_synchronization_app",
]
