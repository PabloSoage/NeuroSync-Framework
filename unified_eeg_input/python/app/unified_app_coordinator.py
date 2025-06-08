"""
Unified application coordinator.

This module coordinates between the EEG processor and input collector applications.
"""

from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal


class UnifiedAppCoordinator(QObject):
    """
    Coordinates actions between EEG processor and input collector.

    This class is responsible for synchronizing recording operations and
    maintaining the integrated state of the application.
    """

    # Signals
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    status_message = pyqtSignal(str, str)  # message, color

    def __init__(self, integration_service: Any) -> None:
        """Initialize the unified app coordinator."""
        super().__init__()
        self.integration_service = integration_service
        self.main_window = None

        # Recording state
        self.is_recording = False

        # Connect signals from integration service
        self.integration_service.status_message.connect(self.status_message)

    def set_main_window(self, main_window: Any) -> None:
        """Set the main window reference."""
        self.main_window = main_window

    def start_recording(self, record_config: Dict[str, Any]) -> None:
        """
        Start recording on both modules if enabled.

        Args:
            record_config: Dictionary with recording configuration
        """
        if self.is_recording:
            self.status_message.emit("Already recording", "warning")
            return

        # Start recording based on configuration
        success = self.integration_service.start_recording(record_config)

        if success:
            self.is_recording = True
            self.recording_started.emit()
            self.status_message.emit("Recording started", "success")
        else:
            self.status_message.emit("Failed to start recording", "error")

    def stop_recording(self) -> None:
        """Stop recording on both modules."""
        if not self.is_recording:
            self.status_message.emit("Not recording", "warning")
            return

        # Stop recording
        success = self.integration_service.stop_recording()

        if success:
            self.is_recording = False
            self.recording_stopped.emit()
            self.status_message.emit("Recording stopped", "success")
        else:
            self.status_message.emit("Failed to stop recording", "error")

    def add_marker(self, marker_value: Any) -> None:
        """
        Add a marker to both recordings.

        Args:
            marker_value: Value of the marker
        """
        if not self.is_recording:
            self.status_message.emit("Not recording", "warning")
            return

        success = self.integration_service.add_marker(marker_value)

        if success:
            self.status_message.emit(f"Marker {marker_value} added", "success")
        else:
            self.status_message.emit("Failed to add marker", "error")

    def handle_tab_change(self, index: int) -> None:
        """
        Handle tab change event.

        Args:
            index: Index of the selected tab
        """
        # Any actions needed when switching between tabs
        pass

    def is_ready_for_recording(self) -> bool:
        """
        Check if the system is ready for recording.

        Returns:
            bool: True if ready for recording
        """
        return self.integration_service.is_ready_for_recording()

    def update_recording_controls(self) -> None:
        """Update recording controls in the UI."""
        if self.main_window:
            self.main_window.update_recording_controls(
                self.is_recording, self.is_ready_for_recording()
            )
