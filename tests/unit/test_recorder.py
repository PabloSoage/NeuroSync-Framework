"""Unit tests for Recorder (phase F4)."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest
import pyxdf

from neurosync.acquisition.simulated import (
    SimSpec,
    SimulatedSource,
    Sine,
    device_time_ns,
    render,
)
from neurosync.core.anchors import ClockAnchor
from neurosync.core.bus import EventBus
from neurosync.core.clock import ManualClock, PerfCounterClock
from neurosync.core.errors import InvalidInput, InvalidState
from neurosync.core.model import InputEvent, InputKind, InputSourceKind
from neurosync.core.ring import SignalRing
from neurosync.recording.recorder import Recorder
from neurosync.recording.sidecar import SessionSidecar


def test_recorder_basic_lifecycle(tmp_path: Path) -> None:
    clock = PerfCounterClock()
    spec = SimSpec(signals=(Sine(10.0),), fs=250.0, n_channels=4)
    source = SimulatedSource(spec)
    ring = SignalRing(source.info, capacity=2000)

    bus: EventBus[InputEvent] = EventBus()
    path = tmp_path / "lifecycle.xdf"

    anchor = ClockAnchor(mono_ns=clock.now_ns(), unix_ns=1700000000_000000000, uncertainty_ns=50)

    recorder = Recorder(
        path=path,
        clock=clock,
        rings=[ring],
        bus=bus,
        initial_anchor=anchor,
        session_id="test_session",
    )

    # Double start raises InvalidState
    recorder.start()
    with pytest.raises(InvalidState):
        recorder.start()

    source.start(ring, clock)
    bus.publish(
        "input_events",
        InputEvent(
            seq=1,
            t_host_ns=clock.now_ns(),
            source=InputSourceKind.KEYBOARD,
            kind=InputKind.KEY_DOWN,
            code=65,
        ),
    )

    time.sleep(0.3)
    source.stop()
    summary = recorder.stop(timeout_s=2.0)

    assert summary.samples[source.info.stream_id] > 0
    assert summary.event_count >= 1
    assert summary.dropped_events == 0
    assert summary.losses[source.info.stream_id] == 0

    # Sidecar JSON exists and parses cleanly
    sidecar_path = path.with_suffix(".json")
    assert sidecar_path.exists()
    sidecar = SessionSidecar.load(sidecar_path)
    assert sidecar.session_id == "test_session"
    assert sidecar.initial_anchor is not None
    assert sidecar.initial_anchor.mono_ns == anchor.mono_ns
    assert sidecar.summary is not None
    assert sidecar.summary.samples[source.info.stream_id] == summary.samples[source.info.stream_id]

    # Read back with pyxdf
    streams, _header = pyxdf.load_xdf(str(path))
    assert len(streams) >= 3  # signal, aux, anchors, events


def test_recorder_simulated_crash(tmp_path: Path) -> None:
    clock = ManualClock(start_ns=1000_000_000)
    spec = SimSpec(signals=(Sine(5.0),), fs=250.0, n_channels=2)
    source = SimulatedSource(spec)
    ring = SignalRing(source.info, capacity=1000)

    path = tmp_path / "crash.xdf"
    recorder = Recorder(path=path, clock=clock, rings=[ring])

    # Emit first chunk of 100 samples
    source.emit_range(ring, clock, 100)
    clock.advance(1_000_000_000)
    recorder.record_all()  # commits flush + fsync + boundary

    # Simulate crash by closing file without stop() footers
    recorder._writer.close()

    # pyxdf must open the file and recover all flushed data
    streams, _header = pyxdf.load_xdf(
        str(path), synchronize_clocks=False, dejitter_timestamps=False
    )
    assert len(streams) >= 2  # signal and aux
    sig_stream = next(s for s in streams if s["info"]["name"][0] == source.info.stream_id)
    assert len(sig_stream["time_stamps"]) == 100


def test_recorder_quick_roundtrip(tmp_path: Path) -> None:
    clock = ManualClock(start_ns=1_000_000_000)
    spec = SimSpec(signals=(Sine(10.0, amplitude=15.0),), fs=250.0, n_channels=4)
    source = SimulatedSource(spec)
    ring = SignalRing(source.info, capacity=5000)

    path = tmp_path / "quick_roundtrip.xdf"
    recorder = Recorder(path=path, clock=clock, rings=[ring])

    n_samples = 2500  # 10 seconds of simulated signal
    source.emit_range(ring, clock, n_samples)
    clock.advance(10_000_000_000)
    recorder.record_all()
    recorder.stop()

    streams, _ = pyxdf.load_xdf(str(path), synchronize_clocks=False, dejitter_timestamps=False)
    sig_stream = next(s for s in streams if s["info"]["name"][0] == source.info.stream_id)
    aux_stream = next(s for s in streams if s["info"]["name"][0] == f"{source.info.stream_id}_aux")

    # Verify signal matches render() ground truth
    expected_data = render(spec, 0, n_samples)
    assert sig_stream["time_series"].shape == (n_samples, 4)
    assert np.allclose(sig_stream["time_series"].T, expected_data, atol=1e-12)

    # Verify seqs and device timestamps match ground truth
    expected_seqs = np.arange(n_samples, dtype=np.float64)
    expected_dev_ts = device_time_ns(spec, np.arange(n_samples)).astype(np.float64)
    assert np.allclose(aux_stream["time_series"][:, 0], expected_seqs)
    assert np.allclose(aux_stream["time_series"][:, 1], expected_dev_ts)


@pytest.mark.slow
def test_recorder_one_hour_roundtrip(tmp_path: Path) -> None:
    """1 hour simulated roundtrip (900,000 samples, 16 channels)."""
    clock = ManualClock(start_ns=1_000_000_000)
    spec = SimSpec(signals=(Sine(10.0, amplitude=25.0),), fs=250.0, n_channels=16)
    source = SimulatedSource(spec)
    ring = SignalRing(source.info, capacity=1_000_000)

    path = tmp_path / "one_hour.xdf"
    recorder = Recorder(path=path, clock=clock, rings=[ring])

    n_samples = 250 * 3600  # 900,000 samples
    source.emit_range(ring, clock, n_samples)
    clock.advance(3600_000_000_000)
    recorder.record_all()
    summary = recorder.stop()

    assert summary.samples[source.info.stream_id] == n_samples
    assert summary.losses[source.info.stream_id] == 0
    assert summary.gaps[source.info.stream_id] == 0

    streams, _ = pyxdf.load_xdf(str(path), synchronize_clocks=False, dejitter_timestamps=False)
    sig_stream = next(s for s in streams if s["info"]["name"][0] == source.info.stream_id)
    aux_stream = next(s for s in streams if s["info"]["name"][0] == f"{source.info.stream_id}_aux")

    expected_data = render(spec, 0, n_samples)
    assert sig_stream["time_series"].shape == (n_samples, 16)
    assert np.allclose(sig_stream["time_series"].T, expected_data, atol=1e-12)

    expected_seqs = np.arange(n_samples, dtype=np.float64)
    assert np.allclose(aux_stream["time_series"][:, 0], expected_seqs)


def test_recorder_invalid_inputs(tmp_path: Path) -> None:
    clock = ManualClock()
    with pytest.raises(InvalidInput, match="at least one SignalRing"):
        Recorder(path=tmp_path / "none.xdf", clock=clock, rings=[])
