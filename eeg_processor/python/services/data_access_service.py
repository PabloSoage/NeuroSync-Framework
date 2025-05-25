from typing import Dict, List, Any, Tuple, Callable
import numpy as np
import threading
import logging


class DataAccessService:
    """
    Service providing real-time access to EEG data stream.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = DataAccessService()
            return cls._instance
    
    def __init__(self):
        """Initialize the data access service."""
        self._data_lock = threading.Lock()
        self._current_data = np.array([])
        self._current_timestamps = []
        self._metadata = {}
        self._callbacks = {}
        self._callback_counter = 0
        
        # Try to get reference to collector
        self._collector_ref = None
        self._init_collector_reference()
        
        logging.info("Data access service initialized")

    def _init_collector_reference(self):
        """Initialize reference to the collector service."""
        try:
            from .collector_service import CollectorService
            self._collector_ref = CollectorService()
        except Exception as e:
            logging.debug(f"Could not initialize collector reference: {e}")
    
    def update_data(self, data: np.ndarray, timestamps: List[int]) -> None:
        """
        Update the current data and timestamps.
        
        Args:
            data: New data array
            timestamps: Corresponding timestamps
        """
        with self._data_lock:
            self._current_data = data.copy() if data.size > 0 else np.array([])
            self._current_timestamps = timestamps.copy()
            
        # Notify callbacks
        self._notify_callbacks(data, timestamps)
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Update the metadata.
        
        Args:
            metadata: New metadata dictionary
        """
        with self._data_lock:
            self._metadata.update(metadata)
            
        # Update from collector if available
        if self._collector_ref:
            self._update_metadata_from_collector(metadata)
    
    def get_current_data(self) -> Tuple[np.ndarray, List[int]]:
        """
        Get the current data and timestamps.
        
        Returns:
            Tuple of (data, timestamps)
        """
        with self._data_lock:
            return self._current_data.copy(), self._current_timestamps.copy()
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get the current metadata.
        
        Returns:
            Metadata dictionary
        """
        with self._data_lock:
            return self._metadata.copy()
    
    def _update_metadata_from_collector(self, metadata: Dict[str, Any]) -> None:
        """Update metadata from collector information."""
        try:
            if self._collector_ref and self._collector_ref.is_connected():
                # Get board info and update metadata
                board_info = self._collector_ref.get_board_info()
                if board_info:
                    metadata.update(board_info)
        except Exception as e:
            logging.debug(f"Error updating metadata from collector: {e}")
    
    def _get_active_collector(self):
        """Get the active collector instance."""
        if self._collector_ref:
            return self._collector_ref
        return None
    
    def get_channel_data(self, channel_index: int) -> Tuple[np.ndarray, List[int]]:
        """
        Get data for a specific channel.
        
        Args:
            channel_index: Index of the channel
            
        Returns:
            Tuple of (channel_data, timestamps)
        """
        with self._data_lock:
            if self._current_data.size > 0 and channel_index < self._current_data.shape[0]:
                return self._current_data[channel_index].copy(), self._current_timestamps.copy()
            return np.array([]), []
    
    def get_channel_names(self) -> List[str]:
        """
        Get names of all channels.
        
        Returns:
            List of channel names
        """
        with self._data_lock:
            return self._metadata.get('channel_names', [])
    
    def get_sampling_rate(self) -> float:
        """
        Get the sampling rate.
        
        Returns:
            Sampling rate in Hz
        """
        with self._data_lock:
            return self._metadata.get('sampling_rate', 0.0)
    
    def is_streaming(self) -> bool:
        """
        Check if streaming is active.
        
        Returns:
            True if streaming, False otherwise
        """
        with self._data_lock:
            return self._metadata.get('streaming', False)
    
    def register_callback(self, callback: Callable[[np.ndarray, List[int]], None]) -> int:
        """
        Register a callback for data updates.
        
        Args:
            callback: Function to call when data updates
            
        Returns:
            Callback ID for later removal
        """
        with self._data_lock:
            callback_id = self._callback_counter
            self._callbacks[callback_id] = callback
            self._callback_counter += 1
            return callback_id
    
    def unregister_callback(self, callback_id: int) -> bool:
        """
        Unregister a callback.
        
        Args:
            callback_id: ID of callback to remove
            
        Returns:
            True if successful, False otherwise
        """
        with self._data_lock:
            if callback_id in self._callbacks:
                del self._callbacks[callback_id]
                return True
            return False
    
    def _notify_callbacks(self, data: np.ndarray, timestamps: List[int]) -> None:
        """Notify all registered callbacks of data update."""
        # Get callbacks outside the lock
        with self._data_lock:
            callbacks = list(self._callbacks.values())
        
        # Call callbacks outside the lock
        for callback in callbacks:
            try:
                callback(data, timestamps)
            except Exception as e:
                logging.error(f"Error in data callback: {e}")
