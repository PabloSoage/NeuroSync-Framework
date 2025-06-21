import logging
from typing import Dict, List, Tuple, Any

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
        ripple: float = 1.0,
    ) -> np.ndarray:
        """
        Apply bandpass filter to the data.

        Args:
            data: Input data to filter
            start_freq: Low cutoff frequency
            stop_freq: High cutoff frequency
            order: Filter order
            filter_type: Type of filter to use
            ripple: Ripple in passband (for Chebyshev filters, in dB)

        Returns:
            Filtered data
        """
        filtered_data = data.copy()

        # Validate input data first
        if data.size == 0:
            logging.warning("Empty data provided to bandpass filter")
            return data

        # Check for synthetic board data patterns (all zeros or identical values)
        is_synthetic_data = self._is_synthetic_or_problematic_data(data)

        # Force Butterworth for synthetic/problematic data
        if is_synthetic_data and filter_type in [
            FilterTypes.CHEBYSHEV_TYPE_1,
            FilterTypes.CHEBYSHEV_TYPE_1_ZERO_PHASE,
        ]:
            logging.warning(
                "Detected synthetic/problematic data - forcing Butterworth filter instead of Chebyshev for stability"
            )
            filter_type = FilterTypes.BUTTERWORTH
            ripple = 0.0

        # Enhanced parameter validation for Chebyshev filters
        if filter_type in [
            FilterTypes.CHEBYSHEV_TYPE_1,
            FilterTypes.CHEBYSHEV_TYPE_1_ZERO_PHASE,
        ]:
            # Even more conservative parameters for Chebyshev
            original_ripple = ripple
            ripple = max(1.0, min(ripple, 2.0))  # Force ripple between 1-2 dB
            order = max(2, min(order, 3))  # Limit order to 2-3 for maximum stability

            if original_ripple != ripple:
                logging.debug(
                    f"Adjusted Chebyshev ripple from {original_ripple:.1f} to {ripple:.1f} dB for stability"
                )

            # Very conservative frequency validation for Chebyshev
            nyquist = self.sampling_rate / 2
            max_freq_ratio = 0.4  # Even more conservative for Chebyshev

            if stop_freq > max_freq_ratio * nyquist:
                new_stop = max_freq_ratio * nyquist
                logging.warning(
                    f"Reducing Chebyshev high cutoff from {stop_freq:.1f} to {new_stop:.1f} Hz for stability"
                )
                stop_freq = new_stop

            if start_freq > max_freq_ratio * nyquist * 0.6:
                new_start = max_freq_ratio * nyquist * 0.05  # Very low
                logging.warning(
                    f"Reducing Chebyshev low cutoff from {start_freq:.1f} to {new_start:.1f} Hz for stability"
                )
                start_freq = new_start

            # Ensure minimum bandwidth for Chebyshev
            min_bandwidth = 5.0  # Increased minimum bandwidth
            if (stop_freq - start_freq) < min_bandwidth:
                logging.warning(
                    f"Adjusting Chebyshev bandwidth to minimum {min_bandwidth} Hz"
                )
                center_freq = (start_freq + stop_freq) / 2
                start_freq = max(0.1, center_freq - min_bandwidth / 2)
                stop_freq = min(
                    nyquist * max_freq_ratio, center_freq + min_bandwidth / 2
                )

            # Final safety check - if frequencies are still problematic, force Butterworth
            if start_freq >= stop_freq or stop_freq > nyquist * 0.8:
                logging.error(
                    f"Chebyshev frequencies still problematic after adjustment, forcing Butterworth"
                )
                filter_type = FilterTypes.BUTTERWORTH
                ripple = 0.0
        else:
            # For non-Chebyshev filters, set ripple to 0
            ripple = 0.0

        # Convert ripple to int for BrainFlow - ENSURE it's being used
        ripple_int = int(round(ripple))

        # Log the actual parameters being used
        logging.debug(
            f"Applying bandpass filter: {start_freq:.1f}-{stop_freq:.1f}Hz, order={order}, type={filter_type}, ripple={ripple_int}dB"
        )

        # Standard frequency validation
        nyquist = self.sampling_rate / 2
        if start_freq >= nyquist or stop_freq >= nyquist:
            logging.warning(
                f"Filter frequencies too high for sampling rate {self.sampling_rate}Hz"
            )
            return data

        if start_freq >= stop_freq:
            logging.warning(
                f"Invalid frequency range: {start_freq:.1f} >= {stop_freq:.1f}"
            )
            return data

        # Process each channel with enhanced error handling
        for channel_idx in range(data.shape[0]):
            try:
                # Pre-validate channel data
                channel_data = filtered_data[channel_idx]

                # Check for NaN/Inf in input data
                if not np.isfinite(channel_data).all():
                    logging.warning(
                        f"Channel {channel_idx} contains NaN/Inf values, cleaning..."
                    )
                    channel_data = np.nan_to_num(
                        channel_data, nan=0.0, posinf=0.0, neginf=0.0
                    )
                    filtered_data[channel_idx] = channel_data

                # Enhanced data quality checks
                data_std = np.std(channel_data)
                data_mean = np.mean(channel_data)
                data_range = np.ptp(channel_data)  # Peak-to-peak

                # Skip filtering if data is problematic
                if data_std == 0 or not np.isfinite(data_std):
                    logging.warning(
                        f"Channel {channel_idx} has zero or invalid variance, skipping filter"
                    )
                    continue

                # Check for constant or near-constant data (common in synthetic boards)
                if data_range < 1e-10:
                    logging.warning(
                        f"Channel {channel_idx} has near-constant data (range: {data_range:.2e}), skipping filter"
                    )
                    continue

                if data_range > 1e6:  # Very large range can cause numerical issues
                    logging.warning(
                        f"Channel {channel_idx} has very large range ({data_range:.2e}), normalizing..."
                    )
                    # Normalize to prevent numerical issues
                    if data_std > 0:
                        channel_data = (channel_data - data_mean) / data_std
                        filtered_data[channel_idx] = channel_data

                # Check if we have enough data for the filter
                min_samples_needed = max(order * 10, 50)  # Even more conservative
                if len(channel_data) < min_samples_needed:
                    logging.warning(
                        f"Not enough samples for filter on channel {channel_idx}: {len(channel_data)} < {min_samples_needed}"
                    )
                    continue

                # Apply filter with additional safeguards for Chebyshev
                try:
                    if filter_type in [
                        FilterTypes.CHEBYSHEV_TYPE_1,
                        FilterTypes.CHEBYSHEV_TYPE_1_ZERO_PHASE,
                    ]:
                        # Additional pre-processing for Chebyshev stability
                        # Remove DC component more aggressively
                        dc_removed = channel_data - np.mean(channel_data)

                        # Apply a very light smoothing to reduce high-frequency noise that can destabilize Chebyshev
                        from scipy import signal as scipy_signal

                        try:
                            # Light smoothing with a simple moving average
                            window_size = min(5, len(dc_removed) // 10)
                            if window_size >= 3:
                                smoothed = scipy_signal.savgol_filter(
                                    dc_removed, window_size, 1
                                )
                                filtered_data[channel_idx] = smoothed
                            else:
                                filtered_data[channel_idx] = dc_removed
                        except:
                            # Fallback to simple detrend
                            filtered_data[channel_idx] = dc_removed

                        logging.debug(
                            f"Applying Chebyshev filter to channel {channel_idx} with enhanced preprocessing"
                        )

                    # Apply the actual filter - pass ripple_int correctly
                    DataFilter.perform_bandpass(
                        filtered_data[channel_idx],
                        self.sampling_rate,
                        start_freq,
                        stop_freq,
                        order,
                        filter_type,
                        ripple_int,  # This should now be properly passed through
                    )

                except Exception as filter_error:
                    logging.error(
                        f"Filter failed on channel {channel_idx}: {filter_error}"
                    )
                    # Keep original data for this channel
                    filtered_data[channel_idx] = data[channel_idx]
                    continue

                # Enhanced post-filter validation
                if not np.isfinite(filtered_data[channel_idx]).all():
                    logging.warning(
                        f"Filter produced NaN/Inf on channel {channel_idx}, reverting to original data"
                    )
                    filtered_data[channel_idx] = data[channel_idx]
                    continue

                # Check if filter output is reasonable
                output_std = np.std(filtered_data[channel_idx])
                if output_std == 0 or not np.isfinite(output_std):
                    logging.warning(
                        f"Filter produced invalid output on channel {channel_idx}, reverting to original data"
                    )
                    filtered_data[channel_idx] = data[channel_idx]
                    continue

                # Check for filter artifacts (all same values, etc.)
                output_range = np.ptp(filtered_data[channel_idx])
                if output_range < 1e-12:
                    logging.warning(
                        f"Filter output has no variation on channel {channel_idx}, reverting to original data"
                    )
                    filtered_data[channel_idx] = data[channel_idx]
                    continue

            except Exception as e:
                logging.error(f"Error filtering channel {channel_idx}: {e}")
                # On error, keep original data for this channel
                filtered_data[channel_idx] = data[channel_idx]

        self.processed_data = filtered_data
        logging.debug(
            f"Applied bandpass filter {start_freq:.1f}-{stop_freq:.1f}Hz, order {order}, type {filter_type}, ripple {ripple_int}dB"
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
        logging.debug(
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
        logging.debug(f"Applied lowpass filter {cutoff_freq}Hz, order {order}")
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
        logging.debug(f"Applied highpass filter {cutoff_freq}Hz, order {order}")
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
        logging.debug(f"Applied wavelet denoising with {wavelet}")
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
        logging.debug(f"Removed {noise_freq} environmental noise")
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
        logging.debug(f"Downsampled data by factor {factor}")
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
        logging.debug(f"Detrended data with {operation}")
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

        logging.debug(f"Calculated PSD with {window} window")
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

            logging.debug(f"EEG metrics calculated: {metrics}")
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

        logging.debug(f"Detected peaks with threshold {threshold}")
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

    def perform_advanced_bandpass_filter(
        self,
        data: np.ndarray,
        start_freq: float,
        stop_freq: float,
        order: int,
        filter_type: FilterTypes = FilterTypes.BUTTERWORTH,
        ripple: float = 1.0,
    ) -> np.ndarray:
        """
        Apply advanced bandpass filter with specific filter type to the data.
        This method uses the same logic as bandpass_filter for consistency.
        """
        # Log the parameters being received
        logging.debug(
            f"Advanced bandpass filter called with: freq={start_freq:.1f}-{stop_freq:.1f}Hz, order={order}, type={filter_type}, ripple={ripple:.1f}dB"
        )
        return self.bandpass_filter(
            data, start_freq, stop_freq, order, filter_type, ripple
        )

    def get_wavelet_coefficients(
        self,
        data: np.ndarray,
        wavelet: WaveletTypes = WaveletTypes.DB4,
        decomposition_level: int = 3,
        extension_type: int = 0,  # WaveletExtensionTypes.SYMMETRIC
        apply_denoising: bool = False,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Get wavelet coefficients for the data.

        Args:
            data: Input data
            wavelet: Type of wavelet to use
            decomposition_level: Level of decomposition
            extension_type: Extension type for wavelet transform
            apply_denoising: Whether to apply denoising

        Returns:
            Tuple of (coefficients, metadata)
        """
        try:
            coefficients_list = []
            metadata = {
                "wavelet": wavelet,
                "decomposition_level": decomposition_level,
                "extension_type": extension_type,
                "original_shape": data.shape,
                "apply_denoising": apply_denoising,
                "lengths": [],
            }

            for channel_idx in range(data.shape[0]):
                try:
                    # Get wavelet coefficients using BrainFlow
                    channel_data = data[channel_idx].copy()

                    # Apply denoising if requested
                    if apply_denoising:
                        DataFilter.perform_wavelet_denoising(
                            channel_data,
                            wavelet,
                            decomposition_level,
                            WaveletDenoisingTypes.SURESHRINK,
                            ThresholdTypes.HARD,
                            extension_type,
                            NoiseEstimationLevelTypes.FIRST_LEVEL,
                        )

                    # Perform wavelet transform
                    coeffs, lengths = DataFilter.perform_wavelet_transform(
                        channel_data, wavelet, decomposition_level, extension_type
                    )

                    coefficients_list.append(coeffs)
                    if channel_idx == 0:  # Store lengths from first channel
                        metadata["lengths"] = lengths

                except Exception as e:
                    logging.error(
                        f"Error computing wavelet coefficients for channel {channel_idx}: {e}"
                    )
                    # Add empty coefficients for failed channels
                    coefficients_list.append(np.array([]))

            # Convert to numpy array
            if coefficients_list:
                # Pad coefficients to same length if needed
                max_length = max(
                    len(coeffs) for coeffs in coefficients_list if len(coeffs) > 0
                )
                if max_length > 0:
                    padded_coeffs = []
                    for coeffs in coefficients_list:
                        if len(coeffs) > 0:
                            if len(coeffs) < max_length:
                                padded = np.zeros(max_length)
                                padded[: len(coeffs)] = coeffs
                                padded_coeffs.append(padded)
                            else:
                                padded_coeffs.append(coeffs)
                        else:
                            padded_coeffs.append(np.zeros(max_length))

                    coefficients_data = np.array(padded_coeffs)
                else:
                    coefficients_data = np.array([])
            else:
                coefficients_data = np.array([])

            logging.info(
                f"Computed wavelet coefficients with {wavelet}, level {decomposition_level}, denoising: {apply_denoising}"
            )
            return coefficients_data, metadata

        except Exception as e:
            logging.error(f"Error in wavelet computation: {e}")
            return data, {}

    def apply_inverse_wavelet_transform(
        self,
        coefficients: np.ndarray,
        metadata: Dict[str, Any],
    ) -> np.ndarray:
        """
        Apply inverse wavelet transform using stored coefficients.

        Args:
            coefficients: Wavelet coefficients
            metadata: Metadata from forward transform

        Returns:
            Reconstructed data
        """
        try:
            wavelet = metadata.get("wavelet", WaveletTypes.DB4)
            decomp_level = metadata.get("decomposition_level", 3)
            extension_type = metadata.get("extension_type", 0)
            lengths = metadata.get("lengths", [])
            original_shape = metadata.get("original_shape", coefficients.shape)

            # Validate inputs
            if coefficients.size == 0:
                logging.warning(
                    "Empty coefficients provided to inverse wavelet transform"
                )
                return np.zeros(original_shape)

            if len(lengths) == 0:
                logging.warning("No lengths provided for inverse wavelet transform")
                return np.zeros(original_shape)

            # Check if we have the expected coefficient length
            expected_length = sum(lengths)
            logging.debug(
                f"Inverse wavelet: coefficients shape {coefficients.shape}, expected length {expected_length}, original shape {original_shape}"
            )

            reconstructed_data = np.zeros(original_shape)

            for channel_idx in range(coefficients.shape[0]):
                try:
                    # Get coefficients for this channel
                    channel_coeffs = coefficients[channel_idx]

                    if len(channel_coeffs) > 0 and len(lengths) > 0:
                        # Handle coefficient length mismatch more gracefully
                        if len(channel_coeffs) < expected_length:
                            logging.debug(
                                f"Padding coefficients for channel {channel_idx}: {len(channel_coeffs)} -> {expected_length}"
                            )
                            # Pad with zeros if necessary
                            padded_coeffs = np.zeros(expected_length)
                            padded_coeffs[: len(channel_coeffs)] = channel_coeffs
                            channel_coeffs = padded_coeffs
                        elif len(channel_coeffs) > expected_length:
                            logging.debug(
                                f"Truncating coefficients for channel {channel_idx}: {len(channel_coeffs)} -> {expected_length}"
                            )
                            # Truncate if too long
                            channel_coeffs = channel_coeffs[:expected_length]

                        # Prepare coefficients tuple for inverse transform
                        coeffs_tuple = (channel_coeffs, lengths)

                        # Apply inverse wavelet transform
                        restored = DataFilter.perform_inverse_wavelet_transform(
                            coeffs_tuple,
                            original_shape[1],
                            wavelet,
                            decomp_level,
                            extension_type,
                        )

                        # Ensure the restored data fits the original shape
                        if len(restored) <= original_shape[1]:
                            reconstructed_data[channel_idx, : len(restored)] = restored
                        else:
                            reconstructed_data[channel_idx] = restored[
                                : original_shape[1]
                            ]

                        logging.debug(
                            f"Successfully reconstructed channel {channel_idx} with {len(restored)} samples"
                        )
                    else:
                        # If no valid coefficients, keep zeros
                        logging.warning(
                            f"No valid coefficients for channel {channel_idx}"
                        )

                except Exception as e:
                    logging.error(
                        f"Error in inverse wavelet for channel {channel_idx}: {e}"
                    )
                    # Keep zeros for this channel on error

            logging.debug(
                f"Completed inverse wavelet transform: output shape {reconstructed_data.shape}"
            )
            return reconstructed_data

        except Exception as e:
            logging.error(f"Error in inverse wavelet transform: {e}")
            # Return zeros with correct shape instead of original coefficients
            original_shape = metadata.get("original_shape", (1, 1000))
            return np.zeros(original_shape)

    def _is_synthetic_or_problematic_data(self, data: np.ndarray) -> bool:
        """Check if data appears to be synthetic or problematic for advanced filtering."""
        try:
            # Check if all channels have the same values (synthetic board pattern)
            if data.shape[0] > 1:
                first_channel = data[0]
                for i in range(1, data.shape[0]):
                    if np.allclose(data[i], first_channel, rtol=1e-10):
                        return True

            # Check for all zeros or near-constant data
            for channel_idx in range(data.shape[0]):
                channel_data = data[channel_idx]
                if len(channel_data) == 0:
                    continue

                # Check for all zeros
                if np.allclose(channel_data, 0, atol=1e-12):
                    return True

                # Check for near-constant data
                data_range = np.ptp(channel_data)
                if data_range < 1e-10:
                    return True

                # Check for repeating patterns (synthetic data)
                if len(channel_data) > 10:
                    # Check if the data repeats every few samples
                    for period in [2, 3, 4, 5]:
                        if len(channel_data) >= period * 3:
                            first_period = channel_data[:period]
                            is_repeating = True
                            for start in range(
                                period, len(channel_data) - period, period
                            ):
                                if not np.allclose(
                                    channel_data[start : start + period],
                                    first_period,
                                    rtol=1e-10,
                                ):
                                    is_repeating = False
                                    break
                            if is_repeating:
                                return True

            return False

        except Exception as e:
            logging.debug(f"Error checking for synthetic data: {e}")
            return False
