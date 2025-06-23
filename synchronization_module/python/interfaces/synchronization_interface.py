"""
Interfaces for synchronization operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
import numpy as np


class SynchronizationInterface(ABC):
    """Interface for synchronization operations."""

    @abstractmethod
    def start_synchronization(
        self, precision_ms: float = 1.0, callback: Optional[Callable] = None
    ) -> bool:
        """Start synchronization with specified precision."""
        pass

    @abstractmethod
    def stop_synchronization(self) -> bool:
        """Stop synchronization."""
        pass

    @abstractmethod
    def is_synchronizing(self) -> bool:
        """Check if synchronization is active."""
        pass

    @abstractmethod
    def get_synchronized_data(self, duration_seconds: float) -> Dict[str, Any]:
        """Get synchronized data for specified duration."""
        pass


class LSLStreamInterface(ABC):
    """Interface for LSL stream management."""

    @abstractmethod
    def create_stream(
        self, name: str, stream_type: str, channel_count: int, nominal_srate: float
    ) -> Any:
        """Create an LSL stream."""
        pass

    @abstractmethod
    def push_sample(self, stream: Any, sample: np.ndarray) -> None:
        """Push a sample to the stream."""
        pass

    @abstractmethod
    def resolve_streams(self, stream_type: str) -> List[Any]:
        """Resolve available streams of specified type."""
        pass
