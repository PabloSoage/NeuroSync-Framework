"""
EEG Processor CLI Package

This package contains the command-line interface (CLI) components for the EEG Processor application.
It provides interactive and scriptable access to all EEG Processor features, including data access,
monitoring, and control of EEG devices and processing pipelines.

Modules:
- cli_app: Main Typer CLI application and command registration.
- cli_shell: Interactive shell for user-friendly command execution.
- cli_config: Shared configuration and state for CLI operation.
- commands: Command modules for data, monitoring, and control.

All modules are designed to be imported and used by the main CLI entry point.
"""

from .cli_app import app
from .cli_config import (
    headless_mode,
    set_gui_mode,
    get_gui_mode,
    init_headless_mode,
    get_data_service,
    get_interaction_service,
    get_collector_service,
)
from .cli_shell import run_shell

__all__ = [
    "app",
    "run_shell",
    "headless_mode",
    "set_gui_mode",
    "get_gui_mode",
    "init_headless_mode",
    "get_data_service",
    "get_interaction_service",
    "get_collector_service",
]
