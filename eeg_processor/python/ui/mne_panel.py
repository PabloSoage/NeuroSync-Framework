from typing import Any, Optional, Dict

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


class MNEPanel(BasePanel):
    """
    Panel for MNE integration and analysis.

    This refactored version follows SOLID principles:
    - Single Responsibility: Only manages UI layout and coordination
    - Open/Closed: Extensible through widget composition
    - Liskov Substitution: Can be replaced by any compatible panel
    - Interface Segregation: Uses specific widget interfaces
    - Dependency Inversion: Depends on controller abstraction
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

    def closeEvent(self, event) -> None:
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
