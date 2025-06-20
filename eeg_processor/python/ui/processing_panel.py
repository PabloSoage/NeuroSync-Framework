import logging
from typing import Any, Optional, Dict

from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
)

from .base_panel import BasePanel
from ..utils.help_system import HelpButton


class ApiEventHandler(QObject):
    """Thread-safe handler for API events."""

    filter_apply_signal = pyqtSignal(dict, bool)

    def __init__(self):
        super().__init__()


class ProcessingPanel(BasePanel):
    """Panel for signal processing operations."""

    def __init__(
        self,
        collector_service: Any,
        processor_service: Any,
        visualization_service: Any,
        parent: Optional[Any] = None,
    ) -> None:
        """Initialize the processing panel."""
        super().__init__(parent)
        self.collector_service = collector_service
        self.processor_service = processor_service
        self.visualization_service = visualization_service

        # Add state tracking for filters
        self.filters_applied = False

        # Get DataAccessService instance for filter configuration
        from ..services.data_access_service import DataAccessService

        self.data_access_service = DataAccessService.get_instance()

        # Set processor service in data access service for filtering
        self.data_access_service.set_filter_processor(self.processor_service)

        # Setup thread-safe event handler
        self.api_event_handler = ApiEventHandler()
        self.api_event_handler.filter_apply_signal.connect(
            self._handle_api_filter_apply_safe
        )

        # Setup event system subscriptions for API synchronization
        self._setup_event_subscriptions()

        # Setup UI components
        self.setup_filter_options()
        self.setup_metrics_section()
        self.setup_brain_map_section()

        # Add stretch to push everything to the top
        self.layout.addStretch()

    def _setup_event_subscriptions(self) -> None:
        """Setup subscriptions for API-generated events."""
        try:
            from ..core.event_system import EventDispatcher, EventType

            event_dispatcher = EventDispatcher.get_instance()

            # Subscribe to filter events from API
            event_dispatcher.subscribe(
                EventType.FILTER_APPLY, self._handle_api_filter_apply_thread_safe
            )

        except Exception as e:
            logging.error(
                f"Error setting up event subscriptions in processing panel: {e}"
            )

    def _handle_api_filter_apply_thread_safe(self, event: Any) -> None:
        """Handle filter apply events from API in a thread-safe way."""
        try:
            filter_config = event.data.get("filter_config", {})
            applied_to_viz = event.data.get("applied_to_visualization", True)

            logging.info(
                f"Processing panel received API filter event: config={filter_config}, apply_to_viz={applied_to_viz}"
            )

            # Emit signal to handle in main thread
            self.api_event_handler.filter_apply_signal.emit(
                filter_config, applied_to_viz
            )

        except Exception as e:
            logging.error(f"Error handling API filter apply event thread-safe: {e}")

    def _handle_api_filter_apply_safe(
        self, filter_config: Dict[str, Any], applied_to_visualization: bool
    ) -> None:
        """Handle filter apply events from API safely in main thread."""
        try:
            logging.info(
                f"Processing panel updating controls: config={filter_config}, apply_to_viz={applied_to_visualization}"
            )

            # Update the UI controls to reflect the API settings
            self._update_filter_controls_from_api(
                filter_config, applied_to_visualization
            )

        except Exception as e:
            logging.error(f"Error handling API filter apply event safely: {e}")

    def _update_filter_controls_from_api(
        self, filter_config: Dict[str, Any], applied_to_visualization: bool
    ) -> None:
        """Update filter controls based on API filter configuration."""
        try:
            # Temporarily disconnect signals to prevent recursive updates
            self._disconnect_filter_signals()

            # Update bandpass filter controls
            if "bandpass" in filter_config:
                bp_config = filter_config["bandpass"]
                self.bandpass_check.setChecked(bp_config.get("enabled", False))
                if "low_cut" in bp_config:
                    self.bandpass_low_spin.setValue(bp_config["low_cut"])
                elif "low" in bp_config:
                    self.bandpass_low_spin.setValue(bp_config["low"])
                if "high_cut" in bp_config:
                    self.bandpass_high_spin.setValue(bp_config["high_cut"])
                elif "high" in bp_config:
                    self.bandpass_high_spin.setValue(bp_config["high"])

            # Update notch filter controls
            if "notch" in filter_config:
                notch_config = filter_config["notch"]
                self.notch_check.setChecked(notch_config.get("enabled", False))
                if "frequency" in notch_config:
                    # Find and select the appropriate frequency
                    freq = str(int(notch_config["frequency"]))
                    for i in range(self.notch_type_combo.count()):
                        if self.notch_type_combo.itemData(i) == freq:
                            self.notch_type_combo.setCurrentIndex(i)
                            break

            # Update detrend controls
            if "detrend" in filter_config:
                self.detrend_check.setChecked(filter_config["detrend"])

            # Update button state based on whether filters were applied to visualization
            if applied_to_visualization:
                self.filters_applied = True
                self.apply_filters_btn.setText("Remove Filters from Visualization")
                self.apply_filters_btn.setStyleSheet(
                    "background-color: #AA3333; color: white;"
                )
                self.show_status("Filters applied via API")
            else:
                self.filters_applied = False
                self.apply_filters_btn.setText("Apply Filters to Visualization")
                self.apply_filters_btn.setStyleSheet("")
                self.show_status("Filters applied via API")

            # Reconnect signals
            self._connect_filter_signals()

        except Exception as e:
            logging.error(f"Error updating filter controls from API: {e}")
            # Always reconnect signals even if there was an error
            self._connect_filter_signals()

    def _disconnect_filter_signals(self) -> None:
        """Temporarily disconnect filter signals to prevent recursive updates."""
        try:
            self.bandpass_check.toggled.disconnect(self.on_filter_option_changed)
            self.bandpass_low_spin.valueChanged.disconnect(
                self.on_filter_option_changed
            )
            self.bandpass_high_spin.valueChanged.disconnect(
                self.on_filter_option_changed
            )
            self.notch_check.toggled.disconnect(self.on_filter_option_changed)
            self.notch_type_combo.currentIndexChanged.disconnect(
                self.on_filter_option_changed
            )
            self.detrend_check.toggled.disconnect(self.on_filter_option_changed)
        except Exception:
            pass  # Signals might not be connected yet

    def _connect_filter_signals(self) -> None:
        """Reconnect filter signals."""
        try:
            self.bandpass_check.toggled.connect(self.on_filter_option_changed)
            self.bandpass_low_spin.valueChanged.connect(self.on_filter_option_changed)
            self.bandpass_high_spin.valueChanged.connect(self.on_filter_option_changed)
            self.notch_check.toggled.connect(self.on_filter_option_changed)
            self.notch_type_combo.currentIndexChanged.connect(
                self.on_filter_option_changed
            )
            self.detrend_check.toggled.connect(self.on_filter_option_changed)
        except Exception as e:
            logging.error(f"Error reconnecting filter signals: {e}")

    def setup_filter_options(self) -> None:
        """Set up filtering options group."""
        filter_group = QGroupBox("Filtering Options")
        filter_layout = QVBoxLayout(filter_group)

        # Bandpass filter
        bandpass_layout = QHBoxLayout()
        self.bandpass_check = QCheckBox("Bandpass Filter")
        self.bandpass_check.setChecked(True)

        bandpass_low_label = QLabel("Low Cut:")
        self.bandpass_low_spin = QDoubleSpinBox()
        self.bandpass_low_spin.setRange(0.1, 100.0)
        self.bandpass_low_spin.setValue(1.0)
        self.bandpass_low_spin.setSuffix(" Hz")

        bandpass_high_label = QLabel("High Cut:")
        self.bandpass_high_spin = QDoubleSpinBox()
        self.bandpass_high_spin.setRange(0.1, 200.0)
        self.bandpass_high_spin.setValue(50.0)
        self.bandpass_high_spin.setSuffix(" Hz")

        bandpass_layout.addWidget(self.bandpass_check)
        bandpass_layout.addWidget(bandpass_low_label)
        bandpass_layout.addWidget(self.bandpass_low_spin)
        bandpass_layout.addWidget(bandpass_high_label)
        bandpass_layout.addWidget(self.bandpass_high_spin)
        bandpass_layout.addWidget(HelpButton("bandpass_filter", self))
        filter_layout.addLayout(bandpass_layout)

        # Notch filter
        notch_layout = QHBoxLayout()
        self.notch_check = QCheckBox("Notch Filter")
        self.notch_check.setChecked(True)

        notch_type_label = QLabel("Type:")
        self.notch_type_combo = QComboBox()
        self.notch_type_combo.addItem("50 Hz", "50")
        self.notch_type_combo.addItem("60 Hz", "60")

        notch_layout.addWidget(self.notch_check)
        notch_layout.addWidget(notch_type_label)
        notch_layout.addWidget(self.notch_type_combo)
        notch_layout.addWidget(HelpButton("notch_filter", self))
        filter_layout.addLayout(notch_layout)

        # Detrend
        detrend_layout = QHBoxLayout()
        self.detrend_check = QCheckBox("Detrend")
        self.detrend_check.setChecked(True)
        detrend_layout.addWidget(self.detrend_check)
        detrend_layout.addWidget(HelpButton("detrend", self))
        filter_layout.addLayout(detrend_layout)

        # Apply filter button
        apply_layout = QHBoxLayout()
        self.apply_filters_btn = QPushButton("Apply Filters to Visualization")
        self.apply_filters_btn.clicked.connect(self.apply_filters)
        self.apply_filters_btn.setEnabled(False)
        apply_layout.addWidget(self.apply_filters_btn)
        filter_layout.addLayout(apply_layout)

        self.layout.addWidget(filter_group)

        # Connect filter signals AFTER all controls are created
        self._connect_filter_signals()

    def setup_metrics_section(self) -> None:
        """Set up EEG metrics section."""
        metrics_group = QGroupBox("EEG Metrics")
        metrics_layout = QVBoxLayout(metrics_group)

        # Add help for metrics
        metrics_header_layout = QHBoxLayout()
        metrics_header_layout.addWidget(QLabel("EEG Metrics Analysis"))
        metrics_header_layout.addWidget(HelpButton("eeg_basics", self))
        metrics_header_layout.addStretch()
        metrics_layout.addLayout(metrics_header_layout)

        # Add calculate button
        metrics_update_layout = QHBoxLayout()
        self.calculate_metrics_btn = QPushButton("Calculate Metrics")
        self.calculate_metrics_btn.clicked.connect(self.calculate_metrics)
        self.calculate_metrics_btn.setEnabled(False)
        metrics_update_layout.addWidget(self.calculate_metrics_btn)
        metrics_layout.addLayout(metrics_update_layout)

        # Metrics display
        self.metrics_label = QLabel("No metrics calculated")
        metrics_layout.addWidget(self.metrics_label)

        self.layout.addWidget(metrics_group)

    def setup_brain_map_section(self) -> None:
        """Set up brain map visualization section."""
        # Add brain map button
        brain_map_layout = QHBoxLayout()
        self.brain_map_btn = QPushButton("Show Brain Map Visualization")
        self.brain_map_btn.clicked.connect(self.show_brain_map)
        self.brain_map_btn.setEnabled(False)
        brain_map_layout.addWidget(self.brain_map_btn)
        brain_map_layout.addWidget(HelpButton("brain_map", self))

        self.layout.addLayout(brain_map_layout)

        # Setup timer to check brain map status
        self.brain_map_timer = QTimer(self)
        self.brain_map_timer.timeout.connect(self.check_brain_map_status)
        self.brain_map_timer.start(1000)  # Check every second

    def check_brain_map_status(self) -> None:
        """Check if brain map visualizer needs to be restarted."""
        # Only enable the button when streaming and brain map was closed
        if (
            hasattr(self.visualization_service, "brain_map_closed")
            and self.visualization_service.brain_map_closed()
        ):
            self.brain_map_btn.setText("Reopen Brain Map Visualization")
            self.brain_map_btn.setEnabled(True)
        elif (
            not self.visualization_service.brain_map_visible()
            and hasattr(self, "processing_enabled")
            and self.processing_enabled
        ):
            # Processing is enabled but brain map is not visible and wasn't explicitly closed
            self.brain_map_btn.setText("Show Brain Map Visualization")
            self.brain_map_btn.setEnabled(True)

    def apply_filters(self) -> None:
        """Apply or remove the selected filters to visualization and data access."""
        try:
            if not self.filters_applied:
                # Get current filter settings
                filter_settings = self.get_filter_settings()

                # Get EEG channels to show what will be filtered
                try:
                    metadata = self.data_access_service.get_metadata()
                    eeg_channels = metadata.get("eeg_channels", [])
                    channel_names = metadata.get("channel_names", [])

                    if eeg_channels:
                        # Create readable channel list
                        eeg_channel_names = []
                        for i, ch_idx in enumerate(eeg_channels):
                            if i < len(channel_names):
                                eeg_channel_names.append(
                                    f"{channel_names[i]} (CH{ch_idx})"
                                )
                            else:
                                eeg_channel_names.append(f"CH{ch_idx}")

                        logging.info(
                            f"Applying filters to EEG channels only: {', '.join(eeg_channel_names)}"
                        )
                    else:
                        logging.warning(
                            "No EEG channels found - filters may not be applied correctly"
                        )

                except Exception as e:
                    logging.debug(f"Could not get channel info: {e}")

                # Apply filters to visualization
                self.visualization_service.set_bandpass_filter(
                    self.bandpass_check.isChecked(),
                    self.bandpass_low_spin.value(),
                    self.bandpass_high_spin.value(),
                )

                self.visualization_service.set_notch_filter(
                    self.notch_check.isChecked(),
                    float(self.notch_type_combo.currentData()),
                )

                self.visualization_service.set_detrend(self.detrend_check.isChecked())

                # Apply filters to data access service (for MNE and other consumers)
                self.data_access_service.enable_filters(True, filter_settings)

                # Force update all current data through filters
                current_data, current_timestamps = (
                    self.data_access_service.get_raw_data()
                )
                if current_data.size > 0:
                    logging.info(
                        f"Applying filters to existing data buffer of {current_data.shape}"
                    )
                    self.data_access_service.update_data(
                        current_data, current_timestamps
                    )

                # Update button state
                self.filters_applied = True
                self.apply_filters_btn.setText("Remove Filters from Visualization")
                self.apply_filters_btn.setStyleSheet(
                    "background-color: #AA3333; color: white;"
                )

                # More informative status message
                if eeg_channels:
                    self.show_status(
                        f"Filters applied to {len(eeg_channels)} EEG channels only "
                        f"(Timestamp, Markers, Accel, Gyro, etc. preserved)"
                    )
                else:
                    self.show_status(
                        "Filters applied - Note: No EEG channels detected, filters may not work correctly"
                    )
            else:
                # Remove filters from visualization
                self.visualization_service.set_bandpass_filter(False, 1.0, 50.0)
                self.visualization_service.set_notch_filter(False)
                self.visualization_service.set_detrend(False)

                # Disable filters in data access service
                self.data_access_service.enable_filters(False)

                # Update button state
                self.filters_applied = False
                self.apply_filters_btn.setText("Apply Filters to Visualization")
                self.apply_filters_btn.setStyleSheet("")
                self.show_status(
                    "Filters removed from all consumers (visualization, MNE, WebSocket)"
                )

        except Exception as e:
            self.show_error("Filter Error", f"Error applying filters: {str(e)}")

    def on_filter_option_changed(self) -> None:
        """Update filters dynamically when options change and filters are applied."""
        # Only update if filters are already applied
        if hasattr(self, "filters_applied") and self.filters_applied:
            try:
                # Get current filter settings
                filter_settings = self.get_filter_settings()

                # Validate frequency settings
                low_cut = self.bandpass_low_spin.value()
                high_cut = self.bandpass_high_spin.value()

                # Get sampling rate to validate frequencies
                sampling_rate = self.collector_service.get_sampling_rate()
                if sampling_rate > 0:
                    nyquist = sampling_rate / 2

                    # Ensure frequencies are valid
                    if high_cut >= nyquist:
                        high_cut = nyquist * 0.95  # Set to 95% of Nyquist
                        self.bandpass_high_spin.setValue(high_cut)
                        self.show_status(
                            f"High cut frequency adjusted to {high_cut:.1f} Hz (below Nyquist frequency)"
                        )

                    if low_cut >= high_cut:
                        low_cut = high_cut * 0.1  # Set to 10% of high cut
                        self.bandpass_low_spin.setValue(low_cut)
                        self.show_status(
                            f"Low cut frequency adjusted to {low_cut:.1f} Hz"
                        )

                # Apply the same filters as in apply_filters, but without changing button state
                self.visualization_service.set_bandpass_filter(
                    self.bandpass_check.isChecked(),
                    self.bandpass_low_spin.value(),
                    self.bandpass_high_spin.value(),
                )

                self.visualization_service.set_notch_filter(
                    self.notch_check.isChecked(),
                    float(self.notch_type_combo.currentData()),
                )

                self.visualization_service.set_detrend(self.detrend_check.isChecked())

                # Update filters in data access service
                self.data_access_service.update_filter_settings(filter_settings)

                self.show_status("Filters updated dynamically")
            except Exception as e:
                self.show_error("Filter Error", f"Error updating filters: {str(e)}")

    def calculate_metrics(self) -> None:
        """Calculate EEG metrics from current data."""
        try:
            # Get data from collector service
            sampling_rate = self.collector_service.get_sampling_rate()
            if sampling_rate <= 0:
                self.show_error("Metrics Error", "Invalid sampling rate")
                return

            # Calculate metrics
            metrics = self.processor_service.get_eeg_metrics(data, eeg_channels)

            # Format and display metrics
            metrics_text = ""
            for name, value in metrics.items():
                # Handle numpy arrays by taking first value
                if hasattr(value, "__iter__"):
                    value = value[0]
                metrics_text += f"{name.capitalize()}: {value:.2f}\n"

            self.metrics_label.setText(metrics_text)
            self.show_status("EEG metrics calculated")
        except Exception as e:
            self.show_error("Metrics Error", f"Failed to calculate metrics: {str(e)}")

    def show_brain_map(self) -> None:
        """Show brain map visualization."""
        try:
            # Make sure processor is initialized before creating brain map
            sampling_rate = self.collector_service.get_sampling_rate()
            if sampling_rate <= 0:
                self.show_error("Visualization Error", "Invalid sampling rate")
                return

            # Initialize processor if not already done
            if (
                not hasattr(self.processor_service, "processor")
                or self.processor_service.processor is None
            ):
                self.processor_service.initialize_processor(sampling_rate)
                self.show_status(
                    f"Initialized processor with sampling rate {sampling_rate} Hz"
                )

            # Now create brain map visualizer with initialized processor
            success = self.visualization_service.create_brain_map_visualizer(
                self.collector_service.collector, self.processor_service.processor
            )

            if success:
                self.visualization_service.start_brain_map_visualization()
                self.show_status("Brain map visualization started")
            else:
                self.show_error(
                    "Visualization Error", "Failed to create brain map visualizer"
                )
        except Exception as e:
            self.show_error("Visualization Error", f"Error showing brain map: {e}")

    def enable_processing(self, enabled: bool) -> None:
        """Enable or disable processing controls."""
        self.processing_enabled = enabled  # Store the state for brain map checks
        self.apply_filters_btn.setEnabled(enabled)

        # Reset filters state when processing is disabled
        if not enabled and self.filters_applied:
            self.filters_applied = False
            self.apply_filters_btn.setText("Apply Filters to Visualization")
            self.apply_filters_btn.setStyleSheet("")

        self.calculate_metrics_btn.setEnabled(enabled)

        # Only enable brain map button if we're not already showing it
        if (
            not hasattr(self.visualization_service, "brain_map_visible")
            or not self.visualization_service.brain_map_visible()
        ):
            self.brain_map_btn.setEnabled(enabled)

    # Add methods for API interaction
    def _update_filter_controls(self, filter_config: Dict[str, Any]) -> bool:
        """Update filter controls from API call."""
        try:
            # Update bandpass filter controls
            if "bandpass" in filter_config:
                bp_config = filter_config["bandpass"]
                self.bandpass_check.setChecked(bp_config.get("enabled", False))
                if "low_cut" in bp_config:
                    self.bandpass_low_spin.setValue(bp_config["low_cut"])
                if "high_cut" in bp_config:
                    self.bandpass_high_spin.setValue(bp_config["high_cut"])

            # Update notch filter controls
            if "notch" in filter_config:
                notch_config = filter_config["notch"]
                self.notch_check.setChecked(notch_config.get("enabled", False))
                if "frequency" in notch_config:
                    # Find and select the appropriate frequency
                    freq = str(notch_config["frequency"])
                    for i in range(self.notch_type_combo.count()):
                        if self.notch_type_combo.itemData(i) == freq:
                            self.notch_type_combo.setCurrentIndex(i)
                            break

            # Update detrend controls
            if "detrend" in filter_config:
                self.detrend_check.setChecked(filter_config["detrend"])

            # Update button state if filters are applied
            if filter_config.get("applied", False):
                self.filters_applied = True
                self.apply_filters_btn.setText("Remove Filters from Visualization")
                self.apply_filters_btn.setStyleSheet(
                    "background-color: #AA3333; color: white;"
                )
            else:
                self.filters_applied = False
                self.apply_filters_btn.setText("Apply Filters to Visualization")
                self.apply_filters_btn.setStyleSheet("")

            return True
        except Exception as e:
            self.show_error("Filter Controls Update Error", str(e))
            return False

    def get_filter_settings(self) -> Dict[str, Any]:
        """Get current filter settings."""
        return {
            "bandpass": {
                "enabled": self.bandpass_check.isChecked(),
                "low_cut": self.bandpass_low_spin.value(),
                "high_cut": self.bandpass_high_spin.value(),
                "low": self.bandpass_low_spin.value(),  # For backward compatibility
                "high": self.bandpass_high_spin.value(),  # For backward compatibility
            },
            "notch": {
                "enabled": self.notch_check.isChecked(),
                "frequency": float(self.notch_type_combo.currentData()),
            },
            "detrend": self.detrend_check.isChecked(),
            "applied": self.filters_applied,
        }

    def update_metrics_display(self, metrics_text: str) -> bool:
        """Update the metrics display from API call."""
        try:
            self.metrics_label.setText(metrics_text)
            return True
        except Exception as e:
            self.show_error("Metrics Update Error", str(e))
            return False
