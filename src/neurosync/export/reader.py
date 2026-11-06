"""Parser for recorded XDF sessions and sidecar metadata (phase F7)."""

from __future__ import annotations

import contextlib
from pathlib import Path

import numpy as np
import pyxdf

from neurosync.core.anchors import ClockAnchor
from neurosync.core.errors import InvalidInput
from neurosync.core.model import InputEvent, InputKind, InputSourceKind
from neurosync.export.session import ExportSignalStream, ParsedSession
from neurosync.recording.sidecar import SessionSidecar


def load_session(xdf_path: Path | str) -> ParsedSession:
    """Load and parse an XDF recording and its sidecar metadata into ParsedSession."""
    path = Path(xdf_path)
    if not path.is_file():
        raise InvalidInput(f"XDF file does not exist: {path}")

    # Load sidecar if present (.json or .sidecar.json)
    sidecar_path = path.with_suffix(".json")
    if not sidecar_path.is_file():
        sidecar_path = path.with_suffix(".sidecar.json")

    sidecar: SessionSidecar | None = None
    if sidecar_path.is_file():
        sidecar = SessionSidecar.load(sidecar_path)

    session_id = sidecar.session_id if sidecar is not None else path.stem

    # Load streams via pyxdf
    streams, _header = pyxdf.load_xdf(
        str(path),
        synchronize_clocks=False,
        dejitter_timestamps=False,
    )

    signal_streams: list[ExportSignalStream] = []
    events: list[InputEvent] = []
    anchors: list[ClockAnchor] = []

    for stream in streams:
        info = stream.get("info", {})
        s_name = str(info.get("name", ["unnamed"])[0])
        s_type = str(info.get("type", ["UNKNOWN"])[0])
        srate_str = info.get("nominal_srate", ["0"])[0]
        try:
            nominal_srate = float(srate_str)
        except (ValueError, TypeError):
            nominal_srate = 0.0

        ts = np.asarray(stream.get("time_stamps", []), dtype=np.float64)
        data = np.asarray(stream.get("time_series", []), dtype=np.float64)

        if s_type == "ANCHOR" or s_name == "clock_anchors":
            # 3 channels: mono_ns, unix_ns, uncertainty_ns
            if len(data.shape) == 2 and data.shape[1] >= 3:
                for row in data:
                    anchors.append(
                        ClockAnchor(
                            mono_ns=int(row[0]),
                            unix_ns=int(row[1]),
                            uncertainty_ns=int(row[2]),
                        )
                    )
        elif s_type == "EVENTS" or s_name == "events":
            # 6 channels: seq, source, kind, code, value, device
            if len(data.shape) == 2 and data.shape[1] >= 6:
                for i in range(len(data)):
                    row = data[i]
                    t_ns = round(ts[i] * 1e9) if i < len(ts) else 0
                    events.append(
                        InputEvent(
                            seq=int(row[0]),
                            t_host_ns=t_ns,
                            source=InputSourceKind(int(row[1])),
                            kind=InputKind(int(row[2])),
                            code=int(row[3]),
                            value=float(row[4]),
                            device=int(row[5]),
                        )
                    )
        else:
            # Signal stream (EEG, AUX, etc.)
            channel_names: list[str] = []
            channel_units: list[str] = []
            with contextlib.suppress(IndexError, KeyError, TypeError):
                desc = info.get("desc", [{}])[0]
                channels_desc = desc.get("channels", [{}])[0].get("channel", [])
                for ch in channels_desc:
                    channel_names.append(str(ch.get("name", ["ch"])[0]))
                    channel_units.append(str(ch.get("unit", ["uV"])[0]))

            n_channels = data.shape[1] if len(data.shape) == 2 else 0
            if not channel_names or len(channel_names) != n_channels:
                channel_names = [f"ch_{i + 1:02d}" for i in range(n_channels)]
            if not channel_units or len(channel_units) != n_channels:
                channel_units = ["uV"] * n_channels

            signal_streams.append(
                ExportSignalStream(
                    name=s_name,
                    stream_type=s_type,
                    nominal_srate=nominal_srate,
                    channel_names=channel_names,
                    channel_units=channel_units,
                    timestamps_s=ts,
                    data=data,
                )
            )

    return ParsedSession(
        session_id=session_id,
        signals=signal_streams,
        events=events,
        anchors=anchors,
        sidecar=sidecar,
    )
