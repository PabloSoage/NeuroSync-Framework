"""NeuroSync error hierarchy.

Rule: raise the most specific error and **catch only at boundaries** (an API
command, a GUI action, a thread loop). Never return altered data or a
``success: true`` to hide a failure.

Every error has ``code`` (stable, for clients) and ``http_status`` (used by the
API once it exists). The same classes serve the CLI and the GUI.
"""

from __future__ import annotations

from typing import ClassVar


class NeuroSyncError(Exception):
    """Base of all NeuroSync errors."""

    code: ClassVar[str] = "error"
    http_status: ClassVar[int] = 500

    def __init__(self, detail: str = "", **context: object) -> None:
        super().__init__(detail)
        self.detail = detail
        self.context = context

    def to_dict(self) -> dict[str, object]:
        """Stable representation for clients."""
        return {"code": self.code, "detail": self.detail, "context": dict(self.context)}


class InvalidInput(NeuroSyncError):
    """Parameters that make no sense (frequencies out of range, etc.)."""

    code = "invalid_input"
    http_status = 422


class NotFound(NeuroSyncError):
    """Missing resource (stream, session, board)."""

    code = "not_found"
    http_status = 404


class InvalidState(NeuroSyncError):
    """Operation impossible in the current state (e.g. already recording)."""

    code = "invalid_state"
    http_status = 409


class DeviceError(NeuroSyncError):
    """Device or driver failure."""

    code = "device_error"
    http_status = 502


class AcquisitionError(NeuroSyncError):
    """Failure inside a data source."""

    code = "acquisition_error"
    http_status = 500


class RecordingError(NeuroSyncError):
    """Failure while recording."""

    code = "recording_error"
    http_status = 500


class StopTimeout(NeuroSyncError):
    """A thread or process did not stop in time. Never ignored."""

    code = "stop_timeout"
    http_status = 500
