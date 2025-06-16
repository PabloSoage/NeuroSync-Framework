import logging
import threading
from typing import Dict, Any, Optional, Callable, List, Tuple

from ..interfaces.mne_interfaces import (
    MNEConverterInterface, 
    MNEVisualizerInterface, 
    MNEProcessManagerInterface, 
    MNEResultStorageInterface
)
from .mne.mne_converter_service import MNEConverterService
from .mne.mne_visualizer_service import MNEVisualizerService
from .mne.mne_process_manager import MNEProcessManager
from .mne.mne_result_storage import MNEResultStorage
from .data_access_service import DataAccessService

# Check if MNE is available
try:
    import mne
    MNE_AVAILABLE = True
except ImportError:
    MNE_AVAILABLE = False


class MNEService:
    """
    Facade service for MNE integration operations.
    
    This class provides a unified interface for MNE operations while
    coordinating between specialized services (converter, visualizer, etc.).
    Maintains backward compatibility with the original MNE service API.
    """
    
    _instance: Optional["MNEService"] = None
    _lock = threading.RLock()
    
    @classmethod
    def get_instance(cls) -> "MNEService":
        """Get the singleton instance of the MNE service."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = MNEService()
            return cls._instance
    
    def __init__(self) -> None:
        """Initialize the MNE service facade."""
        if MNEService._instance is not None:
            raise RuntimeError("MNEService is a singleton. Use get_instance()")
        
        # Initialize core services
        self._process_manager = MNEProcessManager()
        self._result_storage = MNEResultStorage()
        
        # Initialize specialized services
        self._converter_service = MNEConverterService(
            self._process_manager, 
            self._result_storage
        )
        self._visualizer_service = MNEVisualizerService(
            self._process_manager, 
            self._result_storage
        )
        
        # Data access service
        self._data_access_service = DataAccessService.get_instance()
        
        logging.info("MNE service facade initialized")
    
    def is_available(self) -> bool:
        """Check if MNE is available."""
        return MNE_AVAILABLE
    
    def start_service(self) -> None:
        """Start the MNE service and underlying components."""
        if not MNE_AVAILABLE:
            logging.warning("MNE not available, service not started")
            return
        
        self._process_manager.start_service()
        logging.info("MNE service started")
    
    def stop_service(self) -> None:
        """Stop the MNE service and cleanup resources."""
        self._process_manager.stop_service()
        self._result_storage.clear_all_results()
        logging.info("MNE service stopped")
    
    def cleanup(self) -> None:
        """Cleanup resources when shutting down."""
        self.stop_service()
    
    # Conversion API (delegates to converter service)
    def convert_to_mne_async(
        self,
        duration_seconds: int,
        convert_to_v: bool = True,
        selected_channels: Optional[List[int]] = None,
        callback: Optional[Callable] = None
    ) -> str:
        """
        Convert BrainFlow data to MNE format asynchronously.
        
        Args:
            duration_seconds: Duration of data to convert
            convert_to_v: Whether to convert units to volts
            selected_channels: List of channel indices to convert (None for all)
            callback: Optional callback function
            
        Returns:
            Task ID for tracking the conversion
        """
        # Get current data and metadata
        data, timestamps = self._data_access_service.get_current_data()
        metadata = self._data_access_service.get_metadata()
        
        return self._converter_service.convert_to_mne_async(
            data=data,
            metadata=metadata,
            duration_seconds=duration_seconds,
            convert_to_v=convert_to_v,
            selected_channels=selected_channels,
            callback=callback
        )
    
    def get_conversion_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a conversion task."""
        return self._converter_service.get_conversion_status(task_id)
    
    def cancel_conversion(self, task_id: str) -> bool:
        """Cancel a conversion task."""
        return self._converter_service.cancel_conversion(task_id)
    
    # Visualization API (delegates to visualizer service)
    def create_visualization_async(
        self,
        task_id: str,
        plot_type: str,
        freq_min: int = 1,
        freq_max: int = 50,
        bg_color: str = "#2b2b2b",
        show_individual_channels: bool = True,
        selected_channels_for_display: Optional[List[int]] = None,
        topomap_freq_range: Optional[Tuple[int, int]] = None,
        callback: Optional[Callable] = None
    ) -> str:
        """
        Create MNE visualization asynchronously.
        
        Args:
            task_id: Task ID of the conversion to visualize
            plot_type: Type of plot to create
            freq_min: Minimum frequency for analysis
            freq_max: Maximum frequency for analysis
            bg_color: Background color for the plot
            show_individual_channels: Whether to show individual channels
            selected_channels_for_display: Channels to display
            topomap_freq_range: Frequency range for topomaps
            callback: Optional callback function
            
        Returns:
            Task ID for tracking the visualization
        """
        # Get the MNE data from the conversion result
        mne_data = self._result_storage.get_result(task_id)
        if not mne_data:
            raise ValueError(f"No MNE data found for task ID: {task_id}")
        
        return self._visualizer_service.create_visualization_async(
            mne_data=mne_data,
            plot_type=plot_type,
            freq_min=freq_min,
            freq_max=freq_max,
            bg_color=bg_color,
            show_individual_channels=show_individual_channels,
            selected_channels_for_display=selected_channels_for_display,
            topomap_freq_range=topomap_freq_range,
            callback=callback
        )
    
    def get_visualization_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a visualization task."""
        return self._visualizer_service.get_visualization_status(task_id)
    
    def cancel_visualization(self, task_id: str) -> bool:
        """Cancel a visualization task."""
        return self._visualizer_service.cancel_visualization(task_id)
    
    # Generic task management API - maintain backward compatibility
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of any task (conversion or visualization).
        """
        # First check if it's a conversion task
        conversion_status = self._converter_service.get_conversion_status(task_id)
        if conversion_status.get("status") != "not_found":
            return conversion_status
        
        # Then check if it's a visualization task
        visualization_status = self._visualizer_service.get_visualization_status(task_id)
        if visualization_status.get("status") != "not_found":
            return visualization_status
        
        # Check in process manager directly
        process_status = self._process_manager.get_task_status(task_id)
        if process_status.get("status") != "not_found":
            return process_status
        
        # Not found in any service
        return {
            "status": "not_found",
            "ready": False,
            "successful": False
        }
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel any task (conversion or visualization).
        """
        # Try to cancel as conversion task first
        if self._converter_service.cancel_conversion(task_id):
            return True
        
        # Try to cancel as visualization task
        if self._visualizer_service.cancel_visualization(task_id):
            return True
        
        # Try to cancel directly in process manager
        if self._process_manager.cancel_task(task_id):
            return True
        
        return False
    
    # Result management API
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a stored result for a task."""
        return self._result_storage.get_result(task_id)
    
    def remove_result(self, task_id: str) -> bool:
        """Remove a stored result."""
        return self._result_storage.remove_result(task_id)
    
    def clear_all_results(self) -> None:
        """Clear all stored results."""
        self._result_storage.clear_all_results()
    
    # Service status API
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get overall service status.
        """
        return {
            "mne_available": self.is_available(),
            "process_manager_available": self._process_manager.is_available(),
            "active_results": len(self._result_storage.get_all_task_ids()),
            "services": {
                "converter": "available",
                "visualizer": "available",
                "process_manager": "available" if self._process_manager.is_available() else "unavailable",
                "result_storage": "available"
            }
        }
    
    # Backward compatibility methods for existing UI code
    def convert_to_mne(
        self,
        data: Any,
        metadata: Dict[str, Any],
        duration_seconds: int,
        convert_to_v: bool = True,
        selected_channels: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Legacy synchronous conversion method for backward compatibility.
        Note: This is deprecated, use convert_to_mne_async instead.
        """
        logging.warning("convert_to_mne is deprecated, use convert_to_mne_async instead")
        
        # For backward compatibility, we'll start an async task
        task_id = self._converter_service.convert_to_mne_async(
            data=data,
            metadata=metadata,
            duration_seconds=duration_seconds,
            convert_to_v=convert_to_v,
            selected_channels=selected_channels
        )
        
        # Return task information instead of blocking
        return {
            "success": True,
            "task_id": task_id,
            "message": "Conversion started asynchronously"
        }
    
    # Access to underlying services for advanced use cases
    @property
    def converter_service(self) -> MNEConverterInterface:
        """Get the converter service for advanced operations."""
        return self._converter_service
    
    @property
    def visualizer_service(self) -> MNEVisualizerInterface:
        """Get the visualizer service for advanced operations."""
        return self._visualizer_service
    
    @property
    def process_manager(self) -> MNEProcessManagerInterface:
        """Get the process manager for advanced operations."""
        return self._process_manager
    
    @property
    def result_storage(self) -> MNEResultStorageInterface:
        """Get the result storage for advanced operations."""
        return self._result_storage
