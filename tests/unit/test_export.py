"""Unit tests for offline export facilities (phase F7)."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest

from neurosync.acquisition.simulated import SimSpec, Sine, render
from neurosync.core.anchors import ClockAnchor
from neurosync.core.bus import EventBus
from neurosync.core.clock import PerfCounterClock
from neurosync.core.model import ChannelInfo, ChannelKind, InputEvent, SampleChunk, StreamInfo
from neurosync.core.ring import SignalRing
from neurosync.export.bids import export_session_to_bids
from neurosync.export.csv import export_session_to_csv
from neurosync.export.edf import export_session_to_edf
from neurosync.export.manager import ExportFormat, ExportManager
from neurosync.export.numpy_export import export_session_to_npz
from neurosync.export.reader import load_session
from neurosync.input.markers import MarkerSource
from neurosync.recording.recorder import Recorder


@pytest.fixture
def recorded_xdf_fixture(tmp_path: Path) -> Path:
    """Generate a realistic test XDF session with 4 EEG channels and input events."""
    clock = PerfCounterClock()
    spec = SimSpec(signals=(Sine(10.0), Sine(20.0)), fs=250.0, n_channels=4)
    info = StreamInfo(
        stream_id="primary",
        source="synthetic",
        nominal_fs=250.0,
        channels=(
            ChannelInfo(name="Fp1", kind=ChannelKind.EEG, unit="uV"),
            ChannelInfo(name="Fp2", kind=ChannelKind.EEG, unit="uV"),
            ChannelInfo(name="C3", kind=ChannelKind.EEG, unit="uV"),
            ChannelInfo(name="C4", kind=ChannelKind.EEG, unit="uV"),
        ),
    )
    ring = SignalRing(info, capacity=2000)

    bus: EventBus[InputEvent] = EventBus()
    xdf_path = tmp_path / "sample_recording.xdf"

    anchor = ClockAnchor(
        mono_ns=clock.now_ns(),
        unix_ns=1700000000_000000000,
        uncertainty_ns=40,
    )

    recorder = Recorder(
        path=xdf_path,
        clock=clock,
        rings=[ring],
        bus=bus,
        initial_anchor=anchor,
        session_id="test_session_42",
        batch_interval_s=0.01,
        fsync_interval_s=0.05,
    )

    # Produce some signal data
    recorder.start()
    data = render(spec, 0, 250)
    chunk = SampleChunk(stream_id="primary", seq0=0, data=data, t_host_ns=clock.now_ns())
    ring.write(chunk)

    # Emit some markers and input events
    marker = MarkerSource()
    marker.push(bus, clock, marker_code=101, value=1.0)
    marker.push(bus, clock, marker_code=102, value=2.0)

    # Let recorder process the batch
    recorder.stop(timeout_s=2.0)
    return xdf_path


def test_load_session(recorded_xdf_fixture: Path) -> None:
    session = load_session(recorded_xdf_fixture)
    assert session.session_id == "test_session_42"
    assert len(session.signals) >= 1
    sig = session.signals[0]
    assert sig.sample_count == 250
    assert sig.channel_count == 4
    assert sig.nominal_srate == 250.0
    assert len(session.events) == 2
    assert session.events[0].code == 101
    assert session.events[1].code == 102
    assert session.sidecar is not None
    assert session.sidecar.session_id == "test_session_42"


def test_export_to_csv(recorded_xdf_fixture: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "csv_out"
    files = export_session_to_csv(recorded_xdf_fixture, out_dir)
    assert len(files) == 3  # Primary signal CSV + Primary Aux CSV + Events CSV

    sig_csv = next(f for f in files if f.name.endswith("_primary.csv"))
    events_csv = next(f for f in files if "events" in f.name)

    # Inspect signal CSV
    lines = sig_csv.read_text(encoding="utf-8").splitlines()
    header_comments = [line for line in lines if line.startswith("#")]
    assert any("sample_count=250" in c for c in header_comments)
    assert any("nominal_srate=250.0" in c for c in header_comments)

    data_rows = [line for line in lines if not line.startswith("#")]
    assert len(data_rows) == 251  # 1 column header + 250 data rows

    # Inspect events CSV
    ev_lines = events_csv.read_text(encoding="utf-8").splitlines()
    ev_data_rows = [line for line in ev_lines if not line.startswith("#")]
    assert len(ev_data_rows) == 3  # 1 header + 2 events
    assert "101" in ev_data_rows[1]
    assert "102" in ev_data_rows[2]


def test_export_to_edf(recorded_xdf_fixture: Path, tmp_path: Path) -> None:
    edf_path = tmp_path / "exported.edf"
    res = export_session_to_edf(recorded_xdf_fixture, edf_path)
    assert res == edf_path
    assert edf_path.is_file()

    # Verify binary EDF+ structure
    with edf_path.open("rb") as f:
        version = f.read(8).decode("ascii").strip()
        assert version == "0"
        patient = f.read(80).decode("ascii")
        assert "test_session_42" in patient
        rec_id = f.read(80).decode("ascii")
        assert "NeuroSync_v2" in rec_id
        startdate = f.read(8).decode("ascii")
        assert "." in startdate
        starttime = f.read(8).decode("ascii")
        assert "." in starttime
        header_bytes = int(f.read(8).decode("ascii").strip())
        reserved = f.read(44).decode("ascii").strip()
        assert reserved == "EDF+C"
        n_records = int(f.read(8).decode("ascii").strip())
        assert n_records == 1  # 250 samples at 250Hz = 1 record of 1 sec
        dur = float(f.read(8).decode("ascii").strip())
        assert dur == 1.0
        num_signals = int(f.read(4).decode("ascii").strip())
        assert num_signals == 5  # 4 EEG channels + 1 EDF Annotations

        # Verify header byte size matches formula (num_signals + 1) * 256
        assert header_bytes == (num_signals + 1) * 256

        # Check channel labels
        labels = [f.read(16).decode("ascii").strip() for _ in range(num_signals)]
        assert labels[-1] == "EDF Annotations"


def test_export_to_bids(recorded_xdf_fixture: Path, tmp_path: Path) -> None:
    bids_root = tmp_path / "bids_dataset"
    eeg_dir = export_session_to_bids(
        recorded_xdf_fixture,
        bids_root,
        subject_id="02",
        session_id="baseline",
        task_id="rest",
    )
    assert eeg_dir.is_dir()
    assert (bids_root / "dataset_description.json").is_file()

    # Check files in sub-02/ses-baseline/eeg/
    prefix = "sub-02_ses-baseline_task-rest"
    assert (eeg_dir / f"{prefix}_eeg.edf").is_file()
    assert (eeg_dir / f"{prefix}_eeg.json").is_file()
    assert (eeg_dir / f"{prefix}_channels.tsv").is_file()
    assert (eeg_dir / f"{prefix}_events.tsv").is_file()
    assert (eeg_dir / f"{prefix}_events.json").is_file()

    # Validate _channels.tsv content
    with (eeg_dir / f"{prefix}_channels.tsv").open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        rows = list(reader)
        assert rows[0] == ["name", "type", "units", "status"]
        assert len(rows) == 5  # header + 4 channels

    # Validate _events.tsv content
    with (eeg_dir / f"{prefix}_events.tsv").open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        rows = list(reader)
        assert rows[0] == ["onset", "duration", "trial_type", "value", "sample"]
        assert len(rows) == 3  # header + 2 events


def test_export_to_npz(recorded_xdf_fixture: Path, tmp_path: Path) -> None:
    npz_path = tmp_path / "exported.npz"
    res = export_session_to_npz(recorded_xdf_fixture, npz_path)
    assert res == npz_path
    assert npz_path.is_file()

    with np.load(npz_path, allow_pickle=True) as data:
        assert "session_id" in data
        assert str(data["session_id"]) == "test_session_42"
        stream_names = data["stream_names"].tolist()
        assert len(stream_names) >= 1
        first_stream = stream_names[0]
        sig_data = data[f"{first_stream}_data"]
        assert sig_data.shape == (250, 4)
        assert "events_matrix" in data
        assert data["events_matrix"].shape == (2, 6)


def test_export_manager(recorded_xdf_fixture: Path, tmp_path: Path) -> None:
    mgr = ExportManager(recorded_xdf_fixture)
    out_dir = tmp_path / "all_exports"
    results = mgr.export(ExportFormat.ALL, out_dir, subject_id="03", task_id="oddball")

    assert "csv" in results
    assert "edf" in results
    assert "bids" in results
    assert "npz" in results

    assert len(results["csv"]) >= 1
    assert results["edf"][0].is_file()
    assert results["bids"][0].is_dir()
    assert results["npz"][0].is_file()
