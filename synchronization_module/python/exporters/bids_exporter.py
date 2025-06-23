"""
BIDS dataset exporter for synchronized EEG and input data.
"""

import json
import logging
import os
from typing import Dict, Any, List
import numpy as np

try:
    import mne
    from mne_bids import BIDSPath, write_raw_bids

    BIDS_AVAILABLE = True
except ImportError:
    BIDS_AVAILABLE = False

from ..interfaces.export_interface import DatasetExporterInterface


class BIDSExporter(DatasetExporterInterface):
    """Exports synchronized datasets to BIDS format."""

    description = "BIDS format for neuroimaging data"
    file_extension = ""  # Directory-based format
    supports_events = True
    supports_metadata = True

    def __init__(self):
        """Initialize BIDS exporter."""
        if not BIDS_AVAILABLE:
            logging.warning(
                "MNE and mne-bids not available. BIDS export will be disabled."
            )

    def export_dataset(
        self,
        eeg_data: np.ndarray,
        input_events: Dict[str, Any],
        metadata: Dict[str, Any],
        filepath: str,
    ) -> bool:
        """Export dataset to BIDS format."""
        if not BIDS_AVAILABLE:
            logging.error("BIDS not available")
            return False

        try:
            # Prepare MNE data structure
            sampling_rate = metadata.get("sampling_rate", 250)
            channel_names = metadata.get("channel_names", [])

            # Ensure channel names match data dimensions
            actual_channels = eeg_data.shape[0]
            if not channel_names or len(channel_names) != actual_channels:
                channel_names = [f"EEG{i+1:03d}" for i in range(actual_channels)]
                logging.warning(
                    f"Channel names mismatch. Using generated names for {actual_channels} channels"
                )

            # Truncate or pad channel names to match data
            if len(channel_names) > actual_channels:
                channel_names = channel_names[:actual_channels]
            elif len(channel_names) < actual_channels:
                for i in range(len(channel_names), actual_channels):
                    channel_names.append(f"EEG{i+1:03d}")

            # Create MNE info structure
            info = mne.create_info(
                ch_names=channel_names,
                sfreq=sampling_rate,
                ch_types=["eeg"] * len(channel_names),
            )

            # Convert data to volts (BIDS requirement)
            if metadata.get("unit", "uV") == "uV":
                eeg_data_v = eeg_data * 1e-6  # Convert µV to V
            else:
                eeg_data_v = eeg_data

            # Ensure data is the right shape and type
            eeg_data_v = eeg_data_v.astype(np.float64)

            # Create MNE Raw object
            raw = mne.io.RawArray(eeg_data_v, info)

            # Add input events as annotations
            events_for_mne = []
            event_ids = {}

            if "events" in input_events and input_events["events"]:
                events_data = input_events["events"]
                onsets = []
                durations = []
                descriptions = []

                for event in events_data:
                    try:
                        timestamp = event.get("timestamp", 0)
                        event_type = str(event.get("type", "input"))
                        event_data = str(event.get("data", ""))

                        # Convert timestamp to seconds relative to recording start
                        if timestamp > 1e9:  # Unix timestamp
                            start_timestamp = metadata.get("start_timestamp", timestamp)
                            onset_time = (
                                timestamp - start_timestamp
                            ) / 1000.0  # ms to seconds
                        else:
                            onset_time = float(timestamp)

                        # Ensure onset time is within data range and non-negative
                        max_time = eeg_data.shape[1] / sampling_rate
                        if 0 <= onset_time <= max_time:
                            onsets.append(onset_time)
                            durations.append(0)  # Point events
                            event_name = f"{event_type}_{event_data}"
                            descriptions.append(event_name)

                            # Add to event_ids dictionary
                            if event_name not in event_ids:
                                event_ids[event_name] = len(event_ids) + 1

                    except Exception as e:
                        logging.warning(f"Could not process event for BIDS: {e}")

                if onsets:
                    # Create annotations object
                    annotations = mne.Annotations(
                        onset=onsets, duration=durations, description=descriptions
                    )
                    raw.set_annotations(annotations)

                    # Convert annotations to events array
                    events_for_mne, _ = mne.events_from_annotations(
                        raw, event_id=event_ids
                    )

            # Setup BIDS path
            bids_root = filepath
            subject_id = metadata.get("subject_id", "001")
            session_id = metadata.get("session_id", "001")
            task_name = metadata.get("task", "bci")

            bids_path = BIDSPath(
                subject=subject_id,
                session=session_id,
                task=task_name,
                datatype="eeg",
                root=bids_root,
            )

            # Write BIDS dataset
            write_raw_bids(
                raw,
                bids_path,
                event_id=event_ids if event_ids else None,
                events=events_for_mne if len(events_for_mne) > 0 else None,
                format="BrainVision",  # BrainVision format for EEG data
                overwrite=True,
                allow_preload=True,
            )

            # Add custom metadata
            self._write_custom_metadata(bids_path, metadata, input_events)

            logging.info(f"BIDS dataset exported to {bids_root}")
            return True

        except Exception as e:
            logging.error(f"Failed to export BIDS dataset: {e}")
            return False

    def _write_custom_metadata(
        self, bids_path: Any, metadata: Dict[str, Any], input_events: Dict[str, Any]
    ) -> None:
        """Write custom metadata files."""
        try:
            # Write task events TSV file
            if "events" in input_events:
                events_tsv_path = bids_path.copy().update(
                    suffix="events", extension=".tsv"
                )
                self._write_events_tsv(events_tsv_path.fpath, input_events["events"])

            # Write dataset description
            dataset_desc_path = os.path.join(bids_path.root, "dataset_description.json")
            if not os.path.exists(dataset_desc_path):
                dataset_description = {
                    "Name": "BCI Dataset",
                    "BIDSVersion": "1.6.0",
                    "Authors": ["BCI Dataset Creator"],
                    "DatasetType": "raw",
                    "Description": "Synchronized EEG and input data for BCI research",
                }
                with open(dataset_desc_path, "w") as f:
                    json.dump(dataset_description, f, indent=2)

        except Exception as e:
            logging.error(f"Error writing custom metadata: {e}")

    def _write_events_tsv(self, filepath: str, events: List[Dict]) -> None:
        """Write events to TSV file."""
        try:
            with open(filepath, "w") as f:
                # Write header
                f.write("onset\tduration\ttrial_type\tvalue\n")

                # Write events
                for event in events:
                    timestamp = event.get("timestamp", 0)
                    onset_time = timestamp / 1000.0 if timestamp > 1e9 else timestamp

                    event_type = event.get("type", "input")
                    event_data = str(event.get("data", ""))

                    f.write(f"{onset_time}\t0\t{event_type}\t{event_data}\n")

        except Exception as e:
            logging.error(f"Error writing events TSV: {e}")

    def validate_data(self, eeg_data: np.ndarray, input_events: Dict[str, Any]) -> bool:
        """Validate data for BIDS export."""
        if not BIDS_AVAILABLE:
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
        return ["bids"]
