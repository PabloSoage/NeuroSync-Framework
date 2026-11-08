# Development History and Commit Log

This document provides a readable, structured account of the 455 development commits leading to the Bachelor's Thesis (TFG), correlated with the methodology and development chapters of the thesis report (`Memoria_Latex/contido/Chapter4_Met.tex` and `Chapter5_Dev_it*.tex`).

In accordance with architectural decision **D-17**, original git commit messages (many of which are brief or informal, e.g. `...`, `conc`) are **never rewritten** or rebased. This document serves as the historical ledger explaining what was built at each stage.

---

## 1. Stage Overview

| Stage | Focus | Dates | Commits | Commit Range | Report Reference |
|---|---|---|---|---|---|
| **Iteration 1** | Basic Modules & Initial Integration | 2025-04-12 – 2025-04-19 | 58 | `ea4135f` – `02f6bdd` | Ch. 4 §4.3 (Days 1–19), Ch. 5 §5.1 |
| **Iteration 2** | SOLID Refactoring & Service Architecture | 2025-04-20 – 2025-04-30 | 9 | `58bfbb9` – `d8f432c` | Ch. 4 §4.3 (Days 20–42), Ch. 5 §5.2 |
| **Academic Pause**| Pause for university examinations | 2025-05-01 – 2025-05-13 | 0 | — | Ch. 4 §4.3 (Gantt days 31–42) |
| **Iteration 3** | API Architecture, Advanced DSP & Report | 2025-05-14 – 2026-04-22 | 388 | `b50b423` – `582ec37` | Ch. 4 §4.3 (Days 43–83), Ch. 5 §5.3 |
| **Cleanup & v2** | Repository Sanitization & Rewrite | 2026-11-02 – present | — | `b84cd11` – present | `docs/status.md`, `docs/decisions.md` |

---

## 2. Historical Stages

### Stage 1 · Iteration 1: Basic Modules & Initial Integration
- **Date Range:** 2025-04-12 to 2025-04-19
- **Commits:** 58 (`ea4135f` to `02f6bdd`)
- **Report Reference:** `Chapter4_Met.tex` §4.3 (Gantt days 1–19); `Chapter5_Dev_it1.tex` (§5.1)
- **What Changed:**
  - **Julia exploration:** Initial prototyping in Julia was evaluated and subsequently abandoned due to ecosystem maturity constraints; development consolidated on Python.
  - **Input Collector (`input_collector/`):** Implementation of low-level hooks for keyboard events and mouse tracking (position, clicks, scroll) with configurable key filters and CSV/JSON export.
  - **EEG Processor (`eeg_processor/`):** Driver integration with BrainFlow (synthetic board and physical hardware), real-time oscilloscope visualization with PyQt5/pyqtgraph, and 10-20 system electrode topographical mapping.
  - **First Integration Attempt:** Direct monolithic coupling between the input collector and EEG processor inside a single PyQt5 event loop. This attempt failed due to severe GUI thread starvation, dropped input events, and race conditions (`CON-01` to `CON-04`).
- **Associated Branches:**
  - `SOLID_Integrated_proofs` (merge-base `02f6bdd`, 1 commit `e07e0ba`): Early experiments applying SOLID principles to decoupled services.
  - `It1_Diagrams` (merge-base `02f6bdd`, 3 commits `728ddac`..`1b3aa79`): UML class diagrams and flowcharts for Iteration 1.

---

### Stage 2 · Iteration 2: SOLID Refactoring & Service-Based Integration
- **Date Range:** 2025-04-20 to 2025-04-30 (followed by academic pause until 2025-05-13)
- **Commits:** 9 (`58bfbb9` to `d8f432c`, cumulative 67 commits)
- **Report Reference:** `Chapter4_Met.tex` §4.3 (Gantt days 20–42); `Chapter5_Dev_it2.tex` (§5.2)
- **What Changed:**
  - **Service-Oriented Refactoring:** Re-architecting the monolithic codebase into specialized singleton services (`CollectorService`, `RecordingService`, `ProcessingService`) implementing Single Responsibility and Dependency Inversion.
  - **Synchronization Module (`synchronization_module/`):** Introduction of shared synchronizer classes to coordinate concurrent acquisition threads.
  - **Second Integration Attempt:** While structurally cleaner than Iteration 1, coordinating separate services through the main GUI process continued to produce latency spikes, queue overflows under high sample rates, and thread contention.
  - **Academic Pause (May 1 to May 13):** Development was halted as planned during the university final examination period (documented in report Gantt as days 31–42).
- **Associated Branches:**
  - `It2_Diagrams` (merge-base `d8f432c`, 9 commits `045044a`..`d9c17b6`): Architecture diagrams documenting the service refactoring.

---

### Stage 3 · Iteration 3: API Architecture, Advanced Processing & Completion
- **Date Range:** 2025-05-14 to 2026-04-22
- **Commits:** 388 (`b50b423` to `582ec37`, cumulative 455 commits)
- **Report Reference:** `Chapter4_Met.tex` §4.3 (Gantt days 43–83); `Chapter5_Dev_it3.tex` (§5.3)
- **What Changed:**
  - **API Paradigm Shift (`api_explorer/`):** Development of local REST APIs and WebSocket endpoints using FastAPI and Uvicorn for both data access and hardware control, fully isolating acquisition from visualization.
  - **Web Signal Explorer:** Web-based dynamic dashboard offering multi-channel oscilloscope streaming and live spectrogram inspection.
  - **PS4 Controller Integration:** Native DualShock 4 gamepad support capturing joystick axes, buttons, triggers, and D-pad.
  - **Interactive CLI:** Interactive terminal interface (`cli.py`) for headless experiment execution without launching graphical desktop windows.
  - **Advanced EEG DSP:** Online filtering with causal SOS filters, ocular/muscular artifact removal with FastICA (`sklearn.decomposition.FastICA`), and offline analysis integration with MNE-Python (Welch PSD, STFT spectrograms, band-power topomaps).
  - **Thesis Documentation:** Comprehensive report authored in LaTeX (`Memoria_Latex/`), technical figures (`Diagrams/`), and final repository licensing.
- **Associated Branches:**
  - `API_Proofs` (merge-base `9805278`, 1 commit `96e403d`): Early FastAPI endpoint prototypes.
  - `FastAPI_Proofs` (merged at `ed5a7be` on 2025-05-18): Integration of FastAPI endpoints into the main tree.
  - `PS4_Test` (merge-base `5a7be6b` on 2025-06-01): Gamepad input collection proofs.
  - `ICA_Realtime_Process` (merge-base `8e7c5c1`, 1 commit `b089e67`): Multiprocessing isolation proofs for FastICA computations.
  - `synchronizer` (merge-base `772dbfa`, 1 commit `51b4710`): Timestamp alignment proofs.
  - `Workspace_Chats` (merge-base `20db4e5`, 1 commit `459b3ae`): Experimental notes.

---

### Stage 4 · Cleanup and Next-Generation Rewrite (v2)
- **Cleanup Commit (`b84cd11`, 2026-11-02):**
  - Branch `full-history` created to retain an exact reference to commit `582ec37`.
  - Removed generated build caches, temporary profiling data, and intermediate diagram versions from `main`.
- **v2 High-Performance Branch:**
  - Dedicated `v2` branch established for the complete architectural rewrite.
  - Key innovations:
    1. Single unified clock protocol (`Clock.now_ns()`, `PerfCounterClock`) with periodic UTC anchors (`ClockAnchor`) (D-02).
    2. Single-producer multiple-reader ring buffers (`SignalRing`, `RingReader`) using atomic seqlock counters without lock contention (D-04).
    3. Thread-safe pub-sub `EventBus` with backpressure policies (`Policy.BLOCK`, `Policy.DROP_OLDEST`) (D-04).
    4. Deterministic test bench (`SimulatedSource`) with ground truth and fault injection (D-07).
    5. Lossless BrainFlow acquisition (`BrainFlowSource`) draining internal buffers with `get_board_data()`, resolving historical race `CON-02` and 30-minute stall `EEG-01`.
    6. Native streaming XDF recording (`XdfWriter`, `Recorder`) writing append-only binary files with vectorized NumPy structured arrays and metadata JSON sidecars (D-08).
