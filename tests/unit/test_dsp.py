"""Unit tests for DSP, online causal filtering, spectral analysis and FastICA (phase F5)."""

from __future__ import annotations

import numpy as np

from neurosync.core.clock import ManualClock
from neurosync.core.model import ChannelInfo, ChannelKind, SampleChunk, StreamInfo
from neurosync.core.ring import SignalRing
from neurosync.dsp.filters import (
    CausalSosFilter,
    FilterConfig,
    FilterPipeline,
)
from neurosync.dsp.ica import FastIcaEstimator
from neurosync.dsp.spectral import (
    compute_psd,
    compute_spectrogram,
    extract_eeg_bands,
)
from neurosync.dsp.stream import FilteredStreamWorker


def test_causal_filter_chunk_continuity() -> None:
    """Verifies stateful continuity: chunked filtering matches single-block filtering."""
    fs = 250.0
    cfg = FilterConfig.bandpass(1.0, 40.0, fs=fs, order=4)
    f_single = CausalSosFilter(cfg, n_channels=2)
    f_chunked = CausalSosFilter(cfg, n_channels=2)

    # 1000 samples test signal
    t = np.arange(1000) / fs
    sig0 = np.sin(2 * np.pi * 10.0 * t) + 0.5 * np.sin(2 * np.pi * 50.0 * t)
    sig1 = np.cos(2 * np.pi * 5.0 * t)
    data = np.stack([sig0, sig1], axis=0)

    # Single pass
    out_single = f_single.filter_chunk(data)

    # Chunked pass in 10 blocks of 100 samples
    chunks_out: list[np.ndarray] = []
    for i in range(0, 1000, 100):
        chunk = data[:, i : i + 100]
        chunks_out.append(f_chunked.filter_chunk(chunk))
    out_chunked = np.concatenate(chunks_out, axis=1)

    # Discard transient initial samples
    assert np.allclose(out_single[:, 50:], out_chunked[:, 50:], atol=1e-10)


def test_notch_filter_attenuation() -> None:
    """Verify 50 Hz notch filter strongly suppresses 50 Hz power."""
    fs = 250.0
    cfg = FilterConfig.notch(50.0, fs=fs, bandwidth_hz=2.0)
    flt = CausalSosFilter(cfg, n_channels=1)

    t = np.arange(2500) / fs
    sig = np.sin(2 * np.pi * 50.0 * t)  # 50 Hz line noise
    data = sig.reshape(1, -1)

    filtered = flt.filter_chunk(data)
    # Check attenuation in steady state
    in_power = np.mean(data[0, 500:] ** 2)
    out_power = np.mean(filtered[0, 500:] ** 2)
    suppression_ratio = out_power / in_power
    assert suppression_ratio < 0.01  # >20 dB suppression


def test_filter_pipeline_execution() -> None:
    fs = 250.0
    notch_cfg = FilterConfig.notch(50.0, fs=fs)
    bp_cfg = FilterConfig.bandpass(0.5, 40.0, fs=fs)

    p = FilterPipeline(
        [
            CausalSosFilter(notch_cfg, n_channels=2),
            CausalSosFilter(bp_cfg, n_channels=2),
        ]
    )

    data = np.ones((2, 100), dtype=np.float64)
    out = p.process_chunk(data)
    assert out.shape == (2, 100)

    offline = p.process_offline(data, zero_phase=True)
    assert offline.shape == (2, 100)


def test_filtered_stream_worker() -> None:
    fs = 250.0
    clock = ManualClock()
    channels = (ChannelInfo(name="Fz", kind=ChannelKind.EEG),)
    in_info = StreamInfo("raw", "test", channels=channels, nominal_fs=fs)
    out_info = StreamInfo("filtered", "test", channels=channels, nominal_fs=fs)

    in_ring = SignalRing(in_info, capacity=1000)
    out_ring = SignalRing(out_info, capacity=1000)

    flt = CausalSosFilter(FilterConfig.lowpass(30.0, fs=fs), n_channels=1)
    pipeline = FilterPipeline([flt])

    worker = FilteredStreamWorker(in_ring, out_ring, pipeline, clock)

    # Write 50 samples into in_ring
    data = np.sin(2 * np.pi * 10.0 * np.arange(50) / fs).reshape(1, -1)
    chunk = SampleChunk("raw", seq0=0, data=data, t_host_ns=clock.now_ns())
    in_ring.write(chunk)

    processed = worker.drain_all()
    assert processed == 50
    assert out_ring.head == 50

    out_reader = out_ring.reader(from_start=True)
    sl = out_reader.read_new()
    assert sl is not None
    assert sl.n == 50
    assert sl.seq[0] == 0


def test_spectral_psd_and_spectrogram() -> None:
    fs = 250.0
    t = np.arange(1000) / fs
    sig = np.sin(2 * np.pi * 10.0 * t).reshape(1, -1)

    psd_res = compute_psd(sig, fs=fs, nperseg=250)
    assert psd_res.psd.shape[0] == 1
    peak_freq = psd_res.freqs[np.argmax(psd_res.psd[0])]
    assert np.isclose(peak_freq, 10.0, atol=1.0)

    spec_res = compute_spectrogram(sig, fs=fs, nperseg=128)
    assert spec_res.sxx.ndim == 3
    assert spec_res.sxx.shape[0] == 1


def test_eeg_bands_extraction() -> None:
    fs = 250.0
    t = np.arange(1000) / fs
    # 10 Hz pure alpha wave
    sig = np.sin(2 * np.pi * 10.0 * t).reshape(1, -1)

    bands = extract_eeg_bands(sig, fs=fs, relative=True)
    assert "alpha" in bands
    assert "theta" in bands
    # Alpha power should dominate
    assert bands["alpha"][0] > bands["theta"][0]
    assert bands["alpha"][0] > bands["delta"][0]
    assert bands["alpha"][0] > bands["beta"][0]


def test_fast_ica_decomposition() -> None:
    """Test FastICA separation on synthetic mixed sources."""
    np.random.seed(42)
    n_samples = 2000
    t = np.linspace(0, 10, n_samples)

    s1 = np.sin(2 * t)  # signal 1
    s2 = np.sign(np.sin(3 * t))  # signal 2: square signal
    s = np.stack([s1, s2], axis=0)  # (2, 2000)

    # Mixing matrix A
    a = np.array([[1.0, 1.0], [0.5, 2.0]])
    x = a @ s  # mixed data (2, 2000)

    estimator = FastIcaEstimator(max_iter=300)
    # Test without process pool for quick deterministic unit test execution
    res = estimator.fit(x, use_process_pool=False)

    assert res.n_components == 2
    assert res.components.shape == (2, n_samples)

    # Reconstruct dropping component 0
    clean = FastIcaEstimator.reconstruct(res, drop_indices=[0])
    assert clean.shape == (2, n_samples)
