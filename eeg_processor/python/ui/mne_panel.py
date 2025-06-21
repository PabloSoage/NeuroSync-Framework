import logging
from typing import Any, Optional, Dict, List

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QCloseEvent

from .base_panel import BasePanel
from .mne.mne_panel_controller import MNEPanelController
from .mne.widgets.mne_conversion_widget import MNEConversionWidget
from .mne.widgets.mne_status_widget import MNEStatusWidget
from .mne.widgets.mne_visualization_widget import MNEVisualizationWidget
from ..services.mne_service import MNEService

# Check if MNE is available
try:
    import mne

    MNE_AVAILABLE = True
except ImportError:
    MNE_AVAILABLE = False

class MNEApiEventHandler(QObject):
    """Thread-safe handler for MNE API events."""

    convert_signal = pyqtSignal(int, bool)  # duration, use_filters
    plot_signal = pyqtSignal(dict)  # plot parameters
    select_channels_signal = pyqtSignal(list)  # channel_indices

    def __init__(self):
        super().__init__()

class MNEPanel(BasePanel):
    """
    Panel for MNE integration and analysis.
    """

    def __init__(
        self,
        collector_service: Any,
        processor_service: Any,
        parent: Optional[Any] = None,
        visualization_service: Optional[Any] = None,
    ) -> None:
        """Initialize the MNE panel."""
        super().__init__(parent)

        # Store service references for compatibility
        self.collector_service = collector_service
        self.processor_service = processor_service
        self.visualization_service = visualization_service

        # Get MNE service
        self.mne_service = MNEService.get_instance()

        if self.mne_service.is_available():
            self._setup_mne_panel()
            self.mne_service.start_service()
            self._setup_api_event_subscriptions()
        else:
            self._setup_mne_not_available()

        # Add stretch to push everything to the top
        self.layout.addStretch()

    def _setup_mne_panel(self) -> None:
        """Setup the MNE panel with widgets and controller."""
        # Create specialized widgets
        self.conversion_widget = MNEConversionWidget()
        self.visualization_widget = MNEVisualizationWidget()
        self.status_widget = MNEStatusWidget()

        # Setup API event handler
        self.api_event_handler = MNEApiEventHandler()
        self.api_event_handler.convert_signal.connect(self._handle_api_convert_safe)
        self.api_event_handler.plot_signal.connect(self._handle_api_plot_safe)
        self.api_event_handler.select_channels_signal.connect(self._handle_api_select_channels_safe)

        # Create controller to coordinate widgets
        self.controller = MNEPanelController(
            self.conversion_widget,
            self.visualization_widget,
            self.status_widget,
            parent=self,
            visualization_service=self.visualization_service,
        )

        # Connect controller signals to panel signals
        self.controller.status_message.connect(self.status_message.emit)
        self.controller.error_message.connect(self.error_message.emit)

        # Add widgets to layout
        self.layout.addWidget(self.conversion_widget)
        self.layout.addWidget(self.visualization_widget)
        self.layout.addWidget(self.status_widget)

    def _setup_mne_not_available(self) -> None:
        """Show warning when MNE is not installed."""
        from PyQt5.QtWidgets import QLabel

        warning_label = QLabel(
            "MNE package is not installed. Please install it using: pip install mne"
        )
        warning_label.setStyleSheet("color: #FFAA33; font-weight: bold;")
        self.layout.addWidget(warning_label)

    def enable_processing(self, enabled: bool) -> None:
        """Enable or disable MNE processing controls."""
        if hasattr(self, "controller"):
            self.controller.enable_processing(enabled)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle panel close event."""
        if hasattr(self, "controller"):
            self.controller.cleanup()
        super().closeEvent(event)

    # API compatibility methods
    def get_mne_settings(self) -> Dict[str, Any]:
        """Get current MNE settings for API compatibility."""
        if not hasattr(self, "controller"):
            return {"available": False}

        # Delegate to widgets through controller
        conversion_params = self.conversion_widget.get_conversion_parameters()
        visualization_params = self.visualization_widget.get_visualization_parameters()

        return {
            "available": True,
            "duration": conversion_params["duration_seconds"],
            "convert_to_v": conversion_params["convert_to_v"],
            "conversion_mode": conversion_params["mode"],
            "plot_type": visualization_params["plot_type"],
            "freq_range": [
                visualization_params["freq_min"],
                visualization_params["freq_max"],
            ],
            "topomap_freq_range": list(visualization_params["topomap_freq_range"]),
            "psd_individual_mode": visualization_params["show_individual_channels"],
        }

    def update_mne_plot(self, plot_data: Dict[str, Any]) -> bool:
        """Update MNE plot from API call."""
        if not hasattr(self, "controller"):
            return False

        try:
            plot_type = plot_data.get("type", "psd")

            if plot_type.lower() in ["psd", "topomap", "raw data", "spectrogram"]:
                # Set the combo box in visualization widget
                combo = self.visualization_widget.plot_type_combo
                index = combo.findText(plot_type.title())
                if index >= 0:
                    combo.setCurrentIndex(index)

                # Trigger visualization through controller
                params = self.visualization_widget.get_visualization_parameters()
                self.controller._handle_visualization_request(params)
                return True

            return False

        except Exception as e:
            self.show_error("MNE Plot Update Error", str(e))
            return False

    def _setup_api_event_subscriptions(self) -> None:
        """Setup subscriptions for API-generated MNE events."""
        try:
            from ..core.event_system import EventDispatcher, EventType

            event_dispatcher = EventDispatcher.get_instance()

            # Subscribe to MNE events
            event_dispatcher.subscribe(
                EventType.MNE_CONVERT, self._handle_api_convert_thread_safe
            )
            event_dispatcher.subscribe(
                EventType.MNE_PLOT, self._handle_api_plot_thread_safe
            )
            event_dispatcher.subscribe(
                EventType.MNE_SELECT_CHANNELS, self._handle_api_select_channels_thread_safe
            )

        except Exception as e:
            logging.error(f"Error setting up MNE API event subscriptions: {e}")

    def _handle_api_convert_thread_safe(self, event: Any) -> None:
        """Handle MNE convert events from API in a thread-safe way."""
        try:
            data = event.data
            duration = data.get("duration", 5)
            use_filters = data.get("use_filters", True)

            logging.info(f"API MNE convert event received: duration={duration}, use_filters={use_filters}")

            self.api_event_handler.convert_signal.emit(duration, use_filters)
        except Exception as e:
            logging.error(f"Error handling API MNE convert event: {e}")

    def _handle_api_plot_thread_safe(self, event: Any) -> None:
        """Handle MNE plot events from API in a thread-safe way."""
        try:
            data = event.data

            logging.info(f"API MNE plot event received: {data}")

            self.api_event_handler.plot_signal.emit(data)
        except Exception as e:
            logging.error(f"Error handling API MNE plot event: {e}")

    def _handle_api_select_channels_thread_safe(self, event: Any) -> None:
        """Handle MNE channel selection events from API in a thread-safe way."""
        try:
            data = event.data
            channel_indices = data.get("channel_indices", [])

            logging.info(f"API MNE select channels event received: {len(channel_indices)} channels")

            self.api_event_handler.select_channels_signal.emit(channel_indices)
        except Exception as e:
            logging.error(f"Error handling API MNE select channels event: {e}")

    def _handle_api_convert_safe(self, duration: int, use_filters: bool) -> None:
        """Handle MNE convert from API safely in main thread."""
        try:
            # Validate duration
            if duration < 1 or duration > 60:
                logging.error(f"Invalid duration received: {duration}, using default 5")
                duration = 5

            logging.info(f"API MNE convert: duration={duration}, use_filters={use_filters}")

            # Update conversion widget settings
            self.conversion_widget.duration_spin.blockSignals(True)
            self.conversion_widget.duration_spin.setValue(duration)
            self.conversion_widget.duration_spin.blockSignals(False)

            if hasattr(self.conversion_widget, 'use_filters_check'):
                self.conversion_widget.use_filters_check.blockSignals(True)
                self.conversion_widget.use_filters_check.setChecked(use_filters)
                self.conversion_widget.use_filters_check.blockSignals(False)

            # Trigger conversion through controller
            params = self.conversion_widget.get_conversion_parameters()
            logging.info(f"Triggering MNE conversion with params: {params}")
            self.controller._handle_conversion_request(params)

        except Exception as e:
            logging.error(f"Error in API MNE convert handler: {e}")
            self.controller._show_error("API MNE Error", f"Error processing convert request: {str(e)}")

    def _handle_api_plot_safe(self, plot_params: Dict[str, Any]) -> None:
        """Handle MNE plot from API safely in main thread."""
        try:
            plot_type = plot_params.get("plot_type", "PSD")
            freq_min = plot_params.get("freq_min", 1)
            freq_max = plot_params.get("freq_max", 50)
            topomap_band = plot_params.get("topomap_band", "Alpha (8-13 Hz)")
            topomap_freq_min = plot_params.get("topomap_freq_min", 8)
            topomap_freq_max = plot_params.get("topomap_freq_max", 13)
            psd_individual_mode = plot_params.get("psd_individual_mode", True)
            selected_channels = plot_params.get("selected_channels", [])

            logging.info(
                f"API MNE plot: type={plot_type}, freq={freq_min}-{freq_max}, channels={len(selected_channels)}")

            # Update visualization widget settings
            viz_widget = self.visualization_widget

            # Update plot type
            plot_combo = viz_widget.plot_type_combo
            plot_combo.blockSignals(True)
            index = plot_combo.findText(plot_type)
            if index >= 0:
                plot_combo.setCurrentIndex(index)
            plot_combo.blockSignals(False)

            # Update frequency range
            viz_widget.freq_min_spin.blockSignals(True)
            viz_widget.freq_min_spin.setValue(freq_min)
            viz_widget.freq_min_spin.blockSignals(False)

            viz_widget.freq_max_spin.blockSignals(True)
            viz_widget.freq_max_spin.setValue(freq_max)
            viz_widget.freq_max_spin.blockSignals(False)

            # Update topomap band
            topomap_combo = viz_widget.topomap_band_combo
            topomap_combo.blockSignals(True)

            # Check if it's a custom range
            if "Custom" in topomap_band or (topomap_freq_min != 8 or topomap_freq_max != 13):
                # Set to custom and show custom controls
                custom_index = topomap_combo.findText("Custom Range")
                if custom_index >= 0:
                    topomap_combo.setCurrentIndex(custom_index)
                    viz_widget.topomap_freq_min_spin.setValue(topomap_freq_min)
                    viz_widget.topomap_freq_max_spin.setValue(topomap_freq_max)
                    viz_widget._on_topomap_band_changed()  # Show custom controls
            else:
                # Try to find matching predefined band
                band_index = topomap_combo.findText(topomap_band)
                if band_index >= 0:
                    topomap_combo.setCurrentIndex(band_index)

            topomap_combo.blockSignals(False)

            # Update PSD mode
            viz_widget.psd_individual_check.blockSignals(True)
            viz_widget.psd_individual_check.setChecked(psd_individual_mode)
            viz_widget.psd_individual_check.blockSignals(False)
            viz_widget._update_psd_mode_info()

            # Update channel selection
            if selected_channels:
                # Validate channel indices
                valid_channels = []
                for ch in selected_channels:
                    if isinstance(ch, int) and 0 <= ch < len(self.controller.channel_names):
                        valid_channels.append(ch)

                self.controller.selected_channels = valid_channels
                self.controller._update_channel_displays()
                logging.info(f"Updated selected channels: {len(valid_channels)} channels")
            else:
                # Use all channels
                self.controller.selected_channels = list(range(len(self.controller.channel_names)))
                self.controller._update_channel_displays()
                logging.info("Using all channels (none specified)")

            # Trigger visualization through controller
            params = viz_widget.get_visualization_parameters()
            logging.info(f"Triggering MNE visualization with params: {params}")
            self.controller._handle_visualization_request(params)

        except Exception as e:
            logging.error(f"Error in API MNE plot handler: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            self.controller._show_error("API MNE Error", f"Error processing plot request: {str(e)}")

    def _handle_api_select_channels_safe(self, channel_indices: List[int]) -> None:
        """Handle MNE channel selection from API safely in main thread."""
        try:
            # Si channel_indices está vacío, seleccionar todos los canales
            if not channel_indices and self.controller.channel_names:
                channel_indices = list(range(len(self.controller.channel_names)))
                logging.info(f"Empty channel list received, selecting all {len(channel_indices)} channels")

            # Update selected channels
            self.controller.selected_channels = channel_indices
            self.controller._update_channel_displays()

            logging.info(f"MNE channels updated from API: {len(channel_indices)} channels selected")

        except Exception as e:
            logging.error(f"Error in API MNE channels handler: {e}")
