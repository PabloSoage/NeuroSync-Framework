"""
Service for handling interaction API requests.

This service acts as a bridge between the external API and internal services,
publishing events to update the UI when API actions are performed. It follows
the same singleton pattern as the input_collector module.
"""

import logging
import threading
from typing import Dict, List, Any, Optional

from ..core.event_system import EventDispatcher, EventType, dispatch


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

        logging.info("Interaction service initialized")

    def _check_initialized(self) -> bool:
        """Check if the service is properly initialized."""
        if not self._initialized:
            logging.warning("Interaction service not properly initialized")
            return False
        return True

    def initialize(self) -> None:
        """Initialize the service with required dependencies."""
        try:
            # Initialize any required dependencies here
            self._initialized = True
            logging.info("Interaction service initialization completed")
        except Exception as e:
            logging.error(f"Error initializing interaction service: {e}")
            raise

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
            from .collector_service import CollectorService

            collector_service = CollectorService()
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
            from .collector_service import CollectorService

            collector_service = CollectorService()
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
        try:
            from .collector_service import CollectorService

            collector_service = CollectorService()
            success = collector_service.start_stream(buffer_size)

            result = {
                "success": success,
                "buffer_size": buffer_size,
                "message": (
                    "Streaming started successfully"
                    if success
                    else "Failed to start streaming"
                ),
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.STREAM_START if success else EventType.ERROR_OCCURRED,
                {"streaming": success, "buffer_size": buffer_size},
                source="interaction_service",
            )

            return result

        except Exception as e:
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
        try:
            from .collector_service import CollectorService

            collector_service = CollectorService()
            success = collector_service.stop_stream()

            result = {
                "success": success,
                "message": (
                    "Streaming stopped successfully"
                    if success
                    else "Failed to stop streaming"
                ),
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.STREAM_STOP if success else EventType.ERROR_OCCURRED,
                {"streaming": False},
                source="interaction_service",
            )

            return result

        except Exception as e:
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
        try:
            from .collector_service import CollectorService

            collector_service = CollectorService()
            success = collector_service.add_streamer(streamer_params)

            result = {
                "success": success,
                "streamer_params": streamer_params,
                "message": (
                    "Streamer added successfully"
                    if success
                    else "Failed to add streamer"
                ),
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.STREAMER_ADD,
                {"streamer_params": streamer_params, "success": success},
                source="interaction_service",
            )

            return result

        except Exception as e:
            logging.error(f"Error adding streamer: {e}")
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
        try:
            from .collector_service import CollectorService

            collector_service = CollectorService()
            success = collector_service.remove_streamer(streamer_params)

            result = {
                "success": success,
                "streamer_params": streamer_params,
                "message": (
                    "Streamer removed successfully"
                    if success
                    else "Failed to remove streamer"
                ),
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.STREAMER_REMOVE,
                {"streamer_params": streamer_params, "success": success},
                source="interaction_service",
            )

            return result

        except Exception as e:
            logging.error(f"Error removing streamer: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Remove streamer failed: {str(e)}",
            }

    def start_recording(self, filename: str, data_type: str = "raw") -> Dict[str, Any]:
        """
        Start data recording.

        Args:
            filename: Path to save the recording
            data_type: Type of data to record ('raw', 'processed', or 'both')

        Returns:
            Dictionary with recording result information
        """
        try:
            from .recording_service import RecordingService
            from .collector_service import CollectorService

            recording_service = RecordingService()
            collector_service = CollectorService()

            success = recording_service.start_recording(
                collector_service.collector, filename, data_type
            )

            result = {
                "success": success,
                "filename": filename,
                "data_type": data_type,
                "message": (
                    "Recording started successfully"
                    if success
                    else "Failed to start recording"
                ),
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
        try:
            from .recording_service import RecordingService
            from .collector_service import CollectorService

            recording_service = RecordingService()
            collector_service = CollectorService()

            success = recording_service.stop_recording(collector_service.collector)

            result = {
                "success": success,
                "message": (
                    "Recording stopped successfully"
                    if success
                    else "Failed to stop recording"
                ),
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
            from .recording_service import RecordingService
            from .collector_service import CollectorService

            recording_service = RecordingService()
            collector_service = CollectorService()

            success = recording_service.insert_marker(
                collector_service.collector, marker_value
            )

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

            # Get current data
            data, timestamps = data_service.get_current_data()

            if data.size == 0:
                return {"success": False, "message": "No data available for filtering"}

            # Apply filters
            filtered_data = processor_service.apply_all_filters(data, filter_config)

            # Update data service with filtered data
            data_service.update_data(filtered_data, timestamps)

            result = {
                "success": True,
                "filter_config": filter_config,
                "message": "Filters applied successfully",
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.FILTER_APPLY,
                {"filter_config": filter_config, "success": True},
                source="interaction_service",
            )

            dispatch(
                EventType.PROCESSING_COMPLETED,
                {"data_shape": filtered_data.shape},
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
            from .visualization_service import VisualizationService
            from .collector_service import CollectorService
            from .processor_service import ProcessorService

            viz_service = VisualizationService()
            collector_service = CollectorService()
            processor_service = ProcessorService()

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
            from .visualization_service import VisualizationService

            viz_service = VisualizationService()

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
            metrics = processor_service.get_eeg_metrics(data, eeg_channels)

            result = {
                "success": True,
                "metrics": metrics,
                "message": "EEG metrics calculated successfully",
            }

            # Dispatch event for UI updates
            dispatch(
                EventType.METRICS_CALCULATED,
                {"metrics": metrics, "success": True},
                source="interaction_service",
            )

            return result

        except Exception as e:
            logging.error(f"Error calculating EEG metrics: {e}")
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
            from .collector_service import CollectorService
            from .recording_service import RecordingService
            from .data_access_service import DataAccessService
            from .visualization_service import VisualizationService

            collector_service = CollectorService()
            recording_service = RecordingService()
            data_service = DataAccessService.get_instance()
            viz_service = VisualizationService()

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
            from .collector_service import CollectorService

            collector_service = CollectorService()
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
            from .collector_service import CollectorService

            collector_service = CollectorService()

            if not collector_service.collector:
                return {
                    "success": False,
                    "message": "No collector available to save data",
                }

            # Save data using collector's save method
            collector_service.collector.save_data(filename, data_type)

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
