"""CounterUnwrapper and split_runs (phase F2; the BrainFlow source uses them in F3)."""

from __future__ import annotations

import numpy as np
import pytest

from neurosync.acquisition.counter import CounterUnwrapper, split_runs


def test_clean_sequence_with_8_bit_wrap() -> None:
    u = CounterUnwrapper(8)
    raw = np.arange(600) % 256
    r = u.update(raw)
    assert list(r.index) == list(range(600))
    assert r.gaps == 0 and r.duplicates == 0


def test_same_result_when_chunked() -> None:
    u = CounterUnwrapper(8)
    raw = np.arange(600) % 256
    out: list[int] = []
    for k in range(0, 600, 7):
        out.extend(u.update(raw[k : k + 7]).index.tolist())
    assert out == list(range(600))


def test_gap() -> None:
    u = CounterUnwrapper(8)
    r = u.update([250, 251, 254, 255, 0])  # 252 and 253 are missing
    assert list(r.index) == [0, 1, 4, 5, 6]
    assert list(r.gap_before) == [0, 0, 2, 0, 0]
    assert r.gaps == 2


def test_duplicate() -> None:
    u = CounterUnwrapper(8)
    r = u.update([10, 11, 11, 12])
    assert list(r.index) == [0, 1, -1, 2]
    assert list(r.duplicate) == [False, False, True, False]
    assert r.duplicates == 1


def test_16_bit_counter() -> None:
    u = CounterUnwrapper(16)
    raw = np.arange(65_530, 65_540) % 65_536
    assert list(u.update(raw).index) == list(range(10))


def test_out_of_range() -> None:
    with pytest.raises(ValueError):
        CounterUnwrapper(8).update([256])


def test_split_runs() -> None:
    idx = np.array([0, 1, 2, 5, 6, 9], dtype=np.int64)
    assert split_runs(idx) == [(0, 3), (3, 5), (5, 6)]
    assert split_runs(np.array([], dtype=np.int64)) == []
