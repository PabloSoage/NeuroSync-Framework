from typing import Any, Dict, Optional, List

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QWidget,
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
        self.filter_type_combo.addItem("Butterworth", FilterTypes.BUTTERWORTH)
        self.filter_type_combo.addItem("Chebyshev Type 1", FilterTypes.CHEBYSHEV_TYPE_1)
        self.filter_type_combo.addItem("Bessel", FilterTypes.BESSEL)
        self.filter_type_combo.addItem(
            "Butterworth Zero Phase", FilterTypes.BUTTERWORTH_ZERO_PHASE
        )
        # Connect to dynamic update
        self.filter_type_combo.currentIndexChanged.connect(self._on_settings_changed)
        filter_type_layout.addWidget(self.filter_type_combo)

        filter_type_layout.addWidget(QLabel("Window Function:"))
        self.window_function_combo = QComboBox()
        self.window_function_combo.addItem("Hanning", WindowOperations.HANNING)
        self.window_function_combo.addItem("Hamming", WindowOperations.HAMMING)
        self.window_function_combo.addItem(
            "Blackman Harris", WindowOperations.BLACKMAN_HARRIS
        )
        self.window_function_combo.addItem("No Window", WindowOperations.NO_WINDOW)
        # Connect to dynamic update
        self.window_function_combo.currentIndexChanged.connect(self._on_settings_changed)
        filter_type_layout.addWidget(self.window_function_combo)

        adv_filter_layout.addLayout(filter_type_layout)

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
            self.selected_channels = dialog.get_selected_channels()
            self._update_channel_display()
            # Emit settings change if filters are currently applied
            self._on_settings_changed()

    def _update_channel_display(self) -> None:
        """Update the channel selection display."""
        if not self.channel_names:
            self.filter_channel_info_label.setText("No channels available")
            self.filter_channel_select_btn.setEnabled(False)
            return
        
        self.filter_channel_select_btn.setEnabled(True)
        
        if not self.selected_channels:
            self.filter_channel_info_label.setText("No channels selected")
        elif len(self.selected_channels) == len(self.channel_names):
            self.filter_channel_info_label.setText("All channels selected")
        else:
            count = len(self.selected_channels)
            total = len(self.channel_names)
            self.filter_channel_info_label.setText(f"{count}/{total} channels selected")

    def update_channels(self, channel_names: List[str]) -> None:
        """Update available channels."""
        self.channel_names = channel_names.copy()
        
        # Reset selected channels to all channels
        self.selected_channels = list(range(len(self.channel_names)))
        self._update_channel_display()

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
            "selected_channels": self.selected_channels.copy(),
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
        return {
            "filter_type": self.filter_type_combo.currentData(),
            "window_function": self.window_function_combo.currentData(),
            "applied": self.applied,
            "low_cut": 1.0,  # Could be made configurable
            "high_cut": 50.0,  # Could be made configurable
            "order": 4,
            "selected_channels": self.selected_channels.copy(),
        }
