"""
Modular API Explorer.

This module provides a reusable, dynamic API Explorer that can be used by different modules
to expose their APIs through a web interface.
"""

import os
import sys
import inspect
import threading
import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, Union, Type
import logging
from enum import Enum

# FastAPI imports
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query, Body, APIRouter, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, Field, create_model


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
        
        # Set up templates and static files
        self._setup_directories()
        self.templates = Jinja2Templates(directory="templates")
        self.app.mount("/static", StaticFiles(directory="static"), name="static")
        
        # Module registry - stores information about registered modules
        self.modules = {}
        
        # WebSocket connections
        self.active_connections: List[WebSocket] = []
        
        # Callback registry
        self.callback_registry: Dict[str, Dict[int, Callable]] = {}
        self.next_callback_id = 0
        
        # Setup basic routes
        self._setup_routes()
        
        # Server control
        self.server = None
        self.server_thread = None
        self.is_running = False
    
    def _setup_directories(self):
        """Set up necessary directories."""
        os.makedirs("templates", exist_ok=True)
        os.makedirs("static", exist_ok=True)
    
    def _setup_routes(self):
        """Set up the basic routes for the API Explorer."""
        # Home page route
        @self.app.get("/", response_class=HTMLResponse)
        async def get_home():
            return self._generate_html()
        
        # WebSocket endpoint for real-time events
        @self.app.websocket("/ws/{module_id}")
        async def websocket_endpoint(websocket: WebSocket, module_id: str):
            await websocket.accept()
            # Add connection info with module ID for routing
            websocket.scope["module_id"] = module_id
            self.active_connections.append(websocket)
            
            try:
                # Keep connection open
                while True:
                    # Wait for client messages (can be used to implement commands)
                    data = await websocket.receive_text()
                    # We don't need to do anything with client messages for now
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
            finally:
                # Ensure cleanup happens
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
    
    def _generate_html(self) -> str:
        """Generate HTML for the home page."""
        modules_html = ""
        for module_id, module_info in self.modules.items():
            # Create a module section
            modules_html += f"""
            <div class="module-section mb-5" id="module-{module_id}">
                <h2 class="mb-3">{module_info['name']} API</h2>
                <p class="mb-4">{module_info['description']}</p>
                
                <ul class="nav nav-tabs" id="{module_id}Tabs" role="tablist">
                    <li class="nav-item">
                        <a class="nav-link active" id="{module_id}-explorer-tab" data-bs-toggle="tab" 
                           href="#{module_id}-explorer" role="tab">API Explorer</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" id="{module_id}-realtime-tab" data-bs-toggle="tab" 
                           href="#{module_id}-realtime" role="tab">Real-time Events</a>
                    </li>
                </ul>
                
                <div class="tab-content" id="{module_id}TabContent">
                    <!-- API Explorer Tab -->
                    <div class="tab-pane fade show active" id="{module_id}-explorer" role="tabpanel">
                        <div class="row mb-3">
                            <div class="col-md-3">
                                <div class="card">
                                    <div class="card-header">API Methods</div>
                                    <div class="card-body p-0">
                                        <div class="list-group list-group-flush">
                                            {self._generate_method_links(module_id, module_info)}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="col-md-9">
                                {self._generate_method_cards(module_id, module_info)}
                            </div>
                        </div>
                    </div>
                    
                    <!-- Real-time Events Tab -->
                    <div class="tab-pane fade" id="{module_id}-realtime" role="tabpanel">
                        <h3 class="mt-3">Real-time Events</h3>
                        <p>Connect to the WebSocket to see real-time events as they happen.</p>
                        
                        <div class="mb-3">
                            <button class="btn btn-primary" id="{module_id}-connect-ws-btn" 
                                    onclick="connectWebSocket('{module_id}')">Connect WebSocket</button>
                            <button class="btn btn-danger" id="{module_id}-disconnect-ws-btn" 
                                    onclick="disconnectWebSocket('{module_id}')" disabled>Disconnect</button>
                            <button class="btn btn-secondary" id="{module_id}-clear-events-btn" 
                                    onclick="clearEvents('{module_id}')">Clear Events</button>
                        </div>
                        
                        <div>
                            <label>
                                <input type="checkbox" id="{module_id}-auto-scroll" checked> Auto-scroll
                            </label>
                        </div>
                        
                        <div class="real-time-container" id="{module_id}-events-container">
                            <div class="text-muted">Not connected. Click "Connect WebSocket" to start receiving events.</div>
                        </div>
                    </div>
                </div>
            </div>
            <hr>
            """
        
        # If no modules registered, show a message
        if not modules_html:
            modules_html = """
            <div class="alert alert-info">
                <h4>No API Modules Registered</h4>
                <p>This API Explorer is waiting for modules to register their APIs.</p>
                <p>Once a module registers, its API methods will appear here.</p>
            </div>
            """
        
        # Complete HTML template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dynamic API Explorer</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .nav-link {{
                    color: #007bff;
                    cursor: pointer;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                .method-card {{
                    margin-bottom: 15px;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    background-color: #ffffff;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }}
                .method-header {{
                    padding: 12px 15px;
                    background-color: #f1f3f5;
                    border-bottom: 1px solid #dee2e6;
                    cursor: pointer;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .method-body {{
                    padding: 15px;
                    display: none;
                }}
                .method-body.active {{
                    display: block;
                }}
                .form-group {{
                    margin-bottom: 15px;
                }}
                pre {{
                    background-color: #f8f9fa;
                    padding: 10px;
                    border-radius: 5px;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
                .real-time-container {{
                    height: 300px;
                    overflow-y: auto;
                    border: 1px solid #dee2e6;
                    padding: 10px;
                    border-radius: 5px;
                    background-color: #f8f9fa;
                    font-family: monospace;
                }}
                .event {{
                    margin-bottom: 8px;
                    padding: 5px;
                    border-radius: 3px;
                }}
                .event-key {{ background-color: #e3f2fd; }}
                .event-mouse {{ background-color: #e8f5e9; }}
                .event-button {{ background-color: #fff8e1; }}
                .event-controller {{ background-color: #f3e5f5; }}
                .badge {{
                    margin-left: 8px;
                }}
                .http-get {{ background-color: #28a745; color: white; }}
                .http-post {{ background-color: #007bff; color: white; }}
                .execute-btn {{
                    background-color: #007bff;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                    cursor: pointer;
                }}
                .execute-btn:hover {{
                    background-color: #0069d9;
                }}
                .card-header {{
                    background-color: #f8f9fa;
                    font-weight: bold;
                }}
                .tab-content {{
                    padding: 15px 0;
                }}
                .module-section {{
                    margin-top: 30px;
                    padding-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="mb-4">Dynamic API Explorer</h1>
                
                {modules_html}
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
            <script>
                // JavaScript for API Explorer functionality
                const webSockets = {{}};
                
                // Toggle method details
                function toggleMethod(moduleId, methodId) {{
                    const methodBody = document.getElementById(`${{moduleId}}-${{methodId}}`);
                    methodBody.classList.toggle('active');
                }}
                
                // Execute API method
                async function executeMethod(moduleId, methodId) {{
                    const responseElem = document.getElementById(`${{moduleId}}-${{methodId}}_response`);
                    responseElem.textContent = "Loading...";
                    
                    try {{
                        // Get parameters from form elements
                        const paramElements = document.querySelectorAll(`[id^="${{moduleId}}-${{methodId}}_param_"]`);
                        let url = `/api/${{moduleId}}/${{methodId}}`;
                        let options = {{ method: 'GET' }};
                        let body = null;
                        let queryParams = [];
                        
                        // Check if this is a POST method
                        const methodType = document.getElementById(`${{moduleId}}-${{methodId}}_type`);
                        if (methodType && methodType.value === 'POST') {{
                            options.method = 'POST';
                            body = {{}};
                        }}
                        
                        // Process parameters
                        paramElements.forEach(param => {{
                            const paramName = param.id.replace(`${{moduleId}}-${{methodId}}_param_`, '');
                            const paramValue = param.value.trim();
                            
                            if (paramValue) {{
                                if (options.method === 'GET') {{
                                    queryParams.push(`${{paramName}}=${{encodeURIComponent(paramValue)}}`);
                                }} else {{
                                    // For POST, add to body
                                    body[paramName] = paramValue;
                                }}
                            }}
                        }});
                        
                        // Add query parameters to URL for GET requests
                        if (queryParams.length > 0 && options.method === 'GET') {{
                            url += `?${{queryParams.join('&')}}`;
                        }}
                        
                        // Set up headers and body for POST requests
                        if (options.method === 'POST' && body) {{
                            options.headers = {{ 'Content-Type': 'application/json' }};
                            options.body = JSON.stringify(body);
                        }}
                        
                        // Make API request
                        const response = await fetch(url, options);
                        const data = await response.json();
                        
                        // Update response element
                        responseElem.textContent = JSON.stringify(data, null, 2);
                        
                    }} catch (error) {{
                        responseElem.textContent = `Error: ${{error.message}}`;
                    }}
                }}
                
                // WebSocket connection for real-time events
                function connectWebSocket(moduleId) {{
                    if (webSockets[moduleId]) {{
                        return; // Already connected
                    }}
                    
                    const connectBtn = document.getElementById(`${{moduleId}}-connect-ws-btn`);
                    const disconnectBtn = document.getElementById(`${{moduleId}}-disconnect-ws-btn`);
                    const eventsContainer = document.getElementById(`${{moduleId}}-events-container`);
                    
                    // Clear previous events
                    eventsContainer.innerHTML = '';
                    
                    // Create WebSocket connection
                    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    webSockets[moduleId] = new WebSocket(`${{wsProtocol}}//${{window.location.host}}/ws/${{moduleId}}`);
                    
                    webSockets[moduleId].onopen = function(e) {{
                        connectBtn.disabled = true;
                        disconnectBtn.disabled = false;
                        addEvent(moduleId, 'WebSocket connection established', 'success');
                    }};
                    
                    webSockets[moduleId].onmessage = function(event) {{
                        try {{
                            const data = JSON.parse(event.data);
                            
                            // Determine event type for styling
                            let eventClass = 'event';
                            if (data.event_type) {{
                                if (data.event_type.includes('key')) {{
                                    eventClass += ' event-key';
                                }} else if (data.event_type.includes('mouse')) {{
                                    eventClass += ' event-mouse';
                                }} else if (data.event_type.includes('button')) {{
                                    eventClass += ' event-button';
                                }} else if (data.event_type.includes('controller')) {{
                                    eventClass += ' event-controller';
                                }}
                            }}
                            
                            // Format and display event
                            const eventElement = document.createElement('div');
                            eventElement.className = eventClass;
                            eventElement.textContent = JSON.stringify(data);
                            eventsContainer.appendChild(eventElement);
                            
                            // Auto-scroll if enabled
                            if (document.getElementById(`${{moduleId}}-auto-scroll`).checked) {{
                                eventsContainer.scrollTop = eventsContainer.scrollHeight;
                            }}
                        }} catch (e) {{
                            console.error('Error parsing WebSocket message:', e);
                        }}
                    }};
                    
                    webSockets[moduleId].onclose = function(event) {{
                        if (event.wasClean) {{
                            addEvent(moduleId, `WebSocket connection closed cleanly, code=${{event.code}}, reason=${{event.reason}}`, 'info');
                        }} else {{
                            addEvent(moduleId, 'WebSocket connection died', 'error');
                        }}
                        
                        connectBtn.disabled = false;
                        disconnectBtn.disabled = true;
                        webSockets[moduleId] = null;
                    }};
                    
                    webSockets[moduleId].onerror = function(error) {{
                        addEvent(moduleId, `WebSocket error: ${{error.message}}`, 'error');
                    }};
                }}
                
                function disconnectWebSocket(moduleId) {{
                    if (webSockets[moduleId]) {{
                        webSockets[moduleId].close();
                        webSockets[moduleId] = null;
                        
                        document.getElementById(`${{moduleId}}-connect-ws-btn`).disabled = false;
                        document.getElementById(`${{moduleId}}-disconnect-ws-btn`).disabled = true;
                    }}
                }}
                
                function clearEvents(moduleId) {{
                    document.getElementById(`${{moduleId}}-events-container`).innerHTML = '';
                }}
                
                function addEvent(moduleId, message, type = 'info') {{
                    const eventsContainer = document.getElementById(`${{moduleId}}-events-container`);
                    const eventElement = document.createElement('div');
                    eventElement.className = `event event-${{type}}`;
                    eventElement.textContent = message;
                    eventsContainer.appendChild(eventElement);
                    
                    // Auto-scroll if enabled
                    if (document.getElementById(`${{moduleId}}-auto-scroll`).checked) {{
                        eventsContainer.scrollTop = eventsContainer.scrollHeight;
                    }}
                }}
            </script>
        </body>
        </html>
        """
        
        return html_content
    
    def _generate_method_links(self, module_id: str, module_info: Dict) -> str:
        """Generate HTML for the method links sidebar."""
        method_groups = module_info.get('method_groups', {})
        if not method_groups:
            return "<a href='#' class='list-group-item list-group-item-action disabled'>No methods available</a>"
        
        links_html = ""
        for group_id, group_info in method_groups.items():
            links_html += f"<a href='#{module_id}-{group_id}' class='list-group-item list-group-item-action'>{group_info['name']}</a>"
        
        return links_html
    
    def _generate_method_cards(self, module_id: str, module_info: Dict) -> str:
        """Generate HTML for the method cards."""
        method_groups = module_info.get('method_groups', {})
        if not method_groups:
            return "<div class='alert alert-info'>No methods available for this module.</div>"
        
        cards_html = ""
        for group_id, group_info in method_groups.items():
            # Add group header
            cards_html += f"<h3 id='{module_id}-{group_id}' class='mt-4'>{group_info['name']}</h3>"
            
            # Add methods in this group
            methods = group_info.get('methods', {})
            for method_id, method_info in methods.items():
                # Method type badge
                method_type = method_info.get('type', 'GET')
                badge_class = "http-post" if method_type == "POST" else "http-get"
                
                # Parameter handling
                params_html = ""
                for param_id, param_info in method_info.get('params', {}).items():
                    param_type = param_info.get('type', 'text')
                    param_desc = param_info.get('description', '')
                    param_required = param_info.get('required', False)
                    
                    if param_type == 'select':
                        # For dropdown parameters
                        options_html = ""
                        for option in param_info.get('options', []):
                            options_html += f"<option value='{option}'>{option}</option>"
                        
                        params_html += f"""
                        <div class="form-group">
                            <label for="{module_id}-{method_id}_param_{param_id}">{param_id}{' (required)' if param_required else ''}:</label>
                            <select class="form-control" id="{module_id}-{method_id}_param_{param_id}">
                                {options_html}
                            </select>
                            <small class="form-text text-muted">{param_desc}</small>
                        </div>
                        """
                    else:
                        # For text/number parameters
                        placeholder = param_info.get('placeholder', '')
                        params_html += f"""
                        <div class="form-group">
                            <label for="{module_id}-{method_id}_param_{param_id}">{param_id}{' (required)' if param_required else ''}:</label>
                            <input type="{param_type}" class="form-control" id="{module_id}-{method_id}_param_{param_id}" 
                                   placeholder="{placeholder}">
                            <small class="form-text text-muted">{param_desc}</small>
                        </div>
                        """
                
                # Hidden field to store method type
                type_field = f'<input type="hidden" id="{module_id}-{method_id}_type" value="{method_type}">'
                
                # Create the complete method card
                cards_html += f"""
                <div class="method-card">
                    <div class="method-header" onclick="toggleMethod('{module_id}', '{method_id}')">
                        <span>{method_info.get('name', method_id)}</span>
                        <span class="badge {badge_class}">{method_type}</span>
                    </div>
                    <div class="method-body" id="{module_id}-{method_id}">
                        <p>{method_info.get('description', '')}</p>
                        {type_field}
                        {params_html}
                        <button class="execute-btn" onclick="executeMethod('{module_id}', '{method_id}')">Execute</button>
                        <div class="mt-3">
                            <h5>Response:</h5>
                            <pre id="{module_id}-{method_id}_response">// Response will appear here</pre>
                        </div>
                    </div>
                </div>
                """
        
        return cards_html
    
    def register_module(self, module_id: str, name: str, description: str) -> None:
        """
        Register a new module with the API Explorer.
        
        Args:
            module_id: Unique identifier for the module
            name: Display name for the module
            description: Description of the module's functionality
        """
        if module_id in self.modules:
            # Update existing module info
            self.modules[module_id].update({
                'name': name,
                'description': description
            })
        else:
            # Add new module
            self.modules[module_id] = {
                'name': name,
                'description': description,
                'method_groups': {},
                'router': APIRouter(prefix=f"/api/{module_id}", tags=[name])
            }
            
            # Create callback registry for this module
            self.callback_registry[module_id] = {}
    
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
    
    def register_event_callback(self, module_id: str, callback: Callable) -> int:
        """
        Register a callback for a module's events.
        
        Args:
            module_id: ID of the module to register callback for
            callback: Function to call with events
            
        Returns:
            Callback ID for later unregistering
        """
        if module_id not in self.callback_registry:
            self.callback_registry[module_id] = {}
        
        callback_id = self.next_callback_id
        self.next_callback_id += 1
        
        self.callback_registry[module_id][callback_id] = callback
        return callback_id
    
    def unregister_event_callback(self, module_id: str, callback_id: int) -> bool:
        """
        Unregister a previously registered callback.
        
        Args:
            module_id: ID of the module the callback belongs to
            callback_id: ID of the callback to remove
            
        Returns:
            True if successfully unregistered, False otherwise
        """
        if (module_id in self.callback_registry and 
            callback_id in self.callback_registry[module_id]):
            self.callback_registry[module_id][callback_id] = None
            return True
        return False
    
    async def broadcast_event(self, module_id: str, event_data: Dict) -> None:
        """
        Broadcast an event to all WebSocket clients for a specific module.
        
        Args:
            module_id: ID of the module the event belongs to
            event_data: Event data to broadcast
        """
        # Notify callbacks for this module
        if module_id in self.callback_registry:
            for callback in self.callback_registry[module_id].values():
                if callback:
                    try:
                        callback(event_data)
                    except Exception as e:
                        logging.error(f"Error in {module_id} callback: {e}")
        
        # Send to all connected WebSockets for this module
        for connection in self.active_connections:
            if connection.scope.get("module_id") == module_id:
                try:
                    await connection.send_json(event_data)
                except Exception as e:
                    logging.error(f"Error sending to WebSocket: {e}")
    
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
        
        if block:
            # Run in current thread (blocking)
            uvicorn.run(self.app, host=host, port=port)
        else:
            # Run in background thread
            if self.is_running:
                logging.warning("Server is already running")
                return
            
            self.is_running = True
            
            def run_server():
                config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
                self.server = uvicorn.Server(config)
                self.server.run()
                self.is_running = False
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            logging.info(f"API Explorer server started at http://{host}:{port}")
    
    def stop_server(self) -> None:
        """Stop the API Explorer server."""
        if self.server and self.is_running:
            self.server.should_exit = True
            self.is_running = False
            logging.info("API Explorer server stopping...")
