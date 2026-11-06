"""BIDS (Brain Imaging Data Structure) offline exporter (phase F7).

Exports synchronized EEG recordings and behavioral events into full BIDS 1.9+ structure:
- dataset_description.json
- sub-<subject_id>/[ses-<session_id>/]eeg/
  - sub-<subject_id>_task-<task_id>_eeg.edf
  - sub-<subject_id>_task-<task_id>_eeg.json
  - sub-<subject_id>_task-<task_id>_channels.tsv
  - sub-<subject_id>_task-<task_id>_events.tsv
  - sub-<subject_id>_task-<task_id>_events.json
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from neurosync.core.errors import InvalidInput
from neurosync.export.edf import export_session_to_edf
from neurosync.export.reader import load_session
from neurosync.export.session import ParsedSession


def export_session_to_bids(
    session_or_path: ParsedSession | Path | str,
    output_root: Path | str,
    *,
    subject_id: str = "01",
    task_id: str = "experiment",
    session_id: str | None = None,
    stream_name: str | None = None,
    dataset_name: str = "NeuroSync EEG Study",
) -> Path:
    """Export session to BIDS compliant directory structure.

    Args:
        session_or_path: ParsedSession or path to .xdf file.
        output_root: Target BIDS root directory.
        subject_id: Subject label (without 'sub-').
        task_id: Task name (without 'task-').
        session_id: Optional session label (without 'ses-').
        stream_name: Optional signal stream to export.
        dataset_name: Dataset name for dataset_description.json.

    Returns:
        Path to the generated EEG modality folder.
    """
    session = (
        load_session(session_or_path)
        if not isinstance(session_or_path, ParsedSession)
        else session_or_path
    )
    sig = session.get_signal(stream_name)
    if sig is None:
        raise InvalidInput("Session has no continuous signal streams to export to BIDS")

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)

    # 1. dataset_description.json
    desc_path = root / "dataset_description.json"
    if not desc_path.exists():
        desc_data: dict[str, Any] = {
            "Name": dataset_name,
            "BIDSVersion": "1.9.0",
            "DatasetType": "raw",
            "License": "CC0",
            "Authors": ["NeuroSync Framework"],
        }
        desc_path.write_text(json.dumps(desc_data, indent=2), encoding="utf-8")

    # 2. Build sub- / ses- directory
    sub_tag = f"sub-{subject_id}"
    ses_tag = f"ses-{session_id}" if session_id else ""
    task_tag = f"task-{task_id}"

    eeg_dir = root / sub_tag / ses_tag / "eeg" if ses_tag else root / sub_tag / "eeg"
    eeg_dir.mkdir(parents=True, exist_ok=True)

    base_prefix = f"{sub_tag}_{ses_tag}_{task_tag}" if ses_tag else f"{sub_tag}_{task_tag}"

    # 3. Export EDF+ file
    edf_filename = f"{base_prefix}_eeg.edf"
    edf_path = eeg_dir / edf_filename
    export_session_to_edf(session, edf_path, stream_name=stream_name)

    # 4. Export sidecar _eeg.json
    sidecar_data: dict[str, Any] = {
        "TaskName": task_id,
        "SamplingFrequency": sig.nominal_srate,
        "EEGChannelCount": sig.channel_count,
        "RecordingType": "continuous",
        "PowerLineFrequency": 50.0,
        "EEGReference": "common",
        "SoftwareFilters": {
            "Anti-aliasing": "none",
        },
    }
    if session.sidecar is not None and session.sidecar.clock_info is not None:
        sidecar_data["ClockImplementation"] = session.sidecar.clock_info.implementation

    (eeg_dir / f"{base_prefix}_eeg.json").write_text(
        json.dumps(sidecar_data, indent=2), encoding="utf-8"
    )

    # 5. Export _channels.tsv
    channels_tsv = eeg_dir / f"{base_prefix}_channels.tsv"
    with channels_tsv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["name", "type", "units", "status"])
        for name, unit in zip(sig.channel_names, sig.channel_units, strict=False):
            writer.writerow([name, "EEG", unit, "good"])

    # 6. Export _events.tsv and _events.json
    events_tsv = eeg_dir / f"{base_prefix}_events.tsv"
    t0_s = float(sig.timestamps_s[0]) if len(sig.timestamps_s) > 0 else 0.0

    with events_tsv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["onset", "duration", "trial_type", "value", "sample"])
        for ev in session.events:
            ev_t_s = ev.t_host_ns * 1e-9
            onset_s = max(0.0, ev_t_s - t0_s)
            sample_idx = round(onset_s * sig.nominal_srate) if sig.nominal_srate > 0 else 0
            trial_type = f"{ev.kind.name}_{ev.code}"
            writer.writerow([f"{onset_s:.6f}", "0.0", trial_type, ev.value, sample_idx])

    events_json = eeg_dir / f"{base_prefix}_events.json"
    events_meta: dict[str, Any] = {
        "onset": {"Description": "Onset time of the event from recording start", "Units": "second"},
        "duration": {"Description": "Duration of the event", "Units": "second"},
        "trial_type": {"Description": "Kind and code of input or marker event"},
        "value": {"Description": "Value associated with the event"},
        "sample": {"Description": "Sample index in the EEG stream closest to onset"},
    }
    events_json.write_text(json.dumps(events_meta, indent=2), encoding="utf-8")

    return eeg_dir
