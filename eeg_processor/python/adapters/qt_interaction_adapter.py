"""
Qt Interaction Adapter for synchronizing API changes with PyQt5 GUI.

This adapter bridges between the core event system and Qt GUI components,
ensuring thread-safe updates and maintaining consistency between API calls
and GUI state. It follows the same pattern as the input_collector module.
"""

import logging
import threading
from typing import Any, Callable, Optional, TypeVar, Dict
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from PyQt5.QtCore import QObject, QTimer, QThread
from PyQt5.QtWidgets import QApplication, QComboBox, QSpinBox, QLineEdit, QCheckBox

T = TypeVar("T")


class QtInteractionAdapter(QObject):
    """
    Adapter to synchronize API interactions with Qt GUI components.

    This class provides thread-safe communication between the core services
    and the PyQt5 GUI, similar to the pattern used in input_collector.
    """

    def __init__(self, main_app: Optional[Any] = None) -> None:
        """
        Initialize the Qt interaction adapter.

        Args:
            main_app: Reference to the main EEGProcessorApp instance
        """
        super().__init__()
        self.main_app = main_app
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="QtAdapter"
        )

        logging.info("Qt interaction adapter initialized")

    def _execute_safely(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute a function safely with proper thread handling.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If execution fails or times out
        """
        if QApplication.instance() is None:
            raise RuntimeError("No QApplication instance available")

        # Check if we're in the main thread
        if QThread.currentThread() == QApplication.instance().thread():
            # Execute directly in main thread
            return func(*args, **kwargs)
        else:
            # Execute in main thread using QTimer
            result: Optional[T] = None
            exception: Optional[Exception] = None
            finished = threading.Event()

            def execute_in_main_thread() -> None:
                nonlocal result, exception
                try:
                    result = func(*args, **kwargs)
                except Exception as e:
                    exception = e
                finally:
                    finished.set()

            # Schedule execution in main thread
            QTimer.singleShot(0, execute_in_main_thread)

            # Wait for completion with timeout
            if not finished.wait(timeout=5.0):
                raise TimeoutError("Qt operation timed out")

            if exception is not None:
                raise exception

            if result is None:
                raise RuntimeError("Operation completed but returned None")

            return result

    # Connection Panel Methods
    def connect_board(
        self, board_id: int, params: Dict[str, Any], preset: int = 0
    ) -> bool:
        """Connect to an EEG board via API."""
        try:

            def _connect() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "connection_panel"
                ):
                    return False

                panel = self.main_app.connection_panel

                # Update board selection
                if hasattr(panel, "board_type_combo"):
                    self._set_combo_by_data(panel.board_type_combo, board_id)

                # Update preset
                if hasattr(panel, "preset_combo"):
                    self._set_combo_by_data(panel.preset_combo, preset)

                # Update parameters
                if hasattr(panel, "_update_params_from_dict"):
                    panel._update_params_from_dict(params)

                # Trigger connection
                if hasattr(panel, "connect_board"):
                    panel.connect_board()
                    return True
                return False

            return self._execute_safely(_connect)

        except Exception as e:
            logging.error(f"Error connecting board via API: {e}")
            return False

    def disconnect_board(self, force_ui_update: bool = False) -> bool:
        """Disconnect from EEG board via API."""
        try:

            def _disconnect() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "connection_panel"
                ):
                    return False

                panel = self.main_app.connection_panel

                if hasattr(panel, "disconnect_board"):
                    panel.disconnect_board()

                # Force additional UI updates if requested
                if force_ui_update:
                    self._update_all_panels_connection_state(False)

                return True

            return self._execute_safely(_disconnect)

        except Exception as e:
            logging.error(f"Error disconnecting board via API: {e}")
            return False

    def start_stream(self) -> bool:
        """Start streaming via API."""
        try:

            def _start_stream() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "connection_panel"
                ):
                    return False

                panel = self.main_app.connection_panel

                if hasattr(panel, "start_stream"):
                    panel.start_stream()
                    return True
                return False

            return self._execute_safely(_start_stream)

        except Exception as e:
            logging.error(f"Error starting stream via API: {e}")
            return False

    def stop_stream(self) -> bool:
        """Stop streaming via API."""
        try:

            def _stop_stream() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "connection_panel"
                ):
                    return False

                panel = self.main_app.connection_panel

                if hasattr(panel, "stop_stream"):
                    panel.stop_stream()
                    return True
                return False

            return self._execute_safely(_stop_stream)

        except Exception as e:
            logging.error(f"Error stopping stream via API: {e}")
            return False

    # Processing Panel Methods
    def apply_filters(self, filter_config: Dict[str, Any]) -> bool:
        """Apply filters via API."""
        try:

            def _apply_filters() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "processing_panel"
                ):
                    return False

                panel = self.main_app.processing_panel

                # Update filter controls
                if hasattr(panel, "_update_filter_controls"):
                    panel._update_filter_controls(filter_config)

                # Apply filters if specified
                if filter_config.get("apply", False) and hasattr(
                    panel, "apply_filters"
                ):
                    panel.apply_filters()

                return True

            return self._execute_safely(_apply_filters)

        except Exception as e:
            logging.error(f"Error applying filters via API: {e}")
            return False

    def calculate_metrics(self) -> bool:
        """Calculate EEG metrics via API."""
        try:

            def _calculate_metrics() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "processing_panel"
                ):
                    return False

                panel = self.main_app.processing_panel

                if hasattr(panel, "calculate_metrics"):
                    panel.calculate_metrics()
                    return True
                return False

            return self._execute_safely(_calculate_metrics)

        except Exception as e:
            logging.error(f"Error calculating metrics via API: {e}")
            return False

    def show_brain_map(self) -> bool:
        """Show brain map visualization via API."""
        try:

            def _show_brain_map() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "processing_panel"
                ):
                    return False

                panel = self.main_app.processing_panel

                if hasattr(panel, "show_brain_map"):
                    panel.show_brain_map()
                    return True
                return False

            return self._execute_safely(_show_brain_map)

        except Exception as e:
            logging.error(f"Error showing brain map via API: {e}")
            return False

    # Recording Panel Methods
    def start_recording(self, filename: str, data_type: str = "raw") -> bool:
        """Start recording via API."""
        try:

            def _start_recording() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "recording_panel"
                ):
                    return False

                panel = self.main_app.recording_panel

                # Update recording settings
                if hasattr(panel, "record_file_edit"):
                    panel.record_file_edit.setText(filename)

                # Set data type
                if (
                    hasattr(panel, "raw_radio")
                    and hasattr(panel, "processed_radio")
                    and hasattr(panel, "both_radio")
                ):
                    if data_type == "processed":
                        panel.processed_radio.setChecked(True)
                    elif data_type == "both":
                        panel.both_radio.setChecked(True)
                    else:
                        panel.raw_radio.setChecked(True)

                # Start recording
                if hasattr(panel, "start_recording"):
                    panel.start_recording()
                    return True
                return False

            return self._execute_safely(_start_recording)

        except Exception as e:
            logging.error(f"Error starting recording via API: {e}")
            return False

    def stop_recording(self) -> bool:
        """Stop recording via API."""
        try:

            def _stop_recording() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "recording_panel"
                ):
                    return False

                panel = self.main_app.recording_panel

                if hasattr(panel, "stop_recording"):
                    panel.stop_recording()
                    return True
                return False

            return self._execute_safely(_stop_recording)

        except Exception as e:
            logging.error(f"Error stopping recording via API: {e}")
            return False

    def add_marker(self, marker_value: int) -> bool:
        """Add marker via API."""
        try:

            def _add_marker() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "recording_panel"
                ):
                    return False

                panel = self.main_app.recording_panel

                # Set marker value
                if hasattr(panel, "marker_value_spin"):
                    panel.marker_value_spin.setValue(marker_value)

                # Add marker
                if hasattr(panel, "add_marker"):
                    panel.add_marker()
                    return True
                return False

            return self._execute_safely(_add_marker)

        except Exception as e:
            logging.error(f"Error adding marker via API: {e}")
            return False

    # Streaming Panel Methods
    def add_streamer(self, streamer_params: str) -> bool:
        """Add streamer via API."""
        try:

            def _add_streamer() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "streaming_panel"
                ):
                    return False

                panel = self.main_app.streaming_panel

                if hasattr(panel, "add_streamer"):
                    panel.add_streamer(streamer_params)
                    return True
                return False

            return self._execute_safely(_add_streamer)

        except Exception as e:
            logging.error(f"Error adding streamer via API: {e}")
            return False

    def remove_streamer(self, streamer_params: str) -> bool:
        """Remove streamer via API."""
        try:

            def _remove_streamer() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "streaming_panel"
                ):
                    return False

                panel = self.main_app.streaming_panel

                # Find and select the streamer in the list
                if hasattr(panel, "streamers_list"):
                    for i in range(panel.streamers_list.count()):
                        if panel.streamers_list.item(i).text() == streamer_params:
                            panel.streamers_list.setCurrentRow(i)
                            break

                # Remove streamer
                if hasattr(panel, "delete_selected_streamer"):
                    panel.delete_selected_streamer()
                    return True
                return False

            return self._execute_safely(_remove_streamer)

        except Exception as e:
            logging.error(f"Error removing streamer via API: {e}")
            return False

    def send_board_config(self, config_cmd: str) -> bool:
        """Send board configuration via API."""
        try:

            def _send_config() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "streaming_panel"
                ):
                    return False

                panel = self.main_app.streaming_panel

                # Set config command
                if hasattr(panel, "config_cmd_edit"):
                    panel.config_cmd_edit.setText(config_cmd)

                # Send config
                if hasattr(panel, "send_board_config"):
                    panel.send_board_config()
                    return True
                return False

            return self._execute_safely(_send_config)

        except Exception as e:
            logging.error(f"Error sending board config via API: {e}")
            return False

    # MNE Panel Methods
    def convert_to_mne(self, duration: int = 5) -> bool:
        """Convert data to MNE format via API."""
        try:

            def _convert_to_mne() -> bool:
                if self.main_app is None or not hasattr(self.main_app, "mne_panel"):
                    return False

                panel = self.main_app.mne_panel

                # Set duration
                if hasattr(panel, "mne_duration_spin"):
                    panel.mne_duration_spin.setValue(duration)

                # Convert to MNE
                if hasattr(panel, "convert_to_mne"):
                    panel.convert_to_mne()
                    return True
                return False

            return self._execute_safely(_convert_to_mne)

        except Exception as e:
            logging.error(f"Error converting to MNE via API: {e}")
            return False

    def plot_mne_visualization(self, plot_type: str) -> bool:
        """Plot MNE visualization via API."""
        try:

            def _plot_visualization() -> bool:
                if self.main_app is None or not hasattr(self.main_app, "mne_panel"):
                    return False

                panel = self.main_app.mne_panel

                if hasattr(panel, "plot_mne_visualization"):
                    panel.plot_mne_visualization(plot_type)
                    return True
                return False

            return self._execute_safely(_plot_visualization)

        except Exception as e:
            logging.error(f"Error plotting MNE visualization via API: {e}")
            return False

    # Advanced Panel Methods
    def compute_ica(self, components: int, channel: int = -1) -> bool:
        """Compute ICA via API."""
        try:

            def _compute_ica() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "advanced_panel"
                ):
                    return False

                panel = self.main_app.advanced_panel

                # Set parameters
                if hasattr(panel, "ica_components_spin"):
                    panel.ica_components_spin.setValue(components)

                if hasattr(panel, "ica_channel_combo"):
                    self._set_combo_by_data(panel.ica_channel_combo, channel)

                # Compute ICA
                if hasattr(panel, "compute_ica"):
                    panel.compute_ica()
                    return True
                return False

            return self._execute_safely(_compute_ica)

        except Exception as e:
            logging.error(f"Error computing ICA via API: {e}")
            return False

    def compute_wavelet(self, wavelet_type: int, level: int, channel: int) -> bool:
        """Compute wavelet transform via API."""
        try:

            def _compute_wavelet() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "advanced_panel"
                ):
                    return False

                panel = self.main_app.advanced_panel

                # Set parameters
                if hasattr(panel, "wavelet_type_combo"):
                    self._set_combo_by_data(panel.wavelet_type_combo, wavelet_type)

                if hasattr(panel, "wavelet_level_spin"):
                    panel.wavelet_level_spin.setValue(level)

                if hasattr(panel, "wavelet_channel_combo"):
                    self._set_combo_by_data(panel.wavelet_channel_combo, channel)

                # Compute wavelet
                if hasattr(panel, "compute_wavelet"):
                    panel.compute_wavelet()
                    return True
                return False

            return self._execute_safely(_compute_wavelet)

        except Exception as e:
            logging.error(f"Error computing wavelet via API: {e}")
            return False

    # Status and State Methods
    def show_status_message(self, message: str) -> bool:
        """Show status message via API."""
        try:

            def _show_status() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "show_status_message"
                ):
                    return False

                self.main_app.show_status_message(message)
                return True

            return self._execute_safely(_show_status)

        except Exception as e:
            logging.error(f"Error showing status message via API: {e}")
            return False

    def update_visualization_button(self, enabled: bool) -> bool:
        """Update visualization button state via API."""
        try:

            def _update_viz_button() -> bool:
                if self.main_app is None or not hasattr(
                    self.main_app, "connection_panel"
                ):
                    return False

                panel = self.main_app.connection_panel

                if hasattr(panel, "update_visualization_button"):
                    panel.update_visualization_button(enabled)
                    return True
                return False

            return self._execute_safely(_update_viz_button)

        except Exception as e:
            logging.error(f"Error updating visualization button via API: {e}")
            return False

    # Utility Methods
    def _set_combo_by_data(self, combo: Any, data_value: Any) -> None:
        """Set combo box selection by data value."""
        try:
            for i in range(combo.count()):
                if combo.itemData(i) == data_value:
                    combo.setCurrentIndex(i)
                    break
        except Exception as e:
            logging.error(f"Error setting combo value: {e}")

    def _update_all_panels_connection_state(self, connected: bool) -> None:
        """Update connection state across all panels."""
        try:
            if self.main_app is None:
                return

            # Update connection panel
            if hasattr(self.main_app, "connection_panel"):
                panel = self.main_app.connection_panel
                if hasattr(panel, "_update_connection_state"):
                    panel._update_connection_state(connected)

            # Update processing panel
            if hasattr(self.main_app, "processing_panel"):
                panel = self.main_app.processing_panel
                if hasattr(panel, "enable_processing"):
                    panel.enable_processing(connected)

            # Update recording panel
            if hasattr(self.main_app, "recording_panel"):
                panel = self.main_app.recording_panel
                if hasattr(panel, "enable_recording"):
                    panel.enable_recording(connected)

            # Update streaming panel
            if hasattr(self.main_app, "streaming_panel"):
                panel = self.main_app.streaming_panel
                if hasattr(panel, "enable_streaming"):
                    panel.enable_streaming(connected)

            # Update MNE panel
            if hasattr(self.main_app, "mne_panel"):
                panel = self.main_app.mne_panel
                if hasattr(panel, "enable_processing"):
                    panel.enable_processing(connected)

            # Update advanced panel
            if hasattr(self.main_app, "advanced_panel"):
                panel = self.main_app.advanced_panel
                if hasattr(panel, "enable_processing"):
                    panel.enable_processing(connected)

        except Exception as e:
            logging.error(f"Error updating panel states: {e}")

    def get_connection_settings(self) -> Dict[str, Any]:
        """Get current connection settings."""
        try:

            def _get_settings() -> Dict[str, Any]:
                if self.main_app is None or not hasattr(
                    self.main_app, "connection_panel"
                ):
                    return {}

                panel = self.main_app.connection_panel

                if hasattr(panel, "get_connection_settings"):
                    return panel.get_connection_settings()
                return {}

            return self._execute_safely(_get_settings)

        except Exception as e:
            logging.error(f"Error getting connection settings: {e}")
            return {}

    def get_filter_settings(self) -> Dict[str, Any]:
        """Get current filter settings."""
        try:

            def _get_settings() -> Dict[str, Any]:
                if self.main_app is None or not hasattr(
                    self.main_app, "processing_panel"
                ):
                    return {}

                panel = self.main_app.processing_panel

                if hasattr(panel, "get_filter_settings"):
                    return panel.get_filter_settings()
                return {}

            return self._execute_safely(_get_settings)

        except Exception as e:
            logging.error(f"Error getting filter settings: {e}")
            return {}

    def get_recording_settings(self) -> Dict[str, Any]:
        """Get current recording settings."""
        try:

            def _get_settings() -> Dict[str, Any]:
                if self.main_app is None or not hasattr(
                    self.main_app, "recording_panel"
                ):
                    return {}

                panel = self.main_app.recording_panel

                if hasattr(panel, "get_recording_settings"):
                    return panel.get_recording_settings()
                return {}

            return self._execute_safely(_get_settings)

        except Exception as e:
            logging.error(f"Error getting recording settings: {e}")
            return {}

    def __del__(self) -> None:
        """Cleanup when adapter is destroyed."""
        try:
            if hasattr(self, "_executor"):
                self._executor.shutdown(wait=False)
        except Exception:
            pass  # Ignore cleanup errors
