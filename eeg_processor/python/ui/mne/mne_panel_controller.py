import logging
from typing import Any, Optional, Dict, List, Tuple

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QDialog

from .widgets.channel_selection_dialog import ChannelSelectionDialog
from .widgets.mne_conversion_widget import MNEConversionWidget
from .widgets.mne_status_widget import MNEStatusWidget
from .widgets.mne_visualization_widget import MNEVisualizationWidget
from ...services.data_access_service import DataAccessService
from ...services.mne_service import MNEService


class MNEPanelController(QObject):
    """
    Controller that coordinates MNE panel operations.

    This class applies the SOLID principles by:
    - Single Responsibility: Only coordinates MNE panel logic
    - Open/Closed: Extensible through signals and interfaces
    - Liskov Substitution: Can be replaced by any compatible controller
    - Interface Segregation: Uses specific widget interfaces
    - Dependency Inversion: Depends on service abstractions
    """

    # Signals for communication with parent components
    status_message = pyqtSignal(str)
    error_message = pyqtSignal(str, str)

    def __init__(
        self,
        conversion_widget: MNEConversionWidget,
        visualization_widget: MNEVisualizationWidget,
        status_widget: MNEStatusWidget,
        parent: Optional[QObject] = None,
    ):
        """Initialize the MNE panel controller."""
        super().__init__(parent)

        # Widgets
        self.conversion_widget = conversion_widget
        self.visualization_widget = visualization_widget
        self.status_widget = status_widget

        # Services
        self.mne_service = MNEService.get_instance()
        self.data_service = DataAccessService.get_instance()

        # State management
        self.current_conversion_task: Optional[str] = None
        self.current_visualization_task: Optional[str] = None
        self.selected_channels: List[int] = []
        self.conversion_selected_channels: List[int] = []
        self.channel_names: List[str] = []
        self.last_converted_channels: List[int] = []

        # Setup connections and timers
        self._connect_widgets()
        self._setup_status_timer()
        self._initialize_channel_data()

    def _connect_widgets(self) -> None:
        """Connect widget signals to controller methods."""
        # Conversion widget signals
        self.conversion_widget.conversion_requested.connect(
            self._handle_conversion_request
        )
        self.conversion_widget.conversion_cancelled.connect(self._cancel_conversion)
        self.conversion_widget.channel_selection_requested.connect(
            self._handle_channel_selection
        )

        # Visualization widget signals
        self.visualization_widget.visualization_requested.connect(
            self._handle_visualization_request
        )
        self.visualization_widget.visualization_cancelled.connect(
            self._cancel_visualization
        )
        self.visualization_widget.channel_selection_requested.connect(
            self._handle_channel_selection
        )

    def _setup_status_timer(self) -> None:
        """Setup timer for checking task status."""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._check_task_status)

    def _initialize_channel_data(self) -> None:
        """Initialize channel data from data service."""
        try:
            metadata = self.data_service.get_metadata()
            self.channel_names = metadata.get("channel_names", [])
            eeg_channels = metadata.get("eeg_channels", [])

            if not self.channel_names and eeg_channels:
                self.channel_names = [f"CH{i+1}" for i in range(len(eeg_channels))]

            if not self.selected_channels and self.channel_names:
                self.selected_channels = list(range(len(self.channel_names)))
                self.conversion_selected_channels = self.selected_channels.copy()

            self._update_channel_displays()

        except Exception as e:
            logging.debug(f"Error initializing channel data: {e}")

    def _handle_conversion_request(self, params: Dict[str, Any]) -> None:
        """Handle conversion request from widget."""
        if not self.mne_service.is_available():
            self._show_error("MNE Error", "MNE package is not installed")
            return

        try:
            # Determine channels for conversion
            channels_for_conversion = None
            if params["mode"] == "performance":
                if not self.conversion_selected_channels:
                    self._show_error("MNE Error", "No channels selected for conversion")
                    return
                channels_for_conversion = self.conversion_selected_channels

            # Start conversion
            self.current_conversion_task = self.mne_service.convert_to_mne_async(
                duration_seconds=params["duration_seconds"],
                convert_to_v=params["convert_to_v"],
                selected_channels=channels_for_conversion,
                callback=self._conversion_callback,
            )

            # Update UI state
            self.conversion_widget.set_conversion_state(True)
            self.status_timer.start(100)

            mode_name = "Performance" if params["mode"] == "performance" else "Flexible"
            channel_info = (
                f"{len(channels_for_conversion)} channels"
                if channels_for_conversion
                else "all channels"
            )

            self._add_status_message(
                f"Starting MNE conversion in {mode_name} Mode with {channel_info}"
            )
            self.status_message.emit(f"Converting {channel_info} to MNE format...")

        except Exception as e:
            self._show_error("MNE Error", f"Error starting conversion: {str(e)}")
            logging.error(f"MNE conversion start error: {e}")

    def _handle_visualization_request(self, params: Dict[str, Any]) -> None:
        """Handle visualization request from widget."""
        if not self.current_conversion_task:
            self._show_error("MNE Error", "No MNE data available. Convert data first.")
            return

        # Check conversion status
        status = self.mne_service.get_task_status(self.current_conversion_task)
        if not status.get("ready") or not status.get("successful"):
            self._show_error("MNE Error", "MNE conversion not complete or failed.")
            return

        try:
            # Start visualization
            self.current_visualization_task = (
                self.mne_service.create_visualization_async(
                    task_id=self.current_conversion_task,
                    plot_type=params["plot_type"],
                    freq_min=params["freq_min"],
                    freq_max=params["freq_max"],
                    bg_color=params["bg_color"],
                    show_individual_channels=params["show_individual_channels"],
                    selected_channels_for_display=self.selected_channels,
                    topomap_freq_range=params["topomap_freq_range"],
                    callback=self._visualization_callback,
                )
            )

            # Update UI state
            self.visualization_widget.set_visualization_state(True)
            self.status_timer.start(100)

            self._add_status_message(f"Starting {params['plot_type']} visualization")
            self.status_message.emit(
                f"Generating {params['plot_type']} visualization..."
            )

        except Exception as e:
            self._show_error("MNE Error", f"Error starting visualization: {str(e)}")
            logging.error(f"MNE visualization start error: {e}")

    def _handle_channel_selection(self, selection_type: str) -> None:
        """Handle channel selection request."""
        try:
            if selection_type == "conversion":
                self._open_conversion_channel_selection()
            elif selection_type == "visualization":
                self._open_visualization_channel_selection()

        except Exception as e:
            self._show_error(
                "Channel Selection Error", f"Error opening channel selection: {str(e)}"
            )
            logging.error(f"Channel selection error: {e}")

    def _open_conversion_channel_selection(self) -> None:
        """Open channel selection for conversion."""
        if not self.channel_names:
            self._show_error(
                "Channel Selection", "No channels available. Start streaming first."
            )
            return

        dialog = ChannelSelectionDialog(
            channel_names=self.channel_names,
            selected_channels=self.conversion_selected_channels,
            parent=self.conversion_widget,
        )
        dialog.setWindowTitle("Select Channels for MNE Conversion")

        if dialog.exec_() == QDialog.Accepted:
            self.conversion_selected_channels = dialog.get_selected_channels()
            self._update_channel_displays()
            self._add_status_message(
                f"Selected {len(self.conversion_selected_channels)} channels for conversion"
            )

    def _open_visualization_channel_selection(self) -> None:
        """Open channel selection for visualization."""
        available_names, available_indices = (
            self._get_available_channels_for_visualization()
        )

        if not available_names:
            self._show_error(
                "Channel Selection", "No channels available for visualization."
            )
            return

        dialog = ChannelSelectionDialog(
            channel_names=available_names,
            selected_channels=self.selected_channels,
            parent=self.visualization_widget,
        )
        dialog.setWindowTitle("Select Channels for Visualization")

        if dialog.exec_() == QDialog.Accepted:
            self.selected_channels = dialog.get_selected_channels()
            self._update_channel_displays()
            self._add_status_message(
                f"Selected {len(self.selected_channels)} channels for visualization"
            )

    def _get_available_channels_for_visualization(self) -> Tuple[List[str], List[int]]:
        """Get available channels for visualization based on conversion mode."""
        selected_mode = None
        try:
            selected_mode = self.conversion_widget.conversion_mode_combo.currentText()
        except:
            selected_mode = "Flexible"
        is_performance = "Performance" in selected_mode

        # Performance mode after conversion: show only converted channels
        if (
            is_performance
            and self.current_conversion_task
            and self.last_converted_channels
        ):
            names = [
                self.channel_names[i]
                for i in self.last_converted_channels
                if i < len(self.channel_names)
            ]
            indices = list(range(len(names)))
            return names, indices

        # Flexible mode or before conversion: all channels
        return self.channel_names.copy(), list(range(len(self.channel_names)))

    def _conversion_callback(self, task_id: str, result: Dict[str, Any]) -> None:
        """Handle conversion completion."""
        if result.get("success"):
            self._add_status_message(f"Conversion completed successfully: {task_id}")
            self.status_message.emit("MNE conversion completed successfully")
            self.visualization_widget.set_enabled(True)

            # Store converted channels info
            if self.conversion_selected_channels:
                self.last_converted_channels = self.conversion_selected_channels.copy()

        else:
            error_msg = result.get("error", "Unknown error")
            self._add_status_message(f"Conversion failed: {error_msg}")
            self._show_error("MNE Conversion Error", error_msg)

        self.conversion_widget.set_conversion_state(False)

    def _visualization_callback(self, task_id: str, result: Dict[str, Any]) -> None:
        """Handle visualization completion."""
        if result.get("success"):
            self._add_status_message(f"Visualization completed: {task_id}")
            self.status_message.emit("MNE visualization completed")
            self.visualization_widget.display_plot(result.get("plot_data"))

        else:
            error_msg = result.get("error", "Unknown error")
            self._add_status_message(f"Visualization failed: {error_msg}")
            self._show_error("MNE Visualization Error", error_msg)

        self.visualization_widget.set_visualization_state(False)

    def _cancel_conversion(self) -> None:
        """Cancel current conversion."""
        if self.current_conversion_task:
            if self.mne_service.cancel_task(self.current_conversion_task):
                self._add_status_message(
                    f"Cancelled conversion task: {self.current_conversion_task}"
                )
                self.status_message.emit("Conversion cancelled")

            self.conversion_widget.set_conversion_state(False)
            self.current_conversion_task = None

    def _cancel_visualization(self) -> None:
        """Cancel current visualization."""
        if self.current_visualization_task:
            if self.mne_service.cancel_task(self.current_visualization_task):
                self._add_status_message(
                    f"Cancelled visualization task: {self.current_visualization_task}"
                )
                self.status_message.emit("Visualization cancelled")

            self.visualization_widget.set_visualization_state(False)
            self.current_visualization_task = None

    def _check_task_status(self) -> None:
        """Check status of active tasks."""
        # Check conversion task
        if self.current_conversion_task:
            status = self.mne_service.get_task_status(self.current_conversion_task)
            if (
                status
                and status.get("ready", False)
                and not status.get("successful", False)
            ):
                error_msg = status.get("error", "Unknown error")
                self._add_status_message(f"Conversion failed: {error_msg}")
                self._show_error("MNE Conversion Error", error_msg)
                self.conversion_widget.set_conversion_state(False)
                self.current_conversion_task = None

        # Check visualization task
        if self.current_visualization_task:
            status = self.mne_service.get_task_status(self.current_visualization_task)
            if (
                status
                and status.get("ready", False)
                and not status.get("successful", False)
            ):
                error_msg = status.get("error", "Unknown error")
                self._add_status_message(f"Visualization failed: {error_msg}")
                self._show_error("MNE Visualization Error", error_msg)
                self.visualization_widget.set_visualization_state(False)
                self.current_visualization_task = None

        # Stop timer if no active tasks
        if not self.current_conversion_task and not self.current_visualization_task:
            self.status_timer.stop()

    def _update_channel_displays(self) -> None:
        """Update channel information displays in widgets."""
        # Update conversion widget
        if self.conversion_selected_channels:
            if len(self.conversion_selected_channels) == len(self.channel_names):
                self.conversion_widget.update_channel_info("All channels")
            else:
                count = len(self.conversion_selected_channels)
                self.conversion_widget.update_channel_info(f"{count} channels selected")

        # Update visualization widget
        if self.selected_channels:
            if len(self.selected_channels) == len(self.channel_names):
                self.visualization_widget.update_channel_info("All channels")
            else:
                count = len(self.selected_channels)
                self.visualization_widget.update_channel_info(
                    f"{count} channels selected"
                )

    def _add_status_message(self, message: str) -> None:
        """Add status message to status widget."""
        self.status_widget.add_status_message(message)

    def _show_error(self, title: str, message: str) -> None:
        """Show error message."""
        self.error_message.emit(title, message)

    def enable_processing(self, enabled: bool) -> None:
        """Enable or disable processing."""
        self.conversion_widget.set_enabled(enabled)

        if enabled:
            self._initialize_channel_data()
        else:
            self.visualization_widget.set_enabled(False)
            self.current_conversion_task = None
            self.current_visualization_task = None

    def cleanup(self) -> None:
        """Cleanup resources."""
        if self.current_conversion_task:
            self.mne_service.cancel_task(self.current_conversion_task)
        if self.current_visualization_task:
            self.mne_service.cancel_task(self.current_visualization_task)
        if hasattr(self, "status_timer"):
            self.status_timer.stop()
