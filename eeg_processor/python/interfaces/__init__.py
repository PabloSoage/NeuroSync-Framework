"""
Interfaces Package for EEG Data Collection and Processing.

This package contains abstract base classes that define the contracts for various
components of the EEG processing system. These interfaces ensure modularity,
testability, and extensibility across the entire application.

Core Collector Interfaces:
- CollectorInterface: Base interface for all data collectors with core operations
  * prepare_session, start_stream, stop_stream, release_session
  * get_data, get_device_info methods
- MarkerInterface: Interface for event marker insertion during data collection
- ConfigurableCollectorInterface: Interface for device configuration operations

Board Management Interfaces:
- BoardInterface: Interface for device board configuration and management
  * Board discovery, grouping, and requirement determination
  * Parameter creation and board description functionality

Recording Interfaces:
- DataStorageInterface: Interface for data storage operations
  * save_data method for persisting collected data
- ContinuousRecordingInterface: Interface for continuous recording operations
  * start_continuous_recording, stop_continuous_recording methods

MNE Processing Interfaces:
- MNEConverterInterface: Interface for MNE data conversion operations
  * Asynchronous conversion from BrainFlow to MNE format
  * Task status monitoring and cancellation capabilities
- MNEVisualizerInterface: Interface for MNE visualization operations
  * Asynchronous plot generation with various visualization types
  * Task management for visualization operations
- MNEResultStorageInterface: Interface for MNE result storage operations
  * Store, retrieve, and manage processing results
- MNEProcessManagerInterface: Interface for multiprocessing operations
  * Process pool management and task submission
- MNERealtimeInterface: Interface for real-time MNE processing
  * Real-time data processing with configurable parameters
  * Session management for continuous processing

These interfaces provide the foundation for a flexible and extensible EEG processing
architecture, allowing for easy testing, mocking, and implementation swapping.
"""

from .board_interface import BoardInterface
from .collector_interface import (
    CollectorInterface,
    MarkerInterface,
    ConfigurableCollectorInterface,
)
from .mne_interfaces import (
    MNEConverterInterface,
    MNEVisualizerInterface,
    MNEResultStorageInterface,
    MNEProcessManagerInterface,
    MNERealtimeInterface,
)
from .recording_interface import (
    DataStorageInterface,
    ContinuousRecordingInterface,
)

__all__ = [
    # Core collector interfaces
    "CollectorInterface",
    "MarkerInterface",
    "ConfigurableCollectorInterface",
    # Board management
    "BoardInterface",
    # Recording interfaces
    "DataStorageInterface",
    "ContinuousRecordingInterface",
    # MNE processing interfaces
    "MNEConverterInterface",
    "MNEVisualizerInterface",
    "MNEResultStorageInterface",
    "MNEProcessManagerInterface",
    "MNERealtimeInterface",
]
