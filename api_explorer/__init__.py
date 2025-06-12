"""
API Explorer for modules.

This package provides a comprehensive web-based interface for exploring and
testing module APIs in real-time. Features a dynamic FastAPI server that allows
multiple modules to register their APIs, WebSocket support for real-time event
streaming, interactive parameter forms, and a modern responsive UI with dark mode
support. Includes file browser capabilities, visualization components for data
streams, and comprehensive API documentation generation.
"""

from .api_explorer import ApiExplorer
from .websocket_manager import WebSocketManager
from .worker_pool import WebSocketWorkerPool, WorkerStats
from .serialization import FastJSONSerializer

__all__ = [
    "ApiExplorer",
    "WebSocketManager",
    "WebSocketWorkerPool",
    "WorkerStats",
    "FastJSONSerializer",
]
