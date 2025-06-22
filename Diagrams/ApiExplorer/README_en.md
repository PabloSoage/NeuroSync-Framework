# API Explorer - Architecture and Technical Documentation

## Summary

API Explorer is a web framework designed to provide dynamic API exploration and testing capabilities for Python modules. Built on FastAPI with advanced WebSocket support, it offers a modern and responsive interface that allows multiple modules to register their APIs at runtime, providing interactive parameter forms, real-time event streaming, and data visualization capabilities. The system implements a singleton pattern for global accessibility while maintaining thread-safe operations and a scalable architecture.

## General Architecture

### Main Architectural Pattern

The API Explorer follows a **singleton-based service architecture** combined with **observer**, **registry**, and **worker pool** patterns, organizing functionality into well-defined layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Web Browser │  │ HTTP Client │  │  WebSocket Client   │ │
│  │ (Modular)   │  │   (REST)    │  │                     │ │
│  │ (Managers)  │  │             │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                 PRESENTATION LAYER                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  HTML       │  │     CSS     │  │    JavaScript       │ │
│  │ Templates   │  │   Styles    │  │    Modules          │ │
│  │ (Jinja2)    │  │ (Responsive)│  │   (Chart.js)        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   WEB FRAMEWORK                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   FastAPI   │  │  WebSocket  │  │   Static Files      │ │
│  │   Server    │  │   Manager   │  │   Service           │ │
│  │  (uvicorn)  │  │ (Worker Pool)│  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   CORE SERVICE                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ ApiExplorer │  │  Module     │  │ Event Broadcasting  │ │
│  │ (Singleton) │  │ Registry    │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │    JSON     │  │ Parameter   │  │    Connection       │ │
│  │Serialization│  │ Validation  │  │   Management        │ │
│  │             │  │             │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     DATA LAYER                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Module    │  │   Method    │  │   Parameter         │ │
│  │ Information │  │ Information │  │  Information        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Components and Architecture

### 1. **API Explorer Core** (api_explorer.py)

**Purpose**: Central singleton service that manages the entire API exploration framework.

#### Components:
- **`ApiExplorer`**: Main singleton class coordinating all operations
- **Module Registry**: Dynamic registration system for external modules
- **`WebSocketManager`**: Real-time communication handler with worker pools
- **Route Management**: Dynamic FastAPI route generation
- **Event Broadcasting**: Multi-client event distribution system

#### Key Features:
- **Singleton Pattern**: Thread-safe unique instance
- **Dynamic Registration**: Runtime module and method registration
- **Thread-Safe Operations**: Main lock for synchronization
- **Port Management**: Automatic port detection and assignment
- **Server Lifecycle**: Complete start/stop server management

```python
# Basic usage example
from api_explorer import ApiExplorer

explorer = ApiExplorer.get_instance()
explorer.register_module("my_module", "My Module", "Description")
explorer.add_method_group("my_module", "control", "Control Methods")
explorer.register_method("my_module", "control", "start", method_info, handler)

# Event broadcasting
explorer.broadcast_event("my_module", {
    "timestamp": time.time(),
    "data": data,
    "event_type": "data_update"
})
```

#### Architecture Details:
- **Thread Safety**: Main lock (`_lock`) for critical operations
- **Event System**: Event broadcasting with basic throttling
- **File System Integration**: Server-side directory navigation
- **Error Handling**: Basic logging and exception management

### 2. **WebSocket System**

#### WebSocketManager (websocket_manager.py)

**Purpose**: Central WebSocket connection manager with worker pool architecture.

##### Components:
- **`WebSocketManager`**: Main connection and worker coordinator
- **`WebSocketWorkerPool`**: Worker pool for distributed processing
- **`WorkerStats`**: Performance metrics per worker
- **`FastJSONSerializer`**: Optimized JSON serialization

##### Features:
- **Worker Pool Architecture**: Load distribution across multiple workers
- **Adaptive Throttling**: Frequency-based message throttling
- **Load Balancing**: Round-robin distribution among workers
- **Performance Tracking**: Processing metrics tracking

```python
# Automatic worker pool per module
{
    "module_id": "data_stream",
    "worker_count": 4,
    "messages_per_second": estimated,
    "avg_processing_time": measured,
    "queue_utilization": calculated
}
```

#### JSON Serialization (serialization.py)

**Purpose**: Optimized JSON serialization system for data transmission.

##### Features:
- **orjson Integration**: Use of orjson when available for maximum speed
- **Template Caching**: Pre-compilation of frequent JSON structures
- **Fallback Safety**: Graceful degradation to stdlib json if orjson unavailable
- **Data Sanitization**: Automatic cleanup of non-serializable data

### 3. **Main Module** (main.py)

**Purpose**: Entry point and high-level server management.

#### Components:
- **`run_explorer()`**: Main function to start the API Explorer
- **`main()`**: Command-line entry point
- **Server Configuration**: Host and port configuration

#### Features:
- **Flexible Deployment**: Supports blocking and non-blocking server modes
- **Configuration Management**: Host and port configuration
- **Import Management**: Automatic path resolution for module imports

### 4. **Modular Frontend Architecture**

#### Modular JavaScript (`static/js/`)

**Purpose**: Frontend architecture based on managers with event-driven communication.

##### Main Components:

###### **APIExplorer Coordinator** (script.js)
- **Manager Coordination**: Central coordination of all managers
- **Event-Driven Communication**: Event system between managers
- **Module Initialization**: Sequential module initialization

###### **DarkModeManager** (darkModeManager.js)
- **Theme Management**: Centralized dark/light theme management
- **Callback System**: Theme change notifications to other managers
- **Chart Integration**: Automatic Chart.js theme updates
- **Persistence**: User preference storage

###### **WebSocketManager** (webSocketManager.js)
- **Connection Management**: Multiple WebSocket connection management
- **Event Buffering**: Smart buffering for high-frequency events
- **Performance Optimization**: Update throttling for visual smoothness
- **Error Handling**: Connection error handling and cleanup

###### **ChartManager** (chartManager.js)
- **Chart Coordination**: Multiple Chart.js instance management
- **Batched Updates**: Batch updates for optimization
- **Throttling**: Data frequency-based throttling
- **Multi-Channel Support**: Separate or combined channel visualization

###### **EventDisplayManager** (eventDisplayManager.js)
- **Event Display**: Real-time event display coordination
- **Auto-Scrolling**: Smart automatic scrolling
- **Data Table Updates**: Incremental table updates

###### **FileBrowserManager** (fileBrowserManager.js)
- **Server Integration**: Server-side file navigation integration
- **Modal Management**: File browser modal management
- **Path Resolution**: Cross-platform path resolution

###### **APIMethodsManager** (apiMethodsManager.js)
- **Method Execution**: API method execution
- **Parameter Handling**: Dynamic parameter management
- **Template Loading**: Automatic JSON template loading

```javascript
// Manager architecture example
class APIExplorer {
    constructor() {
        this.darkModeManager = new DarkModeManager();
        this.webSocketManager = new WebSocketManager();
        this.chartManager = new ChartManager();
        this.eventDisplayManager = new EventDisplayManager();
    }

    setupManagerCommunication() {
        // Event-driven communication between managers
        this.darkModeManager.onModeChange((isDark) => {
            this.chartManager.updateTheme(isDark);
        });

        this.webSocketManager.onDataReceived((moduleId, data) => {
            this.chartManager.updateData(moduleId, data);
            this.eventDisplayManager.addDataEvent(moduleId, data);
        });
    }
}
```

#### Responsive HTML Template (index.html)

**Purpose**: Dynamic and responsive web interface with Bootstrap framework.

##### Key Components:
- **Module Registration Interface**: Dynamic module list generation
- **API Explorer Tabs**: Module-based API exploration interface
- **Real-time Event Panels**: Optimized WebSocket event visualization
- **Parameter Forms**: Dynamic form generation
- **File Browser Modal**: Server-side file system navigation
- **Data Visualization**: Chart.js integration

##### Features:
- **Responsive Design**: Bootstrap-based responsive layout
- **Dark/Light Mode**: Complete theme system with persistence
- **Dynamic Content**: Jinja2 templates
- **Real-time Updates**: Live updates via WebSocket
- **Interactive Forms**: Parameter type-specific controls

#### Advanced CSS Styles (styles.css)

**Purpose**: Styling system with dual theme support.

##### Components:
- **Dark Mode Styles**: Complete professional dark theme implementation
- **Light Mode Styles**: Default light theme with modern appearance
- **Component Styles**: Consistent styles for all UI components
- **Responsive Layout**: Mobile-first responsive design principles
- **Chart Integration**: Integrated Chart.js themes

## Data Structures and Models

### 1. **Module Information**
**Purpose**: Module metadata storage as nested dictionaries.

#### Structure:
```python
{
    "module_id": {
        "name": str,
        "description": str,
        "show_data_table": bool,
        "method_groups": {
            "group_id": {
                "name": str,
                "methods": {
                    "method_id": {
                        "name": str,
                        "description": str,
                        "type": str,  # "GET" or "POST"
                        "params": {...}
                    }
                }
            }
        },
        "router": APIRouter
    }
}
```

### 2. **WorkerStats**
**Purpose**: Performance metrics for worker pools.

#### Attributes:
- **Message Processing**: Message count processed per worker
- **Timing Metrics**: Average processing time
- **Queue Utilization**: Message queue utilization
- **Activity Tracking**: Last activity timestamp

### 3. **Event Data**
**Purpose**: Basic structure for WebSocket events.

#### Typical structure:
```python
{
    "timestamp": float,
    "event_type": str,
    "module_id": str,
    "data": dict,
    "visualization_data": dict  # optional
}
```

## Features and Capabilities

### 1. **Data Visualization**

#### Chart Integration:
- **Chart.js Framework**: Professional charts
- **Real-time Streaming**: Live data updates
- **Multi-channel Support**: Separate visualization for different data channels
- **Batched Updates**: Batch updates for visual smoothness

#### Visualization Modes:
- **Combined Charts**: All channels in a single chart
- **Separate Charts**: Individual charts per channel
- **Type Filtering**: Display filtering by data type (EEG, EMG, etc.)
- **Auto-scaling**: Dynamic scaling based on data

### 2. **WebSocket Event System**

#### Real-time Communication:
- **Worker Pool Architecture**: Distributed processing
- **Message Throttling**: Frequency-based throttling
- **Load Balancing**: Distribution among workers
- **Performance Monitoring**: Performance metrics

#### Event Types:
- **Data Events**: Data events with visualization
- **System Events**: System events
- **Important Events**: Priority events that are not discarded

### 3. **JSON Serialization**

#### Optimizations:
- **orjson Integration**: Use of orjson when available
- **Template Pre-compilation**: Pre-compiled templates
- **Fallback Safety**: Graceful degradation to stdlib json
- **Data Sanitization**: Automatic data cleanup

### 4. **Dynamic Parameter Forms**

#### Supported Parameter Types:
- **Text**: Basic text inputs
- **Numbers**: Numeric inputs with validation
- **Ranges**: Sliders with custom formatting
- **Selection**: Dropdowns with predefined options
- **Files**: Integrated file browser
- **JSON Templates**: Text areas with automatic template loading

## Integration and Usage Patterns

### 1. **Module Registration Pattern**

```python
# Basic module registration
explorer = ApiExplorer.get_instance()
explorer.register_module("my_module", "My Module", "Description")
explorer.add_method_group("my_module", "control", "Control")
explorer.register_method("my_module", "control", "start", method_info, handler)
```

### 2. **Event Broadcasting Pattern**

```python
# Event broadcasting
event_data = {
    "timestamp": time.time(),
    "event_type": "data_update",
    "data": data,
    "visualization_data": {
        "list_view": formatted_data
    }
}

explorer.broadcast_event("my_module", event_data)
```

### 3. **Server Integration Pattern**

```python
# Server initialization
def setup_api():
    explorer = ApiExplorer.get_instance()
    
    # Register modules
    register_modules(explorer)
    
    # Start server
    explorer.start_server(host="localhost", port=8000, block=False)
    return explorer
```

## Implemented Architectural Patterns

### 1. **Singleton Pattern**
- **`ApiExplorer`**: Thread-safe singleton
- **Global State Management**: Consistent state
- **Resource Sharing**: Efficient resource sharing

### 2. **Worker Pool Pattern**
- **Distributed Processing**: Distributed processing for WebSockets
- **Load Balancing**: Automatic load balancing
- **Adaptive Scaling**: Module type-based scaling

### 3. **Observer Pattern**
- **Event Broadcasting**: Event broadcasting to multiple clients
- **Callback System**: Callback system for notifications

### 4. **Registry Pattern**
- **Dynamic Registration**: Dynamic module and method registration
- **Runtime Configuration**: Runtime configuration

## Performance Features

### 1. **High-Frequency Data Handling**
- **Worker Pool Processing**: Distributed processing
- **Adaptive Throttling**: Smart throttling
- **Batch Processing**: Batch processing

### 2. **Connection Management**
- **Worker Pool Architecture**: Scalable architecture
- **Performance Monitoring**: Performance monitoring
- **Automatic Cleanup**: Automatic resource cleanup

### 3. **UI Performance**
- **Batched DOM Updates**: Batch DOM updates
- **Throttled Chart Updates**: Chart updates with throttling
- **Incremental Table Updates**: Incremental table updates

## Technology Stack

### Backend:
- **FastAPI**: Asynchronous web framework
- **Uvicorn**: ASGI server
- **orjson** (optional): Fast JSON serialization
- **asyncio**: Asynchronous programming
- **WebSockets**: Bidirectional communication

### Frontend:
- **Modular JavaScript**: Manager architecture
- **Chart.js**: Data visualization
- **Bootstrap 5**: Responsive CSS framework
- **WebSocket APIs**: Native WebSocket APIs

### Tools:
- **Worker Pools**: Distributed processing
- **Throttling**: Resource throttling
- **Performance Monitoring**: Metrics monitoring