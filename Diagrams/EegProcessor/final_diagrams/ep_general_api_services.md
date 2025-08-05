```mermaid
classDiagram
    direction LR
    
    %% Entry Point (mantener contexto)
    class RunApplication {
        <<entry point>>
        +main()$
        +parse_config()$
    }
    
    %% Core Application (referencia)
    class EEGProcessorApp {
        <<main application>>
        +setup_ui()
        +update_status()
        +closeEvent()
    }
    
    %% APIs
    class EEGDataAPI {
        <<static data access api>>
        +get_current_data()$
        +get_channel_data()$
        +get_metadata()$
        +get_sampling_rate()$
        +get_channel_names()$
        +is_streaming()$
        +register_data_callback()$
    }


    class CLIPackage {
        <<command line interface>>
    }

    
    class EEGProcessorInteractionAPI {
        <<static interaction api>>
        +get_available_boards()$
        +connect_to_board()$
        +disconnect_from_board()$
        +start_stream()$
        +stop_stream()$
        +apply_filters()$
        +start_recording()$
        +stop_recording()$
        +perform_ica()$
        +convert_to_mne()$
        +compute_wavelet()$
    }
    
    class EEGProcessorApiIntegration {
        <<api integration service>>
        +data_service: DataAccessService
        +interaction_integration: EEGProcessorInteractionApiIntegration
        +get_instance()$
        +register_api()
    }
    
    class EEGProcessorInteractionApiIntegration {
        <<interaction api integration>>
        +interaction_service: InteractionService
        +get_instance()$
        +register_api_methods()
    }
    
    %% Core Services
    class CollectorService {
        <<data collection service>>
        +get_instance()$
        +is_connected()
        +is_streaming_active()
        +connect_to_board()
        +start_stream()
        +cleanup()
    }
    
    class DataAccessService {
        <<centralized data access>>
        +get_instance()$
        +get_current_data()
        +get_metadata()
        +register_callback()
        +is_streaming()
    }
    
    class ProcessorService {
        <<signal processing service>>
        +apply_filters()
        +get_filter_settings()
        +calculate_eeg_metrics()
    }
    
    class RecordingService {
        <<data recording service>>
        +get_instance()$
        +is_recording()
        +start_continuous_recording()
        +stop_continuous_recording()
        +insert_marker()
    }
    
    class VisualizationService {
        <<visualization management service>>
        +start_eeg_visualization()
        +stop_eeg_visualization()
        +start_brain_map_visualization()
        +cleanup()
    }
    
    class InteractionService {
        <<interaction coordination service>>
        +get_instance()$
        +get_available_boards()
        +connect_to_board()
        +start_stream()
        +apply_filters()
        +start_recording()
        +perform_ica()
        +convert_to_mne()
    }
    
    class MNEService {
        <<mne processing service>>
        +get_instance()$
        +convert_to_mne_async()
        +start_realtime_processing()
        +cleanup()
    }
    
    class AdvancedProcessingService {
        <<advanced analysis service>>
        +compute_ica()
        +compute_wavelet()
        +apply_downsampling()
        +apply_advanced_filters()
    }
    
    class ApiExplorer {
        <<external api framework>>
        +get_instance()$
        +register_module()
        +start_server()
    }
    
    %% Entry Point Relationships
    RunApplication ..> EEGProcessorApp : creates and runs
    RunApplication ..> CLIPackage : manages
    
    %% Core Services in App
    EEGProcessorApp "1" *-- "1" CollectorService : contains
    EEGProcessorApp "1" *-- "1" ProcessorService : contains
    EEGProcessorApp "1" *-- "1" VisualizationService : contains
    EEGProcessorApp "1" *-- "1" RecordingService : contains
    EEGProcessorApp "1" *-- "0..1" MNEService : contains
    
    %% Service Dependencies
    EEGProcessorApp ..> AdvancedProcessingService : uses
    EEGProcessorApp ..> DataAccessService : uses
    EEGProcessorApp ..> InteractionService : uses
    
    %% API Integration Composition
    EEGProcessorApiIntegration "1" *-- "1" DataAccessService : contains
    EEGProcessorApiIntegration "1" *-- "1" EEGProcessorInteractionApiIntegration : contains
    EEGProcessorInteractionApiIntegration "1" *-- "1" InteractionService : contains
    
    %% CLI Dependencies
    CLIPackage ..> DataAccessService : uses
    CLIPackage ..> InteractionService : uses

    %% API Delegation Pattern
    EEGDataAPI ..> DataAccessService : delegates to
    EEGProcessorInteractionAPI ..> InteractionService : delegates to
    
    %% Integration Layer
    EEGProcessorInteractionApiIntegration ..> ApiExplorer : uses
    EEGProcessorApiIntegration ..> ApiExplorer : uses
```