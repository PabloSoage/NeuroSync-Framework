"""
Integration service for unified application.

This module provides services that coordinate between the EEG processor and
input collector applications.
"""

import os
import time
from typing import Dict, Any, Union

import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from .lsl_sync_service import LSLSyncService


class IntegrationService(QObject):
    """
    Service for integrating EEG processor and input collector functionality.

    This class provides methods to coordinate operations between the two modules,
    particularly for synchronizing recording operations.
    """

    status_message = pyqtSignal(str, str)  # message, color

    def __init__(
        self,
        input_collector_components: Dict[str, Any],
        eeg_processor_components: Dict[str, Any],
    ) -> None:
        """Initialize the integration service."""
        super().__init__()

        self.input_collector = input_collector_components
        self.eeg_processor = eeg_processor_components

        # Recording state
        self.recording_start_time: float = 0.0
        self.recording_directory = ""

        # Create LSL synchronization service
        self.lsl_sync = LSLSyncService()

        # Connect LSL sync signals
        self.lsl_sync.status_message.connect(self.status_message)

        # Initialize LSL streams
        self._initialize_lsl()

        # Setup Timer for periodic checks
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_components_status)
        self.check_timer.start(1000)  # Check every second

        # Data forwarding setup
        self.setup_data_forwarding()

    def _initialize_lsl(self) -> None:
        """Initialize LSL streams."""
        # Get EEG device info for stream configuration
        collector_service = self.eeg_processor["collector_service"]
        eeg_channels = 8  # Default
        eeg_sample_rate = 250  # Default

        if collector_service.is_connected():
            # Get actual values from the connected board
            board_desc = collector_service.get_board_description()
            if board_desc:
                eeg_channels = board_desc.get("eeg_channels", 8)
                eeg_sample_rate = board_desc.get("sampling_rate", 250)

        # Initialize LSL streams
        self.lsl_sync.initialize_streams(
            eeg_channels=eeg_channels,
            eeg_sample_rate=eeg_sample_rate,
            input_channels=20,  # Enough for keyboard, mouse, and controller inputs
            input_sample_rate=60,  # Input events typically happen at lower rates
        )

        # Start LSL synchronization
        self.lsl_sync.start_sync()

    def setup_data_forwarding(self) -> None:
        """Set up data forwarding from EEG and input collector to LSL."""
        # Connect to EEG data stream
        try:
            processor_service = self.eeg_processor["processor_service"]
            processor_service.register_data_callback(self._forward_eeg_data)
            self.status_message.emit("Connected to EEG data stream", "success")
        except Exception as e:
            self.status_message.emit(
                f"Error connecting to EEG data stream: {str(e)}", "warning"
            )

        # Connect to input events
        try:
            event_processor = self.input_collector["event_processor"]
            event_processor.register_event_callback(self._forward_input_event)
            self.status_message.emit("Connected to input event stream", "success")
        except Exception as e:
            self.status_message.emit(
                f"Error connecting to input event stream: {str(e)}", "warning"
            )

    def _forward_eeg_data(self, eeg_data: Union[np.ndarray, Any]) -> None:
        """
        Forward EEG data to LSL stream.

        Args:
            eeg_data: EEG data sample
        """
        # Convert data to the format expected by LSL
        # For example, extract the EEG channel data as a list
        if isinstance(eeg_data, np.ndarray):
            # Use as is if it's already a numpy array
            sample = eeg_data.tolist()
        elif hasattr(eeg_data, "channels_data"):
            # Extract channels data if it's an EEG data object
            sample = eeg_data.channels_data
        else:
            # Try to convert to a list
            sample = list(eeg_data)

        # Push to LSL
        self.lsl_sync.push_eeg_data(sample)

    def _forward_input_event(self, input_event: Any) -> None:
        """
        Forward input event to LSL stream.

        Args:
            input_event: Input event data
        """
        # Convert input event to a numeric representation
        # Create a fixed-size vector representing the event
        # For example: [timestamp, event_type_code, key_code, x, y, button, ...]

        # Initialize with zeros
        input_data = [0.0] * 20  # Match the channel count in initialize_streams

        # Set common fields
        input_data[0] = input_event.timestamp

        # Set event type code
        event_types = {
            "key_press": 1,
            "key_release": 2,
            "mouse_move": 3,
            "mouse_click": 4,
            "mouse_scroll": 5,
            "none": 0,
        }
        input_data[1] = event_types.get(input_event.event_type, 0)

        # Set key code if relevant
        if input_event.key:
            # Simplified encoding of key values
            # In a real implementation, you'd want a more mapping
            try:
                # Remove 'Key.' prefix if present and encode first character
                key_str = input_event.key.replace("Key.", "")
                input_data[2] = ord(key_str[0]) if key_str else 0
            except:
                input_data[2] = 0

        # Set mouse position and button if relevant
        if input_event.mouse_x is not None:
            input_data[3] = input_event.mouse_x
        if input_event.mouse_y is not None:
            input_data[4] = input_event.mouse_y

        if input_event.button_pressed:
            # Encode button press
            button_types = {"Button.left": 1, "Button.right": 2, "Button.middle": 3}
            input_data[5] = button_types.get(input_event.button_pressed, 0)

        # Set mouse movement attributes if relevant
        if input_event.speed is not None:
            input_data[6] = input_event.speed
        if input_event.speed_x is not None:
            input_data[7] = input_event.speed_x
        if input_event.speed_y is not None:
            input_data[8] = input_event.speed_y

        # Additional mouse movement data
        if input_event.mouse_delta_x is not None:
            input_data[9] = input_event.mouse_delta_x
        if input_event.mouse_delta_y is not None:
            input_data[10] = input_event.mouse_delta_y

        # Active keys bitmap (simplified - in real implementation you'd want a better encoding)
        if input_event.active_keys:
            for i, key in enumerate(
                input_event.active_keys[:8]
            ):  # Store up to 8 active keys
                try:
                    # Simple encoding - just first character ASCII value
                    key_str = key.replace("Key.", "")
                    input_data[11 + i] = ord(key_str[0]) if key_str else 0
                except:
                    input_data[11 + i] = 0

        # Push to LSL
        self.lsl_sync.push_input_data(input_data)

    def check_components_status(self) -> None:
        """Periodically check the status of both components."""
        # Check if EEG board is connected and update LSL if needed
        eeg_connected = self.eeg_processor["collector_service"].is_connected()
        eeg_streaming = (
            self.eeg_processor["collector_service"].is_streaming_active()
            if eeg_connected
            else False
        )

        # Check if input collection is active
        input_active = True  # Input collection is always available

        # Re-initialize LSL if EEG configuration has changed
        if eeg_connected and not self.lsl_sync.eeg_outlet:
            self._initialize_lsl()

    def start_recording(self, config: Dict[str, Any]) -> bool:
        """
        Start recording on both modules if enabled.

        Args:
            config: Dictionary with recording configuration

        Returns:
            bool: True if recording started successfully
        """
        success = True

        # Create recording directory if needed
        if config["save_directory"]:
            directory = config["save_directory"]
            os.makedirs(directory, exist_ok=True)
        else:
            # Create a timestamped directory in the current directory
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            directory = os.path.join("recordings", f"session_{timestamp}")
            os.makedirs(directory, exist_ok=True)

        self.recording_directory = directory

        # Start LSL recording for synchronized data
        lsl_recording_success = self.lsl_sync.start_recording()
        success = success and lsl_recording_success

        # Start input collector recording if enabled
        if config["record_input"]:
            input_success = self._start_input_recording(config, directory)
            success = success and input_success

        # Start EEG recording if enabled
        if config["record_eeg"]:
            eeg_success = self._start_eeg_recording(config, directory)
            success = success and eeg_success

        # Record start time if any recording was successful
        if success:
            self.recording_start_time = time.time()

        return success

    def _start_input_recording(self, config: Dict[str, Any], directory: str) -> bool:
        """
        Start input collector recording.

        Args:
            config: Recording configuration
            directory: Directory to save files

        Returns:
            bool: True if successful
        """
        try:
            # Configure input logging
            logging_manager = self.input_collector["logging_manager"]

            # Configure JSON logging if needed
            if config["input_json"]:
                logging_manager.set_json_logging(True)

            # Configure CSV logging if needed
            if config["input_csv"]:
                csv_path = os.path.join(directory, "input_data.csv")
                logging_manager.csv_logger.set_filepath(csv_path)
                logging_manager.set_csv_logging(True, csv_path)

            # Get app coordinator and start recording
            app_coordinator = self.input_collector["app_coordinator"]

            # Don't allow recording if in edit mode
            if app_coordinator.edit_mode:
                self.status_message.emit(
                    "Cannot start recording while in edit mode", "warning"
                )
                return False

            # Toggle recording state through the coordinator
            if not app_coordinator.is_recording:
                app_coordinator.toggle_recording()
                return app_coordinator.is_recording

            return True

        except Exception as e:
            self.status_message.emit(
                f"Error starting input recording: {str(e)}", "error"
            )
            return False

    def _start_eeg_recording(self, config: Dict[str, Any], directory: str) -> bool:
        """
        Start EEG recording.

        Args:
            config: Recording configuration
            directory: Directory to save files

        Returns:
            bool: True if successful
        """
        try:
            # Check if EEG collector is connected and streaming
            collector_service = self.eeg_processor["collector_service"]
            if not collector_service.is_connected():
                self.status_message.emit("EEG board not connected", "warning")
                return False

            if not collector_service.is_streaming_active():
                self.status_message.emit("EEG stream not active", "warning")
                return False

            # Configure recording based on data type setting
            recording_service = self.eeg_processor["recording_service"]
            eeg_filename = os.path.join(directory, "eeg_data.csv")

            # Start recording through the recording service
            success = recording_service.start_recording(
                collector_service.collector, eeg_filename, config["eeg_data_type"]
            )

            if not success:
                self.status_message.emit("Failed to start EEG recording", "error")

            return success

        except Exception as e:
            self.status_message.emit(f"Error starting EEG recording: {str(e)}", "error")
            return False

    def stop_recording(self) -> bool:
        """
        Stop recording on both modules.

        Returns:
            bool: True if recording stopped successfully
        """
        success = True

        # Stop LSL recording
        lsl_success = self.lsl_sync.stop_recording()
        success = success and lsl_success

        # Stop input collector recording
        input_success = self._stop_input_recording()
        success = success and input_success

        # Stop EEG recording
        eeg_success = self._stop_eeg_recording()
        success = success and eeg_success

        # Export synchronized dataset
        if lsl_success and self.recording_directory:
            # Export CSV by default
            dataset_path = os.path.join(
                self.recording_directory, "synchronized_dataset"
            )
            self.lsl_sync.export_dataset("csv", dataset_path)

            # Export HDF5 if available
            try:
                import h5py

                self.lsl_sync.export_dataset("hdf5", dataset_path)
            except ImportError:
                pass

        # Reset recording state
        self.recording_start_time = 0

        return success

    def _stop_input_recording(self) -> bool:
        """
        Stop input collector recording.

        Returns:
            bool: True if successful
        """
        try:
            # Get app coordinator
            app_coordinator = self.input_collector["app_coordinator"]

            # Toggle recording state through the coordinator if recording
            if app_coordinator.is_recording:
                app_coordinator.toggle_recording()
                return not app_coordinator.is_recording

            return True

        except Exception as e:
            self.status_message.emit(
                f"Error stopping input recording: {str(e)}", "error"
            )
            return False

    def _stop_eeg_recording(self) -> bool:
        """
        Stop EEG recording.

        Returns:
            bool: True if successful
        """
        try:
            # Check if EEG is recording
            recording_service = self.eeg_processor["recording_service"]
            collector_service = self.eeg_processor["collector_service"]

            if recording_service.is_recording():
                success = recording_service.stop_recording(collector_service.collector)

                if not success:
                    self.status_message.emit("Failed to stop EEG recording", "error")

                return success

            return True

        except Exception as e:
            self.status_message.emit(f"Error stopping EEG recording: {str(e)}", "error")
            return False

    def add_marker(self, marker_value: Any) -> bool:
        """
        Add a marker to both recordings.

        Args:
            marker_value: Value of the marker

        Returns:
            bool: True if marker added successfully
        """
        success = True

        # Add marker to LSL stream
        lsl_success = self.lsl_sync.push_marker(marker_value)
        success = success and lsl_success

        # Add marker to EEG recording if active
        recording_service = self.eeg_processor["recording_service"]
        collector_service = self.eeg_processor["collector_service"]

        if recording_service.is_recording():
            eeg_success = recording_service.insert_marker(
                collector_service.collector, marker_value
            )
            success = success and eeg_success

        # Input collector doesn't support markers directly
        # Additional custom marker handling could be added here

        return success

    def is_ready_for_recording(self) -> bool:
        """
        Check if the system is ready for recording.

        Returns:
            bool: True if ready for recording
        """
        # Check EEG processor is connected and streaming
        collector_service = self.eeg_processor["collector_service"]
        eeg_ready = (
            collector_service.is_connected() and collector_service.is_streaming_active()
        )

        # Input collector is always ready for recording
        input_ready = True

        # System is ready if at least one component is ready
        return eeg_ready or input_ready

    def get_recording_time(self) -> float:
        """
        Get the current recording time in seconds.

        Returns:
            float: Recording time in seconds
        """
        if self.recording_start_time > 0:
            return time.time() - self.recording_start_time
        return 0

    def get_eeg_ready_state(self) -> bool:
        """
        Get the ready state of the EEG processor.

        Returns:
            bool: True if EEG processor is ready for recording
        """
        collector_service = self.eeg_processor["collector_service"]
        return (
            collector_service.is_connected() and collector_service.is_streaming_active()
        )

    def get_input_ready_state(self) -> bool:
        """
        Get the ready state of the input collector.

        Returns:
            bool: True if input collector is ready for recording
        """
        # Input collector is always ready for recording
        return True

    def get_synchronized_data(self, max_samples: int = 100) -> Dict[str, Any]:
        """
        Get synchronized data for visualization.

        Args:
            max_samples: Maximum number of samples to return

        Returns:
            dict: Dictionary with synchronized data
        """
        # Get dataset preview from LSL sync service
        return self.lsl_sync.get_dataset_preview(max_samples)

    def cleanup(self) -> None:
        """Clean up resources."""
        # Clean up LSL sync service
        self.lsl_sync.cleanup()
