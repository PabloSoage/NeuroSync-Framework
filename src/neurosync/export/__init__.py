"""Offline export facilities for converting recorded XDF sessions (phase F7).

Supports:
- CSV (time series and event logs)
- EDF+ (European Data Format with TAL annotations)
- BIDS (Brain Imaging Data Structure 1.9+ dataset layout)
- NumPy (.npz compressed archives)
"""

from __future__ import annotations

from neurosync.export.bids import export_session_to_bids
from neurosync.export.csv import export_session_to_csv
from neurosync.export.edf import export_session_to_edf
from neurosync.export.manager import ExportFormat, ExportManager
from neurosync.export.numpy_export import export_session_to_npz
from neurosync.export.reader import load_session
from neurosync.export.session import ExportSignalStream, ParsedSession

__all__ = [
    "ExportFormat",
    "ExportManager",
    "ExportSignalStream",
    "ParsedSession",
    "export_session_to_bids",
    "export_session_to_csv",
    "export_session_to_edf",
    "export_session_to_npz",
    "load_session",
]
