"""
CLI application for EEG Processor.

This module provides a Typer CLI application for interacting with the EEG Processor.
"""

import atexit
import signal
import sys
import threading
from typing import Any

import typer
from rich.console import Console

# Import configuration and shared state
from .cli_config import (
    headless_mode,
    set_cli_running,
    is_cli_running,
    headless_app,
)

# Import command modules
from .commands.data_commands import data_app
from .commands.interaction_commands import control_app
from .commands.monitor_commands import monitor_app

# Create console for output
console = Console()

# Create main CLI app
app = typer.Typer(
    name="eeg-processor",
    help="EEG Processor CLI - Control and monitor EEG data processing",
)

# Add command groups
app.add_typer(data_app, name="data", help="Data access commands")
app.add_typer(control_app, name="control", help="Control and interaction commands")
app.add_typer(monitor_app, name="monitor", help="Monitoring commands")


def run_cli() -> None:
    """Run the CLI application."""
    try:
        # Set CLI as running
        set_cli_running(True)

        # Register shutdown handler
        atexit.register(shutdown_cli)

        # Register signal handlers only if in main thread
        is_main_thread = threading.current_thread() is threading.main_thread()
        if is_main_thread:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            console.print(
                "[dim]Running in main thread - signal handlers registered[/dim]"
            )
        else:
            console.print(
                "[dim]Running in secondary thread - signal handlers skipped[/dim]"
            )

        # Import here to avoid circular imports
        from .cli_shell import run_shell

        # Run the interactive shell
        run_shell()
    finally:
        # Make sure we clean up properly
        set_cli_running(False)
        shutdown_cli()


def signal_handler(sig: int, frame: Any) -> None:
    """Handle termination signals."""
    console.print("\n[yellow]Signal received, shutting down CLI...[/yellow]")
    shutdown_cli()
    sys.exit(0)


def shutdown_cli() -> None:
    """Safely shut down the CLI."""
    if not is_cli_running():
        return

    set_cli_running(False)

    try:
        # Clean up headless mode if active
        if headless_mode and headless_app:
            headless_app.shutdown()

        # Clean up API connections if needed
        try:
            from ..api_integration import get_api_integration

            api = get_api_integration()
            if api and hasattr(api, "shutdown"):
                api.shutdown()
        except:
            pass

        # Reset sys.stdin to avoid lock errors during shutdown
        if hasattr(sys, "stdin") and hasattr(sys.stdin, "close"):
            try:
                # Only close if we're not in interactive mode
                if not sys.stdin.isatty():
                    sys.stdin.close()
            except:
                pass

    except Exception as e:
        console.print(f"[bold red]Error during CLI shutdown: {e}[/bold red]")


@app.command("version")
def version() -> None:
    """Display the version of the EEG processor CLI."""
    console.print("EEG Processor CLI v1.0.0")


@app.command("info")
def info() -> None:
    """Display information about the EEG processor."""
    from .cli_config import headless_mode, init_headless_mode
    from ..interaction_api import EEGProcessorInteractionAPI

    # Get app state
    if headless_mode:
        init_headless_mode()

    try:
        system_status = EEGProcessorInteractionAPI.get_system_status()

        # Create a table to display the info
        from rich.table import Table
        from rich import box

        table = Table(title="EEG Processor Info", box=box.ROUNDED)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        if system_status.get("success"):
            status = system_status.get("status", {})

            table.add_row("Connected", str(status.get("connected", False)))
            table.add_row("Streaming", str(status.get("streaming", False)))
            table.add_row("Recording", str(status.get("recording", False)))
            table.add_row("Board Name", status.get("board_name", "Unknown"))
            table.add_row("Board ID", str(status.get("board_id", -1)))
            table.add_row("Sampling Rate", f"{status.get('sampling_rate', 0)} Hz")
            table.add_row("Channels", str(len(status.get("channel_names", []))))
            table.add_row("Data Available", str(status.get("data_available", False)))
        else:
            table.add_row("Status", "Error getting system status")
            table.add_row("Error", system_status.get("error", "Unknown"))

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error getting application info: {e}[/bold red]")


if __name__ == "__main__":
    app()
