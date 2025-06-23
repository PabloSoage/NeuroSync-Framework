"""
EDF+ dataset exporter for synchronized EEG and input data.
"""

import logging
import os
from typing import Dict, Any, List
import numpy as np
import datetime

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
        filepath: str,
    ) -> bool:
        """Export dataset to EDF+ format."""
        if not EDF_AVAILABLE:
            logging.error("EDF+ not available. Please install pyedflib package.")
            return False

        # Ensure filepath has correct extension
        if not filepath.lower().endswith(".edf"):
            filepath = filepath + self.file_extension

        # Ensure directory exists
        directory = os.path.dirname(os.path.abspath(filepath))
        if directory:
            os.makedirs(directory, exist_ok=True)

        try:
            # Validate input data dimensions
            if eeg_data.size == 0 or len(eeg_data.shape) != 2:
                logging.error(f"Invalid EEG data shape: {eeg_data.shape}")
                return False

            # Prepare channel information
            sampling_rate = metadata.get("sampling_rate", 250)
            channel_names = metadata.get("channel_names", [])

            if not channel_names or len(channel_names) != eeg_data.shape[0]:
                channel_names = [f"Ch{i+1}" for i in range(eeg_data.shape[0])]

            # Ensure channel_names are strings and not too long (EDF+ limit is 16 chars)
            channel_names = [str(name)[:16] for name in channel_names]

            logging.info(
                f"Creating EDF+ file with {len(channel_names)} channels at {sampling_rate}Hz"
            )

            # Get current time for recording start date
            start_date = datetime.datetime.now()
            try:
                # Try to get timestamp from metadata
                start_timestamp = metadata.get("start_timestamp")
                if (
                    start_timestamp
                    and isinstance(start_timestamp, (int, float))
                    and start_timestamp > 1000000000
                ):
                    # Convert Unix timestamp to datetime
                    start_date = datetime.datetime.fromtimestamp(start_timestamp)
                    logging.info(f"Using provided start date: {start_date}")
            except Exception as e:
                logging.warning(
                    f"Could not parse start timestamp, using current date: {e}"
                )

            # Create EDF+ file writer
            try:
                num_channels = len(channel_names)
                writer = pyedflib.EdfWriter(
                    filepath, num_channels, file_type=pyedflib.FILETYPE_EDFPLUS
                )
                logging.info(f"EDF writer created with {num_channels} channels")
            except Exception as e:
                logging.error(f"Failed to create EDF writer: {e}")
                return False

            # Set header information with all required fields
            header = {
                "technician": "BCI Dataset Creator",
                "recording_additional": "Synchronized EEG and Input Data",
                "patientname": metadata.get("subject_id", "Anonymous"),
                "patient_additional": "",
                "patientcode": metadata.get("session_id", ""),
                "equipment": metadata.get("board_name", "EEG Processor"),
                "admincode": "",
                "gender": metadata.get("gender", "X"),  # Required field: X for unknown
                "startdate": start_date,  # Using datetime object instead of string
                "birthdate": start_date.replace(
                    year=start_date.year - 25
                ),  # Required field, using fake date
                "sex": "X",  # Required field: M, F, or X for unknown
            }

            # Remove any None values that might cause issues
            header = {k: v if v is not None else "" for k, v in header.items()}

            try:
                writer.setHeader(header)
                logging.info("EDF header set successfully")
            except Exception as e:
                logging.error(f"Failed to set EDF header: {e}")
                writer.close()
                return False

            # Configure signal parameters for each channel
            signal_headers = []

            for i, channel_name in enumerate(channel_names):
                # Calculate reasonable physical min/max from data
                ch_data = eeg_data[i, :]
                data_min = float(np.min(ch_data))
                data_max = float(np.max(ch_data))

                # Ensure we have reasonable ranges
                if abs(data_max - data_min) < 1e-6:
                    data_min = -100.0
                    data_max = 100.0
                else:
                    # Add 10% padding
                    padding = (data_max - data_min) * 0.1
                    data_min -= padding
                    data_max += padding

                signal_headers.append(
                    {
                        "label": channel_name,
                        "dimension": "uV",
                        "sample_rate": int(sampling_rate),
                        "physical_max": data_max,
                        "physical_min": data_min,
                        "digital_max": 32767,
                        "digital_min": -32768,
                        "prefilter": str(metadata.get("prefilter", "")),
                        "transducer": str(metadata.get("transducer", "")),
                    }
                )

            # Set signal headers
            for i, signal_header in enumerate(signal_headers):
                try:
                    writer.setSignalHeader(i, signal_header)
                except Exception as e:
                    logging.error(f"Failed to set signal header for channel {i}: {e}")
                    writer.close()
                    return False

            # Write EEG data channel by channel
            for i in range(len(channel_names)):
                try:
                    # Convert data to float64 as required by pyedflib
                    channel_data = eeg_data[i, :].astype(np.float64)
                    writer.writeSignal(i, channel_data)
                    logging.debug(f"Wrote {len(channel_data)} samples for channel {i}")
                except Exception as e:
                    logging.error(f"Failed to write signal data for channel {i}: {e}")
                    writer.close()
                    return False

            # Add input events as annotations
            if "events" in input_events and input_events["events"]:
                events_data = input_events["events"]
                logging.info(f"Adding {len(events_data)} annotations")

                try:
                    for event in events_data:
                        timestamp = event.get("timestamp", 0)
                        event_type = event.get("type", "input")
                        event_data = str(event.get("data", ""))

                        # Convert timestamp to seconds relative to recording start
                        if timestamp > 1e9:  # Unix timestamp
                            # Convert to relative time
                            start_timestamp_ms = metadata.get(
                                "start_timestamp", timestamp
                            )
                            onset_time = max(
                                0, (timestamp - start_timestamp_ms) / 1000.0
                            )
                        else:
                            onset_time = float(timestamp)

                        # Ensure onset is within recording duration
                        max_time = eeg_data.shape[1] / sampling_rate
                        if onset_time <= max_time:
                            # Add annotation
                            writer.writeAnnotation(
                                onset_time, 0, f"{event_type}: {event_data}"  # duration
                            )
                except Exception as e:
                    logging.error(f"Failed to write annotations: {e}")
                    # Continue without annotations

            # Close and finalize file
            writer.close()
            logging.info(f"EDF+ dataset exported successfully to {filepath}")
            return True

        except Exception as e:
            logging.error(f"Failed to export EDF+ dataset: {e}")
            return False

    def validate_data(self, eeg_data: np.ndarray, input_events: Dict[str, Any]) -> bool:
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
        return ["edf", "edf+"]
