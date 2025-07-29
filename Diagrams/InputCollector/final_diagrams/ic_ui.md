```mermaid
classDiagram
    direction TB
    
    %% Main UI Classes
    class UIManager {
        <<main ui coordinator>>
        +toggle_recording: pyqtSignal
        +switch_collector: pyqtSignal
        +toggle_edit_mode: pyqtSignal
        +update_recording_state()
        +update_collector_list()
        +log_status()
        +update_active_keys_display()
    }
    
    class VisualizerManager {
        <<visualizer coordinator>>
        +key_clicked: pyqtSignal
        +button_toggled: pyqtSignal
        +get_keyboard_visualizer()
        +get_mouse_visualizer()
        +get_mouse_buttons_selector()
        +get_ps4_controller_visualizer()
        +update_for_collector()
        +set_tracked_keys()
        +set_edit_mode()
    }
    
    class KeyboardEventFilter {
        <<event filter>>
        +eventFilter()
    }
    
    %% External Visualizers (References)
    class KeyboardVisualizer {
        <<external>>
    }
    
    class MouseVisualizer {
        <<external>>
    }
    
    class MouseButtonsSelector {
        <<external>>
    }
    
    class PS4ControllerVisualizer {
        <<external>>
    }
    
    %% Protocol Interfaces (References)
    class AbstractVisualizerProvider {
        <<protocol>>
    }
    
    class AbstractVisualizerController {
        <<protocol>>
    }
    
    %% Qt Framework
    class QMainWindow {
        <<qt framework>>
    }
    
    class QtUIComponents {
        <<qt ui components>>
    }
    %% Package Reference
    class UIPackage {
        <<module package>>
    }
    
    %% Package Composition
    UIPackage "1" *-- "1" UIManager : contains
    UIPackage "1" *-- "1" VisualizerManager : contains
    UIPackage "1" *-- "1" KeyboardEventFilter : contains
    
    %% Core Component Relationships
    UIManager "1" *-- "1" QMainWindow : manages
    UIManager "1" *-- "*" QtUIComponents : contains
    
    VisualizerManager "1" *-- "1" KeyboardVisualizer : manages
    VisualizerManager "1" *-- "1" MouseVisualizer : manages
    VisualizerManager "1" *-- "1" MouseButtonsSelector : manages
    VisualizerManager "1" *-- "1" PS4ControllerVisualizer : manages
    VisualizerManager "1" *-- "1" KeyboardEventFilter : uses
    
    KeyboardEventFilter "1" *-- "1" VisualizerManager : references
    
    %% Protocol Implementation
    VisualizerManager ..|> AbstractVisualizerProvider : implements
    VisualizerManager ..|> AbstractVisualizerController : implements
    
    %% Signal Connections
    MouseButtonsSelector ..> VisualizerManager : signals to
    KeyboardEventFilter ..> VisualizerManager : signals to
```