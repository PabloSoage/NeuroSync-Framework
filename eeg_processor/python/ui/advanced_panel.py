from typing import Any, Optional, Dict

from PyQt5.QtGui import QCloseEvent

from .base_panel import BasePanel
from .advanced.advanced_panel_controller import AdvancedPanelController
from .advanced.widgets.ica_widget import ICAWidget
from .advanced.widgets.wavelet_widget import WaveletWidget
from .advanced.widgets.downsampling_widget import DownsamplingWidget
from .advanced.widgets.advanced_filter_widget import AdvancedFilterWidget


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

        self._setup_advanced_panel()

        # Add stretch to push everything to the top
        self.layout.addStretch()

    def _setup_advanced_panel(self) -> None:
        """Setup the advanced processing panel with widgets and controller."""
        # Create specialized widgets
        self.ica_widget = ICAWidget()
        self.wavelet_widget = WaveletWidget()
        self.downsampling_widget = DownsamplingWidget()
        self.advanced_filter_widget = AdvancedFilterWidget()

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

        # Add widgets to layout
        self.layout.addWidget(self.ica_widget)
        self.layout.addWidget(self.wavelet_widget)
        self.layout.addWidget(self.downsampling_widget)
        self.layout.addWidget(self.advanced_filter_widget)

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
