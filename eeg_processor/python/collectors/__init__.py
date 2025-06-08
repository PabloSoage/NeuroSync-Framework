"""
EEG Collectors Package.

This package provides data collection interfaces and implementations for EEG and biosignal
devices using the BrainFlow library. It includes:

- BrainFlowCollector: Main collector implementation with multiple interface support
- EEGCollector: Alias for BrainFlowCollector for backward compatibility
- BrainFlowBoardConfiguration: Board configuration and management utilities
- BoardConfiguration: Static wrapper for board configuration methods

The collectors support various features including continuous recording, marker insertion,
data storage, and device configuration for a wide range of EEG devices.
"""

from .board_configuration import BrainFlowBoardConfiguration, BoardConfiguration
from .eeg_collector import EEGCollector, BrainFlowCollector

__all__ = ["EEGCollector"]
