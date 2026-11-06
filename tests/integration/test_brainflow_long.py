"""Integration test for long-running BrainFlow acquisition (phase F3).

Guarantees no stall after 30 minutes (historical bug EEG-01).
Only runs with: pytest -m slow.
"""

from __future__ import annotations

import time

import pytest
from brainflow.board_shim import BoardIds, BoardShim

from neurosync.acquisition.brainflow_source import BrainFlowSource
from neurosync.core.clock import PerfCounterClock
from neurosync.core.ring import SignalRing


@pytest.mark.slow
def test_brainflow_synthetic_two_hours() -> None:
    BoardShim.disable_board_logger()
    source = BrainFlowSource(BoardIds.SYNTHETIC_BOARD.value)
    clock = PerfCounterClock()
    # 30 seconds capacity is enough since we continuously poll and verify
    ring = SignalRing(source.info, capacity=250 * 30)

    source.start(ring, clock)
    t0 = time.monotonic()
    last_head = 0

    try:
        # Run for 2 hours (7200 seconds)
        while time.monotonic() - t0 < 7200.0:
            time.sleep(10.0)
            assert source.error is None
            stats = source.stats()
            assert stats.gaps == 0
            assert stats.duplicates == 0
            # Ensure head is monotonically advancing
            assert ring.head > last_head
            last_head = ring.head
    finally:
        source.stop()
