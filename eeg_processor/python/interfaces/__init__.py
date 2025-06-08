"""
Interfaces package for EEG data collection and processing.

This package contains abstract base classes that define the contracts
for various components of the EEG processing system.
"""

from .collector_interface import CollectorInterface

__all__ = ["CollectorInterface"]
