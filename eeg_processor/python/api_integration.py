import os
import sys
import socket
import asyncio
import logging
import time
import numpy as np
import importlib
from typing import Dict, List, Any, Optional, Tuple
from fastapi import Request
from fastapi.responses import HTMLResponse

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from api_explorer import ApiExplorer
    explorer_available = True
except ImportError:
    explorer_available = False
    logger.warning("API Explorer not found. Web API will not be available.")

# Import core services - we need direct access to services, not just through API
from .data_access_api import EEGDataAPI
from .services.data_access_service import DataAccessService
from .services.collector_service import CollectorService

class EEGProcessorApiIntegration:
    """Direct integration with EEG processor services and data."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = EEGProcessorApiIntegration()
        return cls._instance
        
    def __init__(self):
        self.explorer = None
        self.module_id = "eeg_processor"
        self.data_service = DataAccessService.get_instance()
        
        # Get collector service directly for access to board/collector info
        self.collector_service = None
        try:
            self.collector_service = CollectorService()
        except Exception as e:
            logger.warning(f"Could not initialize collector service: {e}")
        
        # Callback registration for streaming data
        self.callback_id = None
        
        # Timer to periodically pull data from the collector
        self.update_timer = None
        
    def start_data_polling(self, interval=0.5):
        """Start polling for data from the collector service."""
        self.stop_data_polling()  # Stop any existing timer
        
        loop = asyncio.get_event_loop()
        self.update_timer = loop.call_later(interval, self._poll_data, interval, loop)
        logger.info(f"Started data polling with interval {interval}s")
        
    def stop_data_polling(self):
        """Stop polling for data."""
        if self.update_timer:
            self.update_timer.cancel()
            self.update_timer = None
            logger.info("Stopped data polling")
            
    def _poll_data(self, interval, loop):
        """Poll for new data from the collector and update the data service."""
        try:
            if self.collector_service and self.collector_service.is_connected() and self.collector_service.is_streaming_active():
                # Get data from collector
                data, timestamps = self.collector_service.get_board_data(100)  # Get last 100 samples
                
                if data.size > 0:
                    # Update data in the data service
                    self.data_service.update_data(data, timestamps)
                    
                    # Update metadata if not set
                    metadata = self.data_service.get_metadata()
                    if not metadata.get("streaming", False) or metadata.get("sampling_rate", 0) == 0:
                        new_metadata = {
                            "streaming": True,
                            "sampling_rate": self.collector_service.get_sampling_rate(),
                            "eeg_channels": self.collector_service.get_eeg_channels(),
                            "channel_names": self._get_channel_names_direct()
                        }
                        self.data_service.update_metadata(new_metadata)
                        
                    logger.debug(f"Updated data service with data shape {data.shape}")
        except Exception as e:
            logger.error(f"Error polling data: {e}")
        finally:
            # Schedule next poll
            if loop.is_running():
                self.update_timer = loop.call_later(interval, self._poll_data, interval, loop)
        
    def register_api(self, host: str = "127.0.0.1", port: int = 8000) -> bool:
        """Register all EEG data endpoints with the API Explorer."""
        if not explorer_available:
            return False
            
        # Find available port
        while self._port_in_use(host, port):
            logger.info(f"Port {port} already in use, trying port {port+1}")
            port += 1
        
        # Get API Explorer instance
        self.explorer = ApiExplorer.get_instance()
        
        # Register module - especificando show_data_table=True para este módulo
        self.explorer.register_module(
            module_id=self.module_id,
            name="EEG Processor",
            description="Real-time access to EEG data streams and device information",
            show_data_table=True  # Indicamos que queremos mostrar la tabla de datos
        )
        
        # Register method groups
        self._register_method_groups()
        
        # Register methods for each group
        self._register_status_methods()
        self._register_device_methods()
        self._register_data_methods()
        self._register_channel_methods()
        self._register_quality_methods()
        self._register_event_methods()
        
        # Start server
        self.explorer.start_server(host=host, port=port, block=False)

        # Ya no es necesaria la ruta /realtime, se integra en la página principal
        # en la pestaña "Real-time Events"

        # Register data callback
        self.callback_id = EEGDataAPI.register_data_callback(self._handle_data_callback)
        
        # Start data polling
        self.start_data_polling()
        
        return True
        
    def _register_method_groups(self):
        """Register all method groups."""
        groups = [
            ("status", "Status Methods"),
            ("device", "Device Methods"),
            ("data", "Data Access Methods"),
            ("channels", "Channel Methods"),
            ("quality", "Signal Quality Methods"),
            ("events", "Event Methods")
        ]
        
        for group_id, group_name in groups:
            self.explorer.add_method_group(self.module_id, group_id, group_name)
            
    def _register_status_methods(self):
        """Register methods for checking stream status."""
        self.explorer.register_method(
            self.module_id, "status", "is_streaming",
            {
                "name": "is_streaming()",
                "description": "Check if EEG data is currently streaming",
                "type": "GET",
                "params": {}
            },
            self._handle_is_streaming
        )
        
        self.explorer.register_method(
            self.module_id, "status", "get_metadata",
            {
                "name": "get_metadata()",
                "description": "Get stream metadata (board info, channels, etc.)",
                "type": "GET",
                "params": {}
            },
            self._handle_get_metadata
        )
        
        self.explorer.register_method(
            self.module_id, "status", "get_sampling_rate",
            {
                "name": "get_sampling_rate()",
                "description": "Get current sampling rate in Hz",
                "type": "GET",
                "params": {}
            },
            self._handle_get_sampling_rate
        )
        
    def _register_device_methods(self):
        """Register methods for accessing device information."""
        self.explorer.register_method(
            self.module_id, "device", "get_board_info",
            {
                "name": "get_board_info()",
                "description": "Get information about the connected board",
                "type": "GET",
                "params": {}
            },
            self._handle_get_board_info
        )
        
        self.explorer.register_method(
            self.module_id, "device", "get_preset",
            {
                "name": "get_preset()",
                "description": "Get current data preset mode",
                "type": "GET",
                "params": {}
            },
            self._handle_get_preset
        )
        
    def _register_data_methods(self):
        """Register methods for accessing EEG data."""
        self.explorer.register_method(
            self.module_id, "data", "get_current_data",
            {
                "name": "get_current_data(max_samples)",
                "description": "Get latest EEG samples (all channels)",
                "type": "GET",
                "params": {
                    "max_samples": {
                        "type": "number",
                        "description": "Maximum number of samples to return",
                        "required": False
                    }
                }
            },
            self._handle_get_current_data
        )
        
        self.explorer.register_method(
            self.module_id, "data", "get_eeg_data",
            {
                "name": "get_eeg_data(max_samples)",
                "description": "Get latest data for EEG channels only",
                "type": "GET",
                "params": {
                    "max_samples": {
                        "type": "number",
                        "description": "Maximum number of samples to return",
                        "required": False
                    }
                }
            },
            self._handle_get_eeg_data
        )
        
    def _register_channel_methods(self):
        """Register methods for accessing channel information."""
        self.explorer.register_method(
            self.module_id, "channels", "get_channel_names",
            {
                "name": "get_channel_names()",
                "description": "Get names of all channels",
                "type": "GET",
                "params": {}
            },
            self._handle_get_channel_names
        )
        
        self.explorer.register_method(
            self.module_id, "channels", "get_eeg_channels",
            {
                "name": "get_eeg_channels()",
                "description": "Get indices of EEG channels only",
                "type": "GET",
                "params": {}
            },
            self._handle_get_eeg_channels
        )
        
        self.explorer.register_method(
            self.module_id, "channels", "get_channel_data",
            {
                "name": "get_channel_data(channel_index, max_samples)",
                "description": "Get data for a specific channel by index",
                "type": "GET",
                "params": {
                    "channel_index": {
                        "type": "number",
                        "description": "Channel index",
                        "required": True
                    },
                    "max_samples": {
                        "type": "number",
                        "description": "Maximum number of samples to return",
                        "required": False
                    }
                }
            },
            self._handle_get_channel_data
        )
        
        self.explorer.register_method(
            self.module_id, "channels", "get_channel_by_name",
            {
                "name": "get_channel_by_name(channel_name, max_samples)",
                "description": "Get data for a specific channel by name",
                "type": "GET",
                "params": {
                    "channel_name": {
                        "type": "text",
                        "description": "Channel name",
                        "required": True
                    },
                    "max_samples": {
                        "type": "number",
                        "description": "Maximum number of samples to return",
                        "required": False
                    }
                }
            },
            self._handle_get_channel_by_name
        )
        
    def _register_quality_methods(self):
        """Register methods for signal quality assessment."""
        self.explorer.register_method(
            self.module_id, "quality", "get_signal_quality",
            {
                "name": "get_signal_quality(channel_index)",
                "description": "Get signal quality for a specific channel (0-1)",
                "type": "GET",
                "params": {
                    "channel_index": {
                        "type": "number",
                        "description": "Channel index",
                        "required": True
                    }
                }
            },
            self._handle_get_signal_quality
        )
        
        self.explorer.register_method(
            self.module_id, "quality", "get_all_channels_quality",
            {
                "name": "get_all_channels_quality()",
                "description": "Get signal quality for all channels",
                "type": "GET",
                "params": {}
            },
            self._handle_get_all_channels_quality
        )
        
    def _register_event_methods(self):
        """Register methods for event handling."""
        self.explorer.register_method(
            self.module_id, "events", "register_data_callback",
            {
                "name": "register_data_callback()",
                "description": "Register for real-time data updates via WebSocket",
                "type": "POST",
                "params": {}
            },
            self._handle_register_data_callback
        )
        
    def _port_in_use(self, host, port):
        """Check if port is already in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex((host, port)) == 0
            
    # --- Direct access to internal data ---
    
    def _get_active_collector(self):
        """Get currently active collector for direct data access."""
        if not self.collector_service:
            return None
            
        # Try to access the collector service's active collector
        try:
            # Different possible attribute names
            if hasattr(self.collector_service, 'collector'):
                return self.collector_service.collector
            elif hasattr(self.collector_service, 'active_collector'):
                return self.collector_service.active_collector
            elif hasattr(self.collector_service, 'current_collector'):
                return self.collector_service.current_collector
            
            # Fallback: try to get collector from internal state
            collectors = getattr(self.collector_service, '_collectors', {})
            active_id = getattr(self.collector_service, '_active_collector_id', None)
            if active_id and active_id in collectors:
                return collectors[active_id]
                
        except Exception as e:
            logger.error(f"Error accessing collector: {e}")
            
        return None
    
    def _get_board_id_and_preset(self) -> Tuple[int, int]:
        """Get current board ID and preset."""
        collector = self._get_active_collector()
        if collector and hasattr(collector, 'board_id') and hasattr(collector, 'preset'):
            return collector.board_id, collector.preset
            
        # Fallback: if collector or attributes aren't available
        try:
            # If collector service is available, try to get board info from there
            if self.collector_service:
                board_info = self.collector_service.get_board_info()
                if board_info:
                    return board_info.get('board_id', None), board_info.get('preset', None)
        except Exception as e:
            logger.debug(f"Error getting board ID and preset from fallback: {e}")
        
        return None, None
        
    def _get_sampling_rate_direct(self) -> float:
        """Get sampling rate directly from collector."""
        collector = self._get_active_collector()
        if collector and hasattr(collector, 'sampling_rate'):
            return collector.sampling_rate
        
        # Alternative method: try BrainFlow directly
        try:
            from brainflow.board_shim import BoardShim
            board_id, preset = self._get_board_id_and_preset()
            if board_id is not None and preset is not None:
                return BoardShim.get_sampling_rate(board_id, preset)
        except Exception as e:
            logger.debug(f"Error getting sampling rate from BrainFlow: {e}")
            
        return 0
        
    def _get_eeg_channels_direct(self) -> List[int]:
        """Get EEG channels directly from collector."""
        # First attempt: from collector
        collector = self._get_active_collector()
        if collector and hasattr(collector, 'eeg_channels'):
            return collector.eeg_channels
    
        # Second attempt: from collector service
        if self.collector_service:
            try:
                channels = self.collector_service.get_eeg_channels()
                if channels:
                    return channels
            except Exception as e:
                logger.debug(f"Error getting EEG channels from collector service: {e}")
        
        # Third attempt: from BrainFlow directly
        try:
            from brainflow.board_shim import BoardShim
            board_id, preset = self._get_board_id_and_preset()
            if board_id is not None and preset is not None:
                return BoardShim.get_eeg_channels(board_id, preset)
        except Exception as e:
            logger.debug(f"Error getting EEG channels from BrainFlow: {e}")
        
        # Fourth attempt: from metadata
        try:
            metadata = self.data_service.get_metadata()
            if metadata and 'eeg_channels' in metadata:
                return metadata['eeg_channels']
        except Exception as e:
            logger.debug(f"Error getting EEG channels from metadata: {e}")
    
        # Last resort: return empty list
        return []
        
    def _get_channel_names_direct(self) -> List[str]:
        """Get channel names directly from collector."""
        collector = self._get_active_collector()
        if collector and hasattr(collector, 'eeg_names'):
            return collector.eeg_names
            
        # Fallback: generate generic names for EEG channels
        eeg_channels = self._get_eeg_channels_direct()
        if eeg_channels:
            return [f"CH{i+1}" for i in range(len(eeg_channels))]
            
        return []
        
    def _get_board_info_direct(self) -> Dict[str, Any]:
        """Get complete board info directly from collector."""
        # First attempt: get currently selected board info
        selected_board_info = self._get_selected_board_info()
        if selected_board_info:
            return selected_board_info
        
        # Fallback: get info from collector service if connected
        if self.collector_service and self.collector_service.is_connected():
            try:
                board_info = self.collector_service.get_board_info()
                if board_info:
                    # Add connection and streaming status
                    board_info["connected"] = True
                    board_info["streaming"] = self.collector_service.is_streaming_active()
                    return board_info
            except Exception as e:
                logger.debug(f"Error getting board info from collector service: {e}")
    
        # Last fallback: get from data service metadata
        try:
            metadata = self.data_service.get_metadata()
            if "board_info" in metadata and isinstance(metadata["board_info"], dict):
                board_info = metadata["board_info"].copy()
                # Add connection status
                if self.collector_service:
                    board_info["connected"] = self.collector_service.is_connected()
                    board_info["streaming"] = self.collector_service.is_streaming_active()
                return board_info
        except Exception as e:
            logger.debug(f"Error getting board info from metadata: {e}")
    
        # If all else fails: return minimal info
        return {
            "board_id": -1,
            "board_name": "Unknown",
            "sampling_rate": 0,
            "eeg_channels": [],
            "channel_names": [],
            "connected": False,
            "streaming": False
        }
        
    def _get_selected_board_info(self) -> Dict[str, Any]:
        """Get information about the currently selected board (even if not connected)."""
        try:
            from .collectors.board_configuration import BoardConfiguration
            
            # Try to access the UI connection panel to get selected board
            if not hasattr(self, "_main_window"):
                # Find the main application window
                from PyQt5.QtWidgets import QApplication
                for widget in QApplication.topLevelWidgets():
                    if widget.__class__.__name__ == "EEGProcessorApp":
                        self._main_window = widget
                        break
            
            # If we found the main window, try to get the selected board
            if hasattr(self, "_main_window"):
                # Get the connection panel from the main window
                if hasattr(self._main_window, "connection_panel"):
                    connection_panel = self._main_window.connection_panel
                    # Get the selected board ID
                    if hasattr(connection_panel, "board_type_combo"):
                        board_id = connection_panel.board_type_combo.currentData()
                        if board_id is not None:
                            # Get the selected preset
                            preset = None
                            if hasattr(connection_panel, "preset_combo"):
                                preset = connection_panel.preset_combo.currentData()
                            
                            # Get board description from BoardConfiguration
                            board_desc = BoardConfiguration.get_board_description(board_id, preset)
                            if board_desc:
                                # Get connection status
                                connected = self.collector_service and self.collector_service.is_connected()
                                streaming = self.collector_service and self.collector_service.is_streaming_active()
                                
                                # Format channel names properly
                                eeg_names = board_desc.get("eeg_names", "")
                                if isinstance(eeg_names, str) and "," in eeg_names:
                                    eeg_names = eeg_names.split(",")
                                
                                # Create new dictionary with ordered keys for better readability
                                ordered_result = {}
                                
                                # 1. Basic board information first
                                ordered_result["board_id"] = board_id
                                ordered_result["board_name"] = board_desc.get("name", f"Board ID {board_id}")
                                ordered_result["sampling_rate"] = board_desc.get("sampling_rate", 0)
                                ordered_result["preset"] = preset
                                
                                # 2. Add available presets if present
                                if "available_presets" in board_desc:
                                    ordered_result["available_presets"] = board_desc["available_presets"]
                                
                                # 3. EEG channels and names
                                if "eeg_channels" in board_desc:
                                    ordered_result["eeg_channels"] = board_desc["eeg_channels"]
                                
                                if eeg_names:
                                    ordered_result["eeg_names"] = eeg_names
                                    ordered_result["channel_names"] = eeg_names
                                
                                # 4. Primary channel info
                                if "num_rows" in board_desc:
                                    ordered_result["num_rows"] = board_desc["num_rows"]
                                if "package_num_channel" in board_desc:
                                    ordered_result["package_num_channel"] = board_desc["package_num_channel"]
                                if "timestamp_channel" in board_desc:
                                    ordered_result["timestamp_channel"] = board_desc["timestamp_channel"]
                                if "marker_channel" in board_desc:
                                    ordered_result["marker_channel"] = board_desc["marker_channel"]
                                
                                # 5. Other specialized channels in a consistent order
                                for channel_type in [
                                    "emg_channels", "ecg_channels", "eog_channels", 
                                    "eda_channels", "ppg_channels", "accel_channels", 
                                    "gyro_channels", "temperature_channels", 
                                    "resistance_channels", "battery_channel"
                                ]:
                                    if channel_type in board_desc:
                                        ordered_result[channel_type] = board_desc[channel_type]
                                
                                # 6. Connection status at the end
                                ordered_result["connected"] = connected
                                ordered_result["streaming"] = streaming
                                
                                # 7. Copy any remaining fields we didn't explicitly handle
                                for key, value in board_desc.items():
                                    if key not in ordered_result and key != "name":  # Skip 'name' as we renamed it to 'board_name'
                                        ordered_result[key] = value
                                
                                return ordered_result
        except Exception as e:
            logger.debug(f"Error getting selected board info: {e}")
            
        return None

    # --- Handler methods for API endpoints ---
    
    async def _handle_is_streaming(self):
        """Handle is_streaming endpoint."""
        is_streaming = EEGDataAPI.is_streaming()
        
        # If API reports not streaming but we have a collector that is streaming
        if not is_streaming and self.collector_service:
            is_streaming = self.collector_service.is_streaming_active()
            
            # Update data service with streaming status
            if is_streaming:
                self.data_service.update_metadata({"streaming": True})
                
        return {"streaming": is_streaming}
        
    async def _handle_get_metadata(self):
        """Handle get_metadata endpoint with enhanced data."""
        metadata = EEGDataAPI.get_metadata()
        
        # Enhance with direct data if needed
        if not metadata.get("sampling_rate"):
            metadata["sampling_rate"] = self._get_sampling_rate_direct()
            
        if not metadata.get("channel_names"):
            metadata["channel_names"] = self._get_channel_names_direct()
            
        if not metadata.get("eeg_channels"):
            metadata["eeg_channels"] = self._get_eeg_channels_direct()
            
        # Add board info if available
        board_info = self._get_board_info_direct()
        if board_info:
            metadata["board_info"] = board_info
            
        return metadata
        
    async def _handle_get_sampling_rate(self):
        """Handle get_sampling_rate endpoint."""
        rate = EEGDataAPI.get_sampling_rate()
        
        # Fall back to direct access if API returns 0
        if rate == 0:
            rate = self._get_sampling_rate_direct()
            
        return {"sampling_rate": rate}
        
    async def _handle_get_board_info(self):
        """Handle get_board_info endpoint."""
        board_info = self._get_board_info_direct()
        
        # Add connection status
        if self.collector_service:
            board_info["connected"] = self.collector_service.is_connected()
            board_info["streaming"] = self.collector_service.is_streaming_active()
        
        # Always provide at least some basic data
        if not board_info:
            # Provide minimal info if nothing else is available
            return {
                "error": "No board information available",
                "connected": False,
                "streaming": False
            }
        
        return board_info
    
    async def _handle_get_preset(self):
        """Handle get_preset endpoint."""
        board_id, preset = self._get_board_id_and_preset()
        
        # If preset is None, try to get it from board info
        if preset is None:
            board_info = self._get_board_info_direct()
            preset = board_info.get("preset", 0)
        
        return {
            "preset": preset if preset is not None else 0,
            "board_id": board_id if board_id is not None else -1
        }
        
    async def _handle_get_current_data(self, max_samples: Optional[int] = None):
        """Handle get_current_data endpoint."""
        data, timestamps = EEGDataAPI.get_current_data()
        
        # Apply max_samples limit if provided
        if max_samples and data.size > 0:
            data = data[:, -max_samples:]
            timestamps = timestamps[-max_samples:]
            
        # Convert to list for JSON serialization
        if hasattr(data, 'tolist'):
            data = data.tolist()
            
        return {
            "data": data,
            "timestamps": timestamps,
            "shape": [len(data), len(timestamps)] if isinstance(data, list) else []
        }
        
    async def _handle_get_eeg_data(self, max_samples: Optional[int] = None):
        """Handle get_eeg_data endpoint (EEG channels only)."""
        data, timestamps = EEGDataAPI.get_current_data()
        
        # Extract only EEG channels if we have data
        if data.size > 0:
            # Get EEG channels
            eeg_channels = self._get_eeg_channels_direct()
            
            if eeg_channels and len(eeg_channels) > 0:
                # Get actual channel names from metadata
                actual_channel_names = EEGDataAPI.get_channel_names()
                
                # Ensure eeg_channels indices are valid for the data array
                valid_channels = [ch for ch in eeg_channels if ch < data.shape[0]]
                
                if valid_channels:
                    # Filter to keep only valid EEG channels
                    eeg_data = data[valid_channels]
                    
                    # Apply max_samples limit if provided
                    if max_samples and eeg_data.shape[1] > max_samples:
                        eeg_data = eeg_data[:, -max_samples:]
                        if len(timestamps) > max_samples:
                            timestamps = timestamps[-max_samples:]
                
                    # Generate proper channel names
                    channel_names = []
                    if actual_channel_names and len(actual_channel_names) >= len(valid_channels):
                        # Get the actual channel names for the valid channels
                        for i, ch in enumerate(valid_channels):
                            if ch < len(actual_channel_names):
                                channel_name = actual_channel_names[ch]
                            else:
                                # Use the EEG channel index if necessary
                                eeg_index = eeg_channels.index(ch) if ch in eeg_channels else i
                                if eeg_index < len(actual_channel_names):
                                    channel_name = actual_channel_names[eeg_index]
                                else:
                                    channel_name = f"CH{ch+1}"
                            channel_names.append(channel_name)
                    else:
                        # Use generic channel names with correct indices
                        for ch in valid_channels:
                            channel_names.append(f"CH{ch+1}")
                    
                    # Convert to list for JSON serialization
                    if hasattr(eeg_data, 'tolist'):
                        eeg_data = eeg_data.tolist()
                        
                    return {
                        "data": eeg_data,
                        "timestamps": timestamps,
                        "eeg_channels": valid_channels,
                        "channel_names": channel_names
                    }
                
            # Fallback: return empty result with metadata
            channel_names = EEGDataAPI.get_channel_names()
            return {
                "data": [],
                "timestamps": [],
                "eeg_channels": eeg_channels,
                "channel_names": channel_names if channel_names else [],
                "error": "No valid EEG channels found or no data available"
            }
        
        # If no data at all
        return {
            "data": [],
            "timestamps": [],
            "eeg_channels": [],
            "channel_names": [],
            "error": "No data available"
        }

    async def _handle_get_channel_names(self):
        """Handle get_channel_names endpoint."""
        names = EEGDataAPI.get_channel_names()
        
        # Fall back to direct access if API returns empty list
        if not names:
            names = self._get_channel_names_direct()
            
        return {"channel_names": names}
        
    async def _handle_get_eeg_channels(self):
        """Handle get_eeg_channels endpoint."""
        channels = self._get_eeg_channels_direct()
        
        # Get the actual channel names from the collector metadata
        channel_names = EEGDataAPI.get_channel_names()
        
        # Map channel indices to their actual names
        named_channels = {}
        if channel_names:
            for i, ch in enumerate(channels):
                if i < len(channel_names):
                    named_channels[ch] = channel_names[i]
                else:
                    named_channels[ch] = f"CH{ch+1}"
        
        return {
            "eeg_channels": channels,
            "channel_names": channel_names[:len(channels)] if channel_names else [],
            "channels_map": named_channels
        }
        
    async def _handle_get_channel_data(self, channel_index: int, max_samples: Optional[int] = None):
        """Handle get_channel_data endpoint."""
        data, timestamps = EEGDataAPI.get_channel_data(channel_index)
        
        # Apply max_samples limit if provided
        if max_samples and data.size > 0:
            data = data[-max_samples:]
            timestamps = timestamps[-max_samples:]
            
        # Convert to list for JSON serialization
        if hasattr(data, 'tolist'):
            data = data.tolist()
            
        return {
            "channel_index": channel_index,
            "data": data,
            "timestamps": timestamps
        }
        
    async def _handle_get_channel_by_name(self, channel_name: str, max_samples: Optional[int] = None):
        """Handle get_channel_by_name endpoint."""
        data, timestamps = EEGDataAPI.get_channel_by_name(channel_name)
        
        # Apply max_samples limit if provided
        if max_samples and data.size > 0:
            data = data[-max_samples:]
            timestamps = timestamps[-max_samples:]
            
        # Convert to list for JSON serialization
        if hasattr(data, 'tolist'):
            data = data.tolist()
            
        return {
            "channel_name": channel_name,
            "data": data,
            "timestamps": timestamps
        }
        
    async def _handle_get_signal_quality(self, channel_index: int):
        """Handle get_signal_quality endpoint."""
        # Try to import the SignalProcessor
        try:
            from .processors.signal_processor import SignalProcessor
            
            # Get required data
            data, _ = EEGDataAPI.get_current_data()
            sampling_rate = self._get_sampling_rate_direct()
            
            # Instantiate processor and get quality
            processor = SignalProcessor(sampling_rate)
            quality = processor.get_signal_quality(data, channel_index)
            
            return {
                "channel_index": channel_index,
                "quality": quality
            }
        except Exception as e:
            logger.error(f"Error calculating signal quality: {e}")
            return {
                "channel_index": channel_index,
                "quality": 0,
                "error": str(e)
            }
            
    async def _handle_get_all_channels_quality(self):
        """Handle get_all_channels_quality endpoint."""
        try:
            from .processors.signal_processor import SignalProcessor
            
            # Get required data
            data, _ = EEGDataAPI.get_current_data()
            
            # Check if we have valid data
            if data.size == 0:
                return {
                    "error": "No data available for quality calculation",
                    "quality_by_index": {}
                }
            
            # Get sampling rate and EEG channels
            sampling_rate = self._get_sampling_rate_direct()
            if sampling_rate == 0:
                sampling_rate = 250  # Default fallback sampling rate
                
            eeg_channels = self._get_eeg_channels_direct()
            if not eeg_channels:
                # Fallback: use all channels or first 8
                eeg_channels = list(range(min(8, data.shape[0])))
            
            # Get channel names
            channel_names = EEGDataAPI.get_channel_names()
            
            # Instantiate processor
            processor = SignalProcessor(sampling_rate)
            
            # Get quality for all channels
            quality_by_index = {}
            for ch in eeg_channels:
                try:
                    # Ensure channel index is valid
                    if ch < data.shape[0]:
                        quality = processor.get_signal_quality(data, ch)
                        quality_by_index[ch] = quality
                    else:
                        logger.warning(f"Channel index {ch} out of bounds for data shape {data.shape}")
                        quality_by_index[ch] = 0.0
                except Exception as e:
                    logger.error(f"Error calculating quality for channel {ch}: {e}")
                    quality_by_index[ch] = 0.0
                    
            # Add channel names if available
            quality_by_name = {}
            if channel_names:
                for i, ch in enumerate(eeg_channels):
                    if i < len(channel_names):
                        channel_name = channel_names[i]
                        quality_by_name[channel_name] = quality_by_index.get(ch, 0.0)
        
            result = {"quality_by_index": quality_by_index}
            if quality_by_name:
                result["quality_by_name"] = quality_by_name
                
            return result
    
        except Exception as e:
            logger.error(f"Error calculating all channel quality: {e}")
            return {
                "error": str(e),
                "quality_by_index": {}
            }
        
    async def _handle_register_data_callback(self):
        """Handle register_data_callback endpoint."""
        # This is just a placeholder for the WebSocket connection
        return {"status": "Use WebSocket connection for real-time updates"}
        
    # --- Data callback handling ---
    
    def _handle_data_callback(self, data, timestamps):
        """Handle incoming data for WebSocket broadcasting."""
        if not self.explorer:
            return
            
        try:
            # Get metadata for channel information
            metadata = self.data_service.get_metadata()
            board_info = self._get_board_info_direct()
            
            # Get all types of channels
            eeg_channels = self._get_eeg_channels_direct()
            
            # Get additional channel types if available
            channel_types = {}
            for channel_type in ['eeg', 'emg', 'ecg', 'accel', 'gyro', 'eda', 'ppg', 'temperature']:
                if f"{channel_type}_channels" in board_info:
                    channel_types[channel_type] = board_info[f"{channel_type}_channels"]
            
            # If no channel types found, default to EEG only
            if not channel_types:
                channel_types = {'eeg': eeg_channels}
            
            # Determine how many samples to send (not too many to keep WebSocket efficient)
            samples_to_send = min(20, data.shape[1]) if data.size > 0 else 0
            
            if data.size > 0 and samples_to_send > 0:
                # Prepare visualization data - both raw values and time series
                viz_data = {
                    "list_view": [],  # For raw list visualization
                    "chart_data": {},  # For chart visualization
                    "timestamps": [] 
                }
                
                # Get the last N timestamps (convert to relative time if needed)
                ts_slice = timestamps[-samples_to_send:]
                # Convert timestamps to relative time (milliseconds since start)
                if ts_slice:
                    base_time = ts_slice[0]
                    rel_timestamps = [int(ts - base_time) for ts in ts_slice]
                    viz_data["timestamps"] = rel_timestamps
                
                # Process each channel type
                for ch_type, channels in channel_types.items():
                    # Skip if no channels of this type
                    if not channels:
                        continue
                        
                    # Get channel names if available
                    channel_names = []
                    if ch_type == 'eeg' and metadata.get('channel_names'):
                        channel_names = metadata.get('channel_names')
                    else:
                        # Generate generic names
                        channel_names = [f"{ch_type.upper()}_{i}" for i in range(len(channels))]
                    
                    # Slice to ensure we have valid names
                    channel_names = channel_names[:len(channels)]
                    
                    # Add data for each channel
                    chart_data_by_type = {}
                    
                    for i, ch_idx in enumerate(channels):
                        if ch_idx < data.shape[0]:
                            # Get name for this channel
                            ch_name = channel_names[i] if i < len(channel_names) else f"{ch_type}_{ch_idx}"
                            
                            # Get the last N samples for this channel
                            channel_data = data[ch_idx, -samples_to_send:].tolist()
                            
                            # Add to list view (last value only)
                            if channel_data:
                                viz_data["list_view"].append({
                                    "channel": ch_name,
                                    "type": ch_type,
                                    "value": channel_data[-1],
                                    "values": channel_data[-5:],  # Last 5 values for brief history
                                    "index": ch_idx
                                })
                        
                            # Add to chart data
                            chart_data_by_type[ch_name] = channel_data
                
                # Add chart data for this type
                if chart_data_by_type:
                    viz_data["chart_data"][ch_type] = chart_data_by_type
            
            # Create payload with both visualization options
            payload = {
                "event_type": "eeg_data_update",
                "timestamp": time.time(),
                "sampling_rate": self._get_sampling_rate_direct(),
                "visualization_data": viz_data,
                "samples_count": samples_to_send,
                "visualization_modes": ["list", "chart"],
                "channel_types": list(channel_types.keys()),
                "metadata": {
                    "board_name": board_info.get("board_name", "Unknown"),
                    "channel_count": data.shape[0] if data.size > 0 else 0,
                    "eeg_channels_count": len(eeg_channels)
                }
            }
            
            # Broadcast through WebSocket
            self._broadcast_event(payload)
        except Exception as e:
            logger.error(f"Error in data callback: {e}")
    
    def _broadcast_event(self, payload):
        """Broadcast event through WebSocket."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        async def _broadcast():
            try:
                await self.explorer.broadcast_event(self.module_id, payload)
            except Exception as e:
                logger.error(f"Error broadcasting event: {e}")
                
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(_broadcast(), loop)
        else:
            loop.run_until_complete(_broadcast())
            

def get_api_integration():
    """Get the API integration singleton instance."""
    return EEGProcessorApiIntegration.get_instance()

def initialize_api(enable: bool = True, host: str = "127.0.0.1", port: int = 8000) -> bool:
    """Initialize the EEG Processor API."""
    if not enable:
        return False
        
    try:
        integration = get_api_integration()
        success = integration.register_api(host=host, port=port)
        return success
    except Exception as e:
        logger.error(f"Error initializing API: {e}")
        return False
