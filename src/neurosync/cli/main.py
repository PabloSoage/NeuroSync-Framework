"""Command line interface for NeuroSync (phase F9, per D-10 & D-11).

Built on Typer and Rich, consuming the shared command registry and communicating with neurosyncd.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from neurosync.cli.client import NeuroSyncClient
from neurosync.export.manager import ExportFormat, ExportManager
from neurosync.server.service import run_server

app = typer.Typer(
    name="neurosync",
    help="High-performance EEG acquisition, causal DSP, and lossless recording CLI.",
    add_completion=False,
)
console = Console()

DEFAULT_SERVER_URL = "http://127.0.0.1:8000"


def _get_client(server_url: str) -> NeuroSyncClient:
    return NeuroSyncClient(base_url=server_url)


@app.command()
def status(
    server_url: Annotated[
        str, typer.Option("--server", "-s", help="neurosyncd server URL")
    ] = DEFAULT_SERVER_URL,
) -> None:
    """Display current neurosyncd daemon and acquisition status."""
    with _get_client(server_url) as client:
        if not client.check_health():
            rprint(f"[bold red]Error:[/bold red] neurosyncd server is not running at {server_url}.")
            rprint("Start it with: [green]neurosync serve[/green] or [green]neurosyncd[/green]")
            raise typer.Exit(code=1)

        st = client.get_status()

    table = Table(title="NeuroSync System Status", border_style="cyan")
    table.add_column("Property", style="bold white")
    table.add_column("Value", style="green")

    state_color = "green" if st.status in ("acquiring", "recording") else "yellow"
    table.add_row("Server State", f"[{state_color}]{st.status.upper()}[/{state_color}]")
    table.add_row("Uptime", f"{st.uptime_s:.2f} s")
    table.add_row("Active Board", st.active_board or "None")
    table.add_row("Filter Enabled", "Yes" if st.filter_enabled else "No")

    if st.primary_stream:
        ch_str = ", ".join(st.primary_stream.channels[:8])
        if len(st.primary_stream.channels) > 8:
            ch_str += f" (+{len(st.primary_stream.channels) - 8} more)"
        stream_desc = f"{st.primary_stream.stream_id} @ {st.primary_stream.nominal_fs} Hz"
        table.add_row("Primary Stream", stream_desc)
        table.add_row("Channels", ch_str)
        table.add_row("Samples Acquired", str(st.primary_stream.sample_count))

    if st.recording_file:
        table.add_row("Recording File", st.recording_file)
        table.add_row("Samples Recorded", str(st.samples_recorded))
        table.add_row("Events Recorded", str(st.events_recorded))

    console.print(table)


@app.command()
def start(
    board_id: Annotated[
        int, typer.Option("--board-id", "-b", help="BrainFlow board id (-1 for synthetic)")
    ] = -1,
    serial_port: Annotated[str | None, typer.Option("--port", "-p", help="Serial COM port")] = None,
    master_board: Annotated[
        int | None, typer.Option("--master", "-m", help="Master board id for playback file")
    ] = None,
    server_url: Annotated[str, typer.Option("--server", "-s")] = DEFAULT_SERVER_URL,
) -> None:
    """Start signal acquisition on the daemon."""
    with _get_client(server_url) as client:
        try:
            st = client.start_acquisition(
                board_id=board_id, serial_port=serial_port, master_board=master_board
            )
            rprint(f"[bold green]Acquisition started![/bold green] Status: {st.status}")
        except Exception as exc:
            rprint(f"[bold red]Failed to start acquisition:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc


@app.command()
def stop(
    server_url: Annotated[str, typer.Option("--server", "-s")] = DEFAULT_SERVER_URL,
) -> None:
    """Stop signal acquisition and active recording on the daemon."""
    with _get_client(server_url) as client:
        try:
            st = client.stop_acquisition()
            rprint(f"[green]Acquisition stopped.[/green] State: [yellow]{st.status}[/yellow].")
        except Exception as exc:
            rprint(f"[bold red]Failed to stop acquisition:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc


@app.command()
def record(
    output_path: Annotated[str, typer.Argument(help="Destination .xdf file path")],
    session_id: Annotated[str, typer.Option("--session-id", help="Session ID")] = "session",
    server_url: Annotated[str, typer.Option("--server", "-s")] = DEFAULT_SERVER_URL,
) -> None:
    """Begin recording streaming signals and events to an append-only XDF file."""
    with _get_client(server_url) as client:
        try:
            st = client.start_recording(output_path=output_path, session_id=session_id)
            rprint(f"[bold green]Recording started:[/bold green] {st.recording_file}")
        except Exception as exc:
            rprint(f"[bold red]Failed to start recording:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc


@app.command(name="stop-record")
def stop_record(
    server_url: Annotated[str, typer.Option("--server", "-s")] = DEFAULT_SERVER_URL,
) -> None:
    """Stop active recording session and display metrics summary."""
    with _get_client(server_url) as client:
        try:
            res = client.stop_recording()
            table = Table(title="Recording Summary", border_style="green")
            table.add_column("Metric", style="bold white")
            table.add_column("Value", style="cyan")
            table.add_row("Session ID", res.session_id)
            table.add_row("XDF File", res.xdf_path)
            table.add_row("Duration", f"{res.duration_s:.3f} s")
            table.add_row("Total Samples", str(res.total_samples))
            table.add_row("Total Events", str(res.total_events))
            table.add_row("Max Flush Lag", f"{res.max_flush_lag_ms:.2f} ms")
            console.print(table)
        except Exception as exc:
            rprint(f"[bold red]Failed to stop recording:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc


@app.command()
def marker(
    code: Annotated[int, typer.Argument(help="Marker code (integer)")],
    value: Annotated[
        float, typer.Option("--value", "-v", help="Marker floating-point value")
    ] = 1.0,
    server_url: Annotated[str, typer.Option("--server", "-s")] = DEFAULT_SERVER_URL,
) -> None:
    """Inject an experimental event marker into the daemon's event bus."""
    with _get_client(server_url) as client:
        try:
            ev = client.emit_marker(marker_code=code, value=value)
            rprint(f"[green]Marker injected:[/green] code={ev['code']} seq={ev['seq']}")
        except Exception as exc:
            rprint(f"[bold red]Failed to emit marker:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc


@app.command()
def filter(
    lowcut: Annotated[float | None, typer.Option("--lowcut", help="Highpass cut (Hz)")] = 1.0,
    highcut: Annotated[float | None, typer.Option("--highcut", help="Lowpass cut (Hz)")] = 45.0,
    notch: Annotated[float | None, typer.Option("--notch", help="Mains notch cut (Hz)")] = 50.0,
    disable: Annotated[bool, typer.Option("--disable", help="Disable filtering")] = False,
    server_url: Annotated[str, typer.Option("--server", "-s")] = DEFAULT_SERVER_URL,
) -> None:
    """Configure real-time causal SOS filter pipeline on the daemon."""
    with _get_client(server_url) as client:
        try:
            st = client.configure_filter(
                enabled=not disable,
                lowcut_hz=lowcut,
                highcut_hz=highcut,
                notch_hz=notch,
            )
            state = "Enabled" if st.filter_enabled else "Disabled"
            rprint(f"[bold green]Filter configured successfully.[/bold green] Status: {state}")
        except Exception as exc:
            rprint(f"[bold red]Failed to configure filter:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc


@app.command()
def export(
    xdf_path: Annotated[Path, typer.Argument(help="Input recorded .xdf file", exists=True)],
    output_dir: Annotated[Path, typer.Option("--out", "-o", help="Target output directory")],
    format_name: Annotated[
        str, typer.Option("--format", "-f", help="Export target: csv, edf, bids, npz, all")
    ] = "all",
    subject_id: Annotated[str, typer.Option("--subject", help="Subject label for BIDS")] = "01",
    task_id: Annotated[str, typer.Option("--task", help="Task label for BIDS")] = "experiment",
    session_id: Annotated[str | None, typer.Option("--session", help="Session label")] = None,
) -> None:
    """Offline converter exporting XDF files into CSV, EDF+, BIDS 1.9+, or NumPy."""
    try:
        mgr = ExportManager(xdf_path)
        fmt = ExportFormat(format_name.lower())
        results = mgr.export(
            fmt,
            output_dir,
            subject_id=subject_id,
            task_id=task_id,
            session_id=session_id,
        )

        table = Table(title=f"Export Completed -> {output_dir}", border_style="cyan")
        table.add_column("Format", style="bold white")
        table.add_column("Generated Path(s)", style="green")

        for f_name, paths in results.items():
            for p in paths:
                table.add_row(f_name.upper(), str(p))

        console.print(table)
    except Exception as exc:
        rprint(f"[bold red]Export failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def serve(
    host: Annotated[str, typer.Option("--host", "-h", help="Bind host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p", help="Bind port")] = 8000,
    log_level: Annotated[str, typer.Option("--log-level", "-l", help="Logging level")] = "info",
) -> None:
    """Start the standalone neurosyncd daemon server process."""
    rprint(f"[bold cyan]Starting neurosyncd on http://{host}:{port}...[/bold cyan]")
    run_server(host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    app()
