```mermaid
classDiagram
    %% ================================================================================
    %% UI MODULE - USER INTERFACE ARCHITECTURE
    %% ================================================================================
    
    %% ================================================================================
    %% CORE PANEL BASE CLASS
    %% ================================================================================
    
    class BasePanel {
        <<abstract ui panel>>
        +status_message: pyqtSignal[str]
        +error_message: pyqtSignal[str, str]
        +content_widget: QWidget
        +layout: QVBoxLayout
        
        +__init__(parent: Optional[QWidget]) void
        +show_status(message: str) void
        +show_error(title: str, message: str) void
    }
    
    %% ================================================================================
    %% CORE PANEL CLASSES
    %% ================================================================================
    
    class ConnectionPanel {
        <<board connection management>>
        +board_connected: pyqtSignal
        +board_disconnected: pyqtSignal
        +stream_started: pyqtSignal
        +stream_stopped: pyqtSignal
        
        +collector_service: Any
        +visualization_service: Any
        +api_event_handler: ApiEventHandler
        +board_groups: List[Tuple[str, int]]
        +param_fields: Dict[str, QWidget]
        +board_type_combo: QComboBox
        +filter_edit: QLineEdit
        +preset_combo: QComboBox
        +connect_btn: QPushButton
        +disconnect_btn: QPushButton
        +start_stream_btn: QPushButton
        +stop_stream_btn: QPushButton
        +show_viz_btn: QPushButton
        +board_info_label: QLabel
        
        +__init__(collector_service: Any, visualization_service: Any, parent: Optional[Any]) void
        +setup_visualization_control() void
        +setup_board_selection() void
        +setup_board_info() void
        +on_board_type_changed() void
        +filter_boards() void
        +browse_file() void
        +connect_board() void
        +disconnect_board() void
        +start_stream() void
        +stop_stream() void
        +show_visualization() void
        +update_visualization_button(enabled: bool) void
        +enable_streaming(enabled: bool) void
        -_validate_streaming_board_preset() void
        -_reconnect_with_preset_zero() void
        -_convert_params_to_dict(params: Any) Dict[str, Any]
        -_update_connection_state(connected: bool) bool
        -_update_streaming_state(streaming: bool) bool
        -_update_params_from_dict(params: Dict[str, Any]) bool
        +get_connection_settings() Dict[str, Any]
    }
    
    class ProcessingPanel {
        <<signal processing operations>>
        +collector_service: Any
        +processor_service: Any
        +visualization_service: Any
        +data_access_service: DataAccessService
        +api_event_handler: ApiEventHandler
        +filters_applied: bool
        +processing_enabled: bool
        +bandpass_check: QCheckBox
        +bandpass_low_spin: QDoubleSpinBox
        +bandpass_high_spin: QDoubleSpinBox
        +notch_check: QCheckBox
        +notch_type_combo: QComboBox
        +detrend_check: QCheckBox
        +apply_filters_btn: QPushButton
        +calculate_metrics_btn: QPushButton
        +metrics_label: QLabel
        +brain_map_btn: QPushButton
        +brain_map_timer: QTimer
        
        +__init__(collector_service: Any, processor_service: Any, visualization_service: Any, parent: Optional[Any]) void
        +setup_filter_options() void
        +setup_metrics_section() void
        +setup_brain_map_section() void
        +check_brain_map_status() void
        +apply_filters() void
        +on_filter_option_changed() void
        +calculate_metrics() void
        +show_brain_map() void
        +enable_processing(enabled: bool) void
        -_update_filter_controls_from_api(filter_config: Dict[str, Any], applied_to_visualization: bool) void
        -_disconnect_filter_signals() void
        -_connect_filter_signals() void
        -_update_filter_controls(filter_config: Dict[str, Any]) bool
        +get_filter_settings() Dict[str, Any]
        +update_metrics_display(metrics_text: str) bool
    }
    
    class RecordingPanel {
        <<data recording operations>>
        +recording_started: pyqtSignal
        +recording_stopped: pyqtSignal
        +collector_service: Any
        +recording_service: Any
        +api_event_handler: ApiEventHandler
        +record_file_edit: QLineEdit
        +raw_radio: QRadioButton
        +processed_radio: QRadioButton
        +both_radio: QRadioButton
        +start_record_btn: QPushButton
        +stop_record_btn: QPushButton
        +marker_value_spin: QSpinBox
        +add_marker_btn: QPushButton
        +recording_status_label: QLabel
        +status_timer: QTimer
        
        +__init__(collector_service: Any, recording_service: Any, parent: Optional[Any]) void
        +setup_recording_controls() void
        +setup_marker_controls() void
        +setup_status_display() void
        +update_recording_status() void
        +browse_file() void
        +start_recording() void
        +stop_recording() void
        +add_marker() void
        +enable_recording(enabled: bool) void
        -_update_recording_state(recording: bool) void
    }
    
    class StreamingPanel {
        <<data streaming management>>
        +collector_service: CollectorService
        +recording_service: Optional[Any]
        +active_streamers: List[Dict[str, str]]
        +file_streamer_path: QLineEdit
        +file_data_type_combo: QComboBox
        +network_streamer_path: QLineEdit
        +custom_streamer_path: QLineEdit
        +streamers_list: QListWidget
        +config_cmd_edit: QLineEdit
        +config_response_text: QTextEdit
        +send_config_btn: QPushButton
        
        +__init__(collector_service: CollectorService, parent: Optional[Any]) void
        +setup_streamer_configuration() void
        +setup_board_configuration() void
        +add_streamer(streamer_params: str, streamer_type: str, data_type: str) void
        +delete_selected_streamer() void
        +send_board_config() void
        +enable_streaming(enabled: bool) void
        +stop_all_streamers() void
        +on_board_disconnected() void
        -_add_file_streamer(file_path: str, data_type: str) bool
        -_validate_streaming_board_setup() void
        -_reconnect_with_preset_zero() void
        -_convert_params_to_dict(params: Any) Dict[str, Any]
        -_delete_tracked_streamer(streamer_info: Dict[str, str], selected_row: int) bool
        -_delete_legacy_streamer(streamer_params: str) bool
        +update_streamer_list(streamers_list: List[str]) bool
        +update_config_response(response_text: str) bool
        +get_streamer_params() Dict[str, str]
        +get_active_streamers() List[str]
    }
    
    class MNEPanel {
        <<mne integration panel>>
        +collector_service: Any
        +processor_service: Any
        +visualization_service: Optional[Any]
        +mne_service: MNEService
        +api_event_handler: MNEApiEventHandler
        +conversion_widget: Optional[MNEConversionWidget]
        +visualization_widget: Optional[MNEVisualizationWidget]
        +status_widget: Optional[MNEStatusWidget]
        +controller: Optional[MNEPanelController]
        
        +__init__(collector_service: Any, processor_service: Any, parent: Optional[Any], visualization_service: Optional[Any]) void
        +enable_processing(enabled: bool) void
        +closeEvent(event: QCloseEvent) void
        -_setup_mne_panel() void
        -_setup_mne_not_available() void
        +get_mne_settings() Dict[str, Any]
        +update_mne_plot(plot_data: Dict[str, Any]) bool
    }
    
    class AdvancedProcessingPanel {
        <<advanced processing panel>>
        +collector_service: Any
        +processor_service: Any
        +api_event_handler: ApiEventHandler
        +ica_widget: ICAWidget
        +wavelet_widget: WaveletWidget
        +downsampling_widget: DownsamplingWidget
        +advanced_filter_widget: AdvancedFilterWidget
        +controller: AdvancedPanelController
        
        +__init__(collector_service: Any, processor_service: Any, parent: Optional[Any]) void
        +enable_processing(enabled: bool) void
        +closeEvent(event: QCloseEvent) void
        -_setup_advanced_panel() void
        +get_ica_settings() Dict[str, Any]
        +get_wavelet_settings() Dict[str, Any]
        +get_downsample_settings() Dict[str, Any]
        +get_advanced_filter_settings() Dict[str, Any]
        +update_channel_lists(channel_names: list) bool
    }
    
    %% ================================================================================
    %% SPECIALIZED UI PACKAGES
    %% ================================================================================
    
    class AdvancedUIPackage {
        <<specialized ui package>>
        +AdvancedPanelController: Class
        +dialogs: module
        +widgets: module
    }
    
    class MNEUIPackage {
        <<specialized ui package>>
        +MNEPanelController: Class
        +widgets: module
    }
    
    %% ================================================================================
    %% CORE CONTROLLERS
    %% ================================================================================
    
    class AdvancedPanelController {
        <<advanced processing coordinator>>
        +status_message: pyqtSignal[str]
        +error_message: pyqtSignal[str, str]
        +export_progress: pyqtSignal[int, str]
        +export_finished: pyqtSignal[bool, str]
        +ica_widget: ICAWidget
        +wavelet_widget: WaveletWidget
        +downsampling_widget: DownsamplingWidget
        +advanced_filter_widget: AdvancedFilterWidget
        +processing_service: AdvancedProcessingService
        +export_service: ExportService
        +ica_process_service: ICAProcessService
        +ica_realtime_service: ICARealtimeService
        
        +enable_processing(enabled: bool) void
        +update_channel_lists(channel_names: List[str]) bool
        +cleanup() void
    }
    
    class MNEPanelController {
        <<mne coordination controller>>
        +status_message: pyqtSignal[str]
        +error_message: pyqtSignal[str, str]
        +conversion_widget: MNEConversionWidget
        +visualization_widget: MNEVisualizationWidget
        +status_widget: MNEStatusWidget
        +mne_service: MNEService
        +data_service: DataAccessService
        +current_conversion_task: Optional[str]
        +current_visualization_task: Optional[str]
        +current_realtime_session: Optional[str]
        
        +enable_processing(enabled: bool) void
        +cleanup() void
    }
    
    %% ================================================================================
    %% API EVENT HANDLERS
    %% ================================================================================
    
    class ApiEventHandler {
        <<thread-safe api handler>>
        +ui_update_signal: pyqtSignal[dict]
        +stream_start_signal: pyqtSignal
        +stream_stop_signal: pyqtSignal
        +board_connect_signal: pyqtSignal
        +board_disconnect_signal: pyqtSignal
        +visualization_start_signal: pyqtSignal[str]
        +visualization_stop_signal: pyqtSignal[str]
        +filter_apply_signal: pyqtSignal[dict, bool]
        +recording_start_signal: pyqtSignal[dict]
        +recording_stop_signal: pyqtSignal
        +recording_status_changed_signal: pyqtSignal[dict]
        
        +__init__() void
    }
    
    class MNEApiEventHandler {
        <<mne api event handler>>
        +convert_signal: pyqtSignal[int, bool]
        +plot_signal: pyqtSignal[dict]
        +select_channels_signal: pyqtSignal[list]
        
        +__init__() void
    }
    
    %% ================================================================================
    %% SPECIALIZED WIDGETS
    %% ================================================================================
    
    class MNEConversionWidget {
        <<mne conversion interface>>
        +conversion_requested: pyqtSignal[dict]
        +conversion_cancelled: pyqtSignal
        +channel_selection_requested: pyqtSignal[str]
        +realtime_requested: pyqtSignal[dict]
        +realtime_stopped: pyqtSignal
        +realtime_param_changed: pyqtSignal[str, object]
        
        +get_conversion_parameters() Dict[str, Any]
        +get_realtime_parameters() Dict[str, Any]
        +set_conversion_state(converting: bool) void
        +set_realtime_state(active: bool) void
    }
    
    class MNEVisualizationWidget {
        <<mne visualization interface>>
        +visualization_requested: pyqtSignal[dict]
        +visualization_cancelled: pyqtSignal
        +channel_selection_requested: pyqtSignal[str]
        +plot_type_changed: pyqtSignal[str]
        +freq_range_changed: pyqtSignal[int, int]
        +psd_mode_changed: pyqtSignal[bool]
        +topomap_band_changed: pyqtSignal[int, int]
        
        +get_visualization_parameters() Dict[str, Any]
        +set_visualization_state(visualizing: bool) void
        +display_plot(plot_data: str) void
    }
    
    class MNEStatusWidget {
        <<mne status monitoring>>
        +add_status_message(message: str) void
        +clear_status() void
        +update_realtime_status(status_info: Dict[str, Any]) void
    }
    
    class ICAWidget {
        <<ica analysis widget>>
        +compute_requested: pyqtSignal[dict]
        +view_components_requested: pyqtSignal[dict]
        +export_overview_requested: pyqtSignal
        +export_all_requested: pyqtSignal
        +realtime_start_requested: pyqtSignal[dict]
        +realtime_stop_requested: pyqtSignal
        +realtime_interval_changed: pyqtSignal[float]
        
        +update_channels(channel_names: List[str]) void
        +set_ica_results(ica_results: Dict[str, Any]) void
        +set_realtime_active(active: bool, message: str) void
        +get_colormap() str
    }
    
    class WaveletWidget {
        <<wavelet analysis widget>>
        +compute_requested: pyqtSignal[dict]
        +apply_inverse_requested: pyqtSignal[bool]
        +settings_changed: pyqtSignal[dict]
        
        +update_channels(channel_names: List[str]) void
        +set_wavelet_results(coefficients: Any, metadata: Dict[str, Any]) void
        +has_wavelet_results() bool
    }
    
    class DownsamplingWidget {
        <<downsampling widget>>
        +apply_requested: pyqtSignal[dict]
        +settings_changed: pyqtSignal[dict]
        
        +get_downsample_settings() Dict[str, Any]
    }
    
    class AdvancedFilterWidget {
        <<advanced filter widget>>
        +apply_requested: pyqtSignal[dict]
        +settings_changed: pyqtSignal[dict]
        
        +update_channels(channel_names: List[str]) void
        +set_processing_panel_reference(processing_panel: Any) void
        +get_advanced_filter_settings() Dict[str, Any]
    }
    
    %% ================================================================================
    %% UI MODULE PACKAGE
    %% ================================================================================
    
    class UIPackage {
        <<module package>>
        +BasePanel: Class
        +ConnectionPanel: Class
        +ProcessingPanel: Class
        +RecordingPanel: Class
        +StreamingPanel: Class
        +MNEPanel: Class
        +AdvancedProcessingPanel: Class
        +advanced: module
        +mne: module
    }
    
    %% ================================================================================
    %% SERVICE DEPENDENCIES
    %% ================================================================================
    
    class CollectorService {
        <<data collection service>>
        +is_connected() bool
        +is_streaming_active() bool
        +connect_to_board(board_id: int, params: Dict[str, Any], preset: int) bool
        +disconnect_from_board() bool
        +start_stream() bool
        +stop_stream() bool
        +get_sampling_rate() float
        +get_board_info() Dict[str, Any]
        +add_streamer(streamer_params: str) bool
        +remove_streamer(streamer_params: str) bool
        +config_device(config_cmd: str) str
    }
    
    class DataAccessService {
        <<data access service>>
        +get_instance()$ DataAccessService
        +get_current_data() Tuple[Any, Any]
        +get_raw_data() Tuple[Any, Any]
        +get_metadata() Dict[str, Any]
        +enable_filters(enabled: bool, filter_settings: Optional[Dict[str, Any]]) void
        +update_filter_settings(filter_settings: Dict[str, Any]) void
        +set_filter_processor(processor_service: Any) void
    }
    
    class MNEService {
        <<mne processing service>>
        +get_instance()$ MNEService
        +is_available() bool
        +start_service() void
        +convert_to_mne_async(duration_seconds: int, convert_to_v: bool, selected_channels: Optional[List[int]], callback: Callable, data: Any, metadata: Dict[str, Any]) str
        +create_visualization_async(task_id: str, plot_type: str, freq_min: int, freq_max: int, bg_color: str, show_individual_channels: bool, selected_channels_for_display: List[int], topomap_freq_range: Tuple[int, int], callback: Callable) str
    }
    
    class AdvancedProcessingService {
        <<advanced analysis service>>
        +compute_ica(params: Dict[str, Any]) Dict[str, Any]
        +compute_wavelet(params: Dict[str, Any]) Dict[str, Any]
        +apply_wavelet_inverse(apply: bool) Dict[str, Any]
        +apply_downsampling(params: Dict[str, Any]) Dict[str, Any]
        +apply_advanced_filters(params: Dict[str, Any]) Dict[str, Any]
    }
    
    %% ================================================================================
    %% QT5 FRAMEWORK COMPONENTS
    %% ================================================================================
    
    class QWidget {
        <<qt5 framework>>
        +parent: Optional[QWidget]
        +setEnabled(enabled: bool) void
        +show() void
        +hide() void
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
    
    class QVBoxLayout {
        <<qt5 framework>>
        +addWidget(widget: QWidget) void
        +addLayout(layout: QLayout) void
    }
    
    class QScrollArea {
        <<qt5 framework>>
        +setWidgetResizable(resizable: bool) void
        +setWidget(widget: QWidget) void
    }
    
    class QComboBox {
        <<qt5 framework>>
        +currentText() str
        +currentData() Any
        +addItem(text: str, userData: Any) void
    }
    
    class QPushButton {
        <<qt5 framework>>
        +clicked: pyqtSignal
        +setText(text: str) void
        +setEnabled(enabled: bool) void
    }
    
    class QLabel {
        <<qt5 framework>>
        +setText(text: str) void
        +text() str
    }
    
    class QCheckBox {
        <<qt5 framework>>
        +isChecked() bool
        +setChecked(checked: bool) void
        +toggled: pyqtSignal[bool]
    }
    
    class QSpinBox {
        <<qt5 framework>>
        +value() int
        +setValue(value: int) void
        +valueChanged: pyqtSignal[int]
    }
    
    class QDoubleSpinBox {
        <<qt5 framework>>
        +value() float
        +setValue(value: float) void
        +valueChanged: pyqtSignal[float]
    }
    
    class QLineEdit {
        <<qt5 framework>>
        +text() str
        +setText(text: str) void
        +textChanged: pyqtSignal[str]
    }
    
    class QTextEdit {
        <<qt5 framework>>
        +append(text: str) void
        +clear() void
        +setText(text: str) void
    }
    
    class QListWidget {
        <<qt5 framework>>
        +addItem(text: str) void
        +takeItem(row: int) QListWidgetItem
        +clear() void
        +currentItem() QListWidgetItem
        +row(item: QListWidgetItem) int
    }
    
    class QRadioButton {
        <<qt5 framework>>
        +isChecked() bool
        +setChecked(checked: bool) void
    }
    
    class QTimer {
        <<qt5 framework>>
        +timeout: pyqtSignal
        +start(msec: int) void
        +stop() void
        +isActive() bool
    }
    
    class QCloseEvent {
        <<qt5 framework>>
    }
    
    %% ================================================================================
    %% EXTERNAL COMPONENTS
    %% ================================================================================
    
    class BoardConfiguration {
        <<board configuration>>
        +get_all_boards()$ List[Tuple[str, int]]
        +get_board_requirements(board_id: int)$ Dict[str, Any]
        +get_board_description(board_id: int, preset: int)$ Dict[str, Any]
        +get_preset_info()$ Dict[int, str]
    }
    
    class HelpButton {
        <<help system integration>>
        +topic: str
        +__init__(topic: str, parent: QWidget) void
    }
    
    class EventDispatcher {
        <<event system>>
        +get_instance()$ EventDispatcher
        +subscribe(event_type: EventType, callback: Callable) void
    }
    
    class EventType {
        <<event types enum>>
        +UI_UPDATE_CONTROLS$: EventType
        +STREAM_START$: EventType
        +STREAM_STOP$: EventType
        +BOARD_CONNECT$: EventType
        +BOARD_DISCONNECT$: EventType
        +VISUALIZATION_START$: EventType
        +VISUALIZATION_STOP$: EventType
        +FILTER_APPLY$: EventType
        +RECORDING_START$: EventType
        +RECORDING_STOP$: EventType
        +RECORDING_STATUS_CHANGED$: EventType
        +MNE_CONVERT$: EventType
        +MNE_PLOT$: EventType
        +MNE_SELECT_CHANNELS$: EventType
        +ICA_COMPUTE$: EventType
        +ICA_VIEW_COMPONENTS$: EventType
        +ICA_SELECT_CHANNELS$: EventType
        +WAVELET_COMPUTE$: EventType
        +WAVELET_APPLY_INVERSE$: EventType
        +DOWNSAMPLE_APPLY$: EventType
        +ADVANCED_FILTERS_APPLY$: EventType
        +STREAMER_ADD$: EventType
        +STREAMER_REMOVE$: EventType
        +DEVICE_CONFIG_RESPONSE$: EventType
    }
    
    %% ================================================================================
    %% STANDARD LIBRARY COMPONENTS
    %% ================================================================================
    
    class logging {
        <<stdlib>>
        +info(message: str) void
        +debug(message: str) void
        +warning(message: str) void
        +error(message: str) void
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
    UIPackage "1" *-- "1" BasePanel : contains
    UIPackage "1" *-- "1" ConnectionPanel : contains
    UIPackage "1" *-- "1" ProcessingPanel : contains
    UIPackage "1" *-- "1" RecordingPanel : contains
    UIPackage "1" *-- "1" StreamingPanel : contains
    UIPackage "1" *-- "1" MNEPanel : contains
    UIPackage "1" *-- "1" AdvancedProcessingPanel : contains
    UIPackage "1" *-- "1" AdvancedUIPackage : contains
    UIPackage "1" *-- "1" MNEUIPackage : contains
    
    %% Inheritance Hierarchy
    ConnectionPanel --|> BasePanel : extends
    ProcessingPanel --|> BasePanel : extends
    RecordingPanel --|> BasePanel : extends
    StreamingPanel --|> BasePanel : extends
    MNEPanel --|> BasePanel : extends
    AdvancedProcessingPanel --|> BasePanel : extends
    BasePanel --|> QWidget : extends
    
    %% Controller Relationships
    AdvancedProcessingPanel "1" *-- "1" AdvancedPanelController : controller
    MNEPanel "1" *-- "0..1" MNEPanelController : controller
    
    AdvancedPanelController "1" o-- "1" ICAWidget : ica_widget
    AdvancedPanelController "1" o-- "1" WaveletWidget : wavelet_widget
    AdvancedPanelController "1" o-- "1" DownsamplingWidget : downsampling_widget
    AdvancedPanelController "1" o-- "1" AdvancedFilterWidget : advanced_filter_widget
    
    MNEPanelController "1" o-- "1" MNEConversionWidget : conversion_widget
    MNEPanelController "1" o-- "1" MNEVisualizationWidget : visualization_widget
    MNEPanelController "1" o-- "1" MNEStatusWidget : status_widget
    
    %% API Event Handler Relationships
    ConnectionPanel "1" *-- "1" ApiEventHandler : api_event_handler
    ProcessingPanel "1" *-- "1" ApiEventHandler : api_event_handler
    RecordingPanel "1" *-- "1" ApiEventHandler : api_event_handler
    AdvancedProcessingPanel "1" *-- "1" ApiEventHandler : api_event_handler
    MNEPanel "1" *-- "1" MNEApiEventHandler : api_event_handler
    
    %% Core Component Relationships
    BasePanel "1" *-- "1" QScrollArea : scroll area
    BasePanel "1" *-- "1" QWidget : content_widget
    BasePanel "1" *-- "1" QVBoxLayout : layout
    
    ConnectionPanel "1" *-- "*" QComboBox : board_type_combo, preset_combo, param_fields
    ConnectionPanel "1" *-- "*" QPushButton : connect_btn, disconnect_btn, start_stream_btn, stop_stream_btn, show_viz_btn
    ConnectionPanel "1" *-- "1" QLineEdit : filter_edit
    ConnectionPanel "1" *-- "1" QLabel : board_info_label
    
    ProcessingPanel "1" *-- "*" QCheckBox : bandpass_check, notch_check, detrend_check
    ProcessingPanel "1" *-- "*" QDoubleSpinBox : bandpass_low_spin, bandpass_high_spin
    ProcessingPanel "1" *-- "*" QComboBox : notch_type_combo
    ProcessingPanel "1" *-- "*" QPushButton : apply_filters_btn, calculate_metrics_btn, brain_map_btn
    ProcessingPanel "1" *-- "1" QLabel : metrics_label
    ProcessingPanel "1" *-- "1" QTimer : brain_map_timer
    
    RecordingPanel "1" *-- "1" QLineEdit : record_file_edit
    RecordingPanel "1" *-- "*" QRadioButton : raw_radio, processed_radio, both_radio
    RecordingPanel "1" *-- "*" QPushButton : start_record_btn, stop_record_btn
    RecordingPanel "1" *-- "1" QSpinBox : marker_value_spin
    RecordingPanel "1" *-- "1" QPushButton : add_marker_btn
    RecordingPanel "1" *-- "1" QLabel : recording_status_label
    RecordingPanel "1" *-- "1" QTimer : status_timer
    
    StreamingPanel "1" *-- "*" QLineEdit : file_streamer_path, network_streamer_path, custom_streamer_path, config_cmd_edit
    StreamingPanel "1" *-- "1" QComboBox : file_data_type_combo
    StreamingPanel "1" *-- "1" QListWidget : streamers_list
    StreamingPanel "1" *-- "1" QTextEdit : config_response_text
    StreamingPanel "1" *-- "1" QPushButton : send_config_btn
    
    %% Signal Relationships
    BasePanel "1" *-- "2" pyqtSignal : status_message, error_message
    ConnectionPanel "1" *-- "4" pyqtSignal : board_connected, board_disconnected, stream_started, stream_stopped
    ProcessingPanel "1" *-- "0" pyqtSignal : inherits from BasePanel
    RecordingPanel "1" *-- "2" pyqtSignal : recording_started, recording_stopped
    StreamingPanel "1" *-- "0" pyqtSignal : inherits from BasePanel
    MNEPanel "1" *-- "0" pyqtSignal : inherits from BasePanel
    AdvancedProcessingPanel "1" *-- "0" pyqtSignal : inherits from BasePanel
    
    ApiEventHandler "1" *-- "*" pyqtSignal : various event signals
    MNEApiEventHandler "1" *-- "3" pyqtSignal : convert_signal, plot_signal, select_channels_signal
    
    %% Service Dependencies
    ConnectionPanel ..> CollectorService : uses
    ProcessingPanel ..> CollectorService : uses
    ProcessingPanel ..> DataAccessService : uses
    RecordingPanel ..> CollectorService : uses
    StreamingPanel ..> CollectorService : uses
    MNEPanel ..> MNEService : uses
    AdvancedProcessingPanel ..> AdvancedProcessingService : uses
    
    %% Event System Dependencies
    ConnectionPanel ..> EventDispatcher : subscribes
    ProcessingPanel ..> EventDispatcher : subscribes
    RecordingPanel ..> EventDispatcher : subscribes
    AdvancedProcessingPanel ..> EventDispatcher : subscribes
    MNEPanel ..> EventDispatcher : subscribes
    
    ConnectionPanel ..> EventType : uses
    ProcessingPanel ..> EventType : uses
    RecordingPanel ..> EventType : uses
    AdvancedProcessingPanel ..> EventType : uses
    MNEPanel ..> EventType : uses
    
    %% External Dependencies
    ConnectionPanel ..> BoardConfiguration : uses
    ConnectionPanel ..> HelpButton : uses
    ProcessingPanel ..> HelpButton : uses
    RecordingPanel ..> HelpButton : uses
    StreamingPanel ..> HelpButton : uses
    
    %% Qt Framework Dependencies
    ConnectionPanel ..> QVBoxLayout : creates
    ConnectionPanel ..> QComboBox : creates
    ConnectionPanel ..> QPushButton : creates
    ConnectionPanel ..> QLabel : creates
    ConnectionPanel ..> QLineEdit : creates
    
    ProcessingPanel ..> QVBoxLayout : creates
    ProcessingPanel ..> QCheckBox : creates
    ProcessingPanel ..> QDoubleSpinBox : creates
    ProcessingPanel ..> QPushButton : creates
    ProcessingPanel ..> QTimer : creates
    
    RecordingPanel ..> QVBoxLayout : creates
    RecordingPanel ..> QLineEdit : creates
    RecordingPanel ..> QRadioButton : creates
    RecordingPanel ..> QPushButton : creates
    RecordingPanel ..> QSpinBox : creates
    RecordingPanel ..> QTimer : creates
    
    StreamingPanel ..> QVBoxLayout : creates
    StreamingPanel ..> QLineEdit : creates
    StreamingPanel ..> QComboBox : creates
    StreamingPanel ..> QListWidget : creates
    StreamingPanel ..> QTextEdit : creates
    
    %% Standard Library Dependencies
    ConnectionPanel ..> logging : uses
    ProcessingPanel ..> logging : uses
    RecordingPanel ..> logging : uses
    StreamingPanel ..> logging : uses
    MNEPanel ..> logging : uses
    AdvancedProcessingPanel ..> logging : uses
    
    ConnectionPanel ..> typing : uses
    ProcessingPanel ..> typing : uses
    RecordingPanel ..> typing : uses
    StreamingPanel ..> typing : uses
    MNEPanel ..> typing : uses
    AdvancedProcessingPanel ..> typing : uses
    
    %% ================================================================================
    %% LOGICAL GROUPINGS
    %% ================================================================================
    
    %% Core Panel Categories
    ConnectionPanel -.- ProcessingPanel : "primary panels"
    ProcessingPanel -.- RecordingPanel : "primary panels"
    RecordingPanel -.- StreamingPanel : "primary panels"
    StreamingPanel -.- MNEPanel : "primary panels"
    MNEPanel -.- AdvancedProcessingPanel : "primary panels"
    
    %% Specialized Packages
    AdvancedUIPackage -.- MNEUIPackage : "specialized ui packages"
    
    %% Controllers
    AdvancedPanelController -.- MNEPanelController : "specialized controllers"
    
    %% API Event Handlers
    ApiEventHandler -.- MNEApiEventHandler : "event handling"
    
    %% Qt Framework Components
    QWidget -.- QObject : "qt framework"
    QObject -.- pyqtSignal : "qt framework"
    pyqtSignal -.- QVBoxLayout : "qt framework"
    QVBoxLayout -.- QScrollArea : "qt framework"
    QScrollArea -.- QComboBox : "qt framework"
    QComboBox -.- QPushButton : "qt framework"
    QPushButton -.- QLabel : "qt framework"
    QLabel -.- QCheckBox : "qt framework"
    QCheckBox -.- QSpinBox : "qt framework"
    QSpinBox -.- QDoubleSpinBox : "qt framework"
    QDoubleSpinBox -.- QLineEdit : "qt framework"
    QLineEdit -.- QTextEdit : "qt framework"
    QTextEdit -.- QListWidget : "qt framework"
    QListWidget -.- QRadioButton : "qt framework"
    QRadioButton -.- QTimer : "qt framework"
    
    %% External Components
    BoardConfiguration -.- HelpButton : "external utilities"
    HelpButton -.- EventDispatcher : "external utilities"
    EventDispatcher -.- EventType : "external utilities"
    
    %% Services
    CollectorService -.- DataAccessService : "core services"
    DataAccessService -.- MNEService : "core services"
    MNEService -.- AdvancedProcessingService : "core services"
    
    %% Standard Library
    logging -.- typing : "standard libraries"
```