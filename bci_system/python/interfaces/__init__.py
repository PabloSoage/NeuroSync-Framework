"""
Interface definitions for the BCI system.
"""

from .module_interface import IRecordingModule, IEEGModule, IInputModule

__all__ = ['IRecordingModule', 'IEEGModule', 'IInputModule']
