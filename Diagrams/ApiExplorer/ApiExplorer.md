```mermaid
classDiagram
    %% ================================================================================
    %% MAIN MODULE CLASSES
    %% ================================================================================
    class ApiExplorer {
        <<singleton>>
        -_instance: Optional[ApiExplorer]
        -_lock: threading.Lock
        -app: FastAPI
        -base_dir: str
        -templates: Jinja2Templates
        -modules: Dict[str, Dict[str, Any]]
        -active_connections: List[WebSocket]
        -callback_registry: Dict[str, Dict[int, Callable]]
        -next_callback_id: int
        -active_module_count: int
        -active_modules: Set[str]
        -server: Optional[uvicorn.Server]
        -server_thread: Optional[threading.Thread]
        -is_running: bool
        -server_port: Optional[int]
        -server_host: Optional[str]

        +get_instance()$ ApiExplorer
        +__init__() void
        +start_server(host: str, port: int, block: bool) void
        +stop_server() void
        +register_module(module_id: str, name: str, description: str, show_data_table: bool) void
        +add_method_group(module_id: str, group_id: str, name: str) void
        +register_method(module_id: str, group_id: str, method_id: str, method_info: Dict, handler_function: Callable) void
        +broadcast_event(module_id: str, event_data: Dict[str, Any]) void
        -_setup_directories() void
        -_setup_routes() void
        -_is_port_in_use(host: str, port: int) bool
    }

    class MainModule {
        <<module>>
        +run_explorer(host: str, port: int, block: bool) ApiExplorer
        +main() void
    }

    %% ================================================================================
    %% WEB FRAMEWORK COMPONENTS
    %% ================================================================================
    class FastAPI {
        <<framework>>
        +title: str
        +description: str
        +version: str
        +add_middleware(middleware: Any) void
        +mount(path: str, app: Any, name: str) void
        +get(path: str) Callable
        +post(path: str) Callable
        +websocket(path: str) Callable
        +include_router(router: APIRouter) void
    }

    class APIRouter {
        <<framework>>
        +prefix: str
        +tags: List[str]
        +get(path: str) Callable
        +post(path: str) Callable
    }

    class WebSocket {
        <<framework>>
        +scope: Dict[str, Any]
        +accept() void
        +send_json(data: Dict) void
        +receive_text() str
        +close() void
    }

    class uvicornServer {
        <<framework>>
        +should_exit: bool
        +run() void
    }

    class Jinja2Templates {
        <<framework>>
        +directory: str
        +TemplateResponse(template: str, context: Dict) HTMLResponse
    }

    class StaticFiles {
        <<framework>>
        +directory: str
    }

    %% ================================================================================
    %% FRONTEND COMPONENTS
    %% ================================================================================
    class HTMLTemplate {
        <<template>>
        +modules: List[Dict]
        +base_browse_path: str
        +module_sections: List[ModuleSection]
        +api_explorer_tabs: List[Tab]
        +real_time_tabs: List[Tab]
        +file_browser_modal: Modal

        +render_module_list() str
        +render_method_cards() str
        +render_real_time_events() str
        +render_file_browser() str
    }

    class CSSStyles {
        <<stylesheet>>
        +dark_mode_styles: Dict[str, str]
        +light_mode_styles: Dict[str, str]
        +component_styles: Dict[str, str]
        +responsive_layout: Dict[str, str]
        +graph_container_styles: Dict[str, str]
        +modal_styles: Dict[str, str]

        +apply_dark_mode() void
        +apply_light_mode() void
        +style_components() void
    }

    class JavaScriptModule {
        <<script>>
        +webSockets: Dict[str, WebSocket]
        +moduleCharts: Dict[str, Chart]
        +channelData: Dict[str, Dict]
        +activeTypeFilters: Dict[str, str]
        +fileBrowserModal: Modal
        +currentBrowseTargetId: str
        +currentBrowseDefaultExt: str
        +currentBrowsePath: str

        +initDarkMode() void
        +toggleMethod(moduleId: str, methodId: str) void
        +executeMethod(moduleId: str, methodId: str) Promise[void]
        +connectWebSocket(moduleId: str) void
        +disconnectWebSocket(moduleId: str) void
        +clearEvents(moduleId: str) void
        +addEvent(moduleId: str, message: str, type: str) void
        +initOrUpdateGraph(moduleId: str) void
        +createSeparateChannelGraphs(moduleId: str, container: Element, activeType: str) void
        +createCombinedGraph(moduleId: str, canvas: Element, activeType: str) void
        +updateChannelData(moduleId: str, data: Dict) void
        +toggleGraphView(moduleId: str) void
        +toggleSeparateChannels(moduleId: str) void
        +clearAllCharts(moduleId: str) void
        +updateTypeFilters(moduleId: str, types: List[str], activeType: str) void
        +updateChartsForDarkMode(isDarkMode: bool) void
        +openBrowserDialog(overridePath: str) Promise[void]
    }

    %% ================================================================================
    %% DATA STRUCTURES
    %% ================================================================================
    class ModuleInfo {
        <<data structure>>
        +module_id: str
        +name: str
        +description: str
        +show_data_table: bool
        +method_groups: Dict[str, MethodGroup]
        +router: APIRouter

        +to_dict() Dict[str, Any]
        +add_method_group(group_id: str, group: MethodGroup) void
    }

    class MethodGroup {
        <<data structure>>
        +group_id: str
        +name: str
        +methods: Dict[str, MethodInfo]

        +add_method(method_id: str, method: MethodInfo) void
        +to_dict() Dict[str, Any]
    }

    class MethodInfo {
        <<data structure>>
        +method_id: str
        +name: str
        +description: str
        +type: str
        +params: Dict[str, ParameterInfo]
        +handler_function: Callable

        +to_dict() Dict[str, Any]
        +validate_params(input_params: Dict) bool
    }

    class ParameterInfo {
        <<data structure>>
        +param_id: str
        +type: str
        +required: bool
        +description: str
        +placeholder: str
        +options: Optional[List[str]]
        +min: Optional[Union[int, float]]
        +max: Optional[Union[int, float]]
        +step: Optional[Union[int, float]]
        +default: Optional[Any]
        +file_filter: Optional[str]
        +default_extension: Optional[str]
        +save_mode: Optional[bool]

        +validate_value(value: Any) bool
        +to_dict() Dict[str, Any]
    }

    class WebSocketConnection {
        <<data structure>>
        +websocket: WebSocket
        +module_id: str
        +connected_at: datetime
        +last_ping: datetime

        +send_event(event_data: Dict) Promise[void]
        +is_alive() bool
        +disconnect() void
    }

    class EventData {
        <<data structure>>
        +timestamp: float
        +event_type: str
        +module_id: str
        +data: Dict[str, Any]
        +visualization_data: Optional[Dict]

        +to_json() str
        +format_for_display() str
    }

    %% ================================================================================
    %% FRONTEND UI COMPONENTS
    %% ================================================================================
    class ModuleSection {
        <<UI component>>
        +module_id: str
        +tabs: List[Tab]
        +api_explorer_panel: APIExplorerPanel
        +real_time_panel: RealTimePanel

        +render() str
        +toggle_visibility() void
    }

    class APIExplorerPanel {
        <<UI component>>
        +method_list: MethodList
        +method_details: MethodDetails

        +render_methods() str
        +execute_method(method_id: str) void
    }

    class RealTimePanel {
        <<UI component>>
        +websocket_controls: WebSocketControls
        +event_display: EventDisplay
        +graph_container: GraphContainer
        +data_table: DataTable

        +connect_websocket() void
        +update_display(event: EventData) void
    }

    class MethodList {
        <<UI component>>
        +methods: List[MethodInfo]
        +selected_method: Optional[str]

        +render_list() str
        +select_method(method_id: str) void
    }

    class MethodDetails {
        <<UI component>>
        +method: MethodInfo
        +parameter_forms: List[ParameterForm]
        +response_display: ResponseDisplay

        +render_form() str
        +execute() Promise[void]
    }

    class ParameterForm {
        <<UI component>>
        +parameter: ParameterInfo
        +input_element: HTMLElement
        +validation_state: bool

        +render() str
        +get_value() Any
        +validate() bool
    }

    class GraphContainer {
        <<UI component>>
        +charts: Dict[str, Chart]
        +type_filters: TypeFilters
        +channel_data: Dict[str, List[float]]
        +separate_channels_mode: bool

        +init_chart(module_id: str) void
        +update_data(data: Dict) void
        +toggle_separate_mode() void
    }

    class DataTable {
        <<UI component>>
        +headers: List[str]
        +rows: List[Dict[str, Any]]
        +sort_column: Optional[str]
        +sort_direction: str

        +update_data(data: List[Dict]) void
        +sort_by_column(column: str) void
        +render() str
    }

    class FileModal {
        <<UI component>>
        +current_path: str
        +file_list: List[FileItem]
        +path_input: HTMLInputElement
        +file_prefix_input: HTMLInputElement
        +target_input_id: str

        +open(target_id: str) void
        +navigate_to(path: str) void
        +select_file() void
        +close() void
    }

    %% ================================================================================
    %% CHART VISUALIZATION COMPONENTS
    %% ================================================================================
    class ChartJS {
        <<external library>>
        +Chart: Class
        +defaults: ChartDefaults

        +new Chart(canvas: HTMLCanvasElement, config: ChartConfig) Chart
    }

    class Chart {
        <<chart instance>>
        +data: ChartData
        +options: ChartOptions
        +canvas: HTMLCanvasElement

        +update(mode: str) void
        +destroy() void
        +resize() void
    }

    class ChartData {
        <<chart data>>
        +labels: List[str]
        +datasets: List[Dataset]

        +add_data_point(value: float) void
        +remove_oldest_point() void
    }

    class Dataset {
        <<chart dataset>>
        +label: str
        +data: List[float]
        +borderColor: str
        +backgroundColor: str
        +borderWidth: float
        +pointRadius: float
        +tension: float
        +hidden: bool

        +update_data(values: List[float]) void
        +toggle_visibility() void
    }

    %% ================================================================================
    %% STANDARD LIBRARY COMPONENTS
    %% ================================================================================
    class threading {
        <<stdlib>>
        +Lock: Class
        +Thread: Class
    }

    class uvicorn {
        <<framework>>
        +run(app: FastAPI, host: str, port: int) void
        +Server: Class
        +Config: Class
    }

    class json {
        <<stdlib>>
        +loads(data: str) Dict
        +dumps(data: Dict) str
    }

    class logging {
        <<stdlib>>
        +info(message: str) void
        +error(message: str) void
        +warning(message: str) void
    }

    class os {
        <<stdlib>>
        +path: PathModule
        +makedirs(path: str, exist_ok: bool) void
        +listdir(path: str) List[str]
        +getcwd() str
    }

    %% ================================================================================
    %% RELATIONSHIPS
    %% ================================================================================

    %% Singleton Pattern
    ApiExplorer --|> ApiExplorer : singleton instance

    %% Main Module Dependencies
    MainModule --> ApiExplorer : creates and manages
    MainModule --> uvicorn : uses for server execution

    %% Framework Integration
    ApiExplorer "1" --> "1" FastAPI : manages
    ApiExplorer --> Jinja2Templates : uses for templating
    ApiExplorer --> StaticFiles : serves static content
    ApiExplorer --> uvicornServer : runs server
    ApiExplorer "1" --> "*" APIRouter : manages module routers
    ApiExplorer "1" --> "*" WebSocket : manages connections

    %% Data Structure Management
    ApiExplorer "1" --> "*" ModuleInfo : manages modules
    ModuleInfo "1" --> "*" MethodGroup : contains groups
    MethodGroup "1" --> "*" MethodInfo : contains methods
    MethodInfo "1" --> "*" ParameterInfo : defines parameters
    ApiExplorer "1" --> "*" WebSocketConnection : manages connections
    ApiExplorer --> EventData : broadcasts events

    %% Frontend Structure
    HTMLTemplate --> ModuleSection : renders sections
    ModuleSection "1" --> "1" APIExplorerPanel : contains
    ModuleSection "1" --> "1" RealTimePanel : contains
    APIExplorerPanel "1" --> "1" MethodList : contains
    APIExplorerPanel "1" --> "1" MethodDetails : contains
    MethodDetails "1" --> "*" ParameterForm : contains forms
    RealTimePanel "1" --> "1" GraphContainer : contains
    RealTimePanel "1" --> "1" DataTable : contains

    %% JavaScript Module Management
    JavaScriptModule --> ChartJS : uses for visualization
    JavaScriptModule "1" --> "*" Chart : manages charts
    Chart "1" --> "1" ChartData : contains data
    ChartData "1" --> "*" Dataset : contains datasets
    JavaScriptModule --> FileModal : manages file browser

    %% CSS and Styling
    CSSStyles --> HTMLTemplate : styles components
    CSSStyles --> ModuleSection : applies themes
    CSSStyles --> FileModal : styles modal

    %% Event Flow
    ApiExplorer --> WebSocket : broadcasts via
    WebSocket --> JavaScriptModule : receives events
    JavaScriptModule --> GraphContainer : updates charts
    JavaScriptModule --> DataTable : updates data

    %% File System Integration
    ApiExplorer --> os : accesses file system
    FileModal --> ApiExplorer : requests file listings

    %% Standard Library Usage
    ApiExplorer --> threading : uses for concurrency
    ApiExplorer --> json : uses for serialization
    ApiExplorer --> logging : uses for debugging
    ApiExplorer --> os : uses for file operations

    %% HTTP Request Handling
    FastAPI --> MethodInfo : routes to handlers
    APIRouter --> MethodInfo : contains route handlers
    ParameterInfo --> ParameterForm : defines form fields

    %% Real-time Communication
    WebSocketConnection --> EventData : transmits events
    EventData --> JavaScriptModule : updates frontend
    JavaScriptModule --> GraphContainer : updates visualizations

    %% Module Registration Flow
    note for ApiExplorer "Module Registration Flow:\n1. register_module() creates router\n2. add_method_group() organizes methods\n3. register_method() adds endpoints\n4. Routes automatically available in UI\n5. WebSocket events broadcast to clients"

    %% Frontend Architecture
    note for JavaScriptModule "Frontend Architecture:\n• Event-driven UI updates\n• Real-time chart visualization\n• WebSocket communication\n• Dynamic form generation\n• File browser integration\n• Dark/light mode theming"

    %% Chart Visualization
    note for GraphContainer "Chart Features:\n• Real-time data streaming\n• Multiple chart types\n• Channel separation mode\n• Type filtering (EEG, EMG, etc.)\n• Auto-scaling axes\n• Dark mode support"

    %% WebSocket Communication
    note for WebSocketConnection "WebSocket Features:\n• Per-module event routing\n• Automatic reconnection\n• Ping/pong keepalive\n• JSON event formatting\n• Connection status tracking"

    %% File Browser
    note for FileModal "File Browser Features:\n• Server-side directory listing\n• Path navigation\n• File prefix input\n• Extension filtering\n• Save/load mode support\n• Cross-platform paths"

    %% System Architecture
    note "API Explorer Architecture:\n• Singleton pattern for global access\n• Dynamic module registration\n• FastAPI backend with WebSocket support\n• Bootstrap + Chart.js frontend\n• File system integration\n• Real-time event streaming\n• Responsive dark/light theming\n• Cross-platform compatibility"
```
