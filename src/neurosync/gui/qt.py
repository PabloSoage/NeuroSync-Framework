"""PySide6 desktop GUI for NeuroSync Framework (Phase F11, per D-10 & D-12).

Isolates Qt and pyqtgraph imports strictly to this module.
Connects to neurosyncd over REST and WebSockets.
"""

from __future__ import annotations

import contextlib
import json
import logging
import subprocess
import sys
from collections import deque
from typing import Any, cast

import httpx
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from neurosync.cli.client import NeuroSyncClient

logger = logging.getLogger(__name__)

# Standard 16-channel EEG channel names and vibrant distinct colors
DEFAULT_CHANNEL_NAMES = [
    "Fp1",
    "Fp2",
    "F3",
    "F4",
    "C3",
    "C4",
    "P3",
    "P4",
    "O1",
    "O2",
    "F7",
    "F8",
    "T7",
    "T8",
    "P7",
    "P8",
]

PALETTE_COLORS = [
    "#06b6d4",
    "#10b981",
    "#f59e0b",
    "#ec4899",
    "#3b82f6",
    "#8b5cf6",
    "#14b8a6",
    "#84cc16",
    "#f97316",
    "#6366f1",
    "#d946ef",
    "#0284c7",
    "#22c55e",
    "#eab308",
    "#a855f7",
    "#ef4444",
]


class DaemonStreamWorker(QObject):
    """Background worker receiving stream chunks and events over WebSockets."""

    data_received = Signal(list)
    event_received = Signal(dict)
    connection_changed = Signal(bool)

    def __init__(self, ws_base_url: str = "ws://127.0.0.1:8000") -> None:
        super().__init__()
        self.ws_base_url = ws_base_url
        self._running = False

    def start_streaming(self) -> None:
        """Run the streaming loop inside the dedicated QThread."""
        import websockets.sync.client

        self._running = True
        stream_url = f"{self.ws_base_url}/ws/stream?format=json"

        while self._running:
            try:
                with websockets.sync.client.connect(stream_url) as ws:
                    self.connection_changed.emit(True)
                    while self._running:
                        try:
                            msg = ws.recv(timeout=0.1)
                            if isinstance(msg, str):
                                payload = json.loads(msg)
                                if "data" in payload:
                                    self.data_received.emit(payload["data"])
                        except TimeoutError:
                            continue
            except (OSError, RuntimeError):
                self.connection_changed.emit(False)
                # Retry delay without blocking GUI
                QThread.msleep(1000)

    def stop(self) -> None:
        """Signal the worker thread to terminate cleanly."""
        self._running = False


class OscilloscopeWidget(QWidget):
    """Real-time multi-channel oscilloscope widget supporting stacked and separated views."""

    def __init__(
        self,
        n_channels: int = 16,
        fs: float = 250.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.n_channels = n_channels
        self.fs = fs
        self.time_window_s = 5.0
        self.gain = 1.0
        self.mode = "stacked"  # "stacked" or "separate"

        self.buf_len = int(self.fs * 10)
        self.data_buffer = [
            deque([0.0] * self.buf_len, maxlen=self.buf_len) for _ in range(n_channels)
        ]

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Plot Widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#080c12")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("bottom", "Time (seconds)")
        layout.addWidget(self.plot_widget)

        # Create plot curves
        self.curves: list[pg.PlotDataItem] = []
        for i in range(self.n_channels):
            color = PALETTE_COLORS[i % len(PALETTE_COLORS)]
            pen = pg.mkPen(color=color, width=1.2)
            curve = self.plot_widget.plot(pen=pen)
            self.curves.append(curve)

        self._update_axes()

    def _update_axes(self) -> None:
        if self.mode == "stacked":
            # Set custom ticks on Y axis for channel names
            y_axis = self.plot_widget.getAxis("left")
            spacing = 100.0
            ticks = []
            for i in range(self.n_channels):
                ch_name = (
                    DEFAULT_CHANNEL_NAMES[i] if i < len(DEFAULT_CHANNEL_NAMES) else f"CH{i + 1}"
                )
                ticks.append(((self.n_channels - 1 - i) * spacing, ch_name))
            y_axis.setTicks([ticks])
            self.plot_widget.setYRange(-spacing, self.n_channels * spacing)
        else:
            self.plot_widget.getAxis("left").setTicks(None)
            self.plot_widget.autoRange()

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self._update_axes()

    def set_gain(self, gain: float) -> None:
        self.gain = gain

    def set_time_window(self, seconds: float) -> None:
        self.time_window_s = seconds

    def append_chunk(self, chunk: list[list[float]]) -> None:
        n_ch = min(len(chunk), self.n_channels)
        for i in range(n_ch):
            self.data_buffer[i].extend(chunk[i])

    def update_plot(self) -> None:
        n_samples = int(self.fs * self.time_window_s)
        time_x = np.linspace(-self.time_window_s, 0.0, n_samples)
        spacing = 100.0

        for i, curve in enumerate(self.curves):
            buf = self.data_buffer[i]
            if len(buf) < n_samples:
                continue
            y_data = np.array(list(buf)[-n_samples:], dtype=np.float64) * self.gain

            if self.mode == "stacked":
                offset = (self.n_channels - 1 - i) * spacing
                curve.setData(time_x, y_data + offset)
            else:
                curve.setData(time_x, y_data)


class SpectralWidget(QWidget):
    """Real-time Welch PSD and EEG power bands bar chart."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)

        # PSD Spectrum plot
        self.psd_plot = pg.PlotWidget(title="Welch Power Spectral Density (1-50 Hz)")
        self.psd_plot.setBackground("#080c12")
        self.psd_plot.showGrid(x=True, y=True, alpha=0.3)
        self.psd_plot.setLabel("bottom", "Frequency (Hz)")
        self.psd_plot.setLabel("left", "PSD (dB / µV²/Hz)")
        self.psd_plot.setXRange(0, 50)
        self.psd_curve = self.psd_plot.plot(pen=pg.mkPen("#06b6d4", width=2))
        layout.addWidget(self.psd_plot, stretch=2)

        # Band-power bar graph
        self.band_plot = pg.PlotWidget(title="EEG Band Powers")
        self.band_plot.setBackground("#080c12")
        self.band_plot.setLabel("bottom", "Frequency Band")
        self.band_plot.setLabel("left", "Relative Power")
        x_ticks = [(1, "Delta"), (2, "Theta"), (3, "Alpha"), (4, "Beta"), (5, "Gamma")]
        self.band_plot.getAxis("bottom").setTicks([x_ticks])
        self.band_plot.setXRange(0.5, 5.5)

        self.bar_items = pg.BarGraphItem(
            x=[1, 2, 3, 4, 5],
            height=[10, 8, 15, 6, 3],
            width=0.6,
            brushes=[
                pg.mkBrush("#3b82f6"),
                pg.mkBrush("#06b6d4"),
                pg.mkBrush("#10b981"),
                pg.mkBrush("#f59e0b"),
                pg.mkBrush("#8b5cf6"),
            ],
        )
        self.band_plot.addItem(self.bar_items)
        layout.addWidget(self.band_plot, stretch=1)

    def update_spectrum(self, raw_data: np.ndarray) -> None:
        """Compute Welch PSD and band power from raw EEG samples."""
        if raw_data.size < 128:
            return

        from scipy.signal import welch

        freqs, psd = welch(raw_data, fs=250.0, nperseg=min(256, len(raw_data)))
        mask = (freqs >= 1.0) & (freqs <= 50.0)
        f_sub = freqs[mask]
        p_sub = psd[mask]

        if len(f_sub) > 0 and np.all(p_sub > 0):
            p_db = 10 * np.log10(p_sub)
            self.psd_curve.setData(f_sub, p_db)

            # Compute bands
            def _band_power(f_min: float, f_max: float) -> float:
                b_mask = (freqs >= f_min) & (freqs < f_max)
                return float(np.mean(psd[b_mask])) if np.any(b_mask) else 1.0

            delta = _band_power(0.5, 4.0)
            theta = _band_power(4.0, 8.0)
            alpha = _band_power(8.0, 12.0)
            beta = _band_power(12.0, 30.0)
            gamma = _band_power(30.0, 45.0)

            self.bar_items.setOpts(height=[delta, theta, alpha, beta, gamma])


class EventLogWidget(QWidget):
    """Real-time event stream table."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Seq", "Host Time (s)", "Event Code", "Payload"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("background-color: #080c12; color: #e2e8f0;")
        layout.addWidget(self.table)

    def add_event(self, ev: dict[str, Any]) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        seq_item = QTableWidgetItem(str(ev.get("seq", row)))
        t_sec = float(ev.get("t_host_ns", 0)) / 1e9
        time_item = QTableWidgetItem(f"{t_sec:.3f}")
        code_item = QTableWidgetItem(str(ev.get("code", "EVENT")))
        payload_item = QTableWidgetItem(json.dumps(ev.get("payload", {})))

        self.table.setItem(row, 0, seq_item)
        self.table.setItem(row, 1, time_item)
        self.table.setItem(row, 2, code_item)
        self.table.setItem(row, 3, payload_item)
        self.table.scrollToBottom()


class ExportDialog(QDialog):
    """Modal dialog for offline export to CSV, EDF+, BIDS, and NumPy."""

    def __init__(self, client: NeuroSyncClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.client = client
        self.setWindowTitle("Export Session Data")
        self.resize(400, 250)

        layout = QFormLayout(self)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["csv", "edf", "bids", "npz"])
        layout.addRow("Export Format:", self.format_combo)

        self.out_dir_edit = QLineEdit("exports")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_dir)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.out_dir_edit)
        dir_layout.addWidget(browse_btn)
        layout.addRow("Output Directory:", dir_layout)

        self.btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn_box.accepted.connect(self._run_export)
        self.btn_box.rejected.connect(self.reject)
        layout.addRow(self.btn_box)

    def _browse_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if d:
            self.out_dir_edit.setText(d)

    def _run_export(self) -> None:
        fmt = self.format_combo.currentText()
        out_dir = self.out_dir_edit.text()
        try:
            resp = self.client.export(
                xdf_path="latest.xdf",
                output_dir=out_dir,
                format_name=fmt,
            )
            count = sum(len(paths) for paths in resp.results.values())
            QMessageBox.information(
                self,
                "Export Successful",
                f"Exported {count} files to {out_dir}",
            )
            self.accept()
        except (httpx.HTTPError, OSError, RuntimeError) as exc:
            QMessageBox.critical(self, "Export Failed", f"Error: {exc}")


class NeuroSyncMainWindow(QMainWindow):
    """Main application window for NeuroSync PySide6 GUI."""

    def __init__(self, server_url: str = "http://127.0.0.1:8000") -> None:
        super().__init__()
        self.server_url = server_url
        self.client = NeuroSyncClient(base_url=server_url)

        self.setWindowTitle("NeuroSync Framework v2 · Desktop GUI")
        self.resize(1280, 800)

        self._ensure_server_running()

        self.oscilloscope = OscilloscopeWidget(n_channels=16, fs=250.0)
        self.spectral = SpectralWidget()
        self.events_widget = EventLogWidget()

        self._setup_ui()
        self._setup_worker()

        # Update timer for oscilloscope plots (~30 Hz)
        self.plot_timer = QTimer(self)
        self.plot_timer.timeout.connect(self._on_plot_tick)
        self.plot_timer.start(33)

        # Status polling timer (1 Hz)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._on_status_tick)
        self.status_timer.start(1000)

    def _ensure_server_running(self) -> None:
        """Start neurosyncd background daemon if it is not already reachable (D-10)."""
        try:
            self.client.get_status()
        except (httpx.HTTPError, OSError):
            # Server not responding, spawn daemon process
            with contextlib.suppress(OSError):
                subprocess.Popen(
                    [sys.executable, "-m", "neurosync.server.service"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Control Panel GroupBox
        ctrl_box = QGroupBox("Acquisition & Session Controls")
        ctrl_layout = QHBoxLayout(ctrl_box)

        # Source Selection
        ctrl_layout.addWidget(QLabel("Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItem("Synthetic (16ch)", -1)
        self.source_combo.addItem("Simulated Ground Truth", 0)
        ctrl_layout.addWidget(self.source_combo)

        # Start/Stop Acq
        self.btn_acq_start = QPushButton("Start Acq")
        self.btn_acq_start.setStyleSheet("background-color: #2563eb; color: white;")
        self.btn_acq_start.clicked.connect(self._start_acquisition)
        ctrl_layout.addWidget(self.btn_acq_start)

        self.btn_acq_stop = QPushButton("Stop Acq")
        self.btn_acq_stop.setEnabled(False)
        self.btn_acq_stop.clicked.connect(self._stop_acquisition)
        ctrl_layout.addWidget(self.btn_acq_stop)

        # Recording
        ctrl_layout.addWidget(QLabel("Session:"))
        self.session_edit = QLineEdit("session_001")
        self.session_edit.setMaximumWidth(120)
        ctrl_layout.addWidget(self.session_edit)

        self.btn_rec_start = QPushButton("Record")
        self.btn_rec_start.setStyleSheet("background-color: #059669; color: white;")
        self.btn_rec_start.setEnabled(False)
        self.btn_rec_start.clicked.connect(self._start_recording)
        ctrl_layout.addWidget(self.btn_rec_start)

        self.btn_rec_stop = QPushButton("Stop Rec")
        self.btn_rec_stop.setEnabled(False)
        self.btn_rec_stop.clicked.connect(self._stop_recording)
        ctrl_layout.addWidget(self.btn_rec_stop)

        # Quick Markers
        ctrl_layout.addWidget(QLabel("Markers:"))
        for m in [1, 2, 3]:
            btn_mk = QPushButton(f"M{m}")
            btn_mk.setMaximumWidth(40)
            btn_mk.clicked.connect(lambda _, val=m: self._send_marker(val))
            ctrl_layout.addWidget(btn_mk)

        # Filter Toggles
        self.chk_notch = QCheckBox("Notch (50Hz)")
        self.chk_notch.setChecked(True)
        self.chk_notch.toggled.connect(self._update_filters)
        ctrl_layout.addWidget(self.chk_notch)

        self.chk_bp = QCheckBox("BP (1-40Hz)")
        self.chk_bp.setChecked(True)
        self.chk_bp.toggled.connect(self._update_filters)
        ctrl_layout.addWidget(self.chk_bp)

        # Export Button
        btn_export = QPushButton("Export Data...")
        btn_export.clicked.connect(self._open_export_dialog)
        ctrl_layout.addWidget(btn_export)

        main_layout.addWidget(ctrl_box)

        # Oscilloscope controls bar
        osc_bar = QHBoxLayout()
        osc_bar.addWidget(QLabel("View Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Stacked Montage", "stacked")
        self.mode_combo.addItem("Separate Traces", "separate")
        self.mode_combo.currentIndexChanged.connect(
            lambda: self.oscilloscope.set_mode(str(self.mode_combo.currentData()))
        )
        osc_bar.addWidget(self.mode_combo)

        osc_bar.addWidget(QLabel("Time Window:"))
        self.time_combo = QComboBox()
        self.time_combo.addItem("2s", 2.0)
        self.time_combo.addItem("5s", 5.0)
        self.time_combo.addItem("10s", 10.0)
        self.time_combo.setCurrentIndex(1)
        self.time_combo.currentIndexChanged.connect(
            lambda: self.oscilloscope.set_time_window(float(self.time_combo.currentData()))
        )
        osc_bar.addWidget(self.time_combo)

        osc_bar.addWidget(QLabel("Gain:"))
        self.gain_spin = QDoubleSpinBox()
        self.gain_spin.setRange(0.1, 20.0)
        self.gain_spin.setSingleStep(0.5)
        self.gain_spin.setValue(1.0)
        self.gain_spin.valueChanged.connect(self.oscilloscope_set_gain)
        osc_bar.addWidget(self.gain_spin)
        osc_bar.addStretch()

        main_layout.addLayout(osc_bar)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.addTab(self.oscilloscope, "Real-Time Oscilloscope")
        self.tabs.addTab(self.spectral, "Spectral PSD & Band Power")
        self.tabs.addTab(self.events_widget, "Event Stream Log")
        main_layout.addWidget(self.tabs, stretch=1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_daemon = QLabel("Daemon: Checking...")
        self.lbl_acq = QLabel("Acquisition: Idle")
        self.lbl_rec = QLabel("Recording: Idle")
        self.lbl_lost = QLabel("Lost: 0")

        self.status_bar.addPermanentWidget(self.lbl_daemon)
        self.status_bar.addPermanentWidget(self.lbl_acq)
        self.status_bar.addPermanentWidget(self.lbl_rec)
        self.status_bar.addPermanentWidget(self.lbl_lost)

    def oscilloscope_set_gain(self, val: float) -> None:
        self.oscilloscope.set_gain(val)

    def _setup_worker(self) -> None:
        self.worker_thread = QThread()
        # Parse ws URL from server URL
        ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
        self.stream_worker = DaemonStreamWorker(ws_base_url=ws_url)
        self.stream_worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.stream_worker.start_streaming)
        self.stream_worker.data_received.connect(self.oscilloscope.append_chunk)
        self.stream_worker.event_received.connect(self.events_widget.add_event)
        self.stream_worker.connection_changed.connect(self._on_connection_changed)

        self.worker_thread.start()

    def _on_connection_changed(self, connected: bool) -> None:
        if connected:
            self.lbl_daemon.setText("Daemon: Online")
            self.lbl_daemon.setStyleSheet("color: #10b981;")
        else:
            self.lbl_daemon.setText("Daemon: Offline")
            self.lbl_daemon.setStyleSheet("color: #ef4444;")

    def _on_plot_tick(self) -> None:
        self.oscilloscope.update_plot()
        if self.tabs.currentIndex() == 1:
            # Update spectrum tab with channel 0 data
            ch0 = self.oscilloscope.data_buffer[0]
            if len(ch0) > 128:
                self.spectral.update_spectrum(np.array(list(ch0)[-256:]))

    def _on_status_tick(self) -> None:
        try:
            status = self.client.get_status()
            is_acq = status.status in {"acquiring", "recording"}
            is_rec = status.status == "recording"

            self.btn_acq_start.setEnabled(not is_acq)
            self.btn_acq_stop.setEnabled(is_acq)
            self.btn_rec_start.setEnabled(is_acq and not is_rec)
            self.btn_rec_stop.setEnabled(is_rec)

            self.lbl_acq.setText("Acquisition: Running" if is_acq else "Acquisition: Idle")
            self.lbl_rec.setText("Recording: Active" if is_rec else "Recording: Idle")
        except (httpx.HTTPError, OSError):
            self._on_connection_changed(False)

    def _start_acquisition(self) -> None:
        board_id = int(self.source_combo.currentData())
        try:
            self.client.start_acquisition(board_id=board_id)
            self._on_status_tick()
        except (httpx.HTTPError, RuntimeError) as exc:
            QMessageBox.critical(self, "Acquisition Error", str(exc))

    def _stop_acquisition(self) -> None:
        try:
            self.client.stop_acquisition()
            self._on_status_tick()
        except (httpx.HTTPError, RuntimeError) as exc:
            QMessageBox.critical(self, "Error Stopping Acquisition", str(exc))

    def _start_recording(self) -> None:
        session = self.session_edit.text().strip() or "session_001"
        try:
            out_file = f"{session}.xdf"
            self.client.start_recording(output_path=out_file, session_id=session)
            self._on_status_tick()
        except (httpx.HTTPError, RuntimeError) as exc:
            QMessageBox.critical(self, "Recording Error", str(exc))

    def _stop_recording(self) -> None:
        try:
            summary = self.client.stop_recording()
            samples = summary.total_samples
            events = summary.total_events
            dur = summary.duration_s
            QMessageBox.information(
                self,
                "Recording Completed",
                f"Saved to XDF.\nDuration: {dur:.1f}s\nSamples: {samples}\nEvents: {events}",
            )
            self._on_status_tick()
        except (httpx.HTTPError, RuntimeError) as exc:
            QMessageBox.critical(self, "Error Stopping Recording", str(exc))

    def _send_marker(self, marker_code: int) -> None:
        with contextlib.suppress(httpx.HTTPError, OSError):
            self.client.emit_marker(marker_code=marker_code, value=1.0)

    def _update_filters(self) -> None:
        with contextlib.suppress(httpx.HTTPError, OSError):
            self.client.configure_filter(
                enabled=self.chk_bp.isChecked() or self.chk_notch.isChecked(),
                lowcut_hz=1.0 if self.chk_bp.isChecked() else None,
                highcut_hz=40.0 if self.chk_bp.isChecked() else None,
                notch_hz=50.0 if self.chk_notch.isChecked() else None,
            )

    def _open_export_dialog(self) -> None:
        dlg = ExportDialog(self.client, self)
        dlg.exec()

    def shutdown(self) -> None:
        """Cleanly stop timers and background threads."""
        self.plot_timer.stop()
        self.status_timer.stop()
        self.stream_worker.stop()
        self.worker_thread.quit()
        self.worker_thread.wait(2000)

    def closeEvent(self, event: Any) -> None:
        self.shutdown()
        super().closeEvent(event)


def apply_dark_theme(app: QApplication) -> None:
    """Configure modern dark palette for PySide6 application."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0f141c"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e2e8f0"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#18202c"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#212c3d"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e2e8f0"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#212c3d"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e2e8f0"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#2563eb"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)


def main() -> None:
    """CLI entrypoint for running the NeuroSync PySide6 desktop GUI."""
    existing_app = QApplication.instance()
    app = cast(QApplication, existing_app) if existing_app is not None else QApplication(sys.argv)
    apply_dark_theme(app)
    window = NeuroSyncMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
