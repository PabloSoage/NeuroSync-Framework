import logging
import time
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
from brainflow.board_shim import (
    BoardShim,
    BrainFlowInputParams,
    BoardIds,
    BrainFlowPresets,
)
from brainflow.exit_codes import BrainFlowError, BrainFlowExitCodes

from ..interfaces.collector_interface import (
    CollectorInterface,
    MarkerInterface,
    ConfigurableCollectorInterface,
)


class EEGCollector(
    CollectorInterface,
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

        # Validate that the requested preset is available
        if self.preset not in self.available_presets:
            logging.warning(
                f"Requested preset {self.preset} not available for board {self.board_id}. Using default preset."
            )
            self.preset = BrainFlowPresets.DEFAULT_PRESET.value

        # FIXED: Special handling for streaming board - inherit from master board if specified
        master_board_id = None
        if hasattr(self.params, "master_board") and self.params.master_board:
            master_board_id = self.params.master_board
            logging.info(
                f"Streaming board detected with master board: {master_board_id}"
            )

        # Get board information using the ACTUAL preset, with master board fallback
        logging.info(f"Initializing board info for preset {self.preset}")

        try:
            self.sampling_rate = BoardShim.get_sampling_rate(self.board_id, self.preset)
            logging.info(
                f"Sampling rate for preset {self.preset}: {self.sampling_rate}"
            )
        except Exception as e:
            logging.warning(
                f"Could not get sampling rate for preset {self.preset}: {e}"
            )
            # FIXED: For streaming board, try to get from master board
            if master_board_id:
                try:
                    self.sampling_rate = BoardShim.get_sampling_rate(
                        master_board_id, self.preset
                    )
                    logging.info(
                        f"Using sampling rate from master board {master_board_id}: {self.sampling_rate}"
                    )
                except Exception as e2:
                    logging.warning(
                        f"Could not get sampling rate from master board: {e2}"
                    )
                    self.sampling_rate = 250  # Default
            else:
                # Try with default preset as fallback
                try:
                    self.sampling_rate = BoardShim.get_sampling_rate(
                        self.board_id, BrainFlowPresets.DEFAULT_PRESET
                    )
                    logging.info(
                        f"Using sampling rate from default preset: {self.sampling_rate}"
                    )
                except Exception as e2:
                    logging.error(
                        f"Could not get sampling rate even with default preset: {e2}"
                    )
                    self.sampling_rate = 250  # Reasonable default

        try:
            self.eeg_channels = BoardShim.get_eeg_channels(self.board_id, self.preset)
            logging.info(f"EEG channels for preset {self.preset}: {self.eeg_channels}")
        except Exception as e:
            logging.warning(f"Could not get EEG channels for preset {self.preset}: {e}")
            # FIXED: For streaming board, try to get from master board
            if master_board_id:
                try:
                    self.eeg_channels = BoardShim.get_eeg_channels(
                        master_board_id, self.preset
                    )
                    logging.info(
                        f"Using EEG channels from master board {master_board_id}: {self.eeg_channels}"
                    )
                except Exception as e2:
                    logging.warning(
                        f"Could not get EEG channels from master board: {e2}"
                    )
                    self.eeg_channels = []
            else:
                # For auxiliary presets, EEG channels might not exist - this is normal
                if self.preset == BrainFlowPresets.AUXILIARY_PRESET.value:
                    logging.info(
                        "Auxiliary preset typically has no EEG channels - this is expected"
                    )
                    self.eeg_channels = []
                else:
                    # Try with default preset as fallback
                    try:
                        self.eeg_channels = BoardShim.get_eeg_channels(
                            self.board_id, BrainFlowPresets.DEFAULT_PRESET
                        )
                        logging.info(
                            f"Using EEG channels from default preset: {self.eeg_channels}"
                        )
                    except Exception as e2:
                        logging.warning(
                            f"Could not get EEG channels even with default preset: {e2}"
                        )
                        self.eeg_channels = []

        # Get other channels using master board info if needed
        try:
            self.timestamp_channel = BoardShim.get_timestamp_channel(
                self.board_id, self.preset
            )
        except Exception as e:
            logging.warning(
                f"Could not get timestamp channel for preset {self.preset}: {e}"
            )
            if master_board_id:
                try:
                    self.timestamp_channel = BoardShim.get_timestamp_channel(
                        master_board_id, self.preset
                    )
                    logging.info(
                        f"Using timestamp channel from master board: {self.timestamp_channel}"
                    )
                except:
                    self.timestamp_channel = -1
            else:
                try:
                    self.timestamp_channel = BoardShim.get_timestamp_channel(
                        self.board_id, BrainFlowPresets.DEFAULT_PRESET
                    )
                except:
                    self.timestamp_channel = -1

        try:
            self.marker_channel = BoardShim.get_marker_channel(
                self.board_id, self.preset
            )
        except Exception as e:
            logging.warning(
                f"Could not get marker channel for preset {self.preset}: {e}"
            )
            if master_board_id:
                try:
                    self.marker_channel = BoardShim.get_marker_channel(
                        master_board_id, self.preset
                    )
                    logging.info(
                        f"Using marker channel from master board: {self.marker_channel}"
                    )
                except:
                    self.marker_channel = -1
            else:
                try:
                    self.marker_channel = BoardShim.get_marker_channel(
                        self.board_id, BrainFlowPresets.DEFAULT_PRESET
                    )
                except:
                    self.marker_channel = -1

        # Get additional channel types - use master board info if available
        try:
            self.exg_channels = BoardShim.get_exg_channels(self.board_id, self.preset)
        except:
            if master_board_id:
                try:
                    self.exg_channels = BoardShim.get_exg_channels(
                        master_board_id, self.preset
                    )
                except:
                    self.exg_channels = self.eeg_channels
            else:
                self.exg_channels = self.eeg_channels

        # CRITICAL FIX: Get other channel types with CORRECT preset
        self.channel_types = {
            "eeg": self.eeg_channels,
            "emg": self._get_channels_safely(
                BoardShim.get_emg_channels, "EMG", master_board_id
            ),
            "ecg": self._get_channels_safely(
                BoardShim.get_ecg_channels, "ECG", master_board_id
            ),
            "eog": self._get_channels_safely(
                BoardShim.get_eog_channels, "EOG", master_board_id
            ),
            "eda": self._get_channels_safely(
                BoardShim.get_eda_channels, "EDA", master_board_id
            ),
            "ppg": self._get_channels_safely(
                BoardShim.get_ppg_channels, "PPG", master_board_id
            ),
            "accel": self._get_channels_safely(
                BoardShim.get_accel_channels, "Accel", master_board_id
            ),
            "gyro": self._get_channels_safely(
                BoardShim.get_gyro_channels, "Gyro", master_board_id
            ),
            "temperature": self._get_channels_safely(
                BoardShim.get_temperature_channels, "Temperature", master_board_id
            ),
            "resistance": self._get_channels_safely(
                BoardShim.get_resistance_channels, "Resistance", master_board_id
            ),
            "other": self._get_channels_safely(
                BoardShim.get_other_channels, "Other", master_board_id
            ),
        }

        # Log detected channel types for debugging
        for ch_type, channels in self.channel_types.items():
            if channels:
                logging.info(
                    f"Detected {ch_type} channels for preset {self.preset}: {channels}"
                )

        # Try to get EEG names with master board fallback
        try:
            self.eeg_names = BoardShim.get_eeg_names(self.board_id, self.preset)
            if isinstance(self.eeg_names, str):
                self.eeg_names = self.eeg_names.split(",")
            logging.info(f"EEG names for preset {self.preset}: {self.eeg_names}")
        except Exception as e:
            logging.debug(f"Could not get EEG names for preset {self.preset}: {e}")
            # FIXED: Try master board for EEG names
            if master_board_id:
                try:
                    self.eeg_names = BoardShim.get_eeg_names(
                        master_board_id, self.preset
                    )
                    if isinstance(self.eeg_names, str):
                        self.eeg_names = self.eeg_names.split(",")
                    logging.info(
                        f"Using EEG names from master board {master_board_id}: {self.eeg_names}"
                    )
                except Exception as e2:
                    logging.debug(f"Could not get EEG names from master board: {e2}")
                    # Generate generic names based on available channels
                    if self.eeg_channels:
                        self.eeg_names = [
                            f"Channel {i}" for i in range(len(self.eeg_channels))
                        ]
                    else:
                        self.eeg_names = []
            else:
                # For auxiliary presets, EEG names might not exist - this is normal
                if self.preset == BrainFlowPresets.AUXILIARY_PRESET.value:
                    logging.info(
                        "Auxiliary preset typically has no EEG names - this is expected"
                    )
                    self.eeg_names = []
                else:
                    # Try with default preset
                    try:
                        self.eeg_names = BoardShim.get_eeg_names(
                            self.board_id, BrainFlowPresets.DEFAULT_PRESET
                        )
                        if isinstance(self.eeg_names, str):
                            self.eeg_names = self.eeg_names.split(",")
                    except:
                        # Generate generic names based on available channels
                        if self.eeg_channels:
                            self.eeg_names = [
                                f"Channel {i}" for i in range(len(self.eeg_channels))
                            ]
                        else:
                            self.eeg_names = []

        # Get device name
        try:
            self.device_name = BoardShim.get_device_name(self.board_id)
            if master_board_id:
                try:
                    master_name = BoardShim.get_device_name(master_board_id)
                    self.device_name = f"{self.device_name} (Master: {master_name})"
                except:
                    pass
        except:
            self.device_name = f"Board ID {self.board_id}"

        # Get number of rows with master board fallback
        try:
            self.num_rows = BoardShim.get_num_rows(self.board_id, self.preset)
            logging.info(f"Number of rows for preset {self.preset}: {self.num_rows}")
        except Exception as e:
            logging.warning(
                f"Could not get number of rows for preset {self.preset}: {e}"
            )
            if master_board_id:
                try:
                    self.num_rows = BoardShim.get_num_rows(master_board_id, self.preset)
                    logging.info(
                        f"Using number of rows from master board: {self.num_rows}"
                    )
                except:
                    self.num_rows = (
                        len(self.eeg_channels) + 2
                    )  # EEG channels + timestamp + marker
            else:
                try:
                    self.num_rows = BoardShim.get_num_rows(
                        self.board_id, BrainFlowPresets.DEFAULT_PRESET
                    )
                except:
                    self.num_rows = (
                        len(self.eeg_channels) + 2
                    )  # EEG channels + timestamp + marker

        logging.info(
            f"BrainFlow Collector initialized with board_id: {self.board_id}, preset: {self.preset}"
        )
        if master_board_id:
            logging.info(
                f"Using master board {master_board_id} for channel configuration"
            )
        logging.info(
            f"Device: {self.device_name}, Sampling rate: {self.sampling_rate}Hz"
        )
        logging.info(f"EEG channels: {self.eeg_channels}")
        logging.info(
            f"Channel types detected: {[k for k, v in self.channel_types.items() if v]}"
        )
        logging.info(f"Available presets: {self.available_presets}")

    def _get_channels_safely(
        self,
        channel_func: Any,
        channel_type: str,
        master_board_id: Optional[int] = None,
    ) -> List[int]:
        """
        Safely get channels of a specific type, handling exceptions.

        Args:
            channel_func: The BoardShim function to call
            channel_type: The type of channel (for logging)
            master_board_id: Optional master board ID for fallback

        Returns:
            List of channel indices
        """
        try:
            # Try with current board and preset first
            channels = channel_func(self.board_id, self.preset)

            # VALIDATION: Filter out invalid "other" channels for auxiliary presets
            if (
                channel_type == "Other"
                and self.preset == BrainFlowPresets.AUXILIARY_PRESET.value
            ):
                if channels:
                    logging.info(
                        f"Found {len(channels)} {channel_type} channels for preset {self.preset}, but filtering them out as they typically contain invalid data"
                    )
                return []  # Return empty list for "other" channels in auxiliary preset

            if channels:
                logging.debug(
                    f"Found {channel_type} channels for preset {self.preset}: {channels}"
                )
            return channels
        except Exception as e:
            logging.debug(
                f"No {channel_type} channels available for preset {self.preset}: {e}"
            )

            # FIXED: Try master board if available
            if master_board_id:
                try:
                    channels = channel_func(master_board_id, self.preset)
                    if channels:
                        logging.debug(
                            f"Using {channel_type} channels from master board {master_board_id}: {channels}"
                        )
                    return channels
                except Exception as e2:
                    logging.debug(
                        f"No {channel_type} channels available from master board: {e2}"
                    )

            # ONLY fallback to default preset if we're not already using auxiliary preset
            # For auxiliary preset, it's normal that some channel types don't exist
            if self.preset != BrainFlowPresets.AUXILIARY_PRESET.value:
                try:
                    channels = channel_func(
                        self.board_id, BrainFlowPresets.DEFAULT_PRESET
                    )
                    if channels:
                        logging.debug(
                            f"Using {channel_type} channels from default preset: {channels}"
                        )
                    return channels
                except Exception as e2:
                    logging.debug(
                        f"No {channel_type} channels available even with default preset: {e2}"
                    )
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
                # Get all data and remove it from the buffer
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
