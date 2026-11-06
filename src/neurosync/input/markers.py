"""Experimental stimulation and task marker publisher (phase F6).

Used to stamp cognitive tasks, stimulus presentation onsets, and response triggers.
"""

from __future__ import annotations

from neurosync.core.bus import EventBus
from neurosync.core.clock import Clock
from neurosync.core.model import InputEvent, InputKind, InputSourceKind


class MarkerSource:
    """Publishes experimental markers to the EventBus."""

    def __init__(self, topic: str = "input_events") -> None:
        self.topic = topic

    def push(
        self,
        bus: EventBus[InputEvent],
        clock: Clock,
        marker_code: int,
        value: float = 1.0,
    ) -> InputEvent:
        """Publish a marker event."""
        ev = InputEvent(
            seq=0,
            t_host_ns=clock.now_ns(),
            source=InputSourceKind.MARKER,
            kind=InputKind.MARKER,
            code=int(marker_code),
            value=float(value),
        )
        bus.publish(self.topic, ev)
        return ev
