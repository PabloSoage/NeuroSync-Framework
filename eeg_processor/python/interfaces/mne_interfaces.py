from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List, Tuple

import numpy as np


class MNEConverterInterface(ABC):
    """Interface for MNE data conversion operations."""

    @abstractmethod
    def convert_to_mne_async(
        self,
        data: np.ndarray,
        metadata: Dict[str, Any],
        duration_seconds: int,
        convert_to_v: bool = True,
        selected_channels: Optional[List[int]] = None,
        callback: Optional[Callable] = None,
    ) -> str:
        """Convert BrainFlow data to MNE format asynchronously."""
        pass

    @abstractmethod
    def get_conversion_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a conversion task."""
        pass

    @abstractmethod
    def cancel_conversion(self, task_id: str) -> bool:
        """Cancel a conversion task."""
        pass


class MNEVisualizerInterface(ABC):
    """Interface for MNE visualization operations."""

    @abstractmethod
    def create_visualization_async(
        self,
        mne_data: Dict[str, Any],
        plot_type: str,
        freq_min: int = 1,
        freq_max: int = 50,
        bg_color: str = "#2b2b2b",
        show_individual_channels: bool = True,
        selected_channels_for_display: Optional[List[int]] = None,
        topomap_freq_range: Optional[Tuple[int, int]] = None,
        callback: Optional[Callable] = None,
    ) -> str:
        """Create MNE visualization asynchronously."""
        pass

    @abstractmethod
    def get_visualization_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a visualization task."""
        pass

    @abstractmethod
    def cancel_visualization(self, task_id: str) -> bool:
        """Cancel a visualization task."""
        pass


class MNEResultStorageInterface(ABC):
    """Interface for MNE result storage operations."""

    @abstractmethod
    def store_result(self, task_id: str, result: Dict[str, Any]) -> None:
        """Store a task result."""
        pass

    @abstractmethod
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a stored result."""
        pass

    @abstractmethod
    def remove_result(self, task_id: str) -> bool:
        """Remove a stored result."""
        pass

    @abstractmethod
    def clear_all_results(self) -> None:
        """Clear all stored results."""
        pass


class MNEProcessManagerInterface(ABC):
    """Interface for managing multiprocessing operations."""

    @abstractmethod
    def start_service(self) -> None:
        """Start the process pool."""
        pass

    @abstractmethod
    def stop_service(self) -> None:
        """Stop the process pool and cleanup."""
        pass

    @abstractmethod
    def submit_task(
        self, worker_func: Callable, *args, task_id: str = None, **kwargs
    ) -> str:
        """Submit a task to the process pool with optional task ID."""
        pass

    @abstractmethod
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task."""
        pass

    @abstractmethod
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the service is available."""
        pass


class MNERealtimeInterface(ABC):
    """Interface for MNE real-time processing operations."""

    @abstractmethod
    def start_realtime_processing(
        self,
        update_interval_seconds: float = 2.0,
        plot_type: str = "PSD",
        duration_seconds: int = 10,
        convert_to_v: bool = True,
        selected_channels: Optional[List[int]] = None,
        visualization_params: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable] = None,
    ) -> str:
        """Start real-time MNE processing."""
        pass

    @abstractmethod
    def stop_realtime_processing(self, session_id: str) -> bool:
        """Stop real-time processing session."""
        pass

    @abstractmethod
    def update_realtime_params(
        self, 
        session_id: str, 
        params: Dict[str, Any]
    ) -> bool:
        """Update real-time processing parameters."""
        pass

    @abstractmethod
    def get_realtime_status(self, session_id: str) -> Dict[str, Any]:
        """Get real-time processing status."""
        pass

    @abstractmethod
    def is_realtime_active(self, session_id: str) -> bool:
        """Check if real-time processing is active."""
        pass
