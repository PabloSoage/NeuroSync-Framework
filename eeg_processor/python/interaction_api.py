"""
Interaction API for controlling EEG processor functionality.

This API allows external control of all GUI functions including
board connection, data processing, recording, and visualization.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

from .services.data_access_service import DataAccessService
from .core.event_system import EventSystem, EventType


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
            from .collectors.board_configuration import BoardConfiguration
            
            boards = BoardConfiguration.get_all_boards()
            board_list = []
            
            for board_name, board_id in boards:
                board_info = {
                    "id": board_id,
                    "name": board_name,
                    "description": BoardConfiguration.get_board_description(board_id)
                }
                board_list.append(board_info)
            
            return board_list
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
    def connect_to_board(board_id: int, params: Dict[str, Any] = None, 
                        preset: int = 0) -> Dict[str, Any]:
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
            from .services.collector_service import CollectorService
            
            collector_service = CollectorService()
            success = collector_service.connect_to_board(board_id, params or {}, preset)
            
            if success:
                # Publish event for GUI updates
                event_system = EventSystem.get_instance()
                event_system.publish_event(
                    EventType.BOARD_CONNECT,
                    {
                        "board_id": board_id,
                        "params": params or {},
                        "preset": preset
                    },
                    source="interaction_api"
                )
                
                # Get board info
                board_info = collector_service.get_board_info()
                
                return {
                    "success": True,
                    "message": "Board connected successfully",
                    "board_info": board_info
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to connect to board",
                    "error": "Connection failed"
                }
                
        except Exception as e:
            logging.error(f"Error connecting to board: {e}")
            return {
                "success": False,
                "message": "Error connecting to board",
                "error": str(e)
            }
    
    @staticmethod
    def disconnect_from_board() -> Dict[str, Any]:
        """
        Disconnect from the current board.
        
        Returns:
            Dictionary with disconnection result
        """
        try:
            from .services.collector_service import CollectorService
            
            collector_service = CollectorService()
            success = collector_service.disconnect_from_board()
            
            if success:
                # Publish event for GUI updates
                event_system = EventSystem.get_instance()
                event_system.publish_event(
                    EventType.BOARD_DISCONNECT,
                    {},
                    source="interaction_api"
                )
                
                return {
                    "success": True,
                    "message": "Board disconnected successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to disconnect from board"
                }
                
        except Exception as e:
            logging.error(f"Error disconnecting from board: {e}")
            return {
                "success": False,
                "message": "Error disconnecting from board",
                "error": str(e)
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
            from .services.collector_service import CollectorService
            
            collector_service = CollectorService()
            success = collector_service.start_stream(buffer_size)
            
            if success:
                # Publish event for GUI updates
                event_system = EventSystem.get_instance()
                event_system.publish_event(
                    EventType.STREAM_START,
                    {"buffer_size": buffer_size},
                    source="interaction_api"
                )
                
                return {
                    "success": True,
                    "message": "Stream started successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to start stream"
                }
                
        except Exception as e:
            logging.error(f"Error starting stream: {e}")
            return {
                "success": False,
                "message": "Error starting stream",
                "error": str(e)
            }
    
    @staticmethod
    def stop_stream() -> Dict[str, Any]:
        """
        Stop data streaming.
        
        Returns:
            Dictionary with stream stop result
        """
        try:
            from .services.collector_service import CollectorService
            
            collector_service = CollectorService()
            success = collector_service.stop_stream()
            
            if success:
                # Publish event for GUI updates
                event_system = EventSystem.get_instance()
                event_system.publish_event(
                    EventType.STREAM_STOP,
                    {},
                    source="interaction_api"
                )
                
                return {
                    "success": True,
                    "message": "Stream stopped successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to stop stream"
                }
                
        except Exception as e:
            logging.error(f"Error stopping stream: {e}")
            return {
                "success": False,
                "message": "Error stopping stream",
                "error": str(e)
            }
    
    @staticmethod
    def get_connection_status() -> Dict[str, Any]:
        """
        Get current connection and streaming status.
        
        Returns:
            Dictionary with status information
        """
        try:
            from .services.collector_service import CollectorService
            
            collector_service = CollectorService()
            data_access = DataAccessService.get_instance()
            
            return {
                "connected": collector_service.is_connected(),
                "streaming": collector_service.is_streaming_active(),
                "metadata": data_access.get_metadata()
            }
            
        except Exception as e:
            logging.error(f"Error getting connection status: {e}")
            return {
                "connected": False,
                "streaming": False,
                "error": str(e)
            }
    
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
            from .services.processor_service import ProcessorService
            from .services.collector_service import CollectorService
            
            # Get current data
            collector_service = CollectorService()
            data, _ = collector_service.get_board_data()
            
            if data.size == 0:
                return {
                    "success": False,
                    "message": "No data available for filtering"
                }
            
            # Initialize processor if needed
            processor_service = ProcessorService()
            sampling_rate = collector_service.get_sampling_rate()
            if processor_service.processor is None:
                processor_service.initialize_processor(sampling_rate)
            
            # Apply filters
            filtered_data = processor_service.apply_all_filters(data, filter_config)
            
            # Set processed data back to collector
            collector_service.set_processed_data(filtered_data)
            
            # Publish event for GUI updates
            event_system = EventSystem.get_instance()
            event_system.publish_event(
                EventType.FILTER_APPLY,
                {"filter_config": filter_config},
                source="interaction_api"
            )
            
            return {
                "success": True,
                "message": "Filters applied successfully",
                "filter_config": filter_config
            }
            
        except Exception as e:
            logging.error(f"Error applying filters: {e}")
            return {
                "success": False,
                "message": "Error applying filters",
                "error": str(e)
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
            from .services.visualization_service import VisualizationService
            from .services.collector_service import CollectorService
            from .services.processor_service import ProcessorService
            
            # Get services
            viz_service = VisualizationService()
            collector_service = CollectorService()
            processor_service = ProcessorService()
            
            # Initialize processor if needed
            if processor_service.processor is None:
                sampling_rate = collector_service.get_sampling_rate()
                processor_service.initialize_processor(sampling_rate)
            
            success = False
            if viz_type == "eeg":
                if not viz_service.eeg_visualizer:
                    viz_service.create_eeg_visualizer(collector_service, processor_service)
                success = viz_service.start_eeg_visualization()
            elif viz_type == "brain_map":
                if not viz_service.brain_map_visualizer:
                    viz_service.create_brain_map_visualizer(collector_service, processor_service)
                success = viz_service.start_brain_map_visualization()
            
            if success:
                # Publish event for GUI updates
                event_system = EventSystem.get_instance()
                event_system.publish_event(
                    EventType.VISUALIZATION_START,
                    {"viz_type": viz_type},
                    source="interaction_api"
                )
                
                return {
                    "success": True,
                    "message": f"{viz_type} visualization started successfully"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to start {viz_type} visualization"
                }
                
        except Exception as e:
            logging.error(f"Error starting visualization: {e}")
            return {
                "success": False,
                "message": "Error starting visualization",
                "error": str(e)
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
            from .services.visualization_service import VisualizationService
            
            viz_service = VisualizationService()
            
            success = False
            if viz_type == "eeg":
                success = viz_service.stop_eeg_visualization()
            elif viz_type == "brain_map":
                success = viz_service.stop_brain_map_visualization()
            
            if success:
                # Publish event for GUI updates
                event_system = EventSystem.get_instance()
                event_system.publish_event(
                    EventType.VISUALIZATION_STOP,
                    {"viz_type": viz_type},
                    source="interaction_api"
                )
                
                return {
                    "success": True,
                    "message": f"{viz_type} visualization stopped successfully"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to stop {viz_type} visualization"
                }
                
        except Exception as e:
            logging.error(f"Error stopping visualization: {e}")
            return {
                "success": False,
                "message": "Error stopping visualization",
                "error": str(e)
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
            from .services.recording_service import RecordingService
            from .services.collector_service import CollectorService
            
            recording_service = RecordingService()
            collector_service = CollectorService()
            
            success = recording_service.start_recording(collector_service, filename, data_type)
            
            if success:
                # Publish event for GUI updates
                event_system = EventSystem.get_instance()
                event_system.publish_event(
                    EventType.RECORDING_START,
                    {
                        "filename": filename,
                        "data_type": data_type
                    },
                    source="interaction_api"
                )
                
                return {
                    "success": True,
                    "message": "Recording started successfully",
                    "filename": filename,
                    "data_type": data_type
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to start recording"
                }
                
        except Exception as e:
            logging.error(f"Error starting recording: {e}")
            return {
                "success": False,
                "message": "Error starting recording",
                "error": str(e)
            }
    
    @staticmethod
    def stop_recording() -> Dict[str, Any]:
        """
        Stop data recording.
        
        Returns:
            Dictionary with recording stop result
        """
        try:
            from .services.recording_service import RecordingService
            from .services.collector_service import CollectorService
            
            recording_service = RecordingService()
            collector_service = CollectorService()
            
            success = recording_service.stop_recording(collector_service)
            
            if success:
                # Publish event for GUI updates
                event_system = EventSystem.get_instance()
                event_system.publish_event(
                    EventType.RECORDING_STOP,
                    {},
                    source="interaction_api"
                )
                
                return {
                    "success": True,
                    "message": "Recording stopped successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to stop recording"
                }
                
        except Exception as e:
            logging.error(f"Error stopping recording: {e}")
            return {
                "success": False,
                "message": "Error stopping recording",
                "error": str(e)
            }
    
    @staticmethod
    def get_recording_status() -> Dict[str, Any]:
        """
        Get current recording status.
        
        Returns:
            Dictionary with recording status
        """
        try:
            from .services.recording_service import RecordingService
            
            recording_service = RecordingService()
            
            return {
                "recording": recording_service.is_recording(),
                "duration": recording_service.get_recording_duration(),
                "filename": recording_service.get_recording_filename(),
                "data_type": recording_service.get_recording_data_type()
            }
            
        except Exception as e:
            logging.error(f"Error getting recording status: {e}")
            return {
                "recording": False,
                "error": str(e)
            }
    
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
            from .services.collector_service import CollectorService
            
            collector_service = CollectorService()
            success = collector_service.insert_marker(marker_value)
            
            if success:
                # Publish event for GUI updates
                event_system = EventSystem.get_instance()
                event_system.publish_event(
                    EventType.MARKER_INSERT,
                    {"marker_value": marker_value},
                    source="interaction_api"
                )
                
                return {
                    "success": True,
                    "message": f"Marker {marker_value} inserted successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to insert marker"
                }
                
        except Exception as e:
            logging.error(f"Error inserting marker: {e}")
            return {
                "success": False,
                "message": "Error inserting marker",
                "error": str(e)
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
            from .services.collector_service import CollectorService
            
            collector_service = CollectorService()
            success = collector_service.add_streamer(streamer_params)
            
            if success:
                # Publish event for GUI updates
                event_system = EventSystem.get_instance()
                event_system.publish_event(
                    EventType.STREAMER_ADD,
                    {"streamer_params": streamer_params},
                    source="interaction_api"
                )
                
                return {
                    "success": True,
                    "message": "Streamer added successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to add streamer"
                }
                
        except Exception as e:
            logging.error(f"Error adding streamer: {e}")
            return {
                "success": False,
                "message": "Error adding streamer",
                "error": str(e)
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
            from .services.collector_service import CollectorService
            
            collector_service = CollectorService()
            success = collector_service.remove_streamer(streamer_params)
            
            if success:
                # Publish event for GUI updates
                event_system = EventSystem.get_instance()
                event_system.publish_event(
                    EventType.STREAMER_REMOVE,
                    {"streamer_params": streamer_params},
                    source="interaction_api"
                )
                
                return {
                    "success": True,
                    "message": "Streamer removed successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to remove streamer"
                }
                
        except Exception as e:
            logging.error(f"Error removing streamer: {e}")
            return {
                "success": False,
                "message": "Error removing streamer",
                "error": str(e)
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
            from .services.processor_service import ProcessorService
            from .services.collector_service import CollectorService
            
            # Get current data
            collector_service = CollectorService()
            data, _ = collector_service.get_board_data()
            
            if data.size == 0:
                return {
                    "success": False,
                    "message": "No data available for ICA"
                }
            
            # Initialize processor if needed
            processor_service = ProcessorService()
            sampling_rate = collector_service.get_sampling_rate()
            if processor_service.processor is None:
                processor_service.initialize_processor(sampling_rate)
            
            # Perform ICA
            w, k, a, s = processor_service.perform_ica(data, num_components)
            
            if w is not None:
                # Publish event for GUI updates
                event_system = EventSystem.get_instance()
                event_system.publish_event(
                    EventType.ICA_APPLY,
                    {"num_components": num_components},
                    source="interaction_api"
                )
                
                return {
                    "success": True,
                    "message": "ICA performed successfully",
                    "components": num_components
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to perform ICA"
                }
                
        except Exception as e:
            logging.error(f"Error performing ICA: {e}")
            return {
                "success": False,
                "message": "Error performing ICA",
                "error": str(e)
            }
    
    @staticmethod
    def get_eeg_metrics() -> Dict[str, Any]:
        """
        Calculate EEG metrics from current data.
        
        Returns:
            Dictionary with EEG metrics
        """
        try:
            from .services.processor_service import ProcessorService
            from .services.collector_service import CollectorService
            
            # Get current data
            collector_service = CollectorService()
            data, _ = collector_service.get_board_data()
            eeg_channels = collector_service.get_eeg_channels()
            
            if data.size == 0:
                return {
                    "success": False,
                    "message": "No data available for metrics calculation"
                }
            
            # Initialize processor if needed
            processor_service = ProcessorService()
            sampling_rate = collector_service.get_sampling_rate()
            if processor_service.processor is None:
                processor_service.initialize_processor(sampling_rate)
            
            # Calculate metrics
            metrics = processor_service.get_eeg_metrics(data, eeg_channels)
            
            return {
                "success": True,
                "message": "EEG metrics calculated successfully",
                "metrics": metrics
            }
            
        except Exception as e:
            logging.error(f"Error calculating EEG metrics: {e}")
            return {
                "success": False,
                "message": "Error calculating EEG metrics",
                "error": str(e)
            }
    
    @staticmethod
    def get_system_status() -> Dict[str, Any]:
        """
        Get comprehensive system status.
        
        Returns:
            Dictionary with complete system status
        """
        try:
            # Get connection status
            connection_status = EEGProcessorInteractionAPI.get_connection_status()
            
            # Get recording status
            recording_status = EEGProcessorInteractionAPI.get_recording_status()
            
            # Get visualization status
            from .services.visualization_service import VisualizationService
            viz_service = VisualizationService()
            
            return {
                "connection": connection_status,
                "recording": recording_status,
                "visualization": {
                    "eeg_visible": viz_service.visualization_visible(),
                    "brain_map_visible": viz_service.brain_map_visible()
                },
                "timestamp": __import__('time').time()
            }
            
        except Exception as e:
            logging.error(f"Error getting system status: {e}")
            return {
                "error": str(e),
                "timestamp": __import__('time').time()
            }
