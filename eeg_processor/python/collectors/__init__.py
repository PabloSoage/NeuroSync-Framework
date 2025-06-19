"""
EEG Collectors Package.

This package provides data collection interfaces and implementations for EEG and biosignal
devices using the BrainFlow library. It includes:

- EEGCollector: Main collector implementation with multiple interface support
  * Implements CollectorInterface for basic data collection operations
  * Implements MarkerInterface for event marker insertion during recording
  * Implements ConfigurableCollectorInterface for device configuration
  * Supports multiple BrainFlow presets (DEFAULT, AUXILIARY, ANCILLARY)
  * Handles various EEG devices including OpenBCI, Muse, Neurosity, g.tec, ANT Neuro, and more
  * Provides automatic channel detection and board information management
  * Supports streaming boards with master board configuration

- BrainFlowBoardConfiguration: Board configuration and management utilities
  * Provides comprehensive board information and requirements
  * Handles parameter validation and BrainFlowInputParams creation
  * Groups boards by manufacturer and type for easier selection
  * Manages preset information and board descriptions
  * Determines required vs optional parameters for each board type

- BoardConfiguration: Static wrapper for board configuration methods
  * Backward compatibility layer for existing code
  * Provides static methods that delegate to BrainFlowBoardConfiguration
  * Maintains API compatibility while allowing future enhancements

The collectors support various features including:
- Continuous data streaming with configurable buffer sizes
- Real-time marker insertion for event-related experiments
- Multi-preset data collection (EEG, auxiliary sensors, ancillary data)
- Automatic device detection and configuration
- Comprehensive error handling and logging
- Data export and storage capabilities
"""

from .board_configuration import BrainFlowBoardConfiguration, BoardConfiguration
from .eeg_collector import EEGCollector

__all__ = ["EEGCollector", "BrainFlowBoardConfiguration", "BoardConfiguration"]
