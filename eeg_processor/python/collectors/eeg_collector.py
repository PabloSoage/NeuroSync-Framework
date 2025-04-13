import logging
import time
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter

from ..interfaces.collector_interface import CollectorInterface


class EEGCollector(CollectorInterface):
    """
    Collector for EEG data using BrainFlow.
    
    This class handles the connection to EEG devices, data acquisition,
    and basic data management operations.
    """
    
    def __init__(self, board_id: int = BoardIds.SYNTHETIC_BOARD, params: Optional[BrainFlowInputParams] = None):
        """
        Initialize the EEG collector.
        
        Args:
            board_id: ID of the board to connect to (default: SYNTHETIC_BOARD)
            params: Parameters for board initialization
        """
        BoardShim.enable_dev_board_logger()
        
        if params is None:
            params = BrainFlowInputParams()
            
        self.params = params
        self.board_id = board_id
        self.board = BoardShim(self.board_id, self.params)
        self.is_streaming = False
        self.start_time = 0
        self.raw_data = None
        self.processed_data = None
        self.timestamps = []
        
        # Get board information
        self.sampling_rate = BoardShim.get_sampling_rate(self.board_id)
        self.eeg_channels = BoardShim.get_eeg_channels(self.board_id)
        self.timestamp_channel = BoardShim.get_timestamp_channel(self.board_id)
        self.marker_channel = BoardShim.get_marker_channel(self.board_id)
        
        logging.info(f"EEG Collector initialized with board_id: {self.board_id}")
        
    def prepare_session(self) -> None:
        """
        Prepare the session for data collection.
        """
        self.board.prepare_session()
        logging.info("EEG session prepared")
        
    def start_stream(self) -> None:
        """
        Start streaming EEG data.
        """
        if not self.is_streaming:
            self.board.start_stream()
            self.is_streaming = True
            self.start_time = int(round(time.time() * 1000))  # Current time in ms
            logging.info("EEG stream started")
        else:
            logging.warning("Stream already running")
            
    def stop_stream(self) -> None:
        """
        Stop streaming EEG data.
        """
        if self.is_streaming:
            self.board.stop_stream()
            self.is_streaming = False
            logging.info("EEG stream stopped")
        else:
            logging.warning("No stream to stop")
            
    def release_session(self) -> None:
        """
        Release resources after the session is finished.
        """
        if self.is_streaming:
            self.stop_stream()
        self.board.release_session()
        logging.info("EEG session released")
        
    def get_data(self, num_samples: Optional[int] = None) -> Tuple[np.ndarray, List[int]]:
        """
        Get collected EEG data.
        
        Args:
            num_samples: Number of samples to get, all data if None
            
        Returns:
            Tuple containing the EEG data and timestamps in ms
        """
        if not self.is_streaming:
            logging.warning("Stream not running, no data available")
            return np.array([]), []
            
        if num_samples is None:
            # Get all data and keep it in the buffer
            data = self.board.get_board_data()
        else:
            # Get latest num_samples samples
            data = self.board.get_current_board_data(num_samples)
            
        # Get timestamps from the data
        try:
            timestamps = data[self.timestamp_channel].tolist()
            # If board doesn't provide timestamps, generate them
            if not timestamps or len(timestamps) == 0:
                current_time = int(round(time.time() * 1000))
                timestamps = list(range(self.start_time, current_time, 
                                       int(1000 / self.sampling_rate)))[-data.shape[1]:]
        except Exception as e:
            logging.error(f"Error getting timestamps: {e}")
            timestamps = []
            
        self.raw_data = data
        self.timestamps = timestamps
        
        return data, timestamps
        
    def save_data(self, filename: str, data_type: str = 'raw') -> None:
        """
        Save collected data to a file.
        
        Args:
            filename: Path to save the file
            data_type: Type of data to save ('raw' or 'processed')
        """
        if data_type == 'raw' and self.raw_data is not None:
            DataFilter.write_file(self.raw_data, filename, 'w')
            logging.info(f"Raw data saved to {filename}")
        elif data_type == 'processed' and self.processed_data is not None:
            DataFilter.write_file(self.processed_data, filename, 'w')
            logging.info(f"Processed data saved to {filename}")
        else:
            logging.warning(f"No {data_type} data available to save")
            
    def get_board_info(self) -> Dict[str, Any]:
        """
        Get information about the connected EEG board.
        
        Returns:
            Dictionary with board information
        """
        return {
            'board_id': self.board_id,
            'board_name': BoardShim.get_device_name(self.board_id),
            'sampling_rate': self.sampling_rate,
            'eeg_channels': self.eeg_channels,
            'timestamp_channel': self.timestamp_channel,
            'marker_channel': self.marker_channel,
            'num_channels': BoardShim.get_num_rows(self.board_id)
        }
        
    def insert_marker(self, marker_value: int) -> None:
        """
        Insert a marker into the data stream.
        
        Args:
            marker_value: Value of the marker to insert
        """
        if self.is_streaming:
            self.board.insert_marker(marker_value)
            logging.info(f"Marker {marker_value} inserted")
        else:
            logging.warning("Cannot insert marker: stream not running")
    
    def get_eeg_channels(self) -> List[int]:
        """
        Get the EEG channel indices.
        
        Returns:
            List of EEG channel indices
        """
        return self.eeg_channels
    
    def set_processed_data(self, data: np.ndarray) -> None:
        """
        Set processed data after signal processing.
        
        Args:
            data: Processed EEG data
        """
        self.processed_data = data
