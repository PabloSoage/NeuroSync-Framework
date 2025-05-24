"""
Qt Interaction Adapter module.

This module provides an adapter that bridges between the UI framework (PyQt5) 
and the framework-independent interaction service layer.
"""

import logging
import threading
import time
from typing import Dict, List, Any, Optional, Tuple, Set, Callable

from PyQt5.QtCore import QMetaObject, Qt, QObject, pyqtSlot, QTimer, QEventLoop

class QtInteractionAdapter:
    """
    Adapter for PyQt5 UI components to the interaction service.
    
    This adapter ensures that all UI framework-specific operations 
    are performed in a thread-safe manner and properly isolated from
    the core service layer.
    """
    
    def __init__(self):
        """Initialize the adapter."""
        self.collector_service = None
        self.processor_service = None
        self.recording_service = None
        self.visualization_service = None
        self.connection_panel = None
        self.processing_panel = None
        self.recording_panel = None
        self.streaming_panel = None
        self.advanced_panel = None
        self.mne_panel = None
        
        # Lock for thread safety on operations
        self._lock = threading.Lock()
        
        logging.info("Qt interaction adapter created")
    
    def initialize(self, collector_service, processor_service, recording_service, 
                 visualization_service, ui_panels) -> bool:
        """
        Initialize the adapter with application components.
        
        Args:
            collector_service: Collector service
            processor_service: Processor service
            recording_service: Recording service
            visualization_service: Visualization service
            ui_panels: Dictionary of UI panels
            
        Returns:
            bool: True if successful
        """
        try:
            self.collector_service = collector_service
            self.processor_service = processor_service
            self.recording_service = recording_service
            self.visualization_service = visualization_service
            
            # Store UI panels
            self.connection_panel = ui_panels.get('connection_panel')
            self.processing_panel = ui_panels.get('processing_panel')
            self.recording_panel = ui_panels.get('recording_panel')
            self.streaming_panel = ui_panels.get('streaming_panel')
            self.advanced_panel = ui_panels.get('advanced_panel')
            self.mne_panel = ui_panels.get('mne_panel')
            
            logging.info("Qt interaction adapter initialized")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize Qt interaction adapter: {e}")
            return False
    
    def _execute_safely(self, func, *args, **kwargs):
        """
        Execute a function safely, ensuring it runs on the main thread.
        
        Args:
            func: The function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
        """
        # Create a timer in the current thread
        timer = QTimer()
        # Create an event loop in the current thread
        loop = QEventLoop()
        # Variable to store the result
        result_container = {"result": None, "done": False, "exception": None}
        
        # Function to be executed in the main thread
        def execute_function():
            try:
                result_container["result"] = func(*args, **kwargs)
                result_container["done"] = True
            except Exception as e:
                result_container["exception"] = e
                result_container["done"] = True
            finally:
                loop.quit()
        
        # Connect the timer to the function
        timer.timeout.connect(execute_function)
        # Set timer to fire once
        timer.setSingleShot(True)
        # Start the timer with a short timeout
        timer.start(0)
        # Wait for the function to complete
        loop.exec_()
        
        # Check if an exception occurred
        if result_container["exception"]:
            raise result_container["exception"]
        
        # Return the result
        return result_container["result"]
    
    #
    # Board connection methods
    #
    
    def connect_board(self, board_id: int, params: Dict[str, Any], preset: int) -> bool:
        """
        Connect to an EEG board.
        
        Args:
            board_id: ID of the board to connect to
            params: Connection parameters
            preset: Data preset to use
            
        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.collector_service:
                return False
                
            # Check if already connected
            if self.collector_service.is_connected():
                return False
                
            try:
                # Use our thread-safe execution function
                success = self._execute_safely(
                    self.collector_service.connect_to_board,
                    board_id, params, preset
                )
                
                # Update UI if connection was successful
                if success and self.connection_panel:
                    # Update connection panel UI
                    self._execute_safely(self.connection_panel.enable_streaming, True)
                    
                    # Update streaming panel if available
                    if self.streaming_panel:
                        self._execute_safely(self.streaming_panel.enable_streaming, True)
                
                return success
            except Exception as e:
                logging.error(f"Error connecting to board: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    def disconnect_board(self) -> bool:
        """
        Disconnect from the current EEG board.
        
        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.collector_service:
                return False
                
            # Check if connected
            if not self.collector_service.is_connected():
                return False
                
            try:
                # Stop streaming if active
                if self.collector_service.is_streaming_active():
                    self.stop_stream()
                
                # Use our thread-safe execution function
                success = self._execute_safely(
                    self.collector_service.disconnect_from_board
                )
                
                # Update UI if disconnection was successful
                if success:
                    # Update connection panel UI
                    if self.connection_panel:
                        self._execute_safely(self.connection_panel.enable_streaming, False)
                    
                    # Update other panels
                    if self.streaming_panel:
                        self._execute_safely(self.streaming_panel.enable_streaming, False)
                    if self.recording_panel:
                        self._execute_safely(self.recording_panel.enable_recording, False)
                    if self.processing_panel:
                        self._execute_safely(self.processing_panel.enable_processing, False)
                    if self.advanced_panel:
                        self._execute_safely(self.advanced_panel.enable_processing, False)
                    if self.mne_panel:
                        self._execute_safely(self.mne_panel.enable_processing, False)
                
                return success
            except Exception as e:
                logging.error(f"Error disconnecting from board: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    #
    # Streaming methods
    #
    
    def start_stream(self) -> bool:
        """
        Start streaming data from the board.
        
        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.collector_service:
                return False
                
            # Check if connected
            if not self.collector_service.is_connected():
                return False
                
            # Check if already streaming
            if self.collector_service.is_streaming_active():
                return False
                
            try:
                # Use our thread-safe execution function
                success = self._execute_safely(
                    self.collector_service.start_stream
                )
                
                # Initialize processor if available
                if success and self.processor_service:
                    sampling_rate = self.collector_service.get_sampling_rate()
                    if sampling_rate > 0:
                        self._execute_safely(
                            self.processor_service.initialize_processor,
                            sampling_rate
                        )
                
                # Start visualization if available
                if success and self.visualization_service:
                    processor = self.processor_service.processor if self.processor_service else None
                    self._execute_safely(
                        self.visualization_service.create_eeg_visualizer,
                        self.collector_service.collector,
                        processor
                    )
                    self._execute_safely(
                        self.visualization_service.start_eeg_visualization
                    )
                
                # Update UI if streaming was started successfully
                if success:
                    # Enable recording controls
                    if self.recording_panel:
                        self._execute_safely(self.recording_panel.enable_recording, True)
                    
                    # Enable processing controls
                    if self.processing_panel:
                        self._execute_safely(self.processing_panel.enable_processing, True)
                    if self.advanced_panel:
                        self._execute_safely(self.advanced_panel.enable_processing, True)
                    if self.mne_panel:
                        self._execute_safely(self.mne_panel.enable_processing, True)
                
                return success
            except Exception as e:
                logging.error(f"Error starting stream: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    def stop_stream(self) -> bool:
        """
        Stop streaming data from the board.
        
        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.collector_service:
                return False
                
            # Check if streaming
            if not self.collector_service.is_streaming_active():
                return False
                
            try:
                # Stop recording if active
                if self.recording_service and self.recording_service.is_recording():
                    self.stop_recording()
                
                # Use our thread-safe execution function
                success = self._execute_safely(
                    self.collector_service.stop_stream
                )
                
                # Stop visualization if available
                if success and self.visualization_service:
                    self._execute_safely(
                        self.visualization_service.stop_eeg_visualization
                    )
                
                # Update UI if streaming was stopped successfully
                if success:
                    # Disable recording controls
                    if self.recording_panel:
                        self._execute_safely(self.recording_panel.enable_recording, False)
                    
                    # Disable processing controls
                    if self.processing_panel:
                        self._execute_safely(self.processing_panel.enable_processing, False)
                    if self.advanced_panel:
                        self._execute_safely(self.advanced_panel.enable_processing, False)
                    if self.mne_panel:
                        self._execute_safely(self.mne_panel.enable_processing, False)
                
                return success
            except Exception as e:
                logging.error(f"Error stopping stream: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    #
    # Recording methods
    #
    
    def start_recording(self, filename: str, data_type: str = "raw") -> bool:
        """
        Start recording data to file.
        
        Args:
            filename: Path to save the recording
            data_type: Type of data to record ("raw", "processed", or "both")
            
        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.collector_service or not self.recording_service:
                return False
                
            # Check if connected and streaming
            if not self.collector_service.is_connected():
                return False
                
            if not self.collector_service.is_streaming_active():
                return False
                
            # Check if already recording
            if self.recording_service.is_recording():
                return False
                
            try:
                # Use our thread-safe execution function
                success = self._execute_safely(
                    self.recording_service.start_recording,
                    self.collector_service.collector, filename, data_type
                )
                
                # Update UI if recording was started successfully
                if success and self.recording_panel:
                    # Update recording panel UI
                    self._execute_safely(
                        self.recording_panel.update_recording_status,
                        "Recording..."
                    )
                
                return success
            except Exception as e:
                logging.error(f"Error starting recording: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    def stop_recording(self) -> bool:
        """
        Stop recording and save data to file.
        
        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.collector_service or not self.recording_service:
                return False
                
            # Check if recording
            if not self.recording_service.is_recording():
                return False
                
            try:
                # Use our thread-safe execution function
                success = self._execute_safely(
                    self.recording_service.stop_recording,
                    self.collector_service.collector
                )
                
                # Update UI if recording was stopped successfully
                if success and self.recording_panel:
                    # Update recording panel UI
                    self._execute_safely(
                        self.recording_panel.update_recording_status,
                        "Not recording"
                    )
                
                return success
            except Exception as e:
                logging.error(f"Error stopping recording: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    def add_marker(self, marker_value: int) -> bool:
        """
        Add a marker to the data stream.
        
        Args:
            marker_value: Marker value to add
            
        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.collector_service or not self.recording_service:
                return False
                
            # Check if recording
            if not self.recording_service.is_recording():
                return False
                
            try:
                # Use our thread-safe execution function
                success = self._execute_safely(
                    self.recording_service.insert_marker,
                    self.collector_service.collector, marker_value
                )
                
                return success
            except Exception as e:
                logging.error(f"Error adding marker: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    #
    # Processing methods
    #
    
    def apply_filters(self, bandpass: bool = True, bandpass_low: float = 1.0, 
                     bandpass_high: float = 50.0, notch: bool = True, 
                     notch_freq: float = 50.0, detrend: bool = True) -> bool:
        """
        Apply filters to the EEG data visualization.
        
        Args:
            bandpass: Whether to apply bandpass filter
            bandpass_low: Low cutoff frequency for bandpass filter
            bandpass_high: High cutoff frequency for bandpass filter
            notch: Whether to apply notch filter
            notch_freq: Frequency for notch filter
            detrend: Whether to apply detrending
            
        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.visualization_service:
                return False
                
            try:
                # Apply filters
                self._execute_safely(
                    self.visualization_service.set_bandpass_filter,
                    bandpass, bandpass_low, bandpass_high
                )
                self._execute_safely(
                    self.visualization_service.set_notch_filter,
                    notch, notch_freq
                )
                self._execute_safely(
                    self.visualization_service.set_detrend,
                    detrend
                )
                
                # Update UI if filters were applied successfully
                if self.processing_panel:
                    # Update processing panel UI to show filters are applied
                    if hasattr(self.processing_panel, 'filters_applied'):
                        self._execute_safely(
                            setattr, self.processing_panel, 'filters_applied', True
                        )
                    if hasattr(self.processing_panel, 'apply_filters_btn'):
                        self._execute_safely(
                            self.processing_panel.apply_filters_btn.setText,
                            "Remove Filters from Visualization"
                        )
                        self._execute_safely(
                            self.processing_panel.apply_filters_btn.setStyleSheet,
                            "background-color: #AA3333; color: white;"
                        )
                
                return True
            except Exception as e:
                logging.error(f"Error applying filters: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    def remove_filters(self) -> bool:
        """
        Remove all filters from the EEG data visualization.
        
        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.visualization_service:
                return False
                
            try:
                # Remove filters
                self._execute_safely(
                    self.visualization_service.set_bandpass_filter,
                    False, 1.0, 50.0
                )
                self._execute_safely(
                    self.visualization_service.set_notch_filter,
                    False
                )
                self._execute_safely(
                    self.visualization_service.set_detrend,
                    False
                )
                
                # Update UI if filters were removed successfully
                if self.processing_panel:
                    # Update processing panel UI to show filters are removed
                    if hasattr(self.processing_panel, 'filters_applied'):
                        self._execute_safely(
                            setattr, self.processing_panel, 'filters_applied', False
                        )
                    if hasattr(self.processing_panel, 'apply_filters_btn'):
                        self._execute_safely(
                            self.processing_panel.apply_filters_btn.setText,
                            "Apply Filters to Visualization"
                        )
                        self._execute_safely(
                            self.processing_panel.apply_filters_btn.setStyleSheet,
                            ""
                        )
                
                return True
            except Exception as e:
                logging.error(f"Error removing filters: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    def show_brain_map(self) -> bool:
        """
        Show brain map visualization.
        
        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.collector_service or not self.processor_service or not self.visualization_service:
                return False
                
            # Check if connected and streaming
            if not self.collector_service.is_connected():
                return False
                
            if not self.collector_service.is_streaming_active():
                return False
                
            try:
                # Initialize processor if needed
                sampling_rate = self.collector_service.get_sampling_rate()
                if sampling_rate <= 0:
                    return False
                    
                if not hasattr(self.processor_service, 'processor') or self.processor_service.processor is None:
                    self._execute_safely(
                        self.processor_service.initialize_processor,
                        sampling_rate
                    )
                    
                # Create and start brain map visualization
                success = self._execute_safely(
                    self.visualization_service.create_brain_map_visualizer,
                    self.collector_service.collector,
                    self.processor_service.processor
                )
                
                if success:
                    self._execute_safely(
                        self.visualization_service.start_brain_map_visualization
                    )
                    
                    # Update UI if brain map was shown successfully
                    if self.processing_panel and hasattr(self.processing_panel, 'brain_map_btn'):
                        self._execute_safely(
                            self.processing_panel.brain_map_btn.setEnabled,
                            False
                        )
                
                return success
            except Exception as e:
                logging.error(f"Error showing brain map: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    #
    # Visualization methods
    #
    
    def show_eeg_visualization(self) -> bool:
        """
        Show EEG visualization window.
        
        Returns:
            bool: True if successful
        """
        with self._lock:
            if not self.collector_service or not self.visualization_service:
                return False
                
            # Check if connected and streaming
            if not self.collector_service.is_connected():
                return False
                
            if not self.collector_service.is_streaming_active():
                return False
                
            # Check if visualization is closed
            if not self.visualization_service.visualization_closed():
                return True
                
            try:
                # Create and start visualization
                success = self._execute_safely(
                    self.visualization_service.create_eeg_visualizer,
                    self.collector_service.collector,
                    None  # We'll initialize the processor later
                )
                
                if success:
                    self._execute_safely(
                        self.visualization_service.start_eeg_visualization
                    )
                    
                    # Update UI if visualization was shown successfully
                    if self.connection_panel and hasattr(self.connection_panel, 'show_viz_btn'):
                        self._execute_safely(
                            self.connection_panel.show_viz_btn.setEnabled,
                            False
                        )
                
                return success
            except Exception as e:
                logging.error(f"Error showing EEG visualization: {e}")
                import traceback
                traceback.print_exc()
                return False