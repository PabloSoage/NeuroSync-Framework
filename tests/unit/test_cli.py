"""Unit tests for NeuroSync Typer CLI (phase F9)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from brainflow.board_shim import BoardShim
from typer.testing import CliRunner

from neurosync.acquisition.simulated import SimSpec, Sine, render
from neurosync.cli.main import app
from neurosync.core.anchors import ClockAnchor
from neurosync.core.bus import EventBus
from neurosync.core.clock import PerfCounterClock
from neurosync.core.model import ChannelInfo, ChannelKind, InputEvent, SampleChunk, StreamInfo
from neurosync.core.ring import SignalRing
from neurosync.recording.recorder import Recorder
from neurosync.server.schema import ServerStatusResponse, StopRecordingResponse, StreamStatus

runner = CliRunner()


@pytest.fixture(autouse=True)
def disable_brainflow_logging() -> None:
    BoardShim.disable_board_logger()


@pytest.fixture
def sample_xdf(tmp_path: Path) -> Path:
    """Create a minimal real XDF file for CLI export testing."""
    clock = PerfCounterClock()
    spec = SimSpec(signals=(Sine(10.0),), fs=250.0, n_channels=2)
    info = StreamInfo(
        stream_id="cli_test",
        source="sim",
        nominal_fs=250.0,
        channels=(
            ChannelInfo(name="Ch1", kind=ChannelKind.EEG, unit="uV"),
            ChannelInfo(name="Ch2", kind=ChannelKind.EEG, unit="uV"),
        ),
    )
    ring = SignalRing(info, capacity=500)
    bus: EventBus[InputEvent] = EventBus()
    xdf_path = tmp_path / "cli_sample.xdf"

    anchor = ClockAnchor(mono_ns=clock.now_ns(), unix_ns=1700000000_000000000, uncertainty_ns=50)
    rec = Recorder(
        path=xdf_path,
        clock=clock,
        rings=[ring],
        bus=bus,
        initial_anchor=anchor,
        session_id="cli_sess",
        batch_interval_s=0.01,
        fsync_interval_s=0.05,
    )
    rec.start()
    data = render(spec, 0, 250)
    ring.write(SampleChunk(stream_id="cli_test", seq0=0, data=data, t_host_ns=clock.now_ns()))
    rec.stop(timeout_s=2.0)
    return xdf_path


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "High-performance EEG acquisition" in result.stdout
    assert "status" in result.stdout
    assert "start" in result.stdout
    assert "stop" in result.stdout
    assert "record" in result.stdout
    assert "export" in result.stdout


def test_cli_status_server_down() -> None:
    with patch("neurosync.cli.main._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.check_health.return_value = False
        mock_get_client.return_value = mock_client

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 1
        assert "server is not running" in result.stdout


def test_cli_status_server_running() -> None:
    with patch("neurosync.cli.main._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.check_health.return_value = True
        mock_client.get_status.return_value = ServerStatusResponse(
            status="acquiring",
            uptime_s=12.34,
            active_board="Synthetic",
            filter_enabled=True,
            primary_stream=StreamStatus(
                stream_id="primary",
                nominal_fs=250.0,
                channels=["Fp1", "Fp2"],
                sample_count=500,
                head=500,
            ),
        )
        mock_get_client.return_value = mock_client

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "ACQUIRING" in result.stdout
        assert "12.34 s" in result.stdout
        assert "Synthetic" in result.stdout
        assert "Fp1, Fp2" in result.stdout


def test_cli_start_and_stop_acquisition() -> None:
    with patch("neurosync.cli.main._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.start_acquisition.return_value = ServerStatusResponse(
            status="acquiring", uptime_s=1.0
        )
        mock_client.stop_acquisition.return_value = ServerStatusResponse(
            status="idle", uptime_s=2.0
        )
        mock_get_client.return_value = mock_client

        res_start = runner.invoke(app, ["start", "--board-id", "-1"])
        assert res_start.exit_code == 0
        assert "Acquisition started" in res_start.stdout

        res_stop = runner.invoke(app, ["stop"])
        assert res_stop.exit_code == 0
        assert "Acquisition stopped" in res_stop.stdout


def test_cli_record_lifecycle() -> None:
    with patch("neurosync.cli.main._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.start_recording.return_value = ServerStatusResponse(
            status="recording", uptime_s=5.0, recording_file="test.xdf"
        )
        mock_client.stop_recording.return_value = StopRecordingResponse(
            session_id="test_sess",
            xdf_path="test.xdf",
            duration_s=10.5,
            total_samples=2500,
            total_events=3,
            max_flush_lag_ms=1.2,
        )
        mock_client.emit_marker.return_value = {"code": 100, "seq": 1}
        mock_client.configure_filter.return_value = ServerStatusResponse(
            status="recording", uptime_s=6.0, filter_enabled=True
        )
        mock_get_client.return_value = mock_client

        # Record start
        res_rec = runner.invoke(app, ["record", "test.xdf", "--session-id", "test_sess"])
        assert res_rec.exit_code == 0
        assert "Recording started" in res_rec.stdout

        # Marker
        res_mark = runner.invoke(app, ["marker", "100", "--value", "2.0"])
        assert res_mark.exit_code == 0
        assert "Marker injected" in res_mark.stdout

        # Filter config
        res_filt = runner.invoke(app, ["filter", "--lowcut", "2.0", "--highcut", "40.0"])
        assert res_filt.exit_code == 0
        assert "Filter configured successfully" in res_filt.stdout

        # Record stop
        res_stop = runner.invoke(app, ["stop-record"])
        assert res_stop.exit_code == 0
        assert "Recording Summary" in res_stop.stdout
        assert "2500" in res_stop.stdout


def test_cli_export_command(sample_xdf: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "cli_exported"
    res = runner.invoke(
        app,
        ["export", str(sample_xdf), "--out", str(out_dir), "--format", "all"],
    )
    assert res.exit_code == 0
    assert "Export Completed" in res.stdout
    assert (out_dir / "cli_sess_cli_test.csv").is_file()
    assert (out_dir / "cli_sess.edf").is_file()
    assert (out_dir / "cli_sess.npz").is_file()
    assert (out_dir / "bids").is_dir()
