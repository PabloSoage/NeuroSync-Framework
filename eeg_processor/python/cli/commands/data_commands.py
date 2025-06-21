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
) -> None:
    """Get current EEG data from all channels."""
    try:
        from ...data_access_api import EEGDataAPI
        
        data, timestamps = EEGDataAPI.get_current_data()
        
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
            # Table format
            table = Table(title=f"Current EEG Data ({data.shape[0]} channels, {data.shape[1]} samples)")
            table.add_column("Channel", style="cyan")
            table.add_column("Latest Value", style="green")
            table.add_column("Min", style="blue")
            table.add_column("Max", style="red")
            table.add_column("Mean", style="yellow")
            
            channel_names = EEGDataAPI.get_channel_names()
            
            for i in range(data.shape[0]):
                channel_name = channel_names[i] if i < len(channel_names) else f"CH{i+1}"
                channel_data = data[i]
                
                table.add_row(
                    channel_name,
                    f"{channel_data[-1]:.4f}",
                    f"{channel_data.min():.4f}",
                    f"{channel_data.max():.4f}",
                    f"{channel_data.mean():.4f}"
                )
                
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]Error getting current data: {e}[/red]")


@data_app.command("eeg-data")
def get_eeg_data(
    max_samples: Optional[int] = typer.Option(None, "--max-samples", help="Maximum samples to return"),
    format: str = typer.Option("table", "--format", help="Output format: table, json"),
) -> None:
    """Get current data for EEG channels only."""
    try:
        from ...data_access_api import EEGDataAPI
        
        data, timestamps = EEGDataAPI.get_eeg_data(max_samples)
        
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
            # Table format
            table = Table(title=f"EEG Data ({data.shape[0]} EEG channels, {data.shape[1]} samples)")
            table.add_column("EEG Channel", style="cyan")
            table.add_column("Latest Value", style="green")
            table.add_column("RMS", style="blue")
            table.add_column("Range", style="red")
            
            eeg_channels = EEGDataAPI.get_eeg_channels()
            channel_names = EEGDataAPI.get_channel_names()
            
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
                    f"{data_range:.4f}"
                )
                
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]Error getting EEG data: {e}[/red]")


@data_app.command("channel-data")
def get_channel_data(
    channel_index: int = typer.Argument(..., help="Channel index (1-based)"),
    max_samples: Optional[int] = typer.Option(None, "--max-samples", help="Maximum samples to return"),
    format: str = typer.Option("table", "--format", help="Output format: table, json"),
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
) -> None:
    """Get signal quality for channels."""
    try:
        from ...data_access_api import EEGDataAPI
        
        if channel_index is not None:
            # Get quality for specific channel
            from ...processors.signal_processor import SignalProcessor
            
            data, _ = EEGDataAPI.get_current_data()
            if data.size == 0:
                console.print("[yellow]No data available for quality assessment[/yellow]")
                return
                
            sampling_rate = EEGDataAPI.get_sampling_rate()
            processor = SignalProcessor(sampling_rate)
            
            # Convert from 1-based to 0-based index
            quality = processor.get_signal_quality(data, channel_index - 1)
            
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
            # Get quality for all channels
            quality_values = EEGDataAPI.get_all_channels_quality()
            
            if not quality_values:
                console.print("[yellow]No quality data available[/yellow]")
                return
                
            table = Table(title="Signal Quality (All Channels)")
            table.add_column("Channel", style="cyan")
            table.add_column("Quality Score", style="green")
            table.add_column("Level", style="yellow")
            
            channel_names = EEGDataAPI.get_channel_names()
            
            for ch_idx, quality in quality_values.items():
                channel_name = channel_names[ch_idx] if ch_idx < len(channel_names) else f"CH{ch_idx+1}"
                
                if quality > 0.8:
                    level = "[green]Excellent[/green]"
                elif quality > 0.6:
                    level = "[yellow]Good[/yellow]"
                elif quality > 0.4:
                    level = "[orange1]Fair[/orange1]"
                else:
                    level = "[red]Poor[/red]"
                    
                table.add_row(channel_name, f"{quality:.3f}", level)
                
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]Error getting signal quality: {e}[/red]")