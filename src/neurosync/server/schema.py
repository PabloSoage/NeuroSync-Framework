"""Typed command registry and request/response schemas (phase F8, per D-10 & D-11).

Single source of truth for the HTTP API, WebSocket protocol, and CLI commands.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StreamStatus(BaseModel):
    """Status of an individual signal ring or stream."""

    stream_id: str
    nominal_fs: float
    channels: list[str]
    sample_count: int
    head: int


class ServerStatusResponse(BaseModel):
    """Overall status of the neurosyncd server process."""

    status: str = Field(description="Server state: idle, acquiring, recording")
    uptime_s: float = Field(description="Server process uptime in seconds")
    active_board: str | None = Field(default=None, description="Acquisition board name or id")
    primary_stream: StreamStatus | None = None
    filtered_stream: StreamStatus | None = None
    recording_file: str | None = None
    samples_recorded: int = 0
    events_recorded: int = 0
    filter_enabled: bool = False


class StartAcquisitionRequest(BaseModel):
    """Request to start signal acquisition from BrainFlow or simulated source."""

    board_id: int = Field(default=-1, description="BrainFlow board id (-1 for SYNTHETIC_BOARD)")
    serial_port: str | None = Field(default=None, description="Optional serial COM port")
    master_board: int | None = Field(default=None, description="Master board id for playback file")


class StopAcquisitionRequest(BaseModel):
    """Request to stop signal acquisition."""


class StartRecordingRequest(BaseModel):
    """Request to begin streaming recording to an append-only XDF file."""

    output_path: str = Field(description="Destination .xdf file path")
    session_id: str = Field(default="session", description="Unique session identifier")


class StopRecordingRequest(BaseModel):
    """Request to stop current recording session."""


class StopRecordingResponse(BaseModel):
    """Response returned upon stopping recording, containing session summary metrics."""

    session_id: str
    xdf_path: str
    duration_s: float
    total_samples: int
    total_events: int
    max_flush_lag_ms: float


class EmitMarkerRequest(BaseModel):
    """Request to stamp an experimental event or marker onto the EventBus."""

    marker_code: int = Field(description="Integer marker code (e.g. 1-255)")
    value: float = Field(default=1.0, description="Optional floating point trigger value")


class ConfigureFilterRequest(BaseModel):
    """Request to update causal SOS filter pipeline configuration."""

    enabled: bool = Field(default=True, description="Enable or bypass online filtering")
    lowcut_hz: float | None = Field(default=1.0, description="Highpass / Bandpass low cut")
    highcut_hz: float | None = Field(default=45.0, description="Lowpass / Bandpass high cut")
    notch_hz: float | None = Field(default=50.0, description="Mains notch filter frequency")


class ExportRequest(BaseModel):
    """Request to run offline conversion on an existing XDF recording."""

    xdf_path: str = Field(description="Path to the recorded .xdf file")
    output_dir: str = Field(description="Target directory for exported files")
    format: str = Field(default="all", description="Export target format: csv, edf, bids, npz, all")
    subject_id: str = Field(default="01", description="Subject identifier for BIDS")
    task_id: str = Field(default="experiment", description="Task label for BIDS")


class ExportResponse(BaseModel):
    """Response returned after running offline export."""

    results: dict[str, list[str]] = Field(
        default_factory=dict, description="Generated paths grouped by format"
    )
