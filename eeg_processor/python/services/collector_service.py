import logging
from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np
import threading
import time

from .data_access_service import DataAccessService
from ..collectors.board_configuration import BoardConfiguration
from ..collectors.eeg_collector import EEGCollector


class CollectorService:
    """
    Service for managing EEG data collection.
    
    This class provides an interface for connecting to EEG boards,
    streaming data, and managing the collector state.
    """
    
    def __init__(self):
        """Initialize the collector service."""
        self.collector = None
        self.is_streaming = False
        
        # Background data fetch thread
        self._data_thread = None
        self._stop_event = threading.Event()
    
    def connect_to_board(self, board_id: int, params: Dict[str, Any], preset: int) -> bool:
        """
        Connect to an EEG board.
        
        Args:
            board_id: ID of the board to connect to
            params: Dictionary of connection parameters
            preset: Data preset to use
            
        Returns:
            True if connection was successful, False otherwise
        """
        try:
            # Create input parameters from dictionary
            board_params = BoardConfiguration.create_input_params(board_id, params)
            
            # Create collector
            self.collector = EEGCollector(board_id, board_params, preset)
            self.collector.prepare_session()
            logging.info(f"Connected to board {board_id}")
            
            # Add this code after successful connection
            if self.collector:
                # Update metadata in DataAccessService
                data_access = DataAccessService.get_instance()
                
                # Update metadata with complete board info
                device_info = self.collector.get_device_info()
                
                # Update metadata with device info
                data_access.update_metadata({
                    "sampling_rate": device_info.get("sampling_rate", 0),
                    "eeg_channels": device_info.get("eeg_channels", []),
                    "channel_names": device_info.get("eeg_names", []),
                    "num_channels": len(device_info.get("eeg_channels", [])),
                    "board_id": device_info.get("board_id", -1),
                    "board_name": device_info.get("board_name", ""),
                    "streaming": False,
                    "board_info": device_info  # Store the complete info
                })
        
            return True
        except Exception as e:
            logging.error(f"Connection error: {e}")
            self.collector = None
            return False
    
    def disconnect_from_board(self) -> bool:
        """
        Disconnect from the current board.
        
        Returns:
            True if disconnection was successful, False otherwise
        """
        if not self.collector:
            return True
            
        try:
            if self.is_streaming:
                self.stop_stream()
                
            self.collector.release_session()
            self.collector = None
            logging.info("Disconnected from board")
            return True
        except Exception as e:
            logging.error(f"Disconnection error: {e}")
            return False
    
    def start_stream(self, buffer_size: int = 450000) -> bool:
        """
        Start streaming data from the board.
        
        Args:
            buffer_size: Size of the buffer for data
            
        Returns:
            True if stream started successfully, False otherwise
        """
        if not self.collector:
            return False
            
        try:
            self.collector.start_stream(buffer_size)
            self.is_streaming = True
            
            # Update streaming status in DataAccessService
            data_access = DataAccessService.get_instance()
            data_access.update_metadata({"streaming": True})
            
            # Start background data retrieval thread
            self._stop_event.clear()
            self._data_thread = threading.Thread(target=self._data_loop, daemon=True)
            self._data_thread.start()
            
            logging.info("Stream started")
            return True
        except Exception as e:
            logging.error(f"Stream start error: {e}")
            return False
    
    def stop_stream(self) -> bool:
        """
        Stop streaming data from the board.
        
        Returns:
            True if stream stopped successfully, False otherwise
        """
        if not self.collector or not self.is_streaming:
            return False
            
        try:
            self.collector.stop_stream()
            self.is_streaming = False
            
            # Update streaming status in DataAccessService
            data_access = DataAccessService.get_instance()
            data_access.update_metadata({"streaming": False})
            
            # Stop background data retrieval thread
            self._stop_event.set()
            if self._data_thread:
                self._data_thread.join()
            
            logging.info("Stream stopped")
            return True
        except Exception as e:
            logging.error(f"Stream stop error: {e}")
            return False
    
    def get_board_data(self, num_samples: Optional[int] = None) -> Tuple[np.ndarray, List[int]]:
        """
        Get collected data from the board.
        
        Args:
            num_samples: Number of samples to get, all data if None
            
        Returns:
            Tuple containing the data and timestamps in ms
        """
        if not self.collector or not self.is_streaming:
            return np.array([]), []
            
        try:
            data, timestamps = self.collector.get_data(num_samples)
            
            # Update the DataAccessService with the new data
            data_access = DataAccessService.get_instance()
            data_access.update_data(data, timestamps)
            
            return data, timestamps
        except Exception as e:
            logging.error(f"Data retrieval error: {e}")
            return np.array([]), []
    
    def get_board_info(self) -> Dict[str, Any]:
        """
        Get information about the connected board.
        
        Returns:
            Dictionary with board information
        """
        if not self.collector:
            return {}
            
        try:
            return self.collector.get_board_info()
        except Exception as e:
            logging.error(f"Board info retrieval error: {e}")
            return {}
    
    def insert_marker(self, marker_value: Union[int, float]) -> bool:
        """
        Insert a marker into the data stream.
        
        Args:
            marker_value: Value of the marker to insert
            
        Returns:
            True if marker was inserted successfully, False otherwise
        """
        if not self.collector or not self.is_streaming:
            return False
            
        try:
            self.collector.insert_marker(marker_value)
            return True
        except Exception as e:
            logging.error(f"Marker insertion error: {e}")
            return False
    
    def set_processed_data(self, data: np.ndarray) -> bool:
        """
        Set processed data after signal processing.
        
        Args:
            data: Processed data
            
        Returns:
            True if data was set successfully, False otherwise
        """
        if not self.collector:
            return False
            
        try:
            self.collector.set_processed_data(data)
            return True
        except Exception as e:
            logging.error(f"Setting processed data error: {e}")
            return False
    
    def add_streamer(self, streamer_params: str) -> bool:
        """
        Add a streamer to stream data.
        
        Args:
            streamer_params: Parameters for the streamer
            
        Returns:
            True if streamer was added successfully, False otherwise
        """
        if not self.collector:
            return False
            
        try:
            self.collector.add_streamer(streamer_params)
            return True
        except Exception as e:
            logging.error(f"Adding streamer error: {e}")
            return False
    
    def remove_streamer(self, streamer_params: str) -> bool:
        """
        Remove a streamer.
        
        Args:
            streamer_params: Parameters for the streamer to remove
            
        Returns:
            True if streamer was removed successfully, False otherwise
        """
        if not self.collector:
            return False
            
        try:
            self.collector.delete_streamer(streamer_params)
            return True
        except Exception as e:
            logging.error(f"Removing streamer error: {e}")
            return False
    
    def get_eeg_channels(self) -> List[int]:
        """
        Get the EEG channels from the current board.
        
        Returns:
            List of EEG channel indices
        """
        if not self.collector:
            return []
            
        try:
            return self.collector.get_eeg_channels()
        except Exception as e:
            logging.error(f"Getting EEG channels error: {e}")
            return []
    
    def get_channel_by_type(self, channel_type: str) -> List[int]:
        """
        Get channels of a specific type.
        
        Args:
            channel_type: Type of channels to get ('eeg', 'emg', etc.)
            
        Returns:
            List of channel indices
        """
        if not self.collector:
            return []
            
        try:
            return self.collector.get_channel_by_type(channel_type)
        except Exception as e:
            logging.error(f"Getting channels by type error: {e}")
            return []
    
    def get_sampling_rate(self) -> int:
        """
        Get the sampling rate of the current board.
        
        Returns:
            Sampling rate in Hz
        """
        if not self.collector:
            return 0
            
        try:
            return self.collector.sampling_rate
        except Exception as e:
            logging.error(f"Getting sampling rate error: {e}")
            return 0
    
    def config_device(self, config: str) -> str:
        """
        Send configuration to the device.
        
        Args:
            config: Configuration string to send
            
        Returns:
            Response from the device
        """
        if not self.collector:
            return ""
            
        try:
            return self.collector.config_device(config)
        except Exception as e:
            logging.error(f"Device configuration error: {e}")
            return ""
    
    def set_preset(self, preset: int) -> bool:
        """
        Change the current preset.
        
        Args:
            preset: New preset value
            
        Returns:
            True if preset was set successfully, False otherwise
        """
        if not self.collector:
            return False
            
        try:
            return self.collector.set_preset(preset)
        except Exception as e:
            logging.error(f"Setting preset error: {e}")
            return False
    
    def is_connected(self) -> bool:
        """
        Check if a board is connected.
        
        Returns:
            True if board is connected, False otherwise
        """
        return self.collector is not None
    
    def is_streaming_active(self) -> bool:
        """
        Check if the board is streaming data.
        
        Returns:
            True if board is streaming, False otherwise
        """
        return self.is_streaming
        
    def cleanup(self) -> None:
        """Clean up resources when closing the application."""
        # Ensure background thread is stopped
        self._stop_event.set()
    
    def _data_loop(self):
        """Background loop to fetch data and update DataAccessService."""
        data_access = DataAccessService.get_instance()
        # Determine sampling rate once
        sr = None
        while not self._stop_event.is_set() and self.collector and self.is_streaming:
            try:
                # Fetch available data
                data, timestamps = self.collector.get_data()
                if data.size > 0:
                    data_access.update_data(data, timestamps)
                    if sr is None:
                        md = data_access.get_metadata()
                        sr = md.get("sampling_rate", None)
                # Sleep for sample interval if known
                if sr and sr > 0:
                    time.sleep(1.0 / sr)
                else:
                    time.sleep(0.01)
            except Exception:
                break
