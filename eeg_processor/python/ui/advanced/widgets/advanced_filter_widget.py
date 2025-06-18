from typing import Any, Dict, Optional, List
import logging

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QWidget,
    QDoubleSpinBox,
    QSpinBox,
)
from brainflow.data_filter import FilterTypes, WindowOperations

from ....utils.help_system import HelpButton


class AdvancedFilterWidget(QWidget):
    """
    Widget for advanced filtering operations.
    
    This widget handles advanced filter-specific configuration and user interactions.
    """
    
    # Signals for communication with controller
    apply_requested = pyqtSignal(dict)  # Filter parameters including apply/remove flag
    settings_changed = pyqtSignal(dict)  # Settings changed for dynamic update

    def __init__(self, parent: Optional[Any] = None) -> None:
        """Initialize the advanced filter widget."""
        super().__init__(parent)
        
        # Filter state
        self.applied = False
        
        # Channel state
        self.channel_names: List[str] = []
        self.selected_channels: List[int] = []
        
        # Reference to processing panel for dynamic parameter reading
        self._processing_panel = None
        
        # Create main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the advanced filter widget UI."""
        adv_filter_group = QGroupBox("Advanced Filtering Options")
        adv_filter_layout = QVBoxLayout(adv_filter_group)

        # Add help button
        filter_header_layout = QHBoxLayout()
        filter_header_layout.addWidget(QLabel("Advanced Filters Configuration"))
        filter_header_layout.addWidget(HelpButton("advanced_filters", self))
        filter_header_layout.addStretch()
        adv_filter_layout.addLayout(filter_header_layout)

        # Filter Type Selection
        filter_type_layout = QHBoxLayout()
        filter_type_layout.addWidget(QLabel("Filter Type:"))
        self.filter_type_combo = QComboBox()
        
        # Add all available filter types from BrainFlow
        self.filter_type_combo.addItem("Butterworth", FilterTypes.BUTTERWORTH)
        self.filter_type_combo.addItem("Chebyshev Type 1", FilterTypes.CHEBYSHEV_TYPE_1)
        self.filter_type_combo.addItem("Bessel", FilterTypes.BESSEL)
        self.filter_type_combo.addItem("Butterworth Zero Phase", FilterTypes.BUTTERWORTH_ZERO_PHASE)
        self.filter_type_combo.addItem("Chebyshev Type 1 Zero Phase", FilterTypes.CHEBYSHEV_TYPE_1_ZERO_PHASE)
        self.filter_type_combo.addItem("Bessel Zero Phase", FilterTypes.BESSEL_ZERO_PHASE)
        
        # Connect to dynamic update
        self.filter_type_combo.currentIndexChanged.connect(self._on_settings_changed)
        # Connect to enable/disable ripple control
        self.filter_type_combo.currentIndexChanged.connect(self._on_filter_type_changed)
        filter_type_layout.addWidget(self.filter_type_combo)

        # Add filter order control
        filter_type_layout.addWidget(QLabel("Order:"))
        self.filter_order_spin = QSpinBox()
        self.filter_order_spin.setRange(1, 10)
        self.filter_order_spin.setValue(4)
        self.filter_order_spin.valueChanged.connect(self._on_settings_changed)
        filter_type_layout.addWidget(self.filter_order_spin)

        adv_filter_layout.addLayout(filter_type_layout)

        # Window function selection
        window_layout = QHBoxLayout()
        window_layout.addWidget(QLabel("Window Function:"))
        self.window_function_combo = QComboBox()
        self.window_function_combo.addItem("No Window", WindowOperations.NO_WINDOW)
        self.window_function_combo.addItem("Hanning", WindowOperations.HANNING)
        self.window_function_combo.addItem("Hamming", WindowOperations.HAMMING)
        self.window_function_combo.addItem("Blackman Harris", WindowOperations.BLACKMAN_HARRIS)
        # Connect to dynamic update
        self.window_function_combo.currentIndexChanged.connect(self._on_settings_changed)
        window_layout.addWidget(self.window_function_combo)
        window_layout.addStretch()
        adv_filter_layout.addLayout(window_layout)

        # Ripple control for Chebyshev filters (fixed parameters)
        ripple_layout = QHBoxLayout()
        self.ripple_label = QLabel("Ripple (dB):")
        ripple_layout.addWidget(self.ripple_label)
        
        self.ripple_spin = QDoubleSpinBox()
        self.ripple_spin.setRange(0.1, 3.0)  # Conservative range for stability
        self.ripple_spin.setValue(1.0)
        self.ripple_spin.setSuffix(" dB")
        self.ripple_spin.setDecimals(1)
        self.ripple_spin.setSingleStep(0.1)
        self.ripple_spin.valueChanged.connect(self._on_settings_changed)
        ripple_layout.addWidget(self.ripple_spin)
        
        # Add better tooltip with stability guidance
        self.ripple_spin.setToolTip(
            "Ripple in passband for Chebyshev filters.\n"
            "Lower values = less ripple but potential instability.\n"
            "Recommended: 0.5-2.0 dB for stable filtering.\n"
            "Higher orders may require higher ripple values."
        )
        
        ripple_layout.addStretch()
        adv_filter_layout.addLayout(ripple_layout)
        
        # Initially hide ripple control (Butterworth is default)
        self.ripple_label.hide()
        self.ripple_spin.hide()

        # Channel selection
        channel_layout = QVBoxLayout()
        channel_layout.addWidget(QLabel("Channel Selection:"))
        
        # Channel selection button and info
        channel_selection_layout = QHBoxLayout()
        self.filter_channel_select_btn = QPushButton("Select Channels")
        self.filter_channel_select_btn.clicked.connect(self._open_channel_selection)
        channel_selection_layout.addWidget(self.filter_channel_select_btn)
        
        self.filter_channel_info_label = QLabel("All channels")
        self.filter_channel_info_label.setStyleSheet("color: #AAAAAA; font-style: italic;")
        channel_selection_layout.addWidget(self.filter_channel_info_label)
        channel_selection_layout.addStretch()
        
        channel_layout.addLayout(channel_selection_layout)
        adv_filter_layout.addLayout(channel_layout)

        # Apply Advanced Filtering
        filter_buttons_layout = QHBoxLayout()
        self.apply_adv_filter_btn = QPushButton("Apply Advanced Filters")
        self.apply_adv_filter_btn.clicked.connect(self._toggle_advanced_filters)
        self.apply_adv_filter_btn.setEnabled(False)
        filter_buttons_layout.addWidget(self.apply_adv_filter_btn)

        adv_filter_layout.addLayout(filter_buttons_layout)

        self.layout.addWidget(adv_filter_group)

    def _open_channel_selection(self) -> None:
        """Open channel selection dialog."""
        if not self.channel_names:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Channel Selection", "No channels available. Start streaming first."
            )
            return

        from ...mne.widgets.channel_selection_dialog import ChannelSelectionDialog
        from PyQt5.QtWidgets import QDialog

        dialog = ChannelSelectionDialog(
            channel_names=self.channel_names,
            selected_channels=self.selected_channels,
            parent=self,
        )
        dialog.setWindowTitle("Select Channels for Advanced Filtering")

        if dialog.exec_() == QDialog.Accepted:
            old_channels = self.selected_channels.copy()
            self.selected_channels = dialog.get_selected_channels()
            self._update_channel_display()
            
            # Emit settings change for dynamic update (only if selection actually changed)
            if old_channels != self.selected_channels:
                self._on_settings_changed()

    def _update_channel_display(self) -> None:
        """Update the channel selection display."""
        if not self.channel_names:
            self.filter_channel_info_label.setText("No channels available")
            self.filter_channel_select_btn.setEnabled(False)
            return
        
        self.filter_channel_select_btn.setEnabled(True)
        
        if not self.selected_channels:
            # If no channels selected, treat as "all channels" for filtering
            self.filter_channel_info_label.setText("All channels (none selected)")
            self.filter_channel_info_label.setStyleSheet("color: #FFB366; font-style: italic;")
        elif len(self.selected_channels) == len(self.channel_names):
            self.filter_channel_info_label.setText("All channels selected")
            self.filter_channel_info_label.setStyleSheet("color: #AAAAAA; font-style: italic;")
        else:
            count = len(self.selected_channels)
            total = len(self.channel_names)
            self.filter_channel_info_label.setText(f"{count}/{total} channels selected")
            self.filter_channel_info_label.setStyleSheet("color: #AAAAAA; font-style: italic;")

    def update_channels(self, channel_names: List[str]) -> None:
        """Update available channels."""
        self.channel_names = channel_names.copy()
        
        # Reset selected channels to all channels
        self.selected_channels = list(range(len(self.channel_names)))
        self._update_channel_display()

    def set_processing_panel_reference(self, processing_panel) -> None:
        """Set reference to processing panel for reading basic filter parameters."""
        self._processing_panel = processing_panel

    def _get_basic_bandpass_params(self) -> Dict[str, float]:
        """Get current basic bandpass parameters from processing panel."""
        if self._processing_panel:
            try:
                return {
                    "low_cut": self._processing_panel.bandpass_low_spin.value(),
                    "high_cut": self._processing_panel.bandpass_high_spin.value()
                }
            except Exception as e:
                logging.debug(f"Error reading basic bandpass params: {e}")
        
        # Fallback values
        return {"low_cut": 1.0, "high_cut": 50.0}

    def _on_filter_type_changed(self) -> None:
        """Handle filter type change to show/hide ripple control and adjust parameters."""
        filter_type = self.filter_type_combo.currentData()
        
        # Show ripple control only for Chebyshev filters
        is_chebyshev = filter_type in [FilterTypes.CHEBYSHEV_TYPE_1, FilterTypes.CHEBYSHEV_TYPE_1_ZERO_PHASE]
        
        self.ripple_label.setVisible(is_chebyshev)
        self.ripple_spin.setVisible(is_chebyshev)
        
        # Adjust recommended parameters for stability
        if is_chebyshev:
            # For Chebyshev filters, adjust order and ripple for stability
            current_order = self.filter_order_spin.value()
            if current_order > 6:
                self.filter_order_spin.setValue(4)  # Reduce order for stability
                logging.info("Reduced filter order to 4 for Chebyshev filter stability")
            
            # Ensure ripple is in a stable range
            current_ripple = self.ripple_spin.value()
            if current_ripple < 0.5:
                self.ripple_spin.setValue(1.0)
                logging.info("Increased ripple to 1.0 dB for Chebyshev filter stability")

    def _toggle_advanced_filters(self) -> None:
        """Toggle advanced filters application."""
        self.applied = not self.applied
        
        # If no channels selected, pass empty list to indicate "all channels"
        channels_to_filter = self.selected_channels.copy() if self.selected_channels else []
        
        # Get dynamic basic bandpass parameters
        basic_params = self._get_basic_bandpass_params()
        
        # Get filter-specific parameters
        filter_type = self.filter_type_combo.currentData()
        order = self.filter_order_spin.value()
        ripple = self.ripple_spin.value()
        
        # Additional validation for Chebyshev filters
        if filter_type in [FilterTypes.CHEBYSHEV_TYPE_1, FilterTypes.CHEBYSHEV_TYPE_1_ZERO_PHASE]:
            # Ensure stable parameters for Chebyshev
            if order > 6:
                order = 4
                self.filter_order_spin.setValue(4)
                logging.warning("Reduced Chebyshev filter order to 4 for stability")
            
            if ripple < 0.5:
                ripple = 1.0
                self.ripple_spin.setValue(1.0)
                logging.warning("Increased Chebyshev ripple to 1.0 dB for stability")
        
        params = {
            "apply": self.applied,
            "filter_type": filter_type,
            "window_function": self.window_function_combo.currentData(),
            "low_cut": basic_params["low_cut"],  # Use dynamic basic parameters
            "high_cut": basic_params["high_cut"],  # Use dynamic basic parameters
            "order": order,
            "ripple": ripple,  # Will be converted to int in processor
            "selected_channels": channels_to_filter,
        }
        
        self.apply_requested.emit(params)
        
        # Update button appearance
        if self.applied:
            self.apply_adv_filter_btn.setText("Remove Advanced Filters")
            self.apply_adv_filter_btn.setStyleSheet("background-color: #AA3333; color: white;")
        else:
            self.apply_adv_filter_btn.setText("Apply Advanced Filters")
            self.apply_adv_filter_btn.setStyleSheet("")

    def _on_settings_changed(self) -> None:
        """Emit signal when settings change for dynamic update."""
        # Only emit if advanced filters are currently applied
        if hasattr(self, 'applied') and self.applied:
            settings = self.get_advanced_filter_settings()
            self.settings_changed.emit(settings)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the widget."""
        self.apply_adv_filter_btn.setEnabled(enabled)
        
        if not enabled:
            self.applied = False
            self.apply_adv_filter_btn.setText("Apply Advanced Filters")
            self.apply_adv_filter_btn.setStyleSheet("")

    def get_advanced_filter_settings(self) -> Dict[str, Any]:
        """Get current advanced filter settings."""
        # If no channels selected, pass empty list to indicate "all channels"
        channels_to_filter = self.selected_channels.copy() if self.selected_channels else []
        
        # Get dynamic bandpass parameters
        basic_params = self._get_basic_bandpass_params()
        
        return {
            "filter_type": self.filter_type_combo.currentData(),
            "window_function": self.window_function_combo.currentData(),
            "applied": self.applied,
            "low_cut": basic_params["low_cut"],  # Use dynamic basic parameters
            "high_cut": basic_params["high_cut"],  # Use dynamic basic parameters
            "order": self.filter_order_spin.value(),
            "ripple": self.ripple_spin.value(),
            "selected_channels": channels_to_filter,
        }
