```mermaid
classDiagram
    %% ================================================================================
    %% UI/ADVANCED/WIDGETS MODULE - ADVANCED PROCESSING WIDGET COMPONENTS
    %% ================================================================================

    %% ================================================================================
    %% CORE WIDGET CLASSES
    %% ================================================================================

    class AdvancedFilterWidget {
        <<advanced filter widget>>
        +apply_requested: pyqtSignal[dict]
        +settings_changed: pyqtSignal[dict]

        +applied: bool
        +channel_names: List[str]
        +selected_channels: List[int]
        -_processing_panel: Optional[Any]
        +filter_type_combo: QComboBox
        +filter_order_spin: QSpinBox
        +window_function_combo: QComboBox
        +ripple_label: QLabel
        +ripple_spin: QDoubleSpinBox
        +filter_channel_select_btn: QPushButton
        +filter_channel_info_label: QLabel
        +apply_adv_filter_btn: QPushButton

        +__init__(parent: Optional[Any]) void
        +update_channels(channel_names: List[str]) void
        +set_processing_panel_reference(processing_panel: Any) void
        +set_enabled(enabled: bool) void
        +get_advanced_filter_settings() Dict[str, Any]
        -_setup_ui() void
        -_open_channel_selection() void
        -_update_channel_display() void
        -_get_basic_bandpass_params() Dict[str, float]
        -_on_filter_type_changed() void
        -_toggle_advanced_filters() void
        -_on_settings_changed() void
    }

    class ICAWidget {
        <<ica analysis widget>>
        +compute_requested: pyqtSignal[dict]
        +view_components_requested: pyqtSignal[dict]
        +export_overview_requested: pyqtSignal
        +export_all_requested: pyqtSignal
        +realtime_start_requested: pyqtSignal[dict]
        +realtime_stop_requested: pyqtSignal
        +realtime_interval_changed: pyqtSignal[float]

        +channel_names: List[str]
        +selected_channels: List[int]
        +ica_results: Optional[Dict[str, Any]]
        +realtime_active: bool
        +ica_components_spin: QSpinBox
        +ica_channel_select_btn: QPushButton
        +ica_channel_info_label: QLabel
        +compute_ica_btn: QPushButton
        +view_ica_components_btn: QPushButton
        +realtime_enable_check: QCheckBox
        +interval_spin: QDoubleSpinBox
        +window_size_spin: QDoubleSpinBox
        +realtime_status_label: QLabel
        +colormap_combo: QComboBox

        +__init__(parent: Optional[Any]) void
        +update_channels(channel_names: List[str]) void
        +set_ica_results(ica_results: Dict[str, Any]) void
        +get_ica_results() Optional[Dict[str, Any]]
        +set_realtime_active(active: bool, message: str) void
        +get_colormap() str
        +set_enabled(enabled: bool) void
        +get_ica_settings() Dict[str, Any]
        -_setup_ui() void
        -_open_channel_selection() void
        -_update_channel_display() void
        -_request_ica_computation() void
        -_request_ica_visualization() void
        -_on_realtime_enable_changed(state: int) void
        -_on_interval_changed(value: float) void
    }

    class WaveletWidget {
        <<wavelet analysis widget>>
        +compute_requested: pyqtSignal[dict]
        +apply_inverse_requested: pyqtSignal[bool]
        +settings_changed: pyqtSignal[dict]

        +channel_names: List[str]
        +wavelet_results: Optional[Dict[str, Any]]
        +inverse_applied: bool
        +wavelet_type_combo: QComboBox
        +wavelet_level_spin: QSpinBox
        +wavelet_channel_combo: QComboBox
        +extension_combo: QComboBox
        +apply_denoising_check: QCheckBox
        +compute_wavelet_btn: QPushButton
        +inverse_wavelet_btn: QPushButton

        +__init__(parent: Optional[Any]) void
        +update_channels(channel_names: List[str]) void
        +set_wavelet_results(coefficients: Any, metadata: Dict[str, Any]) void
        +has_wavelet_results() bool
        +set_enabled(enabled: bool) void
        +get_wavelet_settings() Dict[str, Any]
        -_setup_ui() void
        -_request_wavelet_computation() void
        -_toggle_inverse_transform() void
        -_on_settings_changed() void
    }

    class DownsamplingWidget {
        <<downsampling widget>>
        +apply_requested: pyqtSignal[dict]
        +settings_changed: pyqtSignal[dict]

        +applied: bool
        +downsample_factor_spin: QSpinBox
        +downsample_agg_combo: QComboBox
        +apply_downsample_btn: QPushButton

        +__init__(parent: Optional[Any]) void
        +set_enabled(enabled: bool) void
        +get_downsample_settings() Dict[str, Any]
        -_setup_ui() void
        -_toggle_downsampling() void
        -_on_settings_changed() void
    }

    class AdvancedWidgetsPackage {
        <<module package>>
        +AdvancedFilterWidget: Class
        +ICAWidget: Class
        +WaveletWidget: Class
        +DownsamplingWidget: Class
    }

    %% ================================================================================
    %% EXTERNAL DIALOG CLASSES
    %% ================================================================================

    class ChannelSelectionDialog {
        <<external dialog>>
        +channel_names: List[str]
        +selected_channels: List[int]

        +__init__(channel_names: List[str], selected_channels: List[int], parent: QWidget) void
        +get_selected_channels() List[int]
        +exec_() int
        +setWindowTitle(title: str) void
    }

    class HelpButton {
        <<external utility>>
        +topic: str

        +__init__(topic: str, parent: QWidget) void
    }

    %% ================================================================================
    %% QT5 FRAMEWORK COMPONENTS
    %% ================================================================================

    class QWidget {
        <<qt5 framework>>
        +parent: Optional[QWidget]

        +__init__(parent: Optional[QWidget]) void
        +setEnabled(enabled: bool) void
        +show() void
        +hide() void
        +setVisible(visible: bool) void
        +setToolTip(tooltip: str) void
        +setStyleSheet(style: str) void
    }

    class pyqtSignal {
        <<qt5 framework>>
        +emit(*args: Any) void
        +connect(slot: Callable) void
        +disconnect(slot: Optional[Callable]) void
        +blockSignals(block: bool) bool
    }

    class QVBoxLayout {
        <<qt5 framework>>
        +addWidget(widget: QWidget) void
        +addLayout(layout: QLayout) void
        +setContentsMargins(left: int, top: int, right: int, bottom: int) void
    }

    class QHBoxLayout {
        <<qt5 framework>>
        +addWidget(widget: QWidget) void
        +addLayout(layout: QLayout) void
        +addStretch() void
    }

    class QGroupBox {
        <<qt5 framework>>
        +title: str

        +__init__(title: str) void
        +setTitle(title: str) void
    }

    class QLabel {
        <<qt5 framework>>
        +setText(text: str) void
        +text() str
        +setStyleSheet(style: str) void
        +setVisible(visible: bool) void
        +hide() void
        +show() void
    }

    class QPushButton {
        <<qt5 framework>>
        +clicked: pyqtSignal
        +setText(text: str) void
        +setEnabled(enabled: bool) void
        +setStyleSheet(style: str) void
        +setToolTip(tooltip: str) void
    }

    class QSpinBox {
        <<qt5 framework>>
        +valueChanged: pyqtSignal[int]
        +setRange(min: int, max: int) void
        +setValue(value: int) void
        +value() int
        +setToolTip(tooltip: str) void
    }

    class QDoubleSpinBox {
        <<qt5 framework>>
        +valueChanged: pyqtSignal[float]
        +setRange(min: float, max: float) void
        +setValue(value: float) void
        +value() float
        +setSuffix(suffix: str) void
        +setDecimals(decimals: int) void
        +setSingleStep(step: float) void
        +setToolTip(tooltip: str) void
    }

    class QComboBox {
        <<qt5 framework>>
        +currentIndexChanged: pyqtSignal[int]
        +currentTextChanged: pyqtSignal[str]
        +addItem(text: str, userData: Any) void
        +currentData() Any
        +currentText() str
        +currentIndex() int
        +setCurrentIndex(index: int) void
        +count() int
        +itemData(index: int) Any
        +clear() void
        +setEnabled(enabled: bool) void
        +setToolTip(tooltip: str) void
        +setVisible(visible: bool) void
        +blockSignals(block: bool) bool
    }

    class QCheckBox {
        <<qt5 framework>>
        +stateChanged: pyqtSignal[int]
        +setChecked(checked: bool) void
        +isChecked() bool
        +setEnabled(enabled: bool) void
        +setToolTip(tooltip: str) void
        +blockSignals(block: bool) bool
    }

    class QFrame {
        <<qt5 framework>>
        +setFrameShape(shape: QFrame.Shape) void
        +setFrameShadow(shadow: QFrame.Shadow) void
        +HLine$: QFrame.Shape
        +Sunken$: QFrame.Shadow
    }

    class QDialog {
        <<qt5 framework>>
        +Accepted$: int
        +exec_() int
        +setWindowTitle(title: str) void
    }

    class QMessageBox {
        <<qt5 framework>>
        +warning(parent: QWidget, title: str, text: str)$ int
        +information(parent: QWidget, title: str, text: str)$ int
        +Yes$: int
        +No$: int
    }

    %% ================================================================================
    %% BRAINFLOW COMPONENTS
    %% ================================================================================

    class FilterTypes {
        <<brainflow enum>>
        +BUTTERWORTH$: FilterTypes
        +CHEBYSHEV_TYPE_1$: FilterTypes
        +BESSEL$: FilterTypes
        +BUTTERWORTH_ZERO_PHASE$: FilterTypes
        +CHEBYSHEV_TYPE_1_ZERO_PHASE$: FilterTypes
        +BESSEL_ZERO_PHASE$: FilterTypes
        +value: int
    }

    class WindowOperations {
        <<brainflow enum>>
        +NO_WINDOW$: WindowOperations
        +HANNING$: WindowOperations
        +HAMMING$: WindowOperations
        +BLACKMAN_HARRIS$: WindowOperations
        +value: int
    }

    class WaveletTypes {
        <<brainflow enum>>
        +HAAR$: WaveletTypes
        +DB1$: WaveletTypes
        +DB2$: WaveletTypes
        +DB3$: WaveletTypes
        +DB4$: WaveletTypes
        +DB5$: WaveletTypes
        +DB6$: WaveletTypes
        +DB7$: WaveletTypes
        +DB8$: WaveletTypes
        +DB9$: WaveletTypes
        +DB10$: WaveletTypes
        +DB11$: WaveletTypes
        +DB12$: WaveletTypes
        +DB13$: WaveletTypes
        +DB14$: WaveletTypes
        +DB15$: WaveletTypes
        +BIOR1_1$: WaveletTypes
        +BIOR1_3$: WaveletTypes
        +BIOR1_5$: WaveletTypes
        +BIOR2_2$: WaveletTypes
        +BIOR2_4$: WaveletTypes
        +BIOR2_6$: WaveletTypes
        +BIOR2_8$: WaveletTypes
        +BIOR3_1$: WaveletTypes
        +BIOR3_3$: WaveletTypes
        +BIOR3_5$: WaveletTypes
        +BIOR3_7$: WaveletTypes
        +BIOR3_9$: WaveletTypes
        +BIOR4_4$: WaveletTypes
        +BIOR5_5$: WaveletTypes
        +BIOR6_8$: WaveletTypes
        +COIF1$: WaveletTypes
        +COIF2$: WaveletTypes
        +COIF3$: WaveletTypes
        +COIF4$: WaveletTypes
        +COIF5$: WaveletTypes
        +SYM2$: WaveletTypes
        +SYM3$: WaveletTypes
        +SYM4$: WaveletTypes
        +SYM5$: WaveletTypes
        +SYM6$: WaveletTypes
        +SYM7$: WaveletTypes
        +SYM8$: WaveletTypes
        +SYM9$: WaveletTypes
        +SYM10$: WaveletTypes
        +value: int
    }

    class WaveletExtensionTypes {
        <<brainflow enum>>
        +SYMMETRIC$: WaveletExtensionTypes
        +PERIODIC$: WaveletExtensionTypes
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
    %% STANDARD LIBRARY COMPONENTS
    %% ================================================================================

    class logging {
        <<stdlib>>
        +info(message: str) void
        +debug(message: str) void
        +warning(message: str) void
        +error(message: str) void
    }

    class typing {
        <<stdlib>>
        +Dict
        +List
        +Any
        +Optional
    }

    %% ================================================================================
    %% RELATIONSHIPS
    %% ================================================================================

    %% Package Composition
    AdvancedWidgetsPackage "1" *-- "1" AdvancedFilterWidget : contains
    AdvancedWidgetsPackage "1" *-- "1" ICAWidget : contains
    AdvancedWidgetsPackage "1" *-- "1" WaveletWidget : contains
    AdvancedWidgetsPackage "1" *-- "1" DownsamplingWidget : contains

    %% Inheritance
    AdvancedFilterWidget --|> QWidget : extends
    ICAWidget --|> QWidget : extends
    WaveletWidget --|> QWidget : extends
    DownsamplingWidget --|> QWidget : extends

    %% Core Component Relationships
    AdvancedFilterWidget "1" *-- "1" QVBoxLayout : layout
    AdvancedFilterWidget "1" *-- "1" QComboBox : filter_type_combo
    AdvancedFilterWidget "1" *-- "1" QSpinBox : filter_order_spin
    AdvancedFilterWidget "1" *-- "1" QComboBox : window_function_combo
    AdvancedFilterWidget "1" *-- "1" QDoubleSpinBox : ripple_spin
    AdvancedFilterWidget "1" *-- "1" QPushButton : filter_channel_select_btn
    AdvancedFilterWidget "1" *-- "1" QPushButton : apply_adv_filter_btn
    AdvancedFilterWidget "1" *-- "1" QLabel : filter_channel_info_label
    AdvancedFilterWidget "1" *-- "1" QLabel : ripple_label

    ICAWidget "1" *-- "1" QVBoxLayout : layout
    ICAWidget "1" *-- "1" QSpinBox : ica_components_spin
    ICAWidget "1" *-- "1" QPushButton : ica_channel_select_btn
    ICAWidget "1" *-- "1" QPushButton : compute_ica_btn
    ICAWidget "1" *-- "1" QPushButton : view_ica_components_btn
    ICAWidget "1" *-- "1" QCheckBox : realtime_enable_check
    ICAWidget "1" *-- "1" QDoubleSpinBox : interval_spin
    ICAWidget "1" *-- "1" QDoubleSpinBox : window_size_spin
    ICAWidget "1" *-- "1" QLabel : realtime_status_label
    ICAWidget "1" *-- "1" QComboBox : colormap_combo

    WaveletWidget "1" *-- "1" QVBoxLayout : layout
    WaveletWidget "1" *-- "1" QComboBox : wavelet_type_combo
    WaveletWidget "1" *-- "1" QSpinBox : wavelet_level_spin
    WaveletWidget "1" *-- "1" QComboBox : wavelet_channel_combo
    WaveletWidget "1" *-- "1" QComboBox : extension_combo
    WaveletWidget "1" *-- "1" QCheckBox : apply_denoising_check
    WaveletWidget "1" *-- "1" QPushButton : compute_wavelet_btn
    WaveletWidget "1" *-- "1" QPushButton : inverse_wavelet_btn

    DownsamplingWidget "1" *-- "1" QVBoxLayout : layout
    DownsamplingWidget "1" *-- "1" QSpinBox : downsample_factor_spin
    DownsamplingWidget "1" *-- "1" QComboBox : downsample_agg_combo
    DownsamplingWidget "1" *-- "1" QPushButton : apply_downsample_btn

    %% Signal Relationships
    AdvancedFilterWidget "1" *-- "2" pyqtSignal : signals
    ICAWidget "1" *-- "7" pyqtSignal : signals
    WaveletWidget "1" *-- "3" pyqtSignal : signals
    DownsamplingWidget "1" *-- "2" pyqtSignal : signals

    %% Qt Component Signal Connections
    QPushButton "1" *-- "1" pyqtSignal : clicked
    QSpinBox "1" *-- "1" pyqtSignal : valueChanged
    QDoubleSpinBox "1" *-- "1" pyqtSignal : valueChanged
    QComboBox "1" *-- "2" pyqtSignal : currentIndexChanged, currentTextChanged
    QCheckBox "1" *-- "1" pyqtSignal : stateChanged

    %% External Dependencies
    AdvancedFilterWidget ..> ChannelSelectionDialog : creates
    ICAWidget ..> ChannelSelectionDialog : creates
    AdvancedFilterWidget ..> HelpButton : uses
    ICAWidget ..> HelpButton : uses
    WaveletWidget ..> HelpButton : uses
    DownsamplingWidget ..> HelpButton : uses

    %% BrainFlow Dependencies
    AdvancedFilterWidget ..> FilterTypes : uses
    AdvancedFilterWidget ..> WindowOperations : uses
    WaveletWidget ..> WaveletTypes : uses
    WaveletWidget ..> WaveletExtensionTypes : uses
    DownsamplingWidget ..> AggOperations : uses

    %% Qt Framework Dependencies
    AdvancedFilterWidget ..> QVBoxLayout : creates
    AdvancedFilterWidget ..> QHBoxLayout : creates
    AdvancedFilterWidget ..> QGroupBox : creates
    AdvancedFilterWidget ..> QLabel : creates
    AdvancedFilterWidget ..> QPushButton : creates
    AdvancedFilterWidget ..> QSpinBox : creates
    AdvancedFilterWidget ..> QDoubleSpinBox : creates
    AdvancedFilterWidget ..> QComboBox : creates
    AdvancedFilterWidget ..> QMessageBox : uses
    AdvancedFilterWidget ..> QDialog : uses

    ICAWidget ..> QVBoxLayout : creates
    ICAWidget ..> QHBoxLayout : creates
    ICAWidget ..> QGroupBox : creates
    ICAWidget ..> QLabel : creates
    ICAWidget ..> QPushButton : creates
    ICAWidget ..> QSpinBox : creates
    ICAWidget ..> QDoubleSpinBox : creates
    ICAWidget ..> QComboBox : creates
    ICAWidget ..> QCheckBox : creates
    ICAWidget ..> QFrame : creates
    ICAWidget ..> QDialog : uses

    WaveletWidget ..> QVBoxLayout : creates
    WaveletWidget ..> QHBoxLayout : creates
    WaveletWidget ..> QGroupBox : creates
    WaveletWidget ..> QLabel : creates
    WaveletWidget ..> QPushButton : creates
    WaveletWidget ..> QSpinBox : creates
    WaveletWidget ..> QComboBox : creates
    WaveletWidget ..> QCheckBox : creates

    DownsamplingWidget ..> QVBoxLayout : creates
    DownsamplingWidget ..> QHBoxLayout : creates
    DownsamplingWidget ..> QGroupBox : creates
    DownsamplingWidget ..> QLabel : creates
    DownsamplingWidget ..> QPushButton : creates
    DownsamplingWidget ..> QSpinBox : creates
    DownsamplingWidget ..> QComboBox : creates

    %% Standard Library Dependencies
    AdvancedFilterWidget ..> logging : uses
    AdvancedFilterWidget ..> typing : uses
    ICAWidget ..> typing : uses
    WaveletWidget ..> typing : uses
    DownsamplingWidget ..> typing : uses

    %% ================================================================================
    %% LOGICAL GROUPINGS
    %% ================================================================================

    %% Widget Categories
    AdvancedFilterWidget -.- ICAWidget : "advanced analysis widgets"
    ICAWidget -.- WaveletWidget : "advanced analysis widgets"
    WaveletWidget -.- DownsamplingWidget : "advanced analysis widgets"

    %% Qt Framework Components
    QWidget -.- pyqtSignal : "qt framework"
    pyqtSignal -.- QVBoxLayout : "qt framework"
    QVBoxLayout -.- QHBoxLayout : "qt framework"
    QHBoxLayout -.- QGroupBox : "qt framework"
    QGroupBox -.- QLabel : "qt framework"
    QLabel -.- QPushButton : "qt framework"
    QPushButton -.- QSpinBox : "qt framework"
    QSpinBox -.- QDoubleSpinBox : "qt framework"
    QDoubleSpinBox -.- QComboBox : "qt framework"
    QComboBox -.- QCheckBox : "qt framework"
    QCheckBox -.- QFrame : "qt framework"

    %% BrainFlow Components
    FilterTypes -.- WindowOperations : "brainflow enums"
    WindowOperations -.- WaveletTypes : "brainflow enums"
    WaveletTypes -.- WaveletExtensionTypes : "brainflow enums"
    WaveletExtensionTypes -.- AggOperations : "brainflow enums"

    %% Standard Library Components
    logging -.- typing : "standard libraries"
```
