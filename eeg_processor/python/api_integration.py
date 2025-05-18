import os
import sys
import socket
import asyncio
import logging
import numpy as np
import importlib
from typing import Dict, List, Any, Optional, Tuple

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
        
        # Register module
        self.explorer.register_module(
            module_id=self.module_id,
            name="EEG Processor",
            description="Real-time access to EEG data streams and device information"
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
        
        # Register data callback
        self.callback_id = EEGDataAPI.register_data_callback(self._handle_data_callback)
        
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
        collector = self._get_active_collector()
        if collector and hasattr(collector, 'eeg_channels'):
            return collector.eeg_channels
            
        # Alternative method: try BrainFlow directly
        try:
            from brainflow.board_shim import BoardShim
            board_id, preset = self._get_board_id_and_preset()
            if board_id is not None and preset is not None:
                return BoardShim.get_eeg_channels(board_id, preset)
        except Exception as e:
            logger.debug(f"Error getting EEG channels from BrainFlow: {e}")
            
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
        """Get board info directly from collector."""
        collector = self._get_active_collector()
        if collector and hasattr(collector, 'get_device_info'):
            return collector.get_device_info()
        elif collector and hasattr(collector, 'get_board_info'):
            return collector.get_board_info()
            
        # Basic fallback info
        board_id, preset = self._get_board_id_and_preset()
        sampling_rate = self._get_sampling_rate_direct()
        eeg_channels = self._get_eeg_channels_direct()
        
        return {
            "board_id": board_id,
            "preset": preset,
            "sampling_rate": sampling_rate,
            "eeg_channels": eeg_channels
        }
    
    # --- Handler methods for API endpoints ---
    
    async def _handle_is_streaming(self):
        """Handle is_streaming endpoint."""
        is_streaming = EEGDataAPI.is_streaming()
        
        # If API reports not streaming but we have a collector that is streaming
        if not is_streaming:
            collector = self._get_active_collector()
            if collector and hasattr(collector, 'is_streaming'):
                is_streaming = collector.is_streaming
                
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
        return self._get_board_info_direct()
        
    async def _handle_get_preset(self):
        """Handle get_preset endpoint."""
        board_id, preset = self._get_board_id_and_preset()
        return {"preset": preset}
        
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
            eeg_channels = self._get_eeg_channels_direct()
            if eeg_channels:
                # Filter to keep only EEG channels
                eeg_data = data[eeg_channels]
                
                # Apply max_samples limit if provided
                if max_samples:
                    eeg_data = eeg_data[:, -max_samples:]
                    timestamps = timestamps[-max_samples:]
                    
                # Convert to list for JSON serialization
                if hasattr(eeg_data, 'tolist'):
                    eeg_data = eeg_data.tolist()
                    
                return {
                    "data": eeg_data,
                    "timestamps": timestamps,
                    "eeg_channels": eeg_channels,
                    "channel_names": self._get_channel_names_direct()
                }
                
        # If we couldn't extract EEG data
        return {
            "data": [],
            "timestamps": [],
            "eeg_channels": self._get_eeg_channels_direct(),
            "channel_names": self._get_channel_names_direct()
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
        return {"eeg_channels": channels}
        
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
            sampling_rate = self._get_sampling_rate_direct()
            eeg_channels = self._get_eeg_channels_direct()
            
            # Instantiate processor
            processor = SignalProcessor(sampling_rate)
            
            # Get quality for all channels
            quality_values = {}
            for ch in eeg_channels:
                try:
                    quality = processor.get_signal_quality(data, ch)
                    quality_values[ch] = quality
                except Exception as e:
                    quality_values[ch] = 0
                    
            # Add channel names if available
            channel_names = self._get_channel_names_direct()
            if channel_names and len(channel_names) >= len(eeg_channels):
                return {
                    "quality_by_index": quality_values,
                    "quality_by_name": {
                        channel_names[i]: quality_values[ch]
                        for i, ch in enumerate(eeg_channels)
                        if i < len(channel_names)
                    }
                }
                
            return {"quality_by_index": quality_values}
            
        except Exception as e:
            logger.error(f"Error calculating all channel quality: {e}")
            return {"error": str(e)}
        
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
            # Create a simplified payload with essential data
            # (Full data would be too large for efficient WebSocket transmission)
            
            # Get only EEG channels for the payload
            eeg_channels = self._get_eeg_channels_direct()
            eeg_names = self._get_channel_names_direct()
            
            # Take just a few channels and the most recent samples for efficiency
            samples_to_send = min(5, data.shape[1]) if data.size > 0 else 0
            
            if data.size > 0 and samples_to_send > 0 and len(eeg_channels) > 0:
                # Create a simplified representation
                channels_to_send = min(4, len(eeg_channels))  # Send at most 4 channels
                selected_channels = eeg_channels[:channels_to_send]
                
                # Extract data for selected channels, last few samples
                channel_data = data[selected_channels, -samples_to_send:]
                
                # Create payload with recent snapshot and metadata
                payload = {
                    "event_type": "eeg_data_update",
                    "timestamp": timestamps[-1] if timestamps else time.time(),
                    "sampling_rate": self._get_sampling_rate_direct(),
                    "channels": selected_channels[:channels_to_send],
                    "channel_names": eeg_names[:channels_to_send] if eeg_names else [],
                    "data": channel_data.tolist() if hasattr(channel_data, 'tolist') else channel_data,
                    "samples": samples_to_send,
                    "total_channels": len(eeg_channels)
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
