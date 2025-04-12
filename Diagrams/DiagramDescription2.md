# Diagram Description

## D1: Sequential Pipeline

- **IDataSource (Interface):**
  Interface defining the core methods required for any data acquisition source, allowing for system extensibility and component swapping.

- **IInputCollector (Interface):**
  Interface for standardizing input collection mechanisms regardless of the specific device type (keyboard, mouse, etc.).

- **IEmulator (Interface):**
  Interface for device emulation implementation, providing abstraction for different output mechanisms.

- **EEGDataCollector:**
  Responsible for initializing and stopping EEG signal acquisition through the BrainFlow library and returning raw data. Includes configuration for different channel sets, montage types, and reference electrodes. Provides methods for checking available devices and testing connections.

- **InputDataCollector:**
  Manages the capture of keyboard and mouse events (using libraries like pynput) along with their timestamps. Supports configuration of tracked keys and mouse movement capabilities. Maintains event buffers for synchronization.

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

- **IInputCollector (Interface):**
  Enhanced with event notification capabilities for real-time input monitoring.

- **EEGDataCollector:**
  Maintains its role as responsible for capturing EEG signals but adds the onData function to notify other modules (such as InferenceEngine) whenever new data is available in real-time. Includes callback management for data subscribers.

- **InputDataCollector:**
  Similar to the sequential pipeline version but includes event notification capabilities for real-time monitoring of user inputs.

- **DataPreprocessor:**
  Enhanced with real-time processing capabilities through the preprocessRealTimeData method, optimized for low-latency feature extraction from streaming EEG data.

- **InferenceEngine:**
  Now has a direct relationship with EEGDataCollector. It can subscribe to or directly query EEG readings for real-time inference. This doesn't eliminate the synchronization function with inputs but allows inference to be performed immediately using live data without waiting for an intermediate stage. Includes a data buffer for maintaining temporal context and dedicated handlers for new EEG data.

- **Data Flow:**
  The real-time pipeline maintains the sequential processing capabilities but adds direct connections between data sources and the inference engine, enabling lower-latency operation for applications requiring immediate response to neural signals.