"""
User Interface Package for EEG Processor Application.

This package provides a modular user interface built with PyQt5 for
EEG data processing applications. It implements a panel-based architecture where each
component handles specific aspects of the EEG processing workflow, from data collection
to advanced signal analysis.

Core UI Panels:

- BasePanel: Foundation class providing common functionality for all UI panels
  * Standardized signal communication (status_message, error_message)
  * Scrollable layout support with proper content management
  * Common error handling and status reporting mechanisms
  * Consistent styling and theme integration across all panels

- ConnectionPanel: Board connection and streaming control interface
  * Board selection with intelligent filtering and categorization
  * Dynamic parameter validation with visual feedback (required/optional/disabled fields)
  * Advanced streaming board configuration with preset synchronization validation
  * Real-time board information display with channel mapping and sampling rate details
  * Event-driven UI updates for API synchronization and state management
  * Visualization window management with reopening capabilities

- ProcessingPanel: Signal processing and filtering operations interface
  * Real-time filter application with dynamic parameter updates during processing
  * Bandpass, notch, and detrend filtering with automatic EEG channel detection
  * EEG metrics calculation including band powers and statistical analysis
  * Brain map visualization integration with performance optimization
  * Filter state synchronization across multiple consumers (visualization, MNE, WebSocket)
  * Dynamic frequency validation based on sampling rate and Nyquist limits

- RecordingPanel: Data recording and marker insertion interface
  * Multi-format recording support (raw, processed, both) with real-time data streaming
  * Marker insertion during recording with precise timestamp synchronization
  * File browser integration with automatic path validation and format detection
  * Recording status monitoring with error handling and recovery
  * API compatibility for external recording control and status updates

- StreamingPanel: Data streaming configuration and management interface
  * Multi-streamer support: File streaming (via RecordingService), Network, Custom protocols
  * Intelligent streamer type detection with automatic parameter validation
  * Streaming board preset validation with socket timeout error prevention
  * Active streamer tracking with proper cleanup and state management
  * Board configuration commands with response monitoring and error handling

- MNEPanel: MNE library integration for advanced neurophysiological analysis
  * SOLID principle implementation with specialized widget composition and controller coordination
  * Multi-mode conversion support: Flexible (all channels), Performance (selected), Real-time
  * Advanced visualization with PSD, topomaps, spectrograms, and raw data displays
  * Real-time processing sessions with dynamic parameter updates and performance monitoring
  * Error handling with graceful degradation when MNE is unavailable

- AdvancedProcessingPanel: Advanced signal processing operations interface
  * Independent Component Analysis with real-time monitoring and export capabilities
  * Wavelet transform analysis with denoising and inverse transform support
  * Advanced filtering with multiple mathematical implementations and stability analysis
  * Intelligent downsampling with performance optimization and aggregation method selection
  * Multi-technique analysis workflows with cross-validation and result coordination

Specialized UI Packages:

- advanced: Advanced processing UI components
  * AdvancedPanelController: Controller coordinating multiple specialized widgets
  * widgets: Specialized widgets for ICA, wavelet, filtering, and downsampling operations
  * dialogs: Advanced visualization dialogs for interactive result exploration

- mne: MNE integration UI components
  * MNEPanelController: SOLID-principle implementation for MNE operations coordination
  * widgets: Specialized widgets for conversion, visualization, status monitoring, and channel selection

Architectural Features:

Panel-Based Modular Design:
- Each panel encapsulates specific functionality with clear separation of concerns
- Standardized communication through Qt signals for loose coupling between components
- Hierarchical widget composition with specialized controllers for complex operations
- Consistent base class implementation providing common UI patterns and error handling

Real-time Processing Support:
- Dynamic parameter updates without requiring processing session restarts
- Performance monitoring with CPU usage warnings and optimization suggestions
- Adaptive timeout management for high-frequency update intervals
- Memory-efficient operations with automatic buffer management and resource cleanup

State Management and Synchronization:
- Event-driven architecture for application-wide state updates and cross-component communication
- API compatibility layer for external control and monitoring of UI state
- Persistent state preservation across different operational contexts and processing sessions
- Filter state synchronization between panels and backend services

Error Handling and Recovery:
- Exception handling with detailed error reporting and user-friendly messages
- Graceful degradation when advanced features are unavailable or system resources are limited
- Automatic recovery from failed operations with state preservation and user notification
- Service initialization fallbacks ensuring core functionality remains available

User Experience Enhancements:
- Intelligent parameter validation with real-time feedback and stability warnings
- Performance optimization guidance with actionable suggestions for improving processing efficiency
- Context-sensitive help integration with detailed parameter guidance and best practices
- Dark theme integration with consistent styling across all components

Integration Capabilities:
- Seamless coordination with backend services for data collection, processing, and analysis
- Real-time data stream management with optimized buffer operations and low-latency updates
- Visualization service integration for immediate feedback and result display
- Export service coordination for documentation and result archiving

Technical Implementation:
- Qt5 framework with proper signal/slot architecture for responsive UI updates
- Thread-safe operations with appropriate UI thread marshalling for real-time processing
- Resource lifecycle management with cleanup procedures and memory optimization
- Scrollable layouts with adaptive content management for varying screen sizes and content

Validation and Stability:
- Parameter range validation with automatic adjustment for stability and performance
- Cross-validation between related parameters for consistent analysis results
- Real-time stability monitoring for filter configurations and processing parameters
- Performance impact assessment with warnings for CPU-intensive operations

The UI package provides a interface for EEG analysis, enabling researchers and practitioners to leverage advanced signal
processing techniques through an intuitive, feature-rich Qt-based interface with
real-time processing support, result documentation,
and robust error handling throughout all operations.
"""

# Import specialized UI packages
from . import advanced
from . import mne
from .advanced_panel import AdvancedProcessingPanel
from .base_panel import BasePanel
from .connection_panel import ConnectionPanel
from .mne_panel import MNEPanel
from .processing_panel import ProcessingPanel
from .recording_panel import RecordingPanel
from .streaming_panel import StreamingPanel

__all__ = [
    # Core UI panels
    "BasePanel",
    "ConnectionPanel",
    "ProcessingPanel",
    "RecordingPanel",
    "StreamingPanel",
    "MNEPanel",
    "AdvancedProcessingPanel",
    # Specialized UI packages
    "advanced",
    "mne",
]
