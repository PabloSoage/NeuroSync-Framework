"""
LSL Synchronizer module for Brain-Computer Interface systems.

This module provides classes and functions to synchronize EEG and input data streams
using Lab Streaming Layer (LSL) with millisecond precision. It supports:
1. Creation of LSL outlets for publishing EEG and input data
2. Creation of LSL inlets for receiving synchronized data
3. Visualization of synchronized data streams
4. Export of synchronized data to standard formats (HDF5, EDF+, BIDS)
"""

import logging
import queue
import threading
import time
from typing import Dict, List, Optional, Union

import h5py
import numpy as np
from PyQt5.QtCore import QTimer, pyqtSignal, Qt

# For visualization
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
)

# Fixed import - remove LostError which doesn't exist in pylsl
from pylsl import StreamInfo, StreamOutlet, StreamInlet, resolve_streams, local_clock


class LSLStreamPublisher:
    """
    Handles publishing data to LSL streams.

    This class creates LSL outlets for sending data from either EEG or input collectors
    to the LSL network for synchronization with other data streams.
    """

    def __init__(
        self,
        stream_name: str,
        stream_type: str,
        channel_count: int,
        sampling_rate: float,
        channel_format: str = "float32",
        source_id: str = None,
    ):
        """
        Initialize an LSL stream publisher.

        Args:
            stream_name: Name of the stream (e.g., 'EEG' or 'InputEvents')
            stream_type: Type of the stream (e.g., 'EEG' or 'Markers')
            channel_count: Number of channels in the stream
            sampling_rate: Data sampling rate (use 0 for irregular sampling rate)
            channel_format: Format of the channel data ('float32', 'int16', etc.)
            source_id: Unique identifier for the stream source
        """
        self.stream_name = stream_name
        self.stream_type = stream_type

        # Create stream info
        self.info = StreamInfo(
            name=stream_name,
            type=stream_type,
            channel_count=channel_count,
            nominal_srate=sampling_rate,
            channel_format=channel_format,
            source_id=source_id,
        )

        # Add metadata to the stream
        desc = self.info.desc()
        desc.append_child_value("manufacturer", "BCI System TFG")

        # Add channel info for EEG streams
        if stream_type == "EEG":
            channels = desc.append_child("channels")
            for i in range(channel_count):
                ch = channels.append_child("channel")
                ch.append_child_value("label", f"CH{i+1}")
                ch.append_child_value("unit", "microvolts")
                ch.append_child_value("type", "EEG")

        # Create outlet
        self.outlet = StreamOutlet(self.info)
        logging.info(
            f"Created LSL stream: {stream_name} ({stream_type}) with {channel_count} channels"
        )

    def send_data(
        self, data: Union[List[float], np.ndarray], timestamp: Optional[float] = None
    ) -> None:
        """
        Send data to the LSL stream.

        Args:
            data: Data samples to send (list or NumPy array)
            timestamp: Optional timestamp (if None, current time will be used)
        """
        try:
            self.outlet.push_sample(data, timestamp)
        except Exception as e:
            logging.error(f"Error sending data to LSL stream {self.stream_name}: {e}")

    def send_chunk(
        self, data: np.ndarray, timestamps: Optional[List[float]] = None
    ) -> None:
        """
        Send a chunk of data to the LSL stream.

        Args:
            data: 2D array of data samples (samples × channels)
            timestamps: Optional list of timestamps for each sample
        """
        try:
            self.outlet.push_chunk(data, timestamps)
        except Exception as e:
            logging.error(f"Error sending chunk to LSL stream {self.stream_name}: {e}")


class LSLInputPublisher:
    """
    Specialized LSL publisher for input events (keyboard, mouse, controllers).

    This class handles the specifics of publishing input events to LSL.
    """

    def __init__(self):
        """Initialize the input event publisher."""
        # Create a stream for input events
        # Channel format is string for event markers
        self.publisher = LSLStreamPublisher(
            stream_name="InputEvents",
            stream_type="Markers",
            channel_count=3,  # [event_type, key/button, state]
            sampling_rate=0,  # Irregular sampling rate
            channel_format="string",
        )

        # Add metadata for input events
        desc = self.publisher.info.desc()
        desc.append_child_value("event_types", "keyboard,mouse,controller")

        logging.info("LSL Input Publisher initialized")

    def send_keyboard_event(self, key: str, pressed: bool) -> None:
        """
        Send a keyboard event to the LSL stream.

        Args:
            key: The key that was pressed/released
            pressed: True if pressed, False if released
        """
        event_data = ["keyboard", key, "1" if pressed else "0"]
        self.publisher.send_data(event_data)

    def send_mouse_event(
        self,
        button: str = None,
        pressed: bool = None,
        x: float = None,
        y: float = None,
        scroll_x: float = None,
        scroll_y: float = None,
    ) -> None:
        """
        Send a mouse event to the LSL stream.

        Args:
            button: Mouse button name (e.g., 'left', 'right', 'middle')
            pressed: True if pressed, False if released
            x: X coordinate of the mouse
            y: Y coordinate of the mouse
            scroll_x: Horizontal scroll value
            scroll_y: Vertical scroll value
        """
        if button is not None and pressed is not None:
            # Button press/release event
            event_data = ["mouse_button", button, "1" if pressed else "0"]
        elif x is not None and y is not None:
            # Mouse movement event
            event_data = ["mouse_move", f"{x},{y}", ""]
        elif scroll_x is not None or scroll_y is not None:
            # Mouse scroll event
            sx = scroll_x if scroll_x is not None else 0
            sy = scroll_y if scroll_y is not None else 0
            event_data = ["mouse_scroll", f"{sx},{sy}", ""]
        else:
            return

        self.publisher.send_data(event_data)

    def send_controller_event(
        self, controller_type: str, button: str, value: Union[bool, float]
    ) -> None:
        """
        Send a controller event to the LSL stream.

        Args:
            controller_type: Type of controller (e.g., 'ps4')
            button: Button or axis name
            value: Button state (boolean) or axis value (float)
        """
        # Convert value to string
        if isinstance(value, bool):
            value_str = "1" if value else "0"
        else:
            value_str = str(value)

        event_data = [f"controller_{controller_type}", button, value_str]
        self.publisher.send_data(event_data)


class LSLEEGPublisher:
    """
    Specialized LSL publisher for EEG data.

    This class handles the specifics of publishing EEG data to LSL.
    """

    def __init__(
        self,
        device_name: str,
        channel_count: int,
        sampling_rate: float,
        channel_names: Optional[List[str]] = None,
    ):
        """
        Initialize the EEG data publisher.

        Args:
            device_name: Name of the EEG device
            channel_count: Number of EEG channels
            sampling_rate: EEG sampling rate in Hz
            channel_names: Optional list of channel names
        """
        self.device_name = device_name
        self.publisher = LSLStreamPublisher(
            stream_name=f"EEG-{device_name}",
            stream_type="EEG",
            channel_count=channel_count,
            sampling_rate=sampling_rate,
        )

        # Add metadata for EEG streams
        desc = self.publisher.info.desc()
        desc.append_child_value("device", device_name)

        # Add channel names if provided
        if channel_names:
            channels = desc.child("channels")
            if channels and len(channel_names) == channel_count:
                for i, name in enumerate(channel_names):
                    if i < channel_count:
                        ch = channels.child(f"channel[{i}]")
                        if ch:
                            ch.set_child_value("label", name)

        logging.info(
            f"LSL EEG Publisher initialized for {device_name} with {channel_count} channels"
        )

    def send_eeg_data(
        self, data: np.ndarray, timestamp: Optional[float] = None
    ) -> None:
        """
        Send EEG data samples to the LSL stream.

        Args:
            data: EEG data array (channels)
            timestamp: Optional timestamp (if None, current time will be used)
        """
        self.publisher.send_data(data, timestamp)

    def send_eeg_chunk(
        self, data: np.ndarray, timestamps: Optional[List[float]] = None
    ) -> None:
        """
        Send a chunk of EEG data to the LSL stream.

        Args:
            data: 2D array of EEG data (samples × channels)
            timestamps: Optional list of timestamps for each sample
        """
        self.publisher.send_chunk(data, timestamps)


class LSLMarkerPublisher:
    """
    Specialized LSL publisher for experiment markers and annotations.

    This class handles the specifics of publishing marker data to LSL.
    """

    def __init__(self):
        """Initialize the marker publisher."""
        self.publisher = LSLStreamPublisher(
            stream_name="ExperimentMarkers",
            stream_type="Markers",
            channel_count=2,  # [marker_type, marker_value]
            sampling_rate=0,  # Irregular sampling rate
            channel_format="string",
        )

        logging.info("LSL Marker Publisher initialized")

    def send_marker(self, marker_type: str, marker_value: str) -> None:
        """
        Send a marker to the LSL stream.

        Args:
            marker_type: Type of the marker (e.g., 'trial_start', 'stimulus')
            marker_value: Value associated with the marker
        """
        self.publisher.send_data([marker_type, marker_value])


class LSLDataReceiver:
    """
    Receives and synchronizes data from multiple LSL streams.

    This class handles the reception of data from LSL streams and
    provides methods to access the synchronized data.
    """

    def __init__(
        self, stream_types: Optional[List[str]] = None, resolve_timeout: float = 10.0
    ):
        """
        Initialize the LSL data receiver.

        Args:
            stream_types: Types of streams to receive (e.g., ['EEG', 'Markers'])
                        If None, all available streams will be used
            resolve_timeout: Timeout for resolving streams in seconds
        """
        self.stream_types = stream_types
        self.inlets = []
        self.stream_names = []
        self.stream_info = []
        self.resolve_timeout = resolve_timeout

        self.running = False
        self.buffer = {}  # Buffer for synchronized data

        # Thread for continuous data collection
        self.collection_thread = None
        self.data_queue = queue.Queue()

    def resolve_streams(self) -> bool:
        """
        Resolve available LSL streams based on the specified types.

        Returns:
            True if streams were found, False otherwise
        """
        try:
            # Clear existing inlets
            self.inlets = []
            self.stream_names = []
            self.stream_info = []

            # Resolve streams - Fixed API usage
            # Note: Different versions of pylsl have different APIs
            # In newer versions, resolve_streams() doesn't take a timeout parameter directly
            if self.stream_types:
                all_streams = []
                for stream_type in self.stream_types:
                    try:
                        # Try the current API style (no timeout in resolve_streams)
                        streams = resolve_streams(f"type='{stream_type}'")
                        # If we get here, this API worked, now wait for streams with timeout
                        import time

                        start_time = time.time()
                        while (
                            not streams
                            and time.time() - start_time < self.resolve_timeout
                        ):
                            streams = resolve_streams(f"type='{stream_type}'")
                            time.sleep(0.1)
                        all_streams.extend(streams)
                    except TypeError:
                        # Fall back to older API which might take a timeout parameter
                        try:
                            # This is for backward compatibility with older pylsl versions
                            streams = resolve_streams(
                                f"type='{stream_type}'", timeout=self.resolve_timeout
                            )
                            all_streams.extend(streams)
                        except Exception as e:
                            logging.error(
                                f"Error resolving streams for type {stream_type}: {e}"
                            )
            else:
                try:
                    # Try the current API style (no timeout in resolve_streams)
                    all_streams = resolve_streams()
                    # Wait for streams with timeout
                    import time

                    start_time = time.time()
                    while (
                        not all_streams
                        and time.time() - start_time < self.resolve_timeout
                    ):
                        all_streams = resolve_streams()
                        time.sleep(0.1)
                except TypeError:
                    # Fall back to older API which might take a timeout parameter
                    try:
                        all_streams = resolve_streams(timeout=self.resolve_timeout)
                    except Exception as e:
                        logging.error(f"Error resolving streams: {e}")
                        all_streams = []

            if not all_streams:
                logging.warning("No LSL streams found")
                return False

            # Create inlets for each stream
            for info in all_streams:
                try:
                    inlet = StreamInlet(info)
                    self.inlets.append(inlet)
                    self.stream_names.append(info.name())
                    self.stream_info.append(info)
                    logging.info(
                        f"Connected to LSL stream: {info.name()} ({info.type()})"
                    )
                except Exception as e:
                    logging.error(f"Error creating inlet for {info.name()}: {e}")

            return len(self.inlets) > 0

        except Exception as e:
            logging.error(f"Error resolving LSL streams: {e}")
            return False

    def start_collection(self, buffer_duration: float = 10.0) -> bool:
        """
        Start continuous data collection from all inlets.

        Args:
            buffer_duration: Duration of data to keep in buffer (seconds)

        Returns:
            True if collection started successfully, False otherwise
        """
        if not self.inlets:
            if not self.resolve_streams():
                return False

        if self.running:
            logging.warning("Data collection is already running")
            return True

        # Initialize buffer for each stream
        self.buffer = {
            name: {"timestamps": [], "data": []} for name in self.stream_names
        }
        self.buffer_duration = buffer_duration

        # Start collection thread
        self.running = True
        self.collection_thread = threading.Thread(target=self._collection_thread_func)
        self.collection_thread.daemon = True
        self.collection_thread.start()

        logging.info("LSL data collection started")
        return True

    def stop_collection(self) -> None:
        """Stop continuous data collection."""
        if self.running:
            self.running = False
            if self.collection_thread:
                self.collection_thread.join(timeout=2.0)
            logging.info("LSL data collection stopped")

    def _collection_thread_func(self) -> None:
        """Thread function for continuous data collection from all inlets."""
        try:
            while self.running:
                # Check for samples from each inlet
                for i, inlet in enumerate(self.inlets):
                    name = self.stream_names[i]

                    try:
                        # Get any new samples
                        result = inlet.pull_sample(timeout=0.0)
                        if result[0] is not None:
                            sample, timestamp = result

                            # Add to buffer
                            self.buffer[name]["timestamps"].append(timestamp)
                            self.buffer[name]["data"].append(sample)

                            # Add to queue for real-time processing
                            self.data_queue.put((name, sample, timestamp))

                    except Exception as e:
                        # Handle connection errors - note we don't use LostError which doesn't exist
                        # Instead check the error message to identify connection problems
                        error_str = str(e).lower()
                        if (
                            "lost" in error_str
                            or "disconnect" in error_str
                            or "closed" in error_str
                        ):
                            logging.warning(f"Lost connection to stream: {name}")
                        else:
                            logging.error(f"Error reading from stream {name}: {e}")
                        continue

                # Trim buffers to keep only recent data
                current_time = local_clock()
                for name in self.stream_names:
                    timestamps = self.buffer[name]["timestamps"]
                    if timestamps:
                        # Find index of oldest timestamp to keep
                        cutoff_time = current_time - self.buffer_duration
                        cutoff_idx = 0
                        for i, ts in enumerate(timestamps):
                            if ts >= cutoff_time:
                                cutoff_idx = i
                                break

                        # Trim buffer if needed
                        if cutoff_idx > 0:
                            self.buffer[name]["timestamps"] = timestamps[cutoff_idx:]
                            self.buffer[name]["data"] = self.buffer[name]["data"][
                                cutoff_idx:
                            ]

                # Sleep briefly to avoid high CPU usage
                time.sleep(0.001)

        except Exception as e:
            logging.error(f"Error in LSL collection thread: {e}")
            self.running = False

    def get_latest_data(self, stream_name: Optional[str] = None) -> Dict:
        """
        Get the latest data from the buffer.

        Args:
            stream_name: Name of the stream to get data from, or None for all streams

        Returns:
            Dictionary with stream data and timestamps
        """
        if not self.buffer:
            return {}

        if stream_name:
            if stream_name in self.buffer:
                return {
                    "timestamps": self.buffer[stream_name]["timestamps"],
                    "data": self.buffer[stream_name]["data"],
                }
            else:
                return {}
        else:
            return self.buffer

    def get_synchronized_data(self, sync_window: float = 0.01) -> Dict:
        """
        Get synchronized data from all streams.

        This method aligns data from different streams based on their timestamps,
        grouping samples that occurred within the sync_window of each other.

        Args:
            sync_window: Time window (in seconds) to consider samples synchronized

        Returns:
            Dictionary with synchronized data points
        """
        if not self.buffer or not self.stream_names:
            return {}

        # Find the stream with the most regular sampling rate (likely EEG)
        reference_stream = self.stream_names[0]
        for name in self.stream_names:
            if "EEG" in name or "eeg" in name.lower():
                reference_stream = name
                break

        if not self.buffer[reference_stream]["timestamps"]:
            return {}

        # Create synchronized data structure
        sync_data = {
            "reference_stream": reference_stream,
            "reference_timestamps": self.buffer[reference_stream]["timestamps"],
            "reference_data": self.buffer[reference_stream]["data"],
            "synchronized_events": [],
        }

        # For each timestamp in the reference stream, find synchronized events
        for i, ref_time in enumerate(sync_data["reference_timestamps"]):
            events = []

            # Look for events in other streams within the sync window
            for name in self.stream_names:
                if name == reference_stream:
                    continue

                timestamps = self.buffer[name]["timestamps"]
                data = self.buffer[name]["data"]

                # Find all events within the sync window
                for j, ts in enumerate(timestamps):
                    if abs(ts - ref_time) <= sync_window:
                        events.append(
                            {
                                "stream": name,
                                "timestamp": ts,
                                "time_diff": ts - ref_time,
                                "data": data[j],
                            }
                        )

            # Only add to synchronized events if there are any matching events
            if events:
                sync_data["synchronized_events"].append(
                    {"reference_idx": i, "reference_time": ref_time, "events": events}
                )

        return sync_data


class DatasetExporter:
    """
    Exports synchronized data to standard dataset formats.

    This class provides methods to export synchronized EEG and input data
    to various standard formats like HDF5, EDF+, and BIDS.
    """

    def __init__(self, receiver: LSLDataReceiver):
        """
        Initialize the dataset exporter.

        Args:
            receiver: LSL data receiver with synchronized data
        """
        self.receiver = receiver
        logging.info("Dataset Exporter initialized")

    def export_to_hdf5(self, filename: str, metadata: Optional[Dict] = None) -> bool:
        """
        Export synchronized data to HDF5 format.

        Args:
            filename: Output filename
            metadata: Optional metadata to include in the file

        Returns:
            True if export was successful, False otherwise
        """
        try:
            # Get synchronized data
            sync_data = self.receiver.get_synchronized_data()
            if not sync_data:
                logging.error("No synchronized data available for export")
                return False

            # Create HDF5 file
            with h5py.File(filename, "w") as f:
                # Add metadata
                if metadata:
                    metadata_group = f.create_group("metadata")
                    for key, value in metadata.items():
                        metadata_group.attrs[key] = value

                # Add reference stream data
                ref_stream = sync_data["reference_stream"]
                ref_group = f.create_group(f"streams/{ref_stream}")
                ref_group.create_dataset(
                    "timestamps", data=sync_data["reference_timestamps"]
                )
                ref_group.create_dataset("data", data=sync_data["reference_data"])

                # Add synchronized events
                events_group = f.create_group("synchronized_events")
                for i, event_group in enumerate(sync_data["synchronized_events"]):
                    eg = events_group.create_group(f"event_{i}")
                    eg.attrs["reference_idx"] = event_group["reference_idx"]
                    eg.attrs["reference_time"] = event_group["reference_time"]

                    for j, evt in enumerate(event_group["events"]):
                        e = eg.create_group(f"related_event_{j}")
                        e.attrs["stream"] = evt["stream"]
                        e.attrs["timestamp"] = evt["timestamp"]
                        e.attrs["time_diff"] = evt["time_diff"]
                        e.create_dataset("data", data=evt["data"])

                # Add raw stream data (all streams)
                raw_data = self.receiver.get_latest_data()
                for name, data in raw_data.items():
                    stream_group = f.create_group(f"raw_streams/{name}")
                    stream_group.create_dataset("timestamps", data=data["timestamps"])
                    stream_group.create_dataset("data", data=data["data"])

            logging.info(f"Exported synchronized data to HDF5: {filename}")
            return True

        except Exception as e:
            logging.error(f"Error exporting to HDF5: {e}")
            return False

    def export_to_edf(self, filename: str) -> bool:
        """
        Export EEG data to EDF+ format.

        Args:
            filename: Output filename

        Returns:
            True if export was successful, False otherwise
        """
        try:
            # Check if MNE is available for EDF export
            try:
                import mne
            except ImportError:
                logging.error("MNE package is required for EDF export")
                return False

            # Get data
            sync_data = self.receiver.get_latest_data()
            if not sync_data:
                logging.error("No data available for export")
                return False

            # Find EEG stream
            eeg_stream = None
            for name in sync_data.keys():
                if "EEG" in name or "eeg" in name.lower():
                    eeg_stream = name
                    break

            if not eeg_stream:
                logging.error("No EEG stream found for EDF export")
                return False

            # Get EEG data and timestamps
            eeg_data = np.array(sync_data[eeg_stream]["data"])
            timestamps = np.array(sync_data[eeg_stream]["timestamps"])

            if len(eeg_data) == 0:
                logging.error("No EEG data available for export")
                return False

            # Calculate sampling frequency
            if len(timestamps) > 1:
                sfreq = 1.0 / np.mean(np.diff(timestamps))
            else:
                # Default to 250 Hz if can't calculate
                sfreq = 250

            # Transpose data to be in the format expected by MNE (channels × samples)
            eeg_data = eeg_data.T

            # Create channel names
            n_channels = eeg_data.shape[0]
            ch_names = [f"EEG{i+1}" for i in range(n_channels)]

            # Create MNE info object
            info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types="eeg")

            # Create raw object and save to EDF
            raw = mne.io.RawArray(eeg_data, info)
            raw.save(filename, overwrite=True)

            logging.info(f"Exported EEG data to EDF: {filename}")
            return True

        except Exception as e:
            logging.error(f"Error exporting to EDF: {e}")
            return False

    def export_to_csv(self, eeg_filename: str, events_filename: str) -> bool:
        """
        Export synchronized data to CSV files.

        Args:
            eeg_filename: Filename for EEG data
            events_filename: Filename for event data

        Returns:
            True if export was successful, False otherwise
        """
        try:
            import pandas as pd

            # Get synchronized data
            sync_data = self.receiver.get_latest_data()
            if not sync_data:
                logging.error("No data available for export")
                return False

            # Find EEG stream
            eeg_stream = None
            for name in sync_data.keys():
                if "EEG" in name or "eeg" in name.lower():
                    eeg_stream = name
                    break

            if eeg_stream:
                # Export EEG data
                eeg_data = np.array(sync_data[eeg_stream]["data"])
                eeg_timestamps = np.array(sync_data[eeg_stream]["timestamps"])

                if len(eeg_data) > 0:
                    # Create EEG dataframe
                    n_channels = len(eeg_data[0])
                    columns = ["timestamp"] + [f"ch{i+1}" for i in range(n_channels)]

                    eeg_df = pd.DataFrame(columns=columns)
                    eeg_df["timestamp"] = eeg_timestamps

                    for i in range(n_channels):
                        eeg_df[f"ch{i+1}"] = [d[i] for d in eeg_data]

                    # Save to CSV
                    eeg_df.to_csv(eeg_filename, index=False)
                    logging.info(f"Exported EEG data to CSV: {eeg_filename}")

            # Export event data from all non-EEG streams
            event_streams = [name for name in sync_data.keys() if name != eeg_stream]

            if event_streams:
                # Combine all events
                events = []
                for stream in event_streams:
                    stream_data = sync_data[stream]
                    for i, timestamp in enumerate(stream_data["timestamps"]):
                        data = stream_data["data"][i]
                        events.append(
                            {
                                "timestamp": timestamp,
                                "stream": stream,
                                "data": str(data),
                            }
                        )

                # Sort by timestamp
                events.sort(key=lambda x: x["timestamp"])

                # Create events dataframe
                events_df = pd.DataFrame(events)

                # Save to CSV
                events_df.to_csv(events_filename, index=False)
                logging.info(f"Exported events data to CSV: {events_filename}")

            return True

        except Exception as e:
            logging.error(f"Error exporting to CSV: {e}")
            return False


class LSLSynchronizerWidget(QWidget):
    """
    Widget for controlling and visualizing LSL synchronization.

    This class provides a user interface for starting/stopping LSL synchronization,
    visualizing synchronized data, and exporting datasets.
    """

    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        """Initialize the LSL synchronizer widget."""
        super().__init__(parent)

        # LSL components
        self.eeg_publisher = None
        self.input_publisher = None
        self.marker_publisher = None
        self.receiver = LSLDataReceiver()
        self.exporter = DatasetExporter(self.receiver)

        # Stream status tracking
        self.stream_status = {}  # To track the status of each stream
        self.stream_status_widgets = {}  # To hold the status label widgets

        # UI setup
        self.setup_ui()

        # Timer for updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(500)  # Update every 500 ms

        logging.info("LSL Synchronizer Widget initialized")

    def setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("LSL Data Synchronization")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        main_layout.addWidget(title_label)

        # Status section
        status_group = QWidget()
        status_layout = QHBoxLayout(status_group)

        status_layout.addWidget(QLabel("Status:"))
        self.status_label = QLabel("Not Active")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch(1)

        self.streams_label = QLabel("Available Streams: 0")
        status_layout.addWidget(self.streams_label)

        main_layout.addWidget(status_group)

        # Stream status section
        self.stream_status_container = QWidget()
        self.stream_status_layout = QVBoxLayout(self.stream_status_container)
        self.stream_status_layout.setContentsMargins(0, 0, 0, 0)
        self.stream_status_layout.setSpacing(2)

        self.stream_status_label = QLabel("Stream Status:")
        self.stream_status_label.setStyleSheet("font-weight: bold;")
        self.stream_status_layout.addWidget(self.stream_status_label)

        # Add empty status section - will be populated dynamically
        main_layout.addWidget(self.stream_status_container)

        # Control buttons
        button_layout = QHBoxLayout()

        self.start_sync_btn = QPushButton("Start Synchronization")
        self.start_sync_btn.clicked.connect(self.start_synchronization)
        button_layout.addWidget(self.start_sync_btn)

        self.stop_sync_btn = QPushButton("Stop Synchronization")
        self.stop_sync_btn.clicked.connect(self.stop_synchronization)
        self.stop_sync_btn.setEnabled(False)
        button_layout.addWidget(self.stop_sync_btn)

        self.refresh_btn = QPushButton("Refresh Streams")
        self.refresh_btn.clicked.connect(self.refresh_streams)
        button_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(button_layout)

        # Export section
        export_group = QWidget()
        export_layout = QHBoxLayout(export_group)

        export_layout.addWidget(QLabel("Export Format:"))

        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["HDF5", "EDF+", "CSV", "BIDS"])
        export_layout.addWidget(self.export_format_combo)

        self.export_btn = QPushButton("Export Dataset")
        self.export_btn.clicked.connect(self.export_dataset)
        self.export_btn.setEnabled(False)
        export_layout.addWidget(self.export_btn)

        main_layout.addWidget(export_group)

        # Add visualization placeholder
        viz_label = QLabel("Synchronization Visualization")
        viz_label.setAlignment(Qt.AlignCenter)
        viz_label.setStyleSheet("background-color: #252526; padding: 20px;")
        main_layout.addWidget(viz_label, 1)

        # Status message at bottom
        self.message_label = QLabel("")
        main_layout.addWidget(self.message_label)

    def start_synchronization(self):
        """Start LSL synchronization."""
        try:
            # Start the receiver if not already running
            if not self.receiver.running:
                success = self.receiver.start_collection()
                if success:
                    self.status_label.setText("Active - Synchronizing")
                    self.start_sync_btn.setEnabled(False)
                    self.stop_sync_btn.setEnabled(True)
                    self.export_btn.setEnabled(True)
                    self.show_status("Synchronization started")
                else:
                    self.show_status("Failed to start synchronization", error=True)
        except Exception as e:
            logging.error(f"Error starting synchronization: {e}")
            self.show_status(f"Error: {str(e)}", error=True)

    def stop_synchronization(self):
        """Stop LSL synchronization."""
        try:
            if self.receiver.running:
                self.receiver.stop_collection()
                self.status_label.setText("Not Active")
                self.start_sync_btn.setEnabled(True)
                self.stop_sync_btn.setEnabled(False)
                self.show_status("Synchronization stopped")
        except Exception as e:
            logging.error(f"Error stopping synchronization: {e}")
            self.show_status(f"Error: {str(e)}", error=True)

    def refresh_streams(self):
        """Refresh available LSL streams."""
        try:
            success = self.receiver.resolve_streams()
            if success:
                stream_count = len(self.receiver.stream_names)
                self.streams_label.setText(f"Available Streams: {stream_count}")

                # Initialize stream status tracking for each stream
                self._update_stream_status_display()

                # Build status message
                streams_info = ", ".join(self.receiver.stream_names)
                self.show_status(f"Found {stream_count} streams: {streams_info}")
            else:
                self.streams_label.setText("Available Streams: 0")
                self.show_status("No LSL streams found")

                # Clear stream status display
                self._clear_stream_status_display()
        except Exception as e:
            logging.error(f"Error refreshing streams: {e}")
            self.show_status(f"Error: {str(e)}", error=True)

    def _update_stream_status_display(self):
        """Update the UI with status indicators for each stream."""
        # Clear existing status widgets
        self._clear_stream_status_display()

        # Create a widget for each stream
        for stream_name in self.receiver.stream_names:
            stream_type = "Unknown"
            for i, info in enumerate(self.receiver.stream_info):
                if info.name() == stream_name:
                    stream_type = info.type()
                    break

            # Create a row for this stream
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)

            # Stream name and type
            name_label = QLabel(f"{stream_name} ({stream_type})")
            row_layout.addWidget(name_label)

            row_layout.addStretch(1)

            # Status indicator
            status_label = QLabel("Waiting for data...")
            status_label.setStyleSheet("color: #FFAA33;")  # Yellow warning color
            row_layout.addWidget(status_label)

            # Status count indicator
            count_label = QLabel("Samples: 0")
            row_layout.addWidget(count_label)

            # Add to layout
            self.stream_status_layout.addWidget(row_widget)

            # Store widget references
            self.stream_status_widgets[stream_name] = {
                "row": row_widget,
                "status": status_label,
                "count": count_label,
            }

            # Initialize status tracking
            self.stream_status[stream_name] = {
                "last_sample_time": 0,
                "sample_count": 0,
                "has_data": False,
            }

    def _clear_stream_status_display(self):
        """Clear all stream status widgets."""
        # Remove all stream status widgets
        for stream_name, widgets in self.stream_status_widgets.items():
            if "row" in widgets:
                widgets["row"].setParent(None)
                widgets["row"].deleteLater()

        # Clear dictionaries
        self.stream_status_widgets.clear()
        self.stream_status.clear()

    def export_dataset(self):
        """Export synchronized data to the selected format."""
        try:
            if not self.receiver.running and not self.receiver.buffer:
                self.show_status("No data available for export", error=True)
                return

            # Generate timestamp for filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")

            # Get export format
            export_format = self.export_format_combo.currentText()

            # Export based on selected format
            if export_format == "HDF5":
                filename = f"synchronized_data_{timestamp}.h5"
                success = self.exporter.export_to_hdf5(filename)
                if success:
                    self.show_status(f"Exported to {filename}")
                else:
                    self.show_status("Failed to export to HDF5", error=True)

            elif export_format == "EDF+":
                filename = f"eeg_data_{timestamp}.edf"
                success = self.exporter.export_to_edf(filename)
                if success:
                    self.show_status(f"Exported to {filename}")
                else:
                    self.show_status("Failed to export to EDF+", error=True)

            elif export_format == "CSV":
                eeg_filename = f"eeg_data_{timestamp}.csv"
                events_filename = f"events_data_{timestamp}.csv"
                success = self.exporter.export_to_csv(eeg_filename, events_filename)
                if success:
                    self.show_status(
                        f"Exported to {eeg_filename} and {events_filename}"
                    )
                else:
                    self.show_status("Failed to export to CSV", error=True)

            elif export_format == "BIDS":
                self.show_status("BIDS export not implemented yet", error=True)

        except Exception as e:
            logging.error(f"Error exporting dataset: {e}")
            self.show_status(f"Export error: {str(e)}", error=True)

    def update_status(self):
        """Update status information."""
        if not self.receiver.running:
            return

        # Check for data in each stream
        buffer = self.receiver.buffer
        if not buffer:
            return

        # Update status for each stream
        for stream_name, data in buffer.items():
            if (
                stream_name not in self.stream_status
                or stream_name not in self.stream_status_widgets
            ):
                continue

            timestamps = data.get("timestamps", [])
            stream_data = data.get("data", [])

            # Check if we have new data
            if timestamps and stream_data:
                sample_count = len(timestamps)
                last_sample_time = timestamps[-1] if timestamps else 0

                # Update status tracking
                previous_count = self.stream_status[stream_name]["sample_count"]
                self.stream_status[stream_name]["sample_count"] = sample_count
                self.stream_status[stream_name]["last_sample_time"] = last_sample_time

                # Check if we have new data
                has_new_data = sample_count > previous_count

                # Update UI
                if has_new_data:
                    # Mark as having data
                    if not self.stream_status[stream_name]["has_data"]:
                        self.stream_status[stream_name]["has_data"] = True

                    # Update status display
                    status_label = self.stream_status_widgets[stream_name]["status"]
                    status_label.setText("Receiving data")
                    status_label.setStyleSheet("color: #5FB878;")  # Green success color

                    # Update count
                    count_label = self.stream_status_widgets[stream_name]["count"]
                    count_label.setText(f"Samples: {sample_count}")

        # Get synchronized events info
        sync_data = self.receiver.get_synchronized_data()

        # Update overall status
        if sync_data and "synchronized_events" in sync_data:
            event_count = len(sync_data["synchronized_events"])
            self.streams_label.setText(
                f"Streams: {len(self.receiver.stream_names)} | Synchronized Events: {event_count}"
            )
        else:
            # Check if any stream has data
            any_data = any(status["has_data"] for status in self.stream_status.values())

            if any_data:
                no_data_streams = [
                    name
                    for name, status in self.stream_status.items()
                    if not status["has_data"]
                ]
                if no_data_streams:
                    waiting_msg = f"Waiting for data from: {', '.join(no_data_streams)}"
                    self.streams_label.setText(waiting_msg)
                else:
                    self.streams_label.setText(
                        "All streams have data, waiting for synchronization events..."
                    )
            else:
                self.streams_label.setText(
                    f"Streams: {len(self.receiver.stream_names)} | Waiting for data..."
                )

    def show_status(self, message, error=False):
        """Show a status message."""
        self.message_label.setText(message)
        if error:
            self.message_label.setStyleSheet("color: #FF5555;")
        else:
            self.message_label.setStyleSheet("color: #5FB878;")

        # Emit signal for parent application
        self.status_message.emit(message)


def create_eeg_publisher(device_name, board_id, num_channels, sampling_rate):
    """
    Create an EEG publisher with device-specific configuration.

    Args:
        device_name: Name of the EEG device
        board_id: Board ID (from BrainFlow)
        num_channels: Number of channels
        sampling_rate: Sampling rate in Hz

    Returns:
        Configured LSLEEGPublisher
    """
    publisher = LSLEEGPublisher(
        device_name=device_name, channel_count=num_channels, sampling_rate=sampling_rate
    )

    # Add device-specific metadata
    desc = publisher.publisher.info.desc()
    desc.append_child_value("board_id", str(board_id))

    return publisher


def create_input_publisher():
    """
    Create an input event publisher.

    Returns:
        Configured LSLInputPublisher
    """
    return LSLInputPublisher()


def create_marker_publisher():
    """
    Create a marker/annotation publisher.

    Returns:
        Configured LSLMarkerPublisher
    """
    return LSLMarkerPublisher()
