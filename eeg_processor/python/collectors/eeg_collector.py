import logging
import os
import queue
import sys
import threading
import time
from typing import Dict, List, Any, Optional, Tuple, TextIO

import numpy as np

from ..interfaces.collector_interface import (
    CollectorInterface,
    DataStorageInterface,
    ContinuousRecordingInterface,
    MarkerInterface,
    ConfigurableCollectorInterface,
)

from brainflow.board_shim import (
    BoardShim,
    BrainFlowInputParams,
    BoardIds,
    BrainFlowPresets,
)
from brainflow.data_filter import DataFilter
from brainflow.exit_codes import BrainFlowError, BrainFlowExitCodes


class BrainFlowCollector(
    CollectorInterface,
    DataStorageInterface,
    ContinuousRecordingInterface,
    MarkerInterface,
    ConfigurableCollectorInterface,
):
    """
    Collector for biosignal data using BrainFlow.

    This class implements multiple interfaces to provide complete
    functionality for BrainFlow-based data collection.
    """

    def __init__(
        self,
        board_id: int = BoardIds.SYNTHETIC_BOARD,
        params: Optional[BrainFlowInputParams] = None,
        preset: int = BrainFlowPresets.DEFAULT_PRESET,
    ):
        """
        Initialize the BrainFlow collector.

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
        self.timestamps: List[int] = []

        # Setup the data manager for continuous recording
        self.data_manager = BrainFlowDataManager(self)

        # Initialize board information
        self._initialize_board_info()

    def _initialize_board_info(self) -> None:
        """Initialize board-related information and channel properties."""
        try:
            # Get available presets for this board
            self.available_presets = BoardShim.get_board_presets(self.board_id)
            logging.info(
                f"Available presets for board {self.board_id}: {self.available_presets}"
            )
        except Exception as e:
            logging.warning(f"Could not get available presets: {e}")
            self.available_presets = [BrainFlowPresets.DEFAULT_PRESET]

        # Get board information
        try:
            self.sampling_rate = BoardShim.get_sampling_rate(self.board_id, self.preset)
            self.eeg_channels = BoardShim.get_eeg_channels(self.board_id, self.preset)
            self.timestamp_channel = BoardShim.get_timestamp_channel(
                self.board_id, self.preset
            )
            self.marker_channel = BoardShim.get_marker_channel(
                self.board_id, self.preset
            )

            # Get additional channel types if available
            try:
                self.exg_channels = BoardShim.get_exg_channels(
                    self.board_id, self.preset
                )
            except:
                self.exg_channels = self.eeg_channels

            # Get other channel types
            self.channel_types = {
                "eeg": self.eeg_channels,
                "emg": self._get_channels_safely(BoardShim.get_emg_channels, "EMG"),
                "ecg": self._get_channels_safely(BoardShim.get_ecg_channels, "ECG"),
                "eog": self._get_channels_safely(BoardShim.get_eog_channels, "EOG"),
                "eda": self._get_channels_safely(BoardShim.get_eda_channels, "EDA"),
                "ppg": self._get_channels_safely(BoardShim.get_ppg_channels, "PPG"),
                "accel": self._get_channels_safely(
                    BoardShim.get_accel_channels, "Accel"
                ),
                "gyro": self._get_channels_safely(BoardShim.get_gyro_channels, "Gyro"),
                "temperature": self._get_channels_safely(
                    BoardShim.get_temperature_channels, "Temperature"
                ),
                "resistance": self._get_channels_safely(
                    BoardShim.get_resistance_channels, "Resistance"
                ),
                "other": self._get_channels_safely(
                    BoardShim.get_other_channels, "Other"
                ),
            }

            # Try to get EEG names if available
            try:
                self.eeg_names = BoardShim.get_eeg_names(self.board_id, self.preset)
                if isinstance(self.eeg_names, str):
                    self.eeg_names = self.eeg_names.split(",")
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

        logging.info(
            f"BrainFlow Collector initialized with board_id: {self.board_id}, preset: {self.preset}"
        )
        logging.info(
            f"Device: {self.device_name}, Sampling rate: {self.sampling_rate}Hz"
        )
        logging.info(f"EEG channels: {self.eeg_channels}")

    def _get_channels_safely(self, channel_func: Any, channel_type: str) -> List[int]:
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

    # CollectorInterface implementation
    def prepare_session(self) -> None:
        """Prepare the session for data collection."""
        try:
            self.board.prepare_session()
            logging.info("BrainFlow session prepared")
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
        Start streaming data.

        Args:
            buffer_size: Size of the buffer for data
        """
        if not self.is_streaming:
            self.board.start_stream(buffer_size)
            self.is_streaming = True
            self.start_time = int(round(time.time() * 1000))  # Current time in ms
            logging.info(f"BrainFlow stream started with buffer size {buffer_size}")
        else:
            logging.warning("Stream already running")

    def stop_stream(self) -> None:
        """Stop streaming data."""
        if self.is_streaming:
            self.board.stop_stream()
            self.is_streaming = False
            logging.info("BrainFlow stream stopped")
        else:
            logging.warning("No stream to stop")

    def release_session(self) -> None:
        """Release resources after the session is finished."""
        if self.is_streaming:
            self.stop_stream()
        self.board.release_session()
        logging.info("BrainFlow session released")

    def get_data(
        self, num_samples: Optional[int] = None
    ) -> Tuple[np.ndarray, List[int]]:
        """
        Get collected data.

        Args:
            num_samples: Number of samples to get, all data if None

        Returns:
            Tuple containing the data and timestamps in ms
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
                data = self.board.get_current_board_data(
                    num_samples, preset=self.preset
                )

            # Get timestamps from the data
            timestamps = self._extract_timestamps(data)

            self.raw_data = data
            self.timestamps = timestamps

            return data, timestamps
        except Exception as e:
            logging.error(f"Error getting data: {e}")
            return np.array([]), []

    def _extract_timestamps(self, data: np.ndarray) -> List[int]:
        """
        Extract timestamps from data array or generate if not available.

        Args:
            data: Data array from board

        Returns:
            List of timestamps
        """
        try:
            timestamps = data[self.timestamp_channel].tolist()
            # If board doesn't provide timestamps, generate them
            if not timestamps or len(timestamps) == 0:
                current_time = int(round(time.time() * 1000))
                timestamps = list(
                    range(self.start_time, current_time, int(1000 / self.sampling_rate))
                )[-data.shape[1] :]
            return timestamps
        except Exception as e:
            logging.error(f"Error extracting timestamps: {e}")
            return []

    def get_device_info(self) -> Dict[str, Any]:
        """
        Get information about the connected device.

        Returns:
            Dictionary with device information
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

    # Add backward compatibility method
    def get_board_info(self) -> Dict[str, Any]:
        """
        Backward compatibility method that calls get_device_info().

        Returns:
            Dictionary with device information
        """
        return self.get_device_info()

    def get_eeg_channels(self) -> List[int]:
        """
        Get the EEG channel indices.

        Returns:
            List of EEG channel indices
        """
        return self.eeg_channels

    # DataStorageInterface implementation
    def save_data(self, filename: str, data_type: str = "raw") -> None:
        """
        Save collected data to a file.

        Args:
            filename: Path to save the file
            data_type: Type of data to save ('raw' or 'processed')
        """
        try:
            data = None
            if data_type == "raw" and self.raw_data is not None:
                data = self.raw_data
            elif data_type == "processed" and self.processed_data is not None:
                data = self.processed_data
            else:
                logging.warning(f"No {data_type} data available to save")
                return

            # Use the FileWriter utility class to write the data
            writer = BrainFlowFileWriter(self)
            writer.write_to_file(filename, data, data_type)
            logging.info(f"{data_type} data saved to {filename}")

        except Exception as e:
            logging.error(f"Error saving data: {e}")

    # ContinuousRecordingInterface implementation
    def start_continuous_recording(self, filename: str, data_type: str = "raw") -> None:
        """
        Start continuous recording of data to a file.

        Args:
            filename: Path to save the file
            data_type: Type of data to record ('raw', 'processed', or 'both')
        """
        self.data_manager.start_recording(filename, data_type)

    def stop_continuous_recording(self) -> None:
        """Stop continuous recording and close the file."""
        self.data_manager.stop_recording()

    # MarkerInterface implementation
    def insert_marker(self, marker_value: float) -> None:
        """
        Insert a marker into the data stream.

        Args:
            marker_value: Value of the marker to insert
        """
        if self.is_streaming:
            # Insert the marker with the specified value
            self.board.insert_marker(marker_value, preset=self.preset)

            # Add a small delay to ensure the marker is registered
            # before the next data capture by get_current_board_data
            time.sleep(0.01)

            logging.info(
                f"Marker {marker_value} inserted at channel {self.marker_channel}"
            )
        else:
            logging.warning("Cannot insert marker: stream not running")

    # ConfigurableCollectorInterface implementation
    def config_device(self, config: str) -> str:
        """
        Send configuration to the device.

        Args:
            config: Configuration string to send

        Returns:
            Response from the device
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
            self._initialize_board_info()

            return True
        except Exception as e:
            logging.error(f"Error changing preset: {e}")
            return False

    # Additional utility methods
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

    def set_processed_data(self, data: np.ndarray) -> None:
        """
        Set processed data after signal processing.

        Args:
            data: Processed data
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

    # Add property for backward compatibility
    @property
    def total_recorded_samples(self) -> int:
        """
        Get the total number of recorded samples.

        Returns:
            Total number of recorded samples
        """
        return self.data_manager.total_recorded_samples


class BrainFlowDataManager:
    """
    Manages continuous data recording for BrainFlow collectors.
    This class handles the recording thread and file operations.
    """

    def __init__(self, collector: "BrainFlowCollector") -> None:
        """
        Initialize the data manager.

        Args:
            collector: The BrainFlowCollector instance
        """
        self.collector = collector
        self.recording = False
        self.recording_file: Optional[TextIO] = None
        self.processed_recording_file: Optional[TextIO] = None
        self.recording_thread: Optional[threading.Thread] = None
        self.recording_queue: queue.Queue = queue.Queue()
        self.total_recorded_samples = 0
        self.recording_start_time: float = 0
        self.last_data_count = 0
        self.data_type = "raw"
        self.is_recording_both = False

    def start_recording(self, filename: str, data_type: str = "raw") -> None:
        """
        Start recording data to a file.

        Args:
            filename: Path to save the file
            data_type: Type of data to record ('raw', 'processed', or 'both')
        """
        if self.recording:
            logging.warning("Recording is already in progress")
            return

        try:
            self.data_type = data_type
            self.is_recording_both = data_type == "both"

            # For 'both', create two different files
            if data_type == "both":
                # Create filenames for raw and processed
                base_name, extension = os.path.splitext(filename)
                self.raw_filename = f"{base_name}_raw{extension}"
                self.processed_filename = f"{base_name}_processed{extension}"

                # Start recording raw data
                self._start_file_recording(self.raw_filename, "raw")

                # Start recording processed data
                self._start_file_recording(self.processed_filename, "processed")

                logging.info(
                    f"Dual continuous recording started in {self.raw_filename} and {self.processed_filename}"
                )
            else:
                # Standard case: single data type
                self._start_file_recording(filename, data_type)
                logging.info(f"Continuous recording started in {filename}")

            # Initialize recording variables
            self.recording = True
            self.total_recorded_samples = 0
            self.recording_start_time = time.time()
            self.last_data_count = self.collector.get_board_data_count()

            # Start recording thread
            self.recording_thread = threading.Thread(
                target=self._recording_thread_func, daemon=True
            )
            self.recording_thread.start()

        except Exception as e:
            logging.error(f"Error starting continuous recording: {e}")
            if hasattr(self, "recording_file") and self.recording_file is not None:
                self.recording_file.close()
                self.recording_file = None
            if (
                hasattr(self, "processed_recording_file")
                and self.processed_recording_file is not None
            ):
                self.processed_recording_file.close()
                self.processed_recording_file = None
            raise

    def _start_file_recording(self, filename: str, data_type: str) -> None:
        """
        Start recording to a specific file with correct metadata.

        Args:
            filename: Path to save the file
            data_type: Type of data ('raw' or 'processed')
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

        # Open file and write header
        file_handle = open(filename, "w", newline="")

        # Write initial metadata
        header = [
            f"# EEG Recording - {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Board: {self.collector.device_name} (ID: {self.collector.board_id})",
            f"# Preset: {self.collector.preset}",
            f"# Sampling Rate: {self.collector.sampling_rate} Hz",
            f"# Data Type: {data_type}",
            f"# Channels: {self.collector.num_rows}",
            f"# Samples: 0",  # Placeholder to be updated at the end
            f"# Duration: 0.00 seconds",  # Placeholder to be updated at the end
        ]

        # Add column names using the advanced logic
        writer = BrainFlowFileWriter(self.collector)
        column_names = writer.generate_column_names()

        # Add column names line to header
        header.append(", ".join(column_names))

        # Write header lines with line breaks
        for line in header:
            file_handle.write(line + "\n")

        # Store file handle based on data type
        if data_type == "raw":
            self.recording_file = file_handle
        elif data_type == "processed":
            self.processed_recording_file = file_handle

    def _recording_thread_func(self) -> None:
        """
        Function executed in a separate thread for continuous recording.
        Monitors new data and writes it to file.
        """
        try:
            # Keep track of last processed data count
            last_count = self.last_data_count

            while self.recording:
                # Get current data count in buffer
                current_count = self.collector.get_board_data_count()

                # If new data is available
                if current_count > last_count:
                    # Calculate how many new samples we have
                    new_samples = current_count - last_count

                    # Get raw data (always needed for both types)
                    raw_data = self.collector.board.get_current_board_data(
                        new_samples, preset=self.collector.preset
                    )

                    # Write raw data if applicable
                    if self.data_type == "raw" or self.data_type == "both":
                        self._write_data_to_file(raw_data, "raw")

                    # Write processed data if applicable
                    if self.data_type == "processed" or self.data_type == "both":
                        # For processed data, use processed data if available
                        if (
                            self.collector.processed_data is not None
                            and self.collector.processed_data.shape[1] >= new_samples
                        ):
                            processed_data = self.collector.processed_data[
                                :, -new_samples:
                            ]
                        else:
                            # If no processed data, use raw data as fallback
                            processed_data = raw_data

                        self._write_data_to_file(processed_data, "processed")

                    # Update sample counter and last count
                    self.total_recorded_samples += new_samples
                    last_count = current_count

                # Short pause to avoid CPU overload
                time.sleep(0.1)

        except Exception as e:
            logging.error(f"Error in recording thread: {e}")

    def _write_data_to_file(self, data: np.ndarray, data_type: str) -> None:
        """
        Write data to the corresponding file.

        Args:
            data: Data to write
            data_type: Type of data ('raw' or 'processed')
        """
        # Select correct file
        file_handle = None
        if data_type == "raw":
            file_handle = self.recording_file
        elif data_type == "processed":
            file_handle = self.processed_recording_file

        if file_handle is None:
            return

        # Check for markers in the data
        if (
            hasattr(self.collector, "marker_channel")
            and self.collector.marker_channel < data.shape[0]
        ):
            # Check for non-zero values in marker channel
            markers = data[self.collector.marker_channel]
            non_zero_markers = markers[markers != 0]
            if len(non_zero_markers) > 0:
                logging.info(
                    f"Detected markers in {data_type} data: {non_zero_markers}"
                )

        # Write each sample as a row in CSV
        for i in range(data.shape[1]):  # For each column (sample)
            sample = data[:, i]  # This is a sample with all channels

            # Log if there's a marker in this sample
            if hasattr(
                self.collector, "marker_channel"
            ) and self.collector.marker_channel < len(sample):
                if sample[self.collector.marker_channel] != 0:
                    logging.info(
                        f"Writing marker value {sample[self.collector.marker_channel]} to {data_type} CSV"
                    )

            line = ",".join(str(val) for val in sample)
            file_handle.write(line + "\n")

        # Flush to ensure data is written to disk
        file_handle.flush()

    def stop_recording(self) -> None:
        """
        Stop continuous recording and close the file.
        """
        if not self.recording:
            logging.warning("No active recording to stop")
            return

        try:
            # Mark as not recording to stop the thread
            self.recording = False

            # Wait for thread to finish
            if self.recording_thread is not None:
                self.recording_thread.join(timeout=2.0)  # Wait maximum 2 seconds

            # Calculate actual duration
            recording_duration = time.time() - self.recording_start_time

            # Close and update raw file if active
            if hasattr(self, "recording_file") and self.recording_file is not None:
                self._finalize_recording_file(self.recording_file, recording_duration)
                self.recording_file = None

            # Close and update processed file if active
            if (
                hasattr(self, "processed_recording_file")
                and self.processed_recording_file is not None
            ):
                self._finalize_recording_file(
                    self.processed_recording_file, recording_duration
                )
                self.processed_recording_file = None

            logging.info(
                f"Recording completed: {self.total_recorded_samples} samples in {recording_duration:.2f} seconds"
            )

        except Exception as e:
            logging.error(f"Error stopping continuous recording: {e}")
            # Try to close any open files
            if hasattr(self, "recording_file") and self.recording_file is not None:
                try:
                    self.recording_file.close()
                except:
                    pass
                self.recording_file = None

            if (
                hasattr(self, "processed_recording_file")
                and self.processed_recording_file is not None
            ):
                try:
                    self.processed_recording_file.close()
                except:
                    pass
                self.processed_recording_file = None
            raise

        finally:
            # Reset variables
            self.recording = False
            self.is_recording_both = False
            self.recording_thread = None
            self.recording_queue = queue.Queue()

    def _finalize_recording_file(
        self, file_handle: TextIO, recording_duration: float
    ) -> None:
        """
        Finalize a recording file by updating its metadata.

        Args:
            file_handle: File handle to finalize
            recording_duration: Recording duration in seconds
        """
        # Save file name to reopen later
        filename = file_handle.name

        # Close file that's in write mode
        file_handle.close()

        # Reopen file in read+write mode
        with open(filename, "r", encoding="utf-8") as file:
            # Read all file content
            content = file.readlines()

        # Reopen file in write mode to update metadata
        with open(filename, "w", encoding="utf-8") as file:
            # Rewrite file with updated metadata
            for i, line in enumerate(content):
                if i == 6:  # Samples line
                    file.write(f"# Samples: {self.total_recorded_samples}\n")
                elif i == 7:  # Duration line
                    file.write(f"# Duration: {recording_duration:.2f} seconds\n")
                else:
                    file.write(line)


class BrainFlowFileWriter:
    """
    Handles file writing operations for BrainFlow data.
    """

    def __init__(self, collector: "BrainFlowCollector") -> None:
        """
        Initialize the file writer.

        Args:
            collector: The BrainFlowCollector instance
        """
        self.collector = collector

    def write_to_file(self, filename: str, data: np.ndarray, data_type: str) -> None:
        """
        Write data to a file with appropriate formatting and metadata.

        Args:
            filename: Path to save the file
            data: Data to write
            data_type: Type of data ('raw' or 'processed')
        """
        # For CSV files, use our format with headers
        if filename.endswith(".csv"):
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

            with open(filename, "w", newline="") as file:
                # Write metadata
                header = [
                    f"# EEG Recording - {time.strftime('%Y-%m-%d %H:%M:%S')}",
                    f"# Board: {self.collector.device_name} (ID: {self.collector.board_id})",
                    f"# Preset: {self.collector.preset}",
                    f"# Sampling Rate: {self.collector.sampling_rate} Hz",
                    f"# Data Type: {data_type}",
                    f"# Channels: {data.shape[0]}",
                    f"# Samples: {data.shape[1]}",
                    f"# Duration: {data.shape[1]/self.collector.sampling_rate:.2f} seconds",
                ]

                # Generate column names
                column_names = self.generate_column_names()

                # Add column names line to header
                header.append("# Column names: " + ", ".join(column_names))

                # Write header lines with line breaks
                for line in header:
                    file.write(line + "\n")

                # Write each sample as a row in CSV
                for i in range(data.shape[1]):  # For each column (sample)
                    sample = data[:, i]  # This is a sample with all channels
                    line = ",".join(str(val) for val in sample)
                    file.write(line + "\n")

        else:
            # For other formats, use BrainFlow's writer
            DataFilter.write_file(data, filename, "w")

    def generate_column_names(self) -> List[str]:
        """
        Generate descriptive column names for data channels.

        Returns:
            List of column names
        """
        column_names = []

        # Generate names for the number of rows in the board data
        for i in range(self.collector.num_rows):
            # Identify channel type and assign descriptive name
            if (
                hasattr(self.collector, "timestamp_channel")
                and i == self.collector.timestamp_channel
            ):
                column_names.append("Timestamp")
            elif (
                hasattr(self.collector, "marker_channel")
                and i == self.collector.marker_channel
            ):
                column_names.append("Marker")
            elif i in self.collector.channel_types.get("eeg", []):
                # Try to use EEG channel name if available
                eeg_index = self.collector.channel_types["eeg"].index(i)
                if hasattr(self.collector, "eeg_names") and eeg_index < len(
                    self.collector.eeg_names
                ):
                    column_names.append(f"EEG_{self.collector.eeg_names[eeg_index]}")
                else:
                    column_names.append(f"EEG_{eeg_index}")
            elif i in self.collector.channel_types.get("emg", []):
                emg_index = self.collector.channel_types["emg"].index(i)
                column_names.append(f"EMG_{emg_index}")
            elif i in self.collector.channel_types.get("ecg", []):
                ecg_index = self.collector.channel_types["ecg"].index(i)
                column_names.append(f"ECG_{ecg_index}")
            elif i in self.collector.channel_types.get("eog", []):
                eog_index = self.collector.channel_types["eog"].index(i)
                column_names.append(f"EOG_{eog_index}")
            elif i in self.collector.channel_types.get("eda", []):
                eda_index = self.collector.channel_types["eda"].index(i)
                column_names.append(f"EDA_{eda_index}")
            elif i in self.collector.channel_types.get("ppg", []):
                ppg_index = self.collector.channel_types["ppg"].index(i)
                column_names.append(f"PPG_{ppg_index}")
            elif i in self.collector.channel_types.get("accel", []):
                accel_index = self.collector.channel_types["accel"].index(i)
                accel_names = ["X", "Y", "Z"]
                axis_name = (
                    accel_names[accel_index % 3] if accel_index < 3 else accel_index
                )
                column_names.append(f"ACCEL_{axis_name}")
            elif i in self.collector.channel_types.get("gyro", []):
                gyro_channels = self.collector.channel_types.get("gyro")
                if gyro_channels is not None:
                    gyro_index = gyro_channels.index(i)
                    gyro_names = ["X", "Y", "Z"]
                    axis_name = (
                        gyro_names[gyro_index % 3] if gyro_index < 3 else gyro_index
                    )
                    column_names.append(f"GYRO_{axis_name}")
                else:
                    column_names.append(f"CH_{i}")
            elif i in self.collector.channel_types.get("temperature", []):
                temp_index = self.collector.channel_types["temperature"].index(i)
                column_names.append(f"TEMP_{temp_index}")
            elif i in self.collector.channel_types.get("resistance", []):
                res_index = self.collector.channel_types["resistance"].index(i)
                column_names.append(f"RES_{res_index}")
            else:
                # Generic name for unidentified channels
                column_names.append(f"CH_{i}")

        return column_names


# Add this line at the end of the file to maintain backward compatibility
EEGCollector = BrainFlowCollector
