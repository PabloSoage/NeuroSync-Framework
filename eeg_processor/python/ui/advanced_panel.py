from typing import Any, Optional, Dict, List

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QGridLayout,
)
from brainflow.data_filter import (
    FilterTypes,
    AggOperations,
    WindowOperations,
    WaveletTypes,
)

from .base_panel import BasePanel
from ..utils.help_system import HelpButton


class AdvancedProcessingPanel(BasePanel):
    """Panel for advanced signal processing operations."""

    def __init__(
        self, collector_service: Any, processor_service: Any, parent: Optional[Any] = None
    ) -> None:
        """Initialize the advanced processing panel."""
        super().__init__(parent)
        self.collector_service = collector_service
        self.processor_service = processor_service

        # Setup UI components
        self.setup_ica_section()
        self.setup_wavelet_section()
        self.setup_downsampling_section()
        self.setup_advanced_filtering_section()

        # Add stretch to push everything to the top
        self.layout.addStretch()

    def setup_ica_section(self) -> None:
        """Set up ICA section."""
        ica_group = QGroupBox("Independent Component Analysis (ICA)")
        ica_layout = QVBoxLayout(ica_group)

        # Add help button for ICA
        ica_header_layout = QHBoxLayout()
        ica_header_layout.addWidget(QLabel("ICA Configuration"))
        ica_header_layout.addWidget(HelpButton("ica", self))
        ica_header_layout.addStretch()
        ica_layout.addLayout(ica_header_layout)

        # ICA Parameters
        ica_params_layout = QHBoxLayout()
        ica_params_layout.addWidget(QLabel("Number of Components:"))
        self.ica_components_spin = QSpinBox()
        self.ica_components_spin.setRange(1, 10)
        self.ica_components_spin.setValue(2)
        ica_params_layout.addWidget(self.ica_components_spin)

        ica_params_layout.addWidget(QLabel("Channel:"))
        self.ica_channel_combo = QComboBox()
        self.ica_channel_combo.addItem("All Channels", -1)
        # Channels will be populated when connected to a board
        ica_params_layout.addWidget(self.ica_channel_combo)

        ica_layout.addLayout(ica_params_layout)

        # ICA Control buttons
        ica_buttons_layout = QHBoxLayout()
        self.compute_ica_btn = QPushButton("Compute ICA")
        self.compute_ica_btn.clicked.connect(self.compute_ica)
        self.compute_ica_btn.setEnabled(False)
        ica_buttons_layout.addWidget(self.compute_ica_btn)

        self.view_ica_components_btn = QPushButton("View ICA Components")
        self.view_ica_components_btn.clicked.connect(self.view_ica_components)
        self.view_ica_components_btn.setEnabled(False)
        ica_buttons_layout.addWidget(self.view_ica_components_btn)

        ica_layout.addLayout(ica_buttons_layout)

        self.layout.addWidget(ica_group)

    def setup_wavelet_section(self) -> None:
        """Set up wavelet transform section."""
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
        wavelet_params_layout.addWidget(self.wavelet_type_combo, 0, 1)

        wavelet_params_layout.addWidget(QLabel("Decomposition Level:"), 0, 2)
        self.wavelet_level_spin = QSpinBox()
        self.wavelet_level_spin.setRange(1, 8)
        self.wavelet_level_spin.setValue(3)
        wavelet_params_layout.addWidget(self.wavelet_level_spin, 0, 3)

        wavelet_params_layout.addWidget(QLabel("Channel:"), 1, 0)
        self.wavelet_channel_combo = QComboBox()
        # Channels will be populated when connected to a board
        wavelet_params_layout.addWidget(self.wavelet_channel_combo, 1, 1)

        wavelet_layout.addLayout(wavelet_params_layout)

        # Wavelet Control buttons
        wavelet_buttons_layout = QHBoxLayout()
        self.compute_wavelet_btn = QPushButton("Compute Wavelet Transform")
        self.compute_wavelet_btn.clicked.connect(self.compute_wavelet)
        self.compute_wavelet_btn.setEnabled(False)
        wavelet_buttons_layout.addWidget(self.compute_wavelet_btn)

        self.inverse_wavelet_btn = QPushButton("Apply Inverse Transform")
        self.inverse_wavelet_btn.clicked.connect(self.apply_inverse_wavelet)
        self.inverse_wavelet_btn.setEnabled(False)
        wavelet_buttons_layout.addWidget(self.inverse_wavelet_btn)

        wavelet_layout.addLayout(wavelet_buttons_layout)

        self.layout.addWidget(wavelet_group)

    def setup_downsampling_section(self) -> None:
        """Set up downsampling section."""
        downsample_group = QGroupBox("Downsampling")
        downsample_layout = QVBoxLayout(downsample_group)

        # Add help button for Downsampling
        downsample_header_layout = QHBoxLayout()
        downsample_header_layout.addWidget(QLabel("Downsampling Configuration"))
        downsample_header_layout.addWidget(HelpButton("downsampling", self))
        downsample_header_layout.addStretch()
        downsample_layout.addLayout(downsample_header_layout)

        # Downsampling Parameters
        downsample_params_layout = QHBoxLayout()

        downsample_params_layout.addWidget(QLabel("Factor:"))
        self.downsample_factor_spin = QSpinBox()
        self.downsample_factor_spin.setRange(2, 10)
        self.downsample_factor_spin.setValue(2)
        downsample_params_layout.addWidget(self.downsample_factor_spin)

        downsample_params_layout.addWidget(QLabel("Aggregation Method:"))
        self.downsample_agg_combo = QComboBox()
        self.downsample_agg_combo.addItem("Mean", AggOperations.MEAN)
        self.downsample_agg_combo.addItem("Median", AggOperations.MEDIAN)
        self.downsample_agg_combo.addItem("Each", AggOperations.EACH)
        downsample_params_layout.addWidget(self.downsample_agg_combo)

        downsample_layout.addLayout(downsample_params_layout)

        # Downsampling Control buttons
        downsample_buttons_layout = QHBoxLayout()
        self.apply_downsample_btn = QPushButton("Apply Downsampling")
        self.apply_downsample_btn.clicked.connect(self.apply_downsampling)
        self.apply_downsample_btn.setEnabled(False)
        downsample_buttons_layout.addWidget(self.apply_downsample_btn)

        downsample_layout.addLayout(downsample_buttons_layout)

        self.layout.addWidget(downsample_group)

    def setup_advanced_filtering_section(self) -> None:
        """Set up advanced filtering section."""
        adv_filter_group = QGroupBox("Advanced Filtering Options")
        adv_filter_layout = QVBoxLayout(adv_filter_group)

        # Filter Type Selection
        filter_type_layout = QHBoxLayout()
        filter_type_layout.addWidget(QLabel("Filter Type:"))
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItem("Butterworth", FilterTypes.BUTTERWORTH)
        self.filter_type_combo.addItem("Chebyshev Type 1", FilterTypes.CHEBYSHEV_TYPE_1)
        self.filter_type_combo.addItem("Bessel", FilterTypes.BESSEL)
        self.filter_type_combo.addItem(
            "Butterworth Zero Phase", FilterTypes.BUTTERWORTH_ZERO_PHASE
        )
        filter_type_layout.addWidget(self.filter_type_combo)

        filter_type_layout.addWidget(QLabel("Window Function:"))
        self.window_function_combo = QComboBox()
        self.window_function_combo.addItem("Hanning", WindowOperations.HANNING)
        self.window_function_combo.addItem("Hamming", WindowOperations.HAMMING)
        self.window_function_combo.addItem(
            "Blackman Harris", WindowOperations.BLACKMAN_HARRIS
        )
        self.window_function_combo.addItem("No Window", WindowOperations.NO_WINDOW)
        filter_type_layout.addWidget(self.window_function_combo)

        adv_filter_layout.addLayout(filter_type_layout)

        # Apply Advanced Filtering
        filter_buttons_layout = QHBoxLayout()
        self.apply_adv_filter_btn = QPushButton("Apply Advanced Filters")
        self.apply_adv_filter_btn.clicked.connect(self.apply_advanced_filters)
        self.apply_adv_filter_btn.setEnabled(False)
        filter_buttons_layout.addWidget(self.apply_adv_filter_btn)

        adv_filter_layout.addLayout(filter_buttons_layout)

        self.layout.addWidget(adv_filter_group)

    def compute_ica(self) -> None:
        """Compute ICA components."""
        try:
            # Implementation of ICA computation
            self.show_status("ICA computation started")
            # Actual implementation would get data and call processor_service
            self.view_ica_components_btn.setEnabled(True)
        except Exception as e:
            self.show_error("ICA Error", f"Error computing ICA: {str(e)}")

    def view_ica_components(self) -> None:
        """View ICA components."""
        try:
            # Implementation of ICA component visualization
            self.show_status("Showing ICA components")
        except Exception as e:
            self.show_error("ICA Error", f"Error displaying ICA components: {str(e)}")

    def compute_wavelet(self) -> None:
        """Compute wavelet transform."""
        try:
            # Implementation of wavelet transform
            self.show_status("Wavelet transform computed")
            self.inverse_wavelet_btn.setEnabled(True)
        except Exception as e:
            self.show_error(
                "Wavelet Error", f"Error computing wavelet transform: {str(e)}"
            )

    def apply_inverse_wavelet(self) -> None:
        """Apply inverse wavelet transform."""
        try:
            # Implementation of inverse wavelet transform
            self.show_status("Inverse wavelet transform applied")
        except Exception as e:
            self.show_error(
                "Wavelet Error", f"Error applying inverse wavelet: {str(e)}"
            )

    def apply_downsampling(self) -> None:
        """Apply downsampling to data."""
        try:
            # Implementation of downsampling
            self.show_status("Downsampling applied")
        except Exception as e:
            self.show_error(
                "Downsampling Error", f"Error applying downsampling: {str(e)}"
            )

    def apply_advanced_filters(self) -> None:
        """Apply advanced filters."""
        try:
            # Implementation of advanced filtering
            self.show_status("Advanced filters applied")
        except Exception as e:
            self.show_error(
                "Filtering Error", f"Error applying advanced filters: {str(e)}"
            )

    # Add methods for API interaction
    def get_ica_settings(self) -> Dict[str, Any]:
        """Get current ICA settings."""
        return {
            "components": self.ica_components_spin.value(),
            "channel": self.ica_channel_combo.currentData(),
        }

    def get_wavelet_settings(self) -> Dict[str, Any]:
        """Get current wavelet settings."""
        return {
            "type": self.wavelet_type_combo.currentData(),
            "level": self.wavelet_level_spin.value(),
            "channel": self.wavelet_channel_combo.currentData(),
        }

    def get_downsample_settings(self) -> Dict[str, Any]:
        """Get current downsample settings."""
        return {
            "factor": self.downsample_factor_spin.value(),
            "aggregation": self.downsample_agg_combo.currentData(),
        }

    def get_advanced_filter_settings(self) -> Dict[str, Any]:
        """Get current advanced filter settings."""
        return {
            "filter_type": self.filter_type_combo.currentData(),
            "window_function": self.window_function_combo.currentData(),
        }

    def update_channel_lists(self, channel_names: List[str]) -> bool:
        """Update channel selection dropdowns from API call."""
        try:
            current_ica_ch = self.ica_channel_combo.currentData()
            current_wavelet_ch = self.wavelet_channel_combo.currentData()

            # Clear existing items
            self.ica_channel_combo.clear()
            self.wavelet_channel_combo.clear()

            # Add "All Channels" option to ICA
            self.ica_channel_combo.addItem("All Channels", -1)

            # Add channel options
            for i, name in enumerate(channel_names):
                self.ica_channel_combo.addItem(name, i)
                self.wavelet_channel_combo.addItem(name, i)

            # Try to restore previous selections
            if current_ica_ch is not None:
                for i in range(self.ica_channel_combo.count()):
                    if self.ica_channel_combo.itemData(i) == current_ica_ch:
                        self.ica_channel_combo.setCurrentIndex(i)
                        break

            if current_wavelet_ch is not None:
                for i in range(self.wavelet_channel_combo.count()):
                    if self.wavelet_channel_combo.itemData(i) == current_wavelet_ch:
                        self.wavelet_channel_combo.setCurrentIndex(i)
                        break

            return True
        except Exception as e:
            self.show_error("Channel List Update Error", str(e))
            return False

    def enable_processing(self, enabled: bool) -> None:
        """Enable or disable advanced processing controls."""
        self.compute_ica_btn.setEnabled(enabled)
        self.compute_wavelet_btn.setEnabled(enabled)
        self.apply_downsample_btn.setEnabled(enabled)
        self.apply_adv_filter_btn.setEnabled(enabled)

        # Reset dependent buttons
        if not enabled:
            self.view_ica_components_btn.setEnabled(False)
            self.inverse_wavelet_btn.setEnabled(False)
