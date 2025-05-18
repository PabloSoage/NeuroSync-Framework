import logging
import threading
import time
from typing import Dict, List, Any, Tuple, Callable

import numpy as np


class DataAccessService:
    """
    Service providing real-time access to EEG data stream.
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
        
        # Reference to collector service for direct access when needed
        self._collector_service = None
        
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
        
        # Initialize collector reference (will be set properly when collector starts)
        self._init_collector_reference()
        
        logging.info("Data access service initialized")
    
    def _init_collector_reference(self):
        """Initialize reference to collector service (if available)."""
        try:
            from .collector_service import CollectorService
            self._collector_service = CollectorService()
            logging.info("Connected to collector service")
        except Exception as e:
            logging.debug(f"Could not connect to collector service: {e}")
    
    def update_data(self, data: np.ndarray, timestamps: List[int]) -> None:
        """Update the current data buffer."""
        with self._data_lock:
            self._current_data = data
            self._timestamps = timestamps
            
            # Update last update timestamp
            with self._metadata_lock:
                self._metadata["last_update"] = time.time()
        
        # Notify registered callbacks
        self._notify_callbacks(data, timestamps)
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update stream metadata."""
        with self._metadata_lock:
            self._metadata.update(metadata)
    
    def get_current_data(self) -> Tuple[np.ndarray, List[int]]:
        """Get the current data and timestamps."""
        with self._data_lock:
            return self._current_data.copy(), self._timestamps.copy()
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get the current stream metadata."""
        with self._metadata_lock:
            metadata = self._metadata.copy()
            
            # If we have a collector service and metadata is missing critical info, try to get it directly
            if self._collector_service and (metadata.get("sampling_rate", 0) == 0 or not metadata.get("channel_names")):
                self._update_metadata_from_collector(metadata)
                
            return metadata
    
    def _update_metadata_from_collector(self, metadata: Dict[str, Any]) -> None:
        """Update metadata from collector if available."""
        try:
            # Get active collector
            collector = self._get_active_collector()
            if not collector:
                return
                
            # Update sampling rate if missing
            if metadata.get("sampling_rate", 0) == 0 and hasattr(collector, "sampling_rate"):
                metadata["sampling_rate"] = collector.sampling_rate
                
            # Update channel names if missing
            if not metadata.get("channel_names") and hasattr(collector, "eeg_names"):
                metadata["channel_names"] = collector.eeg_names
                
            # Update EEG channels if missing
            if not metadata.get("eeg_channels") and hasattr(collector, "eeg_channels"):
                metadata["eeg_channels"] = collector.eeg_channels
                
            # Update board info if missing
            if metadata.get("board_id", -1) == -1 and hasattr(collector, "board_id"):
                metadata["board_id"] = collector.board_id
                
            # Update board name if missing
            if not metadata.get("board_name") and hasattr(collector, "device_name"):
                metadata["board_name"] = collector.device_name
                
            # Update preset if missing
            if not metadata.get("preset") and hasattr(collector, "preset"):
                metadata["preset"] = collector.preset
                
            # Update streaming status
            if hasattr(collector, "is_streaming"):
                metadata["streaming"] = collector.is_streaming
                
            # Store the entire board_info for convenience if available
            if (hasattr(collector, "get_device_info") or hasattr(collector, "get_board_info")):
                try:
                    if hasattr(collector, "get_device_info"):
                        metadata["board_info"] = collector.get_device_info()
                    elif hasattr(collector, "get_board_info"):
                        metadata["board_info"] = collector.get_board_info()
                except Exception as e:
                    logging.debug(f"Error getting board info: {e}")
        except Exception as e:
            logging.debug(f"Error updating metadata from collector: {e}")
    
    def _get_active_collector(self):
        """Get the active collector from collector service."""
        if not self._collector_service:
            return None
            
        try:
            # Different possible attribute names in collector service
            if hasattr(self._collector_service, 'collector'):
                return self._collector_service.collector
            elif hasattr(self._collector_service, 'active_collector'):
                return self._collector_service.active_collector
            
            # Try to get from collectors dict
            if hasattr(self._collector_service, '_collectors'):
                collectors = self._collector_service._collectors
                active_id = getattr(self._collector_service, '_active_collector_id', None)
                if active_id and active_id in collectors:
                    return collectors[active_id]
        except Exception as e:
            logging.debug(f"Error getting active collector: {e}")
            
        return None
    
    def get_channel_data(self, channel_index: int) -> Tuple[np.ndarray, List[int]]:
        """Get data for a specific channel."""
        with self._data_lock:
            if self._current_data.size == 0 or channel_index >= self._current_data.shape[0]:
                return np.array([]), []
                
            return self._current_data[channel_index].copy(), self._timestamps.copy()
    
    def get_channel_names(self) -> List[str]:
        """Get names of all channels."""
        with self._metadata_lock:
            names = self._metadata.get("channel_names", []).copy()
            
            # If names are empty, try to get from collector
            if not names:
                collector = self._get_active_collector()
                if collector and hasattr(collector, "eeg_names"):
                    names = collector.eeg_names
                
                # If still empty, try to generate generic names based on channels
                if not names:
                    eeg_channels = self._metadata.get("eeg_channels", [])
                    if eeg_channels:
                        names = [f"CH{i+1}" for i in range(len(eeg_channels))]
            
            return names
    
    def get_sampling_rate(self) -> float:
        """Get the sampling rate."""
        with self._metadata_lock:
            rate = self._metadata.get("sampling_rate", 0)
            
            # If rate is 0, try to get directly from collector
            if rate == 0:
                collector = self._get_active_collector()
                if collector and hasattr(collector, "sampling_rate"):
                    rate = collector.sampling_rate
                    
                    # Update metadata for future calls
                    self._metadata["sampling_rate"] = rate
            
            return rate
    
    def is_streaming(self) -> bool:
        """Check if streaming is active."""
        with self._metadata_lock:
            streaming = self._metadata.get("streaming", False)
            
            # If not streaming according to metadata, check directly
            if not streaming:
                collector = self._get_active_collector()
                if collector and hasattr(collector, "is_streaming"):
                    streaming = collector.is_streaming
                    
                    # Update metadata
                    self._metadata["streaming"] = streaming
            
            return streaming
    
    def register_callback(self, callback: Callable[[np.ndarray, List[int]], None]) -> int:
        """Register a callback function to be called when new data arrives."""
        with self._callback_lock:
            callback_id = len(self._callbacks)
            self._callbacks.append(callback)
            return callback_id
    
    def unregister_callback(self, callback_id: int) -> bool:
        """Unregister a previously registered callback."""
        with self._callback_lock:
            if 0 <= callback_id < len(self._callbacks):
                self._callbacks[callback_id] = None
                return True
            return False
    
    def _notify_callbacks(self, data: np.ndarray, timestamps: List[int]) -> None:
        """Notify all registered callbacks of new data."""
        with self._callback_lock:
            for callback in self._callbacks:
                if callback is not None:
                    try:
                        callback(data, timestamps)
                    except Exception as e:
                        logging.error(f"Error in data access callback: {e}")
