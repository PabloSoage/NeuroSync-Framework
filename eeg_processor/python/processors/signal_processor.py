import logging
from typing import Dict, List, Tuple

import numpy as np
from brainflow.data_filter import (
    DataFilter,
    FilterTypes,
    AggOperations,
    WindowOperations,
    WaveletTypes,
)
from brainflow.data_filter import (
    NoiseTypes,
    DetrendOperations,
    WaveletDenoisingTypes,
    ThresholdTypes,
)
from brainflow.data_filter import WaveletExtensionTypes, NoiseEstimationLevelTypes
from brainflow.ml_model import (
    MLModel,
    BrainFlowMetrics,
    BrainFlowClassifiers,
    BrainFlowModelParams,
)


class SignalProcessor:
    """
    Processor for EEG signals using BrainFlow's DataFilter and MLModel.

    This class provides methods for filtering, transforming, and analyzing EEG data.
    """

    def __init__(self, sampling_rate: float):
        """
        Initialize the signal processor.

        Args:
            sampling_rate: Sampling rate of the EEG data
        """
        self.sampling_rate = sampling_rate
        self.processed_data = None
        logging.info(
            f"Signal processor initialized with sampling rate {sampling_rate}Hz"
        )

    def bandpass_filter(
        self,
        data: np.ndarray,
        start_freq: float,
        stop_freq: float,
        order: int,
        filter_type: FilterTypes = FilterTypes.BUTTERWORTH,
    ) -> np.ndarray:
        """
        Apply bandpass filter to the data.

        Args:
            data: Input data to filter
            start_freq: Low cutoff frequency
            stop_freq: High cutoff frequency
            order: Filter order
            filter_type: Type of filter to use

        Returns:
            Filtered data
        """
        filtered_data = data.copy()
        for channel_idx in range(data.shape[0]):
            DataFilter.perform_bandpass(
                filtered_data[channel_idx],
                self.sampling_rate,
                start_freq,
                stop_freq,
                order,
                filter_type,
                0,
            )

        self.processed_data = filtered_data
        logging.info(
            f"Applied bandpass filter {start_freq}-{stop_freq}Hz, order {order}"
        )
        return filtered_data

    def bandstop_filter(
        self,
        data: np.ndarray,
        start_freq: float,
        stop_freq: float,
        order: int,
        filter_type: FilterTypes = FilterTypes.BUTTERWORTH,
    ) -> np.ndarray:
        """
        Apply bandstop filter to the data.

        Args:
            data: Input data to filter
            start_freq: Low cutoff frequency
            stop_freq: High cutoff frequency
            order: Filter order
            filter_type: Type of filter to use

        Returns:
            Filtered data
        """
        filtered_data = data.copy()
        for channel_idx in range(data.shape[0]):
            DataFilter.perform_bandstop(
                filtered_data[channel_idx],
                self.sampling_rate,
                start_freq,
                stop_freq,
                order,
                filter_type,
                0,
            )

        self.processed_data = filtered_data
        logging.info(
            f"Applied bandstop filter {start_freq}-{stop_freq}Hz, order {order}"
        )
        return filtered_data

    def lowpass_filter(
        self,
        data: np.ndarray,
        cutoff_freq: float,
        order: int,
        filter_type: FilterTypes = FilterTypes.BUTTERWORTH,
    ) -> np.ndarray:
        """
        Apply lowpass filter to the data.

        Args:
            data: Input data to filter
            cutoff_freq: Cutoff frequency
            order: Filter order
            filter_type: Type of filter to use

        Returns:
            Filtered data
        """
        filtered_data = data.copy()
        for channel_idx in range(data.shape[0]):
            DataFilter.perform_lowpass(
                filtered_data[channel_idx],
                self.sampling_rate,
                cutoff_freq,
                order,
                filter_type,
                0,
            )

        self.processed_data = filtered_data
        logging.info(f"Applied lowpass filter {cutoff_freq}Hz, order {order}")
        return filtered_data

    def highpass_filter(
        self,
        data: np.ndarray,
        cutoff_freq: float,
        order: int,
        filter_type: FilterTypes = FilterTypes.BUTTERWORTH,
    ) -> np.ndarray:
        """
        Apply highpass filter to the data.

        Args:
            data: Input data to filter
            cutoff_freq: Cutoff frequency
            order: Filter order
            filter_type: Type of filter to use

        Returns:
            Filtered data
        """
        filtered_data = data.copy()
        for channel_idx in range(data.shape[0]):
            DataFilter.perform_highpass(
                filtered_data[channel_idx],
                self.sampling_rate,
                cutoff_freq,
                order,
                filter_type,
                0,
            )

        self.processed_data = filtered_data
        logging.info(f"Applied highpass filter {cutoff_freq}Hz, order {order}")
        return filtered_data

    def denoise(
        self, data: np.ndarray, wavelet: WaveletTypes = WaveletTypes.DB4
    ) -> np.ndarray:
        """
        Apply wavelet denoising to the data.

        Args:
            data: Input data to denoise
            wavelet: Type of wavelet to use

        Returns:
            Denoised data
        """
        denoised_data = data.copy()
        for channel_idx in range(data.shape[0]):
            DataFilter.perform_wavelet_denoising(
                denoised_data[channel_idx],
                wavelet,
                3,  # Decomposition level
                WaveletDenoisingTypes.SURESHRINK,
                ThresholdTypes.HARD,
                WaveletExtensionTypes.SYMMETRIC,
                NoiseEstimationLevelTypes.FIRST_LEVEL,
            )

        self.processed_data = denoised_data
        logging.info(f"Applied wavelet denoising with {wavelet}")
        return denoised_data

    def remove_environmental_noise(
        self, data: np.ndarray, noise_type: NoiseTypes = NoiseTypes.FIFTY
    ) -> np.ndarray:
        """
        Remove environmental noise (50Hz or 60Hz) from the data.

        Args:
            data: Input data
            noise_type: Type of noise to remove (50Hz or 60Hz)

        Returns:
            Filtered data
        """
        filtered_data = data.copy()
        for channel_idx in range(data.shape[0]):
            DataFilter.remove_environmental_noise(
                filtered_data[channel_idx], self.sampling_rate, noise_type
            )

        self.processed_data = filtered_data
        noise_freq = "50Hz" if noise_type == NoiseTypes.FIFTY else "60Hz"
        logging.info(f"Removed {noise_freq} environmental noise")
        return filtered_data

    def perform_downsampling(
        self,
        data: np.ndarray,
        factor: int,
        operation: AggOperations = AggOperations.MEAN,
    ) -> np.ndarray:
        """
        Downsample the data by aggregating samples.

        Args:
            data: Input data
            factor: Downsampling factor
            operation: Aggregation operation (MEAN, MEDIAN, etc.)

        Returns:
            Downsampled data
        """
        downsampled_data = np.zeros((data.shape[0], int(data.shape[1] / factor)))
        for channel_idx in range(data.shape[0]):
            downsampled_data[channel_idx] = DataFilter.perform_downsampling(
                data[channel_idx], factor, operation
            )

        self.processed_data = downsampled_data
        logging.info(f"Downsampled data by factor {factor}")
        return downsampled_data

    def detrend(
        self, data: np.ndarray, operation: DetrendOperations = DetrendOperations.LINEAR
    ) -> np.ndarray:
        """
        Remove trend from the data.

        Args:
            data: Input data
            operation: Type of detrending (CONSTANT, LINEAR)

        Returns:
            Detrended data
        """
        detrended_data = data.copy()
        for channel_idx in range(data.shape[0]):
            DataFilter.detrend(detrended_data[channel_idx], operation)

        self.processed_data = detrended_data
        logging.info(f"Detrended data with {operation}")
        return detrended_data

    def get_psd(
        self, data: np.ndarray, window: WindowOperations = WindowOperations.HANNING
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate the Power Spectral Density of the data.

        Args:
            data: Input data
            window: Window function to use

        Returns:
            Tuple of (frequencies, psd_values)
        """
        nfft = DataFilter.get_nearest_power_of_two(self.sampling_rate)
        psd_result = []
        freqs = np.arange(0, nfft // 2 + 1) * self.sampling_rate / nfft

        for channel_idx in range(data.shape[0]):
            psd = DataFilter.get_psd_welch(
                data[channel_idx], nfft, nfft // 2, self.sampling_rate, window
            )
            psd_result.append(psd)

        logging.info(f"Calculated PSD with {window} window")
        return freqs, np.array(psd_result)

    def get_band_power(
        self, data: np.ndarray, start_freq: float, stop_freq: float
    ) -> np.ndarray:
        """
        Calculate band power for specific frequency range.

        Args:
            data: Input data
            start_freq: Start frequency of the band
            stop_freq: Stop frequency of the band

        Returns:
            Band power values for each channel
        """
        nfft = DataFilter.get_nearest_power_of_two(self.sampling_rate)
        band_powers = []

        for channel_idx in range(data.shape[0]):
            psd = DataFilter.get_psd_welch(
                data[channel_idx],
                nfft,
                nfft // 2,
                self.sampling_rate,
                WindowOperations.HANNING,
            )
            band_power = DataFilter.get_band_power(psd, start_freq, stop_freq)
            band_powers.append(band_power)

        logging.debug(f"Calculated band power for {start_freq}-{stop_freq}Hz")
        return np.array(band_powers)

    def get_eeg_metrics(
        self, data: np.ndarray, eeg_channels: List[int]
    ) -> Dict[str, float]:
        """
        Calculate EEG metrics (mindfulness, restfulness, etc.) from the data.

        Args:
            data: Input data
            eeg_channels: List of EEG channel indices

        Returns:
            Dictionary with metric names and values
        """
        try:
            # Get band powers for the EEG metrics
            bands = DataFilter.get_avg_band_powers(
                data, eeg_channels, self.sampling_rate, True
            )
            feature_vector = bands[0]

            # Create dictionary to store metrics
            metrics = {}

            # Calculate mindfulness
            mindfulness_params = BrainFlowModelParams(
                BrainFlowMetrics.MINDFULNESS.value,
                BrainFlowClassifiers.DEFAULT_CLASSIFIER.value,
            )
            mindfulness_model = MLModel(mindfulness_params)
            mindfulness_model.prepare()
            metrics["mindfulness"] = mindfulness_model.predict(feature_vector)
            # Use the same value for concentration
            metrics["concentration"] = metrics["mindfulness"]
            mindfulness_model.release()

            # Calculate restfulness
            restfulness_params = BrainFlowModelParams(
                BrainFlowMetrics.RESTFULNESS.value,
                BrainFlowClassifiers.DEFAULT_CLASSIFIER.value,
            )
            restfulness_model = MLModel(restfulness_params)
            restfulness_model.prepare()
            metrics["restfulness"] = restfulness_model.predict(feature_vector)
            # Use the same value for relaxation
            metrics["relaxation"] = metrics["restfulness"]
            restfulness_model.release()

            logging.info(f"EEG metrics calculated: {metrics}")
            return metrics

        except Exception as e:
            logging.error(f"Failed to calculate EEG metrics: {e}")
            return {
                "mindfulness": 0.0,
                "restfulness": 0.0,
                "concentration": 0.0,
                "relaxation": 0.0,
            }

    def perform_ica(
        self, data: np.ndarray, num_components: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Perform Independent Component Analysis on the data.

        Args:
            data: Input data, should be 2D with rows as channels and columns as samples
            num_components: Number of independent components to extract

        Returns:
            Tuple of (W, K, A, S) matrices from ICA
        """
        try:
            # Ensure data is properly shaped for ICA
            if len(data.shape) == 1:
                # Reshape single channel to 2D with 1 row
                data = data.reshape(1, -1)
            elif len(data.shape) > 2:
                # For 3D+ data, reshape to 2D matrix with channels as rows
                original_shape = data.shape
                data = data.reshape(original_shape[0], -1)

            # Perform ICA
            w, k, a, s = DataFilter.perform_ica(data, num_components)

            logging.info(f"ICA performed with {num_components} components")
            return w, k, a, s

        except Exception as e:
            logging.error(f"Failed to perform ICA: {e}")
            return None, None, None, None

    def detect_peaks(
        self,
        data: np.ndarray,
        lag: int = 5,
        threshold: float = 3.5,
        influence: float = 0.1,
    ) -> np.ndarray:
        """
        Detect peaks in signal using z-score algorithm.

        Args:
            data: Input data
            lag: Window size for averaging
            threshold: Threshold in stddev units
            influence: Contribution of peaks to mean value (0-1)

        Returns:
            Array with detected peaks
        """
        peaks = np.zeros((data.shape[0], data.shape[1]))
        for channel_idx in range(data.shape[0]):
            peaks[channel_idx] = DataFilter.detect_peaks_z_score(
                data[channel_idx], lag, threshold, influence
            )

        logging.info(f"Detected peaks with threshold {threshold}")
        return peaks

    def restore_wavelet_coeffs(
        self, data: np.ndarray, wavelet: int, decomp_level: int, level_to_restore: int
    ) -> np.ndarray:
        """
        Restore data from wavelet detailed coefficients.

        Args:
            data: Input data
            wavelet: Wavelet type
            decomp_level: Decomposition level
            level_to_restore: Level to restore

        Returns:
            Restored signal
        """
        restored_data = np.zeros((data.shape[0], data.shape[1]))
        for channel_idx in range(data.shape[0]):
            restored_data[channel_idx] = (
                DataFilter.restore_data_from_wavelet_detailed_coeffs(
                    data[channel_idx], wavelet, decomp_level, level_to_restore
                )
            )

        logging.info(
            f"Restored data from wavelet coefficients at level {level_to_restore}"
        )
        return restored_data

    def get_signal_quality(
        self, data: np.ndarray, channel: int, gain: int = 24
    ) -> float:
        """
        Calculate signal quality based on railed percentage.

        Args:
            data: Input data array
            channel: Channel index to check
            gain: Amplifier gain

        Returns:
            Quality score between 0 (bad) and 1 (good)
        """
        try:
            if channel >= data.shape[0] or data.size == 0:
                return 0.0

            channel_data = data[channel]
            railed_percentage = DataFilter.get_railed_percentage(channel_data, gain)

            # Convert to quality score (0 to 1, where 1 is best quality)
            # A high railed percentage means poor quality
            quality = 1.0 - min(railed_percentage / 100.0, 1.0)

            logging.debug(
                f"Channel {channel} railed percentage: {railed_percentage}%, quality: {quality:.2f}"
            )
            return quality

        except Exception as e:
            logging.error(f"Error calculating signal quality: {e}")
            return 0.0  # Return worst quality on error

    def get_all_channels_quality(
        self, data: np.ndarray, channels: List[int], gain: int = 24
    ) -> Dict[int, float]:
        """
        Calculate quality for multiple channels.

        Args:
            data: Input data array
            channels: List of channel indices
            gain: Amplifier gain

        Returns:
            Dictionary mapping channel indices to quality scores
        """
        quality_dict = {}
        for channel in channels:
            quality_dict[channel] = self.get_signal_quality(data, channel, gain)
        return quality_dict
