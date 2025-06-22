"""
Export manager for handling dataset exports in multiple formats.
"""
import logging
import os
from typing import Dict, Any, List, Optional
import numpy as np

from .hdf5_exporter import HDF5Exporter
from .edf_exporter import EDFExporter
from .bids_exporter import BIDSExporter
from ..interfaces.export_interface import DatasetExporterInterface


class ExportManager:
    """Manages dataset exports in multiple formats."""
    
    def __init__(self):
        """Initialize export manager."""
        self.exporters: Dict[str, DatasetExporterInterface] = {
            'hdf5': HDF5Exporter(),
            'edf': EDFExporter(), 
            'bids': BIDSExporter()
        }
        
        logging.info("Export manager initialized")
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats."""
        return list(self.exporters.keys())
    
    def export_dataset(
        self,
        format_name: str,
        eeg_data: np.ndarray,
        input_events: Dict[str, Any],
        metadata: Dict[str, Any],
        filepath: str,
        **kwargs
    ) -> bool:
        """Export dataset in specified format."""
        if format_name not in self.exporters:
            logging.error(f"Unsupported format: {format_name}")
            return False
        
        try:
            exporter = self.exporters[format_name]
            
            # Validate data
            if not exporter.validate_data(eeg_data, input_events):
                logging.error(f"Data validation failed for {format_name}")
                return False
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Export
            success = exporter.export_dataset(
                eeg_data, input_events, metadata, filepath
            )
            
            if success:
                logging.info(f"Successfully exported dataset to {filepath}")
            else:
                logging.error(f"Failed to export dataset to {filepath}")
                
            return success
            
        except Exception as e:
            logging.error(f"Error exporting dataset: {e}")
            return False
    
    def validate_export_data(
        self,
        format_name: str,
        eeg_data: np.ndarray,
        input_events: Dict[str, Any]
    ) -> bool:
        """Validate data for specific format."""
        if format_name not in self.exporters:
            return False
            
        return self.exporters[format_name].validate_data(eeg_data, input_events)
    
    def get_format_info(self, format_name: str) -> Dict[str, Any]:
        """Get information about a specific format."""
        if format_name not in self.exporters:
            return {}
            
        exporter = self.exporters[format_name]
        return {
            'name': format_name,
            'description': getattr(exporter, 'description', ''),
            'file_extension': getattr(exporter, 'file_extension', ''),
            'supports_events': getattr(exporter, 'supports_events', True),
            'supports_metadata': getattr(exporter, 'supports_metadata', True)
        }
    
    def cleanup(self) -> None:
        """Cleanup export resources."""
        for exporter in self.exporters.values():
            if hasattr(exporter, 'cleanup'):
                exporter.cleanup()