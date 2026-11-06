"""Core hardware and session execution engine for neurosyncd (phase F8).

Owns hardware acquisition, online filtering, recording sessions, and marker injection.
Decoupled from FastAPI, Uvicorn, CLI and GUI.
"""

from __future__ import annotations

import threading
from pathlib import Path

from brainflow.board_shim import BrainFlowInputParams

from neurosync.acquisition.brainflow_source import BrainFlowSource
from neurosync.core.anchors import take_anchor
from neurosync.core.bus import EventBus
from neurosync.core.clock import Clock, PerfCounterClock
from neurosync.core.errors import InvalidState
from neurosync.core.model import InputEvent, StreamInfo
from neurosync.core.ring import SignalRing
from neurosync.dsp.filters import CausalSosFilter, FilterConfig, FilterPipeline
from neurosync.dsp.stream import FilteredStreamWorker
from neurosync.export.manager import ExportFormat, ExportManager
from neurosync.input.markers import MarkerSource
from neurosync.recording.recorder import Recorder
from neurosync.server.schema import (
    ConfigureFilterRequest,
    ExportRequest,
    ExportResponse,
    ServerStatusResponse,
    StartAcquisitionRequest,
    StartRecordingRequest,
    StopRecordingResponse,
    StreamStatus,
)


class ServerEngine:
    """Manages the full lifecycle of data acquisition, filtering, and recording."""

    def __init__(self, clock: Clock | None = None) -> None:
        self.clock: Clock = clock or PerfCounterClock()
        self._start_mono_ns = self.clock.now_ns()

        self.bus: EventBus[InputEvent] = EventBus()
        self.marker_source = MarkerSource()

        self._lock = threading.Lock()
        self._source: BrainFlowSource | None = None
        self._raw_ring: SignalRing | None = None
        self._filtered_ring: SignalRing | None = None
        self._filter_worker: FilteredStreamWorker | None = None
        self._filter_config = FilterConfig.bandpass(1.0, 45.0, fs=250.0)
        self._notch_hz: float | None = 50.0
        self._filter_enabled = True

        self._recorder: Recorder | None = None
        self._recording_path: Path | None = None
        self._session_id: str = ""
        self._active_board_desc: str | None = None

    @property
    def is_acquiring(self) -> bool:
        with self._lock:
            return self._source is not None and self._source.is_alive

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._recorder is not None and self._recorder.is_alive

    @property
    def raw_ring(self) -> SignalRing | None:
        with self._lock:
            return self._raw_ring

    @property
    def filtered_ring(self) -> SignalRing | None:
        with self._lock:
            return self._filtered_ring

    def start_acquisition(self, req: StartAcquisitionRequest) -> ServerStatusResponse:
        """Initialize acquisition hardware and start ingestion ring."""
        with self._lock:
            if self._source is not None and self._source.is_alive:
                raise InvalidState("Acquisition is already running")

            params = BrainFlowInputParams()
            if req.serial_port:
                params.serial_port = req.serial_port
            if req.master_board is not None:
                params.master_board = req.master_board

            source = BrainFlowSource(board_id=req.board_id, params=params)
            fs = source.info.nominal_fs or 250.0
            capacity = round(fs * 60)  # 60s ring buffer

            raw_ring = SignalRing(source.info, capacity=capacity)
            source.start(raw_ring, self.clock)

            self._source = source
            self._raw_ring = raw_ring
            self._active_board_desc = f"BrainFlow_{req.board_id}"

            # Setup filtered derived stream if enabled
            self._setup_filter_pipeline_locked(fs)

        return self.get_status()

    def _setup_filter_pipeline_locked(self, fs: float) -> None:
        """Instantiate or reconfigure causal filter pipeline for current raw ring."""
        if self._raw_ring is None:
            return

        if self._filter_worker is not None:
            self._filter_worker.stop()
            self._filter_worker = None

        if not self._filter_enabled:
            self._filtered_ring = None
            return

        n_ch = self._raw_ring.info.n_channels
        # Build pipeline filters
        configs = []
        if self._filter_config is not None:
            configs.append(self._filter_config)
        if self._notch_hz is not None:
            configs.append(FilterConfig.notch(self._notch_hz, fs=fs))

        if not configs:
            self._filtered_ring = None
            return

        sos_filters = [CausalSosFilter(cfg, n_channels=n_ch) for cfg in configs]
        pipeline = FilterPipeline(sos_filters)

        derived_info = StreamInfo(
            stream_id="filtered",
            source="dsp",
            channels=self._raw_ring.info.channels,
            nominal_fs=self._raw_ring.info.nominal_fs,
        )
        filtered_ring = SignalRing(derived_info, capacity=self._raw_ring.capacity)

        self._filter_worker = FilteredStreamWorker(
            input_ring=self._raw_ring,
            output_ring=filtered_ring,
            pipeline=pipeline,
            clock=self.clock,
        )
        self._filtered_ring = filtered_ring
        self._filter_worker.start()

    def stop_acquisition(self) -> ServerStatusResponse:
        """Stop acquisition and any active recording."""
        with self._lock:
            if self._recorder is not None and self._recorder.is_alive:
                self._stop_recording_locked()

            if self._filter_worker is not None:
                self._filter_worker.stop()
                self._filter_worker = None

            if self._source is not None:
                self._source.stop()
                self._source = None

            self._active_board_desc = None
        return self.get_status()

    def start_recording(self, req: StartRecordingRequest) -> ServerStatusResponse:
        """Start streaming session recording to XDF."""
        with self._lock:
            if self._source is None or not self._source.is_alive or self._raw_ring is None:
                raise InvalidState("Cannot record without an active signal stream")
            if self._recorder is not None and self._recorder.is_alive:
                raise InvalidState("A recording session is already in progress")

            path = Path(req.output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            rings = [self._raw_ring]
            if self._filtered_ring is not None:
                rings.append(self._filtered_ring)

            anchor = take_anchor(self.clock)
            recorder = Recorder(
                path=path,
                clock=self.clock,
                rings=rings,
                bus=self.bus,
                initial_anchor=anchor,
                session_id=req.session_id,
            )
            recorder.start()

            self._recorder = recorder
            self._recording_path = path
            self._session_id = req.session_id

        return self.get_status()

    def _stop_recording_locked(self) -> StopRecordingResponse:
        """Internal helper to finalize recording with lock held."""
        if self._recorder is None:
            raise InvalidState("No active recording session to stop")

        rec = self._recorder
        path = self._recording_path or Path("unknown.xdf")
        session_id = self._session_id

        summary = rec.stop(timeout_s=3.0)
        self._recorder = None
        self._recording_path = None
        self._session_id = ""

        total_samples = sum(summary.samples.values())
        return StopRecordingResponse(
            session_id=session_id,
            xdf_path=str(path),
            duration_s=summary.duration_s,
            total_samples=total_samples,
            total_events=summary.event_count,
            max_flush_lag_ms=summary.max_flush_lag_ms,
        )

    def stop_recording(self) -> StopRecordingResponse:
        """Stop current recording session and return final summary metrics."""
        with self._lock:
            return self._stop_recording_locked()

    def emit_marker(self, marker_code: int, value: float = 1.0) -> InputEvent:
        """Stamp an experimental marker event onto the event bus."""
        return self.marker_source.push(
            self.bus,
            self.clock,
            marker_code=marker_code,
            value=value,
        )

    def configure_filter(self, req: ConfigureFilterRequest) -> ServerStatusResponse:
        """Update filter parameters dynamically."""
        with self._lock:
            self._filter_enabled = req.enabled
            fs = 250.0
            if self._raw_ring is not None and self._raw_ring.info.nominal_fs:
                fs = self._raw_ring.info.nominal_fs

            if req.lowcut_hz is not None and req.highcut_hz is not None:
                self._filter_config = FilterConfig.bandpass(req.lowcut_hz, req.highcut_hz, fs=fs)
            elif req.lowcut_hz is not None:
                self._filter_config = FilterConfig.highpass(req.lowcut_hz, fs=fs)
            elif req.highcut_hz is not None:
                self._filter_config = FilterConfig.lowpass(req.highcut_hz, fs=fs)

            self._notch_hz = req.notch_hz

            if self._raw_ring is not None:
                self._setup_filter_pipeline_locked(fs)

        return self.get_status()

    def run_export(self, req: ExportRequest) -> ExportResponse:
        """Run offline export converting recorded XDF to specified target format."""
        mgr = ExportManager(req.xdf_path)
        fmt = ExportFormat(req.format.lower())
        results = mgr.export(
            fmt,
            req.output_dir,
            subject_id=req.subject_id,
            task_id=req.task_id,
        )
        serialized_results: dict[str, list[str]] = {
            k: [str(p) for p in v] for k, v in results.items()
        }
        return ExportResponse(results=serialized_results)

    def get_status(self) -> ServerStatusResponse:
        """Query current engine operational status."""
        with self._lock:
            uptime = (self.clock.now_ns() - self._start_mono_ns) * 1e-9

            state = "idle"
            if self._recorder is not None and self._recorder.is_alive:
                state = "recording"
            elif self._source is not None and self._source.is_alive:
                state = "acquiring"

            primary_status: StreamStatus | None = None
            if self._raw_ring is not None:
                primary_status = StreamStatus(
                    stream_id=self._raw_ring.info.stream_id,
                    nominal_fs=self._raw_ring.info.nominal_fs or 0.0,
                    channels=[ch.name for ch in self._raw_ring.info.channels],
                    sample_count=self._raw_ring.head,
                    head=self._raw_ring.head,
                )

            filtered_status: StreamStatus | None = None
            if self._filtered_ring is not None:
                filtered_status = StreamStatus(
                    stream_id=self._filtered_ring.info.stream_id,
                    nominal_fs=self._filtered_ring.info.nominal_fs or 0.0,
                    channels=[ch.name for ch in self._filtered_ring.info.channels],
                    sample_count=self._filtered_ring.head,
                    head=self._filtered_ring.head,
                )

            recording_file = str(self._recording_path) if self._recording_path else None
            samples_rec = 0
            events_rec = 0
            if self._recorder is not None:
                samples_rec = sum(ctx.total_samples for ctx in self._recorder._streams.values())
                events_rec = self._recorder._total_events

            return ServerStatusResponse(
                status=state,
                uptime_s=uptime,
                active_board=self._active_board_desc,
                primary_stream=primary_status,
                filtered_stream=filtered_status,
                recording_file=recording_file,
                samples_recorded=samples_rec,
                events_recorded=events_rec,
                filter_enabled=self._filter_enabled,
            )
