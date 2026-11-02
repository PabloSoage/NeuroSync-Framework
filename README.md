# NeuroSync Framework

> **Branch `v2`: rewrite in progress.** The new code lives in `src/neurosync`
> (tests in `tests/`, CI in `.github/workflows/ci.yml`). Start with
> [`docs/status.md`](docs/status.md) (what is done and the exact next steps) and
> [`docs/decisions.md`](docs/decisions.md) (closed design decisions). The thesis
> code below (`eeg_processor/`, `input_collector/`, `synchronization_module/`,
> `api_explorer/`) is kept unchanged as reference until v2 reaches parity.


An open-source software suite developed for the simultaneous capture, processing, and visualization of neurophysiological signals (EEG) and human-interface device (HID) inputs. 

Developed as a **Final Degree Project** in **Computer Engineering (Computing Specialization)**, this framework provides a modular pipeline for real-time data ingestion from commercial EEG headsets, signal filtering, artifact rejection (ICA), and user interaction tracking.

## Core Architecture & Modules

The repository is structured as a monorepo comprising four main subsystems. They are designed to operate independently or as part of a synchronized pipeline.

### 1. EEG Processor (`/eeg_processor`)
Handles real-time signal acquisition and digital processing.
* **Hardware Abstraction:** Utilizes `BrainFlow` to interface with supported boards (e.g., g.tec Unicorn, OpenBCI, Muse).
* **Signal Processing:** Implements configurable filters (Butterworth, Chebyshev, Bessel) and Wavelet transforms for continuous signal conditioning.
* **Concurrent Analysis:** Isolates CPU-intensive operations—such as FastICA (Independent Component Analysis) and `MNE-Python` conversions—into separate OS processes using `multiprocessing` to maintain system responsiveness.

### 2. Input Collector (`/input_collector`)
Tracks and logs user behavioral data.
* **Multi-Device Tracking:** Asynchronously captures Keyboard/Mouse events and PS4 Controllers (via SDL2 event loops).
* **Event System:** Emits normalized event payloads agnostic of the underlying hardware source.

### 3. Synchronization Module (`/synchronization_module`) - *Experimental*
An integration layer currently in development, aiming to unify EEG and Input streams into a single timeline.
* **LSL Integration:** Implements Lab Streaming Layer concepts to resolve clock drifts between asynchronous hardware sources.
* **Dataset Export:** Designed to format and export synchronized sessions into scientific standards (BIDS, EDF+, HDF5, CSV).

---

## Multi-Interface Architecture

To ensure maximum accessibility and programmatic control, the framework exposes its capabilities through three distinct interface layers:

### 1. Native Desktop GUI (PyQt5)
A panel-based desktop application designed for direct visual feedback and experiment control.
* **EEG Visualizers:** Multi-signal plotting and 10-20 system Brain Topomaps with real-time signal quality indicators.
* **Live Processing Controls:** Dynamic adjustment of Bandpass/Notch frequencies, downsampling factors, and ICA components on the fly.
* **Interactive Overlays:** Visualizes controller analog stick coordinates and button states alongside a live event log.

### 2. Interactive CLI (Typer & Rich)
A powerful command-line interface tailored for headless server environments, automated scripting, and terminal-based monitoring.
* **Interactive Shell:** Features a custom REPL environment to execute control commands seamlessly (`start-recording`, `apply-filters`, etc.).
* **Real-time Terminal Monitoring:** Utilizes the `Rich` library to render live data tables, active hardware states, and signal quality metrics directly in the terminal without needing a graphical server.

### 3. Web API & Explorer (FastAPI)
A dynamic web middleware serving real-time data to external clients and browsers.
* **REST & WebSocket Backends:** Auto-discovers and registers module endpoints at runtime. Implements a Worker Pool architecture for efficient WebSocket connection management.
* **High-Performance Streaming:** Supports `orjson` serialization and batched payloads for smooth, low-latency data transmission.
* **Dynamic API Explorer:** A built-in web dashboard (similar to Swagger UI but tailored for live data) featuring interactive parameter forms, real-time event tables, and `Chart.js` integration for remote signal visualization.

---

## ⚙️ Quick Start

### Prerequisites
* Python 3.11.4 (Recommended)
* PS4 controller support uses SDL2 through `pysdl2` and `pysdl2-dll`, both installed from `requirements.txt`

### Installation & Execution
It is highly recommended to use a virtual environment. The required dependencies include `brainflow`, `PyQt5`, `pyqtgraph`, `scipy`, `mne`, `fastapi`, `typer`, `rich`, and optionally `pylsl`.

**For Windows:**
```cmd
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

**For Linux / macOS:**
```bash
python3 -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
```

### Launching the Modules
You can launch the core modules independently. Each provides arguments to enable the GUI, the CLI, or the Web APIs.

```bash
# Launch the EEG Processor (GUI only)
python eeg_processor/run.py

# Launch the Input Collector (GUI + Interactive CLI side-by-side)
python input_collector/run.py --cli

# Launch in Headless mode with the FastAPI Web Explorer enabled
python eeg_processor/run.py --no-gui --enable-web-api --api-port 8000

# (Experimental) Launch the unified synchronization application
python synchronization_module/run.py
```

---

## Documentation & Diagrams

Comprehensive technical documentation is included in the repository:
* **`/Memoria_Latex`**: Contains the LaTeX source and the final PDF of the academic manuscript, detailing the mathematical foundations and methodology.
* **`/Diagrams`**: The final UML architectures, flowcharts, and component integrations of each module (`final_diagrams/`, Mermaid sources plus their `.pdf` renders, including the per-iteration versions in `It1/` and `It2/`), and a description of each module (`README_en.md`, `README_es.md`).

---

## Known Limitations

This branch is the code as delivered for the Final Degree Project (2025). A later
review found the following limitations, kept here so that nobody relies on them
by accident:

* **Synchronization is experimental.** The integrated synchronization module stamps
  EEG chunks and input events with `time.time()` on arrival; it does not use LSL
  clock correction. On Windows with Python 3.11 and 3.12, `time.time()` advances
  in steps of about 15.6 ms. The report (`Memoria_Latex`) already lists the
  synchronization module and the EDF+/HDF5/BIDS exports as future work.
* **Long sessions.** Acquisition reads with `get_current_board_data()`, which does
  not drain BrainFlow's ring buffer; with the default buffer the stream stops
  delivering new data after about 30 minutes at 250 Hz.
* **Applying filters while recording** re-sends the 30 s display buffer to
  consumers, so recordings may contain duplicated samples.
* **The web API is meant for local use only.** It has no authentication and its
  CORS policy is permissive; do not expose it beyond `127.0.0.1`.

These issues are addressed in the v2 rewrite (see below), not in this branch.

## Branches

| Branch | Contents |
|---|---|
| `main` | The final code of the Final Degree Project, its report (`Memoria_Latex`) and the final diagrams. Its history is the whole development (455 commits, April–September 2025) followed by a single cleanup commit that keeps only the final diagrams. |
| `v2` | Work-in-progress rewrite: a single installable package (`src/neurosync`), one monotonic clock, lock-free ring buffers, XDF recording, a headless server with GUI/CLI/web clients and a Qt 6 GUI. See `docs/status.md` on that branch. |
| `full-history` | The last development commit before the cleanup (`582ec37`), with every intermediate diagram and draft still in the tree. |

---

## ⚖️ License

Copyright (C) 2026 Pablo Soage Rodas

This program is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License v3.0** as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the `LICENSE` file for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see https://www.gnu.org/licenses/.