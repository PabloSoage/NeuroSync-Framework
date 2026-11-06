"""Gamepad and DualShock 4 controller event collector (phase F6).

Captures analog stick axes, triggers, and digital button presses/releases.
"""

from __future__ import annotations

import threading

from neurosync.core.bus import EventBus
from neurosync.core.clock import Clock
from neurosync.core.errors import InvalidState, StopTimeout
from neurosync.core.model import InputEvent, InputKind, InputSourceKind


class GamepadCollector:
    """Gamepad input collector publishing state changes to EventBus."""

    def __init__(
        self,
        *,
        device_index: int = 0,
        poll_period_s: float = 0.010,
        topic: str = "input_events",
    ) -> None:
        self.device_index = device_index
        self.poll_period_s = poll_period_s
        self.topic = topic

        self._bus: EventBus[InputEvent] | None = None
        self._clock: Clock | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._active = False
        self._error: Exception | None = None

        # State tracking to only emit changes
        self._button_states: dict[int, bool] = {}
        self._axis_values: dict[int, float] = {}

    @property
    def is_alive(self) -> bool:
        return self._active

    def emit_axis_change(self, axis_idx: int, value: float) -> None:
        """Record and publish an axis change event."""
        if self._bus is None or self._clock is None:
            return
        last_val = self._axis_values.get(axis_idx, 0.0)
        if abs(last_val - value) > 0.01:
            self._axis_values[axis_idx] = value
            ev = InputEvent(
                seq=0,
                t_host_ns=self._clock.now_ns(),
                source=InputSourceKind.GAMEPAD,
                kind=InputKind.AXIS,
                code=axis_idx,
                value=float(value),
                device=self.device_index,
            )
            self._bus.publish(self.topic, ev)

    def emit_button_change(self, button_idx: int, pressed: bool) -> None:
        """Record and publish a button state change event."""
        if self._bus is None or self._clock is None:
            return
        last_state = self._button_states.get(button_idx, False)
        if last_state != pressed:
            self._button_states[button_idx] = pressed
            kind = InputKind.BUTTON_DOWN if pressed else InputKind.BUTTON_UP
            ev = InputEvent(
                seq=0,
                t_host_ns=self._clock.now_ns(),
                source=InputSourceKind.GAMEPAD,
                kind=kind,
                code=button_idx,
                value=1.0 if pressed else 0.0,
                device=self.device_index,
            )
            self._bus.publish(self.topic, ev)

    def start(self, bus: EventBus[InputEvent], clock: Clock) -> None:
        """Start gamepad polling thread."""
        if self._active:
            raise InvalidState("GamepadCollector is already running")
        self._bus = bus
        self._clock = clock
        self._active = True
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"gamepad-{self.device_index}",
        )
        self._thread.start()

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                # Loop wait interval
                self._stop.wait(self.poll_period_s)
        except Exception as exc:  # noqa: BLE001 - thread boundary: stored and exposed
            self._error = exc

    def stop(self, timeout_s: float = 2.0) -> None:
        """Stop polling thread."""
        if not self._active:
            return
        self._active = False
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout_s)
            if self._thread.is_alive():
                raise StopTimeout("Gamepad thread failed to stop", timeout_s=timeout_s)
            self._thread = None
        if self._error is not None:
            raise self._error
