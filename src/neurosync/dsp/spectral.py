"""Spectral estimation and EEG band power extraction (phase F5).

Provides:
- Welch Power Spectral Density (PSD)
- Short-Time Fourier Transform (STFT) spectrogram
- Standard clinical EEG frequency band extraction (Delta, Theta, Alpha, Beta, Gamma)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
from scipy import integrate, signal

from neurosync.core.errors import InvalidInput

#: Standard clinical EEG frequency bands (Hz)
EEG_BANDS: dict[str, tuple[float, float]] = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 50.0),
}


@dataclass(frozen=True, slots=True)
class PsdResult:
    """Welch Power Spectral Density computation result."""

    freqs: npt.NDArray[np.float64]
    psd: npt.NDArray[np.float64]  # shape (n_channels, n_freqs)


@dataclass(frozen=True, slots=True)
class SpectrogramResult:
    """STFT Spectrogram computation result."""

    freqs: npt.NDArray[np.float64]
    times_s: npt.NDArray[np.float64]
    sxx: npt.NDArray[np.float64]  # shape (n_channels, n_freqs, n_times)


def compute_psd(
    data: npt.NDArray[np.floating[Any]],
    fs: float,
    *,
    nperseg: int | None = None,
    noverlap: int | None = None,
    window: str = "hann",
) -> PsdResult:
    """Compute Welch PSD for multi-channel data.

    Args:
        data: shape (n_channels, n_samples)
        fs: Sampling rate in Hz
        nperseg: Segment length in samples (default: min(256, n_samples))
        noverlap: Overlap in samples (default: nperseg // 2)
        window: Window function name
    """
    if data.ndim != 2:
        raise InvalidInput(f"data must be 2D (n_channels, n_samples), got shape {data.shape}")
    n_samples = data.shape[1]
    if n_samples < 4:
        raise InvalidInput("Need at least 4 samples to compute PSD")

    seg_len = min(n_samples, nperseg if nperseg is not None else 256)
    overlap = seg_len // 2 if noverlap is None else noverlap

    freqs, psd = signal.welch(
        data,
        fs=fs,
        window=window,
        nperseg=seg_len,
        noverlap=overlap,
        axis=-1,
    )
    return PsdResult(freqs=freqs.astype(np.float64), psd=psd.astype(np.float64))


def compute_spectrogram(
    data: npt.NDArray[np.floating[Any]],
    fs: float,
    *,
    nperseg: int = 128,
    noverlap: int | None = None,
    window: str = "hann",
) -> SpectrogramResult:
    """Compute STFT spectrogram for multi-channel data.

    Args:
        data: shape (n_channels, n_samples)
        fs: Sampling rate in Hz
        nperseg: Segment length (FFT window size)
        noverlap: Window overlap (default: nperseg * 3 // 4)
        window: Window name
    """
    if data.ndim != 2:
        raise InvalidInput(f"data must be 2D, got shape {data.shape}")
    n_samples = data.shape[1]
    seg_len = min(n_samples, nperseg)
    overlap = min(seg_len - 1, seg_len * 3 // 4 if noverlap is None else noverlap)

    freqs, times, sxx = signal.spectrogram(
        data,
        fs=fs,
        window=window,
        nperseg=seg_len,
        noverlap=overlap,
        axis=-1,
    )
    return SpectrogramResult(
        freqs=freqs.astype(np.float64),
        times_s=times.astype(np.float64),
        sxx=sxx.astype(np.float64),
    )


def compute_band_power(
    freqs: npt.NDArray[np.float64],
    psd: npt.NDArray[np.float64],
    low_hz: float,
    high_hz: float,
) -> npt.NDArray[np.float64]:
    """Calculate absolute band power within [low_hz, high_hz] using composite Simpson integration.

    Args:
        freqs: Frequency axis (n_freqs,)
        psd: Power spectral density (n_channels, n_freqs) or (n_freqs,)
        low_hz: Lower bound
        high_hz: Upper bound

    Returns:
        Band power array of shape (n_channels,) or scalar.
    """
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    if not np.any(mask):
        return (
            np.zeros(psd.shape[0], dtype=np.float64)
            if psd.ndim == 2
            else np.asarray(0.0, dtype=np.float64)
        )

    sub_freqs = freqs[mask]
    sub_psd = psd[:, mask] if psd.ndim == 2 else psd[mask]

    if len(sub_freqs) == 1:
        # Approximate with single bin width
        df = freqs[1] - freqs[0] if len(freqs) > 1 else 1.0
        return np.asarray(sub_psd * df, dtype=np.float64)

    power = integrate.simpson(sub_psd, x=sub_freqs, axis=-1)
    return np.asarray(power, dtype=np.float64)


def extract_eeg_bands(
    data: npt.NDArray[np.floating[Any]],
    fs: float,
    *,
    bands: Mapping[str, tuple[float, float]] | None = None,
    relative: bool = False,
) -> dict[str, npt.NDArray[np.float64]]:
    """Compute power for all specified EEG frequency bands across channels.

    Args:
        data: array of shape (n_channels, n_samples)
        fs: Sampling rate in Hz
        bands: Dictionary of band names to (low, high) tuples.
        relative: If True, normalize by total power across all bands.

    Returns:
        Mapping of band name -> power array of shape (n_channels,).
    """
    target_bands = bands or EEG_BANDS
    psd_res = compute_psd(data, fs)

    raw_powers: dict[str, npt.NDArray[np.float64]] = {}
    total_power = np.zeros(data.shape[0], dtype=np.float64)

    for name, (low, high) in target_bands.items():
        p = compute_band_power(psd_res.freqs, psd_res.psd, low, high)
        raw_powers[name] = p
        total_power += p

    if relative:
        eps = 1e-12
        total_safe = np.where(total_power > eps, total_power, 1.0)
        return {k: (v / total_safe) for k, v in raw_powers.items()}

    return raw_powers
