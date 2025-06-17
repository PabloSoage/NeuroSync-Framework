import logging
from typing import Any, List

import numpy as np
import pyqtgraph as pg
from brainflow.data_filter import DataFilter, WindowOperations
from pyqtgraph.Qt import QtCore

from ..collectors.eeg_collector import EEGCollector
from ..processors.signal_processor import SignalProcessor
from ..services.data_access_service import DataAccessService


class EEGVisualizer:
    """
    Visualizer for EEG data using PyQtGraph.

    This class provides real-time visualization of EEG data with various display options.
    """

    def __init__(self, collector: EEGCollector, processor: SignalProcessor) -> None:
        """
        Initialize the EEG visualizer.

        Args:
            collector: EEG data collector (for metadata only)
            processor: Signal processor for data filtering
        """
        # Only use collector for metadata, not for data
        self.collector = collector
        self.processor = processor

        # Get data from DataAccessService
        self.data_service = DataAccessService.get_instance()

        # Register as local callback for immediate updates (no processing delay)
        self.local_callback_id = self.data_service.register_local_callback(
            self._on_immediate_data
        )

        # Get metadata from collector
        self.sampling_rate = collector.sampling_rate
        self.eeg_channels = collector.get_eeg_channels()
        self.num_channels = len(self.eeg_channels)
        self.update_speed_ms = 50
        self.window_size = 4  # Display 4 seconds of data
        self.num_points = int(self.window_size * self.sampling_rate)

        # Data for plotting
        self.time_vector = np.linspace(0, self.window_size, self.num_points)

        # Setup UI elements
        self.setup_ui()

        logging.info("EEG visualizer initialized with immediate local callback")

    def _on_immediate_data(self, data: np.ndarray, timestamps: List[int]) -> None:
        """Handle immediate data updates for responsive visualization."""
        try:
            # This ensures immediate visualization updates without waiting for processing
            # The data is already in DataAccessService buffer for get_raw_data() calls
            logging.debug(f"Received immediate data update: {data.shape}")
        except Exception as e:
            logging.error(f"Error handling immediate data in visualizer: {e}")

    def setup_ui(self) -> None:
        """Set up the user interface for the visualizer."""
        self.win = pg.GraphicsLayoutWidget(title="EEG Data Visualization")
        self.win.resize(1000, 600)
        self.win.setWindowTitle("Real-time EEG Visualization")

        # Set up close event handler
        self.win.closeEvent = self.handle_close_event

        # Add sample rate display (NEW)
        self.sample_rate_label = pg.LabelItem(justify="left")
        self.sample_rate_label.setText(
            '<span style="font-family: Arial; font-size: 12pt; font-weight: bold;">'
            "Sample Rate: --- Hz</span>"
        )

        # Add header plot for labels and info (NEW)
        self.win.addItem(self.sample_rate_label, row=0, col=0, colspan=2)

        # Create plots for each EEG channel - shift down by 1 for header
        self.plots = []
        self.curves = []

        # Quality indicators
        self.quality_indicators = []

        # Define quality colors
        self.quality_colors = [
            (255, 0, 0),  # Red (bad quality)
            (255, 165, 0),  # Orange (poor quality)
            (255, 255, 0),  # Yellow (fair quality)
            (144, 238, 144),  # Light green (good quality)
            (0, 128, 0),  # Dark green (excellent quality)
        ]

        for i in range(self.num_channels):
            plot = self.win.addPlot(row=i + 1, col=0)  # Offset by 1 for header
            plot.showAxis("left", True)
            plot.setMenuEnabled("left", False)

            if i == 0:
                plot.setTitle("EEG Channels")
            else:
                plot.hideAxis("top")

            if i == self.num_channels - 1:
                plot.setLabel("bottom", "Time", "s")
            else:
                plot.hideAxis("bottom")

            # Use actual EEG channel names if available
            if hasattr(self.collector, "eeg_names") and i < len(
                self.collector.eeg_names
            ):
                ch_name = self.collector.eeg_names[i]
            else:
                ch_name = f"CH {self.eeg_channels[i]}"
            plot.setLabel("left", ch_name)

            # Add curve for the data
            curve = plot.plot(
                pen=pg.mkPen(
                    color=(i * 50 % 255, 255 - i * 30 % 255, i * 20 % 255), width=1
                )
            )
            self.plots.append(plot)
            self.curves.append(curve)

            # Add quality indicator (circle with color indicating quality)
            quality_indicator = pg.ScatterPlotItem()
            plot.addItem(quality_indicator)
            self.quality_indicators.append(quality_indicator)

        # Add FFT plot - also offset by 1
        self.fft_plot = self.win.addPlot(row=1, col=1, rowspan=self.num_channels // 2)
        self.fft_plot.setTitle("Power Spectrum")
        self.fft_plot.setLabel("bottom", "Frequency", "Hz")
        self.fft_plot.setLabel("left", "Power", "µV²/Hz")
        self.fft_plot.setLogMode(x=False, y=True)  # Log scale for power
        self.fft_curves = []

        # Determine number of columns for the legend based on number of channels
        legend_columns = 1
        if self.num_channels > 8:
            legend_columns = 2
        if self.num_channels > 16:
            legend_columns = 3

        # Create legend with multiple columns for better space management
        self.fft_legend = self.fft_plot.addLegend(
            offset=(-10, 10), colCount=legend_columns
        )

        # Increase the maximum number of channels in the spectrum (up to 16)
        max_fft_channels = min(self.num_channels, 16)

        for i in range(max_fft_channels):
            color = pg.mkPen(
                color=(i * 50 % 255, 255 - i * 30 % 255, i * 20 % 255), width=2
            )
            curve = self.fft_plot.plot(pen=color)
            self.fft_curves.append(curve)

            # Use real channel names in the FFT legend
            if hasattr(self.collector, "eeg_names") and i < len(
                self.collector.eeg_names
            ):
                legend_name = self.collector.eeg_names[i]
            else:
                legend_name = f"CH{self.eeg_channels[i]}"

            self.fft_legend.addItem(curve, legend_name)

        # Add band power indicator - also offset by 1
        self.band_plot = self.win.addPlot(
            row=self.num_channels // 2 + 1, col=1, rowspan=self.num_channels // 2
        )
        self.band_plot.setTitle("Band Powers")
        self.band_plot.setLabel("bottom", "Band")
        self.band_plot.setLabel("left", "Power", "dB")

        self.bands = ["Delta", "Theta", "Alpha", "Beta", "Gamma"]
        self.band_ranges = [(1, 4), (4, 8), (8, 13), (13, 30), (30, 50)]
        self.bar_graph = pg.BarGraphItem(
            x=range(len(self.bands)), height=[0] * len(self.bands), width=0.6, brush="b"
        )
        self.band_plot.addItem(self.bar_graph)
        self.band_plot.setXRange(-0.5, len(self.bands) - 0.5)

        # Set axis labels
        ax = self.band_plot.getAxis("bottom")
        ax.setTicks([list(enumerate(self.bands))])

        # Show the window
        self.win.show()

        # Setup timer for updating the plots
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)

    def handle_close_event(self, event: Any) -> None:
        """Handle window close event to signal the app that visualization was closed."""
        # Unregister from callbacks
        if hasattr(self, "local_callback_id"):
            self.data_service.unregister_local_callback(self.local_callback_id)
            logging.info("EEG visualizer unregistered from local callbacks")

        self.stop()  # Stop the timer
        # Emit signal or notify that window was closed
        logging.info("EEG visualization window closed by user")
        # Accept the close event
        event.accept()

    def start(self) -> None:
        """Start updating the visualizer."""
        self.timer.start(self.update_speed_ms)
        self.win.show()  # Make sure window is visible
        logging.info("EEG visualizer started")

    def stop(self) -> None:
        """Stop updating the visualizer."""
        self.timer.stop()
        logging.info("EEG visualizer stopped")

    def update_plots(self) -> None:
        """Update all plots with new data."""
        try:
            # Get data from DataAccessService - use get_current_data() to get filtered data
            # This ensures consistency with the centralized filter pipeline
            data, timestamps = self.data_service.get_current_data()
            metadata = self.data_service.get_metadata()

            # Get sample rate info from metadata
            actual_sample_rate = metadata.get("actual_sample_rate", 0)
            expected_sample_rate = metadata.get("sampling_rate", 250)

            # Update sample rate display
            if actual_sample_rate > 0:
                efficiency = (actual_sample_rate / expected_sample_rate) * 100
                if efficiency >= 90:
                    color = "green"
                elif efficiency >= 70:
                    color = "orange"
                else:
                    color = "red"

                self.sample_rate_label.setText(
                    f'<span style="font-family: Arial; font-size: 12pt; font-weight: bold;">'
                    f"Expected: {expected_sample_rate} Hz | "
                    f'<span style="color:{color}">Actual: {actual_sample_rate:.1f} Hz ({efficiency:.1f}%)</span>'
                    f"</span>"
                )

            if data.size == 0 or len(self.eeg_channels) == 0:
                return

            # Use data as-is since it comes from the centralized filter pipeline
            # Remove local filtering - DataAccessService handles this
            data_to_plot = data.copy()

            # Remove visualization-specific filtering - now handled centrally
            # if self.apply_bandpass:
            #     data_to_plot = self.processor.bandpass_filter(
            #         data_to_plot, self.bandpass_low, self.bandpass_high, 4
            #     )
            # if self.apply_notch:
            #     data_to_plot = self.processor.remove_environmental_noise(data_to_plot)
            # if self.apply_detrend:
            #     data_to_plot = self.processor.detrend(data_to_plot)

            # Calculate signal quality for each channel
            quality_scores = self.processor.get_all_channels_quality(
                data_to_plot, self.eeg_channels
            )

            # Update time series plots
            for i, channel in enumerate(self.eeg_channels):
                if i < len(self.curves) and channel < data_to_plot.shape[0]:
                    try:
                        # Get channel data and ensure it's 1D
                        channel_data = data_to_plot[channel][-self.num_points :]
                        if len(channel_data) > 0:
                            # Force to 1D array even if it's already 1D
                            channel_data = np.asarray(channel_data).flatten()
                            time_vector = self.time_vector[-len(channel_data) :]
                            self.curves[i].setData(time_vector, channel_data)

                            # Update quality indicator
                            quality = quality_scores.get(channel, 0)

                            # Position quality indicator at the latest data point
                            if len(time_vector) > 0 and len(channel_data) > 0:
                                x = time_vector[-1]
                                y = channel_data[-1]

                                # Determine color based on quality score
                                color_idx = min(
                                    int(quality * len(self.quality_colors)),
                                    len(self.quality_colors) - 1,
                                )
                                color_tuple = self.quality_colors[color_idx]

                                # Set size based on quality (better quality = smaller dot)
                                size = 12 - (quality * 5)  # Size between 7-12px

                                # Update position and appearance
                                self.quality_indicators[i].setData(
                                    [x],
                                    [y],
                                    size=size,
                                    brush=pg.mkBrush(color_tuple),
                                    pxMode=True,
                                )

                                # Optional: Add border to dots for better visibility
                                self.quality_indicators[i].setPen(
                                    pg.mkPen("w", width=0.5)
                                )
                    except Exception as e:
                        logging.error(
                            f"Error plotting time series for channel {channel}: {e}"
                        )

            # Update FFT plots (for channels)
            nfft = DataFilter.get_nearest_power_of_two(self.sampling_rate)
            for i, channel in enumerate(self.eeg_channels):
                if i < len(self.fft_curves) and channel < data_to_plot.shape[0]:
                    try:
                        # Get channel data and ensure it's 1D
                        channel_data = data_to_plot[channel][-self.num_points :]
                        if len(channel_data) > 0:
                            # Force to 1D array
                            channel_data = np.asarray(channel_data).flatten()

                            # Check if we have enough data for FFT
                            if len(channel_data) > nfft:
                                # Calculate PSD with proper error handling
                                try:
                                    # Use a smaller nfft if necessary
                                    actual_nfft = min(nfft, len(channel_data) // 2)
                                    actual_nfft = DataFilter.get_nearest_power_of_two(
                                        actual_nfft
                                    )

                                    # Get PSD using BrainFlow's DataFilter
                                    psd = DataFilter.get_psd_welch(
                                        channel_data,
                                        actual_nfft,
                                        actual_nfft // 2,
                                        self.sampling_rate,
                                        WindowOperations.HANNING.value,
                                    )

                                    # Ensure PSD is a 1D numpy array
                                    psd = np.asarray(psd).flatten()

                                    # Generate frequency vector of the same length as PSD
                                    freq = np.linspace(
                                        0, self.sampling_rate / 2, len(psd)
                                    )

                                    # Both freq and psd must be 1D arrays of the same length
                                    if len(freq) == len(psd) and len(freq) > 0:
                                        self.fft_curves[i].setData(freq, psd)
                                except Exception as e:
                                    logging.error(
                                        f"PSD calculation error for channel {channel}: {e}"
                                    )
                            else:
                                logging.debug(
                                    f"Not enough data for FFT on channel {channel}: {len(channel_data)} < {nfft}"
                                )
                    except Exception as e:
                        logging.error(f"Error plotting FFT for channel {channel}: {e}")

            # Update band powers
            if len(self.eeg_channels) > 0:
                # Use first channel for band powers
                channel = self.eeg_channels[0]
                if channel < data_to_plot.shape[0]:
                    try:
                        channel_data = data_to_plot[channel][-self.num_points :]
                        if len(channel_data) > 0:
                            # Force to 1D array
                            channel_data_flat = np.asarray(channel_data).flatten()

                            # Check if we have enough data for band power calculation
                            if len(channel_data_flat) > nfft:
                                # Create a properly formatted single-channel array for band power calculation
                                single_channel_data = np.array([channel_data_flat])

                                powers = []
                                for low, high in self.band_ranges:
                                    try:
                                        band_power = self.processor.get_band_power(
                                            single_channel_data, low, high
                                        )[0]
                                        # Convert to dB with safety check for non-positive values
                                        power_db = 10 * np.log10(max(band_power, 1e-10))
                                        powers.append(power_db)
                                    except Exception as e:
                                        logging.error(
                                            f"Error calculating band power {low}-{high}Hz: {e}"
                                        )
                                        powers.append(
                                            -100
                                        )  # Default low value on error

                                # Update the bar graph
                                if len(powers) == len(self.bands):
                                    self.bar_graph.setOpts(height=powers)
                            else:
                                logging.debug(
                                    f"Not enough data for band power: {len(channel_data_flat)} < {nfft}"
                                )
                    except Exception as e:
                        logging.error(f"Error plotting band powers: {e}")

        except Exception as e:
            logging.error(f"Error updating plots: {e}")

    def set_frequency_range(self, min_freq: float, max_freq: float) -> None:
        """Set the frequency range for the FFT plot."""
        self.fft_plot.setXRange(min_freq, max_freq)

    def set_log_mode(self, use_log: bool) -> None:
        """Set whether to use logarithmic scale for power spectrum."""
        self.fft_plot.setLogMode(x=False, y=use_log)

    def is_visible(self) -> bool:
        """Check if the visualization window is visible."""
        return self.win.isVisible()
