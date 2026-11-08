"""Keyboard and mouse event collector using pynput (phase F6).

Captures both key down and key up events (fixing the thesis bug where releases were dropped),
mouse movements, mouse clicks, and scroll wheel actions.
"""

from __future__ import annotations

import threading
from typing import Any

from pynput import keyboard, mouse

from neurosync.core.bus import EventBus
from neurosync.core.clock import Clock
from neurosync.core.errors import InvalidState, StopTimeout
from neurosync.core.model import InputEvent, InputKind, InputSourceKind


def _key_to_code(key: Any) -> tuple[int, float]:
    """Convert a pynput key object into integer code and float value."""
    if hasattr(key, "vk") and key.vk is not None:
        return int(key.vk), 1.0
    if hasattr(key, "char") and key.char is not None:
        return ord(key.char), 1.0
    if hasattr(key, "value") and hasattr(key.value, "vk"):
        return int(key.value.vk), 1.0
    return hash(str(key)) % 65535, 1.0


def _button_to_code(button: Any) -> int:
    """Convert pynput mouse button to integer identifier (1=left, 2=right, 3=middle)."""
    if button == mouse.Button.left:
        return 1
    if button == mouse.Button.right:
        return 2
    if button == mouse.Button.middle:
        return 3
    return 4


class KeyboardMouseCollector:
    """Collects real-time keyboard and mouse events and pushes to EventBus."""

    def __init__(
        self,
        *,
        capture_keyboard: bool = True,
        capture_mouse: bool = True,
        topic: str = "input_events",
    ) -> None:
        self.capture_keyboard = capture_keyboard
        self.capture_mouse = capture_mouse
        self.topic = topic

        self._bus: EventBus[InputEvent] | None = None
        self._clock: Clock | None = None
        self._kb_listener: keyboard.Listener | None = None
        self._mouse_listener: mouse.Listener | None = None
        self._active = False
        self._lock = threading.Lock()

    @property
    def is_alive(self) -> bool:
        with self._lock:
            return self._active

    def start(self, bus: EventBus[InputEvent], clock: Clock) -> None:
        """Start listening for keyboard and mouse events."""
        with self._lock:
            if self._active:
                raise InvalidState("KeyboardMouseCollector is already running")
            self._bus = bus
            self._clock = clock
            self._active = True

            if self.capture_keyboard:
                self._kb_listener = keyboard.Listener(
                    on_press=self._on_key_press,
                    on_release=self._on_key_release,
                )
                self._kb_listener.daemon = False
                self._kb_listener.start()

            if self.capture_mouse:
                self._mouse_listener = mouse.Listener(
                    on_move=self._on_mouse_move,
                    on_click=self._on_mouse_click,
                    on_scroll=self._on_mouse_scroll,
                )
                self._mouse_listener.daemon = False
                self._mouse_listener.start()

    def _on_key_press(self, key: Any) -> None:
        if not self._active or self._bus is None or self._clock is None:
            return
        code, _ = _key_to_code(key)
        ev = InputEvent(
            seq=0,
            t_host_ns=self._clock.now_ns(),
            source=InputSourceKind.KEYBOARD,
            kind=InputKind.KEY_DOWN,
            code=code,
            value=1.0,
        )
        self._bus.publish(self.topic, ev)

    def _on_key_release(self, key: Any) -> None:
        if not self._active or self._bus is None or self._clock is None:
            return
        code, _ = _key_to_code(key)
        ev = InputEvent(
            seq=0,
            t_host_ns=self._clock.now_ns(),
            source=InputSourceKind.KEYBOARD,
            kind=InputKind.KEY_UP,
            code=code,
            value=0.0,
        )
        self._bus.publish(self.topic, ev)

    def _on_mouse_move(self, x: int, y: int) -> None:
        if not self._active or self._bus is None or self._clock is None:
            return
        ev = InputEvent(
            seq=0,
            t_host_ns=self._clock.now_ns(),
            source=InputSourceKind.MOUSE,
            kind=InputKind.MOVE,
            code=int(x),
            value=float(y),
        )
        self._bus.publish(self.topic, ev)

    def _on_mouse_click(self, x: int, y: int, button: Any, pressed: bool) -> None:
        if not self._active or self._bus is None or self._clock is None:
            return
        kind = InputKind.BUTTON_DOWN if pressed else InputKind.BUTTON_UP
        code = _button_to_code(button)
        ev = InputEvent(
            seq=0,
            t_host_ns=self._clock.now_ns(),
            source=InputSourceKind.MOUSE,
            kind=kind,
            code=code,
            value=1.0 if pressed else 0.0,
        )
        self._bus.publish(self.topic, ev)

    def _on_mouse_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        if not self._active or self._bus is None or self._clock is None:
            return
        ev = InputEvent(
            seq=0,
            t_host_ns=self._clock.now_ns(),
            source=InputSourceKind.MOUSE,
            kind=InputKind.WHEEL,
            code=int(dx),
            value=float(dy),
        )
        self._bus.publish(self.topic, ev)

    def stop(self, timeout_s: float = 2.0) -> None:
        """Stop all listeners cleanly."""
        with self._lock:
            if not self._active:
                return
            self._active = False

        if self._kb_listener is not None:
            self._kb_listener.stop()
            self._kb_listener.join(timeout_s)
            if self._kb_listener.is_alive():
                raise StopTimeout("Keyboard listener failed to stop", timeout_s=timeout_s)
            self._kb_listener = None

        if self._mouse_listener is not None:
            self._mouse_listener.stop()
            self._mouse_listener.join(timeout_s)
            if self._mouse_listener.is_alive():
                raise StopTimeout("Mouse listener failed to stop", timeout_s=timeout_s)
            self._mouse_listener = None
