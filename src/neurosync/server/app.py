"""FastAPI application for neurosyncd server (phase F8 & F10, per D-10 & D-11).

Provides typed REST endpoints, high-throughput real-time binary WebSockets,
and serves the real-time web visualizer dashboard.
"""

from __future__ import annotations

import asyncio
import contextlib
import struct
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from neurosync.core.bus import Policy
from neurosync.core.errors import InvalidInput, InvalidState, NeuroSyncError
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
)
from neurosync.web import get_static_dir, get_web_dir


def create_app(engine: ServerEngine | None = None) -> FastAPI:
    """Create and configure the neurosyncd FastAPI application."""
    active_engine = engine or ServerEngine()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        # Clean shutdown on server stop
        if active_engine.is_acquiring:
            active_engine.stop_acquisition()

    app = FastAPI(
        title="NeuroSync Daemon (neurosyncd)",
        description="High-performance EEG acquisition, causal DSP, and lossless recording.",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Expose engine on app.state for testing and dependency injection
    app.state.engine = active_engine

    # Mount static assets for the real-time web dashboard (Phase F10)
    static_dir = get_static_dir()
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        """Serve the real-time web visualizer dashboard."""
        index_file = get_web_dir() / "index.html"
        if not index_file.exists():
            raise HTTPException(status_code=404, detail="Dashboard index not found")
        return FileResponse(index_file)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "neurosyncd"}

    @app.get("/api/status", response_model=ServerStatusResponse)
    async def get_status() -> ServerStatusResponse:
        return active_engine.get_status()

    @app.post("/api/acquisition/start", response_model=ServerStatusResponse)
    async def start_acquisition(req: StartAcquisitionRequest) -> ServerStatusResponse:
        try:
            return active_engine.start_acquisition(req)
        except (InvalidState, InvalidInput, NeuroSyncError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/acquisition/stop", response_model=ServerStatusResponse)
    async def stop_acquisition() -> ServerStatusResponse:
        return active_engine.stop_acquisition()

    @app.post("/api/recording/start", response_model=ServerStatusResponse)
    async def start_recording(req: StartRecordingRequest) -> ServerStatusResponse:
        try:
            return active_engine.start_recording(req)
        except (InvalidState, InvalidInput, NeuroSyncError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/recording/stop", response_model=StopRecordingResponse)
    async def stop_recording() -> StopRecordingResponse:
        try:
            return active_engine.stop_recording()
        except (InvalidState, InvalidInput, NeuroSyncError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/markers")
    async def emit_marker(req: EmitMarkerRequest) -> dict[str, Any]:
        ev = active_engine.emit_marker(req.marker_code, req.value)
        return {
            "seq": ev.seq,
            "t_host_ns": ev.t_host_ns,
            "code": ev.code,
            "value": ev.value,
        }

    @app.post("/api/dsp/filter", response_model=ServerStatusResponse)
    async def configure_filter(req: ConfigureFilterRequest) -> ServerStatusResponse:
        return active_engine.configure_filter(req)

    @app.post("/api/export", response_model=ExportResponse)
    async def export_session(req: ExportRequest) -> ExportResponse:
        try:
            return active_engine.run_export(req)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.websocket("/ws/stream")
    async def stream_websocket(
        ws: WebSocket,
        stream: str = Query(default="filtered"),
        fmt: str = Query(default="binary"),
    ) -> None:
        """Stream real-time signal chunks over WebSocket.

        Supports both raw binary format (ultra-fast) and JSON format.
        """
        await ws.accept()

        fmt_mode = ws.query_params.get("format", fmt)
        current_ring = None
        reader = None

        with contextlib.suppress(WebSocketDisconnect, asyncio.CancelledError):
            while True:
                target_ring = (
                    active_engine.filtered_ring if stream == "filtered" else active_engine.raw_ring
                )
                if target_ring is None:
                    target_ring = active_engine.raw_ring

                if target_ring is not current_ring:
                    current_ring = target_ring
                    reader = current_ring.reader() if current_ring is not None else None

                if reader is not None:
                    chunk = reader.read_new()
                    if chunk is not None and chunk.n > 0:
                        n_channels = int(chunk.data.shape[0])
                        t_host = int(chunk.t_host_ns[0]) if len(chunk.t_host_ns) > 0 else 0
                        if fmt_mode == "json":
                            payload = {
                                "n_samples": chunk.n,
                                "n_channels": n_channels,
                                "t_host_ns": t_host,
                                "data": chunk.data.tolist(),
                            }
                            await ws.send_json(payload)
                        else:
                            # Binary framing: [4B 'NSYC'][4B n_ch][4B n_samples][8B t_host_ns]
                            header = struct.pack(
                                "<4sIIQ",
                                b"NSYC",
                                n_channels,
                                chunk.n,
                                t_host,
                            )
                            # contiguous float64 array bytes
                            data_bytes = chunk.data.astype("<f8").tobytes()
                            await ws.send_bytes(header + data_bytes)

                # ~25Hz flush rate for client stream
                await asyncio.sleep(0.040)

    @app.websocket("/ws/events")
    async def events_websocket(ws: WebSocket) -> None:
        """Stream real-time input and marker events over WebSocket."""
        await ws.accept()
        sub = active_engine.bus.subscribe(
            topic="input_events",
            name="ws-events",
            maxsize=1024,
            policy=Policy.DROP_OLDEST,
        )

        try:
            with contextlib.suppress(WebSocketDisconnect, asyncio.CancelledError):
                while True:
                    envelopes = sub.drain(max_n=50)
                    for env in envelopes:
                        ev = env.msg
                        await ws.send_json(
                            {
                                "seq": env.seq,
                                "code": ev.code,
                                "t_host_ns": ev.t_host_ns,
                                "payload": {"value": ev.value, "kind": ev.kind.value},
                            }
                        )
                    await asyncio.sleep(0.040)
        finally:
            sub.close()

    return app
