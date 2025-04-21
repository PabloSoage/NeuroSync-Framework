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

- **InputData:**
  Comprehensive data class for representing input events with timestamps, including keyboard presses, mouse movements, controller button presses, and axis movements. Contains information about active keys, mouse positions, directions, and various tracking metrics.

- **KeyboardMouseCollector:**
  Implementation of AbstractInputCollector for capturing keyboard and mouse events using pynput. Features multiple mouse tracking modes (joystick, delta, angle, axis) with customizable sensitivity. Supports key state tracking, real-time event notifications, and direction-based movement representation.

- **PS4ControllerCollector:**
  Implementation of AbstractInputCollector for PS4 controllers using SDL2. Captures button presses, joystick movements, and trigger inputs. Provides device scanning, controller selection, and real-time event notifications using a callback system.

- **CollectorManager:**
  Manages different input collectors (keyboard/mouse, PS4 controller) and serves as a central point for input event handling. It abstracts away the details of specific collectors, allowing the application to work with different input sources through a unified interface.

- **VisualizerManager:**
  Manages visualization components for input events. Creates, configures, and updates visualizers for keyboard, mouse, and controller inputs. Implements implicit interfaces to avoid metaclass conflicts with Qt.

- **UIManager:**
  Manages the user interface components and layout for the application. Handles user interactions, component visibility, and status updates, delegating specific actions to the appropriate components.

- **EventProcessor:**
  Processes input events for display, logging, and visualization. Formats events based on collector type and provides consistent event handling across different input sources.

- **LoggingManager:**
  Centralizes logging functionality, managing both JSON and CSV logging of input events. Provides a unified interface for enabling/disabling logging and storing event data.

- **CSVLogger and JSONLogger:**
  Specialized loggers that handle the output of input events to CSV and JSON formats respectively, each focusing on its specific format requirements.

- **AppCoordinator:**
  Central coordinator that mediates between all application components according to the Mediator pattern. Handles high-level application logic, input event processing, recording management, visualization updates, and configuration changes.

- **InputCollectorApp:**
  Main application class that integrates all components and provides the entry point for the application. Sets up the UI, initializes components, connects signals, and manages the application lifecycle.

- **VisualizerBase, KeyboardVisualizer, MouseVisualizer, MouseButtonsSelector:**
  Visualization components that render input events graphically. Follow a common interface through inheritance from VisualizerBase, supporting different collector types and visualization modes.

## D2: Real-time Inference Pipeline

- **Input Collector Components:**
  Refactored to adhere to SOLID principles with clear separation of concerns between collection (CollectorManager), visualization (VisualizerManager), user interface (UIManager), logging (LoggingManager), and coordination (AppCoordinator).

- **AbstractInputCollector (Interface):**
  Enhanced with event notification capabilities for real-time input monitoring through the on_event callback mechanism. Both implementations (KeyboardMouseCollector and PS4ControllerCollector) provide immediate event notifications when inputs are detected.

- **InputData:**
  Comprehensive data structure for representing input events with additional fields for real-time tracking modes, directional information, and device-specific metrics. Serves as a unified data structure for all input types.

- **CollectorManager:**
  Manages multiple input collectors and provides a unified interface for accessing input events. Enables real-time processing by forwarding events to registered visualizers and callbacks as soon as they occur.

- **VisualizerManager:**
  Manages visualization components with real-time updates based on input events. Handles interaction between visualizers and the UI, enabling features like interactive key selection.

- **EventProcessor:**
  Processes input events in real-time for display, logging, and control purposes. Formats events based on their type and source, and propagates them to the appropriate components.

- **AppCoordinator:**
  Acts as a central mediator between components, coordinating the flow of real-time input events from collectors to visualizers, loggers, and the UI. Manages application state and responds to user interactions.

- **Logging System:**
  The LoggingManager, CSVLogger, and JSONLogger components work together to provide efficient real-time logging of input events with minimal impact on performance.

- **Data Flow:**
  The real-time pipeline maintains the sequential processing capabilities but adds direct connections between components, enabling lower-latency operation. Input collectors provide event-driven updates to visualizers and the inference engine for responsive control.

- **SOLID Principles Implementation:**
  The refactored architecture now follows:
  - Single Responsibility: Each component has a clear, focused purpose
  - Open/Closed: Components can be extended without modification
  - Liskov Substitution: Different implementations can be swapped without breaking functionality
  - Interface Segregation: Interfaces are specific to client needs
  - Dependency Inversion: High-level modules depend on abstractions, not concrete implementations
