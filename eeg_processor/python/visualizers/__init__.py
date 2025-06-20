"""
Visualizers Package for EEG and Biosignal Data Visualization.

This package provides real-time visualization tools for EEG and other
biosignal data types. It implements a modular architecture supporting multiple
visualization modalities with optimized performance, caching mechanisms, and
scientific visualization capabilities.

Core Visualizers:

- MultiSignalVisualizer: Advanced multi-page biosignal visualization system
  * Intelligent channel type detection from connected boards with preset-specific configurations
  * Lazy loading visualization architecture with caching for performance optimization
  * Multi-tab interface supporting EEG, EMG, ECG, EOG, EDA, PPG, accelerometer, and gyroscope data
  * Real-time data integration with DataAccessService for immediate updates and low-latency processing
  * Advanced signal processing status monitoring with filter, wavelet, and downsampling indicators
  * Performance-optimized rendering with selective tab updates and memory-efficient operations
  * Dark theme integration with scientific visualization standards

- BrainMapVisualizer: Topographic brain mapping for EEG signal quality monitoring
  * International 10-20/10-10 electrode positioning system with standard positions
  * Real-time signal quality visualization using color-coded quality indicators (5-level system)
  * Anatomical brain region overlays (frontal, central, parietal, occipital) with proper coloring
  * Intelligent electrode name matching with alias support for various hardware manufacturers
  * G.tec Unicorn compatibility with automatic channel mapping to standard positions
  * Performance monitoring with adaptive update rates and quality calculation optimization
  * Interactive electrode labels with quality legend and orientation markers

Key Features:

Real-time Processing Capabilities:
- High-frequency data updates (50-100ms) with optimized rendering pipelines
- Intelligent caching system preserving visualizers across board reconnections
- Selective update mechanisms preventing UI blocking during intensive operations
- Performance monitoring with CPU usage optimization and adaptive timeout management
- Memory-efficient buffer management with automatic cleanup and resource optimization

Advanced Visualization Features:
- Scientific-grade visualization with color schemes and proper scaling
- Multiple plot types: time series, power spectral density, topographic maps, band powers
- Quality indicators with 5-level color coding (excellent, good, fair, poor, bad)
- Interactive elements with mouse wheel scrolling, zoom, and pan capabilities
- High-resolution rendering suitable for research documentation and publication

Channel Detection and Management:
- Intelligent channel type detection from actual connected hardware and preset configurations
- Support for multiple hardware manufacturers (OpenBCI, g.tec, Muse, ANT Neuro, etc.)
- Automatic electrode positioning with standard 10-20/10-10 system compliance
- Fallback mechanisms ensuring visualization availability even with unrecognized hardware
- Dynamic channel mapping with real-time updates based on device configuration changes

Performance Optimization:
- Lazy loading architecture reducing startup time and memory usage
- Caching mechanisms with intelligent invalidation based on board and preset changes
- Selective rendering updating only visible components to maintain responsiveness
- Thread-safe operations with proper UI thread marshalling for real-time updates
- Resource lifecycle management with cleanup procedures

Signal Processing Integration:
- Real-time filter status monitoring with visual indicators for active processing
- Integration with advanced processing pipeline showing wavelet, ICA, and downsampling status
- Quality calculation coordination with signal processor for accurate quality metrics
- Dynamic processing parameter updates with immediate visual feedback

Scientific Visualization Standards:
- International electrode positioning standards (10-20/10-10 system) with precise coordinates
- Brain region visualization and coloring
- Color schemes optimized for extended viewing and scientific accuracy
- High-contrast dark theme reducing eye strain during long analysis sessions
- Output with proper scaling, fonts, and appearance

User Experience Enhancements:
- Intuitive tab-based interface with clear modality separation and easy navigation
- Real-time status indicators showing processing state, sample rates, and efficiency metrics
- Context-sensitive help integration with detailed parameter guidance
- Responsive layout adapting to different screen sizes and channel counts
- Error handling with user-friendly messages and automatic recovery

Integration Capabilities:
- Seamless coordination with DataAccessService for centralized data management
- Filter integration showing real-time processing effects and parameter synchronization
- Event system integration for application-wide state updates and cross-component communication
- Service dependency injection enabling testing, modularity, and flexible service replacement
- Backward compatibility with existing visualization workflows and API interfaces

Technical Implementation:
- PyQtGraph framework providing high-performance scientific visualization capabilities
- Qt5 integration with proper signal/slot architecture for responsive UI updates
- NumPy-optimized data processing with efficient array operations and memory management
- Thread-safe operations with appropriate UI thread marshalling for real-time processing
- Error handling with detailed logging and automatic recovery mechanisms

Data Flow Architecture:
1. Channel detection from connected hardware with preset-specific configuration analysis
2. Lazy visualization creation with caching for performance optimization
3. Real-time data integration from DataAccessService with immediate update processing
4. Quality calculation coordination with signal processor for accurate metrics
5. Dynamic rendering with selective updates and memory-efficient operations
6. Presentation with scientific visualization standards and user experience optimization

The visualizers package provides a solution for EEG and biosignal visualization, enabling researchers and practitioners
to monitor, analyze, and document signal quality and characteristics through
intuitive, high-performance, visualization interfaces
with real-time processing support and output quality.
"""

from .brain_map_viz import BrainMapVisualizer
from .eeg_viz import MultiSignalVisualizer

__all__ = [
    "MultiSignalVisualizer", 
    "BrainMapVisualizer",
]
