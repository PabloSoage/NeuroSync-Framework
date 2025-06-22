"""
ICA Services Package.

This package provides specialized services for Independent Component Analysis (ICA)
operations in the EEG processing system. It includes functionality
for ICA computation, visualization, real-time processing, and export capabilities.

Core ICA Services:

- ICAProcessService: Dedicated multiprocess service for ICA operations
  * Manages a persistent worker process for all ICA-related computations
  * Handles ICA computation with configurable parameters and component selection
  * Provides asynchronous visualization with real-time updates and colormap support
  * Supports both manual visualization requests and real-time streaming updates
  * Manages export operations for overview images and individual component analysis
  * Implements proper process lifecycle management and cleanup procedures
  * Uses Qt signals for seamless integration with the main UI thread

- ICARealtimeService: Real-time ICA computation and monitoring
  * Maintains sliding window buffers for continuous ICA analysis
  * Provides configurable update intervals (0.5-2.0 seconds) for real-time processing
  * Supports dynamic parameter updates during active processing sessions
  * Implements proper data buffer management with configurable window sizes (2.0-10.0 seconds)
  * Handles channel selection and component number configuration
  * Provides real-time status monitoring and error handling
  * Integrates with the main data access service for continuous data retrieval

- ExportService: Export functionality for ICA results
  * Exports enhanced overview images with detailed component visualization
  * Creates individual component plots with time series and power spectral density
  * Generates matrix visualizations for mixing and unmixing matrices
  * Supports batch export of all ICA components to directory structures
  * Provides progress tracking and cancellation capabilities for long operations
  * Uses separate worker processes to prevent UI blocking during exports
  * Supports multiple colormap options and high-resolution output (300 DPI)

Key Features:
- Multiprocess architecture for CPU-intensive ICA computations
- Real-time processing with configurable sliding windows
- Visualization options with customizable colormaps
- Export capabilities for analysis documentation and reporting
- Proper resource management and cleanup procedures
- Thread-safe communication using Qt signals and multiprocessing queues
- Error handling and progress monitoring for all operations
- Integration with the main EEG processing pipeline

The ICA services are designed to work seamlessly with the main EEG collector
and processor services, providing a solution for independent component
analysis in real-time EEG applications.
"""

from .export_service import ExportService
from .ica_process_service import ICAProcessService
from .ica_realtime_service import ICARealtimeService

__all__ = ["ExportService", "ICAProcessService", "ICARealtimeService"]
