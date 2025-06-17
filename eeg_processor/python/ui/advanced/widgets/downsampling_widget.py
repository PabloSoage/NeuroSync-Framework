from typing import Any, Dict, Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QComboBox,
)
from brainflow.data_filter import AggOperations

from ...base_panel import BasePanel
from ....utils.help_system import HelpButton


class DownsamplingWidget(BasePanel):
    """
    Widget for downsampling operations.
    
    This widget handles downsampling-specific configuration and user interactions.
    """
    
    # Signals for communication with controller
    apply_requested = pyqtSignal(dict)  # Downsampling parameters including apply/remove flag

    def __init__(self, parent: Optional[Any] = None) -> None:
        """Initialize the downsampling widget."""
        super().__init__(parent)
        
        # Downsampling state
        self.applied = False
        
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the downsampling widget UI."""
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
        self.apply_downsample_btn.clicked.connect(self._toggle_downsampling)
        self.apply_downsample_btn.setEnabled(False)
        downsample_buttons_layout.addWidget(self.apply_downsample_btn)

        downsample_layout.addLayout(downsample_buttons_layout)

        self.layout.addWidget(downsample_group)

    def _toggle_downsampling(self) -> None:
        """Toggle downsampling application."""
        self.applied = not self.applied
        
        params = {
            "apply": self.applied,
            "factor": self.downsample_factor_spin.value(),
            "operation": self.downsample_agg_combo.currentData()
        }
        
        self.apply_requested.emit(params)
        
        # Update button appearance
        if self.applied:
            self.apply_downsample_btn.setText("Remove Downsampling")
            self.apply_downsample_btn.setStyleSheet("background-color: #AA3333; color: white;")
        else:
            self.apply_downsample_btn.setText("Apply Downsampling")
            self.apply_downsample_btn.setStyleSheet("")

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the widget."""
        self.apply_downsample_btn.setEnabled(enabled)
        
        if not enabled:
            self.applied = False
            self.apply_downsample_btn.setText("Apply Downsampling")
            self.apply_downsample_btn.setStyleSheet("")

    def get_downsample_settings(self) -> Dict[str, Any]:
        """Get current downsampling settings."""
        return {
            "factor": self.downsample_factor_spin.value(),
            "aggregation": self.downsample_agg_combo.currentData(),
            "applied": self.applied,
        }
