# Input Collector - Architecture and Technical Documentation

## Summary

Input Collector is a comprehensive application designed to capture, process, visualize, and log real-time input events from multiple devices (keyboard, mouse, PS4 controllers). The application implements a **modular event-driven architecture** that supports multiple user interfaces (GUI, CLI, Web API) and provides extensible capabilities for different collector types and visualization modes.

## General Architecture

### Main Architectural Pattern

The application follows a **hexagonal architecture (Ports and Adapters)** combined with **Mediator**, **Observer** and **Event-Driven Architecture** patterns, organizing code into well-defined layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL INTERFACES                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │    GUI      │  │     CLI     │  │     Web API         │ │
│  │  (PyQt5)    │  │   (Typer)   │  │  (API Explorer)     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                       ADAPTERS                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │QtInteraction│  │ CLI Commands│  │ API Integrations    │ │
│  │   Adapter   │  │             │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │Interaction  │  │Data Access  │  │  Core Event System  │ │
│  │  Service    │  │  Service    │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION CORE                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │    App      │  │ Collectors  │  │    Processing       │ │
│  │ Coordinator │  │   Manager   │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                        DOMAIN                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Interfaces  │  │ Visualizers │  │     Logging         │ │
│  │             │  │             │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Submodules and Components

### 1. **Core Event System** (`core/`)

**Purpose**: Centralized, framework-independent event system for decoupled communication between components.

#### Components:
- **`EventDispatcher`**: Thread-safe singleton managing subscriptions and event dispatching
- **`EventType`**: Enumeration of system event types (INPUT, STATE_CHANGE, RECORDING_STARTED, etc.)
- **Utility Functions**: Simplified API for common usage (`dispatch`, `subscribe`, `unsubscribe`)

#### Features:
- **Event-driven architecture**: Decoupled communication between modules
- **Thread-safe**: Multiple granular locks for different operations
- **Error isolation**: Callback failures don't affect other subscribers
- **Late synchronization**: Last event storage for later subscribers
- **Framework-independent**: No dependency on Qt or other frameworks

```python
# Enhanced usage example
from core import dispatch, subscribe, EventType

def on_input_event(data):
    print(f"Received input: {data}")

def on_recording_started(data):
    print(f"Recording started: {data}")

# Subscribe to multiple event types
subscribe(EventType.INPUT, on_input_event)
subscribe(EventType.RECORDING_STARTED, on_recording_started)

# Dispatch with structured data
dispatch(EventType.INPUT, {
    "key": "A", 
    "timestamp": time.time(),
    "collector_type": "keyboard_mouse"
})
```

### 2. **Interfaces** (`interfaces/`)

**Purpose**: Definition of contracts and fundamental data structures.

#### Components:
- **`InputData`**: Main dataclass for input events (25+ fields)
- **`AbstractInputCollector`**: Interface for input collectors
- **`AbstractVisualizer`**: Interface for visualizers
- **`AbstractVisualizerProvider/Controller`**: Protocols for UI management

#### Features:
- **Comprehensive dataclass**: Support for all input types and tracking modes
- **Consistent contracts**: Interfaces ensuring uniform behavior
- **Structural typing**: Python protocols for flexibility
- **Serialization**: Optimized `to_dict()` method for logging and APIs

### 3. **Collectors** (`collectors/`)

**Purpose**: Capturing input events from different devices with thread-safe architecture.

#### Components:
- **`CollectorManager`**: Central manager with dynamic capabilities
- **`KeyboardMouseCollector`**: Collector with multiple tracking modes
- **`PS4ControllerCollector`**: Thread-based architecture with SDL2 event loop

#### PS4ControllerCollector Features:
- **Thread-based architecture**: SDL2 event loop in dedicated thread
- **Automatic reconnection**: Robust handling of disconnections
- **Thread-safe event processing**: Granular locks and error handling
- **Change detection**: Previous state tracking for triggers/sticks
- **Core event integration**: Automatic dispatch to event system

```python
# PS4 Controller capabilities
{
    "supports_analog_sticks": True,
    "supports_triggers": True,
    "supports_haptic_feedback": False,
    "button_count": 14,
    "analog_stick_count": 2,
    "trigger_count": 2,
    "connection_type": "SDL2_GameController",
    "auto_reconnect": True,
    "thread_safe_events": True
}
```

#### Mouse Tracking Modes:
```python
TRACKING_MODES = {
    "delta": "Raw movement deltas",
    "angle": "Direction and angle (8-directional)",
    "axis": "Cardinal directions (N/S/E/W)",
    "joystick": "Direction and speed (analog-like)"
}
```

### 4. **Processing** (`processing/`)

**Purpose**: Event processing, formatting, and transformation with extended support.

#### Components:
- **`EventProcessor`**: Processor with extended PS4 support

#### Features:
- **Collector-specific formatting**: Different handling for keyboard/mouse vs PS4
- **Special event detection**: F9 for toggle recording, system events
- **Multi-mode formatting**: Support for all mouse tracking modes
- **Axis processing**: Specialized handling for PS4 joysticks and triggers
- **Thread-safe**: Safe processing with Qt signals

### 5. **Services** (`services/`)

**Purpose**: Enhanced singleton service layer for business logic.

#### Components:
- **`InteractionService`**: Service for expanded application control
- **`DataAccessService`**: Service for real-time data access with categorization

#### Features:
- **Enhanced thread-safety**: Granular locks for different operations
- **Event categorization**: Separation by type (key, mouse_movement, mouse_button, controller)
- **Callback system**: Reactive patterns for external consumers
- **Memory management**: Configurable history limits
- **Metadata state**: Tracking of active collector information

### 6. **Visualizers** (`visualizers/`)

**Purpose**: Real-time visualization components with advanced interfaces.

#### Components:
- **`BaseVisualizer`**: Base class with capabilities support
- **`KeyboardVisualizer`**: Enhanced virtual keyboard
- **`MouseVisualizer`**: Enhanced joystick visualization
- **`MouseButtonsSelector`**: Selector with edit mode
- **`PS4ControllerVisualizer`**: Split panel interface with real-time logging

#### PS4ControllerVisualizer Features:
- **Split panel interface**: Controller visual + real-time state panel
- **Thread-safe updates**: Qt signals for thread-based updates
- **Real-time logging**: Log panel with colors and timestamps
- **Advanced edit mode**: Snapshot/commit system for positions
- **Multiple modes**: Image overlay + direct drawing
- **Live state**: Display of trigger, stick and button values

```python
# Split panel architecture
┌─────────────────────────────────────────────────┐
│                                                 │
│  Controller Visualization                       │
│  (Image overlay + interactive elements)         │
│                                                 │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ State Panel                                     │
│ ┌─────────────────┐ ┌─────────────────────────┐ │
│ │ Active Buttons  │ │ Analog Values           │ │
│ │                 │ │ Left Stick: (0.2, -0.8)│ │
│ └─────────────────┘ │ Right Stick: (0.0, 0.0)│ │
│                     │ L2 Trigger: 0.0         │ │
│                     │ R2 Trigger: 0.0         │ │
│                     └─────────────────────────┘ │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ Real-time Event Log                             │
│ [14:23:45] Button X pressed                     │
│ [14:23:45] Left stick moved to (0.2, -0.8)     │
│ [14:23:46] Button X released                    │
└─────────────────────────────────────────────────┘
```

### 7. **Logging** (`logging/`)

**Purpose**: Multi-format logging system.

#### Components:
- **`LoggingManager`**: Central logging coordinator
- **`JSONLogger`**: Logger for structured JSON format
- **`CSVLogger`**: Logger for tabular CSV format

#### Features:
- **Dynamic CSV headers**: Automatic generation based on tracked keys
- **Collector-specific formatting**: Different fields for keyboard/mouse vs PS4
- **Thread-safe signals**: Communication via Qt signals
- **Automatic management**: Auto file opening/closing

### 8. **UI** (`ui/`)

**Purpose**: User interface management and visualizer coordination with professional theme.

#### Components:
- **`UIManager`**: Main manager with professional dark theme
- **`VisualizerManager`**: Coordinator with capabilities awareness
- **`KeyboardEventFilter`**: Filter for edit mode

#### Features:
- **Professional dark theme**: Consistent colors and styles
- **Capabilities-aware**: Adaptive UI based on active collector
- **PS4 integration**: Specific controls for PS4 visualizer
- **Edit mode coordination**: Centralized edit mode management

### 9. **App Coordinator** (`app/`)

**Purpose**: Central mediator with core event system integration.

#### Components:
- **`AppCoordinator`**: Main coordinator with core events

#### Features:
- **Core event integration**: Automatic dispatch to event system
- **Thread-safe coordination**: Qt signals for UI operations
- **Centralized state**: Consistent management of recording, edit mode, tracked keys
- **Error handling**: Robust error handling in coordination

### 10. **Adapters** (`adapters/`)

**Purpose**: Thread-safe adapters between frameworks and core services.

#### Components:
- **`QtInteractionAdapter`**: Adapter for thread-safe UI operations

#### Features:
- **Thread-safe execution**: Timeouts and error handling for cross-thread operations
- **Framework isolation**: Clear separation between Qt and core services
- **Comprehensive API**: Complete support for all application operations

### 11. **CLI** (`cli/`)

**Purpose**: Command-line interface with advanced monitoring capabilities.

#### Components:
- **`CLIApp`**: Main CLI application with Typer
- **`CLIShell`**: Interactive REPL-style shell
- **`CLIConfig`**: Configuration and shared state management
- **`HeadlessInputCollector`**: Application stack for headless mode
- **Commands**: Specialized command modules
- **`PS4ControllerMonitor`**: Dedicated monitor for PS4 controllers

#### CLI Features:

##### **Monitor Commands**:
- **PS4ControllerMonitor**: Dedicated monitor for PS4 controllers
- **Event-driven architecture**: Use of core event system
- **Rich console interface**: Real-time tables and panels
- **Cross-platform key detection**: ESC/Q to exit on Windows/Unix
- **Smart collector detection**: Specific monitoring based on active collector

```bash
# PS4 monitoring with real-time display
$ input-collector monitor controller
┌─────────────────────────────────────────────────┐
│                PS4 Controller                   │
├─────────────────────────────────────────────────┤
│ Buttons: X, Circle                              │
│ Left Stick: (0.2, -0.8) → SE                   │
│ Right Stick: (0.0, 0.0) → Center               │
│ L2 Trigger: 128/255 (50%)                      │
│ R2 Trigger: 0/255 (0%)                         │
└─────────────────────────────────────────────────┘

Recent Events:
[14:23:45] Button X pressed
[14:23:45] Left stick moved SE
[14:23:46] L2 trigger: 50%
[14:23:46] Button X released

Press ESC or Q to exit...
```

##### **Command Structure**:
```bash
# Data access commands
input-collector data active-keys
input-collector data mouse-position
input-collector data controller-connected

# Interaction commands
input-collector interaction recording start
input-collector interaction collectors switch ps4_controller
input-collector interaction mouse set-mode joystick

# Advanced monitoring
input-collector monitor events --collector ps4_controller
input-collector monitor controller  # Auto-detects PS4
```

### 12. **API Integration** (root files)

**Purpose**: Web API exposure for remote access with core event integration.

#### Components:
- **`InputCollectorAPI`**: Static API for application control
- **`InputDataAPI`**: Static API for data access
- **`InputCollectorApiIntegration`**: Web integration for data with core events
- **`InteractionApiIntegration`**: Web integration for control with core events

#### Features:
- **Core event integration**: Automatic WebSocket broadcasts via event system
- **PS4 state tracking**: Specialized state for PS4 controllers
- **Enhanced fallbacks**: Improved operation without web server
- **Thread-safe operations**: All API operations are thread-safe

## Implemented Architectural Patterns

### 1. **Event-Driven Architecture**
- **Core Event System** as communication backbone
- **Pub/Sub pattern** for decoupling
- **Framework-independent** for flexibility

### 2. **Mediator Pattern**
- **`AppCoordinator`** acts as central mediator
- **Core event integration** for external communication
- **Thread-safe coordination** via Qt signals

### 3. **Singleton Pattern**
- **Thread-safe implementation** with double-checked locking
- **Granular locking** for different operations
- **Error isolation** for robustness

### 4. **Observer Pattern**
- **Core event system** as main implementation
- **Qt signals/slots** for UI thread-safety
- **Callback systems** in services

### 5. **Strategy Pattern**
- **Dynamic collector capabilities**
- **Adaptive UI** based on active collector
- **Interchangeable multiple tracking modes**

### 6. **Adapter Pattern**
- **Enhanced framework isolation**
- **Thread-safe adaptations** with timeouts
- **Cross-platform compatibility**

## Key System Features

### 1. **Complete Event-Driven Architecture**
- **Framework-independent core event system**
- **Thread-safe communication** between all components
- **Automatic event broadcasting** for APIs and CLI
- **Late subscriber synchronization** for robustness

### 2. **Comprehensive Thread Safety**
- **Multiple granular locks** in services and collectors
- **Qt signal/slot threading** for UI updates
- **SDL2 event loop threading** for PS4 controller
- **Error isolation** in callbacks and event handlers

### 3. **Advanced Multi-Interface**
- **GUI**: PyQt5 application with split panels and real-time updates
- **CLI**: Interactive shell with collector-specific monitoring
- **Web API**: Remote control with WebSocket real-time events

### 4. **Robust PS4 Controller Support**
- **SDL2 integration** with thread-safe event processing
- **Automatic reconnection** for wireless devices
- **Advanced visualization** with image overlays
- **Real-time monitoring** in CLI with Rich console

### 5. **Enhanced User Experience**
- **Professional dark theme** consistent
- **Split panel interfaces** for detailed information
- **Real-time state displays** with live value updates
- **Cross-platform CLI** with intelligent key detection

### 6. **Advanced Configurability**
- **Dynamic capabilities** adaptation based on device
- **Multiple mouse tracking modes** with adjustable parameters
- **Edit mode** for visual customization
- **Flexible key/button tracking** configuration

### 7. **Robust Logging and Monitoring**
- **Multi-format simultaneous logging** (CSV + JSON)
- **Dynamic CSV headers** based on configuration
- **Real-time event monitoring** in CLI and GUI
- **WebSocket event streaming** for external integration

### 8. **Extensibility and Maintainability**
- **Clear module boundaries** with well-defined interfaces
- **Event-driven communication** for loose coupling
- **Framework-independent core** for portability
- **Comprehensive error handling** and recovery

## Main Data Flow

```
1. Input Device → Collector (thread-safe) → InputData
2. InputData → Core Event System → Multiple Subscribers
3. InputData → EventProcessor → ProcessingResult  
4. ProcessingResult → AppCoordinator → UI + Logging
5. Core Events → {API WebSocket, CLI Monitor, External Systems}
6. Thread-safe Updates → {GUI Panels, CLI Display, Web Clients}
```

## Main Use Cases

### 1. **Game Development**
- **PS4 controller testing** with real-time visualization
- **Input lag analysis** with precise timestamps
- **Analog input mapping** for stick and trigger calibration
- **Multi-input coordination** testing

### 2. **UX/UI Research**
- **Mouse movement pattern analysis** with multiple tracking modes
- **Keyboard usage heatmaps** with real-time visualization
- **Accessibility testing** with usage pattern monitoring
- **Cross-device interaction studies**

### 3. **Automation and Testing**
- **Macro recording** with multi-device support
- **Automated UI testing** with event playback
- **Input validation** for applications
- **Performance benchmarking** of input handling

### 4. **Real-Time System Monitoring**
- **Live input monitoring** via CLI or Web API
- **Device connectivity tracking** with automatic reconnection
- **Usage analytics** with structured logging
- **Remote monitoring** via WebSocket APIs

### 5. **Development and Debugging**
- **Real-time event inspection**
- **Input device debugging** with detailed state
- **API integration testing** with comprehensive endpoints
- **Cross-platform compatibility verification**

## Technologies and Dependencies

### Core
- **Python 3.8+**: Main language with modern typing
- **PyQt5**: GUI framework with thread-safe signals
- **dataclasses**: Optimized data structures
- **threading**: Concurrency and synchronization

### Advanced CLI
- **Typer**: Modern CLI framework with auto-completion
- **Rich**: Advanced output with tables, panels and colors
- **Cross-platform**: Complete Windows/Unix/macOS support

### Enhanced Input Capture
- **pynput**: Cross-platform keyboard/mouse capture
- **pysdl2** (optional): SDL2 binding for PS4 controller
- **Platform-specific APIs**: Integration with native OS APIs

### Web API and Communication
- **API Explorer**: Web framework for documented APIs
- **WebSocket**: Bidirectional real-time communication
- **HTTP REST**: Stateless APIs for operations

### Advanced Visualization
- **Qt Graphics**: Optimized rendering for visualizers
- **Image processing**: Overlay support for controller visualization
- **Real-time updates**: 60 FPS capable rendering

## Deployment Architecture

```
Input Collector Application
├── Standalone GUI Mode
│   ├── Full feature set
│   ├── Real-time visualization
│   └── Local file logging
├── CLI Headless Mode
│   ├── Minimal resource usage
│   ├── Scriptable operations
│   └── Remote monitoring
├── Hybrid GUI + CLI Mode
│   ├── Concurrent operation
│   ├── Shared state management
│   └── Coordinated cleanup
└── Web API Integration
    ├── Remote control capability
    ├── Real-time event streaming
    └── Cross-platform accessibility
```