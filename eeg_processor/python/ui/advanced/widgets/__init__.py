"""
Advanced Processing Widgets Package.

This package provides specialized Qt widgets for advanced EEG signal processing operations
within the EEG processing application. These widgets offer comprehensive user interfaces
for sophisticated analysis techniques including filtering, decomposition, and feature
extraction methods.

Core Advanced Processing Widgets:

- AdvancedFilterWidget: Comprehensive advanced filtering interface
  * Multiple filter types: Butterworth, Chebyshev Type 1, Bessel with zero-phase variants
  * Configurable filter order (1-10) with stability recommendations for each type
  * Window function selection: Hanning, Hamming, Blackman-Harris for frequency domain operations
  * Ripple control for Chebyshev filters with stability warnings and parameter validation
  * Channel-specific filtering with intuitive selection interface and optimization indicators
  * Dynamic parameter updates with real-time application to data streams
  * Stability monitoring and warnings for potentially unstable filter configurations
  * Integration with basic bandpass parameters from processing panel for coordinated filtering

- ICAWidget: Independent Component Analysis control interface
  * Configurable component count (1-16) with automatic optimization suggestions
  * Advanced channel selection with performance impact indicators
  * Standard ICA computation with progress monitoring and result visualization
  * Real-time ICA monitoring with sliding window analysis (0.5-2.0s update intervals)
  * Dynamic parameter updates during active real-time sessions without restart
  * Component visualization with multiple colormap options (Viridis, Plasma, Inferno, etc.)
  * Export capabilities for overview plots and individual component analysis
  * Performance optimization with channel reduction strategies for computational efficiency

- WaveletWidget: Wavelet transform analysis interface
  * Comprehensive wavelet type selection including Daubechies, Biorthogonal, Coiflets, Symlets
  * Configurable decomposition levels (1-8) with frequency separation guidance
  * Channel-specific analysis with intelligent selection for single-channel operations
  * Extension type control (Symmetric, Periodic) for boundary condition handling
  * Optional wavelet denoising with artifact removal capabilities before transformation
  * Inverse wavelet transform application with real-time toggle capabilities
  * Dynamic parameter updates for live coefficient modification and analysis
  * Coefficient visualization and analysis tools for detailed wavelet decomposition

- DownsamplingWidget: Data downsampling operations interface
  * Configurable downsampling factors (2-10x) with performance impact indicators
  * Multiple aggregation methods: Mean, Median, Each for different analysis requirements
  * Real-time application with immediate effect on data streams and visualization
  * Dynamic parameter updates with automatic recomputation of downsampled data
  * Memory usage optimization indicators showing computational load reduction
  * Integration with visualization systems for immediate feedback on parameter changes

Key Features:

Advanced Signal Processing Capabilities:
- State-of-the-art filtering with multiple mathematical implementations
- Independent Component Analysis for artifact removal and source separation
- Wavelet analysis for time-frequency decomposition and denoising
- Intelligent downsampling for computational efficiency and storage optimization
- Real-time processing with dynamic parameter updates without session interruption

User Experience Enhancements:
- Intuitive parameter controls with validation and stability warnings
- Real-time visual feedback with immediate parameter effect visualization
- Performance optimization suggestions based on computational load analysis
- Channel selection optimization with memory usage and processing time indicators
- Comprehensive tooltips and help integration for parameter guidance and best practices

Dynamic Processing Features:
- Live parameter updates with immediate effect on active data streams
- Real-time monitoring of computational performance and optimization opportunities
- Adaptive UI behavior based on current processing load and system capabilities
- Seamless integration between different processing techniques for complex analysis pipelines
- Memory-efficient operations with automatic buffer management and resource optimization

Technical Implementation:
- Qt signal/slot architecture for responsive UI updates and loose coupling
- Thread-safe parameter updates with proper synchronization between UI and processing
- Resource lifecycle management with comprehensive cleanup and memory optimization
- Error handling with detailed user feedback and automatic recovery mechanisms
- Integration with advanced processing service for sophisticated analysis coordination

Stability and Validation:
- Comprehensive parameter validation with range checking and stability analysis
- Automatic detection of potentially unstable configurations with user warnings
- Graceful degradation for edge cases and parameter boundary conditions
- Performance monitoring with adaptive timeout management for intensive operations
- Cross-validation between related parameters for consistent analysis results

Integration Capabilities:
- Seamless coordination with advanced processing service for backend computation
- Real-time synchronization with data access service for continuous data streams
- Integration with visualization systems for immediate feedback and result display
- Channel selection coordination with other components for consistent analysis workflows
- Event system integration for application-wide state updates and synchronization

The advanced processing widgets provide a complete, production-ready interface
for sophisticated EEG analysis, enabling researchers to apply advanced signal
processing techniques through an intuitive Qt-based interface with real-time
processing support, comprehensive parameter validation, and performance optimization.
"""

from .advanced_filter_widget import AdvancedFilterWidget
from .downsampling_widget import DownsamplingWidget
from .ica_widget import ICAWidget
from .wavelet_widget import WaveletWidget

__all__ = ["AdvancedFilterWidget", "DownsamplingWidget", "ICAWidget", "WaveletWidget"]
