"""
Adapter for EEG processor module.

This adapter wraps the EEGProcessorApp to implement the IEEGModule interface.
"""

import time
import logging
from typing import Dict, Any, Optional

from ..interfaces.module_interface import IEEGModule
from eeg_processor.python.eeg_processor_app import EEGProcessorApp


class EEGModuleAdapter(IEEGModule):
    """
    Adapter for EEGProcessorApp to implement the IEEGModule interface.
    
    This class follows the Adapter pattern to convert the EEGProcessorApp
    interface to the IEEGModule interface expected by the integrated application.
    """
    
    def __init__(self, eeg_processor: EEGProcessorApp):
        """
        Initialize the adapter with an EEGProcessorApp instance.
        
        Args:
            eeg_processor: The EEGProcessorApp instance to adapt
        """
        self._eeg_app = eeg_processor
        self._recording_start_time = 0
        self._recording_filename = ""
        self._recording_data_type = "raw"
        
    def connect_to_device(self) -> bool:
        """Connect to EEG device using the wrapped EEGProcessorApp."""
        if not hasattr(self._eeg_app, 'connect_board'):
            logging.error("EEG app doesn't have connect_board method")
            return False
        
        try:
            # This will execute connect_board() but won't return success/failure
            # We'll need to check is_connected() after a short delay
            self._eeg_app.connect_board()
            time.sleep(0.2)  # Give some time for connection to establish
            return self.is_connected()
        except Exception as e:
            logging.error(f"Error connecting to EEG device: {e}")
            return False
            
    def disconnect_from_device(self) -> bool:
        """Disconnect from EEG device."""
        if not hasattr(self._eeg_app, 'disconnect_board'):
            logging.error("EEG app doesn't have disconnect_board method")
            return False
        
        try:
            # Call disconnect method on EEG processor app
            self._eeg_app.disconnect_board()
            time.sleep(0.1)  # Allow time for disconnection to complete
            return not self.is_connected()
        except Exception as e:
            logging.error(f"Error disconnecting from EEG device: {e}")
            return False
    
    def start_stream(self) -> bool:
        """Start EEG data streaming."""
        if not hasattr(self._eeg_app, 'start_stream'):
            logging.error("EEG app doesn't have start_stream method")
            return False
        
        try:
            self._eeg_app.start_stream()
            time.sleep(0.1)  # Allow time for stream to start
            return self.is_streaming()
        except Exception as e:
            logging.error(f"Error starting EEG stream: {e}")
            return False
    
    def stop_stream(self) -> bool:
        """Stop EEG data streaming."""
        if not hasattr(self._eeg_app, 'stop_stream'):
            logging.error("EEG app doesn't have stop_stream method")
            return False
        
        try:
            self._eeg_app.stop_stream()
            time.sleep(0.1)  # Allow time for stream to stop
            return not self.is_streaming()
        except Exception as e:
            logging.error(f"Error stopping EEG stream: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if connected to EEG device."""
        # Check for collector attribute which indicates connection
        return (hasattr(self._eeg_app, 'collector') and 
                self._eeg_app.collector is not None)
    
    def is_streaming(self) -> bool:
        """Check if data is streaming."""
        return (hasattr(self._eeg_app, 'is_streaming') and 
                self._eeg_app.is_streaming)
    
    def start_recording(self, filename: str, options: Dict[str, Any]) -> bool:
        """Start recording EEG data to file."""
        if not self.is_connected() or not self.is_streaming():
            logging.error("Cannot record EEG: not connected or not streaming")
            return False
            
        try:
            data_type = options.get("data_type", "raw")
            if data_type not in ["raw", "processed", "both"]:
                data_type = "raw"  # Default to raw if invalid option
                
            self._recording_filename = filename
            self._recording_data_type = data_type
            self._recording_start_time = time.time()
            
            # Start recording using the collector's method directly
            if hasattr(self._eeg_app, 'collector'):
                self._eeg_app.collector.start_continuous_recording(filename, data_type)
                logging.info(f"Started EEG recording to {filename} ({data_type} data)")
                return True
            else:
                logging.error("EEG app doesn't have collector attribute")
                return False
        except Exception as e:
            logging.error(f"Error starting EEG recording: {e}")
            return False
    
    def stop_recording(self) -> bool:
        """Stop EEG recording."""
        if not self.is_recording_active():
            # Nothing to stop
            return True
            
        try:
            if hasattr(self._eeg_app, 'collector'):
                if hasattr(self._eeg_app.collector, 'stop_continuous_recording'):
                    self._eeg_app.collector.stop_continuous_recording()
                    self._recording_filename = ""
                    logging.info("Stopped EEG recording")
                    return True
                else:
                    logging.error("EEG collector doesn't have stop_continuous_recording method")
                    return False
            else:
                logging.error("EEG app doesn't have collector attribute")
                return False
        except Exception as e:
            logging.error(f"Error stopping EEG recording: {e}")
            return False
    
    def is_recording_active(self) -> bool:
        """Check if recording is currently active."""
        # For EEG processor, check if the collector is recording
        if hasattr(self._eeg_app, 'collector'):
            return hasattr(self._eeg_app.collector, 'is_recording') and self._eeg_app.collector.is_recording
        return False
    
    @property
    def recording_info(self) -> Dict[str, Any]:
        """Get information about the current recording."""
        info = {
            "is_recording": self.is_recording_active(),
            "filename": self._recording_filename,
            "data_type": self._recording_data_type,
            "duration": 0,
            "sample_count": 0
        }
        
        if self.is_recording_active() and self._recording_start_time > 0:
            info["duration"] = time.time() - self._recording_start_time
            
            # Try to get sample count if available
            if (hasattr(self._eeg_app, 'collector') and 
                hasattr(self._eeg_app.collector, 'total_recorded_samples')):
                info["sample_count"] = self._eeg_app.collector.total_recorded_samples
        
        return info
    
    def show_visualization(self, visible: bool = True) -> None:
        """Show or hide EEG visualizations."""
        if not hasattr(self._eeg_app, 'visualizer'):
            # No visualizer available or not streaming
            return
            
        if visible:
            # Show visualization if it exists but is not visible
            if self.is_streaming() and hasattr(self._eeg_app, 'show_visualization'):
                self._eeg_app.show_visualization()
        else:
            # Hide visualization if available and visible
            if hasattr(self._eeg_app, 'visualizer') and self._eeg_app.visualizer:
                if hasattr(self._eeg_app.visualizer, 'stop'):
                    self._eeg_app.visualizer.stop()
