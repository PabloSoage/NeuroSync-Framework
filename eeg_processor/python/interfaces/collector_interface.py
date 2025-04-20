from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple


class CollectorInterface(ABC):
    """
    Base interface for data collectors.
    Defines core methods that should be implemented by any collector.
    """

    @abstractmethod
    def prepare_session(self) -> None:
        """Prepare the session for data collection."""
        pass

    @abstractmethod
    def start_stream(self) -> None:
        """Start streaming data."""
        pass

    @abstractmethod
    def stop_stream(self) -> None:
        """Stop streaming data."""
        pass

    @abstractmethod
    def release_session(self) -> None:
        """Release resources after the session is finished."""
        pass

    @abstractmethod
    def get_data(self, num_samples: Optional[int] = None) -> Tuple[Any, List[int]]:
        """
        Get collected data.

        Args:
            num_samples: Number of samples to get, all data if None

        Returns:
            Tuple containing the data and timestamps in ms
        """
        pass

    @abstractmethod
    def get_device_info(self) -> Dict[str, Any]:
        """
        Get information about the connected device.

        Returns:
            Dictionary with device information
        """
        pass


class DataStorageInterface(ABC):
    """Interface for data storage operations."""

    @abstractmethod
    def save_data(self, filename: str, data_type: str = "raw") -> None:
        """
        Save collected data to a file.

        Args:
            filename: Path to save the file
            data_type: Type of data to save ('raw' or 'processed')
        """
        pass


class ContinuousRecordingInterface(ABC):
    """Interface for continuous data recording operations."""
    
    @abstractmethod
    def start_continuous_recording(self, filename: str, data_type: str = "raw") -> None:
        """
        Start continuous recording of data to a file.
        
        Args:
            filename: Path to save the file
            data_type: Type of data to record ('raw' or 'processed')
        """
        pass
    
    @abstractmethod
    def stop_continuous_recording(self) -> None:
        """Stop continuous recording and close the file."""
        pass


class MarkerInterface(ABC):
    """Interface for marker operations."""

    @abstractmethod
    def insert_marker(self, marker_value: Any) -> None:
        """
        Insert a marker into the data stream.

        Args:
            marker_value: Value of the marker to insert
        """
        pass


class ConfigurableCollectorInterface(ABC):
    """Interface for collectors that can be configured."""
    
    @abstractmethod
    def config_device(self, config: str) -> str:
        """
        Send configuration to the device.
        
        Args:
            config: Configuration string to send
            
        Returns:
            Response from the device
        """
        pass
    
    @abstractmethod
    def set_preset(self, preset: Any) -> bool:
        """
        Change the current preset/mode.
        
        Args:
            preset: New preset value
            
        Returns:
            Success status
        """
        pass
