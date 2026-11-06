"""Independent Component Analysis (FastICA) for EEG artifact decomposition (phase F5).

Implements architectural decision D-05:
- Heavy iterative operations (FastICA) run in separate worker processes to protect
  real-time ingestion threads from GIL-induced latency spikes.
"""

from __future__ import annotations

import concurrent.futures
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
from sklearn.decomposition import FastICA

from neurosync.core.errors import InvalidInput, ProcessingError


@dataclass(frozen=True, slots=True)
class IcaResult:
    """Decomposition result of FastICA."""

    components: npt.NDArray[np.float64]  # shape (n_components, n_samples)
    mixing: npt.NDArray[np.float64]  # shape (n_channels, n_components)
    unmixing: npt.NDArray[np.float64]  # shape (n_components, n_channels)
    mean: npt.NDArray[np.float64]  # shape (n_channels,)

    @property
    def n_components(self) -> int:
        return int(self.components.shape[0])


def _fit_ica_worker(
    data: npt.NDArray[np.float64],
    n_components: int | None,
    max_iter: int,
    random_state: int,
) -> tuple[
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
]:
    """Worker function executed inside process pool without GIL contention."""
    # Data shape: (n_channels, n_samples) -> FastICA expects (n_samples, n_channels)
    x = data.T
    mean = np.mean(x, axis=0)
    x_centered = x - mean

    ica = FastICA(
        n_components=n_components,
        max_iter=max_iter,
        random_state=random_state,
        whiten="unit-variance",
    )
    sources = ica.fit_transform(x_centered)  # (n_samples, n_components)
    mixing = ica.mixing_  # (n_channels, n_components)
    unmixing = ica.components_  # (n_components, n_channels)

    return (
        sources.T.astype(np.float64),
        mixing.astype(np.float64),
        unmixing.astype(np.float64),
        mean.astype(np.float64),
    )


class FastIcaEstimator:
    """Manages isolated process pool execution of FastICA artifact extraction."""

    def __init__(self, max_iter: int = 500, random_state: int = 42) -> None:
        self.max_iter = max_iter
        self.random_state = random_state

    def fit(
        self,
        data: npt.NDArray[np.floating[Any]],
        *,
        n_components: int | None = None,
        use_process_pool: bool = True,
        timeout_s: float = 30.0,
    ) -> IcaResult:
        """Decompose EEG data into independent components.

        Args:
            data: shape (n_channels, n_samples).
            n_components: Number of components (default: n_channels).
            use_process_pool: If True, execute in separate process (D-05).
            timeout_s: Timeout in seconds for worker process execution.
        """
        if data.ndim != 2:
            raise InvalidInput(f"data must be 2D, got shape {data.shape}")
        n_channels, n_samples = data.shape
        if n_samples < n_channels:
            raise InvalidInput(
                f"Need at least as many samples as channels: {n_samples} < {n_channels}"
            )

        comp_count = n_components if n_components is not None else n_channels
        raw_data = data.astype(np.float64)

        if use_process_pool:
            with concurrent.futures.ProcessPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(
                    _fit_ica_worker,
                    raw_data,
                    comp_count,
                    self.max_iter,
                    self.random_state,
                )
                try:
                    sources, mixing, unmixing, mean = fut.result(timeout=timeout_s)
                except Exception as exc:
                    raise ProcessingError(f"FastICA process pool failed: {exc}") from exc
        else:
            sources, mixing, unmixing, mean = _fit_ica_worker(
                raw_data,
                comp_count,
                self.max_iter,
                self.random_state,
            )

        return IcaResult(
            components=sources,
            mixing=mixing,
            unmixing=unmixing,
            mean=mean,
        )

    @staticmethod
    def reconstruct(result: IcaResult, drop_indices: Sequence[int]) -> npt.NDArray[np.float64]:
        """Reconstruct clean EEG data excluding specified artifact component indices.

        Args:
            result: IcaResult from fit().
            drop_indices: Component row indices to zero out (e.g. eye blinks, muscle artifacts).

        Returns:
            Cleaned multi-channel signal array of shape (n_channels, n_samples).
        """
        cleaned_components = result.components.copy()
        for idx in drop_indices:
            if 0 <= idx < result.n_components:
                cleaned_components[idx, :] = 0.0

        # Reconstruct: X = S * A^T + mean
        # S is (n_components, n_samples), A is (n_channels, n_components)
        # S.T @ A.T = (n_samples, n_channels) -> transpose to (n_channels, n_samples)
        reconstructed = (cleaned_components.T @ result.mixing.T) + result.mean
        return reconstructed.T.astype(np.float64)
