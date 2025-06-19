from typing import Any, Dict, List, Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QWidget,
)

from ....utils.help_system import HelpButton


class ICAWidget(QWidget):
    """
    Widget for Independent Component Analysis operations.

    This widget handles ICA-specific configuration and user interactions.
    """

    # Signals for communication with controller
    compute_requested = pyqtSignal(dict)  # ICA parameters
    view_components_requested = pyqtSignal(dict)  # Visualization parameters
    export_overview_requested = pyqtSignal()
    export_all_requested = pyqtSignal()

    # Real-time signals
    realtime_start_requested = pyqtSignal(dict)  # Real-time parameters
    realtime_stop_requested = pyqtSignal()
    realtime_interval_changed = pyqtSignal(float)  # New interval

    def __init__(self, parent: Optional[Any] = None) -> None:
        """Initialize the ICA widget."""
        super().__init__(parent)

        # ICA state
        self.channel_names: List[str] = []
        self.selected_channels: List[int] = []
        self.ica_results: Optional[Dict[str, Any]] = None
        self.realtime_active: bool = False

        # Create main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the ICA widget UI."""
        ica_group = QGroupBox("Independent Component Analysis (ICA)")
        ica_layout = QVBoxLayout(ica_group)

        # Add help button for ICA
        ica_header_layout = QHBoxLayout()
        ica_header_layout.addWidget(QLabel("ICA Configuration"))
        ica_header_layout.addWidget(HelpButton("ica", self))
        ica_header_layout.addStretch()
        ica_layout.addLayout(ica_header_layout)

        # ICA Parameters
        ica_params_layout = QVBoxLayout()

        # Number of components
        components_layout = QHBoxLayout()
        components_layout.addWidget(QLabel("Number of Components:"))
        self.ica_components_spin = QSpinBox()
        self.ica_components_spin.setRange(1, 16)
        self.ica_components_spin.setValue(2)
        components_layout.addWidget(self.ica_components_spin)
        components_layout.addStretch()
        ica_params_layout.addLayout(components_layout)

        # Channel selection
        channel_layout = QVBoxLayout()
        channel_layout.addWidget(QLabel("Channel Selection:"))

        # Channel selection button and info
        channel_selection_layout = QHBoxLayout()
        self.ica_channel_select_btn = QPushButton("Select Channels")
        self.ica_channel_select_btn.clicked.connect(self._open_channel_selection)
        channel_selection_layout.addWidget(self.ica_channel_select_btn)

        self.ica_channel_info_label = QLabel("All channels")
        self.ica_channel_info_label.setStyleSheet("color: #AAAAAA; font-style: italic;")
        channel_selection_layout.addWidget(self.ica_channel_info_label)
        channel_selection_layout.addStretch()

        channel_layout.addLayout(channel_selection_layout)
        ica_params_layout.addLayout(channel_layout)

        ica_layout.addLayout(ica_params_layout)

        # Standard ICA Control buttons
        ica_buttons_layout = QHBoxLayout()
        self.compute_ica_btn = QPushButton("Compute ICA")
        self.compute_ica_btn.clicked.connect(self._request_ica_computation)
        self.compute_ica_btn.setEnabled(False)
        ica_buttons_layout.addWidget(self.compute_ica_btn)

        self.view_ica_components_btn = QPushButton("View ICA Components")
        self.view_ica_components_btn.clicked.connect(self._request_ica_visualization)
        self.view_ica_components_btn.setEnabled(False)
        ica_buttons_layout.addWidget(self.view_ica_components_btn)

        ica_layout.addLayout(ica_buttons_layout)

        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        ica_layout.addWidget(separator)

        # Real-time ICA section
        realtime_layout = QVBoxLayout()

        # Real-time header
        realtime_header = QHBoxLayout()
        realtime_header.addWidget(QLabel("Real-time ICA Monitor"))
        realtime_header.addWidget(HelpButton("ica_realtime", self))
        realtime_header.addStretch()
        realtime_layout.addLayout(realtime_header)

        # Real-time controls
        realtime_controls_layout = QVBoxLayout()

        # Real-time enable checkbox
        realtime_enable_layout = QHBoxLayout()
        self.realtime_enable_check = QCheckBox("Enable Real-time ICA")
        self.realtime_enable_check.stateChanged.connect(
            self._on_realtime_enable_changed
        )
        realtime_enable_layout.addWidget(self.realtime_enable_check)
        realtime_enable_layout.addStretch()
        realtime_controls_layout.addLayout(realtime_enable_layout)

        # Update interval control
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Update Interval:"))
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.5, 2.0)
        self.interval_spin.setSingleStep(0.1)
        self.interval_spin.setValue(1.0)
        self.interval_spin.setSuffix(" s")
        self.interval_spin.setEnabled(False)
        self.interval_spin.valueChanged.connect(self._on_interval_changed)
        interval_layout.addWidget(self.interval_spin)

        interval_layout.addWidget(QLabel("Window Size:"))
        self.window_size_spin = QDoubleSpinBox()
        self.window_size_spin.setRange(2.0, 10.0)
        self.window_size_spin.setSingleStep(0.5)
        self.window_size_spin.setValue(5.0)
        self.window_size_spin.setSuffix(" s")
        self.window_size_spin.setEnabled(False)
        interval_layout.addWidget(self.window_size_spin)

        interval_layout.addStretch()
        realtime_controls_layout.addLayout(interval_layout)

        # Real-time status
        self.realtime_status_label = QLabel("Real-time mode: Disabled")
        self.realtime_status_label.setStyleSheet("color: #888888; font-style: italic;")
        realtime_controls_layout.addWidget(self.realtime_status_label)

        realtime_layout.addLayout(realtime_controls_layout)
        ica_layout.addLayout(realtime_layout)

        self.layout.addWidget(ica_group)

        # Create hidden colormap combo for export functionality (not shown in main panel)
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItem("Viridis", "viridis")
        self.colormap_combo.addItem("Plasma", "plasma")
        self.colormap_combo.addItem("Inferno", "inferno")
        self.colormap_combo.addItem("Magma", "magma")
        self.colormap_combo.addItem("Coolwarm", "coolwarm")
        self.colormap_combo.addItem("RdBu", "RdBu")
        self.colormap_combo.addItem("Spectral", "Spectral")
        self.colormap_combo.addItem("Jet", "jet")
        self.colormap_combo.setVisible(False)  # Hidden in main panel

    def _open_channel_selection(self) -> None:
        """Open channel selection dialog."""
        if not self.channel_names:
            self.show_error(
                "Channel Selection", "No channels available. Start streaming first."
            )
            return

        from ...mne.widgets.channel_selection_dialog import ChannelSelectionDialog
        from PyQt5.QtWidgets import QDialog

        dialog = ChannelSelectionDialog(
            channel_names=self.channel_names,
            selected_channels=self.selected_channels,
            parent=self,
        )
        dialog.setWindowTitle("Select Channels for ICA Analysis")

        if dialog.exec_() == QDialog.Accepted:
            self.selected_channels = dialog.get_selected_channels()
            self._update_channel_display()

    def _update_channel_display(self) -> None:
        """Update the channel selection display."""
        if not self.channel_names:
            self.ica_channel_info_label.setText("No channels available")
            self.ica_channel_select_btn.setEnabled(False)
            return

        self.ica_channel_select_btn.setEnabled(True)

        if not self.selected_channels:
            self.ica_channel_info_label.setText("No channels selected")
        elif len(self.selected_channels) == len(self.channel_names):
            self.ica_channel_info_label.setText("All channels selected")
        else:
            count = len(self.selected_channels)
            total = len(self.channel_names)
            self.ica_channel_info_label.setText(f"{count}/{total} channels selected")

    def _request_ica_computation(self) -> None:
        """Request ICA computation."""
        params = {
            "num_components": self.ica_components_spin.value(),
            "selected_channels": self.selected_channels.copy(),
        }
        self.compute_requested.emit(params)

    def _request_ica_visualization(self) -> None:
        """Request ICA visualization."""
        params = {"colormap": self.get_colormap()}
        self.view_components_requested.emit(params)

    def _on_realtime_enable_changed(self, state: int) -> None:
        """Handle real-time enable checkbox change."""
        enabled = state == 2  # Qt.Checked

        if enabled:
            # Start real-time mode
            params = {
                "num_components": self.ica_components_spin.value(),
                "selected_channels": self.selected_channels.copy(),
                "update_interval": self.interval_spin.value(),
                "window_size": self.window_size_spin.value(),
            }
            self.realtime_start_requested.emit(params)
        else:
            # Stop real-time mode
            self.realtime_stop_requested.emit()

    def _on_interval_changed(self, value: float) -> None:
        """Handle interval change."""
        if self.realtime_active:
            self.realtime_interval_changed.emit(value)

    def set_realtime_active(self, active: bool, message: str = "") -> None:
        """Set real-time mode status."""
        self.realtime_active = active

        # Update UI
        self.realtime_enable_check.blockSignals(True)
        self.realtime_enable_check.setChecked(active)
        self.realtime_enable_check.blockSignals(False)

        self.interval_spin.setEnabled(active)
        self.window_size_spin.setEnabled(active)

        # Update status
        if active:
            self.realtime_status_label.setText(f"Real-time mode: Active - {message}")
            self.realtime_status_label.setStyleSheet(
                "color: #00AA00; font-weight: bold;"
            )

            # Disable exports during real-time mode
            self.view_ica_components_btn.setEnabled(False)
        else:
            self.realtime_status_label.setText(f"Real-time mode: Disabled - {message}")
            self.realtime_status_label.setStyleSheet(
                "color: #888888; font-style: italic;"
            )

            # Re-enable exports if we have results
            if self.ica_results:
                self.view_ica_components_btn.setEnabled(True)

    def update_channels(self, channel_names: List[str]) -> None:
        """Update available channels."""
        self.channel_names = channel_names.copy()

        # Reset selected channels to all channels
        self.selected_channels = list(range(len(self.channel_names)))
        self._update_channel_display()

    def set_ica_results(self, ica_results: Dict[str, Any]) -> None:
        """Set ICA computation results."""
        self.ica_results = ica_results

        # Only enable view button if not in real-time mode
        if not self.realtime_active:
            self.view_ica_components_btn.setEnabled(True)

    def get_ica_results(self) -> Optional[Dict[str, Any]]:
        """Get current ICA results."""
        return self.ica_results

    def get_colormap(self) -> str:
        """Get selected colormap."""
        return self.colormap_combo.currentData()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the widget."""
        self.compute_ica_btn.setEnabled(enabled)

        if not enabled:
            self.view_ica_components_btn.setEnabled(False)
            self.ica_results = None

            # Stop real-time mode if active
            if self.realtime_active:
                self.realtime_enable_check.setChecked(False)

    def get_ica_settings(self) -> Dict[str, Any]:
        """Get current ICA settings."""
        return {
            "components": self.ica_components_spin.value(),
            "channels": self.selected_channels,
            "use_all_channels": (
                len(self.selected_channels) == len(self.channel_names)
                if self.channel_names
                else True
            ),
            "realtime_enabled": self.realtime_active,
            "update_interval": self.interval_spin.value(),
            "window_size": self.window_size_spin.value(),
        }
