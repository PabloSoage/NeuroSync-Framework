import logging
from typing import Dict, List, Any, Tuple, Optional

import numpy as np
from brainflow.data_filter import WaveletTypes, AggOperations

from ..processors.signal_processor import SignalProcessor


class ProcessorService:
    """
    Service for signal processing operations.

    This service encapsulates all signal processing functionality and provides
    a clean interface for filter application and metric calculation.
    """

    def __init__(self) -> None:
        """Initialize the processor service."""
        self.processor: Optional[SignalProcessor] = None
        self.sampling_rate = 0

    def initialize_processor(self, sampling_rate: int) -> None:
        """
        Initialize the signal processor with the specified sampling rate.

        Args:
            sampling_rate: Sample rate in Hz
        """
        self.sampling_rate = sampling_rate
        self.processor = SignalProcessor(sampling_rate)
        logging.info(f"Processor initialized with sampling rate {sampling_rate}Hz")

    def apply_bandpass_filter(
        self,
        data: np.ndarray,
        low_cutoff: float,
        high_cutoff: float,
        channels: Optional[List[int]] = None,
    ) -> np.ndarray:
        """
        Apply bandpass filter to the data.

        Args:
            data: Data to filter (2D array: channels x samples)
            low_cutoff: Low cutoff frequency in Hz
            high_cutoff: High cutoff frequency in Hz
            channels: Specific channels to filter (defaults to all)

        Returns:
            Filtered data
        """
        if self.processor is None:
            logging.warning("Processor not initialized for bandpass filter")
            return data

        try:
            # Ensure data is 2D
            if data.ndim == 1:
                data = data.reshape(1, -1)
            
            logging.debug(f"Applying bandpass filter {low_cutoff}-{high_cutoff} Hz to data shape {data.shape}")
            
            # Apply filter to specific channels or all data
            if channels is not None:
                filtered_data = data.copy()
                for channel in channels:
                    if channel < data.shape[0]:
                        # Apply filter to single channel
                        channel_data = data[channel:channel+1, :]  # Keep 2D
                        filtered_channel_data = self.processor.bandpass_filter(
                            channel_data, low_cutoff, high_cutoff, 4
                        )
                        filtered_data[channel:channel+1, :] = filtered_channel_data
                return filtered_data
            else:
                # Apply to all channels
                return self.processor.bandpass_filter(data, low_cutoff, high_cutoff, 4)
        except Exception as e:
            logging.error(f"Bandpass filter error: {e}")
            return data

    def apply_notch_filter(
        self, data: np.ndarray, notch_freq: float, channels: Optional[List[int]] = None
    ) -> np.ndarray:
        """
        Apply notch filter to the data.

        Args:
            data: Data to filter (2D array: channels x samples)
            notch_freq: Notch frequency in Hz
            channels: Specific channels to filter (defaults to all)

        Returns:
            Filtered data
        """
        if self.processor is None:
            logging.warning("Processor not initialized for notch filter")
            return data

        try:
            # Ensure data is 2D
            if data.ndim == 1:
                data = data.reshape(1, -1)
                
            logging.debug(f"Applying notch filter {notch_freq} Hz to data shape {data.shape}")
            
            # Use environmental noise removal which includes notch filtering
            if channels is not None:
                filtered_data = data.copy()
                for channel in channels:
                    if channel < data.shape[0]:
                        # Apply filter to single channel
                        channel_data = data[channel:channel+1, :]  # Keep 2D
                        filtered_channel_data = self.processor.remove_environmental_noise(
                            channel_data
                        )
                        filtered_data[channel:channel+1, :] = filtered_channel_data
                return filtered_data
            else:
                # Apply to all channels
                return self.processor.remove_environmental_noise(data)
        except Exception as e:
            logging.error(f"Notch filter error: {e}")
            # Fallback: try bandstop filter
            try:
                bandwidth = 2.0  # 2Hz bandwidth around notch frequency
                return self.apply_bandstop_filter(data, notch_freq - bandwidth/2, notch_freq + bandwidth/2, channels)
            except Exception as e2:
                logging.error(f"Bandstop fallback error: {e2}")
                return data

    def apply_bandstop_filter(
        self,
        data: np.ndarray,
        low_cutoff: float,
        high_cutoff: float,
        channels: Optional[List[int]] = None,
    ) -> np.ndarray:
        """
        Apply bandstop filter to the data.

        Args:
            data: Data to filter (2D array: channels x samples)
            low_cutoff: Low cutoff frequency in Hz
            high_cutoff: High cutoff frequency in Hz
            channels: Specific channels to filter (defaults to all)

        Returns:
            Filtered data
        """
        if self.processor is None:
            logging.warning("Processor not initialized for bandstop filter")
            return data

        try:
            # Ensure data is 2D
            if data.ndim == 1:
                data = data.reshape(1, -1)
                
            logging.debug(f"Applying bandstop filter {low_cutoff}-{high_cutoff} Hz to data shape {data.shape}")
            
            # Apply filter to specific channels or all data
            if channels is not None:
                filtered_data = data.copy()
                for channel in channels:
                    if channel < data.shape[0]:
                        # Apply filter to single channel
                        channel_data = data[channel:channel+1, :]  # Keep 2D
                        filtered_channel_data = self.processor.bandstop_filter(
                            channel_data, low_cutoff, high_cutoff, 4
                        )
                        filtered_data[channel:channel+1, :] = filtered_channel_data
                return filtered_data
            else:
                # Apply to all channels
                return self.processor.bandstop_filter(data, low_cutoff, high_cutoff, 4)
        except Exception as e:
            logging.error(f"Bandstop filter error: {e}")
            return data

    def apply_detrend(
        self, data: np.ndarray, channels: Optional[List[int]] = None
    ) -> np.ndarray:
        """
        Apply detrend operation to the data.

        Args:
            data: Data to detrend (2D array: channels x samples)
            channels: Specific channels to detrend (defaults to all)

        Returns:
            Detrended data
        """
        if self.processor is None:
            logging.warning("Processor not initialized for detrend")
            return data

        try:
            # Ensure data is 2D
            if data.ndim == 1:
                data = data.reshape(1, -1)
                
            logging.debug(f"Applying detrend to data shape {data.shape}")
            
            if channels is not None:
                detrended_data = data.copy()
                for channel in channels:
                    if channel < data.shape[0]:
                        # Apply detrend to single channel
                        channel_data = data[channel:channel+1, :]  # Keep 2D
                        detrended_channel_data = self.processor.detrend(channel_data)
                        detrended_data[channel:channel+1, :] = detrended_channel_data
                return detrended_data
            else:
                # Apply to all channels
                return self.processor.detrend(data)
        except Exception as e:
            logging.error(f"Detrend error: {e}")
            return data

    def apply_wavelet_denoising(
        self,
        data: np.ndarray,
        wavelet: WaveletTypes,
        channels: Optional[List[int]] = None,
    ) -> np.ndarray:
        """
        Apply wavelet denoising to the data.

        Args:
            data: Data to denoise
            wavelet: Wavelet type to use
            channels: Specific channels to denoise (defaults to all)

        Returns:
            Denoised data
        """
        if self.processor is None:
            logging.warning("Processor not initialized")
            return data

        try:
            if channels is not None:
                denoised_data = data.copy()
                channel_data = data[channels]
                denoised_channel_data = self.processor.denoise(channel_data, wavelet)
                denoised_data[channels] = denoised_channel_data
                return denoised_data
            else:
                return self.processor.denoise(data, wavelet)
        except Exception as e:
            logging.error(f"Wavelet denoising error: {e}")
            return data

    def apply_all_filters(
        self, data: np.ndarray, filters_config: Dict[str, Any]
    ) -> np.ndarray:
        """
        Apply multiple filters to the data based on configuration.

        Args:
            data: Data to filter
            filters_config: Dictionary with filter configurations

        Returns:
            Filtered data
        """
        if self.processor is None:
            logging.warning("Processor not initialized")
            return data

        try:
            filtered_data = data.copy()

            # Apply filters based on configuration
            if filters_config.get("bandpass"):
                bp_config = filters_config["bandpass"]
                filtered_data = self.apply_bandpass_filter(
                    filtered_data,
                    bp_config.get("low", 1.0),
                    bp_config.get("high", 50.0),
                    bp_config.get("channels"),
                )

            if filters_config.get("notch"):
                notch_config = filters_config["notch"]
                filtered_data = self.apply_notch_filter(
                    filtered_data,
                    notch_config.get("freq", 50.0),
                    notch_config.get("channels"),
                )

            if filters_config.get("detrend"):
                detrend_config = filters_config["detrend"]
                filtered_data = self.apply_detrend(
                    filtered_data, detrend_config.get("channels")
                )

            if filters_config.get("wavelet_denoise"):
                wavelet_config = filters_config["wavelet_denoise"]
                filtered_data = self.apply_wavelet_denoising(
                    filtered_data,
                    wavelet_config.get("wavelet", WaveletTypes.DB4),
                    wavelet_config.get("channels"),
                )

            return filtered_data
        except Exception as e:
            logging.error(f"Apply all filters error: {e}")
            return data

    def get_eeg_metrics(
        self, data: np.ndarray, eeg_channels: List[int]
    ) -> Dict[str, Any]:
        """
        Calculate EEG metrics from the data.

        Args:
            data: EEG data
            eeg_channels: List of EEG channel indices

        Returns:
            Dictionary of metrics
        """
        # Check if processor is initialized, if not, initialize it with default sampling rate
        if self.processor is None:
            default_sampling_rate = 250
            self.initialize_processor(default_sampling_rate)

        # Double check that processor is now initialized
        if self.processor is None:
            logging.error("Failed to initialize processor")
            return {}

        try:
            return self.processor.get_eeg_metrics(data, eeg_channels)
        except Exception as e:
            logging.error(f"EEG metrics calculation error: {e}")
            return {}

    def perform_ica(self, data: np.ndarray, num_components: int) -> Tuple:
        """
        Perform Independent Component Analysis (ICA) on the data.

        Args:
            data: Data to analyze
            num_components: Number of ICA components

        Returns:
            Tuple of ICA results (w, k, a, s)
        """
        if self.processor is None:
            logging.warning("Processor not initialized")
            return None, None, None, None

        try:
            return self.processor.perform_ica(data, num_components)
        except Exception as e:
            logging.error(f"ICA error: {e}")
            return None, None, None, None

    def perform_downsampling(
        self,
        data: np.ndarray,
        factor: int,
        operation: AggOperations = AggOperations.MEAN,
    ) -> np.ndarray:
        """
        Perform downsampling on the data.

        Args:
            data: Data to downsample
            factor: Downsampling factor
            operation: Aggregation operation to use

        Returns:
            Downsampled data
        """
        if self.processor is None:
            logging.warning("Processor not initialized")
            return data

        try:
            return self.processor.perform_downsampling(data, factor, operation)
        except Exception as e:
            logging.error(f"Downsampling error: {e}")
            return data
