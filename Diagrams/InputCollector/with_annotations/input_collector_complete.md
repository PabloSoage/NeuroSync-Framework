```mermaid
classDiagram
    %% ================================================================================
    %% MAIN APPLICATION ENTRY POINTS
    %% ================================================================================
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
        +run_collector_app() void
    }

    %% ================================================================================
    %% CORE API CLASSES
    %% ================================================================================
    class InputCollectorAPI {
        <<interaction API>>
        +MOUSE_SETTING_RANGES: Dict[str, Tuple[int, int]]

        +initialize(...)$ void
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
        +set_mouse_settings(...)$ bool
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

    %% ================================================================================
    %% INTERFACES SUBMODULE
    %% ================================================================================
    class InputData {
        <<dataclass>>
        +timestamp: float
        +event_type: str
        +key: Optional[str]
        +mouse_x: Optional[float]
        +mouse_y: Optional[float]
        +button_pressed: Optional[str]
        +button: Optional[str]
        +direction: Optional[str]
        +speed: Optional[float]
        +speed_x: Optional[float]
        +speed_y: Optional[float]
        +rel_x: Optional[float]
        +rel_y: Optional[float]
        +is_moving: Optional[bool]
        +active_keys: Optional[List[str]]
        +mouse_delta_x: Optional[float]
        +mouse_delta_y: Optional[float]
        +mouse_delta_magnitude: Optional[float]
        +mouse_delta_angle: Optional[float]
        +mouse_tracking_mode: Optional[str]
        +direction_only: Optional[bool]
        +discrete_angle: Optional[int]
        +north: Optional[float]
        +south: Optional[float]
        +east: Optional[float]
        +west: Optional[float]

        +__post_init__() void
        +to_dict() Dict[str, Any]
    }

    class AbstractInputCollector {
        <<abstract>>
        +start_capture()* void
        +stop_capture()* void
        +get_input_event()* InputData
        +on_event(callback: Callable)* void
        +set_supported_keys(keys: List[str])* void
        +get_events_since(timestamp: float)* List[InputData]
        +clear_events()* void
        +get_active_keys() List[str]
        +get_collector_type() str
        +get_capabilities() Dict[str, Any]
    }

    class AbstractVisualizer {
        <<abstract>>
        +update(input_data: Optional[InputData])* void
        +force_update()* void
        +set_collector_capabilities(capabilities: Dict[str, Any]) void
        +set_edit_mode(enabled: bool) void
        +supports_collector(collector_type: str) bool
    }

    class AbstractVisualizerProvider {
        <<protocol>>
        +get_keyboard_visualizer() Any
        +get_mouse_visualizer() Any
        +get_mouse_buttons_selector() Any
    }

    class AbstractVisualizerController {
        <<protocol>>
        +update_for_collector(collector_type: str, capabilities: Dict[str, Any]) void
        +set_tracked_keys(keys: List[str]) void
        +set_scroll_tracking(enabled: bool) void
        +set_edit_mode(enabled: bool) void
        +force_update() void
    }

    %% ================================================================================
    %% COLLECTORS SUBMODULE
    %% ================================================================================
    class CollectorManager {
        -collectors: Dict[str, AbstractInputCollector]
        -current_collector: Optional[AbstractInputCollector]
        -current_collector_type: Optional[str]
        -visualizers: List[Any]
        -tracked_keys: List[str]
        -event_callbacks: List[Callable]
        -data_access_service: DataAccessService

        +__init__() void
        +add_collector(collector_type: str, collector: AbstractInputCollector) void
        +set_current_collector(collector_type: str) bool
        +get_available_collectors() List[Dict[str, str]]
        +start_capture() void
        +stop_capture() void
        +register_visualizer(visualizer: Any) void
        +unregister_visualizer(visualizer: Any) void
        +set_tracked_keys(keys: List[str]) void
        +get_active_keys() List[str]
        +on_event(callback: Callable) void
        +remove_event_handler(callback: Callable) void
        +get_current_collector_capabilities() Dict[str, Any]
        +get_current_collector_type() str
        +get_collector(collector_type: str) Optional[AbstractInputCollector]
        +get_current_collector() Optional[AbstractInputCollector]
        -_initialize_collectors() void
        -_get_collector_display_name(collector_type: str) str
        -_update_visualizers() void
        -_update_visualizer(visualizer: Any) void
        -_handle_input_event(event: InputData) void
        -_get_controller_name() str
    }

    class KeyboardMouseCollector {
        -keyboard_events: List[InputData]
        -mouse_events: List[InputData]
        -supported_keys: List[str]
        -is_capturing: bool
        -event_callbacks: List[Callable]
        -key_state: Dict[str, bool]
        -mouse_state: Dict[str, Any]
        -keyboard_listener: Optional[keyboard.Listener]
        -mouse_listener: Optional[mouse.Listener]
        -mouse_tracking_mode: str
        -direction_only: bool
        -angle_grouping: int

        +__init__() void
        +start_listeners() void
        +stop_listeners() void
        +on_press(key: Any) bool
        +on_release(key: Any) bool
        +on_move(x: int, y: int) void
        +on_click(x: int, y: int, button: Any, pressed: bool) void
        +on_scroll(x: int, y: int, dx: int, dy: int) void
        +set_screen_dimensions(width: int, height: int) void
        +set_joystick_sensitivity(sensitivity: float) void
        +set_mouse_tracking_mode(mode: str, direction_only: bool, angle_grouping: int) void
        -_reset_mouse_state(x: int, y: int) void
        -_reset_wheel(x: int, y: int) void
        -_process_event(event: InputData) void
        -_get_delta_direction() Optional[str]
        -_get_angle_direction() Optional[str]
        -_get_joystick_direction(velocity_x: float, velocity_y: float) Optional[str]
    }

    class PS4ControllerCollector {
        -controller_events: List[InputData]
        -is_capturing: bool
        -event_callbacks: List[Callable]
        -controller: SDL_GameController
        -joystick: SDL_Joystick
        -controller_name: str
        -controller_index: int
        -button_states: Dict[str, bool]
        -stick_positions: Dict[str, tuple]
        -trigger_values: Dict[str, float]
        -previous_trigger_values: Dict[str, float]
        -previous_stick_positions: Dict[str, tuple]
        -event_thread: Optional[threading.Thread]
        -event_stop_event: threading.Event
        -event_lock: threading.Lock
        -max_events: int
        -tracked_keys_set: Set[str]
        -supported_keys: List[str]

        +__init__() void
        +initialize_sdl() bool
        +start_capture() void
        +stop_capture() void
        +scan_controllers() List[Dict[str, Any]]
        +connect_to_first_available() bool
        +connect_to_controller(controller_index: int) bool
        +get_input_event() InputData
        +on_event(callback: Callable) void
        +set_supported_keys(keys: List[str]) void
        +get_events_since(timestamp: float) List[InputData]
        +clear_events() void
        +get_active_keys() List[str]
        +get_collector_type() str
        +get_capabilities() Dict[str, Any]
        -_process_sdl_event(event: sdl2.SDL_Event) void
        -_handle_button_event(button_event: sdl2.SDL_ControllerButtonEvent, is_pressed: bool) void
        -_handle_joystick_button_event(button_event: sdl2.SDL_JoyButtonEvent, is_pressed: bool) void
        -_handle_axis_event(axis_event: sdl2.SDL_ControllerAxisEvent) void
        -_on_controller_disconnected() void
        -_try_reconnect() void
        -_process_event(event: InputData) void
        -_safe_callback(callback: Callable[[InputData], None], event: InputData) void
        -_event_loop() void
    }

    %% ================================================================================
    %% VISUALIZERS SUBMODULE
    %% ================================================================================
    class BaseVisualizer {
        +capabilities: Dict[str, Any]
        +edit_mode: bool
        +supported_collectors: List[str]

        +__init__(parent: Optional[QWidget]) void
        +update(input_data: Optional[InputData]) void
        +force_update() void
        +set_collector_capabilities(capabilities: Dict[str, Any]) void
        +set_edit_mode(enabled: bool) void
        +supports_collector(collector_type: str) bool
    }

    class KeyboardVisualizer {
        -DEFAULT_KEYBOARD_LAYOUT: List[List[str]]
        -dark_bg: QColor
        -key_bg: QColor
        -key_text: QColor
        -tracked_key_bg: QColor
        -active_key_bg: QColor
        -active_keys: Set[str]
        -tracked_keys: Set[str]
        -key_mappings: Dict[str, str]
        -key_rects: Dict[str, QRect]

        +__init__(parent: Optional[QWidget]) void
        +set_tracked_keys(keys: List[str]) void
        +get_key_at_position(x: int, y: int) Optional[str]
        +paintEvent(event: QPaintEvent) void
        +sizeHint() QSize
        +minimumSizeHint() QSize
        -_create_key_mappings() void
    }

    class MouseVisualizer {
        -dark_bg: QColor
        -info_label: QLabel
        -button_label: QLabel
        -canvas: Canvas

        +__init__(parent: Optional[QWidget]) void
        +update(input_data: Optional[Any]) void
        +force_update() void
        +sizeHint() QSize
        +set_collector_capabilities(capabilities: Dict[str, Any]) void
    }

    class Canvas {
        -mouse_x: int
        -mouse_y: int
        -rel_x: float
        -rel_y: float
        -movement_direction: Optional[str]
        -left_button_pressed: bool
        -right_button_pressed: bool
        -middle_button_pressed: bool
        -is_moving: bool
        -speed: float
        -tracking_mode: str
        -direction_only: bool
        -discrete_angle: int
        -north: float
        -south: float
        -east: float
        -west: float

        +__init__(parent: Optional[QWidget]) void
        +update_state(input_data: Any) void
        +paintEvent(event: QPaintEvent) void
    }

    class MouseButtonsSelector {
        +button_toggled: pyqtSignal
        -left_button: MouseButton
        -right_button: MouseButton
        -scroll_button: MouseButton

        +__init__(parent: Optional[QWidget]) void
        +setTrackedButtons(button_ids: List[str]) void
        +setActiveButtons(active_buttons: List[str]) void
        +setEditMode(edit_mode: bool) void
        +setScrollTracking(enabled: bool) void
        +isScrollTracked() bool
        +sizeHint() QSize
        -_on_button_clicked(button_id: str) void
    }

    class MouseButton {
        +clicked: pyqtSignal
        -button_id: str
        -label: str
        -tracked: bool
        -active: bool
        -edit_mode: bool

        +__init__(button_id: str, label: str, parent: Optional[QWidget]) void
        +paintEvent(event: QPaintEvent) void
        +mousePressEvent(event: QMouseEvent) void
        +setTracked(tracked: bool) void
        +setActive(active: bool) void
        +setEditMode(edit_mode: bool) void
        +sizeHint() QSize
    }

    class PS4ControllerVisualizer {
        +key_clicked: pyqtSignal
        +update_requested: pyqtSignal
        -button_states: Dict[str, bool]
        -stick_positions: Dict[str, tuple]
        -trigger_values: Dict[str, float]
        -image_mode: bool
        -images_loaded: bool
        -images: Dict[str, Dict[str, Any]]
        -base_image: Optional[QPixmap]
        -positions_file: Path
        -_edit_mode: bool
        -selected_item: Optional[str]
        -drag_start: Optional[QPoint]
        -element_groups: Dict[str, List[str]]
        -controller_widget: QWidget
        -right_panel: QWidget
        -log_text: QTextEdit
        -state_update_timer: QTimer
        -splitter: QSplitter
        -state_panel: QWidget
        -active_buttons_display: QTextEdit
        -left_x_value: QLabel
        -right_x_value: QLabel
        -left_trigger_value: QLabel
        -right_trigger_value: QLabel
        -_snapshot: Dict[str, Optional[Tuple[int, int]]]
        -_should_commit: bool
        -_ps4_active_buttons: Set[str]

        +__init__(parent: Optional[QWidget]) void
        +_init_ui() void
        +load_images() void
        +toggle_edit_mode() bool
        +set_edit_mode(enabled: bool) void
        +toggle_image_mode() bool
        +set_image_mode(use_image_mode: bool) bool
        +update_state_display() void
        +log_event(event_data: Any, color: Optional[str]) void
        +clear_log() void
        +restore_positions() void
        +mousePressEvent(event: QMouseEvent) void
        +mouseMoveEvent(event: QMouseEvent) void
        +mouseReleaseEvent(event: QMouseEvent) void
        +_paint_controller(event: QPaintEvent) void
        +paintEvent(event: QPaintEvent) void
        +paint_edit_overlays(painter: QPainter) void
        +paint_image_mode(painter: QPainter) void
        +paint_drawn_mode(painter: QPainter) void
        +draw_image_analog_sticks(painter: QPainter) void
        +draw_image_triggers(painter: QPainter) void
        +draw_dpad(painter: QPainter, x: int, y: int) void
        +draw_action_buttons(painter: QPainter, x: int, y: int) void
        +draw_analog_stick(painter: QPainter, x: int, y: int, stick: str) void
        +draw_shoulder_buttons(painter: QPainter) void
        +draw_triggers(painter: QPainter) void
        +draw_start_select(painter: QPainter) void
        +_thread_safe_update(input_data: InputData) void
        +_log_event_main_thread(event_data: Any, color: Optional[str]) void
        +load_positions_from_json() Dict[str, Any]
        +get_default_positions() Dict[str, Dict[str, Any]]
        +save_positions_to_json() bool
        +find_group_for_item(item_key: str) Optional[str]
        +move_group(group_name: str, delta_x: int, delta_y: int) void
    }

    %% ================================================================================
    %% LOGGING SUBMODULE
    %% ================================================================================
    class LoggingManager {
        +status_message: pyqtSignal
        -json_logger: JSONLogger
        -csv_logger: CSVLogger
        -log_to_json: bool
        -log_to_csv: bool

        +__init__() void
        +set_json_logging(enabled: bool) bool
        +set_csv_logging(enabled: bool, filepath: Optional[str]) bool
        +initialize_csv_file(headers: List[str], tracked_keys: List[str], tracking_mode: str, direction_only: bool) bool
        +log_event(event: InputData, collector_type: str) void
        +start_recording() void
        +stop_recording() void
        +close_all() void
    }

    class JSONLogger {
        +status_message: pyqtSignal
        -log_file: Optional[TextIO]

        +__init__() void
        +open_log() bool
        +close_log() void
        +log_recording_start() void
        +log_recording_stop() void
        +log_event(event: InputData, collector_type: str) void
    }

    class CSVLogger {
        +status_message: pyqtSignal
        -csv_file: Optional[TextIO]
        -csv_writer: Optional[Any]
        -csv_headers: List[str]
        -filepath: str

        +__init__() void
        +set_filepath(filepath: str) void
        +initialize(headers: List[str], tracked_keys: List[str], tracking_mode: str, direction_only: bool) bool
        +close_log() void
        +log_event(event: InputData, collector_type: str) void
    }

    %% ================================================================================
    %% UI SUBMODULE
    %% ================================================================================
    class UIManager {
        +toggle_recording: pyqtSignal
        +toggle_json_logging: pyqtSignal
        +toggle_csv_logging: pyqtSignal
        +select_csv_path: pyqtSignal
        +switch_collector: pyqtSignal
        +scan_controllers: pyqtSignal
        +toggle_edit_mode: pyqtSignal
        +update_tracking_mode: pyqtSignal
        +set_mouse_tracking_mode: pyqtSignal
        +apply_mouse_settings: pyqtSignal
        +toggle_fullscreen: pyqtSignal
        +mouse_button_toggled: pyqtSignal
        +toggle_ps4_viz_mode: pyqtSignal
        +toggle_ps4_overlay_edit: pyqtSignal
        +toggle_ps4_overlay_discard: pyqtSignal

        -main_window: QMainWindow
        -components: Dict[str, Any]
        -main_layout: QVBoxLayout
        -left_viz_layout: QVBoxLayout
        -in_unified_mode: bool

        +__init__(main_window: QMainWindow) void
        +set_visualizers(...) void
        +update_recording_state(is_recording: bool) void
        +update_collector_list(collectors: List[Dict[str, str]]) void
        +select_collector(collector_type: str) void
        +update_ui_for_collector(collector_type: str, capabilities: Dict[str, Any]) void
        +set_csv_path(path: str) void
        +log_status(message: str, color: Optional[str]) void
        +update_active_keys_display(active_keys: List[str]) void
        +is_direction_only_mode() bool
        +set_direction_only_checkbox(enabled: bool) void
        +get_tracking_mode() str
        +get_angle_grouping() int
        +get_delta_smoothing() float
        +get_joystick_sensitivity() float
        +update_tracking_modes(valid_modes: List[str], current_mode: str, default_mode: str) void
        +get_current_collector_data() Optional[str]
        +select_collector_by_type(collector_type: str) void
        +update_edit_mode(enabled: bool) void
        +hide_recording_controls() void
        +update_ps4_overlay_edit_state(edit_mode: bool) void
    }

    class VisualizerManager {
        +key_clicked: pyqtSignal
        +button_toggled: pyqtSignal

        -edit_mode_enabled: bool
        -keyboard_viz: KeyboardVisualizer
        -mouse_viz: MouseVisualizer
        -mouse_buttons_selector: MouseButtonsSelector
        -ps4_controller_viz: PS4ControllerVisualizer
        -keyboard_event_filter: KeyboardEventFilter

        +__init__(parent: Optional[QWidget]) void
        +get_keyboard_visualizer() KeyboardVisualizer
        +get_mouse_visualizer() MouseVisualizer
        +get_mouse_buttons_selector() MouseButtonsSelector
        +get_ps4_controller_visualizer() PS4ControllerVisualizer
        +update_for_collector(collector_type: str, capabilities: Dict[str, Any]) void
        +set_tracked_keys(keys: List[str]) void
        +set_scroll_tracking(enabled: bool) void
        +set_edit_mode(enabled: bool) void
        +force_update() void
    }

    class KeyboardEventFilter {
        -visualizer_manager: VisualizerManager

        +__init__(visualizer_manager: VisualizerManager) void
        +eventFilter(obj: QObject, event: QEvent) bool
    }

    %% ================================================================================
    %% PROCESSING SUBMODULE
    %% ================================================================================
    class EventProcessor {
        +toggle_recording_requested: pyqtSignal
        -f9_key_down: bool

        +__init__() void
        +process_event(event: InputData, collector_type: str) Dict[str, Any]
        -_is_special_event(event: InputData) bool
        -_process_special_event(event: InputData) Dict[str, Any]
        -_should_log_event(event: InputData) bool
        -_format_display_text(event: InputData, collector_type: str) str
        -_format_keyboard_mouse_event_text(event: InputData) str
        -_format_keyboard_part(event: InputData) str
        -_format_mouse_part(event: InputData) str
        -_has_button_press(event: InputData) bool
        -_has_scroll_event(event: InputData) bool
        -_add_movement_info(mouse_parts: List[str], event: InputData, tracking_mode: str) void
        -_add_delta_mode_info(mouse_parts: List[str], event: InputData) void
        -_add_angle_mode_info(mouse_parts: List[str], event: InputData) void
        -_add_axis_mode_info(mouse_parts: List[str], event: InputData) void
        -_add_joystick_mode_info(mouse_parts: List[str], event: InputData) void
        -_format_ps4_event_text(event: InputData) str
        -_format_axis_motion(event: InputData, active_keys: List[str]) str
        -_format_joystick_axis(event: InputData, active_keys: List[str]) str
    }

    %% ================================================================================
    %% APP COORDINATOR SUBMODULE
    %% ================================================================================
    class AppCoordinator {
        +event_received: pyqtSignal
        +recording_started: pyqtSignal
        +recording_stopped: pyqtSignal
        +edit_mode_toggled: pyqtSignal
        +collector_switched: pyqtSignal
        +tracked_keys_changed: pyqtSignal

        -collector_manager: CollectorManager
        -ui_manager: UIManager
        -logging_manager: LoggingManager
        -event_processor: EventProcessor
        -is_recording: bool
        -tracked_keys: List[str]
        -edit_mode: bool
        -f9_key_down: bool

        +__init__(collector_manager: CollectorManager, ui_manager: UIManager, logging_manager: LoggingManager, event_processor: EventProcessor) void
        +initialize(tracked_keys: List[str]) void
        +on_collector_event(event: InputData) void
        +toggle_recording() void
        +toggle_edit_mode() void
        +handle_key_edit(key: str) void
        +handle_button_edit(button_id: str, is_tracked: bool) void
        +switch_collector(collector_type: str) void
        +set_mouse_tracking_mode(mode: str) void
        +apply_mouse_settings() void
        +get_tracked_keys() List[str]
    }

    %% ================================================================================
    %% SERVICES SUBMODULE
    %% ================================================================================
    class InteractionService {
        -_instance: Optional[InteractionService]
        -_lock: threading.Lock
        -_components: Dict[str, Any]
        -_last_status: Dict[str, Any]
        -_initialized: bool

        +get_instance()$ InteractionService
        +__init__() void
        +register_component(component_name: str, component: Any) void
        +get_component(component_name: str) Any
        +initialize(components: Dict[str, Any]) bool
        +get_last_status() Dict[str, Any]
        +start_recording() bool
        +stop_recording() bool
        +toggle_recording() bool
        +is_recording() bool
        +enable_json_logging(enabled: bool) bool
        +enable_csv_logging(enabled: bool, filepath: Optional[str]) bool
        +set_csv_path(filepath: str) bool
        +get_logging_state() Dict[str, Any]
        +get_available_collectors() List[Dict[str, str]]
        +switch_collector(collector_type: str) bool
        +get_current_collector() Dict[str, Any]
        +scan_controllers() List[Dict[str, Any]]
        +connect_controller(index: int) bool
    }

    class DataAccessService {
        -_instance: Optional[DataAccessService]
        -_lock: threading.Lock
        -_data_lock: threading.Lock
        -_metadata_lock: threading.Lock
        -_callback_lock: threading.Lock
        -_current_event: Optional[InputData]
        -_key_events: List[InputData]
        -_mouse_movement_events: List[InputData]
        -_mouse_button_events: List[InputData]
        -_controller_events: List[InputData]
        -_active_keys: Set[str]
        -_mouse_position: Tuple[float, float]
        -_mouse_buttons: Dict[str, bool]
        -_metadata: Dict[str, Any]
        -_callbacks: List[Optional[Callable]]
        -_max_history: int

        +get_instance()$ DataAccessService
        +__init__() void
        +update_data(event: InputData) void
        +update_metadata(metadata: Dict[str, Any]) void
        +get_current_event() Optional[InputData]
        +get_key_events(max_count: Optional[int]) List[InputData]
        +get_mouse_movement_events(max_count: Optional[int]) List[InputData]
        +get_mouse_button_events(max_count: Optional[int]) List[InputData]
        +get_controller_events(max_count: Optional[int]) List[InputData]
        +get_active_keys() List[str]
        +is_key_active(key: str) bool
        +get_mouse_position() Tuple[float, float]
        +get_mouse_button_state(button: str) bool
        +get_metadata() Dict[str, Any]
        +register_callback(callback: Callable[[InputData], None]) int
        +unregister_callback(callback_id: int) bool
    }

    %% ================================================================================
    %% ADAPTERS SUBMODULE
    %% ================================================================================
    class QtInteractionAdapter {
        -app_coordinator: Optional[Any]
        -ui_manager: Optional[Any]
        -logging_manager: Optional[Any]
        -collector_manager: Optional[Any]
        -event_processor: Optional[Any]
        -_lock: threading.Lock

        +__init__() void
        +initialize(app_coordinator: Any, ui_manager: Any, logging_manager: Any, collector_manager: Any, event_processor: Any) bool
        +start_recording() bool
        +stop_recording() bool
        +toggle_recording() Tuple[bool, bool]
        +is_recording() bool
        +set_csv_path(filepath: str) bool
        +scan_controllers() List[Dict[str, Any]]
        +connect_controller(index: int) bool
        +switch_collector(collector_type: str) bool
        +set_mouse_tracking_mode(mode: str, direction_only: Optional[bool]) bool
        +set_mouse_settings(delta_smoothing: Optional[float], joystick_sensitivity: Optional[float], angle_grouping: Optional[int]) bool
        +get_mouse_settings() Dict[str, Any]
        +get_tracked_keys() List[str]
        +toggle_edit_mode() Tuple[bool, bool]
        +is_edit_mode() bool
        +add_tracked_key(key: str) bool
        +remove_tracked_key(key: str) bool
        +toggle_button_tracking(button_id: str, track: bool) bool
        +toggle_fullscreen() bool
    }

    %% ================================================================================
    %% CORE EVENT SYSTEM SUBMODULE
    %% ================================================================================
    class EventType {
        <<enumeration>>
        +INPUT: auto()
        +STATE_CHANGE: auto()
        +RECORDING_STARTED: auto()
        +RECORDING_STOPPED: auto()
        +EDIT_MODE_CHANGED: auto()
        +COLLECTOR_CHANGED: auto()
        +TRACKED_KEYS_CHANGED: auto()
    }

    class EventDispatcher {
        -_instance: Optional[EventDispatcher]
        -_lock: threading.Lock
        -_subscribers: Dict[EventType, Set[Callable]]
        -_last_events: Dict[EventType, Any]
        -_subscribers_lock: threading.Lock

        +get_instance()$ EventDispatcher
        +__init__() void
        +subscribe(event_type: EventType, callback: Callable) void
        +unsubscribe(event_type: EventType, callback: Callable) void
        +dispatch(event_type: EventType, data: Any) void
    }

    %% ================================================================================
    %% CLI SUBMODULE
    %% ================================================================================
    class CLIApp {
        <<module>>
        +app: typer.Typer
        +console: Console

        +run_cli() void
        +signal_handler(sig: int, frame: Any) void
        +shutdown_cli() void
        +version() void
        +info() void
    }

    class CLIShell {
        <<module>>
        +console: Console

        +run_interactive_shell() void
        +run_typer_command(args: List[str]) void
        +show_welcome_message() void
        +show_help_message() void
        +show_status() void
        +run_shell() void
    }

    class CLIConfig {
        <<module>>
        +headless_mode: bool
        +headless_app: Optional[HeadlessInputCollector]
        +gui_mode: bool
        +cli_running: threading.Event

        +set_gui_mode(enabled: bool) void
        +get_gui_mode() bool
        +init_headless_mode() HeadlessInputCollector
        +set_cli_running(running: bool) void
        +is_cli_running() bool
        +wait_for_cli_exit(timeout: Optional[float]) bool
    }

    class HeadlessInputCollector {
        +console: Console
        +collector_manager: CollectorManager
        +event_processor: EventProcessor
        +logging_manager: LoggingManager
        +ui_manager: UIManager
        +visualizer_manager: VisualizerManager
        +app_coordinator: AppCoordinator
        +tracked_keys: List[str]

        +__init__() void
        +shutdown() void
    }

    class DataCommands {
        <<CLI module>>
        +active_keys() void
        +is_key_active(key: str) void
        +mouse_position() void
        +mouse_button(button: str) void
        +mouse_direction() void
        +metadata() void
        +current_event() void
        +events(event_type: str, count: int) void
        +controller_connected() void
    }

    class InteractionCommands {
        <<CLI module>>
        +recording(action: str) void
        +logging(log_type: str, action: str, filepath: str) void
        +collectors(action: str, collector_type: str, controller_index: int) void
        +mouse(action: str, mode: str, direction_only: bool, delta_smoothing: float, joystick_sensitivity: float, angle_grouping: int) void
        +keys(action: str, key: str, button: str, track: bool) void
        +fullscreen() void
        +status() void
        +recording_start() void
        +recording_stop() void
        +recording_toggle() void
        +recording_status() void
        +logging_json(action: str) void
        +logging_csv(action: str, filepath: str) void
        +logging_status() void
        +collectors_list() void
        +collectors_current() void
        +collectors_switch(collector: str) void
        +collectors_scan() void
        +connect_controller(index: int) void
        +set_mouse_tracking_mode(mode: str, direction_only: bool) void
        +get_available_tracking_modes(direction_only: bool) void
        +set_mouse_settings(delta_smoothing: int, joystick_sensitivity: int, angle_grouping: int) void
        +get_mouse_settings() void
        +get_tracked_keys() void
        +toggle_edit_mode() void
        +is_edit_mode() void
        +add_tracked_key(key: str) void
        +remove_tracked_key(key: str) void
        +toggle_button_tracking(button_id: str, track: bool) void
        +toggle_fullscreen() void
        +get_application_state() void
    }

    class MonitorCommands {
        <<CLI module>>
        +monitor_events() void
        +monitor_active_keys() void
        +monitor_mouse() void
        +monitor_controller() void
        +monitor_status() void
        -_run_monitor(allowed: List[str], show_keys: bool) void
        -_run_ps4_controller_monitor() void
    }

    class PS4ControllerMonitor {
        -console: Console
        -button_states: Dict[str, bool]
        -stick_positions: Dict[str, tuple]
        -trigger_values: Dict[str, int]
        -recent_events: List[str]
        -max_events: int
        -event_handlers: List[Tuple[EventType, Callable]]
        -display_dirty: bool
        -display_lock: threading.Lock

        +__init__() void
        +start_monitoring() bool
        +stop_monitoring() void
        +process_event_from_core(event_data: Any) void
        +create_display() Layout
        +create_state_table() Table
        +create_logs_panel() str
        +is_display_dirty() bool
        +mark_display_clean() void
    }

    %% ================================================================================
    %% API INTEGRATION CLASSES
    %% ================================================================================
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
        +initialize_api(enable_web_api: bool, host: str, port: int) bool
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
        +initialize_interaction_api(enable_web_api: bool, host: str, port: int) bool
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

    %% ================================================================================
    %% QT FRAMEWORK COMPONENTS
    %% ================================================================================
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

    class QObject {
        <<Qt>>
        +pyqtSignal
        +pyqtSlot
    }

    class QWidget {
        <<Qt>>
        +paintEvent(event: QPaintEvent) void
        +mousePressEvent(event: QMouseEvent) void
        +sizeHint() QSize
    }

    class QSplitter {
        <<Qt>>
        +addWidget(widget: QWidget) void
        +setSizes(sizes: List[int]) void
        +setOrientation(orientation: Qt.Orientation) void
    }

    class QLabel {
        <<Qt>>
        +setText(text: str) void
        +text() str
    }

    class QTextEdit {
        <<Qt>>
        +append(text: str) void
        +clear() void
        +toPlainText() str
    }

    %% ================================================================================
    %% UTILITY FUNCTIONS
    %% ================================================================================
    class is_sdl2_available {
        <<function>>
        +is_sdl2_available() bool
    }

    %% ================================================================================
    %% MAIN RELATIONSHIPS
    %% ================================================================================

    %% Entry Point Relationships
    run --> InputCollectorApp : creates and runs
    run --> CLIApp : starts CLI thread
    run --> InputCollectorApiIntegration : initializes data API
    run --> InteractionApiIntegration : initializes control API

    %% Main Application Inheritance
    QMainWindow <|-- InputCollectorApp : inherits

    %% Core Component Relationships
    InputCollectorApp --> AppCoordinator : coordinates via
    InputCollectorApp --> CollectorManager : manages via
    InputCollectorApp --> UIManager : presents via
    InputCollectorApp --> VisualizerManager : displays via
    InputCollectorApp --> LoggingManager : logs via
    InputCollectorApp --> EventProcessor : processes via

    %% Interface Implementations
    AbstractInputCollector <|-- KeyboardMouseCollector : implements
    AbstractInputCollector <|-- PS4ControllerCollector : implements
    AbstractVisualizer <|-- BaseVisualizer : implements
    BaseVisualizer <|-- KeyboardVisualizer : extends
    BaseVisualizer <|-- MouseVisualizer : extends
    BaseVisualizer <|-- MouseButtonsSelector : extends
    BaseVisualizer <|-- PS4ControllerVisualizer : extends

    %% Qt Inheritance
    QObject <|-- LoggingManager : inherits
    QObject <|-- JSONLogger : inherits
    QObject <|-- CSVLogger : inherits
    QObject <|-- UIManager : inherits
    QObject <|-- VisualizerManager : inherits
    QObject <|-- KeyboardEventFilter : inherits
    QObject <|-- EventProcessor : inherits
    QObject <|-- AppCoordinator : inherits
    QWidget <|-- BaseVisualizer : inherits
    QWidget <|-- Canvas : inherits
    QWidget <|-- MouseButton : inherits

    %% Manager Relationships
    CollectorManager "1" --> "*" AbstractInputCollector : manages
    LoggingManager "1" --> "1" JSONLogger : manages
    LoggingManager "1" --> "1" CSVLogger : manages
    VisualizerManager "1" --> "1" KeyboardVisualizer : manages
    VisualizerManager "1" --> "1" MouseVisualizer : manages
    VisualizerManager "1" --> "1" MouseButtonsSelector : manages
    VisualizerManager "1" --> "1" PS4ControllerVisualizer : manages
    VisualizerManager "1" --> "1" KeyboardEventFilter : inherits

    %% Enhanced Visualizer Relationships
    MouseVisualizer "1" --> "1" Canvas : contains
    MouseButtonsSelector "1" --> "3" MouseButton : contains
    PS4ControllerVisualizer "1" --> "1" QWidget : controller_widget
    PS4ControllerVisualizer "1" --> "1" QTextEdit : log_text
    PS4ControllerVisualizer "1" --> "1" QTimer : state_update_timer
    PS4ControllerVisualizer "1" --> "1" QSplitter : splitter
    PS4ControllerVisualizer "1" --> "1" QWidget : state_panel
    PS4ControllerVisualizer "1" --> "1" QWidget : right_panel
    PS4ControllerVisualizer "1" --> "*" QLabel : value labels

    %% Coordinator Relationships
    AppCoordinator "1" --> "1" CollectorManager : coordinates
    AppCoordinator "1" --> "1" UIManager : coordinates
    AppCoordinator "1" --> "1" LoggingManager : coordinates
    AppCoordinator "1" --> "1" EventProcessor : coordinates

    %% Data Flow
    AbstractInputCollector --> InputData : creates
    AbstractVisualizer --> InputData : processes
    EventProcessor --> InputData : processes
    DataAccessService --> InputData : stores/retrieves
    JSONLogger --> InputData : logs
    CSVLogger --> InputData : logs

    %% API Relationships
    InputCollectorAPI --> InteractionService : delegates to
    InputDataAPI --> DataAccessService : delegates to
    QtInteractionAdapter --> AppCoordinator : coordinates
    QtInteractionAdapter --> UIManager : manages UI
    QtInteractionAdapter --> LoggingManager : manages logging
    QtInteractionAdapter --> CollectorManager : manages collectors
    QtInteractionAdapter --> EventProcessor : processes events

    %% Service Singleton Patterns
    InteractionService --|> InteractionService : singleton instance
    DataAccessService --|> DataAccessService : singleton instance
    EventDispatcher --|> EventDispatcher : singleton instance

    %% CLI Integration
    CLIApp --> DataCommands : includes via add_typer
    CLIApp --> InteractionCommands : includes via add_typer
    CLIApp --> MonitorCommands : includes via add_typer
    CLIConfig --> HeadlessInputCollector : creates/manages
    HeadlessInputCollector --> AppCoordinator : creates/manages
    HeadlessInputCollector --> CollectorManager : creates/manages
    HeadlessInputCollector --> LoggingManager : creates/manages
    HeadlessInputCollector --> EventProcessor : creates/manages
    HeadlessInputCollector --> UIManager : creates minimal version
    HeadlessInputCollector --> VisualizerManager : creates minimal version

    %% Enhanced CLI Monitor Relationships
    MonitorCommands --> PS4ControllerMonitor : creates and manages
    MonitorCommands --> EventDispatcher : subscribes to events
    PS4ControllerMonitor --> EventDispatcher : subscribes to events

    %% Command API Usage
    DataCommands --> InputDataAPI : uses for data access
    InteractionCommands --> InputCollectorAPI : uses for control
    MonitorCommands --> InputCollectorAPI : uses for application state

    %% Web API Integration
    InputCollectorApiIntegration --> InputDataAPI : exposes methods
    InteractionApiIntegration --> InputCollectorAPI : exposes methods
    InputCollectorApiIntegration --> EventDispatcher : subscribes to events
    InteractionApiIntegration --> EventDispatcher : subscribes to events

    %% Protocol Implementation (implicit)
    VisualizerManager ..|> AbstractVisualizerProvider : implements
    VisualizerManager ..|> AbstractVisualizerController : implements

    %% Enhanced Event System Usage
    AppCoordinator --> EventDispatcher : dispatches events
    InputCollectorApiIntegration --> EventDispatcher : subscribes to events
    InteractionApiIntegration --> EventDispatcher : subscribes to events
    MonitorCommands --> EventDispatcher : subscribes to events
    PS4ControllerMonitor --> EventDispatcher : subscribes to events
    PS4ControllerCollector --> EventDispatcher : dispatches events

    %% Thread-Safe Communication
    PS4ControllerVisualizer --> EventDispatcher : thread-safe updates
    PS4ControllerCollector --> EventDispatcher : thread-safe event dispatch

    %% Utility Functions
    PS4ControllerCollector --> is_sdl2_available : uses

    %% ================================================================================
    %% NOTES
    %% ================================================================================
    note for InputCollectorApp "Main GUI application class\nIntegrates all submodules into cohesive app\nManages Qt widgets and event handling\nCoordinates between UI, collectors, and logging"

    note for AppCoordinator "Central mediator implementing the Mediator pattern\nCoordinates all major application components\nHandles high-level business logic and state management\nEnsures thread-safe event processing via Qt signals"

    note for CollectorManager "Manages multiple input collectors\nHandles collector lifecycle and capabilities\nRoutes events to visualizers and data service\nProvides unified interface for input capture"

    note for PS4ControllerCollector "Enhanced PS4 controller with thread-safe event processing:\n• SDL2 event loop architecture in dedicated thread\n• Automatic reconnection capabilities\n• Thread-safe event handling with locks\n• Core event system integration\n• Previous state tracking for change detection\n• Safe callback handling with error isolation"

    note for PS4ControllerVisualizer "Advanced PS4 visualizer with split panel interface:\n• Thread-safe updates via signals/slots\n• Real-time state logging and display\n• Enhanced edit mode with snapshots\n• Dark theme support\n• Split interface: controller visualization + state panel\n• Live value updates with QLabel integration"

    note for PS4ControllerMonitor "Dedicated PS4 controller CLI monitor:\n• Rich console interface with live updates\n• Event-driven architecture using core events\n• Thread-safe display with dirty flags\n• Mimics visualizer functionality in console\n• Cross-platform key listener for exit\n• Real-time state tracking and logging"

    note for MonitorCommands "Monitor command improvements:\n• Smart collector detection for appropriate monitoring\n• Enhanced PS4 controller display via PS4ControllerMonitor\n• Event-driven monitoring using core events\n• Cross-platform key detection (ESC/Q to exit)\n• Integration with InteractionApiIntegration\n• Fallback to general monitoring for other collectors"

    note for EventDispatcher "Singleton event dispatcher with simplified design\nThread-safe subscription management\nAutomatic state synchronization for late subscribers\nError isolation prevents callback failures from affecting others"

    note for InteractionService "Singleton service for external control\nProvides API for application control\nManages component registration and coordination\nThread-safe with status tracking"

    note for DataAccessService "Singleton service for real-time data access\nProvides low-latency access to input streams\nMaintains event history with type categorization\nSupports callback registration for reactive patterns"

    note for QtInteractionAdapter "Thread-safe adapter bridging UI framework and core services\nImplements Adapter pattern for framework isolation\nProvides API for external integration\nEnsures all UI operations execute in main thread"

    note for CLIApp "Main CLI application entry point\nManages Typer app with command modules\nHandles signals and cleanup\nSupports both standalone and GUI-concurrent modes"

    note for HeadlessInputCollector "Minimal application stack for CLI-only mode\nInitializes core components without GUI\nMaintains API compatibility\nProvides clean shutdown procedures"

    %% Enhanced Module Architecture Documentation
    note "Enhanced Module Architecture:\n• Event-driven communication via EventDispatcher\n• Thread-safe operations across all components\n• Enhanced PS4 controller support with real-time monitoring\n• Rich CLI interface with cross-platform compatibility\n• Split panel visualizer interfaces with real-time logging\n• Core event system for decoupled communication\n• Improved error handling and recovery mechanisms\n• SDL2 event loop architecture for PS4 controller\n• Thread-safe UI updates via Qt signals/slots\n• Smart collector-specific monitoring in CLI"
```
