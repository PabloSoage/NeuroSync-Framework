"""
Adapters for BCI system modules.
"""

from .eeg_adapter import EEGModuleAdapter
from .input_adapter import InputModuleAdapter

__all__ = ['EEGModuleAdapter', 'InputModuleAdapter']
