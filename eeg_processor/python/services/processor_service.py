import logging
from typing import Dict, List, Any, Tuple, Optional
import numpy as np

from brainflow.data_filter import DataFilter, FilterTypes, WaveletTypes, AggOperations
from ..processors.signal_processor import SignalProcessor

class ProcessorService:
    """
    Service for signal processing operations.
    
    This service encapsulates all signal processing functionality and provides
    a clean interface for filter application and metric calculation.
    """
    
    def __init__(self):
        """Initialize the processor service."""
        self.processor = None
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
    
    def apply_bandpass_filter(self, data: np.ndarray, low_cutoff: float, high_cutoff: float,
                           channels: Optional[List[int]] = None) -> np.ndarray:
        """
        Apply bandpass filter to the data.
        
        Args:
            data: Data to filter
            low_cutoff: Low cutoff frequency in Hz
            high_cutoff: High cutoff frequency in Hz
            channels: Specific channels to filter (defaults to all)
            
        Returns:
            Filtered data
        """
        if self.processor is None:
            logging.warning("Processor not initialized")
            return data
            
        try:
            return self.processor.apply_bandpass_filter(data, low_cutoff, high_cutoff, channels)
        except Exception as e:
            logging.error(f"Bandpass filter error: {e}")
            return data
    
    def apply_notch_filter(self, data: np.ndarray, notch_freq: float,
                       channels: Optional[List[int]] = None) -> np.ndarray:
        """
        Apply notch filter to the data.
        
        Args:
            data: Data to filter
            notch_freq: Notch frequency in Hz
            channels: Specific channels to filter (defaults to all)
            
        Returns:
            Filtered data
        """
        if self.processor is None:
            logging.warning("Processor not initialized")
            return data
            
        try:
            return self.processor.apply_notch_filter(data, notch_freq, channels)
        except Exception as e:
            logging.error(f"Notch filter error: {e}")
            return data
    
    def apply_detrend(self, data: np.ndarray, 
                  channels: Optional[List[int]] = None) -> np.ndarray:
        """
        Apply detrend operation to the data.
        
        Args:
            data: Data to detrend
            channels: Specific channels to detrend (defaults to all)
            
        Returns:
            Detrended data
        """
        if self.processor is None:
            logging.warning("Processor not initialized")
            return data
            
        try:
            return self.processor.apply_detrend(data, channels)
        except Exception as e:
            logging.error(f"Detrend error: {e}")
            return data
    
    def apply_wavelet_denoising(self, data: np.ndarray, wavelet: WaveletTypes,
                           channels: Optional[List[int]] = None) -> np.ndarray:
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
            return self.processor.apply_wavelet_denoising(data, wavelet, channels)
        except Exception as e:
            logging.error(f"Wavelet denoising error: {e}")
            return data
    
    def apply_all_filters(self, data: np.ndarray, filters_config: Dict[str, Any]) -> np.ndarray:
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
            
            # Apply bandpass if configured
            if filters_config.get('bandpass', {}).get('enabled', False):
                low_cutoff = filters_config['bandpass'].get('low_cutoff', 1.0)
                high_cutoff = filters_config['bandpass'].get('high_cutoff', 50.0)
                filtered_data = self.apply_bandpass_filter(filtered_data, low_cutoff, high_cutoff)
            
            # Apply notch if configured
            if filters_config.get('notch', {}).get('enabled', False):
                notch_freq = filters_config['notch'].get('frequency', 50.0)
                filtered_data = self.apply_notch_filter(filtered_data, notch_freq)
            
            # Apply detrend if configured
            if filters_config.get('detrend', False):
                filtered_data = self.apply_detrend(filtered_data)
            
            # Apply wavelet denoising if configured
            if filters_config.get('wavelet', {}).get('enabled', False):
                wavelet = filters_config['wavelet'].get('type', WaveletTypes.DB4)
                filtered_data = self.apply_wavelet_denoising(filtered_data, wavelet)
            
            return filtered_data
        except Exception as e:
            logging.error(f"Applying filters error: {e}")
            return data
    
    def get_eeg_metrics(self, data: np.ndarray, eeg_channels: List[int]) -> Dict[str, Any]:
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
            logging.info("Initializing processor with default sampling rate for metrics calculation")
            # Try to infer sampling rate from data or use default
            if data.size > 0 and hasattr(data, 'shape') and data.shape[1] > 100:
                # Assume sampling rate is 250 Hz if we have enough data
                estimated_sr = 250
            else:
                estimated_sr = 250  # Default sampling rate
                
            self.initialize_processor(estimated_sr)
            
        try:
            # Use the processor's get_eeg_metrics method
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
            return (None, None, None, None)
            
        try:
            return self.processor.perform_ica(data, num_components)
        except Exception as e:
            logging.error(f"ICA error: {e}")
            return (None, None, None, None)
    
    def perform_downsampling(self, data: np.ndarray, factor: int, 
                         operation: AggOperations = AggOperations.MEAN) -> np.ndarray:
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
