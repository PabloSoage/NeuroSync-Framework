import logging
import os
import time
import threading
from typing import Any, Optional, List

import numpy as np

from .data_access_service import DataAccessService
from ..interfaces.recording_interface import (
    DataStorageInterface,
    ContinuousRecordingInterface,
)


class RecordingService(DataStorageInterface, ContinuousRecordingInterface):
    """
    Service for managing data recording operations.

    This service handles recording start/stop, status tracking, and file operations.
    """

    _instance: Optional["RecordingService"] = None
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "RecordingService":
        """Get the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = RecordingService()
            return cls._instance

    def __init__(self) -> None:
        """Initialize the recording service."""
        if RecordingService._instance is not None:
            raise RuntimeError("RecordingService is a singleton. Use get_instance()")
        
        self.recording = False
        self.start_time: float = 0
        self.filename = ""
        self.data_type = "raw"

        # Initialize the data manager for recording operations
        self.data_manager = RecordingDataManager(self)
        
        logging.info("RecordingService singleton initialized")

    def start_recording(self, filename: str, data_type: str = "raw") -> bool:
        """
        Start recording data to a file.

        Args:
            filename: Path to save the file
            data_type: Type of data to record ('raw', 'processed', or 'both')

        Returns:
            True if recording started successfully, False otherwise
        """
        if self.recording:
            logging.warning("Recording is already in progress")
            return False

        if not os.path.dirname(filename):
            # Create a default directory if only filename is provided
            directory = os.path.join(os.getcwd(), "recordings")
            os.makedirs(directory, exist_ok=True)
            filename = os.path.join(directory, filename)

        try:
            # Start continuous recording using the data manager
            self.start_continuous_recording(filename, data_type)

            # Update state
            self.recording = True
            self.start_time = time.time()
            self.filename = filename
            self.data_type = data_type

            logging.info(f"Recording started to {filename} (type: {data_type})")
            return True
        except Exception as e:
            logging.error(f"Recording start error: {e}")
            return False

    def stop_recording(self) -> bool:
        """
        Stop recording and save data to file.

        Returns:
            True if recording stopped successfully, False otherwise
        """
        if not self.recording:
            return False

        try:
            # Stop continuous recording using the data manager
            self.stop_continuous_recording()

            # Record final state for reporting
            duration = time.time() - self.start_time
            filename = self.filename
            data_type = self.data_type

            # Update state
            self.recording = False
            self.start_time = 0
            self.filename = ""
            self.data_type = "raw"

            logging.info(
                f"Recording stopped, saved to {filename} (duration: {duration:.2f}s)"
            )
            return True
        except Exception as e:
            logging.error(f"Recording stop error: {e}")
            return False

    def insert_marker(self, marker_value: float) -> bool:
        """
        Insert a marker into the data stream during recording.

        Args:
            marker_value: Value of the marker to insert

        Returns:
            True if marker was inserted successfully, False otherwise
        """
        if not self.recording:
            logging.warning("Cannot insert marker: not recording")
            return False

        try:
            return self.data_manager.insert_marker(marker_value)
        except Exception as e:
            logging.error(f"Marker insertion error: {e}")
            return False

    def is_recording(self) -> bool:
        """
        Check if recording is in progress.

        Returns:
            True if recording is active, False otherwise
        """
        return self.recording

    def get_recording_duration(self) -> float:
        """
        Get the duration of the current recording in seconds.

        Returns:
            Duration in seconds, or 0 if not recording
        """
        if not self.recording:
            return 0

        return time.time() - self.start_time

    def get_recording_filename(self) -> str:
        """
        Get the current recording filename.

        Returns:
            Current recording filename, or empty string if not recording
        """
        return self.filename

    def get_recording_data_type(self) -> str:
        """
        Get the current recording data type.

        Returns:
            Current recording data type, or "raw" if not recording
        """
        return self.data_type

    def cleanup(self) -> None:
        """Clean up recording resources."""
        if self.recording:
            self.stop_recording()
        self.recording = False
        self.start_time = 0
        self.filename = ""
        self.data_type = "raw"

    # ================================
    # Interface Implementations
    # ================================

    def start_continuous_recording(self, filename: str, data_type: str = "raw") -> None:
        """
        Start continuous recording to file.

        Args:
            filename: Path to save the file
            data_type: Type of data ('raw', 'processed', or 'both')
        """
        self.data_manager.start_recording(filename, data_type)

    def stop_continuous_recording(self) -> None:
        """Stop continuous recording."""
        self.data_manager.stop_recording()

    def save_data(self, filename: str, data_type: str = "raw") -> None:
        """
        Save collected data to a file.

        Args:
            filename: Path to save the file
            data_type: Type of data to save ('raw' or 'processed')
        """
        try:
            # Get DataAccessService for data access
            data_access = DataAccessService.get_instance()

            data = None

            if data_type == "raw":
                raw_data, _ = data_access.get_raw_data()
                if raw_data.size > 0:
                    data = raw_data
                else:
                    logging.warning("No raw data available to save")
                    return

            elif data_type == "processed":
                processed_data, _ = (
                    data_access.get_current_data()
                )  # This applies filters
                if processed_data.size > 0:
                    data = processed_data
                else:
                    logging.warning("No processed data available to save")
                    return
            else:
                logging.warning(
                    f"Invalid data type '{data_type}'. Use 'raw' or 'processed'"
                )
                return

            # Get active collector for metadata
            collector = data_access._get_active_collector()
            if not collector:
                logging.error("No active collector available for file metadata")
                return

            # Use the RecordingFileWriter utility class to write the data
            writer = RecordingFileWriter(collector)
            writer.write_to_file(filename, data, data_type)
            logging.info(f"{data_type} data saved to {filename}")

        except Exception as e:
            logging.error(f"Error saving data: {e}")

    # ================================
    # Additional Properties
    # ================================

    @property
    def total_recorded_samples(self) -> int:
        """Get total recorded samples."""
        return self.data_manager.total_recorded_samples

    def get_board_data_count(self) -> int:
        """
        Get current data count for recording purposes.

        Returns:
            Number of samples currently in buffer
        """
        try:
            data_access = DataAccessService.get_instance()
            with data_access._data_lock:
                return (
                    data_access._current_data.shape[1]
                    if data_access._current_data.size > 0
                    else 0
                )
        except Exception as e:
            logging.error(f"Error getting board data count: {e}")
            return 0


class RecordingDataManager:
    """
    Manages continuous data recording for RecordingService.
    This class handles the recording thread and file operations.
    """

    def __init__(self, recording_service: "RecordingService") -> None:
        """
        Initialize the data manager.

        Args:
            recording_service: The RecordingService instance
        """
        self.recording_service = recording_service
        self.recording = False
        self.recording_file: Optional[Any] = None
        self.processed_recording_file: Optional[Any] = None
        # REMOVED: self.recording_thread - no longer needed
        # REMOVED: self.recording_stop_event - no longer needed
        self.total_recorded_samples = 0
        self.recording_start_time: float = 0
        # REMOVED: self.last_data_count - no longer needed
        self.data_type = "raw"
        self.is_recording_both = False

        # NEW: Direct callback approach
        self.data_callback_id: Optional[int] = None

    def start_recording(self, filename: str, data_type: str = "raw") -> None:
        """
        Start recording data to a file using direct callbacks.

        Args:
            filename: Path to save the file
            data_type: Type of data to record ('raw', 'processed', or 'both')
        """
        if self.recording:
            logging.warning("Recording is already in progress")
            return

        # Get DataAccessService and active collector for header generation
        data_access = DataAccessService.get_instance()
        collector = data_access._get_active_collector()
        if not collector:
            raise RuntimeError("No active collector available for recording")

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
                self._start_file_recording(self.raw_filename, "raw", collector)

                # Start recording processed data
                self._start_file_recording(
                    self.processed_filename, "processed", collector
                )

                logging.info(
                    f"Dual continuous recording started in {self.raw_filename} and {self.processed_filename}"
                )
            else:
                # Standard case: single data type
                self._start_file_recording(filename, data_type, collector)
                logging.info(f"Continuous recording started in {filename}")

            # Initialize recording variables
            self.recording = True
            self.total_recorded_samples = 0
            self.recording_start_time = time.time()

            # NEW: Register direct callback for immediate data streaming
            self.data_callback_id = data_access.register_local_callback(
                self._on_new_data
            )
            logging.info(
                "Registered direct callback for recording - no data duplication"
            )

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

    def _on_new_data(self, data: np.ndarray, timestamps: List[int]) -> None:
        """
        Handle new data from DataAccessService callback.
        This receives only NEW data chunks - no duplication.

        Args:
            data: New data chunk (only new samples)
            timestamps: Corresponding timestamps
        """
        if not self.recording:
            return

        try:
            # Get the size of the new chunk
            new_samples = data.shape[1] if data.size > 0 else 0

            if new_samples == 0:
                return

            logging.debug(f"Recording received {new_samples} new samples via callback")

            # Record raw data if needed
            if self.data_type == "raw" or self.data_type == "both":
                # data is already raw from the callback
                self._write_data_to_file(data, "raw")

            # Record processed data if needed
            if self.data_type == "processed" or self.data_type == "both":
                # Get the same samples but already filtered from DataAccessService
                data_access = DataAccessService.get_instance()

                # Get the filtered buffer and extract the same number of new samples
                filtered_buffer, _ = data_access.get_current_data()

                if filtered_buffer.size > 0 and filtered_buffer.shape[1] >= new_samples:
                    # Get the last 'new_samples' from the filtered buffer
                    # These correspond to the same samples as the raw data callback
                    processed_chunk = filtered_buffer[:, -new_samples:]
                    self._write_data_to_file(processed_chunk, "processed")
                    logging.debug(
                        f"Wrote {new_samples} pre-filtered samples to processed file"
                    )
                else:
                    # Fallback: use raw data if filtered buffer is not available
                    logging.warning(
                        "Filtered buffer not available, using raw data for processed recording"
                    )
                    self._write_data_to_file(data, "processed")

            # Update sample counter
            self.total_recorded_samples += new_samples

        except Exception as e:
            logging.error(f"Error in recording data callback: {e}")

    def stop_recording(self) -> None:
        """
        Stop continuous recording and close the file.
        """
        if not self.recording:
            logging.warning("No active recording to stop")
            return

        try:
            # Mark as not recording
            self.recording = False

            # NEW: Unregister callback instead of stopping thread
            if self.data_callback_id is not None:
                data_access = DataAccessService.get_instance()
                data_access.unregister_local_callback(self.data_callback_id)
                self.data_callback_id = None
                logging.info("Unregistered recording callback")

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
            # REMOVED: self.recording_thread = None - no longer used

    def _finalize_recording_file(
        self, file_handle: Any, recording_duration: float
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

    def insert_marker(self, marker_value: float) -> bool:
        """
        Insert a marker into the data stream during recording.

        Args:
            marker_value: Value of the marker to insert

        Returns:
            True if marker was inserted successfully, False otherwise
        """
        if not self.recording:
            return False

        try:
            # Get collector service for marker insertion
            data_access = DataAccessService.get_instance()
            if data_access._collector_service:
                return data_access._collector_service.insert_marker(marker_value)
            return False
        except Exception as e:
            logging.error(f"Error inserting marker: {e}")
            return False

    def _start_file_recording(
        self, filename: str, data_type: str, collector: Any
    ) -> None:
        """
        Start recording to a specific file with correct metadata.

        Args:
            filename: Path to save the file
            data_type: Type of data ('raw' or 'processed')
            collector: The collector instance for metadata
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

        # Open file and write header
        file_handle = open(filename, "w", newline="")

        # Write initial metadata
        header = [
            f"# EEG Recording - {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Board: {collector.device_name} (ID: {collector.board_id})",
            f"# Preset: {collector.preset}",
            f"# Sampling Rate: {collector.sampling_rate} Hz",
            f"# Data Type: {data_type}",
            f"# Channels: {collector.num_rows}",
            f"# Samples: 0",  # Placeholder to be updated at the end
            f"# Duration: 0.00 seconds",  # Placeholder to be updated at the end
        ]

        # Add column names using the RecordingFileWriter logic
        writer = RecordingFileWriter(collector)
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

    def _write_data_to_file(self, data: np.ndarray, data_type: str) -> None:
        """
        Write data to the appropriate recording file.

        Args:
            data: Data to write
            data_type: Type of data ('raw' or 'processed')
        """
        try:
            # Select appropriate file handle
            if data_type == "processed" and hasattr(self, "processed_recording_file"):
                file_handle = self.processed_recording_file
            elif data_type == "raw" and hasattr(self, "recording_file"):
                file_handle = self.recording_file
            else:
                logging.warning(f"No file handle available for {data_type} data")
                return

            if file_handle is None:
                logging.warning(f"File handle is None for {data_type} data")
                return

            # Write each sample as a row in CSV format
            for i in range(data.shape[1]):  # For each sample
                sample = data[:, i]  # Get all channels for this sample
                line = ",".join(str(val) for val in sample)
                file_handle.write(line + "\n")

            # Flush to ensure data is written immediately
            file_handle.flush()

            logging.debug(f"Wrote {data.shape[1]} samples of {data_type} data to file")

        except Exception as e:
            logging.error(f"Error writing {data_type} data to file: {e}")


class RecordingFileWriter:
    """
    Handles file writing operations for RecordingService data.
    """

    def __init__(self, collector: Any) -> None:
        """
        Initialize the file writer.

        Args:
            collector: The collector instance
        """
        self.collector = collector

    def write_to_file(self, filename: str, data: Any, data_type: str) -> None:
        """
        Write data to a file with appropriate formatting and metadata.

        Args:
            filename: Path to save the file
            data: Data to write
            data_type: Type of data ('raw' or 'processed')
        """
        import numpy as np

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
                header.append(", ".join(column_names))

                # Write header lines with line breaks
                for line in header:
                    file.write(line + "\n")

                # Write each sample as a row in CSV
                for i in range(data.shape[1]):  # For each column (sample)
                    sample = data[:, i]  # This is a sample with all channels
                    line = ",".join(str(val) for val in sample)
                    file.write(line + "\n")

        else:
            # For other formats, fallback to numpy save
            np.save(filename, data)

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
