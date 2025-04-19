"""
Interface definitions for BCI system modules.

This module provides interface classes that define contracts for modules
in the BCI system, following the Interface Segregation Principle.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class IRecordingModule(ABC):
    """Interface for any module that supports recording functionality."""
    
    @abstractmethod
    def start_recording(self, filename: str, options: Dict[str, Any]) -> bool:
        """Start recording data to a file.
        
        Args:
            filename: The path where data should be recorded
            options: Dictionary of recording options specific to the module
            
        Returns:
            bool: True if recording started successfully, False otherwise
        """
        pass
        
    @abstractmethod
    def stop_recording(self) -> bool:
        """Stop any ongoing recording.
        
        Returns:
            bool: True if recording stopped successfully, False otherwise
        """
        pass
        
    @abstractmethod
    def is_recording_active(self) -> bool:
        """Check if recording is currently active.
        
        Returns:
            bool: True if recording is active, False otherwise
        """
        pass
        
    @property
    @abstractmethod
    def recording_info(self) -> Dict[str, Any]:
        """Get information about the current recording.
        
        Returns:
            Dict[str, Any]: Recording information including duration, file paths, etc.
        """
        pass


class IEEGModule(IRecordingModule):
    """Interface for EEG processing module."""
    
    @abstractmethod
    def connect_to_device(self) -> bool:
        """Connect to EEG device/board.
        
        Returns:
            bool: True if connected successfully, False otherwise
        """
        pass
        
    @abstractmethod
    def disconnect_from_device(self) -> bool:
        """Disconnect from EEG device/board.
        
        Returns:
            bool: True if disconnected successfully, False otherwise
        """
        pass
        
    @abstractmethod
    def start_stream(self) -> bool:
        """Start EEG data streaming.
        
        Returns:
            bool: True if stream started successfully, False otherwise
        """
        pass
        
    @abstractmethod
    def stop_stream(self) -> bool:
        """Stop EEG data streaming.
        
        Returns:
            bool: True if stream stopped successfully, False otherwise
        """
        pass
        
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to EEG device.
        
        Returns:
            bool: Connection status
        """
        pass
        
    @abstractmethod
    def is_streaming(self) -> bool:
        """Check if data is streaming.
        
        Returns:
            bool: Streaming status
        """
        pass
        
    @abstractmethod
    def show_visualization(self, visible: bool = True) -> None:
        """Show or hide EEG visualizations.
        
        Args:
            visible: Whether visualizations should be visible
        """
        pass


class IInputModule(IRecordingModule):
    """Interface for input collection module."""
    
    @abstractmethod
    def is_ready(self) -> bool:
        """Check if input collector is ready to record.
        
        Returns:
            bool: Ready status
        """
        pass
        
    @abstractmethod
    def set_tracked_inputs(self, input_list: list) -> None:
        """Set which inputs should be tracked.
        
        Args:
            input_list: List of input identifiers to track
        """
        pass
        
    @abstractmethod
    def show_visualization(self, visible: bool = True) -> None:
        """Show or hide input visualizations.
        
        Args:
            visible: Whether visualizations should be visible
        """
        pass
