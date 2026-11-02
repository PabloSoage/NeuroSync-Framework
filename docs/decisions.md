# v2 design decisions (closed)

These decisions are **not reopened** during implementation. If something does
not fit, describe the problem in `docs/status.md` ("Blockers") and stop; do not
pick another path on your own.

The full analysis behind them lives in the author's private notes. This file is
the operational summary and is self-contained.

| ID | Decision | In practice |
|---|---|---|
| D-01 | One package, `neurosync`, with a `src/` layout. `neurosync.core` does not import Qt, FastAPI, BrainFlow, LSL, MNE or scipy, nor any other `neurosync` subpackage | Enforced by import-linter (`pyproject.toml`) and `tests/arch/test_rules.py` |
| D-02 | **One clock**: `Clock.now_ns()`, implemented with `time.perf_counter_ns`. Nobody reads `time.time()`, `time.monotonic()` or `datetime.now()` except `core/anchors.py` | UTC comes from anchors (`take_anchor`), stored as one more stream |
| D-03 | Every sample carries its **unwrapped source index** (`seq`), the host timestamp of its chunk (`t_host_ns`) and, if available, the source timestamp (`t_source_ns`). Per-sample time is reconstructed **when reading**, by regression, never when writing | `SampleChunk`, `SignalRing`; counters are unwrapped with `CounterUnwrapper` and split with `split_runs` |
| D-04 | Regular signal → `SignalRing` (one producer, several readers with their own cursor). Irregular events → `EventBus` (bounded queue per subscriber) | The producer never waits for a reader. Nothing is dropped silently: there are counters (`lost`, `SubStats.dropped`) |
| D-05 | Concurrency: one thread per source that only reads and writes to its ring; one serial command executor; asyncio only for networking; a **process** pool for ICA and MNE. **No daemon threads** | `stop()` always has a timeout and raises `StopTimeout` if the thread does not stop |
| D-06 | Explicit errors (`core/errors.py`), caught only at boundaries. Returning altered data or `success: true` to hide a failure is forbidden | `tests/arch` forbids `except:` and `except ...: pass`; ruff `BLE001` |
| D-07 | No EEG headset is available. The test bench is: `SimulatedSource` (ground truth and faults), the BrainFlow synthetic board (fixed 250 Hz × 16 channels, 8-bit counter) and `PlaybackFileBoard` | No acceptance criterion may depend on a headset |
| D-08 | **RAW is always recorded**, as **XDF written in-process**, append-only. EDF+, BIDS and CSV are offline exports from the XDF | HDF5 is not the native format. The XDF writer is validated by reading back with `pyxdf` |
| D-09 | Online filtering is **causal and stateful** (`scipy.signal.sosfilt` with `zi`), as a derived stream. Changing filters never re-injects past data | Zero-phase (`filtfilt`) only offline |
| D-10 | Topology: a server process `neurosyncd` without Qt owns hardware and recording; GUI, CLI and web are clients. The GUI starts the server if it is not running | Binary WebSocket for clients, LSL as optional output |
| D-11 | One typed command registry (pydantic v2), from which the HTTP API and the CLI (Typer) are generated | No hand-written per-module API layers |
| D-12 | New GUI on **PySide6** (Qt 6), imported only in `neurosync/gui/qt.py`. The old GUI is not ported | pyqtgraph for real-time plots |
| D-13 | Python **>= 3.12**; CI on 3.12 and 3.13, Ubuntu and Windows | 3.13 recommended on Windows |
| D-14 | Rust only as an optional extension (PyO3 + maturin), only when the test harness justifies it with a number, and always with a pure-Python implementation behind the same interface | Not before phase F11 |
| D-15 | The thesis code (`eeg_processor/`, `input_collector/`, `synchronization_module/`, `api_explorer/`) is **not modified**; it is removed in phase F12 once v2 reaches feature parity | CI and linters only look at `src/` and `tests/` |
| D-16 | Commits as `Pablo Soage <p.soage@udc.es>`, without `Co-Authored-By` or tool signatures. Work happens on branch `v2`; it reaches `main` only with green CI. Code, docs and commit messages in English | — |
