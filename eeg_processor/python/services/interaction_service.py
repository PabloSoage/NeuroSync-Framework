"""
Service for handling interaction API requests.

This service acts as a bridge between the external API and internal services,
publishing events to update the UI when API actions are performed. It follows
the same singleton pattern as the input_collector module.
"""

import logging
import threading
from typing import Dict, List, Any, Optional, TYPE_CHECKING

from ..core.event_system import EventDispatcher, EventType, dispatch

if TYPE_CHECKING:
    from .collector_service import CollectorService
    from .processor_service import ProcessorService
    from .recording_service import RecordingService
    from .visualization_service import VisualizationService
    from .data_access_service import DataAccessService


class InteractionService:
    """
    Service that handles interaction API requests and coordinates with other services.

    This service acts as a bridge between the external API and internal services,
    publishing events to update the UI when API actions are performed.
    """

    _instance: Optional["InteractionService"] = None
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "InteractionService":
        """Get the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = InteractionService()
            return cls._instance

    def __init__(self) -> None:
        """Initialize the interaction service."""
        if InteractionService._instance is not None:
            raise RuntimeError("InteractionService is a singleton. Use get_instance()")

        self.event_dispatcher = EventDispatcher.get_instance()
        self._initialized = False

        # Component registry like input_collector
        self._components: Dict[str, Any] = {}
        self._last_status = {"success": False, "message": "Service not initialized"}

        # Shared service instances - initialize once and reuse
        self._collector_service: Optional["CollectorService"] = None
        self._processor_service: Optional["ProcessorService"] = None
        self._recording_service: Optional["RecordingService"] = None
        self._visualization_service: Optional["VisualizationService"] = None
        self._data_access_service: Optional["DataAccessService"] = None

        logging.info("Interaction service initialized")

        # Auto-initialize the service
        self._auto_initialize()

    def _auto_initialize(self) -> None:
        """Auto-initialize the service with basic setup."""
        try:
            # Initialize core services immediately
            self._get_collector_service()
            self._get_data_access_service()

            self._initialized = True
            self._set_status(True, "Service auto-initialized successfully")
            logging.info("Interaction service auto-initialized")
        except Exception as e:
            self._set_status(False, f"Auto-initialization failed: {e}")
            logging.warning(f"Auto-initialization failed, will retry on first use: {e}")

    def register_component(self, component_name: str, component: Any) -> None:
        """
        Register an application component with the service.

        Args:
            component_name: Name of the component
            component: The component instance
        """
        self._components[component_name] = component
        logging.info(
            f"Component '{component_name}' registered with interaction service"
        )

    def get_component(self, component_name: str) -> Any:
        """
        Get a registered component by name.

        Args:
            component_name: Name of the component to retrieve

        Returns:
            The component instance or None if not found
        """
        return self._components.get(component_name)

    def _set_status(self, success: bool, message: str) -> None:
        """
        Set the status of the last operation.

        Args:
            success: Whether the operation was successful
            message: Status message
        """
        self._last_status = {"success": success, "message": message}
        log_level = logging.INFO if success else logging.ERROR
        logging.log(log_level, f"Interaction status: {message}")

    def get_last_status(self) -> Dict[str, Any]:
        """
        Get the status of the last operation.

        Returns:
            Dict with status information
        """
        return self._last_status

    def _get_collector_service(self) -> "CollectorService":
        """Get or create collector service instance."""
        if self._collector_service is None:
            from .collector_service import CollectorService

            self._collector_service = CollectorService.get_instance()
            self.register_component("collector_service", self._collector_service)
        return self._collector_service

    def _get_processor_service(self) -> "ProcessorService":
        """Get or create processor service instance."""
        if self._processor_service is None:
            from .processor_service import ProcessorService

            self._processor_service = ProcessorService()
            self.register_component("processor_service", self._processor_service)
        return self._processor_service

    def _get_recording_service(self) -> "RecordingService":
        """Get or create recording service instance."""
        if self._recording_service is None:
            from .recording_service import RecordingService

            self._recording_service = RecordingService()
            self.register_component("recording_service", self._recording_service)
        return self._recording_service

    def _get_visualization_service(self) -> "VisualizationService":
        """Get or create visualization service instance."""
        if self._visualization_service is None:
            from .visualization_service import VisualizationService

            self._visualization_service = VisualizationService()
            self.register_component(
                "visualization_service", self._visualization_service
            )
        return self._visualization_service

    def _get_data_access_service(self) -> "DataAccessService":
        """Get or create data access service instance."""
        if self._data_access_service is None:
            from .data_access_service import DataAccessService

            self._data_access_service = DataAccessService.get_instance()
            self.register_component("data_access_service", self._data_access_service)
        return self._data_access_service

    def _check_initialized(self) -> bool:
        """Check if the service is properly initialized."""
        if not self._initialized:
            # Try to initialize if not already done
            logging.info("Service not initialized, attempting auto-initialization")
            try:
                self._auto_initialize()
                if self._initialized:
                    return True
            except Exception as e:
                logging.error(f"Failed to auto-initialize: {e}")

            self._set_status(
                False, "Service not initialized and auto-initialization failed"
            )
            return False
        return True

    def initialize(self, components: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize the service with required dependencies.

        Args:
            components: Optional dictionary of components to register

        Returns:
            bool: True if successful
        """
        try:
            # Register components if provided
            if components:
                for name, component in components.items():
                    self.register_component(name, component)

            # Initialize core services
            self._get_collector_service()
            self._get_data_access_service()

            self._initialized = True
            self._set_status(True, "Service initialized successfully")
            logging.info("Interaction service initialization completed")
            return True
        except Exception as e:
            self._set_status(False, f"Error initializing interaction service: {e}")
            logging.error(f"Error initializing interaction service: {e}")
            return False

    def get_available_boards(self) -> List[Dict[str, Any]]:
        """
        Get list of available EEG boards.

        Returns:
            List of dictionaries with board information
        """
        try:
            from ..collectors.board_configuration import BoardConfiguration

            boards = BoardConfiguration.get_all_boards()
            board_list = []

            for board_name, board_id in boards:
                board_info = {
                    "id": board_id,
                    "name": board_name,
                    "requirements": BoardConfiguration.get_board_requirements(board_id),
                }
                board_list.append(board_info)

            # Dispatch event for UI updates
            dispatch(
                EventType.BOARD_INFO_UPDATED,
                {"boards": board_list},
                source="interaction_service",
            )

            return board_list

        except Exception as e:
            logging.error(f"Error getting available boards: {e}")
            return []

    def connect_to_board(
        self, board_id: int, params: Dict[str, Any], preset: int = 0
    ) -> Dict[str, Any]:
        """
        Connect to an EEG board.

        Args:
            board_id: ID of the board to connect to
            params: Connection parameters
            preset: Data preset to use

        Returns:
            Dictionary with connection result information
        """
        try:
            collector_service = self._get_collector_service()
            success = collector_service.connect_to_board(board_id, params, preset)

            result = {
                "success": success,
                "board_id": board_id,
                "preset": preset,
                "message": (
                    "Board connected successfully"
                    if success
                    else "Failed to connect to board"
                ),
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.BOARD_CONNECT if success else EventType.ERROR_OCCURRED,
                {
                    "connected": success,
                    "board_id": board_id,
                    "preset": preset,
                    "params": params,
                },
                source="interaction_service",
            )

            if success:
                # Update connection status
                dispatch(
                    EventType.CONNECTION_STATUS_CHANGED,
                    {"connected": True, "board_id": board_id},
                    source="interaction_service",
                )

            return result

        except Exception as e:
            logging.error(f"Error connecting to board: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Connection failed: {str(e)}",
            }

    def disconnect_from_board(self) -> Dict[str, Any]:
        """
        Disconnect from the current board.

        Returns:
            Dictionary with disconnection result information
        """
        try:
            collector_service = self._get_collector_service()
            success = collector_service.disconnect_from_board()

            result = {
                "success": success,
                "message": (
                    "Board disconnected successfully"
                    if success
                    else "Failed to disconnect from board"
                ),
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.BOARD_DISCONNECT if success else EventType.ERROR_OCCURRED,
                {"connected": False},
                source="interaction_service",
            )

            if success:
                # Update connection status
                dispatch(
                    EventType.CONNECTION_STATUS_CHANGED,
                    {"connected": False},
                    source="interaction_service",
                )

            return result

        except Exception as e:
            logging.error(f"Error disconnecting from board: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Disconnection failed: {str(e)}",
            }

    def start_stream(self, buffer_size: int = 450000) -> Dict[str, Any]:
        """
        Start data streaming.

        Args:
            buffer_size: Size of the buffer for data

        Returns:
            Dictionary with streaming result information
        """
        if not self._check_initialized():
            return {
                "success": False,
                "message": self._last_status["message"],
                "error": "NOT_INITIALIZED",
            }

        try:
            collector_service = self._get_collector_service()

            # Validate that we're connected before starting stream
            if not collector_service.is_connected():
                self._set_status(
                    False, "No board connected. Please connect to a board first."
                )
                return {
                    "success": False,
                    "message": "No board connected. Please connect to a board first.",
                    "error": "NOT_CONNECTED",
                }

            # Check if already streaming
            if collector_service.is_streaming_active():
                self._set_status(False, "Already streaming")
                return {
                    "success": False,
                    "message": "Already streaming",
                    "error": "ALREADY_STREAMING",
                }

            # Ensure buffer_size is an integer
            buffer_size = int(buffer_size)

            success = collector_service.start_stream(buffer_size)

            if success:
                self._set_status(True, "Streaming started successfully")

                # Dispatch additional events for GUI synchronization
                dispatch(
                    EventType.UI_UPDATE_CONTROLS,
                    {"streaming": True, "connected": True},
                    source="interaction_service",
                )
            else:
                self._set_status(False, "Failed to start streaming")

            result = {
                "success": success,
                "buffer_size": buffer_size,
                "message": self._last_status["message"],
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.STREAM_START if success else EventType.ERROR_OCCURRED,
                {"streaming": success, "buffer_size": buffer_size},
                source="interaction_service",
            )

            return result

        except Exception as e:
            self._set_status(False, f"Error starting stream: {e}")
            logging.error(f"Error starting stream: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Stream start failed: {str(e)}",
            }

    def stop_stream(self) -> Dict[str, Any]:
        """
        Stop data streaming.

        Returns:
            Dictionary with streaming result information
        """
        if not self._check_initialized():
            return {
                "success": False,
                "message": self._last_status["message"],
                "error": "NOT_INITIALIZED",
            }

        try:
            collector_service = self._get_collector_service()

            # Validate that we're actually streaming before stopping
            if not collector_service.is_streaming_active():
                self._set_status(False, "Not currently streaming")
                return {
                    "success": False,
                    "message": "No active stream to stop.",
                    "error": "NOT_STREAMING",
                }

            success = collector_service.stop_stream()

            if success:
                self._set_status(True, "Streaming stopped successfully")

                # Dispatch additional events for GUI synchronization
                dispatch(
                    EventType.UI_UPDATE_CONTROLS,
                    {"streaming": False, "connected": True},
                    source="interaction_service",
                )
            else:
                self._set_status(False, "Failed to stop streaming")

            result = {
                "success": success,
                "message": self._last_status["message"],
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.STREAM_STOP if success else EventType.ERROR_OCCURRED,
                {"streaming": False},
                source="interaction_service",
            )

            return result

        except Exception as e:
            self._set_status(False, f"Error stopping stream: {e}")
            logging.error(f"Error stopping stream: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Stream stop failed: {str(e)}",
            }

    def add_streamer(self, streamer_params: str) -> Dict[str, Any]:
        """
        Add a data streamer.

        Args:
            streamer_params: Parameters for the streamer

        Returns:
            Dictionary with streamer result information
        """
        if not self._check_initialized():
            return {
                "success": False,
                "message": self._last_status["message"],
                "error": "NOT_INITIALIZED",
            }

        try:
            collector_service = self._get_collector_service()

            # Validate that we're connected before adding streamer
            if not collector_service.is_connected():
                self._set_status(
                    False, "No board connected. Please connect to a board first."
                )
                return {
                    "success": False,
                    "message": "No board connected. Please connect to a board first.",
                    "error": "NOT_CONNECTED",
                }

            # Determine streamer type and validate accordingly
            streamer_type = self._determine_streamer_type(streamer_params)
            
            if streamer_type == "file":
                # For file streamers, we need recording service and streaming to be active
                recording_service = self._get_recording_service()
                
                if not collector_service.is_streaming_active():
                    self._set_status(
                        False, "Board must be streaming to add file streamer"
                    )
                    return {
                        "success": False,
                        "message": "Board must be streaming to add file streamer",
                        "error": "NOT_STREAMING",
                    }

                if recording_service.is_recording():
                    self._set_status(
                        False, "A file recording is already in progress"
                    )
                    return {
                        "success": False,
                        "message": "A file recording is already in progress. Stop current recording first.",
                        "error": "ALREADY_RECORDING",
                    }

                # Parse file streamer params (format: "file_path|data_type" or just "file_path")
                if "|" in streamer_params:
                    file_path, data_type = streamer_params.split("|", 1)
                else:
                    file_path, data_type = streamer_params, "raw"

                success = recording_service.start_recording(file_path, data_type)
                
            elif streamer_type in ["network", "custom"]:
                # For network/custom streamers, validate preset compatibility
                try:
                    self._validate_streaming_board_preset()
                except Exception as validation_error:
                    self._set_status(False, f"Preset validation failed: {validation_error}")
                    return {
                        "success": False,
                        "message": f"Preset validation failed: {validation_error}",
                        "error": "PRESET_VALIDATION_FAILED",
                    }

                success = collector_service.add_streamer(streamer_params)
            else:
                # Unknown streamer type
                self._set_status(False, f"Unknown streamer type for: {streamer_params}")
                return {
                    "success": False,
                    "message": f"Unknown streamer type for: {streamer_params}",
                    "error": "UNKNOWN_STREAMER_TYPE",
                }

            if success:
                self._set_status(True, f"Streamer added successfully: {streamer_params}")
            else:
                self._set_status(False, f"Failed to add streamer: {streamer_params}")

            result = {
                "success": success,
                "streamer_params": streamer_params,
                "streamer_type": streamer_type,
                "message": self._last_status["message"],
            }

            # Dispatch event for UI updates - ENSURE THIS ALWAYS HAPPENS
            dispatch(
                EventType.STREAMER_ADD,
                {
                    "streamer_params": streamer_params,
                    "streamer_type": streamer_type,
                    "success": success
                },
                source="interaction_service",
            )

            logging.info(f"Dispatched STREAMER_ADD event: success={success}, type={streamer_type}, params={streamer_params}")

            return result

        except Exception as e:
            self._set_status(False, f"Error adding streamer: {e}")
            logging.error(f"Error adding streamer: {e}")
            
            # Dispatch failed event
            dispatch(
                EventType.STREAMER_ADD,
                {
                    "streamer_params": streamer_params,
                    "streamer_type": "unknown",
                    "success": False,
                    "error": str(e)
                },
                source="interaction_service",
            )
            
            return {
                "success": False,
                "error": str(e),
                "message": f"Add streamer failed: {str(e)}",
            }

    def remove_streamer(self, streamer_params: str) -> Dict[str, Any]:
        """
        Remove a data streamer.

        Args:
            streamer_params: Parameters for the streamer to remove

        Returns:
            Dictionary with streamer result information
        """
        if not self._check_initialized():
            return {
                "success": False,
                "message": self._last_status["message"],
                "error": "NOT_INITIALIZED",
            }

        try:
            collector_service = self._get_collector_service()

            # Determine streamer type
            streamer_type = self._determine_streamer_type(streamer_params)

            if streamer_type == "file":
                # For file streamers, stop recording
                recording_service = self._get_recording_service()

                if recording_service.is_recording():
                    success = recording_service.stop_recording()
                else:
                    # Already stopped, consider it successful
                    success = True

            elif streamer_type in ["network", "custom"]:
                # For network/custom streamers, use collector service
                if not collector_service.is_connected():
                    # If board is disconnected, consider removal successful (cleanup)
                    success = True
                    logging.warning("Board disconnected, removing streamer from tracking only")
                else:
                    success = collector_service.remove_streamer(streamer_params)
            else:
                # Try generic removal through collector service
                if collector_service.is_connected():
                    success = collector_service.remove_streamer(streamer_params)
                else:
                    success = True  # Cleanup mode

            if success:
                self._set_status(True, f"Streamer removed successfully: {streamer_params}")
            else:
                self._set_status(False, f"Failed to remove streamer: {streamer_params}")

            result = {
                "success": success,
                "streamer_params": streamer_params,
                "streamer_type": streamer_type,
                "message": self._last_status["message"],
            }

            # Dispatch event for UI updates - ENSURE THIS ALWAYS HAPPENS
            dispatch(
                EventType.STREAMER_REMOVE,
                {
                    "streamer_params": streamer_params,
                    "streamer_type": streamer_type,
                    "success": success
                },
                source="interaction_service",
            )

            logging.info(f"Dispatched STREAMER_REMOVE event: success={success}, type={streamer_type}, params={streamer_params}")

            return result

        except Exception as e:
            self._set_status(False, f"Error removing streamer: {e}")
            logging.error(f"Error removing streamer: {e}")
            
            # Dispatch failed event
            dispatch(
                EventType.STREAMER_REMOVE,
                {
                    "streamer_params": streamer_params,
                    "streamer_type": "unknown",
                    "success": False,
                    "error": str(e)
                },
                source="interaction_service",
            )
            
            return {
                "success": False,
                "error": str(e),
                "message": f"Remove streamer failed: {str(e)}",
            }

    def send_board_config(self, config_cmd: str) -> Dict[str, Any]:
        """
        Send configuration command to the device.

        Args:
            config_cmd: Configuration command string

        Returns:
            Dictionary with configuration result information
        """
        if not self._check_initialized():
            return {
                "success": False,
                "message": self._last_status["message"],
                "error": "NOT_INITIALIZED",
            }

        try:
            collector_service = self._get_collector_service()

            # Validate that we're connected before sending config
            if not collector_service.is_connected():
                self._set_status(
                    False, "No board connected. Please connect to a board first."
                )
                return {
                    "success": False,
                    "message": "No board connected. Please connect to a board first.",
                    "error": "NOT_CONNECTED",
                }

            response = collector_service.config_device(config_cmd)

            result = {
                "success": True,
                "config_command": config_cmd,
                "response": response,
                "message": "Configuration command sent successfully",
            }

            self._set_status(True, f"Configuration command sent: {config_cmd}")

            # Dispatch events for UI updates
            dispatch(
                EventType.BOARD_CONFIG_SENT,
                {"config_command": config_cmd, "response": response},
                source="interaction_service",
            )

            dispatch(
                EventType.DEVICE_CONFIG_RESPONSE,
                {"response": response},
                source="interaction_service",
            )

            return result

        except Exception as e:
            self._set_status(False, f"Error sending config command: {e}")
            logging.error(f"Error sending config command: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Configuration failed: {str(e)}",
            }

    def _determine_streamer_type(self, streamer_params: str) -> str:
        """
        Determine the type of streamer based on parameters.

        Args:
            streamer_params: Streamer parameters string

        Returns:
            Streamer type: "file", "network", or "custom"
        """
        # Handle both string and potential JSON format for file streamers
        if "|" in streamer_params:
            return "file"
        elif streamer_params.endswith((".csv", ".txt")):
            return "file"
        elif "file_path" in streamer_params:  # Añadir esta condición para JSON de file streamer
            return "file"
        elif any(proto in streamer_params for proto in ["streaming_board://", "udp://", "tcp://"]):
            return "network"
        else:
            return "custom"

    def _validate_streaming_board_preset(self) -> None:
        """
        Validate that the current board preset is compatible with streaming.

        Raises:
            Exception: If preset validation fails or user cancels
        """
        try:
            from brainflow.board_shim import BrainFlowPresets

            collector_service = self._get_collector_service()
            collector = collector_service.collector

            if not collector:
                raise Exception("No collector available for preset validation")

            # Get current preset
            current_preset = getattr(collector, "preset", BrainFlowPresets.DEFAULT_PRESET.value)

            # Check if preset is non-default (which can cause streaming issues)
            if current_preset != BrainFlowPresets.DEFAULT_PRESET.value:
                logging.warning(
                    f"Non-default preset detected ({current_preset}). "
                    f"This may cause streaming compatibility issues. "
                    f"Consider using preset {BrainFlowPresets.DEFAULT_PRESET.value} for optimal compatibility."
                )

                # Optionally raise an exception here to force preset validation: (if not blocked, GUI will handle it)
                raise Exception(f"Non-default preset {current_preset} detected. Use preset {BrainFlowPresets.DEFAULT_PRESET.value} for streaming compatibility.")

            logging.info(f"Preset validation passed: current_preset={current_preset}")

        except Exception as e:
            logging.error(f"Preset validation failed: {e}")
            raise e

    def start_recording(self, filename: str, data_type: str = "raw") -> Dict[str, Any]:
        """
        Start data recording.

        Args:
            filename: Path to save the recording
            data_type: Type of data to record ('raw', 'processed', or 'both')

        Returns:
            Dictionary with recording result information
        """
        if not self._check_initialized():
            return {
                "success": False,
                "message": self._last_status["message"],
                "error": "NOT_INITIALIZED",
            }

        try:
            recording_service = self._get_recording_service()
            collector_service = self._get_collector_service()

            # Validate state before recording
            if not collector_service.is_connected():
                self._set_status(
                    False, "No board connected. Please connect to a board first."
                )
                return {
                    "success": False,
                    "message": "No board connected. Please connect to a board first.",
                    "error": "NOT_CONNECTED",
                }

            # Check if already recording
            if recording_service.is_recording():
                self._set_status(False, "Already recording")
                return {
                    "success": False,
                    "message": "Already recording",
                    "error": "ALREADY_RECORDING",
                }

            if not collector_service.collector:
                self._set_status(False, "Collector not available")
                return {
                    "success": False,
                    "message": "Collector not available.",
                    "error": "NO_COLLECTOR",
                }

            success = recording_service.start_recording(filename, data_type)

            if success:
                self._set_status(True, "Recording started successfully")
            else:
                self._set_status(False, "Failed to start recording")

            result = {
                "success": success,
                "filename": filename,
                "data_type": data_type,
                "message": self._last_status["message"],
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.RECORDING_START if success else EventType.ERROR_OCCURRED,
                {"recording": success, "filename": filename, "data_type": data_type},
                source="interaction_service",
            )

            if success:
                dispatch(
                    EventType.RECORDING_STATUS_CHANGED,
                    {"recording": True, "filename": filename},
                    source="interaction_service",
                )

            return result

        except Exception as e:
            self._set_status(False, f"Error starting recording: {e}")
            logging.error(f"Error starting recording: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Recording start failed: {str(e)}",
            }

    def stop_recording(self) -> Dict[str, Any]:
        """
        Stop data recording.

        Returns:
            Dictionary with recording result information
        """
        if not self._check_initialized():
            return {
                "success": False,
                "message": self._last_status["message"],
                "error": "NOT_INITIALIZED",
            }

        try:
            recording_service = self._get_recording_service()
            collector_service = self._get_collector_service()

            # Validate state before stopping recording
            if not recording_service.is_recording():
                self._set_status(False, "Not currently recording")
                return {
                    "success": False,
                    "message": "No active recording to stop.",
                    "error": "NOT_RECORDING",
                }

            if not collector_service.collector:
                self._set_status(False, "Collector not available")
                return {
                    "success": False,
                    "message": "Collector not available.",
                    "error": "NO_COLLECTOR",
                }

            success = recording_service.stop_recording()

            if success:
                self._set_status(True, "Recording stopped successfully")
            else:
                self._set_status(False, "Failed to stop recording")

            result = {
                "success": success,
                "message": self._last_status["message"],
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.RECORDING_STOP if success else EventType.ERROR_OCCURRED,
                {"recording": False},
                source="interaction_service",
            )

            if success:
                dispatch(
                    EventType.RECORDING_STATUS_CHANGED,
                    {"recording": False},
                    source="interaction_service",
                )

            return result

        except Exception as e:
            self._set_status(False, f"Error stopping recording: {e}")
            logging.error(f"Error stopping recording: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Recording stop failed: {str(e)}",
            }

    def insert_marker(self, marker_value: float) -> Dict[str, Any]:
        """
        Insert a marker into the data stream.

        Args:
            marker_value: Value of the marker to insert

        Returns:
            Dictionary with marker result information
        """
        try:
            recording_service = self._get_recording_service()
            collector_service = self._get_collector_service()

            success = recording_service.insert_marker(marker_value)

            result = {
                "success": success,
                "marker_value": marker_value,
                "message": (
                    f"Marker {marker_value} inserted successfully"
                    if success
                    else "Failed to insert marker"
                ),
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.MARKER_INSERT,
                {"marker_value": marker_value, "success": success},
                source="interaction_service",
            )

            return result

        except Exception as e:
            logging.error(f"Error inserting marker: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Marker insertion failed: {str(e)}",
            }

    def apply_filters(self, filter_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply signal processing filters.

        Args:
            filter_config: Filter configuration

        Returns:
            Dictionary with filter result information
        """
        try:
            from .processor_service import ProcessorService
            from .data_access_service import DataAccessService

            processor_service = ProcessorService()
            data_service = DataAccessService.get_instance()

            # Check if we should apply to visualization
            apply_to_viz = filter_config.get("apply_to_visualization", True)
            force_update = filter_config.get("force_update", False)

            # Initialize processor if needed
            collector_service = self._get_collector_service()
            sampling_rate = collector_service.get_sampling_rate()
            if sampling_rate > 0 and (not hasattr(processor_service, "processor") or processor_service.processor is None):
                processor_service.initialize_processor(sampling_rate)

            # Enable filters in data access service first
            data_service.enable_filters(True, filter_config)

            # If force_update is enabled, reprocess existing data
            if force_update:
                current_data, current_timestamps = data_service.get_raw_data()
                if current_data.size > 0:
                    logging.info(f"Force updating filters on existing data buffer of {current_data.shape}")
                    # This will trigger the callbacks with filtered data
                    data_service.update_data(current_data, current_timestamps)

            # Apply to visualization if requested
            if apply_to_viz:
                try:
                    visualization_service = self._get_visualization_service()
                    
                    # Apply bandpass filter
                    if filter_config.get("bandpass", {}).get("enabled", False):
                        bp_config = filter_config["bandpass"]
                        visualization_service.set_bandpass_filter(
                            True,
                            bp_config.get("low_cut", bp_config.get("low", 1.0)),
                            bp_config.get("high_cut", bp_config.get("high", 50.0))
                        )
                    else:
                        visualization_service.set_bandpass_filter(False)

                    # Apply notch filter  
                    if filter_config.get("notch", {}).get("enabled", False):
                        notch_config = filter_config["notch"]
                        visualization_service.set_notch_filter(
                            True,
                            notch_config.get("frequency", notch_config.get("freq", 50.0))
                        )
                    else:
                        visualization_service.set_notch_filter(False)

                    # Apply detrend
                    visualization_service.set_detrend(filter_config.get("detrend", False))

                    logging.info("Filters applied to visualization")
                except Exception as viz_error:
                    logging.warning(f"Could not apply filters to visualization: {viz_error}")
            else:
                try:
                    visualization_service = self._get_visualization_service()
                    
                    # Remove filters from visualization
                    visualization_service.set_bandpass_filter(False, 1.0, 50.0)
                    visualization_service.set_notch_filter(False)
                    visualization_service.set_detrend(False)

                    DataAccessService.get_instance().enable_filters(False)
                    
                    logging.info("Filters removed from data stream and visualization")
                except Exception as viz_error:
                    logging.warning(f"Could not remove filters from visualization: {viz_error}")

            result = {
                "success": True,
                "filter_config": filter_config,
                "applied_to_visualization": apply_to_viz,
                "force_updated": force_update,
                "message": "Filters applied successfully",
            }

            # Dispatch event for UI updates (this will update the processing panel)
            dispatch(
                EventType.FILTER_APPLY,
                {
                    "filter_config": filter_config, 
                    "success": True,
                    "applied_to_visualization": apply_to_viz
                },
                source="interaction_service",
            )

            dispatch(
                EventType.PROCESSING_COMPLETED,
                {"filter_config": filter_config},
                source="interaction_service",
            )

            return result

        except Exception as e:
            logging.error(f"Error applying filters: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Filter application failed: {str(e)}",
            }

    def start_visualization(self, viz_type: str = "eeg") -> Dict[str, Any]:
        """
        Start data visualization.

        Args:
            viz_type: Type of visualization ("eeg" or "brain_map")

        Returns:
            Dictionary with visualization result information
        """
        try:
            # Use singleton instances
            viz_service = self._get_visualization_service()
            collector_service = self._get_collector_service()
            processor_service = self._get_processor_service()

            # Validate that we have a connected collector and are streaming
            if not collector_service.is_connected():
                return {
                    "success": False,
                    "message": "No board connected. Please connect to a board first.",
                    "error": "NOT_CONNECTED",
                }

            if not collector_service.is_streaming_active():
                return {
                    "success": False,
                    "message": "No active stream. Please start streaming first.",
                    "error": "NOT_STREAMING",
                }

            success = False
            if viz_type == "eeg":
                success = viz_service.create_eeg_visualizer(
                    collector_service.collector, processor_service.processor
                )
                if success:
                    success = viz_service.start_eeg_visualization()
            elif viz_type == "brain_map":
                success = viz_service.create_brain_map_visualizer(
                    collector_service.collector, processor_service.processor
                )
                if success:
                    success = viz_service.start_brain_map_visualization()

            result = {
                "success": success,
                "visualization_type": viz_type,
                "message": (
                    f"{viz_type.title()} visualization started successfully"
                    if success
                    else f"Failed to start {viz_type} visualization"
                ),
            }

            # Dispatch event for UI updates
            event_type = (
                EventType.BRAIN_MAP_SHOW
                if viz_type == "brain_map"
                else EventType.VISUALIZATION_START
            )
            dispatch(
                event_type,
                {"visualization_type": viz_type, "success": success},
                source="interaction_service",
            )

            # Additional UI update for show visualization button
            if success:
                dispatch(
                    EventType.UI_UPDATE_CONTROLS,
                    {"visualization_visible": True, "streaming": True},
                    source="interaction_service",
                )

            return result

        except Exception as e:
            logging.error(f"Error starting visualization: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Visualization start failed: {str(e)}",
            }

    def stop_visualization(self, viz_type: str = "eeg") -> Dict[str, Any]:
        """
        Stop data visualization.

        Args:
            viz_type: Type of visualization ("eeg" or "brain_map")

        Returns:
            Dictionary with visualization result information
        """
        try:
            viz_service = self._get_visualization_service()

            success = False
            if viz_type == "eeg":
                success = viz_service.stop_eeg_visualization()
            elif viz_type == "brain_map":
                success = viz_service.stop_brain_map_visualization()

            result = {
                "success": success,
                "visualization_type": viz_type,
                "message": (
                    f"{viz_type.title()} visualization stopped successfully"
                    if success
                    else f"Failed to stop {viz_type} visualization"
                ),
            }

            # Dispatch event for UI updates
            event_type = (
                EventType.BRAIN_MAP_HIDE
                if viz_type == "brain_map"
                else EventType.VISUALIZATION_STOP
            )
            dispatch(
                event_type,
                {"visualization_type": viz_type, "success": success},
                source="interaction_service",
            )

            # Additional UI update for show visualization button
            if success:
                dispatch(
                    EventType.UI_UPDATE_CONTROLS,
                    {"visualization_visible": False, "streaming": True},
                    source="interaction_service",
                )

            return result

        except Exception as e:
            logging.error(f"Error stopping visualization: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Visualization stop failed: {str(e)}",
            }

    def perform_ica(self, num_components: int) -> Dict[str, Any]:
        """
        Perform Independent Component Analysis.

        Args:
            num_components: Number of ICA components

        Returns:
            Dictionary with ICA result information
        """
        try:
            from .processor_service import ProcessorService
            from .data_access_service import DataAccessService

            processor_service = ProcessorService()
            data_service = DataAccessService.get_instance()

            # Get current data
            data, timestamps = data_service.get_current_data()

            if data.size == 0:
                return {"success": False, "message": "No data available for ICA"}

            # Perform ICA
            w, k, a, s = processor_service.perform_ica(data, num_components)

            success = (
                w is not None and k is not None and a is not None and s is not None
            )

            result = {
                "success": success,
                "num_components": num_components,
                "message": (
                    "ICA computed successfully" if success else "Failed to compute ICA"
                ),
            }

            if success:
                result["components_shape"] = s.shape

            # Dispatch event for UI updates
            dispatch(
                EventType.ICA_COMPUTE if success else EventType.ERROR_OCCURRED,
                {"num_components": num_components, "success": success},
                source="interaction_service",
            )

            if success:
                dispatch(
                    EventType.ICA_COMPLETED,
                    {"components_shape": s.shape},
                    source="interaction_service",
                )

            return result

        except Exception as e:
            logging.error(f"Error performing ICA: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"ICA computation failed: {str(e)}",
            }

    def get_eeg_metrics(self) -> Dict[str, Any]:
        """
        Calculate EEG metrics from current data.

        Returns:
            Dictionary with EEG metrics or success/error information
        """
        try:
            from .processor_service import ProcessorService
            from .data_access_service import DataAccessService

            processor_service = ProcessorService()
            data_service = DataAccessService.get_instance()

            # Get current data and metadata
            data, timestamps = data_service.get_current_data()
            metadata = data_service.get_metadata()

            if data.size == 0:
                return {
                    "success": False,
                    "message": "No data available for metrics calculation",
                }

            eeg_channels = metadata.get("eeg_channels", [])
            if not eeg_channels:
                return {
                    "success": False,
                    "message": "No EEG channels available for metrics calculation",
                }

            # Calculate metrics
            raw_metrics = processor_service.get_eeg_metrics(data, eeg_channels)

            # Convert NumPy arrays to Python lists for JSON serialization
            serializable_metrics = {}
            for metric_name, metric_value in raw_metrics.items():
                if hasattr(metric_value, 'tolist'):
                    # NumPy array
                    serializable_metrics[metric_name] = metric_value.tolist()
                elif hasattr(metric_value, '__iter__') and not isinstance(metric_value, str):
                    # Other iterable
                    serializable_metrics[metric_name] = list(metric_value)
                elif hasattr(metric_value, 'item'):
                    # NumPy scalar
                    serializable_metrics[metric_name] = metric_value.item()
                else:
                    # Regular scalar
                    serializable_metrics[metric_name] = float(metric_value)

            result = {
                "success": True,
                "metrics": serializable_metrics,
                "message": "EEG metrics calculated successfully",
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.METRICS_CALCULATED,
                {"metrics": serializable_metrics, "success": True},
                source="interaction_service",
            )

            return result

        except Exception as e:
            logging.error(f"Error calculating EEG metrics: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Metrics calculation failed: {str(e)}",
            }

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.

        Returns:
            Dictionary with system status
        """
        try:
            collector_service = self._get_collector_service()
            recording_service = self._get_recording_service()
            data_service = self._get_data_access_service()
            viz_service = self._get_visualization_service()

            # Get metadata
            metadata = data_service.get_metadata()

            status = {
                "connected": collector_service.is_connected(),
                "streaming": collector_service.is_streaming_active(),
                "recording": recording_service.is_recording(),
                "visualization_visible": viz_service.visualization_visible(),
                "brain_map_visible": viz_service.brain_map_visible(),
                "sampling_rate": metadata.get("sampling_rate", 0),
                "board_id": metadata.get("board_id", -1),
                "board_name": metadata.get("board_name", ""),
                "eeg_channels": metadata.get("eeg_channels", []),
                "channel_names": data_service.get_channel_names(),
                "data_available": data_service.get_current_data()[0].size > 0,
            }

            if recording_service.is_recording():
                status["recording_duration"] = (
                    recording_service.get_recording_duration()
                )
                status["recording_filename"] = (
                    recording_service.get_recording_filename()
                )
                status["recording_data_type"] = (
                    recording_service.get_recording_data_type()
                )

            result = {
                "success": True,
                "status": status,
                "message": "System status retrieved successfully",
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.SYSTEM_STATUS_CHANGED,
                {"status": status},
                source="interaction_service",
            )

            return result

        except Exception as e:
            logging.error(f"Error getting system status: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Status retrieval failed: {str(e)}",
            }

    def config_device(self, config_cmd: str) -> Dict[str, Any]:
        """
        Send configuration command to the device.

        Args:
            config_cmd: Configuration command string

        Returns:
            Dictionary with configuration result information
        """
        try:
            collector_service = self._get_collector_service()
            response = collector_service.config_device(config_cmd)

            result = {
                "success": True,
                "config_command": config_cmd,
                "response": response,
                "message": "Configuration command sent successfully",
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.BOARD_CONFIG_SENT,
                {"config_command": config_cmd, "response": response},
                source="interaction_service",
            )

            dispatch(
                EventType.DEVICE_CONFIG_RESPONSE,
                {"response": response},
                source="interaction_service",
            )

            return result

        except Exception as e:
            logging.error(f"Error sending config command: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Configuration failed: {str(e)}",
            }

    def save_current_data(
        self, filename: str, data_type: str = "raw"
    ) -> Dict[str, Any]:
        """
        Save current data to file.

        Args:
            filename: File to save data to
            data_type: Type of data to save ('raw' or 'processed')

        Returns:
            Dictionary with save result information
        """
        try:
            data_service = self._get_data_access_service()
            recording_service = self._get_recording_service()

            # Get current data
            data, timestamps = data_service.get_current_data()

            if data.size == 0:
                return {
                    "success": False,
                    "message": "No data available to save",
                }

            # Save data using recording service
            recording_service.save_data(filename, data_type)

            result = {
                "success": True,
                "filename": filename,
                "data_type": data_type,
                "message": f"Data saved to {filename} successfully",
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.DATA_UPDATED,
                {"filename": filename, "data_type": data_type, "saved": True},
                source="interaction_service",
            )

            return result

        except Exception as e:
            logging.error(f"Error saving data: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Data save failed: {str(e)}",
            }

    def cleanup(self) -> None:
        """Clean up the interaction service."""
        try:
            self._initialized = False
            logging.info("Interaction service cleaned up")
        except Exception as e:
            logging.error(f"Error during interaction service cleanup: {e}")
            logging.error(f"Error during interaction service cleanup: {e}")
