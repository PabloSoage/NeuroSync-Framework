import logging
from typing import List, Optional

import numpy as np
import pyqtgraph as pg
from brainflow.data_filter import DataFilter, WindowOperations
from pyqtgraph.Qt import QtCore

from ..collectors.eeg_collector import EEGCollector


class MultiModalityVisualizer:
    """
    Visualizer for multiple data modalities (EEG, EMG, ECG, etc.)

    This class provides real-time visualization for various types of biosignals.
    """

    def __init__(self, collector: EEGCollector):
        """
        Initialize the multi-modality visualizer.

        Args:
            collector: Data collector object
        """
        self.collector = collector
        self.sampling_rate = collector.sampling_rate
        self.update_speed_ms = 50
        self.window_size = 4  # Display 4 seconds of data
        self.num_points = int(self.window_size * self.sampling_rate)

        # Data for plotting
        self.time_vector = np.linspace(0, self.window_size, self.num_points)

        # Track modal windows
        self.windows = {}

        # Initialize available channel types
        self.channel_types = {}
        self._init_channel_types()

        logging.info("Multi-modality visualizer initialized")

    def _init_channel_types(self):
        """Initialize channel type data."""
        # Define colors and labels for different channel types
        type_colors = {
            "eeg": (0, 255, 0),  # Green
            "emg": (255, 100, 0),  # Orange
            "ecg": (255, 0, 0),  # Red
            "eog": (0, 200, 200),  # Cyan
            "eda": (200, 100, 0),  # Brown
            "ppg": (255, 0, 255),  # Magenta
            "accel": (0, 100, 255),  # Blue
            "gyro": (100, 100, 255),  # Light blue
        }

        type_labels = {
            "eeg": "EEG",
            "emg": "EMG",
            "ecg": "ECG",
            "eog": "EOG",
            "eda": "EDA",
            "ppg": "PPG",
            "accel": "Accelerometer",
            "gyro": "Gyroscope",
        }

        # Get channels of each type
        for ch_type in type_colors.keys():
            channels = self.collector.get_channel_by_type(ch_type)
            if channels and len(channels) > 0:
                self.channel_types[ch_type] = {
                    "channels": channels,
                    "color": type_colors.get(ch_type, (255, 255, 255)),
                    "label": type_labels.get(ch_type, ch_type.upper()),
                }

                # For EEG, try to get channel names
                if ch_type == "eeg" and hasattr(self.collector, "eeg_names"):
                    self.channel_types[ch_type][
                        "channel_names"
                    ] = self.collector.eeg_names
                else:
                    self.channel_types[ch_type]["channel_names"] = [
                        f"Ch{i}" for i in channels
                    ]

    def create_visualization(self, channel_type: str):
        """
        Create a visualization window for a specific channel type.

        Args:
            channel_type: Type of channel to visualize
        """
        if channel_type not in self.channel_types:
            logging.warning(f"No {channel_type} channels available")
            return

        if channel_type in self.windows and self.windows[channel_type].isVisible():
            logging.info(f"{channel_type} visualization already open")
            self.windows[channel_type].raise_()
            return

        # Get channels and settings for this type
        channels = self.channel_types[channel_type]["channels"]
        color = self.channel_types[channel_type]["color"]
        label = self.channel_types[channel_type]["label"]
        names = self.channel_types[channel_type]["channel_names"]

        # Create window
        win = pg.GraphicsLayoutWidget(title=f"{label} Visualization")
        win.resize(1000, 600)
        win.setWindowTitle(f"Real-time {label} Visualization")

        # Create plots for each channel
        plots = []
        curves = []

        for i, channel in enumerate(channels):
            plot = win.addPlot(row=i, col=0)
            plot.showAxis("left", True)
            plot.setMenuEnabled("left", False)

            if i == 0:
                plot.setTitle(f"{label} Channels")
            else:
                plot.hideAxis("top")

            if i == len(channels) - 1:
                plot.setLabel("bottom", "Time", "s")
            else:
                plot.hideAxis("bottom")

            # Set channel name as label
            ch_name = names[i] if i < len(names) else f"Ch {channel}"
            plot.setLabel("left", ch_name)

            # Use custom color for this channel type
            curve = plot.plot(pen=pg.mkPen(color=color, width=1))
            plots.append(plot)
            curves.append(curve)

        # Add FFT plot if applicable (for signal data, not for motion data)
        if channel_type in ["eeg", "emg", "ecg", "eog"]:
            fft_plot = win.addPlot(row=0, col=1, rowspan=len(channels) // 2)
            fft_plot.setTitle(f"{label} Power Spectrum")
            fft_plot.setLabel("bottom", "Frequency", "Hz")
            fft_plot.setLabel("left", "Power")
            fft_plot.setLogMode(x=False, y=True)

            fft_curves = []
            legend = fft_plot.addLegend()

            max_fft_channels = min(len(channels), 8)  # Limit number of FFT plots
            for i in range(max_fft_channels):
                fft_color = pg.mkPen(color=(color[0], color[1], color[2], 200), width=2)
                curve = fft_plot.plot(pen=fft_color)
                fft_curves.append(curve)
                legend.addItem(
                    curve, names[i] if i < len(names) else f"Ch{channels[i]}"
                )
        else:
            fft_curves = None

        # Show the window
        win.show()

        # Setup timer for updating the plots
        timer = QtCore.QTimer()
        timer.timeout.connect(
            lambda: self._update_plots(channel_type, channels, curves, fft_curves)
        )
        timer.start(self.update_speed_ms)

        # Store window and data for this channel type
        self.windows[channel_type] = win
        self.channel_types[channel_type]["timer"] = timer
        self.channel_types[channel_type]["curves"] = curves
        self.channel_types[channel_type]["fft_curves"] = fft_curves

        logging.info(f"Created {label} visualization with {len(channels)} channels")

    def _update_plots(
        self,
        channel_type: str,
        channels: List[int],
        curves: List,
        fft_curves: Optional[List] = None,
    ):
        """Update plots for a specific channel type."""
        try:
            # Get the latest data
            data, timestamps = self.collector.get_data(self.num_points)

            if data.size == 0:
                return

            # Update time series plots
            for i, channel in enumerate(channels):
                if i < len(curves) and channel < data.shape[0]:
                    try:
                        channel_data = data[channel][-self.num_points :]
                        if len(channel_data) > 0:
                            # Ensure flat array even if already 1D
                            channel_data = np.asarray(channel_data).flatten()
                            time_vector = self.time_vector[-len(channel_data) :]
                            curves[i].setData(time_vector, channel_data)
                    except Exception as e:
                        logging.error(f"Error updating time series plot: {e}")

            # Update FFT plots if applicable
            if fft_curves is not None:
                nfft = DataFilter.get_nearest_power_of_two(self.sampling_rate)
                for i, channel in enumerate(channels):
                    if i < len(fft_curves) and channel < data.shape[0]:
                        try:
                            channel_data = data[channel][-self.num_points :]
                            if len(channel_data) > nfft:  # Need enough data for FFT
                                # Calculate PSD
                                psd_result = DataFilter.get_psd_welch(
                                    channel_data,
                                    nfft,
                                    nfft // 2,
                                    self.sampling_rate,
                                    WindowOperations.HANNING.value,
                                )

                                # Generate frequency vector
                                freq = np.linspace(
                                    0, self.sampling_rate / 2, len(psd_result)
                                )
                                fft_curves[i].setData(freq, psd_result)
                        except Exception as e:
                            logging.error(f"Error updating FFT plot: {e}")

        except Exception as e:
            logging.error(f"Error in update_plots: {e}")

    def close_all(self):
        """Close all visualization windows."""
        for window_type, window in self.windows.items():
            try:
                # Stop the timer
                if "timer" in self.channel_types[window_type]:
                    self.channel_types[window_type]["timer"].stop()
                # Close the window
                window.close()
            except Exception as e:
                logging.error(f"Error closing {window_type} window: {e}")

        # Clear windows dict
        self.windows = {}

    def is_window_open(self, channel_type: str) -> bool:
        """
        Check if a visualization window for a specific channel type is open.

        Args:
            channel_type: Type of channel to check

        Returns:
            True if the window is open, False otherwise
        """
        return channel_type in self.windows and self.windows[channel_type].isVisible()

    def get_available_modalities(self) -> List[str]:
        """
        Get a list of available modalities for visualization.

        Returns:
            List of available modality names
        """
        return list(self.channel_types.keys())
