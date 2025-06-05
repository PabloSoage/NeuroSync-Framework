"""
Data commands for the CLI application.

These commands allow interacting with the data access API.
"""

from typing import Optional, List, Dict, Any
import time

import typer
from rich.console import Console
from rich.table import Table
from rich import box

# Import shared config instead of from cli_app
from ..cli_config import headless_mode, init_headless_mode
from ...data_access_api import InputDataAPI

console = Console()
app = typer.Typer()


@app.command("active-keys")
def active_keys():
    """Get list of currently active keys."""
    if headless_mode:
        init_headless_mode()

    try:
        keys = InputDataAPI.get_active_keys()

        if not keys:
            console.print("[yellow]No keys currently active[/yellow]")
        else:
            console.print("[green]Active keys:[/green]")
            for key in keys:
                console.print(f"- {key}")

    except Exception as e:
        console.print(f"[bold red]Error getting active keys: {e}[/bold red]")


@app.command("is-key-active")
def is_key_active(key: str):
    """Check if a specific key is active."""
    if headless_mode:
        init_headless_mode()

    try:
        active = InputDataAPI.is_key_active(key)

        if active:
            console.print(f"[green]Key '{key}' is active[/green]")
        else:
            console.print(f"[yellow]Key '{key}' is not active[/yellow]")

    except Exception as e:
        console.print(f"[bold red]Error checking key '{key}': {e}[/bold red]")


@app.command("mouse-position")
def mouse_position():
    """Get the current mouse position."""
    if headless_mode:
        init_headless_mode()

    try:
        x, y = InputDataAPI.get_mouse_position()
        console.print(f"Mouse position: [cyan]X={x}[/cyan], [cyan]Y={y}[/cyan]")

    except Exception as e:
        console.print(f"[bold red]Error getting mouse position: {e}[/bold red]")


@app.command("mouse-button")
def mouse_button(
    button: str = typer.Argument(
        ..., help="Mouse button to check (left, right, middle)"
    )
):
    """Check if a mouse button is pressed."""
    if headless_mode:
        init_headless_mode()

    # Validate button
    valid_buttons = ["left", "right", "middle"]
    if button not in valid_buttons:
        console.print(
            f"[bold red]Invalid button: {button}. Must be one of: {', '.join(valid_buttons)}[/bold red]"
        )
        raise typer.Exit(1)

    try:
        pressed = InputDataAPI.get_mouse_button_state(button)

        if pressed:
            console.print(f"[green]Mouse button '{button}' is pressed[/green]")
        else:
            console.print(f"[yellow]Mouse button '{button}' is not pressed[/yellow]")

    except Exception as e:
        console.print(
            f"[bold red]Error checking mouse button '{button}': {e}[/bold red]"
        )


@app.command("mouse-direction")
def mouse_direction():
    """Get the current mouse movement direction."""
    if headless_mode:
        init_headless_mode()

    try:
        direction = InputDataAPI.get_mouse_direction()
        moving = InputDataAPI.is_mouse_moving()

        if moving:
            console.print(f"Mouse is moving: Direction = [cyan]{direction}[/cyan]")
        else:
            console.print("[yellow]Mouse is not currently moving[/yellow]")

    except Exception as e:
        console.print(f"[bold red]Error getting mouse direction: {e}[/bold red]")


@app.command("metadata")
def metadata():
    """Get metadata about the input collection process."""
    if headless_mode:
        init_headless_mode()

    try:
        meta = InputDataAPI.get_metadata()

        # Create a table for the metadata
        table = Table(title="Input Collector Metadata", box=box.ROUNDED)

        # Add columns
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        # Add rows for each metadata item
        for key, value in meta.items():
            table.add_row(key, str(value))

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error getting metadata: {e}[/bold red]")


@app.command("current-event")
def current_event():
    """Get the most recent input event."""
    if headless_mode:
        init_headless_mode()

    try:
        event = InputDataAPI.get_current_event()

        if not event:
            console.print("[yellow]No events recorded yet[/yellow]")
            return

        # Create a table for the event
        table = Table(title="Current Event", box=box.ROUNDED)

        # Add columns
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        # Get event dictionary
        if hasattr(event, "to_dict"):
            event_dict = event.to_dict()
        else:
            event_dict = vars(event)

        # Add rows for each event property
        for key, value in event_dict.items():
            if not key.startswith("_"):  # Skip private attributes
                table.add_row(key, str(value))

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error getting current event: {e}[/bold red]")


@app.command("events")
def events(
    event_type: str = typer.Argument(
        ..., help="Event type (key, mouse_movement, mouse_button, controller)"
    ),
    count: int = typer.Option(5, "--count", "-c", help="Number of events to show"),
):
    """Get recent events of a specific type."""
    if headless_mode:
        init_headless_mode()

    # Map event type to API method
    event_type_map = {
        "key": InputDataAPI.get_key_events,
        "mouse_movement": InputDataAPI.get_mouse_movement_events,
        "mouse_button": InputDataAPI.get_mouse_button_events,
        "controller": InputDataAPI.get_controller_events,
    }

    if event_type not in event_type_map:
        console.print(
            f"[bold red]Invalid event type: {event_type}. Must be one of: {', '.join(event_type_map.keys())}[/bold red]"
        )
        raise typer.Exit(1)

    try:
        # Get events
        events = event_type_map[event_type](count)

        if not events:
            console.print(f"[yellow]No {event_type} events recorded yet[/yellow]")
            return

        # Create a table for the events
        table = Table(
            title=f"Recent {event_type.replace('_', ' ').title()} Events",
            box=box.ROUNDED,
        )

        # Add columns based on first event
        first_event = events[0]
        if hasattr(first_event, "to_dict"):
            first_event_dict = first_event.to_dict()
        else:
            first_event_dict = vars(first_event)

        # Add timestamp column first
        table.add_column("Timestamp", style="cyan")

        # Add other relevant columns based on event type
        if event_type == "key":
            table.add_column("Key", style="green")
            table.add_column("Event Type", style="yellow")
            table.add_column("Active Keys", style="magenta")
        elif event_type == "mouse_movement":
            table.add_column("Event Type", style="green")
            table.add_column("Tracking Mode", style="yellow")
            if "rel_x" in first_event_dict:
                table.add_column("X", style="magenta")
                table.add_column("Y", style="magenta")
            if "direction" in first_event_dict:
                table.add_column("Direction", style="magenta")
        elif event_type == "mouse_button":
            table.add_column("Button", style="green")
            table.add_column("Event Type", style="yellow")
            table.add_column("Pressed", style="magenta")
        elif event_type == "controller":
            table.add_column("Control", style="green")
            table.add_column("Event Type", style="yellow")
            table.add_column("Value", style="magenta")

        # Add rows for each event
        for event in events:
            if hasattr(event, "to_dict"):
                event_dict = event.to_dict()
            else:
                event_dict = vars(event)

            # Build row based on event type
            if event_type == "key":
                table.add_row(
                    str(event_dict.get("timestamp", "")),
                    str(event_dict.get("key", "")),
                    str(event_dict.get("event_type", "")),
                    str(event_dict.get("active_keys", [])),
                )
            elif event_type == "mouse_movement":
                if "rel_x" in event_dict:
                    table.add_row(
                        str(event_dict.get("timestamp", "")),
                        str(event_dict.get("event_type", "")),
                        str(event_dict.get("mouse_tracking_mode", "")),
                        str(event_dict.get("rel_x", "")),
                        str(event_dict.get("rel_y", "")),
                    )
                elif "direction" in event_dict:
                    table.add_row(
                        str(event_dict.get("timestamp", "")),
                        str(event_dict.get("event_type", "")),
                        str(event_dict.get("mouse_tracking_mode", "")),
                        str(event_dict.get("direction", "")),
                    )
                else:
                    table.add_row(
                        str(event_dict.get("timestamp", "")),
                        str(event_dict.get("event_type", "")),
                        str(event_dict.get("mouse_tracking_mode", "")),
                        "N/A",
                    )
            elif event_type == "mouse_button":
                table.add_row(
                    str(event_dict.get("timestamp", "")),
                    str(event_dict.get("button", "")),
                    str(event_dict.get("event_type", "")),
                    str(event_dict.get("button_pressed", False)),
                )
            elif event_type == "controller":
                table.add_row(
                    str(event_dict.get("timestamp", "")),
                    str(event_dict.get("key", "")),
                    str(event_dict.get("event_type", "")),
                    str(event_dict.get("value", "")),
                )

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error getting events: {e}[/bold red]")


@app.command("controller-connected")
def controller_connected():
    """Check if a controller is connected."""
    if headless_mode:
        init_headless_mode()

    try:
        connected = InputDataAPI.is_controller_connected()

        if connected:
            name = InputDataAPI.get_controller_name()
            console.print(f"[green]Controller connected: {name}[/green]")
        else:
            console.print("[yellow]No controller connected[/yellow]")

    except Exception as e:
        console.print(f"[bold red]Error checking controller: {e}[/bold red]")
