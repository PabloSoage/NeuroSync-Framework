"""
EEG Processor - Real-time EEG Data Processing Framework.

Framework for real-time EEG data collection,
processing, analysis, and visualization with support for 20+ hardware manufacturers
and advanced neurophysiological analysis capabilities.

Quick Start:
    Basic usage:
    >>> python run.py

    Command line parameters:
    --logging {debug,info,warning,error,critical}
        Set logging level (default: info)

    --enable-web-api
        Enable REST API for data access with optional interaction methods

    --api-host HOST
        Host address for web API (default: 127.0.0.1)

    --api-port PORT
        Port for web API (default: 8000)

    --enable-control-api
        Enable dedicated control API with full interaction capabilities

    --control-api-host HOST
        Host address for control API (default: 127.0.0.1)

    --control-api-port PORT
        Port for control API (default: 8001)

    --control-api-only
        Enable only control API without data access API

    Example configurations:
    >>> python run.py --logging debug
    >>> python run.py --enable-web-api --api-port 8080
    >>> python run.py --enable-control-api --control-api-port 9000

Features:
- Real-time EEG data collection from multiple hardware manufacturers
- Advanced signal processing (filtering, ICA, wavelet transforms)
- Qt-based user interface with dark theme
- REST API with WebSocket support for real-time data streaming
- MNE-Python integration for advanced neurophysiological analysis
- Visualization tools and export capabilities
- Educational help system with theoretical background

Supported Hardware:
OpenBCI, g.tec, Muse, ANT Neuro, Neurosity, BrainBit, NeuroSky, and more.

For detailed documentation and examples, see the python package documentation.
"""

# Re-export the main application and core components for convenience
from .python import (
    EEGProcessorApp,
    EEGCollector,
    SignalProcessor,
    MultiSignalVisualizer,
    BrainMapVisualizer,
)
