from typing import Any, Optional, Dict

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QProgressBar,
)

from ....utils.help_system import HelpButton


class MNEConversionWidget(QWidget):
    """Widget specialized for MNE data conversion operations."""

    # Signals
    conversion_requested = pyqtSignal(dict)  # Emit conversion parameters
    conversion_cancelled = pyqtSignal()
    channel_selection_requested = pyqtSignal(str)  # conversion/visualization
    realtime_requested = pyqtSignal(dict)  # Emit real-time parameters
    realtime_stopped = pyqtSignal()

    # Add new signal for dynamic parameter updates
    realtime_param_changed = pyqtSignal(str, object)  # param_name, value

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the MNE conversion widget."""
        super().__init__(parent)
        self.setup_ui()
        self.reset_state()

    def setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)

        # Conversion group
        conversion_group = QGroupBox("Convert to MNE Format")
        conversion_layout = QVBoxLayout(conversion_group)

        # Header with help
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("MNE Integration"))
        header_layout.addWidget(HelpButton("mne", self))
        header_layout.addStretch()
        conversion_layout.addLayout(header_layout)

        # Description
        conversion_layout.addWidget(
            QLabel("Convert BrainFlow data to MNE format for advanced analysis")
        )

        # Conversion mode
        self._setup_conversion_mode(conversion_layout)

        # Parameters
        self._setup_conversion_parameters(conversion_layout)

        # Channel selection for performance mode
        self._setup_performance_mode_channels(conversion_layout)

        # Control buttons
        self._setup_conversion_controls(conversion_layout)

        # Progress bar
        self.conversion_progress = QProgressBar()
        self.conversion_progress.setVisible(False)
        conversion_layout.addWidget(self.conversion_progress)

        layout.addWidget(conversion_group)

    def _setup_conversion_mode(self, layout: QVBoxLayout) -> None:
        """Setup conversion mode selection."""
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Conversion Mode:"))

        self.conversion_mode_combo = QComboBox()
        self.conversion_mode_combo.addItems(
            [
                "Flexible Mode (All Channels)",
                "Performance Mode (Selected Only)",
                "Real-time Mode (Auto-updating)",
            ]
        )
        self.conversion_mode_combo.setCurrentText("Flexible Mode (All Channels)")
        self.conversion_mode_combo.currentTextChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.conversion_mode_combo)

        self.mode_info_label = QLabel(
            "ℹ️ Converts all channels, apply selection during visualization"
        )
        self.mode_info_label.setStyleSheet(
            "color: #888888; font-style: italic; font-size: 10px;"
        )
        mode_layout.addWidget(self.mode_info_label)
        mode_layout.addStretch()

        layout.addLayout(mode_layout)

    def _setup_conversion_parameters(self, layout: QVBoxLayout) -> None:
        """Setup conversion parameters."""
        params_layout = QHBoxLayout()

        params_layout.addWidget(QLabel("Data Duration (seconds):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 60)
        self.duration_spin.setValue(10)
        params_layout.addWidget(self.duration_spin)

        params_layout.addWidget(QLabel("Auto Convert to V:"))
        self.convert_to_v_check = QCheckBox()
        self.convert_to_v_check.setChecked(True)
        params_layout.addWidget(self.convert_to_v_check)

        layout.addLayout(params_layout)

        # Add checkbox for using processing panel filters
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Use Processing Panel Filters:"))
        self.use_filters_check = QCheckBox()
        self.use_filters_check.setChecked(True)
        self.use_filters_check.setToolTip(
            "Apply bandpass, notch, and detrend filters from the Processing Panel (if active)"
        )
        filter_layout.addWidget(self.use_filters_check)

        # Add filter status indicator
        self.filter_status = QLabel("(No filters currently active)")
        self.filter_status.setStyleSheet(
            "color: #888888; font-style: italic; font-size: 10px;"
        )
        filter_layout.addWidget(self.filter_status)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Real-time specific parameters
        self._setup_realtime_parameters(layout)

    def _setup_realtime_parameters(self, layout: QVBoxLayout) -> None:
        """Setup real-time mode parameters."""
        self.realtime_params_layout = QHBoxLayout()

        self.realtime_params_layout.addWidget(QLabel("Update Interval:"))
        self.update_interval_spin = QSpinBox()
        self.update_interval_spin.setRange(5, 300)  # 0.5s to 30s (in tenths of seconds)
        self.update_interval_spin.setValue(20)  # Default 2.0s
        self.update_interval_spin.setSuffix(" × 0.1s")
        self.update_interval_spin.setToolTip(
            "Update interval: 5 = 0.5s (high CPU), 10 = 1.0s (balanced), 20 = 2.0s (efficient)"
        )
        # Connect to dynamic update with conversion to seconds
        self.update_interval_spin.valueChanged.connect(
            lambda value: self.realtime_param_changed.emit(
                "update_interval", value / 10.0
            )
        )
        self.realtime_params_layout.addWidget(self.update_interval_spin)

        # Performance warning indicator
        self.performance_warning = QLabel("⚠️ High CPU")
        self.performance_warning.setStyleSheet(
            "color: #FF6B6B; font-style: italic; font-size: 9px;"
        )
        self.performance_warning.setVisible(False)
        self.realtime_params_layout.addWidget(self.performance_warning)

        # Dynamic update indicator
        self.dynamic_update_label = QLabel("🔄 All changes apply automatically")
        self.dynamic_update_label.setStyleSheet(
            "color: #00CC88; font-style: italic; font-size: 9px;"
        )
        self.realtime_params_layout.addWidget(self.dynamic_update_label)

        # Connect warning system
        self.update_interval_spin.valueChanged.connect(self._update_performance_warning)

        self.realtime_params_layout.addStretch()

        self.realtime_params_widget = QWidget()
        self.realtime_params_widget.setLayout(self.realtime_params_layout)
        self.realtime_params_widget.setVisible(False)
        layout.addWidget(self.realtime_params_widget)

    def _update_performance_warning(self, value: int) -> None:
        """Update performance warning based on interval."""
        interval_seconds = value / 10.0

        if interval_seconds < 1.0:
            self.performance_warning.setText("⚠️ High CPU")
            self.performance_warning.setStyleSheet(
                "color: #FF6B6B; font-style: italic; font-size: 9px;"
            )
            self.performance_warning.setVisible(True)
        elif interval_seconds < 1.5:
            self.performance_warning.setText("⚡ Medium CPU")
            self.performance_warning.setStyleSheet(
                "color: #FFB366; font-style: italic; font-size: 9px;"
            )
            self.performance_warning.setVisible(True)
        else:
            self.performance_warning.setVisible(False)

    def _setup_performance_mode_channels(self, layout: QVBoxLayout) -> None:
        """Setup performance mode channel selection."""
        self.performance_channel_layout = QHBoxLayout()
        self.performance_channel_layout.addWidget(QLabel("Channels for Conversion:"))

        self.conversion_channels_label = QLabel("All channels")
        self.conversion_channels_label.setStyleSheet(
            "color: #CCCCCC; font-style: italic;"
        )
        self.performance_channel_layout.addWidget(self.conversion_channels_label)
        self.performance_channel_layout.addStretch()

        self.select_conversion_channels_btn = QPushButton("Select Channels")
        self.select_conversion_channels_btn.clicked.connect(
            lambda: self.channel_selection_requested.emit("conversion")
        )
        self.select_conversion_channels_btn.setStyleSheet("background-color: #FF8C00;")
        self.performance_channel_layout.addWidget(self.select_conversion_channels_btn)

        self.performance_channel_widget = QWidget()
        self.performance_channel_widget.setLayout(self.performance_channel_layout)
        self.performance_channel_widget.setVisible(False)
        layout.addWidget(self.performance_channel_widget)

    def _setup_conversion_controls(self, layout: QVBoxLayout) -> None:
        """Setup conversion control buttons."""
        buttons_layout = QHBoxLayout()

        self.convert_btn = QPushButton("Convert to MNE")
        self.convert_btn.clicked.connect(self._request_conversion)
        buttons_layout.addWidget(self.convert_btn)

        # Real-time controls
        self.start_realtime_btn = QPushButton("Start Real-time")
        self.start_realtime_btn.clicked.connect(self._request_realtime)
        self.start_realtime_btn.setStyleSheet("background-color: #00AA00;")
        self.start_realtime_btn.setVisible(False)
        buttons_layout.addWidget(self.start_realtime_btn)

        self.stop_realtime_btn = QPushButton("Stop Real-time")
        self.stop_realtime_btn.clicked.connect(self.realtime_stopped.emit)
        self.stop_realtime_btn.setStyleSheet("background-color: #AA0000;")
        self.stop_realtime_btn.setVisible(False)
        self.stop_realtime_btn.setEnabled(False)
        buttons_layout.addWidget(self.stop_realtime_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.conversion_cancelled.emit)
        self.cancel_btn.setEnabled(False)
        buttons_layout.addWidget(self.cancel_btn)

        layout.addLayout(buttons_layout)

    def _on_mode_changed(self) -> None:
        """Handle conversion mode change."""
        selected_mode = self.conversion_mode_combo.currentText()
        is_performance_mode = "Performance Mode" in selected_mode
        is_realtime_mode = "Real-time Mode" in selected_mode

        # Show/hide relevant controls
        self.performance_channel_widget.setVisible(is_performance_mode)
        self.realtime_params_widget.setVisible(is_realtime_mode)

        # Show/hide buttons
        self.convert_btn.setVisible(not is_realtime_mode)
        self.start_realtime_btn.setVisible(is_realtime_mode)
        self.stop_realtime_btn.setVisible(is_realtime_mode)

        # Update info label
        if is_realtime_mode:
            self.mode_info_label.setText(
                "🔄 Optimized real-time: Only converts selected channels"
            )
            self.mode_info_label.setStyleSheet(
                "color: #00CC88; font-style: italic; font-size: 10px;"
            )
        elif is_performance_mode:
            self.mode_info_label.setText(
                "⚡ Converts only selected channels for better performance"
            )
            self.mode_info_label.setStyleSheet(
                "color: #FFB366; font-style: italic; font-size: 10px;"
            )
        else:
            self.mode_info_label.setText(
                "ℹ️ Converts all channels, apply selection during visualization"
            )
            self.mode_info_label.setStyleSheet(
                "color: #88BB88; font-style: italic; font-size: 10px;"
            )

    def _request_realtime(self) -> None:
        """Request real-time processing with current parameters."""
        params = self.get_realtime_parameters()
        self.realtime_requested.emit(params)

    def get_realtime_parameters(self) -> Dict[str, Any]:
        """Get current real-time parameters."""
        return {
            "update_interval_seconds": float(self.update_interval_spin.value() / 10.0),
            "duration_seconds": self.duration_spin.value(),
            "convert_to_v": self.convert_to_v_check.isChecked(),
        }

    def _request_conversion(self) -> None:
        """Request conversion with current parameters."""
        params = self.get_conversion_parameters()
        self.conversion_requested.emit(params)

    def get_conversion_parameters(self) -> Dict[str, Any]:
        """Get current conversion parameters."""
        selected_mode = self.conversion_mode_combo.currentText()

        return {
            "duration_seconds": self.duration_spin.value(),
            "convert_to_v": self.convert_to_v_check.isChecked(),
            "use_filters": (
                self.use_filters_check.isChecked()
                if hasattr(self, "use_filters_check")
                else False
            ),
            "mode": (
                "performance" if "Performance Mode" in selected_mode else "flexible"
            ),
        }

    # Add method to update filter status text
    def update_filter_status(self, status_text: str, is_active: bool = False) -> None:
        """Update the filter status indicator."""
        if hasattr(self, "filter_status"):
            self.filter_status.setText(status_text)
            if is_active:
                self.filter_status.setStyleSheet(
                    "color: #88CC88; font-style: italic; font-size: 10px;"
                )
            else:
                self.filter_status.setStyleSheet(
                    "color: #888888; font-style: italic; font-size: 10px;"
                )

    def set_realtime_state(self, active: bool) -> None:
        """Set the real-time processing state."""
        self.start_realtime_btn.setEnabled(not active)
        self.stop_realtime_btn.setEnabled(active)

        # Disable mode switching during real-time
        self.conversion_mode_combo.setEnabled(not active)

        # Show/hide dynamic update indicator
        if hasattr(self, "dynamic_update_label"):
            self.dynamic_update_label.setVisible(active)

    def set_conversion_state(self, converting: bool) -> None:
        """Set the conversion state."""
        self.convert_btn.setEnabled(not converting)
        self.cancel_btn.setEnabled(converting)
        self.conversion_progress.setVisible(converting)

        if converting:
            self.conversion_progress.setRange(0, 0)  # Indeterminate

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the widget."""
        self.convert_btn.setEnabled(enabled)
        if hasattr(self, "select_conversion_channels_btn"):
            self.select_conversion_channels_btn.setEnabled(enabled)

    def update_channel_info(self, channel_info: str) -> None:
        """Update the channel information display."""
        if hasattr(self, "conversion_channels_label"):
            self.conversion_channels_label.setText(channel_info)

    def reset_state(self) -> None:
        """Reset widget to initial state."""
        self.set_conversion_state(False)
        self.set_enabled(False)
