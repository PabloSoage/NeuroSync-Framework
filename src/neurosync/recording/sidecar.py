"""Session sidecar metadata (phase F4).

Stores non-streaming metadata alongside the primary ``.xdf`` recording:
- ClockInfo (system clock resolution, monotonicity, implementation)
- ClockAnchor (correspondence between monotonic clock and UTC)
- Stream descriptions (channels, nominal sampling rates, units)
- RecordingSummary (duration, sample counts, gaps, losses, flush lag)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from neurosync.core.anchors import ClockAnchor
from neurosync.core.clock import ClockInfo


@dataclass(frozen=True, slots=True)
class RecordingSummary:
    """Summary metrics of a completed recording session."""

    samples: dict[str, int]
    gaps: dict[str, int]
    losses: dict[str, int]
    event_count: int
    dropped_events: int
    duration_s: float
    max_flush_lag_ms: float

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecordingSummary:
        """Construct summary from dictionary."""
        return cls(
            samples=dict(data.get("samples", {})),
            gaps=dict(data.get("gaps", {})),
            losses=dict(data.get("losses", {})),
            event_count=int(data.get("event_count", 0)),
            dropped_events=int(data.get("dropped_events", 0)),
            duration_s=float(data.get("duration_s", 0.0)),
            max_flush_lag_ms=float(data.get("max_flush_lag_ms", 0.0)),
        )


@dataclass(frozen=True, slots=True)
class SessionSidecar:
    """Metadata sidecar saved alongside the recorded XDF file."""

    session_id: str
    created_at_mono_ns: int
    clock_info: ClockInfo
    initial_anchor: ClockAnchor | None = None
    streams: dict[str, Any] | None = None
    summary: RecordingSummary | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert sidecar to serializable dictionary."""
        anchor_dict = asdict(self.initial_anchor) if self.initial_anchor is not None else None
        return {
            "session_id": self.session_id,
            "created_at_mono_ns": self.created_at_mono_ns,
            "clock_info": asdict(self.clock_info),
            "initial_anchor": anchor_dict,
            "streams": self.streams or {},
            "summary": self.summary.to_dict() if self.summary is not None else None,
        }

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize sidecar as JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: Path | str) -> None:
        """Write sidecar to JSON file."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionSidecar:
        """Construct sidecar from dictionary."""
        ci_raw = data.get("clock_info", {})
        clock_info = ClockInfo(
            implementation=str(ci_raw.get("implementation", "unknown")),
            resolution_s=float(ci_raw.get("resolution_s", 0.0)),
            monotonic=bool(ci_raw.get("monotonic", True)),
            adjustable=bool(ci_raw.get("adjustable", False)),
        )
        anchor_raw = data.get("initial_anchor")
        initial_anchor = (
            ClockAnchor(
                mono_ns=int(anchor_raw["mono_ns"]),
                unix_ns=int(anchor_raw["unix_ns"]),
                uncertainty_ns=int(anchor_raw["uncertainty_ns"]),
                lsl_s=float(anchor_raw["lsl_s"]) if anchor_raw.get("lsl_s") is not None else None,
            )
            if anchor_raw is not None
            else None
        )
        summary_raw = data.get("summary")
        summary = RecordingSummary.from_dict(summary_raw) if summary_raw is not None else None

        return cls(
            session_id=str(data.get("session_id", "")),
            created_at_mono_ns=int(data.get("created_at_mono_ns", 0)),
            clock_info=clock_info,
            initial_anchor=initial_anchor,
            streams=data.get("streams", {}),
            summary=summary,
        )

    @classmethod
    def load(cls, path: Path | str) -> SessionSidecar:
        """Load sidecar from JSON file."""
        text = Path(path).read_text(encoding="utf-8")
        data: dict[str, Any] = json.loads(text)
        return cls.from_dict(data)
