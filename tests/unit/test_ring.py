"""SignalRing and RingReader (phase F2)."""

from __future__ import annotations

import threading

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from neurosync.core.model import ChannelInfo, ChannelKind, QualityFlags, SampleChunk, StreamInfo
from neurosync.core.ring import NO_SOURCE_TS, SignalRing


def _info(n_channels: int = 2, fs: float = 100.0) -> StreamInfo:
    return StreamInfo(
        stream_id="s",
        source="test",
        channels=tuple(ChannelInfo(f"c{i}", ChannelKind.EEG) for i in range(n_channels)),
        nominal_fs=fs,
    )


def _chunk(
    seq0: int,
    n: int,
    n_channels: int = 2,
    t: int = 0,
    flags: QualityFlags = QualityFlags.NONE,
) -> SampleChunk:
    # Each sample value = its index, to check what gets copied.
    data = np.tile(np.arange(seq0, seq0 + n, dtype=np.float64), (n_channels, 1))
    return SampleChunk(stream_id="s", seq0=seq0, data=data, t_host_ns=t, flags=flags)


def test_simple_read() -> None:
    ring = SignalRing(_info(), capacity=10)
    reader = ring.reader()
    ring.write(_chunk(0, 4, t=7))
    sl = reader.read_new()
    assert sl is not None
    assert sl.n == 4 and sl.lost == 0
    assert list(sl.data[0]) == [0, 1, 2, 3]
    assert list(sl.seq) == [0, 1, 2, 3]
    assert list(sl.t_host_ns) == [7, 7, 7, 7]
    assert all(sl.t_source_ns == NO_SOURCE_TS)
    assert reader.read_new() is None


def test_wraps_without_loss_when_reader_keeps_up() -> None:
    ring = SignalRing(_info(), capacity=10)
    reader = ring.reader()
    seen: list[float] = []
    for k in range(0, 100, 3):
        ring.write(_chunk(k, 3))
        sl = reader.read_new()
        assert sl is not None and sl.lost == 0
        seen.extend(sl.data[0].tolist())
    assert seen == list(range(0, 102))


def test_late_reader_loses_oldest_and_knows_it() -> None:
    ring = SignalRing(_info(), capacity=10)
    reader = ring.reader()
    ring.write(_chunk(0, 8))
    ring.write(_chunk(8, 8))  # head = 16; only [6, 16) remains
    sl = reader.read_new()
    assert sl is not None
    assert sl.lost == 6
    assert list(sl.data[0]) == list(range(6, 16))
    assert sl.flags[0] & QualityFlags.OVERRUN
    assert reader.lost_total == 6


def test_read_last_does_not_move_cursor() -> None:
    ring = SignalRing(_info(), capacity=10)
    reader = ring.reader()
    ring.write(_chunk(0, 5))
    last = reader.read_last(3)
    assert list(last.data[0]) == [2, 3, 4]
    sl = reader.read_new()
    assert sl is not None and sl.n == 5


def test_chunk_flags_go_on_its_first_sample() -> None:
    ring = SignalRing(_info(), capacity=10)
    reader = ring.reader()
    ring.write(_chunk(0, 3, flags=QualityFlags.GAP))
    sl = reader.read_new()
    assert sl is not None
    assert sl.flags[0] & QualityFlags.GAP
    assert not sl.flags[1] & QualityFlags.GAP


def test_chunk_larger_than_ring_fails() -> None:
    ring = SignalRing(_info(), capacity=4)
    with pytest.raises(ValueError):
        ring.write(_chunk(0, 5))


def test_chunk_of_other_stream_fails() -> None:
    ring = SignalRing(_info(), capacity=4)
    data = np.zeros((2, 1))
    with pytest.raises(ValueError):
        ring.write(SampleChunk(stream_id="other", seq0=0, data=data, t_host_ns=0))


def test_reader_from_start() -> None:
    ring = SignalRing(_info(), capacity=10)
    ring.write(_chunk(0, 4))
    reader = ring.reader(from_start=True)
    sl = reader.read_new()
    assert sl is not None and sl.n == 4


@settings(max_examples=200, deadline=None)
@given(
    capacity=st.integers(1, 40),
    sizes=st.lists(st.integers(1, 40), min_size=1, max_size=40),
    reads=st.lists(st.integers(1, 50), min_size=1, max_size=40),
)
def test_property_read_plus_lost_equals_written(
    capacity: int, sizes: list[int], reads: list[int]
) -> None:
    ring = SignalRing(_info(1), capacity=capacity)
    reader = ring.reader()
    got: list[float] = []
    lost = 0
    seq = 0
    for i, n in enumerate(sizes):
        n = min(n, capacity)
        ring.write(_chunk(seq, n, n_channels=1))
        seq += n
        sl = reader.read_new(max_n=reads[i % len(reads)])
        if sl is not None:
            lost += sl.lost
            got.extend(sl.data[0].tolist())
    while (sl := reader.read_new()) is not None:
        lost += sl.lost
        got.extend(sl.data[0].tolist())
    # What was read is increasing, without repeats, and with the lost part covers everything.
    assert got == sorted(set(got))
    assert len(got) + lost == seq


def test_writer_and_reader_in_different_threads() -> None:
    """The reader never sees torn data: every sample equals its index."""
    ring = SignalRing(_info(4), capacity=64)
    reader = ring.reader()
    total = 200_000
    done = threading.Event()

    def writer() -> None:
        seq = 0
        while seq < total:
            ring.write(_chunk(seq, 16, n_channels=4))
            seq += 16
        done.set()

    t = threading.Thread(target=writer)
    t.start()
    read = 0
    lost = 0
    last = -1.0
    while not (done.is_set() and ring.head == reader.cursor):
        sl = reader.read_new()
        if sl is None:
            continue
        lost += sl.lost
        read += sl.n
        if sl.n:
            # Consistency: all four channels equal and the value is the index.
            assert np.array_equal(sl.data[0], sl.data[3])
            assert np.array_equal(sl.data[0], sl.seq.astype(np.float64))
            assert sl.data[0][0] > last
            last = float(sl.data[0][-1])
    t.join()
    assert read + lost == total
