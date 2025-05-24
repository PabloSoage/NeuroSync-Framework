"""
Interaction service module.

Provides service-layer interfaces for controlling and interacting with
the EEG processor application components.
"""
from typing import Dict, List, Optional, Any, Tuple, Callable, Set
import threading
import logging
import time
from ..core.event_system import EventType, dispatch

class InteractionService:
    """
    Service for controlling and interacting with the EEG processor application.
    
    This service provides methods to interact with the various components of the 
    application, allowing external control of board connection, streaming, recording,
    and other key functionality.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """Get or create the singleton instance of the service."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = InteractionService()
            return cls._instance
    
    def __init__(self):
        """Initialize the interaction service."""
        self._components = {}
        self._last_status = {"success": False, "message": "Service not initialized"}
        self._initialized = False
        logging.info("Interaction service initialized")
    
    def register_component(self, component_name: str, component: Any) -> None:
        """
        Register an application component with the service.
        
        Args:
            component_name: Name of the component (e.g., 'app_coordinator')
            component: The component instance
        """
        self._components[component_name] = component
        logging.info(f"Component '{component_name}' registered with interaction service")
    
    def get_component(self, component_name: str) -> Any:
        """
        Get a registered component by name.
        
        Args:
            component_name: Name of the component to retrieve
            
        Returns:
            The component instance or None if not found
        """
        return self._components.get(component_name)
    
    def initialize(self, components: Dict[str, Any]) -> bool:
        """
        Initialize the service with application components.
        
        Args:
            components: Dictionary of components to register
            
        Returns:
            bool: True if successful
        """
        try:
            # Register all components
            for name, component in components.items():
                self.register_component(name, component)
                
            self._initialized = True
            self._set_status(True, "Service initialized successfully")
            return True
        except Exception as e:
            self._set_status(False, f"Failed to initialize service: {e}")
            logging.error(f"Failed to initialize interaction service: {e}")
            return False
    
    def _set_status(self, success: bool, message: str) -> None:
        """
        Set the status of the last operation.
        
        Args:
            success: Whether the operation was successful
            message: Status message
        """
        self._last_status = {"success": success, "message": message}
        log_level = logging.INFO if success else logging.ERROR
        logging.log(log_level, f"Interaction status: {message}")
    
    def get_last_status(self) -> Dict[str, Any]:
        """
        Get the status of the last operation.
        
        Returns:
            Dict with status information
        """
        return self._last_status
    
    def _check_initialized(self) -> bool:
        """
        Check if the service is initialized.
        
        Returns:
            bool: True if initialized
        """
        if not self._initialized:
            self._set_status(False, "Service not initialized")
            return False
        return True
    
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
        if not self._check_initialized():
            return False
            
        try:
            collector_service = self.get_component('collector_service')
            if not collector_service:
                self._set_status(False, "Collector service not available")
                return False
                
            # Check if already connected
            if collector_service.is_connected():
                self._set_status(False, "Already connected to a board")
                return False
                
            # Connect to board
            success = collector_service.connect_to_board(board_id, params, preset)
            
            if success:
                self._set_status(True, f"Connected to board ID {board_id}")
                # Dispatch event
                dispatch(EventType.BOARD_CONNECTED, {"board_id": board_id, "preset": preset})
                return True
            else:
                self._set_status(False, "Failed to connect to board")
                return False
                
        except Exception as e:
            self._set_status(False, f"Error connecting to board: {e}")
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
        if not self._check_initialized():
            return False
            
        try:
            collector_service = self.get_component('collector_service')
            if not collector_service:
                self._set_status(False, "Collector service not available")
                return False
                
            # Check if connected
            if not collector_service.is_connected():
                self._set_status(False, "Not connected to a board")
                return False
                
            # Stop streaming if active
            if collector_service.is_streaming_active():
                collector_service.stop_stream()
                
            # Disconnect from board
            success = collector_service.disconnect_from_board()
            
            if success:
                self._set_status(True, "Disconnected from board")
                # Dispatch event
                dispatch(EventType.BOARD_DISCONNECTED, {})
                return True
            else:
                self._set_status(False, "Failed to disconnect from board")
                return False
                
        except Exception as e:
            self._set_status(False, f"Error disconnecting from board: {e}")
            logging.error(f"Error disconnecting from board: {e}")
            return False
    
    def is_connected(self) -> bool:
        """
        Check if connected to a board.
        
        Returns:
            bool: True if connected
        """
        if not self._check_initialized():
            return False
            
        collector_service = self.get_component('collector_service')
        if not collector_service:
            return False
            
        return collector_service.is_connected()
    
    def get_board_info(self) -> Dict[str, Any]:
        """
        Get information about the connected board.
        
        Returns:
            Dict with board information
        """
        if not self._check_initialized():
            return {"error": "Service not initialized"}
            
        try:
            collector_service = self.get_component('collector_service')
            if not collector_service:
                return {"error": "Collector service not available"}
                
            if not collector_service.is_connected():
                return {"error": "Not connected to a board"}
                
            board_info = collector_service.get_board_info()
            if not board_info:
                return {"error": "Failed to get board information"}
                
            return board_info
        except Exception as e:
            logging.error(f"Error getting board info: {e}")
            return {"error": str(e)}
    
    #
    # Streaming methods
    #
    
    def start_stream(self) -> bool:
        """
        Start streaming data from the board.
        
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            collector_service = self.get_component('collector_service')
            visualization_service = self.get_component('visualization_service')
            processor_service = self.get_component('processor_service')
            
            if not collector_service:
                self._set_status(False, "Collector service not available")
                return False
                
            # Check if connected
            if not collector_service.is_connected():
                self._set_status(False, "Not connected to a board")
                return False
                
            # Check if already streaming
            if collector_service.is_streaming_active():
                self._set_status(False, "Already streaming")
                return False
                
            # Start streaming
            success = collector_service.start_stream()
            
            if success:
                # Initialize processor if available
                if processor_service:
                    sampling_rate = collector_service.get_sampling_rate()
                    if sampling_rate > 0:
                        processor_service.initialize_processor(sampling_rate)
                
                # Start visualization if available
                if visualization_service:
                    processor = processor_service.processor if processor_service else None
                    visualization_service.create_eeg_visualizer(
                        collector_service.collector,
                        processor
                    )
                    visualization_service.start_eeg_visualization()
                
                self._set_status(True, "Streaming started")
                # Dispatch event
                dispatch(EventType.STREAM_STARTED, {})
                return True
            else:
                self._set_status(False, "Failed to start streaming")
                return False
                
        except Exception as e:
            self._set_status(False, f"Error starting stream: {e}")
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
        if not self._check_initialized():
            return False
            
        try:
            collector_service = self.get_component('collector_service')
            visualization_service = self.get_component('visualization_service')
            
            if not collector_service:
                self._set_status(False, "Collector service not available")
                return False
                
            # Check if streaming
            if not collector_service.is_streaming_active():
                self._set_status(False, "Not currently streaming")
                return False
                
            # Stop streaming
            success = collector_service.stop_stream()
            
            if success:
                # Stop visualization if available
                if visualization_service:
                    visualization_service.stop_eeg_visualization()
                
                self._set_status(True, "Streaming stopped")
                # Dispatch event
                dispatch(EventType.STREAM_STOPPED, {})
                return True
            else:
                self._set_status(False, "Failed to stop streaming")
                return False
                
        except Exception as e:
            self._set_status(False, f"Error stopping stream: {e}")
            logging.error(f"Error stopping stream: {e}")
            return False
    
    def is_streaming(self) -> bool:
        """
        Check if streaming is active.
        
        Returns:
            bool: True if streaming is active
        """
        if not self._check_initialized():
            return False
            
        collector_service = self.get_component('collector_service')
        if not collector_service:
            return False
            
        return collector_service.is_streaming_active()
    
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
        if not self._check_initialized():
            return False
            
        try:
            collector_service = self.get_component('collector_service')
            recording_service = self.get_component('recording_service')
            
            if not collector_service or not recording_service:
                self._set_status(False, "Required services not available")
                return False
                
            # Check if connected and streaming
            if not collector_service.is_connected():
                self._set_status(False, "Not connected to a board")
                return False
                
            if not collector_service.is_streaming_active():
                self._set_status(False, "Not currently streaming")
                return False
                
            # Check if already recording
            if recording_service.is_recording():
                self._set_status(False, "Already recording")
                return False
                
            # Start recording
            success = recording_service.start_recording(
                collector_service.collector, filename, data_type
            )
            
            if success:
                self._set_status(True, f"Recording started to {filename}")
                # Dispatch event
                dispatch(EventType.RECORDING_STARTED, {"filename": filename, "data_type": data_type})
                return True
            else:
                self._set_status(False, "Failed to start recording")
                return False
                
        except Exception as e:
            self._set_status(False, f"Error starting recording: {e}")
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
        if not self._check_initialized():
            return False
            
        try:
            collector_service = self.get_component('collector_service')
            recording_service = self.get_component('recording_service')
            
            if not collector_service or not recording_service:
                self._set_status(False, "Required services not available")
                return False
                
            # Check if recording
            if not recording_service.is_recording():
                self._set_status(False, "Not currently recording")
                return False
                
            # Stop recording
            success = recording_service.stop_recording(collector_service.collector)
            
            if success:
                self._set_status(True, "Recording stopped and saved")
                # Dispatch event
                dispatch(EventType.RECORDING_STOPPED, {})
                return True
            else:
                self._set_status(False, "Failed to stop recording")
                return False
                
        except Exception as e:
            self._set_status(False, f"Error stopping recording: {e}")
            logging.error(f"Error stopping recording: {e}")
            return False
    
    def is_recording(self) -> bool:
        """
        Check if recording is active.
        
        Returns:
            bool: True if recording is active
        """
        if not self._check_initialized():
            return False
            
        recording_service = self.get_component('recording_service')
        if not recording_service:
            return False
            
        return recording_service.is_recording()
    
    def add_marker(self, marker_value: int) -> bool:
        """
        Add a marker to the data stream.
        
        Args:
            marker_value: Marker value to add
            
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            collector_service = self.get_component('collector_service')
            recording_service = self.get_component('recording_service')
            
            if not collector_service or not recording_service:
                self._set_status(False, "Required services not available")
                return False
                
            # Check if recording
            if not recording_service.is_recording():
                self._set_status(False, "Not currently recording")
                return False
                
            # Add marker
            success = recording_service.insert_marker(
                collector_service.collector, marker_value
            )
            
            if success:
                self._set_status(True, f"Marker {marker_value} added")
                # Dispatch event
                dispatch(EventType.MARKER_ADDED, {"value": marker_value})
                return True
            else:
                self._set_status(False, "Failed to add marker")
                return False
                
        except Exception as e:
            self._set_status(False, f"Error adding marker: {e}")
            logging.error(f"Error adding marker: {e}")
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
        if not self._check_initialized():
            return False
            
        try:
            visualization_service = self.get_component('visualization_service')
            
            if not visualization_service:
                self._set_status(False, "Visualization service not available")
                return False
                
            # Apply filters
            visualization_service.set_bandpass_filter(bandpass, bandpass_low, bandpass_high)
            visualization_service.set_notch_filter(notch, notch_freq)
            visualization_service.set_detrend(detrend)
            
            self._set_status(True, "Filters applied to visualization")
            # Dispatch event
            dispatch(EventType.FILTER_APPLIED, {
                "bandpass": bandpass,
                "bandpass_low": bandpass_low,
                "bandpass_high": bandpass_high,
                "notch": notch,
                "notch_freq": notch_freq,
                "detrend": detrend
            })
            return True
                
        except Exception as e:
            self._set_status(False, f"Error applying filters: {e}")
            logging.error(f"Error applying filters: {e}")
            return False
    
    def remove_filters(self) -> bool:
        """
        Remove all filters from the EEG data visualization.
        
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            visualization_service = self.get_component('visualization_service')
            
            if not visualization_service:
                self._set_status(False, "Visualization service not available")
                return False
                
            # Remove filters
            visualization_service.set_bandpass_filter(False, 1.0, 50.0)
            visualization_service.set_notch_filter(False)
            visualization_service.set_detrend(False)
            
            self._set_status(True, "Filters removed from visualization")
            # Dispatch event
            dispatch(EventType.FILTER_REMOVED, {})
            return True
                
        except Exception as e:
            self._set_status(False, f"Error removing filters: {e}")
            logging.error(f"Error removing filters: {e}")
            return False
    
    def calculate_eeg_metrics(self) -> Dict[str, Any]:
        """
        Calculate EEG metrics from current data.
        
        Returns:
            Dict with EEG metrics
        """
        if not self._check_initialized():
            return {"error": "Service not initialized"}
            
        try:
            collector_service = self.get_component('collector_service')
            processor_service = self.get_component('processor_service')
            
            if not collector_service or not processor_service:
                return {"error": "Required services not available"}
                
            # Check if connected and streaming
            if not collector_service.is_connected():
                return {"error": "Not connected to a board"}
                
            if not collector_service.is_streaming_active():
                return {"error": "Not currently streaming"}
                
            # Get sampling rate
            sampling_rate = collector_service.get_sampling_rate()
            if sampling_rate <= 0:
                return {"error": "Invalid sampling rate"}
                
            # Initialize processor if needed
            if not hasattr(processor_service, 'processor') or processor_service.processor is None:
                processor_service.initialize_processor(sampling_rate)
                
            # Get data
            data, _ = collector_service.get_board_data(4 * sampling_rate)  # 4 seconds of data
            if data.size == 0:
                return {"error": "No data available"}
                
            # Get EEG channels
            eeg_channels = collector_service.get_eeg_channels()
            if not eeg_channels:
                return {"error": "No EEG channels available"}
                
            # Calculate metrics
            metrics = processor_service.get_eeg_metrics(data, eeg_channels)
            
            # Format metrics
            formatted_metrics = {}
            for name, value in metrics.items():
                # Handle numpy arrays by taking first value
                if hasattr(value, '__iter__'):
                    value = value[0]
                formatted_metrics[name] = float(value)
                
            return formatted_metrics
                
        except Exception as e:
            logging.error(f"Error calculating EEG metrics: {e}")
            return {"error": str(e)}
    
    def show_brain_map(self) -> bool:
        """
        Show brain map visualization.
        
        Returns:
            bool: True if successful
        """
        if not self._check_initialized():
            return False
            
        try:
            collector_service = self.get_component('collector_service')
            processor_service = self.get_component('processor_service')
            visualization_service = self.get_component('visualization_service')
            
            if not collector_service or not processor_service or not visualization_service:
                self._set_status(False, "Required services not available")
                return False
                
            # Check if connected and streaming
            if not collector_service.is_connected():
                self._set_status(False, "Not connected to a board")
                return False
                
            if not collector_service.is_streaming_active():
                self._set_status(False, "Not currently streaming")
                return False
                
            # Initialize processor if needed
            sampling_rate = collector_service.get_sampling_rate()
            if sampling_rate <= 0:
                self._set_status(False, "Invalid sampling rate")
                return False
                
            if not hasattr(processor_service, 'processor') or processor_service.processor is None:
                processor_service.initialize_processor(sampling_rate)
                
            # Create and start brain map visualization
            success = visualization_service.create_brain_map_visualizer(
                collector_service.collector,
                processor_service.processor
            )
            
            if success:
                visualization_service.start_brain_map_visualization()
                self._set_status(True, "Brain map visualization started")
                return True
            else:
                self._set_status(False, "Failed to create brain map visualizer")
                return False
                
        except Exception as e:
            self._set_status(False, f"Error showing brain map: {e}")
            logging.error(f"Error showing brain map: {e}")
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
        if not self._check_initialized():
            return False
            
        try:
            collector_service = self.get_component('collector_service')
            visualization_service = self.get_component('visualization_service')
            
            if not collector_service or not visualization_service:
                self._set_status(False, "Required services not available")
                return False
                
            # Check if connected and streaming
            if not collector_service.is_connected():
                self._set_status(False, "Not connected to a board")
                return False
                
            if not collector_service.is_streaming_active():
                self._set_status(False, "Not currently streaming")
                return False
                
            # Check if visualization is closed
            if not visualization_service.visualization_closed():
                self._set_status(False, "Visualization already visible")
                return True
                
            # Create and start visualization
            success = visualization_service.create_eeg_visualizer(
                collector_service.collector,
                None  # We'll initialize the processor later
            )
            
            if success:
                visualization_service.start_eeg_visualization()
                self._set_status(True, "EEG visualization window shown")
                return True
            else:
                self._set_status(False, "Failed to create EEG visualizer")
                return False
                
        except Exception as e:
            self._set_status(False, f"Error showing EEG visualization: {e}")
            logging.error(f"Error showing EEG visualization: {e}")
            return False
    
    def get_application_state(self) -> Dict[str, Any]:
        """
        Get comprehensive application state.
        
        Returns:
            Dict with application state
        """
        if not self._check_initialized():
            return {"error": "Service not initialized"}
            
        try:
            collector_service = self.get_component('collector_service')
            recording_service = self.get_component('recording_service')
            
            if not collector_service:
                return {"error": "Collector service not available"}
                
            # Get board info
            board_info = {}
            if collector_service.is_connected():
                board_info = collector_service.get_board_info()
                
            # Get connection state
            connected = collector_service.is_connected()
            
            # Get streaming state
            streaming = collector_service.is_streaming_active()
            
            # Get recording state
            recording = False
            recording_info = {}
            if recording_service:
                recording = recording_service.is_recording()
                if recording:
                    recording_info = {
                        "duration": recording_service.get_recording_duration(),
                        "filename": recording_service.get_recording_filename()
                    }
            
            return {
                "board_info": board_info,
                "connected": connected,
                "streaming": streaming,
                "recording": recording,
                "recording_info": recording_info
            }
                
        except Exception as e:
            logging.error(f"Error getting application state: {e}")
            return {"error": str(e)}