import logging
import queue
import threading
import time
from collections import deque
from typing import Dict, List, Any, Optional, Tuple, Union, Deque

import numpy as np

from .data_access_service import DataAccessService
from ..collectors.board_configuration import BoardConfiguration
from ..collectors.eeg_collector import EEGCollector


class CollectorService:
    """
    Service for managing EEG data collection.

    This class provides an interface for connecting to EEG boards,
    streaming data, and managing the collector state.
    """

    _instance: Optional["CollectorService"] = None
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "CollectorService":
        """Get the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = CollectorService()
            return cls._instance

    def __init__(self) -> None:
        """Initialize the collector service."""
        if CollectorService._instance is not None:
            raise RuntimeError("CollectorService is a singleton. Use get_instance()")

        self.collector: Optional[EEGCollector] = None
        self.is_streaming = False

        # Background data fetch thread
        self._data_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Sample rate metrics
        self._sample_window_size = 5.0
        self._samples_timestamps: Deque[float] = deque(maxlen=1000)
        self._last_sample_count = 0
        self._current_sample_rate = 0.0
        self._last_timestamp = 0.0
        self._last_reported_time = 0.0
        self._report_interval = 0.5

        logging.info("CollectorService singleton initialized (simplified)")

    def _data_loop(self) -> None:
        """Background loop to fetch data and update DataAccessService."""
        data_access = DataAccessService.get_instance()

        # Reset metrics
        self._last_sample_count = 0
        self._current_sample_rate = 0.0
        self._samples_timestamps.clear()
        self._last_timestamp = time.time()
        self._last_reported_time = self._last_timestamp

        # Variables for data processing - IMPROVED for better consistency
        min_event_interval = 0.02  # 50Hz event rate for smoother data flow
        last_event_time = 0.0
        target_chunk_size = 5  # Target 5 samples per chunk at 250Hz = 20ms chunks

        # Get sampling information
        expected_sampling_rate = 0
        if self.collector:
            try:
                expected_sampling_rate = self.collector.sampling_rate
            except:
                expected_sampling_rate = 250

        # Calculate target chunk size based on sampling rate
        if expected_sampling_rate > 0:
            target_chunk_size = max(1, int(expected_sampling_rate * min_event_interval))
            logging.info(f"Target chunk size: {target_chunk_size} samples ({min_event_interval*1000:.1f}ms)")

        while not self._stop_event.is_set() and self.collector and self.is_streaming:
            try:
                current_time = time.time()

                # Get available data
                try:
                    available_count = self.collector.get_board_data_count()
                except Exception as e:
                    logging.debug(f"Error getting board data count: {e}")
                    available_count = 0

                # Process data only if new data is available
                if available_count > self._last_sample_count:
                    new_samples = available_count - self._last_sample_count
                    
                    # Get data in reasonable chunks to maintain flow consistency
                    # Don't take all available data at once if it's too much
                    samples_to_get = min(new_samples, target_chunk_size * 3) # Max 3x target chunk
                    
                    if samples_to_get > 0:
                        self._last_sample_count += samples_to_get

                        # Get new data
                        data, timestamps = self.collector.get_data(samples_to_get)

                        if data.size > 0 and data.shape[1] > 0:
                            # Update sampling rate metrics
                            self._update_sample_metrics(data, current_time)

                            # Update DataAccessService with consistent chunks
                            data_access.update_data(data, timestamps)

                            # Send event for other components
                            if current_time - last_event_time >= min_event_interval:
                                try:
                                    from ..core.event_system import EventType, dispatch
                                    dispatch(
                                        EventType.DATA_UPDATED,
                                        {"data": data, "timestamps": timestamps},
                                        source="collector_service",
                                    )
                                    last_event_time = current_time
                                except Exception as e:
                                    logging.debug(f"Error dispatching data event: {e}")
                            
                            logging.debug(f"Collected {samples_to_get} samples (available: {new_samples})")

                # Adaptive sleep based on data availability
                if expected_sampling_rate > 0:
                    if available_count > self._last_sample_count + target_chunk_size * 2:
                        # Data is accumulating, process faster
                        sleep_time = min_event_interval * 0.5
                    elif new_samples == 0:
                        # No new data, sleep longer
                        sleep_time = min_event_interval * 2
                    else:
                        # Normal processing
                        sleep_time = min_event_interval
                else:
                    sleep_time = 0.01

                time.sleep(sleep_time)

            except Exception as e:
                logging.error(f"Error in data loop: {e}")
                time.sleep(0.1)

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

    def connect_to_board(
        self, board_id: int, params: Dict[str, Any], preset: int
    ) -> bool:
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
            if self.collector:
                self.collector.prepare_session()
                logging.info(f"Connected to board {board_id}")

                # Update metadata in DataAccessService
                data_access = DataAccessService.get_instance()

                # Update metadata with complete board info
                device_info = self.collector.get_device_info()

                # Update metadata with device info
                data_access.update_metadata(
                    {
                        "sampling_rate": device_info.get("sampling_rate", 0),
                        "eeg_channels": device_info.get("eeg_channels", []),
                        "channel_names": device_info.get("eeg_names", []),
                        "num_channels": len(device_info.get("eeg_channels", [])),
                        "board_id": device_info.get("board_id", -1),
                        "board_name": device_info.get("board_name", ""),
                        "streaming": False,
                        "board_info": device_info,  # Store the complete info
                    }
                )

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
            # Ensure buffer_size is an integer
            buffer_size = int(buffer_size)

            self.collector.start_stream(buffer_size)
            self.is_streaming = True

            # Update streaming status and buffer info in DataAccessService
            data_access = DataAccessService.get_instance()
            
            # Calculate reasonable buffer size for DataAccessService based on sampling rate
            sampling_rate = self.get_sampling_rate()
            if sampling_rate > 0:
                # Set DataAccessService buffer to 30 seconds of data (reasonable for real-time processing)
                service_buffer_samples = sampling_rate * 30
                data_access._buffer_max_samples = service_buffer_samples
                logging.info(f"DataAccessService buffer set to {service_buffer_samples} samples (30s at {sampling_rate}Hz)")
            
            data_access.update_metadata({
                "streaming": True,
                "collector_buffer_size": buffer_size,  # Collector's buffer size
                "service_buffer_size": getattr(data_access, '_buffer_max_samples', None)  # Service buffer size
            })

            # Start background data retrieval thread
            self._stop_event.clear()
            self._data_thread = threading.Thread(target=self._data_loop, daemon=True)
            self._data_thread.start()

            logging.info(f"Stream started with collector buffer: {buffer_size}, service buffer: {getattr(data_access, '_buffer_max_samples', 'auto')}")
            return True
        except Exception as e:
            logging.error(f"Stream start error: {e}")
            return False

    def get_board_data(
        self, num_samples: Optional[int] = None
    ) -> Tuple[np.ndarray, List[int]]:
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

    def get_current_sample_rate(self) -> float:
        """
        Get the current measured sample rate.

        Returns:
            Current sample rate in Hz
        """
        return self._current_sample_rate

    def _update_sample_rate(self, current_time: float) -> None:
        """
        Update sampling rate based on recorded timestamps.

        Args:
            current_time: Current time to calculate the window
        """
        # We need at least two samples to calculate a rate
        if len(self._samples_timestamps) < 2:
            self._current_sample_rate = 0.0
            return

        # Find samples within the time window
        window_start = current_time - self._sample_window_size
        samples_in_window = [
            ts for ts in self._samples_timestamps if ts >= window_start
        ]

        # Calculate rate based on samples within the window
        if len(samples_in_window) >= 2:
            # Calculate using the first and last sample in the window
            time_span = samples_in_window[-1] - samples_in_window[0]
            if time_span > 0:
                # Subtract 1 because we need the number of intervals, not points
                sample_count = len(samples_in_window) - 1
                rate = sample_count / time_span

                # Limit to reasonable values (1-1000Hz)
                rate = max(1.0, min(1000.0, rate))
                self._current_sample_rate = rate

                # Update metadata
                try:
                    DataAccessService.get_instance().update_metadata(
                        {"actual_sample_rate": self._current_sample_rate}
                    )
                except Exception as e:
                    logging.debug(f"Error updating sample rate metadata: {e}")

                logging.debug(
                    f"Sample rate: {self._current_sample_rate:.2f} Hz ({len(samples_in_window)} samples in {time_span:.2f}s)"
                )
        else:
            # Not enough samples in the window
            self._current_sample_rate = 0.0

    def _update_sample_metrics(self, data: np.ndarray, current_time: float) -> None:
        """Update sample rate metrics."""
        samples_received = data.shape[1]

        # Record timestamp for each new sample
        now = time.time()
        interval = (
            (now - self._last_timestamp) / samples_received
            if samples_received > 0
            else 0
        )

        for i in range(samples_received):
            self._samples_timestamps.append(now - (samples_received - i - 1) * interval)

        self._last_timestamp = now

        # Calculate actual sampling rate
        if current_time - self._last_reported_time >= self._report_interval:
            self._update_sample_rate(current_time)
            self._last_reported_time = current_time