"""Anchors between the monotonic clock and UTC.

This is the **only** module under ``src/`` allowed to read wall-clock time
(``time.time_ns``). ``tests/arch/test_rules.py`` enforces it.

An anchor says: "monotonic instant ``mono_ns`` corresponds to UTC ``unix_ns``,
with an uncertainty of ``uncertainty_ns``". Anchors are taken when a session
starts and then every ~10 s, and are stored as one more stream. Wall-clock
corrections (NTP, ``w32time``) therefore never make recording timestamps jump.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from neurosync.core.clock import Clock

#: Maximum wait for the wall clock to change value while taking an anchor.
#: On Windows with Python <= 3.12 it changes every ~15.6 ms; 50 ms leaves margin.
DEFAULT_MAX_WAIT_NS = 50_000_000


@dataclass(frozen=True, slots=True)
class ClockAnchor:
    """Correspondence between the monotonic clock and UTC."""

    mono_ns: int
    unix_ns: int
    uncertainty_ns: int
    lsl_s: float | None = None

    def to_unix_ns(self, mono_ns: int) -> int:
        """Convert a monotonic instant to UTC ns using this anchor."""
        return self.unix_ns + (mono_ns - self.mono_ns)


def take_anchor(
    clock: Clock,
    *,
    max_wait_ns: int = DEFAULT_MAX_WAIT_NS,
    lsl_clock: Callable[[], float] | None = None,
) -> ClockAnchor:
    """Take an anchor by waiting for the edge where the wall clock changes.

    With a coarse wall clock (Windows, Python <= 3.12) the edge is exact in UTC
    and is bracketed on the monotonic clock between two consecutive reads. With
    a fine wall clock it changes on every read, and the uncertainty is the cost
    of one read.

    Args:
        clock: the system monotonic clock.
        max_wait_ns: maximum time spent waiting for the edge. If it runs out,
            the last read is used and the uncertainty grows to the wall-clock
            resolution.
        lsl_clock: ``pylsl.local_clock``, to also store the matching LSL instant.

    Returns:
        The anchor.
    """
    t_start = clock.now_ns()
    before = clock.now_ns()
    wall_prev = time.time_ns()
    last_before_with_old_value = before
    while True:
        before = clock.now_ns()
        wall = time.time_ns()
        after = clock.now_ns()
        if wall != wall_prev:
            # The edge happened after the previous read (which still returned
            # the old value) and before this one.
            mono = (last_before_with_old_value + after) // 2
            uncertainty = after - last_before_with_old_value
            break
        last_before_with_old_value = before
        if after - t_start > max_wait_ns:
            mono = (before + after) // 2
            uncertainty = max_wait_ns
            break
    lsl_s = lsl_clock() if lsl_clock is not None else None
    return ClockAnchor(mono_ns=mono, unix_ns=wall, uncertainty_ns=uncertainty, lsl_s=lsl_s)
