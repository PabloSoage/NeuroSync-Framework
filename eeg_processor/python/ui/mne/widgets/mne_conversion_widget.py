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
            ["Flexible Mode (All Channels)", "Performance Mode (Selected Only)"]
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

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.conversion_cancelled.emit)
        self.cancel_btn.setEnabled(False)
        buttons_layout.addWidget(self.cancel_btn)

        layout.addLayout(buttons_layout)

    def _on_mode_changed(self) -> None:
        """Handle conversion mode change."""
        selected_mode = self.conversion_mode_combo.currentText()
        is_performance_mode = "Performance Mode" in selected_mode

        self.performance_channel_widget.setVisible(is_performance_mode)

        if is_performance_mode:
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
            "mode": (
                "performance" if "Performance Mode" in selected_mode else "flexible"
            ),
        }

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
        self.select_conversion_channels_btn.setEnabled(enabled)

    def update_channel_info(self, channel_info: str) -> None:
        """Update the channel information display."""
        self.conversion_channels_label.setText(channel_info)

    def reset_state(self) -> None:
        """Reset widget to initial state."""
        self.set_conversion_state(False)
        self.set_enabled(False)
