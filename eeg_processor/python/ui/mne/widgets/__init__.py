"""
MNE Widgets Package.

This package provides specialized Qt widgets for MNE (Modified Neurophysiological Environment)
integration within the EEG processing application. These widgets offer user
interfaces for data conversion, visualization, status monitoring, and channel selection
specific to MNE operations.

Core MNE Widgets:

- MNEConversionWidget: Advanced data conversion interface for BrainFlow to MNE format
  * Multiple conversion modes: Flexible (all channels), Performance (selected), Real-time
  * Dynamic parameter controls with real-time updates and performance warnings
  * Filter integration with processing panel filters (bandpass, notch, detrend)
  * Real-time mode with configurable update intervals (0.5-30 seconds)
  * Performance optimization indicators and CPU usage warnings
  * Channel selection integration for performance mode operations
  * Dynamic status updates and mode-specific UI adaptations

- MNEVisualizationWidget: Visualization control interface
  * Multiple plot types: Power Spectral Density (PSD), Topomaps, Raw Data, Spectrograms
  * Dynamic parameter updates with real-time signal emission for live processing
  * Frequency range controls with validation and band-specific settings
  * Topomap frequency band selection (Alpha, Beta, Gamma, Delta, Theta, Custom)
  * PSD mode selection (individual channels vs averaged with variability)
  * Channel selection integration with real-time optimization indicators
  * Base64 image display with proper scaling and error handling
  * Real-time mode indicators and automatic update status display

- MNEStatusWidget: Real-time operation monitoring and status tracking
  * Timestamped status message logging with monospace font display
  * Real-time session monitoring with performance metrics and efficiency tracking
  * CPU usage warnings and timeout detection for high-frequency operations
  * Channel optimization messages and computation load indicators
  * Performance warnings for processing time vs update interval analysis
  * Color-coded status indicators (green for normal, amber for warnings, red for errors)
  * Uptime tracking and update count monitoring for continuous sessions

- ChannelSelectionDialog: Reusable channel selection interface
  * Grid-based checkbox layout for efficient channel selection
  * Select All/Deselect All functionality for quick bulk operations
  * Real-time selection count display and validation
  * Scrollable interface for handling large channel counts
  * Dark theme integration with consistent application styling
  * Modal dialog design for focused channel selection workflow
  * Proper keyboard navigation and accessibility support

Key Features:

Real-time Integration:
- Dynamic parameter updates without requiring session restart
- Performance monitoring with CPU usage warnings and optimization tips
- Live status updates with color-coded indicators and progress tracking
- Automatic UI adaptation based on processing mode and performance requirements

User Experience Enhancements:
- Consistent dark theme styling across all widgets
- Intuitive mode switching with automatic UI reconfiguration
- Performance warnings and optimization suggestions for efficient processing
- Real-time feedback with emoji indicators and visual status cues
- Tooltips and help integration for parameter guidance

Technical Capabilities:
- Qt signal/slot architecture for loose coupling with backend services
- Thread-safe status updates with proper UI thread marshalling
- Efficient image display with base64 decoding and automatic scaling
- Responsive layout design adapting to different window sizes
- Proper resource management and cleanup for widget lifecycle

Performance Optimization:
- Channel selection optimization with computation load reduction indicators
- Real-time performance monitoring with adaptive timeout management
- CPU usage warnings for high-frequency update intervals
- Memory-efficient image handling with proper scaling and caching
- Optimized UI updates to prevent blocking during intensive operations

Integration Features:
- Seamless integration with MNE services and processing pipeline
- Coordination with data access service for real-time data retrieval
- Filter integration with processing panel for advanced signal conditioning
- Event system integration for application-wide state synchronization
- Backward compatibility with existing MNE service APIs

The MNE widgets provide a user-friendly interface for advanced
neurophysiological analysis, enabling researchers to leverage MNE-Python
capabilities through an intuitive Qt-based interface with real-time processing
support and performance monitoring.
"""

from .channel_selection_dialog import ChannelSelectionDialog
from .mne_conversion_widget import MNEConversionWidget
from .mne_status_widget import MNEStatusWidget
from .mne_visualization_widget import MNEVisualizationWidget

__all__ = [
    "ChannelSelectionDialog",
    "MNEConversionWidget",
    "MNEStatusWidget",
    "MNEVisualizationWidget",
]
