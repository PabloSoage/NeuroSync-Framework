```mermaid
classDiagram
    %% Main Application Entry Points
    class run {
        <<module>>
        +cli_thread: Optional[threading.Thread]

        +parse_config() Dict[str, Any]
        +start_cli_in_thread() threading.Thread
        +cleanup_cli_thread() void
        +main() void
    }

    class InputCollectorApp {
        <<main application>>
        +dark_bg: str
        +dark_frame_bg: str
        +text_color: str
        +accent_color: str
        +success_color: str
        +warning_color: str
        +error_color: str
        +is_fullscreen: bool
        +tracked_keys: List[str]
        +collector_manager: CollectorManager
        +event_processor: EventProcessor
        +logging_manager: LoggingManager
        +ui_manager: UIManager
        +visualizer_manager: VisualizerManager
        +app_coordinator: AppCoordinator
        +update_timer: QTimer
        +_ps4_overlay_edit_mode: bool

        +__init__() void
        +run() void
        +closeEvent(event: Any) void
        -_initialize_components() void
        -_create_collector_manager() CollectorManager
        -_create_visualizer_manager() VisualizerManager
        -_connect_signals() void
        -_initialize_state() void
        -_initialize_ui() void
        -_sync_mouse_settings() void
        -_setup_shortcuts() void
        +_toggle_json_logging(enabled: bool) void
        +_toggle_csv_logging(enabled: bool) void
        +_select_csv_path() void
        +_switch_collector(collector_name: str) void
        +_scan_controllers() void
        +_toggle_fullscreen() void
        +_toggle_ps4_viz_mode(mode: str) void
        +_toggle_ps4_overlay_edit(enabled: bool) void
        +_discard_ps4_overlay_edits() void
        -_update_ui_for_collector() void
        -_update_active_keys_display() void
        -_on_recording_started() void
        -_on_recording_stopped() void
        -_on_edit_mode_toggled(enabled: bool) void
        -_on_collector_switched(collector_type: str, capabilities: Dict) void
        -_on_tracked_keys_changed(tracked_keys: List[str]) void
        -_handle_ps4_controller_switch() bool
        -_force_keyboard_mouse_mode() void
    }

    %% API Classes
    class InputCollectorAPI {
        <<interaction API>>
        +MOUSE_SETTING_RANGES: Dict[str, Tuple[int, int]]

        +initialize(app_coordinator: Any, ui_manager: Any, logging_manager: Any, collector_manager: Any, event_processor: Any)$ void
        +get_last_operation_status()$ Dict[str, Any]
        +start_recording()$ bool
        +stop_recording()$ bool
        +toggle_recording()$ bool
        +is_recording()$ bool
        +enable_json_logging(enabled: bool)$ bool
        +enable_csv_logging(enabled: bool, filepath: Optional[str])$ bool
        +set_csv_path(filepath: str)$ bool
        +get_logging_state()$ Dict[str, Any]
        +get_available_collectors()$ List[Dict[str, str]]
        +switch_collector(collector_type: str)$ bool
        +get_current_collector()$ Dict[str, Any]
        +scan_controllers()$ List[Dict[str, Any]]
        +connect_controller(index: int)$ bool
        +set_mouse_tracking_mode(mode: str, direction_only: Optional[bool])$ bool
        +set_mouse_settings(delta_smoothing: Optional[float], joystick_sensitivity: Optional[float], angle_grouping: Optional[int])$ bool
        +get_mouse_settings()$ Dict[str, Any]
        +get_tracked_keys()$ List[str]
        +toggle_edit_mode()$ bool
        +is_edit_mode()$ bool
        +add_tracked_key(key: str)$ bool
        +remove_tracked_key(key: str)$ bool
        +toggle_button_tracking(button_id: str, track: bool)$ bool
        +toggle_fullscreen()$ bool
        +get_application_state()$ Dict[str, Any]
        +get_available_tracking_modes(direction_only: Optional[bool])$ List[str]
        -_parse_bool(val: Any)$ bool
    }

    class InputDataAPI {
        <<data access API>>
        +get_current_event()$ Optional[InputData]
        +get_key_events(max_count: Optional[int])$ List[InputData]
        +get_mouse_movement_events(max_count: Optional[int])$ List[InputData]
        +get_mouse_button_events(max_count: Optional[int])$ List[InputData]
        +get_controller_events(max_count: Optional[int])$ List[InputData]
        +get_active_keys()$ List[str]
        +is_key_active(key: str)$ bool
        +get_mouse_position()$ Tuple[float, float]
        +get_mouse_button_state(button: str)$ bool
        +get_metadata()$ Dict[str, Any]
        +register_event_callback(callback: Callable)$ int
        +unregister_event_callback(callback_id: int)$ bool
        +is_mouse_moving()$ bool
        +get_mouse_direction()$ Optional[str]
        +is_controller_connected()$ bool
        +get_controller_name()$ str
    }

    %% API Integration Classes
    class InputCollectorApiIntegration {
        <<data API integration>>
        +explorer: Optional[Any]
        +module_id: str
        +is_registered: bool
        +event_callback_id: Optional[int]
        +fallback_method_groups: Dict[str, Dict[str, Any]]
        +fallback_methods: Dict[str, Dict[str, Any]]
        +module_registered: bool
        +_event_subscriptions: List[Tuple[EventType, Callable]]
        +_pressed_buttons: Set[str]
        +_ps4_button_states: Dict[str, bool]
        +_ps4_active_buttons: Set[str]
        +_ps4_stick_states: Dict[str, Dict[str, Union[float, str]]]
        +_ps4_trigger_states: Dict[str, float]

        +__init__() void
        +register_api(start_server: bool, host: str, port: int) bool
        +shutdown() void
        -_find_available_port(host: str, port: int) int
        -_is_port_in_use(host: str, port: int) bool
        -_register_module() bool
        -_register_module_fallback() bool
        -_register_all_methods() void
        -_register_method_groups() void
        -_register_state_methods() void
        -_register_event_methods() void
        -_register_controller_methods() void
        -_register_callback_methods() void
        -_setup_websocket_events() void
        -_subscribe_to_core_events() void
        -_handle_core_event(event_type: EventType, data: Any) void
        -_format_mouse_event(event_data: Any) Optional[Dict]
        -_angle_to_direction(angle: int) str
        -_update_ps4_controller_state(data: Any) void
        -_get_ps4_controller_state() Dict[str, Any]
        -_get_stick_direction(x_value: float, y_value: float) str
        -_broadcast_event(event_dict: Dict) void
        -_event_to_dict(event: Any) Dict
    }

    class InteractionApiIntegration {
        <<control API integration>>
        +explorer: Optional[Any]
        +module_id: str
        +is_registered: bool
        +fallback_method_groups: Dict[str, Dict[str, Dict[str, Any]]]
        +fallback_methods: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]
        +module_registered: bool
        +_event_subscriptions: List[Tuple[EventType, Callable]]
        +_pressed_buttons: Set[str]
        +data_api_integration: Optional[Any]
        +_ps4_button_states: Dict[str, bool]
        +_ps4_active_buttons: Set[str]
        +_ps4_stick_states: Dict[str, Dict[str, Union[float, str]]]
        +_ps4_trigger_states: Dict[str, float]

        +__init__() void
        +register_api(start_server: bool, host: str, port: int) bool
        +shutdown() void
        -_register_module() bool
        -_register_module_fallback() bool
        -_register_all_methods() void
        -_register_method_groups() void
        -_register_recording_methods() void
        -_register_logging_methods() void
        -_register_collector_methods() void
        -_register_mouse_methods() void
        -_register_key_methods() void
        -_register_ui_methods() void
        -_setup_websocket_events() void
        -_subscribe_to_core_events() void
        -_handle_core_event(event_type: EventType, data: Any) void
        -_format_mouse_event(event_data: Any) Optional[Dict]
        -_update_ps4_controller_state(data: Any) void
        -_get_ps4_controller_state() Dict[str, Any]
        -_broadcast_event(event_dict: Dict) void
        -_event_to_dict(event: Any) Dict
        +_handle_start_recording()$ Dict[str, Any]
        +_handle_stop_recording()$ Dict[str, Any]
        +_handle_toggle_recording()$ Dict[str, Any]
        +_handle_is_recording()$ Dict[str, Any]
        +_handle_enable_json_logging(enabled: bool)$ Dict[str, Any]
        +_handle_enable_csv_logging(enabled: bool, filepath: Optional[str])$ Dict[str, Any]
        +_handle_set_csv_path(filepath: str)$ Dict[str, Any]
        +_handle_get_logging_state()$ Dict[str, Any]
        +_handle_get_available_collectors()$ Dict[str, Any]
        +_handle_switch_collector(collector_type: str)$ Dict[str, Any]
        +_handle_get_current_collector()$ Dict[str, Any]
        +_handle_scan_controllers()$ Dict[str, Any]
        +_handle_connect_controller(index: int)$ Dict[str, Any]
        +_handle_set_mouse_tracking_mode(mode: str, direction_only: Optional[bool])$ Dict[str, Any]
        +_handle_set_mouse_settings(delta_smoothing: Optional[float], joystick_sensitivity: Optional[float], angle_grouping: Optional[int])$ Dict[str, Any]
        +_handle_get_mouse_settings()$ Dict[str, Any]
        +_handle_get_tracked_keys()$ Dict[str, Any]
        +_handle_toggle_edit_mode()$ Dict[str, Any]
        +_handle_is_edit_mode()$ Dict[str, Any]
        +_handle_add_tracked_key(key: str)$ Dict[str, Any]
        +_handle_remove_tracked_key(key: str)$ Dict[str, Any]
        +_handle_toggle_button_tracking(button_id: str, track: bool)$ Dict[str, Any]
        +_handle_toggle_fullscreen()$ Dict[str, Any]
        +_handle_get_application_state()$ Dict[str, Any]
    }

    %% Submodule References
    class AppSubmodule {
        <<submodule>>
        +AppCoordinator
        +EventCoordination
        +ComponentOrchestration
    }

    class CollectorsSubmodule {
        <<submodule>>
        +CollectorManager
        +KeyboardMouseCollector
        +PS4ControllerCollector
        +ThreadSafeEventProcessing
        +SDL2EventLoop
        +AutomaticReconnection
        +is_sdl2_available
    }

    class InterfacesSubmodule {
        <<submodule>>
        +InputData
        +AbstractInputCollector
        +AbstractVisualizer
        +AbstractVisualizerProvider
        +AbstractVisualizerController
        +ContractDefinitions
    }

    class VisualizersSubmodule {
        <<submodule>>
        +KeyboardVisualizer
        +MouseVisualizer
        +MouseButtonsSelector
        +PS4ControllerVisualizer
        +BaseVisualizer
        +ThreadSafeUpdates
        +SplitPanelInterface
        +RealTimeStateLogging
        +EnhancedEditMode
    }

    class LoggingSubmodule {
        <<submodule>>
        +LoggingManager
        +CSVLogger
        +JSONLogger
        +MultiformatLogging
    }

    class UISubmodule {
        <<submodule>>
        +UIManager
        +VisualizerManager
        +DarkThemeSupport
        +ResponsiveLayout
    }

    class ProcessingSubmodule {
        <<submodule>>
        +EventProcessor
        +EventFiltering
        +SpecialEventDetection
    }

    class ServicesSubmodule {
        <<submodule>>
        +InteractionService
        +DataAccessService
        +SingletonServices
        +ThreadSafeOperations
    }

    class AdaptersSubmodule {
        <<submodule>>
        +QtInteractionAdapter
        +ThreadSafeAdaptation
        +FrameworkIsolation
    }

    class CoreSubmodule {
        <<submodule>>
        +EventSystem
        +EventType
        +EventDispatcher
        +DecoupledCommunication
        +ThreadSafeEventDelivery
    }

    class CLISubmodule {
        <<submodule>>
        +CLIApp
        +CLIShell
        +CLIConfig
        +DataCommands
        +InteractionCommands
        +MonitorCommands
        +PS4ControllerMonitor
        +CoreEventSystemIntegration
        +CrossPlatformSupport
        +RichConsoleInterface
        +EventDrivenMonitoring
    }

    %% Qt Framework Components
    class QMainWindow {
        <<Qt>>
        +showFullScreen() void
        +showNormal() void
        +closeEvent(event: Any) void
    }

    class QApplication {
        <<Qt>>
        +exec_() int
        +processEvents() void
        +desktop() QDesktopWidget
    }

    class QTimer {
        <<Qt>>
        +timeout: pyqtSignal
        +start(msec: int) void
        +singleShot(msec: int, slot: Callable)$ void
    }

    %% External API Framework
    class ApiExplorer {
        <<external>>
        +get_instance()$ ApiExplorer
        +register_module(module_id: str, name: str, description: str) bool
        +add_method_group(module_id: str, group_id: str, name: str) bool
        +register_method(module_id: str, group_id: str, method_id: str, method_info: Dict, handler: Callable) void
        +start_server(host: str, port: int) void
        +broadcast_event(event_dict: Dict) void
        +is_running: bool
        +server_port: Optional[int]
    }

    %% Configuration Classes
    class Config {
        <<configuration>>
        +fullscreen: bool
        +no_gui: bool
        +cli: bool
        +enable_web_api: bool
        +api_host: str
        +api_port: int
        +enable_control_api: bool
        +control_api_host: str
        +control_api_port: int
    }

    %% Singleton Integration Functions
    class APIFunctions {
        <<module functions>>
        +get_api_integration() InputCollectorApiIntegration
        +initialize_api(enable_web_api: bool, host: str, port: int) bool
        +get_interaction_api_integration() InteractionApiIntegration
        +initialize_interaction_api(enable_web_api: bool, host: str, port: int) bool
    }

    %% Standard Library Components
    class threading {
        <<stdlib>>
        +Thread
        +Event
        +Lock
        +current_thread() Thread
        +main_thread() Thread
    }

    class argparse {
        <<stdlib>>
        +ArgumentParser
        +Namespace
    }

    class sys {
        <<stdlib>>
        +argv: List[str]
        +path: List[str]
        +exit(code: int) void
    }

    %% Main Relationships
    run --> InputCollectorApp : creates and runs
    run --> Config : parses configuration
    run --> APIFunctions : initializes APIs
    run --> CLISubmodule : starts CLI thread
    run --> threading : manages CLI thread

    QMainWindow <|-- InputCollectorApp : inherits

    InputCollectorApp --> AppSubmodule : coordinates via AppCoordinator
    InputCollectorApp --> CollectorsSubmodule : manages via CollectorManager
    InputCollectorApp --> UISubmodule : presents via UIManager
    InputCollectorApp --> VisualizersSubmodule : displays via VisualizerManager
    InputCollectorApp --> LoggingSubmodule : logs via LoggingManager
    InputCollectorApp --> ProcessingSubmodule : processes via EventProcessor
    InputCollectorApp --> QTimer : uses for updates

    %% API Relationships
    InputCollectorAPI --> ServicesSubmodule : delegates to InteractionService
    InputDataAPI --> ServicesSubmodule : delegates to DataAccessService

    InputCollectorApiIntegration --> InputDataAPI : exposes methods
    InputCollectorApiIntegration --> ApiExplorer : integrates with
    InputCollectorApiIntegration --> CoreSubmodule : subscribes to events

    InteractionApiIntegration --> InputCollectorAPI : exposes methods
    InteractionApiIntegration --> ApiExplorer : integrates with
    InteractionApiIntegration --> CoreSubmodule : subscribes to events
    InteractionApiIntegration --> InputCollectorApiIntegration : reuses utilities

    %% Service Layer Integration
    InputCollectorApp --> InputCollectorAPI : initializes
    InputCollectorAPI --> ServicesSubmodule : uses InteractionService
    InputDataAPI --> ServicesSubmodule : uses DataAccessService

    %% Cross-Module Dependencies
    InputCollectorApp --> InterfacesSubmodule : uses InputData and interfaces
    InputCollectorApiIntegration --> InterfacesSubmodule : processes InputData
    InteractionApiIntegration --> InterfacesSubmodule : handles InputData

    %% Enhanced Core Event System Integration
    CLISubmodule --> CoreSubmodule : uses EventSystem for monitoring
    CollectorsSubmodule --> CoreSubmodule : dispatches events via EventSystem
    VisualizersSubmodule --> CoreSubmodule : receives thread-safe updates
    ProcessingSubmodule --> CoreSubmodule : coordinates via EventDispatcher
    AppSubmodule --> CoreSubmodule : orchestrates through EventSystem

    %% Thread-Safe Communication
    CollectorsSubmodule --> VisualizersSubmodule : thread-safe UI updates
    CLISubmodule --> CollectorsSubmodule : event-driven monitoring
    VisualizersSubmodule --> UISubmodule : split panel interfaces

    %% Framework Integration
    InputCollectorApp --> QApplication : requires for GUI
    run --> argparse : parses command line
    run --> sys : manages paths and exit

    %% Enhanced Submodule Notes
    note for CLISubmodule "Enhanced CLI with event-driven monitoring:\n• PS4 controller real-time display\n• Cross-platform key detection (ESC/Q)\n• Rich console interface with tables/panels\n• Core event system integration\n• Smart collector-specific monitoring\n• Thread-safe operations with cleanup"

    note for CollectorsSubmodule "Thread-safe event processing:\n• SDL2 event loop architecture\n• Automatic reconnection capabilities\n• Enhanced PS4 controller support\n• Event-driven state management\n• Core event system integration"

    note for VisualizersSubmodule "Thread-safe UI updates:\n• Split panel PS4 interface\n• Real-time state logging\n• Enhanced edit mode capabilities\n• Signal/slot based updates\n• Dark theme support"

    note for CoreSubmodule "Centralized event system:\n• Framework-independent communication\n• Thread-safe event delivery\n• Decoupled component interaction\n• Subscribe/unsubscribe patterns\n• Event type enumeration"

    %% Main Application Notes
    note for run "Main entry point script\nParses configuration from command line\nStarts GUI, CLI, and web APIs as configured\nManages thread coordination and cleanup"

    note for InputCollectorApp "Main GUI application class\nIntegrates all submodules into cohesive app\nManages Qt widgets and event handling\nCoordinates between UI, collectors, and logging"

    note for InputCollectorAPI "Static facade for application control\nProvides API for external access\nDelegates to InteractionService for operations\nHandles parameter validation and UI synchronization"

    note for InputDataAPI "Static facade for data access\nProvides real-time access to input events\nDelegates to DataAccessService for data\nOptimized for low-latency queries"

    note for InputCollectorApiIntegration "Web API integration for data access\nRegisters methods with API Explorer\nProvides WebSocket real-time events\nMaintains PS4 controller state tracking"

    note for InteractionApiIntegration "Web API integration for application control\nRegisters control methods with API Explorer\nProvides remote control\nReuses utilities from data API integration"

    %% Architecture Overview
    note "Enhanced Module Architecture:\n• Event-driven communication via CoreSubmodule\n• Thread-safe operations across all components\n• Enhanced PS4 controller support with real-time monitoring\n• Rich CLI interface with cross-platform compatibility\n• Split panel visualizer interfaces\n• Core event system for decoupled communication\n• Improved error handling and recovery mechanisms"

    %% Execution Flow
    note "Enhanced Execution Flow:\n1. run.py parses configuration and initializes components\n2. Core event system establishes communication channels\n3. Collectors initialize with thread-safe event processing\n4. CLI starts with event-driven monitoring capabilities\n5. GUI initializes with enhanced visualizers\n6. All components communicate via core event system\n7. Thread-safe updates and real-time state synchronization\n8. Coordinated cleanup with proper thread management"
```
