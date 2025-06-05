"""
CLI application for Input Collector.

This module provides a Typer CLI application for interacting with the Input Collector.
"""
import atexit
import signal
import threading
import time
import sys
import os
import asyncio
from typing import Optional, List, Dict, Any

import typer
from rich.console import Console
import keyboard

# Import configuration and shared state
from .cli_config import headless_mode, set_gui_mode, get_gui_mode, init_headless_mode, set_cli_running, is_cli_running, \
    headless_app

# Import CLI command modules
from .commands.data_commands import app as data_app
from .commands.interaction_commands import app as interaction_app
from .commands.monitor_commands import app as monitor_app

# Create console for output
console = Console()

# Create main Typer app
app = typer.Typer(
    name="input-collector",
    help="Command line interface for Input Collector",
)

# Add commands from modules
app.add_typer(data_app, name="data", help="Data access commands")
app.add_typer(interaction_app, name="control", help="Interaction control commands")
app.add_typer(monitor_app, name="monitor", help="Real-time monitoring commands")

def run_cli():
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
            console.print("[dim]Running in main thread - signal handlers registered[/dim]")
        else:
            console.print("[dim]Running in secondary thread - signal handlers skipped[/dim]")
        
        # Import here to avoid circular imports
        from .cli_shell import run_shell
        
        # Run the interactive shell
        run_shell()
    finally:
        # Make sure we clean up properly
        set_cli_running(False)
        shutdown_cli()

def signal_handler(sig, frame):
    """Handle termination signals."""
    console.print("\n[yellow]Signal received, shutting down CLI...[/yellow]")
    shutdown_cli()
    sys.exit(0)

def shutdown_cli():
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
            if api and hasattr(api, 'shutdown'):
                api.shutdown()
        except:
            pass
            
        try:
            from ..interaction_api_integration import get_interaction_api_integration
            api = get_interaction_api_integration()
            if api and hasattr(api, 'shutdown'):
                api.shutdown()
        except:
            pass

        # Reset sys.stdin to avoid lock errors during shutdown
        if hasattr(sys, 'stdin') and hasattr(sys.stdin, 'close'):
            try:
                # Only close if we're not in interactive mode
                if not sys.stdin.isatty():
                    sys.stdin.close()
            except:
                pass
            
    except Exception as e:
        console.print(f"[bold red]Error during CLI shutdown: {e}[/bold red]")

@app.command("version")
def version():
    """Display the version of the input collector CLI."""
    from . import __version__
    console.print(f"Input Collector CLI v{__version__}")

@app.command("info")
def info():
    """Display information about the input collector."""
    # Import here to avoid circular import
    from .cli_config import headless_mode, init_headless_mode
    from ..interaction_api import InputCollectorAPI
    
    # Get app state
    if headless_mode:
        init_headless_mode()
        
    try:
        app_state = InputCollectorAPI.get_application_state()
        
        # Create a table to display the info
        from rich.table import Table
        from rich import box
        
        table = Table(title="Input Collector Info", box=box.ROUNDED)
        
        # Add columns
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        # Add rows
        if "collector" in app_state:
            collector = app_state["collector"]
            table.add_row("Current Collector", collector.get("type", "Unknown"))
            
        table.add_row("Recording", str(app_state.get("recording", False)))
        table.add_row("Edit Mode", str(app_state.get("edit_mode", False)))
        
        if "tracked_keys" in app_state:
            table.add_row("Tracked Keys", ", ".join(app_state["tracked_keys"]))
            
        if "mouse_settings" in app_state:
            mouse = app_state["mouse_settings"]
            table.add_row("Tracking Mode", mouse.get("tracking_mode", "Unknown"))
            table.add_row("Direction Only", str(mouse.get("direction_only", False)))
            
        if "logging" in app_state:
            logging = app_state["logging"]
            table.add_row("JSON Logging", str(logging.get("json_enabled", False)))
            table.add_row("CSV Logging", str(logging.get("csv_enabled", False)))
            if logging.get("csv_enabled", False):
                table.add_row("CSV Path", logging.get("csv_path", "Not set"))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error getting application info: {e}[/bold red]")

def set_gui_mode(enabled: bool):
    """Set whether CLI is running alongside GUI."""
    from .cli_config import set_gui_mode as config_set_gui_mode
    config_set_gui_mode(enabled)

if __name__ == "__main__":
    app()
