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
    QGridLayout,
    QWidget,
)
from brainflow.data_filter import WaveletTypes

from ....utils.help_system import HelpButton


class WaveletWidget(QWidget):
    """
    Widget for wavelet transform operations.
    
    This widget handles wavelet-specific configuration and user interactions.
    """
    
    # Signals for communication with controller
    compute_requested = pyqtSignal(dict)  # Wavelet parameters
    apply_inverse_requested = pyqtSignal(bool)  # Apply/remove inverse transform
    settings_changed = pyqtSignal(dict)  # Settings changed for dynamic update

    def __init__(self, parent: Optional[Any] = None) -> None:
        """Initialize the wavelet widget."""
        super().__init__(parent)
        
        # Wavelet state
        self.channel_names: List[str] = []
        self.wavelet_results: Optional[Dict[str, Any]] = None
        self.inverse_applied = False
        
        # Create main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the wavelet widget UI."""
        wavelet_group = QGroupBox("Wavelet Transforms")
        wavelet_layout = QVBoxLayout(wavelet_group)

        # Add help button for Wavelet
        wavelet_header_layout = QHBoxLayout()
        wavelet_header_layout.addWidget(QLabel("Wavelet Analysis"))
        wavelet_header_layout.addWidget(HelpButton("wavelet", self))
        wavelet_header_layout.addStretch()
        wavelet_layout.addLayout(wavelet_header_layout)

        # Wavelet Parameters
        wavelet_params_layout = QGridLayout()

        wavelet_params_layout.addWidget(QLabel("Wavelet Type:"), 0, 0)
        self.wavelet_type_combo = QComboBox()
        self.wavelet_type_combo.addItem("DB4", WaveletTypes.DB4)
        self.wavelet_type_combo.addItem("DB5", WaveletTypes.DB5)
        self.wavelet_type_combo.addItem("DB6", WaveletTypes.DB6)
        self.wavelet_type_combo.addItem("BIOR3_9", WaveletTypes.BIOR3_9)
        self.wavelet_type_combo.addItem("HAAR", WaveletTypes.HAAR)
        # Connect to dynamic update
        self.wavelet_type_combo.currentIndexChanged.connect(self._on_settings_changed)
        wavelet_params_layout.addWidget(self.wavelet_type_combo, 0, 1)

        wavelet_params_layout.addWidget(QLabel("Decomposition Level:"), 0, 2)
        self.wavelet_level_spin = QSpinBox()
        self.wavelet_level_spin.setRange(1, 8)
        self.wavelet_level_spin.setValue(3)
        # Connect to dynamic update
        self.wavelet_level_spin.valueChanged.connect(self._on_settings_changed)
        wavelet_params_layout.addWidget(self.wavelet_level_spin, 0, 3)

        wavelet_params_layout.addWidget(QLabel("Channel:"), 1, 0)
        self.wavelet_channel_combo = QComboBox()
        # Connect to dynamic update
        self.wavelet_channel_combo.currentIndexChanged.connect(self._on_settings_changed)
        wavelet_params_layout.addWidget(self.wavelet_channel_combo, 1, 1)

        wavelet_layout.addLayout(wavelet_params_layout)

        # Wavelet Control buttons
        wavelet_buttons_layout = QHBoxLayout()
        self.compute_wavelet_btn = QPushButton("Compute Wavelet Transform")
        self.compute_wavelet_btn.clicked.connect(self._request_wavelet_computation)
        self.compute_wavelet_btn.setEnabled(False)
        wavelet_buttons_layout.addWidget(self.compute_wavelet_btn)

        self.inverse_wavelet_btn = QPushButton("Apply Inverse Transform")
        self.inverse_wavelet_btn.clicked.connect(self._toggle_inverse_transform)
        self.inverse_wavelet_btn.setEnabled(False)
        wavelet_buttons_layout.addWidget(self.inverse_wavelet_btn)

        wavelet_layout.addLayout(wavelet_buttons_layout)

        self.layout.addWidget(wavelet_group)

    def _request_wavelet_computation(self) -> None:
        """Request wavelet computation."""
        params = {
            "wavelet_type": self.wavelet_type_combo.currentData(),
            "decomp_level": self.wavelet_level_spin.value(),
            "channel_selection": self.wavelet_channel_combo.currentData()
        }
        self.compute_requested.emit(params)

    def _toggle_inverse_transform(self) -> None:
        """Toggle inverse transform application."""
        self.inverse_applied = not self.inverse_applied
        self.apply_inverse_requested.emit(self.inverse_applied)
        
        # Update button appearance
        if self.inverse_applied:
            self.inverse_wavelet_btn.setText("Remove Inverse Transform")
            self.inverse_wavelet_btn.setStyleSheet("background-color: #AA3333; color: white;")
        else:
            self.inverse_wavelet_btn.setText("Apply Inverse Transform")
            self.inverse_wavelet_btn.setStyleSheet("")

    def _on_settings_changed(self) -> None:
        """Emit signal when settings change for dynamic update."""
        # Only emit if inverse transform is currently applied
        if hasattr(self, 'inverse_applied') and self.inverse_applied:
            settings = self.get_wavelet_settings()
            self.settings_changed.emit(settings)

    def update_channels(self, channel_names: List[str]) -> None:
        """Update available channels."""
        self.channel_names = channel_names.copy()
        
        # Update channel combo
        current_selection = self.wavelet_channel_combo.currentData()
        self.wavelet_channel_combo.clear()

        # Add channel options
        for i, name in enumerate(channel_names):
            self.wavelet_channel_combo.addItem(name, i)

        # Try to restore previous selection
        if current_selection is not None:
            for i in range(self.wavelet_channel_combo.count()):
                if self.wavelet_channel_combo.itemData(i) == current_selection:
                    self.wavelet_channel_combo.setCurrentIndex(i)
                    break

    def set_wavelet_results(self, coefficients: Any, metadata: Dict[str, Any]) -> None:
        """Set wavelet computation results."""
        self.wavelet_results = {
            "coefficients": coefficients,
            "metadata": metadata
        }
        self.inverse_wavelet_btn.setEnabled(True)

    def has_wavelet_results(self) -> bool:
        """Check if wavelet results are available."""
        return self.wavelet_results is not None

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the widget."""
        self.compute_wavelet_btn.setEnabled(enabled)
        
        if not enabled:
            self.inverse_wavelet_btn.setEnabled(False)
            self.wavelet_results = None
            self.inverse_applied = False
            self.inverse_wavelet_btn.setText("Apply Inverse Transform")
            self.inverse_wavelet_btn.setStyleSheet("")

    def get_wavelet_settings(self) -> Dict[str, Any]:
        """Get current wavelet settings."""
        return {
            "type": self.wavelet_type_combo.currentData(),
            "level": self.wavelet_level_spin.value(),
            "channel": self.wavelet_channel_combo.currentData(),
            "inverse_applied": self.inverse_applied,
        }
