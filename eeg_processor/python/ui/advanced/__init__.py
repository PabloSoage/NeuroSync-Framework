"""
Advanced Processing UI Package.

This package provides the user interface layer for advanced EEG signal processing
operations within the EEG processing application. It implements an MVC
(Model-View-Controller) architecture for signal analysis with real-time
processing capabilities and advanced visualization features.

Core Components:

- AdvancedPanelController: Controller implementing advanced processing coordination
  * Manages complex interactions between multiple specialized widgets and backend services
  * Coordinates Independent Component Analysis (ICA) with real-time monitoring capabilities
  * Handles wavelet transform operations with dynamic parameter updates and inverse transforms
  * Controls advanced filtering with multiple mathematical implementations and channel selection
  * Manages downsampling operations with various aggregation methods and performance optimization
  * Implements export workflows with progress tracking and multiprocessing support
  * Provides real-time processing coordination with adaptive performance monitoring

- widgets: Specialized widget collection for advanced signal processing operations
  * AdvancedFilterWidget: Multi-type filtering with stability analysis and parameter validation
  * ICAWidget: Independent Component Analysis with real-time monitoring and export capabilities
  * WaveletWidget: Wavelet transform analysis with denoising and inverse transform support
  * DownsamplingWidget: Intelligent downsampling with performance impact indicators

- dialogs: Advanced visualization and interaction dialogs
  * ICAVisualizationDialog: ICA result visualization with interactive analysis

Controller Architecture Features:

Advanced Processing Coordination:
- Multi-service integration coordinating advanced processing, ICA, export, and real-time services
- Parameter validation with stability analysis for complex processing configurations
- Dynamic parameter updates enabling real-time modification without processing interruption
- Channel mapping intelligence converting UI selections to appropriate data array indices
- Performance optimization with adaptive processing based on system capabilities and load

Real-time Processing Management:
- Real-time ICA monitoring with sliding window analysis and configurable update intervals
- Dynamic visualization updates with memory-efficient plot refreshing and selective data updates
- Performance monitoring with CPU usage warnings and optimization suggestions for intensive operations
- Adaptive timeout management for high-frequency update intervals with automatic recovery
- Session lifecycle management with proper resource cleanup and state preservation

Export Workflow Coordination:
- Export capabilities supporting overview plots, individual components, and batch operations
- Progress tracking with cancellation support for long-running multiprocessing export operations
- Multiple export formats with customizable parameters including resolution, colormaps, and styling
- Documentation generation with consistent branding and automated file organization
- Integration with dedicated export services for CPU-intensive operations without UI blocking

Filter Integration and Coordination:
- Advanced filter coordination with basic processing panel for parameter synchronization
- Multiple filter type support including Butterworth, Chebyshev, and Bessel implementations
- Channel-specific filtering with intelligent mapping between UI selections and data indices
- Stability monitoring and warnings for potentially unstable filter configurations
- Dynamic filter application with real-time effect monitoring and performance analysis

Error Handling and Recovery:
- Exception handling with detailed error reporting and user-friendly messages
- Degradation when advanced features are unavailable or system resources are limited
- Automatic recovery from failed operations with state preservation and user notification
- Service initialization fallbacks ensuring core functionality remains available
- Resource cleanup coordination preventing memory leaks and system resource exhaustion

State Management:
- Complex state coordination across multiple processing modes and analysis techniques
- Parameter preservation across different operational contexts and processing sessions
- UI state synchronization with backend processing services and real-time operations
- Dynamic channel list updates with intelligent mapping and validation
- Processing mode transitions with proper cleanup and resource management

Service Integration:
- Advanced Processing Service coordination for signal analysis operations
- ICA Process Service integration for dedicated multiprocess ICA computation and visualization
- ICA Realtime Service coordination for continuous monitoring and adaptive processing
- Export Service integration for documentation and result archiving
- Data Access Service coordination for real-time data stream management and buffer optimization

Performance Optimization Features:
- Intelligent channel selection reducing computational load and memory usage requirements
- Real-time optimization indicators showing processing efficiency gains and resource utilization
- Performance warnings for CPU-intensive operations and parameter combinations requiring attention
- Memory usage tracking and optimization suggestions for large channel counts and complex processing
- Adaptive processing strategies based on system capabilities and current processing load

User Experience Enhancements:
- Intuitive workflow coordination between different advanced processing techniques and analysis methods
- Real-time feedback with status updates and visual progress indicators
- Performance optimization guidance with actionable suggestions for improving processing efficiency
- Context-sensitive help integration with detailed parameter guidance and best practices
- Error reporting with troubleshooting guidance and recovery suggestions

Technical Implementation:
- Qt signal/slot architecture ensuring responsive UI updates and loose coupling between components
- Multi-threading coordination with proper UI thread marshalling for real-time operations
- Resource lifecycle management with cleanup procedures and memory optimization
- Service dependency injection enabling testing, modularity, and flexible service replacement
- Event-driven architecture supporting complex workflows and asynchronous processing coordination

Integration Capabilities:
- Seamless coordination with data collection services for real-time data stream processing
- Processing panel integration for filter parameter synchronization and coordinated analysis
- Visualization service coordination for real-time display updates and performance monitoring
- Export service integration for documentation and result archiving
- Event system integration for application-wide state updates and cross-component communication

Advanced Analysis Features:
- Multi-technique analysis workflows combining filtering, ICA, and wavelet processing
- Real-time analysis with adaptive processing based on data characteristics and system performance
- Interactive result exploration with detailed visualization and statistical analysis capabilities
- Batch processing support for large-scale analysis and documentation generation
- Cross-validation between different analysis techniques for signal understanding

The advanced processing UI package provides an interface
for EEG analysis, enabling researchers to apply advanced signal
processing techniques through an intuitive Qt-based interface with real-time
processing support, parameter validation, performance optimization,
and grade result documentation capabilities.
"""

from . import dialogs
from . import widgets
from .advanced_panel_controller import AdvancedPanelController

__all__ = ["AdvancedPanelController", "dialogs", "widgets"]
