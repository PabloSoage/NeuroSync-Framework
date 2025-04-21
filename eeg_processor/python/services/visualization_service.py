import logging
from typing import Optional

from ..visualizers.eeg_viz import EEGVisualizer
from ..visualizers.brain_map_viz import BrainMapVisualizer

class VisualizationService:
    """
    Service for managing visualization components.
    
    This service handles all visualization operations including EEG waveforms
    and brain maps.
    """
    
    def __init__(self):
        """Initialize the visualization service."""
        self.eeg_visualizer = None
        self.brain_map_visualizer = None
    
    def create_eeg_visualizer(self, collector, processor) -> bool:
        """
        Create an EEG visualizer.
        
        Args:
            collector: The data collector object
            processor: The signal processor object
            
        Returns:
            True if visualizer was created successfully, False otherwise
        """
        try:
            # Handle case where processor is None but we need one
            if processor is None:
                try:
                    from ..processors.signal_processor import SignalProcessor
                    # Try to create a basic processor if possible
                    if hasattr(collector, 'sampling_rate') and collector.sampling_rate > 0:
                        processor = SignalProcessor(collector.sampling_rate)
                        logging.info(f"Created fallback signal processor with sampling rate {collector.sampling_rate}Hz")
                except Exception as e:
                    logging.warning(f"Could not create fallback processor: {e}")
                    # Continue without a processor - visualizer should handle this case
            
            self.eeg_visualizer = EEGVisualizer(collector, processor)
            return True
        except Exception as e:
            logging.error(f"EEG visualizer creation error: {e}")
            return False
    
    def create_brain_map_visualizer(self, collector, processor) -> bool:
        """
        Create a brain map visualizer.
        
        Args:
            collector: The data collector object
            processor: The signal processor object
            
        Returns:
            True if visualizer was created successfully, False otherwise
        """
        try:
            # Handle case where processor is None but we need one
            if processor is None:
                try:
                    from ..processors.signal_processor import SignalProcessor
                    # Try to create a basic processor if possible
                    if hasattr(collector, 'sampling_rate') and collector.sampling_rate > 0:
                        processor = SignalProcessor(collector.sampling_rate)
                        logging.info(f"Created fallback signal processor with sampling rate {collector.sampling_rate}Hz")
                    else:
                        logging.warning("Cannot create fallback processor: no sampling rate available")
                        return False
                except Exception as e:
                    logging.error(f"Could not create processor for brain map: {e}")
                    return False
            
            # Create the brain map visualizer with our prepared processor
            self.brain_map_visualizer = BrainMapVisualizer(collector, processor)
            return True
        except Exception as e:
            logging.error(f"Brain map visualizer creation error: {e}")
            return False
    
    def start_eeg_visualization(self) -> bool:
        """
        Start the EEG visualization.
        
        Returns:
            True if visualization started successfully, False otherwise
        """
        if not self.eeg_visualizer:
            return False
            
        try:
            self.eeg_visualizer.start()
            return True
        except Exception as e:
            logging.error(f"EEG visualization start error: {e}")
            return False
    
    def stop_eeg_visualization(self) -> bool:
        """
        Stop the EEG visualization.
        
        Returns:
            True if visualization stopped successfully, False otherwise
        """
        if not self.eeg_visualizer:
            return False
            
        try:
            self.eeg_visualizer.stop()
            return True
        except Exception as e:
            logging.error(f"EEG visualization stop error: {e}")
            return False
    
    def start_brain_map_visualization(self) -> bool:
        """
        Start the brain map visualization.
        
        Returns:
            True if visualization started successfully, False otherwise
        """
        if not self.brain_map_visualizer:
            return False
            
        try:
            self.brain_map_visualizer.start()
            return True
        except Exception as e:
            logging.error(f"Brain map visualization start error: {e}")
            return False
    
    def visualization_visible(self) -> bool:
        """
        Check if EEG visualization is currently visible.
        
        Returns:
            True if visualization is visible, False otherwise
        """
        return self.eeg_visualizer is not None and self.eeg_visualizer.is_visible()
    
    def visualization_closed(self) -> bool:
        """
        Check if EEG visualization was closed.
        
        Returns:
            True if visualization is closed, False otherwise
        """
        return self.eeg_visualizer is not None and not self.eeg_visualizer.is_visible()
    
    def set_bandpass_filter(self, enabled: bool, low_cutoff: float, high_cutoff: float) -> bool:
        """
        Configure bandpass filter settings for visualization.
        
        Args:
            enabled: Whether the filter is enabled
            low_cutoff: Low cutoff frequency in Hz
            high_cutoff: High cutoff frequency in Hz
            
        Returns:
            True if settings were applied successfully, False otherwise
        """
        success = True
        
        # Apply settings to EEG visualizer
        if self.eeg_visualizer:
            try:
                self.eeg_visualizer.set_bandpass_filter(enabled, low_cutoff, high_cutoff)
            except Exception as e:
                logging.error(f"Setting bandpass filter for EEG visualizer error: {e}")
                success = False
                
        # Apply the same settings to brain map visualizer for consistency
        if self.brain_map_visualizer and hasattr(self.brain_map_visualizer, 'set_bandpass_filter'):
            try:
                self.brain_map_visualizer.set_bandpass_filter(enabled, low_cutoff, high_cutoff)
            except Exception as e:
                logging.error(f"Setting bandpass filter for brain map visualizer error: {e}")
                success = False
                
        return success
    
    def set_notch_filter(self, enabled: bool, frequency: float = 50.0) -> bool:
        """
        Configure notch filter settings for visualization.
        
        Args:
            enabled: Whether the filter is enabled
            frequency: Notch frequency in Hz
            
        Returns:
            True if settings were applied successfully, False otherwise
        """
        success = True
        
        # Apply settings to EEG visualizer
        if self.eeg_visualizer:
            try:
                self.eeg_visualizer.set_notch_filter(enabled)
            except Exception as e:
                logging.error(f"Setting notch filter for EEG visualizer error: {e}")
                success = False
                
        # Apply the same settings to brain map visualizer for consistency
        if self.brain_map_visualizer and hasattr(self.brain_map_visualizer, 'set_notch_filter'):
            try:
                self.brain_map_visualizer.set_notch_filter(enabled)
            except Exception as e:
                logging.error(f"Setting notch filter for brain map visualizer error: {e}")
                success = False
                
        return success
    
    def set_detrend(self, enabled: bool) -> bool:
        """
        Configure detrend settings for visualization.
        
        Args:
            enabled: Whether detrending is enabled
            
        Returns:
            True if settings were applied successfully, False otherwise
        """
        success = True
        
        # Apply settings to EEG visualizer
        if self.eeg_visualizer:
            try:
                self.eeg_visualizer.set_detrend(enabled)
            except Exception as e:
                logging.error(f"Setting detrend for EEG visualizer error: {e}")
                success = False
                
        # Apply the same settings to brain map visualizer for consistency
        if self.brain_map_visualizer and hasattr(self.brain_map_visualizer, 'set_detrend'):
            try:
                self.brain_map_visualizer.set_detrend(enabled)
            except Exception as e:
                logging.error(f"Setting detrend for brain map visualizer error: {e}")
                success = False
                
        return success
    
    def update_plots(self) -> bool:
        """
        Update the visualization plots.
        
        Returns:
            True if plots were updated successfully, False otherwise
        """
        if not self.eeg_visualizer:
            return False
            
        try:
            self.eeg_visualizer.update_plots()
            return True
        except Exception as e:
            logging.error(f"Updating plots error: {e}")
            return False
    
    def cleanup(self) -> None:
        """Clean up visualization resources."""
        try:
            if self.eeg_visualizer:
                self.eeg_visualizer.stop()
                self.eeg_visualizer = None
                
            if self.brain_map_visualizer:
                if hasattr(self.brain_map_visualizer, 'close'):
                    self.brain_map_visualizer.close()
                self.brain_map_visualizer = None
        except Exception as e:
            logging.error(f"Visualization cleanup error: {e}")
