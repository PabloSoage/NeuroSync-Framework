"""Server process and command registry for neurosyncd (phase F8, per D-10 & D-11).

Provides:
- ServerEngine: hardware ownership, causal DSP, lossless recording
- Typed command registry (Pydantic v2 schemas)
- FastAPI application with REST endpoints and real-time binary WebSockets
- Service runner using Uvicorn
"""

from __future__ import annotations

from neurosync.server.app import create_app
from neurosync.server.engine import ServerEngine
from neurosync.server.schema import (
    ConfigureFilterRequest,
    EmitMarkerRequest,
    ExportRequest,
    ExportResponse,
    ServerStatusResponse,
    StartAcquisitionRequest,
    StartRecordingRequest,
    StopRecordingResponse,
    StreamStatus,
)
from neurosync.server.service import run_server

__all__ = [
    "ConfigureFilterRequest",
    "EmitMarkerRequest",
    "ExportRequest",
    "ExportResponse",
    "ServerEngine",
    "ServerStatusResponse",
    "StartAcquisitionRequest",
    "StartRecordingRequest",
    "StopRecordingResponse",
    "StreamStatus",
    "create_app",
    "run_server",
]
