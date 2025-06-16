import logging
import threading
from typing import Dict, List, Any, Tuple, Callable, Optional

import numpy as np


class DataAccessService:
    """
    Service providing real-time access to EEG data stream.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "DataAccessService":
        """Get the singleton instance of the service."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = DataAccessService()
            return cls._instance

    def __init__(self) -> None:
        """Initialize the data access service."""
        self._data_lock = threading.Lock()
        self._metadata_lock = threading.Lock()

        # Current data buffer: 2D array (channels x samples), start empty
        self._current_data = np.zeros((0, 0))
        self._timestamps: List[int] = []
        # Maximum number of samples to keep (set after sampling_rate known)
        self._buffer_max_samples: Optional[int] = None

        # Reference to collector service for direct access when needed
        self._collector_service: Optional[Any] = None

        # Board and stream metadata
        self._metadata = {
            "sampling_rate": 0,
            "eeg_channels": [],
            "channel_names": [],
            "num_channels": 0,
            "board_id": -1,
            "board_name": "",
            "streaming": False,
            "last_update": 0,
        }

        # Registered callbacks for data updates
        self._callbacks: List[Optional[Callable[[np.ndarray, List[int]], None]]] = []
        self._callback_lock = threading.Lock()

        # Filter settings and processor service for optional filtering
        self._filter_settings: Optional[Dict[str, Any]] = None
        self._filters_enabled = False
        self._processor_service: Optional[Any] = None

        # Initialize collector reference (will be set properly when collector starts)
        self._init_collector_reference()

        logging.info("Data access service initialized")

    def _init_collector_reference(self) -> None:
        """Initialize reference to collector service (if available)."""
        try:
            from .collector_service import CollectorService

            self._collector_service = CollectorService.get_instance()
            logging.info("Connected to collector service")
        except Exception as e:
            logging.debug(f"Could not connect to collector service: {e}")

    def set_filter_processor(self, processor_service: Any) -> None:
        """Set the processor service for applying filters."""
        self._processor_service = processor_service
        logging.info("Filter processor service set for DataAccessService")

    def enable_filters(
        self, enabled: bool, filter_settings: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Enable or disable filters for data served by this service.

        Args:
            enabled: Whether to enable filters
            filter_settings: Filter configuration (if None, will use existing settings)
        """
        with self._data_lock:
            self._filters_enabled = enabled
            if filter_settings is not None:
                self._filter_settings = filter_settings

        action = "enabled" if enabled else "disabled"
        logging.info(f"DataAccessService filters {action}")

    def update_filter_settings(self, filter_settings: Dict[str, Any]) -> None:
        """Update filter settings."""
        with self._data_lock:
            self._filter_settings = filter_settings
        logging.debug("DataAccessService filter settings updated")

    def _apply_filters_if_enabled(self, data: np.ndarray) -> np.ndarray:
        """Apply filters to data if enabled and processor is available."""
        if not self._filters_enabled or not self._processor_service or not self._filter_settings:
            return data

        if data.size == 0:
            return data

        try:
            filtered_data = data.copy()
            
            logging.debug(f"Applying filters to data shape {data.shape}")
            
            # Initialize processor if not already done
            if not hasattr(self._processor_service, 'processor') or self._processor_service.processor is None:
                # Try to get sampling rate from metadata
                sampling_rate = self._metadata.get("sampling_rate", 250)
                if sampling_rate > 0:
                    self._processor_service.initialize_processor(int(sampling_rate))
                    logging.info(f"Auto-initialized processor with sampling rate {sampling_rate} Hz for filtering")
                else:
                    logging.warning("Cannot initialize processor: no valid sampling rate")
                    return data
            
            # Apply bandpass filter if enabled
            if self._filter_settings.get("bandpass", {}).get("enabled", False):
                bp = self._filter_settings["bandpass"]
                low_cut = bp.get("low_cut", bp.get("low", 1.0))
                high_cut = bp.get("high_cut", bp.get("high", 50.0))
                logging.debug(f"Applying bandpass filter {low_cut}-{high_cut} Hz")
                filtered_data = self._processor_service.apply_bandpass_filter(
                    filtered_data, low_cut, high_cut
                )
                
            # Apply notch filter if enabled
            if self._filter_settings.get("notch", {}).get("enabled", False):
                notch = self._filter_settings["notch"]
                freq = notch.get("frequency", 50)
                logging.debug(f"Applying notch filter {freq} Hz")
                filtered_data = self._processor_service.apply_notch_filter(
                    filtered_data, freq
                )
                
            # Apply detrend if enabled
            if self._filter_settings.get("detrend", False):
                logging.debug("Applying detrend")
                filtered_data = self._processor_service.apply_detrend(filtered_data)
                
            logging.debug("Filters applied successfully in DataAccessService")
            return filtered_data
            
        except Exception as e:
            logging.error(f"Error applying filters in DataAccessService: {e}")
            return data

    def update_data(self, data: np.ndarray, timestamps: List[int]) -> None:
        """Update the current data buffer."""
        with self._data_lock:
            # Append new data to buffer
            if (
                self._current_data.size == 0
                or self._current_data.shape[0] != data.shape[0]
            ):
                # Initialize or reset buffer if channel count changes
                self._current_data = data.copy()
                self._timestamps = timestamps.copy()
            else:
                # Concatenate along time axis
                self._current_data = np.concatenate((self._current_data, data), axis=1)
                self._timestamps.extend(timestamps)
            # Trim oldest samples if exceeding buffer size
            if (
                self._buffer_max_samples
                and self._current_data.shape[1] > self._buffer_max_samples
            ):
                excess = self._current_data.shape[1] - self._buffer_max_samples
                self._current_data = self._current_data[:, excess:]
                self._timestamps = self._timestamps[excess:]

        # Notify registered callbacks
        self._notify_callbacks(data, timestamps)

    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update stream metadata."""
        with self._metadata_lock:
            self._metadata.update(metadata)
            # Initialize buffer max length when sampling_rate is first known
            sr = self._metadata.get("sampling_rate", 0)
            if sr and not self._buffer_max_samples:
                # Keep 10 seconds of data by default
                if isinstance(sr, (int, float)):
                    self._buffer_max_samples = int(sr) * 10

    def get_current_data(self) -> Tuple[np.ndarray, List[int]]:
        """Get the current data and timestamps, optionally filtered."""
        with self._data_lock:
            raw_data = self._current_data.copy()
            timestamps = self._timestamps.copy()
            
            # Apply filters if enabled
            if self._filters_enabled and raw_data.size > 0:
                logging.debug("DataAccessService: Applying filters to current data")
                filtered_data = self._apply_filters_if_enabled(raw_data)
                if not np.array_equal(filtered_data, raw_data):
                    logging.debug("DataAccessService: Data was successfully filtered")
                else:
                    logging.debug("DataAccessService: Data was not changed by filters")
                return filtered_data, timestamps
            else:
                logging.debug("DataAccessService: Returning raw data (filters disabled)")
                return raw_data, timestamps

    def get_raw_data(self) -> Tuple[np.ndarray, List[int]]:
        """Get the current raw data and timestamps without any filtering."""
        with self._data_lock:
            return self._current_data.copy(), self._timestamps.copy()

    def get_metadata(self) -> Dict[str, Any]:
        """Get the current stream metadata."""
        with self._metadata_lock:
            metadata = self._metadata.copy()

            # If we have a collector service and metadata is missing critical info, try to get it directly
            if self._collector_service and (
                metadata.get("sampling_rate", 0) == 0
                or not metadata.get("channel_names")
            ):
                self._update_metadata_from_collector(metadata)

            return metadata

    def _update_metadata_from_collector(self, metadata: Dict[str, Any]) -> None:
        """Update metadata from collector if available."""
        try:
            # Get active collector
            collector = self._get_active_collector()
            if not collector:
                return

            # Update sampling rate if missing
            if metadata.get("sampling_rate", 0) == 0 and hasattr(
                collector, "sampling_rate"
            ):
                metadata["sampling_rate"] = collector.sampling_rate

            # Update channel names if missing
            if not metadata.get("channel_names") and hasattr(collector, "eeg_names"):
                metadata["channel_names"] = collector.eeg_names

            # Update EEG channels if missing
            if not metadata.get("eeg_channels") and hasattr(collector, "eeg_channels"):
                metadata["eeg_channels"] = collector.eeg_channels

            # Update board info if missing
            if metadata.get("board_id", -1) == -1 and hasattr(collector, "board_id"):
                metadata["board_id"] = collector.board_id

            # Update board name if missing
            if not metadata.get("board_name") and hasattr(collector, "device_name"):
                metadata["board_name"] = collector.device_name

            # Update preset if missing
            if not metadata.get("preset") and hasattr(collector, "preset"):
                metadata["preset"] = collector.preset

            # Update streaming status
            if hasattr(collector, "is_streaming"):
                metadata["streaming"] = collector.is_streaming

            # Store the entire board_info for convenience if available
            if hasattr(collector, "get_device_info") or hasattr(
                collector, "get_board_info"
            ):
                try:
                    if hasattr(collector, "get_device_info"):
                        metadata["board_info"] = collector.get_device_info()
                    elif hasattr(collector, "get_board_info"):
                        metadata["board_info"] = collector.get_board_info()
                except Exception as e:
                    logging.debug(f"Error getting board info: {e}")
        except Exception as e:
            logging.debug(f"Error updating metadata from collector: {e}")

    def _get_active_collector(self) -> Optional[Any]:
        """Get the active collector from collector service."""
        if not self._collector_service:
            return None

        try:
            # Different possible attribute names in collector service
            if hasattr(self._collector_service, "collector"):
                return self._collector_service.collector
            elif hasattr(self._collector_service, "active_collector"):
                return self._collector_service.active_collector

            # Try to get from collectors dict
            if hasattr(self._collector_service, "_collectors"):
                collectors = self._collector_service._collectors
                active_id = getattr(
                    self._collector_service, "_active_collector_id", None
                )
                if active_id and active_id in collectors:
                    return collectors[active_id]
        except Exception as e:
            logging.debug(f"Error getting active collector: {e}")

        return None

    def get_channel_data(self, channel_index: int) -> Tuple[np.ndarray, List[int]]:
        """Get data for a specific channel, optionally filtered."""
        with self._data_lock:
            if (
                self._current_data.size == 0
                or channel_index >= self._current_data.shape[0]
            ):
                return np.array([]), []

            raw_data = self._current_data.copy()
            timestamps = self._timestamps.copy()

            # Apply filters if enabled
            if self._filters_enabled and raw_data.size > 0:
                filtered_data = self._apply_filters_if_enabled(raw_data)
                return filtered_data[channel_index].copy(), timestamps
            else:
                return raw_data[channel_index].copy(), timestamps

    def get_channel_names(self) -> List[str]:
        """Get names of all channels."""
        with self._metadata_lock:
            names = self._metadata.get("channel_names", [])
            if isinstance(names, list):
                names = names.copy()
            else:
                names = []

            # If names are empty, try to get from collector
            if not names:
                collector = self._get_active_collector()
                if collector and hasattr(collector, "eeg_names"):
                    eeg_names = collector.eeg_names
                    if isinstance(eeg_names, list):
                        names = eeg_names

                # If still empty, try to generate generic names based on channels
                if not names:
                    eeg_channels = self._metadata.get("eeg_channels", [])
                    if eeg_channels and isinstance(eeg_channels, list):
                        names = [f"CH{i+1}" for i in range(len(eeg_channels))]

            return names

    def get_sampling_rate(self) -> float:
        """Get the sampling rate."""
        with self._metadata_lock:
            rate = self._metadata.get("sampling_rate", 0)
            if not isinstance(rate, (int, float)):
                rate = 0

            # If rate is 0, try to get directly from collector
            if rate == 0:
                collector = self._get_active_collector()
                if collector and hasattr(collector, "sampling_rate"):
                    collector_rate = collector.sampling_rate
                    if isinstance(collector_rate, (int, float)):
                        rate = float(collector_rate)
                        # Update metadata for future calls
                        self._metadata["sampling_rate"] = rate

            return float(rate)

    def is_streaming(self) -> bool:
        """Check if streaming is active."""
        with self._metadata_lock:
            streaming = self._metadata.get("streaming", False)
            if not isinstance(streaming, bool):
                streaming = False

            # If not streaming according to metadata, check directly
            if not streaming:
                collector = self._get_active_collector()
                if collector and hasattr(collector, "is_streaming"):
                    collector_streaming = collector.is_streaming
                    if isinstance(collector_streaming, bool):
                        streaming = collector_streaming
                        # Update metadata
                        self._metadata["streaming"] = streaming

            return streaming

    def register_callback(
        self, callback: Callable[[np.ndarray, List[int]], None]
    ) -> int:
        """Register a callback function to be called when new data arrives."""
        with self._callback_lock:
            callback_id = len(self._callbacks)
            self._callbacks.append(callback)
            return callback_id

    def unregister_callback(self, callback_id: int) -> bool:
        """Unregister a previously registered callback."""
        with self._callback_lock:
            if 0 <= callback_id < len(self._callbacks):
                self._callbacks[callback_id] = None
                return True
            return False

    def _notify_callbacks(self, data: np.ndarray, timestamps: List[int]) -> None:
        """Notify all registered callbacks of new data."""
        with self._callback_lock:
            for callback in self._callbacks:
                if callback is not None:
                    try:
                        # FIXED: Use get_current_data() to ensure same filtering as API calls
                        # This prevents double filtering since get_current_data() already applies filters
                        current_data, current_timestamps = self.get_current_data()
                        
                        # Send the most recent data that matches the new data length
                        if current_data.size > 0 and data.size > 0:
                            # Get the same amount of recent data as was just added
                            samples_to_send = min(data.shape[1], current_data.shape[1])
                            callback_data = current_data[:, -samples_to_send:]
                            callback_timestamps = current_timestamps[-samples_to_send:]
                            
                            callback(callback_data, callback_timestamps)
                            if self._filters_enabled:
                                logging.debug("Sent filtered data to callback (same as get_current_data)")
                            else:
                                logging.debug("Sent raw data to callback (same as get_current_data)")
                        else:
                            # Fallback to original data if no current data available
                            callback(data, timestamps)
                            logging.debug("Sent fallback data to callback")
                            
                    except Exception as e:
                        logging.error(f"Error in data access callback: {e}")
