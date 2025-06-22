"""
Exporters package for dataset export operations.

Contains specialized exporters for different dataset formats
including HDF5, EDF+, and BIDS.
"""

from .export_manager import ExportManager
from .hdf5_exporter import HDF5Exporter

# Try to import other exporters with fallback
try:
    from .edf_exporter import EDFExporter
    EDF_AVAILABLE = True
except ImportError:
    EDF_AVAILABLE = False

try:
    from .bids_exporter import BIDSExporter
    BIDS_AVAILABLE = True
except ImportError:
    BIDS_AVAILABLE = False

__all__ = [
    "ExportManager",
    "HDF5Exporter",
]

if EDF_AVAILABLE:
    __all__.append("EDFExporter")

if BIDS_AVAILABLE:
    __all__.append("BIDSExporter")