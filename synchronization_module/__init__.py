"""
Synchronization Module for Brain-Computer Interface Dataset Creation

This module provides synchronization and dataset creation capabilities
for combining EEG processor and input collector data streams using
Lab Streaming Layer (LSL) for precise temporal alignment.
"""

from .python.synchronization_app import SynchronizationApp, run_synchronization_app

__all__ = [
    "SynchronizationApp",
    "run_synchronization_app",
]
