"""Simulated input event source with reproducible scripting (phase F6).

Used in automated CI environments where no physical desktop session or keyboard is attached.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from neurosync.core.bus import EventBus
from neurosync.core.clock import Clock
from neurosync.core.model import InputEvent, InputKind, InputSourceKind


@dataclass(frozen=True, slots=True)
class ScriptedAction:
    """Pre-recorded or scripted input event to emit at offset."""

    time_offset_ns: int
    source: InputSourceKind
    kind: InputKind
    code: int
    value: float = 0.0
    device: int = 0


class SimulatedInputSource:
    """Deterministic publisher of input events."""

    def __init__(self, script: Sequence[ScriptedAction] | None = None) -> None:
        self.script = list(script or ())

    def emit(
        self,
        bus: EventBus[InputEvent],
        clock: Clock,
        source: InputSourceKind,
        kind: InputKind,
        code: int,
        value: float = 0.0,
        device: int = 0,
        topic: str = "input_events",
    ) -> InputEvent:
        """Publish a single simulated event timestamped with clock."""
        ev = InputEvent(
            seq=0,
            t_host_ns=clock.now_ns(),
            source=source,
            kind=kind,
            code=code,
            value=value,
            device=device,
        )
        bus.publish(topic, ev)
        return ev

    def play_script(
        self,
        bus: EventBus[InputEvent],
        clock: Clock,
        t0_ns: int | None = None,
        topic: str = "input_events",
    ) -> list[InputEvent]:
        """Emit all scripted actions in order."""
        base_t = t0_ns if t0_ns is not None else clock.now_ns()
        emitted: list[InputEvent] = []
        for action in self.script:
            ev = InputEvent(
                seq=0,
                t_host_ns=base_t + action.time_offset_ns,
                source=action.source,
                kind=action.kind,
                code=action.code,
                value=action.value,
                device=action.device,
            )
            bus.publish(topic, ev)
            emitted.append(ev)
        return emitted
