"""
MNE UI Package.

This package provides the complete user interface layer for MNE (Modified Neurophysiological
Environment) integration within the EEG processing application. It implements a comprehensive
MVC (Model-View-Controller) architecture for advanced neurophysiological analysis with
real-time processing capabilities.

Core Components:

- MNEPanelController: Advanced controller implementing SOLID principles
  * Single Responsibility: Coordinates MNE panel operations exclusively
  * Open/Closed: Extensible through Qt signals and service interfaces
  * Liskov Substitution: Compatible controller interface for easy replacement
  * Interface Segregation: Uses specific widget interfaces for focused functionality
  * Dependency Inversion: Depends on service abstractions rather than concrete implementations

  Key Features:
  * Real-time processing session management with dynamic parameter updates
  * Asynchronous task coordination for conversion and visualization operations
  * Filter integration with processing panel for advanced signal conditioning
  * Performance optimization through intelligent channel selection strategies
  * Comprehensive error handling and status monitoring throughout operations
  * Multi-mode support: Flexible (all channels), Performance (selected), Real-time

- widgets: Specialized Qt widget collection for MNE operations
  * MNEConversionWidget: Advanced conversion interface with multiple processing modes
  * MNEVisualizationWidget: Comprehensive visualization controls with real-time updates
  * MNEStatusWidget: Real-time monitoring with performance metrics and optimization tips
  * ChannelSelectionDialog: Reusable channel selection with optimization indicators

Controller Architecture Features:

State Management:
- Maintains separate task tracking for conversion, visualization, and real-time operations
- Preserves channel selections across different operational modes
- Tracks filter states and synchronizes with processing panel settings
- Manages UI state transitions with proper cleanup and resource management

Real-time Processing Capabilities:
- Dynamic parameter updates without session restart requirements
- Live performance monitoring with CPU usage warnings and optimization suggestions
- Adaptive timeout management for high-frequency update intervals
- Channel selection optimization with memory usage reduction indicators
- Seamless integration with data access service for continuous data streams

Filter Integration:
- Automatic detection of active processing panel filters
- Real-time synchronization of filter settings between panels
- Optional filter application during MNE conversion and real-time processing
- Dynamic status updates showing active filter configurations
- Performance impact monitoring when filters are applied

Performance Optimization Features:
- Intelligent channel selection reducing computational load and memory usage
- Real-time optimization indicators showing processing efficiency gains
- Performance warnings for CPU-intensive operations and parameter combinations
- Memory usage tracking and optimization suggestions for large channel counts
- Adaptive processing based on system capabilities and update frequency requirements

Task Coordination:
- Asynchronous task management preventing UI blocking during intensive operations
- Comprehensive callback handling for conversion, visualization, and real-time updates
- Task cancellation support with proper resource cleanup and state restoration
- Status monitoring with detailed progress tracking and error reporting
- Timeout detection and recovery mechanisms for robust operation

Error Handling and Recovery:
- Comprehensive exception handling with detailed error reporting
- Graceful degradation when MNE package is unavailable
- Automatic recovery from failed operations with state preservation
- User-friendly error messages with actionable troubleshooting guidance
- Logging integration for debugging and performance analysis

Integration Capabilities:
- Seamless coordination with MNE services for advanced neurophysiological analysis
- Data access service integration for real-time data stream management
- Visualization service coordination for filter state synchronization
- Event system integration for application-wide state updates
- Service dependency injection for testing and modularity

User Experience Enhancements:
- Intuitive mode switching with automatic UI reconfiguration
- Real-time feedback with emoji indicators and visual progress cues
- Performance optimization suggestions and efficiency indicators
- Comprehensive status logging with timestamp tracking
- Context-sensitive help integration and parameter guidance

Technical Implementation:
- Qt signal/slot architecture for loose coupling and event-driven design
- Thread-safe operations with proper UI thread marshalling
- Resource lifecycle management with comprehensive cleanup procedures
- Memory-efficient operations with automatic buffer management
- Scalable architecture supporting multiple concurrent processing sessions

The MNE UI package provides a production-ready, user-friendly interface for
advanced EEG analysis, enabling researchers to leverage the full power of
MNE-Python through an intuitive Qt-based interface with comprehensive
real-time processing support and performance optimization features.
"""

from . import widgets
from .mne_panel_controller import MNEPanelController

__all__ = ["MNEPanelController", "widgets"]
