# EEG Processor CLI

This command-line interface allows you to control and monitor the EEG Processor application with an interactive shell environment.

## Installation

Install the required dependencies:

```bash
pip install -r requirements_cli.txt
```

## Usage

### Running CLI with GUI

Start both the GUI and CLI simultaneously:

```bash
python run.py --cli
```

### Running CLI Only (Headless Mode)

Start only the CLI without GUI:

```bash
python run.py --no-gui
```

### API Integration

Enable web APIs alongside CLI:

```bash
# With data access API
python run.py --cli --enable-web-api --api-port 8000

# With control API
python run.py --cli --enable-control-api --control-api-port 8001
```

## CLI Commands

### Connection Commands
```bash
# Connect to synthetic board
control connect -1 --preset 0

# Connect to real board with parameters
control connect 0 --params '{"serial_port": "COM3"}'

# Disconnect
control disconnect

# List available boards
control boards
```

### Data Commands
```bash
# Get current data
data current-data --max-samples 100

# Get EEG channels only
data eeg-data --max-samples 50

# Get specific channel
data channel-data 1 --max-samples 100

# Get metadata
data metadata

# Get sampling rate
data sampling-rate

# Check signal quality
data signal-quality --channel-index 1
```

### Streaming Commands
```bash
# Start stream
control start-stream --buffer-size 450000

# Stop stream
control stop-stream

# Get status
control status
```

### Processing Commands
```bash
# Apply filters
control apply-filters --bandpass-low 1.0 --bandpass-high 50.0 --notch-freq 50

# Perform ICA
control ica 8 --channels "0,1,2,3,4,5,6,7"

# Convert to MNE
control mne-convert 10 --use-filters

# Compute wavelets
control wavelet 4 3 0 --denoising

# Apply downsampling
control downsampling 2 --method mean --apply
```

### Recording Commands
```bash
# Start recording
control start-recording recording.csv --data-type raw

# Stop recording
control stop-recording

# Insert marker
control insert-marker 100
```

### Monitoring Commands
```bash
# Monitor data stream
monitor stream --duration 30 --refresh-rate 0.5

# Monitor system status
monitor status --refresh-rate 2.0

# Monitor specific channels
monitor channels --channels "0,1,2,3" --refresh-rate 1.0

# Monitor signal quality
monitor quality --refresh-rate 3.0

# Monitor recording
monitor recording --refresh-rate 1.0
```

### Visualization Commands
```bash
# Start EEG visualization
control start-viz --type eeg

# Stop visualization
control stop-viz --type eeg

# Start brain map
control start-viz --type brain_map
```

## Interactive Shell Commands

When in the interactive shell, you can use these special commands:

- `help` - Show available commands
- `status` - Show current system status
- `clear` - Clear the screen
- `exit` or `quit` - Exit the CLI

## Advanced Features

### Real-time Monitoring

The monitor commands provide real-time displays with Rich formatting:

- Live data tables with automatic updates
- Color-coded signal quality indicators
- Progress bars and status indicators
- Multi-panel layouts for comprehensive monitoring

### API Integration

The CLI can work alongside web APIs:

- Data Access API for real-time data retrieval
- Control API for remote system control
- WebSocket support for live data streaming

### Error Handling

The CLI provides comprehensive error handling:

- Connection status validation
- Parameter validation with helpful messages
- Handling of service failures
- Detailed error reporting

## Examples

### Complete Workflow

```bash
# Start the CLI
python run.py --no-gui

# Check available boards
control boards

# Connect to synthetic board
control connect -1 --preset 0

# Start streaming
control start-stream

# Monitor data in real-time
monitor stream --duration 30

# Apply signal processing
control apply-filters --bandpass-low 1.0 --bandpass-high 50.0

# Start recording
control start-recording test_recording.csv

# Monitor recording progress
monitor recording

# Stop recording after some time
control stop-recording

# Perform analysis
control ica 8
control mne-convert 10

# Stop streaming and disconnect
control stop-stream
control disconnect

# Exit
exit
```

### Quick Data Check

```bash
# Get current status
control status

# Check if data is flowing
data current-data --max-samples 10

# Check signal quality
data signal-quality
```

## Configuration

The CLI respects the same configuration as the main application:

- Board configurations in `collectors/board_configuration.py`
- Service settings from the main application
- Logging levels and output formatting

## Troubleshooting

### Common Issues

1. **"Services not available"** - Make sure the EEG processor is properly initialized
2. **"No data available"** - Ensure a board is connected and streaming is active
3. **"Invalid board ID"** - Check available boards with `control boards`
4. **"Command not found"** - Use `help` to see available commands

### Debug Mode

Enable debug logging for detailed information:

```bash
python run.py --no-gui --logging debug
```
