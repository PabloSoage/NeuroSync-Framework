"""Web user interface and static dashboard assets for NeuroSync (Phase F10).

Provides a real-time oscilloscope visualizer, event monitor, and control
dashboard served directly by neurosyncd.
"""

from __future__ import annotations

from pathlib import Path


def get_web_dir() -> Path:
    """Return the absolute path to the directory containing web assets."""
    return Path(__file__).resolve().parent


def get_static_dir() -> Path:
    """Return the absolute path to the static assets directory."""
    return get_web_dir() / "static"
