"""
Service for handling interaction API requests.
"""

import logging
from typing import Dict, List, Any, Optional

from ..core.event_system import EventSystem, EventType


class InteractionService:
    """
    Service that handles interaction API requests and coordinates with other services.

    This service acts as a bridge between the external API and internal services,
    publishing events to update the UI when API actions are performed.
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

        logging.info("Interaction service initialized")

    def get_available_boards(self) -> List[Dict[str, Any]]:
        """
        Get list of available EEG boards.

        Returns:
            List of dictionaries with board information
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        return EEGProcessorInteractionAPI.get_available_boards()

    def connect_to_board(
        self, board_id: int, params: Dict[str, Any], preset: int = 0
    ) -> bool:
        """
        Connect to an EEG board.

        Args:
            board_id: ID of the board to connect to
            params: Connection parameters
            preset: Data preset to use

        Returns:
            True if connection successful, False otherwise
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.connect_to_board(board_id, params, preset)

        return result.get("success", False)

    def disconnect_from_board(self) -> Dict[str, Any]:
        """
        Disconnect from the current board.

        Returns:
            Dictionary with disconnection result information
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.disconnect_from_board()

        # El método debe devolver un diccionario completo, no solo un booleano
        # Esto permitirá una mejor información de error y estado
        return result

    def start_stream(self, buffer_size: int = 450000) -> bool:
        """
        Start data streaming.

        Args:
            buffer_size: Size of the buffer for data

        Returns:
            True if streaming started successfully, False otherwise
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.start_stream(buffer_size)

        return result.get("success", False)

    def stop_stream(self) -> bool:
        """
        Stop data streaming.

        Returns:
            True if streaming stopped successfully, False otherwise
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.stop_stream()

        return result.get("success", False)

    def add_streamer(self, streamer_params: str) -> bool:
        """
        Add a data streamer.

        Args:
            streamer_params: Parameters for the streamer

        Returns:
            True if streamer added successfully, False otherwise
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.add_streamer(streamer_params)

        return result.get("success", False)

    def remove_streamer(self, streamer_params: str) -> bool:
        """
        Remove a data streamer.

        Args:
            streamer_params: Parameters for the streamer to remove

        Returns:
            True if streamer removed successfully, False otherwise
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.remove_streamer(streamer_params)

        return result.get("success", False)

    def start_recording(self, filename: str, data_type: str = "raw") -> bool:
        """
        Start data recording.

        Args:
            filename: Path to save the recording
            data_type: Type of data to record ('raw', 'processed', or 'both')

        Returns:
            True if recording started successfully, False otherwise
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.start_recording(filename, data_type)

        return result.get("success", False)

    def stop_recording(self) -> bool:
        """
        Stop data recording.

        Returns:
            True if recording stopped successfully, False otherwise
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.stop_recording()

        return result.get("success", False)

    def insert_marker(self, marker_value: float) -> bool:
        """
        Insert a marker into the data stream.

        Args:
            marker_value: Value of the marker to insert

        Returns:
            True if marker inserted successfully, False otherwise
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.insert_marker(marker_value)

        return result.get("success", False)

    def apply_filters(self, filter_config: Dict[str, Any]) -> bool:
        """
        Apply signal processing filters.

        Args:
            filter_config: Filter configuration

        Returns:
            True if filters applied successfully, False otherwise
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.apply_filters(filter_config)

        return result.get("success", False)

    def start_visualization(self, viz_type: str = "eeg") -> bool:
        """
        Start data visualization.

        Args:
            viz_type: Type of visualization ("eeg" or "brain_map")

        Returns:
            True if visualization started successfully, False otherwise
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.start_visualization(viz_type)

        return result.get("success", False)

    def stop_visualization(self, viz_type: str = "eeg") -> bool:
        """
        Stop data visualization.

        Args:
            viz_type: Type of visualization ("eeg" or "brain_map")

        Returns:
            True if visualization stopped successfully, False otherwise
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.stop_visualization(viz_type)

        return result.get("success", False)

    def perform_ica(self, num_components: int) -> bool:
        """
        Perform Independent Component Analysis.

        Args:
            num_components: Number of ICA components

        Returns:
            True if ICA performed successfully, False otherwise
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.perform_ica(num_components)

        return result.get("success", False)

    def get_eeg_metrics(self) -> Dict[str, Any]:
        """
        Calculate EEG metrics from current data.

        Returns:
            Dictionary with EEG metrics or success/error information
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.get_eeg_metrics()

        return result

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.

        Returns:
            Dictionary with system status
        """
        from ..interaction_api import EEGProcessorInteractionAPI

        result = EEGProcessorInteractionAPI.get_system_status()

        return result

    def config_device(self, config_cmd: str) -> str:
        """
        Send configuration command to the device.

        Args:
            config_cmd: Configuration command string

        Returns:
            Response from the device
        """
        try:
            from ..services.collector_service import CollectorService

            collector_service = CollectorService()
            response = collector_service.config_device(config_cmd)

            # Publish event for UI updates
            self.event_system.publish_event(
                EventType.UI_UPDATE_STATUS,
                {"message": f"Config command sent: {config_cmd}"},
                source="interaction_service",
            )

            # Update config response in UI
            self.event_system.publish_event(
                EventType.UI_UPDATE_CONTROLS,
                {"controls": {"streaming_panel.config_response_text": response}},
                source="interaction_service",
            )

            return response
        except Exception as e:
            logging.error(f"Error sending config command: {e}")
            return f"Error: {str(e)}"

    def save_current_data(self, filename: str, data_type: str = "raw") -> bool:
        """
        Save current data to file.

        Args:
            filename: File to save data to
            data_type: Type of data to save ('raw' or 'processed')

        Returns:
            True if data saved successfully, False otherwise
        """
        try:
            from ..services.collector_service import CollectorService

            collector_service = CollectorService()
            collector_service.save_data(filename, data_type)

            # Publish event for UI updates
            self.event_system.publish_event(
                EventType.UI_UPDATE_STATUS,
                {"message": f"Data saved to {filename}"},
                source="interaction_service",
            )

            return True
        except Exception as e:
            logging.error(f"Error saving data: {e}")
            return False
