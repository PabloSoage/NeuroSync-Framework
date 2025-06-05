# Input Collector CLI

This command-line interface allows you to control and monitor the Input Collector application without using the GUI.

## Installation

Install the required dependencies:

```bash
pip install -r requirements_cli.txt
```

## Usage

### Running in Headless Mode

To run the input collector without a GUI:

```bash
python run.py --no-gui
```

You can combine this with API options:

```bash
python run.py --no-gui --enable-web-api --api-port=8000 --enable-control-api --control-api-port=8001
```

### Available Commands

```bash
# Show general info
input-collector info

# Monitor events in real-time
input-collector monitor events

# Monitor active keys
input-collector monitor active-keys

# Monitor mouse
input-collector monitor mouse

# Monitor application status
input-collector monitor status

# Control recording
input-collector control recording start
input-collector control recording stop
input-collector control recording status

# Configure logging
input-collector control logging csv --action enable --filepath "data.csv"
input-collector control logging json --action enable
input-collector control logging status

# Manage collectors
input-collector control collectors list
input-collector control collectors switch --type keyboard_mouse
input-collector control collectors scan
input-collector control collectors connect --index 0

# Configure mouse tracking
input-collector control mouse mode --mode axis --direction-only
input-collector control mouse settings --delta-smoothing 30 --joystick-sensitivity 120 --angle-grouping 45

# Manage tracked keys
input-collector control keys list
input-collector control keys add --key "w"
input-collector control keys remove --key "w"
```

## Data Access Commands

```bash
# Get active keys
input-collector data active-keys

# Check if a specific key is active
input-collector data is-key-active "w"

# Get mouse position
input-collector data mouse-position

# Check mouse button state
input-collector data mouse-button left

# Get mouse direction
input-collector data mouse-direction

# Get collector metadata
input-collector data metadata

# Get current event
input-collector data current-event

# Get recent events by type
input-collector data events key --count 10
input-collector data events mouse_movement --count 10
input-collector data events mouse_button --count 10
```
