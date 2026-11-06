"""Recording engine for regular signals, events and clock anchors (phase F4).

Coordinates:
- Ingestion from SPMC ``SignalRing``s via dedicated non-blocking ``RingReader``s
- Event bus drain with ``Policy.BLOCK`` to avoid losing stimulus / input markers
- In-process appending to binary XDF via ``XdfWriter``
- Periodic fsync + boundary commits for crash resilience
- Production of metadata sidecar JSON and RecordingSummary
"""

from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from neurosync.core.anchors import ClockAnchor
from neurosync.core.bus import EventBus, Policy, Subscription
from neurosync.core.clock import Clock, ClockInfo, perf_counter_info
from neurosync.core.errors import InvalidInput, InvalidState, StopTimeout
from neurosync.core.model import ChannelInfo, ChannelKind, InputEvent, QualityFlags
from neurosync.core.ring import RingReader, SignalRing
from neurosync.recording.sidecar import RecordingSummary, SessionSidecar
from neurosync.recording.xdf_writer import XdfWriter


@dataclass(slots=True)
class _StreamContext:
    stream_id: str
    primary_id: int
    aux_id: int
    reader: RingReader
    total_samples: int = 0
    total_gaps: int = 0
    total_lost: int = 0
    first_ts: float | None = None
    last_ts: float | None = None


class Recorder:
    """Non-daemon multi-stream recorder writing append-only XDF."""

    def __init__(
        self,
        path: Path | str,
        clock: Clock,
        rings: Sequence[SignalRing] | Mapping[str, SignalRing],
        *,
        bus: EventBus[InputEvent] | None = None,
        events_subscription: Subscription[InputEvent] | None = None,
        batch_interval_s: float = 0.050,
        fsync_interval_s: float = 0.500,
        initial_anchor: ClockAnchor | None = None,
        clock_info: ClockInfo | None = None,
        session_id: str = "session",
    ) -> None:
        """Create recorder for rings and optional event bus.

        Args:
            path: Target file path for the .xdf recording.
            clock: Monotonic clock protocol.
            rings: Rings to record from.
            bus: Optional EventBus to subscribe to for InputEvents.
            events_subscription: Optional pre-existing subscription.
            batch_interval_s: Sleep between flush iterations (default 50 ms).
            fsync_interval_s: Target interval between OS fsyncs (default 0.5 s).
            initial_anchor: Monotonic <-> UTC anchor at start.
            clock_info: System clock info stored in sidecar.
            session_id: Recording identifier for sidecar metadata.
        """
        self.path = Path(path)
        self.clock = clock
        self.batch_interval_s = batch_interval_s
        self.fsync_interval_s = fsync_interval_s
        self.initial_anchor = initial_anchor
        self.session_id = session_id
        self.clock_info = clock_info or perf_counter_info()

        # Ring setup
        ring_list: list[SignalRing] = (
            list(rings.values()) if isinstance(rings, Mapping) else list(rings)
        )
        if not ring_list:
            raise InvalidInput("Recorder requires at least one SignalRing")

        self._streams: dict[str, _StreamContext] = {}
        curr_id = 1
        for ring in ring_list:
            sid = ring.info.stream_id
            if sid in self._streams:
                raise InvalidInput(f"Duplicate stream_id in rings: {sid}")
            self._streams[sid] = _StreamContext(
                stream_id=sid,
                primary_id=curr_id,
                aux_id=curr_id + 1,
                reader=ring.reader(),
            )
            curr_id += 2

        # Anchors and events setup
        self._anchors_id = 900
        self._events_id = 901
        self._bus_sub: Subscription[InputEvent] | None = None
        if events_subscription is not None:
            self._bus_sub = events_subscription
        elif bus is not None:
            # Policy.BLOCK to ensure no dropped user inputs/markers (D-04)
            self._bus_sub = bus.subscribe(
                topic="input_events",
                name="recorder",
                maxsize=10_000,
                policy=Policy.BLOCK,
            )

        self._total_events = 0
        self._first_event_ts: float | None = None
        self._last_event_ts: float | None = None
        self._start_mono_ns = self.clock.now_ns()
        self._last_fsync_ns = self._start_mono_ns
        self._max_flush_lag_ms = 0.0

        # Writer initialization
        self._writer = XdfWriter(self.path)
        self._init_xdf_headers(ring_list)

        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._closed = False
        self._error: Exception | None = None

    def _init_xdf_headers(self, rings: list[SignalRing]) -> None:
        """Write stream headers for all registered signals, aux, anchors and events."""
        now_s = self._start_mono_ns * 1e-9

        # Register signal rings and auxiliary streams
        for ring in rings:
            info = ring.info
            ctx = self._streams[info.stream_id]

            # Primary signal stream
            kind_str = info.channels[0].kind.value.upper() if info.channels else "EEG"
            fs = info.nominal_fs if info.nominal_fs is not None else 0.0
            self._writer.write_stream_header(
                stream_id=ctx.primary_id,
                name=info.stream_id,
                type=kind_str,
                channel_count=info.n_channels,
                nominal_srate=fs,
                channel_format=info.dtype,
                channels=info.channels,
                metadata=info.metadata,
            )
            self._writer.write_clock_offset(ctx.primary_id, now_s, 0.0)

            # Auxiliary metadata stream (seq and t_source_ns as per D-03)
            aux_channels = (
                ChannelInfo(name="seq", kind=ChannelKind.AUX, unit="count"),
                ChannelInfo(name="t_source_ns", kind=ChannelKind.AUX, unit="ns"),
            )
            self._writer.write_stream_header(
                stream_id=ctx.aux_id,
                name=f"{info.stream_id}_aux",
                type="AUX",
                channel_count=2,
                nominal_srate=fs,
                channel_format="double64",
                channels=aux_channels,
            )
            self._writer.write_clock_offset(ctx.aux_id, now_s, 0.0)

        # Clock anchors stream
        anchor_channels = (
            ChannelInfo(name="mono_ns", kind=ChannelKind.AUX, unit="ns"),
            ChannelInfo(name="unix_ns", kind=ChannelKind.AUX, unit="ns"),
            ChannelInfo(name="uncertainty_ns", kind=ChannelKind.AUX, unit="ns"),
        )
        self._writer.write_stream_header(
            stream_id=self._anchors_id,
            name="clock_anchors",
            type="ANCHOR",
            channel_count=3,
            nominal_srate=0.0,
            channel_format="double64",
            channels=anchor_channels,
        )
        self._writer.write_clock_offset(self._anchors_id, now_s, 0.0)

        if self.initial_anchor is not None:
            self.record_anchor(self.initial_anchor)

        # Events stream if subscription is active
        if self._bus_sub is not None:
            event_channels = (
                ChannelInfo(name="seq", kind=ChannelKind.MARKER, unit="count"),
                ChannelInfo(name="source", kind=ChannelKind.MARKER, unit="enum"),
                ChannelInfo(name="kind", kind=ChannelKind.MARKER, unit="enum"),
                ChannelInfo(name="code", kind=ChannelKind.MARKER, unit="code"),
                ChannelInfo(name="value", kind=ChannelKind.MARKER, unit="value"),
                ChannelInfo(name="device", kind=ChannelKind.MARKER, unit="id"),
            )
            self._writer.write_stream_header(
                stream_id=self._events_id,
                name="events",
                type="EVENTS",
                channel_count=6,
                nominal_srate=0.0,
                channel_format="double64",
                channels=event_channels,
            )
            self._writer.write_clock_offset(self._events_id, now_s, 0.0)

        self._writer.flush()

    def record_anchor(self, anchor: ClockAnchor) -> None:
        """Record a clock anchor into the anchor stream."""
        ts_s = np.array([anchor.mono_ns * 1e-9], dtype=np.float64)
        data = np.array(
            [[anchor.mono_ns], [anchor.unix_ns], [anchor.uncertainty_ns]],
            dtype=np.float64,
        )
        self._writer.write_samples_numeric(self._anchors_id, ts_s, data)

    def _record_signals(self) -> int:
        """Poll each reader and append new samples to XDF."""
        samples_recorded = 0
        for ctx in self._streams.values():
            sl = ctx.reader.read_new()
            if sl is None or sl.n == 0:
                continue

            samples_recorded += sl.n
            ctx.total_samples += sl.n
            ctx.total_lost += sl.lost
            ctx.total_gaps += int(np.count_nonzero(sl.flags & QualityFlags.GAP))

            ts_s = sl.t_host_ns.astype(np.float64) * 1e-9
            if ctx.first_ts is None:
                ctx.first_ts = float(ts_s[0])
            ctx.last_ts = float(ts_s[-1])

            # Write primary stream
            self._writer.write_samples_numeric(ctx.primary_id, ts_s, sl.data)

            # Write aux stream
            aux_data = np.stack(
                [sl.seq.astype(np.float64), sl.t_source_ns.astype(np.float64)],
                axis=0,
            )
            self._writer.write_samples_numeric(ctx.aux_id, ts_s, aux_data)

        return samples_recorded

    def _record_events(self) -> int:
        """Drain events from subscription and write to events stream."""
        if self._bus_sub is None:
            return 0
        envelopes = self._bus_sub.drain()
        if not envelopes:
            return 0

        n = len(envelopes)
        self._total_events += n

        ts_list: list[float] = []
        rows: list[list[float]] = []

        for env in envelopes:
            ev = env.msg
            ts = ev.t_host_ns * 1e-9
            ts_list.append(ts)
            rows.append(
                [
                    float(ev.seq),
                    float(ev.source),
                    float(ev.kind),
                    float(ev.code),
                    float(ev.value),
                    float(ev.device),
                ]
            )

        ts_arr = np.asarray(ts_list, dtype=np.float64)
        if self._first_event_ts is None:
            self._first_event_ts = float(ts_arr[0])
        self._last_event_ts = float(ts_arr[-1])

        data = np.asarray(rows, dtype=np.float64).T
        self._writer.write_samples_numeric(self._events_id, ts_arr, data)
        return n

    def step(self) -> int:
        """Perform one batch recording step and commit fsync if due."""
        n_samples = self._record_signals()
        self._record_events()

        now_ns = self.clock.now_ns()
        if (now_ns - self._last_fsync_ns) * 1e-9 >= self.fsync_interval_s:
            self._commit_sync(now_ns)

        return n_samples

    def record_all(self) -> int:
        """Synchronously drain all pending samples and events until clean."""
        total = 0
        while True:
            n = self.step()
            total += n
            if n == 0:
                break
        self._commit_sync(self.clock.now_ns())
        return total

    def _commit_sync(self, now_ns: int) -> None:
        """Write boundary chunk, flush and fsync, updating lag stats."""
        self._writer.write_boundary()
        t0 = self.clock.now_ns()
        self._writer.flush()
        self._writer.fsync()
        lag_ms = (self.clock.now_ns() - t0) * 1e-6
        if lag_ms > self._max_flush_lag_ms:
            self._max_flush_lag_ms = lag_ms
        self._last_fsync_ns = now_ns

    def start(self) -> None:
        """Start recording thread. Raises InvalidState if already running."""
        if self._thread is not None:
            raise InvalidState("Recorder is already started")
        if self._closed:
            raise InvalidState("Recorder is closed")

        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="recorder")
        self._thread.start()

    def _run(self) -> None:
        """Thread loop executing batch recording every batch_interval_s."""
        try:
            while not self._stop.is_set():
                self.step()
                self._stop.wait(self.batch_interval_s)
        except Exception as exc:  # noqa: BLE001 - thread boundary: stored and exposed
            self._error = exc

    @property
    def error(self) -> Exception | None:
        """Exception that stopped the thread, if any."""
        return self._error

    def stop(self, timeout_s: float = 2.0) -> RecordingSummary:
        """Stop recorder thread, finalize XDF and sidecar, return summary."""
        if self._closed:
            raise InvalidState("Recorder already stopped")

        if self._thread is not None:
            self._stop.set()
            self._thread.join(timeout_s)
            if self._thread.is_alive():
                raise StopTimeout("Recorder thread did not stop in time", timeout_s=timeout_s)
            self._thread = None

        if self._error is not None:
            raise self._error

        # Final drain of all remaining data
        self.record_all()
        now_s = self.clock.now_ns() * 1e-9

        # Finalize streams with clock offsets and footers
        for ctx in self._streams.values():
            self._writer.write_clock_offset(ctx.primary_id, now_s, 0.0)
            self._writer.write_clock_offset(ctx.aux_id, now_s, 0.0)

            stats = {
                "gaps": ctx.total_gaps,
                "lost": ctx.total_lost,
                "samples": ctx.total_samples,
            }
            self._writer.write_stream_footer(
                stream_id=ctx.primary_id,
                first_timestamp=ctx.first_ts,
                last_timestamp=ctx.last_ts,
                sample_count=ctx.total_samples,
                stats=stats,
            )
            self._writer.write_stream_footer(
                stream_id=ctx.aux_id,
                first_timestamp=ctx.first_ts,
                last_timestamp=ctx.last_ts,
                sample_count=ctx.total_samples,
            )

        self._writer.write_clock_offset(self._anchors_id, now_s, 0.0)
        self._writer.write_stream_footer(self._anchors_id)

        if self._bus_sub is not None:
            self._writer.write_clock_offset(self._events_id, now_s, 0.0)
            self._writer.write_stream_footer(
                stream_id=self._events_id,
                first_timestamp=self._first_event_ts,
                last_timestamp=self._last_event_ts,
                sample_count=self._total_events,
            )

        self._writer.flush()
        self._writer.fsync()
        self._writer.close()
        self._closed = True

        duration_s = (self.clock.now_ns() - self._start_mono_ns) * 1e-9
        sub_dropped = self._bus_sub.stats.dropped if self._bus_sub is not None else 0

        summary = RecordingSummary(
            samples={s.stream_id: s.total_samples for s in self._streams.values()},
            gaps={s.stream_id: s.total_gaps for s in self._streams.values()},
            losses={s.stream_id: s.total_lost for s in self._streams.values()},
            event_count=self._total_events,
            dropped_events=sub_dropped,
            duration_s=duration_s,
            max_flush_lag_ms=self._max_flush_lag_ms,
        )

        # Write sidecar JSON file alongside .xdf
        sidecar_path = self.path.with_suffix(".json")
        stream_meta = {
            ctx.stream_id: {
                "samples": ctx.total_samples,
                "gaps": ctx.total_gaps,
                "lost": ctx.total_lost,
            }
            for ctx in self._streams.values()
        }
        sidecar = SessionSidecar(
            session_id=self.session_id,
            created_at_mono_ns=self._start_mono_ns,
            clock_info=self.clock_info,
            initial_anchor=self.initial_anchor,
            streams=stream_meta,
            summary=summary,
        )
        sidecar.save(sidecar_path)

        return summary
