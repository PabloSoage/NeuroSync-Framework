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
    
    %% ================================================================================
    %% NOTES
    %% ================================================================================
    
    note for MNEConverterService "Asynchronous MNE Data Conversion Service:\n• Converts BrainFlow raw EEG data to MNE Raw objects with proper metadata\n• Channel selection optimization reducing conversion overhead (selected channels only)\n• Unit conversion support (µV to V) with automatic scaling validation\n• Asynchronous processing preventing GUI blocking during large dataset conversions\n• Proper EEG channel mapping with customizable channel naming conventions\n• Data validation ensuring sufficient duration and sampling rate requirements\n• Error handling with detailed logging for debugging and troubleshooting\n• Task ID management enabling multiple concurrent conversion operations\n• Callback support for completion notification and result handling"
    
    note for MNEVisualizerService "Advanced MNE Visualization Service:\n• Multiple plot types: PSD (individual/averaged), Spectrogram, Raw Data, Topomaps\n• High-quality output (200 DPI) with dark theme integration and professional styling\n• Customizable frequency ranges supporting standard EEG bands (Delta, Theta, Alpha, Beta, Gamma)\n• Channel-specific visualization with intelligent color coding and legend management\n• Base64 image encoding for seamless web/GUI integration without file I/O\n• Responsive layout with automatic scaling based on channel count and plot type\n• Statistical overlays and power spectral density integration for analysis\n• Topomap visualization with spatial power distribution for multiple channels\n• Matplotlib backend optimization for consistent rendering across platforms"
    
    note for MNERealtimeService "Real-Time MNE Processing Service:\n• Continuous processing sessions with configurable update intervals (0.5-30 seconds)\n• Dynamic parameter updates during active sessions without restart requirements\n• Performance monitoring with statistics tracking (processing time, efficiency, timeout count)\n• Channel selection optimization reducing computational load during real-time operations\n• Sliding window analysis with adaptive timeout management based on update frequency\n• Multiple concurrent session support with independent parameter configurations\n• Filter integration supporting both raw and pre-processed data modes\n• Memory-efficient processing with automatic result cleanup and session management\n• Thread-safe operations with proper synchronization and error isolation"
    
    note for MNEProcessManager "Multiprocess Task Management:\n• Dedicated process pool (2 workers) optimized for CPU-intensive MNE operations\n• Custom task ID support enabling precise task tracking and correlation\n• Process lifecycle management with proper initialization and cleanup procedures\n• Worker signal handling preventing interruption during critical operations\n• Task status monitoring with completion detection and error state tracking\n• Graceful shutdown procedures ensuring proper resource cleanup\n• Callback mechanism integration for asynchronous result notification\n• Exception isolation preventing worker process failures from affecting main application"
    
    note for MNEResultStorage "Thread-Safe Result Storage:\n• Atomic operations ensuring data consistency during concurrent access\n• Memory-efficient storage with automatic cleanup capabilities\n• Bulk operations supporting efficient result lifecycle management\n• Thread-safe operations using RLock preventing deadlocks and race conditions\n• Task ID indexing enabling fast result retrieval and management\n• Configurable storage limits preventing memory exhaustion\n• Debug logging for storage operations and memory usage monitoring"
    
    note "MNE-Python Integration Features:\n• Full MNE Raw object creation with proper Info structure and metadata\n• Channel type mapping (EEG) with standard neurophysiological conventions\n• Sampling rate preservation ensuring temporal accuracy\n• Data format compatibility with MNE analysis pipeline\n• Support for MNE visualization and analysis methods\n• Integration with MNE PSD computation using Welch's method\n• Proper handling of MNE coordinate systems and channel locations\n• Compatibility with MNE preprocessing and analysis workflows"
    
    note "Visualization Capabilities:\n• PSD Plots: Individual channel traces with distinct colors, averaged displays with error bands\n• Spectrograms: Time-frequency analysis for single channels with configurable resolution\n• Raw Data: Multi-channel time series with proper scaling and offset management\n• Topomaps: Spatial power distribution with frequency band selection (Delta-Gamma)\n• Custom styling: Dark theme integration, professional color schemes, high-DPI output\n• Dynamic legends: Adaptive based on channel count, collapsible for large datasets\n• Statistical overlays: Mean, standard deviation, min/max indicators for analysis"
    
    note "Real-Time Processing Architecture:\n• Session Management: Independent sessions with unique IDs and parameter sets\n• Performance Optimization: Channel selection reducing conversion and visualization overhead\n• Adaptive Timeouts: Based on update frequency and processing complexity\n• Memory Management: Automatic cleanup of old results and completed tasks\n• Error Recovery: Isolated error handling preventing cascade failures\n• Status Monitoring: Real-time performance metrics and efficiency tracking\n• Dynamic Updates: Parameter changes without session restart for flexibility\n• Thread Safety: Proper synchronization across multiple concurrent sessions"
    
    note "Worker Process Architecture:\n• Conversion Worker: BrainFlow to MNE data transformation with validation\n  - Metadata extraction and Info object creation\n  - Channel selection and naming convention application\n  - Unit conversion with automatic scaling validation\n  - Duration checking and sample count verification\n  - Error handling with detailed diagnostic information\n\n• Visualization Worker: MNE data to high-quality image generation\n  - Matplotlib configuration for headless operation\n  - Plot type routing with specialized rendering for each type\n  - Color scheme management and theme integration\n  - Legend optimization based on channel count\n  - Base64 encoding for web/GUI integration\n  - Memory cleanup and resource management"
```