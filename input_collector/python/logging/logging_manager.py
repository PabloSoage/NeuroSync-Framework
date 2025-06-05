"""
Logging manager module.

Manages all logging functionality for the input collector application,
including JSON and CSV logging facilities.
"""

from typing import Optional, List

from PyQt5.QtCore import QObject, pyqtSignal

from .csv_logger import CSVLogger
from .json_logger import JSONLogger
from ..interfaces import InputData


class LoggingManager(QObject):
    """
    Manages logging of input events to different formats.

    This class centralizes all logging functionality, providing a unified interface
    for logging input events to various formats such as JSON and CSV.
    """

    status_message = pyqtSignal(str, str)  # message, color

    def __init__(self) -> None:
        """Initialize the logging manager."""
        super().__init__()
        self.json_logger = JSONLogger()
        self.csv_logger = CSVLogger()

        # Connect internal signals
        self.json_logger.status_message.connect(self._relay_status_message)
        self.csv_logger.status_message.connect(self._relay_status_message)

        # Logging state
        self.log_to_json = False
        self.log_to_csv = False

    def set_json_logging(self, enabled: bool) -> bool:
        """
        Enable or disable JSON logging.

        Args:
            enabled: Whether to enable JSON logging

        Returns:
            bool: True if the operation was successful
        """
        if enabled == self.log_to_json:
            return True

        self.log_to_json = enabled

        if enabled:
            success = self.json_logger.open_log()
            if not success:
                self.log_to_json = False
                return False
        else:
            self.json_logger.close_log()

        return True

    def set_csv_logging(self, enabled: bool, filepath: Optional[str] = None) -> bool:
        """
        Enable or disable CSV logging.

        Args:
            enabled: Whether to enable CSV logging
            filepath: Path to the CSV file (required when enabling)

        Returns:
            bool: True if the operation was successful
        """
        if enabled == self.log_to_csv:
            return True

        self.log_to_csv = enabled

        if enabled:
            if filepath:
                self.csv_logger.set_filepath(filepath)
            return True
        else:
            self.csv_logger.close_log()
            return True

    def initialize_csv_file(
        self,
        headers: List[str],
        tracked_keys: List[str],
        tracking_mode: str,
        direction_only: bool,
    ) -> bool:
        """
        Initialize the CSV file with headers.

        Args:
            headers: List of column headers
            tracked_keys: List of tracked keys
            tracking_mode: Mouse tracking mode
            direction_only: Whether direction-only mode is enabled

        Returns:
            bool: True if initialization was successful
        """
        if not self.log_to_csv:
            return False

        return self.csv_logger.initialize(
            headers, tracked_keys, tracking_mode, direction_only
        )

    def log_event(self, event: InputData, collector_type: str) -> None:
        """
        Log an input event.

        Args:
            event: The input event to log
            collector_type: Type of collector that generated the event
        """
        if self.log_to_json:
            self.json_logger.log_event(event, collector_type)

        if self.log_to_csv:
            self.csv_logger.log_event(event, collector_type)

    def start_recording(self) -> None:
        """Record the start of a recording session."""
        if self.log_to_json:
            self.json_logger.log_recording_start()

    def stop_recording(self) -> None:
        """Record the end of a recording session."""
        if self.log_to_json:
            self.json_logger.log_recording_stop()

        if self.log_to_csv:
            self.csv_logger.close_log()

    def close_all(self) -> None:
        """Close all open log files."""
        self.json_logger.close_log()
        self.csv_logger.close_log()

    def _relay_status_message(self, message: str, color: str = None) -> None:
        """Relay status messages from loggers to the application."""
        self.status_message.emit(message, color)
