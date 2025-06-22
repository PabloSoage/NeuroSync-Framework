```mermaid
classDiagram
    %% ================================================================================
    %% SERVICES MODULE - SERVICE-ORIENTED ARCHITECTURE FOR EEG PROCESSING
    %% ================================================================================
    
    %% ================================================================================
    %% CORE SERVICE CLASSES
    %% ================================================================================
    
    class CollectorService {
        <<singleton service>>
        -_instance$: Optional[CollectorService]
        -_lock$: threading.RLock
        +collector: Optional[EEGCollector]
        +is_streaming: bool
        -_data_thread: Optional[threading.Thread]
        -_stop_event: threading.Event
        -_sample_window_size: float
        -_samples_timestamps: Deque[float]
        -_last_sample_count: int
        -_current_sample_rate: float
        -_last_timestamp: float
        -_last_reported_time: float
        -_report_interval: float
        
        +get_instance()$ CollectorService
        +__init__() void
        +connect_to_board(board_id: int, params: Dict[str, Any], preset: int) bool
        +disconnect_from_board() bool
        +start_stream(buffer_size: int) bool
        +stop_stream() bool
        +get_board_data(num_samples: Optional[int]) Tuple[np.ndarray, List[int]]
        +get_board_info() Dict[str, Any]
        +insert_marker(marker_value: Union[int, float]) bool
        +set_processed_data(data: np.ndarray) bool
        +add_streamer(streamer_params: str) bool
        +remove_streamer(streamer_params: str) bool
        +get_eeg_channels() List[int]
        +get_channel_by_type(channel_type: str) List[int]
        +get_sampling_rate() int
        +config_device(config: str) str
        +set_preset(preset: int) bool
        +is_connected() bool
        +is_streaming_active() bool
        +get_current_sample_rate() float
        +cleanup() void
        -_data_loop() void
        -_update_sample_rate(current_time: float) void
        -_update_sample_metrics(data: np.ndarray, current_time: float) void
        -_is_streaming_board(board_id: int) bool
        -_get_master_board_info(master_board_id: int, preset: int) Optional[Dict[str, Any]]
    }
    
    class DataAccessService {
        <<singleton service>>
        -_instance$: Optional[DataAccessService]
        -_lock$: threading.Lock
        -_data_lock: threading.Lock
        -_metadata_lock: threading.Lock
        -_current_data: np.ndarray
        -_timestamps: List[int]
        -_buffer_max_samples: Optional[int]
        -_default_buffer_seconds: int
        -_collector_service: Optional[Any]
        -_metadata: Dict[str, Any]
        -_local_callbacks: List[Optional[Callable]]
        -_api_callbacks: List[Optional[Callable]]
        -_callback_lock: threading.Lock
        -_filter_settings: Optional[Dict[str, Any]]
        -_filters_enabled: bool
        -_processor_service: Optional[Any]
        -_use_api_multiprocessing: bool
        -_api_data_queue: Optional[mp.Queue]
        -_api_processed_queue: Optional[mp.Queue]
        -_api_process_pool: Optional[mp.pool.Pool]
        -_api_worker_thread: Optional[threading.Thread]
        -_api_stop_event: threading.Event
        -_advanced_processing_settings: Dict[str, Any]
        -_wavelet_coefficients: Optional[np.ndarray]
        -_wavelet_metadata: Optional[Dict[str, Any]]
        -_wavelet_target_channel: int
        
        +get_instance()$ DataAccessService
        +__init__() void
        +register_local_callback(callback: Callable[[np.ndarray, List[int]], None]) int
        +register_api_callback(callback: Callable[[np.ndarray, List[int]], None]) int
        +register_api_callback_direct(callback: Callable[[np.ndarray, List[int]], None]) int
        +unregister_local_callback(callback_id: int) bool
        +unregister_api_callback(callback_id: int) bool
        +set_filter_processor(processor_service: Any) void
        +enable_filters(enabled: bool, filter_settings: Optional[Dict[str, Any]]) void
        +update_filter_settings(filter_settings: Dict[str, Any]) void
        +enable_advanced_processing(enabled: bool, settings: Optional[Dict[str, Any]]) void
        +update_advanced_processing_settings(processing_settings: Dict[str, Any]) void
        +update_data(data: np.ndarray, timestamps: List[int]) void
        +update_metadata(metadata: Dict[str, Any]) void
        +get_current_data() Tuple[np.ndarray, List[int]]
        +get_raw_data() Tuple[np.ndarray, List[int]]
        +get_metadata() Dict[str, Any]
        +get_channel_data(channel_index: int) Tuple[np.ndarray, List[int]]
        +get_channel_names() List[str]
        +get_sampling_rate() float
        +is_streaming() bool
        +get_all_channels_quality() Dict[int, float]
        +register_callback(callback: Callable[[np.ndarray, List[int]], None]) int
        +unregister_callback(callback_id: int) bool
        -_init_collector_reference() void
        -_enable_api_multiprocessing() void
        -_disable_api_multiprocessing() void
        -_api_worker_init(data_queue: mp.Queue, processed_queue: mp.Queue)$ void
        -_process_api_data_chunk(data_package: Dict[str, Any])$ Dict[str, Any]
        -_api_result_handler() void
        -_apply_filters_if_enabled(data: np.ndarray) np.ndarray
        -_apply_advanced_processing(data: np.ndarray) np.ndarray
        -_notify_callbacks(data: np.ndarray, timestamps: List[int]) void
        -_notify_api_callbacks_direct(data: np.ndarray, timestamps: List[int]) void
        -_notify_api_callbacks_multiprocessing(data: np.ndarray, timestamps: List[int]) void
        -_update_metadata_from_collector(metadata: Dict[str, Any]) void
        -_get_active_collector() Optional[Any]
    }
    
    class ProcessorService {
        <<signal processing service>>
        +processor: Optional[SignalProcessor]
        +sampling_rate: int
        
        +__init__() void
        +initialize_processor(sampling_rate: int) void
        +apply_bandpass_filter(data: np.ndarray, low_cutoff: float, high_cutoff: float, channels: Optional[List[int]]) np.ndarray
        +apply_notch_filter(data: np.ndarray, notch_freq: float, channels: Optional[List[int]]) np.ndarray
        +apply_bandstop_filter(data: np.ndarray, low_cutoff: float, high_cutoff: float, channels: Optional[List[int]]) np.ndarray
        +apply_detrend(data: np.ndarray, channels: Optional[List[int]]) np.ndarray
        +apply_wavelet_denoising(data: np.ndarray, wavelet: WaveletTypes, channels: Optional[List[int]]) np.ndarray
        +apply_all_filters(data: np.ndarray, filters_config: Dict[str, Any]) np.ndarray
        +get_eeg_metrics(data: np.ndarray, eeg_channels: List[int]) Dict[str, Any]
        +perform_ica(data: np.ndarray, num_components: int) Tuple
        +perform_downsampling(data: np.ndarray, factor: int, operation: AggOperations) np.ndarray
        +apply_advanced_bandpass_filter(data: np.ndarray, low_cutoff: float, high_cutoff: float, filter_type: FilterTypes, order: int, channels: Optional[List[int]], ripple: float) np.ndarray
        +compute_wavelet_coefficients(data: np.ndarray, wavelet: WaveletTypes, decomposition_level: int) Tuple[np.ndarray, Dict[str, Any]]
        +apply_inverse_wavelet(coefficients: np.ndarray, metadata: Dict[str, Any]) np.ndarray
        -_get_eeg_channels_only() List[int]
    }
    
    class RecordingService {
        <<singleton service>>
        -_instance$: Optional[RecordingService]
        -_lock$: threading.RLock
        +recording: bool
        +start_time: float
        +filename: str
        +data_type: str
        +data_manager: RecordingDataManager
        
        +get_instance()$ RecordingService
        +__init__() void
        +start_recording(filename: str, data_type: str) bool
        +stop_recording() bool
        +insert_marker(marker_value: float) bool
        +is_recording() bool
        +get_recording_duration() float
        +get_recording_filename() str
        +get_recording_data_type() str
        +cleanup() void
        +start_continuous_recording(filename: str, data_type: str) void
        +stop_continuous_recording() void
        +save_data(filename: str, data_type: str) void
        +get_board_data_count() int
        +total_recorded_samples() int
    }
    
    class VisualizationService {
        <<visualization coordinator>>
        +eeg_visualizer: Optional[MultiSignalVisualizer]
        +brain_map_visualizer: Optional[BrainMapVisualizer]
        +visualization_active: bool
        +bandpass_enabled: bool
        +bandpass_low: float
        +bandpass_high: float
        +notch_enabled: bool
        +notch_freq: float
        +detrend_enabled: bool
        
        +__init__() void
        +create_eeg_visualizer(collector: Any, processor: Any) bool
        +create_brain_map_visualizer(collector: Any, processor: Any) bool
        +start_eeg_visualization() bool
        +stop_eeg_visualization() bool
        +destroy_eeg_visualizer() bool
        +start_brain_map_visualization() bool
        +stop_brain_map_visualization() bool
        +visualization_visible() bool
        +visualization_closed() bool
        +brain_map_visible() bool
        +brain_map_closed() bool
        +set_bandpass_filter(enabled: bool, low_cutoff: float, high_cutoff: float) bool
        +set_notch_filter(enabled: bool, frequency: float) bool
        +set_detrend(enabled: bool) bool
        +update_plots() bool
        +cleanup() void
        +are_filters_applied() bool
        +get_filter_settings() Dict[str, Any]
    }
    
    class InteractionService {
        <<singleton api bridge>>
        -_instance$: Optional[InteractionService]
        -_lock$: threading.RLock
        +event_dispatcher: EventDispatcher
        -_initialized: bool
        -_components: Dict[str, Any]
        -_last_status: Dict[str, Any]
        -_collector_service: Optional[CollectorService]
        -_processor_service: Optional[ProcessorService]
        -_recording_service: Optional[RecordingService]
        -_visualization_service: Optional[VisualizationService]
        -_data_access_service: Optional[DataAccessService]
        
        +get_instance()$ InteractionService
        +__init__() void
        +register_component(component_name: str, component: Any) void
        +get_component(component_name: str) Any
        +initialize(components: Optional[Dict[str, Any]]) bool
        +get_available_boards() List[Dict[str, Any]]
        +connect_to_board(board_id: int, params: Dict[str, Any], preset: int) Dict[str, Any]
        +disconnect_from_board() Dict[str, Any]
        +start_stream(buffer_size: int) Dict[str, Any]
        +stop_stream() Dict[str, Any]
        +add_streamer(streamer_params: str) Dict[str, Any]
        +remove_streamer(streamer_params: str) Dict[str, Any]
        +send_board_config(config_cmd: str) Dict[str, Any]
        +start_recording(filename: str, data_type: str) Dict[str, Any]
        +stop_recording() Dict[str, Any]
        +insert_marker(marker_value: float) Dict[str, Any]
        +apply_filters(filter_config: Dict[str, Any]) Dict[str, Any]
        +start_visualization(viz_type: str) Dict[str, Any]
        +stop_visualization(viz_type: str) Dict[str, Any]
        +perform_ica(num_components: int, selected_channels: Optional[List[int]]) Dict[str, Any]
        +view_ica_components(colormap: str) Dict[str, Any]
        +select_ica_channels(channel_indices: List[int]) Dict[str, Any]
        +get_eeg_metrics() Dict[str, Any]
        +get_system_status() Dict[str, Any]
        +config_device(config_cmd: str) Dict[str, Any]
        +save_current_data(filename: str, data_type: str) Dict[str, Any]
        +convert_to_mne(duration: int, use_filters: bool) Dict[str, Any]
        +plot_mne_visualization(plot_type: str, freq_min: int, freq_max: int, topomap_band: str, topomap_freq_min: int, topomap_freq_max: int, psd_individual_mode: bool, selected_channels: Optional[List[int]]) Dict[str, Any]
        +select_mne_channels(channel_indices: List[int]) Dict[str, Any]
        +compute_wavelet(wavelet_type: int, decomposition_level: int, channel: int, extension_type: int, apply_denoising: bool) Dict[str, Any]
        +apply_wavelet_inverse(channel: int, apply: bool) Dict[str, Any]
        +apply_downsampling(factor: int, aggregation_method: int, apply: bool) Dict[str, Any]
        +apply_advanced_filters(filter_type: int, order: int, window_function: int, selected_channels: Optional[List[int]], apply: bool) Dict[str, Any]
        +get_recording_status() Dict[str, Any]
        +cleanup() void
        +get_last_status() Dict[str, Any]
        -_auto_initialize() void
        -_set_status(success: bool, message: str) void
        -_check_initialized() bool
        -_get_collector_service() CollectorService
        -_get_processor_service() ProcessorService
        -_get_recording_service() RecordingService
        -_get_visualization_service() VisualizationService
        -_get_data_access_service() DataAccessService
        -_determine_streamer_type(streamer_params: str) str
        -_validate_streaming_board_preset() void
    }
    
    class AdvancedProcessingService {
        <<advanced analysis service>>
        -_data_access_service: DataAccessService
        -_processor_service: Optional[Any]
        -_ica_results: Optional[Dict[str, Any]]
        -_wavelet_results: Dict[str, Any]
        -_downsampling_active: bool
        -_advanced_filters_active: bool
        -_inverse_wavelet_active: bool
        
        +__init__() void
        +initialize(processor_service: Any) void
        +get_channel_names() List[str]
        +compute_ica(params: Dict[str, Any]) Dict[str, Any]
        +compute_wavelet(params: Dict[str, Any]) Dict[str, Any]
        +apply_wavelet_inverse(apply: bool) Dict[str, Any]
        +apply_downsampling(params: Dict[str, Any]) Dict[str, Any]
        +apply_advanced_filters(params: Dict[str, Any]) Dict[str, Any]
        +get_ica_results() Optional[Dict[str, Any]]
        +get_wavelet_results() Optional[Dict[str, Any]]
        +update_advanced_processing_settings(processing_type: str, new_settings: Dict[str, Any]) Dict[str, Any]
        +get_current_advanced_settings() Dict[str, Any]
        +cleanup() void
        -_ensure_processor_initialized() void
    }
    
    class MNEService {
        <<singleton mne facade>>
        -_instance$: Optional[MNEService]
        -_lock$: threading.RLock
        -_process_manager: MNEProcessManager
        -_result_storage: MNEResultStorage
        -_converter_service: MNEConverterService
        -_visualizer_service: MNEVisualizerService
        -_realtime_service: MNERealtimeService
        -_data_access_service: DataAccessService
        
        +get_instance()$ MNEService
        +__init__() void
        +is_available() bool
        +start_service() void
        +stop_service() void
        +cleanup() void
        +convert_to_mne_async(duration_seconds: int, convert_to_v: bool, selected_channels: Optional[List[int]], callback: Optional[Callable], data: Optional[np.ndarray], metadata: Optional[Dict[str, Any]], use_raw_data: bool) str
        +get_conversion_status(task_id: str) Dict[str, Any]
        +cancel_conversion(task_id: str) bool
        +create_visualization_async(task_id: str, plot_type: str, freq_min: int, freq_max: int, bg_color: str, show_individual_channels: bool, selected_channels_for_display: Optional[List[int]], topomap_freq_range: Optional[Tuple[int, int]], callback: Optional[Callable]) str
        +get_visualization_status(task_id: str) Dict[str, Any]
        +cancel_visualization(task_id: str) bool
        +start_realtime_processing(update_interval_seconds: float, plot_type: str, duration_seconds: int, convert_to_v: bool, selected_channels: Optional[List[int]], visualization_params: Optional[Dict[str, Any]], callback: Optional[Callable], use_filters: bool, filter_settings: Optional[Dict[str, Any]], processor_service: Optional[Any], use_raw_data: bool) str
        +stop_realtime_processing(session_id: str) bool
        +update_realtime_params(session_id: str, params: Dict[str, Any]) bool
        +get_realtime_status(session_id: str) Dict[str, Any]
        +is_realtime_active(session_id: str) bool
        +get_all_realtime_sessions() List[str]
        +update_realtime_visualization_params(session_id: str, viz_params: Dict[str, Any]) bool
        +update_realtime_channels(session_id: str, selected_channels: List[int]) bool
        +update_realtime_plot_type(session_id: str, plot_type: str) bool
        +update_realtime_interval(session_id: str, interval_seconds: float) bool
        +get_task_status(task_id: str) Dict[str, Any]
        +cancel_task(task_id: str) bool
        +get_result(task_id: str) Optional[Dict[str, Any]]
        +remove_result(task_id: str) bool
        +clear_all_results() void
        +get_service_status() Dict[str, Any]
        +convert_to_mne(data: Any, metadata: Dict[str, Any], duration_seconds: int, convert_to_v: bool, selected_channels: Optional[List[int]]) Dict[str, Any]
        +converter_service() MNEConverterInterface
        +visualizer_service() MNEVisualizerInterface
        +process_manager() MNEProcessManagerInterface
        +result_storage() MNEResultStorageInterface
        +realtime_service() MNERealtimeInterface
    }
    
    class ServicesPackage {
        <<module package>>
        +CollectorService: Class
        +DataAccessService: Class
        +ProcessorService: Class
        +RecordingService: Class
        +VisualizationService: Class
        +InteractionService: Class
        +AdvancedProcessingService: Class
        +MNEService: Class
        +ica: module
        +mne: module
    }
    
    %% ================================================================================
    %% SPECIALIZED SERVICE PACKAGES
    %% ================================================================================
    
    class ICAServicesPackage {
        <<specialized services>>
        +ICAProcessService: Class
        +ICARealtimeService: Class
        +ExportService: Class
    }
    
    class MNEServicesPackage {
        <<specialized services>>
        +MNEConverterService: Class
        +MNEVisualizerService: Class
        +MNERealtimeService: Class
        +MNEProcessManager: Class
        +MNEResultStorage: Class
    }
    
    %% ================================================================================
    %% SUPPORTING CLASSES
    %% ================================================================================
    
    class RecordingDataManager {
        <<data manager>>
        +recording_service: RecordingService
        +recording: bool
        +recording_file: Optional[Any]
        +processed_recording_file: Optional[Any]
        +total_recorded_samples: int
        +recording_start_time: float
        +data_type: str
        +is_recording_both: bool
        +data_callback_id: Optional[int]
        
        +__init__(recording_service: RecordingService) void
        +start_recording(filename: str, data_type: str) void
        +stop_recording() void
        +insert_marker(marker_value: float) bool
        -_on_new_data(data: np.ndarray, timestamps: List[int]) void
        -_start_file_recording(filename: str, data_type: str, collector: Any) void
        -_write_data_to_file(data: np.ndarray, data_type: str) void
        -_finalize_recording_file(file_handle: Any, recording_duration: float) void
    }
    
    class RecordingFileWriter {
        <<file writer>>
        +collector: Any
        
        +__init__(collector: Any) void
        +write_to_file(filename: str, data: Any, data_type: str) void
        +generate_column_names() List[str]
    }
    
    %% ================================================================================
    %% EXTERNAL DEPENDENCIES
    %% ================================================================================
    
    class EEGCollector {
        <<external collector>>
        +board_id: int
        +sampling_rate: int
        +eeg_channels: List[int]
        +device_name: str
        +preset: int
        
        +prepare_session() void
        +release_session() void
        +start_stream(buffer_size: int) void
        +stop_stream() void
        +get_data(num_samples: Optional[int]) Tuple[np.ndarray, List[int]]
        +get_board_data_count() int
        +get_device_info() Dict[str, Any]
        +get_board_info() Dict[str, Any]
        +insert_marker(marker_value: Union[int, float]) void
        +set_processed_data(data: np.ndarray) void
        +add_streamer(streamer_params: str) void
        +delete_streamer(streamer_params: str) void
        +get_eeg_channels() List[int]
        +get_channel_by_type(channel_type: str) List[int]
        +config_device(config: str) str
        +set_preset(preset: int) bool
        +is_streaming() bool
    }
    
    class SignalProcessor {
        <<external processor>>
        +sampling_rate: float
        
        +bandpass_filter(data: np.ndarray, start_freq: float, stop_freq: float, order: int, filter_type: FilterTypes, ripple: float) np.ndarray
        +bandstop_filter(data: np.ndarray, start_freq: float, stop_freq: float, order: int, filter_type: FilterTypes) np.ndarray
        +remove_environmental_noise(data: np.ndarray) np.ndarray
        +detrend(data: np.ndarray) np.ndarray
        +denoise(data: np.ndarray, wavelet: WaveletTypes) np.ndarray
        +get_eeg_metrics(data: np.ndarray, eeg_channels: List[int]) Dict[str, Any]
        +perform_ica(data: np.ndarray, num_components: int) Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
        +perform_downsampling(data: np.ndarray, factor: int, operation: AggOperations) np.ndarray
        +perform_advanced_bandpass_filter(data: np.ndarray, low_cutoff: float, high_cutoff: float, order: int, filter_type: FilterTypes, ripple: float) np.ndarray
        +get_wavelet_coefficients(data: np.ndarray, wavelet: WaveletTypes, decomposition_level: int, extension_type: int, apply_denoising: bool) Tuple[np.ndarray, Dict[str, Any]]
        +apply_inverse_wavelet_transform(coefficients: np.ndarray, metadata: Dict[str, Any]) np.ndarray
        +get_signal_quality(data: np.ndarray, channel: int, gain: int) float
    }
    
    class MultiSignalVisualizer {
        <<external visualizer>>
        +collector: Any
        +processor: Any
        +main_widget: Any
        
        +start() void
        +stop() void
        +is_visible() bool
        +update_plots() void
        +cleanup_for_disconnect() void
        +_clear_cache()$ void
    }
    
    class BrainMapVisualizer {
        <<external visualizer>>
        +collector: Any
        +processor: Any
        
        +start() void
        +close() void
        +is_visible() bool
        +visualization_closed() bool
    }
    
    class BoardConfiguration {
        <<external config>>
        +get_all_boards()$ List[Tuple[str, int]]
        +create_input_params(board_id: int, params: Dict[str, Any])$ Any
    }
    
    class EventDispatcher {
        <<external event system>>
        +get_instance()$ EventDispatcher
        +dispatch(event: Event) void
        +subscribe(event_type: EventType, callback: Callable) void
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
    
    class WaveletTypes {
        <<brainflow enum>>
        +DB4$: WaveletTypes
        +DAUBECHIES_4$: WaveletTypes
        +HAAR$: WaveletTypes
        +value: int
    }
    
    class AggOperations {
        <<brainflow enum>>
        +MEAN$: AggOperations
        +MEDIAN$: AggOperations
        +EACH$: AggOperations
        +value: int
    }
    
    %% ================================================================================
    %% MULTIPROCESSING COMPONENTS
    %% ================================================================================
    
    class multiprocessing {
        <<stdlib>>
        +Process: Class
        +Queue: Class
        +Pool: Class
        +cpu_count() int
    }
    
    class mp_Queue {
        <<multiprocessing>>
        +put(item: Any) void
        +get() Any
        +get_nowait() Any
        +empty() bool
        +full() bool
    }
    
    class mp_Pool {
        <<multiprocessing.pool>>
        +processes: int
        +apply_async(func: Callable, args: Tuple[Any, ...]) AsyncResult
        +terminate() void
        +join() void
    }
    
    class queue {
        <<stdlib>>
        +Empty: Exception
        +Full: Exception
    }
    
    %% ================================================================================
    %% THREADING COMPONENTS
    %% ================================================================================
    
    class threading {
        <<stdlib>>
        +Thread: Class
        +Event: Class
        +Lock: Class
        +RLock: Class
        +main_thread() Thread
    }
    
    class Thread {
        <<threading>>
        +target: Callable
        +args: Tuple[Any, ...]
        +daemon: bool
        +start() void
        +join(timeout: Optional[float]) void
        +is_alive() bool
    }
    
    class Event {
        <<threading>>
        +set() void
        +clear() void
        +is_set() bool
        +wait(timeout: Optional[float]) bool
    }
    
    class Lock {
        <<threading>>
        +acquire(blocking: bool) bool
        +release() void
        +__enter__() Lock
        +__exit__(exc_type: Any, exc_val: Any, exc_tb: Any) void
    }
    
    class RLock {
        <<threading>>
        +acquire(blocking: bool) bool
        +release() void
        +__enter__() RLock
        +__exit__(exc_type: Any, exc_val: Any, exc_tb: Any) void
    }
    
    %% ================================================================================
    %% STANDARD LIBRARY COMPONENTS
    %% ================================================================================
    
    class collections {
        <<stdlib>>
        +deque: Class
    }
    
    class Deque {
        <<collections>>
        +maxlen: Optional[int]
        +append(item: Any) void
        +clear() void
        +__len__() int
    }
    
    class numpy {
        <<stdlib>>
        +ndarray: Class
        +zeros(shape: Tuple[int, ...]) ndarray
        +concatenate(arrays: Tuple[ndarray, ...], axis: int) ndarray
        +array_equal(a: ndarray, b: ndarray) bool
        +copy(data: ndarray) ndarray
    }
    
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
        +strftime(format: str) str
    }
    
    class os {
        <<stdlib>>
        +makedirs(path: str, exist_ok: bool) void
        +path: module
        +getcwd() str
    }
    
    class typing {
        <<stdlib>>
        +Dict
        +List
        +Optional
        +Any
        +Tuple
        +Union
        +Callable
        +TYPE_CHECKING: bool
    }
    
    %% ================================================================================
    %% RELATIONSHIPS
    %% ================================================================================
    
    %% Package Composition
    ServicesPackage "1" *-- "1" CollectorService : contains
    ServicesPackage "1" *-- "1" DataAccessService : contains
    ServicesPackage "1" *-- "1" ProcessorService : contains
    ServicesPackage "1" *-- "1" RecordingService : contains
    ServicesPackage "1" *-- "1" VisualizationService : contains
    ServicesPackage "1" *-- "1" InteractionService : contains
    ServicesPackage "1" *-- "1" AdvancedProcessingService : contains
    ServicesPackage "1" *-- "1" MNEService : contains
    ServicesPackage "1" *-- "1" ICAServicesPackage : contains
    ServicesPackage "1" *-- "1" MNEServicesPackage : contains
    
    %% Core Service Relationships
    CollectorService "1" o-- "0..1" EEGCollector : collector
    CollectorService "1" *-- "0..1" Thread : _data_thread
    CollectorService "1" *-- "1" Event : _stop_event
    CollectorService "1" *-- "1" Deque : _samples_timestamps
    
    DataAccessService "1" o-- "0..1" CollectorService : _collector_service
    DataAccessService "1" o-- "0..1" ProcessorService : _processor_service
    DataAccessService "1" *-- "1" Lock : _data_lock
    DataAccessService "1" *-- "1" Lock : _metadata_lock
    DataAccessService "1" *-- "1" Lock : _callback_lock
    DataAccessService "1" *-- "0..1" mp_Queue : _api_data_queue
    DataAccessService "1" *-- "0..1" mp_Queue : _api_processed_queue
    DataAccessService "1" *-- "0..1" mp_Pool : _api_process_pool
    DataAccessService "1" *-- "0..1" Thread : _api_worker_thread
    DataAccessService "1" *-- "1" Event : _api_stop_event
    
    ProcessorService "1" o-- "0..1" SignalProcessor : processor
    
    RecordingService "1" *-- "1" RecordingDataManager : data_manager
    RecordingDataManager "1" o-- "1" RecordingService : recording_service
    
    VisualizationService "1" o-- "0..1" MultiSignalVisualizer : eeg_visualizer
    VisualizationService "1" o-- "0..1" BrainMapVisualizer : brain_map_visualizer
    
    InteractionService "1" *-- "1" EventDispatcher : event_dispatcher
    InteractionService "1" o-- "0..1" CollectorService : _collector_service
    InteractionService "1" o-- "0..1" ProcessorService : _processor_service
    InteractionService "1" o-- "0..1" RecordingService : _recording_service
    InteractionService "1" o-- "0..1" VisualizationService : _visualization_service
    InteractionService "1" o-- "0..1" DataAccessService : _data_access_service
    
    AdvancedProcessingService "1" o-- "1" DataAccessService : _data_access_service
    AdvancedProcessingService "1" o-- "0..1" ProcessorService : _processor_service
    
    MNEService "1" *-- "1" MNEServicesPackage : contains specialized services
    
    %% Supporting Class Relationships
    RecordingService "1" o-- "1" RecordingFileWriter : uses
    RecordingFileWriter "1" o-- "1" EEGCollector : collector
    
    %% External Dependencies
    CollectorService ..> BoardConfiguration : uses
    CollectorService ..> DataAccessService : updates
    
    ProcessorService ..> SignalProcessor : uses
    ProcessorService ..> FilterTypes : uses
    ProcessorService ..> WaveletTypes : uses
    ProcessorService ..> AggOperations : uses
    
    VisualizationService ..> MultiSignalVisualizer : creates
    VisualizationService ..> BrainMapVisualizer : creates
    
    InteractionService ..> BoardConfiguration : uses
    InteractionService ..> EventDispatcher : uses
    
    %% Multiprocessing Dependencies
    DataAccessService ..> multiprocessing : uses
    DataAccessService ..> mp_Queue : creates
    DataAccessService ..> mp_Pool : creates
    DataAccessService ..> queue : handles exceptions
    
    %% Threading Dependencies
    CollectorService ..> threading : uses
    CollectorService ..> Thread : creates
    CollectorService ..> Event : creates
    
    DataAccessService ..> threading : uses
    DataAccessService ..> Thread : creates
    DataAccessService ..> Lock : creates
    DataAccessService ..> Event : creates
    
    InteractionService ..> threading : uses
    InteractionService ..> RLock : uses
    
    RecordingService ..> threading : uses
    RecordingService ..> RLock : uses
    
    MNEService ..> threading : uses
    MNEService ..> RLock : uses
    
    %% Standard Library Dependencies
    CollectorService ..> collections : uses
    CollectorService ..> Deque : creates
    CollectorService ..> numpy : uses
    CollectorService ..> logging : uses
    CollectorService ..> time : uses
    
    DataAccessService ..> numpy : uses
    DataAccessService ..> logging : uses
    DataAccessService ..> time : uses
    
    RecordingService ..> numpy : uses
    RecordingService ..> logging : uses
    RecordingService ..> time : uses
    RecordingService ..> os : uses
    
    %% Type Hints
    CollectorService ..> typing : uses
    DataAccessService ..> typing : uses
    ProcessorService ..> typing : uses
    RecordingService ..> typing : uses
    VisualizationService ..> typing : uses
    InteractionService ..> typing : uses
    AdvancedProcessingService ..> typing : uses
    MNEService ..> typing : uses
    
    %% ================================================================================
    %% LOGICAL GROUPINGS
    %% ================================================================================
    
    %% Core Services
    CollectorService -.- DataAccessService : "data pipeline"
    DataAccessService -.- ProcessorService : "data pipeline"
    ProcessorService -.- RecordingService : "data pipeline"
    
    %% User Interface Services
    VisualizationService -.- InteractionService : "ui coordination"
    
    %% Advanced Analysis Services
    AdvancedProcessingService -.- MNEService : "advanced analysis"
    
    %% Specialized Service Packages
    ICAServicesPackage -.- MNEServicesPackage : "specialized analysis"
    
    %% Threading Components
    threading -.- Thread : "concurrency framework"
    Thread -.- Event : "concurrency framework"
    Event -.- Lock : "concurrency framework"
    Lock -.- RLock : "concurrency framework"
    
    %% Multiprocessing Components
    multiprocessing -.- mp_Queue : "multiprocessing framework"
    mp_Queue -.- mp_Pool : "multiprocessing framework"
    
    %% BrainFlow Components
    FilterTypes -.- WaveletTypes : "brainflow enums"
    WaveletTypes -.- AggOperations : "brainflow enums"
    
    %% Standard Library Components
    numpy -.- logging : "standard libraries"
    logging -.- time : "standard libraries"
    time -.- os : "standard libraries"
    os -.- collections : "standard libraries"
    collections -.- typing : "standard libraries"
    
    %% ================================================================================
    %% NOTES
    %% ================================================================================
    
    note for CollectorService "EEG Data Collection Service:\n• Singleton service managing hardware interface and data streaming\n• Immediate data processing architecture with 10ms update intervals\n• Real-time sample rate monitoring with sliding window metrics\n• Support for 40+ board types including OpenBCI, Muse, synthetic, and streaming boards\n• Background data thread with optimized performance and low-latency updates\n• Master board channel information for streaming board configurations\n• Device configuration, marker insertion, and streamer management\n• Automatic buffer management and metadata synchronization with DataAccessService"
    
    note for DataAccessService "Centralized Data Access and Management:\n• Singleton service providing thread-safe data buffer management\n• Separated callback flows: local (immediate) and API (optionally multiprocessed)\n• Real-time filter application with processor service integration\n• Advanced processing support including wavelet transforms and downsampling\n• Configurable buffer sizes with automatic truncation (30 seconds default)\n• Multiprocessing worker pools for CPU-intensive API operations\n• Metadata management with collector integration\n• Channel-specific data access and signal quality assessment"
    
    note for ProcessorService "Signal Processing Operations:\n• Filtering suite with automatic EEG channel detection\n• Bandpass, notch, detrend filtering with channel-specific application\n• Advanced filtering with multiple types (Butterworth, Chebyshev, Bessel)\n• Wavelet processing including denoising and coefficient computation\n• Independent Component Analysis with FastICA algorithm\n• EEG metrics calculation including power spectral density\n• Downsampling with configurable aggregation methods\n• Thread-safe operations with proper processor initialization"
    
    note for RecordingService "Data Recording and Storage:\n• Singleton service with continuous recording capabilities\n• Direct callback integration with DataAccessService for immediate data capture\n• Support for raw, processed, or dual-stream recording modes\n• CSV format with metadata headers and channel naming\n• Real-time marker insertion with proper timestamp synchronization\n• Background recording with automatic file finalization\n• Resource management with proper cleanup and error handling"
    
    note for VisualizationService "Visualization Component Coordination:\n• EEG waveform visualization with caching and performance optimization\n• Brain map visualization with automatic processor fallback creation\n• Filter settings management and visualization state tracking\n• Window lifecycle management with cache preservation during stop/start\n• Proper cleanup procedures for board disconnection scenarios\n• Integration with Qt-based visualization components\n• Support for multiple simultaneous visualization types"
    
    note for InteractionService "API Bridge and Service Coordination:\n• Singleton service bridging external REST API and internal operations\n• Event system integration for real-time UI updates and state synchronization\n• Component registry for managing application services and dependencies\n• Validation and state checking with detailed error reporting\n• Auto-initialization and recovery mechanisms for robust operation\n• Support for all EEG processor operations with consistent API responses\n• Status tracking and detailed logging for debugging and monitoring"
    
    note for AdvancedProcessingService "Advanced Signal Analysis:\n• Independent Component Analysis with configurable parameters and validation\n• Wavelet transform computation with support for 25+ wavelet types\n• Real-time inverse wavelet transform application to data streams\n• Advanced filtering with stream integration and dynamic parameter updates\n• Downsampling operations with real-time application capabilities\n• Results storage and management for computed analyses\n• Stream processing integration with DataAccessService coordination"
    
    note for MNEService "MNE-Python Integration Facade:\n• Singleton facade coordinating specialized MNE services\n• Asynchronous data conversion from BrainFlow to MNE format\n• Advanced neurophysiological visualization (PSD, spectrograms, topomaps)\n• Real-time processing sessions with configurable update intervals\n• Multiprocessing support for CPU-intensive operations\n• Task lifecycle management with status tracking and cancellation\n• Backward compatibility layer for existing code integration\n• Result storage and retrieval with proper memory management"
    
    note "Service Architecture Benefits:\n• Singleton Pattern: Consistent state management across application components\n• Event-Driven Design: Loose coupling with real-time synchronization capabilities\n• Service-Oriented Architecture: Clear separation of concerns with well-defined interfaces\n• Thread Safety: Locking strategies and concurrent access management\n• Resource Management: Proper lifecycle control and cleanup procedures\n• Performance Optimization: Optimized data flows and processing pipelines\n• Error Resilience: Robust error handling with recovery mechanisms\n• Extensibility: Plugin-like architecture enabling easy feature additions"
    
    note "Data Flow Architecture:\n1. CollectorService: Hardware interface and raw data collection with immediate processing\n2. DataAccessService: Centralized buffer management with separated callback flows\n3. ProcessorService: Signal processing and filtering operations with EEG optimization\n4. RecordingService: Data persistence with real-time callback integration\n5. VisualizationService: Real-time display coordination with caching optimization\n6. AdvancedProcessingService: Analysis capabilities with stream processing integration\n7. MNEService: Advanced neurophysiological analysis with multiprocessing support\n8. InteractionService: API coordination with event system integration"
    
    note "Specialized Service Integration:\n• ICA Services: Dedicated multiprocess services for independent component analysis\n  - Real-time ICA monitoring with sliding window buffers\n  - Advanced visualization and export capabilities\n  - Progress tracking and cancellation support\n\n• MNE Services: Complete MNE-Python integration services\n  - Asynchronous data conversion with task management\n  - Advanced visualization with multiple plot types\n  - Real-time processing with session management\n  - Thread-safe result storage and multiprocess coordination"
    
    note "Performance and Scalability Features:\n• Immediate Data Processing: 10ms update intervals for minimal latency\n• Multiprocessing Support: CPU-intensive operations isolated in worker processes\n• Memory Management: Automatic buffer truncation and resource cleanup\n• Concurrent Operations: Thread-safe services supporting simultaneous operations\n• Adaptive Processing: Dynamic parameter updates without restart requirements\n• Quality Monitoring: Real-time signal quality assessment and metrics\n• Efficient Callbacks: Separated flows for different consumer types (local vs API)\n• Resource Optimization: Shared services and component reuse across operations"
```