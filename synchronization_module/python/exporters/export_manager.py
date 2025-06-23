"""
Export manager for handling dataset exports in multiple formats.
"""

import logging
import os
import time
from typing import Dict, Any, List, Optional
import numpy as np

from ..interfaces.export_interface import DatasetExporterInterface


class ExportManager:
    """Manages dataset exports in multiple formats."""

    def __init__(self):
        """Initialize export manager."""
        self.exporters: Dict[str, DatasetExporterInterface] = {}
        self.format_extensions = {
            "hdf5": ".h5",
            "h5": ".h5",
            "edf": ".edf",
            "edf+": ".edf",
            "csv": ".csv",
            "bids": "",  # BIDS is directory-based, no extension
        }

        # Try to initialize each exporter
        try:
            from .hdf5_exporter import HDF5Exporter

            self.exporters["hdf5"] = HDF5Exporter()
        except ImportError:
            logging.warning("HDF5 exporter not available")

        try:
            from .edf_exporter import EDFExporter

            edf_exporter = EDFExporter()
            self.exporters["edf"] = edf_exporter
            self.exporters["edf+"] = edf_exporter  # Same exporter for both
        except ImportError:
            logging.warning("EDF exporter not available")

        try:
            from .bids_exporter import BIDSExporter

            self.exporters["bids"] = BIDSExporter()
        except ImportError:
            logging.warning("BIDS exporter not available")

        try:
            from .csv_exporter import CSVExporter

            self.exporters["csv"] = CSVExporter()
        except ImportError:
            logging.warning("CSV exporter not available")

        logging.info(
            f"Export manager initialized with formats: {list(self.exporters.keys())}"
        )

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
        **kwargs,
    ) -> bool:
        """Export dataset in specified format."""
        # Normalize format name but keep 'edf+'
        original_format = format_name.lower()
        format_key = (
            original_format
            if original_format == "edf+"
            else original_format.replace("+", "")
        )

        if format_key not in self.exporters:
            logging.error(
                f"Unsupported format: {format_name}. Available: {list(self.exporters.keys())}"
            )
            return False

        try:
            exporter = self.exporters[format_key]

            # Validate data
            if not exporter.validate_data(eeg_data, input_events):
                logging.error(f"Data validation failed for {format_name}")
                return False

            # Add export timestamp to metadata
            export_metadata = metadata.copy()
            export_metadata["export_timestamp"] = time.time()

            # Add default file extension if not present (except for BIDS)
            if format_key != "bids":
                extension = self.format_extensions.get(format_key, "")
                if extension and not filepath.lower().endswith(extension):
                    filepath = filepath + extension
                    logging.info(f"Added file extension: {filepath}")

            # Ensure output directory exists
            directory = os.path.dirname(os.path.abspath(filepath))
            if directory:
                os.makedirs(directory, exist_ok=True)
                logging.info(f"Ensured directory exists: {directory}")

            # Export
            success = exporter.export_dataset(
                eeg_data=eeg_data,
                input_events=input_events,
                metadata=export_metadata,
                filepath=filepath,
                **kwargs,
            )

            if success:
                logging.info(
                    f"Successfully exported {format_name} dataset to {filepath}"
                )
            else:
                logging.error(f"Failed to export {format_name} dataset to {filepath}")

            return success

        except Exception as e:
            logging.error(f"Error exporting dataset: {e}")
            return False

    def validate_export_data(
        self, format_name: str, eeg_data: np.ndarray, input_events: Dict[str, Any]
    ) -> bool:
        """Validate data for specific format."""
        format_key = format_name.lower()
        if format_key not in self.exporters:
            return False

        return self.exporters[format_key].validate_data(eeg_data, input_events)

    def get_format_info(self, format_name: str) -> Dict[str, Any]:
        """Get information about a specific format."""
        format_key = format_name.lower()
        if format_key not in self.exporters:
            return {}

        exporter = self.exporters[format_key]
        return {
            "name": format_name,
            "description": getattr(exporter, "description", ""),
            "file_extension": getattr(exporter, "file_extension", ""),
            "supports_events": getattr(exporter, "supports_events", True),
            "supports_metadata": getattr(exporter, "supports_metadata", True),
        }

    def get_file_extension(self, format_name: str) -> str:
        """Get the default file extension for a format."""
        format_key = format_name.lower()
        if format_key in self.format_extensions:
            return self.format_extensions[format_key]
        return ""

    def cleanup(self) -> None:
        """Cleanup export resources."""
        for exporter in self.exporters.values():
            if hasattr(exporter, "cleanup"):
                exporter.cleanup()
