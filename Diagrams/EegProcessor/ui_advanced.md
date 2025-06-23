```mermaid
classDiagram
    %% ================================================================================
    %% UI/ADVANCED MODULE - ADVANCED PROCESSING USER INTERFACE ARCHITECTURE
    %% ================================================================================

    %% ================================================================================
    %% CORE CONTROLLER CLASS
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
        +collector_service: Any
        +processor_service: Any
        +processing_service: AdvancedProcessingService
        +export_service: ExportService
        +ica_process_service: ICAProcessService
        +ica_realtime_service: ICARealtimeService
        +export_progress_dialog: Optional[QProgressDialog]
        +export_timer: Optional[QTimer]
        -_last_status_update: float

        +__init__(ica_widget: ICAWidget, wavelet_widget: WaveletWidget, downsampling_widget: DownsamplingWidget, advanced_filter_widget: AdvancedFilterWidget, collector_service: Any, processor_service: Any, parent: Optional[Any]) void
        +enable_processing(enabled: bool) void
        +update_channel_lists(channel_names: List[str]) bool
        +cleanup() void
        -_connect_widget_signals() void
        -_initialize_channel_data() void
        -_setup_processing_panel_reference() void
        -_handle_ica_computation(params: Dict[str, Any]) void
        -_handle_ica_visualization(params: Dict[str, Any]) void
        -_handle_realtime_start(params: Dict[str, Any]) void
        -_handle_realtime_stop() void
        -_handle_realtime_interval_change(interval: float) void
        -_handle_ica_export_overview() void
        -_handle_ica_export_all() void
        -_handle_ica_export_overview_with_colormap(colormap: str) void
        -_handle_ica_export_all_with_colormap(colormap: str) void
        -_handle_wavelet_computation(params: Dict[str, Any]) void
        -_handle_wavelet_inverse(apply: bool) void
        -_handle_wavelet_settings_changed(settings: Dict[str, Any]) void
        -_handle_downsampling(params: Dict[str, Any]) void
        -_handle_downsampling_settings_changed(settings: Dict[str, Any]) void
        -_handle_advanced_filters(params: Dict[str, Any]) void
        -_handle_advanced_filter_settings_changed(settings: Dict[str, Any]) void
        -_on_realtime_ica_updated(ica_components: Dict[str, Any], message: str) void
        -_on_realtime_status_changed(is_active: bool, message: str) void
        -_on_realtime_error(error_message: str) void
        -_on_visualization_ready(success: bool, message: str) void
        -_update_export_progress(percent: int, status: str) void
        -_export_finished(success: bool, message: str) void
        -_cancel_export() void
        -_cleanup_export() void
    }

    class AdvancedUIPackage {
        <<module package>>
        +AdvancedPanelController: Class
        +dialogs: module
        +widgets: module
    }

    %% ================================================================================
    %% SPECIALIZED WIDGET PACKAGES
    %% ================================================================================

    class AdvancedWidgetsPackage {
        <<specialized widgets>>
        +AdvancedFilterWidget: Class
        +ICAWidget: Class
        +WaveletWidget: Class
        +DownsamplingWidget: Class
    }

    class AdvancedDialogsPackage {
        <<specialized dialogs>>
        +ICAVisualizationDialog: Class
    }

    %% ================================================================================
    %% ADVANCED PROCESSING WIDGETS
    %% ================================================================================

    class AdvancedFilterWidget {
        <<advanced filter widget>>
        +apply_requested: pyqtSignal[dict]
        +settings_changed: pyqtSignal[dict]
        +applied: bool
        +channel_names: List[str]
        +selected_channels: List[int]
        +filter_type_combo: QComboBox
        +filter_order_spin: QSpinBox
        +window_function_combo: QComboBox
        +ripple_spin: QDoubleSpinBox
        +filter_channel_select_btn: QPushButton
        +apply_adv_filter_btn: QPushButton

        +update_channels(channel_names: List[str]) void
        +set_processing_panel_reference(processing_panel: Any) void
        +set_enabled(enabled: bool) void
        +get_advanced_filter_settings() Dict[str, Any]
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
        +channel_names: List[str]
        +selected_channels: List[int]
        +ica_results: Optional[Dict[str, Any]]
        +realtime_active: bool
        +ica_components_spin: QSpinBox
        +compute_ica_btn: QPushButton
        +view_ica_components_btn: QPushButton
        +realtime_enable_check: QCheckBox
        +colormap_combo: QComboBox

        +update_channels(channel_names: List[str]) void
        +set_ica_results(ica_results: Dict[str, Any]) void
        +set_realtime_active(active: bool, message: str) void
        +get_colormap() str
        +set_enabled(enabled: bool) void
    }

    class WaveletWidget {
        <<wavelet analysis widget>>
        +compute_requested: pyqtSignal[dict]
        +apply_inverse_requested: pyqtSignal[bool]
        +settings_changed: pyqtSignal[dict]
        +channel_names: List[str]
        +wavelet_results: Optional[Dict[str, Any]]
        +inverse_applied: bool
        +wavelet_type_combo: QComboBox
        +wavelet_level_spin: QSpinBox
        +wavelet_channel_combo: QComboBox
        +compute_wavelet_btn: QPushButton
        +inverse_wavelet_btn: QPushButton

        +update_channels(channel_names: List[str]) void
        +set_wavelet_results(coefficients: Any, metadata: Dict[str, Any]) void
        +has_wavelet_results() bool
        +set_enabled(enabled: bool) void
    }

    class DownsamplingWidget {
        <<downsampling widget>>
        +apply_requested: pyqtSignal[dict]
        +settings_changed: pyqtSignal[dict]
        +applied: bool
        +downsample_factor_spin: QSpinBox
        +downsample_agg_combo: QComboBox
        +apply_downsample_btn: QPushButton

        +set_enabled(enabled: bool) void
        +get_downsample_settings() Dict[str, Any]
    }

    %% ================================================================================
    %% SPECIALIZED DIALOGS
    %% ================================================================================

    class ICAVisualizationDialog {
        <<ica visualization dialog>>
        +export_overview_requested: pyqtSignal
        +export_all_requested: pyqtSignal
        +ica_components: Dict[str, Any]
        +sampling_rate: float
        +is_realtime: bool
        +figure: Optional[Figure]
        +canvas: Optional[FigureCanvas]
        +colormap_combo: QComboBox

        +update_visualization(new_ica_components: Dict[str, Any], colormap: Optional[str]) void
        +closeEvent(event: Any) void
    }

    %% ================================================================================
    %% SERVICE LAYER INTEGRATION
    %% ================================================================================

    class AdvancedProcessingService {
        <<advanced analysis service>>
        +compute_ica(params: Dict[str, Any]) Dict[str, Any]
        +compute_wavelet(params: Dict[str, Any]) Dict[str, Any]
        +apply_wavelet_inverse(apply: bool) Dict[str, Any]
        +apply_downsampling(params: Dict[str, Any]) Dict[str, Any]
        +apply_advanced_filters(params: Dict[str, Any]) Dict[str, Any]
        +get_ica_results() Optional[Dict[str, Any]]
        +get_wavelet_results() Optional[Dict[str, Any]]
        +get_channel_names() List[str]
    }

    class ExportService {
        <<export coordination service>>
        +progress_updated: pyqtSignal[int, str]
        +export_completed: pyqtSignal[bool, str]

        +export_ica_overview(ica_components: Dict[str, Any], colormap: str, sampling_rate: float, filename: str) void
        +export_ica_components(ica_components: Dict[str, Any], colormap: str, sampling_rate: float, directory: str) void
        +check_export_progress() void
        +cancel_export() void
        +cleanup() void
    }

    class ICAProcessService {
        <<ica process service>>
        +visualization_ready: pyqtSignal[bool, str]
        -_is_initialized: bool

        +initialize() bool
        +visualize_ica(ica_components: Dict[str, Any], sampling_rate: float, colormap: str) void
        +is_visualization_active() bool
        +cleanup() void
    }

    class ICARealtimeService {
        <<ica realtime service>>
        +realtime_ica_updated: pyqtSignal[dict, str]
        +realtime_status_changed: pyqtSignal[bool, str]
        +realtime_error: pyqtSignal[str]

        +initialize(processor_service: Any) void
        +start_realtime_ica(params: Dict[str, Any]) bool
        +stop_realtime_ica() void
        +update_interval(interval: float) void
        +cleanup() void
    }

    %% ================================================================================
    %% QT5 FRAMEWORK COMPONENTS
    %% ================================================================================

    class QObject {
        <<qt5 framework>>
        +parent: Optional[QObject]

        +__init__(parent: Optional[QObject]) void
    }

    class pyqtSignal {
        <<qt5 framework>>
        +emit(*args: Any) void
        +connect(slot: Callable) void
        +disconnect(slot: Optional[Callable]) void
    }

    class QWidget {
        <<qt5 framework>>
        +setEnabled(enabled: bool) void
        +parent() QWidget
    }

    class QTimer {
        <<qt5 framework>>
        +timeout: pyqtSignal
        +start(msec: int) void
        +stop() void
    }

    class QProgressDialog {
        <<qt5 framework>>
        +canceled: pyqtSignal
        +setWindowTitle(title: str) void
        +setModal(modal: bool) void
        +setValue(value: int) void
        +setLabelText(text: str) void
        +show() void
        +close() void
    }

    class QFileDialog {
        <<qt5 framework>>
        +getSaveFileName(parent: QWidget, caption: str, directory: str, filter: str)$ Tuple[str, str]
        +getExistingDirectory(parent: QWidget, caption: str, directory: str)$ str
    }

    class QMessageBox {
        <<qt5 framework>>
        +question(parent: QWidget, title: str, text: str, buttons: int)$ int
        +Yes$: int
        +No$: int
    }

    class QSpinBox {
        <<qt5 framework>>
        +value() int
        +setValue(value: int) void
    }

    class QDoubleSpinBox {
        <<qt5 framework>>
        +value() float
        +setValue(value: float) void
    }

    class QComboBox {
        <<qt5 framework>>
        +currentText() str
        +currentData() Any
    }

    class QCheckBox {
        <<qt5 framework>>
        +isChecked() bool
        +setChecked(checked: bool) void
    }

    class QPushButton {
        <<qt5 framework>>
        +clicked: pyqtSignal
        +setEnabled(enabled: bool) void
    }

    %% ================================================================================
    %% MATPLOTLIB COMPONENTS
    %% ================================================================================

    class Figure {
        <<matplotlib>>
        +clear() void
        +savefig(filename: str, dpi: int) void
    }

    class FigureCanvas {
        <<matplotlib.backends.backend_qt5agg>>
        +figure: Figure
        +draw_idle() void
    }

    %% ================================================================================
    %% BRAINFLOW COMPONENTS
    %% ================================================================================

    class FilterTypes {
        <<brainflow enum>>
        +BUTTERWORTH$: FilterTypes
        +CHEBYSHEV_TYPE_1$: FilterTypes
        +BESSEL$: FilterTypes
        +value: int
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

    class time {
        <<stdlib>>
        +time() float
    }

    class typing {
        <<stdlib>>
        +Dict
        +List
        +Any
        +Optional
    }

    %% ================================================================================
    %% RELATIONSHIPS
    %% ================================================================================

    %% Package Composition
    AdvancedUIPackage "1" *-- "1" AdvancedPanelController : contains
    AdvancedUIPackage "1" *-- "1" AdvancedWidgetsPackage : contains
    AdvancedUIPackage "1" *-- "1" AdvancedDialogsPackage : contains

    AdvancedWidgetsPackage "1" *-- "1" AdvancedFilterWidget : contains
    AdvancedWidgetsPackage "1" *-- "1" ICAWidget : contains
    AdvancedWidgetsPackage "1" *-- "1" WaveletWidget : contains
    AdvancedWidgetsPackage "1" *-- "1" DownsamplingWidget : contains

    AdvancedDialogsPackage "1" *-- "1" ICAVisualizationDialog : contains

    %% Inheritance
    AdvancedPanelController --|> QObject : extends
    AdvancedFilterWidget --|> QWidget : extends
    ICAWidget --|> QWidget : extends
    WaveletWidget --|> QWidget : extends
    DownsamplingWidget --|> QWidget : extends

    %% Core Controller Relationships
    AdvancedPanelController "1" o-- "1" AdvancedFilterWidget : ica_widget
    AdvancedPanelController "1" o-- "1" ICAWidget : wavelet_widget
    AdvancedPanelController "1" o-- "1" WaveletWidget : downsampling_widget
    AdvancedPanelController "1" o-- "1" DownsamplingWidget : advanced_filter_widget
    AdvancedPanelController "1" *-- "1" AdvancedProcessingService : processing_service
    AdvancedPanelController "1" *-- "1" ExportService : export_service
    AdvancedPanelController "1" *-- "1" ICAProcessService : ica_process_service
    AdvancedPanelController "1" *-- "1" ICARealtimeService : ica_realtime_service
    AdvancedPanelController "1" *-- "0..1" QProgressDialog : export_progress_dialog
    AdvancedPanelController "1" *-- "0..1" QTimer : export_timer

    %% Widget Component Relationships
    AdvancedFilterWidget "1" *-- "1" QComboBox : filter_type_combo
    AdvancedFilterWidget "1" *-- "1" QSpinBox : filter_order_spin
    AdvancedFilterWidget "1" *-- "1" QComboBox : window_function_combo
    AdvancedFilterWidget "1" *-- "1" QDoubleSpinBox : ripple_spin
    AdvancedFilterWidget "1" *-- "1" QPushButton : filter_channel_select_btn
    AdvancedFilterWidget "1" *-- "1" QPushButton : apply_adv_filter_btn

    ICAWidget "1" *-- "1" QSpinBox : ica_components_spin
    ICAWidget "1" *-- "1" QPushButton : compute_ica_btn
    ICAWidget "1" *-- "1" QPushButton : view_ica_components_btn
    ICAWidget "1" *-- "1" QCheckBox : realtime_enable_check
    ICAWidget "1" *-- "1" QComboBox : colormap_combo

    WaveletWidget "1" *-- "1" QComboBox : wavelet_type_combo
    WaveletWidget "1" *-- "1" QSpinBox : wavelet_level_spin
    WaveletWidget "1" *-- "1" QComboBox : wavelet_channel_combo
    WaveletWidget "1" *-- "1" QPushButton : compute_wavelet_btn
    WaveletWidget "1" *-- "1" QPushButton : inverse_wavelet_btn

    DownsamplingWidget "1" *-- "1" QSpinBox : downsample_factor_spin
    DownsamplingWidget "1" *-- "1" QComboBox : downsample_agg_combo
    DownsamplingWidget "1" *-- "1" QPushButton : apply_downsample_btn

    %% Dialog Relationships
    ICAVisualizationDialog "1" *-- "0..1" Figure : figure
    ICAVisualizationDialog "1" *-- "0..1" FigureCanvas : canvas
    ICAVisualizationDialog "1" *-- "1" QComboBox : colormap_combo

    %% Signal Relationships
    AdvancedPanelController "1" *-- "4" pyqtSignal : signals
    AdvancedFilterWidget "1" *-- "2" pyqtSignal : signals
    ICAWidget "1" *-- "7" pyqtSignal : signals
    WaveletWidget "1" *-- "3" pyqtSignal : signals
    DownsamplingWidget "1" *-- "2" pyqtSignal : signals
    ICAVisualizationDialog "1" *-- "2" pyqtSignal : signals
    ExportService "1" *-- "2" pyqtSignal : signals
    ICAProcessService "1" *-- "1" pyqtSignal : signals
    ICARealtimeService "1" *-- "3" pyqtSignal : signals

    %% Signal Connections
    AdvancedFilterWidget ..> AdvancedPanelController : apply_requested, settings_changed
    ICAWidget ..> AdvancedPanelController : compute_requested, view_components_requested, export signals, realtime signals
    WaveletWidget ..> AdvancedPanelController : compute_requested, apply_inverse_requested, settings_changed
    DownsamplingWidget ..> AdvancedPanelController : apply_requested, settings_changed

    ExportService ..> AdvancedPanelController : progress_updated, export_completed
    ICAProcessService ..> AdvancedPanelController : visualization_ready
    ICARealtimeService ..> AdvancedPanelController : realtime_ica_updated, realtime_status_changed, realtime_error

    ICAVisualizationDialog ..> AdvancedPanelController : export_overview_requested, export_all_requested

    %% Service Dependencies
    AdvancedPanelController ..> AdvancedProcessingService : uses
    AdvancedPanelController ..> ExportService : uses
    AdvancedPanelController ..> ICAProcessService : uses
    AdvancedPanelController ..> ICARealtimeService : uses

    %% Dynamic Dialog Creation
    AdvancedPanelController ..> ICAVisualizationDialog : creates dynamically

    %% Qt Framework Dependencies
    AdvancedPanelController ..> QTimer : creates
    AdvancedPanelController ..> QProgressDialog : creates
    AdvancedPanelController ..> QFileDialog : uses
    AdvancedPanelController ..> QMessageBox : uses

    %% BrainFlow Dependencies
    AdvancedPanelController ..> FilterTypes : uses

    %% Standard Library Dependencies
    AdvancedPanelController ..> logging : uses
    AdvancedPanelController ..> time : uses
    AdvancedPanelController ..> typing : uses

    %% ================================================================================
    %% LOGICAL GROUPINGS
    %% ================================================================================

    %% Core Components
    AdvancedPanelController -.- AdvancedProcessingService : "core coordination"

    %% Widget Categories
    AdvancedFilterWidget -.- ICAWidget : "analysis widgets"
    ICAWidget -.- WaveletWidget : "analysis widgets"
    WaveletWidget -.- DownsamplingWidget : "analysis widgets"

    %% Service Layer
    AdvancedProcessingService -.- ExportService : "service layer"
    ExportService -.- ICAProcessService : "service layer"
    ICAProcessService -.- ICARealtimeService : "service layer"

    %% Qt Framework Components
    QObject -.- pyqtSignal : "qt framework"
    pyqtSignal -.- QWidget : "qt framework"
    QWidget -.- QTimer : "qt framework"
    QTimer -.- QProgressDialog : "qt framework"
    QProgressDialog -.- QFileDialog : "qt framework"
    QFileDialog -.- QMessageBox : "qt framework"

    %% Qt Widget Components
    QSpinBox -.- QDoubleSpinBox : "qt widgets"
    QDoubleSpinBox -.- QComboBox : "qt widgets"
    QComboBox -.- QCheckBox : "qt widgets"
    QCheckBox -.- QPushButton : "qt widgets"

    %% Matplotlib Components
    Figure -.- FigureCanvas : "matplotlib framework"

    %% Standard Library Components
    logging -.- time : "standard libraries"
    time -.- typing : "standard libraries"
```
