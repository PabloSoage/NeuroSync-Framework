"""
Recording manager for the integrated BCI system.

This module handles recording coordination between different BCI system modules.
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional

from ..interfaces.module_interface import IRecordingModule, IEEGModule, IInputModule


class RecordingManager:
    """
    Manages recording sessions across multiple recording modules.
    
    This class follows the Single Responsibility Principle by focusing solely
    on coordinating recording across different modules.
    """
    
    def __init__(self, base_directory: str = ""):
        """
        Initialize the recording manager.
        
        Args:
            base_directory: Base directory for recordings
        """
        self.base_directory = base_directory
        self.session_directory = ""
        self.is_recording = False
        self.session_start_time = 0
        self.recording_modules = []
        self.active_modules = []
        self.module_options = {}
        
        # Create base directory if it doesn't exist
        if self.base_directory and not os.path.exists(self.base_directory):
            os.makedirs(self.base_directory, exist_ok=True)
            
    def register_module(self, module: IRecordingModule, options: Dict[str, Any] = None):
        """
        Register a module with the recording manager.
        
        Args:
            module: The recording module to register
            options: Recording options for this module
        """
        if not isinstance(module, IRecordingModule):
            raise TypeError("Module must implement IRecordingModule interface")
            
        if options is None:
            options = {}
            
        self.recording_modules.append(module)
        self.module_options[module] = options
        logging.info(f"Registered recording module: {module.__class__.__name__}")
        
    def unregister_module(self, module: IRecordingModule):
        """
        Unregister a module from the recording manager.
        
        Args:
            module: The recording module to unregister
        """
        if module in self.recording_modules:
            self.recording_modules.remove(module)
            if module in self.module_options:
                del self.module_options[module]
                
            logging.info(f"Unregistered recording module: {module.__class__.__name__}")
            
    def set_module_options(self, module: IRecordingModule, options: Dict[str, Any]):
        """
        Set recording options for a specific module.
        
        Args:
            module: The module to configure
            options: Recording options for the module
        """
        if module in self.recording_modules:
            self.module_options[module] = options
            
    def update_base_directory(self, directory: str):
        """
        Update the base directory for recordings.
        
        Args:
            directory: New base directory path
        """
        if os.path.exists(directory) or directory == "":
            self.base_directory = directory
            logging.info(f"Updated recording base directory: {directory}")
        else:
            try:
                os.makedirs(directory, exist_ok=True)
                self.base_directory = directory
                logging.info(f"Created recording base directory: {directory}")
            except Exception as e:
                logging.error(f"Failed to create recording directory {directory}: {e}")
                
    def start_recording(self) -> bool:
        """
        Start recording on all registered modules.
        
        Returns:
            bool: True if recording started successfully, False otherwise
        """
        if self.is_recording:
            logging.warning("Recording is already active")
            return True
            
        # Create session directory
        session_timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.session_directory = os.path.join(
            self.base_directory, f"session_{session_timestamp}")
        
        try:
            os.makedirs(self.session_directory, exist_ok=True)
            logging.info(f"Created session directory: {self.session_directory}")
        except Exception as e:
            logging.error(f"Failed to create session directory: {e}")
            return False
            
        # Start recording on each module
        self.active_modules = []
        success = True
        
        for module in self.recording_modules:
            # Get module options
            options = self.module_options.get(module, {})
            
            if not options.get("enabled", True):
                # Skip disabled modules
                logging.info(f"Skipping disabled module: {module.__class__.__name__}")
                continue
                
            # Create unique filename for this module
            module_name = module.__class__.__name__.lower().replace("moduleadapter", "")
            filename = os.path.join(
                self.session_directory, f"{module_name}_{session_timestamp}")
                
            # Start recording
            if module.start_recording(filename, options):
                self.active_modules.append(module)
                logging.info(f"Started recording on module: {module.__class__.__name__}")
            else:
                logging.error(f"Failed to start recording on module: {module.__class__.__name__}")
                success = False
                
        if success and len(self.active_modules) > 0:
            self.is_recording = True
            self.session_start_time = time.time()
            return True
        else:
            # If any module failed, stop recording on all modules
            self._stop_all_recordings()
            return False
            
    def stop_recording(self) -> bool:
        """
        Stop recording on all active modules.
        
        Returns:
            bool: True if recording stopped successfully, False otherwise
        """
        if not self.is_recording:
            return True
            
        success = self._stop_all_recordings()
        
        if success:
            self.is_recording = False
            self.session_start_time = 0
            logging.info("Recording session completed successfully")
        else:
            logging.error("Some modules failed to stop recording properly")
            
        return success
        
    def _stop_all_recordings(self) -> bool:
        """
        Stop recording on all active modules.
        
        Returns:
            bool: True if all modules stopped successfully, False otherwise
        """
        all_success = True
        
        for module in self.active_modules:
            if not module.stop_recording():
                logging.error(f"Failed to stop recording on module: {module.__class__.__name__}")
                all_success = False
                
        self.active_modules = []
        return all_success
        
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about the current recording session.
        
        Returns:
            Dict[str, Any]: Session information
        """
        info = {
            "is_recording": self.is_recording,
            "session_directory": self.session_directory,
            "duration": 0,
            "modules": {},
        }
        
        if self.is_recording and self.session_start_time > 0:
            info["duration"] = time.time() - self.session_start_time
            
        # Collect info from each active module
        for module in self.active_modules:
            module_name = module.__class__.__name__
            info["modules"][module_name] = module.recording_info
            
        return info
