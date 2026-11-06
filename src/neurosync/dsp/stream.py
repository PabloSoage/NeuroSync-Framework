"""Derived stream worker performing real-time causal filtering (phase F5).

Connects an upstream SignalRing to a downstream derived SignalRing.
"""

from __future__ import annotations

import threading

from neurosync.core.clock import Clock
from neurosync.core.errors import InvalidInput, InvalidState, StopTimeout
from neurosync.core.model import QualityFlags, SampleChunk
from neurosync.core.ring import RingReader, SignalRing
from neurosync.dsp.filters import FilterPipeline


class FilteredStreamWorker:
    """Consumes chunks from an input ring, filters them causally, and writes to an output ring."""

    def __init__(
        self,
        input_ring: SignalRing,
        output_ring: SignalRing,
        pipeline: FilterPipeline,
        clock: Clock,
        *,
        poll_period_s: float = 0.005,
    ) -> None:
        if input_ring.info.n_channels != output_ring.info.n_channels:
            raise InvalidInput("Input and output rings must have matching channel counts")
        if pipeline.n_channels != input_ring.info.n_channels:
            raise InvalidInput("Pipeline channel count does not match input ring")

        self.input_ring = input_ring
        self.output_ring = output_ring
        self.pipeline = pipeline
        self.clock = clock
        self.poll_period_s = poll_period_s

        self.reader: RingReader = input_ring.reader()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._error: Exception | None = None
        self._samples_processed = 0

    @property
    def samples_processed(self) -> int:
        return self._samples_processed

    def step(self) -> int:
        """Process one batch of pending samples from the input reader."""
        sl = self.reader.read_new()
        if sl is None or sl.n == 0:
            return 0

        # Filter causally: updates internal filter state
        filtered_data = self.pipeline.process_chunk(sl.data)

        # Build downstream chunk with propagated timestamps and sequence info
        first_t_source = sl.t_source_ns if sl.t_source_ns is not None else None
        chunk = SampleChunk(
            stream_id=self.output_ring.info.stream_id,
            seq0=int(sl.seq[0]),
            data=filtered_data,
            t_host_ns=int(sl.t_host_ns[0]),
            t_source_ns=first_t_source,
            flags=QualityFlags(int(sl.flags[0])),
        )
        self.output_ring.write(chunk)
        self._samples_processed += sl.n
        return sl.n

    def drain_all(self) -> int:
        """Synchronously process all pending samples."""
        total = 0
        while True:
            n = self.step()
            total += n
            if n == 0:
                break
        return total

    def start(self) -> None:
        """Start worker thread."""
        if self._thread is not None:
            raise InvalidState("FilteredStreamWorker already started")
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"dsp-{self.output_ring.info.stream_id}",
        )
        self._thread.start()

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                self.step()
                self._stop.wait(self.poll_period_s)
        except Exception as exc:  # noqa: BLE001 - thread boundary: stored and exposed
            self._error = exc

    @property
    def error(self) -> Exception | None:
        return self._error

    def stop(self, timeout_s: float = 2.0) -> None:
        """Stop worker thread."""
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join(timeout_s)
        if self._thread.is_alive():
            raise StopTimeout("Worker thread did not stop", timeout_s=timeout_s)
        self._thread = None
        if self._error is not None:
            raise self._error
