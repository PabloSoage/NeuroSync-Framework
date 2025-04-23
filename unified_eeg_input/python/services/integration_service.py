"""
Integration service for unified application.

This module provides services that coordinate between the EEG processor and
input collector applications.
"""

import os
import time
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class IntegrationService(QObject):
    """
    Service for integrating EEG processor and input collector functionality.
    
    This class provides methods to coordinate operations between the two modules,
    particularly for synchronizing recording operations.
    """
    
    status_message = pyqtSignal(str, str)  # message, color
    
    def __init__(self, input_collector_components, eeg_processor_components):
        """Initialize the integration service."""
        super().__init__()
        
        self.input_collector = input_collector_components
        self.eeg_processor = eeg_processor_components
        
        # Recording state
        self.recording_start_time = 0
        self.recording_directory = ""
        
        # Setup Timer for periodic checks
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_components_status)
        self.check_timer.start(1000)  # Check every second
    
    def check_components_status(self):
        """Periodically check the status of both components."""
        # Check if EEG board is connected
        eeg_connected = self.eeg_processor['collector_service'].is_connected()
        
        # Check if input collection is active
        input_active = True  # Input collection is always available
        
        # Additional checks can be implemented here
    
    def start_recording(self, config):
        """
        Start recording on both modules if enabled.
        
        Args:
            config: Dictionary with recording configuration
            
        Returns:
            bool: True if recording started successfully
        """
        success = True
        
        # Create recording directory if needed
        if config['save_directory']:
            directory = config['save_directory']
            os.makedirs(directory, exist_ok=True)
        else:
            # Create a timestamped directory in the current directory
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            directory = os.path.join("recordings", f"session_{timestamp}")
            os.makedirs(directory, exist_ok=True)
            
        self.recording_directory = directory
        
        # Start input collector recording if enabled
        if config['record_input']:
            input_success = self._start_input_recording(config, directory)
            success = success and input_success
            
        # Start EEG recording if enabled
        if config['record_eeg']:
            eeg_success = self._start_eeg_recording(config, directory)
            success = success and eeg_success
            
        # Record start time if any recording was successful
        if success:
            self.recording_start_time = time.time()
            
        return success
    
    def _start_input_recording(self, config, directory):
        """
        Start input collector recording.
        
        Args:
            config: Recording configuration
            directory: Directory to save files
            
        Returns:
            bool: True if successful
        """
        try:
            # Configure input logging
            logging_manager = self.input_collector['logging_manager']
            
            # Configure JSON logging if needed
            if config['input_json']:
                logging_manager.set_json_logging(True)
                
            # Configure CSV logging if needed
            if config['input_csv']:
                csv_path = os.path.join(directory, "input_data.csv")
                logging_manager.csv_logger.set_filepath(csv_path)
                logging_manager.set_csv_logging(True, csv_path)
                
            # Get app coordinator and start recording
            app_coordinator = self.input_collector['app_coordinator']
            
            # Don't allow recording if in edit mode
            if app_coordinator.edit_mode:
                self.status_message.emit(
                    "Cannot start recording while in edit mode",
                    "warning"
                )
                return False
                
            # Toggle recording state through the coordinator
            if not app_coordinator.is_recording:
                app_coordinator.toggle_recording()
                return app_coordinator.is_recording
                
            return True
            
        except Exception as e:
            self.status_message.emit(
                f"Error starting input recording: {str(e)}",
                "error"
            )
            return False
    
    def _start_eeg_recording(self, config, directory):
        """
        Start EEG recording.
        
        Args:
            config: Recording configuration
            directory: Directory to save files
            
        Returns:
            bool: True if successful
        """
        try:
            # Check if EEG collector is connected and streaming
            collector_service = self.eeg_processor['collector_service']
            if not collector_service.is_connected():
                self.status_message.emit(
                    "EEG board not connected",
                    "warning"
                )
                return False
                
            if not collector_service.is_streaming_active():
                self.status_message.emit(
                    "EEG stream not active",
                    "warning"
                )
                return False
                
            # Configure recording based on data type setting
            recording_service = self.eeg_processor['recording_service']
            eeg_filename = os.path.join(directory, "eeg_data.csv")
            
            # Start recording through the recording service
            success = recording_service.start_recording(
                collector_service.collector,
                eeg_filename,
                config['eeg_data_type']
            )
            
            if not success:
                self.status_message.emit(
                    "Failed to start EEG recording",
                    "error"
                )
                
            return success
            
        except Exception as e:
            self.status_message.emit(
                f"Error starting EEG recording: {str(e)}",
                "error"
            )
            return False
    
    def stop_recording(self):
        """
        Stop recording on both modules.
        
        Returns:
            bool: True if recording stopped successfully
        """
        success = True
        
        # Stop input collector recording
        input_success = self._stop_input_recording()
        success = success and input_success
        
        # Stop EEG recording
        eeg_success = self._stop_eeg_recording()
        success = success and eeg_success
        
        # Reset recording state
        self.recording_start_time = 0
        
        return success
    
    def _stop_input_recording(self):
        """
        Stop input collector recording.
        
        Returns:
            bool: True if successful
        """
        try:
            # Get app coordinator
            app_coordinator = self.input_collector['app_coordinator']
            
            # Toggle recording state through the coordinator if recording
            if app_coordinator.is_recording:
                app_coordinator.toggle_recording()
                return not app_coordinator.is_recording
                
            return True
            
        except Exception as e:
            self.status_message.emit(
                f"Error stopping input recording: {str(e)}",
                "error"
            )
            return False
    
    def _stop_eeg_recording(self):
        """
        Stop EEG recording.
        
        Returns:
            bool: True if successful
        """
        try:
            # Check if EEG is recording
            recording_service = self.eeg_processor['recording_service']
            collector_service = self.eeg_processor['collector_service']
            
            if recording_service.is_recording():
                success = recording_service.stop_recording(collector_service.collector)
                
                if not success:
                    self.status_message.emit(
                        "Failed to stop EEG recording",
                        "error"
                    )
                    
                return success
            
            return True
            
        except Exception as e:
            self.status_message.emit(
                f"Error stopping EEG recording: {str(e)}",
                "error"
            )
            return False
    
    def add_marker(self, marker_value):
        """
        Add a marker to both recordings.
        
        Args:
            marker_value: Value of the marker
            
        Returns:
            bool: True if marker added successfully
        """
        success = True
        
        # Add marker to EEG recording if active
        recording_service = self.eeg_processor['recording_service']
        collector_service = self.eeg_processor['collector_service']
        
        if recording_service.is_recording():
            eeg_success = recording_service.insert_marker(collector_service.collector, marker_value)
            success = success and eeg_success
            
        # Input collector doesn't support markers directly
        # Additional custom marker handling could be added here
        
        return success
    
    def is_ready_for_recording(self):
        """
        Check if the system is ready for recording.
        
        Returns:
            bool: True if ready for recording
        """
        # Check EEG processor is connected and streaming
        collector_service = self.eeg_processor['collector_service']
        eeg_ready = collector_service.is_connected() and collector_service.is_streaming_active()
        
        # Input collector is always ready for recording
        input_ready = True
        
        # System is ready if at least one component is ready
        return eeg_ready or input_ready
    
    def get_recording_time(self):
        """
        Get the current recording time in seconds.
        
        Returns:
            float: Recording time in seconds
        """
        if self.recording_start_time > 0:
            return time.time() - self.recording_start_time
        return 0
    
    def get_eeg_ready_state(self):
        """
        Get the ready state of the EEG processor.
        
        Returns:
            bool: True if EEG processor is ready for recording
        """
        collector_service = self.eeg_processor['collector_service']
        return collector_service.is_connected() and collector_service.is_streaming_active()
    
    def get_input_ready_state(self):
        """
        Get the ready state of the input collector.
        
        Returns:
            bool: True if input collector is ready for recording
        """
        # Input collector is always ready for recording
        return True
