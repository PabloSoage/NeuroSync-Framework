"""HTTP and WebSocket client for communicating with neurosyncd (phase F9).

Shares schemas from neurosync.server.schema per D-11.
"""

from __future__ import annotations

import httpx

from neurosync.core.errors import DeviceError, InvalidState
from neurosync.server.schema import (
    ConfigureFilterRequest,
    EmitMarkerRequest,
    ExportRequest,
    ExportResponse,
    ServerStatusResponse,
    StartAcquisitionRequest,
    StartRecordingRequest,
    StopRecordingResponse,
)


class NeuroSyncClient:
    """Client for controlling neurosyncd daemon over HTTP/REST."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(base_url=self.base_url, timeout=10.0)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> NeuroSyncClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def check_health(self) -> bool:
        """Check if neurosyncd server is responsive."""
        try:
            res = self._http.get("/health")
            return res.status_code == 200
        except httpx.HTTPError:
            return False

    def get_status(self) -> ServerStatusResponse:
        """Query server status."""
        res = self._http.get("/api/status")
        if res.status_code != 200:
            raise InvalidState(f"Server error: {res.text}")
        return ServerStatusResponse.model_validate(res.json())

    def start_acquisition(
        self,
        board_id: int = -1,
        serial_port: str | None = None,
        master_board: int | None = None,
    ) -> ServerStatusResponse:
        """Start acquisition on server."""
        req = StartAcquisitionRequest(
            board_id=board_id,
            serial_port=serial_port,
            master_board=master_board,
        )
        res = self._http.post("/api/acquisition/start", json=req.model_dump())
        if res.status_code != 200:
            raise DeviceError(f"Failed to start acquisition: {res.text}")
        return ServerStatusResponse.model_validate(res.json())

    def stop_acquisition(self) -> ServerStatusResponse:
        """Stop acquisition on server."""
        res = self._http.post("/api/acquisition/stop")
        if res.status_code != 200:
            raise DeviceError(f"Failed to stop acquisition: {res.text}")
        return ServerStatusResponse.model_validate(res.json())

    def start_recording(
        self,
        output_path: str,
        session_id: str = "session",
    ) -> ServerStatusResponse:
        """Start recording to XDF file."""
        req = StartRecordingRequest(output_path=output_path, session_id=session_id)
        res = self._http.post("/api/recording/start", json=req.model_dump())
        if res.status_code != 200:
            raise InvalidState(f"Failed to start recording: {res.text}")
        return ServerStatusResponse.model_validate(res.json())

    def stop_recording(self) -> StopRecordingResponse:
        """Stop recording and return summary."""
        res = self._http.post("/api/recording/stop")
        if res.status_code != 200:
            raise InvalidState(f"Failed to stop recording: {res.text}")
        return StopRecordingResponse.model_validate(res.json())

    def emit_marker(self, marker_code: int, value: float = 1.0) -> dict[str, object]:
        """Emit experimental marker."""
        req = EmitMarkerRequest(marker_code=marker_code, value=value)
        res = self._http.post("/api/markers", json=req.model_dump())
        if res.status_code != 200:
            raise InvalidState(f"Failed to emit marker: {res.text}")
        return dict(res.json())

    def configure_filter(
        self,
        enabled: bool = True,
        lowcut_hz: float | None = 1.0,
        highcut_hz: float | None = 45.0,
        notch_hz: float | None = 50.0,
    ) -> ServerStatusResponse:
        """Configure filter pipeline on server."""
        req = ConfigureFilterRequest(
            enabled=enabled,
            lowcut_hz=lowcut_hz,
            highcut_hz=highcut_hz,
            notch_hz=notch_hz,
        )
        res = self._http.post("/api/dsp/filter", json=req.model_dump())
        if res.status_code != 200:
            raise InvalidState(f"Failed to configure filter: {res.text}")
        return ServerStatusResponse.model_validate(res.json())

    def export(
        self,
        xdf_path: str,
        output_dir: str,
        format_name: str = "all",
        subject_id: str = "01",
        task_id: str = "experiment",
    ) -> ExportResponse:
        """Run export request on server."""
        req = ExportRequest(
            xdf_path=xdf_path,
            output_dir=output_dir,
            format=format_name,
            subject_id=subject_id,
            task_id=task_id,
        )
        res = self._http.post("/api/export", json=req.model_dump())
        if res.status_code != 200:
            raise InvalidState(f"Failed to export: {res.text}")
        return ExportResponse.model_validate(res.json())
