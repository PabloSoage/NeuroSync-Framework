"""
Core package for synchronization operations.

Contains core components for Lab Streaming Layer (LSL) management
and timing/synchronization precision control.
"""

from .lsl_manager import LSLManager
from .timing_manager import TimingManager

__all__ = [
    "LSLManager",
    "TimingManager",
]