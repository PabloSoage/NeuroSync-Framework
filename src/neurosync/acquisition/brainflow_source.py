"""BrainFlow source with lossless seqlock ingestion (phase F3).

Fixes the historical race condition (CON-02) and 30-minute stall (EEG-01) by:
- Always using ``get_board_data()`` (which drains BrainFlow's internal buffer)
  instead of ``get_board_data_count()`` + ``get_current_board_data()``.
- Decoupling reading from downstream storage and UI through ``SignalRing``.
- Unwrapping hardware sample counters to detect drops and duplicates.
"""

from __future__ import annotations

import dataclasses
import threading
from typing import Any

import numpy as np
from brainflow.board_shim import (
    BoardIds,
    BoardShim,
    BrainFlowError,
    BrainFlowInputParams,
    BrainFlowPresets,
)

from neurosync.acquisition.counter import CounterUnwrapper, split_runs
from neurosync.acquisition.source import SourceStats
from neurosync.core.clock import Clock
from neurosync.core.errors import DeviceError, InvalidInput, InvalidState, StopTimeout
from neurosync.core.model import ChannelInfo, ChannelKind, QualityFlags, SampleChunk, StreamInfo
from neurosync.core.ring import SignalRing


class BrainFlowSource:
    """SignalSource implementation wrapping BrainFlow boards."""

    def __init__(
        self,
        board_id: int,
        params: BrainFlowInputParams | None = None,
        *,
        stream_id: str = "eeg",
        read_period_s: float = 0.005,
        preset: int = BrainFlowPresets.DEFAULT_PRESET.value,
        counter_bits: int = 8,
    ) -> None:
        self.board_id = board_id
        self.params = params if params is not None else BrainFlowInputParams()
        self.stream_id = stream_id
        self.read_period_s = read_period_s
        self.preset = int(preset)
        self.counter_bits = counter_bits

        self._stats = SourceStats()
        self._unwrapper = CounterUnwrapper(counter_bits)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._error: Exception | None = None
        self._board: BoardShim | None = None

        self._init_info()

    def _init_info(self) -> None:
        effective_board = self.board_id
        if (
            self.board_id == BoardIds.PLAYBACK_FILE_BOARD.value
            and self.params is not None
            and hasattr(self.params, "master_board")
            and self.params.master_board != BoardIds.NO_BOARD.value
        ):
            effective_board = int(self.params.master_board)

        try:
            descr: dict[str, Any] = BoardShim.get_board_descr(effective_board, self.preset)
        except BrainFlowError as exc:
            raise DeviceError(
                f"failed to get board description for board_id={effective_board}: {exc}"
            ) from exc

        fs = float(descr["sampling_rate"])
        self._eeg_channels = np.asarray(descr["eeg_channels"], dtype=np.int64)
        self._package_num_channel = int(descr["package_num_channel"])
        self._timestamp_channel = int(descr["timestamp_channel"])
        self._marker_channel = int(descr.get("marker_channel", -1))

        eeg_names_raw = descr.get("eeg_names", "")
        if isinstance(eeg_names_raw, str) and eeg_names_raw.strip():
            parsed_names = [s.strip() for s in eeg_names_raw.split(",") if s.strip()]
        else:
            parsed_names = []

        n_eeg = len(self._eeg_channels)
        if len(parsed_names) < n_eeg:
            parsed_names.extend(f"eeg_{i}" for i in range(len(parsed_names), n_eeg))
        else:
            parsed_names = parsed_names[:n_eeg]

        channels = tuple(
            ChannelInfo(name=name, kind=ChannelKind.EEG, unit="uV") for name in parsed_names
        )

        board_name = str(descr.get("name", f"board_{self.board_id}"))
        self._info = StreamInfo(
            stream_id=self.stream_id,
            source=f"brainflow:{self.board_id}",
            channels=channels,
            nominal_fs=fs,
            metadata=(
                ("board_id", str(self.board_id)),
                ("board_name", board_name),
                ("preset", str(self.preset)),
            ),
        )

    @property
    def info(self) -> StreamInfo:
        """Stream description."""
        return self._info

    def stats(self) -> SourceStats:
        """Copy of current counters."""
        return dataclasses.replace(self._stats)

    @property
    def error(self) -> Exception | None:
        """Exception that stopped the thread, if any."""
        return self._error

    def start(self, ring: SignalRing, clock: Clock) -> None:
        """Start reading thread. Fails if already started."""
        if self._thread is not None:
            raise InvalidState("the source is already started")
        if ring.info.stream_id != self._info.stream_id:
            raise InvalidInput("the ring belongs to another stream")

        try:
            board = BoardShim(self.board_id, self.params)
            board.prepare_session()
            board.start_stream(450000)
        except BrainFlowError as exc:
            raise DeviceError(f"failed to initialize BrainFlow session: {exc}") from exc

        self._board = board
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(ring, clock),
            name=f"source-{self.stream_id}",
        )
        self._thread.start()

    def _run(self, ring: SignalRing, clock: Clock) -> None:
        try:
            board = self._board
            if board is None:
                return

            preset = self.preset
            pkg_ch = self._package_num_channel
            ts_ch = self._timestamp_channel
            eeg_ch = self._eeg_channels
            stream_id = self._info.stream_id

            while not self._stop.wait(self.read_period_s):
                raw = board.get_board_data(preset=preset)
                if raw.shape[1] == 0:
                    continue

                t_host = clock.now_ns()
                counter = raw[pkg_ch].astype(np.int64)
                t_source_ns = (raw[ts_ch] * 1e9).astype(np.int64)

                unwrap = self._unwrapper.update(counter)
                st = self._stats
                if st.last_t_host_ns is not None:
                    st.max_interchunk_ns = max(st.max_interchunk_ns, t_host - st.last_t_host_ns)
                st.last_t_host_ns = t_host
                st.duplicates += unwrap.duplicates
                st.gaps += unwrap.gaps

                keep = ~unwrap.duplicate
                if not np.any(keep):
                    continue

                signal_data = raw[eeg_ch][:, keep]
                t_src_keep = t_source_ns[keep]
                idx = unwrap.index[keep]
                gap_before = unwrap.gap_before[keep]

                for start, stop in split_runs(idx):
                    n = stop - start
                    flags = QualityFlags.GAP if gap_before[start] > 0 else QualityFlags.NONE
                    chunk = SampleChunk(
                        stream_id=stream_id,
                        seq0=int(idx[start]),
                        data=signal_data[:, start:stop],
                        t_host_ns=t_host,
                        t_source_ns=t_src_keep[start:stop],
                        flags=flags,
                    )
                    ring.write(chunk)
                    st.chunks += 1
                    st.samples += n
        except Exception as exc:  # noqa: BLE001 - thread boundary: stored and exposed
            self._error = exc

    def stop(self, timeout_s: float = 2.0) -> None:
        """Stop thread and release device. Raises StopTimeout if not stopped in time."""
        if self._thread is None and self._board is None:
            return

        if self._thread is not None:
            self._stop.set()
            self._thread.join(timeout_s)
            if self._thread.is_alive():
                raise StopTimeout(
                    "BrainFlow reading thread did not stop in time", timeout_s=timeout_s
                )
            self._thread = None

        errs: list[Exception] = []
        if self._board is not None:
            try:
                self._board.stop_stream()
            except BrainFlowError as exc:
                errs.append(exc)
            try:
                self._board.release_session()
            except BrainFlowError as exc:
                errs.append(exc)
            self._board = None

        if errs:
            raise DeviceError(f"errors during BrainFlow cleanup: {errs}")

    def insert_marker(self, value: float) -> None:
        """Insert a marker into the stream."""
        if self._board is None:
            raise InvalidState("cannot insert marker when not streaming")
        try:
            self._board.insert_marker(value, self.preset)
        except BrainFlowError as exc:
            raise DeviceError(f"failed to insert marker: {exc}") from exc
