"""
Interaction service for managing API interactions.

This service coordinates between the interaction API and the underlying services,
ensuring proper state management and event handling.
"""

import logging
from typing import Dict, List, Any, Optional

from ..core.event_system import EventSystem, EventType, Event
from ..interaction_api import EEGProcessorInteractionAPI


class InteractionService:
    """
    Service for managing interaction API operations.
    
    This service provides a layer between the interaction API and the core
    services, handling state management and coordination.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = InteractionService()
        return cls._instance
    
    def __init__(self):
        """Initialize the interaction service."""
        self.event_system = EventSystem.get_instance()
        self._state = {
            "connected": False,
            "streaming": False,
            "recording": False,
            "visualizing": False,
            "current_board_id": None,
            "current_preset": None
        }
        
        # Subscribe to events to maintain state
        self._subscribe_to_events()
        
        logging.info("Interaction service initialized")
    
    def _subscribe_to_events(self):
        """Subscribe to events to maintain internal state."""
        self.event_system.subscribe(EventType.BOARD_CONNECT, self._on_board_connect)
        self.event_system.subscribe(EventType.BOARD_DISCONNECT, self._on_board_disconnect)
        self.event_system.subscribe(EventType.STREAM_START, self._on_stream_start)
        self.event_system.subscribe(EventType.STREAM_STOP, self._on_stream_stop)
        self.event_system.subscribe(EventType.RECORDING_START, self._on_recording_start)
        self.event_system.subscribe(EventType.RECORDING_STOP, self._on_recording_stop)
        self.event_system.subscribe(EventType.VISUALIZATION_START, self._on_visualization_start)
        self.event_system.subscribe(EventType.VISUALIZATION_STOP, self._on_visualization_stop)
    
    def _on_board_connect(self, event: Event):
        """Handle board connection events."""
        self._state["connected"] = True
        self._state["current_board_id"] = event.data.get("board_id")
        self._state["current_preset"] = event.data.get("preset")
    
    def _on_board_disconnect(self, event: Event):
        """Handle board disconnection events."""
        self._state["connected"] = False
        self._state["streaming"] = False
        self._state["current_board_id"] = None
        self._state["current_preset"] = None
    
    def _on_stream_start(self, event: Event):
        """Handle stream start events."""
        self._state["streaming"] = True
    
    def _on_stream_stop(self, event: Event):
        """Handle stream stop events."""
        self._state["streaming"] = False
        self._state["recording"] = False  # Stop recording if streaming stops
    
    def _on_recording_start(self, event: Event):
        """Handle recording start events."""
        self._state["recording"] = True
    
    def _on_recording_stop(self, event: Event):
        """Handle recording stop events."""
        self._state["recording"] = False
    
    def _on_visualization_start(self, event: Event):
        """Handle visualization start events."""
        self._state["visualizing"] = True
    
    def _on_visualization_stop(self, event: Event):
        """Handle visualization stop events."""
        self._state["visualizing"] = False
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current interaction service state.
        
        Returns:
            Dictionary with current state
        """
        return self._state.copy()
    
    def validate_operation(self, operation: str) -> Dict[str, Any]:
        """
        Validate if an operation can be performed given current state.
        
        Args:
            operation: Name of the operation to validate
            
        Returns:
            Dictionary with validation result
        """
        validations = {
            "connect": lambda: not self._state["connected"],
            "disconnect": lambda: self._state["connected"],
            "start_stream": lambda: self._state["connected"] and not self._state["streaming"],
            "stop_stream": lambda: self._state["streaming"],
            "start_recording": lambda: self._state["streaming"],
            "stop_recording": lambda: self._state["recording"],
            "start_visualization": lambda: self._state["streaming"],
            "stop_visualization": lambda: self._state["visualizing"],
            "apply_filters": lambda: self._state["streaming"],
            "insert_marker": lambda: self._state["streaming"],
            "add_streamer": lambda: self._state["connected"],
            "remove_streamer": lambda: self._state["connected"],
            "perform_ica": lambda: self._state["streaming"],
            "get_metrics": lambda: self._state["streaming"]
        }
        
        if operation not in validations:
            return {
                "valid": False,
                "message": f"Unknown operation: {operation}"
            }
        
        try:
            valid = validations[operation]()
            return {
                "valid": valid,
                "message": "Operation allowed" if valid else f"Operation {operation} not allowed in current state"
            }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Error validating operation: {e}"
            }
    
    # Convenience methods that delegate to the interaction API
    
    def get_available_boards(self) -> List[Dict[str, Any]]:
        """Get available boards."""
        return EEGProcessorInteractionAPI.get_available_boards()
    
    def connect_to_board(self, board_id: int, params: Dict[str, Any] = None, 
                        preset: int = 0) -> Dict[str, Any]:
        """Connect to a board with validation."""
        validation = self.validate_operation("connect")
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"]
            }
        
        return EEGProcessorInteractionAPI.connect_to_board(board_id, params, preset)
    
    def disconnect_from_board(self) -> Dict[str, Any]:
        """Disconnect from board with validation."""
        validation = self.validate_operation("disconnect")
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"]
            }
        
        return EEGProcessorInteractionAPI.disconnect_from_board()
    
    def start_stream(self, buffer_size: int = 450000) -> Dict[str, Any]:
        """Start stream with validation."""
        validation = self.validate_operation("start_stream")
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"]
            }
        
        return EEGProcessorInteractionAPI.start_stream(buffer_size)
    
    def stop_stream(self) -> Dict[str, Any]:
        """Stop stream with validation."""
        validation = self.validate_operation("stop_stream")
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"]
            }
        
        return EEGProcessorInteractionAPI.stop_stream()
    
    def start_recording(self, filename: str, data_type: str = "raw") -> Dict[str, Any]:
        """Start recording with validation."""
        validation = self.validate_operation("start_recording")
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"]
            }
        
        return EEGProcessorInteractionAPI.start_recording(filename, data_type)
    
    def stop_recording(self) -> Dict[str, Any]:
        """Stop recording with validation."""
        validation = self.validate_operation("stop_recording")
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"]
            }
        
        return EEGProcessorInteractionAPI.stop_recording()
    
    def apply_filters(self, filter_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply filters with validation."""
        validation = self.validate_operation("apply_filters")
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"]
            }
        
        return EEGProcessorInteractionAPI.apply_filters(filter_config)
    
    def start_visualization(self, viz_type: str = "eeg") -> Dict[str, Any]:
        """Start visualization with validation."""
        validation = self.validate_operation("start_visualization")
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"]
            }
        
        return EEGProcessorInteractionAPI.start_visualization(viz_type)
    
    def stop_visualization(self, viz_type: str = "eeg") -> Dict[str, Any]:
        """Stop visualization with validation."""
        validation = self.validate_operation("stop_visualization")
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"]
            }
        
        return EEGProcessorInteractionAPI.stop_visualization(viz_type)
    
    def insert_marker(self, marker_value: float) -> Dict[str, Any]:
        """Insert marker with validation."""
        validation = self.validate_operation("insert_marker")
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"]
            }
        
        return EEGProcessorInteractionAPI.insert_marker(marker_value)
    
    def add_streamer(self, streamer_params: str) -> Dict[str, Any]:
        """Add streamer with validation."""
        validation = self.validate_operation("add_streamer")
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"]
            }
        
        return EEGProcessorInteractionAPI.add_streamer(streamer_params)
    
    def remove_streamer(self, streamer_params: str) -> Dict[str, Any]:
        """Remove streamer with validation."""
        validation = self.validate_operation("remove_streamer")
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"]
            }
        
        return EEGProcessorInteractionAPI.remove_streamer(streamer_params)
    
    def perform_ica(self, num_components: int) -> Dict[str, Any]:
        """Perform ICA with validation."""
        validation = self.validate_operation("perform_ica")
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"]
            }
        
        return EEGProcessorInteractionAPI.perform_ica(num_components)
    
    def get_eeg_metrics(self) -> Dict[str, Any]:
        """Get EEG metrics with validation."""
        validation = self.validate_operation("get_metrics")
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"]
            }
        
        return EEGProcessorInteractionAPI.get_eeg_metrics()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return EEGProcessorInteractionAPI.get_system_status()
