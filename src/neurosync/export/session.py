"""In-memory representation of a loaded XDF recording session (phase F7).

Represents signals, input/marker events, and clock anchors parsed from an .xdf file
and its optional .sidecar.json file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from neurosync.core.anchors import ClockAnchor
from neurosync.core.model import InputEvent
from neurosync.recording.sidecar import SessionSidecar


@dataclass(frozen=True, slots=True)
class ExportSignalStream:
    """A continuous multi-channel signal stream extracted from XDF."""

    name: str
    stream_type: str
    nominal_srate: float
    channel_names: list[str]
    channel_units: list[str]
    timestamps_s: np.ndarray  # float64 1D array of seconds
    data: np.ndarray  # float64 2D array of shape [n_samples, n_channels]

    @property
    def sample_count(self) -> int:
        return len(self.timestamps_s)

    @property
    def channel_count(self) -> int:
        return len(self.channel_names)

    @property
    def duration_s(self) -> float:
        if len(self.timestamps_s) < 2:
            return 0.0
        return float(self.timestamps_s[-1] - self.timestamps_s[0])


@dataclass(frozen=True, slots=True)
class ParsedSession:
    """Full recording session loaded from XDF and optional sidecar."""

    session_id: str
    signals: list[ExportSignalStream] = field(default_factory=list)
    events: list[InputEvent] = field(default_factory=list)
    anchors: list[ClockAnchor] = field(default_factory=list)
    sidecar: SessionSidecar | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_signal(self, name: str | None = None) -> ExportSignalStream | None:
        """Find a signal stream by name, or return the first signal stream if name is None."""
        if not self.signals:
            return None
        if name is None:
            return self.signals[0]
        for s in self.signals:
            if s.name.lower() == name.lower():
                return s
        return None
