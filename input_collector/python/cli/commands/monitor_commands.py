"""
Monitoring commands for the CLI application.

These commands allow monitoring input events in real-time.
"""

import sys
import threading
import time
from typing import List, Callable, Any, Dict, Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich import box

# Import shared config instead of from cli_app
from ..cli_config import headless_mode, init_headless_mode
from ...core.event_system import EventType, subscribe, unsubscribe, dispatch
from ...interaction_api_integration import get_interaction_api_integration
from ...interaction_api import InputCollectorAPI

app = typer.Typer(no_args_is_help=True)


class PS4ControllerMonitor:
    """Monitor for PS4 controller events that mimics the visualizer display."""
    
    def __init__(self):
        self.console = Console()
        self.button_states: Dict[str, bool] = {}
        self.stick_positions = {"left": (0.0, 0.0), "right": (0.0, 0.0)}
        self.trigger_values = {"left": 0, "right": 0}
        self.recent_events = []
        self.max_events = 20
        
        # Use the core event system instead of direct collector access
        self.event_handlers = []
        
        # Event-driven updates instead of polling
        self.display_dirty = True
        self.display_lock = threading.Lock()
        
    def start_monitoring(self):
        """Start monitoring using the core event system."""
        try:
            # Subscribe to INPUT events from the core event system
            def handle_input_event(event_data):
                self.process_event_from_core(event_data)
            
            # Subscribe to the INPUT event type
            subscribe(EventType.INPUT, handle_input_event)
            self.event_handlers.append((EventType.INPUT, handle_input_event))
            
            self.recent_events.append("[green]Connected to core event system[/green]")
            self.recent_events.append("[yellow]Waiting for PS4 controller events...[/yellow]")
            self.display_dirty = True
            
            return True
        except Exception as e:
            self.recent_events.append(f"[red]Error connecting to event system: {str(e)}[/red]")
            self.display_dirty = True
            return False
    
    def stop_monitoring(self):
        """Stop monitoring by unsubscribing from events."""
        for event_type, handler in self.event_handlers:
            try:
                unsubscribe(event_type, handler)
            except Exception as e:
                self.recent_events.append(f"[red]Error unsubscribing: {str(e)}[/red]")
        self.event_handlers.clear()
        self.recent_events.append("[yellow]Disconnected from event system[/yellow]")
        self.display_dirty = True
    
    def process_event_from_core(self, event_data):
        """Process an event from the core event system."""
        try:
            # Handle different event data formats
            if hasattr(event_data, 'event_type'):
                # InputData object
                input_data = event_data
            elif isinstance(event_data, dict):
                # Dictionary format - convert to object-like access
                class EventObj:
                    def __init__(self, data):
                        for k, v in data.items():
                            setattr(self, k, v)
                input_data = EventObj(event_data)
            else:
                # Unknown format
                with self.display_lock:
                    self.recent_events.append(f"[red]Unknown event format: {type(event_data)}[/red]")
                    self.display_dirty = True
                return
            
            # Check if this is a PS4 controller event
            event_type = getattr(input_data, 'event_type', '')
            
            # Format timestamp like in visualizer
            timestamp = getattr(input_data, 'timestamp', time.time())
            ts_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
            ms = int((timestamp - int(timestamp)) * 1000)
            formatted_time = f"{ts_str}.{ms:03d}"
            
            with self.display_lock:
                if event_type in ["button_press", "button_release"]:
                    key = getattr(input_data, 'key', '')
                    if key:
                        # Update button state
                        self.button_states[key] = (event_type == "button_press")
                        
                        # Add to log with color like visualizer
                        if event_type == "button_press":
                            log_entry = f"[dim]{formatted_time}[/dim] - [green]Button pressed: {key}[/green]"
                        else:
                            log_entry = f"[dim]{formatted_time}[/dim] - [yellow]Button released: {key}[/yellow]"
                        
                        self.recent_events.append(log_entry)
                        self.display_dirty = True
                
                elif event_type == "axis_motion":
                    key = getattr(input_data, 'key', '')
                    rel_x = getattr(input_data, 'rel_x', 0)
                    rel_y = getattr(input_data, 'rel_y', 0)
                    
                    if key == "Left_Stick_X":
                        prev_pos = self.stick_positions["left"]
                        self.stick_positions["left"] = (rel_x, rel_y)
                        
                        # Enhanced logging with "return to zero" detection
                        current_magnitude = abs(rel_x) + abs(rel_y)
                        prev_magnitude = abs(prev_pos[0]) + abs(prev_pos[1])
                        
                        # Log if: significant movement OR crossing back to zero
                        should_log = (
                            current_magnitude > 0.02 or  # Significant movement
                            (prev_magnitude > 0.02 and current_magnitude == 0.0)  # Return to zero
                        )
                        
                        if should_log:
                            if current_magnitude == 0.0:
                                # Special message for return to zero
                                log_entry = f"[dim]{formatted_time}[/dim] - [cyan]Left stick: returned to center (0%, 0%)[/cyan]"
                                self.recent_events.append(log_entry)
                                self.display_dirty = True
                            else:
                                log_entry = f"[dim]{formatted_time}[/dim] - [cyan]Left stick: x={rel_x:.3f} ({int(abs(rel_x)*100)}%), y={rel_y:.3f} ({int(abs(rel_y)*100)}%)[/cyan]"
                                self.recent_events.append(log_entry)
                                self.display_dirty = True
                        else:
                            # Always mark dirty for state table update even if not logging
                            self.display_dirty = True
                    
                    elif key == "Right_Stick_X":
                        prev_pos = self.stick_positions["right"]
                        self.stick_positions["right"] = (rel_x, rel_y)
                        
                        # Enhanced logging with "return to zero" detection
                        current_magnitude = abs(rel_x) + abs(rel_y)
                        prev_magnitude = abs(prev_pos[0]) + abs(prev_pos[1])
                        
                        # Log if: significant movement OR crossing back to zero
                        should_log = (
                            current_magnitude > 0.02 or  # Significant movement
                            (prev_magnitude > 0.02 and current_magnitude == 0.0)  # Return to zero
                        )
                        
                        if should_log:
                            if current_magnitude == 0.0:
                                # Special message for return to zero
                                log_entry = f"[dim]{formatted_time}[/dim] - [cyan]Right stick: returned to center (0%, 0%)[/cyan]"
                                self.recent_events.append(log_entry)
                                self.display_dirty = True
                            else:
                                log_entry = f"[dim]{formatted_time}[/dim] - [cyan]Right stick: x={rel_x:.3f} ({int(abs(rel_x)*100)}%), y={rel_y:.3f} ({int(abs(rel_y)*100)}%)[/cyan]"
                                self.recent_events.append(log_entry)
                                self.display_dirty = True
                        else:
                            # Always mark dirty for state table update even if not logging
                            self.display_dirty = True
                    
                    elif key == "Left_Trigger":
                        prev_value = self.trigger_values["left"] / 32767.0 if self.trigger_values["left"] else 0
                        self.trigger_values["left"] = int(rel_x * 32767)
                        
                        # Enhanced logging with "return to zero" detection
                        should_log = (
                            rel_x > 0.01 or  # Significant pressure
                            (prev_value > 0.01 and rel_x == 0.0)  # Return to zero
                        )
                        
                        if should_log:
                            if rel_x == 0.0:
                                # Special message for return to zero
                                log_entry = f"[dim]{formatted_time}[/dim] - [bright_yellow]Left trigger: released (0%)[/bright_yellow]"
                                self.recent_events.append(log_entry)
                                self.display_dirty = True
                            else:
                                log_entry = f"[dim]{formatted_time}[/dim] - [bright_yellow]Left trigger: {rel_x:.3f} ({int(rel_x*100)}%)[/bright_yellow]"
                                self.recent_events.append(log_entry)
                                self.display_dirty = True
                        else:
                            # Always mark dirty for state table update even if not logging
                            self.display_dirty = True
                    
                    elif key == "Right_Trigger":
                        prev_value = self.trigger_values["right"] / 32767.0 if self.trigger_values["right"] else 0
                        self.trigger_values["right"] = int(rel_x * 32767)
                        
                        # Enhanced logging with "return to zero" detection
                        should_log = (
                            rel_x > 0.01 or  # Significant pressure
                            (prev_value > 0.01 and rel_x == 0.0)  # Return to zero
                        )
                        
                        if should_log:
                            if rel_x == 0.0:
                                # Special message for return to zero
                                log_entry = f"[dim]{formatted_time}[/dim] - [bright_yellow]Right trigger: released (0%)[/bright_yellow]"
                                self.recent_events.append(log_entry)
                                self.display_dirty = True
                            else:
                                log_entry = f"[dim]{formatted_time}[/dim] - [bright_yellow]Right trigger: {rel_x:.3f} ({int(rel_x*100)}%)[/bright_yellow]"
                                self.recent_events.append(log_entry)
                                self.display_dirty = True
                        else:
                            # Always mark dirty for state table update even if not logging
                            self.display_dirty = True
                
                elif event_type == "controller_connected":
                    controller_name = getattr(input_data, 'key', 'Controller')
                    log_entry = f"[dim]{formatted_time}[/dim] - [green]Controller connected: {controller_name}[/green]"
                    self.recent_events.append(log_entry)
                    self.display_dirty = True
                
                elif event_type == "controller_disconnected":
                    log_entry = f"[dim]{formatted_time}[/dim] - [red]Controller disconnected[/red]"
                    self.recent_events.append(log_entry)
                    # Reset states
                    self.button_states = {}
                    self.stick_positions = {"left": (0.0, 0.0), "right": (0.0, 0.0)}
                    self.trigger_values = {"left": 0, "right": 0}
                    self.display_dirty = True
                
                # Keep only recent events
                if len(self.recent_events) > self.max_events * 2:
                    self.recent_events = self.recent_events[-self.max_events:]
                    
        except Exception as e:
            # Add error to log
            formatted_time = time.strftime("%H:%M:%S.%f", time.localtime())[:12]
            with self.display_lock:
                log_entry = f"[dim]{formatted_time}[/dim] - [red]Error: {str(e)}[/red]"
                self.recent_events.append(log_entry)
                self.display_dirty = True
    
    def create_display(self) -> Layout:
        """Create the display layout matching PS4 visualizer."""
        with self.display_lock:
            layout = Layout()
            
            # Split into main sections
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="main"),
            )
            
            # Split main into state and logs
            layout["main"].split_row(
                Layout(name="state", ratio=1),
                Layout(name="logs", ratio=2),
            )
            
            # Header
            layout["header"].update(
                Panel(
                    "[bold cyan]PS4 Controller Monitor[/bold cyan] - Press ESC or Q to stop",
                    box=box.ROUNDED
                )
            )
            
            # State panel
            state_table = self.create_state_table()
            layout["state"].update(
                Panel(state_table, title="Controller State", box=box.ROUNDED)
            )
            
            # Logs panel
            logs_panel = self.create_logs_panel()
            layout["logs"].update(
                Panel(logs_panel, title="Event Log", box=box.ROUNDED)
            )
            
            return layout
    
    def create_state_table(self) -> Table:
        """Create the controller state table."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="bold white")
        table.add_column("Value", style="green")
        
        # Active buttons
        active_buttons = [btn for btn, state in self.button_states.items() if state]
        active_buttons_text = ", ".join(active_buttons) if active_buttons else "None"
        table.add_row("Active Buttons:", active_buttons_text)
        
        table.add_row("", "")  # Spacer
        
        # Joysticks
        left_x, left_y = self.stick_positions["left"]
        right_x, right_y = self.stick_positions["right"]
        
        table.add_row("[bold]Joysticks:", "")
        table.add_row("  Left X:", f"{int(abs(left_x) * 100)}%")
        table.add_row("  Left Y:", f"{int(abs(left_y) * 100)}%")
        table.add_row("  Right X:", f"{int(abs(right_x) * 100)}%")
        table.add_row("  Right Y:", f"{int(abs(right_y) * 100)}%")
        
        table.add_row("", "")  # Spacer
        
        # Triggers
        left_trigger = self.trigger_values["left"] / 32767.0 if self.trigger_values["left"] else 0
        right_trigger = self.trigger_values["right"] / 32767.0 if self.trigger_values["right"] else 0
        
        table.add_row("[bold]Triggers:", "")
        table.add_row("  Left:", f"{int(left_trigger * 100)}%")
        table.add_row("  Right:", f"{int(right_trigger * 100)}%")
        
        return table
    
    def create_logs_panel(self) -> str:
        """Create the logs display."""
        if not self.recent_events:
            return "[dim]No events yet...[/dim]"
        
        log_lines = []
        for event in self.recent_events[-self.max_events:]:
            log_lines.append(event)
        
        return "\n".join(log_lines)
    
    def is_display_dirty(self) -> bool:
        """Check if display needs updating."""
        with self.display_lock:
            return self.display_dirty
    
    def mark_display_clean(self) -> None:
        """Mark display as clean (updated)."""
        with self.display_lock:
            self.display_dirty = False


def _run_monitor(allowed: List[str], show_keys: bool = True) -> None:
    """Run general event monitor."""
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


def _run_ps4_controller_monitor() -> None:
    """Run PS4 controller monitor with visualizer-like display."""
    if headless_mode:
        init_headless_mode()
    
    monitor = PS4ControllerMonitor()
    
    # Add initial message about PS4 controller mode
    monitor.recent_events.append("[green]PS4 Controller monitoring starting...[/green]")
    
    # Start monitoring using core event system
    if not monitor.start_monitoring():
        console = Console()
        console.print("[bold red]Failed to connect to event system[/bold red]")
        console.print("[yellow]The core event system may not be running properly[/yellow]")
        return
    
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
        # Start with immediate display
        with Live(monitor.create_display(), refresh_per_second=60) as live:
            monitor.mark_display_clean()
            
            while not stop.is_set():
                # Only update display when there are new events (event-driven)
                if monitor.is_display_dirty():
                    live.update(monitor.create_display())
                    monitor.mark_display_clean()
                
                # Short sleep to prevent busy waiting but still be responsive
                time.sleep(0.016)  # ~60fps check rate, but only update when dirty
                
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop_monitoring()


@app.command("events")
def monitor_events() -> None:
    """Monitor all input events."""
    # Check if PS4 controller is active - if so, use enhanced display
    state = InputCollectorAPI.get_application_state()
    if state.get("collector", {}).get("type") == "ps4_controller":
        _run_ps4_controller_monitor()
    else:
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
    """Monitor PS4 controller events with enhanced display."""
    # Check if PS4 controller is active
    state = InputCollectorAPI.get_application_state()
    if state.get("collector", {}).get("type") != "ps4_controller":
        Console().print("[bold red]PS4 Controller collector is not active[/bold red]")
        Console().print("[yellow]Use 'control collectors-set ps4_controller' to activate it[/yellow]")
        return
    
    _run_ps4_controller_monitor()


@app.command("status")
def monitor_status() -> None:
    """Monitor application status."""
    _run_monitor(["state"])
