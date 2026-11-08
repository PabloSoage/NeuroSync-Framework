"""Unwrapping of a device packet counter.

Almost every board numbers its packets with a short counter that wraps around:
8 bits on the BrainFlow synthetic board and on the Cyton, 16 on the Enophone.
Detecting gaps and duplicates needs an index that only grows.

Decision rule for a ``bits``-bit counter (modulus ``M = 2**bits``), with
``d = (raw - last) mod M``:

- ``d == 1``: the next packet, nothing to report.
- ``1 < d <= M // 2``: ``d - 1`` packets are missing (gap).
- ``d == 0`` or ``d > M // 2``: repeated or late packet (duplicate); the index
  does not advance.

A gap longer than ``M // 2`` packets looks like a duplicate. That is
unavoidable with short counters: with 8 bits at 250 Hz it is 0.5 s. That is why
sources also watch the time between chunks and flag ``RECONNECTED`` when no data
arrived for longer than that.

Both the simulated source and the BrainFlow source (phase F3) must use
:class:`CounterUnwrapper` and :func:`split_runs`; do not reimplement them.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True, slots=True, eq=False)
class UnwrapResult:
    """Result of unwrapping one block of counter values."""

    #: Unwrapped index per packet; ``-1`` for duplicates.
    index: npt.NDArray[np.int64]
    #: Packets lost right before each packet (0 if none).
    gap_before: npt.NDArray[np.int64]
    #: ``True`` for duplicated or out-of-order packets.
    duplicate: npt.NDArray[np.bool_]

    @property
    def gaps(self) -> int:
        """Packets lost in the block."""
        return int(self.gap_before.sum())

    @property
    def duplicates(self) -> int:
        """Duplicated packets in the block."""
        return int(self.duplicate.sum())


class CounterUnwrapper:
    """Turns a ``bits``-bit counter into a growing index."""

    def __init__(self, bits: int) -> None:
        if not 1 <= bits <= 62:
            raise ValueError("bits must be between 1 and 62")
        self.bits = bits
        self.modulus = 1 << bits
        self._last_raw: int | None = None
        self._last_index = -1

    @property
    def last_index(self) -> int:
        """Last assigned index (``-1`` if none yet)."""
        return self._last_index

    def update(self, raw: npt.ArrayLike) -> UnwrapResult:
        """Process the counter values of one block, in arrival order."""
        values = np.asarray(raw).astype(np.int64, copy=False).ravel()
        if values.size and (values.min() < 0 or values.max() >= self.modulus):
            raise ValueError(f"counter value out of range for {self.bits} bits")
        n = values.size
        index = np.full(n, -1, dtype=np.int64)
        gap_before = np.zeros(n, dtype=np.int64)
        duplicate = np.zeros(n, dtype=np.bool_)
        half = self.modulus // 2
        for k in range(n):  # blocks of tens of packets: the loop is cheap
            r = int(values[k])
            if self._last_raw is None:
                self._last_index = 0
                self._last_raw = r
                index[k] = 0
                continue
            d = (r - self._last_raw) % self.modulus
            if d == 0 or d > half:
                duplicate[k] = True
                continue
            gap_before[k] = d - 1
            self._last_index += d
            self._last_raw = r
            index[k] = self._last_index
        return UnwrapResult(index, gap_before, duplicate)


def split_runs(index: npt.NDArray[np.int64]) -> list[tuple[int, int]]:
    """Split a non-decreasing index (duplicates already removed) into runs.

    Returns ``[(start, stop), ...]`` positions such that ``index[start:stop]``
    is contiguous (step 1). A new run starts after every gap.
    """
    if index.size == 0:
        return []
    breaks = (np.flatnonzero(np.diff(index) != 1) + 1).tolist()
    bounds = [0, *breaks, int(index.size)]
    return [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]
