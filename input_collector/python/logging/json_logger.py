"""
JSON logger module.

Provides functionality for logging input events to JSON format.
"""

import json
import os
import time
from datetime import datetime
from typing import Optional, TextIO, Dict, Any

from PyQt5.QtCore import QObject, pyqtSignal

from ..interfaces import InputData


class JSONLogger(QObject):
    """
    Logger for input events in JSON format.

    This class handles logging input events to JSON files with proper
    formatting and structure.
    """

    status_message = pyqtSignal(str, str)  # message, color

    def __init__(self) -> None:
        """Initialize the JSON logger."""
        super().__init__()
        self.log_file: Optional[TextIO] = None

    def open_log(self) -> bool:
        """
        Open a new JSON log file.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create log file with timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(time.time()))
            filename = f"input_log_{timestamp}.json"

            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

            # Open the file
            self.log_file = open(filename, "w")
            self.status_message.emit(f"Logging to {filename}", None)
            return True
        except Exception as e:
            self.status_message.emit(f"Error opening JSON log file: {e}", "#FF5555")
            return False

    def close_log(self) -> None:
        """Close the current log file."""
        if self.log_file:
            try:
                self.log_file.close()
            except Exception:
                pass
            self.log_file = None

    def log_recording_start(self) -> None:
        """Log the start of a recording session."""
        if not self.log_file:
            return

        try:
            self.log_file.write(
                f'{{\n"event": "recording_started",\n"timestamp": {time.time()}\n}}\n'
            )
            self.log_file.flush()
        except Exception as e:
            self.status_message.emit(f"Error writing to JSON log: {e}", "#FF5555")

    def log_recording_stop(self) -> None:
        """Log the end of a recording session."""
        if not self.log_file:
            return

        try:
            self.log_file.write(
                f'{{\n"event": "recording_stopped",\n"timestamp": {time.time()}\n}}\n'
            )
            self.log_file.flush()
        except Exception as e:
            self.status_message.emit(f"Error writing to JSON log: {e}", "#FF5555")

    def log_event(self, event: InputData, collector_type: str) -> None:
        """
        Log an input event.

        Args:
            event: The input event to log
            collector_type: Type of collector that generated the event
        """
        if not self.log_file:
            return

        try:
            if collector_type == "keyboard_mouse":
                self._log_keyboard_mouse_event(event)
            elif collector_type == "ps4_controller":
                self._log_ps4_event(event)
        except Exception as e:
            self.status_message.emit(f"Error writing to JSON log: {e}", "#FF5555")

    def _log_keyboard_mouse_event(self, event: InputData) -> None:
        """Log a keyboard/mouse event to JSON."""
        # Determine current tracking mode
        tracking_mode = getattr(event, "mouse_tracking_mode", "joystick")

        # Convert scroll direction to numeric value
        scroll_value = 0
        if event.event_type == "mouse_scroll" and event.direction is not None:
            scroll_value = 1 if event.direction == "up" else -1

        # Create a simplified log structure
        clean_log: Dict[str, Any] = {
            "timestamp": event.timestamp,
            "mode": tracking_mode,
            "keyboard": {"keys": event.active_keys or []},
            "mouse": {
                "buttons": [event.button_pressed] if event.button_pressed else []
            },
        }

        # Add scroll_direction if there's actual scrolling
        if scroll_value != 0:
            clean_log["mouse"]["scroll_direction"] = scroll_value

        # Add tracking mode specific data
        if tracking_mode == "joystick":
            clean_log["mouse"]["rel_x"] = (
                event.rel_x if event.rel_x is not None else 0.0
            )
            clean_log["mouse"]["rel_y"] = (
                event.rel_y if event.rel_y is not None else 0.0
            )
            clean_log["mouse"]["speed"] = (
                event.speed if event.speed is not None else 0.0
            )
        elif tracking_mode == "delta":
            clean_log["mouse"]["delta_x"] = getattr(event, "mouse_delta_x", 0.0)
            clean_log["mouse"]["delta_y"] = getattr(event, "mouse_delta_y", 0.0)
        elif tracking_mode == "angle":
            if getattr(event, "direction_only", False):
                clean_log["mouse"]["discrete_angle"] = getattr(
                    event, "discrete_angle", 0
                )
            else:
                clean_log["mouse"]["angle"] = getattr(event, "mouse_delta_angle", 0.0)
                clean_log["mouse"]["magnitude"] = getattr(
                    event, "mouse_delta_magnitude", 0.0
                )
        elif tracking_mode == "axis":
            clean_log["mouse"]["north"] = getattr(event, "north", 0.0)
            clean_log["mouse"]["south"] = getattr(event, "south", 0.0)
            clean_log["mouse"]["east"] = getattr(event, "east", 0.0)
            clean_log["mouse"]["west"] = getattr(event, "west", 0.0)

        # Write to file and flush
        if self.log_file is not None:
            self.log_file.write(json.dumps(clean_log) + "\n")
            self.log_file.flush()

    def _log_ps4_event(self, event: InputData) -> None:
        """Log a PS4 controller event to JSON."""
        if self.log_file is None:
            return

        try:
            timestamp_str = datetime.fromtimestamp(event.timestamp).strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )

            # Create base log entry
            log_entry: Dict[str, Any] = {
                "timestamp": timestamp_str,
                "event_type": event.event_type,
                "collector": "ps4_controller",
                "active_keys": event.active_keys,
            }

            # Add specific details for different event types
            if (
                event.event_type == "button_press"
                or event.event_type == "button_release"
            ):
                log_entry["button"] = event.key
                log_entry["pressed"] = event.event_type == "button_press"

            elif event.event_type == "axis_motion":
                if event.key is not None and "Stick" in event.key:
                    # Analog stick movement
                    log_entry["stick"] = event.key.replace("_X", "")
                    log_entry["x"] = event.rel_x
                    log_entry["y"] = event.rel_y
                elif event.key is not None and "Trigger" in event.key:
                    # Trigger movement
                    log_entry["trigger"] = event.key
                    log_entry["value"] = event.rel_x

            elif event.event_type == "controller_connected":
                log_entry["controller_name"] = event.key

            # Write to file
            self.log_file.write(json.dumps(log_entry) + ",\n")
            self.log_file.flush()

        except Exception as e:
            self.status_message.emit(f"Error logging PS4 event to JSON: {e}", "#FF5555")
