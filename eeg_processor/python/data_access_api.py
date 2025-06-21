"""
API for accessing real-time EEG data streams.

This module provides a clean interface for accessing EEG data and metadata
in real-time with minimal overhead.
"""

import logging
from typing import Dict, List, Any, Tuple, Callable, Optional

import numpy as np

from .services.data_access_service import DataAccessService


class EEGDataAPI:
    """
    Main API for accessing EEG data.

    This class provides methods to access real-time EEG data and metadata.
    """

    _signal_processor_cache = None
    _signal_processor_sampling_rate = None

    @staticmethod
    def get_current_data() -> Tuple[np.ndarray, List[int]]:
        """
        Get the current EEG data and timestamps.

        NOTE: This returns FILTERED data if filters are enabled in DataAccessService,
        RAW data if filters are disabled. Use get_raw_data() for always unfiltered data.

        Returns:
            Tuple of (data_array, timestamps)
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_current_data()

    @staticmethod
    def get_raw_data() -> Tuple[np.ndarray, List[int]]:
        """
        Get the current raw EEG data and timestamps (unfiltered).

        Returns:
            Tuple of (data_array, timestamps)
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_raw_data()

    @staticmethod
    def get_channel_data(channel_index: int) -> Tuple[np.ndarray, List[int]]:
        """
        Get data for a specific channel (potentially filtered).

        Args:
            channel_index: Index of the channel (1-based for external API)

        Returns:
            Tuple of (channel_data, timestamps)
        """
        # Convert from 1-based external index to 0-based internal index
        internal_index = channel_index - 1
        if internal_index < 0:
            return np.array([]), []

        data_access = DataAccessService.get_instance()
        return data_access.get_channel_data(internal_index)

    @staticmethod
    def get_channel_by_name(channel_name: str) -> Tuple[np.ndarray, List[int]]:
        """
        Get data for a channel by its name (potentially filtered).

        Args:
            channel_name: Name of the channel to get

        Returns:
            Tuple of (channel_data, timestamps)
        """
        data_access = DataAccessService.get_instance()
        channel_names = data_access.get_channel_names()

        if channel_name in channel_names:
            channel_index = channel_names.index(channel_name)
            return data_access.get_channel_data(channel_index)

        return np.array([]), []

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        """
        Get the current EEG stream metadata.

        Returns:
            Dictionary with metadata
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_metadata()

    @staticmethod
    def get_sampling_rate() -> float:
        """
        Get the sampling rate.

        Returns:
            Sampling rate in Hz
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_sampling_rate()

    @staticmethod
    def get_channel_names() -> List[str]:
        """
        Get names of all channels.

        Returns:
            List of channel names
        """
        data_access = DataAccessService.get_instance()
        return data_access.get_channel_names()

    @staticmethod
    def is_streaming() -> bool:
        """
        Check if streaming is active.

        Returns:
            True if streaming, False otherwise
        """
        data_access = DataAccessService.get_instance()
        return data_access.is_streaming()

    @staticmethod
    def register_data_callback(
        callback: Callable[[np.ndarray, List[int]], None],
    ) -> int:
        """
        Register a callback function to be called when new data arrives.

        Args:
            callback: Function to call with (data, timestamps)

        Returns:
            Callback ID for later unregistering
        """
        data_access = DataAccessService.get_instance()
        return data_access.register_callback(callback)

    @staticmethod
    def unregister_data_callback(callback_id: int) -> bool:
        """
        Unregister a previously registered callback.

        Args:
            callback_id: ID of the callback to remove

        Returns:
            True if successful, False otherwise
        """
        data_access = DataAccessService.get_instance()
        return data_access.unregister_callback(callback_id)

    @staticmethod
    def get_eeg_channels() -> List[int]:
        """
        Get the EEG channel indices.

        Returns:
            List of EEG channel indices
        """
        data_access = DataAccessService.get_instance()
        metadata = data_access.get_metadata()
        return metadata.get("eeg_channels", [])

    @staticmethod
    def get_board_info() -> Dict[str, Any]:
        """
        Get information about the connected board.

        Returns:
            Dictionary with board information
        """
        data_access = DataAccessService.get_instance()
        metadata = data_access.get_metadata()

        # Get the raw board info if available in metadata
        if "board_info" in metadata and isinstance(metadata["board_info"], dict):
            # Start with the complete board_info from the metadata
            board_info = metadata["board_info"].copy()
        else:
            # If not available, create from other metadata fields
            board_info = {
                "board_id": metadata.get("board_id", -1),
                "board_name": metadata.get("board_name", "Unknown"),
                "sampling_rate": metadata.get("sampling_rate", 0),
                "eeg_channels": metadata.get("eeg_channels", []),
                "channel_names": metadata.get("channel_names", []),
                "streaming": metadata.get("streaming", False),
            }

        return board_info

    @staticmethod
    def get_eeg_data(max_samples: Optional[int] = None) -> Tuple[np.ndarray, List[int]]:
        """
        Get EEG channel data only.

        NOTE: This returns FILTERED data if filters are enabled in DataAccessService.

        Args:
            max_samples: Maximum number of samples to return

        Returns:
            Tuple of (eeg_data, timestamps)
        """
        data_access = DataAccessService.get_instance()
        # Use get_current_data() which applies filters if enabled
        data, timestamps = data_access.get_current_data()
        metadata = data_access.get_metadata()

        eeg_channels = metadata.get("eeg_channels", [])

        if data.size > 0 and eeg_channels:
            # Filter to only include valid eeg channels
            valid_channels = [ch for ch in eeg_channels if ch < data.shape[0]]

            if valid_channels:
                eeg_data = data[valid_channels]

                # Apply max_samples limit if provided
                if max_samples and eeg_data.shape[1] > max_samples:
                    eeg_data = eeg_data[:, -max_samples:]
                    timestamps = timestamps[-max_samples:]

                return eeg_data, timestamps

        # Fallback: return empty data
        return np.array([]), []

    @staticmethod
    def get_board_preset() -> int:
        """
        Get the current board preset value.

        Returns:
            Preset value, or 0 if not available
        """
        data_access = DataAccessService.get_instance()
        metadata = data_access.get_metadata()
        return metadata.get("preset", 0)

    @staticmethod
    def get_all_channels_quality() -> Dict[int, float]:
        """
        Get signal quality for all EEG channels (using filtered data if enabled).

        Returns:
            Dictionary mapping 1-based channel indices to quality scores (0-1)
        """
        try:
            data_access = DataAccessService.get_instance()
            data, _ = data_access.get_current_data()
            metadata = data_access.get_metadata()

            if data.size == 0:
                return {}

            sampling_rate = metadata.get("sampling_rate", 250)
            eeg_channels = metadata.get("eeg_channels", [])

            # Fallback if no EEG channels defined
            if not eeg_channels and data.size > 0:
                eeg_channels = list(range(1, min(8, data.shape[0]) + 1))  # 1-based

            # Reuse signal processor if sampling rate hasn't changed
            if (EEGDataAPI._signal_processor_cache is None or 
                EEGDataAPI._signal_processor_sampling_rate != sampling_rate):
                from .processors.signal_processor import SignalProcessor
                EEGDataAPI._signal_processor_cache = SignalProcessor(sampling_rate)
                EEGDataAPI._signal_processor_sampling_rate = sampling_rate
                logging.debug(f"Created new SignalProcessor for sampling rate {sampling_rate}Hz")

            processor = EEGDataAPI._signal_processor_cache
            quality_values = {}

            for ch in eeg_channels:
                # ch is 1-based, so for numpy arrays use ch-1
                if 0 <= (ch - 1) < data.shape[0]:
                    try:
                        quality = processor.get_signal_quality(data, ch - 1)
                        quality_values[ch] = quality  # Key is 1-based
                    except Exception:
                        quality_values[ch] = 0.0

            return quality_values
        except Exception as e:
            logging.error(f"Error calculating channel quality: {e}")
            return {}

    @staticmethod
    def are_filters_enabled() -> bool:
        """
        Check if filters are currently enabled in DataAccessService.

        Returns:
            True if filters are enabled, False otherwise
        """
        data_access = DataAccessService.get_instance()
        return getattr(data_access, "_filters_enabled", False)

    @staticmethod
    def get_filter_settings() -> Optional[Dict[str, Any]]:
        """
        Get current filter settings from DataAccessService.

        Returns:
            Filter settings dictionary or None if no filters configured
        """
        data_access = DataAccessService.get_instance()
        filter_settings = getattr(data_access, "_filter_settings", None)
        if filter_settings:
            # Add the enabled status to the settings
            filter_settings_copy = filter_settings.copy()
            filter_settings_copy["enabled"] = getattr(
                data_access, "_filters_enabled", False
            )
            return filter_settings_copy
        return None
