"""Unit tests for low-level XdfWriter (phase F4)."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
import pyxdf

from neurosync.core.model import ChannelInfo, ChannelKind
from neurosync.recording.xdf_writer import XdfWriter


def test_xdf_writer_empty(tmp_path: Path) -> None:
    path = tmp_path / "empty.xdf"
    writer = XdfWriter(path)
    writer.close()

    streams, header = pyxdf.load_xdf(str(path))
    assert len(streams) == 0
    assert header is not None
    assert "info" in header
    assert header["info"]["version"][0] == "1.0"


def test_xdf_writer_numeric_stream(tmp_path: Path) -> None:
    path = tmp_path / "numeric.xdf"
    channels = (
        ChannelInfo(name="Fz", kind=ChannelKind.EEG, unit="uV"),
        ChannelInfo(name="Cz", kind=ChannelKind.EEG, unit="uV"),
    )
    with XdfWriter(path) as writer:
        writer.write_stream_header(
            stream_id=1,
            name="EEG_Stream",
            type="EEG",
            channel_count=2,
            nominal_srate=250.0,
            channel_format="double64",
            channels=channels,
        )
        writer.write_clock_offset(stream_id=1, clock_time_s=10.0, offset_s=0.0)

        n_samples = 100
        ts = 10.0 + np.arange(n_samples, dtype=np.float64) / 250.0
        data = np.zeros((2, n_samples), dtype=np.float64)
        data[0, :] = np.sin(2 * np.pi * 10.0 * ts)
        data[1, :] = np.cos(2 * np.pi * 10.0 * ts)

        writer.write_samples_numeric(stream_id=1, timestamps_s=ts, data=data)
        writer.write_clock_offset(stream_id=1, clock_time_s=ts[-1], offset_s=0.0)
        writer.write_stream_footer(
            stream_id=1,
            first_timestamp=float(ts[0]),
            last_timestamp=float(ts[-1]),
            sample_count=n_samples,
        )

    streams, _header = pyxdf.load_xdf(str(path))
    assert len(streams) == 1
    s = streams[0]
    assert s["info"]["name"][0] == "EEG_Stream"
    assert s["info"]["type"][0] == "EEG"
    assert int(s["info"]["channel_count"][0]) == 2
    assert float(s["info"]["nominal_srate"][0]) == 250.0

    assert len(s["time_stamps"]) == n_samples
    assert np.allclose(s["time_stamps"], ts)
    assert s["time_series"].shape == (n_samples, 2)
    assert np.allclose(s["time_series"].T, data)


def test_xdf_writer_string_stream(tmp_path: Path) -> None:
    path = tmp_path / "strings.xdf"
    with XdfWriter(path) as writer:
        writer.write_stream_header(
            stream_id=2,
            name="Markers",
            type="Markers",
            channel_count=1,
            nominal_srate=0.0,
            channel_format="string",
        )
        writer.write_clock_offset(stream_id=2, clock_time_s=1.0, offset_s=0.0)

        ts = [1.0, 2.5, 3.8]
        rows = [["start"], ["target_appear"], ["response_press"]]
        writer.write_samples_strings(stream_id=2, timestamps_s=ts, strings=rows)
        writer.write_clock_offset(stream_id=2, clock_time_s=3.8, offset_s=0.0)
        writer.write_stream_footer(stream_id=2, sample_count=3)

    streams, _ = pyxdf.load_xdf(str(path))
    assert len(streams) == 1
    s = streams[0]
    assert s["info"]["name"][0] == "Markers"
    assert len(s["time_stamps"]) == 3
    assert np.allclose(s["time_stamps"], ts)
    assert s["time_series"] == [["start"], ["target_appear"], ["response_press"]]


def test_xdf_writer_boundary_and_validation() -> None:
    buf = io.BytesIO()
    writer = XdfWriter(buf)
    writer.write_boundary()
    writer.flush()
    # Ensure boundary chunk written to stream
    assert len(buf.getvalue()) > 20

    # Test dimension validation
    with pytest.raises(ValueError, match="expected data with shape"):
        writer.write_samples_numeric(1, np.array([1.0]), np.ones((1, 1, 1)))

    with pytest.raises(ValueError, match="sample count mismatch"):
        writer.write_samples_numeric(1, np.array([1.0, 2.0]), np.ones((1, 1)))
