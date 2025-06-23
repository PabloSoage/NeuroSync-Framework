```mermaid
classDiagram
    %% ================================================================================
    %% SERVICES/ICA MODULE - INDEPENDENT COMPONENT ANALYSIS SERVICES
    %% ================================================================================

    %% ================================================================================
    %% CORE ICA SERVICE CLASSES
    %% ================================================================================

    class ICAProcessService {
        <<multiprocess service>>
        -_ica_process: Optional[mp.Process]
        -_command_queue: Optional[mp.Queue]
        -_response_queue: Optional[mp.Queue]
        -_is_initialized: bool
        -_communication_timer: Optional[QTimer]
        -_current_ica_results: Optional[Dict[str, Any]]
        -_visualization_active: bool
        -_current_colormap: str

        +ica_computed: pyqtSignal[bool, dict, str]
        +visualization_ready: pyqtSignal[bool, str]
        +export_progress: pyqtSignal[int, str]
        +export_completed: pyqtSignal[bool, str]

        +__init__() void
        +initialize() bool
        +compute_ica(ica_data: Any, params: Dict[str, Any], sampling_rate: float) void
        +visualize_ica(ica_components: Dict[str, Any], sampling_rate: float, colormap: str) void
        +close_visualization() void
        +export_ica_overview(ica_components: Dict[str, Any], colormap: str, sampling_rate: float, filename: str) void
        +export_ica_all(ica_components: Dict[str, Any], colormap: str, sampling_rate: float, directory: str) void
        +cancel_current_operation() void
        +get_current_ica_results() Optional[Dict[str, Any]]
        +is_visualization_active() bool
        +cleanup() void
        -_check_responses() void
        -_handle_response(response: Dict[str, Any]) void
    }

    class ICARealtimeService {
        <<realtime service>>
        -_data_access_service: DataAccessService
        -_processor_service: Any
        -_is_active: bool
        -_update_interval: float
        -_window_size: float
        -_realtime_timer: QTimer
        -_ica_params: Dict[str, Any]
        -_data_buffer: Optional[np.ndarray]
        -_buffer_size: int
        -_sampling_rate: float
        -_current_realtime_results: Optional[Dict[str, Any]]

        +realtime_ica_updated: pyqtSignal[dict, str]
        +realtime_status_changed: pyqtSignal[bool, str]
        +realtime_error: pyqtSignal[str]

        +__init__() void
        +initialize(processor_service: Any) bool
        +start_realtime_ica(ica_params: Dict[str, Any]) bool
        +stop_realtime_ica() void
        +update_interval(new_interval: float) bool
        +get_current_interval() float
        +get_current_results() Optional[Dict[str, Any]]
        +get_window_size() float
        +set_window_size(window_size: float) bool
        +is_active() bool
        +cleanup() void
        -_update_realtime_ica() void
        -_update_data_buffer(new_data: np.ndarray) void
        -_compute_window_ica() Optional[Dict[str, Any]]
    }

    class ExportService {
        <<export service>>
        -_export_process: Optional[mp.Process]
        -_export_queue: Optional[mp.Queue]
        -_is_exporting: bool

        +progress_updated: pyqtSignal[int, str]
        +export_completed: pyqtSignal[bool, str]

        +__init__() void
        +export_ica_overview(ica_components: Dict[str, Any], colormap: str, sampling_rate: float, filename: str) void
        +export_ica_components(ica_components: Dict[str, Any], colormap: str, sampling_rate: float, directory: str) void
        +check_export_progress() void
        +cancel_export() void
        +cleanup() void
        -_start_export_process(export_data: Dict[str, Any], export_type: str) void
    }

    class ICAServicesPackage {
        <<module package>>
        +ExportService: Class
        +ICAProcessService: Class
        +ICARealtimeService: Class
    }

    %% ================================================================================
    %% WORKER PROCESS FUNCTIONS
    %% ================================================================================

    class ICAWorkerProcess {
        <<worker process>>
        +_ica_worker_process(command_queue: mp.Queue, response_queue: mp.Queue)$ void
        +_apply_dark_theme_to_process(app: Any)$ void
        +_handle_ica_computation(command: Dict[str, Any], response_queue: mp.Queue)$ void
        +_handle_ica_visualization(command: Dict[str, Any], response_queue: mp.Queue)$ Any
        +_handle_ica_export_overview(command: Dict[str, Any], response_queue: mp.Queue)$ void
        +_handle_ica_export_all(command: Dict[str, Any], response_queue: mp.Queue)$ void
        +_handle_ica_visualization_update(dialog: Any, command: Dict[str, Any], response_queue: mp.Queue)$ void
    }

    class ExportWorkerProcess {
        <<worker process>>
        +_export_worker_process(export_data: Dict[str, Any], export_type: str, progress_queue: mp.Queue)$ void
        +_export_single_overview_worker(export_data: Dict[str, Any], progress_queue: mp.Queue)$ void
        +_export_enhanced_overview_worker(export_data: Dict[str, Any], progress_queue: mp.Queue)$ void
        +_export_all_images_worker(export_data: Dict[str, Any], progress_queue: mp.Queue)$ void
        +_export_enhanced_all_images_worker(export_data: Dict[str, Any], progress_queue: mp.Queue)$ void
        +_create_complete_overview_figure_worker(ica_components: Dict[str, Any], colormap: str, sampling_rate: float, save_path: str)$ void
        +_create_enhanced_overview_figure_worker(ica_components: Dict[str, Any], colormap: str, sampling_rate: float, save_path: str, progress_queue: Optional[mp.Queue])$ void
    }

    %% ================================================================================
    %% EXTERNAL DEPENDENCIES
    %% ================================================================================

    class DataAccessService {
        <<external service>>
        +get_instance()$ DataAccessService
        +get_current_data() Tuple[np.ndarray, List[int]]
        +get_sampling_rate() float
    }

    class SignalProcessor {
        <<external processor>>
        +perform_ica(data: np.ndarray, num_components: int) Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
    }

    class ICAVisualizationDialog {
        <<external ui>>
        +colormap_combo: QComboBox
        +update_visualization(ica_components: Dict[str, Any], colormap: str) void
        +show() void
        +close() void
        +isVisible() bool
    }

    class ThemeManager {
        <<external utility>>
        +apply_dark_theme(app: Any) void
    }

    %% ================================================================================
    %% QT5 FRAMEWORK COMPONENTS
    %% ================================================================================

    class QObject {
        <<qt5 framework>>
        +__init__(parent: Optional[QObject]) void
    }

    class pyqtSignal {
        <<qt5 framework>>
        +emit(*args: Any) void
        +connect(slot: Callable) void
        +disconnect(slot: Optional[Callable]) void
    }

    class QTimer {
        <<qt5 framework>>
        +timeout: pyqtSignal
        +start(msec: int) void
        +stop() void
        +isActive() bool
    }

    class QApplication {
        <<qt5 framework>>
        +processEvents() void
        +quit() void
        +setStyleSheet(style: str) void
    }

    class QComboBox {
        <<qt5 framework>>
        +count() int
        +itemData(index: int) Any
        +setCurrentIndex(index: int) void
    }

    %% ================================================================================
    %% MULTIPROCESSING COMPONENTS
    %% ================================================================================

    class multiprocessing {
        <<stdlib>>
        +Process: Class
        +Queue: Class
    }

    class Process {
        <<multiprocessing>>
        +target: Callable
        +args: Tuple[Any, ...]
        +daemon: bool
        +start() void
        +join(timeout: Optional[float]) void
        +terminate() void
        +kill() void
        +is_alive() bool
    }

    class Queue {
        <<multiprocessing>>
        +put(item: Any) void
        +get() Any
        +get_nowait() Any
        +empty() bool
    }

    class queue {
        <<stdlib>>
        +Empty: Exception
    }

    %% ================================================================================
    %% MATPLOTLIB COMPONENTS
    %% ================================================================================

    class matplotlib {
        <<plotting library>>
        +use(backend: str) void
    }

    class pyplot {
        <<matplotlib>>
        +subplots(nrows: int, ncols: int, figsize: Tuple[float, float]) Tuple[Figure, ndarray]
        +tight_layout() void
        +close(fig: Figure) void
        +colorbar(mappable: Any, ax: Axes, shrink: float) Colorbar
    }

    class Figure {
        <<matplotlib>>
        +suptitle(title: str, fontsize: int, fontweight: str) void
        +savefig(filename: str, dpi: int, bbox_inches: str) void
    }

    class Axes {
        <<matplotlib>>
        +imshow(data: np.ndarray, aspect: str, cmap: str, interpolation: str) AxesImage
        +plot(x: np.ndarray, y: np.ndarray, linewidth: float, color: str, alpha: float) List[Line2D]
        +hist(data: np.ndarray, bins: int, alpha: float, color: str, edgecolor: str) Tuple[np.ndarray, np.ndarray, List[Rectangle]]
        +semilogy(x: np.ndarray, y: np.ndarray, color: str, linewidth: float) List[Line2D]
        +set_title(title: str, fontsize: int, fontweight: str) void
        +set_xlabel(label: str, fontsize: int) void
        +set_ylabel(label: str, fontsize: int) void
        +set_xlim(left: float, right: float) void
        +set_ylim(bottom: float, top: float) void
        +grid(visible: bool, alpha: float) void
        +tick_params(axis: str, which: str, labelsize: int) void
        +text(x: float, y: float, s: str, transform: Any, fontsize: int, verticalalignment: str, bbox: Dict[str, Any]) Text
    }

    %% ================================================================================
    %% SCIPY COMPONENTS
    %% ================================================================================

    class scipy_signal {
        <<scipy library>>
        +welch(x: np.ndarray, fs: float, nperseg: int) Tuple[np.ndarray, np.ndarray]
    }

    %% ================================================================================
    %% STANDARD LIBRARY COMPONENTS
    %% ================================================================================

    class numpy {
        <<stdlib>>
        +ndarray: Class
        +zeros(shape: Tuple[int, ...]) ndarray
        +linspace(start: float, stop: float, num: int) ndarray
        +mean(data: ndarray) float
        +std(data: ndarray) float
        +min(data: ndarray) float
        +max(data: ndarray) float
        +ceil(x: float) int
    }

    class logging {
        <<stdlib>>
        +info(message: str) void
        +warning(message: str) void
        +error(message: str) void
        +debug(message: str) void
    }

    class time {
        <<stdlib>>
        +time() float
        +sleep(seconds: float) void
    }

    class os {
        <<stdlib>>
        +path: module
        +join(path: str, *paths: str) str
    }

    class sys {
        <<stdlib>>
        +argv: List[str]
    }

    class typing {
        <<stdlib>>
        +Any
        +Dict
        +List
        +Optional
        +Tuple
    }

    %% ================================================================================
    %% RELATIONSHIPS
    %% ================================================================================

    %% Package Composition
    ICAServicesPackage "1" *-- "1" ICAProcessService : contains
    ICAServicesPackage "1" *-- "1" ICARealtimeService : contains
    ICAServicesPackage "1" *-- "1" ExportService : contains

    %% Inheritance
    ICAProcessService --|> QObject : extends
    ICARealtimeService --|> QObject : extends
    ExportService --|> QObject : extends

    %% Core Component Relationships
    ICAProcessService "1" *-- "0..1" Process : _ica_process
    ICAProcessService "1" *-- "0..1" Queue : _command_queue
    ICAProcessService "1" *-- "0..1" Queue : _response_queue
    ICAProcessService "1" *-- "0..1" QTimer : _communication_timer

    ICARealtimeService "1" *-- "1" DataAccessService : _data_access_service
    ICARealtimeService "1" *-- "1" QTimer : _realtime_timer
    ICARealtimeService "1" o-- "1" SignalProcessor : _processor_service

    ExportService "1" *-- "0..1" Process : _export_process
    ExportService "1" *-- "0..1" Queue : _export_queue

    %% Signal Relationships
    ICAProcessService "1" *-- "4" pyqtSignal : signals
    ICARealtimeService "1" *-- "3" pyqtSignal : signals
    ExportService "1" *-- "2" pyqtSignal : signals

    %% Worker Process Dependencies
    ICAProcessService ..> ICAWorkerProcess : uses
    ExportService ..> ExportWorkerProcess : uses

    ICAWorkerProcess ..> SignalProcessor : uses
    ICAWorkerProcess ..> ICAVisualizationDialog : creates
    ICAWorkerProcess ..> ThemeManager : uses
    ICAWorkerProcess ..> QApplication : uses
    ICAWorkerProcess ..> ExportWorkerProcess : delegates to

    ExportWorkerProcess ..> matplotlib : uses
    ExportWorkerProcess ..> pyplot : uses
    ExportWorkerProcess ..> Figure : creates
    ExportWorkerProcess ..> Axes : manipulates
    ExportWorkerProcess ..> scipy_signal : uses

    %% External Service Dependencies
    ICARealtimeService ..> DataAccessService : uses
    ICAProcessService ..> SignalProcessor : uses (via worker)

    %% Qt Framework Dependencies
    ICAProcessService ..> QTimer : uses
    ICARealtimeService ..> QTimer : uses
    ICAProcessService ..> pyqtSignal : emits
    ICARealtimeService ..> pyqtSignal : emits
    ExportService ..> pyqtSignal : emits

    %% Multiprocessing Dependencies
    ICAProcessService ..> multiprocessing : uses
    ExportService ..> multiprocessing : uses
    ICAProcessService ..> Process : creates
    ICAProcessService ..> Queue : creates
    ExportService ..> Process : creates
    ExportService ..> Queue : creates
    ICAProcessService ..> queue : handles exceptions

    %% Standard Library Dependencies
    ICAProcessService ..> logging : uses
    ICARealtimeService ..> logging : uses
    ExportService ..> logging : uses
    ICARealtimeService ..> time : uses
    ICARealtimeService ..> numpy : uses
    ExportWorkerProcess ..> os : uses
    ICAWorkerProcess ..> sys : uses

    %% Type Hints
    ICAProcessService ..> typing : uses
    ICARealtimeService ..> typing : uses
    ExportService ..> typing : uses

    %% ================================================================================
    %% LOGICAL GROUPINGS
    %% ================================================================================

    %% ICA Service Types
    ICAProcessService -.- ICARealtimeService : "ica services"
    ICARealtimeService -.- ExportService : "ica services"

    %% Worker Processes
    ICAWorkerProcess -.- ExportWorkerProcess : "worker processes"

    %% Qt Components
    QObject -.- pyqtSignal : "qt framework"
    pyqtSignal -.- QTimer : "qt framework"
    QTimer -.- QApplication : "qt framework"

    %% Multiprocessing Components
    multiprocessing -.- Process : "multiprocessing framework"
    Process -.- Queue : "multiprocessing framework"
    Queue -.- queue : "multiprocessing framework"

    %% Matplotlib Components
    matplotlib -.- pyplot : "plotting framework"
    pyplot -.- Figure : "plotting framework"
    Figure -.- Axes : "plotting framework"

    %% Standard Library Components
    numpy -.- logging : "standard libraries"
    logging -.- time : "standard libraries"
    time -.- os : "standard libraries"
    os -.- sys : "standard libraries"
    sys -.- typing : "standard libraries"
```
