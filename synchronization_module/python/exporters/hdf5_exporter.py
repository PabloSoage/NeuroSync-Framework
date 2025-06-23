"""
HDF5 dataset exporter for synchronized EEG and input data.
"""

import logging
import os
from typing import Dict, Any, List
import numpy as np
import time

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
        filepath: str,
        append_mode: bool = False,
    ) -> bool:
        """Export dataset to HDF5 format."""
        if not HDF5_AVAILABLE:
            logging.error("h5py library not available. Install with: pip install h5py")
            return False

        try:
            # Ensure filepath has correct extension
            if not filepath.lower().endswith((".h5", ".hdf5")):
                filepath = filepath + self.file_extension

            logging.info(f"Starting HDF5 export to {filepath}")

            # Ensure directory exists
            directory = os.path.dirname(filepath)
            if directory:
                os.makedirs(directory, exist_ok=True)

            # Choose file mode based on append_mode
            mode = "a" if append_mode and os.path.exists(filepath) else "w"

            with h5py.File(filepath, mode) as f:
                # Create or get groups
                if "eeg" not in f:
                    eeg_group = f.create_group("eeg")
                else:
                    eeg_group = f["eeg"]

                if "events" not in f:
                    events_group = f.create_group("events")
                else:
                    events_group = f["events"]

                if "metadata" not in f:
                    meta_group = f.create_group("metadata")
                else:
                    meta_group = f["metadata"]

                # Generate unique dataset name for append mode
                timestamp = int(time.time())
                data_suffix = f"_{timestamp}" if append_mode else ""

                # Store EEG data
                logging.info(f"Storing EEG data shape: {eeg_data.shape}")
                compression = "gzip" if metadata.get("compress_data", True) else None
                eeg_group.create_dataset(
                    f"data{data_suffix}", data=eeg_data, compression=compression
                )

                if not append_mode or "sampling_rate" not in eeg_group:
                    eeg_group.create_dataset(
                        "sampling_rate", data=metadata.get("sampling_rate", 250)
                    )

                if "channel_names" in metadata and (
                    not append_mode or "channel_names" not in eeg_group
                ):
                    eeg_group.create_dataset(
                        "channel_names",
                        data=[
                            name.encode("utf-8") for name in metadata["channel_names"]
                        ],
                    )

                # Store input events
                if "events" in input_events and input_events["events"]:
                    events_data = input_events["events"]
                    logging.info(f"Storing {len(events_data)} events")

                    # Convert events to structured format
                    timestamps = [event.get("timestamp", 0) for event in events_data]
                    event_types = [
                        event.get("type", "").encode("utf-8") for event in events_data
                    ]
                    event_data = [
                        str(event.get("data", "")).encode("utf-8")
                        for event in events_data
                    ]

                    events_group.create_dataset(
                        f"timestamps{data_suffix}", data=timestamps
                    )
                    events_group.create_dataset(f"types{data_suffix}", data=event_types)
                    events_group.create_dataset(f"data{data_suffix}", data=event_data)
                else:
                    logging.info("No events to store")

                # Store metadata (only new/updated metadata in append mode)
                for key, value in metadata.items():
                    dataset_key = (
                        f"{key}{data_suffix}"
                        if append_mode and key in meta_group
                        else key
                    )

                    try:
                        if isinstance(value, (str, bytes)):
                            meta_group.create_dataset(
                                dataset_key,
                                data=(
                                    value.encode("utf-8")
                                    if isinstance(value, str)
                                    else value
                                ),
                            )
                        elif isinstance(value, (int, float)):
                            meta_group.create_dataset(dataset_key, data=value)
                        elif isinstance(value, (list, np.ndarray)):
                            meta_group.create_dataset(dataset_key, data=value)
                    except Exception as e:
                        logging.warning(f"Could not store metadata key '{key}': {e}")

                # Add synchronization info
                if "synchronization" not in f:
                    sync_group = f.create_group("synchronization")
                else:
                    sync_group = f["synchronization"]

                sync_group.create_dataset(
                    f"precision_ms{data_suffix}", data=metadata.get("precision_ms", 1.0)
                )
                sync_group.create_dataset(
                    f"export_timestamp{data_suffix}",
                    data=metadata.get("export_timestamp", time.time()),
                )

            logging.info(f"HDF5 dataset exported successfully to {filepath}")
            return True

        except Exception as e:
            logging.error(f"Failed to export HDF5 dataset: {e}")
            return False

    def validate_data(self, eeg_data: np.ndarray, input_events: Dict[str, Any]) -> bool:
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
        return ["hdf5", "h5"]
