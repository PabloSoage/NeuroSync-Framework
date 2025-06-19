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
    QCheckBox,
)
from brainflow.data_filter import WaveletTypes, WaveletExtensionTypes

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

        # Wavelet Type - Add all available wavelets from BrainFlow
        wavelet_params_layout.addWidget(QLabel("Wavelet Type:"), 0, 0)
        self.wavelet_type_combo = QComboBox()

        # Daubechies wavelets
        self.wavelet_type_combo.addItem("Haar", WaveletTypes.HAAR)
        self.wavelet_type_combo.addItem("DB1", WaveletTypes.DB1)
        self.wavelet_type_combo.addItem("DB2", WaveletTypes.DB2)
        self.wavelet_type_combo.addItem("DB3", WaveletTypes.DB3)
        self.wavelet_type_combo.addItem("DB4", WaveletTypes.DB4)
        self.wavelet_type_combo.addItem("DB5", WaveletTypes.DB5)
        self.wavelet_type_combo.addItem("DB6", WaveletTypes.DB6)
        self.wavelet_type_combo.addItem("DB7", WaveletTypes.DB7)
        self.wavelet_type_combo.addItem("DB8", WaveletTypes.DB8)
        self.wavelet_type_combo.addItem("DB9", WaveletTypes.DB9)
        self.wavelet_type_combo.addItem("DB10", WaveletTypes.DB10)
        self.wavelet_type_combo.addItem("DB11", WaveletTypes.DB11)
        self.wavelet_type_combo.addItem("DB12", WaveletTypes.DB12)
        self.wavelet_type_combo.addItem("DB13", WaveletTypes.DB13)
        self.wavelet_type_combo.addItem("DB14", WaveletTypes.DB14)
        self.wavelet_type_combo.addItem("DB15", WaveletTypes.DB15)

        # Biorthogonal wavelets
        self.wavelet_type_combo.addItem("BIOR1_1", WaveletTypes.BIOR1_1)
        self.wavelet_type_combo.addItem("BIOR1_3", WaveletTypes.BIOR1_3)
        self.wavelet_type_combo.addItem("BIOR1_5", WaveletTypes.BIOR1_5)
        self.wavelet_type_combo.addItem("BIOR2_2", WaveletTypes.BIOR2_2)
        self.wavelet_type_combo.addItem("BIOR2_4", WaveletTypes.BIOR2_4)
        self.wavelet_type_combo.addItem("BIOR2_6", WaveletTypes.BIOR2_6)
        self.wavelet_type_combo.addItem("BIOR2_8", WaveletTypes.BIOR2_8)
        self.wavelet_type_combo.addItem("BIOR3_1", WaveletTypes.BIOR3_1)
        self.wavelet_type_combo.addItem("BIOR3_3", WaveletTypes.BIOR3_3)
        self.wavelet_type_combo.addItem("BIOR3_5", WaveletTypes.BIOR3_5)
        self.wavelet_type_combo.addItem("BIOR3_7", WaveletTypes.BIOR3_7)
        self.wavelet_type_combo.addItem("BIOR3_9", WaveletTypes.BIOR3_9)
        self.wavelet_type_combo.addItem("BIOR4_4", WaveletTypes.BIOR4_4)
        self.wavelet_type_combo.addItem("BIOR5_5", WaveletTypes.BIOR5_5)
        self.wavelet_type_combo.addItem("BIOR6_8", WaveletTypes.BIOR6_8)

        # Coiflets wavelets
        self.wavelet_type_combo.addItem("COIF1", WaveletTypes.COIF1)
        self.wavelet_type_combo.addItem("COIF2", WaveletTypes.COIF2)
        self.wavelet_type_combo.addItem("COIF3", WaveletTypes.COIF3)
        self.wavelet_type_combo.addItem("COIF4", WaveletTypes.COIF4)
        self.wavelet_type_combo.addItem("COIF5", WaveletTypes.COIF5)

        # Symlets wavelets
        self.wavelet_type_combo.addItem("SYM2", WaveletTypes.SYM2)
        self.wavelet_type_combo.addItem("SYM3", WaveletTypes.SYM3)
        self.wavelet_type_combo.addItem("SYM4", WaveletTypes.SYM4)
        self.wavelet_type_combo.addItem("SYM5", WaveletTypes.SYM5)
        self.wavelet_type_combo.addItem("SYM6", WaveletTypes.SYM6)
        self.wavelet_type_combo.addItem("SYM7", WaveletTypes.SYM7)
        self.wavelet_type_combo.addItem("SYM8", WaveletTypes.SYM8)
        self.wavelet_type_combo.addItem("SYM9", WaveletTypes.SYM9)
        self.wavelet_type_combo.addItem("SYM10", WaveletTypes.SYM10)

        # Set default to DB4 (commonly used for EEG)
        for i in range(self.wavelet_type_combo.count()):
            if self.wavelet_type_combo.itemData(i) == WaveletTypes.DB4:
                self.wavelet_type_combo.setCurrentIndex(i)
                break

        # Connect to dynamic update
        self.wavelet_type_combo.currentIndexChanged.connect(self._on_settings_changed)
        wavelet_params_layout.addWidget(self.wavelet_type_combo, 0, 1)

        wavelet_params_layout.addWidget(QLabel("Decomposition Level:"), 0, 2)
        self.wavelet_level_spin = QSpinBox()
        self.wavelet_level_spin.setRange(1, 8)
        self.wavelet_level_spin.setValue(3)
        self.wavelet_level_spin.setToolTip(
            "Number of decomposition levels. Higher levels = more frequency separation"
        )
        # Connect to dynamic update
        self.wavelet_level_spin.valueChanged.connect(self._on_settings_changed)
        wavelet_params_layout.addWidget(self.wavelet_level_spin, 0, 3)

        wavelet_params_layout.addWidget(QLabel("Channel:"), 1, 0)
        self.wavelet_channel_combo = QComboBox()
        # Connect to dynamic update
        self.wavelet_channel_combo.currentIndexChanged.connect(
            self._on_settings_changed
        )
        wavelet_params_layout.addWidget(self.wavelet_channel_combo, 1, 1)

        # Extension type
        wavelet_params_layout.addWidget(QLabel("Extension:"), 1, 2)
        self.extension_combo = QComboBox()
        self.extension_combo.addItem("Symmetric", WaveletExtensionTypes.SYMMETRIC)
        self.extension_combo.addItem("Periodic", WaveletExtensionTypes.PERIODIC)
        self.extension_combo.setToolTip(
            "Boundary extension method for wavelet transform"
        )
        self.extension_combo.currentIndexChanged.connect(self._on_settings_changed)
        wavelet_params_layout.addWidget(self.extension_combo, 1, 3)

        wavelet_layout.addLayout(wavelet_params_layout)

        # Wavelet denoising option
        denoising_layout = QHBoxLayout()
        self.apply_denoising_check = QCheckBox("Apply Wavelet Denoising")
        self.apply_denoising_check.setToolTip(
            "Apply wavelet denoising during wavelet coefficient computation.\n"
            "This removes noise from the signal BEFORE computing the transform.\n"
            "The denoised coefficients are then used for inverse transform.\n"
            "Use this if your signal has high-frequency noise artifacts."
        )
        self.apply_denoising_check.stateChanged.connect(self._on_settings_changed)
        denoising_layout.addWidget(self.apply_denoising_check)
        denoising_layout.addStretch()
        wavelet_layout.addLayout(denoising_layout)

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
            "channel_selection": self.wavelet_channel_combo.currentData(),
            "extension_type": self.extension_combo.currentData(),
            "apply_denoising": self.apply_denoising_check.isChecked(),
        }
        self.compute_requested.emit(params)

    def _toggle_inverse_transform(self) -> None:
        """Toggle inverse transform application."""
        self.inverse_applied = not self.inverse_applied
        self.apply_inverse_requested.emit(self.inverse_applied)

        # Update button appearance
        if self.inverse_applied:
            self.inverse_wavelet_btn.setText("Remove Inverse Transform")
            self.inverse_wavelet_btn.setStyleSheet(
                "background-color: #AA3333; color: white;"
            )
        else:
            self.inverse_wavelet_btn.setText("Apply Inverse Transform")
            self.inverse_wavelet_btn.setStyleSheet("")

    def _on_settings_changed(self) -> None:
        """Emit signal when settings change for dynamic update."""
        # Only emit if inverse transform is currently applied
        if hasattr(self, "inverse_applied") and self.inverse_applied:
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
        self.wavelet_results = {"coefficients": coefficients, "metadata": metadata}
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
            "extension_type": self.extension_combo.currentData(),
            "apply_denoising": self.apply_denoising_check.isChecked(),
            "inverse_applied": self.inverse_applied,
        }
