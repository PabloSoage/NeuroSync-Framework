"""EDF+ (European Data Format) offline exporter (phase F7).

Compliant with Kemp & Olivan (2003) EDF+ standard.
Writes standard multi-channel EEG signals and embedded Time-stamped Annotation Lists (TALs).
Zero external C dependencies (pure Python with NumPy).
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

import numpy as np

from neurosync.core.errors import InvalidInput
from neurosync.export.reader import load_session
from neurosync.export.session import ParsedSession


def _format_ascii(val: Any, length: int) -> bytes:
    """Format a value as left-aligned ASCII bytes padded with spaces to exact length."""
    s = str(val)[:length]
    return s.ljust(length).encode("ascii", errors="replace")


def export_session_to_edf(
    session_or_path: ParsedSession | Path | str,
    output_path: Path | str,
    *,
    stream_name: str | None = None,
    record_duration_s: float = 1.0,
) -> Path:
    """Export continuous signal stream and events to a standard EDF+ file.

    Args:
        session_or_path: Either a ParsedSession or path to .xdf file.
        output_path: Destination .edf file path.
        stream_name: Optional signal stream to export (defaults to first stream).
        record_duration_s: Duration of each EDF data record in seconds (default 1.0s).

    Returns:
        Path to generated .edf file.
    """
    session = (
        load_session(session_or_path)
        if not isinstance(session_or_path, ParsedSession)
        else session_or_path
    )
    stream = session.get_signal(stream_name)
    if stream is None:
        raise InvalidInput("Session has no continuous signal streams to export to EDF+")

    out_file = Path(output_path)
    if not str(out_file).lower().endswith(".edf"):
        out_file = out_file.with_suffix(".edf")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    n_samples = stream.sample_count
    fs = stream.nominal_srate if stream.nominal_srate > 0 else 250.0
    samples_per_record = max(1, round(fs * record_duration_s))
    n_records = max(1, int(np.ceil(n_samples / samples_per_record)))

    # Pad data if necessary to fit exact record boundaries
    total_samples_needed = n_records * samples_per_record
    n_ch = stream.channel_count
    if n_samples < total_samples_needed:
        pad_len = total_samples_needed - n_samples
        pad = np.zeros((pad_len, n_ch), dtype=np.float64)
        if n_samples > 0:
            pad[:] = stream.data[-1:]
        data_matrix = np.vstack([stream.data, pad])
    else:
        data_matrix = stream.data[:total_samples_needed]

    # Calculate physical min/max per channel
    d_min = -32768
    d_max = 32767
    p_mins: list[float] = []
    p_maxs: list[float] = []
    for c in range(n_ch):
        col = data_matrix[:, c]
        mn = float(np.min(col))
        mx = float(np.max(col))
        if abs(mx - mn) < 1e-6:
            mn -= 1.0
            mx += 1.0
        p_mins.append(mn)
        p_maxs.append(mx)

    # Number of signals in EDF+: signal channels + 1 EDF Annotations channel
    num_signals = n_ch + 1
    header_bytes = (num_signals + 1) * 256

    # Timestamps & Date
    now = datetime.datetime.now(datetime.UTC)
    date_str = now.strftime("%d.%m.%y")
    time_str = now.strftime("%H.%M.%S")
    startdate_sub = now.strftime("%d-%b-%Y").upper()

    patient_id = f"X X X {session.session_id}"
    recording_id = f"Startdate {startdate_sub} NeuroSync_v2"

    annotation_samples_per_record = 120  # 240 bytes for TAL per record

    with out_file.open("wb") as f:
        # --- Main Header (256 bytes) ---
        f.write(_format_ascii("0", 8))
        f.write(_format_ascii(patient_id, 80))
        f.write(_format_ascii(recording_id, 80))
        f.write(_format_ascii(date_str, 8))
        f.write(_format_ascii(time_str, 8))
        f.write(_format_ascii(header_bytes, 8))
        f.write(_format_ascii("EDF+C", 44))
        f.write(_format_ascii(n_records, 8))
        f.write(_format_ascii(f"{record_duration_s:.6g}", 8))
        f.write(_format_ascii(num_signals, 4))

        # --- Channel Headers (num_signals * 256 bytes) ---
        # 1. Labels (16 * num_signals)
        for name in stream.channel_names:
            lbl = f"EEG {name}" if not name.startswith("EEG") else name
            f.write(_format_ascii(lbl, 16))
        f.write(_format_ascii("EDF Annotations", 16))

        # 2. Transducer type (80 * num_signals)
        for _ in range(n_ch):
            f.write(_format_ascii("Electrode", 80))
        f.write(_format_ascii("", 80))

        # 3. Physical dimension (8 * num_signals)
        for unit in stream.channel_units:
            f.write(_format_ascii(unit, 8))
        f.write(_format_ascii("", 8))

        # 4. Physical minimum (8 * num_signals)
        for p_min in p_mins:
            f.write(_format_ascii(f"{p_min:.3f}", 8))
        f.write(_format_ascii("-1", 8))

        # 5. Physical maximum (8 * num_signals)
        for p_max in p_maxs:
            f.write(_format_ascii(f"{p_max:.3f}", 8))
        f.write(_format_ascii("1", 8))

        # 6. Digital minimum (8 * num_signals)
        for _ in range(n_ch):
            f.write(_format_ascii(d_min, 8))
        f.write(_format_ascii(d_min, 8))

        # 7. Digital maximum (8 * num_signals)
        for _ in range(n_ch):
            f.write(_format_ascii(d_max, 8))
        f.write(_format_ascii(d_max, 8))

        # 8. Prefiltering (80 * num_signals)
        for _ in range(n_ch):
            f.write(_format_ascii("HP:0.1Hz LP:100Hz", 80))
        f.write(_format_ascii("", 80))

        # 9. Number of samples per record (8 * num_signals)
        for _ in range(n_ch):
            f.write(_format_ascii(samples_per_record, 8))
        f.write(_format_ascii(annotation_samples_per_record, 8))

        # 10. Reserved (32 * num_signals)
        for _ in range(num_signals):
            f.write(_format_ascii("", 32))

        # --- Data Records ---
        t0_s = float(stream.timestamps_s[0]) if len(stream.timestamps_s) > 0 else 0.0

        # Group events by record
        events_by_record: dict[int, list[tuple[float, str]]] = {}
        for ev in session.events:
            ev_t_s = ev.t_host_ns * 1e-9
            rel_t_s = max(0.0, ev_t_s - t0_s)
            rec_idx = int(rel_t_s // record_duration_s)
            if 0 <= rec_idx < n_records:
                desc = f"{ev.kind.name}_{ev.code}"
                events_by_record.setdefault(rec_idx, []).append((rel_t_s, desc))

        tal_bytes_per_record = annotation_samples_per_record * 2

        for r in range(n_records):
            idx_start = r * samples_per_record
            idx_end = idx_start + samples_per_record

            # Write signal channels
            for c in range(n_ch):
                col = data_matrix[idx_start:idx_end, c]
                mn = p_mins[c]
                mx = p_maxs[c]
                # Scale to digital int16
                scaled = (col - mn) / (mx - mn) * (d_max - d_min) + d_min
                digital = np.clip(np.round(scaled), d_min, d_max).astype("<i2")
                f.write(digital.tobytes())

            # Write EDF Annotations (TALs)
            # Time stamp of this data record
            tal_chunks = [f"+{record_duration_s * r:.6f}\x14\x14\x00".encode("ascii")]

            for ev_onset, ev_desc in events_by_record.get(r, []):
                tal_chunks.append(f"+{ev_onset:.6f}\x14{ev_desc}\x14\x00".encode("ascii"))

            tal_bytes = b"".join(tal_chunks)
            if len(tal_bytes) > tal_bytes_per_record:
                tal_bytes = tal_bytes[:tal_bytes_per_record]
            else:
                tal_bytes = tal_bytes + b"\x00" * (tal_bytes_per_record - len(tal_bytes))
            f.write(tal_bytes)

    return out_file
