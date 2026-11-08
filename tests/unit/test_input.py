"""Unit tests for neurosync.input collectors (phase F6)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pyxdf

from neurosync.acquisition.simulated import SimSpec, SimulatedSource, Sine
from neurosync.core.anchors import ClockAnchor
from neurosync.core.bus import EventBus, Policy
from neurosync.core.clock import PerfCounterClock
from neurosync.core.errors import InvalidState
from neurosync.core.model import InputEvent, InputKind, InputSourceKind
from neurosync.core.ring import SignalRing
from neurosync.input.collector import InputCollector
from neurosync.input.gamepad import GamepadCollector
from neurosync.input.keyboard_mouse import (
    KeyboardMouseCollector,
    _button_to_code,
    _key_to_code,
)
from neurosync.input.markers import MarkerSource
from neurosync.input.simulated import ScriptedAction, SimulatedInputSource
from neurosync.recording.recorder import Recorder


def test_input_collector_protocol_compliance() -> None:
    """Verify classes conform to InputCollector protocol."""
    assert isinstance(KeyboardMouseCollector(), InputCollector)
    assert isinstance(GamepadCollector(), InputCollector)


def test_marker_source_publish() -> None:
    bus: EventBus[InputEvent] = EventBus()
    sub = bus.subscribe("input_events", "test_sub", maxsize=100, policy=Policy.BLOCK)
    clock = PerfCounterClock()

    marker = MarkerSource()
    ev = marker.push(bus, clock, marker_code=42, value=1.0)

    assert ev.kind == InputKind.MARKER
    assert ev.source == InputSourceKind.MARKER
    assert ev.code == 42
    assert ev.value == 1.0

    envs = sub.drain(timeout_s=0.5)
    assert len(envs) == 1
    assert envs[0].msg.code == 42


def test_simulated_input_source() -> None:
    bus: EventBus[InputEvent] = EventBus()
    sub = bus.subscribe("input_events", "test_sub", maxsize=100, policy=Policy.BLOCK)
    clock = PerfCounterClock()

    sim = SimulatedInputSource()
    ev1 = sim.emit(
        bus,
        clock,
        source=InputSourceKind.KEYBOARD,
        kind=InputKind.KEY_DOWN,
        code=65,
        value=1.0,
    )
    assert ev1.code == 65
    assert ev1.kind == InputKind.KEY_DOWN

    # Scripted playback
    script = [
        ScriptedAction(
            time_offset_ns=1_000_000,
            source=InputSourceKind.MOUSE,
            kind=InputKind.BUTTON_DOWN,
            code=1,
            value=1.0,
        ),
        ScriptedAction(
            time_offset_ns=2_000_000,
            source=InputSourceKind.MOUSE,
            kind=InputKind.BUTTON_UP,
            code=1,
            value=0.0,
        ),
    ]
    sim_scripted = SimulatedInputSource(script)
    t0 = clock.now_ns()
    emitted = sim_scripted.play_script(bus, clock, t0_ns=t0)
    assert len(emitted) == 2
    assert emitted[0].t_host_ns == t0 + 1_000_000
    assert emitted[1].t_host_ns == t0 + 2_000_000

    envs = sub.drain(max_n=10, timeout_s=0.5)
    assert len(envs) == 3
    assert envs[0].msg.code == 65
    assert envs[1].msg.kind == InputKind.BUTTON_DOWN
    assert envs[2].msg.kind == InputKind.BUTTON_UP


def test_gamepad_collector_axis_and_buttons() -> None:
    bus: EventBus[InputEvent] = EventBus()
    sub = bus.subscribe("input_events", "test_sub", maxsize=100, policy=Policy.BLOCK)
    clock = PerfCounterClock()

    collector = GamepadCollector(device_index=1, poll_period_s=0.01)
    collector.start(bus, clock)
    assert collector.is_alive

    with pytest.raises(InvalidState):
        collector.start(bus, clock)

    # Emit axis
    collector.emit_axis_change(axis_idx=0, value=0.75)
    envs = sub.drain(timeout_s=0.5)
    assert len(envs) == 1
    ev_axis = envs[0].msg
    assert ev_axis.source == InputSourceKind.GAMEPAD
    assert ev_axis.kind == InputKind.AXIS
    assert ev_axis.code == 0
    assert abs(ev_axis.value - 0.75) < 1e-4

    # Jitter smaller than threshold (<0.01) should not emit
    collector.emit_axis_change(axis_idx=0, value=0.755)
    assert sub.depth() == 0

    # Emit button down and up
    collector.emit_button_change(button_idx=2, pressed=True)
    envs_btn = sub.drain(timeout_s=0.5)
    assert len(envs_btn) == 1
    assert envs_btn[0].msg.kind == InputKind.BUTTON_DOWN
    assert envs_btn[0].msg.code == 2

    # Duplicate press should not emit again
    collector.emit_button_change(button_idx=2, pressed=True)
    assert sub.depth() == 0

    collector.emit_button_change(button_idx=2, pressed=False)
    envs_up = sub.drain(timeout_s=0.5)
    assert len(envs_up) == 1
    assert envs_up[0].msg.kind == InputKind.BUTTON_UP
    assert envs_up[0].msg.code == 2

    collector.stop()
    assert collector.is_alive is False


def test_keyboard_mouse_helpers() -> None:
    # Test key code conversion
    mock_vk = MagicMock()
    mock_vk.vk = 65
    code, val = _key_to_code(mock_vk)
    assert code == 65 and val == 1.0

    mock_char = MagicMock(spec=["char"])
    mock_char.char = "x"
    code, val = _key_to_code(mock_char)
    assert code == ord("x")

    mock_val = MagicMock(spec=["value"])
    mock_val.value = MagicMock()
    mock_val.value.vk = 27
    code, val = _key_to_code(mock_val)
    assert code == 27

    # Test button code conversion
    from pynput import mouse

    assert _button_to_code(mouse.Button.left) == 1
    assert _button_to_code(mouse.Button.right) == 2
    assert _button_to_code(mouse.Button.middle) == 3


def test_keyboard_mouse_collector_events() -> None:
    bus: EventBus[InputEvent] = EventBus()
    sub = bus.subscribe("input_events", "test_sub", maxsize=100, policy=Policy.BLOCK)
    clock = PerfCounterClock()

    # Start without actual OS hooks in headless test
    collector = KeyboardMouseCollector(capture_keyboard=False, capture_mouse=False)
    collector.start(bus, clock)
    assert collector.is_alive

    # Synthesize internal callback invocations
    mock_key = MagicMock()
    mock_key.vk = 32  # Space
    collector._on_key_press(mock_key)
    collector._on_key_release(mock_key)

    envs_k = sub.drain(max_n=2, timeout_s=0.5)
    assert len(envs_k) == 2
    assert envs_k[0].msg.kind == InputKind.KEY_DOWN
    assert envs_k[0].msg.code == 32
    assert envs_k[1].msg.kind == InputKind.KEY_UP
    assert envs_k[1].msg.code == 32

    # Mouse moves, clicks, scroll
    collector._on_mouse_move(100, 200)
    collector._on_mouse_click(100, 200, MagicMock(), True)
    collector._on_mouse_scroll(100, 200, 0, 1)

    envs_m = sub.drain(max_n=3, timeout_s=0.5)
    assert len(envs_m) == 3
    assert envs_m[0].msg.kind == InputKind.MOVE
    assert envs_m[0].msg.code == 100
    assert envs_m[0].msg.value == 200.0

    assert envs_m[1].msg.kind == InputKind.BUTTON_DOWN
    assert envs_m[2].msg.kind == InputKind.WHEEL

    collector.stop()
    assert not collector.is_alive


def test_recorder_records_input_events_to_xdf() -> None:
    """End-to-end integration: input events recorded through Recorder into valid XDF."""
    bus: EventBus[InputEvent] = EventBus()
    clock = PerfCounterClock()

    spec = SimSpec(signals=(Sine(10.0),), fs=250.0, n_channels=2)
    source = SimulatedSource(spec)
    ring = SignalRing(source.info, capacity=500)

    with tempfile.TemporaryDirectory() as tmp_dir:
        xdf_path = Path(tmp_dir) / "test_session.xdf"
        anchor = ClockAnchor(
            mono_ns=clock.now_ns(),
            unix_ns=1700000000_000000000,
            uncertainty_ns=50,
        )
        rec = Recorder(
            path=xdf_path,
            clock=clock,
            rings=[ring],
            bus=bus,
            initial_anchor=anchor,
            session_id="test_session",
            batch_interval_s=0.01,
            fsync_interval_s=0.05,
        )
        rec.start()

        # Emit some markers and simulated keys
        marker = MarkerSource()
        marker.push(bus, clock, marker_code=100)
        marker.push(bus, clock, marker_code=200)

        sim = SimulatedInputSource()
        sim.emit(
            bus,
            clock,
            source=InputSourceKind.KEYBOARD,
            kind=InputKind.KEY_DOWN,
            code=65,
        )

        rec.stop(timeout_s=2.0)

        # Read back with pyxdf
        streams, _header = pyxdf.load_xdf(
            str(xdf_path),
            synchronize_clocks=False,
            dejitter_timestamps=False,
        )
        # Find events stream
        input_streams = [s for s in streams if s["info"]["name"][0] == "events"]
        assert len(input_streams) == 1
        input_stream = input_streams[0]
        assert len(input_stream["time_series"]) == 3
        # First marker code 100
        assert input_stream["time_series"][0][3] == 100.0
        # Second marker code 200
        assert input_stream["time_series"][1][3] == 200.0
        # Third key code 65
        assert input_stream["time_series"][2][3] == 65.0
