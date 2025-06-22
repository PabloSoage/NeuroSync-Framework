"""
EDF+ dataset exporter for synchronized EEG and input data.
"""
import logging
from typing import Dict, Any, List
import numpy as np

try:
    import pyedflib
    EDF_AVAILABLE = True
except ImportError:
    EDF_AVAILABLE = False

from ..interfaces.export_interface import DatasetExporterInterface


class EDFExporter(DatasetExporterInterface):
    """Exports synchronized datasets to EDF+ format."""
    
    description = "EDF+ format for EEG data with annotations"
    file_extension = ".edf"
    supports_events = True
    supports_metadata = True
    
    def __init__(self):
        """Initialize EDF+ exporter."""
        if not EDF_AVAILABLE:
            logging.warning("pyedflib not available. EDF+ export will be disabled.")
    
    def export_dataset(
        self,
        eeg_data: np.ndarray,
        input_events: Dict[str, Any],
        metadata: Dict[str, Any],
        filepath: str
    ) -> bool:
        """Export dataset to EDF+ format."""
        if not EDF_AVAILABLE:
            logging.error("EDF+ not available")
            return False
        
        try:
            # Prepare channel information
            sampling_rate = metadata.get('sampling_rate', 250)
            channel_names = metadata.get('channel_names', [])
            
            if not channel_names:
                channel_names = [f'Ch{i+1}' for i in range(eeg_data.shape[0])]
            
            # Create EDF+ file
            with pyedflib.EdfWriter(filepath, len(channel_names), file_type=pyedflib.FILETYPE_EDFPLUS) as writer:
                
                # Set header information
                writer.setHeader({
                    'technician': 'BCI Dataset Creator',
                    'recording_additional': 'Synchronized EEG and Input Data',
                    'patientname': metadata.get('subject_id', 'Unknown'),
                    'patient_additional': '',
                    'patientcode': metadata.get('session_id', ''),
                    'equipment': metadata.get('equipment', 'EEG Processor'),
                    'admincode': '',
                    'gender': metadata.get('gender', ''),
                    'startdate': metadata.get('start_date', ''),
                    'birthdate': ''
                })
                
                # Configure channels
                for i, channel_name in enumerate(channel_names):
                    channel_info = {
                        'label': channel_name,
                        'dimension': 'uV',
                        'sample_rate': sampling_rate,
                        'physical_max': 100.0,
                        'physical_min': -100.0,
                        'digital_max': 32767,
                        'digital_min': -32768,
                        'prefilter': metadata.get('prefilter', ''),
                        'transducer': metadata.get('transducer', '')
                    }
                    writer.setSignalHeader(i, channel_info)
                
                # Write EEG data
                for i in range(eeg_data.shape[0]):
                    writer.writeSamples(eeg_data[i, :])
                
                # Add input events as annotations
                if 'events' in input_events:
                    events_data = input_events['events']
                    for event in events_data:
                        timestamp = event.get('timestamp', 0)
                        event_type = event.get('type', 'input')
                        event_data = str(event.get('data', ''))
                        
                        # Convert timestamp to seconds
                        onset_time = timestamp / 1000.0 if timestamp > 1e9 else timestamp
                        
                        # Add annotation
                        writer.writeAnnotation(
                            onset_time,
                            0,  # duration
                            f"{event_type}: {event_data}"
                        )
            
            logging.info(f"EDF+ dataset exported to {filepath}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to export EDF+ dataset: {e}")
            return False
    
    def validate_data(
        self,
        eeg_data: np.ndarray,
        input_events: Dict[str, Any]
    ) -> bool:
        """Validate data for EDF+ export."""
        if not EDF_AVAILABLE:
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
        return ['edf', 'edf+']