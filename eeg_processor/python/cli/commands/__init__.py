"""
EEG Processor CLI Command Modules

This package contains all the command modules for the EEG Processor CLI application.
Each module implements a set of Typer commands for interacting with the EEG processor,
including data access, monitoring, control, and other advanced features.

Modules:
- data_commands: Access and display EEG data and metadata.
- monitor_commands: Real-time monitoring of EEG streams, channels, and signal quality.
- interaction_commands: Control the EEG processor (connect, stream, record, filters, etc.).

All modules are designed to be imported and registered in the main CLI application.
"""

from .data_commands import data_app
from .interaction_commands import control_app
from .monitor_commands import monitor_app

__all__ = [
    "data_app",
    "monitor_app",
    "control_app",
]
