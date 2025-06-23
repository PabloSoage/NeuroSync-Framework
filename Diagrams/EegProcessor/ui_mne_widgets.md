```mermaid
classDiagram
    %% ================================================================================
    %% UI/MNE/WIDGETS MODULE - MNE-SPECIFIC USER INTERFACE COMPONENTS
    %% ================================================================================

    %% ================================================================================
    %% CORE WIDGET CLASSES
    %% ================================================================================

    class MNEConversionWidget {
        <<mne conversion widget>>
        +conversion_requested: pyqtSignal[dict]
        +conversion_cancelled: pyqtSignal
        +channel_selection_requested: pyqtSignal[str]
        +realtime_requested: pyqtSignal[dict]
        +realtime_stopped: pyqtSignal
        +realtime_param_changed: pyqtSignal[str, object]

        +conversion_mode_combo: QComboBox
        +duration_spin: QSpinBox
        +convert_to_v_check: QCheckBox
        +use_filters_check: QCheckBox
        +filter_status: QLabel
        +update_interval_spin: QSpinBox
        +performance_warning: QLabel
        +dynamic_update_label: QLabel
        +conversion_channels_label: QLabel
        +select_conversion_channels_btn: QPushButton
        +convert_btn: QPushButton
        +start_realtime_btn: QPushButton
        +stop_realtime_btn: QPushButton
        +cancel_btn: QPushButton
        +conversion_progress: QProgressBar
        +mode_info_label: QLabel
        +realtime_params_widget: QWidget
        +performance_channel_widget: QWidget

        +__init__(parent: Optional[QWidget]) void
        +setup_ui() void
        +get_conversion_parameters() Dict[str, Any]
        +get_realtime_parameters() Dict[str, Any]
        +set_conversion_state(converting: bool) void
        +set_realtime_state(active: bool) void
        +set_enabled(enabled: bool) void
        +update_channel_info(channel_info: str) void
        +update_filter_status(status_text: str, is_active: bool) void
        +reset_state() void
        -_setup_conversion_mode(layout: QVBoxLayout) void
        -_setup_conversion_parameters(layout: QVBoxLayout) void
        -_setup_realtime_parameters(layout: QVBoxLayout) void
        -_setup_performance_mode_channels(layout: QVBoxLayout) void
        -_setup_conversion_controls(layout: QVBoxLayout) void
        -_on_mode_changed() void
        -_request_conversion() void
        -_request_realtime() void
        -_update_performance_warning(value: int) void
    }

    class MNEVisualizationWidget {
        <<mne visualization widget>>
        +visualization_requested: pyqtSignal[dict]
        +visualization_cancelled: pyqtSignal
        +channel_selection_requested: pyqtSignal[str]
        +plot_type_changed: pyqtSignal[str]
        +freq_range_changed: pyqtSignal[int, int]
        +psd_mode_changed: pyqtSignal[bool]
        +topomap_band_changed: pyqtSignal[int, int]

        +plot_type_combo: QComboBox
        +freq_min_spin: QSpinBox
        +freq_max_spin: QSpinBox
        +topomap_band_combo: QComboBox
        +topomap_freq_min_spin: QSpinBox
        +topomap_freq_max_spin: QSpinBox
        +topomap_range_label: QLabel
        +selected_channels_label: QLabel
        +realtime_channel_indicator: QLabel
        +select_channels_btn: QPushButton
        +psd_individual_check: QCheckBox
        +psd_mode_info: QLabel
        +realtime_viz_indicator: QLabel
        +plot_btn: QPushButton
        +cancel_plot_btn: QPushButton
        +plot_progress: QProgressBar
        +plot_display: QLabel

        +__init__(parent: Optional[QWidget]) void
        +setup_ui() void
        +get_visualization_parameters() Dict[str, Any]
        +set_visualization_state(visualizing: bool) void
        +set_enabled(enabled: bool) void
        +set_realtime_mode(active: bool) void
        +update_channel_info(channel_info: str) void
        +display_plot(plot_data: str) void
        +reset_state() void
        -_setup_plot_selection(layout: QVBoxLayout) void
        -_setup_topomap_controls(layout: QVBoxLayout) void
        -_setup_channel_selection(layout: QVBoxLayout) void
        -_setup_psd_options(layout: QVBoxLayout) void
        -_setup_visualization_controls(layout: QVBoxLayout) void
        -_setup_plot_display(layout: QVBoxLayout) void
        -_emit_freq_range_change() void
        -_emit_topomap_band_change() void
        -_on_topomap_band_changed() void
        -_update_psd_mode_info() void
        -_request_visualization() void
        -_get_topomap_frequency_range() Tuple[int, int]
    }

    class MNEStatusWidget {
        <<mne status monitoring widget>>
        +realtime_info: QLabel
        +status_text: QTextEdit

        +__init__(parent: Optional[QWidget]) void
        +setup_ui() void
        +add_status_message(message: str) void
        +clear_status() void
        +update_realtime_status(status_info: Dict[str, Any]) void
        +add_performance_warning(interval: float, processing_time: float) void
        +add_channel_update_message(old_count: int, new_count: int) void
        +add_optimization_message(channels_selected: int, total_channels: int) void
    }

    class ChannelSelectionDialog {
        <<channel selection dialog>>
        +channel_names: List[str]
        +selected_channels: List[int]
        +checkboxes: List[QCheckBox]
        +info_label: QLabel

        +__init__(channel_names: List[str], selected_channels: Optional[List[int]], parent: Optional[QWidget]) void
        +setup_ui() void
        +apply_dark_theme() void
        +select_all() void
        +deselect_all() void
        +update_info_label() void
        +get_selected_channels() List[int]
    }

    class MNEWidgetsPackage {
        <<module package>>
        +MNEConversionWidget: Class
        +MNEVisualizationWidget: Class
        +MNEStatusWidget: Class
        +ChannelSelectionDialog: Class
    }

    %% ================================================================================
    %% EXTERNAL UTILITY CLASSES
    %% ================================================================================

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
        +setVisible(visible: bool) void
        +show() void
        +hide() void
        +setToolTip(tooltip: str) void
        +setStyleSheet(style: str) void
        +setLayout(layout: QLayout) void
        +size() QSize
    }

    class QDialog {
        <<qt5 framework>>
        +Accepted$: int
        +Rejected$: int

        +__init__(parent: Optional[QWidget]) void
        +setWindowTitle(title: str) void
        +setModal(modal: bool) void
        +resize(width: int, height: int) void
        +exec_() int
        +accept() void
        +reject() void
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
    }

    class QHBoxLayout {
        <<qt5 framework>>
        +addWidget(widget: QWidget) void
        +addLayout(layout: QLayout) void
        +addStretch() void
    }

    class QGridLayout {
        <<qt5 framework>>
        +addWidget(widget: QWidget, row: int, column: int) void
        +setSpacing(spacing: int) void
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
        +setPixmap(pixmap: QPixmap) void
        +setScaledContents(scale: bool) void
        +setAlignment(alignment: Qt.Alignment) void
        +setWordWrap(wrap: bool) void
        +clear() void
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
        +setSuffix(suffix: str) void
        +setToolTip(tooltip: str) void
    }

    class QCheckBox {
        <<qt5 framework>>
        +stateChanged: pyqtSignal[int]
        +toggled: pyqtSignal[bool]
        +setChecked(checked: bool) void
        +isChecked() bool
        +setEnabled(enabled: bool) void
        +setToolTip(tooltip: str) void
    }

    class QComboBox {
        <<qt5 framework>>
        +currentIndexChanged: pyqtSignal[int]
        +currentTextChanged: pyqtSignal[str]
        +addItem(text: str, userData: Any) void
        +addItems(items: List[str]) void
        +currentData() Any
        +currentText() str
        +currentIndex() int
        +setCurrentText(text: str) void
        +setCurrentIndex(index: int) void
        +setEnabled(enabled: bool) void
        +setToolTip(tooltip: str) void
    }

    class QProgressBar {
        <<qt5 framework>>
        +setValue(value: int) void
        +setRange(min: int, max: int) void
        +setVisible(visible: bool) void
    }

    class QTextEdit {
        <<qt5 framework>>
        +append(text: str) void
        +clear() void
        +setReadOnly(readOnly: bool) void
        +setMaximumHeight(height: int) void
        +setStyleSheet(style: str) void
    }

    class QScrollArea {
        <<qt5 framework>>
        +setWidgetResizable(resizable: bool) void
        +setWidget(widget: QWidget) void
        +setMaximumHeight(height: int) void
    }

    class QFrame {
        <<qt5 framework>>
        +setFrameShape(shape: QFrame.Shape) void
        +setFrameShadow(shadow: QFrame.Shadow) void
    }

    class QDialogButtonBox {
        <<qt5 framework>>
        +Ok$: int
        +Cancel$: int
        +accepted: pyqtSignal
        +rejected: pyqtSignal

        +__init__(buttons: int) void
    }

    class QPixmap {
        <<qt5 framework>>
        +loadFromData(data: bytes) bool
        +isNull() bool
        +scaled(size: QSize, aspectRatioMode: Qt.AspectRatioMode, transformMode: Qt.TransformationMode) QPixmap
    }

    class QSize {
        <<qt5 framework>>
        +width() int
        +height() int
    }

    class Qt {
        <<qt5 constants>>
        +AlignCenter$: Qt.Alignment
        +KeepAspectRatio$: Qt.AspectRatioMode
        +SmoothTransformation$: Qt.TransformationMode
    }

    %% ================================================================================
    %% STANDARD LIBRARY COMPONENTS
    %% ================================================================================

    class base64 {
        <<stdlib>>
        +b64decode(s: str) bytes
    }

    class logging {
        <<stdlib>>
        +error(message: str) void
        +info(message: str) void
        +debug(message: str) void
    }

    class time {
        <<stdlib>>
        +strftime(format: str) str
    }

    class typing {
        <<stdlib>>
        +Any
        +Optional
        +Dict
        +List
        +Tuple
    }

    %% ================================================================================
    %% RELATIONSHIPS
    %% ================================================================================

    %% Package Composition
    MNEWidgetsPackage "1" *-- "1" MNEConversionWidget : contains
    MNEWidgetsPackage "1" *-- "1" MNEVisualizationWidget : contains
    MNEWidgetsPackage "1" *-- "1" MNEStatusWidget : contains
    MNEWidgetsPackage "1" *-- "1" ChannelSelectionDialog : contains

    %% Inheritance
    MNEConversionWidget --|> QWidget : extends
    MNEVisualizationWidget --|> QWidget : extends
    MNEStatusWidget --|> QWidget : extends
    ChannelSelectionDialog --|> QDialog : extends

    %% Core Component Relationships - MNEConversionWidget
    MNEConversionWidget "1" *-- "1" QComboBox : conversion_mode_combo
    MNEConversionWidget "1" *-- "1" QSpinBox : duration_spin
    MNEConversionWidget "1" *-- "1" QCheckBox : convert_to_v_check
    MNEConversionWidget "1" *-- "1" QCheckBox : use_filters_check
    MNEConversionWidget "1" *-- "1" QSpinBox : update_interval_spin
    MNEConversionWidget "1" *-- "1" QPushButton : select_conversion_channels_btn
    MNEConversionWidget "1" *-- "1" QPushButton : convert_btn
    MNEConversionWidget "1" *-- "1" QPushButton : start_realtime_btn
    MNEConversionWidget "1" *-- "1" QPushButton : stop_realtime_btn
    MNEConversionWidget "1" *-- "1" QPushButton : cancel_btn
    MNEConversionWidget "1" *-- "1" QProgressBar : conversion_progress
    MNEConversionWidget "1" *-- "*" QLabel : various labels
    MNEConversionWidget "1" *-- "2" QWidget : realtime_params_widget, performance_channel_widget

    %% Core Component Relationships - MNEVisualizationWidget
    MNEVisualizationWidget "1" *-- "1" QComboBox : plot_type_combo
    MNEVisualizationWidget "1" *-- "2" QSpinBox : freq_min_spin, freq_max_spin
    MNEVisualizationWidget "1" *-- "1" QComboBox : topomap_band_combo
    MNEVisualizationWidget "1" *-- "2" QSpinBox : topomap_freq_min_spin, topomap_freq_max_spin
    MNEVisualizationWidget "1" *-- "1" QPushButton : select_channels_btn
    MNEVisualizationWidget "1" *-- "1" QCheckBox : psd_individual_check
    MNEVisualizationWidget "1" *-- "1" QPushButton : plot_btn
    MNEVisualizationWidget "1" *-- "1" QPushButton : cancel_plot_btn
    MNEVisualizationWidget "1" *-- "1" QProgressBar : plot_progress
    MNEVisualizationWidget "1" *-- "1" QLabel : plot_display
    MNEVisualizationWidget "1" *-- "*" QLabel : various status labels

    %% Core Component Relationships - MNEStatusWidget
    MNEStatusWidget "1" *-- "1" QLabel : realtime_info
    MNEStatusWidget "1" *-- "1" QTextEdit : status_text

    %% Core Component Relationships - ChannelSelectionDialog
    ChannelSelectionDialog "1" *-- "*" QCheckBox : checkboxes
    ChannelSelectionDialog "1" *-- "1" QLabel : info_label
    ChannelSelectionDialog "1" *-- "1" QScrollArea : scroll area
    ChannelSelectionDialog "1" *-- "1" QFrame : container frame
    ChannelSelectionDialog "1" *-- "1" QDialogButtonBox : button box

    %% Signal Relationships
    MNEConversionWidget "1" *-- "6" pyqtSignal : signals
    MNEVisualizationWidget "1" *-- "8" pyqtSignal : signals
    QPushButton "1" *-- "1" pyqtSignal : clicked
    QSpinBox "1" *-- "1" pyqtSignal : valueChanged
    QCheckBox "1" *-- "2" pyqtSignal : stateChanged, toggled
    QComboBox "1" *-- "2" pyqtSignal : currentIndexChanged, currentTextChanged
    QDialogButtonBox "1" *-- "2" pyqtSignal : accepted, rejected

    %% Layout Relationships
    MNEConversionWidget "1" *-- "1" QVBoxLayout : main layout
    MNEVisualizationWidget "1" *-- "1" QVBoxLayout : main layout
    MNEStatusWidget "1" *-- "1" QVBoxLayout : main layout
    ChannelSelectionDialog "1" *-- "1" QVBoxLayout : main layout
    ChannelSelectionDialog "1" *-- "1" QGridLayout : checkbox grid

    %% External Dependencies
    MNEConversionWidget ..> HelpButton : uses

    %% Qt Framework Dependencies
    MNEConversionWidget ..> QVBoxLayout : creates
    MNEConversionWidget ..> QHBoxLayout : creates
    MNEConversionWidget ..> QGroupBox : creates
    MNEConversionWidget ..> QLabel : creates
    MNEConversionWidget ..> QPushButton : creates
    MNEConversionWidget ..> QSpinBox : creates
    MNEConversionWidget ..> QCheckBox : creates
    MNEConversionWidget ..> QComboBox : creates
    MNEConversionWidget ..> QProgressBar : creates

    MNEVisualizationWidget ..> QVBoxLayout : creates
    MNEVisualizationWidget ..> QHBoxLayout : creates
    MNEVisualizationWidget ..> QGroupBox : creates
    MNEVisualizationWidget ..> QLabel : creates
    MNEVisualizationWidget ..> QPushButton : creates
    MNEVisualizationWidget ..> QSpinBox : creates
    MNEVisualizationWidget ..> QCheckBox : creates
    MNEVisualizationWidget ..> QComboBox : creates
    MNEVisualizationWidget ..> QProgressBar : creates
    MNEVisualizationWidget ..> QPixmap : uses
    MNEVisualizationWidget ..> Qt : uses constants

    MNEStatusWidget ..> QVBoxLayout : creates
    MNEStatusWidget ..> QGroupBox : creates
    MNEStatusWidget ..> QLabel : creates
    MNEStatusWidget ..> QTextEdit : creates

    ChannelSelectionDialog ..> QVBoxLayout : creates
    ChannelSelectionDialog ..> QHBoxLayout : creates
    ChannelSelectionDialog ..> QGridLayout : creates
    ChannelSelectionDialog ..> QLabel : creates
    ChannelSelectionDialog ..> QPushButton : creates
    ChannelSelectionDialog ..> QCheckBox : creates
    ChannelSelectionDialog ..> QScrollArea : creates
    ChannelSelectionDialog ..> QFrame : creates
    ChannelSelectionDialog ..> QDialogButtonBox : creates

    %% Standard Library Dependencies
    MNEVisualizationWidget ..> base64 : uses
    MNEVisualizationWidget ..> logging : uses
    MNEStatusWidget ..> time : uses

    MNEConversionWidget ..> typing : uses
    MNEVisualizationWidget ..> typing : uses
    MNEStatusWidget ..> typing : uses
    ChannelSelectionDialog ..> typing : uses

    %% ================================================================================
    %% LOGICAL GROUPINGS
    %% ================================================================================

    %% Core Widget Categories
    MNEConversionWidget -.- MNEVisualizationWidget : "mne operation widgets"
    MNEVisualizationWidget -.- MNEStatusWidget : "mne operation widgets"
    MNEStatusWidget -.- ChannelSelectionDialog : "mne operation widgets"

    %% Qt Framework Components
    QWidget -.- QDialog : "qt framework"
    QDialog -.- pyqtSignal : "qt framework"
    pyqtSignal -.- QVBoxLayout : "qt framework"
    QVBoxLayout -.- QHBoxLayout : "qt framework"
    QHBoxLayout -.- QGridLayout : "qt framework"
    QGridLayout -.- QGroupBox : "qt framework"
    QGroupBox -.- QLabel : "qt framework"
    QLabel -.- QPushButton : "qt framework"
    QPushButton -.- QSpinBox : "qt framework"
    QSpinBox -.- QCheckBox : "qt framework"
    QCheckBox -.- QComboBox : "qt framework"
    QComboBox -.- QProgressBar : "qt framework"
    QProgressBar -.- QTextEdit : "qt framework"
    QTextEdit -.- QScrollArea : "qt framework"
    QScrollArea -.- QFrame : "qt framework"
    QFrame -.- QDialogButtonBox : "qt framework"
    QDialogButtonBox -.- QPixmap : "qt framework"
    QPixmap -.- QSize : "qt framework"
    QSize -.- Qt : "qt framework"

    %% Standard Library Components
    base64 -.- logging : "standard libraries"
    logging -.- time : "standard libraries"
    time -.- typing : "standard libraries"
```
