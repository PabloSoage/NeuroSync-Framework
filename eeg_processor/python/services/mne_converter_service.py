import logging
import time
from typing import Dict, Any, Optional, Callable, List
import numpy as np

from ..interfaces.mne_interfaces import MNEConverterInterface, MNEProcessManagerInterface, MNEResultStorageInterface

# Check if MNE is available
try:
    import mne
    MNE_AVAILABLE = True
except ImportError:
    MNE_AVAILABLE = False


class MNEConverterService(MNEConverterInterface):
    """Service for converting BrainFlow data to MNE format."""
    
    def __init__(
        self, 
        process_manager: MNEProcessManagerInterface,
        result_storage: MNEResultStorageInterface
    ) -> None:
        """Initialize the converter service."""
        self.process_manager = process_manager
        self.result_storage = result_storage
        self._completion_callbacks: Dict[str, Callable] = {}
        
        logging.info("MNE converter service initialized")
    
    def convert_to_mne_async(
        self,
        data: np.ndarray,
        metadata: Dict[str, Any],
        duration_seconds: int,
        convert_to_v: bool = True,
        selected_channels: Optional[List[int]] = None,
        callback: Optional[Callable] = None
    ) -> str:
        """Convert BrainFlow data to MNE format asynchronously."""
        if not MNE_AVAILABLE:
            raise RuntimeError("MNE package not available")
        
        if not self.process_manager.is_available():
            raise RuntimeError("Process manager not available")
        
        if data.size == 0:
            raise ValueError("No data available for conversion")
        
        # Generate task ID
        task_id = f"convert_{int(time.time() * 1000)}"
        
        # Store callback if provided
        if callback:
            self._completion_callbacks[task_id] = callback
        
        # Submit conversion task with specific task ID
        returned_task_id = self.process_manager.submit_task(
            _convert_to_mne_worker,
            data, metadata, duration_seconds, convert_to_v, selected_channels,
            task_id=task_id,
            callback=lambda result: self._handle_conversion_complete(task_id, result, callback)
        )
        
        # Ensure the returned task ID matches what we expect
        assert returned_task_id == task_id, f"Task ID mismatch: expected {task_id}, got {returned_task_id}"
        
        logging.info(f"Started MNE conversion task: {task_id}")
        return task_id
    
    def get_conversion_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a conversion task."""
        return self.process_manager.get_task_status(task_id)
    
    def cancel_conversion(self, task_id: str) -> bool:
        """Cancel a conversion task."""
        success = self.process_manager.cancel_task(task_id)
        if success:
            # Clean up callback
            if task_id in self._completion_callbacks:
                del self._completion_callbacks[task_id]
            logging.info(f"Cancelled conversion task: {task_id}")
        return success
    
    def _handle_conversion_complete(self, task_id: str, result: Dict[str, Any], callback: Optional[Callable]) -> None:
        """Handle completion of conversion task."""
        # Store result
        self.result_storage.store_result(task_id, result)
        
        # Call callback if provided
        if callback:
            try:
                callback(task_id, result)
            except Exception as e:
                logging.error(f"Error in conversion callback: {e}")
        
        # Clean up callback
        if task_id in self._completion_callbacks:
            del self._completion_callbacks[task_id]
        
        logging.info(f"Conversion task completed: {task_id}")


def _convert_to_mne_worker(
    data: np.ndarray,
    metadata: Dict[str, Any],
    duration_seconds: int,
    convert_to_v: bool,
    selected_channels: Optional[List[int]] = None
) -> Dict[str, Any]:
    """Worker function to convert BrainFlow data to MNE format."""
    try:
        import mne
        
        sampling_rate = metadata.get("sampling_rate", 250)
        samples_needed = int(duration_seconds * sampling_rate)
        
        # Check if we have enough data
        if data.shape[1] < samples_needed:
            return {
                "success": False,
                "error": f"Not enough data. Need {duration_seconds}s but only have {data.shape[1]/sampling_rate:.1f}s"
            }
        
        # Extract last N seconds
        recent_data = data[:, -samples_needed:]
        
        # Get EEG channels
        eeg_channels = metadata.get("eeg_channels", [])
        if not eeg_channels:
            return {
                "success": False,
                "error": "No EEG channels available"
            }
        
        # Apply channel selection
        if selected_channels is not None:
            # Filter EEG channels based on selection
            selected_eeg_channels = []
            
            for selected_idx in selected_channels:
                if selected_idx < len(eeg_channels):
                    eeg_channel = eeg_channels[selected_idx]
                    if eeg_channel < recent_data.shape[0]:
                        selected_eeg_channels.append(eeg_channel)
            
            if not selected_eeg_channels:
                return {
                    "success": False,
                    "error": "No valid EEG channels selected"
                }
            
            eeg_channels = selected_eeg_channels
            channel_selection_info = f"Selected {len(eeg_channels)} of {len(metadata.get('eeg_channels', []))} channels"
        else:
            channel_selection_info = f"Using all {len(eeg_channels)} channels"
        
        # Extract EEG data
        eeg_data = recent_data[eeg_channels, :]
        
        # Convert units if requested
        if convert_to_v:
            eeg_data = eeg_data / 1000000  # µV to V
        
        # Create channel info
        ch_types = ['eeg'] * len(eeg_channels)
        ch_names = metadata.get("channel_names", [])
        
        # Apply channel selection to channel names
        if selected_channels is not None and ch_names:
            selected_ch_names = []
            for selected_idx in selected_channels:
                if selected_idx < len(ch_names):
                    selected_ch_names.append(ch_names[selected_idx])
                else:
                    selected_ch_names.append(f"EEG_{selected_idx}")
            ch_names = selected_ch_names
        elif not ch_names or len(ch_names) < len(eeg_channels):
            ch_names = [f"EEG_{i}" for i in range(len(eeg_channels))]
        else:
            ch_names = ch_names[:len(eeg_channels)]
        
        # Create MNE info object
        info = mne.create_info(ch_names=ch_names, sfreq=sampling_rate, ch_types=ch_types)
        
        return {
            "success": True,
            "raw_data": eeg_data,
            "info": info,
            "duration": duration_seconds,
            "channels": len(eeg_channels),
            "sampling_rate": sampling_rate,
            "converted_to_v": convert_to_v,
            "selected_channels": selected_channels,
            "channel_selection_info": channel_selection_info
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
