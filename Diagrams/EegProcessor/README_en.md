# EEG Processor - Architecture and Technical Documentation

## Overview

EEG Processor is a modular framework for real-time EEG signal processing that supports multiple hardware devices (OpenBCI, g.tec, Muse, ANT Neuro, Neurosity), advanced analysis (ICA, wavelet transforms, MNE-Python), and multiple interfaces (Qt5 GUI, CLI, REST API). It implements a **service-oriented architecture** with **event-driven patterns** for neurosignal processing.

## General Architecture

### Main Architectural Pattern

The application follows a **Service-Oriented Architecture (SOA)** combined with **Event-Driven**, **Singleton** and **MVC** patterns, organizing code into specialized layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL INTERFACES                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │    GUI      │  │     CLI     │  │     REST API        │ │
│  │  (Qt5 MVC)  │  │   (Typer)   │  │  (WebSocket+HTTP)   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                        ADAPTERS                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │QtInteraction│  │ CLI Commands│  │ API Integrations    │ │
│  │   Adapter   │  │             │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     SERVICE LAYER                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │Collector    │  │Data Access  │  │  Advanced Analysis  │ │
│  │  Service    │  │  Service    │  │     Services        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    UI CONTROLLERS                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │Panel-Based  │  │ MNE Panel   │  │   Advanced Panel    │ │
│  │   MVC       │  │ Controller  │  │   Controller        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                         CORE                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │Event System │  │Signal       │  │   Hardware          │ │
│  │             │  │Processing   │  │  Abstraction        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Submodules and Components

### 1. **Core Event System** (`core/`)

**Purpose**: Centralized thread-safe event system for decoupled communication between components.

#### Components:
- **`EventDispatcher`**: Thread-safe singleton with RLock protection
- **`EventType`**: Enumeration of 40+ event types (CONNECTION, PROCESSING, VISUALIZATION, MNE, ICA, etc.)
- **`Event`**: Dataclass with timestamp, source and data payload

#### Features:
- **Thread-safe operations**: RLock-based synchronization
- **Event history tracking**: 1000 events with automatic rotation
- **Late subscriber support**: Automatic delivery of last event
- **Error isolation**: Callback failures don't affect other subscribers
- **Performance optimization**: Set-based storage for O(1) operations

```python
# Event system usage
from core import dispatch, subscribe, EventType

def on_filter_applied(event):
    print(f"Filter applied: {event.data}")

subscribe(EventType.FILTER_APPLY, on_filter_applied)
dispatch(EventType.FILTER_APPLY, {
    "bandpass": {"low": 1, "high": 50},
    "notch": {"freq": 50},
    "channels": [1, 2, 3, 4]
})
```

### 2. **Interfaces** (`interfaces/`)

**Purpose**: ABC contracts for modular and testable architecture.

#### Components:
- **`CollectorInterface`**: Base for EEG collectors
- **`MarkerInterface`**: Marker insertion during recording
- **`ConfigurableCollectorInterface`**: Device configuration
- **`BoardInterface`**: Board configuration management
- **`MNEInterfaces`**: Contracts for MNE-Python processing
- **`RecordingInterface`**: Storage and continuous recording

#### Features:
- **Abstract Base Classes**: Strict contracts with `@abstractmethod`
- **Type hints**: Complete typing with `numpy.ndarray`, `Dict[str, Any]`
- **Interface segregation**: Specific interfaces for different capabilities
- **Testability**: Mocking and dependency injection facilitated

### 3. **Collectors** (`collectors/`)

**Purpose**: Hardware abstraction layer for EEG devices with BrainFlow support.

#### Components:
- **`EEGCollector`**: Main implementation with multiple interfaces
- **`BrainFlowBoardConfiguration`**: Configuration management for 20+ manufacturers
- **`BoardConfiguration`**: Static wrapper for compatibility

#### EEGCollector - Features:
- **Multi-preset support**: DEFAULT, AUXILIARY, ANCILLARY data streams
- **Real-time marker insertion**: Microsecond synchronization with EEG data
- **Multi-board support**: OpenBCI, g.tec Unicorn, Muse, ANT Neuro, Neurosity, BrainBit, etc.
- **Streaming board support**: Master board configuration with preset validation
- **Automatic channel detection**: EEG, EMG, ECG, accelerometer, gyroscope
- **Thread-safe operations**: Buffer management and data retrieval

```python
# Board configuration capabilities
SUPPORTED_BOARDS = {
    "OpenBCI": [BoardIds.CYTON_BOARD, BoardIds.GANGLION_BOARD],
    "g.tec": [BoardIds.UNICORN_BOARD],
    "Muse": [BoardIds.MUSE_2_BOARD, BoardIds.MUSE_S_BOARD],
    "ANT Neuro": [BoardIds.ANT_NEURO_EE_410_BOARD],
    "Neurosity": [BoardIds.NOTION_1_BOARD, BoardIds.NOTION_2_BOARD],
    "BrainBit": [BoardIds.BRAINBIT_BOARD, BoardIds.BRAINBIT_BLED_BOARD]
}
```

### 4. **Processors** (`processors/`)

**Purpose**: Signal processing engine with advanced algorithms.

#### Components:
- **`SignalProcessor`**: Main engine with multiple algorithms

#### Features:
- **Multiple filter types**: Butterworth, Chebyshev Type 1, Bessel (zero-phase)
- **Intelligent stability monitoring**: Automatic adjustment for synthetic data
- **Wavelet processing**: 15+ types (Daubechies, Biorthogonal, Coiflets, Symlets)
- **Independent Component Analysis**: FastICA with 1-16 component configuration
- **Signal quality assessment**: 5-level system with railed percentage detection
- **EEG metrics**: Band powers (Delta, Theta, Alpha, Beta, Gamma)
- **ML-based cognitive metrics**: Mindfulness, restfulness, concentration scores

```python
# Advanced filtering with stability monitoring
processor = SignalProcessor(sampling_rate=250)
filtered_data = processor.bandpass_filter(
    data=eeg_data,
    start_freq=1.0,
    stop_freq=50.0,
    order=4,
    filter_type=FilterTypes.BUTTERWORTH,
    ripple=0.1  # Auto-adjusted for Chebyshev stability
)
```

### 5. **Services** (`services/`)

**Purpose**: Singleton service layer for business logic and coordination.

#### Main Components:
- **`CollectorService`**: Singleton EEG collection management
- **`DataAccessService`**: Centralized access with buffer management
- **`ProcessorService`**: Filter and processing coordination
- **`RecordingService`**: Continuous multi-format recording
- **`VisualizationService`**: Visual component management
- **`InteractionService`**: API-internal bridge with validation
- **`AdvancedProcessingService`**: ICA, wavelet, downsampling
- **`MNEService`**: Facade for MNE-Python integration

#### Specialized Services:

##### **ICA Services** (`services/ica/`):
- **`ICAProcessService`**: Multiprocess ICA with Qt signal integration
- **`ICARealtimeService`**: Real-time monitoring with sliding window
- **`ExportService`**: Batch export with progress tracking

##### **MNE Services** (`services/mne/`):
- **`MNEConverterService`**: Asynchronous BrainFlow→MNE conversion
- **`MNEVisualizerService`**: Advanced visualization (PSD, topomaps, spectrograms)
- **`MNERealtimeService`**: Real-time processing with configurable sessions
- **`MNEResultStorage`**: Thread-safe storage with lifecycle management
- **`MNEProcessManager`**: Multiprocessing coordination for CPU-intensive operations

#### Features:
- **Thread-safe operations**: Granular locking strategy
- **Singleton pattern**: Double-checked locking with lazy initialization
- **Callback systems**: Reactive patterns for external consumers
- **Memory management**: Buffer limits and automatic cleanup
- **Background processing**: Thread pools for non-blocking operations

### 6. **UI** (`ui/`)

**Purpose**: Panel-based MVC architecture with specialized controllers.

#### Base Structure:
- **`BasePanel`**: Foundation class with standardized messaging
- **Panel Classes**: ConnectionPanel, ProcessingPanel, RecordingPanel, etc.
- **Specialized Controllers**: MNEPanelController, AdvancedPanelController

#### UI Panels:

##### **ConnectionPanel**: 
- **Board selection**: Intelligent filtering and categorization
- **Dynamic parameter validation**: Visual feedback for required/optional fields
- **Streaming board configuration**: Preset validation with socket error prevention
- **Real-time board information**: Channel mapping, sampling rate, hardware details

##### **ProcessingPanel**:
- **Real-time filter application**: Dynamic updates during active processing
- **Filtering**: Bandpass (1-200 Hz), Notch (50/60 Hz), Detrend
- **EEG metrics calculation**: Band powers, statistical analysis
- **Brain map visualization**: Performance optimization with streaming data

##### **MNE Panel** (`ui/mne/`):
- **SOLID principle implementation**: Controller with widget composition
- **Multi-mode conversion**: Flexible (all channels), Performance (selected), Real-time
- **Advanced visualization**: PSD, topomaps, spectrograms, raw data
- **Real-time processing sessions**: Parameter updates without restart
- **Filter integration**: Seamless coordination with processing panel

##### **Advanced Panel** (`ui/advanced/`):
- **ICA Widget**: Real-time monitoring with export capabilities
- **Wavelet Widget**: Transform analysis with denoising support
- **Advanced Filter Widget**: Multi-type filtering with stability analysis
- **Downsampling Widget**: Performance optimization with aggregation methods

#### Specialized Widgets:

##### **MNE Widgets** (`ui/mne/widgets/`):
- **`MNEConversionWidget`**: Multi-mode interface with performance warnings
- **`MNEVisualizationWidget`**: Visualization controls with real-time updates
- **`MNEStatusWidget`**: Real-time monitoring with performance metrics
- **`ChannelSelectionDialog`**: Grid-based selection with optimization indicators

##### **Advanced Widgets** (`ui/advanced/widgets/`):
- **`ICAWidget`**: Component count configuration (1-16) with channel selection
- **`WaveletWidget`**: Wavelet type selection with decomposition levels
- **`AdvancedFilterWidget`**: Filter type, order, window function selection
- **`DownsamplingWidget`**: Factor configuration with aggregation methods

#### UI Features:
- **Dark theme integration**: Consistent styling across components
- **Real-time updates**: Dynamic parameter modification without session restart
- **Performance monitoring**: CPU usage warnings and optimization suggestions
- **Event-driven architecture**: Qt signals for loose coupling
- **Thread-safe operations**: Proper UI thread marshalling

### 7. **Visualizers** (`visualizers/`)

**Purpose**: Real-time scientific visualization components.

#### Components:
- **`MultiSignalVisualizer`**: Multi-page biosignal visualization
- **`BrainMapVisualizer`**: Topographic brain mapping

#### MultiSignalVisualizer - Features:
- **Intelligent channel detection**: EEG, EMG, ECG, EOG, EDA, PPG, accelerometer, gyroscope
- **Lazy loading architecture**: Caching for performance optimization
- **Multi-tab interface**: Separation by signal modality
- **Real-time data integration**: DataAccessService coordination
- **Performance optimization**: Selective tab updates, memory-efficient operations

#### BrainMapVisualizer - Features:
- **International 10-20/10-10 positioning**: Standard electrode positions
- **Real-time signal quality**: Color-coded indicators (5-level system)
- **Anatomical brain regions**: Frontal, central, parietal, occipital overlays
- **G.tec Unicorn compatibility**: Automatic channel mapping
- **Interactive elements**: Electrode labels with quality legend

```python
# Channel type detection capabilities
SUPPORTED_CHANNEL_TYPES = {
    "EEG": "Electroencephalography signals",
    "EMG": "Electromyography signals", 
    "ECG": "Electrocardiography signals",
    "EOG": "Electrooculography signals",
    "EDA": "Electrodermal activity",
    "PPG": "Photoplethysmography",
    "Accelerometer": "3-axis acceleration",
    "Gyroscope": "3-axis angular velocity"
}
```

### 8. **Utils** (`utils/`)

**Purpose**: Utilities and support systems for application.

#### Components:
- **`ThemeManager`**: Advanced styling and dark theme
- **`HelpSystem`**: Contextual help system with 25+ topics

#### ThemeManager - Features:
- **Dark theme implementation**: Qt widget styling optimization
- **Consistent color scheme**: Semantic colors (success, warning, error, accent)
- **Widget coverage**: Buttons, inputs, tabs, scrollbars, groups
- **Accessibility compliance**: Proper contrast ratios

#### HelpSystem - Features:
- **25+ detailed topics**: Hardware, processing, visualization, recording, analysis
- **Context-sensitive help**: HelpButton integration in UI
- **Tabbed help interface**: Organization by functional areas
- **Educational content**: EEG basics, signal processing theory, advanced analysis

### 9. **CLI** (`cli/`)

**Purpose**: Command-line interface with advanced capabilities.

#### Components:
- **`CLIApp`**: Main Typer application with command registration
- **`CLIShell`**: Interactive shell for user-friendly command execution
- **`CLIConfig`**: Configuration and state management for CLI
- **`HeadlessEEGProcessor`**: Headless stack for programmatic use

#### Command Modules:
- **`DataCommands`**: Access and display EEG data/metadata
- **`MonitorCommands`**: Real-time monitoring streams, channels, signal quality
- **`InteractionCommands`**: Control processor (connect, stream, record, filters)

#### Features:
- **Typer framework**: Modern CLI with auto-completion
- **Rich console output**: Tables, panels, real-time displays
- **Cross-platform support**: Windows/Linux/macOS compatibility
- **Headless mode**: Minimal resource usage for scripting
- **Interactive shell**: REPL-style interface with command history

```bash
# CLI usage examples
eeg-processor data current-data --max-samples 1000
eeg-processor control connect-board --board-id 1 --preset 0
eeg-processor monitor realtime --channels 1,2,3,4
eeg-processor control apply-filters --bandpass-low 1 --bandpass-high 50
```

### 10. **Adapters** (`adapters/`)

**Purpose**: Thread-safe bridges between frameworks and core services.

#### Components:
- **`QtInteractionAdapter`**: Thread-safe Qt-service bridge

#### Features:
- **Thread-safe execution**: ThreadPoolExecutor with timeout management (5s default)
- **Framework isolation**: Clear separation between Qt and core services
- **API coverage**: All panel operations and settings retrieval
- **Error handling**: Timeout detection and graceful degradation
- **Cross-thread communication**: QTimer-based main thread execution

### 11. **API Integration** (root files)

**Purpose**: REST API with WebSocket for remote access and control.

#### Components:
- **`EEGDataAPI`**: Static API for data access
- **`EEGProcessorInteractionAPI`**: Static API for system control
- **`EEGProcessorApiIntegration`**: WebSocket integration for data streaming
- **`EEGProcessorInteractionApiIntegration`**: API integration for control operations

#### Features:
- **Dual-mode data streaming**: Direct mode (low latency ~15ms), Multiprocessing mode
- **WebSocket real-time**: Structured payload broadcasting
- **Control API**: Board management, processing, recording, analysis
- **Thread-safe operations**: All API calls thread-safe with timeout management
- **External system integration**: Automatic documentation via API Explorer

```python
# API integration capabilities
API_ENDPOINTS = {
    "Data Access": ["get_current_data", "get_eeg_data", "get_metadata"],
    "Board Control": ["connect_board", "start_stream", "insert_marker"],
    "Processing": ["apply_filters", "calculate_metrics", "perform_ica"],
    "Recording": ["start_recording", "stop_recording", "save_data"],
    "Advanced": ["convert_to_mne", "compute_wavelet", "apply_downsampling"]
}
```

## Implemented Architectural Patterns

### 1. **Service-Oriented Architecture (SOA)**
- **Singleton services** with thread-safe initialization
- **Service coordination** via InteractionService
- **Clear service boundaries** with well-defined interfaces
- **Dependency injection** for testing and modularity

### 2. **Event-Driven Architecture**
- **Core Event System** as communication backbone
- **Pub/Sub pattern** for loose coupling
- **Cross-component coordination** without direct dependencies
- **API-GUI synchronization** via events

### 3. **Model-View-Controller (MVC)**
- **Panel-based MVC**: Controllers coordinating multiple widgets
- **Specialized controllers**: MNEPanelController, AdvancedPanelController
- **Signal/slot communication**: Qt architecture for responsive UI
- **State management**: Consistent across operational contexts

### 4. **Multiprocessing & Multithreading**
- **CPU-intensive operations**: ICA, MNE processing in separate processes
- **Background threads**: Data collection, real-time processing
- **Thread-safe communication**: Qt signals, multiprocessing queues
- **Resource lifecycle management**: Proper cleanup and memory optimization

### 5. **Factory & Strategy Patterns**
- **Board configuration factory**: Dynamic parameter creation
- **Processing strategy**: Multiple filter types and algorithms
- **Visualization strategy**: Adaptive UI based on device capabilities
- **Channel detection strategy**: Intelligent type recognition

### 6. **Adapter Pattern**
- **Framework integration**: Qt-service bridges
- **Hardware abstraction**: BrainFlow device integration
- **API adaptation**: External system integration
- **Cross-platform compatibility**: Unified interfaces

## Key System Features

### 1. **Extensive Hardware Support**
- **20+ manufacturers**: OpenBCI, g.tec, Muse, ANT Neuro, Neurosity, BrainBit, etc.
- **Multi-preset data collection**: DEFAULT, AUXILIARY, ANCILLARY streams
- **Automatic device detection**: Channel mapping and configuration
- **Real-time marker insertion**: Microsecond timestamp synchronization

### 2. **Advanced Signal Processing**
- **Multiple filter implementations**: Butterworth, Chebyshev, Bessel
- **Wavelet analysis**: 15+ wavelet families with denoising
- **Independent Component Analysis**: FastICA with 1-16 components
- **Real-time processing**: Dynamic parameter updates without restart
- **Signal quality assessment**: 5-level scoring with performance indicators

### 3. **MNE-Python Integration**
- **Asynchronous data conversion**: BrainFlow→MNE format
- **Advanced visualization**: PSD, spectrograms, topomaps
- **Real-time processing sessions**: Configurable update intervals
- **Multiprocessing support**: CPU-intensive operations
- **Output**: High-resolution plots (200 DPI)

### 4. **Real-time Capabilities**
- **High-frequency updates**: 50-100ms rendering pipelines
- **Performance monitoring**: CPU usage optimization
- **Adaptive timeout management**: Based on processing complexity
- **Memory-efficient operations**: Automatic buffer management
- **Thread-safe operations**: Concurrent processing support

### 5. **Multi-Interface Architecture**
- **Qt5 GUI**: Panel-based interface with dark theme
- **CLI**: Interactive shell with Rich console output
- **REST API**: WebSocket streaming with HTTP control
- **Cross-platform**: Windows, Linux, macOS support

### 6. **Educational & Research Features**
- **Help system**: 25+ topics with theoretical background
- **Context-sensitive guidance**: Parameter recommendations
- **Progressive complexity**: Basic setup → advanced research
- **Documentation integration**: Inline help with best practices

## Main Data Flow

```
1. Hardware Device → EEGCollector (BrainFlow) → Raw EEG Data
2. Raw Data → SignalProcessor → Filtered/Processed Data
3. Processed Data → DataAccessService → Centralized Buffer
4. Buffer → {UI Panels, CLI Monitor, API Streams, Recording}
5. Advanced Analysis → {ICA, Wavelet, MNE} → Results Storage
6. Real-time Updates → {Qt Signals, WebSocket, CLI Display}
7. Event System → Cross-component Coordination
```

## Main Use Cases

### 1. **Neuroscientific Research**
- **EEG data collection** with multiple devices
- **Advanced signal analysis** (ICA, wavelet, band powers)
- **Real-time processing** with MNE-Python integration
- **Visualization** with export capabilities

### 2. **Brain-Computer Interfaces**
- **Real-time feature extraction** with machine learning metrics
- **Low-latency processing** for feedback systems
- **Multi-channel analysis** with performance optimization
- **External system integration** via REST API

### 3. **Clinical Applications**
- **Signal quality monitoring** with real-time indicators
- **Artifact detection** through ICA and wavelet analysis
- **Multi-format recording** with marker insertion
- **Logging** for clinical documentation

### 4. **Educational Purposes**
- **Interactive EEG exploration** with help system
- **Signal processing learning** with real-time parameter adjustment
- **Hands-on experience** with multiple hardware devices
- **Theoretical background** integrated with practical application

### 5. **Development & Testing**
- **EEG application development** with API access
- **Hardware compatibility testing** across manufacturers
- **Signal processing algorithm validation** with known datasets
- **Performance benchmarking** with multi-threading analysis

## Technologies and Dependencies

### Core Framework
- **Python 3.8+**: Modern typing and asyncio support
- **PyQt5**: Professional GUI framework with native look-and-feel
- **BrainFlow**: Cross-platform library for EEG device integration
- **NumPy**: Optimized array operations for signal processing

### Signal Processing
- **SciPy**: Advanced mathematical functions for filtering
- **MNE-Python** (optional): Neurophysiological analysis capabilities
- **Matplotlib**: High-quality plotting with Qt backend integration
- **scikit-learn**: Machine learning components for cognitive metrics

### CLI & API
- **Typer**: Modern CLI framework with auto-completion
- **Rich**: Advanced console output with tables and real-time displays
- **API Explorer**: Web framework for documented APIs
- **WebSocket**: Real-time bidirectional communication

### Concurrency & Performance
- **Threading**: Background data collection and processing
- **Multiprocessing**: CPU-intensive analysis operations
- **Qt Signals/Slots**: Thread-safe UI communication
- **Asyncio**: Asynchronous operation coordination

### Development & Testing
- **Abstract Base Classes**: Interface contracts for modularity
- **Type hints**: Complete typing for development assistance
- **Dependency injection**: Service coordination and testing support
- **Cross-platform compatibility**: Windows, Linux, macOS support

## Deployment Architecture

```
EEG Processor Application
├── GUI Application Mode
│   ├── Full-featured interface
│   ├── Real-time visualization
│   ├── Advanced analysis panels
│   └── Interactive help system
├── CLI Mode
│   ├── Interactive shell
│   ├── Scriptable operations
│   ├── Real-time monitoring
│   └── Headless processing
├── API Server Mode
│   ├── REST endpoints
│   ├── WebSocket streaming
│   ├── External integration
│   └── Documentation interface
└── Hybrid Modes
    ├── GUI + API concurrent
    ├── CLI + API coordination
    ├── Shared service layer
    └── Coordinated cleanup
```