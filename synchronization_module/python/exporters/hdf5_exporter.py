"""
HDF5 dataset exporter for synchronized EEG and input data.
"""
import logging
import os
from typing import Dict, Any, List
import numpy as np

try:
    import h5py
    HDF5_AVAILABLE = True
except ImportError:
    HDF5_AVAILABLE = False

from ..interfaces.export_interface import DatasetExporterInterface


class HDF5Exporter(DatasetExporterInterface):
    """Exports synchronized datasets to HDF5 format."""
    
    description = "HDF5 format for scientific data storage"
    file_extension = ".h5"
    supports_events = True
    supports_metadata = True
    
    def __init__(self):
        """Initialize HDF5 exporter."""
        if not HDF5_AVAILABLE:
            logging.warning("h5py not available. HDF5 export will be disabled.")
    
    def export_dataset(
        self,
        eeg_data: np.ndarray,
        input_events: Dict[str, Any],
        metadata: Dict[str, Any],
        filepath: str
    ) -> bool:
        """Export dataset to HDF5 format."""
        if not HDF5_AVAILABLE:
            logging.error("HDF5 not available")
            return False
        
        try:
            with h5py.File(filepath, 'w') as f:
                # Create groups
                eeg_group = f.create_group('eeg')
                events_group = f.create_group('events')
                meta_group = f.create_group('metadata')
                
                # Store EEG data
                eeg_group.create_dataset('data', data=eeg_data)
                eeg_group.create_dataset('sampling_rate', data=metadata.get('sampling_rate', 250))
                
                if 'channel_names' in metadata:
                    eeg_group.create_dataset(
                        'channel_names', 
                        data=[name.encode('utf-8') for name in metadata['channel_names']]
                    )
                
                # Store input events
                if 'events' in input_events:
                    events_data = input_events['events']
                    if events_data:
                        # Convert events to structured format
                        timestamps = [event.get('timestamp', 0) for event in events_data]
                        event_types = [event.get('type', '').encode('utf-8') for event in events_data]
                        event_data = [str(event.get('data', '')).encode('utf-8') for event in events_data]
                        
                        events_group.create_dataset('timestamps', data=timestamps)
                        events_group.create_dataset('types', data=event_types)
                        events_group.create_dataset('data', data=event_data)
                
                # Store metadata
                for key, value in metadata.items():
                    if isinstance(value, (str, bytes)):
                        meta_group.create_dataset(key, data=value.encode('utf-8') if isinstance(value, str) else value)
                    elif isinstance(value, (int, float)):
                        meta_group.create_dataset(key, data=value)
                    elif isinstance(value, (list, np.ndarray)):
                        meta_group.create_dataset(key, data=value)
                
                # Add synchronization info
                sync_group = f.create_group('synchronization')
                sync_group.create_dataset('precision_ms', data=metadata.get('precision_ms', 1.0))
                sync_group.create_dataset('export_timestamp', data=metadata.get('export_timestamp', 0))
                
            logging.info(f"HDF5 dataset exported to {filepath}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to export HDF5 dataset: {e}")
            return False
    
    def validate_data(
        self,
        eeg_data: np.ndarray,
        input_events: Dict[str, Any]
    ) -> bool:
        """Validate data for HDF5 export."""
        if not HDF5_AVAILABLE:
            return False
        
        # Check EEG data
        if eeg_data.size == 0:
            logging.error("EEG data is empty")
            return False
        
        if len(eeg_data.shape) != 2:
            logging.error("EEG data must be 2D (channels x samples)")
            return False
        
        # Check input events
        if not isinstance(input_events, dict):
            logging.error("Input events must be a dictionary")
            return False
        
        return True
    
    def get_supported_formats(self) -> List[str]:
        """Get supported formats."""
        return ['hdf5', 'h5']