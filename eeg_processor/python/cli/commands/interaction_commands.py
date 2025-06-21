"""
Interaction commands for the CLI application.

These commands allow controlling the EEG processor application.
"""
import json
from typing import Optional, List

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .. import cli_config

control_app = typer.Typer(name="control", help="EEG processor control commands")
console = Console()


@control_app.command("connect")
def connect_to_board(
    board_id: int = typer.Argument(..., help="Board ID to connect to (use negative IDs for synthetic boards: -1, -2, -3)"),
    preset: int = typer.Option(0, "--preset", help="Data preset to use"),
    params: Optional[str] = typer.Option(None, "--params", help="Connection parameters as JSON"),
) -> None:
    """Connect to an EEG board. For negative IDs use: control connect --preset 0 -- -1"""
    try:
        from ...interaction_api import EEGProcessorInteractionAPI
        
        # Parse parameters if provided
        board_params = {}
        if params:
            try:
                board_params = json.loads(params)
            except json.JSONDecodeError:
                console.print(f"[red]Invalid JSON parameters: {params}[/red]")
                return
        
        # Show helpful info for special boards
        if board_id == -1:
            console.print(f"[blue]Connecting to Synthetic Board (ID: {board_id}) with preset {preset}...[/blue]")
            console.print("[dim]Synthetic board generates random EEG-like data for testing[/dim]")
        elif board_id == -2:
            console.print(f"[blue]Connecting to Streaming Board (ID: {board_id}) with preset {preset}...[/blue]")
        elif board_id == -3:
            console.print(f"[blue]Connecting to Playback File Board (ID: {board_id}) with preset {preset}...[/blue]")
        else:
            console.print(f"[blue]Connecting to board {board_id} with preset {preset}...[/blue]")
                
        result = EEGProcessorInteractionAPI.connect_to_board(board_id, board_params, preset)
        
        if result.get("success"):
            console.print(f"[green]Successfully connected to board {board_id}[/green]")
            console.print(f"Message: {result.get('message', '')}")
        else:
            console.print(f"[red]Failed to connect: {result.get('message', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error connecting to board: {e}[/red]")


@control_app.command("disconnect")
def disconnect_from_board() -> None:
    """Disconnect from the current board."""
    try:
        from ...interaction_api import EEGProcessorInteractionAPI
        
        console.print("[blue]Disconnecting from board...[/blue]")
        
        result = EEGProcessorInteractionAPI.disconnect_from_board()
        
        if result.get("success"):
            console.print("[green]Successfully disconnected[/green]")
        else:
            console.print(f"[red]Failed to disconnect: {result.get('message', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error disconnecting: {e}[/red]")


@control_app.command("start-stream")
def start_stream(
    buffer_size: int = typer.Option(450000, "--buffer-size", help="Buffer size for streaming"),
) -> None:
    """Start data streaming."""
    try:
        from ...interaction_api import EEGProcessorInteractionAPI
        
        console.print(f"[blue]Starting stream with buffer size {buffer_size}...[/blue]")
        
        result = EEGProcessorInteractionAPI.start_stream(buffer_size)
        
        if result.get("success"):
            console.print("[green]Stream started successfully[/green]")
        else:
            console.print(f"[red]Failed to start stream: {result.get('message', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error starting stream: {e}[/red]")


@control_app.command("stop-stream")
def stop_stream() -> None:
    """Stop data streaming."""
    try:
        from ...interaction_api import EEGProcessorInteractionAPI
        
        console.print("[blue]Stopping stream...[/blue]")
        
        result = EEGProcessorInteractionAPI.stop_stream()
        
        if result.get("success"):
            console.print("[green]Stream stopped successfully[/green]")
        else:
            console.print(f"[red]Failed to stop stream: {result.get('message', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error stopping stream: {e}[/red]")


@control_app.command("start-recording")
def start_recording(
    filename: str = typer.Argument(..., help="Recording filename"),
    data_type: str = typer.Option("raw", "--data-type", help="Data type: raw, processed, both"),
) -> None:
    """Start data recording."""
    try:
        from ...interaction_api import EEGProcessorInteractionAPI
        
        console.print(f"[blue]Starting recording to {filename} ({data_type} data)...[/blue]")
        
        result = EEGProcessorInteractionAPI.start_recording(filename, data_type)
        
        if result.get("success"):
            console.print(f"[green]Recording started: {filename}[/green]")
        else:
            console.print(f"[red]Failed to start recording: {result.get('message', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error starting recording: {e}[/red]")


@control_app.command("stop-recording")
def stop_recording() -> None:
    """Stop data recording."""
    try:
        from ...interaction_api import EEGProcessorInteractionAPI
        
        console.print("[blue]Stopping recording...[/blue]")
        
        result = EEGProcessorInteractionAPI.stop_recording()
        
        if result.get("success"):
            console.print("[green]Recording stopped successfully[/green]")
        else:
            console.print(f"[red]Failed to stop recording: {result.get('message', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error stopping recording: {e}[/red]")


@control_app.command("apply-filters")
def apply_filters(
    bandpass_low: float = typer.Option(1.0, "--bandpass-low", help="Bandpass low cutoff (Hz)"),
    bandpass_high: float = typer.Option(50.0, "--bandpass-high", help="Bandpass high cutoff (Hz)"),
    notch_freq: int = typer.Option(50, "--notch-freq", help="Notch filter frequency (50 or 60 Hz)"),
    enable_bandpass: bool = typer.Option(True, "--enable-bandpass/--disable-bandpass", help="Enable bandpass filter"),
    enable_notch: bool = typer.Option(True, "--enable-notch/--disable-notch", help="Enable notch filter"),
    enable_detrend: bool = typer.Option(True, "--enable-detrend/--disable-detrend", help="Enable detrend"),
    apply_to_viz: bool = typer.Option(True, "--apply-to-viz/--no-viz", help="Apply to visualization"),
) -> None:
    """Apply signal processing filters."""
    try:
        from ...interaction_api import EEGProcessorInteractionAPI
        
        filter_config = {
            "bandpass": {
                "enabled": enable_bandpass,
                "low_cut": bandpass_low,
                "high_cut": bandpass_high
            },
            "notch": {
                "enabled": enable_notch,
                "frequency": notch_freq
            },
            "detrend": enable_detrend,
            "apply_to_visualization": apply_to_viz
        }
        
        console.print("[blue]Applying filters...[/blue]")
        console.print(f"Bandpass: {'ON' if enable_bandpass else 'OFF'} ({bandpass_low}-{bandpass_high} Hz)")
        console.print(f"Notch: {'ON' if enable_notch else 'OFF'} ({notch_freq} Hz)")
        console.print(f"Detrend: {'ON' if enable_detrend else 'OFF'}")
        
        result = EEGProcessorInteractionAPI.apply_filters(filter_config)
        
        if result.get("success"):
            console.print("[green]Filters applied successfully[/green]")
        else:
            console.print(f"[red]Failed to apply filters: {result.get('message', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error applying filters: {e}[/red]")


@control_app.command("start-viz")
def start_visualization(
    viz_type: str = typer.Option("eeg", "--type", help="Visualization type: eeg, brain_map"),
) -> None:
    """Start data visualization."""
    try:
        from ...interaction_api import EEGProcessorInteractionAPI
        
        console.print(f"[blue]Starting {viz_type} visualization...[/blue]")
        
        result = EEGProcessorInteractionAPI.start_visualization(viz_type)
        
        if result.get("success"):
            console.print(f"[green]{viz_type.title()} visualization started[/green]")
        else:
            console.print(f"[red]Failed to start visualization: {result.get('message', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error starting visualization: {e}[/red]")


@control_app.command("stop-viz")
def stop_visualization(
    viz_type: str = typer.Option("eeg", "--type", help="Visualization type: eeg, brain_map"),
) -> None:
    """Stop data visualization."""
    try:
        from ...interaction_api import EEGProcessorInteractionAPI
        
        console.print(f"[blue]Stopping {viz_type} visualization...[/blue]")
        
        result = EEGProcessorInteractionAPI.stop_visualization(viz_type)
        
        if result.get("success"):
            console.print(f"[green]{viz_type.title()} visualization stopped[/green]")
        else:
            console.print(f"[red]Failed to stop visualization: {result.get('message', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error stopping visualization: {e}[/red]")


@control_app.command("ica")
def perform_ica(
    num_components: int = typer.Argument(..., help="Number of ICA components (2-16)"),
    channels: Optional[str] = typer.Option(None, "--channels", help="Channel indices (comma-separated)"),
) -> None:
    """Perform Independent Component Analysis."""
    try:
        from ...interaction_api import EEGProcessorInteractionAPI
        
        # Parse channel indices
        selected_channels = None
        if channels:
            try:
                selected_channels = [int(x.strip()) for x in channels.split(",")]
            except ValueError:
                console.print("[red]Invalid channel indices format. Use comma-separated integers.[/red]")
                return
                
        console.print(f"[blue]Performing ICA with {num_components} components...[/blue]")
        if selected_channels:
            console.print(f"Using channels: {selected_channels}")
            
        result = EEGProcessorInteractionAPI.perform_ica(num_components, selected_channels)
        
        if result.get("success"):
            console.print("[green]ICA computation started successfully[/green]")
            console.print(f"Components: {result.get('num_components')}")
            console.print(f"Channels: {len(result.get('selected_channels', []))}")
        else:
            console.print(f"[red]Failed to perform ICA: {result.get('message', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error performing ICA: {e}[/red]")


@control_app.command("mne-convert")
def convert_to_mne(
    duration: int = typer.Argument(..., help="Duration in seconds (1-60)"),
    use_filters: bool = typer.Option(True, "--use-filters/--no-filters", help="Use processing panel filters"),
) -> None:
    """Convert EEG data to MNE format."""
    try:
        from ...interaction_api import EEGProcessorInteractionAPI
        
        console.print(f"[blue]Converting {duration} seconds of data to MNE format...[/blue]")
        console.print(f"Using filters: {'YES' if use_filters else 'NO'}")
        
        result = EEGProcessorInteractionAPI.convert_to_mne(duration, use_filters)
        
        if result.get("success"):
            console.print("[green]MNE conversion started successfully[/green]")
        else:
            console.print(f"[red]Failed to convert to MNE: {result.get('message', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error converting to MNE: {e}[/red]")


@control_app.command("wavelet")
def compute_wavelet(
    wavelet_type: int = typer.Argument(..., help="Wavelet type (0=Haar, 4=DB4, etc.)"),
    level: int = typer.Argument(..., help="Decomposition level (1-8)"),
    channel: int = typer.Argument(..., help="Channel index (0-based)"),
    extension: int = typer.Option(0, "--extension", help="Extension type (0=symmetric, 1=periodic)"),
    denoising: bool = typer.Option(False, "--denoising", help="Apply wavelet denoising"),
) -> None:
    """Compute wavelet transform."""
    try:
        from ...interaction_api import EEGProcessorInteractionAPI
        
        console.print(f"[blue]Computing wavelet transform...[/blue]")
        console.print(f"Type: {wavelet_type}, Level: {level}, Channel: {channel}")
        console.print(f"Extension: {extension}, Denoising: {'YES' if denoising else 'NO'}")
        
        result = EEGProcessorInteractionAPI.compute_wavelet(wavelet_type, level, channel, extension, denoising)
        
        if result.get("success"):
            console.print("[green]Wavelet computation started successfully[/green]")
        else:
            console.print(f"[red]Failed to compute wavelet: {result.get('message', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error computing wavelet: {e}[/red]")


@control_app.command("downsampling")
def apply_downsampling(
    factor: int = typer.Argument(..., help="Downsampling factor (2-10)"),
    method: str = typer.Option("mean", "--method", help="Aggregation method: mean, median, each"),
    apply: bool = typer.Option(True, "--apply/--remove", help="Apply or remove downsampling"),
) -> None:
    """Apply or remove downsampling."""
    try:
        from ...interaction_api import EEGProcessorInteractionAPI
        
        # Map method name to enum value
        method_map = {"mean": 0, "median": 1, "each": 2}
        method_value = method_map.get(method.lower(), 0)
        
        action = "Applying" if apply else "Removing"
        console.print(f"[blue]{action} downsampling with factor {factor} ({method})...[/blue]")
        
        result = EEGProcessorInteractionAPI.apply_downsampling(factor, method_value, apply)
        
        if result.get("success"):
            console.print(f"[green]Downsampling {'applied' if apply else 'removed'} successfully[/green]")
        else:
            console.print(f"[red]Failed to apply downsampling: {result.get('message', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error applying downsampling: {e}[/red]")


@control_app.command("status")
def get_system_status() -> None:
    """Get comprehensive system status."""
    try:
        from ...interaction_api import EEGProcessorInteractionAPI
        
        result = EEGProcessorInteractionAPI.get_system_status()
        
        if result.get("success"):
            status = result.get("status", {})
            
            # Create status table
            table = Table(title="System Status")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Details", style="yellow")
            
            # Connection status
            connected = status.get("connected", False)
            table.add_row("Connection", "✓ Connected" if connected else "✗ Disconnected", 
                         status.get("board_name", "N/A"))
            
            # Streaming status
            streaming = status.get("streaming", False)
            table.add_row("Streaming", "✓ Active" if streaming else "✗ Inactive", 
                         f"{status.get('sampling_rate', 0)} Hz")
            
            # Recording status
            recording = status.get("recording", False)
            table.add_row("Recording", "✓ Recording" if recording else "✗ Not Recording", 
                         status.get("recording_filename", "N/A") if recording else "N/A")
            
            # Data availability
            data_available = status.get("data_available", False)
            table.add_row("Data", "✓ Available" if data_available else "✗ No Data", 
                         f"{len(status.get('channel_names', []))} channels")
            
            console.print(table)
            
        else:
            console.print(f"[red]Failed to get status: {result.get('message', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error getting status: {e}[/red]")


@control_app.command("boards")
def list_available_boards() -> None:
    """List all supported EEG boards from BrainFlow."""
    try:
        from brainflow.board_shim import BoardIds, BoardShim

        # Mapping: nombre amigable a board_id (completado según el enum)
        board_mapping = {
            # Negative IDs for special boards
            "Synthetic Board": BoardIds.SYNTHETIC_BOARD.value,
            "Playback File Board": BoardIds.PLAYBACK_FILE_BOARD.value,
            "Streaming Board": BoardIds.STREAMING_BOARD.value,
            # Positive IDs for real boards
            "Cyton": BoardIds.CYTON_BOARD.value,
            "Ganglion": BoardIds.GANGLION_BOARD.value,
            "Cyton Daisy": BoardIds.CYTON_DAISY_BOARD.value,
            "Galea": BoardIds.GALEA_BOARD.value,
            "Ganglion WiFi": BoardIds.GANGLION_WIFI_BOARD.value,
            "Cyton WiFi": BoardIds.CYTON_WIFI_BOARD.value,
            "Cyton Daisy WiFi": BoardIds.CYTON_DAISY_WIFI_BOARD.value,
            "BrainBit": BoardIds.BRAINBIT_BOARD.value,
            "Unicorn": BoardIds.UNICORN_BOARD.value,
            "Callibri EEG": BoardIds.CALLIBRI_EEG_BOARD.value,
            "Callibri EMG": BoardIds.CALLIBRI_EMG_BOARD.value,
            "Callibri ECG": BoardIds.CALLIBRI_ECG_BOARD.value,
            "Notion OSC 1": BoardIds.NOTION_1_BOARD.value,
            "Notion OSC 2": BoardIds.NOTION_2_BOARD.value,
            "Gforce Pro": BoardIds.GFORCE_PRO_BOARD.value,
            "FreeEEG32": BoardIds.FREEEEG32_BOARD.value,
            "BrainBit BLED": BoardIds.BRAINBIT_BLED_BOARD.value,
            "Gforce Dual": BoardIds.GFORCE_DUAL_BOARD.value,
            "Galea Serial": BoardIds.GALEA_SERIAL_BOARD.value,
            "Muse S BLED": BoardIds.MUSE_S_BLED_BOARD.value,
            "Muse 2 BLED": BoardIds.MUSE_2_BLED_BOARD.value,
            "Crown OSC": BoardIds.CROWN_BOARD.value,
            "AntNeuroEE410": BoardIds.ANT_NEURO_EE_410_BOARD.value,
            "AntNeuroEE411": BoardIds.ANT_NEURO_EE_411_BOARD.value,
            "AntNeuroEE430": BoardIds.ANT_NEURO_EE_430_BOARD.value,
            "AntNeuroEE211": BoardIds.ANT_NEURO_EE_211_BOARD.value,
            "AntNeuroEE212": BoardIds.ANT_NEURO_EE_212_BOARD.value,
            "AntNeuroEE213": BoardIds.ANT_NEURO_EE_213_BOARD.value,
            "AntNeuroEE214": BoardIds.ANT_NEURO_EE_214_BOARD.value,
            "AntNeuroEE215": BoardIds.ANT_NEURO_EE_215_BOARD.value,
            "AntNeuroEE221": BoardIds.ANT_NEURO_EE_221_BOARD.value,
            "AntNeuroEE222": BoardIds.ANT_NEURO_EE_222_BOARD.value,
            "AntNeuroEE223": BoardIds.ANT_NEURO_EE_223_BOARD.value,
            "AntNeuroEE224": BoardIds.ANT_NEURO_EE_224_BOARD.value,
            "AntNeuroEE225": BoardIds.ANT_NEURO_EE_225_BOARD.value,
            "Enophone": BoardIds.ENOPHONE_BOARD.value,
            "Muse 2": BoardIds.MUSE_2_BOARD.value,
            "Muse S": BoardIds.MUSE_S_BOARD.value,
            "BrainAlive": BoardIds.BRAINALIVE_BOARD.value,
            "Muse 2016": BoardIds.MUSE_2016_BOARD.value,
            "Muse 2016 BLED": BoardIds.MUSE_2016_BLED_BOARD.value,
            "Explore 4 Channels": BoardIds.EXPLORE_4_CHAN_BOARD.value,
            "Explore 8 Channels": BoardIds.EXPLORE_8_CHAN_BOARD.value,
            "Ganglion Native": BoardIds.GANGLION_NATIVE_BOARD.value,
            "Emotibit": BoardIds.EMOTIBIT_BOARD.value,
            "Galea V4": BoardIds.GALEA_BOARD_V4.value,
            "Galea Serial V4": BoardIds.GALEA_SERIAL_BOARD_V4.value,
            "NTL WiFi": BoardIds.NTL_WIFI_BOARD.value,
            "AntNeuroEE511": BoardIds.ANT_NEURO_EE_511_BOARD.value,
            "FreeEEG128": BoardIds.FREEEEG128_BOARD.value,
            "AAVAA V3": BoardIds.AAVAA_V3_BOARD.value,
            "Explore Plus 8 Channels": BoardIds.EXPLORE_PLUS_8_CHAN_BOARD.value,
            "Explore Plus 32 Channels": BoardIds.EXPLORE_PLUS_32_CHAN_BOARD.value,
            "PIEEG": BoardIds.PIEEG_BOARD.value,
            "Knight": BoardIds.NEUROPAWN_KNIGHT_BOARD.value,
        }

        # Invertimos el mapping para obtener nombre a partir de ID rápido
        id_to_name = {v: k for k, v in board_mapping.items()}

        # Lista de todos los IDs del enum excepto NO_BOARD
        all_ids = [
            BoardIds.PLAYBACK_FILE_BOARD.value,
            BoardIds.STREAMING_BOARD.value,
            BoardIds.SYNTHETIC_BOARD.value,
            BoardIds.CYTON_BOARD.value,
            BoardIds.GANGLION_BOARD.value,
            BoardIds.CYTON_DAISY_BOARD.value,
            BoardIds.GALEA_BOARD.value,
            BoardIds.GANGLION_WIFI_BOARD.value,
            BoardIds.CYTON_WIFI_BOARD.value,
            BoardIds.CYTON_DAISY_WIFI_BOARD.value,
            BoardIds.BRAINBIT_BOARD.value,
            BoardIds.UNICORN_BOARD.value,
            BoardIds.CALLIBRI_EEG_BOARD.value,
            BoardIds.CALLIBRI_EMG_BOARD.value,
            BoardIds.CALLIBRI_ECG_BOARD.value,
            BoardIds.NOTION_1_BOARD.value,
            BoardIds.NOTION_2_BOARD.value,
            BoardIds.GFORCE_PRO_BOARD.value,
            BoardIds.FREEEEG32_BOARD.value,
            BoardIds.BRAINBIT_BLED_BOARD.value,
            BoardIds.GFORCE_DUAL_BOARD.value,
            BoardIds.GALEA_SERIAL_BOARD.value,
            BoardIds.MUSE_S_BLED_BOARD.value,
            BoardIds.MUSE_2_BLED_BOARD.value,
            BoardIds.CROWN_BOARD.value,
            BoardIds.ANT_NEURO_EE_410_BOARD.value,
            BoardIds.ANT_NEURO_EE_411_BOARD.value,
            BoardIds.ANT_NEURO_EE_430_BOARD.value,
            BoardIds.ANT_NEURO_EE_211_BOARD.value,
            BoardIds.ANT_NEURO_EE_212_BOARD.value,
            BoardIds.ANT_NEURO_EE_213_BOARD.value,
            BoardIds.ANT_NEURO_EE_214_BOARD.value,
            BoardIds.ANT_NEURO_EE_215_BOARD.value,
            BoardIds.ANT_NEURO_EE_221_BOARD.value,
            BoardIds.ANT_NEURO_EE_222_BOARD.value,
            BoardIds.ANT_NEURO_EE_223_BOARD.value,
            BoardIds.ANT_NEURO_EE_224_BOARD.value,
            BoardIds.ANT_NEURO_EE_225_BOARD.value,
            BoardIds.ENOPHONE_BOARD.value,
            BoardIds.MUSE_2_BOARD.value,
            BoardIds.MUSE_S_BOARD.value,
            BoardIds.BRAINALIVE_BOARD.value,
            BoardIds.MUSE_2016_BOARD.value,
            BoardIds.MUSE_2016_BLED_BOARD.value,
            BoardIds.EXPLORE_4_CHAN_BOARD.value,
            BoardIds.EXPLORE_8_CHAN_BOARD.value,
            BoardIds.GANGLION_NATIVE_BOARD.value,
            BoardIds.EMOTIBIT_BOARD.value,
            BoardIds.GALEA_BOARD_V4.value,
            BoardIds.GALEA_SERIAL_BOARD_V4.value,
            BoardIds.NTL_WIFI_BOARD.value,
            BoardIds.ANT_NEURO_EE_511_BOARD.value,
            BoardIds.FREEEEG128_BOARD.value,
            BoardIds.AAVAA_V3_BOARD.value,
            BoardIds.EXPLORE_PLUS_8_CHAN_BOARD.value,
            BoardIds.EXPLORE_PLUS_32_CHAN_BOARD.value,
            BoardIds.PIEEG_BOARD.value,
            BoardIds.NEUROPAWN_KNIGHT_BOARD.value,
        ]

        boards = []
        for board_id in sorted(all_ids):
            name = id_to_name.get(board_id, f"Board {board_id}")
            # Intenta obtener la descripción del BoardShim
            try:
                board_desc = BoardShim.get_board_descr(board_id)
                description = board_desc.get("name", name)
            except Exception:
                description = name
            boards.append({
                "board_id": board_id,
                "name": name,
                "description": description
            })

        if not boards:
            console.print("[yellow]No boards available[/yellow]")
            return

        table = Table(title="Available EEG Boards")
        table.add_column("Board ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description", style="yellow")

        for board in boards:
            table.add_row(
                str(board["board_id"]),
                board["name"],
                board["description"]
            )

        console.print(table)

        # Add helpful note about special boards
        console.print("\n[dim]Note: Use negative IDs for special boards:[/dim]")
        console.print("[dim]  -1: Synthetic Board (for testing)[/dim]")
        console.print("[dim]  -2: Streaming Board[/dim]")
        console.print("[dim]  -3: Playback File Board[/dim]")

    except Exception as e:
        console.print(f"[red]Error listing boards: {e}[/red]")