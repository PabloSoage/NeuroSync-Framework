"""
API integration for the input collector.

This module integrates the input collector with the API Explorer,
registering its methods and handling API requests.
"""

import asyncio
import logging
import os
import socket
import sys
from typing import Optional

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
    print("API Explorer not found. Web API will not be available.")

# Import the InputDataAPI
from .data_access_api import InputDataAPI


class InputCollectorApiIntegration:
    """
    Integrates the input collector with the API Explorer.
    
    This class exposes the input collector's API methods through the API Explorer.
    """
    
    def __init__(self):
        """Initialize the API integration."""
        self.explorer = None
        self.module_id = "input_collector"
        self.is_registered = False
        self.event_callback_id = None
        
        # For storing method groups and methods when fallback is used
        self.fallback_method_groups = {}
        self.fallback_methods = {}
        
        # Module registration status flag
        self.module_registered = False
    
    def register_api(self, start_server: bool = True, host: str = "127.0.0.1", 
                     port: int = 8000) -> bool:
        """
        Register the input collector's API with the Explorer.
        
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
            # Check if a server is already running at the specified port
            if self._is_server_running(host, port):
                print(f"Port {port} is already in use, looking for an alternative port...")
                # Try to find a different port
                for alt_port in range(port+1, port+10):
                    if not self._is_server_running(host, alt_port):
                        print(f"Using alternative port {alt_port}")
                        port = alt_port
                        break
                else:
                    print("Unable to find an available port in the range. Will try to use port", port)
            
            # Get the ApiExplorer instance
            self.explorer = ApiExplorer.get_instance()
            
            # Check if required methods exist
            self._check_explorer_methods()
            
            # Register the input collector module first
            self._register_module()
            
            # Only proceed with method groups if module registration was successful
            if self.module_registered:
                # Register method groups
                self._register_method_groups()
                
                # Register all methods
                self._register_methods()
                
                # Register for real-time events
                self._register_for_events()
                
                # Start the server if requested
                if start_server and not self.explorer.is_running:
                    if hasattr(self.explorer, 'start_server'):
                        self.explorer.start_server(host=host, port=port, block=False)
                    else:
                        logger.warning("ApiExplorer does not have start_server method")
                
                self.is_registered = True
                return True
            else:
                # Failed to register module
                return False
            
        except Exception as e:
            print(f"Error registering input collector API: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _register_module(self) -> bool:
        """Register the input collector module with proper fallback."""
        try:
            if hasattr(self.explorer, 'register_module'):
                self.explorer.register_module(
                    module_id=self.module_id,
                    name="Input Collector",
                    description="API for accessing real-time input data with minimal overhead"
                )
                logger.info(f"Module '{self.module_id}' registered with API Explorer")
                self.module_registered = True
            else:
                logger.warning("ApiExplorer does not have register_module method, using fallback")
                # Create fallback implementation
                if not hasattr(self.explorer, 'modules'):
                    # Create modules dict if it doesn't exist
                    setattr(self.explorer, 'modules', {})
                
                # Create a router for this module
                try:
                    from fastapi import APIRouter
                    router = APIRouter(prefix=f"/api/{self.module_id}", tags=["Input Collector"])
                    
                    # If explorer has an app attribute, add the router directly
                    if hasattr(self.explorer, 'app'):
                        self.explorer.app.include_router(router)
                        logger.info(f"Added router for {self.module_id} directly to app")
                except Exception as e:
                    logger.error(f"Error creating router: {e}")
                    router = None
                
                # Register module in the modules dict
                self.explorer.modules[self.module_id] = {
                    'name': "Input Collector",
                    'description': "API for accessing real-time input data with minimal overhead",
                    'method_groups': {},
                    'router': router  # Attach the router we created
                }
                
                logger.info(f"Module '{self.module_id}' registered using fallback mechanism")
                self.module_registered = True
            
            return self.module_registered
        except Exception as e:
            logger.error(f"Error registering module: {e}")
            self.module_registered = False
            return False
    
    def _check_explorer_methods(self):
        """Check if the ApiExplorer class has the required methods."""
        required_methods = [
            'register_module',
            'add_method_group',
            'register_method',
            'start_server',
            'broadcast_event'
        ]
        
        for method in required_methods:
            if not hasattr(self.explorer, method):
                logger.warning(f"ApiExplorer does not have {method} method")
    
    def _is_server_running(self, host: str, port: int) -> bool:
        """Check if a server is already running at the specified host and port."""
        try:
            # Try to connect to the server
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            
            # If the connection was successful, the server is running
            return result == 0
        except:
            return False
    
    def _register_method_groups(self) -> None:
        """Register method groups for the input collector."""
        if not self.module_registered:
            logger.error("Cannot register method groups - module not registered")
            return
            
        groups = [
            ("state_methods", "State Methods"),
            ("event_methods", "Event Methods"),
            ("controller_methods", "Controller Methods"),
            ("callback_methods", "Callback Methods")
        ]
        
        for group_id, group_name in groups:
            self._add_method_group(self.module_id, group_id, group_name)
    
    def _add_method_group(self, module_id, group_id, name):
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
                logger.warning(f"Falling back to manual method group creation")
                # Fall through to fallback implementation
        
        # Fallback implementation
        logger.warning(f"ApiExplorer does not have add_method_group method, creating fallback")
        
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
    
    def _register_method(self, module_id, group_id, method_id, method_info, handler_function):
        """Register a method with fallback support."""
        if hasattr(self.explorer, 'register_method'):
            self.explorer.register_method(
                module_id, group_id, method_id, method_info, handler_function
            )
        else:
            # Store in fallback
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
            
            # Create fallback endpoint if explorer has any routing capability
            if hasattr(self.explorer, 'app'):
                try:
                    # Try to add a route directly to the FastAPI app
                    from fastapi import APIRouter, Depends, Query, Body
                    from pydantic import create_model
                    
                    # Get the path for this method
                    path = f"/api/{module_id}/{method_id}"
                    
                    # Determine if GET or POST
                    method_type = method_info.get('type', 'GET').upper()
                    
                    # Create a simple async wrapper around the handler function
                    async def endpoint_wrapper(*args, **kwargs):
                        result = await handler_function(*args, **kwargs)
                        return result
                    
                    if method_type == 'GET':
                        # Add GET route directly to app
                        self.explorer.app.add_api_route(
                            path,
                            endpoint_wrapper,
                            methods=["GET"],
                            response_model=None,
                            tags=["Input Collector"]
                        )
                    else:
                        # Add POST route directly to app
                        self.explorer.app.add_api_route(
                            path,
                            endpoint_wrapper,
                            methods=["POST"],
                            response_model=None,
                            tags=["Input Collector"]
                        )
                    
                    logger.info(f"Added fallback route for {method_id} at {path}")
                except Exception as e:
                    logger.error(f"Failed to add fallback route for {method_id}: {e}")
                    import traceback
                    traceback.print_exc()
    
    def _register_methods(self):
        """Register all API methods for the input collector."""
        # Register state methods
        self._register_state_methods()
        
        # Register event methods
        self._register_event_methods()
        
        # Register controller methods
        self._register_controller_methods()
        
        # Register callback methods
        self._register_callback_methods()
    
    def _register_state_methods(self):
        """Register state-related API methods."""
        # get_active_keys method
        self._register_method(
            module_id=self.module_id,
            group_id="state_methods",
            method_id="get_active_keys",
            method_info={
                "name": "get_active_keys()",
                "description": "Get a list of currently active keys.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_get_active_keys
        )
        
        # is_key_active method
        self._register_method(
            module_id=self.module_id,
            group_id="state_methods",
            method_id="is_key_active",
            method_info={
                "name": "is_key_active(key)",
                "description": "Check if a specific key is currently active.",
                "type": "GET",
                "params": {
                    "key": {
                        "type": "text",
                        "description": "Key to check",
                        "placeholder": "e.g., w, a, s, d, Key.space",
                        "required": True
                    }
                }
            },
            handler_function=self._handle_is_key_active
        )
        
        # get_mouse_position method
        self._register_method(
            module_id=self.module_id,
            group_id="state_methods",
            method_id="get_mouse_position",
            method_info={
                "name": "get_mouse_position()",
                "description": "Get the current mouse position as [x, y] coordinates.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_get_mouse_position
        )
        
        # get_mouse_button_state method
        self._register_method(
            module_id=self.module_id,
            group_id="state_methods",
            method_id="get_mouse_button_state",
            method_info={
                "name": "get_mouse_button_state(button)",
                "description": "Get the state of a specific mouse button.",
                "type": "GET",
                "params": {
                    "button": {
                        "type": "select",
                        "description": "Mouse button to check",
                        "options": ["left", "right", "middle"],
                        "required": True
                    }
                }
            },
            handler_function=self._handle_get_mouse_button_state
        )
        
        # is_mouse_moving method
        self._register_method(
            module_id=self.module_id,
            group_id="state_methods",
            method_id="is_mouse_moving",
            method_info={
                "name": "is_mouse_moving()",
                "description": "Check if the mouse is currently moving.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_is_mouse_moving
        )
        
        # get_mouse_direction method
        self._register_method(
            module_id=self.module_id,
            group_id="state_methods",
            method_id="get_mouse_direction",
            method_info={
                "name": "get_mouse_direction()",
                "description": "Get the current mouse movement direction.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_get_mouse_direction
        )
        
        # get_metadata method
        self._register_method(
            module_id=self.module_id,
            group_id="state_methods",
            method_id="get_metadata",
            method_info={
                "name": "get_metadata()",
                "description": "Get metadata about the input collection process.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_get_metadata
        )
    
    def _register_event_methods(self):
        """Register event-related API methods."""
        # get_current_event method
        self._register_method(
            module_id=self.module_id,
            group_id="event_methods",
            method_id="get_current_event",
            method_info={
                "name": "get_current_event()",
                "description": "Get the most recent input event.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_get_current_event
        )
        
        # get_key_events method
        self._register_method(
            module_id=self.module_id,
            group_id="event_methods",
            method_id="get_key_events",
            method_info={
                "name": "get_key_events(max_count)",
                "description": "Get recent keyboard events.",
                "type": "GET",
                "params": {
                    "max_count": {
                        "type": "number",
                        "description": "Maximum number of events to return",
                        "placeholder": "e.g., 10",
                        "required": False
                    }
                }
            },
            handler_function=self._handle_get_key_events
        )
        
        # get_mouse_movement_events method
        self._register_method(
            module_id=self.module_id,
            group_id="event_methods",
            method_id="get_mouse_movement_events",
            method_info={
                "name": "get_mouse_movement_events(max_count)",
                "description": "Get recent mouse movement events.",
                "type": "GET",
                "params": {
                    "max_count": {
                        "type": "number",
                        "description": "Maximum number of events to return",
                        "placeholder": "e.g., 10",
                        "required": False
                    }
                }
            },
            handler_function=self._handle_get_mouse_movement_events
        )
        
        # get_mouse_button_events method
        self._register_method(
            module_id=self.module_id,
            group_id="event_methods",
            method_id="get_mouse_button_events",
            method_info={
                "name": "get_mouse_button_events(max_count)",
                "description": "Get recent mouse button events.",
                "type": "GET",
                "params": {
                    "max_count": {
                        "type": "number",
                        "description": "Maximum number of events to return",
                        "placeholder": "e.g., 10",
                        "required": False
                    }
                }
            },
            handler_function=self._handle_get_mouse_button_events
        )
        
        # get_controller_events method
        self._register_method(
            module_id=self.module_id,
            group_id="event_methods",
            method_id="get_controller_events",
            method_info={
                "name": "get_controller_events(max_count)",
                "description": "Get recent controller events.",
                "type": "GET",
                "params": {
                    "max_count": {
                        "type": "number",
                        "description": "Maximum number of events to return",
                        "placeholder": "e.g., 10",
                        "required": False
                    }
                }
            },
            handler_function=self._handle_get_controller_events
        )
    
    def _register_controller_methods(self):
        """Register controller-related API methods."""
        # is_controller_connected method
        self._register_method(
            module_id=self.module_id,
            group_id="controller_methods",
            method_id="is_controller_connected",
            method_info={
                "name": "is_controller_connected()",
                "description": "Check if a controller is connected.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_is_controller_connected
        )
        
        # get_controller_name method
        self._register_method(
            module_id=self.module_id,
            group_id="controller_methods",
            method_id="get_controller_name",
            method_info={
                "name": "get_controller_name()",
                "description": "Get the name of the connected controller.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_get_controller_name
        )
    
    def _register_callback_methods(self):
        """Register callback-related API methods."""
        # register_event_callback method
        self._register_method(
            module_id=self.module_id,
            group_id="callback_methods",
            method_id="register_event_callback",
            method_info={
                "name": "register_event_callback()",
                "description": "Register a callback for input events. In the API Explorer, this will register a WebSocket connection.",
                "type": "POST",
                "params": {}
            },
            handler_function=self._handle_register_event_callback
        )
        
        # unregister_event_callback method
        self._register_method(
            module_id=self.module_id,
            group_id="callback_methods",
            method_id="unregister_event_callback",
            method_info={
                "name": "unregister_event_callback(callback_id)",
                "description": "Unregister a previously registered callback.",
                "type": "POST",
                "params": {
                    "callback_id": {
                        "type": "number",
                        "description": "ID of the callback to unregister",
                        "placeholder": "e.g., 1",
                        "required": True
                    }
                }
            },
            handler_function=self._handle_unregister_event_callback
        )
    
    def _register_for_events(self):
        """Register for real-time events."""
        callback_id = InputDataAPI.register_event_callback(self._event_callback)
        self.event_callback_id = callback_id
    
    def _event_callback(self, event):
        """
        Callback for input events.
        
        Args:
            event: The input event
        """
        if not self.is_registered or not self.explorer:
            return
        
        try:
            # Convert the event to a dict (removing any non-serializable attributes)
            event_dict = {}
            for key, value in event.__dict__.items():
                if not key.startswith("_") and value is not None:
                    event_dict[key] = value
            
            # Add event type for easier filtering in the frontend
            if 'event_type' not in event_dict and hasattr(event, 'event_type'):
                event_dict['event_type'] = event.event_type
                
            # Debug logging to see if events are being processed
            print(f"WebSocket event: {event_dict.get('event_type', 'unknown')}")
            
            # Broadcast event if method exists
            if hasattr(self.explorer, 'broadcast_event'):
                # Create a new event loop if needed
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run the broadcast in the event loop
                async def broadcast():
                    try:
                        await self.explorer.broadcast_event(self.module_id, event_dict)
                    except Exception as e:
                        print(f"Error broadcasting event: {e}")
                
                try:
                    # Run the coroutine
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(broadcast(), loop)
                    else:
                        loop.run_until_complete(broadcast())
                except Exception as e:
                    print(f"Error in event loop: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("ApiExplorer does not have broadcast_event method, event not sent")
            
        except Exception as e:
            print(f"Error in event callback: {e}")
            import traceback
            traceback.print_exc()
    
    def shutdown(self):
        """Clean up resources."""
        if self.event_callback_id is not None:
            InputDataAPI.unregister_event_callback(self.event_callback_id)
            self.event_callback_id = None
    
    # Handler methods for API endpoints
    
    async def _handle_get_active_keys(self):
        """Handle get_active_keys API endpoint."""
        return InputDataAPI.get_active_keys()
    
    async def _handle_is_key_active(self, key: str):
        """Handle is_key_active API endpoint."""
        return {"active": InputDataAPI.is_key_active(key)}
    
    async def _handle_get_mouse_position(self):
        """Handle get_mouse_position API endpoint."""
        x, y = InputDataAPI.get_mouse_position()
        return {"x": x, "y": y}
    
    async def _handle_get_mouse_button_state(self, button: str):
        """Handle get_mouse_button_state API endpoint."""
        return {"pressed": InputDataAPI.get_mouse_button_state(button)}
    
    async def _handle_is_mouse_moving(self):
        """Handle is_mouse_moving API endpoint."""
        return {"moving": InputDataAPI.is_mouse_moving()}
    
    async def _handle_get_mouse_direction(self):
        """Handle get_mouse_direction API endpoint."""
        return {"direction": InputDataAPI.get_mouse_direction()}
    
    async def _handle_get_metadata(self):
        """Handle get_metadata API endpoint."""
        return InputDataAPI.get_metadata()
    
    async def _handle_get_current_event(self):
        """Handle get_current_event API endpoint."""
        event = InputDataAPI.get_current_event()
        if event is None:
            return None
        # Convert event object to dictionary
        return {k: v for k, v in event.__dict__.items() if not k.startswith("_") and v is not None}
    
    async def _handle_get_key_events(self, max_count: Optional[int] = None):
        """Handle get_key_events API endpoint."""
        events = InputDataAPI.get_key_events(max_count)
        return [
            {k: v for k, v in event.__dict__.items() if not k.startswith("_") and v is not None}
            for event in events
        ]
    
    async def _handle_get_mouse_movement_events(self, max_count: Optional[int] = None):
        """Handle get_mouse_movement_events API endpoint."""
        events = InputDataAPI.get_mouse_movement_events(max_count)
        return [
            {k: v for k, v in event.__dict__.items() if not k.startswith("_") and v is not None}
            for event in events
        ]
    
    async def _handle_get_mouse_button_events(self, max_count: Optional[int] = None):
        """Handle get_mouse_button_events API endpoint."""
        events = InputDataAPI.get_mouse_button_events(max_count)
        return [
            {k: v for k, v in event.__dict__.items() if not k.startswith("_") and v is not None}
            for event in events
        ]
    
    async def _handle_get_controller_events(self, max_count: Optional[int] = None):
        """Handle get_controller_events API endpoint."""
        events = InputDataAPI.get_controller_events(max_count)
        return [
            {k: v for k, v in event.__dict__.items() if not k.startswith("_") and v is not None}
            for event in events
        ]
    
    async def _handle_is_controller_connected(self):
        """Handle is_controller_connected API endpoint."""
        return {"connected": InputDataAPI.is_controller_connected()}
    
    async def _handle_get_controller_name(self):
        """Handle get_controller_name API endpoint."""
        return {"name": InputDataAPI.get_controller_name()}
    
    async def _handle_register_event_callback(self):
        """Handle register_event_callback API endpoint."""
        # This is just a placeholder - actual WebSocket connections are handled separately
        return {"callback_id": 1, "status": "registered"}
    
    async def _handle_unregister_event_callback(self, callback_id: int):
        """Handle unregister_event_callback API endpoint."""
        # This is just a placeholder - actual WebSocket connections are handled separately
        return {"success": True, "message": "Callback unregistered"}


# Create a singleton instance
_api_integration = None

def get_api_integration():
    """Get or create the API integration instance."""
    global _api_integration
    if _api_integration is None:
        _api_integration = InputCollectorApiIntegration()
    return _api_integration

def initialize_api(enable_web_api: bool = True, host: str = "127.0.0.1", port: int = 8000):
    """
    Initialize the web API for the input collector.
    
    Args:
        enable_web_api: Whether to enable the web API
        host: Host to bind the server to
        port: Port to bind the server to
        
    Returns:
        True if initialization was successful, False otherwise
    """
    if not enable_web_api:
        return False
        
    if not explorer_available:
        print("API Explorer not available. Web API will not be enabled.")
        return False
    
    integration = get_api_integration()
    success = integration.register_api(start_server=True, host=host, port=port)
    
    return success
