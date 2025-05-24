"""
Interaction API integration for the EEG processor.

This module integrates the EEG processor's interaction API with the API Explorer,
registering its methods and handling API requests.
"""

import asyncio
import logging
import os
import sys
import time
from typing import Optional, Dict, List, Any, Callable, Union

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path if needed
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Try to import the API Explorer
try:
    from api_explorer import ApiExplorer
    explorer_available = True
except ImportError:
    explorer_available = False
    logger.warning("API Explorer not found. Web API will not be available.")

# Import the EEGProcessorAPI
from .interaction_api import EEGProcessorAPI

# Import core event system
from .core.event_system import EventType, subscribe, unsubscribe

class InteractionApiIntegration:
    """
    Integrates the EEG processor's interaction API with the API Explorer.
    
    This class exposes the EEG processor's interaction API methods through the API Explorer.
    """
    
    def __init__(self):
        """Initialize the API integration."""
        self.explorer = None
        self.module_id = "eeg_processor_control"
        self.is_registered = False
        
        # For storing method groups and methods when fallback is used
        self.fallback_method_groups = {}
        self.fallback_methods = {}
        
        # Module registration status flag
        self.module_registered = False
        
        # For tracking event subscriptions
        self._event_subscriptions = []
    
    def register_api(self, start_server: bool = True, host: str = "127.0.0.1", 
                     port: int = 8001) -> bool:
        """
        Register the EEG processor's interaction API with the Explorer.
        
        Args:
            start_server: Whether to start the API Explorer server
            host: Host to bind the server to
            port: Port to bind the server to
            
        Returns:
            True if registration was successful, False otherwise
        """
        if not explorer_available:
            return False
        
        try:
            # Get the ApiExplorer instance
            self.explorer = ApiExplorer.get_instance()
            
            # Register module
            if not self._register_module():
                return False
            
            # Register methods
            self._register_all_methods()
            
            # Setup websocket events
            self._setup_websocket_events()
            
            # Start server
            if start_server and hasattr(self.explorer, 'start_server') and not self.explorer.is_running:
                self.explorer.start_server(host=host, port=port, block=False)
            
            self.is_registered = True
            return True
        except Exception as e:
            logger.error(f"Error registering interaction API: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _setup_websocket_events(self):
        """Set up event handlers for websocket real-time events."""
        # Subscribe to core events for websocket forwarding
        self._subscribe_to_core_events()

    def _subscribe_to_core_events(self):
        """Subscribe to core events from event system."""
        # Subscribe to all event types
        for event_type in EventType:
            # Create a handler for this event type
            handler = lambda data, event_type=event_type: self._handle_core_event(event_type, data)
            
            # Subscribe to the event
            subscribe(event_type, handler)
            
            # Store subscription for cleanup
            self._event_subscriptions.append((event_type, handler))
            
        logger.info("Subscribed to core events for real-time forwarding")

    def _handle_core_event(self, event_type: EventType, data: Any):
        """
        Handle events from the core event system.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        try:
            # Skip EEG_DATA events to avoid overwhelming the websocket
            if event_type == EventType.EEG_DATA:
                return
                
            # Create a standard event payload
            event_payload = {
                "type": event_type.name,
                "data": self._event_to_dict(data) if hasattr(data, '__dict__') else data,
                "timestamp": time.time()
            }
            
            # Add specific fields based on event type
            if isinstance(data, dict) and "timestamp" in data:
                event_payload["timestamp"] = data["timestamp"]
            
            # Broadcast the event
            self._broadcast_event(event_payload)
        except Exception as e:
            logger.error(f"Error handling core event: {e}")
            import traceback
            traceback.print_exc()

    def _event_to_dict(self, event: Any) -> Dict:
        """Convert an event object to a serializable dictionary."""
        # Check if it's an object with to_dict method
        if hasattr(event, 'to_dict') and callable(getattr(event, 'to_dict')):
            return event.to_dict()
            
        # For other objects, use generic approach
        try:
            # Try to convert to dict if possible
            if hasattr(event, '__dict__'):
                return {k: v for k, v in event.__dict__.items() 
                        if not k.startswith("_") and v is not None}
            elif isinstance(event, dict):
                return event
            else:
                # Convert to string if we can't do anything else
                return {"value": str(event)}
        except:
            # Last resort - convert to string
            return {"value": str(event)}

    def _broadcast_event(self, event_dict: Dict) -> None:
        """Broadcast an event through the WebSocket connection."""
        if not hasattr(self.explorer, 'broadcast_event'):
            logger.warning("ApiExplorer does not have broadcast_event method, event not sent")
            return
            
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Create broadcast coroutine
        async def broadcast():
            try:
                # Add JSON serialization check
                import json
                try:
                    # Test serialization before sending
                    json.dumps(event_dict)
                except TypeError as e:
                    # Something isn't serializable - fix problematic fields
                    logger.warning(f"Event not fully serializable: {e}. Converting problematic fields.")
                    event_dict_copy = event_dict.copy()
                    for key, value in event_dict_copy.items():
                        try:
                            json.dumps({key: value})
                        except:
                            # Convert problematic value to string
                            event_dict[key] = str(value)
                
                await self.explorer.broadcast_event(self.module_id, event_dict)
            except Exception as e:
                logger.error(f"Error in broadcast_event: {e}")
                import traceback
                traceback.print_exc()
        
        # Run the broadcast
        try:
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(broadcast(), loop)
            else:
                loop.run_until_complete(broadcast())
        except Exception as e:
            logger.error(f"Error in event loop: {e}")

    def _register_module(self) -> bool:
        """Register the EEG processor control module."""
        try:
            if hasattr(self.explorer, 'register_module'):
                self.explorer.register_module(
                    module_id=self.module_id,
                    name="EEG Processor Control",
                    description="API for controlling the EEG processor application"
                )
                logger.info(f"Module '{self.module_id}' registered with API Explorer")
                self.module_registered = True
            else:
                self._register_module_fallback()
            return self.module_registered
        except Exception as e:
            logger.error(f"Error registering module: {e}")
            return False
    
    def _register_module_fallback(self) -> bool:
        """Register module using fallback mechanism if standard method isn't available."""
        logger.warning("Using fallback module registration")
        try:
            # Create modules dict if it doesn't exist
            if not hasattr(self.explorer, 'modules'):
                setattr(self.explorer, 'modules', {})
            
            # Create a router for this module
            router = None
            try:
                from fastapi import APIRouter
                router = APIRouter(prefix=f"/api/{self.module_id}", tags=["EEG Processor Control"])
                
                # If explorer has an app attribute, add the router directly
                if hasattr(self.explorer, 'app'):
                    self.explorer.app.include_router(router)
            except Exception as e:
                logger.error(f"Error creating router: {e}")
            
            # Register module in the modules dict
            self.explorer.modules[self.module_id] = {
                'name': "EEG Processor Control",
                'description': "API for controlling the EEG processor application",
                'method_groups': {},
                'router': router
            }
            
            logger.info(f"Module '{self.module_id}' registered using fallback mechanism")
            self.module_registered = True
            return True
        except Exception as e:
            logger.error(f"Error in fallback module registration: {e}")
            return False
    
    def _register_all_methods(self) -> None:
        """Register all method groups and their methods."""
        if not self.module_registered:
            logger.error("Cannot register methods - module not registered")
            return
        
        # Register method groups
        self._register_method_groups()
        
        # Register all methods within groups
        self._register_board_methods()
        self._register_streaming_methods()
        self._register_recording_methods()
        self._register_processing_methods()
        self._register_visualization_methods()
        self._register_state_methods()
    
    def _register_method_groups(self) -> None:
        """Register method groups for the EEG processor."""
        if not self.module_registered:
            logger.error("Cannot register method groups - module not registered")
            return
            
        groups = [
            ("board", "Board Connection"),
            ("streaming", "Streaming Control"),
            ("recording", "Recording Control"),
            ("processing", "Signal Processing"),
            ("visualization", "Visualization Control"),
            ("state", "Application State")
        ]
        
        for group_id, group_name in groups:
            self._add_method_group(self.module_id, group_id, group_name)
    
    def _add_method_group(self, module_id: str, group_id: str, name: str) -> bool:
        """Add a method group with fallback support."""
        # First verify the module exists
        if not self.module_registered:
            logger.error(f"Cannot add method group {group_id} - module {module_id} not registered")
            return False
            
        if hasattr(self.explorer, 'add_method_group'):
            try:
                self.explorer.add_method_group(module_id, group_id, name)
                return True
            except Exception as e:
                logger.error(f"Error adding method group: {e}")
                # Fall through to fallback implementation
        
        # Fallback implementation
        return self._add_method_group_fallback(module_id, group_id, name)
    
    def _add_method_group_fallback(self, module_id: str, group_id: str, name: str) -> bool:
        """Add a method group using fallback mechanism."""
        logger.warning(f"Using fallback method for adding group {group_id}")
        
        # Check if modules attribute exists
        if hasattr(self.explorer, 'modules'):
            # Check if our module exists
            if module_id in self.explorer.modules:
                # Check if method_groups dict exists
                if 'method_groups' not in self.explorer.modules[module_id]:
                    self.explorer.modules[module_id]['method_groups'] = {}
                
                # Add the method group
                self.explorer.modules[module_id]['method_groups'][group_id] = {
                    'name': name,
                    'methods': {}
                }
                
                logger.info(f"Created method group {group_id} in {module_id} using fallback")
                return True
            else:
                logger.error(f"Module {module_id} not found in ApiExplorer modules")
                return False
        else:
            # Storage in local fallback structure
            if module_id not in self.fallback_method_groups:
                self.fallback_method_groups[module_id] = {}
            
            self.fallback_method_groups[module_id][group_id] = {
                'name': name,
                'methods': {}
            }
            
            logger.info(f"Created method group {group_id} in local fallback storage")
            return True
    
    def _register_method(self, module_id: str, group_id: str, method_id: str, 
                         method_info: Dict, handler_function: Callable) -> None:
        """Register a method with fallback support."""
        if hasattr(self.explorer, 'register_method'):
            try:
                self.explorer.register_method(
                    module_id, group_id, method_id, method_info, handler_function
                )
                return
            except Exception as e:
                logger.error(f"Error registering method {method_id}: {e}")
                # Fall through to fallback
        
        # Use fallback registration
        self._register_method_fallback(module_id, group_id, method_id, method_info, handler_function)
    
    def _register_method_fallback(self, module_id: str, group_id: str, method_id: str, 
                                 method_info: Dict, handler_function: Callable) -> None:
        """Register a method using fallback mechanism."""
        # Store in fallback structures
        if module_id not in self.fallback_methods:
            self.fallback_methods[module_id] = {}
        
        if group_id not in self.fallback_methods[module_id]:
            self.fallback_methods[module_id][group_id] = {}
        
        self.fallback_methods[module_id][group_id][method_id] = {
            'info': method_info,
            'handler': handler_function
        }
        
        # Add to group for UI display
        if module_id in self.fallback_method_groups and group_id in self.fallback_method_groups[module_id]:
            self.fallback_method_groups[module_id][group_id]['methods'][method_id] = method_info
            
        logger.info(f"Registered method {method_id} in {module_id}/{group_id} using fallback")
        
        # Create fallback endpoint if explorer has routing capability
        if hasattr(self.explorer, 'app'):
            self._create_fallback_endpoint(module_id, method_id, method_info, handler_function)
    
    def _create_fallback_endpoint(self, module_id: str, method_id: str, 
                                 method_info: Dict, handler_function: Callable) -> None:
        """Create a fallback endpoint directly in the FastAPI app."""
        try:
            # Get the path for this method
            path = f"/api/{module_id}/{method_id}"
            
            # Determine if GET or POST
            method_type = method_info.get('type', 'GET').upper()
            
            # Create async wrapper
            async def endpoint_wrapper(*args, **kwargs):
                result = await handler_function(*args, **kwargs)
                return result
            
            # Add route directly to app
            self.explorer.app.add_api_route(
                path,
                endpoint_wrapper,
                methods=[method_type],
                response_model=None,
                tags=["EEG Processor Control"]
            )
            
            logger.info(f"Added fallback route for {method_id} at {path}")
        except Exception as e:
            logger.error(f"Failed to add fallback route for {method_id}: {e}")
    
    def shutdown(self) -> None:
        """Clean up resources when shutting down."""
        # Unsubscribe from core events
        for event_type, handler in self._event_subscriptions:
            unsubscribe(event_type, handler)
        
        logger.info("API integration shut down")
    
    #
    # Method registration for different API groups
    #
    
    def _register_board_methods(self) -> None:
        """Register board connection methods."""
        # connect_board method
        self._register_method(
            module_id=self.module_id,
            group_id="board",
            method_id="connect_board",
            method_info={
                "name": "connect_board(board_id, params, preset)",
                "description": "Connect to an EEG board.",
                "type": "POST",
                "params": {
                    "board_id": {
                        "type": "number",
                        "description": "ID of the board to connect to",
                        "required": True
                    },
                    "params": {
                        "type": "object",
                        "description": "Connection parameters",
                        "required": True
                    },
                    "preset": {
                        "type": "number",
                        "description": "Data preset to use",
                        "required": True
                    }
                }
            },
            handler_function=self._handle_connect_board
        )
        
        # disconnect_board method
        self._register_method(
            module_id=self.module_id,
            group_id="board",
            method_id="disconnect_board",
            method_info={
                "name": "disconnect_board()",
                "description": "Disconnect from the current EEG board.",
                "type": "POST",
                "params": {}
            },
            handler_function=self._handle_disconnect_board
        )
        
        # is_connected method
        self._register_method(
            module_id=self.module_id,
            group_id="board",
            method_id="is_connected",
            method_info={
                "name": "is_connected()",
                "description": "Check if connected to a board.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_is_connected
        )
        
        # get_board_info method
        self._register_method(
            module_id=self.module_id,
            group_id="board",
            method_id="get_board_info",
            method_info={
                "name": "get_board_info()",
                "description": "Get information about the connected board.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_get_board_info
        )
    
    def _register_streaming_methods(self) -> None:
        """Register streaming control methods."""
        # start_stream method
        self._register_method(
            module_id=self.module_id,
            group_id="streaming",
            method_id="start_stream",
            method_info={
                "name": "start_stream()",
                "description": "Start streaming data from the board.",
                "type": "POST",
                "params": {}
            },
            handler_function=self._handle_start_stream
        )
        
        # stop_stream method
        self._register_method(
            module_id=self.module_id,
            group_id="streaming",
            method_id="stop_stream",
            method_info={
                "name": "stop_stream()",
                "description": "Stop streaming data from the board.",
                "type": "POST",
                "params": {}
            },
            handler_function=self._handle_stop_stream
        )
        
        # is_streaming method
        self._register_method(
            module_id=self.module_id,
            group_id="streaming",
            method_id="is_streaming",
            method_info={
                "name": "is_streaming()",
                "description": "Check if streaming is active.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_is_streaming
        )
    
    def _register_recording_methods(self) -> None:
        """Register recording control methods."""
        # start_recording method
        self._register_method(
            module_id=self.module_id,
            group_id="recording",
            method_id="start_recording",
            method_info={
                "name": "start_recording(filename, data_type)",
                "description": "Start recording data to file.",
                "type": "POST",
                "params": {
                    "filename": {
                        "type": "text",
                        "description": "Path to save the recording",
                        "required": True
                    },
                    "data_type": {
                        "type": "select",
                        "description": "Type of data to record",
                        "options": ["raw", "processed", "both"],
                        "required": False,
                        "default": "raw"
                    }
                }
            },
            handler_function=self._handle_start_recording
        )
        
        # stop_recording method
        self._register_method(
            module_id=self.module_id,
            group_id="recording",
            method_id="stop_recording",
            method_info={
                "name": "stop_recording()",
                "description": "Stop recording and save data to file.",
                "type": "POST",
                "params": {}
            },
            handler_function=self._handle_stop_recording
        )
        
        # is_recording method
        self._register_method(
            module_id=self.module_id,
            group_id="recording",
            method_id="is_recording",
            method_info={
                "name": "is_recording()",
                "description": "Check if recording is active.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_is_recording
        )
        
        # add_marker method
        self._register_method(
            module_id=self.module_id,
            group_id="recording",
            method_id="add_marker",
            method_info={
                "name": "add_marker(marker_value)",
                "description": "Add a marker to the data stream.",
                "type": "POST",
                "params": {
                    "marker_value": {
                        "type": "number",
                        "description": "Marker value to add",
                        "required": True
                    }
                }
            },
            handler_function=self._handle_add_marker
        )
    
    def _register_processing_methods(self) -> None:
        """Register signal processing methods."""
        # apply_filters method
        self._register_method(
            module_id=self.module_id,
            group_id="processing",
            method_id="apply_filters",
            method_info={
                "name": "apply_filters(bandpass, bandpass_low, bandpass_high, notch, notch_freq, detrend)",
                "description": "Apply filters to the EEG data visualization.",
                "type": "POST",
                "params": {
                    "bandpass": {
                        "type": "select",
                        "description": "Whether to apply bandpass filter",
                        "options": [True, False],
                        "required": False,
                        "default": True
                    },
                    "bandpass_low": {
                        "type": "number",
                        "description": "Low cutoff frequency for bandpass filter",
                        "required": False,
                        "default": 1.0
                    },
                    "bandpass_high": {
                        "type": "number",
                        "description": "High cutoff frequency for bandpass filter",
                        "required": False,
                        "default": 50.0
                    },
                    "notch": {
                        "type": "select",
                        "description": "Whether to apply notch filter",
                        "options": [True, False],
                        "required": False,
                        "default": True
                    },
                    "notch_freq": {
                        "type": "select",
                        "description": "Frequency for notch filter",
                        "options": [50.0, 60.0],
                        "required": False,
                        "default": 50.0
                    },
                    "detrend": {
                        "type": "select",
                        "description": "Whether to apply detrending",
                        "options": [True, False],
                        "required": False,
                        "default": True
                    }
                }
            },
            handler_function=self._handle_apply_filters
        )
        
        # remove_filters method
        self._register_method(
            module_id=self.module_id,
            group_id="processing",
            method_id="remove_filters",
            method_info={
                "name": "remove_filters()",
                "description": "Remove all filters from the EEG data visualization.",
                "type": "POST",
                "params": {}
            },
            handler_function=self._handle_remove_filters
        )
        
        # calculate_eeg_metrics method
        self._register_method(
            module_id=self.module_id,
            group_id="processing",
            method_id="calculate_eeg_metrics",
            method_info={
                "name": "calculate_eeg_metrics()",
                "description": "Calculate EEG metrics from current data.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_calculate_eeg_metrics
        )
        
        # show_brain_map method
        self._register_method(
            module_id=self.module_id,
            group_id="processing",
            method_id="show_brain_map",
            method_info={
                "name": "show_brain_map()",
                "description": "Show brain map visualization.",
                "type": "POST",
                "params": {}
            },
            handler_function=self._handle_show_brain_map
        )
    
    def _register_visualization_methods(self) -> None:
        """Register visualization control methods."""
        # show_eeg_visualization method
        self._register_method(
            module_id=self.module_id,
            group_id="visualization",
            method_id="show_eeg_visualization",
            method_info={
                "name": "show_eeg_visualization()",
                "description": "Show EEG visualization window.",
                "type": "POST",
                "params": {}
            },
            handler_function=self._handle_show_eeg_visualization
        )
    
    def _register_state_methods(self) -> None:
        """Register application state methods."""
        # get_application_state method
        self._register_method(
            module_id=self.module_id,
            group_id="state",
            method_id="get_application_state",
            method_info={
                "name": "get_application_state()",
                "description": "Get comprehensive application state.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_get_application_state
        )
        
        # register_event_callback method
        self._register_method(
            module_id=self.module_id,
            group_id="state",
            method_id="register_event_callback",
            method_info={
                "name": "register_event_callback()",
                "description": "Register for real-time events via WebSocket.",
                "type": "POST",
                "params": {}
            },
            handler_function=self._handle_register_event_callback
        )
    
    #
    # API endpoint handlers
    #
    
    async def _handle_connect_board(self, board_id: int, params: Dict[str, Any], preset: int):
        """Handle connect_board API request."""
        try:
            success = EEGProcessorAPI.connect_board(board_id, params, preset)
            return {"success": success, "status": EEGProcessorAPI.get_last_operation_status()}
        except Exception as e:
            logger.error(f"Error in connect_board endpoint: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}
    
    async def _handle_disconnect_board(self):
        """Handle disconnect_board API request."""
        try:
            success = EEGProcessorAPI.disconnect_board()
            return {"success": success, "status": EEGProcessorAPI.get_last_operation_status()}
        except Exception as e:
            logger.error(f"Error in disconnect_board endpoint: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}
    
    async def _handle_is_connected(self):
        """Handle is_connected API request."""
        try:
            connected = EEGProcessorAPI.is_connected()
            return {"connected": connected}
        except Exception as e:
            logger.error(f"Error in is_connected endpoint: {e}")
            return {"connected": False, "error": str(e)}
    
    async def _handle_get_board_info(self):
        """Handle get_board_info API request."""
        try:
            return EEGProcessorAPI.get_board_info()
        except Exception as e:
            logger.error(f"Error in get_board_info endpoint: {e}")
            return {"error": str(e)}
    
    async def _handle_start_stream(self):
        """Handle start_stream API request."""
        try:
            success = EEGProcessorAPI.start_stream()
            return {"success": success, "status": EEGProcessorAPI.get_last_operation_status()}
        except Exception as e:
            logger.error(f"Error in start_stream endpoint: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}
    
    async def _handle_stop_stream(self):
        """Handle stop_stream API request."""
        try:
            success = EEGProcessorAPI.stop_stream()
            return {"success": success, "status": EEGProcessorAPI.get_last_operation_status()}
        except Exception as e:
            logger.error(f"Error in stop_stream endpoint: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}
    
    async def _handle_is_streaming(self):
        """Handle is_streaming API request."""
        try:
            streaming = EEGProcessorAPI.is_streaming()
            return {"streaming": streaming}
        except Exception as e:
            logger.error(f"Error in is_streaming endpoint: {e}")
            return {"streaming": False, "error": str(e)}
    
    async def _handle_start_recording(self, filename: str, data_type: str = "raw"):
        """Handle start_recording API request."""
        try:
            success = EEGProcessorAPI.start_recording(filename, data_type)
            return {"success": success, "status": EEGProcessorAPI.get_last_operation_status()}
        except Exception as e:
            logger.error(f"Error in start_recording endpoint: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}
    
    async def _handle_stop_recording(self):
        """Handle stop_recording API request."""
        try:
            success = EEGProcessorAPI.stop_recording()
            return {"success": success, "status": EEGProcessorAPI.get_last_operation_status()}
        except Exception as e:
            logger.error(f"Error in stop_recording endpoint: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}
    
    async def _handle_is_recording(self):
        """Handle is_recording API request."""
        try:
            recording = EEGProcessorAPI.is_recording()
            return {"recording": recording}
        except Exception as e:
            logger.error(f"Error in is_recording endpoint: {e}")
            return {"recording": False, "error": str(e)}
    
    async def _handle_add_marker(self, marker_value: int):
        """Handle add_marker API request."""
        try:
            success = EEGProcessorAPI.add_marker(marker_value)
            return {"success": success, "status": EEGProcessorAPI.get_last_operation_status()}
        except Exception as e:
            logger.error(f"Error in add_marker endpoint: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}
    
    async def _handle_apply_filters(self, bandpass: bool = True, bandpass_low: float = 1.0, 
                                  bandpass_high: float = 50.0, notch: bool = True, 
                                  notch_freq: float = 50.0, detrend: bool = True):
        """Handle apply_filters API request."""
        try:
            success = EEGProcessorAPI.apply_filters(
                bandpass, bandpass_low, bandpass_high, notch, notch_freq, detrend
            )
            return {"success": success, "status": EEGProcessorAPI.get_last_operation_status()}
        except Exception as e:
            logger.error(f"Error in apply_filters endpoint: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}
    
    async def _handle_remove_filters(self):
        """Handle remove_filters API request."""
        try:
            success = EEGProcessorAPI.remove_filters()
            return {"success": success, "status": EEGProcessorAPI.get_last_operation_status()}
        except Exception as e:
            logger.error(f"Error in remove_filters endpoint: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}
    
    async def _handle_calculate_eeg_metrics(self):
        """Handle calculate_eeg_metrics API request."""
        try:
            metrics = EEGProcessorAPI.calculate_eeg_metrics()
            return metrics
        except Exception as e:
            logger.error(f"Error in calculate_eeg_metrics endpoint: {e}")
            return {"error": str(e)}
    
    async def _handle_show_brain_map(self):
        """Handle show_brain_map API request."""
        try:
            success = EEGProcessorAPI.show_brain_map()
            return {"success": success, "status": EEGProcessorAPI.get_last_operation_status()}
        except Exception as e:
            logger.error(f"Error in show_brain_map endpoint: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}
    
    async def _handle_show_eeg_visualization(self):
        """Handle show_eeg_visualization API request."""
        try:
            success = EEGProcessorAPI.show_eeg_visualization()
            return {"success": success, "status": EEGProcessorAPI.get_last_operation_status()}
        except Exception as e:
            logger.error(f"Error in show_eeg_visualization endpoint: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}
    
    async def _handle_get_application_state(self):
        """Handle get_application_state API request."""
        try:
            return EEGProcessorAPI.get_application_state()
        except Exception as e:
            logger.error(f"Error in get_application_state endpoint: {e}")
            return {"error": str(e)}
    
    async def _handle_register_event_callback(self):
        """Handle register_event_callback API request."""
        # This is just a placeholder for the WebSocket connection
        return {"status": "Use WebSocket connection for real-time updates"}

# Module-level functions for easier access

# Create a singleton instance
_interaction_api_integration = None

def get_interaction_api_integration():
    """Get or create the interaction API integration instance."""
    global _interaction_api_integration
    if _interaction_api_integration is None:
        _interaction_api_integration = InteractionApiIntegration()
    return _interaction_api_integration

def initialize_interaction_api(enable_web_api: bool = True, host: str = "127.0.0.1", port: int = 8001) -> bool:
    """
    Initialize the interaction web API for the EEG processor.
    
    Args:
        enable_web_api: Whether to enable the web API
        host: Host to bind the server to
        port: Port to bind the server to (defaults to 8001 to avoid conflict with data access API)
        
    Returns:
        True if initialization was successful, False otherwise
    """
    if not enable_web_api:
        return False
        
    if not explorer_available:
        logger.warning("API Explorer not available. Web API will not be enabled.")
        return False
    
    integration = get_interaction_api_integration()
    success = integration.register_api(start_server=True, host=host, port=port)
    
    if success:
        logger.info(f"Interaction API initialized at http://{host}:{port}")
    
    return success