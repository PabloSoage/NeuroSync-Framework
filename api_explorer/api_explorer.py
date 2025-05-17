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
                        
                        <div class="ws-controls">
                            <button class="btn btn-primary" id="{module_id}-connect-ws-btn" 
                                    onclick="connectWebSocket('{module_id}')">Connect WebSocket</button>
                            <button class="btn btn-danger" id="{module_id}-disconnect-ws-btn" 
                                    onclick="disconnectWebSocket('{module_id}')" disabled>Disconnect</button>
                            <button class="btn btn-secondary" id="{module_id}-clear-events-btn" 
                                    onclick="clearEvents('{module_id}')">Clear Events</button>
                            
                            <span id="{module_id}-connection-status" class="connection-status disconnected"></span>
                            <span>WebSocket Status</span>
                            
                            <span id="{module_id}-event-count" class="event-count">Events: 0</span>
                        </div>
                        
                        <div class="form-check form-switch mb-3">
                            <input class="form-check-input" type="checkbox" id="{module_id}-auto-scroll" checked>
                            <label class="form-check-label" for="{module_id}-auto-scroll">Auto-scroll</label>
                        </div>
                        
                        <div class="real-time-container" id="{module_id}-events-container">
                            <div class="event event-system">Not connected. Click "Connect WebSocket" to start receiving events.</div>
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
        
        # Complete HTML template with proper CSS styling
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
                    height: 400px;
                    overflow-y: auto;
                    border: 1px solid #dee2e6;
                    padding: 10px;
                    border-radius: 5px;
                    background-color: #1e1e1e;
                    font-family: 'Courier New', monospace;
                    color: #f0f0f0;
                }}
                .event {{
                    margin-bottom: 8px;
                    padding: 8px;
                    border-radius: 3px;
                    word-wrap: break-word;
                    overflow-wrap: break-word;
                    white-space: pre-wrap;
                }}
                .event-key {{ background-color: rgba(100, 150, 200, 0.2); border-left: 3px solid #4b6cb7; }}
                .event-mouse {{ background-color: rgba(100, 200, 100, 0.2); border-left: 3px solid #5cb85c; }}
                .event-button {{ background-color: rgba(200, 150, 100, 0.2); border-left: 3px solid #f0ad4e; }}
                .event-controller {{ background-color: rgba(150, 100, 200, 0.2); border-left: 3px solid #8e44ad; }}
                .event-system {{ background-color: rgba(80, 80, 80, 0.2); border-left: 3px solid #777777; }}
                .event-time {{ 
                    font-size: 0.8em; 
                    color: #aaaaaa; 
                    display: block;
                    margin-bottom: 5px;
                }}
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
                .ws-controls {{
                    margin-bottom: 15px;
                    display: flex;
                    gap: 10px;
                    align-items: center;
                }}
                .event-count {{
                    color: #aaaaaa;
                    font-size: 0.9em;
                    margin-left: auto;
                }}
                .connection-status {{
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }}
                .connected {{ background-color: #5cb85c; }}
                .disconnected {{ background-color: #d9534f; }}
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
                    const statusIndicator = document.getElementById(`${{moduleId}}-connection-status`);
                    
                    // Clear previous events
                    eventsContainer.innerHTML = '';
                    
                    // Create WebSocket connection
                    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    webSockets[moduleId] = new WebSocket(`${{wsProtocol}}//${{window.location.host}}/ws/${{moduleId}}`);
                    
                    // Event counter
                    let eventCount = 0;
                    const eventCountEl = document.getElementById(`${{moduleId}}-event-count`);
                    
                    // Update UI to show connecting state
                    if (statusIndicator) statusIndicator.className = 'connection-status disconnected';
                    addEvent(moduleId, 'Connecting to WebSocket...', 'system');
                    
                    webSockets[moduleId].onopen = function(e) {{
                        connectBtn.disabled = true;
                        disconnectBtn.disabled = false;
                        if (statusIndicator) statusIndicator.className = 'connection-status connected';
                        addEvent(moduleId, 'WebSocket connection established', 'system');
                        
                        // Ping the server every 30 seconds to keep the connection alive
                        webSockets[moduleId].pingInterval = setInterval(() => {{
                            if (webSockets[moduleId] && webSockets[moduleId].readyState === WebSocket.OPEN) {{
                                webSockets[moduleId].send(JSON.stringify({{ command: 'ping' }}));
                            }}
                        }}, 30000);
                    }};
                    
                    webSockets[moduleId].onmessage = function(event) {{
                        try {{
                            const data = JSON.parse(event.data);
                            
                            // Skip system messages like pong responses
                            if (data.response === 'pong') return;
                            
                            // Update event counter
                            eventCount++;
                            if (eventCountEl) eventCountEl.textContent = `Events: ${{eventCount}}`;
                            
                            // Determine event type for styling
                            let eventClass = 'event';
                            let eventType = data.event_type || 'unknown';
                            
                            if (eventType.includes('key')) {{
                                eventClass += ' event-key';
                            }} else if (eventType.includes('mouse')) {{
                                eventClass += ' event-mouse';
                            }} else if (eventType.includes('button') || eventType.includes('click')) {{
                                eventClass += ' event-button';
                            }} else if (eventType.includes('controller') || eventType.includes('axis')) {{
                                eventClass += ' event-controller';
                            }} else {{
                                eventClass += ' event-system';
                            }}
                            
                            // Format event data for display
                            const formattedData = formatEventData(data);
                            
                            // Format timestamp
                            let timeStr = '';
                            if (data.timestamp) {{
                                const date = new Date(data.timestamp * 1000);
                                timeStr = `<span class="event-time">${{date.toLocaleTimeString()}}.${{date.getMilliseconds().toString().padStart(3, '0')}}</span>`;
                            }}
                            
                            // Create and append event element
                            const eventElement = document.createElement('div');
                            eventElement.className = eventClass;
                            eventElement.innerHTML = `${{timeStr}}${{formattedData}}`;
                            eventsContainer.appendChild(eventElement);
                            
                            // Auto-scroll if enabled
                            if (document.getElementById(`${{moduleId}}-auto-scroll`).checked) {{
                                eventsContainer.scrollTop = eventsContainer.scrollHeight;
                            }}
                        }} catch (e) {{
                            console.error('Error parsing WebSocket message:', e, event.data);
                            addEvent(moduleId, `Error parsing message: ${{e.message}}`, 'system');
                        }}
                    }};
                    
                    webSockets[moduleId].onclose = function(event) {{
                        if (webSockets[moduleId].pingInterval) {{
                            clearInterval(webSockets[moduleId].pingInterval);
                        }}
                        
                        if (statusIndicator) statusIndicator.className = 'connection-status disconnected';
                        
                        if (event.wasClean) {{
                            addEvent(moduleId, `WebSocket connection closed cleanly, code=${{event.code}}, reason=${{event.reason}}`, 'system');
                        }} else {{
                            addEvent(moduleId, 'WebSocket connection died', 'system');
                        }}
                        
                        connectBtn.disabled = false;
                        disconnectBtn.disabled = true;
                        webSockets[moduleId] = null;
                    }};
                    
                    webSockets[moduleId].onerror = function(error) {{
                        if (statusIndicator) statusIndicator.className = 'connection-status disconnected';
                        addEvent(moduleId, `WebSocket error: ${{error.message || 'Unknown error'}}`, 'system');
                    }};
                }}
                
                function disconnectWebSocket(moduleId) {{
                    if (webSockets[moduleId]) {{
                        webSockets[moduleId].close();
                        if (webSockets[moduleId].pingInterval) {{
                            clearInterval(webSockets[moduleId].pingInterval);
                        }}
                        webSockets[moduleId] = null;
                        
                        document.getElementById(`${{moduleId}}-connect-ws-btn`).disabled = false;
                        document.getElementById(`${{moduleId}}-disconnect-ws-btn`).disabled = true;
                        
                        const statusIndicator = document.getElementById(`${{moduleId}}-connection-status`);
                        if (statusIndicator) statusIndicator.className = 'connection-status disconnected';
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
                
                // Function to format event data for better display
                function formatEventData(data) {{
                    // Create a simplified representation for display
                    let output = '';
                    
                    // Add event type
                    if (data.event_type) {{
                        output += `<strong>Event:</strong> ${{data.event_type}}\\n`;
                    }}
                    
                    // Add key info if present
                    if (data.key) {{
                        output += `<strong>Key:</strong> ${{data.key}}\\n`;
                    }}
                    
                    // Add active keys if present
                    if (data.active_keys && data.active_keys.length > 0) {{
                        output += `<strong>Active Keys:</strong> ${{data.active_keys.join(', ')}}\\n`;
                    }}
                    
                    // Add mouse position if present
                    if (data.mouse_x !== undefined && data.mouse_y !== undefined) {{
                        output += `<strong>Mouse Position:</strong> (${{data.mouse_x}}, ${{data.mouse_y}})\\n`;
                    }}
                    
                    // Add mouse button if present
                    if (data.button_pressed) {{
                        output += `<strong>Button:</strong> ${{data.button_pressed}}\\n`;
                    }}
                    
                    // Add direction if present
                    if (data.direction) {{
                        output += `<strong>Direction:</strong> ${{data.direction}}\\n`;
                    }}
                    
                    // Add joystick position if present
                    if (data.rel_x !== undefined && data.rel_y !== undefined) {{
                        output += `<strong>Joystick:</strong> (${{data.rel_x.toFixed(2)}}, ${{data.rel_y.toFixed(2)}})\\n`;
                    }}
                    
                    // If there's no specific data to display, show the full object
                    if (!output) {{
                        output = JSON.stringify(data, null, 2);
                    }}
                    
                    return output;
                }}
            </script>
        </body>
        </html>
        """
        
        return html_content
    
    def _generate_server_info_html(self) -> str:
        """Generate HTML with information about API Explorer servers."""
        # Try to detect other API Explorer servers
        other_servers = self._detect_other_servers()
        
        if not self.server_port:
            current_server = "Not yet started"
        else:
            current_server = f"http://{self.server_host}:{self.server_port}"
        
        html = f"""
        <div class="server-info mb-4">
            <h4>API Explorer Servers</h4>
            <p>Current server: <strong>{current_server}</strong></p>
        """
        
        if other_servers:
            html += """
            <p>Other API Explorer servers found:</p>
            <ul>
            """
            
            for server in other_servers:
                html += f"""
                <li><a href="{server}" target="_blank">{server}</a></li>
                """
            
            html += """
            </ul>
            """
        else:
            html += """
            <p>No other API Explorer servers detected.</p>
            """
        
        html += """
        </div>
        """
        return html
    
    def _detect_other_servers(self) -> List[str]:
        """
        Try to detect other API Explorer servers running on different ports.
        
        Returns:
            List[str]: List of server URLs
        """
        other_servers = []
        base_port = 8000
        max_port = 8010
        
        for port in range(base_port, max_port + 1):
            # Skip current server port
            if port == self.server_port:
                continue
                
            # Try to connect to potential server
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                
                if result == 0:  # Port is open
                    other_servers.append(f"http://127.0.0.1:{port}")
            except:
                pass
                
        return other_servers
    
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
