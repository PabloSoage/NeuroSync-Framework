# Input Collector CLI

This command-line interface allows you to control and monitor the Input Collector application with an interactive shell environment.

## Installation

Install the required dependencies:

```bash
pip install -r requirements_cli.txt
```

## Starting the CLI

### CLI Operation Modes

You have two options for using the CLI:

1. **CLI-only mode** (no GUI): 
```bash
python run.py --no-gui
```

2. **Combined GUI and CLI mode** (both interfaces simultaneously):  
```bash
python run.py --cli
```

You can combine these with API options:

```bash
# CLI-only with both APIs enabled
python run.py --no-gui --enable-web-api --api-port=8000 --enable-control-api --control-api-port=8001

# GUI+CLI with both APIs enabled
python run.py --cli --enable-web-api --enable-control-api
```

## Using the Interactive Shell

Once the CLI starts, you'll be presented with an interactive shell that has a split view:
- Left panel: Command input and output
- Right panel: System logs (can be toggled)

### Built-in Shell Commands

```
help         # Show available commands
exit         # Exit the CLI shell
status       # Show current application status
logs         # Toggle visibility of the log panel
clear        # Clear the main panel
clearlogs    # Clear the log history
```

### Available Commands by Category

All commands start with a category prefix (`data`, `control`, or `monitor`):

#### Monitor Commands

```
# Live monitoring of input events
monitor events                       # Monitor all input events in real-time
monitor events --type key            # Monitor only keyboard events
monitor events --type mouse          # Monitor only mouse movement events
monitor events --count 20            # Show up to 20 events per type

# Status monitoring
monitor active-keys                  # Monitor active keys in real-time
monitor mouse                        # Monitor mouse movement and buttons
monitor status                       # Monitor overall application status
```

#### Control Commands

```
# Recording control
control recording start              # Start recording
control recording stop               # Stop recording
control recording toggle             # Toggle recording state
control recording status             # Check recording status

# Logging control
control logging csv --action enable --filepath "data.csv"    # Enable CSV logging
control logging json --action enable                         # Enable JSON logging
control logging status                                       # Check logging status

# Collector management
control collectors list              # List available collectors
control collectors current           # Show current collector
control collectors switch --type keyboard_mouse              # Switch to keyboard & mouse
control collectors scan              # Scan for controllers
control collectors connect --index 0                         # Connect to a controller

# Mouse tracking configuration
control mouse mode --mode axis --direction-only              # Set mouse tracking mode
control mouse settings --delta-smoothing 30 --joystick-sensitivity 120 --angle-grouping 45  # Configure mouse tracking
control mouse tracking-modes         # List available tracking modes

# Key management
control keys list                    # List tracked keys
control keys add --key "w"           # Add key to track
control keys remove --key "w"        # Remove tracked key
control keys edit-mode               # Toggle edit mode

# General control
control status                       # Show full application status
control fullscreen                   # Toggle fullscreen mode (GUI only)
```

#### Data Access Commands

```
# Key state information
data active-keys                     # Get currently active keys
data is-key-active "w"               # Check if specific key is active

# Mouse information
data mouse-position                  # Get current mouse position
data mouse-button left               # Check state of left mouse button
data mouse-direction                 # Get current mouse direction

# Event history
data events key --count 10           # Get last 10 keyboard events
data events mouse_movement --count 5 # Get last 5 mouse movement events
data events mouse_button --count 3   # Get last 3 mouse button events

# System information
data metadata                        # Get collector metadata
data current-event                   # Get most recent input event
data controller-connected            # Check if controller is connected
```

## Interactive Usage Example

```
input-collector> help
[Shows help information]

input-collector> status
[Shows current status]

input-collector> control recording start
Recording started

input-collector> monitor events --type key
[Live display of keyboard events - press Ctrl+C to exit]

input-collector> data active-keys
Active keys:
- w
- Key.shift

input-collector> exit
Exiting Input Collector CLI...
```
