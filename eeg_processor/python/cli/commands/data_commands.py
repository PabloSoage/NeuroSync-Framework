"""
Data commands for the CLI application.

These commands allow accessing EEG data and metadata.
"""
import json
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .. import cli_config

data_app = typer.Typer(name="data", help="EEG data access commands")
console = Console()


@data_app.command("current-data")
def get_current_data(
    max_samples: Optional[int] = typer.Option(None, "--max-samples", help="Maximum samples to return"),
    format: str = typer.Option("table", "--format", help="Output format: table, json"),
    all_data: bool = typer.Option(False, "--all", help="Show all data samples, not just summary"),
    vertical: bool = typer.Option(False, "--vertical", help="Display data vertically (one sample per row)"),
) -> None:
    """Get current EEG data from all channels."""
    try:
        # Get data service from CLI config to avoid reinitializing
        data_service = cli_config.get_data_service()
        if not data_service:
            console.print("[red]Data service not available[/red]")
            return
            
        data, timestamps = data_service.get_current_data()
        
        if data.size == 0:
            console.print("[yellow]No data available[/yellow]")
            return
            
        # Apply max samples limit
        if max_samples and data.shape[1] > max_samples:
            data = data[:, -max_samples:]
            timestamps = timestamps[-max_samples:]
            
        if format == "json":
            result = {
                "data": data.tolist(),
                "timestamps": timestamps,
                "shape": list(data.shape),
                "channels": data.shape[0],
                "samples": data.shape[1]
            }
            console.print(json.dumps(result, indent=2))
        else:
            if all_data:
                channel_names = data_service.get_channel_names()
                
                if vertical:
                    # Vertical display: one sample per row, all channels as columns
                    table = Table(title=f"All EEG Data - Vertical View ({data.shape[0]} channels, {data.shape[1]} samples)")
                    table.add_column("Sample #", style="cyan")
                    table.add_column("Timestamp", style="magenta")
                    
                    # Add column for each channel
                    for i in range(data.shape[0]):
                        channel_name = channel_names[i] if i < len(channel_names) else f"CH{i+1}"
                        table.add_column(channel_name, style="green", justify="right")
                    
                    # Add rows for each sample
                    max_samples_display = min(data.shape[1], 50)  # Limit to 50 samples in vertical view
                    for j in range(-max_samples_display, 0):
                        sample_idx = data.shape[1] + j
                        ts = timestamps[sample_idx] if sample_idx < len(timestamps) else "--"
                        
                        row = [str(sample_idx + 1), str(ts)]
                        
                        # Add value for each channel
                        for i in range(data.shape[0]):
                            row.append(f"{data[i][sample_idx]:.4f}")
                        
                        table.add_row(*row)
                    
                    if data.shape[1] > max_samples_display:
                        console.print(f"\n[dim]Showing last {max_samples_display} samples of {data.shape[1]} total samples[/dim]")
                else:
                    # Horizontal display: one channel per row, samples as columns (existing implementation)
                    table = Table(title=f"All EEG Data ({data.shape[0]} channels, {data.shape[1]} samples)")
                    table.add_column("Channel", style="cyan")
                    
                    # Add columns for each sample (limit to reasonable number)
                    max_samples_display = min(data.shape[1], 20)
                    for i in range(max_samples_display):
                        table.add_column(f"S{i+1}", style="green", justify="right")
                    
                    if data.shape[1] > max_samples_display:
                        table.add_column("...", style="dim")
                    
                    for i in range(data.shape[0]):
                        channel_name = channel_names[i] if i < len(channel_names) else f"CH{i+1}"
                        channel_data = data[i]
                        
                        row = [channel_name]
                        
                        # Add sample values
                        for j in range(max_samples_display):
                            if j < channel_data.size:
                                row.append(f"{channel_data[j]:.4f}")
                            else:
                                row.append("--")
                        
                        if data.shape[1] > max_samples_display:
                            row.append("...")
                        
                        table.add_row(*row)
            else:
                # Summary statistics table (existing implementation)
                table = Table(title=f"Current EEG Data ({data.shape[0]} channels, {data.shape[1]} samples)")
                table.add_column("Channel", style="cyan")
                table.add_column("Latest Value", style="green")
                table.add_column("Min", style="blue")
                table.add_column("Max", style="red")
                table.add_column("Mean", style="yellow")
                table.add_column("Std", style="magenta")
                
                channel_names = data_service.get_channel_names()
                
                for i in range(data.shape[0]):
                    channel_name = channel_names[i] if i < len(channel_names) else f"CH{i+1}"
                    channel_data = data[i]
                    
                    table.add_row(
                        channel_name,
                        f"{channel_data[-1]:.4f}",
                        f"{channel_data.min():.4f}",
                        f"{channel_data.max():.4f}",
                        f"{channel_data.mean():.4f}",
                        f"{channel_data.std():.4f}"
                    )
                    
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]Error getting current data: {e}[/red]")


@data_app.command("eeg-data")
def get_eeg_data(
    max_samples: Optional[int] = typer.Option(None, "--max-samples", help="Maximum samples to return"),
    format: str = typer.Option("table", "--format", help="Output format: table, json"),
    all_data: bool = typer.Option(False, "--all", help="Show all data samples, not just summary"),
    vertical: bool = typer.Option(False, "--vertical", help="Display data vertically (one sample per row)"),
) -> None:
    """Get current data for EEG channels only."""
    try:
        # Similar implementation as current-data but for EEG channels only
        # Get data service from CLI config to avoid reinitializing
        data_service = cli_config.get_data_service()
        if not data_service:
            console.print("[red]Data service not available[/red]")
            return
            
        data, timestamps = data_service.get_eeg_data(max_samples)
        
        if data.size == 0:
            console.print("[yellow]No EEG data available[/yellow]")
            return
            
        if format == "json":
            result = {
                "eeg_data": data.tolist(),
                "timestamps": timestamps,
                "shape": list(data.shape),
                "eeg_channels": data.shape[0],
                "samples": data.shape[1]
            }
            console.print(json.dumps(result, indent=2))
        else:
            if all_data:
                metadata = data_service.get_metadata()
                eeg_channels = metadata.get("eeg_channels", [])
                channel_names = data_service.get_channel_names()
                
                if vertical:
                    # Vertical display: one sample per row, all EEG channels as columns
                    table = Table(title=f"All EEG Data - Vertical View ({data.shape[0]} EEG channels, {data.shape[1]} samples)")
                    table.add_column("Sample #", style="cyan")
                    table.add_column("Timestamp", style="magenta")
                    
                    # Add column for each EEG channel
                    for i, ch_idx in enumerate(eeg_channels):
                        if i >= data.shape[0]:
                            break
                        channel_name = channel_names[ch_idx] if ch_idx < len(channel_names) else f"EEG{i+1}"
                        table.add_column(channel_name, style="green", justify="right")
                    
                    # Add rows for each sample
                    max_samples_display = min(data.shape[1], 50)  # Limit to 50 samples in vertical view
                    for j in range(-max_samples_display, 0):
                        sample_idx = data.shape[1] + j
                        ts = timestamps[sample_idx] if sample_idx < len(timestamps) else "--"
                        
                        row = [str(sample_idx + 1), str(ts)]
                        
                        # Add value for each EEG channel
                        for i in range(min(data.shape[0], len(eeg_channels))):
                            row.append(f"{data[i][sample_idx]:.4f}")
                        
                        table.add_row(*row)
                    
                    if data.shape[1] > max_samples_display:
                        console.print(f"\n[dim]Showing last {max_samples_display} samples of {data.shape[1]} total samples[/dim]")
                else:
                    # Horizontal display (existing implementation)
                    table = Table(title=f"All EEG Data ({data.shape[0]} EEG channels, {data.shape[1]} samples)")
                    table.add_column("EEG Channel", style="cyan")
                    
                    # Add columns for each sample (limit to reasonable number)
                    max_samples_display = min(data.shape[1], 20)
                    for i in range(max_samples_display):
                        table.add_column(f"S{i+1}", style="green", justify="right")
                    
                    if data.shape[1] > max_samples_display:
                        table.add_column("...", style="dim")
                    
                    for i, ch_idx in enumerate(eeg_channels):
                        if i >= data.shape[0]:
                            break
                            
                        channel_name = channel_names[ch_idx] if ch_idx < len(channel_names) else f"EEG{i+1}"
                        channel_data = data[i]
                        
                        row = [channel_name]
                        
                        # Add sample values
                        for j in range(max_samples_display):
                            if j < channel_data.size:
                                row.append(f"{channel_data[j]:.4f}")
                            else:
                                row.append("--")
                        
                        if data.shape[1] > max_samples_display:
                            row.append("...")
                        
                        table.add_row(*row)
            else:
                # Summary statistics (existing implementation)
                table = Table(title=f"EEG Data ({data.shape[0]} EEG channels, {data.shape[1]} samples)")
                table.add_column("EEG Channel", style="cyan")
                table.add_column("Latest Value", style="green")
                table.add_column("RMS", style="blue")
                table.add_column("Range", style="red")
                table.add_column("Mean", style="yellow")
                table.add_column("Std", style="magenta")
                
                metadata = data_service.get_metadata()
                eeg_channels = metadata.get("eeg_channels", [])
                channel_names = data_service.get_channel_names()
                
                for i, ch_idx in enumerate(eeg_channels):
                    if i >= data.shape[0]:
                        break
                        
                    channel_name = channel_names[ch_idx] if ch_idx < len(channel_names) else f"EEG{i+1}"
                    channel_data = data[i]
                    
                    rms = (channel_data ** 2).mean() ** 0.5
                    data_range = channel_data.max() - channel_data.min()
                    
                    table.add_row(
                        channel_name,
                        f"{channel_data[-1]:.4f}",
                        f"{rms:.4f}",
                        f"{data_range:.4f}",
                        f"{channel_data.mean():.4f}",
                        f"{channel_data.std():.4f}"
                    )
                    
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]Error getting EEG data: {e}[/red]")


@data_app.command("channel-data")
def get_channel_data(
    channel_index: int = typer.Argument(..., help="Channel index (1-based)"),
    max_samples: Optional[int] = typer.Option(None, "--max-samples", help="Maximum samples to return"),
    format: str = typer.Option("table", "--format", help="Output format: table, json"),
    all_data: bool = typer.Option(False, "--all", help="Show all data samples, not just summary statistics"),
) -> None:
    """Get data for a specific channel."""
    try:
        from ...data_access_api import EEGDataAPI

        data, timestamps = EEGDataAPI.get_channel_data(channel_index)

        if data.size == 0:
            console.print(f"[yellow]No data available for channel {channel_index}[/yellow]")
            return

        # Apply max samples limit
        if max_samples and data.size > max_samples:
            data = data[-max_samples:]
            timestamps = timestamps[-max_samples:]

        channel_names = EEGDataAPI.get_channel_names()
        channel_name = channel_names[channel_index-1] if channel_index-1 < len(channel_names) else f"CH{channel_index}"

        if format == "json":
            result = {
                "channel_index": channel_index,
                "channel_name": channel_name,
                "data": data.tolist(),
                "timestamps": timestamps,
                "samples": len(data)
            }
            console.print(json.dumps(result, indent=2))
        else:
            if all_data:
                max_samples_display = len(data)  # Por defecto muestra todas las que hay (ya recortadas por --max-samples)
                if not max_samples:
                    # Si no hay --max-samples, limita visualmente (por ejemplo a 100)
                    max_samples_display = min(len(data), 100)
                table = Table(title=f"Data for {channel_name} (Channel {channel_index}, {len(data)} samples)")
                table.add_column("Sample Index", style="cyan")
                table.add_column("Timestamp", style="magenta")
                table.add_column("Value", style="green")
                for i in range(-max_samples_display, 0):
                    idx = len(data) + i
                    ts = timestamps[idx] if idx < len(timestamps) else "--"
                    table.add_row(str(idx+1), str(ts), f"{data[idx]:.6f}")
                if len(data) > max_samples_display:
                    table.add_row("...", "...", "...")
                console.print(table)
            else:
                # Show statistics
                stats_text = f"""
Channel: {channel_name} (Index: {channel_index})
Samples: {len(data)}
Latest Value: {data[-1]:.6f}
Min: {data.min():.6f}
Max: {data.max():.6f}
Mean: {data.mean():.6f}
Std: {data.std():.6f}
RMS: {((data ** 2).mean() ** 0.5):.6f}
                """.strip()

                console.print(Panel(stats_text, title=f"Channel {channel_index} Statistics"))

    except Exception as e:
        console.print(f"[red]Error getting channel data: {e}[/red]")


@data_app.command("metadata")
def get_metadata() -> None:
    """Get stream metadata."""
    try:
        from ...data_access_api import EEGDataAPI
        
        metadata = EEGDataAPI.get_metadata()
        
        # Format metadata nicely
        table = Table(title="Stream Metadata", box=box.ROUNDED)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        # Key metadata fields
        key_fields = [
            ("streaming", "Streaming"),
            ("sampling_rate", "Sampling Rate (Hz)"),
            ("board_id", "Board ID"),
            ("board_name", "Board Name"),
            ("num_channels", "Total Channels"),
            ("eeg_channels", "EEG Channels"),
            ("channel_names", "Channel Names")
        ]
        
        for field, label in key_fields:
            value = metadata.get(field, "N/A")
            if isinstance(value, list):
                if field == "channel_names":
                    value = ", ".join(value) if value else "N/A"
                else:
                    value = str(value)
            table.add_row(label, str(value))
            
        console.print(table)
        
        # Show board info if available
        if "board_info" in metadata:
            board_info = metadata["board_info"]
            console.print("\n[bold]Detailed Board Information:[/bold]")
            console.print(json.dumps(board_info, indent=2))
            
    except Exception as e:
        console.print(f"[red]Error getting metadata: {e}[/red]")


@data_app.command("sampling-rate")
def get_sampling_rate() -> None:
    """Get current sampling rate."""
    try:
        from ...data_access_api import EEGDataAPI
        
        rate = EEGDataAPI.get_sampling_rate()
        console.print(f"[green]Sampling Rate:[/green] {rate} Hz")
        
    except Exception as e:
        console.print(f"[red]Error getting sampling rate: {e}[/red]")


@data_app.command("channel-names")
def get_channel_names() -> None:
    """Get names of all channels."""
    try:
        from ...data_access_api import EEGDataAPI
        
        names = EEGDataAPI.get_channel_names()
        
        if not names:
            console.print("[yellow]No channel names available[/yellow]")
            return
            
        table = Table(title="Channel Names")
        table.add_column("Index", style="cyan")
        table.add_column("Name", style="green")
        
        for i, name in enumerate(names):
            table.add_row(str(i+1), name)
            
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error getting channel names: {e}[/red]")


@data_app.command("board-info")
def get_board_info() -> None:
    """Get information about the connected board."""
    try:
        from ...data_access_api import EEGDataAPI
        
        board_info = EEGDataAPI.get_board_info()
        
        if not board_info:
            console.print("[yellow]No board information available[/yellow]")
            return
            
        # Show key board info
        table = Table(title="Board Information", box=box.ROUNDED)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        key_fields = [
            ("board_id", "Board ID"),
            ("board_name", "Board Name"),
            ("sampling_rate", "Sampling Rate (Hz)"),
            ("connected", "Connected"),
            ("streaming", "Streaming"),
            ("preset", "Preset")
        ]
        
        for field, label in key_fields:
            value = board_info.get(field, "N/A")
            table.add_row(label, str(value))
            
        console.print(table)
        
        # Show full info as JSON
        console.print("\n[bold]Complete Board Info:[/bold]")
        console.print(json.dumps(board_info, indent=2))
        
    except Exception as e:
        console.print(f"[red]Error getting board info: {e}[/red]")


@data_app.command("signal-quality")
def get_signal_quality(
    channel_index: Optional[int] = typer.Option(None, "--channel-index", help="Specific channel index (1-based)"),
    all_channels: bool = typer.Option(False, "--all", help="Show quality for all channels"),
) -> None:
    """Get signal quality for channels."""
    try:
        from ...data_access_api import EEGDataAPI
        
        if channel_index is not None:
            quality_values = EEGDataAPI.get_all_channels_quality()
            quality = quality_values.get(channel_index, 0.0)  # channel_index is 1-based
            channel_names = EEGDataAPI.get_channel_names()
            channel_name = channel_names[channel_index-1] if channel_index-1 < len(channel_names) else f"CH{channel_index}"
            quality_text = f"""
Channel: {channel_name} (Index: {channel_index})
Quality Score: {quality:.3f}
Quality Level: {'Excellent' if quality > 0.8 else 'Good' if quality > 0.6 else 'Fair' if quality > 0.4 else 'Poor'}
            """.strip()
            color = "green" if quality > 0.6 else "yellow" if quality > 0.4 else "red"
            console.print(Panel(quality_text, title="Signal Quality", border_style=color))
        else:
            quality_values = EEGDataAPI.get_all_channels_quality()
            if not quality_values:
                console.print("[yellow]No quality data available[/yellow]")
                return
            channel_names = EEGDataAPI.get_channel_names()
            table = Table(title="Signal Quality (All Channels)")
            table.add_column("Channel Index", style="cyan")
            table.add_column("Channel Name", style="white")
            table.add_column("Quality Score", style="green", justify="right")
            table.add_column("Level", style="yellow")
            table.add_column("Visual Bar", style="white")
            for ch_idx in sorted(quality_values.keys()):
                quality = quality_values[ch_idx]
                channel_name = channel_names[ch_idx-1] if (ch_idx-1) < len(channel_names) else f"CH{ch_idx}"
                if quality > 0.8:
                    level = "[bright_green]Excellent[/bright_green]"
                    visual = "[bright_green]" + "█" * 10 + "[/bright_green]"
                elif quality > 0.6:
                    level = "[green]Good[/green]"
                    visual = "[green]" + "█" * 8 + "░░" + "[/green]"
                elif quality > 0.4:
                    level = "[yellow]Fair[/yellow]"
                    visual = "[yellow]" + "█" * 6 + "░░░░" + "[/yellow]"
                else:
                    level = "[red]Poor[/red]"
                    visual = "[red]" + "█" * 4 + "░░░░░░" + "[/red]"
                table.add_row(
                    str(ch_idx),  # 1-based
                    channel_name, 
                    f"{quality:.3f}", 
                    level,
                    visual
                )                
            console.print(table)
            
            # Add summary statistics
            qualities = list(quality_values.values())
            excellent = sum(1 for q in qualities if q > 0.8)
            good = sum(1 for q in qualities if 0.6 < q <= 0.8)
            fair = sum(1 for q in qualities if 0.4 < q <= 0.6)
            poor = sum(1 for q in qualities if q <= 0.4)
            
            summary = f"""
[bright_green]Excellent: {excellent}[/bright_green] | [green]Good: {good}[/green] | [yellow]Fair: {fair}[/yellow] | [red]Poor: {poor}[/red]
Average Quality: {sum(qualities)/len(qualities):.3f}
            """.strip()
            console.print(Panel(summary, title="Quality Summary"))
            
    except Exception as e:
        console.print(f"[red]Error getting signal quality: {e}[/red]")