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


class ApiEventHandler(QObject):
    """Thread-safe handler for API events."""

    ica_compute_signal = pyqtSignal(int, list)  # num_components, selected_channels
    ica_view_signal = pyqtSignal(str)  # colormap
    ica_channels_signal = pyqtSignal(list)  # channel_indices

    def __init__(self):
        super().__init__()
