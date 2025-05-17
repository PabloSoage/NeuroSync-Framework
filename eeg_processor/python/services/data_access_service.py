import logging
import threading
import time
from typing import Dict, List, Any, Tuple, Callable

import numpy as np


class DataAccessService:
    """
    Service providing real-time access to EEG data stream.
    
    This service allows other components to access the current EEG data
    and metadata without introducing delays in the streaming process.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the service."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = DataAccessService()
            return cls._instance
    
    def __init__(self):
        """Initialize the data access service."""
        self._data_lock = threading.Lock()
        self._metadata_lock = threading.Lock()
        
        # Current data buffer
        self._current_data = np.array([])
        self._timestamps = []
        
        # Board and stream metadata
        self._metadata = {
            "sampling_rate": 0,
            "eeg_channels": [],
            "channel_names": [],
            "num_channels": 0,
            "board_id": -1,
            "board_name": "",
            "streaming": False,
            "last_update": 0
        }
        
        # Registered callbacks for data updates
        self._callbacks = []
        self._callback_lock = threading.Lock()
        
        logging.info("Data access service initialized")
    
    def update_data(self, data: np.ndarray, timestamps: List[int]) -> None:
        """
        Update the current data buffer.
        
        Args:
            data: New data array
            timestamps: Associated timestamps
        """
        with self._data_lock:
            self._current_data = data
            self._timestamps = timestamps
            
            # Update last update timestamp
            self._metadata["last_update"] = time.time()
        
        # Notify registered callbacks
        self._notify_callbacks(data, timestamps)
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Update stream metadata.
        
        Args:
            metadata: Dictionary with metadata values
        """
        with self._metadata_lock:
            self._metadata.update(metadata)
    
    def get_current_data(self) -> Tuple[np.ndarray, List[int]]:
        """
        Get the current data and timestamps.
        
        Returns:
            Tuple of (data_array, timestamps)
        """
        with self._data_lock:
            return self._current_data.copy(), self._timestamps.copy()
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get the current stream metadata.
        
        Returns:
            Dictionary with metadata
        """
        with self._metadata_lock:
            return self._metadata.copy()
    
    def get_channel_data(self, channel_index: int) -> Tuple[np.ndarray, List[int]]:
        """
        Get data for a specific channel.
        
        Args:
            channel_index: Index of the channel to get
            
        Returns:
            Tuple of (channel_data, timestamps)
        """
        with self._data_lock:
            if self._current_data.size == 0 or channel_index >= self._current_data.shape[0]:
                return np.array([]), []
                
            return self._current_data[channel_index].copy(), self._timestamps.copy()
    
    def get_channel_names(self) -> List[str]:
        """
        Get names of all channels.
        
        Returns:
            List of channel names
        """
        with self._metadata_lock:
            return self._metadata.get("channel_names", []).copy()
    
    def get_sampling_rate(self) -> float:
        """
        Get the sampling rate.
        
        Returns:
            Sampling rate in Hz
        """
        with self._metadata_lock:
            return self._metadata.get("sampling_rate", 0)
    
    def is_streaming(self) -> bool:
        """
        Check if streaming is active.
        
        Returns:
            True if streaming, False otherwise
        """
        with self._metadata_lock:
            return self._metadata.get("streaming", False)
    
    def register_callback(self, callback: Callable[[np.ndarray, List[int]], None]) -> int:
        """
        Register a callback function to be called when new data arrives.
        
        Args:
            callback: Function to call with (data, timestamps)
            
        Returns:
            Callback ID for later unregistering
        """
        with self._callback_lock:
            callback_id = len(self._callbacks)
            self._callbacks.append(callback)
            return callback_id
    
    def unregister_callback(self, callback_id: int) -> bool:
        """
        Unregister a previously registered callback.
        
        Args:
            callback_id: ID of the callback to remove
            
        Returns:
            True if successful, False otherwise
        """
        with self._callback_lock:
            if 0 <= callback_id < len(self._callbacks):
                self._callbacks[callback_id] = None
                return True
            return False
    
    def _notify_callbacks(self, data: np.ndarray, timestamps: List[int]) -> None:
        """
        Notify all registered callbacks of new data.
        
        Args:
            data: New data array
            timestamps: Associated timestamps
        """
        with self._callback_lock:
            for callback in self._callbacks:
                if callback is not None:
                    try:
                        callback(data, timestamps)
                    except Exception as e:
                        logging.error(f"Error in data access callback: {e}")
