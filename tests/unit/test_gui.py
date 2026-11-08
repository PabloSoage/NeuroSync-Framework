"""Unit tests for neurosync.gui PySide6 desktop GUI (Phase F11)."""

from __future__ import annotations

import os

import numpy as np
import pytest

# Ensure Qt runs offscreen in test environments
os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp() -> object:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_oscilloscope_widget(qapp: object) -> None:
    """Test OscilloscopeWidget data ingestion, mode switching, and rendering."""
    from neurosync.gui.qt import OscilloscopeWidget

    osc = OscilloscopeWidget(n_channels=16, fs=250.0)
    assert osc.n_channels == 16
    assert len(osc.curves) == 16

    # Ingest synthetic chunk
    chunk = [[float(val)] * 50 for val in range(16)]
    osc.append_chunk(chunk)

    # Test settings
    osc.set_gain(2.0)
    assert osc.gain == 2.0

    osc.set_time_window(2.0)
    assert osc.time_window_s == 2.0

    osc.set_mode("separate")
    assert osc.mode == "separate"

    osc.set_mode("stacked")
    assert osc.mode == "stacked"

    # Run plot update
    osc.update_plot()


def test_spectral_widget(qapp: object) -> None:
    """Test SpectralWidget Welch PSD computation and band power updates."""
    from neurosync.gui.qt import SpectralWidget

    spec = SpectralWidget()
    assert spec.psd_plot is not None
    assert spec.band_plot is not None

    # Feed 10 Hz sine wave (Alpha band)
    t = np.linspace(0, 2.0, 500)
    signal = 10.0 * np.sin(2 * np.pi * 10.0 * t)
    spec.update_spectrum(signal)

    # Check curve data populated
    x_data, y_data = spec.psd_curve.getData()
    assert len(x_data) > 0
    assert len(y_data) > 0


def test_event_log_widget(qapp: object) -> None:
    """Test EventLogWidget event insertion and row rendering."""
    from neurosync.gui.qt import EventLogWidget

    log_widget = EventLogWidget()
    assert log_widget.table.rowCount() == 0

    log_widget.add_event(
        {
            "seq": 1,
            "t_host_ns": 1_000_000_000,
            "code": "MARKER_STIM",
            "payload": {"value": 42.0},
        }
    )
    assert log_widget.table.rowCount() == 1
    item_seq = log_widget.table.item(0, 0)
    item_code = log_widget.table.item(0, 2)
    assert item_seq is not None and item_seq.text() == "1"
    assert item_code is not None and item_code.text() == "MARKER_STIM"


def test_main_window_headless_initialization(qapp: object) -> None:
    """Test NeuroSyncMainWindow headless instantiation and shutdown."""
    from neurosync.gui.qt import NeuroSyncMainWindow

    # Launch pointing to a dummy URL
    win = NeuroSyncMainWindow(server_url="http://127.0.0.1:9999")
    assert win.windowTitle() == "NeuroSync Framework v2 · Desktop GUI"
    assert win.oscilloscope is not None
    assert win.spectral is not None
    assert win.events_widget is not None

    # Clean shutdown
    win.shutdown()
    win.close()
