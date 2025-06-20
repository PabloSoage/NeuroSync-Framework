"""
EEG Processor - Real-time EEG Data Processing Framework.

This package provides a framework for real-time EEG data
collection, processing, analysis, and visualization. It implements a sophisticated
modular architecture supporting multiple hardware devices, advanced signal processing
techniques, real-time analysis, and visualization capabilities.

Core Application:

- EEGProcessorApp: Main Qt-based application with panel architecture
  * Tabbed interface supporting connection, processing, recording, streaming, and advanced analysis
  * Real-time coordination between UI components and backend services
  * Dark theme with consistent styling and accessibility features
  * Event-driven architecture for API-GUI synchronization and cross-component communication
  * Error handling with graceful degradation and user-friendly recovery

Primary Components:

- EEGCollector: Advanced data collection engine with multi-interface support
  * Implements CollectorInterface, MarkerInterface, and ConfigurableCollectorInterface
  * Supports 20+ hardware manufacturers including OpenBCI, g.tec, Muse, ANT Neuro, Neurosity
  * Multi-preset data collection (DEFAULT, AUXILIARY, ANCILLARY) with automatic optimization
  * Real-time marker insertion for event-related experiments and paradigms
  * Streaming board support with master board configuration and preset validation

- SignalProcessor: Sophisticated signal processing engine with advanced capabilities
  * Multiple filter types: Butterworth, Chebyshev Type 1, Bessel with zero-phase variants
  * Intelligent stability monitoring with automatic parameter adjustment for edge cases
  * Wavelet processing: 15+ types with denoising, forward/inverse transforms, coefficient management
  * Independent Component Analysis using FastICA with configurable components (1-16)
  * EEG quality assessment with multi-channel scoring and real-time monitoring
  * Band power calculation for standard frequency bands with ML-based cognitive metrics

- MultiSignalVisualizer: High-performance multi-modality visualization system
  * Intelligent channel detection supporting EEG, EMG, ECG, EOG, EDA, PPG, accelerometer, gyroscope
  * Lazy loading architecture with caching for optimal performance and memory efficiency
  * Real-time data integration with selective updates and adaptive timeout management
  * Scientific visualization with publication-ready output quality

Package Architecture:

Core Infrastructure:
- adapters: Qt interaction adapters for thread-safe API-GUI communication
- core: Event system with event types and subscriber management
- interfaces: Abstract base classes defining contracts for modular, testable architecture

Data Management:
- collectors: Hardware interface layer with board configuration and device management
- processors: Signal processing algorithms with advanced filtering and analysis capabilities
- services: Business logic layer implementing singleton patterns and service coordination

User Interface:
- ui: Complete Qt-based interface with specialized panels and advanced component widgets
- visualizers: Scientific visualization components with real-time rendering and quality indicators
- utils: Theme management and help system with educational content

Advanced Features:

Service-Oriented Architecture:
- CollectorService: Singleton board management with real-time streaming and background processing
- DataAccessService: Centralized data access with filter integration and callback management
- ProcessorService: Filter coordination with immediate application and performance monitoring
- RecordingService: Multi-format recording with marker insertion and background threading
- VisualizationService: Component lifecycle management with caching and performance optimization
- InteractionService: API bridge with event system integration and component registry
- AdvancedProcessingService: ICA, wavelet, and advanced analysis with results management

Specialized Processing Services:
- ICA Services: Multiprocess computation, real-time monitoring, export capabilities
- MNE Services: Neurophysiological analysis, advanced visualization, real-time processing sessions

Real-time Capabilities:
- High-frequency data updates (50-100ms) with optimized rendering pipelines
- Dynamic parameter updates without session restart requirements
- Performance monitoring with CPU usage optimization and adaptive resource management
- Memory-efficient operations with automatic cleanup and intelligent buffer management
- Thread-safe operations with proper UI marshalling and concurrent processing support

Advanced Analysis Features:
- Independent Component Analysis with real-time monitoring and sliding window analysis
- Wavelet transforms with multiple decomposition levels and optional denoising
- MNE integration for advanced neurophysiological analysis and visualization
- Filter coordination with stability monitoring and cross-component synchronization
- Quality assessment with 5-level scoring system and real-time feedback

API Integration:
- REST API with WebSocket support for real-time data streaming
- External system integration through interaction adapters and event coordination
- Thread-safe operations with timeout management and graceful error handling
- Multi-format data access with filtering support and metadata management

Visualization Capabilities:
- Multi-page biosignal visualization with intelligent channel type detection
- Topographic brain mapping with International 10-20/10-10 electrode positioning
- Real-time signal quality monitoring with color-coded indicators and performance metrics
- Interactive visualization controls with parameter updates and immediate feedback
- Export capabilities with high-resolution output suitable for research documentation

Hardware Support:
- 20+ supported manufacturers with automatic device detection and configuration
- Preset-based configuration with parameter validation and optimization suggestions
- Streaming board support with master board coordination and real-time validation
- Channel mapping intelligence with standard positioning systems and manufacturer aliases
- Error handling with device-specific recovery mechanisms

Educational and User Experience:
- Help system with 25+ topics covering theory and practical application
- Context-sensitive guidance with parameter recommendations and best practices
- Progressive complexity support from basic setup to advanced research applications
- Error reporting with troubleshooting guidance and recovery suggestions

Technical Excellence:
- Architecture with logging and debugging capabilities
- Memory leak prevention with proper resource lifecycle management
- Cross-platform compatibility supporting Windows, Linux, and macOS environments
- Extensive parameter validation preventing invalid configurations and numerical instabilities
- Performance optimization with intelligent caching and selective processing updates

Use Cases and Applications:
- Research applications requiring precise frequency analysis and component separation
- Clinical applications with robust error handling and quality validation requirements
- Educational tools demonstrating signal processing concepts with interactive adjustment
- Brain-computer interface development with low-latency processing and feature extraction
- Real-time neurofeedback systems with immediate response and adaptive processing

Data Flow Architecture:
1. Hardware interface through EEGCollector with automatic device configuration
2. Real-time data streaming via CollectorService with optimized buffer management
3. Signal processing through ProcessorService with immediate filter application
4. Centralized data access via DataAccessService with filter integration
5. Real-time visualization through specialized visualizers with performance optimization
6. Recording and export through RecordingService with multi-format support
7. Advanced analysis through specialized services with result management
8. API integration enabling external control and real-time data access

The EEG Processor framework provides a solution for sophisticated EEG signal processing applications,
enabling researchers, clinicians, and developers to leverage advanced neurophysiological
analysis techniques through an intuitive, high-performance interface with real-time processing support and extensive hardware compatibility.
"""

# Core application and main components
from .eeg_processor_app import EEGProcessorApp
from .collectors import EEGCollector, BrainFlowBoardConfiguration, BoardConfiguration
from .processors import SignalProcessor
from .visualizers import (
    MultiSignalVisualizer,
    BrainMapVisualizer,
)

# Core infrastructure
from .core import (
    EventDispatcher,
    EventSystem,
    EventType,
    Event,
    get_dispatcher,
    dispatch,
    subscribe,
    unsubscribe,
    get_last_event,
    clear_event_history,
)

# Services layer
from .services import (
    CollectorService,
    DataAccessService,
    ProcessorService,
    RecordingService,
    VisualizationService,
    InteractionService,
    AdvancedProcessingService,
    MNEService,
)

# Interfaces for modular architecture
from .interfaces import (
    CollectorInterface,
    MarkerInterface,
    ConfigurableCollectorInterface,
    BoardInterface,
    DataStorageInterface,
    ContinuousRecordingInterface,
    MNEConverterInterface,
    MNEVisualizerInterface,
    MNEResultStorageInterface,
    MNEProcessManagerInterface,
    MNERealtimeInterface,
)

# UI components
from .ui import (
    BasePanel,
    ConnectionPanel,
    ProcessingPanel,
    RecordingPanel,
    StreamingPanel,
    MNEPanel,
    AdvancedProcessingPanel,
)

# Utilities
from .utils import (
    ThemeManager,
    HELP_CONTENT,
    HelpDialog,
    HelpButton,
    EEGConceptsHelpDialog,
    show_help_topic,
    show_eeg_concepts_help,
)

# Adapters for external integration
from .adapters import QtInteractionAdapter

# API components
from .data_access_api import EEGDataAPI
from .interaction_api import EEGProcessorInteractionAPI
from .api_integration import (
    EEGProcessorApiIntegration,
    get_api_integration,
    initialize_api,
)
from .interaction_api_integration import EEGProcessorInteractionApiIntegration

__all__ = [
    # Core application
    "EEGProcessorApp",
    # Primary components
    "EEGCollector",
    "SignalProcessor",
    "MultiSignalVisualizer",
    "BrainMapVisualizer",
    # Board configuration
    "BrainFlowBoardConfiguration",
    "BoardConfiguration",
    # Core infrastructure
    "EventDispatcher",
    "EventSystem",
    "EventType",
    "Event",
    "get_dispatcher",
    "dispatch",
    "subscribe",
    "unsubscribe",
    "get_last_event",
    "clear_event_history",
    # Services
    "CollectorService",
    "DataAccessService",
    "ProcessorService",
    "RecordingService",
    "VisualizationService",
    "InteractionService",
    "AdvancedProcessingService",
    "MNEService",
    # Interfaces
    "CollectorInterface",
    "MarkerInterface",
    "ConfigurableCollectorInterface",
    "BoardInterface",
    "DataStorageInterface",
    "ContinuousRecordingInterface",
    "MNEConverterInterface",
    "MNEVisualizerInterface",
    "MNEResultStorageInterface",
    "MNEProcessManagerInterface",
    "MNERealtimeInterface",
    # UI Panels
    "BasePanel",
    "ConnectionPanel",
    "ProcessingPanel",
    "RecordingPanel",
    "StreamingPanel",
    "MNEPanel",
    "AdvancedProcessingPanel",
    # Utilities
    "ThemeManager",
    "HELP_CONTENT",
    "HelpDialog",
    "HelpButton",
    "EEGConceptsHelpDialog",
    "show_help_topic",
    "show_eeg_concepts_help",
    # Adapters
    "QtInteractionAdapter",
    # API components
    "EEGDataAPI",
    "EEGProcessorInteractionAPI",
    "EEGProcessorApiIntegration",
    "get_api_integration",
    "initialize_api",
    "EEGProcessorInteractionApiIntegration",
]
