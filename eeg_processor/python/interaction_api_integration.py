"""
Integration of the interaction API with external API systems.

This module provides integration with external API frameworks following
the same pattern as the input_collector module. It delegates to api_integration.py
to avoid code duplication and ensures all methods appear in a single module.
"""

import logging
from typing import Dict, Any, Optional

from .services.interaction_service import InteractionService
from .interaction_api import EEGProcessorInteractionAPI


class EEGProcessorInteractionApiIntegration:
    """
    Integration class for exposing interaction API through external systems.

    This class provides methods that can be registered with external API
    frameworks to enable remote control of the EEG processor. It follows
    the same delegation pattern as input_collector to avoid code duplication.
    """

    _instance: Optional["EEGProcessorInteractionApiIntegration"] = None

    @classmethod
    def get_instance(cls) -> "EEGProcessorInteractionApiIntegration":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = EEGProcessorInteractionApiIntegration()
        return cls._instance

    def __init__(self) -> None:
        """Initialize the interaction API integration."""
        self.interaction_service = InteractionService.get_instance()
        self.module_id = "eeg_processor_interaction"
        self._target_module_id: Optional[str] = None

        logging.info("EEG Processor interaction API integration initialized")

    def register_api_methods(self, api_explorer: Any) -> None:
        """
        Register interaction API methods with the API explorer.

        Args:
            api_explorer: API explorer instance to register methods with
        """
        # Determine which module to use based on what's available
        self._determine_target_module(api_explorer)

        # If we need to create our own module, do it now
        if self._target_module_id == "eeg_processor_control":
            api_explorer.register_module(
                module_id="eeg_processor_control",
                name="EEG Processor Control",
                description="Remote control interface for EEG processor operations",
            )
            logging.info("Created separate control module for interaction methods")

        # Register method groups for interaction methods
        self._register_method_groups(api_explorer)

        # Register all interaction methods
        self._register_connection_methods(api_explorer)
        self._register_streaming_methods(api_explorer)
        self._register_processing_methods(api_explorer)
        self._register_recording_methods(api_explorer)
        self._register_visualization_methods(api_explorer)
        self._register_advanced_methods(api_explorer)
        self._register_status_methods(api_explorer)

        logging.info(
            f"Interaction API methods registered in module: {self._target_module_id}"
        )

    def _determine_target_module(self, api_explorer: Any) -> None:
        """Determine which module ID to use for registering methods."""
        try:
            # Check if main EEG processor module exists
            if (
                hasattr(api_explorer, "_modules")
                and "eeg_processor" in api_explorer._modules
            ):
                # Use main module (delegated from api_integration.py)
                self._target_module_id = "eeg_processor"
                logging.info("Using existing main EEG processor module")
            elif (
                hasattr(api_explorer, "modules")
                and "eeg_processor" in api_explorer.modules
            ):
                # Alternative attribute name
                self._target_module_id = "eeg_processor"
                logging.info("Using existing main EEG processor module (alt)")
            else:
                # Create separate control module (standalone control API)
                self._target_module_id = "eeg_processor_control"
                logging.info("Will create separate control module")
        except Exception as e:
            # Fallback to separate control module
            self._target_module_id = "eeg_processor_control"
            logging.warning(f"Error determining target module, using fallback: {e}")

    def _register_method_groups(self, api_explorer: Any) -> None:
        """Register method groups for interaction methods."""
        groups = [
            ("connection", "Board Connection"),
            ("streaming", "Data Streaming"),
            ("processing", "Signal Processing"),
            ("recording", "Data Recording"),
            ("visualization", "Data Visualization"),
            ("advanced", "Advanced Processing"),
            ("interaction_status", "Interaction Status"),
        ]

        for group_id, group_name in groups:
            api_explorer.add_method_group(self._target_module_id, group_id, group_name)

    def _register_connection_methods(self, api_explorer: Any) -> None:
        """Register connection-related methods."""
        # Get available boards
        api_explorer.register_method(
            self._target_module_id,
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
            self._target_module_id,
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
            self._target_module_id,
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
            self._target_module_id,
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

    def _register_streaming_methods(self, api_explorer: Any) -> None:
        """Register streaming-related methods."""
        # Start stream
        api_explorer.register_method(
            self._target_module_id,
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
            self._target_module_id,
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
            self._target_module_id,
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
            self._target_module_id,
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

        # Send board config
        api_explorer.register_method(
            self._target_module_id,
            "streaming",
            "send_board_config",
            {
                "name": "send_board_config(config_cmd)",
                "description": "Send configuration command to board",
                "type": "POST",
                "params": {
                    "config_cmd": {
                        "type": "text",
                        "description": "Configuration command",
                        "required": True,
                    }
                },
            },
            self._handle_send_board_config,
        )

    def _register_processing_methods(self, api_explorer: Any) -> None:
        """Register processing-related methods."""
        # Apply filters
        api_explorer.register_method(
            self._target_module_id,
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

        # Get EEG metrics
        api_explorer.register_method(
            self._target_module_id,
            "processing",
            "get_eeg_metrics",
            {
                "name": "get_eeg_metrics()",
                "description": "Calculate EEG metrics from current data",
                "type": "GET",
                "params": {},
            },
            self._handle_get_eeg_metrics,
        )

    def _register_recording_methods(self, api_explorer: Any) -> None:
        """Register recording-related methods."""
        # Start recording
        api_explorer.register_method(
            self._target_module_id,
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
            self._target_module_id,
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
            self._target_module_id,
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
            self._target_module_id,
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

        # Save current data
        api_explorer.register_method(
            self._target_module_id,
            "recording",
            "save_current_data",
            {
                "name": "save_current_data(filename, data_type)",
                "description": "Save current data to file",
                "type": "POST",
                "params": {
                    "filename": {
                        "type": "text",
                        "description": "Filename to save to",
                        "required": True,
                    },
                    "data_type": {
                        "type": "text",
                        "description": "Type of data to save (raw, processed)",
                        "required": False,
                    },
                },
            },
            self._handle_save_current_data,
        )

    def _register_visualization_methods(self, api_explorer: Any) -> None:
        """Register visualization-related methods."""
        # Start visualization
        api_explorer.register_method(
            self._target_module_id,
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
            self._target_module_id,
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

    def _register_advanced_methods(self, api_explorer: Any) -> None:
        """Register advanced processing methods."""
        # Perform ICA
        api_explorer.register_method(
            self._target_module_id,
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

        # Convert to MNE
        api_explorer.register_method(
            self._target_module_id,
            "advanced",
            "convert_to_mne",
            {
                "name": "convert_to_mne(duration)",
                "description": "Convert data to MNE format",
                "type": "POST",
                "params": {
                    "duration": {
                        "type": "number",
                        "description": "Duration in seconds for conversion",
                        "required": False,
                    }
                },
            },
            self._handle_convert_to_mne,
        )

        # Plot MNE visualization
        api_explorer.register_method(
            self._target_module_id,
            "advanced",
            "plot_mne_visualization",
            {
                "name": "plot_mne_visualization(plot_type)",
                "description": "Plot MNE visualization",
                "type": "POST",
                "params": {
                    "plot_type": {
                        "type": "text",
                        "description": "Type of MNE plot",
                        "required": True,
                    }
                },
            },
            self._handle_plot_mne_visualization,
        )

        # Compute wavelet
        api_explorer.register_method(
            self._target_module_id,
            "advanced",
            "compute_wavelet",
            {
                "name": "compute_wavelet(wavelet_type, level, channel)",
                "description": "Compute wavelet transform",
                "type": "POST",
                "params": {
                    "wavelet_type": {
                        "type": "number",
                        "description": "Type of wavelet",
                        "required": True,
                    },
                    "level": {
                        "type": "number",
                        "description": "Decomposition level",
                        "required": True,
                    },
                    "channel": {
                        "type": "number",
                        "description": "Channel to process",
                        "required": True,
                    },
                },
            },
            self._handle_compute_wavelet,
        )

    def _register_status_methods(self, api_explorer: Any) -> None:
        """Register status-related methods."""
        # Get connection status
        api_explorer.register_method(
            self._target_module_id,
            "interaction_status",
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
            self._target_module_id,
            "interaction_status",
            "get_system_status",
            {
                "name": "get_system_status()",
                "description": "Get comprehensive system status",
                "type": "GET",
                "params": {},
            },
            self._handle_get_system_status,
        )

    # Method handlers - these delegate to the EEGProcessorInteractionAPI
    async def _handle_get_available_boards(self) -> Dict[str, Any]:
        """Handle get_available_boards."""
        boards = EEGProcessorInteractionAPI.get_available_boards()
        return {"boards": boards}

    async def _handle_connect_to_board(
        self, board_id: int, params: Optional[Dict[str, Any]] = None, preset: int = 0
    ) -> Dict[str, Any]:
        """Handle connect_to_board."""
        return EEGProcessorInteractionAPI.connect_to_board(board_id, params, preset)

    async def _handle_disconnect_from_board(self) -> Dict[str, Any]:
        """Handle disconnect_from_board."""
        return EEGProcessorInteractionAPI.disconnect_from_board()

    async def _handle_get_board_requirements(self, board_id: int) -> Dict[str, Any]:
        """Handle get_board_requirements."""
        requirements = EEGProcessorInteractionAPI.get_board_requirements(board_id)
        return {"requirements": requirements}

    async def _handle_start_stream(self, buffer_size: int = 450000) -> Dict[str, Any]:
        """Handle start_stream."""
        return EEGProcessorInteractionAPI.start_stream(buffer_size)

    async def _handle_stop_stream(self) -> Dict[str, Any]:
        """Handle stop_stream."""
        return EEGProcessorInteractionAPI.stop_stream()

    async def _handle_add_streamer(self, streamer_params: str) -> Dict[str, Any]:
        """Handle add_streamer."""
        return EEGProcessorInteractionAPI.add_streamer(streamer_params)

    async def _handle_remove_streamer(self, streamer_params: str) -> Dict[str, Any]:
        """Handle remove_streamer."""
        return EEGProcessorInteractionAPI.remove_streamer(streamer_params)

    async def _handle_send_board_config(self, config_cmd: str) -> Dict[str, Any]:
        """Handle send_board_config."""
        return EEGProcessorInteractionAPI.send_board_config(config_cmd)

    async def _handle_apply_filters(
        self, filter_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle apply_filters."""
        return EEGProcessorInteractionAPI.apply_filters(filter_config)

    async def _handle_get_eeg_metrics(self) -> Dict[str, Any]:
        """Handle get_eeg_metrics."""
        return EEGProcessorInteractionAPI.get_eeg_metrics()

    async def _handle_start_recording(
        self, filename: str, data_type: str = "raw"
    ) -> Dict[str, Any]:
        """Handle start_recording."""
        return EEGProcessorInteractionAPI.start_recording(filename, data_type)

    async def _handle_stop_recording(self) -> Dict[str, Any]:
        """Handle stop_recording."""
        return EEGProcessorInteractionAPI.stop_recording()

    async def _handle_insert_marker(self, marker_value: float) -> Dict[str, Any]:
        """Handle insert_marker."""
        return EEGProcessorInteractionAPI.insert_marker(marker_value)

    async def _handle_get_recording_status(self) -> Dict[str, Any]:
        """Handle get_recording_status."""
        return EEGProcessorInteractionAPI.get_recording_status()

    async def _handle_save_current_data(
        self, filename: str, data_type: str = "raw"
    ) -> Dict[str, Any]:
        """Handle save_current_data."""
        return EEGProcessorInteractionAPI.save_current_data(filename, data_type)

    async def _handle_start_visualization(
        self, viz_type: str = "eeg"
    ) -> Dict[str, Any]:
        """Handle start_visualization."""
        return EEGProcessorInteractionAPI.start_visualization(viz_type)

    async def _handle_stop_visualization(self, viz_type: str = "eeg") -> Dict[str, Any]:
        """Handle stop_visualization."""
        return EEGProcessorInteractionAPI.stop_visualization(viz_type)

    async def _handle_perform_ica(self, num_components: int) -> Dict[str, Any]:
        """Handle perform_ica."""
        return EEGProcessorInteractionAPI.perform_ica(num_components)

    async def _handle_convert_to_mne(self, duration: int = 5) -> Dict[str, Any]:
        """Handle convert_to_mne."""
        return EEGProcessorInteractionAPI.convert_to_mne(duration)

    async def _handle_plot_mne_visualization(self, plot_type: str) -> Dict[str, Any]:
        """Handle plot_mne_visualization."""
        return EEGProcessorInteractionAPI.plot_mne_visualization(plot_type)

    async def _handle_compute_wavelet(
        self, wavelet_type: int, level: int, channel: int
    ) -> Dict[str, Any]:
        """Handle compute_wavelet."""
        return EEGProcessorInteractionAPI.compute_wavelet(wavelet_type, level, channel)

    async def _handle_get_connection_status(self) -> Dict[str, Any]:
        """Handle get_connection_status."""
        return EEGProcessorInteractionAPI.get_connection_status()

    async def _handle_get_system_status(self) -> Dict[str, Any]:
        """Handle get_system_status."""
        return EEGProcessorInteractionAPI.get_system_status()
