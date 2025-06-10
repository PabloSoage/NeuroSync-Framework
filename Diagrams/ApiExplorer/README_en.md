# API Explorer - Architecture and Technical Documentation

## Executive Summary

API Explorer is a comprehensive web-based framework designed to provide dynamic API exploration and testing capabilities for Python modules. Built on FastAPI with WebSocket support, it offers a modern, responsive interface that allows multiple modules to register their APIs at runtime, providing interactive parameter forms, real-time event streaming, data visualization, and comprehensive testing capabilities. The system implements a singleton pattern for global accessibility while maintaining thread-safe operations and extensible architecture.

## General Architecture

### Main Architectural Pattern

The API Explorer follows a **singleton-based service architecture** combined with **observer** and **registry** patterns, organizing functionality into well-defined layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Web Browser│  │  HTTP Client│  │   WebSocket Client  │ │
│  │ (Bootstrap) │  │   (REST)    │  │   (Real-time)       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                 PRESENTATION LAYER                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   HTML      │  │     CSS     │  │    JavaScript       │ │
│  │ Templates   │  │   Styles    │  │     Module          │ │
│  │ (Jinja2)    │  │ (Bootstrap) │  │   (Chart.js)        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    WEB FRAMEWORK                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   FastAPI   │  │  WebSocket  │  │   Static Files      │ │
│  │   Server    │  │  Handler    │  │   Serving           │ │
│  │  (uvicorn)  │  │             │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   CORE SERVICE                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ ApiExplorer │  │   Module    │  │     Event           │ │
│  │ (Singleton) │  │  Registry   │  │   Broadcasting      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │    Method   │  │  Parameter  │  │    Connection       │ │
│  │ Management  │  │ Validation  │  │    Management       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     DATA LAYER                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Module    │  │   Method    │  │     Parameter       │ │
│  │    Info     │  │    Info     │  │      Info           │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Components and Architecture

### 1. **API Explorer Core** (`api_explorer.py`)

**Purpose**: Central singleton service managing the entire API exploration framework.

#### Components:
- **`ApiExplorer`**: Main singleton class coordinating all operations
- **Module Registry**: Dynamic registration system for external modules
- **WebSocket Manager**: Real-time communication handler
- **Route Management**: Dynamic FastAPI route generation
- **Event Broadcasting**: Multi-client event distribution system

#### Key Features:
- **Singleton Pattern**: Thread-safe single instance with double-checked locking
- **Dynamic Registration**: Runtime module and method registration
- **Thread-Safe Operations**: Multiple locks for granular thread safety
- **Port Management**: Automatic port detection and allocation
- **Server Lifecycle**: Complete server start/stop management

```python
# Usage example
from api_explorer import ApiExplorer

explorer = ApiExplorer.get_instance()
explorer.register_module("my_module", "My Module", "Description")
explorer.add_method_group("my_module", "control", "Control Methods")
explorer.register_method("my_module", "control", "start", method_info, handler)
```

#### Architecture Details:
- **Thread Safety**: Multiple locks (`_lock`, router-specific locks)
- **Connection Management**: WebSocket connection pool with lifecycle tracking
- **Event System**: Broadcast events to multiple connected clients
- **File System Integration**: Server-side directory browsing and file operations
- **Error Handling**: Comprehensive error isolation and recovery

### 2. **Main Module** (`main.py`)

**Purpose**: Entry point and high-level server management.

#### Components:
- **`run_explorer()`**: Primary function for starting the API Explorer
- **`main()`**: Command-line entry point
- **Server Configuration**: Host, port, and blocking configuration
- **Path Management**: Python path configuration for imports

#### Features:
- **Flexible Deployment**: Supports both blocking and non-blocking server modes
- **Configuration Management**: Host and port configuration
- **Import Management**: Automatic path resolution for module imports
- **Server Abstraction**: Clean interface for external module integration

### 3. **Frontend Architecture**

#### HTML Template (`templates/index.html`)

**Purpose**: Dynamic, responsive web interface with Bootstrap framework.

##### Key Components:
- **Module Registration Interface**: Dynamic module list generation
- **API Explorer Tabs**: Per-module API exploration interface
- **Real-time Event Panels**: WebSocket event display and visualization
- **Parameter Forms**: Dynamic form generation based on method signatures
- **File Browser Modal**: Server-side file system navigation
- **Data Visualization**: Chart.js integration for real-time data streaming

##### Features:
- **Responsive Design**: Bootstrap-based responsive layout
- **Dark/Light Mode**: Complete theming system with user preference persistence
- **Dynamic Content**: Jinja2 templating with JavaScript-driven updates
- **Real-time Updates**: WebSocket-driven live content updates
- **Interactive Forms**: Parameter validation and type-specific input controls

#### CSS Styling (`static/css/styles.css`)

**Purpose**: Comprehensive styling system with dual theme support.

##### Components:
- **Dark Mode Styles**: Complete dark theme implementation
- **Light Mode Styles**: Default light theme with professional appearance
- **Component Styling**: Consistent styling across all UI components
- **Responsive Layout**: Mobile-first responsive design principles
- **Chart Integration**: Chart.js theming integration

##### Features:
- **Theme Consistency**: Unified color palette and typography
- **Accessibility**: High contrast ratios and WCAG compliance considerations
- **Modern Design**: Contemporary web design principles
- **Cross-browser Compatibility**: Consistent appearance across browsers

#### JavaScript Module (`static/js/script.js`)

**Purpose**: Client-side application logic and real-time communication.

##### Key Components:
- **WebSocket Management**: Per-module WebSocket connection handling
- **Chart Visualization**: Real-time data visualization with Chart.js
- **Event Processing**: Real-time event handling and UI updates
- **Form Management**: Dynamic form generation and validation
- **File Browser**: Client-side file system navigation interface
- **Theme Management**: Dark/light mode switching and persistence

##### Features:
- **Event-Driven Architecture**: Reactive UI updates based on WebSocket events
- **Multi-Module Support**: Independent WebSocket connections per module
- **Chart Management**: Multiple chart types with channel separation modes
- **Real-time Filtering**: Type-based event filtering and display
- **Error Handling**: Robust error handling with user feedback
- **State Management**: Client-side state persistence and synchronization

```javascript
// WebSocket connection example
function connectWebSocket(moduleId) {
    const ws = new WebSocket(`ws://localhost:8000/ws/${moduleId}`);
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateUI(moduleId, data);
    };
    webSockets[moduleId] = ws;
}
```

## Data Structures and Models

### 1. **ModuleInfo**
**Purpose**: Complete module metadata and configuration storage.

#### Attributes:
- **Module Identity**: ID, name, description, and display preferences
- **Method Groups**: Organized collection of related methods
- **Router Integration**: FastAPI router for HTTP endpoints
- **Configuration**: Display options and module-specific settings

#### Features:
- **Hierarchical Organization**: Methods organized into logical groups
- **Dynamic Updates**: Runtime modification of module configuration
- **Serialization**: Complete JSON serialization for client transmission

### 2. **MethodInfo** 
**Purpose**: Detailed method metadata and execution configuration.

#### Attributes:
- **Method Identity**: ID, name, description, and categorization
- **Parameter Definition**: Complete parameter specification with validation
- **Handler Integration**: Direct linkage to execution functions
- **Documentation**: Comprehensive method documentation

#### Features:
- **Parameter Validation**: Type checking and constraint enforcement
- **Dynamic Execution**: Runtime method invocation with parameter binding
- **Error Handling**: Comprehensive error capture and reporting

### 3. **ParameterInfo**
**Purpose**: Comprehensive parameter specification and validation.

#### Attributes:
- **Type System**: Support for all Python basic types plus file parameters
- **Validation Rules**: Min/max values, required fields, custom validation
- **UI Generation**: Automatic form control generation based on parameter type
- **Default Values**: Default value specification and handling

#### Features:
- **Rich Type Support**: String, number, boolean, choice, file, and custom types
- **Advanced Validation**: Range checking, pattern matching, custom validators
- **UI Adaptation**: Different form controls based on parameter characteristics
- **File Integration**: File browser integration for file parameters

```python
# Parameter definition example
param_info = {
    "type": "float",
    "required": True,
    "description": "Sampling frequency in Hz",
    "min": 1.0,
    "max": 1000.0,
    "step": 0.1,
    "default": 250.0
}
```

## Advanced Features and Capabilities

### 1. **Real-time Data Visualization**

#### Chart Integration:
- **Chart.js Framework**: Professional charting with multiple chart types
- **Real-time Streaming**: Live data updates via WebSocket
- **Multi-channel Support**: Separate visualization for different data channels
- **Theme Integration**: Automatic chart theming based on UI mode

#### Visualization Modes:
- **Combined Charts**: All channels in single chart for comparison
- **Separate Charts**: Individual charts per channel for detailed analysis
- **Type Filtering**: Filter display by data type (EEG, EMG, etc.)
- **Auto-scaling**: Dynamic axis scaling based on data ranges

#### Features:
- **Performance Optimization**: Efficient data buffering and rendering
- **Interactive Controls**: Zoom, pan, and data point inspection
- **Export Capabilities**: Chart export for documentation and analysis
- **Responsive Design**: Charts adapt to different screen sizes

### 2. **WebSocket Event System**

#### Real-time Communication:
- **Per-module Channels**: Independent WebSocket connections for each module
- **Event Broadcasting**: Simultaneous delivery to multiple connected clients
- **Connection Management**: Automatic reconnection and heartbeat monitoring
- **Message Queuing**: Reliable message delivery with buffering

#### Event Types:
- **Data Events**: Real-time data streaming for visualization
- **Status Events**: Module and system status updates
- **Control Events**: Interactive control confirmations and feedback
- **Error Events**: Error reporting and diagnostic information

#### Features:
- **Scalability**: Support for multiple simultaneous connections
- **Reliability**: Connection monitoring and automatic recovery
- **Security**: Connection validation and access control
- **Performance**: Efficient binary and JSON message encoding

### 3. **File System Integration**

#### Server-side File Browser:
- **Directory Navigation**: Full server-side directory tree navigation
- **File Filtering**: Extension-based filtering and search capabilities
- **Path Resolution**: Cross-platform path handling and resolution
- **Security**: Sandboxed file access with permission validation

#### File Operations:
- **File Selection**: Interactive file selection for parameter input
- **Path Input**: Manual path input with validation
- **Save/Load Modes**: Support for both file loading and saving operations
- **Prefix Handling**: Automatic file prefix generation for saves

#### Features:
- **Cross-platform**: Windows, macOS, and Linux support
- **Performance**: EfficientBelt large directory handling
- **Security**: Secure file access with permission checks
- **Usability**: Intuitive file browser interface

### 4. **Dynamic Parameter Forms**

#### Form Generation:
- **Type-based Controls**: Automatic form control selection based on parameter type
- **Validation Integration**: Real-time validation with visual feedback
- **Advanced Controls**: Sliders, dropdowns, file browsers, and custom controls
- **Layout Management**: Responsive form layout with proper spacing

#### Parameter Types:
- **Basic Types**: String, integer, float, boolean
- **Advanced Types**: Choice (dropdown), range (slider), file
- **Custom Types**: Module-specific parameter types with custom validation
- **Complex Types**: Array and object parameters with nested validation

#### Features:
- **Real-time Validation**: Immediate feedback on parameter validity
- **Error Handling**: Clear error messages and correction guidance
- **Default Values**: Intelligent default value handling and persistence
- **Accessibility**: Full keyboard navigation and screen reader support

## Integration Patterns and Usage

### 1. **Module Registration Pattern**

Modules integrate with API Explorer through a simple registration pattern:

```python
# Basic module registration
explorer = ApiExplorer.get_instance()
explorer.register_module("my_module", "My Module", "Module description")

# Add method groups
explorer.add_method_group("my_module", "control", "Control Methods")
explorer.add_method_group("my_module", "data", "Data Access")

# Register individual methods
method_info = {
    "name": "Start Recording",
    "description": "Begin data recording",
    "type": "control",
    "params": {
        "duration": {
            "type": "float",
            "required": True,
            "description": "Recording duration in seconds",
            "min": 1.0,
            "max": 3600.0
        }
    }
}

def start_recording_handler(duration: float):
    # Implementation
    return {"status": "started", "duration": duration}

explorer.register_method("my_module", "control", "start_recording", 
                        method_info, start_recording_handler)
```

### 2. **Event Broadcasting Pattern**

Real-time events are broadcast to connected clients:

```python
# Broadcasting events to clients
event_data = {
    "timestamp": time.time(),
    "type": "data_update",
    "data": {
        "channel_1": [1.2, 1.5, 1.8],
        "channel_2": [0.8, 0.9, 1.1]
    },
    "visualization": {
        "chart_type": "line",
        "update_mode": "append"
    }
}

explorer.broadcast_event("my_module", event_data)
```

### 3. **Server Integration Pattern**

Integration with existing applications:

```python
# Start API Explorer alongside existing application
def initialize_api_integration():
    explorer = ApiExplorer.get_instance()
    
    # Register module
    setup_module_registration(explorer)
    
    # Start server in separate thread
    explorer.start_server(host="localhost", port=8000, block=False)
    
    return explorer

# Clean shutdown
def shutdown_api_integration():
    explorer = ApiExplorer.get_instance()
    explorer.stop_server()
```

## Architectural Patterns Implemented

### 1. **Singleton Pattern**
- **`ApiExplorer`**: Global singleton with thread-safe instantiation
- **Global State Management**: Consistent state across all components
- **Resource Sharing**: Shared WebSocket connections and server resources

### 2. **Registry Pattern**
- **Module Registry**: Dynamic registration of modules and methods
- **Handler Registry**: Mapping of API endpoints to handler functions
- **Connection Registry**: Management of active WebSocket connections

### 3. **Observer Pattern**
- **WebSocket Events**: Real-time event notification to multiple observers
- **Client Updates**: Automatic UI updates based on server events
- **State Synchronization**: Automatic client state updates

### 4. **Factory Pattern**
- **Form Generation**: Dynamic form creation based on parameter specifications
- **Chart Creation**: Chart instantiation based on data types
- **Route Generation**: Dynamic FastAPI route creation

### 5. **Adapter Pattern**
- **Framework Integration**: Adaptation between different Python frameworks
- **WebSocket Abstraction**: Unified interface for different WebSocket implementations
- **File System Abstraction**: Cross-platform file system operations

### 6. **Command Pattern**
- **API Method Execution**: Encapsulation of method calls with parameters
- **Event Handling**: Command-based event processing
- **Undo/Redo Support**: Potential for command history and reversal

## Performance and Scalability Features

### 1. **Efficient Data Handling**
- **Streaming**: Real-time data streaming without memory accumulation
- **Buffering**: Intelligent buffering for smooth visualization
- **Compression**: Data compression for large datasets
- **Caching**: Strategic caching of frequently accessed data

### 2. **Connection Management**
- **Pool Management**: Efficient WebSocket connection pooling
- **Resource Cleanup**: Automatic cleanup of inactive connections
- **Load Balancing**: Distribution of load across multiple connections
- **Heartbeat Monitoring**: Connection health monitoring and recovery

### 3. **UI Performance**
- **Virtual Scrolling**: Efficient handling of large data lists
- **Lazy Loading**: On-demand loading of UI components
- **Chart Optimization**: Efficient chart rendering and updates
- **Memory Management**: Automatic cleanup of UI resources

## Security and Reliability Features

### 1. **Input Validation**
- **Parameter Validation**: Comprehensive validation of all input parameters
- **SQL Injection Prevention**: Protection against injection attacks
- **XSS Prevention**: Cross-site scripting protection
- **CSRF Protection**: Cross-site request forgery protection

### 2. **Error Handling**
- **Exception Isolation**: Errors in one module don't affect others
- **Graceful Degradation**: System continues operating despite component failures
- **Error Reporting**: Comprehensive error logging and reporting
- **Recovery Mechanisms**: Automatic recovery from common error conditions

### 3. **Resource Management**
- **Memory Limits**: Protection against memory exhaustion
- **Connection Limits**: Limits on concurrent connections
- **Rate Limiting**: Protection against API abuse
- **Timeout Handling**: Proper handling of long-running operations

## Use Cases and Applications

### 1. **API Development and Testing**
- **Interactive Testing**: Real-time API testing with parameter adjustment
- **Documentation**: Automatic API documentation generation
- **Debugging**: Real-time debugging and diagnostic capabilities
- **Integration Testing**: Testing of API integrations in realistic scenarios

### 2. **Real-time Data Monitoring**
- **Sensor Data**: Real-time visualization of sensor data streams
- **System Monitoring**: Live monitoring of system metrics and performance
- **Scientific Instruments**: Real-time data acquisition and visualization
- **IoT Applications**: Monitoring and control of IoT devices

### 3. **Educational and Research**
- **API Education**: Interactive learning environment for API concepts
- **Research Tools**: Platform for research data collection and analysis
- **Prototyping**: Rapid prototyping of API-based applications
- **Demonstration**: Professional demonstration of API capabilities

### 4. **Development Tools**
- **Module Integration**: Integration testing for complex module systems
- **Configuration Management**: Dynamic configuration of application modules
- **Performance Analysis**: Real-time performance monitoring and analysis
- **Quality Assurance**: Automated testing and validation of APIs

## Technology Stack and Dependencies

### Backend Technologies:
- **FastAPI**: Modern, high-performance web framework
- **Uvicorn**: Lightning-fast ASGI server
- **WebSockets**: Real-time bidirectional communication
- **Jinja2**: Powerful templating engine
- **Python 3.8+**: Modern Python with type hints and async support

### Frontend Technologies:
- **Bootstrap 5**: Modern responsive CSS framework
- **Chart.js**: Professional charting library
- **Vanilla JavaScript**: Pure JavaScript for optimal performance
- **WebSocket API**: Native browser WebSocket support
- **CSS Grid/Flexbox**: Modern layout techniques

### Development Tools:
- **Type Hints**: Comprehensive type annotation
- **Async/Await**: Modern asynchronous programming
- **Error Handling**: Comprehensive exception management
- **Logging**: Professional logging and debugging support

## Deployment and Configuration

### 1. **Standalone Deployment**
```python
# Simple standalone deployment
from api_explorer import run_explorer

# Start server
explorer = run_explorer(host="0.0.0.0", port=8000, block=True)
```

### 2. **Integrated Deployment**
```python
# Integration with existing application
from api_explorer import ApiExplorer

def setup_api_explorer():
    explorer = ApiExplorer.get_instance()
    register_my_module(explorer)
    explorer.start_server(host="localhost", port=8000, block=False)
    return explorer
```

### 3. **Production Configuration**
- **Reverse Proxy**: Nginx/Apache integration for production deployment
- **SSL/TLS**: HTTPS support for secure communications
- **Environment Variables**: Configuration via environment variables
- **Docker Support**: Containerized deployment options