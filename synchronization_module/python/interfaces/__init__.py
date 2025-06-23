"""
Interfaces package for synchronization operations.

Contains abstract interfaces for synchronization, LSL stream management,
and dataset export operations.
"""

from .synchronization_interface import SynchronizationInterface, LSLStreamInterface
from .export_interface import DatasetExporterInterface, MetadataInterface

__all__ = [
    "SynchronizationInterface",
    "LSLStreamInterface",
    "DatasetExporterInterface",
    "MetadataInterface",
]
