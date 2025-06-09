# Input Collector - Architecture and Technical Documentation

## Executive Summary

Input Collector is a comprehensive application designed to capture, process, visualize, and log real-time input events from multiple devices (keyboard, mouse, PS4 controllers). The application implements a modular event-driven architecture that supports multiple user interfaces (GUI, CLI, Web API) and provides extensible capabilities for different collector types and visualization modes.

## General Architecture

### Main Architectural Pattern

The application follows a **hexagonal architecture (Ports and Adapters)** combined with **Mediator** and **Observer** patterns, organizing code into well-defined layers:

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

**Purpose**: Centralized, framework-independent event system for decoupled communication.

#### Components:
- **`EventDispatcher`**: Singleton managing subscriptions and event dispatching
- **`EventType`**: Enumeration of system event types
- **Utility Functions**: Simplified API for common usage

#### Features:
- Thread-safe Singleton pattern
- Set-based subscriber management
- Last event storage for late synchronization
- Callback error isolation
- Framework-independent design

```python
# Usage example
from core import dispatch, subscribe, EventType

def on_input_event(data):
    print(f"Received input: {data}")

subscribe(EventType.INPUT, on_input_event)
dispatch(EventType.INPUT, {"key": "A", "timestamp": time.time()})
```

### 2. **Interfaces** (`interfaces/`)

**Purpose**: Definition of contracts and fundamental data structures.

#### Components:
- **`InputData`**: Main dataclass for input events
- **`AbstractInputCollector`**: Interface for input collectors
- **`AbstractVisualizer`**: Interface for visualizers
- **`AbstractVisualizerProvider/Controller`**: Protocols for UI management

#### Features:
- Comprehensive dataclass with 25+ fields for different input types
- Abstract interfaces ensuring consistent contracts
- Python protocols for structural typing
- `to_dict()` method for serialization

### 3. **Collectors** (`collectors/`)

**Purpose**: Capturing input events from different devices.

#### Components:
- **`CollectorManager`**: Central manager for all collectors
- **`KeyboardMouseCollector`**: Collector for keyboard and mouse
- **`PS4ControllerCollector`**: Collector for PS4 controllers (optional with SDL2)

#### Features:
- Strategy pattern for different collector types
- Multiple mouse tracking modes (delta, angle, axes, joystick)
- Automatic device detection
- Real-time state management
- Asynchronous event callbacks

```python
# Mouse tracking modes
TRACKING_MODES = {
    "delta": "Raw movement deltas",
    "angle": "Direction and angle", 
    "axis": "Cardinal directions (N/S/E/W)",
    "joystick": "Direction and speed"
}
```

### 4. **Processing** (`processing/`)

**Purpose**: Event processing, formatting, and transformation.

#### Components:
- **`EventProcessor`**: Central event processor

#### Features:
- Special event detection (F9 for toggle recording)
- Collector-specific formatting
- Event filtering for logging
- Display text generation
- Multiple tracking mode handling

### 5. **Services** (`services/`)

**Purpose**: Singleton service layer for business logic.

#### Components:
- **`InteractionService`**: Service for application control
- **`DataAccessService`**: Service for real-time data access

#### Features:
- Thread-safe Singleton pattern
- Component registration for loose coupling
- Event categorization by type
- Callback system for reactive patterns
- History limits for memory management

### 6. **Visualizers** (`visualizers/`)

**Purpose**: Real-time visualization components for different input types.

#### Components:
- **`BaseVisualizer`**: Common base class
- **`KeyboardVisualizer`**: Virtual keyboard with highlighting
- **`MouseVisualizer`**: Joystick-style mouse visualization
- **`MouseButtonsSelector`**: Mouse button selector
- **`PS4ControllerVisualizer`**: PS4 controller visualizer with image overlays

#### Features:
- BaseVisualizer inheritance for consistent behavior
- Edit mode for key/button selection
- Multiple visualization modes (image/drawn)
- Real-time state updates
- Support for different collector capabilities

### 7. **Logging** (`logging/`)

**Purpose**: Multi-format logging system.

#### Components:
- **`LoggingManager`**: Central logging coordinator
- **`JSONLogger`**: Logger for structured JSON format
- **`CSVLogger`**: Logger for tabular CSV format

#### Features:
- Simultaneous logging to multiple formats
- Dynamic CSV header generation
- Collector-specific formatting
- Qt signals for thread-safe communication
- Automatic file management

### 8. **UI** (`ui/`)

**Purpose**: User interface management and visualizer coordination.

#### Components:
- **`UIManager`**: Main UI manager with dark theme
- **`VisualizerManager`**: Visualizer coordinator
- **`KeyboardEventFilter`**: Event filter for edit mode

#### Features:
- Consistent dark theme
- Responsive layout
- Complex state management (recording, edit mode, collector type)
- Implicit protocol implementation to avoid metaclass conflicts
- Qt signals for asynchronous communication

### 9. **App Coordinator** (`app/`)

**Purpose**: Central mediator implementing the Mediator pattern.

#### Components:
- **`AppCoordinator`**: Main application coordinator

#### Features:
- Centralized Mediator pattern
- High-level state management
- Coordination between collectors, UI, logging, and processing
- Thread-safe processing via Qt signals
- Dispatch to core event system for external consumers

### 10. **Adapters** (`adapters/`)

**Purpose**: Thread-safe adapters between frameworks and core services.

#### Components:
- **`QtInteractionAdapter`**: Adapter for thread-safe UI operations

#### Features:
- Adapter pattern for framework isolation
- Thread-safe execution with timeouts
- Comprehensive API for external integration
- Robust error handling
- Generic typing for type safety

### 11. **CLI** (`cli/`)

**Purpose**: Complete command-line interface.

#### Components:
- **`CLIApp`**: Main CLI application with Typer
- **`CLIShell`**: Interactive REPL-style shell
- **`CLIConfig`**: Configuration and shared state management
- **`HeadlessInputCollector`**: Application stack for headless mode
- **Commands**: Specialized command modules

#### Features:
- Dual support (standalone/concurrent with GUI)
- Interactive shell with built-in commands
- Complete headless mode
- Cross-platform real-time monitoring
- Rich framework for enhanced output

### 12. **API Integration** (root files)

**Purpose**: Web API exposure for remote access.

#### Components:
- **`InputCollectorAPI`**: Static API for application control
- **`InputDataAPI`**: Static API for data access
- **`InputCollectorApiIntegration`**: Web integration for data
- **`InteractionApiIntegration`**: Web integration for control

#### Features:
- Static facades over service layer
- API Explorer integration for web
- WebSocket for real-time events
- Fallbacks for operation without web server
- Specialized PS4 state tracking

## Implemented Architectural Patterns

### 1. **Mediator Pattern**
- **`AppCoordinator`** acts as central mediator
- Reduces coupling between main components
- Centralizes complex coordination logic

### 2. **Singleton Pattern**
- **`EventDispatcher`**, **`InteractionService`**, **`DataAccessService`**
- Thread-safe with double-checked locking
- Consistent global state

### 3. **Observer Pattern**
- Core event system
- Service callbacks
- Qt signals for UI

### 4. **Strategy Pattern**
- Interchangeable different collectors
- Multiple mouse tracking modes
- Different visualizers by input type

### 5. **Adapter Pattern**
- **`QtInteractionAdapter`** for framework isolation
- Adaptation between Qt and core services
- Transparent thread-safety

### 6. **Facade Pattern**
- Static APIs as facades over services
- Simplification of complex interfaces
- Hiding singleton implementation

### 7. **Factory Pattern**
- Collector creation
- UI component initialization
- Visualizer management

## Key System Features

### 1. **Event-Driven Architecture**
- Framework-independent core event system
- Decoupled communication between components
- Extensibility for new event types

### 2. **Comprehensive Thread Safety**
- Multiple levels of granular locks
- Thread-safe execution for UI operations
- Callback error isolation

### 3. **Multi-Interface**
- **GUI**: Complete PyQt5 application
- **CLI**: Interactive shell and batch commands
- **Web API**: Remote control via HTTP/WebSocket

### 4. **Extensibility**
- Abstract interfaces for new collectors
- Pluggable visualizer system
- Well-defined modular architecture

### 5. **Advanced Configurability**
- Multiple mouse tracking modes
- Dynamic tracked keys configuration
- Edit mode for customization

### 6. **Robust Logging**
- Simultaneous multiple formats
- Dynamic CSV headers
- Collector-specific formatting

### 7. **Real-Time Visualization**
- Low-latency updates
- Multiple display modes
- PS4 image overlays

### 8. **Sophisticated State Management**
- Centralized state in services
- Automatic synchronization
- Rollback and recovery

## Main Data Flow

```
1. Input Device → Collector → InputData
2. InputData → EventProcessor → ProcessingResult  
3. ProcessingResult → AppCoordinator → Coordination
4. Coordination → {UI Update, Logging, Core Events}
5. Core Events → {API Broadcasts, CLI Monitoring}
```

## Main Use Cases

### 1. **Game Development**
- Player input pattern analysis
- Control testing and responsiveness
- Input performance metrics

### 2. **UX/UI Research**
- User interaction analysis
- Mouse and keyboard usage patterns
- Accessibility metrics

### 3. **Automation and Testing**
- Complex macro recording
- Automated interface testing
- Input handling validation

### 4. **System Monitoring**
- Peripheral usage analysis
- Anomalous pattern detection
- Productivity metrics

## Technologies and Dependencies

### Core
- **Python 3.8+**: Main language
- **PyQt5**: GUI framework
- **dataclasses**: Data structures
- **threading**: Concurrency

### CLI
- **Typer**: Modern CLI framework
- **Rich**: Enhanced output
- **Cross-platform**: Windows/Unix support

### Input Capture
- **pynput**: Keyboard/mouse capture
- **pysdl2** (optional): SDL2 for PS4
- **Platform-specific**: Native APIs

### Web API
- **API Explorer**: Web API framework
- **WebSocket**: Real-time communication
- **HTTP**: REST APIs