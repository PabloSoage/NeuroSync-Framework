"""Unit tests for neurosyncd server, engine, and command registry (phase F8)."""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pytest
from brainflow.board_shim import BoardShim
from fastapi.testclient import TestClient

from neurosync.core.clock import PerfCounterClock
from neurosync.export.reader import load_session
from neurosync.server.app import create_app
from neurosync.server.engine import ServerEngine
from neurosync.server.schema import (
    ConfigureFilterRequest,
    StartAcquisitionRequest,
    StartRecordingRequest,
)


@pytest.fixture(autouse=True)
def disable_brainflow_logging() -> None:
    BoardShim.disable_board_logger()


def test_engine_lifecycle(tmp_path: Path) -> None:
    clock = PerfCounterClock()
    engine = ServerEngine(clock=clock)

    assert engine.get_status().status == "idle"

    # Start acquisition (Synthetic board)
    status_acq = engine.start_acquisition(StartAcquisitionRequest(board_id=-1))
    assert status_acq.status == "acquiring"
    assert engine.is_acquiring
    assert status_acq.primary_stream is not None
    assert len(status_acq.primary_stream.channels) >= 8

    # Dynamic filter configuration
    status_filt = engine.configure_filter(
        ConfigureFilterRequest(lowcut_hz=2.0, highcut_hz=40.0, notch_hz=50.0)
    )
    assert status_filt.filter_enabled

    # Start recording
    xdf_path = tmp_path / "server_test.xdf"
    status_rec = engine.start_recording(
        StartRecordingRequest(output_path=str(xdf_path), session_id="test_session_eng")
    )
    assert status_rec.status == "recording"
    assert engine.is_recording

    # Emit experimental marker
    ev = engine.emit_marker(marker_code=42, value=1.0)
    assert ev.code == 42

    # Stop recording
    summary = engine.stop_recording()
    assert summary.session_id == "test_session_eng"
    assert summary.total_events >= 1
    assert not engine.is_recording

    # Stop acquisition
    status_idle = engine.stop_acquisition()
    assert status_idle.status == "idle"
    assert not engine.is_acquiring

    # Verify XDF was written and is readable
    session = load_session(xdf_path)
    assert session.session_id == "test_session_eng"
    assert len(session.signals) >= 1
    assert len(session.events) >= 1
    assert session.events[0].code == 42


def test_fastapi_endpoints(tmp_path: Path) -> None:
    clock = PerfCounterClock()
    engine = ServerEngine(clock=clock)
    app = create_app(engine)
    client = TestClient(app)

    # 1. Health & status
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    res_status = client.get("/api/status")
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "idle"

    # 2. Start acquisition
    res_start = client.post("/api/acquisition/start", json={"board_id": -1})
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "acquiring"

    # 3. Emit marker
    res_mark = client.post("/api/markers", json={"marker_code": 99, "value": 3.14})
    assert res_mark.status_code == 200
    assert res_mark.json()["code"] == 99

    # 4. Configure filter
    res_filt = client.post(
        "/api/dsp/filter",
        json={"enabled": True, "lowcut_hz": 1.0, "highcut_hz": 45.0, "notch_hz": 50.0},
    )
    assert res_filt.status_code == 200
    assert res_filt.json()["filter_enabled"] is True

    # 5. Start recording
    xdf_path = tmp_path / "api_test.xdf"
    res_rec = client.post(
        "/api/recording/start",
        json={"output_path": str(xdf_path), "session_id": "api_session"},
    )
    assert res_rec.status_code == 200
    assert res_rec.json()["status"] == "recording"

    # Emit marker while recording is active
    client.post("/api/markers", json={"marker_code": 105, "value": 1.0})

    # 6. Stop recording
    res_stop_rec = client.post("/api/recording/stop")
    assert res_stop_rec.status_code == 200
    rec_data = res_stop_rec.json()
    assert rec_data["session_id"] == "api_session"
    assert rec_data["total_events"] >= 1

    # 7. Stop acquisition
    res_stop_acq = client.post("/api/acquisition/stop")
    assert res_stop_acq.status_code == 200
    assert res_stop_acq.json()["status"] == "idle"


def test_websocket_stream_binary_and_json() -> None:
    clock = PerfCounterClock()
    engine = ServerEngine(clock=clock)
    app = create_app(engine)
    client = TestClient(app)

    # Start acquisition so rings are populated
    res_acq = client.post("/api/acquisition/start", json={"board_id": -1})
    assert res_acq.status_code == 200

    # Test binary WebSocket stream
    with client.websocket_connect("/ws/stream?format=binary") as ws:
        msg = ws.receive_bytes()
        assert len(msg) >= 20  # Header size
        magic, n_ch, n_samples, _t_host_ns = struct.unpack("<4sIIQ", msg[:20])
        assert magic == b"NSYC"
        assert n_ch >= 8
        assert n_samples > 0
        data_bytes = msg[20:]
        arr = np.frombuffer(data_bytes, dtype="<f8")
        assert len(arr) == n_ch * n_samples

    # Test JSON WebSocket stream
    with client.websocket_connect("/ws/stream?format=json") as ws:
        json_data = ws.receive_json()
        assert "n_samples" in json_data
        assert "n_channels" in json_data
        assert "data" in json_data
        assert json_data["n_channels"] >= 8

    client.post("/api/acquisition/stop")
