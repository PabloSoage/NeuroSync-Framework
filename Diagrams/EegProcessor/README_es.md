# EEG Processor - Arquitectura y Documentación Técnica

## Resumen

EEG Processor es un framework modular para procesamiento de señales EEG en tiempo real que soporta múltiples dispositivos de hardware (OpenBCI, g.tec, Muse, ANT Neuro, Neurosity), análisis avanzado (ICA, wavelet transforms, MNE-Python), y múltiples interfaces (GUI Qt5, CLI, REST API). Implementa una **arquitectura orientada a servicios** con **patrones event-driven** para procesamiento neuroseñales.

## Arquitectura General

### Patrón Arquitectónico Principal

La aplicación sigue una **arquitectura orientada a servicios (SOA)** combinada con patrones **Event-Driven**, **Singleton** y **MVC**, organizando el código en capas especializadas:

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFACES EXTERNAS                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │    GUI      │  │     CLI     │  │     REST API        │ │
│  │  (Qt5 MVC)  │  │   (Typer)   │  │  (WebSocket+HTTP)   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      ADAPTADORES                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │QtInteraction│  │ CLI Commands│  │ API Integrations    │ │
│  │   Adapter   │  │             │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE SERVICIOS                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │Collector    │  │Data Access  │  │  Advanced Analysis  │ │
│  │  Service    │  │  Service    │  │     Services        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    CONTROLADORES UI                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │Panel-Based  │  │ MNE Panel   │  │   Advanced Panel    │ │
│  │   MVC       │  │ Controller  │  │   Controller        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      NÚCLEO                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │Event System │  │Signal       │  │   Hardware          │ │
│  │             │  │Processing   │  │  Abstraction        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Submódulos y Componentes

### 1. **Core Event System** (`core/`)

**Propósito**: Sistema de eventos centralizado thread-safe para comunicación desacoplada entre componentes.

#### Componentes:
- **`EventDispatcher`**: Singleton thread-safe con RLock protection
- **`EventType`**: Enumeración de 40+ tipos de eventos (CONNECTION, PROCESSING, VISUALIZATION, MNE, ICA, etc.)
- **`Event`**: Dataclass con timestamp, source y data payload

#### Características:
- **Thread-safe operations**: RLock-based synchronization
- **Event history tracking**: 1000 eventos con rotación automática
- **Late subscriber support**: Entrega automática del último evento
- **Error isolation**: Fallos en callbacks no afectan otros suscriptores
- **Performance optimization**: Set-based storage para O(1) operations

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

**Propósito**: Contratos ABC para arquitectura modular y testeable.

#### Componentes:
- **`CollectorInterface`**: Base para colectores EEG
- **`MarkerInterface`**: Inserción de marcadores durante grabación
- **`ConfigurableCollectorInterface`**: Configuración de dispositivos
- **`BoardInterface`**: Gestión de configuración de boards
- **`MNEInterfaces`**: Contratos para procesamiento MNE-Python
- **`RecordingInterface`**: Almacenamiento y grabación continua

#### Características:
- **Abstract Base Classes**: Contratos estrictos con `@abstractmethod`
- **Type hints**: Tipado completo con `numpy.ndarray`, `Dict[str, Any]`
- **Interface segregation**: Interfaces específicas para diferentes capacidades
- **Testability**: Mocking y dependency injection facilitados

### 3. **Collectors** (`collectors/`)

**Propósito**: Capa de abstracción hardware para dispositivos EEG con soporte BrainFlow.

#### Componentes:
- **`EEGCollector`**: Implementación principal con múltiples interfaces
- **`BrainFlowBoardConfiguration`**: Gestión de configuración de 20+ fabricantes
- **`BoardConfiguration`**: Wrapper estático para compatibilidad

#### EEGCollector - Características:
- **Multi-preset support**: DEFAULT, AUXILIARY, ANCILLARY data streams
- **Real-time marker insertion**: Sincronización microsegundo con datos EEG
- **Multi-board support**: OpenBCI, g.tec Unicorn, Muse, ANT Neuro, Neurosity, BrainBit, etc.
- **Streaming board support**: Master board configuration con validación de preset
- **Automatic channel detection**: EEG, EMG, ECG, accelerometer, gyroscope
- **Thread-safe operations**: Buffer management y data retrieval

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

**Propósito**: Motor de procesamiento de señales con algoritmos avanzados.

#### Componentes:
- **`SignalProcessor`**: Engine principal con múltiples algoritmos

#### Características:
- **Multiple filter types**: Butterworth, Chebyshev Type 1, Bessel (zero-phase)
- **Intelligent stability monitoring**: Ajuste automático para datos sintéticos
- **Wavelet processing**: 15+ tipos (Daubechies, Biorthogonal, Coiflets, Symlets)
- **Independent Component Analysis**: FastICA con configuración 1-16 componentes
- **Signal quality assessment**: Sistema 5-nivel con railed percentage detection
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

**Propósito**: Capa de servicios singleton para lógica de negocio y coordinación.

#### Componentes Principales:
- **`CollectorService`**: Gestión singleton de colección EEG
- **`DataAccessService`**: Acceso centralizado con buffer management
- **`ProcessorService`**: Coordinación de filtros y procesamiento
- **`RecordingService`**: Grabación continua multi-formato
- **`VisualizationService`**: Gestión de componentes visuales
- **`InteractionService`**: Bridge API-interno con validación
- **`AdvancedProcessingService`**: ICA, wavelet, downsampling
- **`MNEService`**: Facade para integración MNE-Python

#### Servicios Especializados:

##### **ICA Services** (`services/ica/`):
- **`ICAProcessService`**: Multiprocess ICA con Qt signal integration
- **`ICARealtimeService`**: Monitoreo tiempo real con sliding window
- **`ExportService`**: Export batch con progress tracking

##### **MNE Services** (`services/mne/`):
- **`MNEConverterService`**: Conversión BrainFlow→MNE asíncrona
- **`MNEVisualizerService`**: Visualización avanzada (PSD, topomaps, spectrograms)
- **`MNERealtimeService`**: Procesamiento tiempo real con sesiones configurable
- **`MNEResultStorage`**: Almacenamiento thread-safe con lifecycle management
- **`MNEProcessManager`**: Coordinación multiprocessing para operaciones CPU-intensivas

#### Características:
- **Thread-safe operations**: Granular locking strategy
- **Singleton pattern**: Double-checked locking con lazy initialization
- **Callback systems**: Reactive patterns para consumers externos
- **Memory management**: Buffer limits y cleanup automático
- **Background processing**: Thread pools para operaciones no-blocking

### 6. **UI** (`ui/`)

**Propósito**: Arquitectura panel-based MVC con controladores especializados.

#### Estructura Base:
- **`BasePanel`**: Foundation class con messaging standardizado
- **Panel Classes**: ConnectionPanel, ProcessingPanel, RecordingPanel, etc.
- **Specialized Controllers**: MNEPanelController, AdvancedPanelController

#### UI Panels:

##### **ConnectionPanel**: 
- **Board selection**: Filtrado inteligente y categorización
- **Dynamic parameter validation**: Visual feedback para campos required/optional
- **Streaming board configuration**: Validación preset con prevención socket errors
- **Real-time board information**: Channel mapping, sampling rate, hardware details

##### **ProcessingPanel**:
- **Real-time filter application**: Updates dinámicos durante procesamiento activo
- **Filtering**: Bandpass (1-200 Hz), Notch (50/60 Hz), Detrend
- **EEG metrics calculation**: Band powers, statistical analysis
- **Brain map visualization**: Performance optimization con streaming datos

##### **MNE Panel** (`ui/mne/`):
- **SOLID principle implementation**: Controller con widget composition
- **Multi-mode conversion**: Flexible (all channels), Performance (selected), Real-time
- **Advanced visualization**: PSD, topomaps, spectrograms, raw data
- **Real-time processing sessions**: Parameter updates sin restart
- **Filter integration**: Coordinación seamless con processing panel

##### **Advanced Panel** (`ui/advanced/`):
- **ICA Widget**: Real-time monitoring con export capabilities
- **Wavelet Widget**: Transform analysis con denoising support
- **Advanced Filter Widget**: Multi-type filtering con stability analysis
- **Downsampling Widget**: Performance optimization con aggregation methods

#### Specialized Widgets:

##### **MNE Widgets** (`ui/mne/widgets/`):
- **`MNEConversionWidget`**: Multi-mode interface con performance warnings
- **`MNEVisualizationWidget`**: Visualization controls con real-time updates
- **`MNEStatusWidget`**: Real-time monitoring con performance metrics
- **`ChannelSelectionDialog`**: Grid-based selection con optimization indicators

##### **Advanced Widgets** (`ui/advanced/widgets/`):
- **`ICAWidget`**: Component count configuration (1-16) con channel selection
- **`WaveletWidget`**: Wavelet type selection con decomposition levels
- **`AdvancedFilterWidget`**: Filter type, order, window function selection
- **`DownsamplingWidget`**: Factor configuration con aggregation methods

#### Características UI:
- **Dark theme integration**: Consistent styling across components
- **Real-time updates**: Dynamic parameter modification sin session restart
- **Performance monitoring**: CPU usage warnings y optimization suggestions
- **Event-driven architecture**: Qt signals para loose coupling
- **Thread-safe operations**: Proper UI thread marshalling

### 7. **Visualizers** (`visualizers/`)

**Propósito**: Componentes visualización científica tiempo real.

#### Componentes:
- **`MultiSignalVisualizer`**: Multi-page biosignal visualization
- **`BrainMapVisualizer`**: Topographic brain mapping

#### MultiSignalVisualizer - Características:
- **Intelligent channel detection**: EEG, EMG, ECG, EOG, EDA, PPG, accelerometer, gyroscope
- **Lazy loading architecture**: Caching para performance optimization
- **Multi-tab interface**: Separation por modalidad signal
- **Real-time data integration**: DataAccessService coordination
- **Performance optimization**: Selective tab updates, memory-efficient operations

#### BrainMapVisualizer - Características:
- **International 10-20/10-10 positioning**: Standard electrode positions
- **Real-time signal quality**: Color-coded indicators (5-level system)
- **Anatomical brain regions**: Frontal, central, parietal, occipital overlays
- **G.tec Unicorn compatibility**: Automatic channel mapping
- **Interactive elements**: Electrode labels con quality legend

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

**Propósito**: Utilities y sistemas soporte para aplicación.

#### Componentes:
- **`ThemeManager`**: Advanced styling y tema oscuro
- **`HelpSystem`**: Sistema help contextual con 25+ topics

#### ThemeManager - Características:
- **Dark theme implementation**: Qt widget styling optimization
- **Consistent color scheme**: Semantic colors (success, warning, error, accent)
- **Widget coverage**: Buttons, inputs, tabs, scrollbars, groups
- **Accessibility compliance**: Proper contrast ratios

#### HelpSystem - Características:
- **25+ detailed topics**: Hardware, processing, visualization, recording, analysis
- **Context-sensitive help**: HelpButton integration en UI
- **Tabbed help interface**: Organization por functional areas
- **Educational content**: EEG basics, signal processing theory, advanced analysis

### 9. **CLI** (`cli/`)

**Propósito**: Command-line interface con capabilities avanzadas.

#### Componentes:
- **`CLIApp`**: Typer application principal con command registration
- **`CLIShell`**: Interactive shell para user-friendly command execution
- **`CLIConfig`**: Configuration y state management para CLI
- **`HeadlessEEGProcessor`**: Headless stack para programmatic use

#### Command Modules:
- **`DataCommands`**: Access y display EEG data/metadata
- **`MonitorCommands`**: Real-time monitoring streams, channels, signal quality
- **`InteractionCommands`**: Control processor (connect, stream, record, filters)

#### Características:
- **Typer framework**: Modern CLI con auto-completion
- **Rich console output**: Tables, panels, real-time displays
- **Cross-platform support**: Windows/Linux/macOS compatibility
- **Headless mode**: Minimal resource usage para scripting
- **Interactive shell**: REPL-style interface con command history

```bash
# CLI usage examples
eeg-processor data current-data --max-samples 1000
eeg-processor control connect-board --board-id 1 --preset 0
eeg-processor monitor realtime --channels 1,2,3,4
eeg-processor control apply-filters --bandpass-low 1 --bandpass-high 50
```

### 10. **Adapters** (`adapters/`)

**Propósito**: Thread-safe bridges entre frameworks y core services.

#### Componentes:
- **`QtInteractionAdapter`**: Thread-safe Qt-service bridge

#### Características:
- **Thread-safe execution**: ThreadPoolExecutor con timeout management (5s default)
- **Framework isolation**: Separation clara entre Qt y services core
- **API coverage**: All panel operations y settings retrieval
- **Error handling**: Timeout detection y graceful degradation
- **Cross-thread communication**: QTimer-based main thread execution

### 11. **API Integration** (archivos raíz)

**Propósito**: REST API con WebSocket para acceso remoto y control.

#### Componentes:
- **`EEGDataAPI`**: Static API para data access
- **`EEGProcessorInteractionAPI`**: Static API para system control
- **`EEGProcessorApiIntegration`**: WebSocket integration para data streaming
- **`EEGProcessorInteractionApiIntegration`**: API integration para control operations

#### Características:
- **Dual-mode data streaming**: Direct mode (low latency ~15ms), Multiprocessing mode
- **WebSocket real-time**: Structured payload broadcasting
- **Control API**: Board management, processing, recording, analysis
- **Thread-safe operations**: All API calls thread-safe con timeout management
- **External system integration**: Documentation automática via API Explorer

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

## Patrones Arquitectónicos Implementados

### 1. **Service-Oriented Architecture (SOA)**
- **Singleton services** con thread-safe initialization
- **Service coordination** via InteractionService
- **Clear service boundaries** con well-defined interfaces
- **Dependency injection** para testing y modularity

### 2. **Event-Driven Architecture**
- **Core Event System** como communication backbone
- **Pub/Sub pattern** para loose coupling
- **Cross-component coordination** sin direct dependencies
- **API-GUI synchronization** via events

### 3. **Model-View-Controller (MVC)**
- **Panel-based MVC**: Controllers coordinando multiple widgets
- **Specialized controllers**: MNEPanelController, AdvancedPanelController
- **Signal/slot communication**: Qt architecture para responsive UI
- **State management**: Consistent across operational contexts

### 4. **Multiprocessing & Multithreading**
- **CPU-intensive operations**: ICA, MNE processing en separate processes
- **Background threads**: Data collection, real-time processing
- **Thread-safe communication**: Qt signals, multiprocessing queues
- **Resource lifecycle management**: Proper cleanup y memory optimization

### 5. **Factory & Strategy Patterns**
- **Board configuration factory**: Dynamic parameter creation
- **Processing strategy**: Multiple filter types y algorithms
- **Visualization strategy**: Adaptive UI based on device capabilities
- **Channel detection strategy**: Intelligent type recognition

### 6. **Adapter Pattern**
- **Framework integration**: Qt-service bridges
- **Hardware abstraction**: BrainFlow device integration
- **API adaptation**: External system integration
- **Cross-platform compatibility**: Unified interfaces

## Características Clave del Sistema

### 1. **Hardware Support Extensivo**
- **20+ fabricantes**: OpenBCI, g.tec, Muse, ANT Neuro, Neurosity, BrainBit, etc.
- **Multi-preset data collection**: DEFAULT, AUXILIARY, ANCILLARY streams
- **Automatic device detection**: Channel mapping y configuration
- **Real-time marker insertion**: Microsecond timestamp synchronization

### 2. **Advanced Signal Processing**
- **Multiple filter implementations**: Butterworth, Chebyshev, Bessel
- **Wavelet analysis**: 15+ wavelet families con denoising
- **Independent Component Analysis**: FastICA con 1-16 components
- **Real-time processing**: Dynamic parameter updates sin restart
- **Signal quality assessment**: 5-level scoring con performance indicators

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
- **Qt5 GUI**: Panel-based interface con dark theme
- **CLI**: Interactive shell con Rich console output
- **REST API**: WebSocket streaming con HTTP control
- **Cross-platform**: Windows, Linux, macOS support

### 6. **Educational & Research Features**
- **Help system**: 25+ topics con theoretical background
- **Context-sensitive guidance**: Parameter recommendations
- **Progressive complexity**: Basic setup → advanced research
- **Documentation integration**: Inline help con best practices

## Flujo de Datos Principal

```
1. Hardware Device → EEGCollector (BrainFlow) → Raw EEG Data
2. Raw Data → SignalProcessor → Filtered/Processed Data
3. Processed Data → DataAccessService → Centralized Buffer
4. Buffer → {UI Panels, CLI Monitor, API Streams, Recording}
5. Advanced Analysis → {ICA, Wavelet, MNE} → Results Storage
6. Real-time Updates → {Qt Signals, WebSocket, CLI Display}
7. Event System → Cross-component Coordination
```

## Casos de Uso Principales

### 1. **Investigación Neurocientífica**
- **EEG data collection** con múltiples dispositivos
- **Advanced signal analysis** (ICA, wavelet, band powers)
- **Real-time processing** con MNE-Python integration
- **Publication-quality visualization** con export capabilities

### 2. **Brain-Computer Interfaces**
- **Real-time feature extraction** con machine learning metrics
- **Low-latency processing** para feedback systems
- **Multi-channel analysis** con performance optimization
- **External system integration** via REST API

### 3. **Clinical Applications**
- **Signal quality monitoring** con real-time indicators
- **Artifact detection** mediante ICA y wavelet analysis
- **Multi-format recording** con marker insertion
- **Logging** para clinical documentation

### 4. **Educational Purposes**
- **Interactive EEG exploration** con help system
- **Signal processing learning** con real-time parameter adjustment
- **Hands-on experience** con multiple hardware devices
- **Theoretical background** integrated con practical application

### 5. **Development & Testing**
- **EEG application development** con API access
- **Hardware compatibility testing** across manufacturers
- **Signal processing algorithm validation** con known datasets
- **Performance benchmarking** con multi-threading analysis

## Tecnologías y Dependencias

### Core Framework
- **Python 3.8+**: Modern typing y asyncio support
- **PyQt5**: Professional GUI framework con native look-and-feel
- **BrainFlow**: Cross-platform library para EEG device integration
- **NumPy**: Optimized array operations para signal processing

### Signal Processing
- **SciPy**: Advanced mathematical functions para filtering
- **MNE-Python** (opcional): Neurophysiological analysis capabilities
- **Matplotlib**: Publication-quality plotting con Qt backend integration
- **scikit-learn**: Machine learning components para cognitive metrics

### CLI & API
- **Typer**: Modern CLI framework con auto-completion
- **Rich**: Advanced console output con tables y real-time displays
- **API Explorer**: Web framework para documented APIs
- **WebSocket**: Real-time bidirectional communication

### Concurrency & Performance
- **Threading**: Background data collection y processing
- **Multiprocessing**: CPU-intensive analysis operations
- **Qt Signals/Slots**: Thread-safe UI communication
- **Asyncio**: Asynchronous operation coordination

### Development & Testing
- **Abstract Base Classes**: Interface contracts para modularity
- **Type hints**: Complete typing para development assistance
- **Dependency injection**: Service coordination y testing support
- **Cross-platform compatibility**: Windows, Linux, macOS support

## Arquitectura de Deployment

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