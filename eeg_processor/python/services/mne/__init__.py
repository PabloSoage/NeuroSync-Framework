"""
MNE Services Package.

This package provides services for MNE (Modified Neurophysiological Environment)
integration in the EEG processing system. It enables advanced neurophysiological analysis,
visualization, and real-time processing capabilities through MNE-Python.

Core MNE Services:

- MNEConverterService: BrainFlow to MNE data conversion service
  * Asynchronous conversion of raw EEG data to MNE Raw objects
  * Supports channel selection and unit conversion (µV to V)
  * Handles metadata extraction and channel information creation
  * Provides proper EEG channel mapping and naming conventions
  * Validates data availability and duration requirements
  * Integrates with multiprocessing for non-blocking conversions

- MNEVisualizerService: Advanced visualization service for MNE data
  * Creates multiple plot types: PSD, Spectrogram, Raw Data, Topomaps
  * Supports individual channel visualization and averaged displays
  * Provides customizable frequency ranges and colormaps
  * Implements dark theme integration for consistent UI appearance
  * Generates high-quality plots (200 DPI) with proper aspect ratios
  * Handles channel-specific color coding and legend management
  * Returns base64-encoded images for web/GUI integration

- MNERealtimeService: Real-time MNE processing and visualization
  * Maintains continuous processing sessions with configurable update intervals (0.5-30s)
  * Supports dynamic parameter updates during active sessions
  * Provides channel selection optimization for performance
  * Implements sliding window analysis with adaptive timeouts
  * Includes performance monitoring and statistics tracking
  * Supports both raw and filtered data processing modes
  * Manages multiple concurrent real-time sessions

- MNEResultStorage: Thread-safe result storage and management
  * Stores conversion and visualization results with unique task IDs
  * Provides atomic operations for concurrent access
  * Implements memory-efficient result lifecycle management
  * Supports bulk operations for cleaning up tasks
  * Thread-safe operations using RLock for consistency

- MNEProcessManager: Multiprocessing management for CPU-intensive operations
  * Manages dedicated process pool (2 workers) for MNE operations
  * Provides task submission with custom task ID support
  * Implements task status monitoring and cancellation capabilities
  * Handles process lifecycle management and cleanup
  * Ensures proper worker initialization and signal handling
  * Supports callback mechanisms for task completion notification

Key Features:
- Asynchronous processing architecture preventing UI blocking
- Real-time analysis with configurable performance parameters
- Advanced visualization capabilities with multiple plot types
- Channel selection optimization for improved performance
- Thread-safe and process-safe operations throughout
- Error handling and logging
- Memory-efficient result management
- Integration with BrainFlow data collection pipeline
- Support for both individual and batch processing workflows

Visualization Capabilities:
- Power Spectral Density (PSD) plots with individual or averaged channels
- Time-frequency spectrograms for single channel analysis
- Raw EEG data visualization with proper scaling and coloring
- Topographic maps showing spatial power distribution
- Customizable frequency bands (Delta, Theta, Alpha, Beta, Gamma)
- High-resolution export capabilities for documentation

Real-time Features:
- Continuous data stream processing with minimal latency
- Dynamic parameter updates without session restart
- Performance monitoring and adaptive timeout management
- Multiple concurrent session support
- Optimized channel selection for reduced computational load
- Integration with filter processing pipeline

The MNE services provide a solution for advanced EEG analysis,
enabling researchers and practitioners to leverage the full power of MNE-Python
within a user-friendly real-time processing environment.
"""

from .mne_converter_service import MNEConverterService
from .mne_process_manager import MNEProcessManager
from .mne_realtime_service import MNERealtimeService
from .mne_result_storage import MNEResultStorage
from .mne_visualizer_service import MNEVisualizerService

__all__ = [
    "MNEConverterService",
    "MNEProcessManager",
    "MNERealtimeService",
    "MNEResultStorage",
    "MNEVisualizerService",
]
