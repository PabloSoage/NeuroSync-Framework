import logging
import threading
from typing import Any, List, Dict, Optional

import numpy as np
import pyqtgraph as pg
from brainflow.data_filter import DataFilter, WindowOperations
from pyqtgraph.Qt import QtCore, QtWidgets

from ..collectors.eeg_collector import EEGCollector
from ..processors.signal_processor import SignalProcessor
from ..services.data_access_service import DataAccessService


class MultiSignalVisualizer:
    """
    Multi-page visualizer for different types of biosignal data.

    Automatically detects available channel types and creates appropriate visualization pages.
    """

    # Class-level cache for visualizers
    _cached_visualizers: Optional[Dict[str, Any]] = None

    def __init__(self, collector: EEGCollector, processor: SignalProcessor) -> None:
        """
        Initialize the multi-signal visualizer.

        Args:
            collector: EEG data collector (for metadata only)
            processor: Signal processor for data filtering
        """
        # Only use collector for metadata, not for data
        self.collector = collector
        self.processor = processor

        # Get data from DataAccessService
        self.data_service = DataAccessService.get_instance()

        # Register as local callback for immediate updates
        self.local_callback_id = self.data_service.register_local_callback(
            self._on_immediate_data
        )

        # Get metadata from collector
        self.sampling_rate = collector.sampling_rate
        self.update_speed_ms = 50
        self.window_size = 4  # Display 4 seconds of data
        self.num_points = int(self.window_size * self.sampling_rate)

        # Data for plotting
        self.time_vector = np.linspace(0, self.window_size, self.num_points)

        # IMPORTANT: Detect channel types AFTER connection using actual preset data
        self.channel_types = self._detect_channel_types_from_connected_board()

        # CACHING: Check if we have cached visualizers from previous instance WITH SAME BOARD AND PRESET
        self._load_cached_visualizers()

        # Setup UI elements IMMEDIATELY
        self.setup_ui_fast()

        logging.info(
            f"Multi-signal visualizer initialized with channel types: {list(self.channel_types.keys())}"
        )

    def _detect_channel_types_from_connected_board(self) -> Dict[str, Dict]:
        """
        OPTIMIZED: Detect available channel types using the ACTUAL connected board and preset.

        Returns:
            Dictionary with channel type info
        """
        channel_types = {}

        # Get the actual device info from the connected collector
        try:
            device_info = self.collector.get_device_info()
            current_preset = device_info.get("preset", "unknown")
            logging.info(
                f"Visualizer: Using device info from connected board with preset {current_preset}"
            )
            logging.info(
                f"Visualizer: Available channel types in collector: {list(self.collector.channel_types.keys())}"
            )

            # Log which channel types have actual channels
            for ch_type, channels in self.collector.channel_types.items():
                if channels:
                    logging.info(f"Visualizer: {ch_type} channels found: {channels}")
                else:
                    logging.debug(
                        f"Visualizer: No {ch_type} channels for preset {current_preset}"
                    )

            # Use the channel information from the actual connected board
            if (
                hasattr(self.collector, "channel_types")
                and self.collector.channel_types
            ):
                collector_types = self.collector.channel_types

                for ch_type, channels in collector_types.items():
                    if (
                        channels
                    ):  # Only include types that ACTUALLY have channels in this preset
                        # Generate names efficiently
                        if ch_type == "eeg" and hasattr(self.collector, "eeg_names"):
                            channel_names = self.collector.eeg_names[: len(channels)]
                        else:
                            # Quick name generation
                            if ch_type == "accel":
                                channel_names = [
                                    f"ACCEL_{['X', 'Y', 'Z'][i % 3]}"
                                    for i in range(len(channels))
                                ]
                            elif ch_type == "gyro":
                                channel_names = [
                                    f"GYRO_{['X', 'Y', 'Z'][i % 3]}"
                                    for i in range(len(channels))
                                ]
                            else:
                                channel_names = [
                                    f"{ch_type.upper()}_{i}"
                                    for i in range(len(channels))
                                ]

                        channel_types[ch_type] = {
                            "channels": channels,
                            "names": channel_names,
                            "count": len(channels),
                        }
                        logging.info(
                            f"Visualizer: Added {ch_type} tab with {len(channels)} channels"
                        )

                logging.info(
                    f"Visualizer: Final channel types for preset {current_preset}: {list(channel_types.keys())}"
                )
                return channel_types

        except Exception as e:
            logging.warning(f"Error getting device info from connected board: {e}")

        # FALLBACK: Simple EEG-only detection if collector data isn't available
        eeg_channels = getattr(self.collector, "eeg_channels", [])
        if not eeg_channels:
            try:
                eeg_channels = self.collector.get_eeg_channels()
            except:
                eeg_channels = []

        if eeg_channels:
            eeg_names = getattr(
                self.collector,
                "eeg_names",
                [f"CH{i}" for i in range(len(eeg_channels))],
            )
            channel_types["eeg"] = {
                "channels": eeg_channels,
                "names": eeg_names[: len(eeg_channels)],
                "count": len(eeg_channels),
            }
            logging.info(
                f"Fallback: Using EEG channels only: {len(eeg_channels)} channels"
            )
        else:
            logging.warning(
                "No channels detected - this may indicate a preset with no data or configuration error"
            )

        return channel_types

    def _load_cached_visualizers(self) -> None:
        """Load cached visualizers if available and still valid for THIS board and preset."""
        try:
            # Get cached visualizers from class-level storage
            cached_data = MultiSignalVisualizer._cached_visualizers

            if cached_data is not None:
                cached_collector_id = cached_data.get("collector_id")
                cached_preset = cached_data.get("preset")
                cached_board_id = cached_data.get("board_id")

                current_collector_id = id(self.collector)
                current_preset = getattr(self.collector, "preset", None)
                current_board_id = getattr(self.collector, "board_id", None)

                # Check if cache is for the same collector, preset, AND board
                if (
                    cached_collector_id == current_collector_id
                    and cached_preset == current_preset
                    and cached_board_id == current_board_id
                ):
                    self._cached_tabs = cached_data.get("tabs", {})
                    logging.info(
                        f"Loaded {len(self._cached_tabs)} cached visualizer tabs for preset {current_preset}"
                    )
                else:
                    # Different collector, preset, or board - clear cache
                    self._clear_cache()
                    self._cached_tabs = {}
                    logging.info(
                        f"Cache invalidated: collector/preset/board changed (cached: {cached_preset}/{cached_board_id}, current: {current_preset}/{current_board_id})"
                    )
            else:
                self._cached_tabs = {}

        except Exception as e:
            logging.debug(f"Error loading cached visualizers: {e}")
            self._cached_tabs = {}

    def _save_cached_visualizers(self) -> None:
        """Save current visualizers to cache with board and preset info."""
        try:
            # Only cache actually created visualizers (not placeholders)
            tabs_to_cache = {}

            for ch_type, visualizer in self.visualizers.items():
                if not isinstance(visualizer, QtWidgets.QLabel):  # Not a placeholder
                    tabs_to_cache[ch_type] = visualizer

            # Store at class level with board and preset information
            current_preset = getattr(self.collector, "preset", None)
            current_board_id = getattr(self.collector, "board_id", None)

            MultiSignalVisualizer._cached_visualizers = {
                "collector_id": id(self.collector),
                "preset": current_preset,
                "board_id": current_board_id,
                "tabs": tabs_to_cache,
            }

            logging.info(
                f"Cached {len(tabs_to_cache)} visualizer tabs for preset {current_preset}, board {current_board_id}"
            )

        except Exception as e:
            logging.debug(f"Error saving cached visualizers: {e}")

    @classmethod
    def _clear_cache(cls) -> None:
        """Clear cached visualizers (called when collector changes)."""
        try:
            if (
                hasattr(cls, "_cached_visualizers")
                and cls._cached_visualizers is not None
            ):
                cached_data = cls._cached_visualizers
                cached_tabs = cached_data.get("tabs", {})

                # Properly clean up cached visualizers
                for ch_type, visualizer in cached_tabs.items():
                    try:
                        if hasattr(visualizer, "deleteLater"):
                            visualizer.deleteLater()
                    except:
                        pass

                cls._cached_visualizers = None
                logging.info("Cleared cached visualizers")

        except Exception as e:
            logging.debug(f"Error clearing cache: {e}")

    def _detect_channel_types_fast(self) -> Dict[str, Dict]:
        """
        OPTIMIZED: Detect available channel types using pre-existing collector data.

        Returns:
            Dictionary with channel type info
        """
        channel_types = {}

        # FAST: Use collector's already-initialized channel_types if available
        if hasattr(self.collector, "channel_types") and self.collector.channel_types:
            collector_types = self.collector.channel_types

            for ch_type, channels in collector_types.items():
                if channels:  # Only include types that have channels
                    # Generate names efficiently
                    if ch_type == "eeg" and hasattr(self.collector, "eeg_names"):
                        channel_names = self.collector.eeg_names[: len(channels)]
                    else:
                        # Quick name generation without complex logic
                        if ch_type == "accel":
                            channel_names = [
                                f"ACCEL_{['X', 'Y', 'Z'][i % 3]}"
                                for i in range(len(channels))
                            ]
                        elif ch_type == "gyro":
                            channel_names = [
                                f"GYRO_{['X', 'Y', 'Z'][i % 3]}"
                                for i in range(len(channels))
                            ]
                        else:
                            channel_names = [
                                f"{ch_type.upper()}_{i}" for i in range(len(channels))
                            ]

                    channel_types[ch_type] = {
                        "channels": channels,
                        "names": channel_names,
                        "count": len(channels),
                    }

            return channel_types

        # FALLBACK: Simple EEG-only detection if collector data isn't available
        eeg_channels = getattr(self.collector, "eeg_channels", [])
        if not eeg_channels:
            try:
                eeg_channels = self.collector.get_eeg_channels()
            except:
                eeg_channels = []

        if eeg_channels:
            eeg_names = getattr(
                self.collector,
                "eeg_names",
                [f"CH{i}" for i in range(len(eeg_channels))],
            )
            channel_types["eeg"] = {
                "channels": eeg_channels,
                "names": eeg_names[: len(eeg_channels)],
                "count": len(eeg_channels),
            }

        return channel_types

    def _on_immediate_data(self, data: np.ndarray, timestamps: List[int]) -> None:
        """Handle immediate data updates for responsive visualization."""
        try:
            logging.debug(f"Received immediate data update: {data.shape}")
        except Exception as e:
            logging.error(f"Error handling immediate data in visualizer: {e}")

    def setup_ui_fast(self) -> None:
        """OPTIMIZED: Set up the user interface quickly."""
        # Create main widget and layout
        self.main_widget = QtWidgets.QWidget()
        self.main_widget.setWindowTitle("Multi-Signal Biosignal Visualization")
        self.main_widget.resize(1200, 800)

        # Apply dark theme
        self.main_widget.setStyleSheet(
            """
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background-color: #404040;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #555555;
                border-bottom: 2px solid #0078d4;
            }
            QTabBar::tab:hover {
                background-color: #4a4a4a;
            }
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 12pt;
                padding: 5px;
            }
        """
        )

        # Set up close event handler
        self.main_widget.closeEvent = self.handle_close_event

        # Create main layout
        main_layout = QtWidgets.QVBoxLayout(self.main_widget)

        # Add sample rate display
        self.sample_rate_label = QtWidgets.QLabel()
        self.sample_rate_label.setText("Sample Rate: --- Hz")
        main_layout.addWidget(self.sample_rate_label)

        # Add processing status display
        self.processing_status_label = QtWidgets.QLabel()
        self.processing_status_label.setStyleSheet(
            "font-size: 10pt; color: #cccccc; padding: 2px;"
        )
        self.processing_status_label.setText("Processing: None Active")
        main_layout.addWidget(self.processing_status_label)

        # Create tab widget for different signal types
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tab_widget)

        # Store visualizers for each type
        self.visualizers = {}
        self.current_tab_index = 0

        # OPTIMIZATION: Add GLOBAL creation lock to prevent any simultaneous creation
        self._tab_creation_lock = threading.Lock()
        self._currently_creating_tab = False  # Simple boolean flag

        # CACHING: Start with cached visualizers if available
        if hasattr(self, "_cached_tabs") and self._cached_tabs:
            self.visualizers.update(self._cached_tabs)

        # OPTIMIZATION: Create first tab immediately, others lazily
        if self.channel_types:
            # Create the first (most important) tab immediately if not cached
            first_type = list(self.channel_types.keys())[0]
            first_info = self.channel_types[first_type]

            if first_info["count"] > 0:
                if first_type in self.visualizers:
                    # Use cached visualizer
                    visualizer = self.visualizers[first_type]
                    self.tab_widget.addTab(
                        visualizer,
                        f"{first_type.upper()} ({first_info['count']} channels)",
                    )
                    logging.info(f"Reused cached visualizer for {first_type}")
                else:
                    # Create new visualizer
                    visualizer = self._create_signal_visualizer_fast(
                        first_type, first_info
                    )
                    self.visualizers[first_type] = visualizer
                    self.tab_widget.addTab(
                        visualizer,
                        f"{first_type.upper()} ({first_info['count']} channels)",
                    )

                # Add other tabs as PLACEHOLDERS or CACHED VISUALIZERS
                for ch_type, ch_info in list(self.channel_types.items())[1:]:
                    if ch_info["count"] > 0:
                        if ch_type in self.visualizers:
                            # Use cached visualizer
                            visualizer = self.visualizers[ch_type]
                            self.tab_widget.addTab(
                                visualizer,
                                f"{ch_type.upper()} ({ch_info['count']} channels)",
                            )
                            logging.info(f"Reused cached visualizer for {ch_type}")
                        else:
                            # Add placeholder - will be created when accessed
                            placeholder = QtWidgets.QLabel(
                                f"Loading {ch_type.upper()} visualizer..."
                            )
                            placeholder.setAlignment(QtCore.Qt.AlignCenter)
                            self.tab_widget.addTab(
                                placeholder,
                                f"{ch_type.upper()} ({ch_info['count']} channels)",
                            )

        # Show the window
        self.main_widget.show()

        # Setup timer for updating the plots
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change events and create visualizers lazily."""
        self.current_tab_index = index

        # CRITICAL: Check if we're already creating a tab - if so, abort immediately
        if self._currently_creating_tab:
            logging.debug(
                f"Tab creation already in progress, ignoring tab change to {index}"
            )
            return

        # LAZY LOADING: Check if this tab needs a real visualizer
        current_widget = self.tab_widget.widget(index)
        if isinstance(current_widget, QtWidgets.QLabel):  # It's a placeholder
            tab_text = self.tab_widget.tabText(index)

            # CRITICAL: Set creation flag IMMEDIATELY to block any other attempts
            with self._tab_creation_lock:
                if self._currently_creating_tab:
                    logging.debug(
                        f"Another thread is creating tab, aborting for {tab_text}"
                    )
                    return

                self._currently_creating_tab = True  # Block all other creations

            try:
                # FIXED: Extract channel type from tab text more precisely
                channel_type_to_create = None

                # Parse the tab text format: "TYPE (X channels)"
                if "(" in tab_text:
                    type_part = tab_text.split("(")[0].strip().lower()

                    # Find the EXACT matching channel type
                    for ch_type in self.channel_types.keys():
                        if ch_type.lower() == type_part:
                            channel_type_to_create = ch_type
                            break

                # Only create the visualizer for the specific channel type
                if (
                    channel_type_to_create
                    and channel_type_to_create in self.channel_types
                ):
                    logging.info(
                        f"Creating visualizer for {channel_type_to_create} on demand"
                    )
                    try:
                        ch_info = self.channel_types[channel_type_to_create]
                        visualizer = self._create_signal_visualizer_fast(
                            channel_type_to_create, ch_info
                        )
                        self.visualizers[channel_type_to_create] = visualizer

                        # Replace ONLY this placeholder
                        self.tab_widget.removeTab(index)
                        self.tab_widget.insertTab(index, visualizer, tab_text)
                        self.tab_widget.setCurrentIndex(index)

                        logging.info(
                            f"Successfully created visualizer for {channel_type_to_create}"
                        )

                    except Exception as e:
                        logging.error(
                            f"Error creating visualizer for {channel_type_to_create}: {e}"
                        )
                        # Keep the placeholder with error message
                        current_widget.setText(
                            f"Error loading {channel_type_to_create.upper()} visualizer: {str(e)}"
                        )
                else:
                    logging.warning(
                        f"Could not determine channel type for tab: {tab_text}"
                    )

            finally:
                # ALWAYS release the creation flag, even if there was an error
                self._currently_creating_tab = False
                logging.debug(f"Released creation flag for {tab_text}")

        logging.debug(f"Switched to tab {index}")

    def _create_signal_visualizer_fast(
        self, ch_type: str, ch_info: Dict
    ) -> pg.GraphicsLayoutWidget:
        """
        OPTIMIZED: Create a visualizer widget efficiently.

        Args:
            ch_type: Type of channels (eeg, emg, etc.)
            ch_info: Channel information dictionary

        Returns:
            Graphics layout widget with plots
        """
        widget = pg.GraphicsLayoutWidget()

        channels = ch_info["channels"]
        names = ch_info["names"]
        num_channels = len(channels)

        # Create plots for each channel
        plots = []
        curves = []
        quality_indicators = []

        # Quality colors
        quality_colors = [
            (255, 0, 0),  # Red (bad quality)
            (255, 165, 0),  # Orange (poor quality)
            (255, 255, 0),  # Yellow (fair quality)
            (144, 238, 144),  # Light green (good quality)
            (0, 128, 0),  # Dark green (excellent quality)
        ]

        # OPTIMIZATION: Limit channels for faster rendering
        max_channels_to_show = min(
            num_channels, 16
        )  # Limit to 16 channels max for performance

        # Create time series plots
        for i in range(max_channels_to_show):
            plot = widget.addPlot(row=i, col=0)
            plot.showAxis("left", True)
            plot.setMenuEnabled("left", False)

            # Dark theme styling for plots
            plot.getAxis("left").setPen(pg.mkPen(color="#ffffff"))
            plot.getAxis("bottom").setPen(pg.mkPen(color="#ffffff"))
            plot.getAxis("left").setTextPen(pg.mkPen(color="#ffffff"))
            plot.getAxis("bottom").setTextPen(pg.mkPen(color="#ffffff"))

            if i == 0:
                plot.setTitle(f"{ch_type.upper()} Channels", color="#ffffff")
            else:
                plot.hideAxis("top")

            if i == max_channels_to_show - 1:
                plot.setLabel("bottom", "Time", "s", color="#ffffff")
            else:
                plot.hideAxis("bottom")

            # Use actual channel names
            ch_name = names[i] if i < len(names) else f"{ch_type.upper()}_{i}"
            plot.setLabel("left", ch_name, color="#ffffff")

            # Add curve for the data
            curve = plot.plot(
                pen=pg.mkPen(
                    color=(i * 50 % 255, 255 - i * 30 % 255, i * 20 % 255), width=1
                )
            )
            plots.append(plot)
            curves.append(curve)

            # Add quality indicator
            quality_indicator = pg.ScatterPlotItem()
            plot.addItem(quality_indicator)
            quality_indicators.append(quality_indicator)

        # Add FFT plot
        fft_plot = widget.addPlot(
            row=0, col=1, rowspan=max(1, max_channels_to_show // 2)
        )
        fft_plot.setTitle("Power Spectrum", color="#ffffff")
        fft_plot.setLabel("bottom", "Frequency", "Hz", color="#ffffff")
        fft_plot.setLabel("left", "Power", "µV²/Hz", color="#ffffff")
        fft_plot.setLogMode(x=False, y=True)

        # Dark theme styling for FFT plot
        fft_plot.getAxis("left").setPen(pg.mkPen(color="#ffffff"))
        fft_plot.getAxis("bottom").setPen(pg.mkPen(color="#ffffff"))
        fft_plot.getAxis("left").setTextPen(pg.mkPen(color="#ffffff"))
        fft_plot.getAxis("bottom").setTextPen(pg.mkPen(color="#ffffff"))

        fft_curves = []
        legend_columns = 1
        if max_channels_to_show > 8:
            legend_columns = 2
        if max_channels_to_show > 16:
            legend_columns = 3

        fft_legend = fft_plot.addLegend(offset=(-10, 10), colCount=legend_columns)

        max_fft_channels = min(max_channels_to_show, 16)
        for i in range(max_fft_channels):
            color = pg.mkPen(
                color=(i * 50 % 255, 255 - i * 30 % 255, i * 20 % 255), width=2
            )
            curve = fft_plot.plot(pen=color)
            fft_curves.append(curve)

            legend_name = names[i] if i < len(names) else f"{ch_type.upper()}_{i}"
            fft_legend.addItem(curve, legend_name)

        # Add band power plot only for EEG channels
        band_plot = None
        bar_graph = None
        bands = None
        band_ranges = None

        if ch_type == "eeg":
            band_plot = widget.addPlot(
                row=max(1, max_channels_to_show // 2),
                col=1,
                rowspan=max(1, max_channels_to_show // 2),
            )
            band_plot.setTitle("Band Powers", color="#ffffff")
            band_plot.setLabel("bottom", "Band", color="#ffffff")
            band_plot.setLabel("left", "Power", "dB", color="#ffffff")

            # Dark theme styling for band plot
            band_plot.getAxis("left").setPen(pg.mkPen(color="#ffffff"))
            band_plot.getAxis("bottom").setPen(pg.mkPen(color="#ffffff"))
            band_plot.getAxis("left").setTextPen(pg.mkPen(color="#ffffff"))
            band_plot.getAxis("bottom").setTextPen(pg.mkPen(color="#ffffff"))

            bands = ["Delta", "Theta", "Alpha", "Beta", "Gamma"]
            band_ranges = [(1, 4), (4, 8), (8, 13), (13, 30), (30, 50)]
            bar_graph = pg.BarGraphItem(
                x=range(len(bands)), height=[0] * len(bands), width=0.6, brush="#0078d4"
            )
            band_plot.addItem(bar_graph)
            band_plot.setXRange(-0.5, len(bands) - 0.5)

            ax = band_plot.getAxis("bottom")
            ax.setTicks([list(enumerate(bands))])

        # Store visualization components
        widget.plots = plots
        widget.curves = curves
        widget.quality_indicators = quality_indicators
        widget.quality_colors = quality_colors
        widget.fft_plot = fft_plot
        widget.fft_curves = fft_curves
        widget.band_plot = band_plot
        widget.bar_graph = bar_graph
        widget.bands = bands
        widget.band_ranges = band_ranges
        widget.channels = channels[
            :max_channels_to_show
        ]  # Only track channels we're actually showing
        widget.names = names
        widget.ch_type = ch_type

        return widget

    def handle_close_event(self, event: Any) -> None:
        """Handle window close event - save cache instead of destroying visualizers."""
        # Unregister from callbacks
        if hasattr(self, "local_callback_id"):
            self.data_service.unregister_local_callback(self.local_callback_id)
            logging.info("Multi-signal visualizer unregistered from local callbacks")

        self.stop()  # Stop the timer

        # CACHING: Save visualizers to cache instead of destroying them
        self._save_cached_visualizers()

        logging.info(
            "Multi-signal visualization window closed by user - visualizers cached"
        )
        event.accept()

    # Add method to properly cleanup when collector disconnects
    def cleanup_for_disconnect(self) -> None:
        """Cleanup visualizers when collector disconnects - this destroys the cache."""
        try:
            # Stop timer
            self.stop()

            # Unregister from callbacks
            if hasattr(self, "local_callback_id"):
                self.data_service.unregister_local_callback(self.local_callback_id)

            # Clear cached visualizers since collector is disconnecting
            self._clear_cache()

            # Close main widget if it exists
            if hasattr(self, "main_widget"):
                self.main_widget.close()

            logging.info("Multi-signal visualizer cleaned up for disconnect")

        except Exception as e:
            logging.error(f"Error during visualizer cleanup: {e}")

    def start(self) -> None:
        """Start updating the visualizer."""
        self.timer.start(self.update_speed_ms)
        self.main_widget.show()
        logging.info("Multi-signal visualizer started")

    def stop(self) -> None:
        """Stop updating the visualizer."""
        self.timer.stop()
        logging.info("Multi-signal visualizer stopped")

    def update_plots(self) -> None:
        """Update all plots with new data - OPTIMIZED to only update visible tab."""
        try:
            # Get data from DataAccessService
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
                    f"Expected: {expected_sample_rate} Hz | "
                    f'<span style="color:{color}">Actual: {actual_sample_rate:.1f} Hz ({efficiency:.1f}%)</span>'
                )

            # Update processing status display
            processing_status = self._get_processing_status()
            self.processing_status_label.setText(processing_status)

            if data.size == 0:
                return

            # Clean data for visualization
            data_to_plot = self._clean_data_for_visualization(data)

            # OPTIMIZATION: Only update the currently visible tab
            current_tab_widget = self.tab_widget.currentWidget()
            if current_tab_widget is not None and not isinstance(
                current_tab_widget, QtWidgets.QLabel
            ):
                # Find which visualizer corresponds to the current tab
                for ch_type, visualizer in self.visualizers.items():
                    if visualizer == current_tab_widget:
                        self._update_visualizer(visualizer, data_to_plot)
                        break

        except Exception as e:
            logging.error(f"Error updating plots: {e}")

    def _clean_data_for_visualization(self, data: np.ndarray) -> np.ndarray:
        """Clean data for stable visualization."""
        data_to_plot = data.copy()

        # Check for and clean NaN/Inf values
        if not np.isfinite(data_to_plot).all():
            logging.warning(
                "Data contains NaN/Inf values, cleaning for visualization..."
            )
            data_to_plot = np.nan_to_num(data_to_plot, nan=0.0, posinf=0.0, neginf=0.0)

        # Clean extreme outliers
        for ch_idx in range(data_to_plot.shape[0]):
            channel_data = data_to_plot[ch_idx]
            if len(channel_data) > 0:
                data_std = np.std(channel_data)
                data_mean = np.mean(channel_data)

                if np.isfinite(data_std) and data_std > 0:
                    outlier_mask = np.abs(channel_data - data_mean) > (10 * data_std)
                    if np.any(outlier_mask):
                        logging.debug(
                            f"Clipping {np.sum(outlier_mask)} outliers in channel {ch_idx}"
                        )
                        data_to_plot[ch_idx] = np.clip(
                            channel_data,
                            data_mean - 10 * data_std,
                            data_mean + 10 * data_std,
                        )

        return data_to_plot

    def _update_visualizer(
        self, visualizer: pg.GraphicsLayoutWidget, data: np.ndarray
    ) -> None:
        """Update a specific visualizer with new data."""
        try:
            channels = visualizer.channels
            ch_type = visualizer.ch_type

            # Calculate signal quality for these channels
            try:
                quality_scores = self.processor.get_all_channels_quality(data, channels)
            except Exception as e:
                logging.debug(f"Error calculating signal quality for {ch_type}: {e}")
                quality_scores = {ch: 0.5 for ch in channels}

            # Update time series plots
            for i, channel in enumerate(channels):
                if i < len(visualizer.curves) and channel < data.shape[0]:
                    try:
                        channel_data = data[channel][-self.num_points :]
                        if len(channel_data) > 0:
                            channel_data = np.asarray(channel_data).flatten()

                            if not np.isfinite(channel_data).all():
                                channel_data = np.zeros_like(channel_data)

                            if len(channel_data) > 0 and np.ptp(channel_data) == 0:
                                channel_data = channel_data + np.random.normal(
                                    0, 1e-6, len(channel_data)
                                )

                            time_vector = self.time_vector[-len(channel_data) :]
                            visualizer.curves[i].setData(time_vector, channel_data)

                            # Update quality indicator
                            quality = quality_scores.get(channel, 0)
                            if not np.isfinite(quality):
                                quality = 0.0
                            quality = max(0.0, min(1.0, quality))

                            if len(time_vector) > 0 and len(channel_data) > 0:
                                x = time_vector[-1]
                                y = channel_data[-1]

                                if np.isfinite(x) and np.isfinite(y):
                                    color_idx = min(
                                        int(quality * len(visualizer.quality_colors)),
                                        len(visualizer.quality_colors) - 1,
                                    )
                                    color_tuple = visualizer.quality_colors[color_idx]
                                    size = max(7, 12 - (quality * 5))

                                    visualizer.quality_indicators[i].setData(
                                        [x],
                                        [y],
                                        size=size,
                                        brush=pg.mkBrush(color_tuple),
                                        pxMode=True,
                                    )
                                    visualizer.quality_indicators[i].setPen(
                                        pg.mkPen("w", width=0.5)
                                    )
                    except Exception as e:
                        logging.debug(
                            f"Error plotting time series for {ch_type} channel {channel}: {e}"
                        )

            # Update FFT plots
            nfft = DataFilter.get_nearest_power_of_two(self.sampling_rate)
            for i, channel in enumerate(channels):
                if i < len(visualizer.fft_curves) and channel < data.shape[0]:
                    try:
                        channel_data = data[channel][-self.num_points :]
                        if len(channel_data) > 0:
                            channel_data = np.asarray(channel_data).flatten()

                            if not np.isfinite(channel_data).all():
                                channel_data = np.nan_to_num(
                                    channel_data, nan=0.0, posinf=0.0, neginf=0.0
                                )

                            if len(channel_data) > nfft:
                                try:
                                    actual_nfft = min(nfft, len(channel_data) // 2)
                                    actual_nfft = DataFilter.get_nearest_power_of_two(
                                        actual_nfft
                                    )

                                    psd = DataFilter.get_psd_welch(
                                        channel_data,
                                        actual_nfft,
                                        actual_nfft // 2,
                                        self.sampling_rate,
                                        WindowOperations.HANNING.value,
                                    )

                                    psd = np.asarray(psd).flatten()
                                    if not np.isfinite(psd).all():
                                        psd = np.nan_to_num(
                                            psd, nan=1e-10, posinf=1e10, neginf=1e-10
                                        )

                                    freq = np.linspace(
                                        0, self.sampling_rate / 2, len(psd)
                                    )

                                    if len(freq) == len(psd) and len(freq) > 0:
                                        visualizer.fft_curves[i].setData(freq, psd)
                                except Exception as e:
                                    logging.error(
                                        f"PSD calculation error for {ch_type} channel {channel}: {e}"
                                    )
                    except Exception as e:
                        logging.error(
                            f"Error plotting FFT for {ch_type} channel {channel}: {e}"
                        )

            # Update band powers (only for EEG)
            if (
                ch_type == "eeg"
                and visualizer.band_plot is not None
                and len(channels) > 0
            ):
                channel = channels[0]
                if channel < data.shape[0]:
                    try:
                        channel_data = data[channel][-self.num_points :]
                        if len(channel_data) > 0:
                            channel_data_flat = np.asarray(channel_data).flatten()

                            if len(channel_data_flat) > nfft:
                                single_channel_data = np.array([channel_data_flat])

                                powers = []
                                for low, high in visualizer.band_ranges:
                                    try:
                                        band_power = self.processor.get_band_power(
                                            single_channel_data, low, high
                                        )[0]
                                        power_db = 10 * np.log10(max(band_power, 1e-10))
                                        powers.append(power_db)
                                    except Exception as e:
                                        logging.error(
                                            f"Error calculating band power {low}-{high}Hz: {e}"
                                        )
                                        powers.append(-100)

                                if len(powers) == len(visualizer.bands):
                                    visualizer.bar_graph.setOpts(height=powers)
                    except Exception as e:
                        logging.error(f"Error plotting band powers for {ch_type}: {e}")

        except Exception as e:
            logging.error(f"Error updating {ch_type} visualizer: {e}")

    def set_frequency_range(self, min_freq: float, max_freq: float) -> None:
        """Set the frequency range for all FFT plots."""
        for visualizer in self.visualizers.values():
            if hasattr(visualizer, "fft_plot"):
                visualizer.fft_plot.setXRange(min_freq, max_freq)

    def set_log_mode(self, use_log: bool) -> None:
        """Set whether to use logarithmic scale for power spectrum."""
        for visualizer in self.visualizers.values():
            if hasattr(visualizer, "fft_plot"):
                visualizer.fft_plot.setLogMode(x=False, y=use_log)

    def is_visible(self) -> bool:
        """Check if the visualization window is visible."""
        return self.main_widget.isVisible()

    def _get_processing_status(self) -> str:
        """Get current processing status for display."""
        try:
            # Check advanced processing settings
            advanced_settings = getattr(
                self.data_service, "_advanced_processing_settings", {}
            )
            status_parts = []

            # Check for wavelet processing
            if advanced_settings.get("wavelet", {}).get("inverse_enabled", False):
                target_channel = getattr(
                    self.data_service, "_wavelet_target_channel", 0
                )
                wavelet_metadata = getattr(self.data_service, "_wavelet_metadata", {})
                wavelet_type = wavelet_metadata.get("wavelet", "Unknown")
                decomp_level = wavelet_metadata.get("decomposition_level", 0)

                channel_names = self.data_service.get_channel_names()
                channel_name = (
                    channel_names[target_channel]
                    if target_channel < len(channel_names)
                    else f"CH{target_channel}"
                )

                status_parts.append(
                    f'<span style="color: #4CAF50;">Wavelet({wavelet_type}, L{decomp_level}) → {channel_name}</span>'
                )

            # Check for advanced filters
            if advanced_settings.get("advanced_filters", {}).get("enabled", False):
                filter_info = advanced_settings["advanced_filters"]
                filter_type = str(filter_info.get("filter_type", "Unknown")).split(".")[
                    -1
                ]
                channels = filter_info.get("selected_channels", [])
                channel_info = (
                    f"{len(channels)} channels" if channels else "all channels"
                )
                status_parts.append(
                    f'<span style="color: #FF9800;">AdvFilter({filter_type}) → {channel_info}</span>'
                )

            # Check for downsampling
            if advanced_settings.get("downsampling", {}).get("enabled", False):
                ds_info = advanced_settings["downsampling"]
                factor = ds_info.get("factor", 1)
                status_parts.append(
                    f'<span style="color: #2196F3;">Downsample(÷{factor})</span>'
                )

            # Check basic filters
            if getattr(self.data_service, "_filters_enabled", False):
                filter_settings = getattr(self.data_service, "_filter_settings", {})
                basic_parts = []

                if filter_settings.get("bandpass", {}).get("enabled", False):
                    bp = filter_settings["bandpass"]
                    low = bp.get("low_cut", bp.get("low", 0))
                    high = bp.get("high_cut", bp.get("high", 0))
                    basic_parts.append(f"BP({low:.0f}-{high:.0f}Hz)")

                if filter_settings.get("notch", {}).get("enabled", False):
                    notch = filter_settings["notch"]
                    freq = notch.get("frequency", 50)
                    basic_parts.append(f"Notch({freq}Hz)")

                if filter_settings.get("detrend", False):
                    basic_parts.append("Detrend")

                if basic_parts:
                    status_parts.append(
                        f'<span style="color: #9C27B0;">{", ".join(basic_parts)}</span>'
                    )

            if status_parts:
                return f"Processing: {' | '.join(status_parts)}"
            else:
                return "Processing: None Active"

        except Exception as e:
            logging.debug(f"Error getting processing status: {e}")
            return "Processing: Status Unknown"
