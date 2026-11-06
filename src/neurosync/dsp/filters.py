"""Causal, stateful online filtering and offline zero-phase filters (phase F5).

Implements architectural decision D-09:
- Online filtering is strictly causal and stateful using Second-Order Sections (SOS).
- Filter state ``zi`` is maintained across chunks so chunk boundaries produce no transients.
- Filter re-configuration acts forward in time and never re-injects or modifies past samples.
- Zero-phase filtering (``sosfiltfilt``) is provided explicitly for offline export and analysis.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np
import numpy.typing as npt
from scipy import signal

from neurosync.core.errors import InvalidInput


class FilterType(StrEnum):
    """Supported digital IIR filter topologies."""

    BUTTERWORTH = "butterworth"
    CHEBYSHEV_1 = "chebyshev1"
    BESSEL = "bessel"
    ELLIPTIC = "elliptic"


class FilterBand(StrEnum):
    """Filter passband specification."""

    LOWPASS = "lowpass"
    HIGHPASS = "highpass"
    BANDPASS = "bandpass"
    BANDSTOP = "bandstop"


@dataclass(frozen=True, slots=True)
class FilterConfig:
    """Design parameters for a digital IIR filter."""

    band: FilterBand
    fs: float
    low_hz: float | None = None
    high_hz: float | None = None
    order: int = 4
    filter_type: FilterType = FilterType.BUTTERWORTH
    ripple_db: float = 0.5
    attenuation_db: float = 40.0

    def __post_init__(self) -> None:
        if self.fs <= 0:
            raise InvalidInput("Sampling rate fs must be positive")
        nyquist = self.fs / 2.0
        if self.band in (FilterBand.HIGHPASS, FilterBand.BANDPASS, FilterBand.BANDSTOP) and (
            self.low_hz is None or self.low_hz <= 0 or self.low_hz >= nyquist
        ):
            raise InvalidInput(f"low_hz must be in (0, {nyquist}) Hz")
        if self.band in (FilterBand.LOWPASS, FilterBand.BANDPASS, FilterBand.BANDSTOP) and (
            self.high_hz is None or self.high_hz <= 0 or self.high_hz >= nyquist
        ):
            raise InvalidInput(f"high_hz must be in (0, {nyquist}) Hz")
        if (
            self.band in (FilterBand.BANDPASS, FilterBand.BANDSTOP)
            and self.low_hz is not None
            and self.high_hz is not None
            and self.low_hz >= self.high_hz
        ):
            raise InvalidInput("low_hz must be strictly less than high_hz")
        if self.order < 1:
            raise InvalidInput("order must be at least 1")

    @classmethod
    def notch(
        cls, notch_hz: float = 50.0, fs: float = 250.0, bandwidth_hz: float = 2.0
    ) -> FilterConfig:
        """Create a narrow bandstop notch filter around line noise frequency."""
        return cls(
            band=FilterBand.BANDSTOP,
            fs=fs,
            low_hz=max(0.1, notch_hz - bandwidth_hz / 2.0),
            high_hz=min(fs / 2.0 - 0.1, notch_hz + bandwidth_hz / 2.0),
            order=2,
            filter_type=FilterType.BUTTERWORTH,
        )

    @classmethod
    def bandpass(
        cls,
        low_hz: float,
        high_hz: float,
        fs: float,
        order: int = 4,
        filter_type: FilterType = FilterType.BUTTERWORTH,
    ) -> FilterConfig:
        """Create a bandpass filter."""
        return cls(
            band=FilterBand.BANDPASS,
            fs=fs,
            low_hz=low_hz,
            high_hz=high_hz,
            order=order,
            filter_type=filter_type,
        )

    @classmethod
    def highpass(
        cls,
        cutoff_hz: float,
        fs: float,
        order: int = 2,
        filter_type: FilterType = FilterType.BUTTERWORTH,
    ) -> FilterConfig:
        """Create a highpass filter."""
        return cls(
            band=FilterBand.HIGHPASS,
            fs=fs,
            low_hz=cutoff_hz,
            order=order,
            filter_type=filter_type,
        )

    @classmethod
    def lowpass(
        cls,
        cutoff_hz: float,
        fs: float,
        order: int = 4,
        filter_type: FilterType = FilterType.BUTTERWORTH,
    ) -> FilterConfig:
        """Create a lowpass filter."""
        return cls(
            band=FilterBand.LOWPASS,
            fs=fs,
            high_hz=cutoff_hz,
            order=order,
            filter_type=filter_type,
        )

    def design_sos(self) -> npt.NDArray[np.float64]:
        """Compute Second-Order Sections (SOS) representation matrix."""
        nyquist = self.fs / 2.0
        ftype_map = {
            FilterType.BUTTERWORTH: "butter",
            FilterType.CHEBYSHEV_1: "cheby1",
            FilterType.BESSEL: "bessel",
            FilterType.ELLIPTIC: "ellip",
        }
        btype_map = {
            FilterBand.LOWPASS: "lowpass",
            FilterBand.HIGHPASS: "highpass",
            FilterBand.BANDPASS: "bandpass",
            FilterBand.BANDSTOP: "bandstop",
        }

        if self.band == FilterBand.LOWPASS:
            wn: float | tuple[float, float] = float(self.high_hz) / nyquist  # type: ignore[arg-type]
        elif self.band == FilterBand.HIGHPASS:
            wn = float(self.low_hz) / nyquist  # type: ignore[arg-type]
        else:
            wn = (float(self.low_hz) / nyquist, float(self.high_hz) / nyquist)  # type: ignore[arg-type]

        sos: npt.NDArray[np.float64] = signal.iirfilter(
            N=self.order,
            Wn=wn,
            rp=self.ripple_db,
            rs=self.attenuation_db,
            btype=btype_map[self.band],
            ftype=ftype_map[self.filter_type],
            output="sos",
        )
        return sos


class CausalSosFilter:
    """Stateful Second-Order Sections (SOS) IIR filter maintaining causal state."""

    def __init__(self, config: FilterConfig, n_channels: int) -> None:
        """Initialize filter for a fixed channel count."""
        if n_channels <= 0:
            raise InvalidInput("n_channels must be positive")
        self.config = config
        self.n_channels = n_channels
        self.sos = config.design_sos()
        self._zi: npt.NDArray[np.float64] | None = None
        self.reset()

    def reset(self) -> None:
        """Reset internal filter states."""
        # Initial condition template for 1 channel: shape (n_sections, 2)
        zi_single = signal.sosfilt_zi(self.sos)
        # Replicate for all channels: shape (n_channels, n_sections, 2)
        self._zi = np.zeros((self.n_channels, self.sos.shape[0], 2), dtype=np.float64)
        for ch in range(self.n_channels):
            self._zi[ch, :, :] = zi_single * 0.0

    def warm_up(self, initial_values: npt.NDArray[np.floating[Any]]) -> None:
        """Seed steady-state conditions using initial step values."""
        zi_single = signal.sosfilt_zi(self.sos)
        if self._zi is None:
            self.reset()
        assert self._zi is not None
        for ch in range(self.n_channels):
            val = (
                float(initial_values[ch])
                if initial_values.ndim == 1
                else float(initial_values[ch, 0])
            )
            self._zi[ch, :, :] = zi_single * val

    def filter_chunk(self, data: npt.NDArray[np.floating[Any]]) -> npt.NDArray[np.float64]:
        """Apply causal filtering to incoming chunk and update internal state in-place.

        Args:
            data: array of shape (n_channels, n_samples).

        Returns:
            Filtered array of shape (n_channels, n_samples).
        """
        if data.shape[0] != self.n_channels:
            raise InvalidInput(
                f"Channel count mismatch: expected {self.n_channels}, got {data.shape[0]}"
            )
        if data.shape[1] == 0:
            return np.empty_like(data, dtype=np.float64)

        if self._zi is None:
            self.reset()
        assert self._zi is not None

        out = np.empty_like(data, dtype=np.float64)
        for ch in range(self.n_channels):
            ch_data = data[ch, :]
            ch_out, self._zi[ch, :, :] = signal.sosfilt(self.sos, ch_data, zi=self._zi[ch, :, :])
            out[ch, :] = ch_out

        return out

    def filter_offline(
        self, data: npt.NDArray[np.floating[Any]], *, zero_phase: bool = False
    ) -> npt.NDArray[np.float64]:
        """Perform offline filtering on complete dataset."""
        if data.shape[0] != self.n_channels:
            raise InvalidInput(f"Channel count mismatch: {data.shape[0]} != {self.n_channels}")
        if zero_phase:
            res: npt.NDArray[np.float64] = signal.sosfiltfilt(self.sos, data, axis=-1)
            return res
        zi_single = signal.sosfilt_zi(self.sos)
        out = np.empty_like(data, dtype=np.float64)
        for ch in range(self.n_channels):
            zi = zi_single * float(data[ch, 0]) if data.shape[1] > 0 else zi_single * 0.0
            ch_out, _ = signal.sosfilt(self.sos, data[ch, :], zi=zi)
            out[ch, :] = ch_out
        return out


class FilterPipeline:
    """Sequential chain of causal filters executed in series (e.g. Notch + Bandpass)."""

    def __init__(self, filters: Sequence[CausalSosFilter]) -> None:
        if not filters:
            raise InvalidInput("FilterPipeline requires at least one filter")
        n_ch = filters[0].n_channels
        if any(f.n_channels != n_ch for f in filters):
            raise InvalidInput("All filters in pipeline must share the same n_channels")
        self.filters = list(filters)
        self.n_channels = n_ch

    def reset(self) -> None:
        """Reset internal states across all pipeline stages."""
        for f in self.filters:
            f.reset()

    def process_chunk(self, data: npt.NDArray[np.floating[Any]]) -> npt.NDArray[np.float64]:
        """Pass chunk sequentially through all filter stages."""
        current = data
        for f in self.filters:
            current = f.filter_chunk(current)
        return current.astype(np.float64)

    def process_offline(
        self, data: npt.NDArray[np.floating[Any]], *, zero_phase: bool = False
    ) -> npt.NDArray[np.float64]:
        """Pass full dataset through all stages offline."""
        current = data
        for f in self.filters:
            current = f.filter_offline(current, zero_phase=zero_phase)
        return current.astype(np.float64)
