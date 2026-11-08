"""Single clock and anchors (phase F1)."""

from __future__ import annotations

import time

import pytest

from neurosync.core.anchors import ClockAnchor, take_anchor
from neurosync.core.clock import Clock, ManualClock, PerfCounterClock, perf_counter_info


def test_perf_counter_clock_is_monotonic() -> None:
    clock = PerfCounterClock()
    prev = clock.now_ns()
    for _ in range(10_000):
        now = clock.now_ns()
        assert now >= prev
        prev = now


def test_clocks_implement_the_protocol() -> None:
    assert isinstance(PerfCounterClock(), Clock)
    assert isinstance(ManualClock(), Clock)


def test_clock_resolution_is_microseconds_or_better() -> None:
    # F1 criterion: smallest step < 1 us. Measure the smallest non-zero increment.
    clock = PerfCounterClock()
    steps: list[int] = []
    prev = clock.now_ns()
    while len(steps) < 1000:
        now = clock.now_ns()
        if now != prev:
            steps.append(now - prev)
            prev = now
    assert min(steps) < 1_000
    assert perf_counter_info().monotonic


def test_manual_clock_never_goes_back() -> None:
    clock = ManualClock(100)
    clock.advance(5)
    assert clock.now_ns() == 105
    clock.set(200)
    assert clock.now_ns() == 200
    with pytest.raises(ValueError):
        clock.advance(-1)
    with pytest.raises(ValueError):
        clock.set(199)


def test_anchor_matches_wall_clock() -> None:
    clock = PerfCounterClock()
    anchor = take_anchor(clock)
    # What the anchor predicts for "now" must be close to time.time_ns().
    predicted = anchor.to_unix_ns(clock.now_ns())
    actual = time.time_ns()
    # Margin: wall-clock resolution (15.6 ms on Windows with Python <= 3.12)
    # plus the anchor uncertainty.
    assert abs(predicted - actual) < 20_000_000 + anchor.uncertainty_ns
    assert anchor.uncertainty_ns < 50_000_000


def test_to_unix_ns_is_linear() -> None:
    anchor = ClockAnchor(mono_ns=1_000, unix_ns=1_700_000_000_000_000_000, uncertainty_ns=10)
    assert anchor.to_unix_ns(1_000) == 1_700_000_000_000_000_000
    assert anchor.to_unix_ns(2_500) == 1_700_000_000_000_001_500


def test_anchor_stores_lsl_clock_when_given() -> None:
    anchor = take_anchor(PerfCounterClock(), lsl_clock=lambda: 42.5)
    assert anchor.lsl_s == 42.5
