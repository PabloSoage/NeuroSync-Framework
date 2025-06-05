"""
Interactive CLI shell for Input Collector.

This module provides an interactive shell for the Input Collector CLI.
"""

import os
import sys
import time
import shlex
from typing import List, Dict, Any, Optional

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box

# Import shared config instead of from cli_app
from .cli_config import headless_mode, get_gui_mode, init_headless_mode
from .cli_app import app
from ..interaction_api import InputCollectorAPI

console = Console()


def run_interactive_shell():
    """Run an interactive shell for the Input Collector CLI."""
    # Initialize headless mode if necessary
    if headless_mode:
        init_headless_mode()

    # Show welcome message
    show_welcome_message()

    # Start command loop
    running = True
    while running:
        try:
            # Get command input
            cmd = Prompt.ask("\n[bold cyan]input-collector[/bold cyan]> ")

            # Skip empty commands
            if not cmd.strip():
                continue

            # Handle built-in commands
            if cmd.strip().lower() == "exit" or cmd.strip().lower() == "quit":
                console.print("[yellow]Exiting Input Collector CLI...[/yellow]")
                running = False
                # If in GUI mode, the GUI will continue running after CLI exits
                if get_gui_mode():
                    console.print(
                        "[yellow]Note: The GUI application will continue running.[/yellow]"
                    )
                continue

            elif cmd.strip().lower() == "help":
                show_help_message()
                continue

            elif cmd.strip().lower() == "status":
                show_status()
                continue

            # Parse command and arguments
            args = shlex.split(cmd)

            # Handle command with typer CLI
            run_typer_command(args)

        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit the CLI shell[/yellow]")
        except Exception as e:
            console.print(f"[bold red]Error: {e}[/bold red]")


def run_typer_command(args: List[str]):
    """Run a Typer command with the given arguments."""
    try:
        # Create a new sys.argv with the command
        old_argv = sys.argv.copy()
        sys.argv = ["input-collector"] + args

        # Run the command
        app()

        # Restore sys.argv
        sys.argv = old_argv
    except SystemExit:
        # Catch SystemExit to prevent the shell from exiting
        pass
    except Exception as e:
        console.print(f"[bold red]Error running command: {e}[/bold red]")


def show_welcome_message():
    """Show the welcome message for the CLI shell."""
    gui_mode_text = ""
    if get_gui_mode():
        gui_mode_text = "\n[yellow]Running alongside GUI - all changes will affect the GUI in real-time.[/yellow]"

    console.print(
        Panel.fit(
            f"[bold green]Input Collector CLI Shell[/bold green]\n\n"
            f"Enter commands to interact with the Input Collector.{gui_mode_text}\n"
            "Type [bold cyan]help[/bold cyan] to see available commands or [bold cyan]exit[/bold cyan] to quit.",
            title="Welcome",
            border_style="blue",
            box=box.ROUNDED,
        )
    )


def show_help_message():
    """Show the help message."""
    # Basic commands help
    basic_commands = """
# Basic commands
status                       # Show current application status
help                         # Show this help message
exit                         # Exit the CLI shell
    """

    # Common commands for controlling the application
    control_commands = """
# Recording control
control recording start      # Start recording
control recording stop       # Stop recording
control recording toggle     # Toggle recording state
control recording status     # Check recording status

# Logging control
control logging csv --action enable --filepath "data.csv"    # Enable CSV logging
control logging json --action enable                        # Enable JSON logging
control logging status                                      # Check logging status

# Collector management
control collectors list      # List available collectors
control collectors current   # Show current collector
control collectors switch --type keyboard_mouse    # Switch to keyboard & mouse
control collectors scan      # Scan for controllers
    """

    # Commands for monitoring
    monitor_commands = """
# Monitoring
monitor events               # Monitor all input events in real-time
monitor events --type key    # Monitor only keyboard events
monitor active-keys          # Monitor active keys
monitor mouse                # Monitor mouse movement and buttons
monitor status               # Monitor application status
    """

    # Commands for querying data
    data_commands = """
# Data access
data active-keys             # Get currently active keys
data mouse-position          # Get current mouse position
data mouse-button left       # Check state of left mouse button
data events key --count 5    # Get last 5 keyboard events
    """

    console.print(
        Panel(
            Syntax(basic_commands.strip(), "bash", theme="monokai", line_numbers=False),
            title="Basic Commands",
            border_style="green",
            expand=False,
        )
    )

    console.print(
        Panel(
            Syntax(
                control_commands.strip(), "bash", theme="monokai", line_numbers=False
            ),
            title="Control Commands",
            border_style="cyan",
            expand=False,
        )
    )

    console.print(
        Panel(
            Syntax(
                monitor_commands.strip(), "bash", theme="monokai", line_numbers=False
            ),
            title="Monitoring Commands",
            border_style="magenta",
            expand=False,
        )
    )

    console.print(
        Panel(
            Syntax(data_commands.strip(), "bash", theme="monokai", line_numbers=False),
            title="Data Access Commands",
            border_style="yellow",
            expand=False,
        )
    )


def show_status():
    """Show current application status."""
    try:
        # Get application state
        if headless_mode:
            init_headless_mode()

        app_state = InputCollectorAPI.get_application_state()

        # Format recording state
        recording = app_state.get("recording", False)
        recording_status = (
            f"[green]ACTIVE[/green]" if recording else "[red]INACTIVE[/red]"
        )

        # Format collector info
        collector = app_state.get("collector", {})
        collector_type = collector.get("type", "Unknown")
        collector_name = collector.get("name", "Unknown")

        # Format logging status
        logging_state = app_state.get("logging", {})
        json_logging = (
            "[green]ENABLED[/green]"
            if logging_state.get("json_enabled", False)
            else "[red]DISABLED[/red]"
        )
        csv_logging = (
            "[green]ENABLED[/green]"
            if logging_state.get("csv_enabled", False)
            else "[red]DISABLED[/red]"
        )

        # Build status message
        status_message = (
            f"[bold]Recording:[/bold] {recording_status}\n"
            f"[bold]Collector:[/bold] {collector_name} ({collector_type})\n"
            f"[bold]JSON Logging:[/bold] {json_logging}\n"
            f"[bold]CSV Logging:[/bold] {csv_logging}"
        )

        # Add CSV path if enabled
        if logging_state.get("csv_enabled", False) and logging_state.get("csv_path"):
            status_message += (
                f"\n[bold]CSV Path:[/bold] {logging_state.get('csv_path')}"
            )

        # Add tracked keys count
        tracked_keys = app_state.get("tracked_keys", [])
        status_message += f"\n[bold]Tracked Keys:[/bold] {len(tracked_keys)} keys"

        # Show status panel
        console.print(
            Panel(
                status_message,
                title="Application Status",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )

    except Exception as e:
        console.print(f"[bold red]Error getting status: {e}[/bold red]")


def run_shell():
    """Run the interactive shell."""
    run_interactive_shell()
