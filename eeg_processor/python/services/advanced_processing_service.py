import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .data_access_service import DataAccessService


class AdvancedProcessingService:
    """
    Service for advanced EEG signal processing operations.
    
    This service encapsulates the business logic for ICA, wavelet transforms,
    downsampling and advanced filtering operations on EEG data.
    """

    def __init__(self) -> None:
        """Initialize the advanced processing service."""
        self._data_access_service = DataAccessService.get_instance()
        self._processor_service = None
        
        # Store computation results
        self._ica_results = None
        self._wavelet_results = {
            'coefficients': None,
            'metadata': None
        }
        
        # Processing state
        self._downsampling_active = False
        self._advanced_filters_active = False
        self._inverse_wavelet_active = False

    def initialize(self, processor_service: Any) -> None:
        """Initialize the service with required dependencies."""
        self._processor_service = processor_service
        self._data_access_service.set_filter_processor(processor_service)

    def get_channel_names(self) -> List[str]:
        """Get available channel names."""
        try:
            metadata = self._data_access_service.get_metadata()
            channel_names = metadata.get("channel_names", [])
            eeg_channels = metadata.get("eeg_channels", [])

            # Generate default channel names if needed
            if not channel_names and eeg_channels:
                return [f"CH{i+1}" for i in range(len(eeg_channels))]
            return channel_names
        except Exception as e:
            logging.error(f"Error getting channel names: {e}")
            return []

    def compute_ica(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compute Independent Component Analysis.
        
        Args:
            params: Dictionary with ICA parameters
                num_components: Number of components to extract
                selected_channels: List of channel indices to use
        
        Returns:
            Dictionary with results containing:
                success: Boolean indicating success
                components: Dictionary with ICA components (if successful)
                error: Error message (if failed)
        """
        try:
            # Get current data
            data, _ = self._data_access_service.get_current_data()
            if data.size == 0:
                return {'success': False, 'error': "No data available for ICA computation"}

            # Extract parameters
            num_components = params["num_components"]
            selected_channels = params["selected_channels"]
            
            # Ensure channels are in valid range
            if any(i >= data.shape[0] for i in selected_channels):
                return {'success': False, 'error': "Selected channels exceed available channels"}
            
            # Extract selected channels
            ica_data = data[selected_channels, :]
            
            # Ensure we have enough data
            min_samples = max(num_components * 100, 1000)
            if ica_data.shape[1] < min_samples:
                return {'success': False, 'error': f"Need at least {min_samples} samples for reliable ICA"}
            
            # Check minimum channels requirement
            if ica_data.shape[0] < 2:
                return {'success': False, 'error': "Need at least 2 channels for ICA"}
            
            # Initialize processor if needed
            self._ensure_processor_initialized()

            # Compute ICA
            w, k, a, s = self._processor_service.perform_ica(ica_data, num_components)
            
            if w is not None:
                ica_components = {
                    "w": w, "k": k, "a": a, "s": s,
                    "selected_channels": selected_channels,
                    "num_components": num_components
                }
                
                # Store for later use
                self._ica_results = ica_components
                
                return {'success': True, 'components': ica_components}
            else:
                return {'success': False, 'error': "ICA computation failed"}

        except Exception as e:
            logging.error(f"Error in ICA computation: {e}")
            return {'success': False, 'error': str(e)}

    def compute_wavelet(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compute wavelet transform.
        
        Args:
            params: Dictionary with wavelet parameters
                wavelet_type: Type of wavelet
                decomp_level: Decomposition level
                channel_selection: Channel index to use
        
        Returns:
            Dictionary with results containing:
                success: Boolean indicating success
                coefficients: Wavelet coefficients (if successful)
                metadata: Metadata about the transform (if successful)
                error: Error message (if failed)
        """
        try:
            # Get current data
            data, _ = self._data_access_service.get_current_data()
            if data.size == 0:
                return {'success': False, 'error': "No data available for wavelet computation"}

            # Extract parameters
            wavelet_type = params["wavelet_type"]
            decomp_level = params["decomp_level"]
            channel_selection = params["channel_selection"]

            # Select data for wavelet analysis
            if channel_selection < data.shape[0]:
                wavelet_data = data[channel_selection:channel_selection+1, :]
            else:
                return {'success': False, 'error': "Selected channel not available"}

            # Initialize processor if needed
            self._ensure_processor_initialized()

            # Compute wavelet coefficients
            coefficients, metadata = self._processor_service.compute_wavelet_coefficients(
                wavelet_data, wavelet_type, decomp_level
            )

            if coefficients is not None:
                # Store for later use
                self._wavelet_results = {
                    'coefficients': coefficients,
                    'metadata': metadata
                }
                
                # Store in data access service for stream processing (if needed)
                self._data_access_service._wavelet_coefficients = coefficients
                self._data_access_service._wavelet_metadata = metadata
                
                return {
                    'success': True, 
                    'coefficients': coefficients, 
                    'metadata': metadata
                }
            else:
                return {'success': False, 'error': "Wavelet computation failed"}

        except Exception as e:
            logging.error(f"Error in wavelet computation: {e}")
            return {'success': False, 'error': str(e)}

    def apply_wavelet_inverse(self, apply: bool) -> Dict[str, Any]:
        """Apply or remove inverse wavelet transform to the data stream.
        
        Args:
            apply: Whether to apply (True) or remove (False) the transform
            
        Returns:
            Dictionary with results containing:
                success: Boolean indicating success
                error: Error message (if failed)
        """
        try:
            # Check if we have wavelet results
            if not self._wavelet_results['coefficients'] is not None:
                return {'success': False, 'error': "No wavelet coefficients available"}
                
            if apply:
                # Apply inverse wavelet transform to the stream
                processing_settings = {
                    "wavelet": {
                        "inverse_enabled": True,
                    }
                }
                
                self._data_access_service.enable_advanced_processing(True, processing_settings)
                self._inverse_wavelet_active = True
            else:
                # Remove inverse wavelet transform
                self._data_access_service.enable_advanced_processing(False)
                self._inverse_wavelet_active = False
                
            return {'success': True}

        except Exception as e:
            logging.error(f"Error in applying inverse wavelet: {e}")
            return {'success': False, 'error': str(e)}

    def apply_downsampling(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply or remove downsampling to the data stream.
        
        Args:
            params: Dictionary with parameters
                apply: Whether to apply (True) or remove (False)
                factor: Downsampling factor
                operation: Type of aggregation operation
                
        Returns:
            Dictionary with results containing:
                success: Boolean indicating success
                error: Error message (if failed)
        """
        try:
            apply = params["apply"]
            
            if apply:
                # Apply downsampling to the stream
                processing_settings = {
                    "downsampling": {
                        "enabled": True,
                        "factor": params["factor"],
                        "operation": params["operation"],
                    }
                }
                
                self._data_access_service.enable_advanced_processing(True, processing_settings)
                self._downsampling_active = True
            else:
                # Remove downsampling
                self._data_access_service.enable_advanced_processing(False)
                self._downsampling_active = False
                
            return {'success': True}

        except Exception as e:
            logging.error(f"Error in applying downsampling: {e}")
            return {'success': False, 'error': str(e)}

    def apply_advanced_filters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply or remove advanced filters to the data stream.
        
        Args:
            params: Dictionary with parameters
                apply: Whether to apply (True) or remove (False)
                filter_type: Type of filter
                low_cut: Low cutoff frequency (optional)
                high_cut: High cutoff frequency (optional)
                order: Filter order (optional)
                
        Returns:
            Dictionary with results containing:
                success: Boolean indicating success
                error: Error message (if failed)
        """
        try:
            apply = params["apply"]
            
            if apply:
                # Apply advanced filters to the stream
                processing_settings = {
                    "advanced_filters": {
                        "enabled": True,
                        "filter_type": params["filter_type"],
                        "low_cut": params.get("low_cut", 1.0),
                        "high_cut": params.get("high_cut", 50.0),
                        "order": params.get("order", 4),
                    }
                }
                
                self._data_access_service.enable_advanced_processing(True, processing_settings)
                self._advanced_filters_active = True
            else:
                # Remove advanced filters
                self._data_access_service.enable_advanced_processing(False)
                self._advanced_filters_active = False
                
            return {'success': True}

        except Exception as e:
            logging.error(f"Error in applying advanced filters: {e}")
            return {'success': False, 'error': str(e)}

    def get_ica_results(self) -> Optional[Dict[str, Any]]:
        """Get the stored ICA results."""
        return self._ica_results
        
    def get_wavelet_results(self) -> Optional[Dict[str, Any]]:
        """Get the stored wavelet results."""
        if self._wavelet_results['coefficients'] is None:
            return None
        return self._wavelet_results
    
    def _ensure_processor_initialized(self) -> None:
        """Ensure the processor is initialized."""
        from .data_access_service import DataAccessService
        
        # Get sampling rate
        sampling_rate = DataAccessService.get_instance().get_sampling_rate()
        
        if sampling_rate > 0 and (not hasattr(self._processor_service, "processor") or 
                                self._processor_service.processor is None):
            self._processor_service.initialize_processor(sampling_rate)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        # Disable any active processing
        if self._downsampling_active or self._advanced_filters_active or self._inverse_wavelet_active:
            self._data_access_service.enable_advanced_processing(False)