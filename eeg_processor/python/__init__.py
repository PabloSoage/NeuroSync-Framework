"""
EEG Processor package for real-time EEG data collection, processing, and visualization.

This package provides a comprehensive framework for working with EEG data from various
hardware devices. It includes components for:
- Data collection from EEG devices via BrainFlow
- Signal processing and analysis
- Real-time visualization
- Data recording and export
- GUI interface for interactive control

The package is designed with a modular architecture that separates concerns into
collectors, processors, visualizers, services, and UI components.
"""

from .collectors import EEGCollector
from .eeg_processor_app import EEGProcessorApp
from .processors import SignalProcessor
from .visualizers import EEGVisualizer

__all__ = ["EEGProcessorApp", "EEGCollector", "SignalProcessor", "EEGVisualizer"]
