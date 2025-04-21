# Diagram Description

## D1: Sequential Pipeline

- **IDataSource (Interface):**
  Interface defining the core methods required for any data acquisition source, allowing for system extensibility and component swapping.

- **CollectorInterface (Interface):**
  Interface for EEG data collection that standardizes methods for board connection, streaming control, data acquisition, and device information retrieval.

- **DataStorageInterface, ContinuousRecordingInterface, MarkerInterface, ConfigurableCollectorInterface (Interfaces):**
  Specialized interfaces that define specific responsibilities for data collection components, following the Interface Segregation Principle from SOLID.

- **BoardInterface (Interface):**
  Interface for board configuration management, providing methods for board discovery, parameter requirements, and description retrieval.

- **AbstractInputCollector (Interface):**
  Abstract interface for input collection mechanisms standardizing the capture of various input sources (keyboard, mouse, game controllers). Defines methods for starting/stopping capture, retrieving events, setting callbacks, and managing event history.

- **IEmulator (Interface):**
  Interface for device emulation implementation, providing abstraction for different output mechanisms.

- **EEGCollector:**
  Implementation of multiple collector interfaces based on BrainFlow. Manages board connections, data streaming, recording, and acquisition from various EEG devices. Uses composition with BrainFlowDataManager to handle continuous recording operations, adhering to the Single Responsibility Principle.

- **BrainFlowDataManager:**
  Specialized class for handling continuous data recording operations, including file management, threading, and sample synchronization.

- **BoardConfiguration:**
  Provides board discovery and configuration capabilities, implementing the BoardInterface. Helps with creating appropriate parameters for different board types.

- **CollectorService:**
  Service layer component that orchestrates EEG collector operations, providing a higher-level API for the application. Manages the lifecycle of the EEGCollector and handles error states.

- **SignalProcessor:**
  Handles signal processing operations on EEG data. Implements various filtering methods, signal transformations, and analysis functions. Maintains a clear single responsibility for signal processing algorithms.

- **ProcessorService:**
  Service layer component that manages signal processor operations and provides a simplified API for common processing tasks. Handles initialization and safe execution of processing operations.

- **RecordingService:**
  Service for managing data recording operations, handling file naming, recording status tracking, and marker insertion during recording.

- **VisualizationService:**
  Service for managing visualization components, providing creation, lifecycle management, and configuration of different visualizers.

- **EEGVisualizer:**
  Real-time visualization for EEG signals. Displays time series data, power spectra, and band powers. Integrates with SignalProcessor to apply filters and with EEGCollector to retrieve data continuously.

- **BrainMapVisualizer:**
  Provides a topographic brain map visualization that displays electrode positions and signal quality. Uses a 2D representation of the head with color-coded quality indicators for real-time monitoring.

- **MultiModalityVisualizer:**
  Visualizes multiple signal modalities beyond just EEG, including EMG, ECG, EOG, and motion data. Creates separate visualization windows for different data types with appropriate visualizations for each.

- **InputData:**
  Flexible data structure for representing all types of input events with timestamps, including keyboard presses, mouse movements, controller button presses, and axis movements. Contains information about active keys, mouse positions, directions, and various tracking metrics.

- **KeyboardMouseCollector:**
  Implementation of AbstractInputCollector for capturing keyboard and mouse events using pynput. Features multiple mouse tracking modes (joystick, delta, angle, axis) with customizable sensitivity. Supports key state tracking, real-time event notifications, and direction-based movement representation.

- **PS4ControllerCollector:**
  Implementation of AbstractInputCollector for PS4 controllers using SDL2. Captures button presses, joystick movements, and trigger inputs. Provides device scanning, controller selection, and real-time event notifications using a callback system.

- **DataSynchronizer:**
  Receives EEG data and input events, and using timestamps, generates a synchronized data structure that links both sources. Implements various synchronization methods and provides verification tools to ensure temporal alignment accuracy.

- **DataLogger:**
  Saves synchronized data for later analysis and training. Also manages the loading of historical data. Supports different storage formats, compression options, and metadata annotation for experiment documentation.

- **DataPreprocessor:**
  Applies filters and cleaning processes to the dataset, and extracts features (e.g., using time windows) that will be used in model training. Includes methods for artifact rejection, signal quality assessment, and visualization of processed data.

- **ModelTrainer:**
  Uses feature vectors (and corresponding action labels) to train the neural network model. Also contemplates hyperparameter optimization. Provides methods for model evaluation, saving/loading trained models, and visualizing training metrics.

- **InferenceEngine:**
  Once a trained model is loaded, it's used to make real-time predictions from received EEG data, generating an action (e.g., determining which key should be pressed). Configurable for different inference devices and confidence thresholds.

- **VirtualDeviceEmulator:**
  Takes the predicted action and translates it into a real action in the system (emulation of key press, mouse movement, etc.). Supports multiple virtual device types and configurable mapping between model outputs and system actions.

## D2: Real-time Inference Pipeline

- **IDataSource (Interface):**
  Extended with callback functionality to support real-time data streaming and event-based architecture.

- **CollectorInterface (Interface):**
  Interface for EEG data collection with standardized methods for streaming control and data acquisition that can be integrated into both sequential and real-time processing pipelines.

- **CollectorInterface, DataStorageInterface, ContinuousRecordingInterface, MarkerInterface, ConfigurableCollectorInterface (Interfaces):**
  The same interfaces from the sequential pipeline, ensuring a consistent design across both pipelines.

- **BoardInterface (Interface):**
  Interface for board configuration management that provides consistent board management capabilities.

- **AbstractInputCollector (Interface):**
  Enhanced with event notification capabilities for real-time input monitoring through the on_event callback mechanism. Both implementations (KeyboardMouseCollector and PS4ControllerCollector) provide immediate event notifications when inputs are detected.

- **InputData:**
  Comprehensive data structure for representing input events with additional fields for real-time tracking modes, directional information, and device-specific metrics. Serves as a unified data structure for all input types.

- **EEGCollector:**
  Enhanced implementation of collector interfaces with callback mechanism for real-time data notifications. Works with BrainFlowDataManager for continuous recording while maintaining real-time responsiveness.

- **BrainFlowDataManager:**
  Handles continuous recording in a way that doesn't interfere with real-time data access, using a separate thread for file operations.

- **BoardConfiguration:**
  Provides the same board discovery and configuration capabilities as in the sequential pipeline.

- **CollectorService:**
  Service layer component that maintains the same API as in the sequential pipeline but optimized for real-time operation.

- **SignalProcessor:**
  Enhanced with real-time processing capabilities. Performs filtering, denoising, and feature extraction operations optimized for low-latency processing. Provides signal quality assessment for real-time monitoring and feedback.

- **ProcessorService:**
  Service layer component that provides the same API as in the sequential pipeline but ensures minimal processing latency for real-time applications.

- **EEGVisualizer, BrainMapVisualizer, MultiModalityVisualizer:**
  Real-time visualization components that continuously update as new data arrives. Each provides specialized views for different aspects of the EEG data: time series, topographic quality mapping, and multi-modal signal visualization.

- **KeyboardMouseCollector:**
  Provides real-time input events through callbacks to subscribers. Offers configurable tracking modes including joystick-like representation, delta-based tracking, angle-based tracking, and axis-based tracking with direction membership values.

- **PS4ControllerCollector:**
  Offers real-time game controller input through an event system. Detects and reports button presses, joystick movements, and pressure-sensitive inputs, with support for controller hotplugging.

- **DataPreprocessor:**
  Enhanced with real-time processing capabilities through the preprocessRealTimeData method, optimized for low-latency feature extraction from streaming EEG data.

- **InferenceEngine:**
  Now has a direct relationship with EEGCollector and can receive real-time events from input collectors. It can subscribe to or directly query EEG readings for real-time inference. This doesn't eliminate the synchronization function with inputs but allows inference to be performed immediately using live data without waiting for an intermediate stage. Includes a data buffer for maintaining temporal context and dedicated handlers for new EEG data.

- **Data Flow:**
  The real-time pipeline maintains the sequential processing capabilities but adds direct connections between data sources and the inference engine, enabling lower-latency operation for applications requiring immediate response to neural signals. Input collectors can now provide event-driven updates to the inference engine for responsive control.
