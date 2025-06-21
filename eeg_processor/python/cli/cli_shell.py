"""
Interactive CLI shell for EEG Processor.

This module provides an interactive shell for the EEG Processor CLI.
"""

import shlex
import sys
from typing import List

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax

from .cli_app import app

# Import shared config instead of from cli_app
from .cli_config import headless_mode, get_gui_mode, init_headless_mode
from ..interaction_api import EEGProcessorInteractionAPI

console = Console()


def run_interactive_shell() -> None:
    """Run an interactive shell for the EEG Processor CLI."""
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
            cmd = Prompt.ask("\n[bold cyan]eeg-processor[/bold cyan]> ")

            # Skip empty commands
            if not cmd.strip():
                continue

            # Handle built-in commands
            if cmd.strip().lower() == "exit" or cmd.strip().lower() == "quit":
                console.print("[yellow]Exiting EEG Processor CLI...[/yellow]")
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

            elif cmd.strip().lower() == "clear":
                console.clear()
                continue

            # Parse command and arguments
            args = shlex.split(cmd)

            # Handle command with typer CLI
            run_typer_command(args)

        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit the CLI shell[/yellow]")
        except Exception as e:
            console.print(f"[bold red]Error: {e}[/bold red]")


def run_typer_command(args: List[str]) -> None:
    """Run a Typer command with the given arguments."""
    try:
        # Create a new sys.argv with the command
        old_argv = sys.argv.copy()
        sys.argv = ["eeg-processor"] + args

        # Run the command
        app()

        # Restore sys.argv
        sys.argv = old_argv
    except SystemExit:
        # Catch SystemExit to prevent the shell from exiting
        pass
    except Exception as e:
        console.print(f"[bold red]Error running command: {e}[/bold red]")


def show_welcome_message() -> None:
    """Show the welcome message for the CLI shell."""
    gui_mode_text = ""
    if get_gui_mode():
        gui_mode_text = "\n[yellow]Running alongside GUI - all changes will affect the GUI in real-time.[/yellow]"

    console.print(
        Panel.fit(
            f"[bold green]EEG Processor CLI Shell[/bold green]\n\n"
            f"Enter commands to interact with the EEG Processor.{gui_mode_text}\n"
            "Type [bold cyan]help[/bold cyan] to see available commands or [bold cyan]exit[/bold cyan] to quit.",
            title="Welcome",
            border_style="blue",
            box=box.ROUNDED,
        )
    )


def show_help_message() -> None:
    """Show the help message."""
    # Basic commands help
    basic_commands = """
# Basic commands
status                       # Show current application status
help                         # Show this help message
clear                        # Clear screen
exit                         # Exit the CLI shell
    """

    # Control commands for EEG processing
    control_commands = """
# Board connection
control connect --preset 0 -- -1                         # Connect to synthetic board (note: use -- before negative IDs)
control connect --preset 0 8                             # Connect to unicorn board
control disconnect                                        # Disconnect
control boards                                            # List available boards
control status                                            # Get system status

# Data streaming
control start-stream --buffer-size 450000                # Start streaming
control stop-stream                                       # Stop streaming

# Signal processing
control apply-filters --bandpass-low 1.0 --bandpass-high 50.0
control ica 8 --channels "0,1,2,3,4,5,6,7"             # ICA analysis
control mne-convert 10 --use-filters                     # Convert to MNE
control wavelet 4 3 0 --denoising                        # Wavelet analysis
control downsampling 2 --method mean --apply             # Downsampling

# Recording
control start-recording recording.csv --data-type raw    # Start recording
control stop-recording                                    # Stop recording
control insert-marker 100                                # Insert marker

# Visualization
control start-viz --type eeg                             # Start EEG visualization
control stop-viz --type eeg                              # Stop visualization
control start-viz --type brain_map                       # Start brain map
    """

    # Monitoring commands
    monitor_commands = """
# Real-time monitoring
monitor stream --duration 30 --refresh-rate 0.5         # Monitor data stream
monitor status --refresh-rate 2.0                       # Monitor system status
monitor channels --channels "0,1,2,3" --refresh-rate 1.0 # Monitor specific channels
monitor quality --refresh-rate 3.0                      # Monitor signal quality
monitor recording --refresh-rate 1.0                    # Monitor recording
    """

    # Data access commands
    data_commands = """
# Data access
data current-data --max-samples 100                     # Get current data
data current-data --all --vertical                      # Show all data vertically
data eeg-data --max-samples 50                          # Get EEG channels only
data channel-data 1 --max-samples 100                   # Get specific channel
data metadata                                            # Get stream metadata
data sampling-rate                                       # Get sampling rate
data signal-quality --channel-index 1                   # Get signal quality for channel
data signal-quality --all                               # Get signal quality for all channels
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


def show_status() -> None:
    """Show current application status."""
    try:
        # Get application state
        if headless_mode:
            init_headless_mode()

        system_status = EEGProcessorInteractionAPI.get_system_status()

        if system_status.get("success"):
            status = system_status.get("status", {})

            # Format connection status
            connected = status.get("connected", False)
            connection_status = (
                "[green]CONNECTED[/green]" if connected else "[red]DISCONNECTED[/red]"
            )

            # Format streaming status
            streaming = status.get("streaming", False)
            streaming_status = (
                "[green]ACTIVE[/green]" if streaming else "[red]INACTIVE[/red]"
            )

            # Format recording status
            recording = status.get("recording", False)
            recording_status = (
                "[green]ACTIVE[/green]" if recording else "[red]INACTIVE[/red]"
            )

            # Build status message
            status_message = (
                f"[bold]Connection:[/bold] {connection_status}\n"
                f"[bold]Streaming:[/bold] {streaming_status}\n"
                f"[bold]Recording:[/bold] {recording_status}\n"
                f"[bold]Board:[/bold] {status.get('board_name', 'Unknown')} (ID: {status.get('board_id', -1)})\n"
                f"[bold]Sampling Rate:[/bold] {status.get('sampling_rate', 0)} Hz\n"
                f"[bold]Channels:[/bold] {len(status.get('channel_names', []))}\n"
                f"[bold]Data Available:[/bold] {status.get('data_available', False)}"
            )

            # Add recording details if active
            if recording:
                recording_filename = status.get("recording_filename", "unknown")
                recording_duration = status.get("recording_duration", 0)
                status_message += f"\n[bold]Recording File:[/bold] {recording_filename}"
                status_message += (
                    f"\n[bold]Recording Duration:[/bold] {recording_duration:.1f}s"
                )

        else:
            status_message = f"[red]Error getting status: {system_status.get('error', 'Unknown error')}[/red]"

        # Show status panel
        console.print(
            Panel(
                status_message,
                title="EEG Processor Status",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )

    except Exception as e:
        console.print(f"[bold red]Error getting status: {e}[/bold red]")


def run_shell() -> None:
    """Run the interactive shell."""
    run_interactive_shell()
