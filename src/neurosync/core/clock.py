"""The single system clock.

Every timestamp in NeuroSync comes from a :class:`Clock`. The default
implementation, :class:`PerfCounterClock`, uses ``time.perf_counter_ns``
(QueryPerformanceCounter on Windows, ``CLOCK_MONOTONIC`` on Linux): monotonic,
with microsecond resolution or better on every platform.

``time.time()`` and ``time.monotonic()`` are not used: on Windows with Python
3.11 and 3.12 both advance in steps of about 15.6 ms. The relation to UTC is
kept separately as anchors (:mod:`neurosync.core.anchors`), so the clock is
never re-anchored in the middle of a recording.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Monotonic time source in nanoseconds."""

    def now_ns(self) -> int:
        """Current instant in ns. Never decreases between calls."""
        ...


class PerfCounterClock:
    """Default clock: ``time.perf_counter_ns``.

    On Windows this is QueryPerformanceCounter, which is system-wide: two
    processes on the same machine read the same time base.
    """

    __slots__ = ()

    def now_ns(self) -> int:
        """Current instant in ns."""
        return time.perf_counter_ns()


class ManualClock:
    """Hand-driven clock for deterministic tests.

    The instant only changes through :meth:`advance` or :meth:`set`.
    """

    __slots__ = ("_t",)

    def __init__(self, start_ns: int = 0) -> None:
        if start_ns < 0:
            raise ValueError("start_ns cannot be negative")
        self._t = start_ns

    def now_ns(self) -> int:
        """Current instant in ns."""
        return self._t

    def advance(self, delta_ns: int) -> None:
        """Move the clock forward by ``delta_ns`` (>= 0)."""
        if delta_ns < 0:
            raise ValueError("a monotonic clock does not go backwards")
        self._t += delta_ns

    def set(self, t_ns: int) -> None:
        """Set the instant; it cannot be earlier than the current one."""
        if t_ns < self._t:
            raise ValueError("a monotonic clock does not go backwards")
        self._t = t_ns


@dataclass(frozen=True, slots=True)
class ClockInfo:
    """What the OS reports about the clock; stored in every session sidecar."""

    implementation: str
    resolution_s: float
    monotonic: bool
    adjustable: bool


def perf_counter_info() -> ClockInfo:
    """Information about ``time.perf_counter`` on this machine."""
    info = time.get_clock_info("perf_counter")
    return ClockInfo(
        implementation=info.implementation,
        resolution_s=info.resolution,
        monotonic=info.monotonic,
        adjustable=info.adjustable,
    )
