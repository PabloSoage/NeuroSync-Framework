from typing import Any, Dict, Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
)
from brainflow.data_filter import FilterTypes, WindowOperations

from ...base_panel import BasePanel
from ....utils.help_system import HelpButton


class AdvancedFilterWidget(BasePanel):
    """
    Widget for advanced filtering operations.
    
    This widget handles advanced filter-specific configuration and user interactions.
    """
    
    # Signals for communication with controller
    apply_requested = pyqtSignal(dict)  # Filter parameters including apply/remove flag

    def __init__(self, parent: Optional[Any] = None) -> None:
        """Initialize the advanced filter widget."""
        super().__init__(parent)
        
        # Filter state
        self.applied = False
        
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the advanced filter widget UI."""
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
        self.apply_adv_filter_btn.clicked.connect(self._toggle_advanced_filters)
        self.apply_adv_filter_btn.setEnabled(False)
        filter_buttons_layout.addWidget(self.apply_adv_filter_btn)

        adv_filter_layout.addLayout(filter_buttons_layout)

        self.layout.addWidget(adv_filter_group)

    def _toggle_advanced_filters(self) -> None:
        """Toggle advanced filters application."""
        self.applied = not self.applied
        
        params = {
            "apply": self.applied,
            "filter_type": self.filter_type_combo.currentData(),
            "window_function": self.window_function_combo.currentData(),
            "low_cut": 1.0,  # Could be made configurable
            "high_cut": 50.0,  # Could be made configurable
            "order": 4,
        }
        
        self.apply_requested.emit(params)
        
        # Update button appearance
        if self.applied:
            self.apply_adv_filter_btn.setText("Remove Advanced Filters")
            self.apply_adv_filter_btn.setStyleSheet("background-color: #AA3333; color: white;")
        else:
            self.apply_adv_filter_btn.setText("Apply Advanced Filters")
            self.apply_adv_filter_btn.setStyleSheet("")

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the widget."""
        self.apply_adv_filter_btn.setEnabled(enabled)
        
        if not enabled:
            self.applied = False
            self.apply_adv_filter_btn.setText("Apply Advanced Filters")
            self.apply_adv_filter_btn.setStyleSheet("")

    def get_advanced_filter_settings(self) -> Dict[str, Any]:
        """Get current advanced filter settings."""
        return {
            "filter_type": self.filter_type_combo.currentData(),
            "window_function": self.window_function_combo.currentData(),
            "applied": self.applied,
        }
