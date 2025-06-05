"""
LSL synchronization service for unified application.

This module provides synchronization between EEG data and input events
using Lab Streaming Layer (LSL) for millisecond-precision timing.
"""

import threading
import time

from PyQt5.QtCore import QObject, pyqtSignal

# Import LSL
try:
    import pylsl

    LSL_AVAILABLE = True
except ImportError:
    print("Warning: pylsl module not found. Install with: pip install pylsl")
    LSL_AVAILABLE = False

# Define stream types
STREAM_TYPE_EEG = "EEG"
STREAM_TYPE_INPUT = "InputEvents"
STREAM_TYPE_MARKERS = "Markers"


class LSLSyncService(QObject):
    """
    Service for synchronizing EEG and input data using LSL.

    This service creates LSL streams, handles data routing between components,
    and provides synchronized data for visualization and export.
    """

    # Signals
    sync_update = pyqtSignal(dict)  # Emitted when new synchronized data is available
    status_message = pyqtSignal(str, str)  # message, color
    new_dataset_sample = pyqtSignal(dict)  # Emitted for each new synchronized sample
    sync_tolerance_exceeded = pyqtSignal(
        float
    )  # Emitted when synchronization delay exceeds tolerance

    def __init__(self):
        """Initialize the LSL synchronization service."""
        super().__init__()

        self.lsl_available = LSL_AVAILABLE
        if not self.lsl_available:
            self.status_message.emit(
                "LSL (Lab Streaming Layer) is not available. Install with: pip install pylsl",
                "warning",
            )
            return

        # LSL outlets and inlets
        self.eeg_outlet = None
        self.input_outlet = None
        self.marker_outlet = None
        self.eeg_inlet = None
        self.input_inlet = None
        self.marker_inlet = None

        # Data buffers for visualization and recording
        self.eeg_buffer = []
        self.input_buffer = []
        self.marker_buffer = []

        # Maximum buffer sizes
        self.max_buffer_size = 1000  # Store last 1000 samples for each stream

        # Synchronization parameters
        self.sync_tolerance = 10.0  # Default tolerance in milliseconds
        self.last_sync_delay = 0.0  # Last measured synchronization delay

        # Synchronized dataset
        self.dataset = {"eeg": [], "input": [], "markers": [], "timestamps": []}

        # Recording state
        self.is_recording = False
        self.recording_start_time = 0

        # Thread for pulling data from LSL
        self.running = False
        self.pull_thread = None

    def initialize_streams(
        self,
        eeg_channels=8,
        eeg_sample_rate=250,
        input_channels=20,
        input_sample_rate=60,
    ):
        """
        Initialize LSL streams for EEG and input data.

        Args:
            eeg_channels: Number of EEG channels
            eeg_sample_rate: EEG sample rate in Hz
            input_channels: Number of input channels (keys, buttons, etc.)
            input_sample_rate: Input sample rate in Hz

        Returns:
            bool: True if initialization was successful
        """
        if not self.lsl_available:
            return False

        try:
            # Create EEG stream info
            eeg_info = pylsl.StreamInfo(
                "UnifiedEEG",
                STREAM_TYPE_EEG,
                eeg_channels,
                eeg_sample_rate,
                "float32",
                "unified_eeg_id",
            )

            # Add metadata to EEG stream
            eeg_desc = eeg_info.desc()
            eeg_desc.append_child_value("manufacturer", "Unified EEG Input Framework")

            channels = eeg_desc.append_child("channels")
            for c in range(eeg_channels):
                channels.append_child("channel").append_child_value(
                    "label", f"EEG{c+1}"
                ).append_child_value("type", "EEG").append_child_value(
                    "unit", "microvolts"
                )

            # Create input events stream info
            input_info = pylsl.StreamInfo(
                "UnifiedInput",
                STREAM_TYPE_INPUT,
                input_channels,
                input_sample_rate,
                "float32",
                "unified_input_id",
            )

            # Add metadata to input stream
            input_desc = input_info.desc()
            input_desc.append_child_value("manufacturer", "Unified EEG Input Framework")

            # Create marker stream info (for event markers)
            marker_info = pylsl.StreamInfo(
                "UnifiedMarkers",
                STREAM_TYPE_MARKERS,
                1,
                0,  # Irregular sampling rate (use 0)
                "int32",
                "unified_markers_id",
            )

            # Create outlets
            self.eeg_outlet = pylsl.StreamOutlet(eeg_info)
            self.input_outlet = pylsl.StreamOutlet(input_info)
            self.marker_outlet = pylsl.StreamOutlet(marker_info)

            self.status_message.emit("LSL streams initialized successfully", "success")
            return True

        except Exception as e:
            self.status_message.emit(
                f"Error initializing LSL streams: {str(e)}", "error"
            )
            return False

    def discover_streams(self, timeout=2.0):
        """
        Discover available LSL streams on the network.

        Args:
            timeout: Time to wait for streams (seconds)

        Returns:
            dict: Dictionary of discovered streams by type
        """
        if not self.lsl_available:
            return {}

        try:
            # Discover all streams
            streams = pylsl.resolve_streams(timeout)

            # Group by stream type
            result = {}
            for stream in streams:
                stream_type = stream.type()
                if stream_type not in result:
                    result[stream_type] = []
                result[stream_type].append(
                    {
                        "name": stream.name(),
                        "type": stream_type,
                        "channels": stream.channel_count(),
                        "sample_rate": stream.nominal_srate(),
                        "source_id": stream.source_id(),
                        "info": stream,
                    }
                )

            return result

        except Exception as e:
            self.status_message.emit(
                f"Error discovering LSL streams: {str(e)}", "error"
            )
            return {}

    def connect_to_streams(
        self,
        eeg_source_id=None,
        input_source_id=None,
        marker_source_id=None,
        timeout=5.0,
    ):
        """
        Connect to specific LSL streams by source ID or find by type.

        Args:
            eeg_source_id: Source ID of the EEG stream (or None to find first EEG)
            input_source_id: Source ID of the input stream (or None to find first Input)
            marker_source_id: Source ID of the marker stream (or None to find first Markers)
            timeout: Timeout for finding streams (seconds)

        Returns:
            bool: True if connected to both required streams
        """
        if not self.lsl_available:
            return False

        try:
            # Close existing inlets first
            self._close_inlets()

            # Connect to EEG stream
            if eeg_source_id:
                streams = pylsl.resolve_byprop(
                    "source_id", eeg_source_id, timeout=timeout
                )
            else:
                streams = pylsl.resolve_byprop("type", STREAM_TYPE_EEG, timeout=timeout)

            if streams:
                self.eeg_inlet = pylsl.StreamInlet(streams[0])
                self.status_message.emit(
                    f"Connected to EEG stream: {streams[0].name()}", "success"
                )
            else:
                self.status_message.emit("No EEG stream found", "warning")

            # Connect to input stream
            if input_source_id:
                streams = pylsl.resolve_byprop(
                    "source_id", input_source_id, timeout=timeout
                )
            else:
                streams = pylsl.resolve_byprop(
                    "type", STREAM_TYPE_INPUT, timeout=timeout
                )

            if streams:
                self.input_inlet = pylsl.StreamInlet(streams[0])
                self.status_message.emit(
                    f"Connected to input stream: {streams[0].name()}", "success"
                )
            else:
                self.status_message.emit("No input stream found", "warning")

            # Connect to marker stream
            if marker_source_id:
                streams = pylsl.resolve_byprop(
                    "source_id", marker_source_id, timeout=timeout
                )
            else:
                streams = pylsl.resolve_byprop(
                    "type", STREAM_TYPE_MARKERS, timeout=timeout
                )

            if streams:
                self.marker_inlet = pylsl.StreamInlet(streams[0])
                self.status_message.emit(
                    f"Connected to marker stream: {streams[0].name()}", "success"
                )
            else:
                self.status_message.emit("No marker stream found", "warning")

            # Check if we're connected to the required streams
            return self.eeg_inlet is not None and self.input_inlet is not None

        except Exception as e:
            self.status_message.emit(
                f"Error connecting to LSL streams: {str(e)}", "error"
            )
            return False

    def _close_inlets(self):
        """Close any open LSL inlets."""
        if self.eeg_inlet:
            self.eeg_inlet.close_stream()
            self.eeg_inlet = None

        if self.input_inlet:
            self.input_inlet.close_stream()
            self.input_inlet = None

        if self.marker_inlet:
            self.marker_inlet.close_stream()
            self.marker_inlet = None

    def start_sync(self):
        """
        Start synchronizing and collecting data from LSL streams.

        Returns:
            bool: True if started successfully
        """
        if not self.lsl_available:
            return False

        if not (self.eeg_inlet and self.input_inlet):
            self.status_message.emit(
                "Cannot start synchronization: Not connected to streams", "error"
            )
            return False

        if self.running:
            self.status_message.emit("Synchronization already running", "warning")
            return True

        try:
            # Start the data pulling thread
            self.running = True
            self.pull_thread = threading.Thread(
                target=self._pull_data_thread, daemon=True
            )
            self.pull_thread.start()

            self.status_message.emit("LSL synchronization started", "success")
            return True

        except Exception as e:
            self.status_message.emit(
                f"Error starting synchronization: {str(e)}", "error"
            )
            self.running = False
            return False

    def stop_sync(self):
        """
        Stop synchronizing data.

        Returns:
            bool: True if stopped successfully
        """
        if not self.running:
            return True

        try:
            # Stop the thread
            self.running = False
            if self.pull_thread:
                self.pull_thread.join(timeout=2.0)  # Wait for thread to terminate
                self.pull_thread = None

            self.status_message.emit("LSL synchronization stopped", "success")
            return True

        except Exception as e:
            self.status_message.emit(
                f"Error stopping synchronization: {str(e)}", "error"
            )
            return False

    def _pull_data_thread(self):
        """Thread function for pulling data from LSL streams."""
        while self.running:
            try:
                # Pull EEG samples with a timeout
                eeg_samples, eeg_timestamps = self.eeg_inlet.pull_chunk(
                    timeout=0.1, max_samples=100
                )

                # Pull input samples with a timeout
                input_samples, input_timestamps = self.input_inlet.pull_chunk(
                    timeout=0.1, max_samples=100
                )

                # Pull marker samples with a timeout
                marker_samples = []
                marker_timestamps = []
                if self.marker_inlet:
                    markers, marker_ts = self.marker_inlet.pull_chunk(
                        timeout=0.1, max_samples=10
                    )
                    for m, ts in zip(markers, marker_ts):
                        marker_samples.append(int(m[0]))
                        marker_timestamps.append(ts)

                # Process new samples
                if eeg_samples or input_samples or marker_samples:
                    self._process_new_samples(
                        eeg_samples,
                        eeg_timestamps,
                        input_samples,
                        input_timestamps,
                        marker_samples,
                        marker_timestamps,
                    )

            except Exception as e:
                self.status_message.emit(
                    f"Error in synchronization thread: {str(e)}", "error"
                )
                time.sleep(1.0)  # Prevent tight loop if there's an error

    def _process_new_samples(
        self,
        eeg_samples,
        eeg_timestamps,
        input_samples,
        input_timestamps,
        marker_samples,
        marker_timestamps,
    ):
        """
        Process new samples from all streams.

        Args:
            eeg_samples: List of EEG sample arrays
            eeg_timestamps: List of EEG timestamps
            input_samples: List of input sample arrays
            input_timestamps: List of input timestamps
            marker_samples: List of marker values
            marker_timestamps: List of marker timestamps
        """
        # Add EEG samples to buffer
        for sample, ts in zip(eeg_samples, eeg_timestamps):
            self.eeg_buffer.append((sample, ts))

        # Add input samples to buffer
        for sample, ts in zip(input_samples, input_timestamps):
            self.input_buffer.append((sample, ts))

        # Add marker samples to buffer
        for marker, ts in zip(marker_samples, marker_timestamps):
            self.marker_buffer.append((marker, ts))

        # Trim buffers if they exceed max size
        if len(self.eeg_buffer) > self.max_buffer_size:
            self.eeg_buffer = self.eeg_buffer[-self.max_buffer_size :]
        if len(self.input_buffer) > self.max_buffer_size:
            self.input_buffer = self.input_buffer[-self.max_buffer_size :]
        if len(self.marker_buffer) > self.max_buffer_size:
            self.marker_buffer = self.marker_buffer[-self.max_buffer_size :]

        # Calculate and check synchronization delay if both streams have data
        if eeg_samples and input_samples:
            # Get most recent timestamps
            latest_eeg_ts = eeg_timestamps[-1]
            latest_input_ts = input_timestamps[-1]

            # Calculate delay in milliseconds
            delay_ms = abs(latest_eeg_ts - latest_input_ts) * 1000
            self.last_sync_delay = delay_ms

            # Check if delay exceeds tolerance
            if delay_ms > self.sync_tolerance:
                self.sync_tolerance_exceeded.emit(delay_ms)

                # Only emit warning message occasionally to avoid flooding
                if int(time.time()) % 10 == 0:  # Once every 10 seconds
                    self.status_message.emit(
                        f"Synchronization delay ({delay_ms:.2f} ms) exceeds tolerance ({self.sync_tolerance:.2f} ms)",
                        "warning",
                    )

        # If recording, add samples to dataset
        if self.is_recording:
            self._add_samples_to_dataset(
                eeg_samples,
                eeg_timestamps,
                input_samples,
                input_timestamps,
                marker_samples,
                marker_timestamps,
            )

        # Emit signal with latest data for visualization
        self._emit_sync_update()

    def _emit_sync_update(self):
        """Emit signal with latest synchronized data for visualization."""
        if not (self.eeg_buffer and self.input_buffer):
            return

        # Create update data structure with recent data
        update_data = {
            "eeg": self.eeg_buffer[-100:] if self.eeg_buffer else [],
            "input": self.input_buffer[-100:] if self.input_buffer else [],
            "markers": self.marker_buffer[-20:] if self.marker_buffer else [],
        }

        # Emit signal
        self.sync_update.emit(update_data)

    def _find_closest_timestamp(self, timestamp, timestamps_list):
        """
        Find the index of the closest timestamp in a list within tolerance.

        Args:
            timestamp: Target timestamp to find
            timestamps_list: List of timestamps to search in

        Returns:
            int: Index of the closest timestamp, or None if list is empty or no match within tolerance
        """
        if not timestamps_list:
            return None

        # Find the closest timestamp
        closest_idx = 0
        min_diff = abs(timestamp - timestamps_list[0])

        for i, ts in enumerate(timestamps_list):
            diff = abs(timestamp - ts)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i

        # Check if the match is within tolerance (convert tolerance from ms to seconds)
        tolerance_seconds = self.sync_tolerance / 1000.0
        if min_diff > tolerance_seconds:
            # If recording, we still use the closest match but log a warning
            if (
                self.is_recording and int(time.time()) % 10 == 0
            ):  # Limit warning frequency
                self.status_message.emit(
                    f"Timestamp match exceeds tolerance: {min_diff*1000:.2f} ms > {self.sync_tolerance:.2f} ms",
                    "warning",
                )

        return closest_idx

    def set_sync_tolerance(self, tolerance_ms):
        """
        Set synchronization tolerance in milliseconds.

        Args:
            tolerance_ms: Tolerance in milliseconds

        Returns:
            bool: True if set successfully
        """
        if tolerance_ms < 0.1:
            tolerance_ms = 0.1  # Set minimum tolerance to 0.1 ms
        elif tolerance_ms > 1000:
            tolerance_ms = 1000  # Set maximum tolerance to 1000 ms (1 second)

        self.sync_tolerance = tolerance_ms
        self.status_message.emit(
            f"Sync tolerance set to {tolerance_ms:.2f} ms", "success"
        )
        return True

    def get_sync_tolerance(self):
        """
        Get current synchronization tolerance.

        Returns:
            float: Tolerance in milliseconds
        """
        return self.sync_tolerance

    def get_last_sync_delay(self):
        """
        Get the last measured synchronization delay.

        Returns:
            float: Delay in milliseconds
        """
        return self.last_sync_delay

    def start_recording(self):
        """
        Start recording synchronized data.

        Returns:
            bool: True if recording started successfully
        """
        if not self.lsl_available:
            return False

        if not (self.eeg_inlet and self.input_inlet):
            self.status_message.emit(
                "Cannot start recording: Not connected to streams", "error"
            )
            return False

        if self.is_recording:
            self.status_message.emit("Already recording", "warning")
            return True

        # Reset dataset
        self.dataset = {"eeg": [], "input": [], "markers": [], "timestamps": []}

        # Set recording state
        self.is_recording = True
        self.recording_start_time = pylsl.local_clock()

        self.status_message.emit("Dataset recording started", "success")
        return True

    def stop_recording(self):
        """
        Stop recording synchronized data.

        Returns:
            bool: True if recording stopped successfully
        """
        if not self.is_recording:
            return True

        # Set recording state
        self.is_recording = False

        self.status_message.emit(
            f"Dataset recording stopped. {len(self.dataset['timestamps'])} samples collected.",
            "success",
        )
        return True

    def _add_samples_to_dataset(
        self,
        eeg_samples,
        eeg_timestamps,
        input_samples,
        input_timestamps,
        marker_samples,
        marker_timestamps,
    ):
        """
        Add new samples to the synchronized dataset.

        Args:
            eeg_samples: List of EEG sample arrays
            eeg_timestamps: List of EEG timestamps
            input_samples: List of input sample arrays
            input_timestamps: List of input timestamps
            marker_samples: List of marker values
            marker_timestamps: List of marker timestamps
        """
        # Add EEG samples to dataset
        for sample, ts in zip(eeg_samples, eeg_timestamps):
            self.dataset["eeg"].append(sample)
            self.dataset["timestamps"].append(ts)

            # Create a sample dict for the new_dataset_sample signal
            sample_dict = {
                "timestamp": ts,
                "eeg": sample,
                "input": None,
                "marker": None,
            }

            # Emit signal for real-time dataset monitoring
            self.new_dataset_sample.emit(sample_dict)

        # Add input samples to dataset
        for sample, ts in zip(input_samples, input_timestamps):
            # Find closest EEG timestamp
            closest_idx = self._find_closest_timestamp(ts, self.dataset["timestamps"])
            if closest_idx is not None:
                # If we have an input sample without corresponding EEG sample,
                # associate it with the closest EEG sample
                while len(self.dataset["input"]) <= closest_idx:
                    self.dataset["input"].append(None)
                self.dataset["input"][closest_idx] = sample

                # Update the dataset sample
                sample_dict = {
                    "timestamp": ts,
                    "eeg": (
                        self.dataset["eeg"][closest_idx]
                        if closest_idx < len(self.dataset["eeg"])
                        else None
                    ),
                    "input": sample,
                    "marker": None,
                }

                # Emit signal for real-time dataset monitoring
                self.new_dataset_sample.emit(sample_dict)

        # Add marker samples to dataset
        for marker, ts in zip(marker_samples, marker_timestamps):
            # Find closest EEG timestamp
            closest_idx = self._find_closest_timestamp(ts, self.dataset["timestamps"])
            if closest_idx is not None:
                # If we have a marker without corresponding EEG sample,
                # associate it with the closest EEG sample
                while len(self.dataset["markers"]) <= closest_idx:
                    self.dataset["markers"].append(None)
                self.dataset["markers"][closest_idx] = marker

                # Update the dataset sample
                sample_dict = {
                    "timestamp": ts,
                    "eeg": (
                        self.dataset["eeg"][closest_idx]
                        if closest_idx < len(self.dataset["eeg"])
                        else None
                    ),
                    "input": (
                        self.dataset["input"][closest_idx]
                        if closest_idx < len(self.dataset["input"])
                        else None
                    ),
                    "marker": marker,
                }

                # Emit signal for real-time dataset monitoring
                self.new_dataset_sample.emit(sample_dict)

    def _find_closest_timestamp(self, timestamp, timestamps_list):
        """
        Find the index of the closest timestamp in a list within tolerance.

        Args:
            timestamp: Target timestamp to find
            timestamps_list: List of timestamps to search in

        Returns:
            int: Index of the closest timestamp, or None if list is empty or no match within tolerance
        """
        if not timestamps_list:
            return None

        # Find the closest timestamp
        closest_idx = 0
        min_diff = abs(timestamp - timestamps_list[0])

        for i, ts in enumerate(timestamps_list):
            diff = abs(timestamp - ts)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i

        # Check if the match is within tolerance (convert tolerance from ms to seconds)
        tolerance_seconds = self.sync_tolerance / 1000.0
        if min_diff > tolerance_seconds:
            # If recording, we still use the closest match but log a warning
            if (
                self.is_recording and int(time.time()) % 10 == 0
            ):  # Limit warning frequency
                self.status_message.emit(
                    f"Timestamp match exceeds tolerance: {min_diff*1000:.2f} ms > {self.sync_tolerance:.2f} ms",
                    "warning",
                )

        return closest_idx

    def set_sync_tolerance(self, tolerance_ms):
        """
        Set synchronization tolerance in milliseconds.

        Args:
            tolerance_ms: Tolerance in milliseconds

        Returns:
            bool: True if set successfully
        """
        if tolerance_ms < 0.1:
            tolerance_ms = 0.1  # Set minimum tolerance to 0.1 ms
        elif tolerance_ms > 1000:
            tolerance_ms = 1000  # Set maximum tolerance to 1000 ms (1 second)

        self.sync_tolerance = tolerance_ms
        self.status_message.emit(
            f"Sync tolerance set to {tolerance_ms:.2f} ms", "success"
        )
        return True

    def get_sync_tolerance(self):
        """
        Get current synchronization tolerance.

        Returns:
            float: Tolerance in milliseconds
        """
        return self.sync_tolerance

    def get_last_sync_delay(self):
        """
        Get the last measured synchronization delay.

        Returns:
            float: Delay in milliseconds
        """
        return self.last_sync_delay

    def export_dataset(self, format_type, filename):
        """
        Export the synchronized dataset to a file.

        Args:
            format_type: Export format ('csv', 'hdf5', 'edf', 'bids', etc.)
            filename: Base filename to save

        Returns:
            bool: True if export was successful
        """
        if not self.dataset["timestamps"]:
            self.status_message.emit("No data to export", "warning")
            return False

        try:
            if format_type.lower() == "csv":
                self._export_to_csv(filename)
            elif format_type.lower() == "hdf5":
                self._export_to_hdf5(filename)
            elif format_type.lower() == "edf":
                self._export_to_edf(filename)
            elif format_type.lower() == "bids":
                self._export_to_bids(filename)
            else:
                self.status_message.emit(
                    f"Unsupported export format: {format_type}", "error"
                )
                return False

            return True

        except Exception as e:
            self.status_message.emit(f"Error exporting dataset: {str(e)}", "error")
            return False

    def _export_to_csv(self, filename):
        """
        Export dataset to CSV files.

        Args:
            filename: Base filename to save
        """
        import pandas as pd
        import os

        # Create separate CSV files for EEG and input data with common timestamps

        # EEG data
        eeg_data = []
        for i, (sample, ts) in enumerate(
            zip(self.dataset["eeg"], self.dataset["timestamps"])
        ):
            row = {"timestamp": ts}
            for ch_idx, value in enumerate(sample):
                row[f"eeg_ch{ch_idx+1}"] = value

            # Add marker if available
            if (
                i < len(self.dataset["markers"])
                and self.dataset["markers"][i] is not None
            ):
                row["marker"] = self.dataset["markers"][i]
            else:
                row["marker"] = 0

            eeg_data.append(row)

        # Create EEG dataframe and save
        eeg_df = pd.DataFrame(eeg_data)
        eeg_filename = f"{os.path.splitext(filename)[0]}_eeg.csv"
        eeg_df.to_csv(eeg_filename, index=False)

        # Input data
        input_data = []
        for i, ts in enumerate(self.dataset["timestamps"]):
            if i < len(self.dataset["input"]) and self.dataset["input"][i] is not None:
                row = {"timestamp": ts}
                sample = self.dataset["input"][i]
                for ch_idx, value in enumerate(sample):
                    row[f"input_ch{ch_idx+1}"] = value

                # Add marker if available
                if (
                    i < len(self.dataset["markers"])
                    and self.dataset["markers"][i] is not None
                ):
                    row["marker"] = self.dataset["markers"][i]
                else:
                    row["marker"] = 0

                input_data.append(row)

        # Create input dataframe and save
        input_df = pd.DataFrame(input_data)
        input_filename = f"{os.path.splitext(filename)[0]}_input.csv"
        input_df.to_csv(input_filename, index=False)

        # Create merged dataframe with interpolated values
        merged_df = pd.DataFrame({"timestamp": self.dataset["timestamps"]})

        # Add EEG columns
        for ch_idx in range(len(self.dataset["eeg"][0]) if self.dataset["eeg"] else 0):
            merged_df[f"eeg_ch{ch_idx+1}"] = [
                sample[ch_idx] if i < len(self.dataset["eeg"]) else None
                for i, sample in enumerate(self.dataset["eeg"])
            ]

        # Add input columns - handling potentially missing values
        max_input_channels = max(
            [len(sample) for sample in self.dataset["input"] if sample is not None]
            or [0]
        )
        for ch_idx in range(max_input_channels):
            merged_df[f"input_ch{ch_idx+1}"] = [
                (
                    sample[ch_idx]
                    if (
                        i < len(self.dataset["input"])
                        and self.dataset["input"][i] is not None
                        and ch_idx < len(self.dataset["input"][i])
                    )
                    else None
                )
                for i in range(len(self.dataset["timestamps"]))
            ]

        # Add marker column
        merged_df["marker"] = [
            (
                self.dataset["markers"][i]
                if (
                    i < len(self.dataset["markers"])
                    and self.dataset["markers"][i] is not None
                )
                else 0
            )
            for i in range(len(self.dataset["timestamps"]))
        ]

        # Save merged dataframe
        merged_filename = f"{os.path.splitext(filename)[0]}_merged.csv"
        merged_df.to_csv(merged_filename, index=False)

        self.status_message.emit(
            f"Dataset exported to CSV files: {eeg_filename}, {input_filename}, {merged_filename}",
            "success",
        )

    def _export_to_hdf5(self, filename):
        """
        Export dataset to HDF5 format.

        Args:
            filename: Filename to save
        """
        try:
            import h5py
            import numpy as np

            # Ensure the filename ends with .h5
            if not filename.endswith(".h5"):
                filename += ".h5"

            with h5py.File(filename, "w") as f:
                # Create groups
                eeg_group = f.create_group("eeg")
                input_group = f.create_group("input")
                marker_group = f.create_group("markers")

                # Store timestamps
                f.create_dataset(
                    "timestamps",
                    data=np.array(self.dataset["timestamps"], dtype=np.float64),
                )

                # Store EEG data
                eeg_data = np.array(self.dataset["eeg"], dtype=np.float32)
                eeg_group.create_dataset("data", data=eeg_data)

                # Create input data array, handling potential None values
                input_data_list = []
                for i in range(len(self.dataset["timestamps"])):
                    if (
                        i < len(self.dataset["input"])
                        and self.dataset["input"][i] is not None
                    ):
                        input_data_list.append(self.dataset["input"][i])
                    else:
                        # Add zeros for missing samples - adjust size based on available samples
                        sample_size = (
                            len(self.dataset["input"][0])
                            if self.dataset["input"]
                            and self.dataset["input"][0] is not None
                            else 0
                        )
                        input_data_list.append([0.0] * sample_size)

                if input_data_list:
                    input_data = np.array(input_data_list, dtype=np.float32)
                    input_group.create_dataset("data", data=input_data)

                # Create marker data array, handling potential None values
                marker_data_list = []
                for i in range(len(self.dataset["timestamps"])):
                    if (
                        i < len(self.dataset["markers"])
                        and self.dataset["markers"][i] is not None
                    ):
                        marker_data_list.append(self.dataset["markers"][i])
                    else:
                        marker_data_list.append(
                            0
                        )  # Default marker value is 0 (no marker)

                marker_data = np.array(marker_data_list, dtype=np.int32)
                marker_group.create_dataset("data", data=marker_data)

                # Add metadata
                f.attrs["created"] = np.string_(time.strftime("%Y-%m-%d %H:%M:%S"))
                f.attrs["description"] = np.string_("Unified EEG-Input Dataset")

                eeg_group.attrs["sample_rate"] = (
                    250.0  # Add actual value from inlet info
                )
                input_group.attrs["sample_rate"] = (
                    60.0  # Add actual value from inlet info
                )

            self.status_message.emit(
                f"Dataset exported to HDF5 file: {filename}", "success"
            )

        except ImportError:
            self.status_message.emit(
                "HDF5 export requires h5py package. Install with: pip install h5py",
                "error",
            )

    def _export_to_edf(self, filename):
        """
        Export dataset to EDF format.

        Args:
            filename: Filename to save
        """
        try:
            import mne
            import numpy as np

            # Ensure the filename ends with .edf
            if not filename.endswith(".edf"):
                filename += ".edf"

            # Prepare EEG data
            eeg_data = np.array(self.dataset["eeg"], dtype=np.float32)

            # Transpose to get channels x samples as required by MNE
            eeg_data = eeg_data.T

            # Create channel names
            ch_names = [f"EEG{i+1}" for i in range(eeg_data.shape[0])]

            # Create MNE info object
            sfreq = 250.0  # Add actual value from inlet info
            info = mne.create_info(
                ch_names=ch_names, sfreq=sfreq, ch_types=["eeg"] * len(ch_names)
            )

            # Create MNE Raw object
            raw = mne.io.RawArray(eeg_data, info)

            # Add markers as annotations
            onset = []
            duration = []
            description = []

            for i, marker in enumerate(self.dataset["markers"]):
                if marker is not None and marker > 0:
                    # Convert from timestamps to seconds from start
                    time_sec = (
                        self.dataset["timestamps"][i] - self.dataset["timestamps"][0]
                    )
                    onset.append(time_sec)
                    duration.append(0.0)  # Point marker
                    description.append(f"Marker_{marker}")

            if onset:
                annot = mne.Annotations(
                    onset=onset, duration=duration, description=description
                )
                raw.set_annotations(annot)

            # Save as EDF
            raw.export(filename, fmt="edf", overwrite=True)

            self.status_message.emit(
                f"Dataset exported to EDF file: {filename}", "success"
            )

        except ImportError:
            self.status_message.emit(
                "EDF export requires MNE package. Install with: pip install mne",
                "error",
            )

    def _export_to_bids(self, filename):
        """
        Export dataset to BIDS format.

        Args:
            filename: Base directory to save BIDS dataset
        """
        try:
            import mne
            import mne_bids
            import numpy as np
            import os
            from datetime import datetime

            # Create BIDS directory structure
            bids_root = filename
            os.makedirs(bids_root, exist_ok=True)

            # Prepare EEG data
            eeg_data = np.array(self.dataset["eeg"], dtype=np.float32)

            # Transpose to get channels x samples as required by MNE
            eeg_data = eeg_data.T

            # Create channel names
            ch_names = [f"EEG{i+1}" for i in range(eeg_data.shape[0])]

            # Create MNE info object
            sfreq = 250.0  # Add actual value from inlet info
            info = mne.create_info(
                ch_names=ch_names, sfreq=sfreq, ch_types=["eeg"] * len(ch_names)
            )

            # Create MNE Raw object
            raw = mne.io.RawArray(eeg_data, info)

            # Add markers as annotations
            onset = []
            duration = []
            description = []

            for i, marker in enumerate(self.dataset["markers"]):
                if marker is not None and marker > 0:
                    # Convert from timestamps to seconds from start
                    time_sec = (
                        self.dataset["timestamps"][i] - self.dataset["timestamps"][0]
                    )
                    onset.append(time_sec)
                    duration.append(0.0)  # Point marker
                    description.append(f"Marker_{marker}")

            if onset:
                annot = mne.Annotations(
                    onset=onset, duration=duration, description=description
                )
                raw.set_annotations(annot)

            # Create BIDS compatible dataset
            subject_id = "001"  # Example subject ID
            task = "bci"
            session_id = "01"
            run = "01"

            # Generate a montage
            montage = mne.channels.make_standard_montage("standard_1020")
            raw.set_montage(montage)

            # Save to BIDS format
            bids_path = mne_bids.BIDSPath(
                subject=subject_id,
                session=session_id,
                task=task,
                run=run,
                root=bids_root,
            )

            # Write the BIDS dataset
            mne_bids.write_raw_bids(raw, bids_path, overwrite=True)

            # Add unified input data as a separate file
            input_data_list = []
            for i in range(len(self.dataset["timestamps"])):
                if (
                    i < len(self.dataset["input"])
                    and self.dataset["input"][i] is not None
                ):
                    row = {"timestamp": self.dataset["timestamps"][i]}
                    for ch_idx, value in enumerate(self.dataset["input"][i]):
                        row[f"input_ch{ch_idx+1}"] = value
                    input_data_list.append(row)

            if input_data_list:
                import pandas as pd

                input_df = pd.DataFrame(input_data_list)
                input_filename = os.path.join(
                    bids_root,
                    f"sub-{subject_id}",
                    f"ses-{session_id}",
                    "eeg",
                    f"sub-{subject_id}_ses-{session_id}_task-{task}_run-{run}_input.tsv",
                )
                os.makedirs(os.path.dirname(input_filename), exist_ok=True)
                input_df.to_csv(input_filename, sep="\t", index=False)

            self.status_message.emit(
                f"Dataset exported to BIDS format: {bids_root}", "success"
            )

        except ImportError:
            self.status_message.emit(
                "BIDS export requires MNE and MNE-BIDS packages. Install with: pip install mne mne-bids",
                "error",
            )

    def push_eeg_data(self, eeg_data):
        """
        Push EEG data to LSL stream.

        Args:
            eeg_data: Array of EEG samples

        Returns:
            bool: True if data was pushed successfully
        """
        if not self.lsl_available or not self.eeg_outlet:
            return False

        try:
            self.eeg_outlet.push_sample(eeg_data)
            return True
        except Exception as e:
            self.status_message.emit(f"Error pushing EEG data: {str(e)}", "error")
            return False

    def push_input_data(self, input_data):
        """
        Push input data to LSL stream.

        Args:
            input_data: Array of input values

        Returns:
            bool: True if data was pushed successfully
        """
        if not self.lsl_available or not self.input_outlet:
            return False

        try:
            self.input_outlet.push_sample(input_data)
            return True
        except Exception as e:
            self.status_message.emit(f"Error pushing input data: {str(e)}", "error")
            return False

    def push_marker(self, marker_value):
        """
        Push marker to LSL stream.

        Args:
            marker_value: Marker value

        Returns:
            bool: True if marker was pushed successfully
        """
        if not self.lsl_available or not self.marker_outlet:
            return False

        try:
            self.marker_outlet.push_sample([marker_value])
            return True
        except Exception as e:
            self.status_message.emit(f"Error pushing marker: {str(e)}", "error")
            return False

    def get_dataset_preview(self, max_samples=100):
        """
        Get a preview of the dataset for UI display.

        Args:
            max_samples: Maximum number of samples to return

        Returns:
            dict: Dictionary with dataset preview
        """
        # Return a copy of a subset of the dataset
        if not self.dataset["timestamps"]:
            return {
                "eeg": [],
                "input": [],
                "markers": [],
                "timestamps": [],
                "sync_info": {
                    "tolerance": self.sync_tolerance,
                    "delay": self.last_sync_delay,
                },
            }

        # Get indices to return (last max_samples)
        start_idx = max(0, len(self.dataset["timestamps"]) - max_samples)

        return {
            "eeg": self.dataset["eeg"][start_idx:] if self.dataset["eeg"] else [],
            "input": self.dataset["input"][start_idx:] if self.dataset["input"] else [],
            "markers": (
                self.dataset["markers"][start_idx:] if self.dataset["markers"] else []
            ),
            "timestamps": (
                self.dataset["timestamps"][start_idx:]
                if self.dataset["timestamps"]
                else []
            ),
            "sync_info": {
                "tolerance": self.sync_tolerance,
                "delay": self.last_sync_delay,
            },
        }

    def cleanup(self):
        """Clean up resources."""
        self.stop_sync()
        self._close_inlets()

        # Close outlets
        self.eeg_outlet = None
        self.input_outlet = None
        self.marker_outlet = None
