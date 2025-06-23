```mermaid
classDiagram
    %% ================================================================================
    %% EEG PROCESSOR MODULE - NEUROPHYSIOLOGICAL PROCESSING FRAMEWORK
    %% ================================================================================

    %% ================================================================================
    %% CORE APPLICATION CLASS
    %% ================================================================================

    class EEGProcessorApp {
        <<main application>>
        +theme_manager: ThemeManager
        +collector_service: CollectorService
        +processor_service: ProcessorService
        +visualization_service: VisualizationService
        +recording_service: RecordingService
        +mne_service: Optional[MNEService]
        +qt_adapter: QtInteractionAdapter
        +app_event_handler: AppEventHandler
        +is_streaming: bool
        +tabs: QTabWidget
        +connection_panel: ConnectionPanel
        +processing_panel: ProcessingPanel
        +recording_panel: RecordingPanel
        +streaming_panel: StreamingPanel
        +advanced_panel: AdvancedProcessingPanel
        +mne_panel: Optional[MNEPanel]
        +status_timer: QTimer

        +__init__() void
        +setup_ui() void
        +connect_panel_signals() void
        +update_status() void
        +on_stream_started() void
        +on_stream_stopped() void
        +on_board_connected() void
        +on_board_disconnected() void
        +on_recording_started() void
        +on_recording_stopped() void
        +show_status_message(message: str) void
        +show_error_message(title: str, message: str) void
        +closeEvent(event: QCloseEvent) void
        -_setup_api_event_subscriptions() void
        -_handle_api_stream_start_thread_safe(event: Any) void
        -_handle_api_stream_stop_thread_safe(event: Any) void
        -_handle_api_board_connect_thread_safe(event: Any) void
        -_handle_api_board_disconnect_thread_safe(event: Any) void
    }

    class AppEventHandler {
        <<thread-safe event handler>>
        +stream_start_signal: pyqtSignal
        +stream_stop_signal: pyqtSignal
        +board_connect_signal: pyqtSignal
        +board_disconnect_signal: pyqtSignal
    }

    %% ================================================================================
    %% DATA ACCESS API
    %% ================================================================================

    class EEGDataAPI {
        <<static data access api>>
        -_signal_processor_cache: Optional[SignalProcessor]
        -_signal_processor_sampling_rate: Optional[float]

        +get_current_data()$ Tuple[np.ndarray, List[int]]
        +get_raw_data()$ Tuple[np.ndarray, List[int]]
        +get_channel_data(channel_index: int)$ Tuple[np.ndarray, List[int]]
        +get_channel_by_name(channel_name: str)$ Tuple[np.ndarray, List[int]]
        +get_metadata()$ Dict[str, Any]
        +get_sampling_rate()$ float
        +get_channel_names()$ List[str]
        +is_streaming()$ bool
        +register_data_callback(callback: Callable)$ int
        +unregister_data_callback(callback_id: int)$ bool
        +get_eeg_channels()$ List[int]
        +get_board_info()$ Dict[str, Any]
        +get_eeg_data(max_samples: Optional[int])$ Tuple[np.ndarray, List[int]]
        +get_board_preset()$ int
        +get_all_channels_quality()$ Dict[int, float]
        +are_filters_enabled()$ bool
        +get_filter_settings()$ Optional[Dict[str, Any]]
    }

    %% ================================================================================
    %% INTERACTION API
    %% ================================================================================

    class EEGProcessorInteractionAPI {
        <<static interaction api>>
        +get_available_boards()$ List[Dict[str, Any]]
        +get_board_requirements(board_id: int)$ Dict[str, bool]
        +connect_to_board(board_id: int, params: Optional[Dict[str, Any]], preset: int)$ Dict[str, Any]
        +disconnect_from_board()$ Dict[str, Any]
        +start_stream(buffer_size: int)$ Dict[str, Any]
        +stop_stream()$ Dict[str, Any]
        +get_connection_status()$ Dict[str, Any]
        +apply_filters(filter_config: Dict[str, Any])$ Dict[str, Any]
        +start_visualization(viz_type: str)$ Dict[str, Any]
        +stop_visualization(viz_type: str)$ Dict[str, Any]
        +start_recording(filename: str, data_type: str)$ Dict[str, Any]
        +stop_recording()$ Dict[str, Any]
        +get_recording_status()$ Dict[str, Any]
        +insert_marker(marker_value: float)$ Dict[str, Any]
        +add_streamer(streamer_params: str)$ Dict[str, Any]
        +remove_streamer(streamer_params: str)$ Dict[str, Any]
        +send_board_config(config_cmd: str)$ Dict[str, Any]
        +perform_ica(num_components: int, selected_channels: Optional[List[int]])$ Dict[str, Any]
        +view_ica_components(colormap: str)$ Dict[str, Any]
        +select_ica_channels(channel_indices: List[int])$ Dict[str, Any]
        +get_eeg_metrics()$ Dict[str, Any]
        +convert_to_mne(duration: int, use_filters: bool)$ Dict[str, Any]
        +plot_mne_visualization(plot_type: str, freq_min: int, freq_max: int, topomap_band: str, topomap_freq_min: int, topomap_freq_max: int, psd_individual_mode: bool, selected_channels: Optional[List[int]])$ Dict[str, Any]
        +select_mne_channels(channel_indices: List[int])$ Dict[str, Any]
        +compute_wavelet(wavelet_type: int, decomposition_level: int, channel: int, extension_type: int, apply_denoising: bool)$ Dict[str, Any]
        +apply_wavelet_inverse(channel: int, apply: bool)$ Dict[str, Any]
        +apply_downsampling(factor: int, aggregation_method: int, apply: bool)$ Dict[str, Any]
        +apply_advanced_filters(filter_type: int, order: int, window_function: int, selected_channels: Optional[List[int]], apply: bool)$ Dict[str, Any]
        +save_current_data(filename: str, data_type: str)$ Dict[str, Any]
        +get_system_status()$ Dict[str, Any]
    }

    %% ================================================================================
    %% API INTEGRATION CLASSES
    %% ================================================================================

    class EEGProcessorApiIntegration {
        <<api integration service>>
        +explorer: Optional[Any]
        +module_id: str
        +data_service: DataAccessService
        +interaction_integration: EEGProcessorInteractionApiIntegration
        +api_callback_id: Optional[int]
        +include_interaction_methods: bool
        -_total_samples_sent: int
        -_websocket_interval: float
        -_pending_samples: np.ndarray
        -_pending_timestamps: List[int]
        -_last_websocket_time: float

        +get_instance()$ EEGProcessorApiIntegration
        +register_api(host: str, port: int, include_interaction: bool) bool
        -_register_all_method_groups() void
        -_register_method_groups() void
        -_register_status_methods() void
        -_register_device_methods() void
        -_register_data_methods() void
        -_register_channel_methods() void
        -_register_quality_methods() void
        -_register_event_methods() void
        -_get_collector_service() Optional[Any]
        -_get_active_collector() Any
        -_get_board_id_and_preset() Tuple[Optional[int], Optional[int]]
        -_get_sampling_rate_direct() float
        -_get_eeg_channels_direct() List[int]
        -_get_channel_names_direct() List[str]
        -_get_board_info_direct() Dict[str, Any]
        -_get_selected_board_info() Optional[Dict[str, Any]]
        -_port_in_use(host: str, port: int) bool
        -_handle_data_callback(data: Any, timestamps: Any) void
        -_handle_direct_data(data: np.ndarray, timestamps: List[int]) void
        -_handle_multiprocessing_data(data: np.ndarray, timestamps: List[int]) void
        -_create_visualization_payload(data: Any, timestamps: Any) Dict[str, Any]
        -_broadcast_event(payload: Dict[str, Any]) void
        +_handle_is_streaming() Dict[str, Any]
        +_handle_get_metadata() Dict[str, Any]
        +_handle_get_sampling_rate() Dict[str, Any]
        +_handle_get_board_info() Dict[str, Any]
        +_handle_get_preset() Dict[str, Any]
        +_handle_get_current_data(max_samples: Optional[int]) Dict[str, Any]
        +_handle_get_eeg_data(max_samples: Optional[int]) Dict[str, Any]
        +_handle_get_channel_names() Dict[str, Any]
        +_handle_get_eeg_channels() Dict[str, Any]
        +_handle_get_channel_data(channel_index: int, max_samples: Optional[int]) Dict[str, Any]
        +_handle_get_channel_by_name(channel_name: str, max_samples: Optional[int]) Dict[str, Any]
        +_handle_get_signal_quality(channel_index: int) Dict[str, Any]
        +_handle_get_all_channels_quality() Dict[str, Any]
        +_handle_register_data_callback() Dict[str, Any]
    }

    class EEGProcessorInteractionApiIntegration {
        <<interaction api integration>>
        +interaction_service: InteractionService
        +module_id: str
        -_target_module_id: Optional[str]

        +get_instance()$ EEGProcessorInteractionApiIntegration
        +register_api_methods(api_explorer: Any) void
        -_determine_target_module(api_explorer: Any) void
        -_register_method_groups(api_explorer: Any) void
        -_register_connection_methods(api_explorer: Any) void
        -_register_streaming_methods(api_explorer: Any) void
        -_register_processing_methods(api_explorer: Any) void
        -_register_recording_methods(api_explorer: Any) void
        -_register_visualization_methods(api_explorer: Any) void
        -_register_advanced_methods(api_explorer: Any) void
        -_register_status_methods(api_explorer: Any) void
        -_get_board_options() List[Dict[str, Any]]
        -_get_preset_options() List[Dict[str, Any]]
        -_get_board_template(board_id: int) Dict[str, Any]
        -_get_streamer_type_options() List[Dict[str, Any]]
        -_get_streamer_template(streamer_type: str) Dict[str, Any]
        -_get_visualization_type_options() List[Dict[str, Any]]
        -_convert_streamer_template_to_params(streamer_type: str, template_params: Dict[str, Any]) str
        -_parse_channel_string(channel_str: str) List[int]
        -_is_field_optional_for_board(param: str, board_id: int, board_name: str) bool
        +_handle_get_available_boards() Dict[str, Any]
        +_handle_connect_to_board(board_id: int, params: Optional[Dict[str, Any]], preset: int) Dict[str, Any]
        +_handle_disconnect_from_board() Dict[str, Any]
        +_handle_get_board_requirements(board_id: int) Dict[str, Any]
        +_handle_get_board_template(board_id: int) Dict[str, Any]
        +_handle_start_stream(buffer_size: int) Dict[str, Any]
        +_handle_stop_stream() Dict[str, Any]
        +_handle_add_streamer(streamer_type: str, streamer_params: Dict[str, Any]) Dict[str, Any]
        +_handle_remove_streamer(streamer_type: str, streamer_params: Dict[str, Any]) Dict[str, Any]
        +_handle_send_board_config(config_cmd: str) Dict[str, Any]
        +_handle_get_streamer_template(streamer_type: str) Dict[str, Any]
        +_handle_apply_filters(bandpass_enabled: str, bandpass_low: float, bandpass_high: float, notch_enabled: str, notch_frequency: str, detrend_enabled: str, apply_to_visualization: str) Dict[str, Any]
        +_handle_get_eeg_metrics() Dict[str, Any]
        +_handle_start_recording(filename: str, data_type: str) Dict[str, Any]
        +_handle_stop_recording() Dict[str, Any]
        +_handle_insert_marker(marker_value: float) Dict[str, Any]
        +_handle_get_recording_status() Dict[str, Any]
        +_handle_save_current_data(filename: str, data_type: str) Dict[str, Any]
        +_handle_start_visualization(viz_type: str) Dict[str, Any]
        +_handle_stop_visualization(viz_type: str) Dict[str, Any]
        +_handle_perform_ica(num_components: float, selected_channels: str) Dict[str, Any]
        +_handle_view_ica_components(colormap: str) Dict[str, Any]
        +_handle_select_ica_channels(channel_indices: str) Dict[str, Any]
        +_handle_convert_to_mne(duration: float, use_filters: str) Dict[str, Any]
        +_handle_plot_mne_visualization(plot_type: str, freq_min: float, freq_max: float, topomap_band: str, topomap_freq_min: float, topomap_freq_max: float, psd_individual_mode: str, selected_channels: str) Dict[str, Any]
        +_handle_select_mne_channels(channel_indices: str) Dict[str, Any]
        +_handle_compute_wavelet(wavelet_type: str, decomposition_level: float, channel: float, extension_type: str, apply_denoising: str) Dict[str, Any]
        +_handle_apply_wavelet_inverse(channel: float, apply: str) Dict[str, Any]
        +_handle_apply_downsampling(factor: float, aggregation_method: str, apply: str) Dict[str, Any]
        +_handle_apply_advanced_filters(filter_type: str, order: float, window_function: str, selected_channels: str, apply: str) Dict[str, Any]
        +_handle_get_connection_status() Dict[str, Any]
        +_handle_get_system_status() Dict[str, Any]
    }

    %% ================================================================================
    %% ENTRY POINT AND CONFIGURATION
    %% ================================================================================

    class RunApplication {
        <<entry point>>
        +cli_thread: Optional[threading.Thread]

        +parse_config()$ Dict[str, Any]
        +start_cli_in_thread()$ threading.Thread
        +cleanup_cli_thread()$ void
        +main()$ void
    }

    %% ================================================================================
    %% CORE FRAMEWORK PACKAGES
    %% ================================================================================

    class EEGProcessorPackage {
        <<framework package>>
        +EEGProcessorApp: Class
        +EEGDataAPI: Class
        +EEGProcessorInteractionAPI: Class
        +adapters: module
        +collectors: module
        +core: module
        +interfaces: module
        +processors: module
        +services: module
        +ui: module
        +utils: module
        +visualizers: module
    }

    class PythonPackage {
        <<python implementation>>
        +EEGProcessorApp: Class
        +EEGDataAPI: Class
        +EEGProcessorInteractionAPI: Class
        +api_integration: module
        +data_access_api: module
        +interaction_api: module
        +interaction_api_integration: module
    }

    %% ================================================================================
    %% MODULE API FUNCTIONS
    %% ================================================================================

    class ModuleAPIFunctions {
        <<module functions>>
        +get_api_integration()$ EEGProcessorApiIntegration
        +initialize_api(enable: bool, host: str, port: int, include_interaction: bool)$ bool
    }

    %% ================================================================================
    %% EXTERNAL SERVICE DEPENDENCIES
    %% ================================================================================

    class CollectorService {
        <<data collection service>>
        +get_instance()$ CollectorService
        +is_connected() bool
        +is_streaming_active() bool
        +get_board_info() Dict[str, Any]
        +cleanup() void
    }

    class ProcessorService {
        <<signal processing service>>
        +apply_filters(filter_config: Dict[str, Any]) void
        +get_filter_settings() Dict[str, Any]
    }

    class VisualizationService {
        <<visualization management service>>
        +visualization_closed() bool
        +visualization_visible() bool
        +cleanup() void
    }

    class RecordingService {
        <<data recording service>>
        +get_instance()$ RecordingService
        +is_recording() bool
        +get_recording_duration() float
        +cleanup() void
    }

    class DataAccessService {
        <<centralized data access>>
        +get_instance()$ DataAccessService
        +get_current_data() Tuple[np.ndarray, List[int]]
        +get_raw_data() Tuple[np.ndarray, List[int]]
        +get_channel_data(channel_index: int) Tuple[np.ndarray, List[int]]
        +get_metadata() Dict[str, Any]
        +get_sampling_rate() float
        +get_channel_names() List[str]
        +is_streaming() bool
        +register_callback(callback: Callable) int
        +unregister_callback(callback_id: int) bool
        +register_api_callback(callback: Callable) Optional[int]
        +register_api_callback_direct(callback: Callable) Optional[int]
        +update_metadata(metadata: Dict[str, Any]) void
    }

    class InteractionService {
        <<interaction coordination service>>
        +get_instance()$ InteractionService
        +get_available_boards() List[Dict[str, Any]]
        +connect_to_board(board_id: int, params: Dict[str, Any], preset: int) Dict[str, Any]
        +disconnect_from_board() Dict[str, Any]
        +start_stream(buffer_size: int) Dict[str, Any]
        +stop_stream() Dict[str, Any]
        +apply_filters(filter_config: Dict[str, Any]) Dict[str, Any]
        +start_visualization(viz_type: str) Dict[str, Any]
        +stop_visualization(viz_type: str) Dict[str, Any]
        +start_recording(filename: str, data_type: str) Dict[str, Any]
        +stop_recording() Dict[str, Any]
        +insert_marker(marker_value: float) Dict[str, Any]
        +add_streamer(streamer_params: str) Dict[str, Any]
        +remove_streamer(streamer_params: str) Dict[str, Any]
        +send_board_config(config_cmd: str) Dict[str, Any]
        +perform_ica(num_components: int, selected_channels: List[int]) Dict[str, Any]
        +view_ica_components(colormap: str) Dict[str, Any]
        +select_ica_channels(channel_indices: List[int]) Dict[str, Any]
        +get_eeg_metrics() Dict[str, Any]
        +convert_to_mne(duration: int, use_filters: bool) Dict[str, Any]
        +plot_mne_visualization(plot_type: str, freq_min: int, freq_max: int, topomap_band: str, topomap_freq_min: int, topomap_freq_max: int, psd_individual_mode: bool, selected_channels: List[int]) Dict[str, Any]
        +select_mne_channels(channel_indices: List[int]) Dict[str, Any]
        +compute_wavelet(wavelet_type: int, decomposition_level: int, channel: int, extension_type: int, apply_denoising: bool) Dict[str, Any]
        +apply_wavelet_inverse(channel: int, apply: bool) Dict[str, Any]
        +apply_downsampling(factor: int, aggregation_method: int, apply: bool) Dict[str, Any]
        +apply_advanced_filters(filter_type: int, order: int, window_function: int, selected_channels: List[int], apply: bool) Dict[str, Any]
        +save_current_data(filename: str, data_type: str) Dict[str, Any]
        +get_system_status() Dict[str, Any]
    }

    class MNEService {
        <<mne processing service>>
        +get_instance()$ MNEService
        +cleanup() void
    }

    %% ================================================================================
    %% UI PANEL DEPENDENCIES
    %% ================================================================================

    class ConnectionPanel {
        <<connection management panel>>
        +board_connected: pyqtSignal
        +board_disconnected: pyqtSignal
        +stream_started: pyqtSignal
        +stream_stopped: pyqtSignal
        +enable_streaming(enabled: bool) void
        +update_visualization_button(enabled: bool) void
    }

    class ProcessingPanel {
        <<signal processing panel>>
        +enable_processing(enabled: bool) void
    }

    class RecordingPanel {
        <<data recording panel>>
        +recording_started: pyqtSignal
        +recording_stopped: pyqtSignal
        +enable_recording(enabled: bool) void
        +update_recording_status() void
    }

    class StreamingPanel {
        <<data streaming panel>>
        +enable_streaming(enabled: bool) void
    }

    class AdvancedProcessingPanel {
        <<advanced processing panel>>
        +enable_processing(enabled: bool) void
    }

    class MNEPanel {
        <<mne integration panel>>
        +enable_processing(enabled: bool) void
    }

    %% ================================================================================
    %% EXTERNAL FRAMEWORK DEPENDENCIES
    %% ================================================================================

    class QtInteractionAdapter {
        <<qt interaction adapter>>
        +__init__(main_window: QMainWindow) void
    }

    class ThemeManager {
        <<theme management>>
        +apply_dark_theme(widget: QWidget) void
    }

    class ApiExplorer {
        <<external api framework>>
        +get_instance()$ ApiExplorer
        +register_module(module_id: str, name: str, description: str, show_data_table: bool) void
        +register_method(module_id: str, group_id: str, method_id: str, config: Dict[str, Any], handler: Callable) void
        +add_method_group(module_id: str, group_id: str, name: str) void
        +start_server(host: str, port: int, block: bool) void
        +broadcast_event(module_id: str, payload: Dict[str, Any]) void
        +server_port: Optional[int]
    }

    class EventDispatcher {
        <<event system>>
        +get_instance()$ EventDispatcher
        +subscribe(event_type: EventType, callback: Callable) void
    }

    class EventType {
        <<event types enum>>
        +STREAM_START$: EventType
        +STREAM_STOP$: EventType
        +BOARD_CONNECT$: EventType
        +BOARD_DISCONNECT$: EventType
    }

    class BoardShim {
        <<brainflow framework>>
        +enable_dev_board_logger()$ void
    }

    %% ================================================================================
    %% QT5 FRAMEWORK COMPONENTS
    %% ================================================================================

    class QMainWindow {
        <<qt5 framework>>
        +setWindowTitle(title: str) void
        +setGeometry(x: int, y: int, width: int, height: int) void
        +setCentralWidget(widget: QWidget) void
        +statusBar() QStatusBar
        +closeEvent(event: QCloseEvent) void
    }

    class QObject {
        <<qt5 framework>>
        +parent: Optional[QObject]
    }

    class pyqtSignal {
        <<qt5 framework>>
        +emit(*args: Any) void
        +connect(slot: Callable) void
        +disconnect(slot: Optional[Callable]) void
    }

    class QTabWidget {
        <<qt5 framework>>
        +addTab(widget: QWidget, label: str) int
        +setSizePolicy(policy: QSizePolicy) void
    }

    class QTimer {
        <<qt5 framework>>
        +timeout: pyqtSignal
        +start(msec: int) void
        +stop() void
    }

    class QWidget {
        <<qt5 framework>>
        +setEnabled(enabled: bool) void
        +show() void
        +hide() void
    }

    class QVBoxLayout {
        <<qt5 framework>>
        +addWidget(widget: QWidget) void
        +addLayout(layout: QLayout) void
    }

    class QHBoxLayout {
        <<qt5 framework>>
        +addWidget(widget: QWidget) void
        +addStretch() void
    }

    class QPushButton {
        <<qt5 framework>>
        +clicked: pyqtSignal
        +setStyleSheet(style: str) void
    }

    class QLabel {
        <<qt5 framework>>
        +setText(text: str) void
        +setStyleSheet(style: str) void
    }

    class QStatusBar {
        <<qt5 framework>>
        +showMessage(message: str) void
    }

    class QMessageBox {
        <<qt5 framework>>
        +critical(parent: QWidget, title: str, text: str)$ int
    }

    class QCloseEvent {
        <<qt5 framework>>
    }

    class QApplication {
        <<qt5 framework>>
        +setStyle(style: str) void
        +exec_() int
        +topLevelWidgets()$ List[QWidget]
    }

    %% ================================================================================
    %% STANDARD LIBRARY COMPONENTS
    %% ================================================================================

    class argparse {
        <<stdlib>>
        +ArgumentParser: Class
        +add_argument() void
        +parse_args() Namespace
    }

    class logging {
        <<stdlib>>
        +basicConfig() void
        +info(message: str) void
        +debug(message: str) void
        +warning(message: str) void
        +error(message: str) void
    }

    class threading {
        <<stdlib>>
        +Thread: Class
        +start() void
        +is_alive() bool
    }

    class asyncio {
        <<stdlib>>
        +get_event_loop() AbstractEventLoop
        +new_event_loop() AbstractEventLoop
        +set_event_loop(loop: AbstractEventLoop) void
        +run_coroutine_threadsafe(coro: Coroutine, loop: AbstractEventLoop) Future
    }

    class socket {
        <<stdlib>>
        +socket() socket
        +AF_INET$: int
        +SOCK_STREAM$: int
    }

    class time {
        <<stdlib>>
        +time() float
    }

    class json {
        <<stdlib>>
        +loads(s: str) Any
        +JSONDecodeError: Exception
    }

    class numpy {
        <<external>>
        +ndarray: Class
        +array() ndarray
        +concatenate() ndarray
    }

    class typing {
        <<stdlib>>
        +Dict
        +List
        +Any
        +Optional
        +Tuple
        +Callable
    }

    %% ================================================================================
    %% RELATIONSHIPS
    %% ================================================================================

    %% Package Composition
    EEGProcessorPackage "1" *-- "1" PythonPackage : contains
    PythonPackage "1" *-- "1" EEGProcessorApp : contains
    PythonPackage "1" *-- "1" EEGDataAPI : contains
    PythonPackage "1" *-- "1" EEGProcessorInteractionAPI : contains
    PythonPackage "1" *-- "1" EEGProcessorApiIntegration : contains
    PythonPackage "1" *-- "1" EEGProcessorInteractionApiIntegration : contains
    PythonPackage "1" *-- "1" ModuleAPIFunctions : contains

    %% Inheritance
    EEGProcessorApp --|> QMainWindow : extends
    AppEventHandler --|> QObject : extends

    %% Core Application Relationships
    EEGProcessorApp "1" *-- "1" ThemeManager : theme_manager
    EEGProcessorApp "1" *-- "1" CollectorService : collector_service
    EEGProcessorApp "1" *-- "1" ProcessorService : processor_service
    EEGProcessorApp "1" *-- "1" VisualizationService : visualization_service
    EEGProcessorApp "1" *-- "1" RecordingService : recording_service
    EEGProcessorApp "1" *-- "0..1" MNEService : mne_service
    EEGProcessorApp "1" *-- "1" QtInteractionAdapter : qt_adapter
    EEGProcessorApp "1" *-- "1" AppEventHandler : app_event_handler
    EEGProcessorApp "1" *-- "1" QTabWidget : tabs
    EEGProcessorApp "1" *-- "1" ConnectionPanel : connection_panel
    EEGProcessorApp "1" *-- "1" ProcessingPanel : processing_panel
    EEGProcessorApp "1" *-- "1" RecordingPanel : recording_panel
    EEGProcessorApp "1" *-- "1" StreamingPanel : streaming_panel
    EEGProcessorApp "1" *-- "1" AdvancedProcessingPanel : advanced_panel
    EEGProcessorApp "1" *-- "0..1" MNEPanel : mne_panel
    EEGProcessorApp "1" *-- "1" QTimer : status_timer

    %% API Integration Relationships
    EEGProcessorApiIntegration "1" o-- "1" DataAccessService : data_service
    EEGProcessorApiIntegration "1" *-- "1" EEGProcessorInteractionApiIntegration : interaction_integration
    EEGProcessorInteractionApiIntegration "1" o-- "1" InteractionService : interaction_service

    %% Static API Dependencies
    EEGDataAPI ..> DataAccessService : delegates to
    EEGProcessorInteractionAPI ..> InteractionService : delegates to

    %% Service Dependencies
    EEGProcessorApp ..> CollectorService : uses
    EEGProcessorApp ..> ProcessorService : uses
    EEGProcessorApp ..> VisualizationService : uses
    EEGProcessorApp ..> RecordingService : uses
    EEGProcessorApp ..> MNEService : uses

    EEGProcessorApiIntegration ..> CollectorService : uses
    EEGProcessorApiIntegration ..> DataAccessService : uses
    EEGProcessorInteractionApiIntegration ..> InteractionService : uses

    %% Signal Relationships
    AppEventHandler "1" *-- "4" pyqtSignal : event signals
    ConnectionPanel "1" *-- "4" pyqtSignal : connection signals
    RecordingPanel "1" *-- "2" pyqtSignal : recording signals

    %% Signal Connections
    ConnectionPanel ..> EEGProcessorApp : stream_started, stream_stopped, board_connected, board_disconnected
    RecordingPanel ..> EEGProcessorApp : recording_started, recording_stopped

    %% Event System Dependencies
    EEGProcessorApp ..> EventDispatcher : subscribes to
    EEGProcessorApp ..> EventType : uses

    %% External Framework Dependencies
    EEGProcessorApp ..> ThemeManager : creates
    EEGProcessorApp ..> QtInteractionAdapter : creates
    EEGProcessorApp ..> BoardShim : uses

    EEGProcessorApiIntegration ..> ApiExplorer : uses

    %% Module API Functions
    ModuleAPIFunctions ..> EEGProcessorApiIntegration : creates and manages

    %% Entry Point Dependencies
    RunApplication ..> EEGProcessorApp : creates and runs
    RunApplication ..> argparse : uses
    RunApplication ..> logging : uses
    RunApplication ..> threading : uses

    %% Qt Framework Dependencies
    EEGProcessorApp ..> QTabWidget : creates
    EEGProcessorApp ..> QVBoxLayout : creates
    EEGProcessorApp ..> QHBoxLayout : creates
    EEGProcessorApp ..> QPushButton : creates
    EEGProcessorApp ..> QLabel : creates
    EEGProcessorApp ..> QTimer : creates
    EEGProcessorApp ..> QMessageBox : uses

    %% Standard Library Dependencies
    EEGProcessorApp ..> logging : uses
    EEGDataAPI ..> logging : uses
    EEGProcessorInteractionAPI ..> logging : uses
    EEGProcessorApiIntegration ..> asyncio : uses
    EEGProcessorApiIntegration ..> socket : uses
    EEGProcessorApiIntegration ..> time : uses
    EEGProcessorApiIntegration ..> numpy : uses
    EEGProcessorInteractionApiIntegration ..> json : uses

    RunApplication ..> argparse : uses
    RunApplication ..> logging : uses
    RunApplication ..> threading : uses

    %% Type Dependencies
    EEGProcessorApp ..> typing : uses
    EEGDataAPI ..> typing : uses
    EEGProcessorInteractionAPI ..> typing : uses
    EEGProcessorApiIntegration ..> typing : uses
    EEGProcessorInteractionApiIntegration ..> typing : uses

    %% ================================================================================
    %% LOGICAL GROUPINGS
    %% ================================================================================

    %% Core Application Components
    EEGProcessorApp -.- AppEventHandler : "core application"

    %% API Layer
    EEGDataAPI -.- EEGProcessorInteractionAPI : "api interfaces"
    EEGProcessorApiIntegration -.- EEGProcessorInteractionApiIntegration : "api integration"

    %% Service Layer
    CollectorService -.- ProcessorService : "core services"
    ProcessorService -.- VisualizationService : "core services"
    VisualizationService -.- RecordingService : "core services"
    RecordingService -.- DataAccessService : "core services"
    DataAccessService -.- InteractionService : "core services"
    InteractionService -.- MNEService : "core services"

    %% UI Panel Layer
    ConnectionPanel -.- ProcessingPanel : "ui panels"
    ProcessingPanel -.- RecordingPanel : "ui panels"
    RecordingPanel -.- StreamingPanel : "ui panels"
    StreamingPanel -.- AdvancedProcessingPanel : "ui panels"
    AdvancedProcessingPanel -.- MNEPanel : "ui panels"

    %% External Framework Components
    QtInteractionAdapter -.- ThemeManager : "external adapters"
    ApiExplorer -.- EventDispatcher : "external frameworks"

    %% Qt Framework Components
    QMainWindow -.- QObject : "qt framework"
    QObject -.- pyqtSignal : "qt framework"
    pyqtSignal -.- QTabWidget : "qt framework"
    QTabWidget -.- QTimer : "qt framework"
    QTimer -.- QWidget : "qt framework"
    QWidget -.- QVBoxLayout : "qt framework"
    QVBoxLayout -.- QHBoxLayout : "qt framework"
    QHBoxLayout -.- QPushButton : "qt framework"
    QPushButton -.- QLabel : "qt framework"
    QLabel -.- QStatusBar : "qt framework"
    QStatusBar -.- QMessageBox : "qt framework"
    QMessageBox -.- QCloseEvent : "qt framework"
    QCloseEvent -.- QApplication : "qt framework"

    %% Standard Library Components
    argparse -.- logging : "standard libraries"
    logging -.- threading : "standard libraries"
    threading -.- asyncio : "standard libraries"
    asyncio -.- socket : "standard libraries"
    socket -.- time : "standard libraries"
    time -.- json : "standard libraries"
    json -.- typing : "standard libraries"

    %% External Libraries
    numpy -.- BoardShim : "external libraries"

    %% ================================================================================
    %% NOTES
    %% ================================================================================

    note for EEGProcessorApp "EEG Processing Application:\n• Advanced Qt-based neurophysiological analysis platform with tabbed interface supporting connection, processing, recording, streaming, and advanced analysis operations\n• Service-oriented architecture coordinating CollectorService, ProcessorService, VisualizationService, RecordingService, and optional MNEService for modular functionality\n• Real-time event-driven coordination with thread-safe API-GUI synchronization through AppEventHandler and event system integration\n• Dynamic panel management with conditional MNE integration based on package availability and automatic service lifecycle management\n• Professional dark theme with consistent styling, accessibility features, and user-friendly error handling\n• Cleanup procedures for advanced panel ICA processes, service resources, and Qt adapter management\n• Status monitoring with periodic updates for recording duration, visualization state, and cross-component synchronization\n• Signal-slot architecture enabling loose coupling between panels and coordinated application state management\n• Memory optimization with proper resource lifecycle control and automatic leak prevention mechanisms"

    note for EEGDataAPI "High-Performance Data Access Interface:\n• Static API providing centralized access to real-time EEG data streams with minimal overhead and thread-safe operations\n• Intelligent filter management distinguishing between filtered and raw data access with automatic service integration\n• Advanced channel management supporting index-based, name-based, and type-specific data retrieval with validation\n• Metadata access including board information, sampling rates, channel mappings, and real-time status\n• Callback registration system enabling real-time data subscriptions with proper lifecycle management and error handling\n• Signal quality assessment using cached SignalProcessor instances with adaptive sampling rate optimization\n• Multi-channel quality analysis with efficient computation and fallback mechanisms for robust operation\n• EEG-specific data extraction with channel filtering, sample limiting, and optimized memory usage\n• Filter status integration providing transparency about data processing state and parameter settings\n• Board preset and configuration access with device information and connection status monitoring"

    note for EEGProcessorInteractionAPI "System Control Interface:\n• Static API enabling complete external control of EEG processor functionality through standardized method signatures\n• Advanced board management with dynamic requirements detection, parameter validation, and configuration assistance\n• Intelligent streaming control with buffer optimization, preset validation, and error recovery mechanisms\n• Filter management supporting bandpass, notch, and detrend filtering with real-time application\n• Multi-modal visualization control supporting EEG and brain map displays with performance optimization\n• Recording management with multi-format support, marker insertion, and real-time status monitoring\n• Streamer configuration with type-specific parameter handling and lifecycle management\n• Advanced processing operations including ICA computation, component visualization, and channel selection\n• MNE integration with conversion support, advanced visualization, and parameter coordination\n• Wavelet analysis with multi-family support, decomposition control, and inverse transform capabilities\n• Downsampling and advanced filtering with multiple algorithms and channel-specific application\n• System status monitoring with state reporting and error handling\n• Data export capabilities with format selection and real-time processing integration"

    note for EEGProcessorApiIntegration "Advanced API Integration and WebSocket Streaming:\n• API explorer integration with dynamic method registration and real-time documentation\n• Dual-mode data streaming: Direct mode (low latency ~15ms) and Multiprocessing mode (high throughput)\n• Intelligent board information access with direct collector integration and UI state synchronization\n• Advanced WebSocket payload creation with structured visualization data and metadata enrichment\n• Real-time data callback handling with accumulation strategies and continuity preservation\n• Dynamic method registration supporting data access, device control, channel management, and quality assessment\n• Port conflict resolution with automatic port selection and availability checking\n• Performance optimization with sample limiting, timestamp management, and memory-efficient operations\n• Filter-aware data handling with transparent processing state communication\n• Multi-channel type support including EEG, EMG, ECG, accelerometer, gyroscope, and specialized sensors\n• Event broadcasting with structured payloads and processing mode indicators\n• Error handling with graceful degradation and logging for debugging support"

    note for EEGProcessorInteractionApiIntegration "External API Framework Integration:\n• Interaction API registration with dynamic method grouping and parameter templates\n• Advanced UI component generation with range controls, select options, and JSON template support\n• Intelligent board template system with dynamic parameter population based on device requirements\n• Streamer configuration with type-specific templates and parameter validation\n• Channel selection with string parsing supporting comma-separated values and JSON array formats\n• Filter configuration with visual range controls and real-time parameter validation\n• MNE integration with plot type selection, frequency range controls, and topomap band configuration\n• Wavelet analysis with Wavelet type selection and parameter optimization\n• Advanced processing with filter type selection, order controls, and channel-specific application\n• Error handling with detailed validation and user-friendly error messages\n• Parameter conversion with type safety and range validation for robust operation\n• Method delegation with proper error isolation and service coordination"

    note "EEG Processor Framework Architecture:\n• Modular Design: Service-oriented architecture with clear separation of concerns and standardized interfaces\n• Real-time Processing: High-frequency data updates with optimized rendering and adaptive resource management\n• API Integration: External control through REST API with WebSocket streaming support\n• Advanced Analysis: ICA, wavelet transforms, MNE integration, and specialized neurophysiological processing\n• Multi-hardware Support: 20+ manufacturer compatibility with automatic device detection and configuration\n• Professional UI: Qt-based interface with dark theme, accessibility features, and intuitive workflow design\n• Performance Optimization: Memory-efficient operations with intelligent caching and adaptive processing strategies\n• Error Handling: Robust exception management with user-friendly feedback and automatic recovery mechanisms\n• Educational Features: Help system with theoretical background and practical guidance\n• Cross-platform Compatibility: Consistent behavior across Windows, Linux, and macOS environments"

    note "Data Flow and Processing Pipeline:\n• Hardware Interface: BrainFlow integration supporting multiple board types with automatic configuration\n• Data Collection: Real-time streaming through CollectorService with optimized buffer management\n• Signal Processing: Advanced filtering and analysis through ProcessorService with immediate application\n• Data Access: Centralized access via DataAccessService with filter integration and callback support\n• Visualization: Multi-modal displays through VisualizationService with performance optimization\n• Recording: Multi-format data recording through RecordingService with marker support\n• Advanced Analysis: Specialized processing through dedicated services with result management\n• API Integration: External access through standardized interfaces with real-time streaming\n• User Interface: Qt-based panels providing intuitive control and immediate feedback\n• Event System: Application-wide coordination through event dispatcher with thread-safe communication"

    note "Advanced Features and Capabilities:\n• Independent Component Analysis: Real-time computation with sliding window analysis and professional visualization\n• Wavelet Processing: 40+ wavelet families with decomposition control and denoising capabilities\n• MNE Integration: Neurophysiological analysis with advanced visualization and real-time processing sessions\n• Filter Coordination: Cross-component synchronization with stability monitoring and parameter validation\n• Quality Assessment: Real-time signal quality monitoring with multi-channel analysis and color-coded feedback\n• Performance Monitoring: CPU usage tracking with adaptive optimization and resource management\n• Memory Efficiency: Intelligent buffer management with automatic cleanup and leak prevention\n• Thread Safety: Proper UI marshalling with concurrent processing support and resource protection\n• Error Recovery: Exception handling with automatic recovery and user guidance\n• Documentation: Context-sensitive help with theoretical background and practical implementation guidance"

    note "Implementation:\n• Design Patterns: Singleton services, factory methods, observer patterns, and dependency injection\n• Memory Management: Automatic resource lifecycle control with leak detection and prevention\n• Threading: Proper thread synchronization with UI marshalling and background processing isolation\n• Performance: Optimized algorithms with caching strategies and adaptive resource allocation\n• Scalability: Support for large datasets and high-frequency processing with adaptive strategies\n• Extensibility: Plugin architecture enabling easy addition of new analysis methods and visualization types\n• Testing: Dependency injection and modular design supporting unit testing\n• Logging: Debugging support with configurable levels and detailed error reporting\n• Configuration: Flexible parameter management with validation and persistence support\n• Cross-platform: Consistent behavior with native integration across different operating systems"

    note "User Experience and Interface Design:\n• Intuitive Workflow: Guided processing workflows with clear visual indicators and progress feedback\n• Real-time Feedback: Immediate status updates with color-coded information and performance metrics\n• Professional Aesthetics: Modern dark theme with consistent styling and accessibility compliance\n• Context-sensitive Help: Integrated guidance system with parameter explanations and best practices\n• Error Communication: User-friendly messages with troubleshooting steps and recovery options\n• Performance Guidance: Optimization suggestions based on system capabilities and processing requirements\n• Accessibility: Keyboard navigation, screen reader compatibility, and high contrast support\n• Customization: User-configurable parameters with preference persistence and workflow adaptation\n• Responsive Design: Adaptive layouts supporting different screen sizes and resolution configurations\n• Cross-platform Consistency: Uniform behavior and appearance across different operating systems"
```
