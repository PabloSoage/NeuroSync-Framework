"""Unit tests for BrainFlowSource (phase F3)."""

from __future__ import annotations

import os
import tempfile
import threading
import time
from collections.abc import Iterator

import numpy as np
import pytest
from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams
from brainflow.data_filter import DataFilter

from neurosync.acquisition.brainflow_source import BrainFlowSource
from neurosync.core.clock import PerfCounterClock
from neurosync.core.errors import InvalidInput, InvalidState
from neurosync.core.model import ChannelKind, StreamInfo
from neurosync.core.ring import SignalRing


@pytest.fixture(autouse=True)
def _clean_brainflow() -> Iterator[None]:
    # Disable loud dev logs during testing
    BoardShim.disable_board_logger()
    yield


def test_brainflow_source_info() -> None:
    source = BrainFlowSource(BoardIds.SYNTHETIC_BOARD.value)
    info = source.info
    assert info.stream_id == "eeg"
    assert info.nominal_fs == 250.0
    assert info.n_channels == 16
    assert all(c.kind == ChannelKind.EEG for c in info.channels)


def test_brainflow_source_synthetic_10s() -> None:
    source = BrainFlowSource(BoardIds.SYNTHETIC_BOARD.value, read_period_s=0.005)
    clock = PerfCounterClock()
    ring = SignalRing(source.info, capacity=5000)
    reader = ring.reader()

    source.start(ring, clock)
    time.sleep(10.0)
    source.stop()

    assert source.error is None
    stats = source.stats()
    assert stats.gaps == 0
    assert stats.duplicates == 0
    assert 2300 <= ring.head <= 2700

    sl = reader.read_new()
    assert sl is not None
    assert sl.n == ring.head
    assert sl.lost == 0
    # Continuous sequence from 0 to head - 1
    assert np.array_equal(sl.seq, np.arange(sl.n, dtype=np.int64))


def test_brainflow_source_stop_cleanly() -> None:
    source = BrainFlowSource(BoardIds.SYNTHETIC_BOARD.value)
    clock = PerfCounterClock()
    ring = SignalRing(source.info, capacity=1000)

    source.start(ring, clock)
    time.sleep(0.2)
    t0 = time.perf_counter()
    source.stop(timeout_s=2.0)
    dt = time.perf_counter() - t0

    assert dt < 2.0
    active_thread_names = [t.name for t in threading.enumerate()]
    assert "source-eeg" not in active_thread_names

    # Idempotent stop
    source.stop(timeout_s=2.0)


def test_brainflow_source_error_handling() -> None:
    source = BrainFlowSource(BoardIds.SYNTHETIC_BOARD.value)
    clock = PerfCounterClock()
    ring = SignalRing(source.info, capacity=1000)

    # Insert marker before start fails
    with pytest.raises(InvalidState):
        source.insert_marker(1.0)

    # Wrong ring stream_id fails
    other_info = StreamInfo(
        stream_id="wrong_id",
        source="test",
        channels=source.info.channels,
        nominal_fs=250.0,
    )
    wrong_ring = SignalRing(other_info, capacity=1000)
    with pytest.raises(InvalidInput):
        source.start(wrong_ring, clock)

    # Start and start again fails
    source.start(ring, clock)
    try:
        with pytest.raises(InvalidState):
            source.start(ring, clock)
    finally:
        source.stop()


def test_brainflow_playback_file() -> None:
    master_id = BoardIds.SYNTHETIC_BOARD.value
    num_rows = BoardShim.get_num_rows(master_id)
    n_samples = 250 * 5  # 5 seconds test file for unit tests

    # Create dummy board matrix
    data = np.zeros((num_rows, n_samples), dtype=np.float64)
    pkg_ch = BoardShim.get_package_num_channel(master_id)
    ts_ch = BoardShim.get_timestamp_channel(master_id)
    eeg_channels = BoardShim.get_eeg_channels(master_id)

    data[pkg_ch] = np.arange(n_samples) % 256
    data[ts_ch] = 1700000000.0 + np.arange(n_samples) / 250.0

    # Fill EEG channels with identifiable pattern
    for i, ch_row in enumerate(eeg_channels):
        data[ch_row] = 10.0 * (i + 1) + np.sin(2 * np.pi * 5.0 * np.arange(n_samples) / 250.0)

    fd, temp_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)

    try:
        DataFilter.write_file(data, temp_path, "w")

        params = BrainFlowInputParams()
        params.file = temp_path
        params.master_board = master_id

        source = BrainFlowSource(
            BoardIds.PLAYBACK_FILE_BOARD.value,
            params,
            read_period_s=0.005,
        )
        clock = PerfCounterClock()
        ring = SignalRing(source.info, capacity=2000)
        reader = ring.reader()

        source.start(ring, clock)
        time.sleep(2.0)
        source.stop()

        assert source.error is None
        sl = reader.read_new()
        assert sl is not None
        assert sl.n > 0
        # Check channel data matches generated pattern
        for i in range(len(eeg_channels)):
            expected_sample0 = 10.0 * (i + 1)
            assert np.isclose(sl.data[i, 0], expected_sample0, atol=0.1)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
