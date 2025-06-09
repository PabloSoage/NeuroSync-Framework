"""
Monitoring commands for the CLI application.

These commands allow monitoring input events in real-time.
"""

import sys
import threading
import time
from typing import List, Callable, Any
import typer
from rich.console import Console
from rich.panel import Panel
from rich import box

# Import shared config instead of from cli_app
from ..cli_config import headless_mode, init_headless_mode
from ...core.event_system import EventType, subscribe, unsubscribe
from ...interaction_api_integration import get_interaction_api_integration
from ...interaction_api import InputCollectorAPI

app = typer.Typer(no_args_is_help=True)


def _run_monitor(allowed: List[str], show_keys: bool = True) -> None:
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
    integration = get_interaction_api_integration()
    original = integration._broadcast_event

    def printer(event_dict: dict) -> None:
        et = event_dict.get("event_type", event_dict.get("type", "")).lower()
        if "all" not in allowed and not any(k in et for k in allowed):
            return
        try:
            # Timestamp
            ts = event_dict.get("timestamp", time.time())
            tstr = (
                time.strftime("%H:%M:%S", time.localtime(ts))
                + f".{int((ts%1)*1000):03d}"
            )
            et_disp = event_dict.get("event_type", event_dict.get("type", "UNKNOWN"))

            # Teclas (only if requested)
            keys_str = ""
            if show_keys:
                keys = event_dict.get("keys", [])
                keys_str = f"[yellow]Keys:[/yellow] {','.join(keys)}" if keys else ""

            # Movimiento del ratón
            mv = event_dict.get("movement", {})
            mv_status = mv.get("status", "")
            mv_str = f"[cyan]Mouse:[/cyan] {mv_status}" if mv_status else ""

            # Botones
            btns = event_dict.get("click", {}).get("buttons", [])
            btns_str = f"[magenta]Buttons:[/magenta] {','.join(btns)}" if btns else ""

            # Montar línea
            parts = [f"[dim]{tstr}[/dim]", f"[green]{et_disp}[/green]"]
            for p in (keys_str, mv_str, btns_str):
                if p:
                    parts.append(p)
            console.print(" | ".join(parts))
        except Exception as e:
            console.print(f"[red]Format error:[/red] {e}")
            console.print(event_dict)

    setattr(integration, "_broadcast_event", printer)
    handlers = []
    for ev in EventType:

        def create_handler(event_type: EventType) -> Callable[[Any], None]:
            return lambda data: integration._handle_core_event(event_type, data)

        h = create_handler(ev)
        subscribe(ev, h)
        handlers.append((ev, h))

    stop = threading.Event()

    def key_listener() -> None:
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
                    dr, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if dr and sys.stdin.read(1) in ("\x1b", "q", "Q"):
                        stop.set()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    threading.Thread(target=key_listener, daemon=True).start()

    try:
        while not stop.is_set():
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        for ev, h in handlers:
            unsubscribe(ev, h)
        setattr(integration, "_broadcast_event", original)
        console.print("[bold red]🛑 Stopped monitoring[/bold red]")


@app.command("events")
def monitor_events() -> None:
    """Monitor all input events."""
    _run_monitor(["all"])


@app.command("active-keys")
def monitor_active_keys() -> None:
    """Monitor only keyboard events."""
    # Must be in keyboard_mouse mode
    state = InputCollectorAPI.get_application_state()
    if state.get("collector", {}).get("type") != "keyboard_mouse":
        Console().print("[bold red]Keyboard & Mouse collector is not active[/bold red]")
        return
    _run_monitor(["key"])


@app.command("mouse")
def monitor_mouse() -> None:
    """Monitor only mouse events."""
    # Must be in keyboard_mouse mode
    state = InputCollectorAPI.get_application_state()
    if state.get("collector", {}).get("type") != "keyboard_mouse":
        Console().print("[bold red]Keyboard & Mouse collector is not active[/bold red]")
        return
    _run_monitor(["mouse"], show_keys=False)


@app.command("controller")
def monitor_controller() -> None:
    """Monitor PS4 controller events."""
    # Must be in ps4_controller mode and connected
    state = InputCollectorAPI.get_application_state()
    c = state.get("collector", {})
    if c.get("type") != "ps4_controller":
        Console().print("[bold red]PS4 Controller collector is not active[/bold red]")
        return
    if not c.get("connected", False) and not state.get("controller_connected", False):
        Console().print("[bold yellow]No PS4 controller connected[/bold yellow]")
        return
    # Only show controller events (button/axis)
    _run_monitor(["button", "axis"], show_keys=False)


@app.command("status")
def monitor_status() -> None:
    """Monitor application status."""
    _run_monitor(["state"])
