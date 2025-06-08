import logging
import os
import time
from typing import Any


class RecordingService:
    """
    Service for managing data recording operations.

    This service handles recording start/stop and status tracking.
    """

    def __init__(self) -> None:
        """Initialize the recording service."""
        self.recording = False
        self.start_time: float = 0
        self.filename = ""
        self.data_type = "raw"

    def start_recording(
        self, collector: Any, filename: str, data_type: str = "raw"
    ) -> bool:
        """
        Start recording data to a file.

        Args:
            collector: The data collector object
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
            # Start continuous recording
            collector.start_continuous_recording(filename, data_type)

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

    def stop_recording(self, collector: Any) -> bool:
        """
        Stop recording and save data to file.

        Args:
            collector: The data collector object

        Returns:
            True if recording stopped successfully, False otherwise
        """
        if not self.recording:
            return False

        try:
            # Stop continuous recording
            collector.stop_continuous_recording()

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

    def insert_marker(self, collector: Any, marker_value: float) -> bool:
        """
        Insert a marker into the data stream during recording.

        Args:
            collector: The data collector object
            marker_value: Value of the marker to insert

        Returns:
            True if marker was inserted successfully, False otherwise
        """
        if not self.recording:
            logging.warning("Cannot insert marker: not recording")
            return False

        try:
            collector.insert_marker(marker_value)
            logging.info(f"Marker {marker_value} inserted")
            return True
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
        self.recording = False
        self.start_time = 0
        self.filename = ""
        self.data_type = "raw"
