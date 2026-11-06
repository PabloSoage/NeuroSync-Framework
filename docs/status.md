# v2 status and how to continue

Last update: 2026-11-02. Working branch: **`v2`**, branched from `main`. `main`
is the whole development history of the thesis (455 commits) plus one cleanup
commit; branch `full-history` points to the last commit before that cleanup.

This file says what is done, what has not been verified, and **exactly** what
to do next, step by step. It is written so that anyone (or any agent) can follow
it without making design decisions. Decisions are closed in
[`decisions.md`](decisions.md).

## 1. Done

Written **without running anything**: no code is executed on the laptop it was
written on. The first execution will be GitHub CI, or yours at home.

| Phase | Piece | File | Tests |
|---|---|---|---|
| F1 | Package, extras, ruff, strict mypy, import-linter, pytest | `pyproject.toml` | — |
| F1 | CI: lint (ruff, mypy, import-linter) and tests on Ubuntu and Windows with Python 3.12 and 3.13 | `.github/workflows/ci.yml` | — |
| F1 | Single clock, `ManualClock` for tests, clock info | `src/neurosync/core/clock.py` | `tests/unit/test_clock_and_anchors.py` |
| F1 | Clock ↔ UTC anchors (the only place using `time.time_ns`) | `src/neurosync/core/anchors.py` | same |
| F1 | Error hierarchy with `code` and `http_status` | `src/neurosync/core/errors.py` | — |
| F1 | Model: `StreamInfo`, `ChannelInfo`, `SampleChunk`, `InputEvent`, `QualityFlags` | `src/neurosync/core/model.py` | indirect |
| F1 | Architecture rules (no wall clock, no daemon threads, no silent `except`, light `core`) | `tests/arch/test_rules.py` | yes |
| F2 | `SignalRing` and `RingReader` (SPMC, seqlock, counted losses) | `src/neurosync/core/ring.py` | `tests/unit/test_ring.py` (hypothesis property and a two-thread test) |
| F2 | `EventBus` and `Subscription` (policies, counters, global order) | `src/neurosync/core/bus.py` | `tests/unit/test_bus.py` |
| F2 | `CounterUnwrapper` and `split_runs` (wrapping counter: gaps and duplicates) | `src/neurosync/acquisition/counter.py` | `tests/unit/test_counter.py` |
| F2 | `SignalSource` interface and `SourceStats` | `src/neurosync/acquisition/source.py` | — |
| F2 | `SimulatedSource`: deterministic signal, drift, drops, duplicates, synchronous mode (`emit_range`) and threaded mode | `src/neurosync/acquisition/simulated.py` | `tests/unit/test_simulated.py` |

**CI is green** on commit `28313a1` (2026-11-02): ruff, strict mypy,
import-linter and all tests on Ubuntu and Windows with Python 3.12 and 3.13.
Local test and formatting run on Windows with Python 3.13 completed (47 tests passed),
`ruff format` applied and `ruff format --check` added to CI (§3 completed).

## 2. Remaining (mandatory order)

1. **F3 · `BrainFlowSource`** (§4, fully specified).
2. **F4 · `Recorder` + `XdfWriter`** (§5, fully specified).
3. **`docs/history.md`** (documentation task, can be done at any point; §2.1).
4. F5 to F12: the phase plan is in the author's private notes
   (`ideas/tfg/08-plan-de-reescritura.md` and `ideas/tfg/tareas/`). Do not
   start a phase before the previous one meets its acceptance criterion.

### 2.1 Task: `docs/history.md` (readable development history)

The thesis commits have short or vague messages (`...`, `conc`,
`comprehensive v2`). They are **not** rewritten (D-17). Instead, write
`docs/history.md`, in English, on branch `v2` (it reaches `main` with the next
merge). Steps, in this order:

1. Get the data. Run from the repository root:
   `git log --reverse --date=short --format='%h|%ad|%s' 582ec37`. Also run
   `git log --reverse --date=short --stat --format='@@%h|%ad|%s' 582ec37`
   for the files touched by each commit. The range is the whole development,
   from the first commit (April 2025) to `582ec37` (2026-04-22, licence and
   README).
2. Split the commits into stages using **only** these sources, in this priority:
   - the planned and actual schedule in `Memoria_Latex/contido/Chapter4_Met.tex`
     (sections "Cronograma inicial planificado" and "Cronograma real ejecutado");
   - the three iterations in `Memoria_Latex/contido/Chapter5_Dev_it1.tex`,
     `Chapter5_Dev_it2.tex` and `Chapter5_Dev_it3.tex`;
   - the commit dates and the directories each commit touches (`eeg_processor/`,
     `input_collector/`, `synchronization_module/`, `api_explorer/`,
     `Diagrams/`, `Memoria_Latex/`).
3. For each stage write: name, date range, first and last commit hash, number
   of commits, what changed (1–5 bullet points, citing the report section),
   and the old development branches that belong to it. Those branches are
   `API_Proofs`, `FastAPI_Proofs`, `ICA_Realtime_Process`, `It1_Diagrams`,
   `It2_Diagrams`, `PS4_Test`, `SOLID_Integrated_proofs`, `Workspace_Chats` and
   `synchronizer`; place each one with `git merge-base main <branch>` and its
   own `git log`.
4. End with the cleanup commit (`b84cd11`) and the start of v2.
5. Rules:
   - Describe only what the commits and the report show. If a stage cannot be
     explained from them, write "unclear from the history" instead of guessing.
   - Do not copy commit messages verbatim when they say nothing (`...`); give
     the files and the report section instead.
   - Keep it under ~250 lines.
   - Add a link to `docs/history.md` in the README "Branches" section.

## 3. First step at home: local run and formatting

On the Windows PC or workstation (PowerShell), with Python 3.13:

```powershell
git clone git@github.com:PabloSoage/NeuroSync-Framework.git
cd NeuroSync-Framework
git switch v2
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
ruff check src tests
ruff format src tests          # applies formatting; review the diff and commit it
mypy --config-file pyproject.toml
lint-imports
pytest -m "not hardware"
```

On Linux (the server) it is the same except for the environment
(`python3.13 -m venv .venv` and `source .venv/bin/activate`).

Rules when fixing failures:

- **A `tests/arch` failure is fixed in the code, never in the test.**
- If a `tests/unit` test fails, first decide whether the test or the code is
  wrong by reading the module docstring: the docstring is the specification. If
  the test contradicts the docstring, change the test; otherwise change the code.
- Always run `mypy --config-file pyproject.toml`. Without that option mypy uses
  the thesis `mypy.ini`, which is still at the repository root.
- Once `ruff format` has been applied once, add
  `- run: ruff format --check src tests` to the `lint` job in
  `.github/workflows/ci.yml`, right after `ruff check`.
- Most likely failures, in order:
  1. mypy and numpy typing (`npt.NDArray[np.floating[Any]]`, `|=` on `uint16`
     arrays). Fix with `cast` or annotations; no generic `type: ignore` (if one
     is unavoidable, use an error code: `# type: ignore[arg-type]`).
  2. `test_realtime_thread_keeps_pace_and_stops` on slow runners: the margin
     (200–800 samples) may be widened; the test must not be removed.
  3. `test_anchor_matches_wall_clock` on Windows: the margin already covers
     15.6 ms; if it fails, look at `anchor.uncertainty_ns`.
- Commit with `git -c user.name="Pablo Soage" -c user.email=p.soage@udc.es commit`,
  without `Co-Authored-By`, message in English.

Exit criterion for §3: the same commands pass locally on Windows, `ruff format` is
applied and committed, and CI (now including `ruff format --check`) is green.

## 4. F3 · `BrainFlowSource` (next phase)

**File:** `src/neurosync/acquisition/brainflow_source.py`.
**Tests:** `tests/unit/test_brainflow_source.py` (synthetic board) and
`tests/integration/test_brainflow_long.py` (marked `slow`).
**Dependency:** extra `brainflow` (already in `pyproject.toml`); add
`brainflow` to the `dev` extra too so CI can run the tests.
`import brainflow` **only** inside this file.

Specification (do not deviate):

1. Class `BrainFlowSource` implementing `SignalSource` (`acquisition/source.py`).
   Constructor:
   `BrainFlowSource(board_id: int, params: BrainFlowInputParams | None = None, *, stream_id: str = "eeg", read_period_s: float = 0.005, preset: int = BrainFlowPresets.DEFAULT_PRESET, counter_bits: int = 8)`.
2. `info` is built from `BoardShim.get_board_descr(board_id, preset)`:
   `sampling_rate` → `nominal_fs`; `eeg_channels` (plus `eeg_names` if present,
   comma separated) → `ChannelKind.EEG` channels. Only signal rows go into
   `data`. The counter (`package_num_channel`), timestamp (`timestamp_channel`)
   and marker (`marker_channel`) rows are **not** channels.
3. `start(ring, clock)`: `BoardShim(board_id, params)`, `prepare_session()`,
   `start_stream(450000)`, then a **non-daemon** `threading.Thread` named
   `source-<stream_id>`.
4. Thread loop, every `read_period_s` (using `self._stop.wait(read_period_s)`):
   - `raw = board.get_board_data(preset=preset)`. **Always `get_board_data`**,
     which empties BrainFlow's buffer. `get_board_data_count` +
     `get_current_board_data` is **forbidden**: that is the original race
     (`CON-02`) and the 30-minute stall (`EEG-01`).
   - If `raw.shape[1] == 0`, continue.
   - `t_host = clock.now_ns()` right after reading.
   - `counter = raw[package_num_channel].astype(np.int64)` → `CounterUnwrapper`.
   - `t_source_ns = (raw[timestamp_channel] * 1e9).astype(np.int64)` (BrainFlow
     returns UNIX seconds as float).
   - Remove duplicates (`~duplicate`) and split with `split_runs`, **exactly as
     `SimulatedSource._emit` does** (reuse; do not reimplement).
   - `ring.write(SampleChunk(...))` per run, flag `QualityFlags.GAP` on the run
     after a gap; update `SourceStats`.
   - Exceptions: store in `self.error` and stop the thread. Never swallow them.
5. `stop(timeout_s=2.0)`: set the event, `join(timeout)`, raise `StopTimeout`
   if still alive; then `stop_stream()` and `release_session()`, each in its own
   `try`, re-raised as `DeviceError`.
6. `insert_marker(value: float)`: `board.insert_marker(value, preset)`. No sleep
   (the original slept 10 ms).

Acceptance tests (all with `BoardIds.SYNTHETIC_BOARD`):

- 10 s of synthetic data: `ring.head` between 2 300 and 2 700 (250 Hz),
  `stats.gaps == 0`, `stats.duplicates == 0`, `seq` continuous from 0 to
  `head - 1`.
- `slow`: **2 h** of synthetic data (`pytest -m slow`, on the server at night):
  0 gaps, 0 duplicates, and `head` still growing after minute 30 (the original
  stalled there).
- `PlaybackFileBoard` (`BoardIds.PLAYBACK_FILE_BOARD`, `params.file`,
  `params.master_board`): write a 60 s file generated with `SimulatedSource` in
  BrainFlow format (rows of the master board, TSV) and check that what is read
  matches what was written.
- `stop()` returns within 2 s and no thread is left (`threading.enumerate()`).

## 5. F4 · `Recorder` and `XdfWriter`

**Files:** `src/neurosync/recording/xdf_writer.py`,
`src/neurosync/recording/recorder.py`, `src/neurosync/recording/sidecar.py`.
**Tests:** `tests/unit/test_xdf_writer.py` (read back with `pyxdf`; add it to
the `dev` extra) and `tests/unit/test_recorder.py`.

XDF format. **Check it against the official specification**
(<https://github.com/sccn/xdf/wiki/Specifications>) before writing code. Summary:

- The file starts with the 4 bytes `XDF:`.
- Each chunk: variable-size length (1 byte holding 1, 4 or 8, then the length in
  little-endian), `uint16` tag, content.
- Tags: 1 FileHeader (XML); 2 StreamHeader (`uint32` StreamID + XML with
  `name`, `type`, `channel_count`, `nominal_srate`, `channel_format`,
  `created_at`, `desc` with channels); 3 Samples (StreamID, variable-size sample
  count, and per sample: 1 byte 0 or 8, the `double` timestamp in seconds if 8,
  then the values); 4 ClockOffset (StreamID, `double` time, `double` offset);
  5 Boundary (the 16 fixed bytes of the spec); 6 StreamFooter (StreamID + XML
  with `first_timestamp`, `last_timestamp`, `sample_count` and, in its own
  element, the `StreamStats` counters).
- Per-sample timestamps = `t_host_ns / 1e9` (single clock). `t_source_ns` and
  `seq` go as **extra channels** in an auxiliary `float64` stream. Clock anchors
  go as their own stream (`mono_ns`, `unix_ns`, `uncertainty_ns`).

`Recorder`: **non-daemon** `threading.Thread`; one `RingReader` per signal
stream and one `Subscription` (`Policy.BLOCK`) for events; writes in batches
every 50 ms; `flush` + `os.fsync` every 0.5 s; `stop(timeout_s)` writes the
StreamFooters and returns a `RecordingSummary` (samples, gaps, losses,
`max_flush_lag_ms`).

Criteria:

- Round trip of 1 simulated hour (`SimulatedSource` + `emit_range`, not real
  time): `pyxdf.load_xdf` returns exactly `render(spec, ...)` and the `seq`s.
- Simulated crash (close the file without footers): `pyxdf` opens it and at most
  the last batch is lost.
- No `print`, no `time.time`.

## 6. Home equipment

- **Windows PC or workstation:** §3, F3, F7; self-hosted CI runner for
  Windows-only tests.
- **Linux server:** nightly `slow` tests.
- **Raspberry Pi 3B / 3A+:** board emulators (OpenBCI WiFi Shield, Enophone) in
  F11.
- **RP2040:** HID keyboard, Cyton over USB and photodiode in F11.
- **KV260:** optional high-rate source.
- **NAS:** session archive.

## 7. Blockers

None yet. If one appears (something in `decisions.md` that cannot be met),
describe it here with date, file and what was tried, and stop the phase until a
decision is made.
