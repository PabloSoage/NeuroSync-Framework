import logging
from typing import Any, Optional, Dict, List

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QScrollArea, QWidget, QVBoxLayout

from .advanced.advanced_panel_controller import AdvancedPanelController
from .advanced.widgets.advanced_filter_widget import AdvancedFilterWidget
from .advanced.widgets.downsampling_widget import DownsamplingWidget
from .advanced.widgets.ica_widget import ICAWidget
from .advanced.widgets.wavelet_widget import WaveletWidget
from .base_panel import BasePanel


class AdvancedProcessingPanel(BasePanel):
    """
    Panel for advanced signal processing operations.
    """

    def __init__(
        self,
        collector_service: Any,
        processor_service: Any,
        parent: Optional[Any] = None,
    ) -> None:
        """Initialize the advanced processing panel."""
        super().__init__(parent)

        # Store service references for compatibility
        self.collector_service = collector_service
        self.processor_service = processor_service

        # Setup thread-safe event handler for API events
        self.api_event_handler = ApiEventHandler()
        self.api_event_handler.ica_compute_signal.connect(
            self._handle_api_ica_compute_safe
        )
        self.api_event_handler.ica_view_signal.connect(
            self._handle_api_ica_view_safe
        )
        self.api_event_handler.ica_channels_signal.connect(
            self._handle_api_ica_channels_safe
        )

        # Connect wavelet signals
        self.api_event_handler.wavelet_compute_signal.connect(
            self._handle_api_wavelet_compute_safe
        )
        self.api_event_handler.wavelet_inverse_signal.connect(
            self._handle_api_wavelet_inverse_safe
        )

        # Connect downsampling signal
        self.api_event_handler.downsampling_apply_signal.connect(
            self._handle_api_downsampling_apply_safe
        )

        self._setup_advanced_panel()

        # Setup event subscriptions for API synchronization
        self._setup_event_subscriptions()

    def _setup_advanced_panel(self) -> None:
        """Setup the advanced processing panel with widgets and controller."""
        # Create a scroll area for the entire panel
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(1)  # Qt.ScrollBarAlwaysOff
        scroll_area.setVerticalScrollBarPolicy(2)  # Qt.ScrollBarAsNeeded

        # Create a container widget for all components
        container_widget = QWidget()
        container_layout = QVBoxLayout(container_widget)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(10)

        # Create specialized widgets
        self.ica_widget = ICAWidget()
        self.wavelet_widget = WaveletWidget()
        self.downsampling_widget = DownsamplingWidget()
        self.advanced_filter_widget = AdvancedFilterWidget()

        # Add widgets to container layout
        container_layout.addWidget(self.ica_widget)
        container_layout.addWidget(self.wavelet_widget)
        container_layout.addWidget(self.downsampling_widget)
        container_layout.addWidget(self.advanced_filter_widget)

        # Add stretch to push everything to the top
        container_layout.addStretch()

        # Set the container as the scroll area's widget
        scroll_area.setWidget(container_widget)

        # Add scroll area to main layout
        self.layout.addWidget(scroll_area)

        # Create controller to coordinate widgets
        self.controller = AdvancedPanelController(
            self.ica_widget,
            self.wavelet_widget,
            self.downsampling_widget,
            self.advanced_filter_widget,
            self.collector_service,
            self.processor_service,
            parent=self,
        )

        # Connect controller signals to panel signals
        self.controller.status_message.connect(self.status_message.emit)
        self.controller.error_message.connect(self.error_message.emit)

    def enable_processing(self, enabled: bool) -> None:
        """Enable or disable advanced processing controls."""
        if hasattr(self, "controller"):
            self.controller.enable_processing(enabled)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle panel close event."""
        if hasattr(self, "controller"):
            self.controller.cleanup()
        super().closeEvent(event)

    # API compatibility methods
    def get_ica_settings(self) -> Dict[str, Any]:
        """Get current ICA settings for API compatibility."""
        if not hasattr(self, "controller"):
            return {}
        return self.ica_widget.get_ica_settings()

    def get_wavelet_settings(self) -> Dict[str, Any]:
        """Get current wavelet settings for API compatibility."""
        if not hasattr(self, "controller"):
            return {}
        return self.wavelet_widget.get_wavelet_settings()

    def get_downsample_settings(self) -> Dict[str, Any]:
        """Get current downsampling settings for API compatibility."""
        if not hasattr(self, "controller"):
            return {}
        return self.downsampling_widget.get_downsample_settings()

    def get_advanced_filter_settings(self) -> Dict[str, Any]:
        """Get current advanced filter settings for API compatibility."""
        if not hasattr(self, "controller"):
            return {}
        return self.advanced_filter_widget.get_advanced_filter_settings()

    def update_channel_lists(self, channel_names: list) -> bool:
        """Update channel selection from API call."""
        if not hasattr(self, "controller"):
            return False
        return self.controller.update_channel_lists(channel_names)

    def _setup_event_subscriptions(self) -> None:
        """Setup subscriptions for API-generated events."""
        try:
            from ..core.event_system import EventDispatcher, EventType

            event_dispatcher = EventDispatcher.get_instance()

            # Subscribe to ICA events
            event_dispatcher.subscribe(
                EventType.ICA_COMPUTE, self._handle_api_ica_compute_thread_safe
            )
            event_dispatcher.subscribe(
                EventType.ICA_VIEW_COMPONENTS, self._handle_api_ica_view_thread_safe
            )
            event_dispatcher.subscribe(
                EventType.ICA_SELECT_CHANNELS, self._handle_api_ica_channels_thread_safe
            )

            # Subscribe to wavelet events
            event_dispatcher.subscribe(
                EventType.WAVELET_COMPUTE, self._handle_api_wavelet_compute_thread_safe
            )
            event_dispatcher.subscribe(
                EventType.WAVELET_APPLY_INVERSE, self._handle_api_wavelet_inverse_thread_safe
            )

            # Subscribe to downsampling events
            event_dispatcher.subscribe(
                EventType.DOWNSAMPLE_APPLY, self._handle_api_downsampling_apply_thread_safe
            )

        except Exception as e:
            logging.error(f"Error setting up API event subscriptions: {e}")

    def _handle_api_ica_compute_thread_safe(self, event: Any) -> None:
        """Handle ICA compute events from API in a thread-safe way."""
        try:
            data = event.data
            self.api_event_handler.ica_compute_signal.emit(
                data.get("num_components", 2),
                data.get("selected_channels", [])
            )
        except Exception as e:
            logging.error(f"Error handling API ICA compute event: {e}")

    def _handle_api_ica_view_thread_safe(self, event: Any) -> None:
        """Handle ICA view events from API in a thread-safe way."""
        try:
            data = event.data
            self.api_event_handler.ica_view_signal.emit(
                data.get("colormap", "viridis")
            )
        except Exception as e:
            logging.error(f"Error handling API ICA view event: {e}")

    def _handle_api_ica_channels_thread_safe(self, event: Any) -> None:
        """Handle ICA channel selection events from API in a thread-safe way."""
        try:
            data = event.data
            self.api_event_handler.ica_channels_signal.emit(
                data.get("channel_indices", [])
            )
        except Exception as e:
            logging.error(f"Error handling API ICA channels event: {e}")

    def _handle_api_ica_compute_safe(self, num_components: int, selected_channels: List[int]) -> None:
        """Handle ICA compute from API safely in main thread."""
        try:
            # IMPORTANTE: Asegurar que num_components es válido
            if num_components <= 0 or num_components > 16:
                logging.error(f"Invalid num_components received: {num_components}, using default 2")
                num_components = 2

            logging.info(f"Setting ICA components to: {num_components}")

            self.ica_widget.ica_components_spin.blockSignals(True)
            self.ica_widget.ica_components_spin.setValue(int(num_components))
            self.ica_widget.ica_components_spin.blockSignals(False)

            # Update selected channels if provided
            if selected_channels:
                # Validate channel indices
                valid_channels = []
                for ch in selected_channels:
                    if isinstance(ch, int) and 0 <= ch < len(self.ica_widget.channel_names):
                        valid_channels.append(ch)

                self.ica_widget.selected_channels = valid_channels
                self.ica_widget._update_channel_display()
                logging.info(f"Updated selected channels: {len(valid_channels)} channels")
            else:
                self.ica_widget.selected_channels = list(range(len(self.ica_widget.channel_names)))
                self.ica_widget._update_channel_display()
                logging.info("Using all channels (none specified)")

            # Trigger ICA computation through controller
            params = {
                "num_components": int(num_components),
                "selected_channels": self.ica_widget.selected_channels.copy()
            }

            logging.info(f"Triggering ICA computation with: {params}")
            self.controller._handle_ica_computation(params)

        except Exception as e:
            logging.error(f"Error in API ICA compute handler: {e}")
            # Emit error to user
            self.controller.error_message.emit("API ICA Error", f"Error processing ICA request: {str(e)}")

    def _handle_api_ica_view_safe(self, colormap: str) -> None:
        """Handle ICA view from API safely in main thread."""
        try:
            # Update colormap in widget
            index = self.ica_widget.colormap_combo.findData(colormap)
            if index >= 0:
                self.ica_widget.colormap_combo.setCurrentIndex(index)

            # Trigger ICA visualization
            params = {"colormap": colormap}
            self.controller._handle_ica_visualization(params)

        except Exception as e:
            logging.error(f"Error in API ICA view handler: {e}")

    def _handle_api_ica_channels_safe(self, channel_indices: List[int]) -> None:
        """Handle ICA channel selection from API safely in main thread."""
        try:
            # Update selected channels
            self.ica_widget.selected_channels = channel_indices
            self.ica_widget._update_channel_display()

            logging.info(f"ICA channels updated from API: {len(channel_indices)} channels selected")

        except Exception as e:
            logging.error(f"Error in API ICA channels handler: {e}")

    def _handle_api_wavelet_compute_thread_safe(self, event: Any) -> None:
        """Handle wavelet compute events from API in a thread-safe way."""
        try:
            data = event.data
            logging.info(f"API Wavelet compute event received: {data}")

            self.api_event_handler.wavelet_compute_signal.emit(data)
        except Exception as e:
            logging.error(f"Error handling API wavelet compute event: {e}")

    def _handle_api_wavelet_inverse_thread_safe(self, event: Any) -> None:
        """Handle wavelet inverse events from API in a thread-safe way."""
        try:
            data = event.data
            channel = data.get("channel", 0)
            apply = data.get("apply", True)

            logging.info(f"API Wavelet inverse event received: channel={channel}, apply={apply}")

            self.api_event_handler.wavelet_inverse_signal.emit(channel, apply)
        except Exception as e:
            logging.error(f"Error handling API wavelet inverse event: {e}")

    def _handle_api_wavelet_compute_safe(self, wavelet_params: Dict[str, Any]) -> None:
        """Handle wavelet compute from API safely in main thread."""
        try:
            wavelet_type = wavelet_params.get("wavelet_type", 4)  # Default to DB4
            decomposition_level = wavelet_params.get("decomposition_level", 3)
            channel = wavelet_params.get("channel", 0)
            extension_type = wavelet_params.get("extension_type", 0)
            apply_denoising = wavelet_params.get("apply_denoising", False)

            logging.info(f"API Wavelet compute: type={wavelet_type}, level={decomposition_level}, channel={channel}")

            # Update wavelet widget settings
            wavelet_widget = self.wavelet_widget

            # Update wavelet type
            wavelet_combo = wavelet_widget.wavelet_type_combo
            wavelet_combo.blockSignals(True)
            for i in range(wavelet_combo.count()):
                if wavelet_combo.itemData(i) == wavelet_type:
                    wavelet_combo.setCurrentIndex(i)
                    break
            wavelet_combo.blockSignals(False)

            # Update decomposition level
            wavelet_widget.wavelet_level_spin.blockSignals(True)
            wavelet_widget.wavelet_level_spin.setValue(decomposition_level)
            wavelet_widget.wavelet_level_spin.blockSignals(False)

            # Update channel selection
            channel_combo = wavelet_widget.wavelet_channel_combo
            channel_combo.blockSignals(True)
            if channel < channel_combo.count():
                channel_combo.setCurrentIndex(channel)
            channel_combo.blockSignals(False)

            # Update extension type
            extension_combo = wavelet_widget.extension_combo
            extension_combo.blockSignals(True)
            for i in range(extension_combo.count()):
                if extension_combo.itemData(i) == extension_type:
                    extension_combo.setCurrentIndex(i)
                    break
            extension_combo.blockSignals(False)

            # Update denoising checkbox
            wavelet_widget.apply_denoising_check.blockSignals(True)
            wavelet_widget.apply_denoising_check.setChecked(apply_denoising)
            wavelet_widget.apply_denoising_check.blockSignals(False)

            # Trigger wavelet computation through controller
            params = {
                "wavelet_type": wavelet_type,
                "decomp_level": decomposition_level,
                "channel_selection": channel,
                "extension_type": extension_type,
                "apply_denoising": apply_denoising,
            }

            logging.info(f"Triggering wavelet computation with params: {params}")
            self.controller._handle_wavelet_computation(params)

        except Exception as e:
            logging.error(f"Error in API wavelet compute handler: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            self.controller.error_message.emit("API Wavelet Error", f"Error processing wavelet request: {str(e)}")

    def _handle_api_wavelet_inverse_safe(self, channel: int, apply: bool) -> None:
        """Handle wavelet inverse from API safely in main thread."""
        try:
            logging.info(f"API Wavelet inverse: channel={channel}, apply={apply}")

            # Update channel selection to match the inverse transform request
            channel_combo = self.wavelet_widget.wavelet_channel_combo
            channel_combo.blockSignals(True)
            if channel < channel_combo.count():
                channel_combo.setCurrentIndex(channel)
            channel_combo.blockSignals(False)

            # Update the inverse applied state
            self.wavelet_widget.inverse_applied = apply

            # Update button appearance
            if apply:
                self.wavelet_widget.inverse_wavelet_btn.setText("Remove Inverse Transform")
                self.wavelet_widget.inverse_wavelet_btn.setStyleSheet(
                    "background-color: #AA3333; color: white;"
                )
            else:
                self.wavelet_widget.inverse_wavelet_btn.setText("Apply Inverse Transform")
                self.wavelet_widget.inverse_wavelet_btn.setStyleSheet("")

            # Trigger inverse transform through controller
            self.controller._handle_wavelet_inverse(apply)

            logging.info(f"Wavelet inverse {'applied' if apply else 'removed'} for channel {channel}")

        except Exception as e:
            logging.error(f"Error in API wavelet inverse handler: {e}")
            self.controller.error_message.emit("API Wavelet Error", f"Error processing inverse request: {str(e)}")

    def _handle_api_downsampling_apply_thread_safe(self, event: Any) -> None:
        """Handle downsampling apply events from API in a thread-safe way."""
        try:
            data = event.data
            factor = data.get("factor", 2)
            aggregation_method = data.get("aggregation_method", 0)
            apply = data.get("apply", True)

            logging.info(
                f"API Downsampling apply event received: factor={factor}, method={aggregation_method}, apply={apply}")

            self.api_event_handler.downsampling_apply_signal.emit(factor, aggregation_method, apply)
        except Exception as e:
            logging.error(f"Error handling API downsampling apply event: {e}")

    def _handle_api_downsampling_apply_safe(self, factor: int, aggregation_method: int, apply: bool) -> None:
        """Handle downsampling apply from API safely in main thread."""
        try:
            # Validate factor
            if factor < 2 or factor > 10:
                logging.error(f"Invalid factor received: {factor}, using default 2")
                factor = 2

            # Validate aggregation method
            if aggregation_method < 0 or aggregation_method > 2:
                logging.error(f"Invalid aggregation method received: {aggregation_method}, using default 0")
                aggregation_method = 0

            logging.info(f"API Downsampling apply: factor={factor}, method={aggregation_method}, apply={apply}")

            # Update downsampling widget settings
            downsampling_widget = self.downsampling_widget

            # Update factor
            downsampling_widget.downsample_factor_spin.blockSignals(True)
            downsampling_widget.downsample_factor_spin.setValue(factor)
            downsampling_widget.downsample_factor_spin.blockSignals(False)

            # Update aggregation method
            agg_combo = downsampling_widget.downsample_agg_combo
            agg_combo.blockSignals(True)
            for i in range(agg_combo.count()):
                if agg_combo.itemData(i) == aggregation_method:
                    agg_combo.setCurrentIndex(i)
                    break
            agg_combo.blockSignals(False)

            # Update applied state
            downsampling_widget.applied = apply

            # Update button appearance
            if apply:
                downsampling_widget.apply_downsample_btn.setText("Remove Downsampling")
                downsampling_widget.apply_downsample_btn.setStyleSheet(
                    "background-color: #AA3333; color: white;"
                )
            else:
                downsampling_widget.apply_downsample_btn.setText("Apply Downsampling")
                downsampling_widget.apply_downsample_btn.setStyleSheet("")

            # Trigger downsampling through controller
            params = {
                "apply": apply,
                "factor": factor,
                "operation": aggregation_method,
            }

            logging.info(f"Triggering downsampling with params: {params}")
            self.controller._handle_downsampling(params)

        except Exception as e:
            logging.error(f"Error in API downsampling apply handler: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            self.controller.error_message.emit("API Downsampling Error",
                                               f"Error processing downsampling request: {str(e)}")


class ApiEventHandler(QObject):
    """Thread-safe handler for API events."""

    ica_compute_signal = pyqtSignal(int, list)  # num_components, selected_channels
    ica_view_signal = pyqtSignal(str)  # colormap
    ica_channels_signal = pyqtSignal(list)  # channel_indices

    wavelet_compute_signal = pyqtSignal(dict)  # wavelet parameters
    wavelet_inverse_signal = pyqtSignal(int, bool)  # channel, apply

    downsampling_apply_signal = pyqtSignal(int, int, bool)  # factor, aggregation_method, apply

    def __init__(self):
        super().__init__()
