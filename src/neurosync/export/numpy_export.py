"""NumPy (.npz) offline exporter for recorded XDF sessions (phase F7).

Saves signal arrays, timestamps, channel descriptions, and event tables in a .npz archive.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from neurosync.export.reader import load_session
from neurosync.export.session import ParsedSession


def export_session_to_npz(
    session_or_path: ParsedSession | Path | str,
    output_path: Path | str,
) -> Path:
    """Export session arrays and metadata into a compressed NumPy .npz archive.

    Args:
        session_or_path: ParsedSession or path to .xdf file.
        output_path: Target .npz file path.

    Returns:
        Path to generated .npz file.
    """
    session = (
        load_session(session_or_path)
        if not isinstance(session_or_path, ParsedSession)
        else session_or_path
    )
    out_file = Path(output_path)
    if not str(out_file).lower().endswith(".npz"):
        out_file = out_file.with_suffix(".npz")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    arrays: dict[str, Any] = {
        "session_id": session.session_id,
    }

    # Store each signal stream
    stream_names: list[str] = []
    for sig in session.signals:
        stream_names.append(sig.name)
        arrays[f"{sig.name}_data"] = sig.data
        arrays[f"{sig.name}_timestamps_s"] = sig.timestamps_s
        arrays[f"{sig.name}_channel_names"] = np.array(sig.channel_names, dtype=object)
        arrays[f"{sig.name}_nominal_srate"] = sig.nominal_srate

    arrays["stream_names"] = np.array(stream_names, dtype=object)

    # Store events
    if session.events:
        ev_matrix = np.zeros((len(session.events), 6), dtype=np.float64)
        for i, ev in enumerate(session.events):
            ev_matrix[i] = [
                float(ev.seq),
                float(ev.source),
                float(ev.kind),
                float(ev.code),
                float(ev.value),
                float(ev.device),
            ]
        arrays["events_matrix"] = ev_matrix
        arrays["events_timestamps_ns"] = np.array(
            [ev.t_host_ns for ev in session.events], dtype=np.int64
        )

    # Store sidecar metadata if available
    if session.sidecar is not None:
        arrays["sidecar_json"] = session.sidecar.to_json()

    np.savez_compressed(out_file, **arrays)
    return out_file
