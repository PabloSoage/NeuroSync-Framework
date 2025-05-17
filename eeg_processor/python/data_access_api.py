"""
API for accessing real-time EEG data streams.

This module provides a clean interface for accessing EEG data and metadata
in real-time with minimal overhead.
"""

from typing import Dict, List, Any, Tuple, Callable

import numpy as np

from .services.data_access_service import DataAccessService


class EEGDataAPI:
    """
    Main API for accessing EEG data.
    
    This class provides methods to access real-time EEG data and metadata.
    """
    
    @staticmethod
    def get_current_data() -> Tuple[np.ndarray, List[int]]:
        """
        Get the current EEG data and timestamps.
        
        Returns:
            Tuple of (data_array, timestamps)
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_current_data()
    
    @staticmethod
    def get_channel_data(channel_index: int) -> Tuple[np.ndarray, List[int]]:
        """
        Get data for a specific channel.
        
        Args:
            channel_index: Index of the channel to get
            
        Returns:
            Tuple of (channel_data, timestamps)
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_channel_data(channel_index)
    
    @staticmethod
    def get_channel_by_name(channel_name: str) -> Tuple[np.ndarray, List[int]]:
        """
        Get data for a channel by its name.
        
        Args:
            channel_name: Name of the channel to get
            
        Returns:
            Tuple of (channel_data, timestamps)
        """
        data_access = DataAccessService.get_instance()
        channel_names = data_access.get_channel_names()
        
        if channel_name in channel_names:
            channel_index = channel_names.index(channel_name)
            return data_access.get_channel_data(channel_index)
        
        return np.array([]), []
    
    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        """
        Get the current EEG stream metadata.
        
        Returns:
            Dictionary with metadata
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_metadata()
    
    @staticmethod
    def get_sampling_rate() -> float:
        """
        Get the sampling rate.
        
        Returns:
            Sampling rate in Hz
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_sampling_rate()
    
    @staticmethod
    def get_channel_names() -> List[str]:
        """
        Get names of all channels.
        
        Returns:
            List of channel names
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_channel_names()
    
    @staticmethod
    def is_streaming() -> bool:
        """
        Check if streaming is active.
        
        Returns:
            True if streaming, False otherwise
        """
        data_access = DataAccessService.get_instance()
        return data_access.is_streaming()
    
    @staticmethod
    def register_data_callback(callback: Callable[[np.ndarray, List[int]], None]) -> int:
        """
        Register a callback function to be called when new data arrives.
        
        Args:
            callback: Function to call with (data, timestamps)
            
        Returns:
            Callback ID for later unregistering
        """
        data_access = DataAccessService.get_instance()
        return data_access.register_callback(callback)
    
    @staticmethod
    def unregister_data_callback(callback_id: int) -> bool:
        """
        Unregister a previously registered callback.
        
        Args:
            callback_id: ID of the callback to remove
            
        Returns:
            True if successful, False otherwise
        """
        data_access = DataAccessService.get_instance()
        return data_access.unregister_callback(callback_id)
