"""
Modular API Explorer.

This module provides a reusable, dynamic API Explorer that can be used by different modules
to expose their APIs through a web interface.
"""

import json
import logging
import os
import threading
from typing import Dict, List, Optional, Callable

import uvicorn
# FastAPI imports
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


class ApiExplorer:
    """
    Dynamic API Explorer for exposing module APIs through a web interface.
    
    This class implements a singleton pattern to ensure only one instance
    is active at a time, allowing multiple modules to register their APIs
    with the same Explorer instance.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """Get or create the singleton instance of ApiExplorer."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = ApiExplorer()
            return cls._instance
    
    def __init__(self):
        """Initialize the API Explorer."""
        if ApiExplorer._instance is not None:
            raise RuntimeError("ApiExplorer is a singleton. Use get_instance() instead.")
        
        # Set up FastAPI application
        self.app = FastAPI(
            title="Dynamic API Explorer",
            description="Interactive documentation for exploring and testing module APIs",
            version="1.0.0",
        )
        
        # Enable CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Get the base directory for this module
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Set up templates and static files with absolute paths
        self._setup_directories()
        self.templates = Jinja2Templates(directory=os.path.join(self.base_dir, "templates"))
        self.app.mount("/static", StaticFiles(directory=os.path.join(self.base_dir, "static")), name="static")
        
        # Module registry - stores information about registered modules
        self.modules = {}
        
        # WebSocket connections
        self.active_connections: List[WebSocket] = []
        
        # Callback registry
        self.callback_registry: Dict[str, Dict[int, Callable]] = {}
        self.next_callback_id = 0
        
        # Active module tracking for reference counting
        self.active_module_count = 0
        self.active_modules = set()
        
        # Server control
        self.server = None
        self.server_thread = None
        self.is_running = False
        self.server_port = None
        self.server_host = None
        
        # Setup basic routes
        self._setup_routes()
    
    def _setup_directories(self):
        """Set up necessary directories."""
        os.makedirs(os.path.join(self.base_dir, "templates"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "static"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "static", "css"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "static", "js"), exist_ok=True)
    
    def _setup_routes(self):
        """Set up the basic routes for the API Explorer."""
        # Home page route
        @self.app.get("/", response_class=HTMLResponse)
        async def get_home(request: Request):
            # Convert modules dictionary to a list for the template
            modules_list = []
            for module_id, module_info in self.modules.items():
                module_data = {
                    'id': module_id,
                    'name': module_info.get('name', ''),
                    'description': module_info.get('description', ''),
                    'show_data_table': module_info.get('show_data_table', False),
                    'method_groups': []
                }
                
                # Convert method groups
                for group_id, group_info in module_info.get('method_groups', {}).items():
                    group_data = {
                        'id': group_id,
                        'name': group_info.get('name', ''),
                        'methods': []
                    }
                    
                    # Convert methods in each group
                    for method_id, method_info in group_info.get('methods', {}).items():
                        method_data = {
                            'id': method_id,
                            'name': method_info.get('name', method_id),
                            'description': method_info.get('description', ''),
                            'type': method_info.get('type', 'GET'),
                            'params': method_info.get('params', {})
                        }
                        group_data['methods'].append(method_data)
                    
                    module_data['method_groups'].append(group_data)
                
                modules_list.append(module_data)
                
            return self.templates.TemplateResponse("index.html", {"request": request, "modules": modules_list})
        
        # WebSocket endpoint for real-time events
        @self.app.websocket("/ws/{module_id}")
        async def websocket_endpoint(websocket: WebSocket, module_id: str):
            await websocket.accept()
            # Add connection info with module ID for routing
            print(f"WebSocket connection established for module: {module_id}")
            websocket.scope["module_id"] = module_id
            self.active_connections.append(websocket)
            
            try:
                # Acknowledge connection
                await websocket.send_json({"status": "connected", "module": module_id})
                
                # Keep connection open
                while True:
                    # Wait for client messages (can be used to implement commands)
                    data = await websocket.receive_text()
                    try:
                        # Parse the message as JSON
                        message = json.loads(data)
                        # Handle command messages
                        if message.get("command") == "ping":
                            await websocket.send_json({"response": "pong"})
                    except:
                        # Ignore non-JSON messages
                        pass
            except WebSocketDisconnect:
                print(f"WebSocket disconnected for module: {module_id}")
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
            finally:
                # Ensure cleanup happens
                print(f"WebSocket connection cleaned up for module: {module_id}")
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
    
    async def broadcast_event(self, module_id: str, event_data: Dict) -> None:
        """
        Broadcast an event to all WebSocket clients for a specific module.
        
        Args:
            module_id: ID of the module the event belongs to
            event_data: Event data to broadcast
        """
        # Print debug information
        print(f"Broadcasting event for module {module_id}: {event_data.get('event_type', 'unknown')}")
        
        # Notify callbacks for this module
        if module_id in self.callback_registry:
            for callback in self.callback_registry[module_id].values():
                if callback:
                    try:
                        callback(event_data)
                    except Exception as e:
                        logging.error(f"Error in {module_id} callback: {e}")
        
        # Send to all connected WebSockets for this module
        active_count = 0
        for connection in self.active_connections:
            if connection.scope.get("module_id") == module_id:
                try:
                    await connection.send_json(event_data)
                    active_count += 1
                except Exception as e:
                    logging.error(f"Error sending to WebSocket: {e}")
        
        # Print how many connections received the event
        if active_count > 0:
            print(f"Event broadcast to {active_count} active connections")
        else:
            print("No active connections to receive event")
    
    def start_server(self, host: str = "127.0.0.1", port: int = 8000, 
                    block: bool = False) -> None:
        """
        Start the API Explorer server.
        
        Args:
            host: Host to bind the server to
            port: Port to bind the server to
            block: Whether to block the current thread (True) or run in background (False)
        """
        # Include all module routers
        for module_id, module_info in self.modules.items():
            router = module_info.get('router')
            if router:
                self.app.include_router(router)
        
        # Check if server is already running
        if self.is_running:
            logging.info(f"API Explorer server already running at http://{self.server_host}:{self.server_port}")
            return
            
        # Check if the specified port is already in use
        original_port = port
        while self._is_port_in_use(host, port):
            logging.info(f"Port {port} is already in use, looking for an alternative port...")
            port += 1
            if port > 8100:  # Set a reasonable limit to avoid infinite loop
                logging.error("Could not find an available port in range 8000-8100")
                return
                
        # If we changed ports, log it
        if port != original_port:
            logging.info(f"Using alternative port {port}")
        
        # Save server host and port
        self.server_host = host
        self.server_port = port
        
        if block:
            # Run in current thread (blocking)
            logging.info(f"API Explorer server starting at http://{host}:{port}")
            uvicorn.run(self.app, host=host, port=port)
        else:
            # Run in background thread
            self.is_running = True
            
            def run_server():
                try:
                    config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
                    self.server = uvicorn.Server(config)
                    logging.info(f"API Explorer server started at http://{host}:{port}")
                    self.server.run()
                except Exception as e:
                    logging.error(f"Error in API Explorer server: {e}")
                finally:
                    self.is_running = False
                    self.server = None
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
    
    def _is_port_in_use(self, host: str, port: int) -> bool:
        """
        Check if a port is already in use.
        
        Args:
            host: Host to check
            port: Port to check
            
        Returns:
            bool: True if port is in use, False otherwise
        """
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            # If there's an error, assume port is not in use
            return False
    
    def stop_server(self) -> None:
        """Stop the API Explorer server."""
        if self.server and self.is_running:
            self.server.should_exit = True
            self.is_running = False
            logging.info("API Explorer server stopping...")
    
    def add_method_group(self, module_id: str, group_id: str, name: str) -> None:
        """
        Add a method group to a module.
        
        Args:
            module_id: ID of the module to add the group to
            group_id: Unique identifier for the group
            name: Display name for the group
        """
        if module_id not in self.modules:
            raise ValueError(f"Module '{module_id}' is not registered.")
        
        module = self.modules[module_id]
        if 'method_groups' not in module:
            module['method_groups'] = {}
        
        module['method_groups'][group_id] = {
            'name': name,
            'methods': {}
        }

    def register_method(self, module_id: str, group_id: str, method_id: str, method_info: Dict,
                        handler_function: Callable) -> None:
        """
        Register an API method with the Explorer.
        
        Args:
            module_id: ID of the module to add the method to
            group_id: ID of the group to add the method to
            method_id: Unique identifier for the method
            method_info: Dictionary with method metadata (name, description, params, etc.)
            handler_function: Function that will handle API requests for this method
        """
        if module_id not in self.modules:
            raise ValueError(f"Module '{module_id}' is not registered.")
        
        module = self.modules[module_id]
        if group_id not in module.get('method_groups', {}):
            raise ValueError(f"Group '{group_id}' is not defined in module '{module_id}'.")
        
        # Add method to the group
        module['method_groups'][group_id]['methods'][method_id] = method_info
        
        # Register the API endpoint
        router = module.get('router')
        if not router:
            raise ValueError(f"Router not found for module '{module_id}'.")
        
        # Determine if GET or POST
        method_type = method_info.get('type', 'GET').upper()
        
        # Get the parameter signature of the handler function
        import inspect
        sig = inspect.signature(handler_function)
        param_names = list(sig.parameters.keys())
        
        # Create the endpoint
        if method_type == 'GET':
            # Create a GET endpoint with properly defined parameters
            if len(param_names) == 0:
                # No parameters needed
                @router.get(f"/{method_id}")
                async def endpoint():
                    return await handler_function()
            else:
                # Create parameters dynamically based on method_info params
                from fastapi import Query, Depends
                from pydantic import create_model
                
                param_dict = {}
                for param_id, param_info in method_info.get('params', {}).items():
                    if param_info.get('type') == 'number':
                        # Number parameter
                        param_dict[param_id] = (Optional[int], Query(None))
                    else:
                        # String parameter (default)
                        param_dict[param_id] = (str, Query(...))
                
                # Create dynamic model for query parameters
                QueryModel = create_model(f'{module_id.capitalize()}{method_id.capitalize()}Query', **param_dict)
                
                # Use Depends to extract parameters
                @router.get(f"/{method_id}")
                async def endpoint(query: QueryModel = Depends()):
                    # Convert to dict and pass to handler
                    param_dict = {k: v for k, v in query.__dict__.items() if v is not None}
                    return await handler_function(**param_dict)
        else:
            # For POST requests
            from fastapi import Body
            from pydantic import create_model
            
            param_fields = {}
            for param_id, param_info in method_info.get('params', {}).items():
                # Determine the Python type based on the param type
                if param_info.get('type') == 'number':
                    field_type = int
                else:
                    field_type = str
                
                # Create the field with type and default
                if param_info.get('required', False):
                    param_fields[param_id] = (field_type, ...)
                else:
                    param_fields[param_id] = (Optional[field_type], None)
            
            # Create dynamic model for request body
            RequestModel = create_model(f'{module_id.capitalize()}{method_id.capitalize()}Request', **param_fields)
            
            @router.post(f"/{method_id}")
            async def endpoint(request_data: RequestModel = Body(...)):
                # Convert to dict and pass to handler
                data_dict = {k: v for k, v in request_data.__dict__.items() if v is not None}
                return await handler_function(**data_dict)
    
    def register_module(self, module_id: str, name: str, description: str, show_data_table: bool = False) -> None:
        """
        Register a new module with its own router.
        
        Args:
            module_id: Unique identifier for the module
            name: Display name for the module
            description: Module description
            show_data_table: Whether to show the data table in real-time view for this module
        """
        if module_id in self.modules:
            raise ValueError(f"Module '{module_id}' already registered.")
        router = APIRouter(prefix=f"/api/{module_id}", tags=[name])
        self.modules[module_id] = {
            'name': name,
            'description': description,
            'method_groups': {},
            'router': router,
            'show_data_table': show_data_table
        }
