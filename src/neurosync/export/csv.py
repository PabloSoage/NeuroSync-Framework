"""Offline CSV exporter for recorded XDF sessions (phase F7).

Exports continuous signal streams and timestamped events into universal, clean CSV files.
"""

from __future__ import annotations

import csv
from pathlib import Path

from neurosync.export.reader import load_session
from neurosync.export.session import ParsedSession


def export_session_to_csv(
    session_or_path: ParsedSession | Path | str,
    output_dir: Path | str,
    *,
    prefix: str | None = None,
) -> list[Path]:
    """Export all streams and events of a session into CSV files in output_dir.

    Args:
        session_or_path: Either an already loaded ParsedSession or path to .xdf file.
        output_dir: Directory where CSV files will be written.
        prefix: Optional prefix for generated filenames (defaults to session_id).

    Returns:
        List of paths to generated CSV files.
    """
    session = (
        load_session(session_or_path)
        if not isinstance(session_or_path, ParsedSession)
        else session_or_path
    )
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    file_prefix = prefix or session.session_id
    generated_files: list[Path] = []

    # 1. Export each continuous signal stream
    for sig in session.signals:
        stream_path = out_dir / f"{file_prefix}_{sig.name}.csv"
        with stream_path.open("w", newline="", encoding="utf-8") as f:
            # Metadata comments
            f.write("# neurosync_version=2.0\n")
            f.write(f"# session_id={session.session_id}\n")
            f.write(f"# stream_name={sig.name}\n")
            f.write(f"# stream_type={sig.stream_type}\n")
            f.write(f"# nominal_srate={sig.nominal_srate}\n")
            f.write(f"# sample_count={sig.sample_count}\n")
            f.write(f"# channel_count={sig.channel_count}\n")

            writer = csv.writer(f)
            header = ["time_s", "mono_ns", *sig.channel_names]
            writer.writerow(header)

            for i in range(sig.sample_count):
                t_s = float(sig.timestamps_s[i])
                mono_ns = round(t_s * 1e9)
                row: list[str | float | int] = [f"{t_s:.6f}", mono_ns]
                row.extend(sig.data[i].tolist())
                writer.writerow(row)

        generated_files.append(stream_path)

    # 2. Export events if present
    if session.events:
        events_path = out_dir / f"{file_prefix}_events.csv"
        with events_path.open("w", newline="", encoding="utf-8") as f:
            f.write("# neurosync_version=2.0\n")
            f.write(f"# session_id={session.session_id}\n")
            f.write(f"# event_count={len(session.events)}\n")

            writer = csv.writer(f)
            writer.writerow(
                ["time_s", "mono_ns", "seq", "source", "kind", "code", "value", "device"]
            )
            for ev in session.events:
                t_s = ev.t_host_ns * 1e-9
                writer.writerow(
                    [
                        f"{t_s:.6f}",
                        ev.t_host_ns,
                        ev.seq,
                        ev.source.name,
                        ev.kind.name,
                        ev.code,
                        ev.value,
                        ev.device,
                    ]
                )
        generated_files.append(events_path)

    return generated_files
