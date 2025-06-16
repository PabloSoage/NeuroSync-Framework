"""
Modular API Explorer.

This module provides a reusable, dynamic API Explorer that can be used by different modules
to expose their APIs through a web interface.
"""

import json
import logging
import os
import threading
from typing import Dict, List, Optional, Callable, Any, Set

import uvicorn

# FastAPI imports
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    APIRouter,
    Request,
    Query,
    HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .websocket_manager import WebSocketManager


class ApiExplorer:
    """
    Dynamic API Explorer for exposing module APIs through a web interface.

    This class implements a singleton pattern to ensure only one instance
    is active at a time, allowing multiple modules to register their APIs
    with the same Explorer instance.
    """

    _instance: Optional["ApiExplorer"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "ApiExplorer":
        """Get or create the singleton instance of ApiExplorer."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = ApiExplorer()
            return cls._instance

    def __init__(self) -> None:
        """Initialize the API Explorer."""
        if ApiExplorer._instance is not None:
            raise RuntimeError(
                "ApiExplorer is a singleton. Use get_instance() instead."
            )

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

        # Get the base directory for this module (the api_explorer package)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        # Set up templates and static files with absolute paths
        self._setup_directories()
        self.templates = Jinja2Templates(
            directory=os.path.join(self.base_dir, "templates")
        )
        self.app.mount(
            "/static",
            StaticFiles(directory=os.path.join(self.base_dir, "static")),
            name="static",
        )

        # Module registry - stores information about registered modules
        self.modules: Dict[str, Dict[str, Any]] = {}

        # WebSocket manager
        self.websocket_manager = WebSocketManager()

        # Callback registry
        self.callback_registry: Dict[str, Dict[int, Callable]] = {}
        self.next_callback_id = 0

        # Active module tracking for reference counting
        self.active_module_count = 0
        self.active_modules: Set[str] = set()

        # Server control
        self.server: Optional[uvicorn.Server] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.server_port: Optional[int] = None
        self.server_host: Optional[str] = None

        # Setup basic routes
        self._setup_routes()

    def _setup_directories(self) -> None:
        """Set up necessary directories only if we're in the api_explorer package."""
        api_explorer_init = os.path.join(self.base_dir, "__init__.py")
        if os.path.exists(api_explorer_init):
            os.makedirs(os.path.join(self.base_dir, "templates"), exist_ok=True)
            os.makedirs(os.path.join(self.base_dir, "static"), exist_ok=True)
            os.makedirs(os.path.join(self.base_dir, "static", "css"), exist_ok=True)
            os.makedirs(os.path.join(self.base_dir, "static", "js"), exist_ok=True)
        else:
            logging.info(
                f"Running ApiExplorer from external module, using templates from {self.base_dir}"
            )

    def _setup_routes(self) -> None:
        """Set up the basic routes for the API Explorer."""

        @self.app.get("/", response_class=HTMLResponse)
        async def get_home(request: Request) -> HTMLResponse:
            modules_list = self._prepare_modules_for_template()
            cwd = os.getcwd().replace("\\", "/")
            return self.templates.TemplateResponse(
                "index.html",
                {"request": request, "modules": modules_list, "base_browse_path": cwd},
            )

        @self.app.websocket("/ws/{module_id}")
        async def websocket_endpoint(websocket: WebSocket, module_id: str) -> None:
            await self._handle_websocket_connection(websocket, module_id)

        @self.app.get("/api/files")
        async def list_files(path: str = Query(...)) -> Dict[str, List[Dict[str, str]]]:
            return self._handle_file_listing(path)

    def _prepare_modules_for_template(self) -> List[Dict[str, Any]]:
        """Convert modules dictionary to a list format suitable for templates."""
        modules_list = []
        for module_id, module_info in self.modules.items():
            module_data = {
                "id": module_id,
                "name": module_info.get("name", ""),
                "description": module_info.get("description", ""),
                "show_data_table": module_info.get("show_data_table", False),
                "method_groups": [],
            }

            for group_id, group_info in module_info.get("method_groups", {}).items():
                group_data = {
                    "id": group_id,
                    "name": group_info.get("name", ""),
                    "methods": [],
                }

                for method_id, method_info in group_info.get("methods", {}).items():
                    method_data = {
                        "id": method_id,
                        "name": method_info.get("name", method_id),
                        "description": method_info.get("description", ""),
                        "type": method_info.get("type", "GET"),
                        "params": method_info.get("params", {}),
                    }
                    group_data["methods"].append(method_data)

                module_data["method_groups"].append(group_data)

            modules_list.append(module_data)

        return modules_list

    async def _handle_websocket_connection(
        self, websocket: WebSocket, module_id: str
    ) -> None:
        """Handle WebSocket connection lifecycle."""
        await websocket.accept()
        print(f"WebSocket connection established for module: {module_id}")

        await self.websocket_manager.add_connection(module_id, websocket)

        try:
            await websocket.send_json({"status": "connected", "module": module_id})

            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    if message.get("command") == "ping":
                        await websocket.send_json({"response": "pong"})
                except:
                    pass
        except WebSocketDisconnect:
            print(f"WebSocket disconnected for module: {module_id}")
        except Exception as e:
            print(f"WebSocket error: {str(e)}")
        finally:
            print(f"WebSocket connection cleaned up for module: {module_id}")
            await self.websocket_manager.remove_connection(module_id, websocket)

    def _handle_file_listing(self, path: str) -> Dict[str, List[Dict[str, str]]]:
        """Handle file browser API requests."""
        if not os.path.exists(path) or not os.path.isdir(path):
            raise HTTPException(
                status_code=400, detail="Path not found or is not a directory"
            )
        items = []
        parent = os.path.dirname(path)
        if parent and os.path.isdir(parent):
            items.append({"name": "..", "path": parent})
        for name in os.listdir(path):
            full = os.path.join(path, name)
            items.append({"name": name, "path": full})
        return {"items": items}

    async def broadcast_event(self, module_id: str, event_data: Dict[str, Any]) -> None:
        """
        Broadcast an event to all WebSocket clients for a specific module.

        Args:
            module_id: ID of the module the event belongs to
            event_data: Event data to broadcast
        """
        # Apply throttling
        if not self.websocket_manager.apply_throttling(module_id, event_data):
            return

        # Notify callbacks for this module
        if module_id in self.callback_registry:
            for callback in self.callback_registry[module_id].values():
                if callback is not None:
                    try:
                        callback(event_data)
                    except Exception as e:
                        logging.error(f"Error in {module_id} callback: {e}")

        # Serialize and queue message
        try:
            serialized_data = self.websocket_manager.serialize_event(
                event_data, module_id
            )
            success = self.websocket_manager.queue_message(module_id, serialized_data)
            if not success:
                logging.warning(f"Failed to queue message for module {module_id}")
        except Exception as e:
            logging.error(f"Error in broadcast_event: {e}")

    def get_websocket_stats(self) -> Dict[str, Any]:
        """Get WebSocket performance statistics."""
        return self.websocket_manager.get_all_stats()

    def start_server(
        self, host: str = "127.0.0.1", port: int = 8000, block: bool = False
    ) -> None:
        """
        Start the API Explorer server.

        Args:
            host: Host to bind the server to
            port: Port to bind the server to
            block: Whether to block the current thread (True) or run in background (False)
        """
        # Include all module routers
        for module_id, module_info in self.modules.items():
            router = module_info.get("router")
            if router:
                self.app.include_router(router)

        if self.is_running:
            logging.info(
                f"API Explorer server already running at http://{self.server_host}:{self.server_port}"
            )
            return

        # Check if the specified port is already in use
        original_port = port
        while self._is_port_in_use(host, port):
            logging.info(
                f"Port {port} is already in use, looking for an alternative port..."
            )
            port += 1
            if port > 8100:
                logging.error("Could not find an available port in range 8000-8100")
                return

        if port != original_port:
            logging.info(f"Using alternative port {port}")

        self.server_host = host
        self.server_port = port

        if block:
            logging.info(f"API Explorer server starting at http://{host}:{port}")
            uvicorn.run(self.app, host=host, port=port)
        else:
            self.is_running = True

            def run_server() -> None:
                try:
                    config = uvicorn.Config(
                        self.app, host=host, port=port, log_level="info"
                    )
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
        """Check if a port is already in use."""
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

    def stop_server(self) -> None:
        """Stop the API Explorer server."""
        if self.server and self.is_running:
            self.server.should_exit = True
            self.is_running = False
            logging.info("API Explorer server stopping...")

    def register_module(
        self, module_id: str, name: str, description: str, show_data_table: bool = False
    ) -> None:
        """Register a new module with its own router."""
        if module_id in self.modules:
            raise ValueError(f"Module '{module_id}' already registered.")
        router = APIRouter(prefix=f"/api/{module_id}", tags=[name])
        self.modules[module_id] = {
            "name": name,
            "description": description,
            "method_groups": {},
            "router": router,
            "show_data_table": show_data_table,
        }

    def add_method_group(self, module_id: str, group_id: str, name: str) -> None:
        """Add a method group to a module."""
        if module_id not in self.modules:
            raise ValueError(f"Module '{module_id}' is not registered.")

        module = self.modules[module_id]
        if "method_groups" not in module:
            module["method_groups"] = {}

        module["method_groups"][group_id] = {"name": name, "methods": {}}

    def register_method(
        self,
        module_id: str,
        group_id: str,
        method_id: str,
        method_info: Dict[str, Any],
        handler_function: Callable[..., Any],
    ) -> None:
        """Register an API method with the Explorer."""
        if module_id not in self.modules:
            raise ValueError(f"Module '{module_id}' is not registered.")

        module = self.modules[module_id]
        if group_id not in module.get("method_groups", {}):
            raise ValueError(
                f"Group '{group_id}' is not defined in module '{module_id}'."
            )

        # Add method to the group
        module["method_groups"][group_id]["methods"][method_id] = method_info

        # Register the API endpoint
        router = module.get("router")
        if not router:
            raise ValueError(f"Router not found for module '{module_id}'.")

        self._register_endpoint(router, method_id, method_info, handler_function)

    def _register_endpoint(
        self,
        router: APIRouter,
        method_id: str,
        method_info: Dict[str, Any],
        handler_function: Callable[..., Any],
    ) -> None:
        """Register an individual endpoint with the router."""
        import inspect
        from fastapi import Query, Depends
        from pydantic import create_model, BaseModel
        from typing import Any, Dict, List, Optional

        method_type = method_info.get("type", "GET").upper()
        sig = inspect.signature(handler_function)
        param_names = list(sig.parameters.keys())

        if method_type == "GET":
            if len(param_names) == 0:

                @router.get(f"/{method_id}")
                async def endpoint() -> Any:
                    return await handler_function()

            else:
                param_dict: Dict[str, Any] = {}
                for param_id, param_info in method_info.get("params", {}).items():
                    param_type = param_info.get("type", "string").lower()
                    if param_type in ["number", "float"]:
                        param_dict[param_id] = (Optional[float], Query(None))
                    elif param_type in ["integer", "int"]:
                        param_dict[param_id] = (Optional[int], Query(None))
                    elif param_type in ["boolean", "bool"]:
                        param_dict[param_id] = (Optional[bool], Query(None))
                    else:
                        param_dict[param_id] = (Optional[str], Query(None))

                QueryModel = create_model(
                    f"{method_id.capitalize()}Query",
                    **param_dict,
                )

                @router.get(f"/{method_id}")
                async def endpoint(query: Any = Depends(QueryModel)) -> Any:
                    param_dict = {
                        k: v for k, v in query.dict().items() if v is not None
                    }
                    return await handler_function(**param_dict)

        else:
            # POST requests - Improved handling
            param_fields: Dict[str, Any] = {}
            for param_id, param_info in method_info.get("params", {}).items():
                param_type = param_info.get("type", "string").lower()

                # Map API types to Python types
                if param_type in ["number", "float"]:
                    field_type = float
                elif param_type in ["integer", "int"]:
                    field_type = int
                elif param_type in ["boolean", "bool"]:
                    field_type = bool
                elif param_type in ["dict", "object"]:
                    field_type = Dict[str, Any]
                elif param_type in ["list", "array"]:
                    field_type = List[Any]
                else:
                    field_type = str

                if param_info.get("required", False):
                    param_fields[param_id] = (field_type, ...)
                else:
                    param_fields[param_id] = (Optional[field_type], None)

            # Create the Pydantic model properly
            RequestModel = create_model(
                f"{method_id.capitalize()}Request",
                __base__=BaseModel,  # Ensure it inherits from BaseModel
                **param_fields,
            )

            @router.post(f"/{method_id}")
            async def endpoint(
                request_data: RequestModel,
            ) -> Any:  # Use the specific model type
                # Safely extract data from the Pydantic model
                try:
                    if hasattr(request_data, "model_dump"):
                        # Pydantic v2
                        data_dict = request_data.model_dump(
                            exclude_unset=True, exclude_none=True
                        )
                    elif hasattr(request_data, "dict"):
                        # Pydantic v1
                        data_dict = request_data.dict(
                            exclude_unset=True, exclude_none=True
                        )
                    else:
                        # Fallback
                        data_dict = {
                            k: v
                            for k, v in vars(request_data).items()
                            if v is not None and not k.startswith("_")
                        }
                except Exception as e:
                    logging.error(f"Error extracting data from request model: {e}")
                    data_dict = {}

                return await handler_function(**data_dict)
