from abc import ABC, abstractmethod


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
