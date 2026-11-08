"""Input event collectors for human behavioral tracking and experimental markers (phase F6).

Captures:
- Keyboard events (presses and releases) via KeyboardMouseCollector
- Mouse movements, clicks, and scroll wheel via KeyboardMouseCollector
- Gamepad / joystick inputs via GamepadCollector
- Experimental stimulation markers via MarkerSource
- Scriptable simulated input events via SimulatedInputSource
"""

from __future__ import annotations

from neurosync.input.collector import InputCollector
from neurosync.input.gamepad import GamepadCollector
from neurosync.input.keyboard_mouse import KeyboardMouseCollector
from neurosync.input.markers import MarkerSource
from neurosync.input.simulated import ScriptedAction, SimulatedInputSource

__all__ = [
    "GamepadCollector",
    "InputCollector",
    "KeyboardMouseCollector",
    "MarkerSource",
    "ScriptedAction",
    "SimulatedInputSource",
]
