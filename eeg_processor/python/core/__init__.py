"""
Core Functionality Package for EEG Processor Application.

This package provides fundamental infrastructure components that form the backbone
of the EEG processing application. It implements essential patterns and systems
for application-wide coordination, communication, and state management.

Core Components:

- EventDispatcher: Singleton event management system
  * Thread-safe event publishing and subscription with RLock protection
  * Event type enumeration covering all application domains
  * Event history tracking (1000 events) with automatic cleanup and rotation
  * Late subscriber support with automatic last event delivery
  * Error handling preventing single callback failures from affecting others
  * Performance-optimized subscription management with set-based storage

- EventType: Enumeration of application-wide events
  * Connection Events: Board connect/disconnect, stream start/stop, status changes
  * Processing Events: Filter application, settings changes, metrics calculation
  * Visualization Events: Display start/stop, brain map control, status updates
  * Recording Events: Recording control, marker insertion, status tracking
  * Streaming Events: Streamer management, configuration changes
  * Advanced Processing Events: ICA, wavelet, downsampling operations
  * MNE Events: Conversion, plotting, advanced neurophysiological analysis
  * Data Events: Real-time data updates, metadata changes, board information
  * UI State Events: Status updates, control enabling/disabling, panel coordination
  * System Events: Status changes, error/warning/info message handling
  * Configuration Events: Settings changes, device configuration, responses
  * Channel Events: Selection changes, data updates, channel-specific operations

- Event: Structured event data container with metadata
  * Timestamp tracking for chronological event ordering and analysis
  * Source identification for debugging and component interaction tracking
  * Flexible data payload with dictionary-based parameter passing
  * Immutable design ensuring event integrity throughout the dispatch process

Key Architectural Features:

Decoupled Communication:
- Publisher-subscriber pattern enabling loose coupling between application components
- Event-driven architecture reducing direct dependencies and improving modularity
- Cross-component communication without requiring explicit component references
- API-GUI coordination through standardized event interfaces and protocols

Thread Safety and Performance:
- RLock-based synchronization ensuring thread-safe operations across concurrent access
- Optimized subscription management with set-based storage for O(1) operations
- Lock minimization preventing deadlocks during callback execution
- Memory-efficient event history with automatic rotation and cleanup procedures

Error Handling:
- Individual callback error isolation preventing cascade failures
- Logging system for debugging and performance analysis
- Degradation when subscribers fail without affecting other components
- Exception containment ensuring system stability during component failures

Advanced Event Management:
- Event history tracking enabling debugging and system state reconstruction
- Last event caching providing state synchronization for late-joining subscribers
- Flexible event filtering and querying capabilities for system monitoring
- Subscriber count tracking for performance optimization and resource management

Singleton Pattern Implementation:
- Thread-safe singleton ensuring single event dispatcher instance across application
- Lazy initialization with proper locking preventing race conditions
- Global convenience functions providing simplified API access
- Legacy compatibility through EventSystem alias maintaining backward compatibility

Event System Applications:

API-GUI Synchronization:
- Real-time status updates between external API and user interface components
- Bidirectional communication enabling API control with GUI feedback
- State synchronization ensuring consistent application state across all components
- Event-driven UI updates providing immediate feedback for user actions

Service Coordination:
- Inter-service communication without direct coupling or circular dependencies
- Data flow coordination between collection, processing, and visualization services
- Status propagation across complex service hierarchies and dependencies
- Resource management coordination preventing conflicts and ensuring proper cleanup

Real-time Processing Coordination:
- Filter application events enabling synchronized processing across visualization components
- Data update notifications ensuring all consumers receive timely updates
- Processing completion signals coordinating complex analysis workflows
- Performance monitoring events enabling adaptive optimization strategies

User Interface Integration:
- Panel coordination ensuring consistent state across multiple UI components
- Dynamic control enabling/disabling based on application state and capabilities
- Status message propagation providing user feedback
- Error handling coordination ensuring proper user notification and recovery

Advanced Features:

Event History and Debugging:
- Chronological event tracking enabling system behavior analysis and debugging
- Configurable history limits preventing memory growth while maintaining useful data
- Event filtering and querying supporting targeted analysis and monitoring
- Performance metrics tracking enabling system optimization and tuning

Subscription Management:
- Dynamic subscription enabling runtime component registration and deregistration
- Late subscriber support ensuring new components receive current state information
- Subscription tracking providing visibility into component relationships and dependencies
- Automatic cleanup preventing memory leaks from orphaned subscriptions

Global Convenience API:
- Simplified dispatch functions reducing boilerplate code across application
- Convenient subscription management through module-level functions
- Direct access to dispatcher features without explicit instance management
- Backward compatibility ensuring existing code continues to function correctly

The core package provides essential infrastructure enabling
application coordination, error handling, and maintainable architecture
throughout the EEG processing system. It serves as the foundation for all
inter-component communication and state management across the application.
"""

from .event_system import (
    EventDispatcher,
    EventSystem,
    EventType,
    Event,
    get_dispatcher,
    dispatch,
    subscribe,
    unsubscribe,
    get_last_event,
    clear_event_history,
)

__all__ = [
    # Core event system classes
    "EventDispatcher",
    "EventSystem",  # Legacy alias
    "EventType",
    "Event",
    # Convenience functions
    "get_dispatcher",
    "dispatch",
    "subscribe",
    "unsubscribe",
    "get_last_event",
    "clear_event_history",
]
