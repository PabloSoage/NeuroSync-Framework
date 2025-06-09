"""
Python package for the Input Collector application.

This package provides a comprehensive framework for collecting, processing,
visualizing, and logging input events from various devices including keyboards,
mice, and game controllers. It features both a GUI application and a command-line
interface, web API access, and extensible architecture supporting different
collector types and visualization methods.

Key components:
- Application core with event-based communication system
- Multiple input collectors (keyboard/mouse, PS4 controller)
- Real-time visualization of input events
- Logging to CSV and JSON formats
- Web API for remote monitoring and control
- CLI for headless operation and scripting
"""

# Main application exports
from .input_collector_app import InputCollectorApp, run_collector_app

# Core API exports
from .data_access_api import InputDataAPI
from .interaction_api import InputCollectorAPI

# Core interfaces
from .interfaces import InputData, AbstractInputCollector, AbstractVisualizer

# Collectors
from .collectors import (
    CollectorManager,
    KeyboardMouseCollector,
)

# Try to import PS4 controller with graceful fallback
try:
    from .collectors import PS4ControllerCollector, is_sdl2_available
except ImportError:
    pass

# Core event system
from .core import EventType, dispatch, subscribe, unsubscribe

# CLI access
from .cli import run_shell, run_interactive_shell, run_cli

# Web API initialization
from .api_integration import initialize_api
from .interaction_api_integration import initialize_interaction_api

__version__ = "1.0.0"

__all__ = [
    # Main application
    "InputCollectorApp",
    "run_collector_app",
    # Core APIs
    "InputDataAPI",
    "InputCollectorAPI",
    # Interfaces
    "InputData",
    "AbstractInputCollector",
    "AbstractVisualizer",
    # Collectors
    "CollectorManager",
    "KeyboardMouseCollector",
    # Event system
    "EventType",
    "dispatch",
    "subscribe",
    "unsubscribe",
    # CLI access
    "run_shell",
    "run_interactive_shell",
    "run_cli",
    # Web API initialization
    "initialize_api",
    "initialize_interaction_api",
    # Version
    "__version__",
]
