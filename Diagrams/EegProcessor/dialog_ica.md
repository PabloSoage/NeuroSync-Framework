```mermaid
classDiagram
    %% ================================================================================
    %% UI/ADVANCED/DIALOGS MODULE - SPECIALIZED DIALOG INTERFACES
    %% ================================================================================
    
    %% ================================================================================
    %% CORE DIALOG CLASSES
    %% ================================================================================
    
    class ICAVisualizationDialog {
        <<ica visualization dialog>>
        +export_overview_requested: pyqtSignal
        +export_all_requested: pyqtSignal
        
        +ica_components: Dict[str, Any]
        +sampling_rate: float
        +is_realtime: bool
        +realtime_update_pending: bool
        +figure: Optional[Figure]
        +canvas: Optional[FigureCanvas]
        +scroll_area: QScrollArea
        +scroll_widget: QWidget
        +scroll_layout: QVBoxLayout
        +colormap_combo: QComboBox
        
        +__init__(ica_components: Dict[str, Any], sampling_rate: float, parent: Optional[Any]) void
        +update_visualization(new_ica_components: Dict[str, Any], colormap: Optional[str]) void
        +closeEvent(event: Any) void
        -_setup_ui() void
        -_create_visualization() void
        -_refresh_visualization() void
        -_update_realtime_plots() void
        -_show_component_detail(component_index: int, component_data: np.ndarray, time_vector: np.ndarray) void
        -_show_matrix_detail(matrix_type: str) void
        -_request_export_overview() void
        -_request_export_all() void
        -_export_single_component(component_index: int, component_data: np.ndarray, time_vector: np.ndarray) void
        -_export_single_matrix_with_colormap(matrix_type: str, matrix_data: np.ndarray, colormap: str) void
        +_export_single_component_worker(export_data: Dict[str, Any], progress_queue: mp.Queue)$ void
        +_export_single_matrix_worker(export_data: Dict[str, Any], progress_queue: mp.Queue)$ void
    }
    
    class AdvancedDialogsPackage {
        <<module package>>
        +ICAVisualizationDialog: Class
    }
    
    %% ================================================================================
    %% DETAIL DIALOG CLASSES (DYNAMICALLY CREATED)
    %% ================================================================================
    
    class ComponentDetailDialog {
        <<dynamic dialog>>
        +component_index: int
        +component_data: np.ndarray
        +time_vector: np.ndarray
        +sampling_rate: float
        +figure: Figure
        +canvas: FigureCanvas
        +export_btn: QPushButton
        
        +__init__(component_index: int, component_data: np.ndarray, time_vector: np.ndarray, sampling_rate: float, parent: QWidget) void
        +create_detailed_plot() void
        +export_component() void
    }
    
    class MatrixDetailDialog {
        <<dynamic dialog>>
        +matrix_type: str
        +matrix_data: np.ndarray
        +colormap: str
        +figure: Figure
        +canvas: FigureCanvas
        +colormap_combo: QComboBox
        +export_btn: QPushButton
        
        +__init__(matrix_type: str, matrix_data: np.ndarray, colormap: str, parent: QWidget) void
        +create_matrix_plot(colormap_name: str) FigureCanvas
        +on_colormap_change() void
        +export_matrix() void
    }
    
    %% ================================================================================
    %% WORKER PROCESS FUNCTIONS
    %% ================================================================================
    
    class ExportWorkerFunctions {
        <<static worker functions>>
        +_export_single_component_worker(export_data: Dict[str, Any], progress_queue: mp.Queue)$ void
        +_export_single_matrix_worker(export_data: Dict[str, Any], progress_queue: mp.Queue)$ void
        +_export_enhanced_overview_worker(export_data: Dict[str, Any], progress_queue: mp.Queue)$ void
        +_export_enhanced_all_images_worker(export_data: Dict[str, Any], progress_queue: mp.Queue)$ void
    }
    
    %% ================================================================================
    %% QT5 FRAMEWORK COMPONENTS
    %% ================================================================================
    
    class QDialog {
        <<qt5 framework>>
        +parent: Optional[QWidget]
        +modal: bool
        
        +__init__(parent: Optional[QWidget]) void
        +setWindowTitle(title: str) void
        +setModal(modal: bool) void
        +resize(width: int, height: int) void
        +show() void
        +close() void
        +closeEvent(event: QCloseEvent) void
    }
    
    class pyqtSignal {
        <<qt5 framework>>
        +emit(*args: Any) void
        +connect(slot: Callable) void
        +disconnect(slot: Optional[Callable]) void
    }
    
    class QVBoxLayout {
        <<qt5 framework>>
        +addWidget(widget: QWidget) void
        +addLayout(layout: QLayout) void
        +setContentsMargins(left: int, top: int, right: int, bottom: int) void
        +count() int
        +itemAt(index: int) QLayoutItem
    }
    
    class QHBoxLayout {
        <<qt5 framework>>
        +addWidget(widget: QWidget) void
        +addStretch() void
        +setContentsMargins(left: int, top: int, right: int, bottom: int) void
    }
    
    class QScrollArea {
        <<qt5 framework>>
        +setWidgetResizable(resizable: bool) void
        +setHorizontalScrollBarPolicy(policy: Qt.ScrollBarPolicy) void
        +setVerticalScrollBarPolicy(policy: Qt.ScrollBarPolicy) void
        +setWidget(widget: QWidget) void
    }
    
    class QWidget {
        <<qt5 framework>>
        +setMinimumHeight(height: int) void
        +setMinimumWidth(width: int) void
        +setParent(parent: Optional[QWidget]) void
        +deleteLater() void
        +layout() QLayout
    }
    
    class QLabel {
        <<qt5 framework>>
        +setText(text: str) void
        +setStyleSheet(style: str) void
        +setAlignment(alignment: Qt.Alignment) void
        +setToolTip(tooltip: str) void
    }
    
    class QPushButton {
        <<qt5 framework>>
        +clicked: pyqtSignal
        +setText(text: str) void
        +setEnabled(enabled: bool) void
        +setToolTip(tooltip: str) void
    }
    
    class QComboBox {
        <<qt5 framework>>
        +currentTextChanged: pyqtSignal[str]
        +addItem(text: str, userData: Any) void
        +currentData() Any
        +currentText() str
        +setCurrentIndex(index: int) void
        +setEnabled(enabled: bool) void
        +setToolTip(tooltip: str) void
        +count() int
        +itemData(index: int) Any
        +blockSignals(block: bool) bool
    }
    
    class QFileDialog {
        <<qt5 framework>>
        +getSaveFileName(parent: QWidget, caption: str, directory: str, filter: str)$ Tuple[str, str]
        +getExistingDirectory(parent: QWidget, caption: str, directory: str)$ str
    }
    
    class QProgressDialog {
        <<qt5 framework>>
        +setWindowTitle(title: str) void
        +setModal(modal: bool) void
        +setValue(value: int) void
        +setLabelText(text: str) void
        +show() void
        +close() void
    }
    
    class QApplication {
        <<qt5 framework>>
        +processEvents()$ void
    }
    
    class QTimer {
        <<qt5 framework>>
        +singleShot(msec: int, slot: Callable)$ void
    }
    
    class Qt {
        <<qt5 constants>>
        +AlignCenter$: Qt.Alignment
        +ScrollBarAlwaysOff$: Qt.ScrollBarPolicy
        +ScrollBarAsNeeded$: Qt.ScrollBarPolicy
    }
    
    %% ================================================================================
    %% MATPLOTLIB COMPONENTS
    %% ================================================================================
    
    class matplotlib {
        <<plotting library>>
        +use(backend: str) void
        +rcParams: Dict[str, Any]
    }
    
    class pyplot {
        <<matplotlib>>
        +figure(figsize: Tuple[float, float]) Figure
        +subplots(nrows: int, ncols: int, figsize: Tuple[float, float]) Tuple[Figure, ndarray]
        +subplot2grid(shape: Tuple[int, int], loc: Tuple[int, int], colspan: int) Axes
        +colorbar(mappable: Any, ax: Axes, shrink: float) Colorbar
        +subplots_adjust(left: float, right: float, top: float, bottom: float, hspace: float, wspace: float) void
        +tight_layout() void
        +close(fig: Figure) void
    }
    
    class Figure {
        <<matplotlib>>
        +add_subplot(nrows: int, ncols: int, index: int) Axes
        +get_axes() List[Axes]
        +canvas: FigureCanvas
        +savefig(filename: str, dpi: int, bbox_inches: str) void
        +clear() void
    }
    
    class Axes {
        <<matplotlib>>
        +imshow(data: np.ndarray, aspect: str, cmap: str, interpolation: str) AxesImage
        +plot(x: np.ndarray, y: np.ndarray, linewidth: float, color: str, alpha: float) List[Line2D]
        +hist(data: np.ndarray, bins: int, alpha: float, color: str, edgecolor: str) Tuple[np.ndarray, np.ndarray, List[Rectangle]]
        +semilogy(x: np.ndarray, y: np.ndarray, color: str, linewidth: float) List[Line2D]
        +set_title(title: str, fontsize: int, fontweight: str) void
        +set_xlabel(xlabel: str, fontsize: int) void
        +set_ylabel(ylabel: str, fontsize: int) void
        +set_xlim(left: float, right: float) void
        +set_ylim(bottom: float, top: float) void
        +set_picker(picker: bool) void
        +grid(visible: bool, alpha: float) void
        +tick_params(axis: str, which: str, labelsize: int) void
        +text(x: float, y: float, s: str, transform: Any, fontsize: int, verticalalignment: str, bbox: Dict[str, Any]) Text
        +get_images() List[AxesImage]
        +get_lines() List[Line2D]
        +set_clim(vmin: float, vmax: float) void
        +component_index: int
        +component_data: np.ndarray
        +time_vector: np.ndarray
        +matrix_type: str
    }
    
    class FigureCanvas {
        <<matplotlib.backends.backend_qt5agg>>
        +figure: Figure
        +mpl_connect(event: str, callback: Callable) int
        +draw_idle() void
        +setMinimumHeight(height: int) void
        +setMinimumWidth(width: int) void
        +setParent(parent: Optional[QWidget]) void
        +deleteLater() void
    }
    
    class AxesImage {
        <<matplotlib>>
        +set_data(data: np.ndarray) void
        +set_clim(vmin: float, vmax: float) void
    }
    
    class Line2D {
        <<matplotlib>>
        +set_data(x: np.ndarray, y: np.ndarray) void
    }
    
    class Colorbar {
        <<matplotlib>>
        +set_label(label: str, fontsize: int) void
    }
    
    %% ================================================================================
    %% SCIPY COMPONENTS
    %% ================================================================================
    
    class scipy_signal {
        <<scipy library>>
        +welch(x: np.ndarray, fs: float, nperseg: int) Tuple[np.ndarray, np.ndarray]
    }
    
    %% ================================================================================
    %% MULTIPROCESSING COMPONENTS
    %% ================================================================================
    
    class multiprocessing {
        <<stdlib>>
        +Process: Class
        +Queue: Class
    }
    
    class Process {
        <<multiprocessing>>
        +target: Callable
        +args: Tuple[Any, ...]
        +start() void
        +is_alive() bool
        +join(timeout: Optional[float]) void
    }
    
    class Queue {
        <<multiprocessing>>
        +put(item: Any) void
        +get() Any
        +get_nowait() Any
        +empty() bool
    }
    
    %% ================================================================================
    %% STANDARD LIBRARY COMPONENTS
    %% ================================================================================
    
    class numpy {
        <<stdlib>>
        +ndarray: Class
        +linspace(start: float, stop: float, num: int) ndarray
        +std(data: ndarray) float
        +mean(data: ndarray) float
        +min(data: ndarray) float
        +max(data: ndarray) float
        +ceil(x: float) int
    }
    
    class time {
        <<stdlib>>
        +time() float
        +strftime(format: str, t: Optional[time.struct_time]) str
        +localtime(timestamp: float) time.struct_time
    }
    
    class typing {
        <<stdlib>>
        +Dict
        +List
        +Any
        +Optional
        +Tuple
    }
    
    %% ================================================================================
    %% RELATIONSHIPS
    %% ================================================================================
    
    %% Package Composition
    AdvancedDialogsPackage "1" *-- "1" ICAVisualizationDialog : contains
    
    %% Inheritance
    ICAVisualizationDialog --|> QDialog : extends
    
    %% Core Component Relationships
    ICAVisualizationDialog "1" *-- "0..1" Figure : figure
    ICAVisualizationDialog "1" *-- "0..1" FigureCanvas : canvas
    ICAVisualizationDialog "1" *-- "1" QScrollArea : scroll_area
    ICAVisualizationDialog "1" *-- "1" QWidget : scroll_widget
    ICAVisualizationDialog "1" *-- "1" QVBoxLayout : scroll_layout
    ICAVisualizationDialog "1" *-- "1" QComboBox : colormap_combo
    
    %% Dynamic Dialog Creation
    ICAVisualizationDialog ..> ComponentDetailDialog : creates dynamically
    ICAVisualizationDialog ..> MatrixDetailDialog : creates dynamically
    
    ComponentDetailDialog "1" *-- "1" Figure : figure
    ComponentDetailDialog "1" *-- "1" FigureCanvas : canvas
    ComponentDetailDialog "1" *-- "1" QPushButton : export_btn
    
    MatrixDetailDialog "1" *-- "1" Figure : figure
    MatrixDetailDialog "1" *-- "1" FigureCanvas : canvas
    MatrixDetailDialog "1" *-- "1" QComboBox : colormap_combo
    MatrixDetailDialog "1" *-- "1" QPushButton : export_btn
    
    %% Signal Relationships
    ICAVisualizationDialog "1" *-- "2" pyqtSignal : signals
    QPushButton "1" *-- "1" pyqtSignal : clicked
    QComboBox "1" *-- "1" pyqtSignal : currentTextChanged
    
    %% Worker Process Dependencies
    ICAVisualizationDialog ..> ExportWorkerFunctions : uses static methods
    ICAVisualizationDialog ..> multiprocessing : uses
    ICAVisualizationDialog ..> Process : creates
    ICAVisualizationDialog ..> Queue : creates
    
    %% Qt Framework Dependencies
    ICAVisualizationDialog ..> QVBoxLayout : creates
    ICAVisualizationDialog ..> QHBoxLayout : creates
    ICAVisualizationDialog ..> QLabel : creates
    ICAVisualizationDialog ..> QPushButton : creates
    ICAVisualizationDialog ..> QFileDialog : uses
    ICAVisualizationDialog ..> QProgressDialog : creates
    ICAVisualizationDialog ..> QApplication : uses
    ICAVisualizationDialog ..> QTimer : uses
    ICAVisualizationDialog ..> Qt : uses constants
    
    %% Matplotlib Dependencies
    ICAVisualizationDialog ..> matplotlib : configures
    ICAVisualizationDialog ..> pyplot : uses
    ICAVisualizationDialog ..> Figure : creates
    ICAVisualizationDialog ..> Axes : manipulates
    ICAVisualizationDialog ..> FigureCanvas : creates
    ICAVisualizationDialog ..> AxesImage : updates
    ICAVisualizationDialog ..> Line2D : updates
    ICAVisualizationDialog ..> Colorbar : creates
    
    Figure "1" *-- "*" Axes : contains
    Figure "1" *-- "1" FigureCanvas : canvas
    Axes "1" *-- "*" AxesImage : contains
    Axes "1" *-- "*" Line2D : contains
    
    %% Scipy Dependencies
    ExportWorkerFunctions ..> scipy_signal : uses
    ComponentDetailDialog ..> scipy_signal : uses
    
    %% Standard Library Dependencies
    ICAVisualizationDialog ..> numpy : uses
    ICAVisualizationDialog ..> time : uses
    ICAVisualizationDialog ..> typing : uses
    
    ExportWorkerFunctions ..> numpy : uses
    ExportWorkerFunctions ..> matplotlib : uses
    ExportWorkerFunctions ..> pyplot : uses
    
    %% Event Handling
    Figure ..> ICAVisualizationDialog : click events
    Axes ..> ICAVisualizationDialog : picker events
    
    %% ================================================================================
    %% LOGICAL GROUPINGS
    %% ================================================================================
    
    %% Dialog Components
    ICAVisualizationDialog -.- ComponentDetailDialog : "dialog hierarchy"
    ComponentDetailDialog -.- MatrixDetailDialog : "dialog hierarchy"
    
    %% Qt Framework Components
    QDialog -.- pyqtSignal : "qt framework"
    pyqtSignal -.- QVBoxLayout : "qt framework"
    QVBoxLayout -.- QHBoxLayout : "qt framework"
    QHBoxLayout -.- QScrollArea : "qt framework"
    QScrollArea -.- QWidget : "qt framework"
    QWidget -.- QLabel : "qt framework"
    QLabel -.- QPushButton : "qt framework"
    QPushButton -.- QComboBox : "qt framework"
    
    %% Matplotlib Components
    matplotlib -.- pyplot : "plotting framework"
    pyplot -.- Figure : "plotting framework"
    Figure -.- Axes : "plotting framework"
    Axes -.- FigureCanvas : "plotting framework"
    FigureCanvas -.- AxesImage : "plotting framework"
    AxesImage -.- Line2D : "plotting framework"
    Line2D -.- Colorbar : "plotting framework"
    
    %% Multiprocessing Components
    multiprocessing -.- Process : "multiprocessing framework"
    Process -.- Queue : "multiprocessing framework"
    
    %% Standard Library Components
    numpy -.- time : "standard libraries"
    time -.- typing : "standard libraries"
    
    %% ================================================================================
    %% NOTES
    %% ================================================================================
    
    note for ICAVisualizationDialog "Advanced ICA Visualization Dialog:\n• ICA component visualization with scrollable interface for 1-16 components\n• Real-time mode support with optimized updates preventing UI blocking and memory leaks\n• Interactive visualization: click-to-detail for components and matrices with statistical analysis\n• Multi-format export: overview, individual components, batch processing with progress tracking\n• Colormap customization: 8 built-in options (Viridis, Plasma, Inferno, Magma, Coolwarm, RdBu, Spectral, Jet)\n• Memory management: proper matplotlib figure lifecycle with automatic cleanup and leak prevention\n• Matrix visualization: mixing (A) and unmixing (W) matrices with weight distributions and annotations\n• Performance optimization: selective plot data updates for real-time mode, lazy loading for initialization"
    
    note for ComponentDetailDialog "Dynamic Component Detail Analysis:\n• Detailed time series visualization with statistical overlays (mean, std, min, max)\n• Power spectral density computation using Welch's method with frequency domain analysis\n• Interactive zoom and pan capabilities for detailed signal inspection\n• High-resolution export (300 DPI) suitable for publication and documentation\n• Statistical analysis integration with automatic PSD computation and frequency band highlighting\n• Error handling for missing scipy dependencies with graceful degradation\n• Responsive layout adapting to different component data sizes and sampling rates"
    
    note for MatrixDetailDialog "Interactive Matrix Analysis Interface:\n• Detailed matrix heatmap visualization with customizable colormaps and interpolation\n• Weight distribution histogram with statistical summary (mean, std, min, max, shape)\n• Dynamic colormap selection with real-time visualization updates\n• Value annotations for small matrices (≤8x8) with readable font sizing\n• Statistical overlays and distribution analysis with histogram binning optimization\n• Export capabilities with high-resolution output and consistent styling\n• Responsive layout with proper subplot proportions (2:1 ratio for matrix:histogram)"
    
    note for ExportWorkerFunctions "Multiprocess Export Architecture:\n• CPU-intensive export operations isolated in worker processes preventing UI blocking\n• Progress tracking with real-time status updates and cancellation support\n• Multiple export types: single component, single matrix, overview, batch processing\n• High-quality output (300 DPI) with consistent styling and professional appearance\n• Memory-efficient processing with proper resource cleanup and matplotlib backend configuration\n• Error handling with detailed progress feedback and graceful failure recovery\n• Platform-independent export with proper file path handling and directory management"
    
    note "Real-Time Processing Capabilities:\n• Optimized Update Strategy: Selective plot data refreshing instead of full figure recreation\n• Memory Efficiency: Preserves matplotlib figure structure while updating component data only\n• Performance Monitoring: Adaptive update strategies based on processing load and component count\n• Timestamp Tracking: Automatic session monitoring with real-time status display\n• Thread Safety: Proper UI thread marshalling for safe cross-thread updates\n• Race Condition Prevention: Update pending flags preventing concurrent modification\n• Resource Management: Automatic cleanup of unused figures and canvas elements"
    
    note "Interactive Visualization Features:\n• Click-to-Detail: Interactive components and matrices revealing detailed analysis windows\n• Scrollable Interface: Viewport-based rendering for efficient handling of large component counts\n• Statistical Integration: Real-time computation of component statistics and frequency analysis\n• Colormap Selection: Dynamic colormap updates with real-time visualization refresh\n• Export Integration: Context-sensitive export options with progress monitoring\n• Responsive Design: Adaptive layout based on screen size and component count\n• Accessibility: Keyboard navigation and tooltip integration for enhanced usability"
    
    note "Export and Documentation System:\n• Multi-Format Support: PNG export with customizable resolution, styling, and colormap\n• Batch Processing: Automated export of all components with consistent naming conventions\n• Progress Monitoring: Real-time progress tracking with detailed status messages and cancellation\n• Documentation Quality: Publication-ready output with statistical overlays and professional styling\n• Directory Organization: Automatic file organization with timestamp and component identification\n• Error Recovery: Robust error handling with detailed feedback and graceful failure management\n• Platform Compatibility: Cross-platform export with proper file system handling"
    
    note "Advanced Technical Architecture:\n• Qt Signal/Slot Integration: Proper event-driven architecture with signal-based communication\n• Matplotlib Backend Management: Qt5Agg backend configuration with proper lifecycle control\n• Memory Leak Prevention: Systematic cleanup of matplotlib figures, canvases, and Qt widgets\n• Thread-Safe Operations: UI thread coordination with background processing isolation\n• Resource Optimization: Lazy loading, viewport rendering, and efficient data structure management\n• Error Isolation: Component-specific error handling preventing cascade failures\n• Performance Profiling: Adaptive strategies based on data size and processing complexity"
    
    note "User Experience and Workflow:\n• Modal and Non-Modal Operation: Flexible dialog management for different workflow requirements\n• Context-Sensitive Help: Tooltips and status messages providing guidance and feedback\n• Visual Feedback: Real-time status indicators, progress bars, and color-coded information\n• Workflow Integration: Seamless coordination with ICA processing services and main application\n• Customization Options: User-configurable export parameters, colormap selection, and layout preferences\n• Session Persistence: State management for real-time sessions with automatic recovery\n• Accessibility Features: Keyboard shortcuts, screen reader compatibility, and high contrast support"
```