"""
Interaction API for the EEG processor.

This provides a clean interface for controlling the EEG processor application.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Callable

from .core.event_system import EventType, subscribe, unsubscribe
from .services.interaction_service import InteractionService

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EEGProcessorAPI:
    """
    Main API for controlling the EEG processor.
    
    This class provides methods to control the application and access real-time events.
    """
    
    # Dictionary of registered event callbacks
    _event_callbacks = {}
    _next_callback_id = 1
    
    @classmethod
    def initialize(cls, app, collector_service, processor_service, recording_service, visualization_service):
        """
        Initialize the API with application components.
        
        Args:
            app: The main application
            collector_service: The collector service
            processor_service: The processor service
            recording_service: The recording service
            visualization_service: The visualization service
        """
        # Initialize the service with the components
        service = InteractionService.get_instance()
        components = {
            'app': app,
            'collector_service': collector_service,
            'processor_service': processor_service,
            'recording_service': recording_service,
            'visualization_service': visualization_service
        }
        service.initialize(components)
        
        # Subscribe to core events
        from .core.event_system import EventType, subscribe
        subscribe(EventType.EEG_DATA, cls._on_eeg_data)
        subscribe(EventType.STATE_CHANGE, cls._on_state_change)
        subscribe(EventType.BOARD_CONNECTED, cls._on_board_connected)
        subscribe(EventType.BOARD_DISCONNECTED, cls._on_board_disconnected)
        subscribe(EventType.STREAM_STARTED, cls._on_stream_started)
        subscribe(EventType.STREAM_STOPPED, cls._on_stream_stopped)
        subscribe(EventType.RECORDING_STARTED, cls._on_recording_started)
        subscribe(EventType.RECORDING_STOPPED, cls._on_recording_stopped)
        subscribe(EventType.FILTER_APPLIED, cls._on_filter_applied)
        subscribe(EventType.FILTER_REMOVED, cls._on_filter_removed)
        subscribe(EventType.MARKER_ADDED, cls._on_marker_added)
        
        logger.info("Interaction API initialized")
    
    @classmethod
    def get_last_operation_status(cls) -> Dict[str, Any]:
        """Get the status of the last operation."""
        service = InteractionService.get_instance()
        return service.get_last_status()
    
    #
    # Event handling methods
    #
    
    @classmethod
    def _on_eeg_data(cls, data: Any) -> None:
        """Handle EEG data events."""
        # Skip to avoid overwhelming with data
        # Only notify for specific events like state changes
        pass
    
    @classmethod
    def _on_state_change(cls, state: Dict[str, Any]) -> None:
        """Handle state change events."""
        # Notify all registered event callbacks
        cls._notify_event_callbacks(state)
    
    @classmethod
    def _on_board_connected(cls, data: Any) -> None:
        """Handle board connected events."""
        state = {"event_type": "board_connected", "data": data}
        cls._notify_event_callbacks(state)
    
    @classmethod
    def _on_board_disconnected(cls, data: Any) -> None:
        """Handle board disconnected events."""
        state = {"event_type": "board_disconnected"}
        cls._notify_event_callbacks(state)
    
    @classmethod
    def _on_stream_started(cls, data: Any) -> None:
        """Handle stream started events."""
        state = {"event_type": "stream_started"}
        cls._notify_event_callbacks(state)
    
    @classmethod
    def _on_stream_stopped(cls, data: Any) -> None:
        """Handle stream stopped events."""
        state = {"event_type": "stream_stopped"}
        cls._notify_event_callbacks(state)
    
    @classmethod
    def _on_recording_started(cls, data: Any) -> None:
        """Handle recording started events."""
        state = {"event_type": "recording_started", "data": data}
        cls._notify_event_callbacks(state)
    
    @classmethod
    def _on_recording_stopped(cls, data: Any) -> None:
        """Handle recording stopped events."""
        state = {"event_type": "recording_stopped"}
        cls._notify_event_callbacks(state)
    
    @classmethod
    def _on_filter_applied(cls, data: Any) -> None:
        """Handle filter applied events."""
        state = {"event_type": "filter_applied", "filters": data}
        cls._notify_event_callbacks(state)
    
    @classmethod
    def _on_filter_removed(cls, data: Any) -> None:
        """Handle filter removed events."""
        state = {"event_type": "filter_removed"}
        cls._notify_event_callbacks(state)
    
    @classmethod
    def _on_marker_added(cls, data: Any) -> None:
        """Handle marker added events."""
        state = {"event_type": "marker_added", "marker": data}
        cls._notify_event_callbacks(state)
    
    @classmethod
    def _notify_event_callbacks(cls, event: Any) -> None:
        """Notify all registered event callbacks."""
        # Make a copy of the callbacks to avoid modification during iteration
        callbacks = list(cls._event_callbacks.values())
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
    
    #
    # Event registration methods
    #
    
    @classmethod
    def register_event_callback(cls, callback: Callable[[Any], None]) -> int:
        """
        Register a callback for real-time events.
        
        Args:
            callback: Function to call when events occur
            
        Returns:
            int: Callback ID for unregistering
        """
        callback_id = cls._next_callback_id
        cls._event_callbacks[callback_id] = callback
        cls._next_callback_id += 1
        return callback_id
    
    @classmethod
    def unregister_event_callback(cls, callback_id: int) -> bool:
        """
        Unregister an event callback.
        
        Args:
            callback_id: ID of the callback to unregister
            
        Returns:
            bool: True if successful
        """
        if callback_id in cls._event_callbacks:
            del cls._event_callbacks[callback_id]
            return True
        return False
    
    #
    # Board connection methods
    #
    
    @classmethod
    def connect_board(cls, board_id: int, params: Dict[str, Any], preset: int) -> bool:
        """
        Connect to an EEG board.
        
        Args:
            board_id: ID of the board to connect to
            params: Connection parameters
            preset: Data preset to use
            
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.connect_board(board_id, params, preset)
    
    @classmethod
    def disconnect_board(cls) -> bool:
        """
        Disconnect from the current EEG board.
        
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.disconnect_board()
    
    @classmethod
    def is_connected(cls) -> bool:
        """
        Check if connected to a board.
        
        Returns:
            bool: True if connected
        """
        service = InteractionService.get_instance()
        return service.is_connected()
    
    @classmethod
    def get_board_info(cls) -> Dict[str, Any]:
        """
        Get information about the connected board.
        
        Returns:
            Dict with board information
        """
        service = InteractionService.get_instance()
        return service.get_board_info()
    
    #
    # Streaming methods
    #
    
    @classmethod
    def start_stream(cls) -> bool:
        """
        Start streaming data from the board.
        
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.start_stream()
    
    @classmethod
    def stop_stream(cls) -> bool:
        """
        Stop streaming data from the board.
        
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.stop_stream()
    
    @classmethod
    def is_streaming(cls) -> bool:
        """
        Check if streaming is active.
        
        Returns:
            bool: True if streaming is active
        """
        service = InteractionService.get_instance()
        return service.is_streaming()
    
    #
    # Recording methods
    #
    
    @classmethod
    def start_recording(cls, filename: str, data_type: str = "raw") -> bool:
        """
        Start recording data to file.
        
        Args:
            filename: Path to save the recording
            data_type: Type of data to record ("raw", "processed", or "both")
            
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.start_recording(filename, data_type)
    
    @classmethod
    def stop_recording(cls) -> bool:
        """
        Stop recording and save data to file.
        
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.stop_recording()
    
    @classmethod
    def is_recording(cls) -> bool:
        """
        Check if recording is active.
        
        Returns:
            bool: True if recording is active
        """
        service = InteractionService.get_instance()
        return service.is_recording()
    
    @classmethod
    def add_marker(cls, marker_value: int) -> bool:
        """
        Add a marker to the data stream.
        
        Args:
            marker_value: Marker value to add
            
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.add_marker(marker_value)
    
    #
    # Processing methods
    #
    
    @classmethod
    def apply_filters(cls, bandpass: bool = True, bandpass_low: float = 1.0, 
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
        service = InteractionService.get_instance()
        return service.apply_filters(bandpass, bandpass_low, bandpass_high, notch, notch_freq, detrend)
    
    @classmethod
    def remove_filters(cls) -> bool:
        """
        Remove all filters from the EEG data visualization.
        
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.remove_filters()
    
    @classmethod
    def calculate_eeg_metrics(cls) -> Dict[str, Any]:
        """
        Calculate EEG metrics from current data.
        
        Returns:
            Dict with EEG metrics
        """
        service = InteractionService.get_instance()
        return service.calculate_eeg_metrics()
    
    @classmethod
    def show_brain_map(cls) -> bool:
        """
        Show brain map visualization.
        
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.show_brain_map()
    
    #
    # Visualization methods
    #
    
    @classmethod
    def show_eeg_visualization(cls) -> bool:
        """
        Show EEG visualization window.
        
        Returns:
            bool: True if successful
        """
        service = InteractionService.get_instance()
        return service.show_eeg_visualization()
    
    #
    # Application state methods
    #
    
    @classmethod
    def get_application_state(cls) -> Dict[str, Any]:
        """
        Get comprehensive application state.
        
        Returns:
            Dict with application state
        """
        service = InteractionService.get_instance()
        return service.get_application_state()