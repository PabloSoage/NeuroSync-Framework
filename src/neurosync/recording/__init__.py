"""Recording module for binary XDF ingestion and sidecars (phase F4)."""

from neurosync.recording.recorder import Recorder
from neurosync.recording.sidecar import RecordingSummary, SessionSidecar
from neurosync.recording.xdf_writer import XdfWriter

__all__ = [
    "Recorder",
    "RecordingSummary",
    "SessionSidecar",
    "XdfWriter",
]
