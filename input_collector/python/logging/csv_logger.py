"""
CSV logger module.

Provides functionality for logging input events to CSV format.
"""

import csv
import os
import time
from typing import List, Optional, TextIO

from PyQt5.QtCore import QObject, pyqtSignal

from ..interfaces import InputData


class CSVLogger(QObject):
    """
    Logger for input events in CSV format.
    
    This class handles logging input events to CSV files with proper
    formatting and column structure.
    """
    
    status_message = pyqtSignal(str, str)  # message, color
    
    def __init__(self) -> None:
        """Initialize the CSV logger."""
        super().__init__()
        self.csv_file: Optional[TextIO] = None
        self.csv_writer = None
        self.csv_headers: List[str] = []
        self.filepath: str = ""
    
    def set_filepath(self, filepath: str) -> None:
        """
        Set the filepath for the CSV log.
        
        Args:
            filepath: Path to the CSV file
        """
        self.filepath = filepath
    
    def initialize(self, headers: List[str], tracked_keys: List[str], tracking_mode: str, direction_only: bool) -> bool:
        """
        Initialize the CSV file with headers.
        
        Args:
            headers: Predefined headers (optional)
            tracked_keys: List of tracked keys
            tracking_mode: Mouse tracking mode
            direction_only: Whether direction-only mode is enabled
            
        Returns:
            bool: True if initialization was successful
        """
        try:
            # Add timestamp to filename if not provided
            if not self.filepath.lower().endswith('.csv'):
                self.filepath += '.csv'
                
            # Always create a fresh CSV file with timestamp
            base_path, extension = os.path.splitext(self.filepath)
            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(time.time()))
            self.filepath = f"{base_path}_{timestamp}{extension}"
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.filepath)), exist_ok=True)
            
            # Open the file for writing
            self.csv_file = open(self.filepath, 'w', newline='')
            
            # Create CSV writer
            self.csv_writer = csv.writer(self.csv_file)
            
            # If headers are provided, use them
            if headers:
                self.csv_headers = headers
            else:
                # Create headers based on tracked keys and mouse mode
                self.csv_headers = ['timestamp']
                
                # Add headers for each tracked key
                for key in sorted(tracked_keys):
                    # Skip F9/media_play_pause key
                    if key == "Key.media_play_pause":
                        continue
                    
                    # Skip mouse buttons - they will be handled separately
                    if key in ["Button.left", "Button.right", "Button.scroll"]:
                        continue
                    
                    # Format the key name - remove "Key." prefix for special keys
                    csv_key_name = key
                    if key.startswith("Key."):
                        csv_key_name = key[4:]  # Remove "Key." prefix
                    
                    # Use key name as header
                    self.csv_headers.append(f"key_{csv_key_name}")
                
                # Add mouse button headers
                if "Button.left" in tracked_keys:
                    self.csv_headers.append('mouse_left')
                if "Button.right" in tracked_keys:
                    self.csv_headers.append('mouse_right')
                if "Button.scroll" in tracked_keys:
                    self.csv_headers.append('mouse_scroll')
                
                # Add mouse mode specific headers
                if tracking_mode == "joystick":
                    self.csv_headers.extend(['mouse_rel_x', 'mouse_rel_y', 'mouse_speed'])
                elif tracking_mode == "delta":
                    self.csv_headers.extend(['mouse_delta_x', 'mouse_delta_y'])
                elif tracking_mode == "angle":
                    if direction_only:
                        self.csv_headers.append('mouse_discrete_angle')
                    else:
                        self.csv_headers.extend(['mouse_angle', 'mouse_magnitude'])
                elif tracking_mode == "axis":
                    self.csv_headers.extend(['mouse_north', 'mouse_south', 'mouse_east', 'mouse_west'])
            
            # Write headers to CSV
            self.csv_writer.writerow(self.csv_headers)
            self.csv_file.flush()
            
            self.status_message.emit(f"CSV logging to: {self.filepath}", "#5FB878")
            return True
            
        except Exception as e:
            self.status_message.emit(f"Error initializing CSV file: {e}", "#FF5555")
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
            return False
    
    def close_log(self) -> None:
        """Close the CSV log file."""
        if self.csv_file:
            try:
                self.csv_file.close()
            except Exception:
                pass
            self.csv_file = None
    
    def log_event(self, event: InputData, collector_type: str) -> None:
        """
        Log an input event.
        
        Args:
            event: The input event to log
            collector_type: Type of collector that generated the event
        """
        if not self.csv_file or not self.csv_writer:
            return
            
        try:
            if collector_type == "keyboard_mouse":
                self._log_keyboard_mouse_event(event)
            elif collector_type == "ps4_controller":
                self._log_ps4_controller_event(event)
        except Exception as e:
            self.status_message.emit(f"Error writing to CSV: {e}", "#FF5555")
    
    def _log_keyboard_mouse_event(self, event: InputData) -> None:
        """Log a keyboard/mouse event to CSV."""
        # Create a row with data for each column
        row_data = {}
        
        # Add timestamp
        row_data['timestamp'] = event.timestamp
        
        # Set default values for all columns
        for header in self.csv_headers:
            if header != 'timestamp':
                row_data[header] = 0
        
        # Process keyboard keys
        for key in event.active_keys:
            # Skip F9/media_play_pause key
            if key == "Key.media_play_pause":
                continue
            
            # Format the key name for CSV column lookup
            csv_key_name = key
            if key.startswith("Key."):
                csv_key_name = key[4:]  # Remove "Key." prefix
            
            key_header = f"key_{csv_key_name}"
            
            if key_header in self.csv_headers:
                row_data[key_header] = 1
        
        # Process mouse buttons
        if hasattr(event, 'button_pressed') and event.button_pressed:
            if event.button_pressed == "Button.left" and 'mouse_left' in self.csv_headers:
                row_data['mouse_left'] = 1
            elif event.button_pressed == "Button.right" and 'mouse_right' in self.csv_headers:
                row_data['mouse_right'] = 1
        
        # Process scroll
        if event.event_type == "mouse_scroll" and 'mouse_scroll' in self.csv_headers:
            scroll_value = 0
            if event.direction == "up":
                scroll_value = 1
            elif event.direction == "down":
                scroll_value = -1
            row_data['mouse_scroll'] = scroll_value
        
        # Process mouse tracking mode specific data
        tracking_mode = getattr(event, "mouse_tracking_mode", "joystick")
        
        if tracking_mode == "joystick":
            if 'mouse_rel_x' in self.csv_headers:
                row_data['mouse_rel_x'] = event.rel_x if event.rel_x is not None else 0.0
            if 'mouse_rel_y' in self.csv_headers:
                row_data['mouse_rel_y'] = event.rel_y if event.rel_y is not None else 0.0
            if 'mouse_speed' in self.csv_headers:
                row_data['mouse_speed'] = event.speed if event.speed is not None else 0.0
        elif tracking_mode == "delta":
            if 'mouse_delta_x' in self.csv_headers:
                row_data['mouse_delta_x'] = event.mouse_delta_x if hasattr(event, "mouse_delta_x") else 0.0
            if 'mouse_delta_y' in self.csv_headers:
                row_data['mouse_delta_y'] = event.mouse_delta_y if hasattr(event, "mouse_delta_y") else 0.0
        elif tracking_mode == "angle":
            direction_only = getattr(event, "direction_only", False)
            if direction_only:
                if 'mouse_discrete_angle' in self.csv_headers:
                    row_data['mouse_discrete_angle'] = event.discrete_angle if hasattr(event, "discrete_angle") else 0
            else:
                if 'mouse_angle' in self.csv_headers:
                    row_data['mouse_angle'] = event.mouse_delta_angle if hasattr(event, "mouse_delta_angle") else 0.0
                if 'mouse_magnitude' in self.csv_headers:
                    row_data['mouse_magnitude'] = event.mouse_delta_magnitude if hasattr(event, "mouse_delta_magnitude") else 0.0
        elif tracking_mode == "axis":
            if 'mouse_north' in self.csv_headers:
                row_data['mouse_north'] = event.north if hasattr(event, "north") else 0.0
            if 'mouse_south' in self.csv_headers:
                row_data['mouse_south'] = event.south if hasattr(event, "south") else 0.0
            if 'mouse_east' in self.csv_headers:
                row_data['mouse_east'] = event.east if hasattr(event, "east") else 0.0
            if 'mouse_west' in self.csv_headers:
                row_data['mouse_west'] = event.west if hasattr(event, "west") else 0.0
        
        # Create row in same order as headers
        row = [row_data.get(header, '') for header in self.csv_headers]
        
        # Write row to CSV
        self.csv_writer.writerow(row)
        self.csv_file.flush()
    
    def _log_ps4_controller_event(self, event: InputData) -> None:
        """Log a PS4 controller event to CSV."""
        # Create a row with data for each column
        row_data = {}
        
        # Add timestamp
        row_data['timestamp'] = event.timestamp
        
        # Set default values for all columns
        for header in self.csv_headers:
            if header != 'timestamp':
                row_data[header] = 0
        
        # Process active buttons - with the same formatting as regular keys
        if hasattr(event, 'active_keys') and event.active_keys:
            for key in event.active_keys:
                # Skip F9/media_play_pause key
                if key == "Key.media_play_pause":
                    continue
                
                # Format the key name for CSV column lookup
                ps4_key_header = f"ps4_{key}"
                
                if ps4_key_header in self.csv_headers:
                    row_data[ps4_key_header] = 1
        
        # Handle specific PS4 controller event types
        if event.event_type == "axis_motion":
            if hasattr(event, 'key') and hasattr(event, 'rel_x') and event.rel_x is not None:
                # Handle joystick axes
                if "Stick" in event.key:
                    if "_X" in event.key:
                        axis_name = event.key.replace("_X", "")
                        header = f"ps4_{axis_name}_x"
                        if header in self.csv_headers:
                            row_data[header] = event.rel_x
                    elif "_Y" in event.key:
                        axis_name = event.key.replace("_Y", "")
                        header = f"ps4_{axis_name}_y"
                        if header in self.csv_headers:
                            row_data[header] = event.rel_y
                
                # Handle trigger axes (L2/R2)
                elif "Trigger" in event.key:
                    header = f"ps4_{event.key}"
                    if header in self.csv_headers:
                        row_data[header] = event.rel_x
        
        # Create row in same order as headers
        row = [row_data.get(header, '') for header in self.csv_headers]
        
        # Write row to CSV
        self.csv_writer.writerow(row)
        self.csv_file.flush()
