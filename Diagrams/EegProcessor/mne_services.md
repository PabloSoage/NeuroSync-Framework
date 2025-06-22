```mermaid
classDiagram
    %% ================================================================================
    %% SERVICES/MNE MODULE - MNE-PYTHON INTEGRATION SERVICES
    %% ================================================================================
    
    %% ================================================================================
    %% CORE MNE SERVICE CLASSES
    %% ================================================================================
    
    class MNEConverterService {
        <<mne conversion service>>
        +process_manager: MNEProcessManagerInterface
        +result_storage: MNEResultStorageInterface
        -_completion_callbacks: Dict[str, Callable]
        
        +__init__(process_manager: MNEProcessManagerInterface, result_storage: MNEResultStorageInterface) void
        +convert_to_mne_async(data: np.ndarray, metadata: Dict[str, Any], duration_seconds: int, convert_to_v: bool, selected_channels: Optional[List[int]], callback: Optional[Callable]) str
        +get_conversion_status(task_id: str) Dict[str, Any]
        +cancel_conversion(task_id: str) bool
        -_handle_conversion_complete(task_id: str, result: Dict[str, Any], callback: Optional[Callable]) void
    }
    
    class MNEVisualizerService {
        <<mne visualization service>>
        +process_manager: MNEProcessManagerInterface
        +result_storage: MNEResultStorageInterface
        -_completion_callbacks: Dict[str, Callable]
        
        +__init__(process_manager: MNEProcessManagerInterface, result_storage: MNEResultStorageInterface) void
        +create_visualization_async(mne_data: Dict[str, Any], plot_type: str, freq_min: int, freq_max: int, bg_color: str, show_individual_channels: bool, selected_channels_for_display: Optional[List[int]], topomap_freq_range: Optional[Tuple[int, int]], callback: Optional[Callable]) str
        +get_visualization_status(task_id: str) Dict[str, Any]
        +cancel_visualization(task_id: str) bool
        -_handle_visualization_complete(task_id: str, result: Dict[str, Any], callback: Optional[Callable]) void
    }
    
    class MNERealtimeService {
        <<mne realtime service>>
        +converter_service: MNEConverterInterface
        +visualizer_service: MNEVisualizerInterface
        +result_storage: MNEResultStorageInterface
        +data_service: DataAccessService
        -_active_sessions: Dict[str, Dict[str, Any]]
        -_session_threads: Dict[str, threading.Thread]
        -_session_stop_events: Dict[str, threading.Event]
        -_session_lock: threading.RLock
        
        +__init__(converter_service: MNEConverterInterface, visualizer_service: MNEVisualizerInterface, result_storage: MNEResultStorageInterface) void
        +start_realtime_processing(update_interval_seconds: float, plot_type: str, duration_seconds: int, convert_to_v: bool, selected_channels: Optional[List[int]], visualization_params: Optional[Dict[str, Any]], callback: Optional[Callable], use_filters: bool, filter_settings: Optional[Dict[str, Any]], processor_service: Optional[Any], use_raw_data: bool) str
        +stop_realtime_processing(session_id: str) bool
        +update_realtime_params(session_id: str, params: Dict[str, Any]) bool
        +update_channels(session_id: str, selected_channels: List[int]) bool
        +update_visualization_params(session_id: str, viz_params: Dict[str, Any]) bool
        +update_plot_type(session_id: str, plot_type: str) bool
        +get_realtime_status(session_id: str) Dict[str, Any]
        +is_realtime_active(session_id: str) bool
        +cleanup_all_sessions() void
        +get_all_active_sessions() List[str]
        -_realtime_processing_loop(session_id: str, stop_event: threading.Event) void
        -_cleanup_session(session_id: str) void
    }
    
    class MNEProcessManager {
        <<multiprocess manager>>
        -_process_pool: Optional[multiprocessing.Pool]
        -_active_tasks: Dict[str, multiprocessing.pool.AsyncResult]
        -_task_lock: threading.RLock
        
        +__init__() void
        +start_service() void
        +stop_service() void
        +submit_task(worker_func: Callable[..., Any], *args: Any, task_id: Optional[str], **kwargs: Any) str
        +get_task_status(task_id: str) Dict[str, Any]
        +cancel_task(task_id: str) bool
        +is_available() bool
        +cleanup_completed_tasks() void
    }
    
    class MNEResultStorage {
        <<thread-safe storage>>
        -_results: Dict[str, Any]
        -_lock: threading.RLock
        
        +__init__() void
        +store_result(task_id: str, result: Dict[str, Any]) void
        +get_result(task_id: str) Optional[Dict[str, Any]]
        +remove_result(task_id: str) bool
        +clear_all_results() void
        +get_all_task_ids() List[str]
    }
    
    class MNEServicesPackage {
        <<module package>>
        +MNEConverterService: Class
        +MNEVisualizerService: Class
        +MNERealtimeService: Class
        +MNEProcessManager: Class
        +MNEResultStorage: Class
    }
    
    %% ================================================================================
    %% WORKER PROCESS FUNCTIONS
    %% ================================================================================
    
    class MNEWorkerFunctions {
        <<worker processes>>
        +_convert_to_mne_worker(data: np.ndarray, metadata: Dict[str, Any], duration_seconds: int, convert_to_v: bool, selected_channels: Optional[List[int]])$ Dict[str, Any]
        +_create_visualization_worker(raw_data: np.ndarray, info: Any, plot_type: str, freq_min: int, freq_max: int, bg_color: str, show_individual_channels: bool, selected_channels_for_display: Optional[List[int]], topomap_freq_range: Optional[Tuple[int, int]])$ Dict[str, Any]
        +_get_band_name(freq_min: int, freq_max: int)$ str
        +_mne_worker_init()$ void
    }
    
    %% ================================================================================
    %% MNE INTERFACES
    %% ================================================================================
    
    class MNEConverterInterface {
        <<interface>>
        +convert_to_mne_async(data: np.ndarray, metadata: Dict[str, Any], duration_seconds: int, convert_to_v: bool, selected_channels: Optional[List[int]], callback: Optional[Callable]) str
        +get_conversion_status(task_id: str) Dict[str, Any]
        +cancel_conversion(task_id: str) bool
    }
    
    class MNEVisualizerInterface {
        <<interface>>
        +create_visualization_async(mne_data: Dict[str, Any], plot_type: str, freq_min: int, freq_max: int, bg_color: str, show_individual_channels: bool, selected_channels_for_display: Optional[List[int]], topomap_freq_range: Optional[Tuple[int, int]], callback: Optional[Callable]) str
        +get_visualization_status(task_id: str) Dict[str, Any]
        +cancel_visualization(task_id: str) bool
    }
    
    class MNERealtimeInterface {
        <<interface>>
        +start_realtime_processing(update_interval_seconds: float, plot_type: str, duration_seconds: int, convert_to_v: bool, selected_channels: Optional[List[int]], visualization_params: Optional[Dict[str, Any]], callback: Optional[Callable], use_filters: bool, filter_settings: Optional[Dict[str, Any]], processor_service: Optional[Any], use_raw_data: bool) str
        +stop_realtime_processing(session_id: str) bool
        +get_realtime_status(session_id: str) Dict[str, Any]
    }
    
    class MNEProcessManagerInterface {
        <<interface>>
        +submit_task(worker_func: Callable[..., Any], *args: Any, task_id: Optional[str], **kwargs: Any) str
        +get_task_status(task_id: str) Dict[str, Any]
        +cancel_task(task_id: str) bool
        +is_available() bool
    }
    
    class MNEResultStorageInterface {
        <<interface>>
        +store_result(task_id: str, result: Dict[str, Any]) void
        +get_result(task_id: str) Optional[Dict[str, Any]]
        +remove_result(task_id: str) bool
    }
    
    %% ================================================================================
    %% EXTERNAL DEPENDENCIES
    %% ================================================================================
    
    class DataAccessService {
        <<external service>>
        +get_instance()$ DataAccessService
        +get_current_data() Tuple[np.ndarray, List[int]]
        +get_raw_data() Tuple[np.ndarray, List[int]]
        +get_metadata() Dict[str, Any]
    }
    
    %% ================================================================================
    %% MNE-PYTHON COMPONENTS
    %% ================================================================================
    
    class mne {
        <<mne-python library>>
        +create_info(ch_names: List[str], sfreq: float, ch_types: List[str]) Info
        +io: module
    }
    
    class mne_io {
        <<mne-python io>>
        +RawArray(data: np.ndarray, info: Info) Raw
    }
    
    class Info {
        <<mne-python>>
        +ch_names: List[str]
        +sfreq: float
        +ch_types: List[str]
    }
    
    class Raw {
        <<mne-python>>
        +get_data() np.ndarray
        +times: np.ndarray
        +pick_channels(ch_names: List[str], ordered: bool) Raw
        +compute_psd(fmin: float, fmax: float, method: str) PSD
    }
    
    class PSD {
        <<mne-python>>
        +get_data() np.ndarray
        +freqs: np.ndarray
        +plot(axes: Axes, show: bool, average: bool, color: str, alpha: float, spatial_colors: bool) Figure
    }
    
    %% ================================================================================
    %% MATPLOTLIB COMPONENTS
    %% ================================================================================
    
    class matplotlib {
        <<plotting library>>
        +use(backend: str) void
        +rcParams: Dict[str, Any]
        +rcParamsDefault: Dict[str, Any]
    }
    
    class pyplot {
        <<matplotlib>>
        +style: module
        +subplots(nrows: int, ncols: int, figsize: Tuple[float, float], facecolor: str) Tuple[Figure, Axes]
        +tight_layout(pad: float) void
        +close(fig: Figure) void
        +Circle(xy: Tuple[float, float], radius: float, color: Any, alpha: float) Patch
        +cm: module
    }
    
    class Figure {
        <<matplotlib>>
        +clear() void
        +suptitle(title: str, color: str, fontweight: str, fontsize: int) void
        +savefig(filename: str, format: str, facecolor: str, edgecolor: str, bbox_inches: str, dpi: int, pad_inches: float) void
        +colorbar(mappable: Any, ax: Axes, shrink: float) Colorbar
    }
    
    class Axes {
        <<matplotlib>>
        +clear() void
        +set_facecolor(color: str) void
        +plot(x: np.ndarray, y: np.ndarray, label: str, color: str, linewidth: float, alpha: float) List[Line2D]
        +pcolormesh(x: np.ndarray, y: np.ndarray, z: np.ndarray, cmap: str) QuadMesh
        +add_patch(patch: Patch) void
        +text(x: float, y: float, s: str, ha: str, va: str, transform: Any, color: str, fontsize: int, bbox: Dict[str, Any]) Text
        +set_title(label: str, color: str, fontweight: str, pad: float) void
        +set_xlabel(xlabel: str, color: str, fontweight: str) void
        +set_ylabel(ylabel: str, color: str, fontweight: str) void
        +set_xlim(left: float, right: float) void
        +set_ylim(bottom: float, top: float) void
        +set_xticks(ticks: List[float]) void
        +set_yticks(ticks: List[float]) void
        +set_aspect(aspect: str) void
        +grid(visible: bool, alpha: float, color: str, linestyle: str, linewidth: float) void
        +tick_params(colors: str, which: str, labelsize: int) void
        +legend(loc: str, fancybox: bool, shadow: bool, framealpha: float, facecolor: str, edgecolor: str, fontsize: int, ncol: int) Legend
        +axis(option: str) void
    }
    
    class colormap_module {
        <<matplotlib.cm>>
        +get_cmap(name: str) Colormap
        +tab20$: Colormap
        +viridis$: Colormap
        +plasma$: Colormap
    }
    
    %% ================================================================================
    %% SCIPY COMPONENTS
    %% ================================================================================
    
    class scipy_signal {
        <<scipy library>>
        +spectrogram(x: np.ndarray, fs: float) Tuple[np.ndarray, np.ndarray, np.ndarray]
        +welch(x: np.ndarray, fs: float, nperseg: int) Tuple[np.ndarray, np.ndarray]
    }
    
    %% ================================================================================
    %% MULTIPROCESSING COMPONENTS
    %% ================================================================================
    
    class multiprocessing {
        <<stdlib>>
        +Pool: Class
        +pool: module
    }
    
    class Pool {
        <<multiprocessing>>
        +processes: int
        +initializer: Callable
        +apply_async(func: Callable, args: Tuple[Any, ...], kwds: Dict[str, Any], callback: Optional[Callable]) AsyncResult
        +terminate() void
        +join() void
    }
    
    class AsyncResult {
        <<multiprocessing.pool>>
        +ready() bool
        +successful() bool
        +get(timeout: Optional[float]) Any
    }
    
    %% ================================================================================
    %% THREADING COMPONENTS
    %% ================================================================================
    
    class threading {
        <<stdlib>>
        +Thread: Class
        +Event: Class
        +RLock: Class
    }
    
    class Thread {
        <<threading>>
        +target: Callable
        +args: Tuple[Any, ...]
        +daemon: bool
        +name: str
        +start() void
        +join(timeout: Optional[float]) void
        +is_alive() bool
    }
    
    class Event {
        <<threading>>
        +set() void
        +is_set() bool
        +wait(timeout: Optional[float]) bool
        +clear() void
    }
    
    class RLock {
        <<threading>>
        +acquire(blocking: bool) bool
        +release() void
        +__enter__() RLock
        +__exit__(exc_type: Any, exc_val: Any, exc_tb: Any) void
    }
    
    %% ================================================================================
    %% IMAGE AND DATA PROCESSING
    %% ================================================================================
    
    class BytesIO {
        <<io>>
        +seek(pos: int) int
        +read() bytes
        +close() void
    }
    
    class base64 {
        <<stdlib>>
        +b64encode(data: bytes) bytes
    }
    
    class numpy {
        <<stdlib>>
        +ndarray: Class
        +mean(data: ndarray) float
        +std(data: ndarray) float
        +ptp(data: ndarray) float
        +log10(data: ndarray) ndarray
        +ceil(x: float) int
        +sqrt(x: float) float
        +linspace(start: float, stop: float, num: int) ndarray
        +copy(data: ndarray) ndarray
        +max(data: ndarray) float
        +min(data: ndarray) float
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
        +sleep(seconds: float) void
    }
    
    class signal {
        <<stdlib>>
        +signal(sig: int, handler: Callable) void
        +SIGINT$: int
        +SIG_IGN$: Callable
    }
    
    class typing {
        <<stdlib>>
        +Dict
        +List
        +Optional
        +Callable
        +Any
        +Tuple
    }
    
    %% ================================================================================
    %% RELATIONSHIPS
    %% ================================================================================
    
    %% Package Composition
    MNEServicesPackage "1" *-- "1" MNEConverterService : contains
    MNEServicesPackage "1" *-- "1" MNEVisualizerService : contains
    MNEServicesPackage "1" *-- "1" MNERealtimeService : contains
    MNEServicesPackage "1" *-- "1" MNEProcessManager : contains
    MNEServicesPackage "1" *-- "1" MNEResultStorage : contains
    
    %% Interface Implementation
    MNEConverterService ..|> MNEConverterInterface : implements
    MNEVisualizerService ..|> MNEVisualizerInterface : implements
    MNERealtimeService ..|> MNERealtimeInterface : implements
    MNEProcessManager ..|> MNEProcessManagerInterface : implements
    MNEResultStorage ..|> MNEResultStorageInterface : implements
    
    %% Service Dependencies
    MNEConverterService "1" o-- "1" MNEProcessManagerInterface : process_manager
    MNEConverterService "1" o-- "1" MNEResultStorageInterface : result_storage
    
    MNEVisualizerService "1" o-- "1" MNEProcessManagerInterface : process_manager
    MNEVisualizerService "1" o-- "1" MNEResultStorageInterface : result_storage
    
    MNERealtimeService "1" o-- "1" MNEConverterInterface : converter_service
    MNERealtimeService "1" o-- "1" MNEVisualizerInterface : visualizer_service
    MNERealtimeService "1" o-- "1" MNEResultStorageInterface : result_storage
    MNERealtimeService "1" o-- "1" DataAccessService : data_service
    
    %% Internal Component Relationships
    MNEProcessManager "1" *-- "0..1" Pool : _process_pool
    MNEProcessManager "1" *-- "*" AsyncResult : _active_tasks
    MNEProcessManager "1" *-- "1" RLock : _task_lock
    
    MNEResultStorage "1" *-- "1" RLock : _lock
    
    MNERealtimeService "1" *-- "*" Thread : _session_threads
    MNERealtimeService "1" *-- "*" Event : _session_stop_events
    MNERealtimeService "1" *-- "1" RLock : _session_lock
    
    %% Worker Function Dependencies
    MNEConverterService ..> MNEWorkerFunctions : uses _convert_to_mne_worker
    MNEVisualizerService ..> MNEWorkerFunctions : uses _create_visualization_worker
    MNEProcessManager ..> MNEWorkerFunctions : uses _mne_worker_init
    
    %% MNE-Python Dependencies
    MNEWorkerFunctions ..> mne : uses
    MNEWorkerFunctions ..> mne_io : uses
    MNEWorkerFunctions ..> Info : creates
    MNEWorkerFunctions ..> Raw : creates
    MNEWorkerFunctions ..> PSD : uses
    
    %% Matplotlib Dependencies
    MNEWorkerFunctions ..> matplotlib : configures
    MNEWorkerFunctions ..> pyplot : uses
    MNEWorkerFunctions ..> Figure : creates
    MNEWorkerFunctions ..> Axes : manipulates
    MNEWorkerFunctions ..> colormap_module : uses
    
    %% Scipy Dependencies
    MNEWorkerFunctions ..> scipy_signal : uses
    
    %% Multiprocessing Dependencies
    MNEProcessManager ..> multiprocessing : uses
    MNEProcessManager ..> Pool : creates
    MNEProcessManager ..> AsyncResult : manages
    
    %% Threading Dependencies
    MNERealtimeService ..> threading : uses
    MNERealtimeService ..> Thread : creates
    MNERealtimeService ..> Event : creates
    MNEResultStorage ..> threading : uses
    MNEProcessManager ..> threading : uses
    
    %% Data Processing Dependencies
    MNEWorkerFunctions ..> BytesIO : uses
    MNEWorkerFunctions ..> base64 : uses
    MNEWorkerFunctions ..> numpy : uses
    
    %% Standard Library Dependencies
    MNEConverterService ..> logging : uses
    MNEVisualizerService ..> logging : uses
    MNERealtimeService ..> logging : uses
    MNEProcessManager ..> logging : uses
    MNEResultStorage ..> logging : uses
    MNERealtimeService ..> time : uses
    MNEConverterService ..> time : uses
    MNEVisualizerService ..> time : uses
    MNEWorkerFunctions ..> signal : uses
    
    %% Type Hints
    MNEConverterService ..> typing : uses
    MNEVisualizerService ..> typing : uses
    MNERealtimeService ..> typing : uses
    MNEProcessManager ..> typing : uses
    MNEResultStorage ..> typing : uses
    
    %% ================================================================================
    %% LOGICAL GROUPINGS
    %% ================================================================================
    
    %% Core MNE Services
    MNEConverterService -.- MNEVisualizerService : "core mne services"
    MNEVisualizerService -.- MNERealtimeService : "core mne services"
    
    %% Infrastructure Services
    MNEProcessManager -.- MNEResultStorage : "infrastructure services"
    
    %% MNE-Python Components
    mne -.- mne_io : "mne-python framework"
    mne_io -.- Info : "mne-python framework"
    Info -.- Raw : "mne-python framework"
    Raw -.- PSD : "mne-python framework"
    
    %% Matplotlib Components
    matplotlib -.- pyplot : "plotting framework"
    pyplot -.- Figure : "plotting framework"
    Figure -.- Axes : "plotting framework"
    
    %% Multiprocessing Components
    multiprocessing -.- Pool : "multiprocessing framework"
    Pool -.- AsyncResult : "multiprocessing framework"
    
    %% Threading Components
    threading -.- Thread : "threading framework"
    Thread -.- Event : "threading framework"
    Event -.- RLock : "threading framework"
    
    %% Standard Library Components
    numpy -.- logging : "standard libraries"
    logging -.- time : "standard libraries"
    time -.- signal : "standard libraries"
    signal -.- typing : "standard libraries"
```