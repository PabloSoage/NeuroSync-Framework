"""
Interaction API for controlling EEG processor functionality.

This API allows external control of all GUI functions including
board connection, data processing, recording, and visualization.
It follows the same pattern as the input_collector module.
"""

import logging
from typing import Dict, List, Any, Optional

from .services.interaction_service import InteractionService


class EEGProcessorInteractionAPI:
    """
    Main interaction API for the EEG processor.

    This class provides methods to control all aspects of the EEG processor
    including board connection, streaming, processing, recording, and visualization.
    """

    @staticmethod
    def get_available_boards() -> List[Dict[str, Any]]:
        """
        Get list of available boards.

        Returns:
            List of dictionaries with board information
        """
        try:
            service = InteractionService.get_instance()
            return service.get_available_boards()
        except Exception as e:
            logging.error(f"Error getting available boards: {e}")
            return []

    @staticmethod
    def get_board_requirements(board_id: int) -> Dict[str, bool]:
        """
        Get parameter requirements for a specific board.

        Args:
            board_id: ID of the board

        Returns:
            Dictionary with required parameters
        """
        try:
            from .collectors.board_configuration import BoardConfiguration

            return BoardConfiguration.get_board_requirements(board_id)
        except Exception as e:
            logging.error(f"Error getting board requirements: {e}")
            return {}

    @staticmethod
    def connect_to_board(
        board_id: int, params: Optional[Dict[str, Any]] = None, preset: int = 0
    ) -> Dict[str, Any]:
        """
        Connect to an EEG board.

        Args:
            board_id: ID of the board to connect to
            params: Connection parameters
            preset: Data preset to use

        Returns:
            Dictionary with connection result
        """
        try:
            service = InteractionService.get_instance()
            return service.connect_to_board(board_id, params or {}, preset)
        except Exception as e:
            logging.error(f"Error connecting to board: {e}")
            return {
                "success": False,
                "message": "Error connecting to board",
                "error": str(e),
            }

    @staticmethod
    def disconnect_from_board() -> Dict[str, Any]:
        """
        Disconnect from the current board.

        Returns:
            Dictionary with disconnection result
        """
        try:
            service = InteractionService.get_instance()
            return service.disconnect_from_board()
        except Exception as e:
            logging.error(f"Error disconnecting from board: {e}")
            return {
                "success": False,
                "message": "Error disconnecting from board",
                "error": str(e),
            }

    @staticmethod
    def start_stream(buffer_size: int = 450000) -> Dict[str, Any]:
        """
        Start data streaming.

        Args:
            buffer_size: Size of the buffer for data

        Returns:
            Dictionary with stream start result
        """
        try:
            service = InteractionService.get_instance()
            return service.start_stream(buffer_size)
        except Exception as e:
            logging.error(f"Error starting stream: {e}")
            return {
                "success": False,
                "message": "Error starting stream",
                "error": str(e),
            }

    @staticmethod
    def stop_stream() -> Dict[str, Any]:
        """
        Stop data streaming.

        Returns:
            Dictionary with stream stop result
        """
        try:
            service = InteractionService.get_instance()
            return service.stop_stream()
        except Exception as e:
            logging.error(f"Error stopping stream: {e}")
            return {
                "success": False,
                "message": "Error stopping stream",
                "error": str(e),
            }

    @staticmethod
    def get_connection_status() -> Dict[str, Any]:
        """
        Get current connection and streaming status.

        Returns:
            Dictionary with status information
        """
        try:
            service = InteractionService.get_instance()
            system_status = service.get_system_status()

            if system_status.get("success", False):
                status = system_status.get("status", {})
                return {
                    "connected": status.get("connected", False),
                    "streaming": status.get("streaming", False),
                    "board_id": status.get("board_id", -1),
                    "board_name": status.get("board_name", ""),
                    "sampling_rate": status.get("sampling_rate", 0),
                    "eeg_channels": status.get("eeg_channels", []),
                    "channel_names": status.get("channel_names", []),
                }
            else:
                return {
                    "connected": False,
                    "streaming": False,
                    "error": system_status.get("error", "Unknown error"),
                }
        except Exception as e:
            logging.error(f"Error getting connection status: {e}")
            return {"connected": False, "streaming": False, "error": str(e)}

    @staticmethod
    def apply_filters(filter_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply signal processing filters.

        Args:
            filter_config: Dictionary with filter configuration

        Returns:
            Dictionary with filter application result
        """
        try:
            service = InteractionService.get_instance()
            return service.apply_filters(filter_config)
        except Exception as e:
            logging.error(f"Error applying filters: {e}")
            return {
                "success": False,
                "message": "Error applying filters",
                "error": str(e),
            }

    @staticmethod
    def start_visualization(viz_type: str = "eeg") -> Dict[str, Any]:
        """
        Start data visualization.

        Args:
            viz_type: Type of visualization ("eeg" or "brain_map")

        Returns:
            Dictionary with visualization start result
        """
        try:
            service = InteractionService.get_instance()
            return service.start_visualization(viz_type)
        except Exception as e:
            logging.error(f"Error starting visualization: {e}")
            return {
                "success": False,
                "message": "Error starting visualization",
                "error": str(e),
            }

    @staticmethod
    def stop_visualization(viz_type: str = "eeg") -> Dict[str, Any]:
        """
        Stop data visualization.

        Args:
            viz_type: Type of visualization ("eeg" or "brain_map")

        Returns:
            Dictionary with visualization stop result
        """
        try:
            service = InteractionService.get_instance()
            return service.stop_visualization(viz_type)
        except Exception as e:
            logging.error(f"Error stopping visualization: {e}")
            return {
                "success": False,
                "message": "Error stopping visualization",
                "error": str(e),
            }

    @staticmethod
    def start_recording(filename: str, data_type: str = "raw") -> Dict[str, Any]:
        """
        Start data recording.

        Args:
            filename: Path to save the recording
            data_type: Type of data to record ("raw", "processed", or "both")

        Returns:
            Dictionary with recording start result
        """
        try:
            service = InteractionService.get_instance()
            return service.start_recording(filename, data_type)
        except Exception as e:
            logging.error(f"Error starting recording: {e}")
            return {
                "success": False,
                "message": "Error starting recording",
                "error": str(e),
            }

    @staticmethod
    def stop_recording() -> Dict[str, Any]:
        """
        Stop data recording.

        Returns:
            Dictionary with recording stop result
        """
        try:
            service = InteractionService.get_instance()
            return service.stop_recording()
        except Exception as e:
            logging.error(f"Error stopping recording: {e}")
            return {
                "success": False,
                "message": "Error stopping recording",
                "error": str(e),
            }

    @staticmethod
    def get_recording_status() -> Dict[str, Any]:
        """
        Get current recording status.

        Returns:
            Dictionary with recording status
        """
        try:
            service = InteractionService.get_instance()
            system_status = service.get_system_status()

            if system_status.get("success", False):
                status = system_status.get("status", {})
                result = {
                    "recording": status.get("recording", False),
                }

                # Add recording details if recording is active
                if status.get("recording", False):
                    result.update(
                        {
                            "duration": status.get("recording_duration", 0),
                            "filename": status.get("recording_filename", ""),
                            "data_type": status.get("recording_data_type", "raw"),
                        }
                    )

                return result
            else:
                return {
                    "recording": False,
                    "error": system_status.get("error", "Unknown error"),
                }
        except Exception as e:
            logging.error(f"Error getting recording status: {e}")
            return {"recording": False, "error": str(e)}

    @staticmethod
    def insert_marker(marker_value: float) -> Dict[str, Any]:
        """
        Insert a marker into the data stream.

        Args:
            marker_value: Value of the marker to insert

        Returns:
            Dictionary with marker insertion result
        """
        try:
            service = InteractionService.get_instance()
            return service.insert_marker(marker_value)
        except Exception as e:
            logging.error(f"Error inserting marker: {e}")
            return {
                "success": False,
                "message": "Error inserting marker",
                "error": str(e),
            }

    @staticmethod
    def add_streamer(streamer_params: str) -> Dict[str, Any]:
        """
        Add a data streamer.

        Args:
            streamer_params: Parameters for the streamer

        Returns:
            Dictionary with streamer addition result
        """
        try:
            service = InteractionService.get_instance()
            return service.add_streamer(streamer_params)
        except Exception as e:
            logging.error(f"Error adding streamer: {e}")
            return {
                "success": False,
                "message": "Error adding streamer",
                "error": str(e),
            }

    @staticmethod
    def remove_streamer(streamer_params: str) -> Dict[str, Any]:
        """
        Remove a data streamer.

        Args:
            streamer_params: Parameters for the streamer to remove

        Returns:
            Dictionary with streamer removal result
        """
        try:
            service = InteractionService.get_instance()
            return service.remove_streamer(streamer_params)
        except Exception as e:
            logging.error(f"Error removing streamer: {e}")
            return {
                "success": False,
                "message": "Error removing streamer",
                "error": str(e),
            }

    @staticmethod
    def send_board_config(config_cmd: str) -> Dict[str, Any]:
        """
        Send configuration command to the device.

        Args:
            config_cmd: Configuration command string

        Returns:
            Dictionary with configuration result
        """
        try:
            service = InteractionService.get_instance()
            return service.config_device(config_cmd)
        except Exception as e:
            logging.error(f"Error sending board config: {e}")
            return {
                "success": False,
                "message": "Error sending board config",
                "error": str(e),
            }

    @staticmethod
    def perform_ica(num_components: int) -> Dict[str, Any]:
        """
        Perform Independent Component Analysis.

        Args:
            num_components: Number of ICA components

        Returns:
            Dictionary with ICA result
        """
        try:
            service = InteractionService.get_instance()
            return service.perform_ica(num_components)
        except Exception as e:
            logging.error(f"Error performing ICA: {e}")
            return {
                "success": False,
                "message": "Error performing ICA",
                "error": str(e),
            }

    @staticmethod
    def get_eeg_metrics() -> Dict[str, Any]:
        """
        Calculate EEG metrics from current data.

        Returns:
            Dictionary with EEG metrics
        """
        try:
            service = InteractionService.get_instance()
            return service.get_eeg_metrics()
        except Exception as e:
            logging.error(f"Error calculating EEG metrics: {e}")
            return {
                "success": False,
                "message": "Error calculating EEG metrics",
                "error": str(e),
            }

    @staticmethod
    def convert_to_mne(duration: int = 5) -> Dict[str, Any]:
        """
        Convert data to MNE format.

        Args:
            duration: Duration in seconds for conversion

        Returns:
            Dictionary with MNE conversion result
        """
        try:
            # This would need to be implemented in the interaction service
            # For now, return a placeholder
            return {
                "success": False,
                "message": "MNE conversion not yet implemented",
                "error": "Feature not available",
            }
        except Exception as e:
            logging.error(f"Error converting to MNE: {e}")
            return {
                "success": False,
                "message": "Error converting to MNE",
                "error": str(e),
            }

    @staticmethod
    def plot_mne_visualization(plot_type: str) -> Dict[str, Any]:
        """
        Plot MNE visualization.

        Args:
            plot_type: Type of MNE plot

        Returns:
            Dictionary with MNE plot result
        """
        try:
            # This would need to be implemented in the interaction service
            # For now, return a placeholder
            return {
                "success": False,
                "message": "MNE plotting not yet implemented",
                "error": "Feature not available",
            }
        except Exception as e:
            logging.error(f"Error plotting MNE visualization: {e}")
            return {
                "success": False,
                "message": "Error plotting MNE visualization",
                "error": str(e),
            }

    @staticmethod
    def compute_wavelet(wavelet_type: int, level: int, channel: int) -> Dict[str, Any]:
        """
        Compute wavelet transform.

        Args:
            wavelet_type: Type of wavelet
            level: Decomposition level
            channel: Channel to process

        Returns:
            Dictionary with wavelet computation result
        """
        try:
            # This would need to be implemented in the interaction service
            # For now, return a placeholder
            return {
                "success": False,
                "message": "Wavelet computation not yet implemented",
                "error": "Feature not available",
            }
        except Exception as e:
            logging.error(f"Error computing wavelet: {e}")
            return {
                "success": False,
                "message": "Error computing wavelet",
                "error": str(e),
            }

    @staticmethod
    def save_current_data(filename: str, data_type: str = "raw") -> Dict[str, Any]:
        """
        Save current data to file.

        Args:
            filename: File to save data to
            data_type: Type of data to save ('raw' or 'processed')

        Returns:
            Dictionary with save result
        """
        try:
            service = InteractionService.get_instance()
            return service.save_current_data(filename, data_type)
        except Exception as e:
            logging.error(f"Error saving data: {e}")
            return {
                "success": False,
                "message": "Error saving data",
                "error": str(e),
            }

    @staticmethod
    def get_system_status() -> Dict[str, Any]:
        """
        Get comprehensive system status.

        Returns:
            Dictionary with complete system status
        """
        try:
            service = InteractionService.get_instance()
            return service.get_system_status()
        except Exception as e:
            logging.error(f"Error getting system status: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": __import__("time").time(),
            }
