import logging
import time
from typing import Any, Dict, Optional

import numpy as np
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from ..data_access_service import DataAccessService


class ICARealtimeService(QObject):
    """
    Service for real-time ICA computation and visualization.

    This service maintains a sliding window of EEG data and periodically
    recomputes ICA components for live monitoring.
    """

    # Signals for real-time updates
    realtime_ica_updated = pyqtSignal(dict, str)  # ica_components, message
    realtime_status_changed = pyqtSignal(bool, str)  # is_active, message
    realtime_error = pyqtSignal(str)  # error_message

    def __init__(self) -> None:
        """Initialize the ICA realtime service."""
        super().__init__()

        # Data access service
        self._data_access_service = DataAccessService.get_instance()

        # Realtime state
        self._is_active = False
        self._update_interval = 1.0  # seconds
        self._window_size = 5.0  # seconds of data to analyze

        # Realtime timer
        self._realtime_timer = QTimer()
        self._realtime_timer.timeout.connect(self._update_realtime_ica)

        # ICA parameters
        self._ica_params = {
            "num_components": 2,
            "selected_channels": [],
            "window_samples": 1000,
        }

        # Data buffer (sliding window)
        self._data_buffer: Optional[np.ndarray] = None
        self._buffer_size = 0
        self._sampling_rate = 0.0

        # Current realtime results
        self._current_realtime_results: Optional[Dict[str, Any]] = None

    def initialize(self, processor_service: Any) -> bool:
        """Initialize the realtime service."""
        try:
            self._processor_service = processor_service

            # Get sampling rate
            self._sampling_rate = self._data_access_service.get_sampling_rate()
            if self._sampling_rate <= 0:
                logging.warning("Invalid sampling rate for ICA realtime service")
                return False

            # Calculate buffer size based on window size
            self._buffer_size = int(self._window_size * self._sampling_rate)

            logging.info(
                f"ICA realtime service initialized (buffer: {self._buffer_size} samples)"
            )
            return True

        except Exception as e:
            logging.error(f"Error initializing ICA realtime service: {e}")
            return False

    def start_realtime_ica(self, ica_params: Dict[str, Any]) -> bool:
        """
        Start real-time ICA computation.

        Args:
            ica_params: Dictionary with ICA parameters
                num_components: Number of components to extract
                selected_channels: List of channel indices
                update_interval: Update interval in seconds (0.5-2.0)

        Returns:
            Boolean indicating success
        """
        try:
            if self._is_active:
                self.stop_realtime_ica()

            # Validate parameters
            num_components = ica_params.get("num_components", 2)
            selected_channels = ica_params.get("selected_channels", [])
            update_interval = ica_params.get("update_interval", 1.0)

            # Validate update interval
            if not (0.5 <= update_interval <= 2.0):
                self.realtime_error.emit(
                    "Update interval must be between 0.5 and 2.0 seconds"
                )
                return False

            # Validate channels
            if not selected_channels:
                self.realtime_error.emit(
                    "Please select at least one channel for real-time ICA"
                )
                return False

            if len(selected_channels) < num_components:
                self.realtime_error.emit(
                    f"Number of selected channels ({len(selected_channels)}) must be >= number of components ({num_components})"
                )
                return False

            # Update parameters
            self._ica_params = {
                "num_components": num_components,
                "selected_channels": selected_channels.copy(),
                "window_samples": self._buffer_size,
            }
            self._update_interval = update_interval

            # Initialize data buffer
            num_channels = len(selected_channels)
            self._data_buffer = np.zeros((num_channels, self._buffer_size))

            # Start timer
            timer_interval_ms = int(update_interval * 1000)
            self._realtime_timer.start(timer_interval_ms)

            self._is_active = True

            message = f"Real-time ICA started: {num_components} components, {len(selected_channels)} channels, {update_interval}s interval"
            self.realtime_status_changed.emit(True, message)
            logging.info(message)

            return True

        except Exception as e:
            error_msg = f"Error starting real-time ICA: {str(e)}"
            logging.error(error_msg)
            self.realtime_error.emit(error_msg)
            return False

    def stop_realtime_ica(self) -> None:
        """Stop real-time ICA computation."""
        try:
            # Stop timer first to prevent new updates
            if self._realtime_timer.isActive():
                self._realtime_timer.stop()

            # Clear flag immediately to prevent pending updates
            self._is_active = False

            # Clear data buffer to prevent memory usage
            self._data_buffer = None
            self._current_realtime_results = None

            # Wait a bit for any pending operations to complete
            import time

            time.sleep(0.1)

            self.realtime_status_changed.emit(False, "Real-time ICA stopped")
            logging.info("Real-time ICA stopped")

        except Exception as e:
            logging.error(f"Error stopping real-time ICA: {e}")

    def update_interval(self, new_interval: float) -> bool:
        """
        Update the real-time update interval.

        Args:
            new_interval: New interval in seconds (0.5-2.0)

        Returns:
            Boolean indicating success
        """
        try:
            # Validate interval
            if not (0.5 <= new_interval <= 2.0):
                self.realtime_error.emit(
                    "Update interval must be between 0.5 and 2.0 seconds"
                )
                return False

            self._update_interval = new_interval

            # Restart timer with new interval if active
            if self._is_active:
                self._realtime_timer.stop()
                timer_interval_ms = int(new_interval * 1000)
                self._realtime_timer.start(timer_interval_ms)

                self.realtime_status_changed.emit(
                    True, f"Real-time ICA interval updated to {new_interval}s"
                )

            return True

        except Exception as e:
            logging.error(f"Error updating interval: {e}")
            self.realtime_error.emit(f"Error updating interval: {str(e)}")
            return False

    def _update_realtime_ica(self) -> None:
        """Update real-time ICA computation."""
        # Early exit if not active (prevents buffer lag)
        if not self._is_active:
            return

        try:
            if self._data_buffer is None:
                return

            # Double-check active state (race condition prevention)
            if not self._is_active:
                return

            # Get current data
            current_data, _ = self._data_access_service.get_current_data()
            if current_data.size == 0:
                return

            # Check active state again before processing
            if not self._is_active:
                return

            selected_channels = self._ica_params["selected_channels"]
            if not isinstance(selected_channels, list):
                self.realtime_error.emit("Invalid selected channels configuration")
                return

            # Validate channel indices
            if any(ch >= current_data.shape[0] for ch in selected_channels):
                if self._is_active:  # Only emit error if still supposed to be active
                    self.realtime_error.emit(
                        "Selected channels exceed available channels"
                    )
                    self.stop_realtime_ica()
                return

            # Extract selected channels data
            selected_data = current_data[selected_channels, :]

            # Update sliding window buffer
            self._update_data_buffer(selected_data)

            # Final active check before computation
            if not self._is_active:
                return

            # Check if we have enough data
            num_components = self._ica_params["num_components"]
            if not isinstance(num_components, int):
                self.realtime_error.emit("Invalid num_components configuration")
                return

            min_samples = max(num_components * 100, 500)
            if self._data_buffer.shape[1] < min_samples:
                # Not enough data yet, skip this update
                return

            # Compute ICA on current window
            ica_results = self._compute_window_ica()

            # Check one more time before emitting (prevents late emissions)
            if ica_results and self._is_active:
                self._current_realtime_results = ica_results

                # Emit updated results
                message = f"Real-time ICA updated ({num_components} components)"
                self.realtime_ica_updated.emit(ica_results, message)

        except Exception as e:
            # Only log error if we're supposed to be active
            if self._is_active:
                error_msg = f"Error in real-time ICA update: {str(e)}"
                logging.error(error_msg)
                self.realtime_error.emit(error_msg)
            # Don't stop on single errors, just log them

    def _update_data_buffer(self, new_data: np.ndarray) -> None:
        """
        Update the sliding window data buffer.

        Args:
            new_data: New data to add to buffer (channels x samples)
        """
        try:
            if new_data.shape[1] == 0 or self._data_buffer is None:
                return

            # Determine how much new data to add
            samples_to_add = min(new_data.shape[1], self._buffer_size)

            if samples_to_add >= self._buffer_size:
                # New data is larger than buffer, just use the latest portion
                self._data_buffer = new_data[:, -self._buffer_size :]
            else:
                # Shift existing data and add new data
                shift_amount = samples_to_add
                self._data_buffer[:, :-shift_amount] = self._data_buffer[
                    :, shift_amount:
                ]
                self._data_buffer[:, -shift_amount:] = new_data[:, -samples_to_add:]

        except Exception as e:
            logging.error(f"Error updating data buffer: {e}")

    def _compute_window_ica(self) -> Optional[Dict[str, Any]]:
        """
        Compute ICA on current window data.

        Returns:
            Dictionary with ICA results or None if computation failed
        """
        try:
            # Ensure processor is initialized
            if (
                not hasattr(self._processor_service, "processor")
                or self._processor_service.processor is None
            ):
                self._processor_service.initialize_processor(self._sampling_rate)

            # Compute ICA
            w, k, a, s = self._processor_service.perform_ica(
                self._data_buffer, self._ica_params["num_components"]
            )

            if w is not None:
                ica_components = {
                    "w": w,
                    "k": k,
                    "a": a,
                    "s": s,
                    "selected_channels": self._ica_params["selected_channels"],
                    "num_components": self._ica_params["num_components"],
                    "realtime": True,  # Mark as realtime result
                    "timestamp": time.time(),
                    "window_size": self._window_size,
                    "sampling_rate": self._sampling_rate,
                }

                return ica_components

            return None

        except Exception as e:
            logging.error(f"Error computing window ICA: {e}")
            return None

    def is_active(self) -> bool:
        """Check if real-time ICA is active."""
        return self._is_active

    def get_current_interval(self) -> float:
        """Get current update interval."""
        return self._update_interval

    def get_current_results(self) -> Optional[Dict[str, Any]]:
        """Get current real-time ICA results."""
        return self._current_realtime_results

    def get_window_size(self) -> float:
        """Get current window size in seconds."""
        return self._window_size

    def set_window_size(self, window_size: float) -> bool:
        """
        Set the analysis window size.

        Args:
            window_size: Window size in seconds (2.0-10.0)

        Returns:
            Boolean indicating success
        """
        try:
            # Validate window size
            if not (2.0 <= window_size <= 10.0):
                self.realtime_error.emit(
                    "Window size must be between 2.0 and 10.0 seconds"
                )
                return False

            self._window_size = window_size
            self._buffer_size = int(self._window_size * self._sampling_rate)

            # Reinitialize buffer if active
            if self._is_active:
                selected_channels = self._ica_params.get("selected_channels", [])
                if isinstance(selected_channels, list) and len(selected_channels) > 0:
                    num_channels = len(selected_channels)
                    self._data_buffer = np.zeros((num_channels, self._buffer_size))

                    self.realtime_status_changed.emit(
                        True, f"Real-time ICA window size updated to {window_size}s"
                    )

            return True

        except Exception as e:
            logging.error(f"Error setting window size: {e}")
            self.realtime_error.emit(f"Error setting window size: {str(e)}")
            return False

    def cleanup(self) -> None:
        """Clean up the realtime service."""
        self.stop_realtime_ica()
