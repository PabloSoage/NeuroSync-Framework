"""
Input Collector - Real-time Input Event Collection and Analysis Framework.

Framework for collecting, processing, analyzing,
and visualizing input events from various devices including keyboards, mice, and
game controllers. Features both GUI and CLI interfaces, web API access, and
extensible architecture supporting multiple input sources and visualization methods.

Quick Start:
    Basic GUI application:
    >>> python run.py

    Command line parameters:
    --fullscreen
        Start application in fullscreen mode

    --no-gui
        Run without GUI (headless mode) using CLI instead

    --cli
        Enable CLI shell along with the GUI for simultaneous operation

    --enable-web-api
        Enable REST API for data access with real-time input monitoring

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

    Example configurations:
    >>> python run.py --fullscreen
    >>> python run.py --enable-web-api --api-port 8080
    >>> python run.py --enable-control-api --control-api-port 9000
    >>> python run.py --no-gui
    >>> python run.py --cli --enable-web-api

Features:
- Real-time input event collection from keyboards, mice, and PS4 controllers
- Qt-based GUI with real-time visualization and interactive controls
- Command-line interface with interactive shell and scripting capabilities
- Dual web API system: data access API and control API for external integration
- Logging system supporting CSV and JSON formats with customizable output
- Event-driven architecture with decoupled communication between components
- Extensible collector system supporting multiple input device types simultaneously

Supported Input Devices:
- Keyboards: All standard keyboards with key mapping and state tracking
- Mice: Position tracking, button states, scroll wheel events, and click detection
- PS4 Controllers: Full DualShock 4 support including analog sticks, triggers, and touchpad
- Extensible architecture for additional controller types and input devices

For detailed documentation and examples, see the python package documentation.
"""

# Re-export the main application and core components for convenience
from .python import (
    InputCollectorApp,
    run_collector_app,
    InputDataAPI,
    InputCollectorAPI,
    CollectorManager,
    KeyboardMouseCollector,
    InputData,
    AbstractInputCollector,
)

# Web API initialization
from .python.api_integration import initialize_api

# CLI access
from .python.cli import run_cli, run_shell, run_interactive_shell
from .python.interaction_api_integration import initialize_interaction_api

# Try to import PS4 controller with fallback
try:
    from .python.collectors import PS4ControllerCollector, is_sdl2_available

    _ps4_available = True
except ImportError:
    _ps4_available = False

# Main exports for external use
__all__ = [
    # Core application
    "InputCollectorApp",
    "run_collector_app",
    # APIs
    "InputDataAPI",
    "InputCollectorAPI",
    # Core components
    "CollectorManager",
    "KeyboardMouseCollector",
    "InputData",
    "AbstractInputCollector",
    # CLI access
    "run_cli",
    "run_shell",
    "run_interactive_shell",
    # Web API initialization
    "initialize_api",
    "initialize_interaction_api",
]

# Add PS4 controller to exports if available
if _ps4_available:
    __all__.extend(["PS4ControllerCollector", "is_sdl2_available"])
