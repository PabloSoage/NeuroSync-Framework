import logging
from typing import Any, Optional, Dict, List, Tuple

import numpy as np
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
        visualization_service: Optional[Any] = None,
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
        self.visualization_service = visualization_service
        self.processor_service = None
        if self.visualization_service and hasattr(
            self.visualization_service, "processor_service"
        ):
            self.processor_service = self.visualization_service.processor_service

        # State management
        self.current_conversion_task: Optional[str] = None
        self.current_visualization_task: Optional[str] = None
        self.current_realtime_session: Optional[str] = None
        self.selected_channels: List[int] = []
        self.conversion_selected_channels: List[int] = []
        self.channel_names: List[str] = []
        self.last_converted_channels: List[int] = []

        # Filter state
        self.filters_applied = False
        self.filter_settings: Dict[str, Any] = {}

        # Setup connections and timers
        self._connect_widgets()
        self._setup_status_timer()
        self._setup_realtime_timer()
        self._initialize_channel_data()

        # Check for active filters
        self._update_filter_status()
        self._setup_filter_check_timer()

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

        # Real-time signals
        self.conversion_widget.realtime_requested.connect(self._handle_realtime_request)
        self.conversion_widget.realtime_stopped.connect(self._stop_realtime_processing)
        # Dynamic parameter updates
        self.conversion_widget.realtime_param_changed.connect(
            self._handle_realtime_param_change
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

        # Dynamic visualization updates
        self.visualization_widget.plot_type_changed.connect(
            self._handle_plot_type_change
        )
        self.visualization_widget.freq_range_changed.connect(
            self._handle_freq_range_change
        )
        self.visualization_widget.psd_mode_changed.connect(self._handle_psd_mode_change)
        self.visualization_widget.topomap_band_changed.connect(
            self._handle_topomap_band_change
        )

    def _setup_status_timer(self) -> None:
        """Setup timer for checking task status."""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._check_task_status)

    def _setup_realtime_timer(self) -> None:
        """Setup timer for real-time status updates."""
        self.realtime_timer = QTimer()
        self.realtime_timer.timeout.connect(self._update_realtime_status)

    def _setup_filter_check_timer(self) -> None:
        """Setup timer to periodically check filter status."""
        self.filter_check_timer = QTimer()
        self.filter_check_timer.timeout.connect(self._update_filter_status)
        self.filter_check_timer.start(2000)  # Check every 2 seconds

    def _update_filter_status(self) -> None:
        """Check if filters are applied in visualization service and update UI."""
        if not self.visualization_service:
            # No visualization service, can't check filters
            if hasattr(self.conversion_widget, "filter_status"):
                self.conversion_widget.update_filter_status(
                    "(No access to filters)", False
                )
            return

        # Check if filters are applied using the visualization service
        self.filters_applied = False
        self.filter_settings = {}

        try:
            # Check for commonly used methods to determine if filters are applied
            if hasattr(self.visualization_service, "are_filters_applied"):
                self.filters_applied = self.visualization_service.are_filters_applied()
            elif hasattr(self.visualization_service, "has_active_filters"):
                self.filters_applied = self.visualization_service.has_active_filters()

            # Get filter settings
            if hasattr(self.visualization_service, "get_filter_settings"):
                self.filter_settings = self.visualization_service.get_filter_settings()

            # Update UI
            if self.filters_applied:
                # Format filter description
                desc_parts = []
                if self.filter_settings.get("bandpass", {}).get("enabled", False):
                    bp = self.filter_settings["bandpass"]
                    desc_parts.append(
                        f"BP {bp.get('low', 1.0)}-{bp.get('high', 50.0)}Hz"
                    )

                if self.filter_settings.get("notch", {}).get("enabled", False):
                    notch = self.filter_settings["notch"]
                    desc_parts.append(f"Notch {notch.get('frequency', 50)}Hz")

                if self.filter_settings.get("detrend", False):
                    desc_parts.append("Detrend")

                filter_desc = "(Active: " + ", ".join(desc_parts) + ")"
                self.conversion_widget.update_filter_status(filter_desc, True)
            else:
                self.conversion_widget.update_filter_status(
                    "(No filters currently active)", False
                )

        except Exception as e:
            logging.error(f"Error checking filter status: {e}")
            self.conversion_widget.update_filter_status(
                "(Error checking filter status)", False
            )

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

            use_filters = params.get("use_filters", False)
            if use_filters and self.filters_applied:
                data, timestamps = self.data_service.get_current_data()
                self._add_status_message("Using filtered data for conversion")
            else:
                data, timestamps = self.data_service.get_raw_data()
                self._add_status_message("Using raw data")

            # Start conversion with potentially filtered data
            self.current_conversion_task = self.mne_service.convert_to_mne_async(
                duration_seconds=params["duration_seconds"],
                convert_to_v=params["convert_to_v"],
                selected_channels=channels_for_conversion,
                callback=self._conversion_callback,
                data=data,  # Pass filtered or raw data
                metadata=self.data_service.get_metadata(),
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

            filter_info = (
                " with filters" if (use_filters and self.filters_applied) else ""
            )

            self._add_status_message(
                f"Starting MNE conversion in {mode_name} Mode with {channel_info}{filter_info}"
            )
            self.status_message.emit(
                f"Converting {channel_info} to MNE format{filter_info}..."
            )

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

    def _handle_realtime_request(self, params: Dict[str, Any]) -> None:
        """Handle real-time processing request."""
        if not self.mne_service.is_available():
            self._show_error("MNE Error", "MNE package is not installed")
            return

        try:
            # Get visualization parameters
            viz_params = self.visualization_widget.get_visualization_parameters()

            # OPTIMIZATION: In real-time mode, channel selection is applied at conversion level
            # This saves processing time and memory by only converting selected channels
            selected_for_conversion = (
                self.selected_channels if self.selected_channels else None
            )

            # Check if filters should be applied
            use_filters = params.get("use_filters", False)

            # Start real-time processing
            self.current_realtime_session = self.mne_service.start_realtime_processing(
                update_interval_seconds=params["update_interval_seconds"],
                plot_type=viz_params["plot_type"],
                duration_seconds=params["duration_seconds"],
                convert_to_v=params["convert_to_v"],
                selected_channels=selected_for_conversion,
                visualization_params=viz_params,
                callback=self._realtime_callback,
                use_filters=use_filters and self.filters_applied,
                filter_settings=(
                    self.filter_settings
                    if (use_filters and self.filters_applied)
                    else None
                ),
                processor_service=(
                    self.processor_service
                    if (use_filters and self.filters_applied)
                    else None
                ),
            )

            # Update UI state
            self.conversion_widget.set_realtime_state(True)
            self.visualization_widget.set_realtime_mode(True)
            self.realtime_timer.start(1000)  # Update every second

            channel_count = (
                len(self.selected_channels)
                if self.selected_channels
                else len(self.channel_names)
            )
            total_channels = len(self.channel_names)

            # Show optimization information
            if (
                selected_for_conversion
                and len(selected_for_conversion) < total_channels
            ):
                optimization_msg = f"⚡ Optimized: Converting only {channel_count}/{total_channels} channels"
                self._add_status_message(optimization_msg)
                self._add_status_message(
                    f"💾 Memory saved: ~{((total_channels - channel_count) / total_channels * 100):.1f}% less data processing"
                )

            # Show filter information
            if use_filters and self.filters_applied:
                self._add_status_message(
                    "🔍 Using processing panel filters for real-time data"
                )

            self._add_status_message(
                f"🚀 Started real-time session: {self.current_realtime_session}"
            )
            self.status_message.emit("Real-time MNE processing started")

        except Exception as e:
            self._show_error(
                "MNE Error", f"Error starting real-time processing: {str(e)}"
            )
            logging.error(f"Real-time processing start error: {e}")

    def _stop_realtime_processing(self) -> None:
        """Stop real-time processing."""
        if self.current_realtime_session:
            if self.mne_service.stop_realtime_processing(self.current_realtime_session):
                self._add_status_message(
                    f"Stopped real-time session: {self.current_realtime_session}"
                )
                self.status_message.emit("Real-time processing stopped")

            self.conversion_widget.set_realtime_state(False)
            self.visualization_widget.set_realtime_mode(False)
            self.realtime_timer.stop()
            self.current_realtime_session = None

            # Reset status display
            self.status_widget.update_realtime_status({"active": False})

    def _realtime_callback(self, session_id: str, result: Dict[str, Any]) -> None:
        """Handle real-time visualization updates."""
        if result.get("success"):
            # Update visualization
            plot_data = result.get("plot_data")
            if plot_data is not None:
                self.visualization_widget.display_plot(str(plot_data))

            # Log successful update
            logging.debug(f"Real-time update completed for session: {session_id}")
        else:
            error_msg = result.get("error", "Unknown error")
            logging.warning(f"Real-time update failed: {error_msg}")

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

        # For real-time mode, show appropriate title with optimization info
        if self.current_realtime_session:
            title = "Select Channels for Real-time Processing (Optimized)"
        else:
            title = "Select Channels for Visualization"

        dialog = ChannelSelectionDialog(
            channel_names=available_names,
            selected_channels=self.selected_channels,
            parent=self.visualization_widget,
        )
        dialog.setWindowTitle(title)

        if dialog.exec_() == QDialog.Accepted:
            old_selection = self.selected_channels.copy()
            self.selected_channels = dialog.get_selected_channels()
            self._update_channel_displays()

            # Log the change with optimization information
            selected_names = [
                available_names[i]
                for i in self.selected_channels
                if i < len(available_names)
            ]
            self._add_status_message(
                f"Selected {len(self.selected_channels)} channels: {', '.join(selected_names[:5])}"
                + (
                    f" and {len(selected_names)-5} more"
                    if len(selected_names) > 5
                    else ""
                )
            )

            # Update real-time session if active
            if self.current_realtime_session:
                try:
                    # Calculate optimization benefit
                    total_channels = len(self.channel_names)
                    new_count = len(self.selected_channels)
                    old_count = len(old_selection)

                    # Update channels directly
                    if self.mne_service.update_realtime_channels(
                        self.current_realtime_session, self.selected_channels
                    ):
                        self._add_status_message(
                            f"✅ Real-time channels updated: {old_count} → {new_count}"
                        )

                        # Show optimization information
                        if new_count < total_channels:
                            memory_saved = (
                                (total_channels - new_count) / total_channels * 100
                            )
                            self._add_status_message(
                                f"⚡ Optimization active: {memory_saved:.1f}% less processing needed"
                            )
                        elif old_count < total_channels and new_count == total_channels:
                            self._add_status_message(
                                f"ℹ️ Processing all channels now (no optimization)"
                            )
                    else:
                        self._add_status_message(
                            "⚠️ Failed to update real-time channels"
                        )

                except Exception as e:
                    logging.error(f"Error updating real-time channels: {e}")
                    self._add_status_message(f"❌ Error updating channels: {str(e)}")

    def _get_available_channels_for_visualization(self) -> Tuple[List[str], List[int]]:
        """Get available channels for visualization based on conversion mode."""
        # In real-time mode, always show all available channels
        if self.current_realtime_session:
            return self.channel_names.copy(), list(range(len(self.channel_names)))

        # For non-real-time mode, use existing logic
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
            plot_data = result.get("plot_data")
            if plot_data is not None:
                self.visualization_widget.display_plot(str(plot_data))

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

    def _update_realtime_status(self) -> None:
        """Update real-time status display."""
        if self.current_realtime_session:
            status = self.mne_service.get_realtime_status(self.current_realtime_session)
            self.status_widget.update_realtime_status(status)

            # Stop timer if session is no longer active
            if not status.get("active", False):
                self.realtime_timer.stop()
                self.conversion_widget.set_realtime_state(False)
                self.current_realtime_session = None

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
        # Stop real-time processing
        if self.current_realtime_session:
            self.mne_service.stop_realtime_processing(self.current_realtime_session)

        # Cancel other tasks
        if self.current_conversion_task:
            self.mne_service.cancel_task(self.current_conversion_task)
        if self.current_visualization_task:
            self.mne_service.cancel_task(self.current_visualization_task)

        # Stop timers
        if hasattr(self, "status_timer"):
            self.status_timer.stop()
        if hasattr(self, "realtime_timer"):
            self.realtime_timer.stop()

    def _handle_realtime_param_change(self, param_name: str, value: Any) -> None:
        """Handle dynamic parameter changes during real-time processing."""
        if not self.current_realtime_session:
            return

        try:
            success = False
            if param_name == "update_interval":
                success = self.mne_service.update_realtime_interval(
                    self.current_realtime_session, value
                )
                if success:
                    self._add_status_message(f"Updated interval to {value}s")

            if success:
                logging.debug(f"Updated real-time parameter {param_name} to {value}")
            else:
                logging.warning(f"Failed to update real-time parameter {param_name}")

        except Exception as e:
            logging.error(f"Error updating real-time parameter {param_name}: {e}")

    def _handle_plot_type_change(self, plot_type: str) -> None:
        """Handle plot type change during real-time processing."""
        if not self.current_realtime_session:
            return

        try:
            if self.mne_service.update_realtime_plot_type(
                self.current_realtime_session, plot_type
            ):
                self._add_status_message(f"Switched to {plot_type} visualization")
            else:
                logging.warning(f"Failed to update plot type to {plot_type}")
        except Exception as e:
            logging.error(f"Error updating plot type: {e}")

    def _handle_freq_range_change(self, freq_min: int, freq_max: int) -> None:
        """Handle frequency range change during real-time processing."""
        if not self.current_realtime_session:
            return

        try:
            viz_params = self.visualization_widget.get_visualization_parameters()
            if self.mne_service.update_realtime_visualization_params(
                self.current_realtime_session, viz_params
            ):
                self._add_status_message(
                    f"Updated frequency range: {freq_min}-{freq_max} Hz"
                )
            else:
                logging.warning("Failed to update frequency range")
        except Exception as e:
            logging.error(f"Error updating frequency range: {e}")

    def _handle_psd_mode_change(self, individual_mode: bool) -> None:
        """Handle PSD mode change during real-time processing."""
        if not self.current_realtime_session:
            return

        try:
            viz_params = self.visualization_widget.get_visualization_parameters()
            if self.mne_service.update_realtime_visualization_params(
                self.current_realtime_session, viz_params
            ):
                mode_name = "Individual" if individual_mode else "Average"
                self._add_status_message(f"Switched to {mode_name} PSD mode")
            else:
                logging.warning("Failed to update PSD mode")
        except Exception as e:
            logging.error(f"Error updating PSD mode: {e}")

    def _handle_topomap_band_change(self, freq_min: int, freq_max: int) -> None:
        """Handle topomap band change during real-time processing."""
        if not self.current_realtime_session:
            return

        try:
            viz_params = self.visualization_widget.get_visualization_parameters()
            if self.mne_service.update_realtime_visualization_params(
                self.current_realtime_session, viz_params
            ):
                self._add_status_message(
                    f"Updated topomap band: {freq_min}-{freq_max} Hz"
                )
            else:
                logging.warning("Failed to update topomap band")
        except Exception as e:
            logging.error(f"Error updating topomap band: {e}")

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
