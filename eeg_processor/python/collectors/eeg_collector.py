import logging
import time
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, BrainFlowPresets
from brainflow.data_filter import DataFilter
from brainflow.exit_codes import BrainFlowError, BrainFlowExitCodes

from ..interfaces.collector_interface import CollectorInterface


class EEGCollector(CollectorInterface):
    """
    Collector for EEG data using BrainFlow.

    This class handles the connection to EEG devices, data acquisition,
    and basic data management operations.
    """

    def __init__(
        self,
        board_id: int = BoardIds.SYNTHETIC_BOARD,
        params: Optional[BrainFlowInputParams] = None,
        preset: int = BrainFlowPresets.DEFAULT_PRESET,
    ):
        """
        Initialize the EEG collector.

        Args:
            board_id: ID of the board to connect to (default: SYNTHETIC_BOARD)
            params: Parameters for board initialization
            preset: Data preset to use (default: DEFAULT_PRESET)
        """
        BoardShim.enable_dev_board_logger()

        if params is None:
            params = BrainFlowInputParams()

        self.params = params
        self.board_id = board_id
        self.preset = preset
        self.board = BoardShim(self.board_id, self.params)
        self.is_streaming = False
        self.start_time = 0
        self.raw_data = None
        self.processed_data = None
        self.timestamps = []
        
        # Get available presets for this board
        try:
            self.available_presets = BoardShim.get_board_presets(self.board_id)
            logging.info(f"Available presets for board {self.board_id}: {self.available_presets}")
        except Exception as e:
            logging.warning(f"Could not get available presets: {e}")
            self.available_presets = [BrainFlowPresets.DEFAULT_PRESET]

        # Get board information
        try:
            self.sampling_rate = BoardShim.get_sampling_rate(self.board_id, self.preset)
            self.eeg_channels = BoardShim.get_eeg_channels(self.board_id, self.preset)
            self.timestamp_channel = BoardShim.get_timestamp_channel(self.board_id, self.preset)
            self.marker_channel = BoardShim.get_marker_channel(self.board_id, self.preset)
            
            # Get additional channel types if available
            try:
                self.exg_channels = BoardShim.get_exg_channels(self.board_id, self.preset)
            except:
                self.exg_channels = self.eeg_channels
                
            # Get other channel types
            self.channel_types = {
                'eeg': self.eeg_channels,
                'emg': self._get_channels_safely(BoardShim.get_emg_channels, "EMG"),
                'ecg': self._get_channels_safely(BoardShim.get_ecg_channels, "ECG"),
                'eog': self._get_channels_safely(BoardShim.get_eog_channels, "EOG"),
                'eda': self._get_channels_safely(BoardShim.get_eda_channels, "EDA"),
                'ppg': self._get_channels_safely(BoardShim.get_ppg_channels, "PPG"),
                'accel': self._get_channels_safely(BoardShim.get_accel_channels, "Accel"),
                'gyro': self._get_channels_safely(BoardShim.get_gyro_channels, "Gyro"),
                'temperature': self._get_channels_safely(BoardShim.get_temperature_channels, "Temperature"),
                'resistance': self._get_channels_safely(BoardShim.get_resistance_channels, "Resistance"),
                'other': self._get_channels_safely(BoardShim.get_other_channels, "Other"),
            }
            
            # Try to get EEG names if available
            try:
                self.eeg_names = BoardShim.get_eeg_names(self.board_id, self.preset)
                if isinstance(self.eeg_names, str):
                    self.eeg_names = self.eeg_names.split(',')
            except:
                self.eeg_names = [f"Channel {i}" for i in self.eeg_channels]
        except Exception as e:
            logging.error(f"Error initializing board information: {e}")
            raise
        
        # Get device name
        try:
            self.device_name = BoardShim.get_device_name(self.board_id)
        except:
            self.device_name = f"Board ID {self.board_id}"
            
        # Get number of rows
        try:
            self.num_rows = BoardShim.get_num_rows(self.board_id, self.preset)
        except:
            self.num_rows = 0

        logging.info(f"EEG Collector initialized with board_id: {self.board_id}, preset: {self.preset}")
        logging.info(f"Device: {self.device_name}, Sampling rate: {self.sampling_rate}Hz")
        logging.info(f"EEG channels: {self.eeg_channels}")

    def _get_channels_safely(self, channel_func, channel_type: str) -> List[int]:
        """
        Safely get channels of a specific type, handling exceptions.
        
        Args:
            channel_func: The BoardShim function to call
            channel_type: The type of channel (for logging)
            
        Returns:
            List of channel indices
        """
        try:
            channels = channel_func(self.board_id, self.preset)
            return channels
        except Exception as e:
            logging.debug(f"No {channel_type} channels available: {e}")
            return []

    def prepare_session(self) -> None:
        """
        Prepare the session for data collection.
        """
        try:
            self.board.prepare_session()
            logging.info("EEG session prepared")
        except BrainFlowError as e:
            if e.exit_code == BrainFlowExitCodes.BOARD_NOT_CREATED_ERROR.value:
                logging.error("Board was not created. Check your parameters.")
            elif e.exit_code == BrainFlowExitCodes.ANOTHER_BOARD_IS_CREATED_ERROR.value:
                logging.error("Another board is already created in the same process.")
            else:
                logging.error(f"Error preparing session: {e}")
            raise

    def start_stream(self, buffer_size: int = 450000) -> None:
        """
        Start streaming EEG data.
        
        Args:
            buffer_size: Size of the buffer for data
        """
        if not self.is_streaming:
            self.board.start_stream(buffer_size)
            self.is_streaming = True
            self.start_time = int(round(time.time() * 1000))  # Current time in ms
            logging.info(f"EEG stream started with buffer size {buffer_size}")
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

    def get_data(
        self, num_samples: Optional[int] = None
    ) -> Tuple[np.ndarray, List[int]]:
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

        try:
            if num_samples is None:
                # Get all data and keep it in the buffer
                data = self.board.get_board_data(preset=self.preset)
            else:
                # Get latest num_samples samples
                data = self.board.get_current_board_data(num_samples, preset=self.preset)

            # Get timestamps from the data
            try:
                timestamps = data[self.timestamp_channel].tolist()
                # If board doesn't provide timestamps, generate them
                if not timestamps or len(timestamps) == 0:
                    current_time = int(round(time.time() * 1000))
                    timestamps = list(
                        range(self.start_time, current_time, int(1000 / self.sampling_rate))
                    )[-data.shape[1]:]
            except Exception as e:
                logging.error(f"Error getting timestamps: {e}")
                timestamps = []

            self.raw_data = data
            self.timestamps = timestamps

            return data, timestamps
        except Exception as e:
            logging.error(f"Error getting data: {e}")
            return np.array([]), []

    def save_data(self, filename: str, data_type: str = "raw") -> None:
        """
        Save collected data to a file.

        Args:
            filename: Path to save the file
            data_type: Type of data to save ('raw' or 'processed')
        """
        if data_type == "raw" and self.raw_data is not None:
            DataFilter.write_file(self.raw_data, filename, "w")
            logging.info(f"Raw data saved to {filename}")
        elif data_type == "processed" and self.processed_data is not None:
            DataFilter.write_file(self.processed_data, filename, "w")
            logging.info(f"Processed data saved to {filename}")
        else:
            logging.warning(f"No {data_type} data available to save")

    def get_board_info(self) -> Dict[str, Any]:
        """
        Get information about the connected EEG board.

        Returns:
            Dictionary with board information
        """
        info = {
            "board_id": self.board_id,
            "board_name": self.device_name,
            "sampling_rate": self.sampling_rate,
            "preset": self.preset,
            "available_presets": self.available_presets,
            "eeg_channels": self.eeg_channels,
            "eeg_names": self.eeg_names,
            "timestamp_channel": self.timestamp_channel,
            "marker_channel": self.marker_channel,
            "num_rows": self.num_rows,
        }
        
        # Add channel type information if available
        for ch_type, channels in self.channel_types.items():
            if channels:
                info[f"{ch_type}_channels"] = channels
        
        return info

    def insert_marker(self, marker_value: float) -> None:
        """
        Insert a marker into the data stream.

        Args:
            marker_value: Value of the marker to insert
        """
        if self.is_streaming:
            self.board.insert_marker(marker_value, self.preset)
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

    def get_channel_by_type(self, channel_type: str) -> List[int]:
        """
        Get channels of a specific type.
        
        Args:
            channel_type: Type of channels to get ('eeg', 'emg', 'ecg', etc.)
            
        Returns:
            List of channel indices
        """
        if channel_type in self.channel_types:
            return self.channel_types[channel_type]
        else:
            logging.warning(f"Unknown channel type: {channel_type}")
            return []

    def set_processed_data(self, data: np.ndarray) -> None:
        """
        Set processed data after signal processing.

        Args:
            data: Processed EEG data
        """
        self.processed_data = data
        
    def add_streamer(self, streamer_params: str) -> None:
        """
        Add a streamer to stream data.
        
        Args:
            streamer_params: Parameters for the streamer
        """
        if self.is_streaming:
            logging.warning("Cannot add streamer while streaming")
            return
            
        try:
            self.board.add_streamer(streamer_params, self.preset)
            logging.info(f"Added streamer with parameters: {streamer_params}")
        except Exception as e:
            logging.error(f"Error adding streamer: {e}")
            
    def delete_streamer(self, streamer_params: str) -> None:
        """
        Delete a streamer.
        
        Args:
            streamer_params: Parameters for the streamer to delete
        """
        try:
            self.board.delete_streamer(streamer_params, self.preset)
            logging.info(f"Deleted streamer with parameters: {streamer_params}")
        except Exception as e:
            logging.error(f"Error deleting streamer: {e}")
            
    def get_board_data_count(self) -> int:
        """
        Get the current number of samples in the buffer.
        
        Returns:
            Number of samples in the buffer
        """
        try:
            count = self.board.get_board_data_count(self.preset)
            return count
        except Exception as e:
            logging.error(f"Error getting board data count: {e}")
            return 0
            
    def config_board(self, config: str) -> str:
        """
        Send configuration to the board.
        
        Args:
            config: Configuration string to send
            
        Returns:
            Response from the board
        """
        try:
            response = self.board.config_board(config)
            logging.info(f"Board configured with: {config}")
            return response
        except Exception as e:
            logging.error(f"Error configuring board: {e}")
            return ""
    
    def set_preset(self, preset: int) -> bool:
        """
        Change the current preset.
        
        Args:
            preset: New preset value
            
        Returns:
            Success status
        """
        if preset not in self.available_presets:
            logging.warning(f"Preset {preset} not available for this board")
            return False
            
        try:
            self.preset = preset
            # Update board information for the new preset
            self.sampling_rate = BoardShim.get_sampling_rate(self.board_id, self.preset)
            self.eeg_channels = BoardShim.get_eeg_channels(self.board_id, self.preset)
            self.timestamp_channel = BoardShim.get_timestamp_channel(self.board_id, self.preset)
            self.marker_channel = BoardShim.get_marker_channel(self.board_id, self.preset)
            
            logging.info(f"Preset changed to {preset}")
            logging.info(f"New sampling rate: {self.sampling_rate}Hz")
            logging.info(f"New EEG channels: {self.eeg_channels}")
            
            return True
        except Exception as e:
            logging.error(f"Error changing preset: {e}")
            return False
