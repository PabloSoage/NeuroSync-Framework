from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple


class CollectorInterface(ABC):
    """
    Interface for EEG data collectors.
    Defines methods that should be implemented by any EEG collector.
    """

    @abstractmethod
    def prepare_session(self) -> None:
        """
        Prepare the session for data collection.
        """
        pass

    @abstractmethod
    def start_stream(self) -> None:
        """
        Start streaming EEG data.
        """
        pass

    @abstractmethod
    def stop_stream(self) -> None:
        """
        Stop streaming EEG data.
        """
        pass

    @abstractmethod
    def release_session(self) -> None:
        """
        Release resources after the session is finished.
        """
        pass

    @abstractmethod
    def get_data(self, num_samples: Optional[int] = None) -> Tuple[Any, List[int]]:
        """
        Get collected EEG data.

        Args:
            num_samples: Number of samples to get, all data if None

        Returns:
            Tuple containing the EEG data and timestamps in ms
        """
        pass

    @abstractmethod
    def save_data(self, filename: str, data_type: str = "raw") -> None:
        """
        Save collected data to a file.

        Args:
            filename: Path to save the file
            data_type: Type of data to save ('raw' or 'processed')
        """
        pass

    @abstractmethod
    def get_board_info(self) -> Dict[str, Any]:
        """
        Get information about the connected EEG board.

        Returns:
            Dictionary with board information
        """
        pass

    @abstractmethod
    def insert_marker(self, marker_value: int) -> None:
        """
        Insert a marker into the data stream.

        Args:
            marker_value: Value of the marker to insert
        """
        pass
