"""
JSON logger module.

Provides functionality for logging input events to JSON format.
"""

import json
import time
import os
import math
from typing import Any, Dict, Optional, TextIO
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
        clean_log = {
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
            clean_log["mouse"]["delta_x"] = (
                event.mouse_delta_x if hasattr(event, "mouse_delta_x") else 0.0
            )
            clean_log["mouse"]["delta_y"] = (
                event.mouse_delta_y if hasattr(event, "mouse_delta_y") else 0.0
            )
        elif tracking_mode == "angle":
            if hasattr(event, "direction_only") and event.direction_only:
                clean_log["mouse"]["discrete_angle"] = (
                    event.discrete_angle if hasattr(event, "discrete_angle") else 0
                )
            else:
                clean_log["mouse"]["angle"] = (
                    event.mouse_delta_angle
                    if hasattr(event, "mouse_delta_angle")
                    else 0.0
                )
                clean_log["mouse"]["magnitude"] = (
                    event.mouse_delta_magnitude
                    if hasattr(event, "mouse_delta_magnitude")
                    else 0.0
                )
        elif tracking_mode == "axis":
            clean_log["mouse"]["north"] = (
                event.north if hasattr(event, "north") else 0.0
            )
            clean_log["mouse"]["south"] = (
                event.south if hasattr(event, "south") else 0.0
            )
            clean_log["mouse"]["east"] = (
                event.east if hasattr(event, "east") else 0.0
            )
            clean_log["mouse"]["west"] = (
                event.west if hasattr(event, "west") else 0.0
            )

        # Write to file and flush
        self.log_file.write(json.dumps(clean_log) + "\n")
        self.log_file.flush()
    
    def _log_ps4_event(self, event: InputData) -> None:
        """Log a PS4 controller event to JSON."""
        # Create a simplified log structure for PS4 controller
        clean_log = {
            "timestamp": event.timestamp,
            "device": "ps4_controller",
            "inputs": {"buttons": event.active_keys or []},
        }

        # Add event-specific data
        if event.event_type == "button_press":
            clean_log["event_type"] = "button_press"
            clean_log["button"] = event.key
        elif event.event_type == "axis_motion":
            clean_log["event_type"] = "axis_motion"
            clean_log["axis"] = event.key
            if "Trigger" in event.key:
                # Trigger value (0 to 1)
                value = event.rel_x if event.rel_x is not None else 0.0
                clean_log["value"] = value
            elif "Stick" in event.key:
                # Get joystick X/Y values
                if "_X" in event.key:
                    base_name = event.key.replace("_X", "")
                    clean_log["axis"] = base_name

                    # X value
                    x_value = event.rel_x if event.rel_x is not None else 0.0

                    # Y value would be in controller state, but we might not have access
                    # Just use what we have
                    y_value = 0.0
                    if hasattr(event, "rel_y") and event.rel_y is not None:
                        y_value = event.rel_y

                    # Store as position
                    clean_log["position"] = {"x": x_value, "y": y_value}

                    # Calculate magnitude and direction
                    magnitude = math.sqrt(x_value**2 + y_value**2)
                    clean_log["magnitude"] = magnitude

                    # Only include direction if significant movement
                    if magnitude > 0.1:
                        # Calculate angle in degrees (0 = right, 90 = down)
                        angle = math.degrees(math.atan2(y_value, x_value))
                        angle = (angle + 360) % 360
                        clean_log["angle"] = angle

        # Write to file and flush
        self.log_file.write(json.dumps(clean_log) + "\n")
        self.log_file.flush()
