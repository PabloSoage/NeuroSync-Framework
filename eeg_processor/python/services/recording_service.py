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
        self, collector_service: Any, filename: str, data_type: str = "raw"
    ) -> bool:
        """
        Start recording data to a file using CollectorService.

        Args:
            collector_service: The collector service object
            filename: Path to save the file
            data_type: Type of data to record ('raw', 'processed', or 'both')

        Returns:
            True if recording started successfully, False otherwise
        """
        if self.recording:
            logging.warning("Recording is already in progress")
            return False

        if not collector_service or not collector_service.is_connected():
            logging.error("No collector service or not connected")
            return False

        # Check if collector has the continuous recording capability
        collector = collector_service.collector
        if not collector:
            logging.error("No active collector available")
            return False

        # Ensure directory exists
        if not os.path.dirname(filename):
            # Create a default directory if only filename is provided
            directory = os.path.join(os.getcwd(), "recordings")
            os.makedirs(directory, exist_ok=True)
            filename = os.path.join(directory, filename)
        else:
            # Create the specified directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

        try:
            # FIXED: Use the collector's continuous recording method directly
            if hasattr(collector, 'start_continuous_recording'):
                collector.start_continuous_recording(filename, data_type)
            else:
                # FALLBACK: If collector doesn't have continuous recording, 
                # we'll implement our own data monitoring approach
                logging.info("Collector doesn't support continuous recording, using fallback approach")
                return self._start_fallback_recording(collector_service, filename, data_type)

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

    def _start_fallback_recording(self, collector_service: Any, filename: str, data_type: str) -> bool:
        """
        Fallback recording method that monitors DataAccessService for new data.

        Args:
            collector_service: The collector service
            filename: Path to save the file
            data_type: Type of data to record

        Returns:
            True if recording started successfully
        """
        try:
            # Import here to avoid circular imports
            from .data_access_service import DataAccessService
            
            # Get data access service
            self.data_access_service = DataAccessService.get_instance()
            
            # Open file for writing
            self.recording_file = open(filename, 'w', newline='')
            
            # Write CSV header
            channel_names = self.data_access_service.get_channel_names()
            if not channel_names:
                # Generate generic names if no channel names available
                metadata = self.data_access_service.get_metadata()
                num_channels = metadata.get('num_channels', 8)  # Default to 8 if unknown
                channel_names = [f"CH{i}" for i in range(num_channels)]
            
            # Add timestamp column
            header_row = ['Timestamp'] + channel_names + ['Marker']
            self.recording_file.write(','.join(header_row) + '\n')
            
            # Register callback to capture data
            self.recording_callback_id = self.data_access_service.register_local_callback(
                self._on_data_for_recording
            )
            
            # Track last data timestamp to avoid duplicates
            self.last_recorded_timestamp = None
            
            logging.info(f"Fallback recording started with {len(channel_names)} channels")
            return True
            
        except Exception as e:
            logging.error(f"Error starting fallback recording: {e}")
            # Clean up on error
            if hasattr(self, 'recording_file') and self.recording_file:
                try:
                    self.recording_file.close()
                except:
                    pass
                self.recording_file = None
            return False

    def _on_data_for_recording(self, data: Any, timestamps: Any) -> None:
        """Callback to handle new data for recording."""
        try:
            if not self.recording or not hasattr(self, 'recording_file') or not self.recording_file:
                return
                
            import numpy as np
            
            # Convert data to numpy array if needed
            if not isinstance(data, np.ndarray):
                return
                
            # Process each sample
            for i in range(data.shape[1]):
                try:
                    # Get timestamp for this sample
                    if i < len(timestamps):
                        timestamp = timestamps[i]
                    else:
                        # Generate timestamp if not available
                        timestamp = int(time.time() * 1000)
                    
                    # Skip if we already recorded this timestamp
                    if self.last_recorded_timestamp is not None and timestamp <= self.last_recorded_timestamp:
                        continue
                    
                    # Extract sample data
                    sample_data = data[:, i]
                    
                    # Create row: timestamp, channel data, marker (0 for now)
                    row_data = [str(timestamp)] + [str(val) for val in sample_data] + ['0']
                    
                    # Write to file
                    self.recording_file.write(','.join(row_data) + '\n')
                    
                    # Update last recorded timestamp
                    self.last_recorded_timestamp = timestamp
                    
                except Exception as e:
                    logging.debug(f"Error recording sample {i}: {e}")
                    continue
            
            # Flush to ensure data is written
            self.recording_file.flush()
            
        except Exception as e:
            logging.error(f"Error in recording callback: {e}")

    def stop_recording(self, collector_service: Any) -> bool:
        """
        Stop recording and save data to file.

        Args:
            collector_service: The collector service object

        Returns:
            True if recording stopped successfully, False otherwise
        """
        if not self.recording:
            return False

        try:
            # Check if collector has continuous recording
            collector = collector_service.collector if collector_service else None
            
            if collector and hasattr(collector, 'stop_continuous_recording'):
                # Use collector's method
                collector.stop_continuous_recording()
            else:
                # Use fallback method
                self._stop_fallback_recording()

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

    def _stop_fallback_recording(self) -> None:
        """Stop fallback recording method."""
        try:
            # Unregister callback
            if hasattr(self, 'recording_callback_id') and hasattr(self, 'data_access_service'):
                self.data_access_service.unregister_local_callback(self.recording_callback_id)
            
            # Close file
            if hasattr(self, 'recording_file') and self.recording_file:
                self.recording_file.close()
                self.recording_file = None
                
            logging.info("Fallback recording stopped")
            
        except Exception as e:
            logging.error(f"Error stopping fallback recording: {e}")

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
