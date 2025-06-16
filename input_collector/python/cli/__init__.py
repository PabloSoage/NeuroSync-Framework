"""
Command Line Interface for Input Collector.

Provides CLI tools to interact with the Input Collector API, including
an interactive shell, configuration management, and specialized command
groups for monitoring, interaction control, and data access operations.
"""

from . import commands
from .cli_app import app, run_cli
from .cli_config import (
    headless_mode,
    set_gui_mode,
    get_gui_mode,
    init_headless_mode,
    HeadlessInputCollector,
    set_cli_running,
    is_cli_running,
    wait_for_cli_exit,
)
from .cli_shell import run_shell, run_interactive_shell

__version__ = "1.0.0"

__all__ = [
    "app",
    "run_cli",
    "headless_mode",
    "set_gui_mode",
    "get_gui_mode",
    "init_headless_mode",
    "HeadlessInputCollector",
    "set_cli_running",
    "is_cli_running",
    "wait_for_cli_exit",
    "run_shell",
    "run_interactive_shell",
    "commands",
    "__version__",
]
