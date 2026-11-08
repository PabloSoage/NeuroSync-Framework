"""Data model: streams, channels, sample chunks and events.

Canonical names (do not change them without updating ``docs/decisions.md``):

- :class:`StreamInfo` describes a stream; :class:`ChannelInfo`, each channel.
- :class:`SampleChunk` is a block of samples from a regular source, as it
  arrives. It carries the source sample index (``seq0``), the host timestamp
  taken on reception (``t_host_ns``) and, if the source provides one, a
  per-sample source timestamp (``t_source_ns``).
- :class:`InputEvent` is an irregular event: key, button, axis, marker.

Key and button releases are events just like presses; the original code
dropped them, so press durations could not be measured.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, IntFlag, StrEnum
from typing import Any

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.floating[Any]]
Int64Array = npt.NDArray[np.int64]


class ChannelKind(StrEnum):
    """Channel type."""

    EEG = "eeg"
    EMG = "emg"
    ECG = "ecg"
    EOG = "eog"
    ACCEL = "accel"
    GYRO = "gyro"
    PPG = "ppg"
    EDA = "eda"
    TEMPERATURE = "temperature"
    BATTERY = "battery"
    AUX = "aux"
    MARKER = "marker"


class QualityFlags(IntFlag):
    """Per-sample or per-chunk quality flags. Combine with ``|``."""

    NONE = 0
    #: Samples are missing before this one (the source counter jumped).
    GAP = 1 << 0
    #: Repeated sample (the source counter went back or repeated).
    DUPLICATE = 1 << 1
    #: A reader fell behind and the ring overwrote samples it had not read.
    OVERRUN = 1 << 2
    #: The value sits at the converter limit (saturated electrode).
    RAILED = 1 << 3
    #: Flat channel (no variation).
    FLAT = 1 << 4
    #: The source disconnected and reconnected before this sample.
    RECONNECTED = 1 << 5


@dataclass(frozen=True, slots=True)
class ChannelInfo:
    """One channel of a stream."""

    name: str
    kind: ChannelKind
    unit: str = "uV"

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("a channel needs a name")


@dataclass(frozen=True, slots=True)
class StreamInfo:
    """Description of a regular signal stream or an event stream."""

    stream_id: str
    source: str
    channels: tuple[ChannelInfo, ...]
    #: Nominal rate in Hz; ``None`` for irregular streams.
    nominal_fs: float | None
    dtype: str = "float64"
    #: Free key-value pairs (e.g. ``("board", "SYNTHETIC_BOARD")``).
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.stream_id:
            raise ValueError("a stream needs a stream_id")
        if self.nominal_fs is not None and self.nominal_fs <= 0:
            raise ValueError("nominal_fs must be positive or None")
        if self.dtype not in ("float32", "float64"):
            raise ValueError("dtype must be float32 or float64")
        names = [c.name for c in self.channels]
        if len(set(names)) != len(names):
            raise ValueError("duplicate channel names")

    @property
    def n_channels(self) -> int:
        """Number of channels."""
        return len(self.channels)


@dataclass(frozen=True, slots=True, eq=False)  # eq on numpy arrays would be ambiguous
class SampleChunk:
    """Block of samples as it arrives from a regular source.

    ``data`` has shape ``(n_channels, n)``. ``seq0`` is the source index of the
    first sample, already unwrapped (see :mod:`neurosync.acquisition.counter`),
    so it only grows.
    """

    stream_id: str
    seq0: int
    data: FloatArray
    t_host_ns: int
    t_source_ns: Int64Array | None = None
    flags: QualityFlags = QualityFlags.NONE

    def __post_init__(self) -> None:
        if self.data.ndim != 2:
            raise ValueError("data must have shape (n_channels, n)")
        if self.seq0 < 0:
            raise ValueError("seq0 cannot be negative")
        if self.t_source_ns is not None and self.t_source_ns.shape != (self.n,):
            raise ValueError("t_source_ns needs one timestamp per sample")

    @property
    def n(self) -> int:
        """Number of samples."""
        return int(self.data.shape[1])

    @property
    def n_channels(self) -> int:
        """Number of channels."""
        return int(self.data.shape[0])


class InputSourceKind(IntEnum):
    """Where an input event comes from."""

    KEYBOARD = 1
    MOUSE = 2
    GAMEPAD = 3
    MARKER = 4
    SIMULATED = 5


class InputKind(IntEnum):
    """What kind of event it is."""

    KEY_DOWN = 1
    KEY_UP = 2
    BUTTON_DOWN = 3
    BUTTON_UP = 4
    MOVE = 5
    WHEEL = 6
    AXIS = 7
    MARKER = 8


@dataclass(frozen=True, slots=True)
class InputEvent:
    """Irregular event stamped with the single clock.

    ``seq`` is assigned by the bus in arrival order: it gives a total order
    across sources. ``t_source_ns`` is the source's own timestamp if it has one
    (e.g. Raw Input), in the source's clock.
    """

    seq: int
    t_host_ns: int
    source: InputSourceKind
    kind: InputKind
    code: int
    value: float = 0.0
    device: int = 0
    t_source_ns: int | None = None
    label: str = ""
