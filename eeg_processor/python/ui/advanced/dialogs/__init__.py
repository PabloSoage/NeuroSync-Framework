"""
Advanced Processing Dialogs Package.

This package provides specialized Qt dialog windows for advanced EEG signal processing
visualization and interaction within the EEG processing application. These dialogs offer
modal and non-modal interfaces for detailed analysis and export of
processing results.

Core Advanced Processing Dialogs:

- ICAVisualizationDialog: Independent Component Analysis visualization interface
  * Multi-component display with scrollable layout for handling large numbers of components (1-16)
  * Interactive component visualization with click-to-detail functionality for in-depth analysis
  * Real-time mode support with optimized updates and memory-efficient plot refreshing
  * Matrix visualization for mixing (A) and unmixing (W) matrices with detailed statistical analysis
  * Multiple export formats including overview plots, individual components, and batch exports
  * Advanced colormap selection with 8 built-in options (Viridis, Plasma, Inferno, Magma, etc.)
  * Memory leak prevention with proper matplotlib figure lifecycle management
  * Performance optimization for real-time updates without UI blocking

Key Features:

Interactive Visualization Capabilities:
- Click-to-detail functionality revealing component analysis with time series and PSD
- Matrix interaction showing detailed weight distributions and statistical breakdowns
- Scrollable interface accommodating varying numbers of components with responsive layout
- Component-specific export with progress monitoring and high-resolution output (300 DPI)
- Real-time visualization updates with optimized plot data refreshing for continuous monitoring

Export and Analysis Features:
- Multi-format export supporting PNG with customizable colormaps and styling
- Overview export combining all components and matrices in a single visualization
- Batch export functionality for all components with individual detail plots and analysis
- Matrix export with statistical overlays, weight distributions, and annotation support
- Progress tracking with cancellation support for long-running export operations
- Multiprocessing export architecture preventing UI blocking during intensive operations

Real-time Processing Support:
- Optimized real-time update mechanism with selective plot data refreshing
- Memory-efficient updates preserving figure structure while updating component data
- Automatic timestamp tracking and display for monitoring session duration
- Performance monitoring with adaptive update strategies based on processing load
- Real-time status indicators with color-coded feedback and session information

Advanced User Experience:
- Dark theme integration with consistent application styling
- Intuitive navigation with mouse wheel scrolling and keyboard accessibility
- Context-sensitive tooltips and help integration for parameter guidance
- Modal and non-modal operation modes for flexible workflow integration
- Responsive layout adapting to different screen sizes and component counts

Technical Implementation:
- Qt-based architecture with proper signal/slot communication patterns
- Matplotlib integration with Qt5Agg backend for high-quality scientific visualization
- Memory management with automatic figure cleanup and resource lifecycle control
- Thread-safe operations with proper UI thread marshalling for real-time updates
- Multiprocessing worker architecture for CPU-intensive export operations

Performance Optimization:
- Lazy loading of visualization components for improved startup performance
- Optimized real-time updates with selective data refreshing instead of full recreation
- Memory leak prevention through proper matplotlib figure and canvas management
- Efficient scrolling with viewport-based rendering for large component counts
- Background export processing with progress feedback and cancellation support

Integration Capabilities:
- Seamless integration with ICA processing services and advanced analysis pipeline
- Coordination with export services for result documentation
- Event system integration for application-wide state updates and notifications
- Service dependency injection for testing and modularity support
- Backward compatibility with existing ICA visualization workflows

Statistical Analysis Features:
- Component statistics including mean, standard deviation, min/max analysis
- Power spectral density computation with frequency domain analysis and band power calculation
- Matrix weight distribution analysis with histogram visualization and statistical summaries
- Time-frequency analysis capabilities with spectrogram support for detailed component inspection
- Interactive statistical overlays with click-to-reveal detailed numerical analysis

Export Workflow Capabilities:
- Documentation export with consistent styling and branding
- Batch processing support for research documentation and report generation
- Customizable export parameters including resolution, format, and colormap selection
- Automated file naming conventions with timestamp and component identification
- Directory-based organization for large-scale analysis documentation

The advanced processing dialogs provide an interface
for EEG analysis visualization, enabling researchers to explore
and document ICA results through an intuitive, feature-rich Qt-based interface
with real-time processing support, export capabilities, and
visualization quality.
"""

from .ica_visualization_dialog import ICAVisualizationDialog

__all__ = ["ICAVisualizationDialog"]
