"""
Interaction commands for the CLI application.

These commands allow controlling the input collector application.
"""

import typer
from rich import box
from rich.console import Console
from rich.table import Table

# Import shared config instead of from cli_app
from ..cli_config import headless_mode, init_headless_mode
from ...interaction_api import InputCollectorAPI

console = Console()
app = typer.Typer()


@app.command("recording")
def recording(
    action: str = typer.Argument(
        ..., help="Action to take (start, stop, toggle, status)"
    )
) -> None:
    """Control recording state."""
    if headless_mode:
        init_headless_mode()

    try:
        if action == "start":
            success = InputCollectorAPI.start_recording()
            if success:
                console.print("[green]Recording started[/green]")
            else:
                status = InputCollectorAPI.get_last_operation_status()
                console.print(
                    f"[bold red]Failed to start recording: {status.get('message', '')}[/bold red]"
                )
        elif action == "stop":
            success = InputCollectorAPI.stop_recording()
            if success:
                console.print("[green]Recording stopped[/green]")
            else:
                status = InputCollectorAPI.get_last_operation_status()
                console.print(
                    f"[bold red]Failed to stop recording: {status.get('message', '')}[/bold red]"
                )
        elif action == "toggle":
            success = InputCollectorAPI.toggle_recording()
            if success:
                is_recording = InputCollectorAPI.is_recording()
                state = "started" if is_recording else "stopped"
                console.print(f"[green]Recording {state}[/green]")
            else:
                status = InputCollectorAPI.get_last_operation_status()
                console.print(
                    f"[bold red]Failed to toggle recording: {status.get('message', '')}[/bold red]"
                )
        elif action == "status":
            is_recording = InputCollectorAPI.is_recording()
            if is_recording:
                console.print("[green]Recording is active[/green]")
            else:
                console.print("[yellow]Recording is not active[/yellow]")
        else:
            console.print(
                f"[bold red]Invalid action: {action}. Must be one of: start, stop, toggle, status[/bold red]"
            )
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[bold red]Error controlling recording: {e}[/bold red]")


@app.command("logging")
def logging(
    log_type: str = typer.Argument(..., help="Log type (json, csv, status)"),
    action: str = typer.Option(
        None, "--action", "-a", help="Action to take (enable, disable)"
    ),
    filepath: str = typer.Option(None, "--filepath", "-f", help="Path for CSV file"),
) -> None:
    """Control logging settings."""
    if headless_mode:
        init_headless_mode()

    try:
        if log_type == "json":
            if action == "enable":
                success = InputCollectorAPI.enable_json_logging(True)
                if success:
                    console.print("[green]JSON logging enabled[/green]")
                else:
                    status = InputCollectorAPI.get_last_operation_status()
                    console.print(
                        f"[bold red]Failed to enable JSON logging: {status.get('message', '')}[/bold red]"
                    )
            elif action == "disable":
                success = InputCollectorAPI.enable_json_logging(False)
                if success:
                    console.print("[green]JSON logging disabled[/green]")
                else:
                    status = InputCollectorAPI.get_last_operation_status()
                    console.print(
                        f"[bold red]Failed to disable JSON logging: {status.get('message', '')}[/bold red]"
                    )
            elif action is None:
                state = InputCollectorAPI.get_logging_state()
                enabled = state.get("json_enabled", False)
                if enabled:
                    console.print("[green]JSON logging is enabled[/green]")
                else:
                    console.print("[yellow]JSON logging is disabled[/yellow]")
            else:
                console.print(
                    f"[bold red]Invalid action: {action}. Must be one of: enable, disable[/bold red]"
                )
                raise typer.Exit(1)
        elif log_type == "csv":
            if action == "enable":
                success = InputCollectorAPI.enable_csv_logging(True, filepath)
                if success:
                    console.print("[green]CSV logging enabled[/green]")
                else:
                    status = InputCollectorAPI.get_last_operation_status()
                    console.print(
                        f"[bold red]Failed to enable CSV logging: {status.get('message', '')}[/bold red]"
                    )
            elif action == "disable":
                success = InputCollectorAPI.enable_csv_logging(False)
                if success:
                    console.print("[green]CSV logging disabled[/green]")
                else:
                    status = InputCollectorAPI.get_last_operation_status()
                    console.print(
                        f"[bold red]Failed to disable CSV logging: {status.get('message', '')}[/bold red]"
                    )
            elif action == "set-path" and filepath:
                success = InputCollectorAPI.set_csv_path(filepath)
                if success:
                    console.print(f"[green]CSV path set to: {filepath}[/green]")
                else:
                    status = InputCollectorAPI.get_last_operation_status()
                    console.print(
                        f"[bold red]Failed to set CSV path: {status.get('message', '')}[/bold red]"
                    )
            elif action is None:
                state = InputCollectorAPI.get_logging_state()
                enabled = state.get("csv_enabled", False)
                path = state.get("csv_path", "Not set")

                if enabled:
                    console.print(f"[green]CSV logging is enabled[/green]")
                    console.print(f"CSV path: [cyan]{path}[/cyan]")
                else:
                    console.print("[yellow]CSV logging is disabled[/yellow]")
                    if path != "Not set":
                        console.print(f"CSV path: [cyan]{path}[/cyan]")
            else:
                console.print(
                    f"[bold red]Invalid action: {action}. Must be one of: enable, disable, set-path[/bold red]"
                )
                raise typer.Exit(1)
        elif log_type == "status":
            state = InputCollectorAPI.get_logging_state()

            # Create a table for the logging state
            table = Table(title="Logging State", box=box.ROUNDED)

            # Add columns
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            # Add rows
            table.add_row("JSON Logging", str(state.get("json_enabled", False)))
            table.add_row("CSV Logging", str(state.get("csv_enabled", False)))
            table.add_row("CSV Path", state.get("csv_path", "Not set"))

            console.print(table)
        else:
            console.print(
                f"[bold red]Invalid log type: {log_type}. Must be one of: json, csv, status[/bold red]"
            )
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[bold red]Error controlling logging: {e}[/bold red]")


@app.command("collectors")
def collectors(
    action: str = typer.Argument(
        ..., help="Action to take (list, current, switch, scan)"
    ),
    collector_type: str = typer.Option(
        None, "--type", "-t", help="Collector type to switch to"
    ),
    controller_index: int = typer.Option(
        None, "--index", "-i", help="Controller index to connect to"
    ),
) -> None:
    """Manage input collectors."""
    if headless_mode:
        init_headless_mode()

    try:
        if action == "list":
            collectors_list = InputCollectorAPI.get_available_collectors()

            if not collectors_list:
                console.print("[yellow]No collectors available[/yellow]")
                return

            # Create a table for the collectors
            table = Table(title="Available Collectors", box=box.ROUNDED)

            # Add columns
            table.add_column("Type", style="cyan")
            table.add_column("Display Name", style="green")

            # Add rows
            for collector in collectors_list:
                table.add_row(collector.get("type", ""), collector.get("name", ""))

            console.print(table)
        elif action == "current":
            collector = InputCollectorAPI.get_current_collector()

            # Create a table for the collector
            table = Table(title="Current Collector", box=box.ROUNDED)

            # Add columns
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            # Add rows
            table.add_row("Type", collector.get("type", ""))
            table.add_row("Display Name", collector.get("name", ""))

            # Add capabilities if available
            if "capabilities" in collector:
                capabilities = collector["capabilities"]
                table.add_row("Capabilities", ", ".join(capabilities))

            console.print(table)
        elif action == "switch" and collector_type:
            success = InputCollectorAPI.switch_collector(collector_type)

            if success:
                console.print(f"[green]Switched to collector: {collector_type}[/green]")
            else:
                status = InputCollectorAPI.get_last_operation_status()
                console.print(
                    f"[bold red]Failed to switch collector: {status.get('message', '')}[/bold red]"
                )
        elif action == "scan":
            controllers = InputCollectorAPI.scan_controllers()

            if not controllers:
                console.print("[yellow]No controllers found[/yellow]")
                return

            # Create a table for the controllers
            table = Table(title="Available Controllers", box=box.ROUNDED)

            # Add columns
            table.add_column("Index", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Is PS4", style="yellow")

            # Add rows
            for controller in controllers:
                table.add_row(
                    str(controller.get("index", "")),
                    controller.get("name", ""),
                    str(controller.get("is_ps4", False)),
                )

            console.print(table)
        elif action == "connect" and controller_index is not None:
            success = InputCollectorAPI.connect_controller(controller_index)

            if success:
                console.print(
                    f"[green]Connected to controller at index: {controller_index}[/green]"
                )
            else:
                status = InputCollectorAPI.get_last_operation_status()
                console.print(
                    f"[bold red]Failed to connect to controller: {status.get('message', '')}[/bold red]"
                )
        else:
            if action not in ["list", "current", "switch", "scan", "connect"]:
                console.print(
                    f"[bold red]Invalid action: {action}. Must be one of: list, current, switch, scan, connect[/bold red]"
                )
            else:
                console.print("[bold red]Missing required arguments[/bold red]")
                if action == "switch":
                    console.print("For 'switch' action, provide --type")
                elif action == "connect":
                    console.print("For 'connect' action, provide --index")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[bold red]Error managing collectors: {e}[/bold red]")


@app.command("mouse")
def mouse(
    action: str = typer.Argument(
        ..., help="Action to take (mode, settings, tracking-modes)"
    ),
    mode: str = typer.Option(
        None, "--mode", "-m", help="Tracking mode to set (joystick, delta, angle, axis)"
    ),
    direction_only: bool = typer.Option(
        None, "--direction-only", "-d", help="Whether to use direction-only mode"
    ),
    delta_smoothing: float = typer.Option(
        None, "--delta-smoothing", help="Smoothing factor for delta tracking (0-90)"
    ),
    joystick_sensitivity: float = typer.Option(
        None,
        "--joystick-sensitivity",
        help="Sensitivity for joystick tracking (10-200)",
    ),
    angle_grouping: int = typer.Option(
        None, "--angle-grouping", help="Angle grouping in degrees (1-90)"
    ),
) -> None:
    """Configure mouse tracking."""
    if headless_mode:
        init_headless_mode()

    try:
        if action == "mode":
            if mode is not None:
                success = InputCollectorAPI.set_mouse_tracking_mode(
                    mode, direction_only
                )

                if success:
                    dir_only_status = ""
                    if direction_only is not None:
                        dir_only_status = f" (direction-only: {direction_only})"

                    console.print(
                        f"[green]Mouse tracking mode set to: {mode}{dir_only_status}[/green]"
                    )
                else:
                    status = InputCollectorAPI.get_last_operation_status()
                    console.print(
                        f"[bold red]Failed to set mouse tracking mode: {status.get('message', '')}[/bold red]"
                    )
            else:
                settings = InputCollectorAPI.get_mouse_settings()

                mode_value = settings.get("tracking_mode", "Unknown")
                dir_only_value = settings.get("direction_only", False)

                console.print(
                    f"Current mode: [cyan]{mode_value}[/cyan] (direction-only: [cyan]{dir_only_value}[/cyan])"
                )
        elif action == "settings":
            # If any settings are provided, update them
            if any(
                param is not None
                for param in [delta_smoothing, joystick_sensitivity, angle_grouping]
            ):
                success = InputCollectorAPI.set_mouse_settings(
                    delta_smoothing, joystick_sensitivity, angle_grouping
                )

                if success:
                    console.print("[green]Mouse settings updated[/green]")
                else:
                    status = InputCollectorAPI.get_last_operation_status()
                    console.print(
                        f"[bold red]Failed to update mouse settings: {status.get('message', '')}[/bold red]"
                    )

            # Show current settings
            settings = InputCollectorAPI.get_mouse_settings()

            # Create a table for the settings
            table = Table(title="Mouse Settings", box=box.ROUNDED)

            # Add columns
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="green")

            # Add rows
            table.add_row("Tracking Mode", settings.get("tracking_mode", "Unknown"))
            table.add_row("Direction Only", str(settings.get("direction_only", False)))
            table.add_row(
                "Delta Smoothing", str(settings.get("delta_smoothing", "N/A"))
            )
            table.add_row(
                "Joystick Sensitivity", str(settings.get("joystick_sensitivity", "N/A"))
            )
            table.add_row("Angle Grouping", str(settings.get("angle_grouping", "N/A")))

            console.print(table)
        elif action == "tracking-modes":
            modes = InputCollectorAPI.get_available_tracking_modes(direction_only)

            if direction_only is not None:
                console.print(f"Available modes for direction-only={direction_only}:")
            else:
                console.print("Available tracking modes:")

            for mode in modes:
                console.print(f"- [cyan]{mode}[/cyan]")
        else:
            console.print(
                f"[bold red]Invalid action: {action}. Must be one of: mode, settings, tracking-modes[/bold red]"
            )
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[bold red]Error configuring mouse tracking: {e}[/bold red]")


@app.command("keys")
def keys(
    action: str = typer.Argument(
        ..., help="Action to take (list, add, remove, edit-mode)"
    ),
    key: str = typer.Option(None, "--key", "-k", help="Key to add or remove"),
    button: str = typer.Option(
        None, "--button", "-b", help="Button to toggle tracking for"
    ),
    track: bool = typer.Option(
        None, "--track", "-t", help="Whether to track the button"
    ),
) -> None:
    """Manage tracked keys and buttons."""
    if headless_mode:
        init_headless_mode()

    try:
        if action == "list":
            keys_list = InputCollectorAPI.get_tracked_keys()

            if not keys_list:
                console.print("[yellow]No keys being tracked[/yellow]")
                return

            console.print("[green]Tracked keys:[/green]")
            for key in keys_list:
                console.print(f"- {key}")
        elif action == "add" and key:
            success = InputCollectorAPI.add_tracked_key(key)

            if success:
                console.print(f"[green]Added tracked key: {key}[/green]")
            else:
                status = InputCollectorAPI.get_last_operation_status()
                console.print(
                    f"[bold red]Failed to add key: {status.get('message', '')}[/bold red]"
                )
        elif action == "remove" and key:
            success = InputCollectorAPI.remove_tracked_key(key)

            if success:
                console.print(f"[green]Removed tracked key: {key}[/green]")
            else:
                status = InputCollectorAPI.get_last_operation_status()
                console.print(
                    f"[bold red]Failed to remove key: {status.get('message', '')}[/bold red]"
                )
        elif action == "toggle-button" and button and track is not None:
            success = InputCollectorAPI.toggle_button_tracking(button, track)

            if success:
                action_str = "Added" if track else "Removed"
                console.print(f"[green]{action_str} tracked button: {button}[/green]")
            else:
                status = InputCollectorAPI.get_last_operation_status()
                console.print(
                    f"[bold red]Failed to toggle button tracking: {status.get('message', '')}[/bold red]"
                )
        elif action == "edit-mode":
            current = InputCollectorAPI.is_edit_mode()

            if current:
                # Disable edit mode
                success = InputCollectorAPI.toggle_edit_mode()
                if success:
                    console.print("[green]Edit mode disabled[/green]")
                else:
                    status = InputCollectorAPI.get_last_operation_status()
                    console.print(
                        f"[bold red]Failed to disable edit mode: {status.get('message', '')}[/bold red]"
                    )
            else:
                # Enable edit mode
                success = InputCollectorAPI.toggle_edit_mode()
                if success:
                    console.print("[green]Edit mode enabled[/green]")
                else:
                    status = InputCollectorAPI.get_last_operation_status()
                    console.print(
                        f"[bold red]Failed to enable edit mode: {status.get('message', '')}[/bold red]"
                    )
        else:
            if action not in ["list", "add", "remove", "toggle-button", "edit-mode"]:
                console.print(
                    f"[bold red]Invalid action: {action}. Must be one of: list, add, remove, toggle-button, edit-mode[/bold red]"
                )
            else:
                console.print("[bold red]Missing required arguments[/bold red]")
                if action == "add" or action == "remove":
                    console.print("Provide --key")
                elif action == "toggle-button":
                    console.print("Provide --button and --track")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[bold red]Error managing keys: {e}[/bold red]")


@app.command("fullscreen")
def fullscreen() -> None:
    """Toggle fullscreen mode."""
    if headless_mode:
        console.print(
            "[yellow]Fullscreen toggle not available in headless mode[/yellow]"
        )
        return

    try:
        success = InputCollectorAPI.toggle_fullscreen()

        if success:
            console.print("[green]Toggled fullscreen mode[/green]")
        else:
            status = InputCollectorAPI.get_last_operation_status()
            console.print(
                f"[bold red]Failed to toggle fullscreen: {status.get('message', '')}[/bold red]"
            )

    except Exception as e:
        console.print(f"[bold red]Error toggling fullscreen: {e}[/bold red]")


@app.command("status")
def status() -> None:
    """Get full application status."""
    if headless_mode:
        init_headless_mode()

    try:
        app_state = InputCollectorAPI.get_application_state()

        # Create a table to display the info
        table = Table(title="Input Collector Status", box=box.ROUNDED)

        # Add columns
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        # Add rows
        if "collector" in app_state:
            collector = app_state["collector"]
            table.add_row("Current Collector", collector.get("type", "Unknown"))
            table.add_row("Collector Name", collector.get("name", "Unknown"))

        table.add_row("Recording", str(app_state.get("recording", False)))
        table.add_row("Edit Mode", str(app_state.get("edit_mode", False)))

        if "active_keys" in app_state:
            table.add_row(
                "Active Keys", ", ".join(app_state["active_keys"] or ["None"])
            )

        if "tracked_keys" in app_state:
            # Limit to 5 keys for display and add "..." if there are more
            keys = app_state["tracked_keys"]
            if len(keys) > 5:
                tracked_display = ", ".join(keys[:5]) + f" ... ({len(keys)-5} more)"
            else:
                tracked_display = ", ".join(keys or ["None"])

            table.add_row("Tracked Keys", tracked_display)

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
        console.print(f"[bold red]Error getting application status: {e}[/bold red]")


@app.command("recording-start")
def recording_start() -> None:
    """Start recording."""
    InputCollectorAPI.start_recording()
    typer.echo("Recording started")


@app.command("recording-stop")
def recording_stop() -> None:
    """Stop recording."""
    InputCollectorAPI.stop_recording()
    typer.echo("Recording stopped")


@app.command("recording-toggle")
def recording_toggle() -> None:
    """Toggle recording state."""
    InputCollectorAPI.toggle_recording()
    typer.echo(
        f"Recording is now {'ON' if InputCollectorAPI.is_recording() else 'OFF'}"
    )


@app.command("recording-status")
def recording_status() -> None:
    """Check recording status."""
    status = InputCollectorAPI.is_recording()
    typer.echo(f"Recording: {'ON' if status else 'OFF'}")


#
# Logging configuration
#
@app.command("logging-json")
def logging_json(
    action: str = typer.Option(..., "--action", "-a", help="enable|disable")
) -> None:
    """Enable or disable JSON logging."""
    enable = action.lower() == "enable"
    InputCollectorAPI.enable_json_logging(enable)
    typer.echo(f"JSON logging {'enabled' if enable else 'disabled'}")


@app.command("logging-csv")
def logging_csv(
    action: str = typer.Option(..., "--action", "-a", help="enable|disable"),
    filepath: str = typer.Option(None, "--filepath", "-f", help="CSV file path"),
) -> None:
    """Enable or disable CSV logging (and set file)."""
    enable = action.lower() == "enable"
    if enable and filepath:
        InputCollectorAPI.set_csv_path(filepath)
    InputCollectorAPI.enable_csv_logging(enable, filepath or "")
    typer.echo(f"CSV logging {'enabled' if enable else 'disabled'}")


@app.command("logging-status")
def logging_status() -> None:
    """Check logging configuration."""
    state = InputCollectorAPI.get_logging_state()
    typer.echo(
        f"JSON: {state['json_enabled']}, CSV: {state['csv_enabled']}, Path: {state.get('csv_path','')}"
    )


#
# Collector management
#
@app.command("collectors-list")
def collectors_list() -> None:
    """List available collectors."""
    for c in InputCollectorAPI.get_available_collectors():
        typer.echo(f"{c['type']}: {c['name']}")


@app.command("collectors-current")
def collectors_current() -> None:
    """Show current collector."""
    cur = InputCollectorAPI.get_current_collector()
    typer.echo(f"{cur['type']}: {cur['name']}")


@app.command("collectors-switch")
def collectors_switch(
    collector: str = typer.Option(..., "--type", "-t", help="collector type")
) -> None:
    """Switch to a different collector."""
    InputCollectorAPI.switch_collector(collector)
    typer.echo(f"Switched to {collector}")


@app.command("collectors-scan")
def collectors_scan() -> None:
    """Scan for controllers."""
    lst = InputCollectorAPI.scan_controllers()
    typer.echo("Found controllers:")
    for c in lst:
        typer.echo(f"- {c['index']}: {c['name']}")


@app.command("connect-controller")
def connect_controller(
    index: int = typer.Argument(..., help="controller index")
) -> None:
    """Connect to a specific controller."""
    success = InputCollectorAPI.connect_controller(index)
    typer.echo("Connected" if success else "Failed")


#
# Mouse tracking configuration
#
@app.command("set-mouse-tracking-mode")
def set_mouse_tracking_mode(
    mode: str = typer.Argument(..., help="joystick|delta|angle|axis"),
    direction_only: bool = typer.Option(False, "--direction-only", "-d"),
) -> None:
    """Set mouse tracking mode."""
    InputCollectorAPI.set_mouse_tracking_mode(mode, direction_only)
    typer.echo(f"Mode set to {mode}, direction_only={direction_only}")


@app.command("get-available-tracking-modes")
def get_available_tracking_modes(
    direction_only: bool = typer.Option(False, "--direction-only", "-d")
) -> None:
    """List valid tracking modes."""
    modes = InputCollectorAPI.get_available_tracking_modes(direction_only)
    typer.echo("Available modes: " + ", ".join(modes))


@app.command("set-mouse-settings")
def set_mouse_settings(
    delta_smoothing: int = typer.Option(..., "--delta-smoothing", help="0–90"),
    joystick_sensitivity: int = typer.Option(
        ..., "--joystick-sensitivity", help="10–200"
    ),
    angle_grouping: int = typer.Option(..., "--angle-grouping", help="1–90"),
) -> None:
    """Configure mouse smoothing, sensitivity, grouping."""
    InputCollectorAPI.set_mouse_settings(
        delta_smoothing, joystick_sensitivity, angle_grouping
    )
    typer.echo("Mouse settings updated")


@app.command("get-mouse-settings")
def get_mouse_settings() -> None:
    """Get current mouse settings."""
    s = InputCollectorAPI.get_mouse_settings()
    typer.echo(
        f"Delta smoothing: {s['delta_smoothing']}, Joystick sensitivity: {s['joystick_sensitivity']}, Angle grouping: {s['angle_grouping']}"
    )


#
# Key tracking management
#
@app.command("get-tracked-keys")
def get_tracked_keys() -> None:
    """List currently tracked keys/buttons."""
    keys = InputCollectorAPI.get_tracked_keys()
    typer.echo(", ".join(keys))


@app.command("toggle-edit-mode")
def toggle_edit_mode() -> None:
    """Enable/disable edit mode."""
    InputCollectorAPI.toggle_edit_mode()
    typer.echo(f"Edit mode: {InputCollectorAPI.is_edit_mode()}")


@app.command("is-edit-mode")
def is_edit_mode() -> None:
    """Check if edit mode is active."""
    typer.echo(f"{InputCollectorAPI.is_edit_mode()}")


@app.command("add-tracked-key")
def add_tracked_key(key: str = typer.Argument(..., help="key identifier")) -> None:
    """Add a key to tracking."""
    InputCollectorAPI.add_tracked_key(key)
    typer.echo(f"Added {key}")


@app.command("remove-tracked-key")
def remove_tracked_key(key: str = typer.Argument(..., help="key identifier")) -> None:
    """Remove a key from tracking."""
    InputCollectorAPI.remove_tracked_key(key)
    typer.echo(f"Removed {key}")


@app.command("toggle-button-tracking")
def toggle_button_tracking(
    button_id: str = typer.Argument(..., help="Button.*"),
    track: bool = typer.Option(..., "--track/--no-track", help="enable or disable"),
) -> None:
    """Toggle mouse button tracking."""
    InputCollectorAPI.toggle_button_tracking(button_id, track)
    typer.echo(f"Button {button_id} tracking {'enabled' if track else 'disabled'}")


#
# UI control
#
@app.command("toggle-fullscreen")
def toggle_fullscreen() -> None:
    """Toggle fullscreen state."""
    InputCollectorAPI.toggle_fullscreen()
    typer.echo("Fullscreen toggled")


@app.command("get-application-state")
def get_application_state() -> None:
    """Retrieve full application state."""
    state = InputCollectorAPI.get_application_state()
    typer.echo(state)
