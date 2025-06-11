"""
Modular API Explorer.

This module provides a reusable, dynamic API Explorer that can be used by different modules
to expose their APIs through a web interface.
"""

import json
import logging
import os
import threading
import time
import asyncio
import queue
import random
from typing import Dict, List, Optional, Callable, Any, Type, Union, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

import uvicorn

# FastAPI imports
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Try to import orjson for faster JSON serialization
try:
    import orjson
    HAS_ORJSON = True
    print("Using orjson for high-performance JSON serialization")
except ImportError:
    HAS_ORJSON = False
    print("orjson not available, using standard json with optimizations")

class FastJSONSerializer:
    """Optimized JSON serializer with caching and performance optimizations."""
    
    def __init__(self):
        self._template_cache = {}
        self._field_cache = {}
        
    def serialize_event(self, event_data: Dict[str, Any], compact: bool = False) -> str:
        """Serialize event data with optimizations."""
        try:
            if HAS_ORJSON:
                return self._serialize_with_orjson(event_data, compact)
            else:
                return self._serialize_with_stdlib(event_data, compact)
        except Exception as e:
            logging.error(f"JSON serialization error: {e}")
            # Fallback to safe serialization
            return self._safe_serialize(event_data)
    
    def _serialize_with_orjson(self, data: Dict[str, Any], compact: bool) -> str:
        """Serialize using orjson (fastest option)."""
        if compact:
            # Use orjson's compact option for minimal size
            return orjson.dumps(data, option=orjson.OPT_SERIALIZE_NUMPY).decode()
        else:
            return orjson.dumps(data).decode()
    
    def _serialize_with_stdlib(self, data: Dict[str, Any], compact: bool) -> str:
        """Optimized stdlib JSON serialization."""
        if compact:
            # Minimal separators for smaller output
            return json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        else:
            # Standard format
            return json.dumps(data, ensure_ascii=False)
    
    def _safe_serialize(self, data: Any) -> str:
        """Safe fallback serialization that handles any data type."""
        try:
            # Sanitize data first
            clean_data = self._sanitize_for_json(data)
            return json.dumps(clean_data, separators=(',', ':'), ensure_ascii=False)
        except Exception:
            # Last resort: convert to string
            return json.dumps({"error": "serialization_failed", "data": str(data)})
    
    def _sanitize_for_json(self, obj: Any) -> Any:
        """Sanitize data to make it JSON serializable."""
        if isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._sanitize_for_json(item) for item in obj]
        elif isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj
        elif hasattr(obj, '__dict__'):
            return self._sanitize_for_json(obj.__dict__)
        else:
            return str(obj)
    
    def precompile_template(self, template_name: str, template_structure: Dict[str, Any]):
        """Precompile common JSON templates for even faster serialization."""
        self._template_cache[template_name] = template_structure
    
    def serialize_from_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """Serialize using a precompiled template."""
        if template_name not in self._template_cache:
            return self.serialize_event(data, compact=True)
        
        # Use template for structure, fill with data
        template = self._template_cache[template_name].copy()
        self._fill_template(template, data)
        
        return self.serialize_event(template, compact=True)
    
    def _fill_template(self, template: Any, data: Dict[str, Any]):
        """Fill template with actual data."""
        if isinstance(template, dict):
            for key, value in template.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    # Template variable
                    var_name = value[2:-1]
                    template[key] = data.get(var_name, None)
                elif isinstance(value, (dict, list)):
                    self._fill_template(value, data)
        elif isinstance(template, list):
            for item in template:
                self._fill_template(item, data)

@dataclass
class WorkerStats:
    """Statistics for a worker."""
    messages_processed: int = 0
    total_processing_time: float = 0.0
    last_activity: float = 0.0
    queue_size: int = 0
    
    @property
    def avg_processing_time(self) -> float:
        return self.total_processing_time / max(1, self.messages_processed)

class WebSocketWorkerPool:
    """Pool of workers for processing WebSocket messages."""
    
    def __init__(self, pool_size: int = None):
        # Auto-detect optimal pool size if not specified
        if pool_size is None:
            import multiprocessing
            pool_size = min(8, max(2, multiprocessing.cpu_count() - 1))
        
        self.pool_size = pool_size
        self.workers: List[asyncio.Task] = []
        self.worker_queues: List[queue.Queue] = []
        self.worker_stats: List[WorkerStats] = []
        self.shutdown_event = asyncio.Event()
        self.round_robin_index = 0
        self.load_balancer_lock = asyncio.Lock()
        
        print(f"Initializing WebSocket worker pool with {pool_size} workers")
        
        # Initialize queues and stats for each worker
        for i in range(pool_size):
            self.worker_queues.append(queue.Queue(maxsize=5000))
            self.worker_stats.append(WorkerStats())
    
    async def start_workers(self, module_id: str, connections: List):
        """Start all worker tasks."""
        for i in range(self.pool_size):
            worker_task = asyncio.create_task(
                self._worker_loop(i, module_id, connections)
            )
            self.workers.append(worker_task)
    
    async def stop_workers(self):
        """Stop all workers gracefully."""
        self.shutdown_event.set()
        
        # Cancel all worker tasks
        for worker in self.workers:
            worker.cancel()
        
        # Wait for all workers to finish
        try:
            await asyncio.gather(*self.workers, return_exceptions=True)
        except Exception as e:
            logging.error(f"Error stopping workers: {e}")
        
        self.workers.clear()
    
    def distribute_message(self, message: str) -> bool:
        """Distribute message to the least loaded worker."""
        try:
            # Find the worker with the smallest queue
            best_worker_idx = 0
            min_queue_size = self.worker_queues[0].qsize()
            
            for i in range(1, self.pool_size):
                queue_size = self.worker_queues[i].qsize()
                if queue_size < min_queue_size:
                    min_queue_size = queue_size
                    best_worker_idx = i
            
            # Try to add to the best worker's queue
            self.worker_queues[best_worker_idx].put_nowait(message)
            self.worker_stats[best_worker_idx].queue_size = self.worker_queues[best_worker_idx].qsize()
            return True
            
        except queue.Full:
            # If all queues are full, try round-robin with dropping
            for i in range(self.pool_size):
                worker_idx = (self.round_robin_index + i) % self.pool_size
                try:
                    # Try to make space by removing old messages
                    worker_queue = self.worker_queues[worker_idx]
                    if worker_queue.full():
                        # Remove up to 10 old messages
                        for _ in range(min(10, worker_queue.qsize())):
                            try:
                                worker_queue.get_nowait()
                            except queue.Empty:
                                break
                    
                    worker_queue.put_nowait(message)
                    self.worker_stats[worker_idx].queue_size = worker_queue.qsize()
                    self.round_robin_index = (worker_idx + 1) % self.pool_size
                    return True
                except queue.Full:
                    continue
            
            return False
    
    async def _worker_loop(self, worker_id: int, module_id: str, connections: List):
        """Main loop for a worker."""
        worker_queue = self.worker_queues[worker_id]
        worker_stats = self.worker_stats[worker_id]
        
        print(f"Worker {worker_id} started for module {module_id}")
        
        while not self.shutdown_event.is_set():
            try:
                messages_to_send = []
                start_time = time.time()
                
                # Collect messages in batch
                batch_size = 50  # Process up to 50 messages at once
                for _ in range(batch_size):
                    try:
                        message = worker_queue.get_nowait()
                        messages_to_send.append(message)
                    except queue.Empty:
                        break
                
                if messages_to_send:
                    # Send messages to all connections
                    await self._send_batch_to_connections(
                        worker_id, messages_to_send, connections
                    )
                    
                    # Update worker statistics
                    processing_time = time.time() - start_time
                    worker_stats.messages_processed += len(messages_to_send)
                    worker_stats.total_processing_time += processing_time
                    worker_stats.last_activity = time.time()
                    worker_stats.queue_size = worker_queue.qsize()
                else:
                    # No messages, sleep briefly
                    await asyncio.sleep(0.001)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in worker {worker_id}: {e}")
                await asyncio.sleep(0.01)
        
        print(f"Worker {worker_id} stopped")
    
    async def _send_batch_to_connections(
        self, worker_id: int, messages: List[str], connections: List
    ):
        """Send a batch of messages to all connections."""
        if not connections:
            return
        
        # Make a copy to avoid modification during iteration
        current_connections = connections[:]
        dead_connections = []
        
        for connection in current_connections:
            try:
                # Send all messages in the batch
                for message in messages:
                    await connection.send_text(message)
            except Exception as e:
                logging.error(f"Worker {worker_id}: Error sending to WebSocket: {e}")
                dead_connections.append(connection)
        
        # Remove dead connections from the original list
        for dead_conn in dead_connections:
            if dead_conn in connections:
                connections.remove(dead_conn)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all workers."""
        stats = {
            "pool_size": self.pool_size,
            "workers": []
        }
        
        total_processed = 0
        total_queue_size = 0
        
        for i, worker_stats in enumerate(self.worker_stats):
            worker_data = {
                "worker_id": i,
                "messages_processed": worker_stats.messages_processed,
                "avg_processing_time_ms": worker_stats.avg_processing_time * 1000,
                "queue_size": worker_stats.queue_size,
                "last_activity": worker_stats.last_activity
            }
            stats["workers"].append(worker_data)
            total_processed += worker_stats.messages_processed
            total_queue_size += worker_stats.queue_size
        
        stats["total_messages_processed"] = total_processed
        stats["total_queue_size"] = total_queue_size
        stats["avg_queue_size"] = total_queue_size / self.pool_size if self.pool_size > 0 else 0
        
        return stats

class WebSocketManager:
    """Manages WebSocket connections with thread-safe message queuing and worker pools."""
    
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
        self.worker_pools: Dict[str, WebSocketWorkerPool] = {}
        self.shutdown_events: Dict[str, asyncio.Event] = {}
        
        # Initialize fast JSON serializer
        self.json_serializer = FastJSONSerializer()
        
        # Precompile common templates
        self._setup_json_templates()
        
        # Statistics tracking
        self.stats_last_update = time.time()
        self.stats_update_interval = 30.0  # Update stats every 30 seconds

    def _setup_json_templates(self):
        """Setup precompiled JSON templates for common event types."""
        # Template for visualization data events
        vis_template = {
            "event_type": "${event_type}",
            "timestamp": "${timestamp}",
            "visualization_data": {
                "list_view": "${list_view}"
            }
        }
        self.json_serializer.precompile_template("visualization", vis_template)
        
        # Template for simple events
        simple_template = {
            "event_type": "${event_type}",
            "timestamp": "${timestamp}",
            "key": "${key}",
            "value": "${value}"
        }
        self.json_serializer.precompile_template("simple", simple_template)

    async def add_connection(self, module_id: str, websocket: WebSocket):
        """Add a WebSocket connection for a module."""
        if module_id not in self.connections:
            self.connections[module_id] = []
            self.shutdown_events[module_id] = asyncio.Event()
            
            # Create worker pool for this module
            pool_size = self._determine_pool_size(module_id)
            self.worker_pools[module_id] = WebSocketWorkerPool(pool_size)
            
            # Start workers
            await self.worker_pools[module_id].start_workers(
                module_id, self.connections[module_id]
            )
            
        self.connections[module_id].append(websocket)
        
    async def remove_connection(self, module_id: str, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if module_id in self.connections:
            if websocket in self.connections[module_id]:
                self.connections[module_id].remove(websocket)
                
            # If no more connections, stop the worker pool
            if not self.connections[module_id]:
                if module_id in self.shutdown_events:
                    self.shutdown_events[module_id].set()
                
                if module_id in self.worker_pools:
                    await self.worker_pools[module_id].stop_workers()
                    del self.worker_pools[module_id]
                
                del self.connections[module_id]
                del self.shutdown_events[module_id]
    
    def _determine_pool_size(self, module_id: str) -> int:
        """Determine optimal pool size based on module characteristics."""
        # You can customize this based on known module characteristics
        # For now, use a default that scales with expected load
        
        # High-frequency modules get more workers
        high_freq_modules = ["eeg", "emg", "sensor_data", "biosignals"]
        if any(keyword in module_id.lower() for keyword in high_freq_modules):
            return 6  # More workers for high-frequency data
        
        # Medium frequency modules
        medium_freq_modules = ["controller", "input", "audio"]
        if any(keyword in module_id.lower() for keyword in medium_freq_modules):
            return 4  # Medium number of workers
        
        # Default for other modules
        return 2
    
    def queue_message(self, module_id: str, message: str) -> bool:
        """Queue a message for sending via worker pool."""
        if module_id not in self.worker_pools:
            return False
        
        return self.worker_pools[module_id].distribute_message(message)
    
    def get_module_stats(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific module's worker pool."""
        if module_id in self.worker_pools:
            return self.worker_pools[module_id].get_stats()
        return None
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all modules."""
        current_time = time.time()
        
        stats = {
            "timestamp": current_time,
            "modules": {}
        }
        
        for module_id, worker_pool in self.worker_pools.items():
            stats["modules"][module_id] = worker_pool.get_stats()
        
        # Log stats periodically
        if current_time - self.stats_last_update > self.stats_update_interval:
            self._log_performance_stats(stats)
            self.stats_last_update = current_time
        
        return stats
    
    def _log_performance_stats(self, stats: Dict[str, Any]):
        """Log performance statistics."""
        print("\n=== WebSocket Worker Pool Statistics ===")
        
        for module_id, module_stats in stats["modules"].items():
            total_processed = module_stats["total_messages_processed"]
            avg_queue_size = module_stats["avg_queue_size"]
            pool_size = module_stats["pool_size"]
            
            print(f"Module {module_id}:")
            print(f"  Pool size: {pool_size} workers")
            print(f"  Total processed: {total_processed}")
            print(f"  Avg queue size: {avg_queue_size:.1f}")
            
            # Show per-worker stats
            for worker in module_stats["workers"]:
                worker_id = worker["worker_id"]
                processed = worker["messages_processed"]
                queue_size = worker["queue_size"]
                avg_time = worker["avg_processing_time_ms"]
                
                print(f"    Worker {worker_id}: {processed} msgs, queue: {queue_size}, avg: {avg_time:.2f}ms")
        
        print("=" * 45)

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

        # WebSocket manager instead of direct connection list
        self.websocket_manager = WebSocketManager()

        # Initialize fast JSON serializer
        self.json_serializer = FastJSONSerializer()

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

        # Message rate limiter
        self._message_throttle: Dict[str, Dict[str, Any]] = {}
        
        # Setup basic routes
        self._setup_routes()

    def _setup_directories(self) -> None:
        """Set up necessary directories only if we're in the api_explorer package."""
        # Check if we are running directly in the api_explorer package
        # This prevents creating directories in other modules
        api_explorer_init = os.path.join(self.base_dir, "__init__.py")
        if os.path.exists(api_explorer_init):
            # We're in the api_explorer package, so create directories
            os.makedirs(os.path.join(self.base_dir, "templates"), exist_ok=True)
            os.makedirs(os.path.join(self.base_dir, "static"), exist_ok=True)
            os.makedirs(os.path.join(self.base_dir, "static", "css"), exist_ok=True)
            os.makedirs(os.path.join(self.base_dir, "static", "js"), exist_ok=True)
        else:
            # We're in a different module, just log a message
            logging.info(
                f"Running ApiExplorer from external module, using templates from {self.base_dir}"
            )

    def _setup_routes(self) -> None:
        """Set up the basic routes for the API Explorer."""

        # Home page route
        @self.app.get("/", response_class=HTMLResponse)
        async def get_home(request: Request) -> HTMLResponse:
            # Convert modules dictionary to a list for the template
            modules_list = []
            for module_id, module_info in self.modules.items():
                module_data = {
                    "id": module_id,
                    "name": module_info.get("name", ""),
                    "description": module_info.get("description", ""),
                    "show_data_table": module_info.get("show_data_table", False),
                    "method_groups": [],
                }

                # Convert method groups
                for group_id, group_info in module_info.get(
                    "method_groups", {}
                ).items():
                    group_data = {
                        "id": group_id,
                        "name": group_info.get("name", ""),
                        "methods": [],
                    }

                    # Convert methods in each group
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

            # add base path for browser
            cwd = os.getcwd().replace("\\", "/")
            return self.templates.TemplateResponse(
                "index.html",
                {"request": request, "modules": modules_list, "base_browse_path": cwd},
            )

        # WebSocket endpoint for real-time events - updated for better connection handling
        @self.app.websocket("/ws/{module_id}")
        async def websocket_endpoint(websocket: WebSocket, module_id: str) -> None:
            await websocket.accept()
            print(f"WebSocket connection established for module: {module_id}")
            
            # Add to WebSocket manager
            await self.websocket_manager.add_connection(module_id, websocket)

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
            except Exception as e:
                print(f"WebSocket error: {str(e)}")
            finally:
                # Ensure cleanup happens
                print(f"WebSocket connection cleaned up for module: {module_id}")
                await self.websocket_manager.remove_connection(module_id, websocket)

        # --- Add directory‐listing endpoint for file browser ---
        from fastapi import Query, HTTPException

        @self.app.get("/api/files")
        async def list_files(path: str = Query(...)) -> Dict[str, List[Dict[str, str]]]:
            import os

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

    def _sanitize_for_json(self, obj: Any) -> Any:
        """Sanitize data to make it JSON serializable."""
        if isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._sanitize_for_json(item) for item in obj]
        elif isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj
        elif hasattr(obj, '__dict__'):
            return self._sanitize_for_json(obj.__dict__)
        else:
            return str(obj)

    async def broadcast_event(self, module_id: str, event_data: Dict[str, Any]) -> None:
        """
        Broadcast an event to all WebSocket clients for a specific module.

        Args:
            module_id: ID of the module the event belongs to
            event_data: Event data to broadcast
        """
        # Implement more aggressive throttling for very high-frequency events (>1000Hz)
        current_time = time.time()
        if module_id not in self._message_throttle:
            self._message_throttle[module_id] = {
                "last_log_time": 0,
                "event_count": 0,
                "last_rate_time": current_time,
                "rate": 0,
                "message_batch": {},
                "last_send_time": 0,
                "high_frequency_mode": False,
                "drop_counter": 0,
                "last_important_event": 0
            }
        
        throttle_data = self._message_throttle[module_id]
        
        # Count events for rate calculation
        throttle_data["event_count"] += 1
        
        # Calculate rate every 500ms
        if current_time - throttle_data["last_rate_time"] >= 0.5:
            elapsed = current_time - throttle_data["last_rate_time"]
            if elapsed > 0:
                throttle_data["rate"] = int(throttle_data["event_count"] / elapsed)
            throttle_data["event_count"] = 0
            throttle_data["last_rate_time"] = current_time
            
            # Enable high frequency mode if rate is very high
            if throttle_data["rate"] > 500:  # More than 500 events/sec
                throttle_data["high_frequency_mode"] = True
            elif throttle_data["rate"] < 100:  # Less than 100 events/sec
                throttle_data["high_frequency_mode"] = False
            
            # Log rate information periodically (every 10 seconds in high frequency mode)
            log_interval = 10.0 if throttle_data["high_frequency_mode"] else 5.0
            if current_time - throttle_data["last_log_time"] >= log_interval:
                mode_str = " (HIGH FREQ MODE)" if throttle_data["high_frequency_mode"] else ""
                dropped_str = f", dropped: {throttle_data['drop_counter']}" if throttle_data['drop_counter'] > 0 else ""
                print(f"Broadcasting events for module {module_id} (rate: ~{throttle_data['rate']}/sec{dropped_str}){mode_str}")
                throttle_data["last_log_time"] = current_time
                throttle_data["drop_counter"] = 0  # Reset drop counter

        # In high frequency mode, implement intelligent event filtering
        if throttle_data["high_frequency_mode"]:
            # Check if this is an important event that should never be dropped
            is_important = self._is_important_event(event_data)
            
            if not is_important:
                # For non-important events, implement statistical sampling
                # Sample rate depends on current frequency (higher frequency = lower sample rate)
                sample_rate = max(0.02, min(0.1, 50.0 / throttle_data["rate"]))  # 2-10% sampling
                
                if random.random() > sample_rate:
                    throttle_data["drop_counter"] += 1
                    return  # Drop this event
            else:
                throttle_data["last_important_event"] = current_time

        # Notify callbacks for this module - do this synchronously but only for important callbacks
        if module_id in self.callback_registry:
            for callback in self.callback_registry[module_id].values():
                if callback is not None:
                    try:
                        # In high frequency mode, only call callback for important events or periodically
                        if (not throttle_data["high_frequency_mode"] or 
                           self._is_important_event(event_data) or 
                           current_time - throttle_data.get("last_callback_time", 0) > 0.1):
                            callback(event_data)
                            throttle_data["last_callback_time"] = current_time
                    except Exception as e:
                        logging.error(f"Error in {module_id} callback: {e}")

        # Serialize once for all connections using optimized serializer
        try:
            # Determine serialization strategy based on event type and frequency
            if throttle_data["high_frequency_mode"]:
                # Use compact serialization and templates for high frequency
                if 'visualization_data' in event_data:
                    serialized_data = self.json_serializer.serialize_from_template("visualization", event_data)
                else:
                    serialized_data = self.json_serializer.serialize_from_template("simple", event_data)
            else:
                # Use standard fast serialization for normal frequency
                serialized_data = self.json_serializer.serialize_event(event_data, compact=False)
            
            # Queue the message for worker pool processing (non-blocking)
            success = self.websocket_manager.queue_message(module_id, serialized_data)
            if not success:
                throttle_data["drop_counter"] += 1
                
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

        # Check if server is already running
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

        # Determine if GET or POST
        method_type = method_info.get("type", "GET").upper()

        # Get the parameter signature of the handler function
        import inspect

        sig = inspect.signature(handler_function)
        param_names = list(sig.parameters.keys())

        # Create the endpoint
        if method_type == "GET":
            # Create a GET endpoint with properly defined parameters
            if len(param_names) == 0:
                # No parameters needed
                @router.get(f"/{method_id}")
                async def endpoint() -> Any:
                    return await handler_function()

            else:
                # Create parameters dynamically based on method_info params
                from fastapi import Query, Depends
                from pydantic import create_model

                param_dict: Dict[str, Any] = {}
                for param_id, param_info in method_info.get("params", {}).items():
                    if param_info.get("type") == "number":
                        # Number parameter
                        param_dict[param_id] = (Optional[int], Query(None))
                    else:
                        # String parameter (default)
                        param_dict[param_id] = (Optional[str], Query(None))

                # Create dynamic model for query parameters
                QueryModel = create_model(
                    f"{module_id.capitalize()}{method_id.capitalize()}Query",
                    **param_dict,
                )

                # Use Depends to extract parameters
                @router.get(f"/{method_id}")
                async def endpoint(query: Any = Depends(QueryModel)) -> Any:
                    # Convert to dict and pass to handler
                    param_dict = {
                        k: v for k, v in query.dict().items() if v is not None
                    }
                    return await handler_function(**param_dict)

        else:
            # For POST requests
            from fastapi import Body
            from pydantic import create_model

            param_fields: Dict[str, Any] = {}
            for param_id, param_info in method_info.get("params", {}).items():
                # Determine the Python type based on the param type
                if param_info.get("type") == "number":
                    field_type: Type[Union[int, str]] = int
                else:
                    field_type = str

                # Create the field with type and default
                if param_info.get("required", False):
                    param_fields[param_id] = (field_type, ...)
                else:
                    param_fields[param_id] = (Optional[field_type], None)

            # Create dynamic model for request body
            RequestModel = create_model(
                f"{module_id.capitalize()}{method_id.capitalize()}Request",
                **param_fields,
            )

            @router.post(f"/{method_id}")
            async def endpoint(request_data: Any = Body(...)) -> Any:
                # Convert to dict and pass to handler
                data_dict = {
                    k: v for k, v in request_data.dict().items() if v is not None
                }
                return await handler_function(**data_dict)

    def register_module(
        self, module_id: str, name: str, description: str, show_data_table: bool = False
    ) -> None:
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
            "name": name,
            "description": description,
            "method_groups": {},
            "router": router,
            "show_data_table": show_data_table,
        }

    def _is_important_event(self, event_data: Dict[str, Any]) -> bool:
        """Determine if an event is important and should not be dropped."""
        event_type = event_data.get('event_type', event_data.get('type', ''))
        
        # Always keep connection/disconnection events
        if any(keyword in event_type.lower() for keyword in 
               ['connect', 'disconnect', 'error', 'state_change', 'start', 'stop']):
            return True
        
        # Keep button press/release events
        if any(keyword in event_type.lower() for keyword in 
               ['button_press', 'button_release', 'key_down', 'key_up']):
            return True
        
        # For visualization data, check if it contains significant changes
        if 'visualization_data' in event_data:
            vis_data = event_data['visualization_data']
            if isinstance(vis_data, dict) and 'list_view' in vis_data:
                # This is sensor data - consider it important if it's the first in a while
                # or if values show significant change
                return True  # For now, keep all visualization data
        
        return False

    def _create_compact_event_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a more compact version of event data for high-frequency transmission."""
        compact = {}
        
        # Always include these essential fields
        essential_fields = ['event_type', 'type', 'timestamp', 'visualization_data']
        
        for field in essential_fields:
            if field in event_data:
                if field == 'visualization_data':
                    # Compact visualization data
                    vis_data = event_data[field]
                    if isinstance(vis_data, dict) and 'list_view' in vis_data:
                        # Round numeric values to reduce precision
                        compact_list = []
                        for item in vis_data['list_view']:
                            compact_item = {
                                'channel': item.get('channel'),
                                'type': item.get('type'),
                                'value': round(float(item.get('value', 0)), 3)  # 3 decimal places
                            }
                            compact_list.append(compact_item)
                        compact[field] = {'list_view': compact_list}
                    else:
                        compact[field] = vis_data
                elif field == 'timestamp':
                    # Round timestamp to milliseconds
                    compact[field] = round(event_data[field], 3)
                else:
                    compact[field] = event_data[field]
        
        # Add other important fields if they exist and are small
        other_fields = ['key', 'button', 'state']
        for field in other_fields:
            if field in event_data and len(str(event_data[field])) < 50:
                compact[field] = event_data[field]
        
        return compact
