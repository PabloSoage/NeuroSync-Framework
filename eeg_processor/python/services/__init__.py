"""
Services Package for EEG Processing System.

This package provides the core business logic and service layer for the EEG processing
application. It implements a comprehensive service-oriented architecture that coordinates
data collection, processing, visualization, recording, and advanced analysis operations.

Core Services:

- CollectorService: Singleton service for EEG data collection and board management
  * Board connection and disconnection with comprehensive parameter validation
  * Real-time data streaming with configurable buffer management and immediate processing
  * Support for multiple board types including OpenBCI, Muse, synthetic, and streaming boards
  * Background data retrieval with optimized sample rate metrics and low-latency updates
  * Marker insertion and device configuration capabilities
  * Integration with DataAccessService for seamless data flow

- DataAccessService: Singleton service providing centralized data access and management
  * Real-time data buffer management with automatic size control and truncation
  * Separated callback flows for local application and external API consumers
  * Optional multiprocessing support for API callbacks with worker pools
  * Filter and advanced processing integration with processor service coordination
  * Thread-safe operations with comprehensive metadata management
  * Support for raw and processed data access with dynamic filter application

- ProcessorService: Signal processing operations and filter management
  * Bandpass, notch, and detrend filtering with automatic EEG channel detection
  * Advanced filtering with multiple filter types (Butterworth, Chebyshev, Bessel)
  * Wavelet processing including denoising and coefficient computation
  * Independent Component Analysis (ICA) computation and management
  * Downsampling operations with configurable aggregation methods
  * EEG metrics calculation including power spectral density and band powers

- RecordingService: Data recording and storage management
  * Continuous recording with real-time data callbacks for immediate storage
  * Support for raw, processed, or dual-stream recording modes
  * CSV format output with comprehensive metadata headers and channel naming
  * Marker insertion during recording with proper timestamp synchronization
  * Background recording thread with proper resource management and cleanup
  * Integration with collector service for seamless data capture

- VisualizationService: Visualization component management and coordination
  * EEG waveform visualization with caching and performance optimization
  * Brain map visualization with collector and processor integration
  * Filter settings management and visualization state tracking
  * Window lifecycle management with proper cleanup and resource handling
  * Integration with Qt-based visualization components

- InteractionService: Singleton service bridging external API and internal operations
  * RESTful API integration with comprehensive error handling and status tracking
  * Event system integration for real-time UI updates and state synchronization
  * Component registry for managing application services and dependencies
  * Validation and state checking for all operations with detailed error reporting
  * Auto-initialization and recovery mechanisms for robust operation

- AdvancedProcessingService: Advanced signal processing and analysis operations
  * Independent Component Analysis with configurable parameters and validation
  * Wavelet transform computation with support for multiple wavelet types
  * Real-time inverse wavelet transform application to data streams
  * Advanced filtering with stream integration and dynamic parameter updates
  * Downsampling operations with real-time application capabilities
  * Results storage and management for computed analyses

- MNEService: Facade service for MNE-Python integration and neurophysiological analysis
  * Asynchronous data conversion from BrainFlow to MNE format with task management
  * Advanced visualization capabilities including PSD, spectrograms, and topomaps
  * Real-time processing sessions with configurable update intervals
  * Multiprocessing support for CPU-intensive operations with proper resource management
  * Result storage and task lifecycle management with comprehensive status tracking
  * Backward compatibility layer for existing code and seamless API transitions

Specialized Service Packages:

- ica: Independent Component Analysis services
  * ICAProcessService: Multiprocess ICA computation with Qt signal integration
  * ICARealtimeService: Real-time ICA monitoring with sliding window analysis
  * ExportService: Comprehensive ICA result export with progress tracking

- mne: MNE-Python integration services
  * MNEConverterService: BrainFlow to MNE data conversion with async processing
  * MNEVisualizerService: Advanced neurophysiological visualization capabilities
  * MNERealtimeService: Real-time MNE processing with session management
  * MNEResultStorage: Thread-safe result storage with lifecycle management
  * MNEProcessManager: Multiprocessing coordination for CPU-intensive operations

Key Architectural Features:

- Singleton Pattern: Core services use singleton pattern for consistent state management
- Event-Driven Architecture: Integration with event system for loose coupling
- Service-Oriented Design: Clear separation of concerns with well-defined interfaces
- Thread Safety: All services implement proper locking and thread-safe operations
- Resource Management: Comprehensive cleanup and lifecycle management
- Error Handling: Robust error handling with detailed logging and recovery mechanisms
- Performance Optimization: Optimized data flows and processing pipelines
- Extensibility: Plugin-like architecture for easy addition of new capabilities

Data Flow Architecture:
1. CollectorService manages hardware interface and raw data collection
2. DataAccessService provides centralized buffer management and data access
3. ProcessorService applies signal processing and filtering operations
4. RecordingService handles data persistence and storage operations
5. VisualizationService manages real-time display and user interface
6. AdvancedProcessingService provides sophisticated analysis capabilities
7. MNEService enables advanced neurophysiological analysis and visualization

The services package provides a complete, production-ready foundation for EEG
signal processing applications with real-time capabilities, advanced analysis
features, and comprehensive data management.
"""

# Import specialized service packages
from . import ica
from . import mne
from .advanced_processing_service import AdvancedProcessingService
from .collector_service import CollectorService
from .data_access_service import DataAccessService
from .interaction_service import InteractionService
from .mne_service import MNEService
from .processor_service import ProcessorService
from .recording_service import RecordingService
from .visualization_service import VisualizationService

__all__ = [
    # Core services
    "CollectorService",
    "DataAccessService",
    "ProcessorService",
    "RecordingService",
    "VisualizationService",
    "InteractionService",
    "AdvancedProcessingService",
    "MNEService",
    # Specialized service packages
    "ica",
    "mne",
]
