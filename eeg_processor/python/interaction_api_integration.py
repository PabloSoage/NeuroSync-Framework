"""
Integration of the interaction API with external API systems.
"""

import logging
from typing import Dict, Any

from .services.interaction_service import InteractionService


class EEGProcessorInteractionApiIntegration:
    """
    Integration class for exposing interaction API through external systems.

    This class provides methods that can be registered with external API
    frameworks to enable remote control of the EEG processor.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = EEGProcessorInteractionApiIntegration()
        return cls._instance

    def __init__(self):
        """Initialize the interaction API integration."""
        self.interaction_service = InteractionService.get_instance()
        self.module_id = "eeg_processor_interaction"

        logging.info("EEG Processor interaction API integration initialized")

    def register_api_methods(self, api_explorer) -> None:
        """
        Register interaction API methods with the API explorer.

        Args:
            api_explorer: API explorer instance to register methods with
        """
        # Register module
        api_explorer.register_module(
            module_id=self.module_id,
            name="EEG Processor Interaction",
            description="Remote control interface for EEG processor operations",
        )

        # Register method groups
        self._register_method_groups(api_explorer)

        # Register all methods
        self._register_connection_methods(api_explorer)
        self._register_streaming_methods(api_explorer)
        self._register_processing_methods(api_explorer)
        self._register_recording_methods(api_explorer)
        self._register_visualization_methods(api_explorer)
        self._register_advanced_methods(api_explorer)
        self._register_status_methods(api_explorer)

        logging.info("Interaction API methods registered")

    def _register_method_groups(self, api_explorer):
        """Register method groups."""
        groups = [
            ("connection", "Board Connection"),
            ("streaming", "Data Streaming"),
            ("processing", "Signal Processing"),
            ("recording", "Data Recording"),
            ("visualization", "Data Visualization"),
            ("advanced", "Advanced Processing"),
            ("status", "System Status"),
        ]

        for group_id, group_name in groups:
            api_explorer.add_method_group(self.module_id, group_id, group_name)

    def _register_connection_methods(self, api_explorer):
        """Register connection-related methods."""
        # Get available boards
        api_explorer.register_method(
            self.module_id,
            "connection",
            "get_available_boards",
            {
                "name": "get_available_boards()",
                "description": "Get list of available EEG boards",
                "type": "GET",
                "params": {},
            },
            self._handle_get_available_boards,
        )

        # Connect to board
        api_explorer.register_method(
            self.module_id,
            "connection",
            "connect_to_board",
            {
                "name": "connect_to_board(board_id, params, preset)",
                "description": "Connect to an EEG board",
                "type": "POST",
                "params": {
                    "board_id": {
                        "type": "number",
                        "description": "ID of the board to connect to",
                        "required": True,
                    },
                    "params": {
                        "type": "object",
                        "description": "Connection parameters (JSON object)",
                        "required": False,
                    },
                    "preset": {
                        "type": "number",
                        "description": "Data preset to use",
                        "required": False,
                    },
                },
            },
            self._handle_connect_to_board,
        )

        # Disconnect from board
        api_explorer.register_method(
            self.module_id,
            "connection",
            "disconnect_from_board",
            {
                "name": "disconnect_from_board()",
                "description": "Disconnect from the current board",
                "type": "POST",
                "params": {},
            },
            self._handle_disconnect_from_board,
        )

        # Get board requirements
        api_explorer.register_method(
            self.module_id,
            "connection",
            "get_board_requirements",
            {
                "name": "get_board_requirements(board_id)",
                "description": "Get parameter requirements for a specific board",
                "type": "GET",
                "params": {
                    "board_id": {
                        "type": "number",
                        "description": "ID of the board",
                        "required": True,
                    }
                },
            },
            self._handle_get_board_requirements,
        )

    def _register_streaming_methods(self, api_explorer):
        """Register streaming-related methods."""
        # Start stream
        api_explorer.register_method(
            self.module_id,
            "streaming",
            "start_stream",
            {
                "name": "start_stream(buffer_size)",
                "description": "Start data streaming",
                "type": "POST",
                "params": {
                    "buffer_size": {
                        "type": "number",
                        "description": "Buffer size for data",
                        "required": False,
                    }
                },
            },
            self._handle_start_stream,
        )

        # Stop stream
        api_explorer.register_method(
            self.module_id,
            "streaming",
            "stop_stream",
            {
                "name": "stop_stream()",
                "description": "Stop data streaming",
                "type": "POST",
                "params": {},
            },
            self._handle_stop_stream,
        )

        # Add streamer
        api_explorer.register_method(
            self.module_id,
            "streaming",
            "add_streamer",
            {
                "name": "add_streamer(streamer_params)",
                "description": "Add a data streamer",
                "type": "POST",
                "params": {
                    "streamer_params": {
                        "type": "text",
                        "description": "Streamer parameters",
                        "required": True,
                    }
                },
            },
            self._handle_add_streamer,
        )

        # Remove streamer
        api_explorer.register_method(
            self.module_id,
            "streaming",
            "remove_streamer",
            {
                "name": "remove_streamer(streamer_params)",
                "description": "Remove a data streamer",
                "type": "POST",
                "params": {
                    "streamer_params": {
                        "type": "text",
                        "description": "Streamer parameters",
                        "required": True,
                    }
                },
            },
            self._handle_remove_streamer,
        )

    def _register_processing_methods(self, api_explorer):
        """Register processing-related methods."""
        # Apply filters
        api_explorer.register_method(
            self.module_id,
            "processing",
            "apply_filters",
            {
                "name": "apply_filters(filter_config)",
                "description": "Apply signal processing filters",
                "type": "POST",
                "params": {
                    "filter_config": {
                        "type": "object",
                        "description": "Filter configuration (JSON object)",
                        "required": True,
                    }
                },
            },
            self._handle_apply_filters,
        )

    def _register_recording_methods(self, api_explorer):
        """Register recording-related methods."""
        # Start recording
        api_explorer.register_method(
            self.module_id,
            "recording",
            "start_recording",
            {
                "name": "start_recording(filename, data_type)",
                "description": "Start data recording",
                "type": "POST",
                "params": {
                    "filename": {
                        "type": "text",
                        "description": "Recording filename",
                        "required": True,
                    },
                    "data_type": {
                        "type": "text",
                        "description": "Type of data to record (raw, processed, both)",
                        "required": False,
                    },
                },
            },
            self._handle_start_recording,
        )

        # Stop recording
        api_explorer.register_method(
            self.module_id,
            "recording",
            "stop_recording",
            {
                "name": "stop_recording()",
                "description": "Stop data recording",
                "type": "POST",
                "params": {},
            },
            self._handle_stop_recording,
        )

        # Insert marker
        api_explorer.register_method(
            self.module_id,
            "recording",
            "insert_marker",
            {
                "name": "insert_marker(marker_value)",
                "description": "Insert a marker into the data stream",
                "type": "POST",
                "params": {
                    "marker_value": {
                        "type": "number",
                        "description": "Marker value",
                        "required": True,
                    }
                },
            },
            self._handle_insert_marker,
        )

        # Get recording status
        api_explorer.register_method(
            self.module_id,
            "recording",
            "get_recording_status",
            {
                "name": "get_recording_status()",
                "description": "Get current recording status",
                "type": "GET",
                "params": {},
            },
            self._handle_get_recording_status,
        )

    def _register_visualization_methods(self, api_explorer):
        """Register visualization-related methods."""
        # Start visualization
        api_explorer.register_method(
            self.module_id,
            "visualization",
            "start_visualization",
            {
                "name": "start_visualization(viz_type)",
                "description": "Start data visualization",
                "type": "POST",
                "params": {
                    "viz_type": {
                        "type": "text",
                        "description": "Type of visualization (eeg, brain_map)",
                        "required": False,
                    }
                },
            },
            self._handle_start_visualization,
        )

        # Stop visualization
        api_explorer.register_method(
            self.module_id,
            "visualization",
            "stop_visualization",
            {
                "name": "stop_visualization(viz_type)",
                "description": "Stop data visualization",
                "type": "POST",
                "params": {
                    "viz_type": {
                        "type": "text",
                        "description": "Type of visualization (eeg, brain_map)",
                        "required": False,
                    }
                },
            },
            self._handle_stop_visualization,
        )

    def _register_advanced_methods(self, api_explorer):
        """Register advanced processing methods."""
        # Perform ICA
        api_explorer.register_method(
            self.module_id,
            "advanced",
            "perform_ica",
            {
                "name": "perform_ica(num_components)",
                "description": "Perform Independent Component Analysis",
                "type": "POST",
                "params": {
                    "num_components": {
                        "type": "number",
                        "description": "Number of ICA components",
                        "required": True,
                    }
                },
            },
            self._handle_perform_ica,
        )

        # Get EEG metrics
        api_explorer.register_method(
            self.module_id,
            "advanced",
            "get_eeg_metrics",
            {
                "name": "get_eeg_metrics()",
                "description": "Calculate EEG metrics from current data",
                "type": "GET",
                "params": {},
            },
            self._handle_get_eeg_metrics,
        )

    def _register_status_methods(self, api_explorer):
        """Register status-related methods."""
        # Get connection status
        api_explorer.register_method(
            self.module_id,
            "status",
            "get_connection_status",
            {
                "name": "get_connection_status()",
                "description": "Get current connection and streaming status",
                "type": "GET",
                "params": {},
            },
            self._handle_get_connection_status,
        )

        # Get system status
        api_explorer.register_method(
            self.module_id,
            "status",
            "get_system_status",
            {
                "name": "get_system_status()",
                "description": "Get comprehensive system status",
                "type": "GET",
                "params": {},
            },
            self._handle_get_system_status,
        )

    # Method handlers
    async def _handle_get_available_boards(self):
        """Handle get_available_boards."""
        return self.interaction_service.get_available_boards()

    async def _handle_connect_to_board(
        self, board_id: int, params: Dict[str, Any] = None, preset: int = 0
    ):
        """Handle connect_to_board."""
        return self.interaction_service.connect_to_board(board_id, params or {}, preset)

    async def _handle_disconnect_from_board(self):
        """Handle disconnect_from_board."""
        result = self.interaction_service.disconnect_from_board()

        # Asegurar que siempre devolvemos un diccionario JSON bien formado
        if isinstance(result, dict):
            return result
        else:
            # Si el resultado no es un diccionario (por ejemplo, es un booleano),
            # convertirlo a un formato JSON adecuado
            success = bool(result)
            return {
                "success": success,
                "message": (
                    "Board disconnected successfully"
                    if success
                    else "Failed to disconnect from board"
                ),
            }

    async def _handle_get_board_requirements(self, board_id: int):
        """Handle get_board_requirements."""
        from .interaction_api import EEGProcessorInteractionAPI

        return {
            "requirements": EEGProcessorInteractionAPI.get_board_requirements(board_id)
        }

    async def _handle_start_stream(self, buffer_size: int = 450000):
        """Handle start_stream."""
        return self.interaction_service.start_stream(buffer_size)

    async def _handle_stop_stream(self):
        """Handle stop_stream."""
        return self.interaction_service.stop_stream()

    async def _handle_add_streamer(self, streamer_params: str):
        """Handle add_streamer."""
        return self.interaction_service.add_streamer(streamer_params)

    async def _handle_remove_streamer(self, streamer_params: str):
        """Handle remove_streamer."""
        return self.interaction_service.remove_streamer(streamer_params)

    async def _handle_apply_filters(self, filter_config: Dict[str, Any]):
        """Handle apply_filters."""
        return self.interaction_service.apply_filters(filter_config)

    async def _handle_start_recording(self, filename: str, data_type: str = "raw"):
        """Handle start_recording."""
        return self.interaction_service.start_recording(filename, data_type)

    async def _handle_stop_recording(self):
        """Handle stop_recording."""
        return self.interaction_service.stop_recording()

    async def _handle_insert_marker(self, marker_value: float):
        """Handle insert_marker."""
        return self.interaction_service.insert_marker(marker_value)

    async def _handle_get_recording_status(self):
        """Handle get_recording_status."""
        from .interaction_api import EEGProcessorInteractionAPI

        return EEGProcessorInteractionAPI.get_recording_status()

    async def _handle_start_visualization(self, viz_type: str = "eeg"):
        """Handle start_visualization."""
        return self.interaction_service.start_visualization(viz_type)

    async def _handle_stop_visualization(self, viz_type: str = "eeg"):
        """Handle stop_visualization."""
        return self.interaction_service.stop_visualization(viz_type)

    async def _handle_perform_ica(self, num_components: int):
        """Handle perform_ica."""
        return self.interaction_service.perform_ica(num_components)

    async def _handle_get_eeg_metrics(self):
        """Handle get_eeg_metrics."""
        return self.interaction_service.get_eeg_metrics()

    async def _handle_get_connection_status(self):
        """Handle get_connection_status."""
        from .interaction_api import EEGProcessorInteractionAPI

        return EEGProcessorInteractionAPI.get_connection_status()

    async def _handle_get_system_status(self):
        """Handle get_system_status."""
        return self.interaction_service.get_system_status()
