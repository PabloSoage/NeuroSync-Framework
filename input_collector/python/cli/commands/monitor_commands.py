"""
Monitoring commands for the CLI application.

These commands allow monitoring input events in real-time.
"""

import sys
import threading
import time
from typing import List
import typer
from rich.console import Console
from rich.panel import Panel
from rich import box

# Import shared config instead of from cli_app
from ..cli_config import headless_mode, init_headless_mode
from ...core.event_system import EventType, subscribe, unsubscribe
from ...interaction_api_integration import get_interaction_api_integration

app = typer.Typer()


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
    """Monitor input events en tiempo real, con formato elegante."""
    if headless_mode:
        init_headless_mode()

    console = Console()
    console.print(
        Panel(
            "[bold cyan]Input Collector Event Monitor[/bold cyan]\n"
            "[yellow]Press ESC or Q to stop.[/yellow]",
            box=box.ROUNDED,
            expand=False,
        )
    )

    # 1) Interceptamos el broadcast original para formatear y mostrar cada evento
    integration = get_interaction_api_integration()
    original_broadcast = integration._broadcast_event

    def format_and_print(payload: dict) -> None:
        try:
            # Timestamp
            ts = payload.get("timestamp", time.time())
            tstr = time.strftime("%H:%M:%S", time.localtime(ts)) + f".{int((ts%1)*1000):03d}"

            # Tipo de evento
            et = payload.get("event_type", payload.get("type", "UNKNOWN"))

            # Teclas
            keys = payload.get("keys", [])
            keys_str = f"[yellow]Keys:[/yellow] {','.join(keys)}" if keys else ""

            # Movimiento del ratón
            mv = payload.get("movement", {})
            mv_status = mv.get("status", "")
            mv_str = f"[cyan]Mouse:[/cyan] {mv_status}" if mv_status else ""

            # Botones
            btns = payload.get("click", {}).get("buttons", [])
            btns_str = f"[magenta]Buttons:[/magenta] {','.join(btns)}" if btns else ""

            # Montar línea
            parts = [f"[dim]{tstr}[/dim]", f"[green]{et}[/green]"]
            for p in (keys_str, mv_str, btns_str):
                if p:
                    parts.append(p)
            console.print(" | ".join(parts))
        except Exception as e:
            console.print(f"[red]Format error:[/red] {e}")
            console.print(payload)

    integration._broadcast_event = format_and_print

    # 2) Suscribirnos a todos los eventos
    handlers = []
    for ev in EventType:
        h = lambda data, et=ev: integration._handle_core_event(et, data)
        subscribe(ev, h)
        handlers.append((ev, h))

    # 3) Listener de ESC/Q para salir
    stop = threading.Event()

    def key_listener():
        if sys.platform == "win32":
            import msvcrt
            while not stop.is_set():
                if msvcrt.kbhit() and msvcrt.getch() in (b"\x1b", b"q", b"Q"):
                    stop.set()
                time.sleep(0.01)
        else:
            import tty, termios, select
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while not stop.is_set():
                    dr,_,_ = select.select([sys.stdin],[],[],0.1)
                    if dr and sys.stdin.read(1) in ("\x1b","q","Q"):
                        stop.set()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    threading.Thread(target=key_listener, daemon=True).start()

    # 4) Esperar hasta tecla de salida
    try:
        while not stop.is_set():
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        # Limpieza
        for ev,h in handlers:
            unsubscribe(ev, h)
        integration._broadcast_event = original_broadcast
        console.print("[bold red]🛑 Stopped monitoring[/bold red]")


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
