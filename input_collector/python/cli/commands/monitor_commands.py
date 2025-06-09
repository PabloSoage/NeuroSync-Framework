"""
Monitoring commands for the CLI application.

These commands allow monitoring input events in real-time.
"""

import time
from typing import List, Any, Dict, Tuple
import threading
import sys

import typer
from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

# Import shared config instead of from cli_app
from ..cli_config import headless_mode, init_headless_mode
from ...core.event_system import EventType, subscribe, unsubscribe
from ...data_access_api import InputDataAPI

console = Console()
app = typer.Typer()

# Store last events for different types
last_events: Dict[str, List[Dict[str, Any]]] = {
    "key": [],
    "mouse": [],
    "button": [],
    "controller": [],
    "all": [],
}

max_events = 10  # Default max events to keep


def event_callback(event: Any) -> None:
    """Callback for processing events."""
    # Skip if event is None
    if event is None:
        return

    # Convert event to dictionary if not already
    if hasattr(event, "to_dict"):
        event_dict = event.to_dict()
    elif hasattr(event, "__dict__"):
        event_dict = {k: v for k, v in vars(event).items() if not k.startswith("_")}
    else:
        event_dict = {"raw": str(event)}

    # Always add to all events
    last_events["all"].insert(0, event_dict)

    # Add to specific event type list
    event_type = event_dict.get("event_type", "")

    if "key" in event_type:
        last_events["key"].insert(0, event_dict)
    elif "mouse_move" in event_type:
        last_events["mouse"].insert(0, event_dict)
    elif "mouse_click" in event_type or "scroll" in event_type:
        last_events["button"].insert(0, event_dict)
    elif "button" in event_type or "axis" in event_type:
        last_events["controller"].insert(0, event_dict)

    # Limit the number of events
    for key in last_events:
        if len(last_events[key]) > max_events:
            last_events[key] = last_events[key][:max_events]


def get_layout(show_types: List[str]) -> Layout:
    """Create the layout for monitoring."""
    layout = Layout()

    # Create tables for different event types
    tables = {}

    if "all" in show_types:
        tables["all"] = create_event_table("All Events", last_events["all"])

    if "key" in show_types:
        tables["key"] = create_event_table("Keyboard Events", last_events["key"])

    if "mouse" in show_types:
        tables["mouse"] = create_event_table(
            "Mouse Movement Events", last_events["mouse"]
        )

    if "button" in show_types:
        tables["button"] = create_event_table(
            "Mouse Button Events", last_events["button"]
        )

    if "controller" in show_types:
        tables["controller"] = create_event_table(
            "Controller Events", last_events["controller"]
        )

    # Configure layout based on the number of tables
    if len(tables) == 1:
        # Just show the one table
        layout.update(list(tables.values())[0])
    elif len(tables) == 2:
        # Two tables side by side
        layout.split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1),
        )
        keys = list(tables.keys())
        layout["left"].update(tables[keys[0]])
        layout["right"].update(tables[keys[1]])
    else:
        # More complex layout for 3+ tables
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
        )

        # Footer with exit instructions
        layout["header"].update(
            Panel(
                "Press [bold red]Ctrl+C[/bold red] to exit monitoring",
                style="white on blue",
            )
        )

        # Arrange the main content
        if len(tables) <= 4:
            # Create a grid layout
            layout["main"].split_grid(n_rows=2, n_columns=2)

            # Add tables to grid
            grid_positions: List[Tuple[str, str]] = [("0-0", "0-1"), ("1-0", "1-1")]
            for i, (key, table) in enumerate(tables.items()):
                row, col = divmod(i, 2)
                layout[f"main-{row}-{col}"].update(table)
        else:
            # Just show the first 4 tables
            layout["main"].split_row(
                Layout(name="left_column", ratio=1),
                Layout(name="right_column", ratio=1),
            )

            layout["left_column"].split_column(
                Layout(name="top_left", ratio=1),
                Layout(name="bottom_left", ratio=1),
            )

            layout["right_column"].split_column(
                Layout(name="top_right", ratio=1),
                Layout(name="bottom_right", ratio=1),
            )

            # Add up to 4 tables
            layout_positions: List[str] = [
                "top_left",
                "top_right",
                "bottom_left",
                "bottom_right",
            ]
            for i, (key, table) in enumerate(list(tables.items())[:4]):
                layout[layout_positions[i]].update(table)

    return layout


def create_event_table(title: str, events: List[Dict[str, Any]]) -> Table:
    """Create a table for displaying events."""
    table = Table(title=title, box=box.ROUNDED)

    # Add columns
    table.add_column("Time", style="cyan", width=10)
    table.add_column("Type", style="green", width=15)
    table.add_column("Details", style="yellow")

    # Add rows for events
    for event in events:
        # Format time as HH:MM:SS.mmm
        timestamp = event.get("timestamp", time.time())
        time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
        time_str += f".{int((timestamp % 1) * 1000):03d}"

        # Get event type
        event_type = event.get("event_type", "unknown")

        # Build details string based on event type
        details = []

        if "key_press" in event_type and "key" in event:
            details.append(f"Key: {event['key']}")
            if "active_keys" in event and event["active_keys"]:
                details.append(f"Active: {', '.join(event['active_keys'])}")

        elif "mouse_move" in event_type:
            if "rel_x" in event and "rel_y" in event:
                details.append(
                    f"X: {event.get('rel_x', 0):.2f}, Y: {event.get('rel_y', 0):.2f}"
                )
            if "direction" in event:
                details.append(f"Dir: {event.get('direction', 'none')}")
            if "mouse_tracking_mode" in event:
                details.append(f"Mode: {event.get('mouse_tracking_mode', 'unknown')}")

        elif "mouse_click" in event_type:
            details.append(f"Button: {event.get('button', 'unknown')}")
            details.append(f"Pressed: {event.get('button_pressed', False)}")

        elif "mouse_scroll" in event_type:
            details.append(f"Direction: {event.get('direction', 'unknown')}")

        elif "button_press" in event_type or "button_release" in event_type:
            details.append(f"Button: {event.get('key', 'unknown')}")

        elif "axis_motion" in event_type:
            control = event.get("key", "unknown")
            details.append(f"Control: {control}")
            if "rel_x" in event:
                details.append(f"X: {event.get('rel_x', 0):.2f}")
            if "rel_y" in event:
                details.append(f"Y: {event.get('rel_y', 0):.2f}")

        # Generic fallback - show a few important keys
        if not details:
            for key in ["key", "button", "value", "direction", "active_keys"]:
                if key in event and event[key]:
                    details.append(f"{key.capitalize()}: {event[key]}")

        # Add the row
        table.add_row(time_str, event_type, ", ".join(details))

    return table


def core_event_handler(event_type: EventType, data: Any) -> None:
    """Handle events from the core event system."""
    # Process the event
    event_callback(data)


@app.command("events")
def monitor_events(
    event_types: List[str] = typer.Option(
        ["all"],
        "--type",
        "-t",
        help="Event types to monitor (all, key, mouse, button, controller)",
    ),
    count: int = typer.Option(
        10, "--count", "-c", help="(Ignorado) número máximo de eventos"
    ),
) -> None:
    """Monitor input events en tiempo real, igual que el WebSocket."""
    if headless_mode:
        init_headless_mode()

    import json
    from ...interaction_api_integration import get_interaction_api_integration
    from ...core.event_system import EventType, subscribe, unsubscribe

    # 1) Preparamos el integrador y parcheamos broadcast para imprimir JSON
    integration = get_interaction_api_integration()
    original_broadcast = integration._broadcast_event
    integration._broadcast_event = lambda payload: print(json.dumps(payload, default=str))

    # 2) Nos suscribimos a todos los eventos del bus
    handlers = []
    for evnt in EventType:
        handler = lambda data, evnt_type=evnt: integration._handle_core_event(evnt_type, data)
        subscribe(evnt, handler)
        handlers.append((evnt, handler))

    # 3) Set up exit mechanism with just key detection
    exit_event = threading.Event()

    # Start background listener for ESC/Q with minimal CPU usage
    def _key_listener():
        if sys.platform == "win32":
            import msvcrt
            while not exit_event.is_set():
                if msvcrt.kbhit():  # Check if key pressed without blocking
                    ch = msvcrt.getch()
                    if ch in (b"\x1b", b"q", b"Q"):  # ESC, q or Q
                        exit_event.set()
                        break
                time.sleep(0.01)  # Small sleep to prevent CPU hogging
        else:
            import termios, tty, select
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while not exit_event.is_set():
                    # Use select with a short timeout for non-blocking check
                    dr, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if dr:
                        ch = sys.stdin.read(1)
                        if ch in ("\x1b", "q", "Q"):  # ESC, q or Q
                            exit_event.set()
                            break
            finally:
                # Restore terminal settings
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    # Start key listener thread as daemon (will terminate when main thread exits)
    listener_thread = threading.Thread(target=_key_listener, daemon=True)
    listener_thread.start()

    print("⏺️  Monitoring events… Press ESC or Q to stop.")
    try:
        # Wait for exit_event with minimal CPU usage
        while not exit_event.is_set():
            time.sleep(0.01)
        print("\n🛑  Stopped monitoring.")
    finally:
        # Clean up subscriptions and restore original broadcast
        for evnt, handler in handlers:
            unsubscribe(evnt, handler)
        integration._broadcast_event = original_broadcast


@app.command("active-keys")
def monitor_active_keys() -> None:
    """Monitor active keys in real-time."""
    if headless_mode:
        init_headless_mode()

    try:
        console.print(
            f"[green]Monitoring active keys... Press [bold cyan]Ctrl+C[/bold cyan] to exit.[/green]"
        )

        # Start the live display
        with Live(refresh_per_second=10) as live:
            try:
                while True:
                    # Get current active keys
                    active_keys = InputDataAPI.get_active_keys()

                    # Create a table to display active keys
                    table = Table(title="Active Keys", box=box.ROUNDED)
                    table.add_column("Key", style="cyan")
                    table.add_column("State", style="green")

                    if not active_keys:
                        table.add_row("No keys active", "")
                    else:
                        for key in active_keys:
                            table.add_row(key, "PRESSED")

                    # Update the display
                    live.update(table)
                    time.sleep(0.1)
            except KeyboardInterrupt:
                # Exit on Ctrl+C
                pass

    except Exception as e:
        console.print(f"[bold red]Error monitoring active keys: {e}[/bold red]")


@app.command("mouse")
def monitor_mouse() -> None:
    """Monitor mouse movement and buttons in real-time."""
    if headless_mode:
        init_headless_mode()

    try:
        console.print(
            f"[green]Monitoring mouse... Press [bold cyan]Ctrl+C[/bold cyan] to exit.[/green]"
        )

        # Start the live display
        with Live(refresh_per_second=20) as live:
            try:
                while True:
                    # Create layout
                    layout = Layout()
                    layout.split_row(
                        Layout(name="position", ratio=1),
                        Layout(name="buttons", ratio=1),
                    )

                    # Position panel
                    x, y = InputDataAPI.get_mouse_position()
                    moving = InputDataAPI.is_mouse_moving()
                    direction = InputDataAPI.get_mouse_direction() if moving else "none"

                    position_text = (
                        f"X: [cyan]{x:.0f}[/cyan], Y: [cyan]{y:.0f}[/cyan]\n"
                    )
                    position_text += f"Moving: [{'green' if moving else 'yellow'}]{moving}[/{'green' if moving else 'yellow'}]\n"
                    position_text += f"Direction: [cyan]{direction}[/cyan]"

                    position_panel = Panel(
                        position_text, title="Mouse Position", border_style="blue"
                    )
                    layout["position"].update(position_panel)

                    # Buttons panel
                    left = InputDataAPI.get_mouse_button_state("left")
                    right = InputDataAPI.get_mouse_button_state("right")
                    middle = InputDataAPI.get_mouse_button_state("middle")

                    buttons_text = f"Left: [{'green' if left else 'red'}]{left}[/{'green' if left else 'red'}]\n"
                    buttons_text += f"Right: [{'green' if right else 'red'}]{right}[/{'green' if right else 'red'}]\n"
                    buttons_text += f"Middle: [{'green' if middle else 'red'}]{middle}[/{'green' if middle else 'red'}]"

                    buttons_panel = Panel(
                        buttons_text, title="Mouse Buttons", border_style="blue"
                    )
                    layout["buttons"].update(buttons_panel)

                    # Update the display
                    live.update(layout)
                    time.sleep(0.05)  # Faster refresh for mouse
            except KeyboardInterrupt:
                # Exit on Ctrl+C
                pass

    except Exception as e:
        console.print(f"[bold red]Error monitoring mouse: {e}[/bold red]")


@app.command("status")
def monitor_status() -> None:
    """Monitor overall application status in real-time."""
    if headless_mode:
        init_headless_mode()

    # Import interaction API
    from ...interaction_api import InputCollectorAPI

    try:
        console.print(
            f"[green]Monitoring application status... Press [bold cyan]Ctrl+C[/bold cyan] to exit.[/green]"
        )

        # Start the live display
        with Live(refresh_per_second=5) as live:
            try:
                while True:
                    # Get app state
                    app_state = InputCollectorAPI.get_application_state()

                    # Create layout
                    layout = Layout()
                    layout.split(
                        Layout(name="recording", size=3),
                        Layout(name="main"),
                    )

                    layout["main"].split_row(
                        Layout(name="left_column", ratio=1),
                        Layout(name="right_column", ratio=1),
                    )

                    layout["left_column"].split(
                        Layout(name="collector", size=8),
                        Layout(name="mouse", size=10),
                        Layout(name="keys", ratio=1),
                    )

                    layout["right_column"].split(
                        Layout(name="logging", size=8),
                        Layout(name="active", ratio=1),
                    )

                    # Recording status
                    recording = app_state.get("recording", False)
                    recording_panel = Panel(
                        f"[{'green' if recording else 'red'}]{'RECORDING' if recording else 'NOT RECORDING'}[/{'green' if recording else 'red'}]",
                        title="Recording Status",
                        border_style="green" if recording else "red",
                    )
                    layout["recording"].update(recording_panel)

                    # Collector info
                    collector = app_state.get("collector", {})
                    collector_type = collector.get("type", "Unknown")
                    collector_name = collector.get("name", "Unknown")
                    collector_panel = Panel(
                        f"Type: [cyan]{collector_type}[/cyan]\nName: [cyan]{collector_name}[/cyan]",
                        title="Current Collector",
                        border_style="blue",
                    )
                    layout["collector"].update(collector_panel)

                    # Mouse settings
                    mouse_settings = app_state.get("mouse_settings", {})
                    tracking_mode = mouse_settings.get("tracking_mode", "Unknown")
                    direction_only = mouse_settings.get("direction_only", False)
                    mouse_text = f"Mode: [cyan]{tracking_mode}[/cyan]\n"
                    mouse_text += f"Direction-only: [{'green' if direction_only else 'yellow'}]{direction_only}[/{'green' if direction_only else 'yellow'}]\n"

                    # Add mode-specific settings
                    if "delta_smoothing" in mouse_settings:
                        mouse_text += f"Delta Smoothing: [cyan]{mouse_settings['delta_smoothing']}[/cyan]\n"
                    if "joystick_sensitivity" in mouse_settings:
                        mouse_text += f"Joystick Sensitivity: [cyan]{mouse_settings['joystick_sensitivity']}[/cyan]\n"
                    if "angle_grouping" in mouse_settings:
                        mouse_text += f"Angle Grouping: [cyan]{mouse_settings['angle_grouping']}°[/cyan]"

                    mouse_panel = Panel(
                        mouse_text, title="Mouse Settings", border_style="blue"
                    )
                    layout["mouse"].update(mouse_panel)

                    # Tracked keys
                    tracked_keys = app_state.get("tracked_keys", [])
                    tracked_keys_text = "\n".join(
                        [f"- {key}" for key in tracked_keys[:15]]
                    )
                    if len(tracked_keys) > 15:
                        tracked_keys_text += f"\n... and {len(tracked_keys) - 15} more"

                    keys_panel = Panel(
                        tracked_keys_text or "No keys being tracked",
                        title=f"Tracked Keys ({len(tracked_keys)})",
                        border_style="blue",
                    )
                    layout["keys"].update(keys_panel)

                    # Logging status
                    logging_status = app_state.get("logging", {})
                    json_enabled = logging_status.get("json_enabled", False)
                    csv_enabled = logging_status.get("csv_enabled", False)
                    csv_path = logging_status.get("csv_path", "Not set")

                    logging_text = f"JSON Logging: [{'green' if json_enabled else 'red'}]{json_enabled}[/{'green' if json_enabled else 'red'}]\n"
                    logging_text += f"CSV Logging: [{'green' if csv_enabled else 'red'}]{csv_enabled}[/{'green' if csv_enabled else 'red'}]\n"

                    if csv_enabled:
                        logging_text += f"CSV Path: [cyan]{csv_path}[/cyan]"

                    logging_panel = Panel(
                        logging_text, title="Logging Status", border_style="blue"
                    )
                    layout["logging"].update(logging_panel)

                    # Active keys
                    active_keys = app_state.get("active_keys", [])
                    if not active_keys:
                        active_text = "No keys currently active"
                    else:
                        active_text = "\n".join([f"- {key}" for key in active_keys])

                    active_panel = Panel(
                        active_text,
                        title="Active Keys",
                        border_style="green" if active_keys else "yellow",
                    )
                    layout["active"].update(active_panel)

                    # Update the display
                    live.update(layout)
                    time.sleep(0.2)  # Slower refresh for status
            except KeyboardInterrupt:
                # Exit on Ctrl+C
                pass

    except Exception as e:
        console.print(f"[bold red]Error monitoring status: {e}[/bold red]")
