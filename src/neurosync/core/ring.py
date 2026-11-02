"""Single-producer, multiple-reader (SPMC) ring buffer for regular signals.

Replaces the original 30 s buffer, which was copied whole on every block and
made the producer wait for the GUI (``EEG-08``, ``CON-03`` in the analysis).

Rules:

- **Only one thread writes** (the source thread). It never waits for readers.
- Each reader has **its own cursor** (:class:`RingReader`) and reads at its own
  pace. If it falls behind by more than the capacity it loses the oldest
  samples and knows it: the result has ``lost > 0`` and ``QualityFlags.OVERRUN``.
- No locks on the read path: a *seqlock*-style protocol. The writer first
  publishes how far it is about to write (``_pending``), writes, then advances
  ``_head``. The reader copies and then checks ``_pending`` to see which part of
  its copy may have been overwritten; that part is discarded and counted as
  lost. This works because, under the GIL, assigning an ``int`` attribute is
  atomic.
- Besides the data, each sample stores: source index (``seq``), host timestamp
  of the block it arrived in (``t_host_ns``), source timestamp (``t_source_ns``,
  or ``NO_SOURCE_TS``) and ``QualityFlags``.

Indices: ``head`` counts samples written since the start (never reset). Sample
``i`` lives at position ``i % capacity``.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from neurosync.core.model import QualityFlags, SampleChunk, StreamInfo

#: ``t_source_ns`` value when the source has no timestamp of its own.
NO_SOURCE_TS = np.iinfo(np.int64).min


@dataclass(frozen=True, slots=True, eq=False)
class RingSlice:
    """Copy of a span of the ring. It belongs to the reader, who may modify it."""

    #: Ring index of the first copied sample.
    start: int
    data: npt.NDArray[np.floating[Any]]
    seq: npt.NDArray[np.int64]
    t_host_ns: npt.NDArray[np.int64]
    t_source_ns: npt.NDArray[np.int64]
    flags: npt.NDArray[np.uint16]
    #: Samples the reader asked for that had already been overwritten.
    lost: int

    @property
    def n(self) -> int:
        """Number of copied samples."""
        return int(self.data.shape[1])

    @property
    def end(self) -> int:
        """Ring index just past the last copied sample."""
        return self.start + self.n


class SignalRing:
    """Preallocated ring buffer for one regular stream."""

    def __init__(self, info: StreamInfo, capacity: int) -> None:
        """Create the ring.

        Args:
            info: stream description; fixes channels and ``dtype``.
            capacity: number of samples that fit. For a duration in seconds use
                :meth:`for_seconds`.
        """
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if info.n_channels <= 0:
            raise ValueError("the stream needs at least one channel")
        self.info = info
        self.capacity = capacity
        self._data = np.zeros((info.n_channels, capacity), dtype=info.dtype)
        self._seq = np.zeros(capacity, dtype=np.int64)
        self._t_host = np.zeros(capacity, dtype=np.int64)
        self._t_source = np.full(capacity, NO_SOURCE_TS, dtype=np.int64)
        self._flags = np.zeros(capacity, dtype=np.uint16)
        self._head = 0
        self._pending = 0
        self._cond = threading.Condition(threading.Lock())

    @classmethod
    def for_seconds(cls, info: StreamInfo, seconds: float) -> SignalRing:
        """Ring with room for ``seconds`` seconds at ``info.nominal_fs``."""
        if info.nominal_fs is None:
            raise ValueError("an irregular stream does not go in a SignalRing; use EventBus")
        return cls(info, max(1, int(np.ceil(seconds * info.nominal_fs))))

    # ------------------------------------------------------------------ writer

    def write(self, chunk: SampleChunk) -> None:
        """Append a chunk. Only the source thread calls this.

        Raises:
            ValueError: if the chunk does not match the stream or does not fit.
        """
        if chunk.stream_id != self.info.stream_id:
            raise ValueError(
                f"chunk of {chunk.stream_id!r} written to ring of {self.info.stream_id!r}"
            )
        if chunk.n_channels != self.info.n_channels:
            raise ValueError("channel count differs from the stream")
        n = chunk.n
        if n == 0:
            return
        if n > self.capacity:
            raise ValueError("the chunk is larger than the ring")
        head = self._head
        self._pending = head + n
        seq = np.arange(chunk.seq0, chunk.seq0 + n, dtype=np.int64)
        t_source = chunk.t_source_ns
        flags = np.zeros(n, dtype=np.uint16)
        if chunk.flags:
            # Chunk flags (GAP, RECONNECTED...) go on its first sample;
            # DUPLICATE and OVERRUN apply to all of them.
            flags[0] = int(chunk.flags)
            whole = chunk.flags & (QualityFlags.DUPLICATE | QualityFlags.OVERRUN)
            if whole:
                flags |= int(whole)
        i = head % self.capacity
        first = min(n, self.capacity - i)
        self._put(i, 0, first, chunk, seq, t_source, flags)
        if first < n:
            self._put(0, first, n, chunk, seq, t_source, flags)
        self._head = head + n
        with self._cond:
            self._cond.notify_all()

    def _put(
        self,
        pos: int,
        a: int,
        b: int,
        chunk: SampleChunk,
        seq: npt.NDArray[np.int64],
        t_source: npt.NDArray[np.int64] | None,
        flags: npt.NDArray[np.uint16],
    ) -> None:
        m = b - a
        self._data[:, pos : pos + m] = chunk.data[:, a:b]
        self._seq[pos : pos + m] = seq[a:b]
        self._t_host[pos : pos + m] = chunk.t_host_ns
        if t_source is None:
            self._t_source[pos : pos + m] = NO_SOURCE_TS
        else:
            self._t_source[pos : pos + m] = t_source[a:b]
        self._flags[pos : pos + m] = flags[a:b]

    # ------------------------------------------------------------------ readers

    @property
    def head(self) -> int:
        """Samples written since the start."""
        return self._head

    def reader(self, *, from_start: bool = False) -> RingReader:
        """Create a reader with its own cursor.

        Args:
            from_start: if ``True``, start at the oldest sample still in the
                ring; otherwise at the next sample to be written.
        """
        start = max(0, self._head - self.capacity) if from_start else self._head
        return RingReader(self, start)

    def copy_range(self, start: int, end: int) -> RingSlice:
        """Copy samples ``[start, end)`` that are still in the ring.

        Anything already overwritten is not copied and is counted in ``lost``.
        """
        if start < 0 or end < start:
            raise ValueError("invalid range")
        end = min(end, self._head)
        lost = 0
        oldest = max(0, self._head - self.capacity)
        if start < oldest:
            lost += min(oldest, end) - start
            start = min(oldest, end)
        data, seq, t_host, t_source, flags = self._copy(start, end)
        # Seqlock: what the writer may have overwritten while we were copying.
        valid_from = self._pending - self.capacity
        if start < valid_from:
            drop = min(valid_from, end) - start
            lost += drop
            start += drop
            data, seq, t_host, t_source, flags = (
                data[:, drop:],
                seq[drop:],
                t_host[drop:],
                t_source[drop:],
                flags[drop:],
            )
        if lost and flags.size:
            flags[0] |= int(QualityFlags.OVERRUN)
        return RingSlice(start, data, seq, t_host, t_source, flags, lost)

    def _copy(
        self, start: int, end: int
    ) -> tuple[
        npt.NDArray[np.floating[Any]],
        npt.NDArray[np.int64],
        npt.NDArray[np.int64],
        npt.NDArray[np.int64],
        npt.NDArray[np.uint16],
    ]:
        n = end - start
        if n <= 0:
            return (
                np.empty((self.info.n_channels, 0), dtype=self._data.dtype),
                np.empty(0, dtype=np.int64),
                np.empty(0, dtype=np.int64),
                np.empty(0, dtype=np.int64),
                np.empty(0, dtype=np.uint16),
            )
        i = start % self.capacity
        if i + n <= self.capacity:
            return (
                self._data[:, i : i + n].copy(),
                self._seq[i : i + n].copy(),
                self._t_host[i : i + n].copy(),
                self._t_source[i : i + n].copy(),
                self._flags[i : i + n].copy(),
            )
        # The span wraps around: fancy indexing already returns copies.
        idx = (np.arange(n) + i) % self.capacity
        return (
            self._data[:, idx],
            self._seq[idx],
            self._t_host[idx],
            self._t_source[idx],
            self._flags[idx],
        )

    def wait_beyond(self, index: int, timeout_s: float) -> bool:
        """Wait until ``head`` exceeds ``index``. Returns whether it did."""
        with self._cond:
            return self._cond.wait_for(lambda: self._head > index, timeout=timeout_s)


class RingReader:
    """A reader's cursor over a :class:`SignalRing`."""

    def __init__(self, ring: SignalRing, start: int) -> None:
        self._ring = ring
        self.cursor = start
        #: Samples this reader has lost since it was created.
        self.lost_total = 0

    def read_new(self, max_n: int | None = None) -> RingSlice | None:
        """Read what was written since the last read (at most ``max_n``).

        Returns ``None`` if there is nothing new. If the reader fell behind, the
        result starts at the oldest available sample and ``lost`` says how many
        were lost.
        """
        head = self._ring.head
        if head <= self.cursor:
            return None
        end = head if max_n is None else min(head, self.cursor + max_n)
        sl = self._ring.copy_range(self.cursor, end)
        self.lost_total += sl.lost
        self.cursor = sl.end if sl.n else end
        return sl

    def read_last(self, n: int) -> RingSlice:
        """Copy the last ``n`` samples (for plotting). Does not move the cursor."""
        if n <= 0:
            raise ValueError("n must be positive")
        head = self._ring.head
        return self._ring.copy_range(max(0, head - n), head)

    def wait(self, timeout_s: float) -> bool:
        """Wait until there is something new for this reader."""
        return self._ring.wait_beyond(self.cursor, timeout_s)
