"""Base protocol and types for user input and behavioral event collectors (phase F6).

Captures:
- Keyboard events (presses and releases)
- Mouse movements, clicks, and scroll wheel events
- Gamepad / joystick inputs (axes, buttons, triggers)
- Experimental stimulation and synchronization markers
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from neurosync.core.bus import EventBus
from neurosync.core.clock import Clock
from neurosync.core.model import InputEvent


@runtime_checkable
class InputCollector(Protocol):
    """Protocol implemented by all input event collectors."""

    def start(self, bus: EventBus[InputEvent], clock: Clock) -> None:
        """Start collecting events and publishing to the event bus."""
        ...

    def stop(self, timeout_s: float = 2.0) -> None:
        """Stop collecting and release hardware/system hooks."""
        ...

    @property
    def is_alive(self) -> bool:
        """Whether the collector is actively listening."""
        ...
