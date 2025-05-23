"""
Interaction API integration for the input collector.

This module integrates the input collector's interaction API with the API Explorer,
registering its methods and handling API requests.
"""

import asyncio
import logging
import os
import sys
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

# Import the InputCollectorAPI
from .interaction_api import InputCollectorAPI


class InteractionApiIntegration:
    """
    Integrates the input collector's interaction API with the API Explorer.
    
    This class exposes the input collector's interaction API methods through the API Explorer.
    """
    
    def __init__(self):
        """Initialize the API integration."""
        self.explorer = None
        self.module_id = "input_collector_control"
        self.is_registered = False
        
        # For storing method groups and methods when fallback is used
        self.fallback_method_groups = {}
        self.fallback_methods = {}
        
        # Module registration status flag
        self.module_registered = False
    
    def register_api(self, start_server: bool = True, host: str = "127.0.0.1", 
                     port: int = 8000) -> bool:
        """
        Register the input collector's interaction API with the Explorer.
        
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
            
            # Start the server if requested
            if start_server and hasattr(self.explorer, 'start_server') and not self.explorer.is_running:
                self.explorer.start_server(host=host, port=port, block=False)
            
            self.is_registered = True
            return True
        except Exception as e:
            logger.error(f"Error registering interaction API: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _register_module(self) -> bool:
        """Register the input collector control module."""
        try:
            if hasattr(self.explorer, 'register_module'):
                self.explorer.register_module(
                    module_id=self.module_id,
                    name="Input Collector Control",
                    description="API for controlling the input collector application"
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
                router = APIRouter(prefix=f"/api/{self.module_id}", tags=["Input Collector Control"])
                
                # If explorer has an app attribute, add the router directly
                if hasattr(self.explorer, 'app'):
                    self.explorer.app.include_router(router)
            except Exception as e:
                logger.error(f"Error creating router: {e}")
            
            # Register module in the modules dict
            self.explorer.modules[self.module_id] = {
                'name': "Input Collector Control",
                'description': "API for controlling the input collector application",
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
        self._register_recording_methods()
        self._register_logging_methods()
        self._register_collector_methods()
        self._register_mouse_methods()
        self._register_key_methods()
        self._register_ui_methods()
    
    def _register_method_groups(self) -> None:
        """Register method groups for the input collector."""
        if not self.module_registered:
            logger.error("Cannot register method groups - module not registered")
            return
            
        groups = [
            ("recording", "Recording Control"),
            ("logging", "Logging Configuration"),
            ("collectors", "Collector Management"),
            ("mouse", "Mouse Tracking Configuration"),
            ("keys", "Key Tracking Management"),
            ("ui", "UI Control")
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
                tags=["Input Collector Control"]
            )
            
            logger.info(f"Added fallback route for {method_id} at {path}")
        except Exception as e:
            logger.error(f"Failed to add fallback route for {method_id}: {e}")
    
    def shutdown(self) -> None:
        """Clean up resources when shutting down."""
        logger.info("API integration shut down")
    
    #
    # Method registration for different API groups
    #
    
    def _register_recording_methods(self) -> None:
        """Register recording control methods."""
        # start_recording method
        self._register_method(
            module_id=self.module_id,
            group_id="recording",
            method_id="start_recording",
            method_info={
                "name": "start_recording()",
                "description": "Start recording input events.",
                "type": "POST",
                "params": {}
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
                "description": "Stop recording input events.",
                "type": "POST",
                "params": {}
            },
            handler_function=self._handle_stop_recording
        )
        
        # toggle_recording method
        self._register_method(
            module_id=self.module_id,
            group_id="recording",
            method_id="toggle_recording",
            method_info={
                "name": "toggle_recording()",
                "description": "Toggle recording state.",
                "type": "POST",
                "params": {}
            },
            handler_function=self._handle_toggle_recording
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
    
    def _register_logging_methods(self) -> None:
        """Register logging configuration methods."""
        # enable_json_logging method
        self._register_method(
            module_id=self.module_id,
            group_id="logging",
            method_id="enable_json_logging",
            method_info={
                "name": "enable_json_logging(enabled)",
                "description": "Enable or disable JSON logging.",
                "type": "POST",
                "params": {
                    "enabled": {
                        "type": "boolean",
                        "description": "Whether to enable JSON logging",
                        "required": True,
                        "default": True
                    }
                }
            },
            handler_function=self._handle_enable_json_logging
        )
        
        # enable_csv_logging method
        self._register_method(
            module_id=self.module_id,
            group_id="logging",
            method_id="enable_csv_logging",
            method_info={
                "name": "enable_csv_logging(enabled, filepath)",
                "description": "Enable or disable CSV logging.",
                "type": "POST",
                "params": {
                    "enabled": {
                        "type": "boolean",
                        "description": "Whether to enable CSV logging",
                        "required": True,
                        "default": True
                    },
                    "filepath": {
                        "type": "text",
                        "description": "Path for CSV file (required when enabling if not previously set)",
                        "required": False
                    }
                }
            },
            handler_function=self._handle_enable_csv_logging
        )
        
        # set_csv_path method
        self._register_method(
            module_id=self.module_id,
            group_id="logging",
            method_id="set_csv_path",
            method_info={
                "name": "set_csv_path(filepath)",
                "description": "Set the CSV logging file path.",
                "type": "POST",
                "params": {
                    "filepath": {
                        "type": "text",
                        "description": "Path for CSV file",
                        "required": True
                    }
                }
            },
            handler_function=self._handle_set_csv_path
        )
        
        # get_logging_state method
        self._register_method(
            module_id=self.module_id,
            group_id="logging",
            method_id="get_logging_state",
            method_info={
                "name": "get_logging_state()",
                "description": "Get current logging configuration.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_get_logging_state
        )
    
    def _register_collector_methods(self) -> None:
        """Register collector management methods."""
        # get_available_collectors method
        self._register_method(
            module_id=self.module_id,
            group_id="collectors",
            method_id="get_available_collectors",
            method_info={
                "name": "get_available_collectors()",
                "description": "Get list of available collectors.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_get_available_collectors
        )
        
        # switch_collector method
        self._register_method(
            module_id=self.module_id,
            group_id="collectors",
            method_id="switch_collector",
            method_info={
                "name": "switch_collector(collector_type)",
                "description": "Switch to a different input collector.",
                "type": "POST",
                "params": {
                    "collector_type": {
                        "type": "text",
                        "description": "Type identifier for the collector",
                        "required": True
                    }
                }
            },
            handler_function=self._handle_switch_collector
        )
        
        # get_current_collector method
        self._register_method(
            module_id=self.module_id,
            group_id="collectors",
            method_id="get_current_collector",
            method_info={
                "name": "get_current_collector()",
                "description": "Get information about the current collector.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_get_current_collector
        )
        
        # scan_controllers method
        self._register_method(
            module_id=self.module_id,
            group_id="collectors",
            method_id="scan_controllers",
            method_info={
                "name": "scan_controllers()",
                "description": "Scan for available controllers.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_scan_controllers
        )
        
        # connect_controller method
        self._register_method(
            module_id=self.module_id,
            group_id="collectors",
            method_id="connect_controller",
            method_info={
                "name": "connect_controller(index)",
                "description": "Connect to a specific controller by index.",
                "type": "POST",
                "params": {
                    "index": {
                        "type": "number",
                        "description": "Controller index from scan_controllers()",
                        "required": True
                    }
                }
            },
            handler_function=self._handle_connect_controller
        )
    
    def _register_mouse_methods(self) -> None:
        """Register mouse tracking configuration methods."""
        # set_mouse_tracking_mode method
        self._register_method(
            module_id=self.module_id,
            group_id="mouse",
            method_id="set_mouse_tracking_mode",
            method_info={
                "name": "set_mouse_tracking_mode(mode, direction_only)",
                "description": "Set the mouse tracking mode.",
                "type": "POST",
                "params": {
                    "mode": {
                        "type": "select",
                        "description": "Tracking mode",
                        "options": ["joystick", "delta", "angle", "axis"],
                        "required": True
                    },
                    "direction_only": {
                        "type": "boolean",
                        "description": "Whether to use direction-only mode",
                        "required": False
                    }
                }
            },
            handler_function=self._handle_set_mouse_tracking_mode
        )
        
        # set_mouse_settings method
        self._register_method(
            module_id=self.module_id,
            group_id="mouse",
            method_id="set_mouse_settings",
            method_info={
                "name": "set_mouse_settings(delta_smoothing, joystick_sensitivity, angle_grouping)",
                "description": "Set mouse tracking settings.",
                "type": "POST",
                "params": {
                    "delta_smoothing": {
                        "type": "number",
                        "description": "Smoothing factor for delta tracking (0-100)",
                        "required": False
                    },
                    "joystick_sensitivity": {
                        "type": "number",
                        "description": "Sensitivity for joystick tracking (0-100)",
                        "required": False
                    },
                    "angle_grouping": {
                        "type": "number",
                        "description": "Angle grouping in degrees (1-60)",
                        "required": False
                    }
                }
            },
            handler_function=self._handle_set_mouse_settings
        )
        
        # get_mouse_settings method
        self._register_method(
            module_id=self.module_id,
            group_id="mouse",
            method_id="get_mouse_settings",
            method_info={
                "name": "get_mouse_settings()",
                "description": "Get current mouse tracking settings.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_get_mouse_settings
        )
    
    def _register_key_methods(self) -> None:
        """Register key tracking methods."""
        # get_tracked_keys method
        self._register_method(
            module_id=self.module_id,
            group_id="keys",
            method_id="get_tracked_keys",
            method_info={
                "name": "get_tracked_keys()",
                "description": "Get list of tracked keys.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_get_tracked_keys
        )
        
        # toggle_edit_mode method
        self._register_method(
            module_id=self.module_id,
            group_id="keys",
            method_id="toggle_edit_mode",
            method_info={
                "name": "toggle_edit_mode()",
                "description": "Toggle key/button edit mode.",
                "type": "POST",
                "params": {}
            },
            handler_function=self._handle_toggle_edit_mode
        )
        
        # is_edit_mode method
        self._register_method(
            module_id=self.module_id,
            group_id="keys",
            method_id="is_edit_mode",
            method_info={
                "name": "is_edit_mode()",
                "description": "Check if edit mode is active.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_is_edit_mode
        )
        
        # add_tracked_key method
        self._register_method(
            module_id=self.module_id,
            group_id="keys",
            method_id="add_tracked_key",
            method_info={
                "name": "add_tracked_key(key)",
                "description": "Add a key to tracked keys list.",
                "type": "POST",
                "params": {
                    "key": {
                        "type": "text",
                        "description": "Key to track (e.g., 'a', 'b', 'Key.space')",
                        "required": True
                    }
                }
            },
            handler_function=self._handle_add_tracked_key
        )
        
        # remove_tracked_key method
        self._register_method(
            module_id=self.module_id,
            group_id="keys",
            method_id="remove_tracked_key",
            method_info={
                "name": "remove_tracked_key(key)",
                "description": "Remove a key from tracked keys list.",
                "type": "POST",
                "params": {
                    "key": {
                        "type": "text",
                        "description": "Key to untrack (e.g., 'a', 'b', 'Key.space')",
                        "required": True
                    }
                }
            },
            handler_function=self._handle_remove_tracked_key
        )
        
        # toggle_button_tracking method
        self._register_method(
            module_id=self.module_id,
            group_id="keys",
            method_id="toggle_button_tracking",
            method_info={
                "name": "toggle_button_tracking(button_id, track)",
                "description": "Toggle tracking for a mouse button.",
                "type": "POST",
                "params": {
                    "button_id": {
                        "type": "select",
                        "description": "Button identifier",
                        "options": ["Button.left", "Button.right", "Button.scroll"],
                        "required": True
                    },
                    "track": {
                        "type": "boolean",
                        "description": "Whether to track the button",
                        "required": True
                    }
                }
            },
            handler_function=self._handle_toggle_button_tracking
        )
    
    def _register_ui_methods(self) -> None:
        """Register UI control methods."""
        # toggle_fullscreen method
        self._register_method(
            module_id=self.module_id,
            group_id="ui",
            method_id="toggle_fullscreen",
            method_info={
                "name": "toggle_fullscreen()",
                "description": "Toggle fullscreen mode.",
                "type": "POST",
                "params": {}
            },
            handler_function=self._handle_toggle_fullscreen
        )
        
        # get_application_state method
        self._register_method(
            module_id=self.module_id,
            group_id="ui",
            method_id="get_application_state",
            method_info={
                "name": "get_application_state()",
                "description": "Get comprehensive application state.",
                "type": "GET",
                "params": {}
            },
            handler_function=self._handle_get_application_state
        )
    
    #
    # API endpoint handlers
    #
    
    async def _handle_start_recording(self):
        """Handle start_recording API request."""
        try:
            success = InputCollectorAPI.start_recording()
            return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
        except Exception as e:
            logger.error(f"Error in start_recording endpoint: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}
    
    async def _handle_stop_recording(self):
        """Handle stop_recording API request."""
        try:
            success = InputCollectorAPI.stop_recording()
            return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
        except Exception as e:
            logger.error(f"Error in stop_recording endpoint: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}
    
    async def _handle_toggle_recording(self):
        """Handle toggle_recording API request."""
        try:
            success = InputCollectorAPI.toggle_recording()
            return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
        except Exception as e:
            logger.error(f"Error in toggle_recording endpoint: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_is_recording(self):
        """Handle is_recording API request."""
        is_recording = InputCollectorAPI.is_recording()
        return {"recording": is_recording}
    
    async def _handle_enable_json_logging(self, enabled: bool = True):
        """Handle enable_json_logging API request."""
        success = InputCollectorAPI.enable_json_logging(enabled)
        return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
    
    async def _handle_enable_csv_logging(self, enabled: bool = True, filepath: Optional[str] = None):
        """Handle enable_csv_logging API request."""
        success = InputCollectorAPI.enable_csv_logging(enabled, filepath)
        return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
    
    async def _handle_set_csv_path(self, filepath: str):
        """Handle set_csv_path API request."""
        success = InputCollectorAPI.set_csv_path(filepath)
        return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
    
    async def _handle_get_logging_state(self):
        """Handle get_logging_state API request."""
        return InputCollectorAPI.get_logging_state()
    
    async def _handle_get_available_collectors(self):
        """Handle get_available_collectors API request."""
        collectors = InputCollectorAPI.get_available_collectors()
        return {"collectors": collectors}
    
    async def _handle_switch_collector(self, collector_type: str):
        """Handle switch_collector API request."""
        success = InputCollectorAPI.switch_collector(collector_type)
        return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
    
    async def _handle_get_current_collector(self):
        """Handle get_current_collector API request."""
        return InputCollectorAPI.get_current_collector()
    
    async def _handle_scan_controllers(self):
        """Handle scan_controllers API request."""
        controllers = InputCollectorAPI.scan_controllers()
        return {"controllers": controllers}
    
    async def _handle_connect_controller(self, index: int):
        """Handle connect_controller API request."""
        success = InputCollectorAPI.connect_controller(index)
        return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
    
    async def _handle_set_mouse_tracking_mode(self, mode: str, direction_only: Optional[bool] = None):
        """Handle set_mouse_tracking_mode API request."""
        success = InputCollectorAPI.set_mouse_tracking_mode(mode, direction_only)
        return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
    
    async def _handle_set_mouse_settings(self, delta_smoothing: Optional[float] = None,
                                      joystick_sensitivity: Optional[float] = None,
                                      angle_grouping: Optional[int] = None):
        """Handle set_mouse_settings API request."""
        success = InputCollectorAPI.set_mouse_settings(
            delta_smoothing, joystick_sensitivity, angle_grouping
        )
        return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
    
    async def _handle_get_mouse_settings(self):
        """Handle get_mouse_settings API request."""
        return InputCollectorAPI.get_mouse_settings()
    
    async def _handle_get_tracked_keys(self):
        """Handle get_tracked_keys API request."""
        keys = InputCollectorAPI.get_tracked_keys()
        return {"keys": keys}
    
    async def _handle_toggle_edit_mode(self):
        """Handle toggle_edit_mode API request."""
        success = InputCollectorAPI.toggle_edit_mode()
        return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
    
    async def _handle_is_edit_mode(self):
        """Handle is_edit_mode API request."""
        edit_mode = InputCollectorAPI.is_edit_mode()
        return {"edit_mode": edit_mode}
    
    async def _handle_add_tracked_key(self, key: str):
        """Handle add_tracked_key API request."""
        success = InputCollectorAPI.add_tracked_key(key)
        return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
    
    async def _handle_remove_tracked_key(self, key: str):
        """Handle remove_tracked_key API request."""
        success = InputCollectorAPI.remove_tracked_key(key)
        return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
    
    async def _handle_toggle_button_tracking(self, button_id: str, track: bool):
        """Handle toggle_button_tracking API request."""
        success = InputCollectorAPI.toggle_button_tracking(button_id, track)
        return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
    
    async def _handle_toggle_fullscreen(self):
        """Handle toggle_fullscreen API request."""
        success = InputCollectorAPI.toggle_fullscreen()
        return {"success": success, "status": InputCollectorAPI.get_last_operation_status()}
    
    async def _handle_get_application_state(self):
        """Handle get_application_state API request."""
        return InputCollectorAPI.get_application_state()


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
    Initialize the interaction web API for the input collector.
    
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
