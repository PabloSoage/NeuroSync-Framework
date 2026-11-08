"""Common interface of regular signal sources.

Every source (simulated, BrainFlow, LSL, board emulators) implements
:class:`SignalSource`:

- :meth:`SignalSource.start` creates **its own thread**, which reads from the
  device, stamps with the single clock and writes into the
  :class:`~neurosync.core.ring.SignalRing`. That thread does nothing else: no
  recording, no filtering, no serialization.
- :meth:`SignalSource.stop` waits for the thread for a bounded time and raises
  :class:`~neurosync.core.errors.StopTimeout` if it does not finish. Never
  ignored.
- :meth:`SignalSource.stats` returns counters that can always be read from
  another thread.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from neurosync.core.clock import Clock
from neurosync.core.model import StreamInfo
from neurosync.core.ring import SignalRing


@dataclass(slots=True)
class SourceStats:
    """Counters of a source. Only its own thread writes them."""

    chunks: int = 0
    samples: int = 0
    #: Samples lost according to the device counter.
    gaps: int = 0
    #: Samples duplicated according to the device counter (not written).
    duplicates: int = 0
    reconnects: int = 0
    last_t_host_ns: int | None = None
    #: Largest gap seen between two consecutive chunks, in ns.
    max_interchunk_ns: int = 0


class SignalSource(Protocol):
    """Regular signal source."""

    @property
    def info(self) -> StreamInfo:
        """Description of the stream it produces."""
        ...

    def start(self, ring: SignalRing, clock: Clock) -> None:
        """Start the reading thread. Fails if already started."""
        ...

    def stop(self, timeout_s: float = 2.0) -> None:
        """Stop the thread and release the device. Raises ``StopTimeout``."""
        ...

    def stats(self) -> SourceStats:
        """Copy of the current counters."""
        ...
