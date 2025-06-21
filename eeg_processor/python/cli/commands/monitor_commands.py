"""
Monitoring commands for the CLI application.

These commands allow monitoring EEG data streams and system status in real-time.
"""
import sys
import threading
import time
from typing import Dict, Any, Optional

import typer
from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.align import Align
from rich.text import Text

from .. import cli_config

monitor_app = typer.Typer(name="monitor", help="EEG data monitoring commands")
console = Console()


def _setup_key_listener(stop_event: threading.Event) -> None:
    """Setup key listener for ESC and Q to stop monitoring."""
    def key_listener() -> None:
        if sys.platform == "win32":
            import msvcrt
            while not stop_event.is_set():
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key in (b"\x1b", b"q", b"Q"):  # ESC, q, Q
                        stop_event.set()
                        break
                time.sleep(0.01)
        else:
            import tty, termios, select
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while not stop_event.is_set():
                    dr, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if dr:
                        key = sys.stdin.read(1)
                        if key in ("\x1b", "q", "Q"):  # ESC, q, Q
                            stop_event.set()
                            break
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    threading.Thread(target=key_listener, daemon=True).start()


@monitor_app.command("stream")
def monitor_stream(
    duration: Optional[int] = typer.Option(None, "--duration", help="Monitor duration in seconds (0 = infinite)"),
    refresh_rate: float = typer.Option(0.5, "--refresh-rate", help="Update frequency in seconds"),
) -> None:
    """Monitor EEG data stream in real-time."""
    try:
        # Get services from CLI config to avoid reinitializing
        data_service = cli_config.get_data_service()
        if not data_service or not data_service.is_streaming():
            console.print("[red]No active data stream. Start streaming first.[/red]")
            return
            
        console.print(f"[blue]Monitoring EEG stream (refresh every {refresh_rate}s)...[/blue]")
        console.print("[yellow]Press ESC or Q to stop monitoring[/yellow]")
        
        start_time = time.time()
        stop_event = threading.Event()
        _setup_key_listener(stop_event)
        
        def create_stream_display():
            """Create the real-time stream display."""
            try:
                # Get current data from service directly
                data, timestamps = data_service.get_current_data()
                metadata = data_service.get_metadata()
                
                if data.size == 0:
                    return Panel(
                        "[yellow]No data available[/yellow]",
                        title="EEG Stream Monitor",
                        border_style="red"
                    )
                
                # Get EEG channel indices (1-based) and names
                eeg_channels = metadata.get("eeg_channels", [])
                channel_names = metadata.get("channel_names", [])
                # Get signal quality (1-based dict)
                try:
                    from ...data_access_api import EEGDataAPI
                    quality_values = EEGDataAPI.get_all_channels_quality()
                except:
                    quality_values = {}

                # Create main layout
                layout = Layout()
                layout.split_column(
                    Layout(name="header", size=3),
                    Layout(name="main", ratio=1),
                    Layout(name="footer", size=3)
                )
                
                # Header with basic info
                sampling_rate = metadata.get("sampling_rate", 0)
                board_name = metadata.get("board_name", "Unknown")
                elapsed = time.time() - start_time
                
                header_text = f"EEG Stream Monitor | Board: {board_name} | Rate: {sampling_rate} Hz | Elapsed: {elapsed:.1f}s"
                layout["header"].update(Panel(header_text, style="bold blue"))
                
                # Main data table
                table = Table(title=f"Live EEG Data ({len(eeg_channels)} EEG channels, {data.shape[1]} samples)")
                table.add_column("Channel", style="cyan")
                table.add_column("Latest (µV)", style="green")
                table.add_column("Min (µV)", style="blue")
                table.add_column("Max (µV)", style="red") 
                table.add_column("RMS (µV)", style="yellow")
                table.add_column("Quality", style="magenta")
                
                # Show only EEG channels, in 1-based order
                for ch_idx in eeg_channels:
                    # ch_idx is 1-based, so for numpy arrays use ch_idx-1
                    if 0 <= (ch_idx - 1) < data.shape[0]:
                        ch_name = channel_names[ch_idx - 1] if (ch_idx - 1) < len(channel_names) else f"CH{ch_idx}"
                        ch_data = data[ch_idx - 1]
                        latest = ch_data[-1] if ch_data.size > 0 else 0
                        min_val = ch_data.min() if ch_data.size > 0 else 0
                        max_val = ch_data.max() if ch_data.size > 0 else 0
                        rms = ((ch_data ** 2).mean() ** 0.5) if ch_data.size > 0 else 0
                        # Quality indicator (1-based)
                        quality = quality_values.get(ch_idx, 0)
                        if quality > 0.8:
                            quality_str = "[green]●[/green] Excellent"
                        elif quality > 0.6:
                            quality_str = "[yellow]●[/yellow] Good"
                        elif quality > 0.4:
                            quality_str = "[orange1]●[/orange1] Fair"
                        else:
                            quality_str = "[red]●[/red] Poor"
                        table.add_row(
                            ch_name,
                            f"{latest:.2f}",
                            f"{min_val:.2f}",
                            f"{max_val:.2f}",
                            f"{rms:.2f}",
                            quality_str
                        )
                
                layout["main"].update(table)
                
                # Footer with controls
                footer_text = "Press ESC or Q to stop monitoring | Use 'data current-data --max-samples 100' for detailed data"
                layout["footer"].update(Panel(footer_text, style="dim"))
                
                return layout
                
            except Exception as e:
                return Panel(
                    f"[red]Error updating display: {e}[/red]",
                    title="EEG Stream Monitor",
                    border_style="red"
                )
        
        # Run live display
        with Live(create_stream_display(), refresh_per_second=1/refresh_rate) as live:
            try:
                while not stop_event.is_set():
                    if duration and (time.time() - start_time) >= duration:
                        break
                    live.update(create_stream_display())
                    time.sleep(refresh_rate)
            except KeyboardInterrupt:
                console.print("\n[yellow]Monitoring stopped by Ctrl+C[/yellow]")
                
        console.print("\n[yellow]Monitoring stopped[/yellow]")
                
    except Exception as e:
        console.print(f"[red]Error monitoring stream: {e}[/red]")


@monitor_app.command("status")
def monitor_status(
    duration: Optional[int] = typer.Option(None, "--duration", help="Monitor duration in seconds (0 = infinite)"),
    refresh_rate: float = typer.Option(2.0, "--refresh-rate", help="Update frequency in seconds"),
) -> None:
    """Monitor system status in real-time."""
    try:
        console.print(f"[blue]Monitoring system status (refresh every {refresh_rate}s)...[/blue]")
        console.print("[yellow]Press ESC or Q to stop monitoring[/yellow]")
        
        start_time = time.time()
        stop_event = threading.Event()
        _setup_key_listener(stop_event)
        
        def create_status_display():
            """Create the real-time status display."""
            try:
                # Get services from CLI config to avoid reinitializing
                interaction_service = cli_config.get_interaction_service()
                if not interaction_service:
                    return Panel(
                        "[red]Interaction service not available[/red]",
                        title="System Status Monitor",
                        border_style="red"
                    )
                
                # Get system status
                system_status = interaction_service.get_system_status()
                
                if not system_status.get("success"):
                    return Panel(
                        f"[red]Error getting status: {system_status.get('error', 'Unknown error')}[/red]",
                        title="System Status Monitor",
                        border_style="red"
                    )
                
                status = system_status.get("status", {})
                elapsed = time.time() - start_time
                
                # Create layout
                layout = Layout()
                layout.split_column(
                    Layout(name="header", size=3),
                    Layout(name="main", ratio=1)
                )
                
                # Header
                header_text = f"System Status Monitor | Elapsed: {elapsed:.1f}s | Last Update: {time.strftime('%H:%M:%S')}"
                layout["header"].update(Panel(header_text, style="bold blue"))
                
                # Main status table
                table = Table(title="EEG Processor Status", box=box.ROUNDED)
                table.add_column("Component", style="cyan")
                table.add_column("Status", style="green")
                table.add_column("Details", style="yellow")
                
                # Connection status
                connected = status.get("connected", False)
                board_name = status.get("board_name", "Unknown")
                board_id = status.get("board_id", -1)
                table.add_row(
                    "Board Connection",
                    "✓ Connected" if connected else "✗ Disconnected",
                    f"{board_name} (ID: {board_id})" if connected else "No board"
                )
                
                # Streaming status
                streaming = status.get("streaming", False)
                sampling_rate = status.get("sampling_rate", 0)
                table.add_row(
                    "Data Streaming",
                    "✓ Active" if streaming else "✗ Inactive",
                    f"{sampling_rate} Hz" if streaming else "Not streaming"
                )
                
                # Recording status
                recording = status.get("recording", False)
                recording_filename = status.get("recording_filename", "")
                recording_duration = status.get("recording_duration", 0)
                table.add_row(
                    "Recording",
                    "✓ Recording" if recording else "✗ Not Recording",
                    f"{recording_filename} ({recording_duration:.1f}s)" if recording else "No recording"
                )
                
                # Data availability
                data_available = status.get("data_available", False)
                channel_count = len(status.get("channel_names", []))
                table.add_row(
                    "Data Status",
                    "✓ Available" if data_available else "✗ No Data",
                    f"{channel_count} channels" if data_available else "No data"
                )
                
                # Processing status
                filters_enabled = status.get("filters_enabled", False)
                table.add_row(
                    "Signal Processing",
                    "✓ Filters Active" if filters_enabled else "○ No Filters",
                    "Bandpass, Notch, Detrend" if filters_enabled else "Raw data"
                )
                
                layout["main"].update(table)
                return layout
                
            except Exception as e:
                return Panel(
                    f"[red]Error updating status: {e}[/red]",
                    title="System Status Monitor",
                    border_style="red"
                )
        
        # Run live display
        with Live(create_status_display(), refresh_per_second=1/refresh_rate) as live:
            try:
                while not stop_event.is_set():
                    if duration and (time.time() - start_time) >= duration:
                        break
                    live.update(create_status_display())
                    time.sleep(refresh_rate)
            except KeyboardInterrupt:
                console.print("\n[yellow]Status monitoring stopped by Ctrl+C[/yellow]")
                
        console.print("\n[yellow]Status monitoring stopped[/yellow]")
                
    except Exception as e:
        console.print(f"[red]Error monitoring status: {e}[/red]")


@monitor_app.command("channels")
def monitor_channels(
    channels: Optional[str] = typer.Option(None, "--channels", help="Comma-separated channel indices to monitor (e.g., \"0,1,2,3\")"),
    duration: Optional[int] = typer.Option(None, "--duration", help="Monitor duration in seconds (0 = infinite)"),
    refresh_rate: float = typer.Option(1.0, "--refresh-rate", help="Update frequency in seconds"),
) -> None:
    """Monitor specific EEG channels in real-time."""
    try:
        # Get services from CLI config to avoid reinitializing
        data_service = cli_config.get_data_service()
        if not data_service or not data_service.is_streaming():
            console.print("[red]No active data stream. Start streaming first.[/red]")
            return
        
        # Parse channel indices
        if channels:
            try:
                channels_to_monitor = [int(x.strip()) for x in channels.split(",")]
            except ValueError:
                console.print("[red]Invalid channel indices format. Use comma-separated integers like: --channels \"0,1,2,3\"[/red]")
                return
        else:
            # Monitor first 8 EEG channels by default
            metadata = data_service.get_metadata()
            eeg_channels = metadata.get("eeg_channels", [])
            channels_to_monitor = eeg_channels[:8] if eeg_channels else list(range(8))
        
        console.print(f"[blue]Monitoring channels {channels_to_monitor} (refresh every {refresh_rate}s)...[/blue]")
        console.print("[yellow]Press ESC or Q to stop monitoring[/yellow]")
        
        start_time = time.time()
        stop_event = threading.Event()
        _setup_key_listener(stop_event)
        
        def create_channels_display():
            """Create the real-time channels display."""
            try:
                data, timestamps = data_service.get_current_data()
                metadata = data_service.get_metadata()
                channel_names = metadata.get("channel_names", [])
                
                if data.size == 0:
                    return Panel(
                        "[yellow]No data available[/yellow]",
                        title="Channel Monitor",
                        border_style="red"
                    )
                
                elapsed = time.time() - start_time
                
                # Create layout
                layout = Layout()
                layout.split_column(
                    Layout(name="header", size=3),
                    Layout(name="main", ratio=1)
                )
                
                # Header
                header_text = f"Channel Monitor | Channels: {len(channels_to_monitor)} | Elapsed: {elapsed:.1f}s"
                layout["header"].update(Panel(header_text, style="bold blue"))
                
                # Channels table
                table = Table(title="Channel Data (Latest 10 samples)", box=box.SIMPLE)
                table.add_column("Channel", style="cyan")
                table.add_column("Name", style="green")
                
                # Add columns for latest 10 samples
                for i in range(10):
                    table.add_column(f"T-{9-i}", style="yellow", justify="right")
                
                for ch_idx in channels_to_monitor:
                    if ch_idx < data.shape[0]:
                        ch_name = channel_names[ch_idx] if ch_idx < len(channel_names) else f"CH{ch_idx+1}"
                        ch_data = data[ch_idx]
                        
                        # Get latest 10 samples
                        latest_samples = ch_data[-10:] if ch_data.size >= 10 else ch_data
                        
                        row = [str(ch_idx), ch_name]
                        for i, sample in enumerate(latest_samples):
                            row.append(f"{sample:.2f}")
                        
                        # Pad with empty values if less than 10 samples
                        while len(row) < 12:  # 2 (channel info) + 10 (samples)
                            row.append("--")
                        
                        table.add_row(*row)
                
                layout["main"].update(table)
                return layout
                
            except Exception as e:
                return Panel(
                    f"[red]Error updating channels: {e}[/red]",
                    title="Channel Monitor",
                    border_style="red"
                )
        
        # Run live display
        with Live(create_channels_display(), refresh_per_second=1/refresh_rate) as live:
            try:
                while not stop_event.is_set():
                    if duration and (time.time() - start_time) >= duration:
                        break
                    live.update(create_channels_display())
                    time.sleep(refresh_rate)
            except KeyboardInterrupt:
                console.print("\n[yellow]Channel monitoring stopped by Ctrl+C[/yellow]")
                
        console.print("\n[yellow]Channel monitoring stopped[/yellow]")
                
    except Exception as e:
        console.print(f"[red]Error monitoring channels: {e}[/red]")


@monitor_app.command("quality")
def monitor_signal_quality(
    duration: Optional[int] = typer.Option(None, "--duration", help="Monitor duration in seconds (0 = infinite)"),
    refresh_rate: float = typer.Option(3.0, "--refresh-rate", help="Update frequency in seconds"),
) -> None:
    """Monitor signal quality for all channels in real-time."""
    try:
        # Get services from CLI config to avoid reinitializing
        data_service = cli_config.get_data_service()
        if not data_service or not data_service.is_streaming():
            console.print("[red]No active data stream. Start streaming first.[/red]")
            return
            
        console.print(f"[blue]Monitoring signal quality (refresh every {refresh_rate}s)...[/blue]")
        console.print("[yellow]Press ESC or Q to stop monitoring[/yellow]")
        
        start_time = time.time()
        stop_event = threading.Event()
        _setup_key_listener(stop_event)
        
        def create_quality_display():
            """Create the real-time quality display."""
            try:
                # Use EEGDataAPI to get 1-based quality and channel info
                from ...data_access_api import EEGDataAPI
                quality_values = EEGDataAPI.get_all_channels_quality()
                metadata = data_service.get_metadata()
                channel_names = metadata.get("channel_names", [])
                eeg_channels = metadata.get("eeg_channels", [])

                if not quality_values or not eeg_channels:
                    return Panel(
                        "[yellow]No quality data available[/yellow]",
                        title="Signal Quality Monitor",
                        border_style="red"
                    )
                
                elapsed = time.time() - start_time
                
                # Create layout
                layout = Layout()
                layout.split_column(
                    Layout(name="header", size=3),
                    Layout(name="main", ratio=1),
                    Layout(name="footer", size=5)
                )
                
                # Header
                header_text = f"Signal Quality Monitor | Elapsed: {elapsed:.1f}s | Channels: {len(eeg_channels)}"
                layout["header"].update(Panel(header_text, style="bold blue"))
                
                # Quality table
                table = Table(title="Signal Quality Assessment", box=box.ROUNDED)
                table.add_column("Channel", style="cyan")
                table.add_column("Name", style="white")
                table.add_column("Quality Score", justify="right", style="yellow")
                table.add_column("Level", style="green")
                table.add_column("Visual", style="white")
                
                excellent_count = good_count = fair_count = poor_count = 0
                
                # Only show EEG channels, in 1-based order
                for ch_idx in eeg_channels:
                    quality = quality_values.get(ch_idx, 0.0)
                    ch_name = channel_names[ch_idx-1] if (ch_idx-1) < len(channel_names) else f"CH{ch_idx}"
                    
                    # Determine quality level and color
                    if quality > 0.8:
                        level = "Excellent"
                        level_color = "[bright_green]Excellent[/bright_green]"
                        visual = "[bright_green]" + "█" * 10 + "[/bright_green]"
                        excellent_count += 1
                    elif quality > 0.6:
                        level = "Good"
                        level_color = "[green]Good[/green]"
                        visual = "[green]" + "█" * 8 + "░░" + "[/green]"
                        good_count += 1
                    elif quality > 0.4:
                        level = "Fair"
                        level_color = "[yellow]Fair[/yellow]"
                        visual = "[yellow]" + "█" * 6 + "░░░░" + "[/yellow]"
                        fair_count += 1
                    else:
                        level = "Poor"
                        level_color = "[red]Poor[/red]"
                        visual = "[red]" + "█" * 4 + "░░░░░░" + "[/red]"
                        poor_count += 1
                    
                    table.add_row(
                        str(ch_idx),  # 1-based
                        ch_name,
                        f"{quality:.3f}",
                        level_color,
                        visual
                    )
                
                layout["main"].update(table)
                
                # Footer with summary
                summary = f"""
[bright_green]Excellent ({excellent_count})[/bright_green] | [green]Good ({good_count})[/green] | [yellow]Fair ({fair_count})[/yellow] | [red]Poor ({poor_count})[/red]

Quality Score: 0.8+ = Excellent, 0.6+ = Good, 0.4+ = Fair, <0.4 = Poor
                """.strip()
                layout["footer"].update(Panel(summary, title="Quality Summary"))
                
                return layout
                
            except Exception as e:
                return Panel(
                    f"[red]Error updating quality: {e}[/red]",
                    title="Signal Quality Monitor", 
                    border_style="red"
                )
        
        # Run live display
        with Live(create_quality_display(), refresh_per_second=1/refresh_rate) as live:
            try:
                while not stop_event.is_set():
                    if duration and (time.time() - start_time) >= duration:
                        break
                    live.update(create_quality_display())
                    time.sleep(refresh_rate)
            except KeyboardInterrupt:
                console.print("\n[yellow]Quality monitoring stopped by Ctrl+C[/yellow]")
                
        console.print("\n[yellow]Quality monitoring stopped[/yellow]")
                
    except Exception as e:
        console.print(f"[red]Error monitoring signal quality: {e}[/red]")


@monitor_app.command("recording")
def monitor_recording(
    refresh_rate: float = typer.Option(1.0, "--refresh-rate", help="Update frequency in seconds"),
) -> None:
    """Monitor recording status and progress."""
    try:
        console.print(f"[blue]Monitoring recording status (refresh every {refresh_rate}s)...[/blue]")
        console.print("[yellow]Press ESC or Q to stop monitoring[/yellow]")
        
        start_time = time.time()
        stop_event = threading.Event()
        _setup_key_listener(stop_event)
        
        def create_recording_display():
            """Create the real-time recording display."""
            try:
                # Get services from CLI config to avoid reinitializing
                interaction_service = cli_config.get_interaction_service()
                if not interaction_service:
                    return Panel(
                        "[red]Interaction service not available[/red]",
                        title="Recording Monitor",
                        border_style="red"
                    )
                
                recording_status = interaction_service.get_recording_status()
                elapsed = time.time() - start_time
                
                # Create display
                if recording_status.get("recording", False):
                    duration = recording_status.get("duration", 0)
                    filename = recording_status.get("filename", "unknown")
                    data_type = recording_status.get("data_type", "raw")
                    
                    status_text = f"""
[green]● RECORDING ACTIVE[/green]

File: {filename}
Duration: {duration:.1f} seconds
Data Type: {data_type.title()}
Monitor Time: {elapsed:.1f}s

[yellow]Recording in progress...[/yellow]
                    """.strip()
                    
                    return Panel(status_text, title="Recording Monitor", border_style="green")
                else:
                    status_text = f"""
[red]○ NO RECORDING[/red]

No active recording session.
Monitor Time: {elapsed:.1f}s

Use 'control start-recording <filename>' to start recording.
                    """.strip()
                    
                    return Panel(status_text, title="Recording Monitor", border_style="red")
                
            except Exception as e:
                return Panel(
                    f"[red]Error getting recording status: {e}[/red]",
                    title="Recording Monitor",
                    border_style="red"
                )
        
        # Run live display
        with Live(create_recording_display(), refresh_per_second=1/refresh_rate) as live:
            try:
                while not stop_event.is_set():
                    live.update(create_recording_display())
                    time.sleep(refresh_rate)
            except KeyboardInterrupt:
                console.print("\n[yellow]Recording monitoring stopped by Ctrl+C[/yellow]")
                
        console.print("\n[yellow]Recording monitoring stopped[/yellow]")
                
    except Exception as e:
        console.print(f"[red]Error monitoring recording: {e}[/red]")