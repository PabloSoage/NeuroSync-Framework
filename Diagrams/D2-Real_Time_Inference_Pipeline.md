```mermaid
  classDiagram
    %% Interfaces for extensibility and reusability
    class IDataSource {
        <<interface>>
        +startAcquisition(): void
        +stopAcquisition(): void
        +getData(): any
        +onData(callback: function): void
    }

    class AbstractInputCollector {
        <<interface>>
        +start_capture(): void
        +stop_capture(): void
        +get_input_event(): InputData
        +on_event(callback: function): void
        +set_supported_keys(keys: List[str]): void
        +get_events_since(timestamp: float): List[InputData]
        +clear_events(): void
        +get_active_keys(): List[str]
        +get_collector_type(): str
        +get_capabilities(): Dict[str, Any]
    }

    class AbstractVisualizer {
        <<interface>>
        +update(input_data: Optional[InputData]): void
        +force_update(): void
        +set_collector_capabilities(capabilities: Dict): void
        +set_edit_mode(enabled: bool): void
        +supports_collector(collector_type: str): bool
    }

    class AbstractVisualizerProvider {
        <<interface>>
        +get_keyboard_visualizer(): KeyboardVisualizer
        +get_mouse_visualizer(): MouseVisualizer
        +get_mouse_buttons_selector(): MouseButtonsSelector
    }

    class AbstractVisualizerController {
        <<interface>>
        +update_for_collector(collector_type: str, capabilities: Dict): void
        +set_tracked_keys(keys: List[str]): void
        +set_scroll_tracking(enabled: bool): void
        +set_edit_mode(enabled: bool): void
        +force_update(): void
    }

    class IEmulator {
        <<interface>>
        +simulateAction(action: Action): void
    }

    %% Data Types
    class EEGData {
        +timestamp: number
        +channels: Map<string, number[]>
        +samplingRate: number
        +metadata: Map[string, any]
    }

    class InputData {
        +timestamp: float
        +event_type: string
        +key: string|null
        +mouse_x: number|null
        +mouse_y: number|null
        +button_pressed: string|null
        +active_keys: List[string]
        +direction: string|null
        +rel_x: number|null
        +rel_y: number|null
        +is_moving: boolean|null
        +mouse_delta_x: number|null
        +mouse_delta_y: number|null
        +mouse_delta_magnitude: number|null
        +mouse_delta_angle: number|null
        +mouse_tracking_mode: string|null
        +direction_only: boolean|null
        +discrete_angle: int|null
        +north: number|null
        +south: number|null
        +east: number|null
        +west: number|null
    }

    class SynchronizedData {
        +eegData: EEGData[]
        +inputEvents: InputData[]
        +synchronizationMarkers: Map<number, number>
    }

    class ProcessedData {
        +filteredSignals: number[][]
        +epochs: number[][][]
        +artifactMask: boolean[]
    }

    class FeatureVector {
        +features: number[][]
        +labels: string[]|number[]
        +metadata: Map[string, any]
    }

    class TrainedModel {
        +modelType: string
        +architecture: string
        +weights: any
        +hyperparameters: Map[string, any]
        +performanceMetrics: Map[string, number]
    }

    class Action {
        +actionType: string
        +keyCode: number|null
        +mouseMovement: [number, number]|null
        +buttonAction: string|null
        +confidence: number
    }

    %% Input Collector Implementation
    class KeyboardMouseCollector {
        -keyboard_events: List[InputData]
        -mouse_events: List[InputData]
        -tracked_keys_set: Set[string]
        -is_capturing: boolean
        -event_callbacks: List[function]
        +start_capture(): void
        +stop_capture(): void
        +get_input_event(): InputData
        +on_event(callback: function): void
        +set_supported_keys(keys: List[string]): void
        +get_events_since(timestamp: float): List[InputData]
        +clear_events(): void
        +set_mouse_tracking_mode(mode: string): void
        +get_collector_type(): str
        +get_capabilities(): Dict[str, Any]
    }

    class PS4ControllerCollector {
        -events: List[InputData]
        -button_state: Map[string, boolean]
        -axis_state: Map[string, number]
        -is_capturing: boolean
        -event_callbacks: List[function]
        +start_capture(): void
        +stop_capture(): void
        +get_input_event(): InputData
        +on_event(callback: function): void
        +set_supported_keys(keys: List[string]): void
        +get_events_since(timestamp: float): List[InputData]
        +clear_events(): void
        +scan_controllers(): List[object]
        +get_collector_type(): str
        +get_capabilities(): Dict[str, Any]
    }

    %% Main modules from input_collector
    class CollectorManager {
        -collectors: Dict[str, AbstractInputCollector]
        -current_collector: AbstractInputCollector
        -current_collector_type: str
        -visualizers: List[AbstractVisualizer]
        -tracked_keys: List[str]
        -event_callbacks: List[function]
        +add_collector(collector_type: str, collector: AbstractInputCollector): void
        +set_current_collector(collector_type: str): bool
        +get_available_collectors(): List[Dict[str, str]]
        +start_capture(): void
        +stop_capture(): void
        +register_visualizer(visualizer: AbstractVisualizer): void
        +unregister_visualizer(visualizer: AbstractVisualizer): void
        +set_tracked_keys(keys: List[str]): void
        +get_active_keys(): List[str]
        +on_event(callback: function): void
        +remove_event_handler(callback: function): void
        +get_current_collector_capabilities(): Dict[str, Any]
        +get_current_collector_type(): str
        +get_collector(collector_type: str): AbstractInputCollector|null
        +get_current_collector(): AbstractInputCollector|null
    }

    class VisualizerManager {
        -keyboard_viz: KeyboardVisualizer
        -mouse_viz: MouseVisualizer
        -mouse_buttons_selector: MouseButtonsSelector
        -edit_mode_enabled: boolean
        +get_keyboard_visualizer(): KeyboardVisualizer
        +get_mouse_visualizer(): MouseVisualizer
        +get_mouse_buttons_selector(): MouseButtonsSelector
        +update_for_collector(collector_type: str, capabilities: Dict[str, Any]): void
        +set_tracked_keys(keys: List[str]): void
        +set_scroll_tracking(enabled: bool): void
        +set_edit_mode(enabled: bool): void
        +force_update(): void
    }

    class UIManager {
        -components: Dict[str, QWidget]
        -main_layout: QVBoxLayout
        +set_visualizers(keyboard_viz: KeyboardVisualizer, mouse_viz: MouseVisualizer, mouse_buttons: MouseButtonsSelector): void
        +update_recording_state(is_recording: bool): void
        +update_collector_list(collectors: List[Dict[str, str]]): void
        +select_collector(collector_type: str): void
        +update_ui_for_collector(collector_type: str, capabilities: Dict[str, Any]): void
        +set_csv_path(path: str): void
        +log_status(message: str, color: str): void
        +update_active_keys_display(active_keys: List[str]): void
        +is_direction_only_mode(): bool
        +get_tracking_mode(): str
        +get_angle_grouping(): int
        +get_delta_smoothing(): float
        +get_joystick_sensitivity(): float
        +update_tracking_modes(valid_modes: List[str], current_mode: str, default_mode: str): void
        +get_current_collector_data(): str
        +select_collector_by_type(collector_type: str): void
        +update_edit_mode(enabled: bool): void
    }

    class LoggingManager {
        -json_logger: JSONLogger
        -csv_logger: CSVLogger
        -log_to_json: boolean
        -log_to_csv: boolean
        +set_json_logging(enabled: bool): boolean
        +set_csv_logging(enabled: bool, filepath: str): boolean
        +initialize_csv_file(headers: List[str], tracked_keys: List[str], tracking_mode: str, direction_only: bool): boolean
        +log_event(event: InputData, collector_type: str): void
        +start_recording(): void
        +stop_recording(): void
        +close_all(): void
    }

    class JSONLogger {
        -filepath: str
        -file: TextIO
        -log_data: Dict[str, Any]
        +open_log(): boolean
        +close_log(): void
        +log_event(event: InputData, collector_type: str): void
        +log_recording_start(): void
        +log_recording_stop(): void
    }

    class CSVLogger {
        -filepath: str
        -file: TextIO
        +set_filepath(filepath: str): void
        +initialize(headers: List[str], tracked_keys: List[str], tracking_mode: str, direction_only: bool): boolean
        +close_log(): void
        +log_event(event: InputData, collector_type: str): void
    }

    class EventProcessor {
        -f9_key_down: boolean
        +process_event(event: InputData, collector_type: str): Dict[str, Any]
        -_is_special_event(event: InputData): boolean
        -_process_special_event(event: InputData): Dict[str, Any]
        -_should_log_event(event: InputData): boolean
        -_format_display_text(event: InputData, collector_type: str): str
    }

    class AppCoordinator {
        -collector_manager: CollectorManager
        -ui_manager: UIManager
        -logging_manager: LoggingManager
        -event_processor: EventProcessor
        -is_recording: boolean
        -tracked_keys: List[str]
        -edit_mode: boolean
        -f9_key_down: boolean
        +initialize(tracked_keys: List[str]): void
        +on_collector_event(event: InputData): void
        +toggle_recording(): void
        +toggle_edit_mode(): void
        +handle_key_edit(key: str): void
        +handle_button_edit(button_id: str, is_tracked: bool): void
        +switch_collector(collector_type: str): void
        +set_mouse_tracking_mode(mode: str): void
        +apply_mouse_settings(): void
        +get_tracked_keys(): List[str]
    }

    class BaseVisualizer {
        -capabilities: Dict[str, Any]
        -edit_mode: boolean
        -supported_collectors: List[str]
        +update(input_data: Optional[InputData]): void
        +force_update(): void
        +set_collector_capabilities(capabilities: Dict[str, Any]): void
        +set_edit_mode(enabled: bool): void
        +supports_collector(collector_type: str): boolean
    }

    class KeyboardVisualizer {
        -keys: Dict[str, Dict[str, Any]]
        -keyboard_layout: List[List[str]]
        -tracked_keys: Set[str]
        -active_keys: Set[str]
        +update(input_data: Optional[InputData]): void
        +force_update(): void
        +set_tracked_keys(keys: List[str]): void
        +get_key_at_position(x: int, y: int): str|null
    }

    class MouseVisualizer {
        -state: Dict[str, Any]
        -direction_vectors: Dict[str, Tuple[float, float]]
        -tracking_mode: str
        -direction_only: boolean
        +update(input_data: Optional[InputData]): void
        +force_update(): void
    }

    class MouseButtonsSelector {
        -buttons: Dict[str, QPushButton]
        -tracked_buttons: Set[str]
        -edit_mode: boolean
        +update(): void
        +setTrackedButtons(buttons: List[str]): void
        +setEditMode(enabled: bool): void
        +setScrollTracking(enabled: bool): void
    }

    class InputCollectorApp {
        -collector_manager: CollectorManager
        -ui_manager: UIManager
        -logging_manager: LoggingManager
        -event_processor: EventProcessor
        -visualizer_manager: VisualizerManager
        -app_coordinator: AppCoordinator
        -tracked_keys: List[str]
        -is_fullscreen: boolean
        +_initialize_components(): void
        +_connect_signals(): void
        +_initialize_state(): void
        +run(): void
    }

    %% Main Modules for BCI system
    class EEGCollector {
        -board: BoardShim
        -params: BrainFlowInputParams
        -board_id: int
        -preset: int
        -is_streaming: boolean
        -sampling_rate: float
        -eeg_channels: List[int]
        -channel_types: Dict[str, List[int]]
        -raw_data: numpy.ndarray
        -processed_data: numpy.ndarray
        -data_manager: BrainFlowDataManager
        -dataCallbacks: function[]
        +prepare_session(): void
        +start_stream(buffer_size: int): void
        +stop_stream(): void
        +release_session(): void
        +get_data(num_samples: Optional[int]): Tuple[numpy.ndarray, List[int]]
        +save_data(filename: str, data_type: str): void
        +get_device_info(): Dict[str, Any]
        +onData(callback: function): void
        +removeCallback(callback: function): boolean
    }

    class SignalProcessor {
        -sampling_rate: float
        -processed_data: numpy.ndarray
        +bandpass_filter(data: numpy.ndarray, start_freq: float, stop_freq: float, order: int): numpy.ndarray
        +bandstop_filter(data: numpy.ndarray, start_freq: float, stop_freq: float, order: int): numpy.ndarray
        +get_signal_quality(data: numpy.ndarray, channel: int): float
        +preprocessRealTimeData(eegData: EEGData): FeatureVector
    }

    class EEGVisualizer {
        -collector: EEGCollector
        -processor: SignalProcessor
        +start(): void
        +stop(): void
        +update_plots(): void
        +set_bandpass_filter(enabled: bool, low_freq: float, high_freq: float): void
    }

    class BrainMapVisualizer {
        -collector: EEGCollector
        -processor: SignalProcessor
        +start(): void
        +stop(): void
        +update_quality_map(): void
    }

    class DataSynchronizer {
        -syncMethod: string
        -windowSize: number
        -toleranceMs: number
        +synchronize(eeg: EEGData, input: InputData): SynchronizedData
        +setSyncMethod(method: string): void
        +setWindowSize(sizeMs: number): void
        +setTolerance(toleranceMs: number): void
        +verifySyncAccuracy(data: SynchronizedData): number
    }

    class DataLogger {
        -storageFormat: string
        -compressionEnabled: boolean
        -storagePath: string
        -metadataFields: string[]
        +saveData(data: SynchronizedData): void
        +loadData(): SynchronizedData[]
        +exportToFormat(data: SynchronizedData, format: string): void
        +annotateData(data: SynchronizedData, annotations: Map[string, any]): void
    }

    class DataPreprocessor {
        -filterTypes: string[]
        -artifactRejectionMethod: string
        -epochDuration: number
        -featureExtractionMethods: string[]
        +calculateSignalQuality(data: EEGData): Map[string, number]
        +visualizeData(data: ProcessedData): any
        +preprocessRealTimeData(eegData: EEGData): FeatureVector
    }

    class InferenceEngine {
        -model: TrainedModel
        -inferenceDevice: string
        -realTimeProcessing: boolean
        -confidenceThreshold: number
        -windowSize: number
        -preprocessor: DataPreprocessor
        -dataBuffer: EEGData[]
        +loadModel(model: TrainedModel): void
        +predict(eeg: EEGData): Action
        +subscribeToEEGSource(source: EEGCollector): void
        +unsubscribeFromEEGSource(source: EEGCollector): void
        +benchmark(): Map[string, number]
        +getLatestPredictions(count: number): Action[]
        +handleNewEEGData(data: EEGData): void
    }

    class VirtualDeviceEmulator {
        -supportedDevices: string[]
        -currentDevice: string
        -mappingConfiguration: Map[string, any]
        +simulateAction(action: Action): void
        +setSupportedDevices(devices: string[]): void
        +setCurrentDevice(device: string): void
        +configureMappings(mappings: Map[string, any]): void
    }

    %% Relationships
    AbstractInputCollector <|.. KeyboardMouseCollector
    AbstractInputCollector <|.. PS4ControllerCollector
    AbstractVisualizer <|.. BaseVisualizer
    BaseVisualizer <|-- KeyboardVisualizer
    BaseVisualizer <|-- MouseVisualizer
    BaseVisualizer <|-- MouseButtonsSelector
    AbstractVisualizerProvider <|.. VisualizerManager
    AbstractVisualizerController <|.. VisualizerManager
    IEmulator <|.. VirtualDeviceEmulator

    CollectorManager "1" o-- "*" AbstractInputCollector : "manages"
    VisualizerManager "1" o-- "1" KeyboardVisualizer : "contains"
    VisualizerManager "1" o-- "1" MouseVisualizer : "contains"
    VisualizerManager "1" o-- "1" MouseButtonsSelector : "contains"
    LoggingManager "1" o-- "1" JSONLogger : "contains"
    LoggingManager "1" o-- "1" CSVLogger : "contains"

    AppCoordinator "1" o-- "1" CollectorManager : "coordinates"
    AppCoordinator "1" o-- "1" UIManager : "coordinates"
    AppCoordinator "1" o-- "1" LoggingManager : "coordinates"
    AppCoordinator "1" o-- "1" EventProcessor : "coordinates"

    InputCollectorApp "1" o-- "1" CollectorManager : "owns"
    InputCollectorApp "1" o-- "1" UIManager : "owns"
    InputCollectorApp "1" o-- "1" LoggingManager : "owns"
    InputCollectorApp "1" o-- "1" EventProcessor : "owns"
    InputCollectorApp "1" o-- "1" VisualizerManager : "owns"
    InputCollectorApp "1" o-- "1" AppCoordinator : "owns"

    UIManager "1" --> "1" VisualizerManager : "sets visualizers"

    CollectorManager --> DataSynchronizer : "provides InputData"
    CollectorManager "1" ..> "1" InferenceEngine : "real-time events"
    EEGCollector --> DataSynchronizer : "provides EEGData"
    DataSynchronizer --> DataLogger : "stores SynchronizedData"
    DataLogger --> DataPreprocessor : "provides data for"
    DataPreprocessor --> InferenceEngine : "used by"

    %% Direct real-time connections
    EEGCollector "1" --> "1" InferenceEngine : "supplies live EEGData"
    EEGCollector "1" --> "1" DataPreprocessor : "real-time processing"
    InferenceEngine "1" --> "1" VirtualDeviceEmulator : "generates Action"

    %% Visualization connections
    EEGCollector "1" --> "1" EEGVisualizer : "provides data to"
    EEGCollector "1" --> "1" BrainMapVisualizer : "provides data to"
    SignalProcessor "1" --> "1" EEGVisualizer : "processes data for"
    SignalProcessor "1" --> "1" BrainMapVisualizer : "processes data for"

    EEGCollector --|> IDataSource
    KeyboardMouseCollector -- InputData : "produces"
    PS4ControllerCollector -- InputData : "produces"
    EEGCollector -- EEGData : "produces"
    DataSynchronizer -- SynchronizedData : "produces"
    DataPreprocessor -- ProcessedData : "produces"
    DataPreprocessor -- FeatureVector : "produces"
    InferenceEngine -- Action : "produces"
```
