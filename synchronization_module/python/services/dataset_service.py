"""
Dataset service for managing dataset creation and export operations.
"""

import logging
import time
from typing import Dict, Any, Optional, List
import numpy as np

from ..exporters.export_manager import ExportManager


class DatasetService:
    """
    Service for dataset management and export operations.

    This service handles the creation, validation, and export of synchronized
    datasets in various formats.
    """

    def __init__(self):
        """Initialize the dataset service."""
        self.logger = logging.getLogger(__name__)

        # Initialize export manager
        self.export_manager = ExportManager()

        # Dataset storage
        self.current_dataset: Optional[Dict[str, Any]] = None

        self.logger.info("Dataset service initialized")

    def create_dataset(
        self,
        eeg_data: np.ndarray,
        input_events: Dict[str, Any],
        sync_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a synchronized dataset.

        Args:
            eeg_data: EEG data array (channels x samples)
            input_events: Input events dictionary
            sync_metadata: Synchronization metadata

        Returns:
            Dataset dictionary
        """
        try:
            # Generate dataset metadata
            dataset_metadata = self._generate_dataset_metadata(sync_metadata)

            # Validate data
            if not self._validate_dataset_data(eeg_data, input_events):
                raise ValueError("Dataset validation failed")

            # Create dataset structure
            dataset = {
                "eeg_data": eeg_data,
                "input_events": input_events,
                "metadata": dataset_metadata,
                "sync_info": sync_metadata,
                "created_at": time.time(),
            }

            self.current_dataset = dataset
            self.logger.info("Dataset created successfully")

            return dataset

        except Exception as e:
            self.logger.error(f"Error creating dataset: {e}")
            raise

    def export_dataset(
        self,
        dataset: Dict[str, Any],
        filepath: str,
        format_name: str = "hdf5",
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Export dataset to specified format.

        Args:
            dataset: Dataset to export
            filepath: Output file path
            format_name: Export format ('hdf5', 'edf', 'bids')
            custom_metadata: Additional metadata

        Returns:
            True if export successful
        """
        try:
            # Prepare export metadata
            export_metadata = dataset.get("metadata", {}).copy()
            if custom_metadata:
                export_metadata.update(custom_metadata)

            # Add export timestamp
            export_metadata["export_timestamp"] = time.time()

            # Export using export manager
            success = self.export_manager.export_dataset(
                format_name=format_name,
                eeg_data=dataset["eeg_data"],
                input_events=dataset["input_events"],
                metadata=export_metadata,
                filepath=filepath,
            )

            if success:
                self.logger.info(f"Dataset exported successfully to {filepath}")
            else:
                self.logger.error(f"Failed to export dataset to {filepath}")

            return success

        except Exception as e:
            self.logger.error(f"Error exporting dataset: {e}")
            return False

    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats."""
        return self.export_manager.get_supported_formats()

    def validate_export_data(self, dataset: Dict[str, Any], format_name: str) -> bool:
        """
        Validate dataset for export in specific format.

        Args:
            dataset: Dataset to validate
            format_name: Target export format

        Returns:
            True if data is valid for export
        """
        try:
            return self.export_manager.validate_export_data(
                format_name, dataset["eeg_data"], dataset["input_events"]
            )
        except Exception as e:
            self.logger.error(f"Error validating export data: {e}")
            return False

    def get_format_info(self, format_name: str) -> Dict[str, Any]:
        """Get information about a specific format."""
        return self.export_manager.get_format_info(format_name)

    def _generate_dataset_metadata(
        self, sync_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive dataset metadata."""
        metadata = {
            "dataset_version": "1.0",
            "created_by": "BCI Dataset Creator",
            "creation_timestamp": time.time(),
            "synchronization_precision_ms": sync_metadata.get("precision_ms", 1.0),
            "sync_quality": sync_metadata.get("sync_quality", 0.0),
            "sync_method": "LSL",
        }

        # Add EEG metadata
        eeg_info = sync_metadata.get("eeg_info", {})
        if eeg_info:
            metadata.update(
                {
                    "sampling_rate": eeg_info.get("sampling_rate", 250),
                    "channel_names": eeg_info.get("channel_names", []),
                    "board_name": eeg_info.get("board_name", ""),
                    "num_channels": eeg_info.get("num_channels", 0),
                }
            )

        # Add input metadata
        input_info = sync_metadata.get("input_info", {})
        if input_info:
            metadata.update(
                {
                    "input_collector_type": input_info.get("collector_type", ""),
                    "tracked_keys": input_info.get("tracked_keys", []),
                    "input_devices": input_info.get("devices", []),
                }
            )

        return metadata

    def _validate_dataset_data(
        self, eeg_data: np.ndarray, input_events: Dict[str, Any]
    ) -> bool:
        """Validate dataset data."""
        try:
            # Validate EEG data
            if eeg_data.size == 0:
                self.logger.error("EEG data is empty")
                return False

            if len(eeg_data.shape) != 2:
                self.logger.error("EEG data must be 2D (channels x samples)")
                return False

            # Validate input events
            if not isinstance(input_events, dict):
                self.logger.error("Input events must be a dictionary")
                return False

            if "events" in input_events:
                events = input_events["events"]
                if not isinstance(events, list):
                    self.logger.error("Events must be a list")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating dataset data: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up dataset service resources."""
        try:
            if hasattr(self, "export_manager"):
                self.export_manager.cleanup()

            self.current_dataset = None
            self.logger.info("Dataset service cleaned up")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
