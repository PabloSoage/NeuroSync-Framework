"""XDF file writer conforming to the XDF 1.0 specification (phase F4).

Validated against pyxdf reference reader. Supports:
- FileHeader (Tag 1)
- StreamHeader (Tag 2)
- Samples (Tag 3) with fast vectorized NumPy structured array layout
- ClockOffset (Tag 4)
- Boundary (Tag 5)
- StreamFooter (Tag 6)
"""

from __future__ import annotations

import contextlib
import io
import os
import struct
from collections.abc import Sequence
from pathlib import Path
from typing import Any, BinaryIO
from xml.sax.saxutils import escape

import numpy as np
import numpy.typing as npt

from neurosync.core.model import ChannelInfo

#: 16-byte magic boundary signature defined by XDF specification
BOUNDARY_UUID = bytes(
    [
        0x43,
        0xA5,
        0x46,
        0xDC,
        0xCB,
        0xF5,
        0x41,
        0x0F,
        0xB3,
        0x0E,
        0xD5,
        0x46,
        0x73,
        0x83,
        0xCB,
        0xE4,
    ]
)

#: Format mapping from numpy dtype string to XDF channel format
FORMAT_MAP = {
    "float64": "double64",
    "double64": "double64",
    "float32": "float32",
    "int64": "int64",
    "int32": "int32",
    "int16": "int16",
    "int8": "int8",
    "string": "string",
}


def encode_varlen_int(val: int) -> bytes:
    """Encode an integer into variable-length XDF format."""
    if val < 0:
        raise ValueError("variable length int cannot be negative")
    if val < 256:
        return b"\x01" + struct.pack("<B", val)
    if val < 2**32:
        return b"\x04" + struct.pack("<I", val)
    return b"\x08" + struct.pack("<Q", val)


class XdfWriter:
    """Streaming writer for Extensible Data Format (XDF) files."""

    def __init__(self, target: BinaryIO | Path | str) -> None:
        """Create writer and initialize XDF container with magic bytes and FileHeader.

        Args:
            target: file-like binary stream or path to write to.
        """
        self._owns_file = False
        if isinstance(target, (str, Path)):
            p = Path(target)
            p.parent.mkdir(parents=True, exist_ok=True)
            self._file: BinaryIO = open(p, "wb")  # noqa: SIM115
            self._owns_file = True
        else:
            self._file = target

        # Write magic bytes
        self._file.write(b"XDF:")
        self.write_file_header()

    @property
    def file(self) -> BinaryIO:
        """Underlying binary stream."""
        return self._file

    def write_boundary(self) -> None:
        """Write a 16-byte boundary chunk (tag 5) for recovery from stream corruption."""
        chunklen = 2 + len(BOUNDARY_UUID)
        self._file.write(encode_varlen_int(chunklen))
        self._file.write(struct.pack("<H", 5))
        self._file.write(BOUNDARY_UUID)

    def write_file_header(
        self, version: str = "1.0", metadata: dict[str, str] | None = None
    ) -> None:
        """Write FileHeader chunk (tag 1)."""
        xml_parts = [f"<info><version>{escape(version)}</version>"]
        if metadata:
            for k, v in metadata.items():
                xml_parts.append(f"<{escape(k)}>{escape(str(v))}</{escape(k)}>")
        xml_parts.append("</info>")
        xml_bytes = "".join(xml_parts).encode("utf-8")

        chunklen = 2 + len(xml_bytes)
        self._file.write(encode_varlen_int(chunklen))
        self._file.write(struct.pack("<H", 1))
        self._file.write(xml_bytes)

    def write_stream_header(
        self,
        stream_id: int,
        name: str,
        type: str,
        channel_count: int,
        nominal_srate: float,
        channel_format: str,
        *,
        created_at: str | None = None,
        channels: Sequence[ChannelInfo] | Sequence[str] | None = None,
        metadata: Sequence[tuple[str, str]] | dict[str, str] | None = None,
    ) -> None:
        """Write StreamHeader chunk (tag 2)."""
        fmt = FORMAT_MAP.get(channel_format, channel_format)
        xml_parts = [
            "<info>",
            f"<name>{escape(name)}</name>",
            f"<type>{escape(type)}</type>",
            f"<channel_count>{channel_count}</channel_count>",
            f"<nominal_srate>{nominal_srate:.6f}</nominal_srate>",
            f"<channel_format>{escape(fmt)}</channel_format>",
        ]
        if created_at is not None:
            xml_parts.append(f"<created_at>{escape(created_at)}</created_at>")

        if channels or metadata:
            xml_parts.append("<desc>")
            if channels:
                xml_parts.append("<channels>")
                for ch in channels:
                    if isinstance(ch, ChannelInfo):
                        ch_name = ch.name
                        ch_unit = ch.unit
                        ch_type = ch.kind.value
                    else:
                        ch_name = str(ch)
                        ch_unit = ""
                        ch_type = type
                    xml_parts.append(
                        f"<channel><label>{escape(ch_name)}</label><unit>{escape(ch_unit)}</unit><type>{escape(ch_type)}</type></channel>"
                    )
                xml_parts.append("</channels>")
            if metadata:
                items = metadata.items() if isinstance(metadata, dict) else metadata
                for k, v in items:
                    xml_parts.append(f"<{escape(k)}>{escape(str(v))}</{escape(k)}>")
            xml_parts.append("</desc>")

        xml_parts.append("</info>")
        xml_bytes = "".join(xml_parts).encode("utf-8")

        chunklen = 2 + 4 + len(xml_bytes)
        self._file.write(encode_varlen_int(chunklen))
        self._file.write(struct.pack("<HI", 2, stream_id))
        self._file.write(xml_bytes)

    def write_samples_numeric(
        self,
        stream_id: int,
        timestamps_s: npt.NDArray[np.float64],
        data: npt.NDArray[np.floating[Any]],
    ) -> None:
        """Write numeric samples chunk (tag 3).

        Args:
            stream_id: target stream ID.
            timestamps_s: 1D array of sample timestamps in seconds.
            data: array of shape (n_channels, n_samples).
        """
        n_samples = len(timestamps_s)
        if n_samples == 0:
            return

        if data.ndim != 2:
            raise ValueError(f"expected data with shape (n_channels, n_samples), got {data.shape}")
        n_channels = data.shape[0]
        if data.shape[1] != n_samples:
            raise ValueError(
                f"sample count mismatch: timestamps have {n_samples}, data has {data.shape[1]}"
            )

        dtype_le = np.dtype(data.dtype).newbyteorder("<")
        # Pack each sample: flag byte (8 for double timestamp), ts (<f8), values
        rec = np.empty(
            n_samples,
            dtype=[("flag", "u1"), ("ts", "<f8"), ("vals", dtype_le, (n_channels,))],
        )
        rec["flag"] = 8
        rec["ts"] = timestamps_s
        rec["vals"] = data.T

        sample_bytes = rec.tobytes()
        varlen_ns = encode_varlen_int(n_samples)
        chunklen = 2 + 4 + len(varlen_ns) + len(sample_bytes)

        self._file.write(encode_varlen_int(chunklen))
        self._file.write(struct.pack("<HI", 3, stream_id))
        self._file.write(varlen_ns)
        self._file.write(sample_bytes)

    def write_samples_strings(
        self,
        stream_id: int,
        timestamps_s: Sequence[float] | npt.NDArray[np.float64],
        strings: Sequence[Sequence[str]],
    ) -> None:
        """Write string samples chunk (tag 3)."""
        n_samples = len(timestamps_s)
        if n_samples == 0:
            return
        if len(strings) != n_samples:
            raise ValueError(f"mismatch: {n_samples} timestamps, {len(strings)} rows")

        buf = io.BytesIO()
        for ts, row in zip(timestamps_s, strings, strict=True):
            buf.write(b"\x08")
            buf.write(struct.pack("<d", float(ts)))
            for item in row:
                raw = item.encode("utf-8")
                buf.write(encode_varlen_int(len(raw)))
                buf.write(raw)

        payload = buf.getvalue()
        varlen_ns = encode_varlen_int(n_samples)
        chunklen = 2 + 4 + len(varlen_ns) + len(payload)

        self._file.write(encode_varlen_int(chunklen))
        self._file.write(struct.pack("<HI", 3, stream_id))
        self._file.write(varlen_ns)
        self._file.write(payload)

    def write_clock_offset(
        self,
        stream_id: int,
        clock_time_s: float,
        offset_s: float = 0.0,
    ) -> None:
        """Write ClockOffset chunk (tag 4)."""
        chunklen = 2 + 4 + 8 + 8
        self._file.write(encode_varlen_int(chunklen))
        self._file.write(struct.pack("<HIdd", 4, stream_id, float(clock_time_s), float(offset_s)))

    def write_stream_footer(
        self,
        stream_id: int,
        first_timestamp: float | None = None,
        last_timestamp: float | None = None,
        sample_count: int = 0,
        stats: dict[str, Any] | None = None,
    ) -> None:
        """Write StreamFooter chunk (tag 6)."""
        ts0_str = f"{first_timestamp:.6f}" if first_timestamp is not None else "0.000000"
        ts1_str = f"{last_timestamp:.6f}" if last_timestamp is not None else "0.000000"
        xml_parts = [
            "<info>",
            f"<first_timestamp>{ts0_str}</first_timestamp>",
            f"<last_timestamp>{ts1_str}</last_timestamp>",
            f"<sample_count>{sample_count}</sample_count>",
        ]
        if stats:
            xml_parts.append("<stats>")
            for k, v in stats.items():
                xml_parts.append(f"<{escape(k)}>{escape(str(v))}</{escape(k)}>")
            xml_parts.append("</stats>")
        xml_parts.append("</info>")
        xml_bytes = "".join(xml_parts).encode("utf-8")

        chunklen = 2 + 4 + len(xml_bytes)
        self._file.write(encode_varlen_int(chunklen))
        self._file.write(struct.pack("<HI", 6, stream_id))
        self._file.write(xml_bytes)

    def flush(self) -> None:
        """Flush user-space buffers to OS."""
        self._file.flush()

    def fsync(self) -> None:
        """Force OS to commit writes to disk."""
        self.flush()
        with contextlib.suppress(AttributeError, io.UnsupportedOperation, OSError):
            os.fsync(self._file.fileno())

    def close(self) -> None:
        """Flush and close underlying file if owned."""
        self.flush()
        if self._owns_file:
            self._file.close()

    def __enter__(self) -> XdfWriter:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
