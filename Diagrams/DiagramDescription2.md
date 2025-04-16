# Diagram Description

## D1: Sequential Pipeline

- **IDataSource (Interface):**
  Interface defining the core methods required for any data acquisition source, allowing for system extensibility and component swapping.

- **AbstractInputCollector (Interface):**
  Abstract interface for input collection mechanisms standardizing the capture of various input sources (keyboard, mouse, game controllers). Defines methods for starting/stopping capture, retrieving events, setting callbacks, and managing event history.

- **IEmulator (Interface):**
  Interface for device emulation implementation, providing abstraction for different output mechanisms.

- **EEGDataCollector:**
  Responsible for initializing and stopping EEG signal acquisition through the BrainFlow library and returning raw data. Includes configuration for different channel sets, montage types, and reference electrodes. Provides methods for checking available devices and testing connections.

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

- **AbstractInputCollector (Interface):**
  Enhanced with event notification capabilities for real-time input monitoring through the on_event callback mechanism. Both implementations (KeyboardMouseCollector and PS4ControllerCollector) provide immediate event notifications when inputs are detected.

- **InputData:**
  Comprehensive data structure for representing input events with additional fields for real-time tracking modes, directional information, and device-specific metrics. Serves as a unified data structure for all input types.

- **EEGDataCollector:**
  Maintains its role as responsible for capturing EEG signals but adds the onData function to notify other modules (such as InferenceEngine) whenever new data is available in real-time. Includes callback management for data subscribers.

- **KeyboardMouseCollector:**
  Provides real-time input events through callbacks to subscribers. Offers configurable tracking modes including joystick-like representation, delta-based tracking, angle-based tracking, and axis-based tracking with direction membership values.

- **PS4ControllerCollector:**
  Offers real-time game controller input through an event system. Detects and reports button presses, joystick movements, and pressure-sensitive inputs, with support for controller hotplugging.

- **DataPreprocessor:**
  Enhanced with real-time processing capabilities through the preprocessRealTimeData method, optimized for low-latency feature extraction from streaming EEG data.

- **InferenceEngine:**
  Now has a direct relationship with EEGDataCollector and can receive real-time events from input collectors. It can subscribe to or directly query EEG readings for real-time inference. This doesn't eliminate the synchronization function with inputs but allows inference to be performed immediately using live data without waiting for an intermediate stage. Includes a data buffer for maintaining temporal context and dedicated handlers for new EEG data.

- **Data Flow:**
  The real-time pipeline maintains the sequential processing capabilities but adds direct connections between data sources and the inference engine, enabling lower-latency operation for applications requiring immediate response to neural signals. Input collectors can now provide event-driven updates to the inference engine for responsive control.
