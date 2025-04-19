"""
Adapter for input collector module.

This adapter wraps the InputCollectorApp to implement the IInputModule interface.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List

from ..interfaces.module_interface import IInputModule
from input_collector.python.input_collector_app import InputCollectorApp


class InputModuleAdapter(IInputModule):
    """
    Adapter for InputCollectorApp to implement the IInputModule interface.
    
    This class follows the Adapter pattern to convert the InputCollectorApp
    interface to the IInputModule interface expected by the integrated application.
    """
    
    def __init__(self, input_collector: InputCollectorApp):
        """
        Initialize the adapter with an InputCollectorApp instance.
        
        Args:
            input_collector: The InputCollectorApp instance to adapt
        """
        self._input_app = input_collector
        self._recording_start_time = 0
        self._recording_filename = ""
        self._recording_formats = {"json": False, "csv": True}
        self._json_filepath = ""
        self._csv_filepath = ""
        
    def is_ready(self) -> bool:
        """Check if input collector is ready to record."""
        # Input collector is always ready for recording
        return True
    
    def set_tracked_inputs(self, input_list: List[str]) -> None:
        """Set which inputs should be tracked."""
        if not hasattr(self._input_app, 'collector'):
            logging.error("Input app doesn't have collector attribute")
            return
            
        try:
            # Update tracked keys
            self._input_app.tracked_keys = input_list
            
            # Update collector
            if hasattr(self._input_app.collector, 'set_supported_keys'):
                self._input_app.collector.set_supported_keys(input_list)
                
            # Update keyboard visualizer if available
            if hasattr(self._input_app, 'keyboard_viz'):
                self._input_app.keyboard_viz.set_tracked_keys(input_list)
                
            # Update mouse buttons selector if available
            if hasattr(self._input_app, 'mouse_buttons_selector'):
                self._input_app.mouse_buttons_selector.setTrackedButtons(input_list)
                
            logging.info(f"Updated tracked inputs: {input_list}")
        except Exception as e:
            logging.error(f"Error setting tracked inputs: {e}")
    
    def start_recording(self, filename: str, options: Dict[str, Any]) -> bool:
        """Start recording input data to file."""
        try:
            # Extract options
            json_enabled = options.get("json", False)
            csv_enabled = options.get("csv", True)
            
            # Store for later reference
            self._recording_formats = {"json": json_enabled, "csv": csv_enabled}
            self._recording_start_time = time.time()
            
            # Base filename without extension
            base_filename = os.path.splitext(filename)[0]
            
            # Setup JSON logging if enabled
            if json_enabled:
                self._json_filepath = f"{base_filename}.json"
                # Set app attributes
                self._input_app.log_to_file = True
                self._input_app.log_file = open(self._json_filepath, "w")
                logging.info(f"Input JSON logging to: {self._json_filepath}")
            else:
                # Disable JSON logging
                self._input_app.log_to_file = False
                if hasattr(self._input_app, 'log_file') and self._input_app.log_file:
                    self._input_app.log_file.close()
                    self._input_app.log_file = None
                    
            # Setup CSV logging if enabled
            if csv_enabled:
                self._csv_filepath = f"{base_filename}.csv"
                # Set app attributes
                self._input_app.log_to_csv = True
                self._input_app.csv_filepath = self._csv_filepath
                logging.info(f"Input CSV logging to: {self._csv_filepath}")
            else:
                # Disable CSV logging
                self._input_app.log_to_csv = False
                
            # Start recording in input collector
            if hasattr(self._input_app, '_toggle_recording') and not self._input_app.is_recording:
                self._input_app._toggle_recording()
                logging.info("Started input recording")
                return True
            elif self._input_app.is_recording:
                logging.warning("Input collector already recording")
                return True
            else:
                logging.error("Input app doesn't have _toggle_recording method")
                return False
                
        except Exception as e:
            logging.error(f"Error starting input recording: {e}")
            return False
    
    def stop_recording(self) -> bool:
        """Stop input recording."""
        if not self.is_recording_active():
            # Nothing to stop
            return True
            
        try:
            # Stop recording in input collector
            if hasattr(self._input_app, '_toggle_recording'):
                self._input_app._toggle_recording()
                logging.info("Stopped input recording")
                
                # Reset recording info
                self._recording_start_time = 0
                self._recording_filename = ""
                self._json_filepath = ""
                self._csv_filepath = ""
                
                return True
            else:
                logging.error("Input app doesn't have _toggle_recording method")
                return False
        except Exception as e:
            logging.error(f"Error stopping input recording: {e}")
            return False
    
    def is_recording_active(self) -> bool:
        """Check if recording is currently active."""
        return hasattr(self._input_app, 'is_recording') and self._input_app.is_recording
    
    @property
    def recording_info(self) -> Dict[str, Any]:
        """Get information about the current recording."""
        info = {
            "is_recording": self.is_recording_active(),
            "formats": self._recording_formats.copy(),
            "json_file": self._json_filepath,
            "csv_file": self._csv_filepath,
            "duration": 0
        }
        
        if self.is_recording_active() and self._recording_start_time > 0:
            info["duration"] = time.time() - self._recording_start_time
        
        return info
    
    def show_visualization(self, visible: bool = True) -> None:
        """Show or hide input visualizations."""
        # In the Input Collector app, visualization is always visible when running
        # This method would need to be implemented if we add ability to hide/show visualizations
        # Currently no direct way to hide visualizations in InputCollectorApp
        pass
