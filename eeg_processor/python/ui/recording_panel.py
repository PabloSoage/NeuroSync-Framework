import logging
from typing import Any, Optional, Dict

from PyQt5.QtCore import pyqtSignal, QObject, QTimer
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QLineEdit,
    QRadioButton,
    QSpinBox,
    QFileDialog,
)

from .base_panel import BasePanel
from ..utils.help_system import HelpButton


class ApiEventHandler(QObject):
    """Thread-safe handler for API events."""

    recording_start_signal = pyqtSignal(dict)
    recording_stop_signal = pyqtSignal()
    recording_status_changed_signal = pyqtSignal(dict)

    def __init__(self) -> None:
        super().__init__()


class RecordingPanel(BasePanel):
    """Panel for recording EEG data."""

    # Define signals specific to recording panel
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()

    def __init__(
        self,
        collector_service: Any,
        recording_service: Any,
        parent: Optional[Any] = None,
    ) -> None:
        """Initialize the recording panel."""
        super().__init__(parent)
        self.collector_service = collector_service
        self.recording_service = recording_service

        # Setup thread-safe event handler
        self.api_event_handler = ApiEventHandler()
        self.api_event_handler.recording_start_signal.connect(
            self._handle_api_recording_start_safe
        )
        self.api_event_handler.recording_stop_signal.connect(
            self._handle_api_recording_stop_safe
        )
        self.api_event_handler.recording_status_changed_signal.connect(
            self._handle_api_recording_status_changed_safe
        )

        # Setup event system subscriptions for API synchronization
        self._setup_event_subscriptions()

        # Setup UI components
        self.setup_recording_controls()
        self.setup_marker_controls()
        self.setup_status_display()

        # Timer for updating recording status (only when recording from GUI)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_recording_status)
        # Don't start timer automatically - only when needed

        # Add stretch to push everything to the top
        self.layout.addStretch()

    def _setup_event_subscriptions(self) -> None:
        """Setup subscriptions for API-generated events."""
        try:
            from ..core.event_system import EventDispatcher, EventType

            event_dispatcher = EventDispatcher.get_instance()

            # Subscribe to recording events from API
            event_dispatcher.subscribe(
                EventType.RECORDING_START, self._handle_api_recording_start_thread_safe
            )
            event_dispatcher.subscribe(
                EventType.RECORDING_STOP, self._handle_api_recording_stop_thread_safe
            )
            event_dispatcher.subscribe(
                EventType.RECORDING_STATUS_CHANGED,
                self._handle_api_recording_status_changed_thread_safe,
            )

        except Exception as e:
            logging.error(
                f"Error setting up event subscriptions in recording panel: {e}"
            )

    def _handle_api_recording_start_thread_safe(self, event: Any) -> None:
        """Handle recording start events from API in a thread-safe way."""
        try:
            event_data = event.data
            logging.info(
                f"Recording panel received API recording start event: {event_data}"
            )

            # Emit signal to handle in main thread
            self.api_event_handler.recording_start_signal.emit(event_data)

        except Exception as e:
            logging.error(f"Error handling API recording start event thread-safe: {e}")

    def _handle_api_recording_stop_thread_safe(self, event: Any) -> None:
        """Handle recording stop events from API in a thread-safe way."""
        try:
            logging.info("Recording panel received API recording stop event")

            # Emit signal to handle in main thread
            self.api_event_handler.recording_stop_signal.emit()

        except Exception as e:
            logging.error(f"Error handling API recording stop event thread-safe: {e}")

    def _handle_api_recording_status_changed_thread_safe(self, event: Any) -> None:
        """Handle recording status changed events from API in a thread-safe way."""
        try:
            event_data = event.data
            logging.info(
                f"Recording panel received API recording status changed event: {event_data}"
            )

            # Emit signal to handle in main thread
            self.api_event_handler.recording_status_changed_signal.emit(event_data)

        except Exception as e:
            logging.error(
                f"Error handling API recording status changed event thread-safe: {e}"
            )

    def _handle_api_recording_start_safe(self, event_data: Dict[str, Any]) -> None:
        """Handle recording start events from API safely in main thread."""
        try:
            logging.info(
                f"Recording panel updating controls for recording start: {event_data}"
            )

            # Update the UI controls to reflect the API recording start
            filename = event_data.get("filename", "")
            data_type = event_data.get("data_type", "raw")

            # Update filename field
            if hasattr(self, "record_file_edit") and filename:
                self.record_file_edit.setText(filename)

            # Update data type radio buttons
            if (
                hasattr(self, "raw_radio")
                and hasattr(self, "processed_radio")
                and hasattr(self, "both_radio")
            ):
                if data_type == "processed":
                    self.processed_radio.setChecked(True)
                elif data_type == "both":
                    self.both_radio.setChecked(True)
                else:
                    self.raw_radio.setChecked(True)

            # Update button states
            self._update_recording_state(True)

            # Start timer to update duration
            self.status_timer.start(1000)  # Update every second

            self.show_status(f"Recording started via API: {filename}")

        except Exception as e:
            logging.error(f"Error handling API recording start event safely: {e}")

    def _handle_api_recording_stop_safe(self) -> None:
        """Handle recording stop events from API safely in main thread."""
        try:
            logging.info("Recording panel updating controls for recording stop")

            # Update button states
            self._update_recording_state(False)

            # Stop timer
            self.status_timer.stop()

            self.show_status("Recording stopped via API")

        except Exception as e:
            logging.error(f"Error handling API recording stop event safely: {e}")

    def _handle_api_recording_status_changed_safe(
        self, event_data: Dict[str, Any]
    ) -> None:
        """Handle recording status changed events from API safely in main thread."""
        try:
            recording = event_data.get("recording", False)
            filename = event_data.get("filename", "")

            logging.info(
                f"Recording panel updating status: recording={recording}, filename={filename}"
            )

            # Update recording state
            self._update_recording_state(recording)

            if recording:
                # Start timer if not already running
                if not self.status_timer.isActive():
                    self.status_timer.start(1000)
                self.show_status(f"Recording status updated: {filename}")
            else:
                # Stop timer
                self.status_timer.stop()
                self.show_status("Recording status updated: Not recording")

        except Exception as e:
            logging.error(
                f"Error handling API recording status changed event safely: {e}"
            )

    def _update_recording_state(self, recording: bool) -> None:
        """Update UI controls based on recording state."""
        try:
            # Update button states
            if hasattr(self, "start_record_btn"):
                self.start_record_btn.setEnabled(not recording)

            if hasattr(self, "stop_record_btn"):
                self.stop_record_btn.setEnabled(recording)

            # Update status display
            if recording:
                # Get current recording info from service
                if hasattr(self, "recording_service"):
                    filename = self.recording_service.get_recording_filename()
                    data_type = self.recording_service.get_recording_data_type()
                    duration = self.recording_service.get_recording_duration()

                    status_text = (
                        f"Recording: {filename} ({data_type}) - {duration:.1f}s"
                    )
                    if hasattr(self, "recording_status_label"):
                        self.recording_status_label.setText(status_text)
            else:
                if hasattr(self, "recording_status_label"):
                    self.recording_status_label.setText("Not recording")

        except Exception as e:
            logging.error(f"Error updating recording state: {e}")

    def setup_recording_controls(self) -> None:
        """Set up recording controls group."""
        record_group = QGroupBox("Recording Controls")
        record_layout = QVBoxLayout(record_group)

        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("File:"))
        self.record_file_edit = QLineEdit()
        self.record_file_edit.setPlaceholderText("Enter filename or browse...")
        file_layout.addWidget(self.record_file_edit)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        file_layout.addWidget(HelpButton("recording_file", self))
        record_layout.addLayout(file_layout)

        # Data type selection
        data_type_layout = QHBoxLayout()
        data_type_layout.addWidget(QLabel("Data Type:"))

        self.raw_radio = QRadioButton("Raw")
        self.raw_radio.setChecked(True)
        data_type_layout.addWidget(self.raw_radio)

        self.processed_radio = QRadioButton("Processed")
        data_type_layout.addWidget(self.processed_radio)

        self.both_radio = QRadioButton("Both")
        data_type_layout.addWidget(self.both_radio)

        data_type_layout.addWidget(HelpButton("recording_data_type", self))
        record_layout.addLayout(data_type_layout)

        # Recording buttons
        button_layout = QHBoxLayout()
        self.start_record_btn = QPushButton("Start Recording")
        self.start_record_btn.clicked.connect(self.start_recording)
        self.start_record_btn.setEnabled(False)
        button_layout.addWidget(self.start_record_btn)

        self.stop_record_btn = QPushButton("Stop Recording")
        self.stop_record_btn.clicked.connect(self.stop_recording)
        self.stop_record_btn.setEnabled(False)
        button_layout.addWidget(self.stop_record_btn)
        record_layout.addLayout(button_layout)

        self.layout.addWidget(record_group)

    def setup_marker_controls(self) -> None:
        """Set up marker controls group."""
        marker_group = QGroupBox("Event Markers")
        marker_layout = QVBoxLayout(marker_group)

        # Marker value input
        marker_input_layout = QHBoxLayout()
        marker_input_layout.addWidget(QLabel("Marker Value:"))

        self.marker_value_spin = QSpinBox()
        self.marker_value_spin.setRange(1, 999)
        self.marker_value_spin.setValue(1)
        marker_input_layout.addWidget(self.marker_value_spin)

        # Add marker button
        self.add_marker_btn = QPushButton("Add Marker")
        self.add_marker_btn.clicked.connect(self.add_marker)
        self.add_marker_btn.setEnabled(False)
        marker_input_layout.addWidget(self.add_marker_btn)

        marker_input_layout.addWidget(HelpButton("event_markers", self))
        marker_layout.addLayout(marker_input_layout)

        self.layout.addWidget(marker_group)

    def setup_status_display(self) -> None:
        """Set up recording status display."""
        status_group = QGroupBox("Recording Status")
        status_layout = QVBoxLayout(status_group)

        self.recording_status_label = QLabel("Not recording")
        status_layout.addWidget(self.recording_status_label)

        self.layout.addWidget(status_group)

    def update_recording_status(self) -> None:
        """Update recording status display - called by timer."""
        try:
            if self.recording_service.is_recording():
                filename = self.recording_service.get_recording_filename()
                data_type = self.recording_service.get_recording_data_type()
                duration = self.recording_service.get_recording_duration()

                status_text = f"Recording: {filename} ({data_type}) - {duration:.1f}s"
                self.recording_status_label.setText(status_text)
            else:
                self.recording_status_label.setText("Not recording")
                # Stop timer if recording stopped
                if self.status_timer.isActive():
                    self.status_timer.stop()
        except Exception as e:
            logging.error(f"Error updating recording status: {e}")

    def browse_file(self) -> None:
        """Open file browser for recording file selection."""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Recording As",
                "",
                "CSV Files (*.csv);;All Files (*)",
            )
            if filename:
                self.record_file_edit.setText(filename)
        except Exception as e:
            self.show_error("File Browser Error", f"Error opening file browser: {e}")

    def start_recording(self) -> None:
        """Start recording."""
        try:
            filename = self.record_file_edit.text().strip()
            if not filename:
                self.show_error("Recording Error", "Please specify a filename")
                return

            # Determine data type
            if self.processed_radio.isChecked():
                data_type = "processed"
            elif self.both_radio.isChecked():
                data_type = "both"
            else:
                data_type = "raw"

            success = self.recording_service.start_recording(filename, data_type)

            if success:
                self._update_recording_state(True)
                self.status_timer.start(1000)  # Start timer for GUI-initiated recording
                self.show_status(f"Recording started: {filename}")

                # Emit signal for app-level handling
                self.recording_started.emit()
            else:
                self.show_error("Recording Error", "Failed to start recording")

        except Exception as e:
            self.show_error("Recording Error", f"Error starting recording: {e}")

    def stop_recording(self) -> None:
        """Stop recording."""
        try:
            success = self.recording_service.stop_recording()

            if success:
                self._update_recording_state(False)
                self.status_timer.stop()
                self.show_status("Recording stopped")

                # Emit signal for app-level handling
                self.recording_stopped.emit()
            else:
                self.show_error("Recording Error", "Failed to stop recording")

        except Exception as e:
            self.show_error("Recording Error", f"Error stopping recording: {e}")

    def add_marker(self) -> None:
        """Add an event marker."""
        try:
            marker_value = self.marker_value_spin.value()
            success = self.recording_service.insert_marker(marker_value)

            if success:
                self.show_status(f"Marker {marker_value} added")
            else:
                self.show_error("Marker Error", "Failed to add marker")

        except Exception as e:
            self.show_error("Marker Error", f"Error adding marker: {e}")

    def enable_recording(self, enabled: bool) -> None:
        """Enable or disable recording controls."""
        # Only enable start button if not currently recording
        recording = (
            self.recording_service.is_recording()
            if hasattr(self, "recording_service")
            else False
        )

        self.start_record_btn.setEnabled(enabled and not recording)
        self.stop_record_btn.setEnabled(enabled and recording)
        self.add_marker_btn.setEnabled(enabled and recording)

        # Update status when enabling/disabling
        if enabled and recording:
            # Start timer if recording is active
            if not self.status_timer.isActive():
                self.status_timer.start(1000)
        elif not enabled:
            # Stop timer if disabled
            self.status_timer.stop()
