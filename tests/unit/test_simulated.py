"""Simulated source (phase F2): determinism, ground truth and faults."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import numpy.typing as npt
import pytest

from neurosync.acquisition.simulated import (
    Drop,
    Duplicate,
    Flat,
    Pulse,
    SimSpec,
    SimulatedSource,
    Sine,
    WhiteNoise,
    delivered_packets,
    device_time_ns,
    render,
    stream_info,
)
from neurosync.core.clock import ManualClock, PerfCounterClock
from neurosync.core.errors import InvalidInput
from neurosync.core.model import QualityFlags
from neurosync.core.ring import SignalRing


def _drain_all(
    ring: SignalRing,
) -> tuple[npt.NDArray[Any], npt.NDArray[Any], npt.NDArray[Any]]:
    sl = ring.copy_range(0, ring.head)
    assert sl.lost == 0
    return sl.data, sl.seq, sl.flags


def test_render_does_not_depend_on_chunking() -> None:
    spec = SimSpec(n_channels=3, signals=(Sine(7.0), WhiteNoise(2.0), Pulse(at=(100, 1500))))
    whole = render(spec, 0, 3000)
    parts = np.concatenate([render(spec, k, 37) for k in range(0, 3000, 37)], axis=1)[:, :3000]
    assert np.array_equal(whole, parts)


def test_render_is_reproducible_with_same_seed() -> None:
    a = render(SimSpec(seed=3, signals=(WhiteNoise(),)), 0, 500)
    b = render(SimSpec(seed=3, signals=(WhiteNoise(),)), 0, 500)
    c = render(SimSpec(seed=4, signals=(WhiteNoise(),)), 0, 500)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_sine_and_pulse_in_place() -> None:
    spec = SimSpec(fs=1000.0, n_channels=2, signals=(Sine(10.0, amplitude=1.0),))
    x = render(spec, 0, 1000)
    # 10 Hz at 1000 Hz: peak at sample 25 (a quarter period).
    assert x[0, 25] == pytest.approx(1.0)
    pulse = Pulse(at=(10,), amplitude=5.0, width=3, channels=(1,))
    spec2 = SimSpec(n_channels=2, signals=(pulse,))
    y = render(spec2, 0, 20)
    assert list(np.flatnonzero(y[1])) == [10, 11, 12]
    assert not y[0].any()


def test_flat_channel() -> None:
    spec = SimSpec(n_channels=2, signals=(Sine(5.0), Flat(channel=1, value=3.0)))
    x = render(spec, 0, 50)
    assert np.all(x[1] == 3.0)


def test_drift_in_device_time() -> None:
    spec = SimSpec(fs=250.0, drift_ppm=100.0)
    t = device_time_ns(spec, [0, 250 * 3600])
    # One hour of nominal samples takes 360 ms less at +100 ppm.
    assert 3600e9 - t[1] == pytest.approx(0.36e9, rel=1e-3)


def test_written_equals_emitted() -> None:
    spec = SimSpec(fs=500.0, n_channels=4, chunk_size=5, signals=(Sine(3.0), WhiteNoise(1.0)))
    src = SimulatedSource(spec)
    ring = SignalRing(stream_info(spec), capacity=10_000)
    src.emit_range(ring, ManualClock(), 5_000)
    data, seq, _ = _drain_all(ring)
    assert np.array_equal(data, render(spec, 0, 5_000))
    assert list(seq) == list(range(5_000))
    assert src.stats().samples == 5_000


def test_drops_and_duplicates_are_counted_not_written() -> None:
    spec = SimSpec(
        n_channels=2,
        chunk_size=10,
        counter_bits=8,
        drops=(Drop(at=300, count=5),),
        duplicates=(Duplicate(at=700, count=2),),
    )
    assert len(delivered_packets(spec, 0, 1000)) == 1000 - 5 + 2
    src = SimulatedSource(spec)
    ring = SignalRing(stream_info(spec), capacity=2_000)
    src.emit_range(ring, ManualClock(), 1_000)
    data, seq, flags = _drain_all(ring)
    st = src.stats()
    assert st.gaps == 5
    assert st.duplicates == 2
    # The index jumps over the gap and there are no repeats.
    assert len(seq) == 995
    assert list(seq[:300]) == list(range(300))
    assert seq[300] == 305
    assert np.all(np.diff(seq) >= 1)
    # The first sample after the gap is flagged GAP.
    assert flags[300] & QualityFlags.GAP
    # The data at each index is the device data for that index.
    assert np.array_equal(data[:, 300], render(spec, 305, 1)[:, 0])


def test_wrapping_counter_in_long_session() -> None:
    spec = SimSpec(n_channels=1, chunk_size=4, counter_bits=8)
    src = SimulatedSource(spec)
    ring = SignalRing(stream_info(spec), capacity=20_000)
    src.emit_range(ring, ManualClock(), 10_000)  # 39 counter wraps
    _, seq, _ = _drain_all(ring)
    assert list(seq) == list(range(10_000))


def test_validation() -> None:
    with pytest.raises(InvalidInput):
        SimSpec(fs=0).validate()
    with pytest.raises(InvalidInput):
        SimSpec(signals=(Pulse(at=(1,), channels=(99,)),)).validate()
    with pytest.raises(InvalidInput):
        SimSpec(counter_bits=8, drops=(Drop(at=10, count=200),)).validate()


def test_realtime_thread_keeps_pace_and_stops() -> None:
    spec = SimSpec(fs=1000.0, n_channels=2, chunk_size=10)
    src = SimulatedSource(spec)
    ring = SignalRing(stream_info(spec), capacity=10_000)
    src.start(ring, PerfCounterClock())
    time.sleep(0.5)
    src.stop()
    assert src.error is None
    # About 500 samples; wide margin for slow CI runners.
    assert 200 <= ring.head <= 800
    _, seq, _ = _drain_all(ring)
    assert list(seq) == list(range(ring.head))
