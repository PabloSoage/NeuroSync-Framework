"""
Integration of the interaction API with external API systems.

This module provides integration with external API frameworks following
the same pattern as the input_collector module. It delegates to api_integration.py
to avoid code duplication and ensures all methods appear in a single module.
"""

import logging
from typing import Dict, Any, Optional, List

from .interaction_api import EEGProcessorInteractionAPI
from .services.interaction_service import InteractionService


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

        # Ensure the interaction service is initialized
        try:
            if not self.interaction_service._initialized:
                self.interaction_service.initialize()
                logging.info("Interaction service initialized via API integration")
        except Exception as e:
            logging.warning(f"Could not initialize interaction service: {e}")

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

        # Get board options and preset options
        board_options = self._get_board_options()
        preset_options = self._get_preset_options()

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
                        "type": "select",
                        "description": "ID of the board to connect to",
                        "required": True,
                        "options": board_options,
                    },
                    "params": {
                        "type": "object",  # Changed to "object" for FastAPI compatibility while keeping template functionality
                        "description": "Connection parameters (will be populated based on selected board)",
                        "required": False,
                        "template_source": "board_id",
                        "placeholder": "Parameters will appear based on board selection",
                        "ui_type": "json_template",  # Add UI hint for template functionality
                    },
                    "preset": {
                        "type": "select",
                        "description": "Data preset to use",
                        "required": False,
                        "options": preset_options,
                        "default": 0,
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

        # Get board template (helper method for UI)
        api_explorer.register_method(
            self._target_module_id,
            "connection",
            "get_board_template",
            {
                "name": "get_board_template(board_id)",
                "description": "Get parameter template for a specific board (UI helper)",
                "type": "GET",
                "params": {
                    "board_id": {
                        "type": "number",
                        "description": "ID of the board",
                        "required": True,
                    }
                },
            },
            self._handle_get_board_template,
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
                        "default": 450000,
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

        # Get streamer type options for dropdown
        streamer_type_options = self._get_streamer_type_options()

        # Add streamer
        api_explorer.register_method(
            self._target_module_id,
            "streaming",
            "add_streamer",
            {
                "name": "add_streamer(streamer_type, streamer_params)",
                "description": "Add a data streamer",
                "type": "POST",
                "params": {
                    "streamer_type": {
                        "type": "select",
                        "description": "Type of streamer to add",
                        "required": True,
                        "options": streamer_type_options,
                        "default": "file",
                    },
                    "streamer_params": {
                        "type": "object",
                        "description": "Streamer parameters (will be populated based on selected type)",
                        "required": True,
                        "template_source": "streamer_type",
                        "placeholder": "Parameters will appear based on streamer type selection",
                        "ui_type": "json_template",
                    },
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
                "name": "remove_streamer(streamer_type, streamer_params)",
                "description": "Remove a data streamer",
                "type": "POST",
                "params": {
                    "streamer_type": {
                        "type": "select",
                        "description": "Type of streamer to remove",
                        "required": True,
                        "options": streamer_type_options,
                        "default": "file",
                    },
                    "streamer_params": {
                        "type": "object",  # Cambiar de "text" a "object"
                        "description": "Streamer parameters (same as used when adding)",
                        "required": True,
                        "template_source": "streamer_type",  # Añadir template_source
                        "placeholder": "Parameters will appear based on streamer type selection",
                        "ui_type": "json_template",  # Añadir UI hint
                        "help_text": "Use the exact same parameter object that was used to add this streamer"
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
                        "description": "Configuration command string",
                        "required": True,
                        "placeholder": "Enter board configuration command",
                    }
                },
            },
            self._handle_send_board_config,
        )

        # Get streamer template (helper method for UI)
        api_explorer.register_method(
            self._target_module_id,
            "streaming",
            "get_streamer_template",
            {
                "name": "get_streamer_template(streamer_type)",
                "description": "Get parameter template for a specific streamer type (UI helper)",
                "type": "GET",
                "params": {
                    "streamer_type": {
                        "type": "select",
                        "description": "Type of streamer",
                        "required": True,
                        "options": streamer_type_options,
                        "default": "file",
                    }
                },
            },
            self._handle_get_streamer_template,
        )

    async def _handle_add_streamer(
            self, streamer_type: str, streamer_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle add_streamer."""
        try:
            logging.info(f"Adding streamer: type={streamer_type}, params={streamer_params}")

            # Convert template params to streamer_params string
            streamer_params_str = self._convert_streamer_template_to_params(
                streamer_type, streamer_params
            )

            logging.info(f"Converted to streamer string: {streamer_params_str}")

            result = EEGProcessorInteractionAPI.add_streamer(streamer_params_str)

            # Enhance the result with the original parameters for reference
            if "success" in result:
                result["original_params"] = {
                    "streamer_type": streamer_type,
                    "template_params": streamer_params,
                    "converted_params": streamer_params_str
                }

            return result
        except Exception as e:
            logging.error(f"Error in add_streamer handler: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Add streamer failed: {e}",
                "error": str(e),
            }

    async def _handle_remove_streamer(
            self, streamer_type: str, streamer_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle remove_streamer."""
        try:
            logging.info(f"Removing streamer: type={streamer_type}, params={streamer_params}")

            # Convert template params to streamer_params string if it's a dict
            if isinstance(streamer_params, dict):
                streamer_params_str = self._convert_streamer_template_to_params(
                    streamer_type, streamer_params
                )
            else:
                streamer_params_str = streamer_params

            logging.info(f"Converted streamer params to string: {streamer_params_str}")

            result = EEGProcessorInteractionAPI.remove_streamer(streamer_params_str)

            # Enhance the result with the original parameters for reference
            if "success" in result:
                result["original_params"] = {
                    "streamer_type": streamer_type,
                    "streamer_params": streamer_params_str
                }

            return result
        except Exception as e:
            logging.error(f"Error in remove_streamer handler: {e}")
            return {
                "success": False,
                "message": f"Remove streamer failed: {e}",
                "error": str(e),
            }

    async def _handle_send_board_config(self, config_cmd: str) -> Dict[str, Any]:
        """Handle send_board_config."""
        return EEGProcessorInteractionAPI.send_board_config(config_cmd)

    async def _handle_get_streamer_template(self, streamer_type: str) -> Dict[str, Any]:
        """Handle get_streamer_template."""
        try:
            logging.info(f"Getting streamer template for type: {streamer_type}")
            template = self._get_streamer_template(streamer_type)
            logging.info(f"Generated streamer template: {template}")

            result = {"template": template, "streamer_type": streamer_type}
            logging.info(f"Returning streamer template result: {result}")
            return result
        except Exception as e:
            logging.error(f"Error in _handle_get_streamer_template: {e}")
            return {"template": {}, "streamer_type": streamer_type, "error": str(e)}

    def _get_streamer_type_options(self) -> List[Dict[str, Any]]:
        """Get available streamer type options for dropdown."""
        return [
            {"value": "file", "label": "File Streamer (Save to file)"},
            {"value": "network", "label": "Network Streamer (UDP/TCP)"},
            {"value": "custom", "label": "Custom Streamer (Other protocols)"},
        ]

    def _get_streamer_template(self, streamer_type: str) -> Dict[str, Any]:
        """Get parameter template for a specific streamer type."""
        try:
            logging.info(f"Building template for streamer_type: {streamer_type}")

            template: Dict[str, Any] = {}

            if streamer_type == "file":
                template = {
                    "file_path": {
                        "value": "recordings/eeg_stream.csv",
                        "description": "Path where to save the streaming data file",
                        "type": "text",
                        "required": True
                    },
                    "data_type": {
                        "value": "raw",
                        "description": "Type of data to record: 'raw', 'processed', or 'both'",
                        "type": "select",
                        "options": [
                            {"value": "raw", "label": "Raw Data"},
                            {"value": "processed", "label": "Processed Data"},
                            {"value": "both", "label": "Both Raw + Processed"}
                        ],
                        "required": True
                    },
                    "_COMMENTS": [
                        "FILE STREAMER - Saves streaming data to a file",
                        "",
                        "Required fields:",
                        "  - file_path: Path where to save the file (e.g., 'recordings/stream.csv')",
                        "  - data_type: Type of data to save ('raw', 'processed', or 'both')",
                        "",
                        "Notes:",
                        "  - File will be created with EEG headers and metadata",
                        "  - Directory will be created automatically if it doesn't exist",
                        "  - Board must be connected and streaming before adding file streamer",
                        "",
                        "Remove this _COMMENTS field before executing"
                    ]
                }

            elif streamer_type == "network":
                template = {
                    "protocol": {
                        "value": "streaming_board",
                        "description": "Protocol to use: 'streaming_board' for BrainFlow network streaming",
                        "type": "text",
                        "required": True
                    },
                    "ip_address": {
                        "value": "225.1.1.1",
                        "description": "IP address for network streaming (default multicast: 225.1.1.1)",
                        "type": "text",
                        "required": True
                    },
                    "ip_port": {
                        "value": 6677,
                        "description": "Port for network streaming (default: 6677)",
                        "type": "number",
                        "required": True
                    },
                    "_COMMENTS": [
                        "NETWORK STREAMER - Streams data over network using BrainFlow protocol",
                        "",
                        "Required fields:",
                        "  - protocol: Usually 'streaming_board' for BrainFlow compatibility",
                        "  - ip_address: Target IP address (225.1.1.1 for multicast)",
                        "  - ip_port: Target port (default: 6677)",
                        "",
                        "Format: 'streaming_board://ip_address:port'",
                        "Example: 'streaming_board://225.1.1.1:6677'",
                        "",
                        "Notes:",
                        "  - Only streams raw data",
                        "  - Requires preset 0 (Default) for optimal compatibility",
                        "  - Board must be connected before adding network streamer",
                        "",
                        "Remove this _COMMENTS field before executing"
                    ]
                }

            elif streamer_type == "custom":
                template = {
                    "protocol": {
                        "value": "udp",
                        "description": "Custom protocol: 'udp', 'tcp', or other custom protocol",
                        "type": "select",
                        "options": [
                            {"value": "udp", "label": "UDP"},
                            {"value": "tcp", "label": "TCP"},
                            {"value": "other", "label": "Other (specify in address)"}
                        ],
                        "required": True
                    },
                    "address": {
                        "value": "127.0.0.1",
                        "description": "Target address for custom streaming",
                        "type": "text",
                        "required": True
                    },
                    "port": {
                        "value": 8080,
                        "description": "Target port for custom streaming",
                        "type": "number",
                        "required": True
                    },
                    "additional_params": {
                        "value": "",
                        "description": "Additional parameters if needed (optional)",
                        "type": "text",
                        "required": False
                    },
                    "_COMMENTS": [
                        "CUSTOM STREAMER - Streams data using custom protocols",
                        "",
                        "Required fields:",
                        "  - protocol: Protocol type (udp, tcp, etc.)",
                        "  - address: Target address",
                        "  - port: Target port",
                        "",
                        "Optional fields:",
                        "  - additional_params: Any additional parameters needed",
                        "",
                        "Format examples:",
                        "  - UDP: 'udp://127.0.0.1:8080'",
                        "  - TCP: 'tcp://192.168.1.100:9090'",
                        "  - Custom: 'custom_protocol://params'",
                        "",
                        "Notes:",
                        "  - Only streams raw data",
                        "  - Board must be connected before adding custom streamer",
                        "  - Specific format depends on your custom implementation",
                        "",
                        "Remove this _COMMENTS field before executing"
                    ]
                }
            else:
                # Unknown streamer type
                template = {
                    "streamer_params": {
                        "value": "",
                        "description": f"Parameters for {streamer_type} streamer",
                        "type": "text",
                        "required": True
                    },
                    "_COMMENTS": [
                        f"UNKNOWN STREAMER TYPE: {streamer_type}",
                        "",
                        "Please specify the complete streamer parameters string.",
                        "",
                        "Remove this _COMMENTS field before executing"
                    ]
                }

            logging.info(f"Built template with {len(template)} fields: {list(template.keys())}")
            return template

        except Exception as e:
            logging.error(f"Error getting streamer template: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return {}

    def _convert_streamer_template_to_params(
            self, streamer_type: str, template_params: Dict[str, Any]
    ) -> str:
        """Convert template parameters to streamer_params string."""
        try:
            logging.info(f"Converting template: type={streamer_type}, params={template_params}")

            # Remove comments if present
            params = {k: v for k, v in template_params.items() if k != "_COMMENTS"}

            # Extract values if template uses {value, description} format
            clean_params = {}
            for key, value in params.items():
                if isinstance(value, dict) and "value" in value:
                    clean_params[key] = value["value"]
                else:
                    clean_params[key] = value

            logging.info(f"Cleaned params: {clean_params}")

            if streamer_type == "file":
                file_path = clean_params.get("file_path", "recordings/stream.csv")
                data_type = clean_params.get("data_type", "raw")

                # For file streamers, use format: "file_path|data_type"
                result = f"{file_path}|{data_type}"
                logging.info(f"File streamer result: {result}")
                return result

            elif streamer_type == "network":
                protocol = clean_params.get("protocol", "streaming_board")
                ip_address = clean_params.get("ip_address", "225.1.1.1")
                ip_port = clean_params.get("ip_port", 6677)

                # Format: protocol://ip_address:port
                result = f"{protocol}://{ip_address}:{ip_port}"
                logging.info(f"Network streamer result: {result}")
                return result

            elif streamer_type == "custom":
                protocol = clean_params.get("protocol", "udp")
                address = clean_params.get("address", "127.0.0.1")
                port = clean_params.get("port", 8080)
                additional = clean_params.get("additional_params", "")

                # Format: protocol://address:port[additional]
                base_params = f"{protocol}://{address}:{port}"
                if additional:
                    base_params += f"/{additional}"
                result = base_params
                logging.info(f"Custom streamer result: {result}")
                return result

            else:
                # For unknown types, try to get a direct params string
                result = clean_params.get("streamer_params", str(template_params))
                logging.info(f"Unknown type result: {result}")
                return result

        except Exception as e:
            logging.error(f"Error converting streamer template to params: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            # Fallback: return the template as is (might work for some cases)
            return str(template_params)

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
        try:
            # Convert string values to integers if needed
            if isinstance(board_id, str):
                board_id = int(board_id)
            if isinstance(preset, str):
                preset = int(preset)

            # Ensure params is a dictionary
            if params is None:
                params = {}

            logging.info(
                f"Connecting to board {board_id} with preset {preset} and params {params}"
            )

            return EEGProcessorInteractionAPI.connect_to_board(board_id, params, preset)
        except ValueError as e:
            logging.error(f"Error converting parameters: {e}")
            return {
                "success": False,
                "message": f"Invalid parameter values: {e}",
                "error": "INVALID_PARAMETERS",
            }
        except Exception as e:
            logging.error(f"Error in connect_to_board handler: {e}")
            return {
                "success": False,
                "message": f"Connection failed: {e}",
                "error": str(e),
            }

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

    async def _handle_add_streamer(
            self, streamer_type: str, streamer_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle add_streamer."""
        try:
            logging.info(f"Adding streamer: type={streamer_type}, params={streamer_params}")

            # Convert template params to streamer_params string
            streamer_params_str = self._convert_streamer_template_to_params(
                streamer_type, streamer_params
            )

            logging.info(f"Converted to streamer string: {streamer_params_str}")

            result = EEGProcessorInteractionAPI.add_streamer(streamer_params_str)

            # Enhance the result with the original parameters for reference
            if "success" in result:
                result["original_params"] = {
                    "streamer_type": streamer_type,
                    "template_params": streamer_params,
                    "converted_params": streamer_params_str
                }

            return result
        except Exception as e:
            logging.error(f"Error in add_streamer handler: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Add streamer failed: {e}",
                "error": str(e),
            }

    async def _handle_remove_streamer(
            self, streamer_type: str, streamer_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle remove_streamer."""
        try:
            logging.info(f"Removing streamer: type={streamer_type}, params={streamer_params}")

            # Convert template params to streamer_params string if it's a dict
            if isinstance(streamer_params, dict):
                streamer_params_str = self._convert_streamer_template_to_params(
                    streamer_type, streamer_params
                )
            else:
                streamer_params_str = streamer_params

            logging.info(f"Converted streamer params to string: {streamer_params_str}")

            result = EEGProcessorInteractionAPI.remove_streamer(streamer_params_str)

            # Enhance the result with the original parameters for reference
            if "success" in result:
                result["original_params"] = {
                    "streamer_type": streamer_type,
                    "streamer_params": streamer_params_str
                }

            return result
        except Exception as e:
            logging.error(f"Error in remove_streamer handler: {e}")
            return {
                "success": False,
                "message": f"Remove streamer failed: {e}",
                "error": str(e),
            }

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

    async def _handle_get_board_template(self, board_id: int) -> Dict[str, Any]:
        """Handle get_board_template."""
        try:
            logging.info(f"Getting board template for board_id: {board_id}")
            template = self._get_board_template(board_id)
            logging.info(f"Generated template: {template}")

            result = {"template": template, "board_id": board_id}
            logging.info(f"Returning template result: {result}")
            return result
        except Exception as e:
            logging.error(f"Error in _handle_get_board_template: {e}")
            return {"template": {}, "board_id": board_id, "error": str(e)}

    def _get_board_options(self) -> List[Dict[str, Any]]:
        """Get available board options for dropdown."""
        try:
            from .collectors.board_configuration import BoardConfiguration

            boards = BoardConfiguration.get_all_boards()

            return [
                {"value": board_id, "label": f"{board_name} (ID: {board_id})"}
                for board_name, board_id in boards
            ]
        except Exception as e:
            logging.error(f"Error getting board options: {e}")
            return [{"value": 0, "label": "Synthetic Board (ID: 0)"}]

    def _get_preset_options(self) -> List[Dict[str, Any]]:
        """Get available preset options for dropdown."""
        try:
            from .collectors.board_configuration import BoardConfiguration

            preset_info = BoardConfiguration.get_preset_info()

            return [
                {"value": preset_val, "label": f"{preset_desc} ({preset_val})"}
                for preset_val, preset_desc in preset_info.items()
            ]
        except Exception as e:
            logging.error(f"Error getting preset options: {e}")
            return [{"value": 0, "label": "Default Preset (0)"}]

    def _get_board_template(self, board_id: int) -> Dict[str, Any]:
        """Get parameter template for a specific board."""
        try:
            logging.info(f"Building template for board_id: {board_id}")
            from .collectors.board_configuration import BoardConfiguration

            requirements = BoardConfiguration.get_board_requirements(board_id)
            logging.info(f"Board requirements: {requirements}")

            template: Dict[str, Any] = {}
            required_comments = []
            optional_comments = []

            # Build complete template with all possible fields
            all_fields: Dict[str, Dict[str, Any]] = {
                "serial_port": {
                    "value": "",
                    "description": "Serial port for board connection (e.g., COM3, /dev/ttyUSB0)",
                },
                "ip_address": {
                    "value": "225.1.1.1",
                    "description": "IP address for network boards (default: 225.1.1.1)",
                },
                "ip_port": {
                    "value": 6677,
                    "description": "IP port for network boards (default: 6677)",
                },
                "mac_address": {
                    "value": "",
                    "description": "MAC address for Bluetooth boards (auto-discovery if empty)",
                },
                "serial_number": {
                    "value": "",
                    "description": "Serial number of the device (useful for multiple devices)",
                },
                "file": {
                    "value": "",
                    "description": "File path for playback boards (full path to CSV file)",
                },
                "master_board": {
                    "value": 0,
                    "description": "Master board ID for daisy chain or streaming boards",
                },
                "other_info": {
                    "value": "",
                    "description": "Additional information (e.g., ExternalSwitchInputMioUSB for Callibri)",
                },
                "timeout": {
                    "value": 15000,
                    "description": "Connection timeout in milliseconds (default: 15000)",
                },
            }

            # Determine field status for this specific board
            for field_name, field_info in all_fields.items():
                is_required = requirements.get(field_name, False)
                is_optional = BoardConfiguration.is_field_optional_for_board(
                    field_name, board_id
                )

                if is_required:
                    # Required field - add to template and comments
                    template[field_name] = field_info["value"]
                    required_comments.append(
                        f"{field_name}: {field_info['description']}"
                    )
                elif is_optional:
                    # Optional field - add to template and comments
                    template[field_name] = field_info["value"]
                    optional_comments.append(
                        f"{field_name}: {field_info['description']}"
                    )
                # Skip fields that are not applicable (neither required nor optional)

            # Add comments if we have any fields
            if required_comments or optional_comments:
                comments = []

                if required_comments:
                    comments.append("REQUIRED fields for this board:")
                    comments.extend([f"  - {comment}" for comment in required_comments])

                if optional_comments:
                    if required_comments:
                        comments.append("")  # Empty line separator
                    comments.append("OPTIONAL fields for this board:")
                    comments.extend([f"  - {comment}" for comment in optional_comments])

                comments.append("")
                comments.append("Remove this _COMMENTS field before executing")
                template["_COMMENTS"] = comments

            logging.info(
                f"Built template with {len(template)} fields: {list(template.keys())}"
            )
            return template
        except Exception as e:
            logging.error(f"Error getting board template: {e}")
            import traceback

            logging.error(f"Traceback: {traceback.format_exc()}")
            return {}
            logging.info(
                f"Built template with {len(template)} fields: {list(template.keys())}"
            )
            return template
        except Exception as e:
            logging.error(f"Error getting board template: {e}")
            import traceback

            logging.error(f"Traceback: {traceback.format_exc()}")
            return {}

    def _is_field_optional_for_board(
        self, param: str, board_id: int, board_name: str
    ) -> bool:
        """
        Determine if a parameter field is optional (vs not applicable) for a specific board.

        Args:
            param: Parameter name
            board_id: Board ID
            board_name: Board name (lowercase)

        Returns:
            True if field is optional, False if not applicable
        """
        from brainflow.board_shim import BoardIds

        # Special boards - check which fields are potentially useful
        if board_id == BoardIds.SYNTHETIC_BOARD.value:
            # Synthetic board: no fields are useful
            return False

        if board_id == BoardIds.PLAYBACK_FILE_BOARD.value:
            # Playback board: only file and master_board are relevant (both required per requirements)
            return False  # No optional fields for playback board

        if board_id == BoardIds.STREAMING_BOARD.value:
            # Streaming board: ip_address, ip_port, master_board are all required per requirements
            return False  # No optional fields for streaming board

        # For real hardware boards, determine based on board characteristics
        try:
            # Check board name patterns to determine optional fields
            if "cyton" in board_name or "ganglion" in board_name:
                if "wifi" in board_name:
                    # WiFi boards: ip_port is required, ip_address is optional (SSDP discovery), timeout optional
                    return param in ["ip_address", "timeout"]
                elif "native" in board_name:
                    # Native Bluetooth: mac_address and serial_number are optional (auto-discovery), timeout optional
                    return param in ["mac_address", "serial_number", "timeout"]
                elif "bled" in board_name:
                    # BLED dongle boards: serial_port required, mac_address optional but helpful, timeout optional
                    return param in ["mac_address", "timeout"]
                else:
                    # Serial boards: serial_port required, timeout is optional
                    return param in ["timeout"]

            elif "muse" in board_name:
                if "bled" in board_name:
                    # Muse BLED: serial_port required, serial_number optional, timeout optional
                    return param in ["serial_number", "timeout"]
                else:
                    # Muse native: mac_address and serial_number optional, timeout optional
                    return param in ["mac_address", "serial_number", "timeout"]

            elif "unicorn" in board_name:
                # Unicorn: serial_number optional (for multiple devices), timeout optional
                return param in ["serial_number", "timeout"]

            elif "brainbit" in board_name:
                if "bled" in board_name:
                    # BrainBit BLED: serial_port required, mac_address optional, timeout optional
                    return param in ["mac_address", "timeout"]
                else:
                    # BrainBit native: serial_number optional, timeout optional
                    return param in ["serial_number", "timeout"]

            elif "notion" in board_name or "crown" in board_name:
                # Neurosity boards: serial_number optional, timeout optional
                return param in ["serial_number", "timeout"]

            elif "freeeeg" in board_name:
                # FreeEEG: serial_port required, timeout optional
                return param in ["timeout"]

            elif "enophone" in board_name or "explore" in board_name:
                # Bluetooth boards: mac_address optional on some platforms, timeout optional
                return param in ["mac_address", "timeout"]

            elif "emotibit" in board_name:
                # EmotiBit: ip_address and serial_number optional, timeout optional
                return param in ["ip_address", "serial_number", "timeout"]

            elif "ant" in board_name or "eego" in board_name:
                # ANT Neuro: timeout might be optional
                return param in ["timeout"]

            elif "callibri" in board_name:
                # Callibri: other_info optional (for ExternalSwitchInputMioUSB), timeout optional
                return param in ["other_info", "timeout"]

            else:
                # Default for unknown boards: timeout is usually optional
                return param in ["timeout"]

        except Exception as e:
            logging.warning(f"Error determining optional fields for {board_name}: {e}")
            # Conservative fallback: consider timeout as optional for most boards
            return param in ["timeout"]
            logging.warning(f"Error determining optional fields for {board_name}: {e}")
            # Conservative fallback: consider timeout as optional for most boards
            return param in ["timeout"]
