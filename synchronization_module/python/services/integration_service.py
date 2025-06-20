"""
Integration service that connects to EEG processor and input collector.

This service manages the communication with both modules and forwards
their data to the synchronizer.
"""

import logging
import threading
import time
from typing import Optional, Dict, Any, Callable
import numpy as np
import json

# Import from parent modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

try:
    from eeg_processor.python.services.data_access_service import DataAccessService as EEGDataAccess
    from input_collector.python.services.data_access_service import DataAccessService as InputDataAccess
    MODULES_AVAILABLE = True
except ImportError as e:
    MODULES_AVAILABLE = False
    logging.error(f"Failed to import parent modules: {e}")


class IntegrationService:
    """
    Service that integrates EEG processor and input collector modules.
    
    This service connects to both modules' data access services and
    forwards their data streams to the synchronizer.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
    
    def __init__(self):
        """Initialize the integration service."""
        if not MODULES_AVAILABLE:
            raise RuntimeError("Parent modules (eeg_processor, input_collector) not available")
        
        # Get instances of data access services
        self.eeg_data_access = EEGDataAccess.get_instance()
        self.input_data_access = InputDataAccess.get_instance()
        
        # Callback IDs for cleanup
        self.eeg_callback_id: Optional[int] = None
        self.input_callback_id: Optional[int] = None
        
        # Data callbacks
        self.eeg_data_callback: Optional[Callable] = None
        self.input_data_callback: Optional[Callable] = None
        
        # Connection state
        self.is_connected = False
        
        # Statistics
        self.stats = {
            'eeg_samples': 0,
            'input_events': 0,
            'errors': 0
        }
        
        logging.info("Integration Service initialized")
    
    def connect_to_modules(self) -> bool:
        """
        Connect to both EEG processor and input collector modules.
        
        Returns:
            bool: True if connection successful
        """
        try:
            # Register callbacks with data access services
            if self.eeg_data_callback:
                self.eeg_callback_id = self.eeg_data_access.register_local_callback(
                    self._handle_eeg_data
                )
                logging.info(f"Connected to EEG data stream (callback ID: {self.eeg_callback_id})")
            
            if self.input_data_callback:
                # Register for all input event types
                self.input_data_access.register_callback(
                    self._handle_input_data
                )
                self.input_callback_id = 1  # Simple ID since input collector uses different system
                logging.info("Connected to input data stream")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            logging.error(f"Failed to connect to modules: {e}")
            self.stats['errors'] += 1
            return False
    
    def disconnect_from_modules(self):
        """Disconnect from both modules."""
        try:
            # Unregister EEG callback
            if self.eeg_callback_id is not None:
                self.eeg_data_access.unregister_local_callback(self.eeg_callback_id)
                self.eeg_callback_id = None
                logging.info("Disconnected from EEG data stream")
            
            # Unregister input callback
            if self.input_callback_id is not None:
                self.input_data_access.unregister_callback(self._handle_input_data)
                self.input_callback_id = None
                logging.info("Disconnected from input data stream")
            
            self.is_connected = False
            
        except Exception as e:
            logging.error(f"Error disconnecting from modules: {e}")
            self.stats['errors'] += 1
    
    def set_eeg_callback(self, callback: Callable[[np.ndarray, float], None]):
        """
        Set callback for EEG data.
        
        Args:
            callback: Function to call with (data, timestamp)
        """
        self.eeg_data_callback = callback
    
    def set_input_callback(self, callback: Callable[[Dict[str, Any], float], None]):
        """
        Set callback for input events.
        
        Args:
            callback: Function to call with (event, timestamp)
        """
        self.input_data_callback = callback
    
    def _handle_eeg_data(self, data: np.ndarray, timestamps: list):
        """
        Handle EEG data from data access service.
        
        Args:
            data: EEG data array
            timestamps: List of timestamps
        """
        try:
            if self.eeg_data_callback and data.size > 0:
                # Process each sample
                for i in range(data.shape[0]):
                    sample = data[i, :]
                    timestamp = timestamps[i] if i < len(timestamps) else time.time()
                    
                    self.eeg_data_callback(sample, timestamp)
                    self.stats['eeg_samples'] += 1
                    
        except Exception as e:
            logging.error(f"Error handling EEG data: {e}")
            self.stats['errors'] += 1
    
    def _handle_input_data(self, event: Any):
        """
        Handle input event from data access service.
        
        Args:
            event: Input event data
        """
        try:
            if self.input_data_callback and event:
                # Convert InputData to dictionary format
                event_dict = {
                    'timestamp': event.timestamp,
                    'event_type': event.event_type,
                    'key': event.key,
                    'mouse_x': event.mouse_x,
                    'mouse_y': event.mouse_y,
                    'mouse_dx': event.mouse_dx,
                    'mouse_dy': event.mouse_dy,
                    'button': event.button,
                    'scroll_direction': event.scroll_direction,
                    'active_keys': list(event.active_keys) if event.active_keys else [],
                    'active_buttons': list(event.active_buttons) if event.active_buttons else []
                }
                
                # Add controller data if available
                if hasattr(event, 'controller_state') and event.controller_state:
                    event_dict['controller_state'] = event.controller_state
                
                self.input_data_callback(event_dict, event.timestamp)
                self.stats['input_events'] += 1
                
        except Exception as e:
            logging.error(f"Error handling input data: {e}")
            self.stats['errors'] += 1
    
    def get_eeg_metadata(self) -> Dict[str, Any]:
        """
        Get metadata from EEG processor.
        
        Returns:
            Dict[str, Any]: EEG metadata
        """
        try:
            return self.eeg_data_access.get_metadata()
        except Exception as e:
            logging.error(f"Failed to get EEG metadata: {e}")
            return {}
    
    def get_input_metadata(self) -> Dict[str, Any]:
        """
        Get metadata from input collector.
        
        Returns:
            Dict[str, Any]: Input metadata
        """
        try:
            return self.input_data_access.get_metadata()
        except Exception as e:
            logging.error(f"Failed to get input metadata: {e}")
            return {}
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get integration statistics.
        
        Returns:
            Dict[str, int]: Statistics
        """
        return self.stats.copy()
    
    def reset_statistics(self):
        """Reset statistics counters."""
        self.stats = {
            'eeg_samples': 0,
            'input_events': 0,
            'errors': 0
        }