"""
CSV dataset exporter for synchronized EEG and input data.
"""

import logging
import os
import time
from typing import Dict, Any, List
import numpy as np

from ..interfaces.export_interface import DatasetExporterInterface


class CSVExporter(DatasetExporterInterface):
    """Exports synchronized datasets to CSV format."""

    description = "CSV format for data analysis and spreadsheet compatibility"
    file_extension = ".csv"
    supports_events = True
    supports_metadata = True

    def __init__(self) -> None:
        """Initialize CSV exporter."""
        self.logger = logging.getLogger("csv_exporter")
        self.logger.setLevel(logging.INFO)

    def export_dataset(
        self,
        eeg_data: np.ndarray,
        input_events: Dict[str, Any],
        metadata: Dict[str, Any],
        filepath: str,
    ) -> bool:
        """Export dataset to CSV format."""
        try:
            # Ensure filepath has correct extension
            if not filepath.lower().endswith(".csv"):
                filepath = filepath + self.file_extension
                self.logger.info(f"Added .csv extension: {filepath}")

            self.logger.info(f"Starting CSV export to {filepath}")

            # Ensure directory exists
            directory = os.path.dirname(os.path.abspath(filepath))
            if directory:
                os.makedirs(directory, exist_ok=True)
                self.logger.info(f"Ensured directory exists: {directory}")

            # Validate data first
            if not self._validate_export_data(eeg_data, input_events):
                self.logger.error("Data validation failed")
                return False

            self.logger.info(f"Exporting EEG data shape: {eeg_data.shape}")

            # Get metadata with defaults
            sampling_rate = metadata.get("sampling_rate", 250)
            board_name = metadata.get("board_name", "Unknown")
            board_id = metadata.get("board_id", -1)

            # Generate column names using EEG processor structure
            column_names = self._generate_eeg_column_names(eeg_data.shape[0], metadata)

            # Create event lookup for efficient access
            events_by_sample = self._create_event_lookup(
                input_events, sampling_rate, eeg_data.shape[1], metadata
            )

            self.logger.info(
                f"Created event lookup with {len(events_by_sample)} event samples"
            )

            # Write file using EEG processor format
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                # Write EEG processor style metadata header
                self._write_eeg_style_header(
                    f, metadata, eeg_data.shape, sampling_rate, board_name, board_id
                )

                # Write column headers (EEG processor style with tabs)
                header_line = "\t".join(column_names)
                f.write(header_line + "\n")
                self.logger.info(f"Written headers: {len(column_names)} columns")

                # Write data rows
                total_written = 0
                chunk_size = 1000

                for chunk_start in range(0, eeg_data.shape[1], chunk_size):
                    chunk_end = min(chunk_start + chunk_size, eeg_data.shape[1])

                    for i in range(chunk_start, chunk_end):
                        # Build row data - each column corresponds to EEG structure
                        row_data = []

                        for ch in range(eeg_data.shape[0]):
                            if (
                                ch == eeg_data.shape[0] - 2
                            ):  # Timestamp column (penultimate)
                                # Use actual timestamp from EEG data
                                row_data.append(f"{eeg_data[ch, i]:.6f}")
                            elif ch == eeg_data.shape[0] - 1:  # Marker column (last)
                                # Check if we have input events for this sample
                                if i in events_by_sample:
                                    # Combine all events for this sample into a single string
                                    event_str = "; ".join(events_by_sample[i])
                                    row_data.append(event_str)
                                else:
                                    # Use EEG marker value or 0
                                    row_data.append(f"{eeg_data[ch, i]:.6f}")
                            else:
                                # Regular EEG channel data
                                row_data.append(f"{eeg_data[ch, i]:.6f}")

                        # Write row with tabs (EEG processor style)
                        f.write("\t".join(row_data) + "\n")
                        total_written += 1

                    # Flush periodically
                    if chunk_end % (chunk_size * 10) == 0:
                        f.flush()
                        self.logger.debug(
                            f"Written {chunk_end}/{eeg_data.shape[1]} samples"
                        )

            self.logger.info(
                f"CSV export completed: {total_written} samples written to {filepath}"
            )

            # Verify file was created
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                self.logger.info(f"Export successful: file size {file_size} bytes")
                return True
            else:
                self.logger.error("File was not created")
                return False

        except Exception as e:
            self.logger.error(f"Failed to export CSV dataset: {e}", exc_info=True)
            return False

    def _write_eeg_style_header(
        self,
        file_handle,
        metadata: Dict[str, Any],
        data_shape: tuple,
        sampling_rate: float,
        board_name: str,
        board_id: int,
    ) -> None:
        """Write EEG processor style metadata header."""
        try:
            # Calculate duration from data shape
            duration = data_shape[1] / sampling_rate

            # EEG processor style header
            header_lines = [
                f"# EEG Recording - {time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"# Board: {board_name} (ID: {board_id})",
                f"# Preset: {metadata.get('preset', 0)}",
                f"# Sampling Rate: {sampling_rate} Hz",
                f"# Data Type: synchronized",  # Indicate this is synchronized data
                f"# Channels: {data_shape[0]}",
                f"# Samples: {data_shape[1]}",
                f"# Duration: {duration:.2f} seconds",
            ]

            # Add sync information
            if "synchronization_precision_ms" in metadata:
                header_lines.append(
                    f"# Sync Precision: {metadata['synchronization_precision_ms']} ms"
                )
            if "sync_quality" in metadata:
                header_lines.append(f"# Sync Quality: {metadata['sync_quality']:.2%}")

            # Write header lines
            for line in header_lines:
                file_handle.write(line + "\n")

        except Exception as e:
            self.logger.warning(f"Error writing metadata header: {e}")
            # Write minimal header
            file_handle.write(
                f"# EEG Recording - {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            file_handle.write(
                f"# Channels: {data_shape[0]}, Samples: {data_shape[1]}\n"
            )

    def _generate_eeg_column_names(
        self, num_channels: int, metadata: Dict[str, Any]
    ) -> List[str]:
        """Generate EEG processor style column names."""
        # Get channel information from metadata
        channel_names = metadata.get("channel_names", [])

        self.logger.info(f"Generating column names for {num_channels} channels")
        self.logger.info(
            f"Available channel names from metadata: {len(channel_names)} names"
        )

        # If we have proper channel names from EEG metadata, use them directly
        if channel_names and len(channel_names) >= num_channels:
            self.logger.info(f"Using provided channel names: {channel_names[:5]}...")
            # Use the channel names exactly as provided by the EEG processor
            return channel_names[:num_channels]

        # If we have some channel names but not enough, try to extend logically
        elif channel_names and len(channel_names) > 0:
            self.logger.info(
                f"Extending {len(channel_names)} channel names to {num_channels}"
            )
            extended_names = channel_names.copy()

            # Add missing channels following the pattern
            for i in range(len(channel_names), num_channels):
                if i == num_channels - 2:
                    extended_names.append("Timestamp")
                elif i == num_channels - 1:
                    extended_names.append("Marker")
                else:
                    extended_names.append(f"CH_{i}")

            return extended_names

        else:
            # Fallback: generate standard names following EEG processor pattern
            self.logger.warning("No channel names available, generating fallback names")
            column_names = []

            for i in range(num_channels):
                if i == 0:
                    column_names.append("CH_0")  # Sample counter
                elif i < num_channels - 2:
                    column_names.append(f"EEG_Ch{i}")  # EEG channels
                elif i == num_channels - 2:
                    column_names.append("Timestamp")  # Timestamp column
                elif i == num_channels - 1:
                    column_names.append("Marker")  # Marker column

            return column_names

    def _create_event_lookup(
        self,
        input_events: Dict[str, Any],
        sampling_rate: float,
        num_samples: int,
        metadata: Dict[str, Any],
    ) -> Dict[int, List[str]]:
        """Create event lookup dictionary mapping sample index to event strings."""
        events_by_sample = {}

        try:
            if "events" not in input_events or not input_events["events"]:
                self.logger.info("No input events to process")
                return events_by_sample

            events_data = input_events["events"]
            self.logger.info(f"Processing {len(events_data)} events")

            for event in events_data:
                try:
                    timestamp = event.get("timestamp", 0)

                    # Convert timestamp to sample index
                    sample_idx = self._timestamp_to_sample_index(
                        timestamp, sampling_rate, metadata
                    )

                    if 0 <= sample_idx < num_samples:
                        if sample_idx not in events_by_sample:
                            events_by_sample[sample_idx] = []

                        # Create a compact event string (like JSON but simpler)
                        event_str = self._format_event_string(event)
                        events_by_sample[sample_idx].append(event_str)
                    else:
                        self.logger.debug(
                            f"Event timestamp out of range: {timestamp} -> sample {sample_idx}"
                        )

                except Exception as e:
                    self.logger.warning(f"Error processing event {event}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error creating event lookup: {e}")

        return events_by_sample

    def _format_event_string(self, event: Dict[str, Any]) -> str:
        """Format event as a compact string suitable for CSV cell."""
        try:
            # Create a compact representation
            event_type = event.get("type", "input")

            # For input events, create a JSON-like but compact string
            if "data" in event:
                data = event["data"]
                if isinstance(data, dict):
                    # Create compact representation of input data
                    compact_data = {}
                    for key, value in data.items():
                        if (
                            value is not None
                            and value != 0
                            and value != ""
                            and value != []
                        ):
                            compact_data[key] = value

                    if compact_data:
                        import json

                        return f"{event_type}:{json.dumps(compact_data, separators=(',', ':'))}"
                    else:
                        return f"{event_type}:no_data"
                else:
                    return f"{event_type}:{data}"
            else:
                return event_type

        except Exception as e:
            self.logger.warning(f"Error formatting event: {e}")
            return "input:error"

    def _timestamp_to_sample_index(
        self, timestamp: float, sampling_rate: float, metadata: Dict[str, Any]
    ) -> int:
        """Convert timestamp to sample index."""
        try:
            # Handle different timestamp formats
            if timestamp > 1e9:  # Unix timestamp in seconds
                start_timestamp = metadata.get("start_timestamp", timestamp)
                relative_time = timestamp - start_timestamp
            elif timestamp > 1e6:  # Unix timestamp in milliseconds
                start_timestamp_ms = (
                    metadata.get("start_timestamp", timestamp / 1000.0) * 1000.0
                )
                relative_time = (timestamp - start_timestamp_ms) / 1000.0
            else:  # Relative time in seconds
                relative_time = timestamp

            return int(round(relative_time * sampling_rate))

        except Exception as e:
            self.logger.warning(f"Error converting timestamp {timestamp}: {e}")
            return int(round(timestamp * sampling_rate))

    def _validate_export_data(
        self, eeg_data: np.ndarray, input_events: Dict[str, Any]
    ) -> bool:
        """Validate data for export."""
        try:
            if eeg_data.size == 0:
                self.logger.error("EEG data is empty")
                return False

            if len(eeg_data.shape) != 2:
                self.logger.error(
                    f"EEG data must be 2D (channels x samples), got shape: {eeg_data.shape}"
                )
                return False

            if eeg_data.shape[1] == 0:
                self.logger.error("EEG data has no samples")
                return False

            if not isinstance(input_events, dict):
                self.logger.error("Input events must be a dictionary")
                return False

            self.logger.info("Data validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Error validating data: {e}")
            return False

    def validate_data(self, eeg_data: np.ndarray, input_events: Dict[str, Any]) -> bool:
        """Validate data for CSV export."""
        return self._validate_export_data(eeg_data, input_events)

    def get_supported_formats(self) -> List[str]:
        """Get supported formats."""
        return ["csv"]
