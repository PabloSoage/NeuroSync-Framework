"""Simulated source with ground truth and injectable faults.

This is the main test bench of v2 (see ``docs/decisions.md``, D-07). The
BrainFlow synthetic board is fixed at 250 Hz and 16 channels, produces a random
signal and cannot inject faults. This source can:

- **Deterministic.** The signal of sample ``k`` depends only on ``spec`` and
  ``k``, not on how delivery is chunked: :func:`render` returns the same data
  for ``[0, 1000)`` in one call or in ten.
- **Ground truth.** :func:`device_time_ns` gives the "device" instant of every
  sample (including drift), and pulses fall on known indices.
- **Faults:** lost packets (:class:`Drop`), duplicates (:class:`Duplicate`) and
  a short counter that wraps around. They go through the same
  :class:`~neurosync.acquisition.counter.CounterUnwrapper` the BrainFlow source
  will use, so they test it too.

For tests without threads or waiting: :meth:`SimulatedSource.emit_range`.
"""

from __future__ import annotations

import dataclasses
import math
import threading
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from neurosync.acquisition.counter import CounterUnwrapper, split_runs
from neurosync.acquisition.source import SourceStats
from neurosync.core.clock import Clock
from neurosync.core.errors import InvalidInput, InvalidState, StopTimeout
from neurosync.core.model import ChannelInfo, ChannelKind, QualityFlags, SampleChunk, StreamInfo
from neurosync.core.ring import SignalRing

#: Noise block size. Fixed: changing it changes the generated signal.
_NOISE_BLOCK = 1024


@dataclass(frozen=True, slots=True)
class Sine:
    """Sine ``amplitude * sin(2*pi*freq_hz*t + phase_rad)`` with ``t = k / fs``."""

    freq_hz: float
    amplitude: float = 10.0
    phase_rad: float = 0.0
    #: Channels it is added to; ``None`` = all.
    channels: tuple[int, ...] | None = None


@dataclass(frozen=True, slots=True)
class WhiteNoise:
    """Gaussian noise with standard deviation ``std``, deterministic by seed."""

    std: float = 1.0
    channels: tuple[int, ...] | None = None


@dataclass(frozen=True, slots=True)
class Pulse:
    """Square pulse ``width`` samples long starting at every index in ``at``."""

    at: tuple[int, ...]
    amplitude: float = 100.0
    width: int = 1
    channels: tuple[int, ...] | None = None


@dataclass(frozen=True, slots=True)
class Flat:
    """Flat channel: replaces everything before it on ``channel`` with ``value``."""

    channel: int
    value: float = 0.0


Signal = Sine | WhiteNoise | Pulse | Flat


@dataclass(frozen=True, slots=True)
class Drop:
    """``count`` packets are lost starting at device index ``at``."""

    at: int
    count: int = 1


@dataclass(frozen=True, slots=True)
class Duplicate:
    """Packet ``at`` is delivered ``count`` extra times, right after itself."""

    at: int
    count: int = 1


@dataclass(frozen=True, slots=True)
class SimSpec:
    """Full configuration of the simulated source."""

    fs: float = 250.0
    n_channels: int = 8
    seed: int = 0
    signals: tuple[Signal, ...] = (Sine(10.0),)
    #: Samples per delivered chunk (1 = one by one; 4 mimics the bursts of the
    #: BrainFlow synthetic board on Windows).
    chunk_size: int = 1
    #: The "device" clock runs ``drift_ppm`` parts per million fast.
    drift_ppm: float = 0.0
    counter_bits: int = 8
    drops: tuple[Drop, ...] = ()
    duplicates: tuple[Duplicate, ...] = ()
    stream_id: str = "sim"

    def validate(self) -> None:
        """Raise ``InvalidInput`` if anything makes no sense."""
        if self.fs <= 0:
            raise InvalidInput("fs must be positive", fs=self.fs)
        if self.n_channels <= 0:
            raise InvalidInput("n_channels must be positive")
        if self.chunk_size <= 0:
            raise InvalidInput("chunk_size must be positive")
        if not 1 <= self.counter_bits <= 62:
            raise InvalidInput("counter_bits must be between 1 and 62")
        if abs(self.drift_ppm) >= 1e6:
            raise InvalidInput("absurd drift_ppm")
        for sig in self.signals:
            chans: tuple[int, ...] | None
            chans = (sig.channel,) if isinstance(sig, Flat) else sig.channels
            if chans is not None and any(not 0 <= c < self.n_channels for c in chans):
                raise InvalidInput("channel out of range in a signal", signal=repr(sig))
            if isinstance(sig, Pulse) and sig.width <= 0:
                raise InvalidInput("pulse width must be positive")
        for d in self.drops:
            if d.at <= 0 or d.count <= 0:
                raise InvalidInput("Drop needs at > 0 and count > 0", at=d.at)
            if d.count >= (1 << self.counter_bits) // 2:
                raise InvalidInput(
                    "a Drop longer than half the counter modulus cannot be detected",
                    count=d.count,
                )
        for u in self.duplicates:
            if u.at < 0 or u.count <= 0:
                raise InvalidInput("Duplicate needs at >= 0 and count > 0", at=u.at)


def stream_info(spec: SimSpec) -> StreamInfo:
    """``StreamInfo`` of the stream produced by ``spec``."""
    channels = tuple(ChannelInfo(f"ch{i}", ChannelKind.EEG) for i in range(spec.n_channels))
    return StreamInfo(
        stream_id=spec.stream_id,
        source="simulated",
        channels=channels,
        nominal_fs=spec.fs,
        metadata=(("seed", str(spec.seed)), ("drift_ppm", str(spec.drift_ppm))),
    )


def device_time_ns(spec: SimSpec, seq: npt.ArrayLike) -> npt.NDArray[np.int64]:
    """True instant (ns since start) at which the device generates ``seq``.

    With positive drift the device runs fast: it produces ``fs * (1 + drift)``
    samples per real second.
    """
    k = np.asarray(seq, dtype=np.float64)
    true_fs = spec.fs * (1.0 + spec.drift_ppm * 1e-6)
    return np.rint(k / true_fs * 1e9).astype(np.int64)


def raw_counter(spec: SimSpec, seq: npt.ArrayLike) -> npt.NDArray[np.int64]:
    """Counter value the device would put in each packet (wrapping)."""
    return np.asarray(seq, dtype=np.int64) % (1 << spec.counter_bits)


def _noise(spec: SimSpec, seq0: int, n: int) -> npt.NDArray[np.float64]:
    out = np.empty((spec.n_channels, n), dtype=np.float64)
    first_block = seq0 // _NOISE_BLOCK
    last_block = (seq0 + n - 1) // _NOISE_BLOCK
    pos = 0
    for b in range(first_block, last_block + 1):
        rng = np.random.default_rng([spec.seed, b])
        block = rng.standard_normal((spec.n_channels, _NOISE_BLOCK))
        lo = max(seq0, b * _NOISE_BLOCK) - b * _NOISE_BLOCK
        hi = min(seq0 + n, (b + 1) * _NOISE_BLOCK) - b * _NOISE_BLOCK
        out[:, pos : pos + hi - lo] = block[:, lo:hi]
        pos += hi - lo
    return out


def render(spec: SimSpec, seq0: int, n: int) -> npt.NDArray[np.float64]:
    """Signal of samples ``[seq0, seq0 + n)``, shape ``(n_channels, n)``.

    Depends only on ``spec`` and the indices: this is the ground truth.
    """
    if seq0 < 0 or n < 0:
        raise ValueError("invalid range")
    data = np.zeros((spec.n_channels, n), dtype=np.float64)
    if n == 0:
        return data
    k = np.arange(seq0, seq0 + n, dtype=np.float64)
    t = k / spec.fs
    all_rows = np.arange(spec.n_channels)
    for sig in spec.signals:
        if isinstance(sig, Flat):
            data[sig.channel, :] = sig.value
            continue
        rows = all_rows if sig.channels is None else np.asarray(sig.channels)
        if isinstance(sig, Sine):
            data[rows, :] += sig.amplitude * np.sin(2.0 * math.pi * sig.freq_hz * t + sig.phase_rad)
        elif isinstance(sig, WhiteNoise):
            data[rows, :] += sig.std * _noise(spec, seq0, n)[rows, :]
        else:  # Pulse
            for start in sig.at:
                lo = max(start, seq0)
                hi = min(start + sig.width, seq0 + n)
                if lo < hi:
                    data[np.ix_(rows, np.arange(lo - seq0, hi - seq0))] += sig.amplitude
    return data


def delivered_packets(spec: SimSpec, seq0: int, seq1: int) -> npt.NDArray[np.int64]:
    """Device indices that reach the host, in order, for ``[seq0, seq1)``.

    Applies drops and duplicates. This is what "the wire" would carry.
    """
    dropped: set[int] = set()
    for d in spec.drops:
        dropped.update(range(d.at, d.at + d.count))
    dup = {u.at: u.count for u in spec.duplicates}
    out: list[int] = []
    for s in range(seq0, seq1):
        if s in dropped:
            continue
        out.append(s)
        out.extend([s] * dup.get(s, 0))
    return np.asarray(out, dtype=np.int64)


class SimulatedSource:
    """Simulated source implementing ``SignalSource``."""

    def __init__(self, spec: SimSpec) -> None:
        spec.validate()
        self.spec = spec
        self._info = stream_info(spec)
        self._stats = SourceStats()
        self._unwrapper = CounterUnwrapper(spec.counter_bits)
        self._next_seq = 0  # next device index to generate
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._error: Exception | None = None

    @property
    def info(self) -> StreamInfo:
        """Stream description."""
        return self._info

    def stats(self) -> SourceStats:
        """Copy of the counters."""
        return dataclasses.replace(self._stats)

    @property
    def error(self) -> Exception | None:
        """Exception that stopped the thread, if any."""
        return self._error

    # -------------------------------------------------------------- no threads

    def emit_range(self, ring: SignalRing, clock: Clock, seq1: int) -> None:
        """Generate and write up to device index ``seq1`` (exclusive).

        Synchronous and without waiting: for deterministic tests, usually with a
        :class:`~neurosync.core.clock.ManualClock`.
        """
        while self._next_seq < seq1:
            end = min(self._next_seq + self.spec.chunk_size, seq1)
            self._emit(ring, clock, self._next_seq, end)
            self._next_seq = end

    def _emit(self, ring: SignalRing, clock: Clock, seq0: int, seq1: int) -> None:
        packets = delivered_packets(self.spec, seq0, seq1)
        if packets.size == 0:
            return
        t_host = clock.now_ns()
        unwrap = self._unwrapper.update(raw_counter(self.spec, packets))
        st = self._stats
        if st.last_t_host_ns is not None:
            st.max_interchunk_ns = max(st.max_interchunk_ns, t_host - st.last_t_host_ns)
        st.last_t_host_ns = t_host
        st.duplicates += unwrap.duplicates
        st.gaps += unwrap.gaps
        keep = ~unwrap.duplicate
        dev = packets[keep]
        idx = unwrap.index[keep]
        gap_before = unwrap.gap_before[keep]
        # Contiguous index runs: a gap opens a new run flagged GAP.
        for start, stop in split_runs(idx):
            d0 = int(dev[start])
            n = stop - start
            flags = QualityFlags.GAP if gap_before[start] > 0 else QualityFlags.NONE
            chunk = SampleChunk(
                stream_id=self.spec.stream_id,
                seq0=int(idx[start]),
                data=render(self.spec, d0, n),
                t_host_ns=t_host,
                t_source_ns=device_time_ns(self.spec, np.arange(d0, d0 + n)),
                flags=flags,
            )
            ring.write(chunk)
            st.chunks += 1
            st.samples += n

    # -------------------------------------------------------------- threaded

    def start(self, ring: SignalRing, clock: Clock) -> None:
        """Start real-time delivery, paced by the device clock."""
        if self._thread is not None:
            raise InvalidState("the source is already started")
        if ring.info.stream_id != self._info.stream_id:
            raise InvalidInput("the ring belongs to another stream")
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, args=(ring, clock), name=f"source-{self.spec.stream_id}"
        )
        self._thread.start()

    def _run(self, ring: SignalRing, clock: Clock) -> None:
        spec = self.spec
        true_fs = spec.fs * (1.0 + spec.drift_ppm * 1e-6)
        t0 = clock.now_ns()
        period_s = spec.chunk_size / spec.fs
        try:
            while not self._stop.is_set():
                due = int((clock.now_ns() - t0) * 1e-9 * true_fs)
                while self._next_seq + spec.chunk_size <= due:
                    end = self._next_seq + spec.chunk_size
                    self._emit(ring, clock, self._next_seq, end)
                    self._next_seq = end
                self._stop.wait(period_s / 2)
        except Exception as exc:  # noqa: BLE001 - thread boundary: stored and exposed
            self._error = exc

    def stop(self, timeout_s: float = 2.0) -> None:
        """Stop the thread. Raises ``StopTimeout`` if it does not finish in time."""
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join(timeout_s)
        if self._thread.is_alive():
            raise StopTimeout("the simulated source did not stop", timeout_s=timeout_s)
        self._thread = None
