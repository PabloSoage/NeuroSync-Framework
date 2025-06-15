from typing import Any, Optional, Dict, List
import logging
import base64
from io import BytesIO

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QProgressBar,
    QTextEdit,
    QDialog,
    QDialogButtonBox,
    QScrollArea,
    QFrame,
    QGridLayout,
)
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QPixmap
import numpy as np

from .base_panel import BasePanel
from ..utils.help_system import HelpButton
from ..services.mne_service import MNEService
from ..services.data_access_service import DataAccessService

# Check if MNE is available
try:
    import mne
    MNE_AVAILABLE = True
except ImportError:
    MNE_AVAILABLE = False


class ChannelSelectionDialog(QDialog):
    """Dialog for selecting EEG channels for MNE analysis."""
    
    def __init__(self, channel_names: List[str], selected_channels: List[int] = None, parent=None):
        """
        Initialize the channel selection dialog.
        
        Args:
            channel_names: List of channel names
            selected_channels: List of initially selected channel indices
            parent: Parent widget
        """
        super().__init__(parent)
        self.channel_names = channel_names
        self.selected_channels = selected_channels or list(range(len(channel_names)))
        self.checkboxes = []
        
        self.setup_ui()
        self.apply_dark_theme()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Select EEG Channels")
        self.setModal(True)
        self.resize(400, 500)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Select channels to include in MNE analysis:")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Selection controls
        controls_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        controls_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all)
        controls_layout.addWidget(deselect_all_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Scrollable area for checkboxes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(300)
        
        # Container widget for checkboxes
        container_widget = QFrame()
        container_layout = QGridLayout(container_widget)
        
        # Create checkboxes for each channel
        for i, channel_name in enumerate(self.channel_names):
            checkbox = QCheckBox(f"{channel_name}")
            checkbox.setChecked(i in self.selected_channels)
            self.checkboxes.append(checkbox)
            
            # Arrange in 2 columns
            row = i // 2
            col = i % 2
            container_layout.addWidget(checkbox, row, col)
        
        scroll_area.setWidget(container_widget)
        layout.addWidget(scroll_area)
        
        # Info label
        self.info_label = QLabel()
        self.update_info_label()
        layout.addWidget(self.info_label)
        
        # Connect checkboxes to update info
        for checkbox in self.checkboxes:
            checkbox.toggled.connect(self.update_info_label)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def apply_dark_theme(self):
        """Apply dark theme styling to the dialog."""
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
            }
            QCheckBox {
                color: #ffffff;
                background-color: transparent;
                spacing: 8px;
                padding: 4px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #555555;
                border-radius: 3px;
                background-color: #3a3a3a;
            }
            QCheckBox::indicator:checked {
                background-color: #007ACC;
                border-color: #007ACC;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #1e90ff;
                border-color: #1e90ff;
            }
            QCheckBox::indicator:hover {
                border-color: #777777;
                background-color: #4a4a4a;
            }
            QPushButton {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #505050;
                border-color: #777777;
            }
            QPushButton:pressed {
                background-color: #353535;
            }
            QScrollArea {
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #1e1e1e;
            }
            QFrame {
                background-color: #1e1e1e;
                border: none;
            }
            QDialogButtonBox QPushButton {
                min-width: 80px;
            }
            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #777777;
            }
        """)
        
    def select_all(self):
        """Select all channels."""
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)
            
    def deselect_all(self):
        """Deselect all channels."""
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)
            
    def update_info_label(self):
        """Update the info label with selection count."""
        selected_count = sum(1 for cb in self.checkboxes if cb.isChecked())
        total_count = len(self.checkboxes)
        self.info_label.setText(f"Selected: {selected_count} of {total_count} channels")
        
    def get_selected_channels(self) -> List[int]:
        """Get the list of selected channel indices."""
        return [i for i, cb in enumerate(self.checkboxes) if cb.isChecked()]


class MNEPanel(BasePanel):
    """Panel for MNE integration and analysis."""

    # Custom signals for async operations
    conversion_completed = pyqtSignal(str, dict)  # task_id, result
    visualization_completed = pyqtSignal(str, dict)  # task_id, result

    def __init__(
        self,
        collector_service: Any,
        processor_service: Any,
        parent: Optional[Any] = None,
    ) -> None:
        """Initialize the MNE panel."""
        super().__init__(parent)
        self.collector_service = collector_service
        self.processor_service = processor_service
        
        # Get MNE service and data access service
        self.mne_service = MNEService.get_instance()
        self.data_service = DataAccessService.get_instance()
        
        # Current task tracking
        self.current_conversion_task: Optional[str] = None
        self.current_visualization_task: Optional[str] = None
        
        # Channel selection state
        self.selected_channels: List[int] = []
        self.channel_names: List[str] = []
        
        # Setup UI components
        if self.mne_service.is_available():
            self.setup_mne_conversion()
            self.setup_mne_visualization()
            self.setup_status_monitoring()
            
            # Start MNE service
            self.mne_service.start_service()
        else:
            self.setup_mne_not_available()

        # Connect signals
        self.conversion_completed.connect(self._on_conversion_completed)
        self.visualization_completed.connect(self._on_visualization_completed)

        # Setup timer for checking task status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._check_task_status)

        # Initialize channel selection
        self._update_channel_selection()

        # Check if streaming is already active when panel is created
        self._check_initial_streaming_state()

        # Add stretch to push everything to the top
        self.layout.addStretch()

    def _check_initial_streaming_state(self):
        """Check if streaming is already active when the panel is created."""
        try:
            # Check if data service indicates streaming is active
            if self.data_service.is_streaming():
                self.enable_processing(True)
            # Also check collector service directly
            elif hasattr(self.collector_service, 'is_streaming_active') and self.collector_service.is_streaming_active():
                self.enable_processing(True)
        except Exception as e:
            logging.debug(f"Error checking initial streaming state: {e}")

    def _update_channel_selection(self):
        """Update channel selection based on current data."""
        try:
            # Get channel information from data service
            metadata = self.data_service.get_metadata()
            self.channel_names = metadata.get("channel_names", [])
            eeg_channels = metadata.get("eeg_channels", [])
            
            # If no channel names, create generic names
            if not self.channel_names and eeg_channels:
                self.channel_names = [f"CH{i+1}" for i in range(len(eeg_channels))]
            
            # Initialize selected channels to all available channels
            if not self.selected_channels and self.channel_names:
                self.selected_channels = list(range(len(self.channel_names)))
                
        except Exception as e:
            logging.debug(f"Error updating channel selection: {e}")

    def setup_mne_not_available(self) -> None:
        """Show warning when MNE is not installed."""
        warning_label = QLabel(
            "MNE package is not installed. Please install it using: pip install mne"
        )
        warning_label.setStyleSheet("color: #FFAA33; font-weight: bold;")
        self.layout.addWidget(warning_label)

    def setup_mne_conversion(self) -> None:
        """Set up MNE conversion section."""
        mne_group = QGroupBox("Convert to MNE Format")
        mne_layout = QVBoxLayout(mne_group)

        # Add help button for MNE
        mne_header_layout = QHBoxLayout()
        mne_header_layout.addWidget(QLabel("MNE Integration"))
        mne_header_layout.addWidget(HelpButton("mne", self))
        mne_header_layout.addStretch()
        mne_layout.addLayout(mne_header_layout)

        # Add description
        mne_layout.addWidget(
            QLabel("Convert BrainFlow data to MNE format for advanced analysis (all channels)")
        )

        # MNE Parameters
        mne_params_layout = QHBoxLayout()
        mne_params_layout.addWidget(QLabel("Data Duration (seconds):"))
        self.mne_duration_spin = QSpinBox()
        self.mne_duration_spin.setRange(1, 60)
        self.mne_duration_spin.setValue(10)
        mne_params_layout.addWidget(self.mne_duration_spin)
        
        # Add unit conversion option
        mne_params_layout.addWidget(QLabel("Auto Convert to V:"))
        self.convert_to_v_check = QCheckBox()
        self.convert_to_v_check.setChecked(True)
        mne_params_layout.addWidget(self.convert_to_v_check)

        mne_layout.addLayout(mne_params_layout)

        # Remove channel selection from conversion section - it's now only for visualization

        # MNE Control buttons
        mne_buttons_layout = QHBoxLayout()

        self.convert_to_mne_btn = QPushButton("Convert to MNE")
        self.convert_to_mne_btn.clicked.connect(self.convert_to_mne)
        self.convert_to_mne_btn.setEnabled(False)
        mne_buttons_layout.addWidget(self.convert_to_mne_btn)

        self.cancel_conversion_btn = QPushButton("Cancel")
        self.cancel_conversion_btn.clicked.connect(self.cancel_conversion)
        self.cancel_conversion_btn.setEnabled(False)
        mne_buttons_layout.addWidget(self.cancel_conversion_btn)

        mne_layout.addLayout(mne_buttons_layout)

        # Progress bar for conversion
        self.conversion_progress = QProgressBar()
        self.conversion_progress.setVisible(False)
        mne_layout.addWidget(self.conversion_progress)

        self.layout.addWidget(mne_group)

    def setup_mne_visualization(self) -> None:
        """Set up MNE visualization section."""
        mne_viz_group = QGroupBox("MNE Visualization")
        mne_viz_layout = QVBoxLayout(mne_viz_group)

        # Plot selection
        plot_selection_layout = QHBoxLayout()
        plot_selection_layout.addWidget(QLabel("Plot Type:"))
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["PSD", "Topomap", "Raw Data", "Spectrogram"])
        plot_selection_layout.addWidget(self.plot_type_combo)
        
        # Frequency range for PSD
        plot_selection_layout.addWidget(QLabel("Freq Range:"))
        self.freq_min_spin = QSpinBox()
        self.freq_min_spin.setRange(1, 100)
        self.freq_min_spin.setValue(1)
        self.freq_min_spin.setSuffix(" Hz")
        plot_selection_layout.addWidget(self.freq_min_spin)
        
        self.freq_max_spin = QSpinBox()
        self.freq_max_spin.setRange(1, 100)
        self.freq_max_spin.setValue(50)
        self.freq_max_spin.setSuffix(" Hz")
        plot_selection_layout.addWidget(self.freq_max_spin)
        
        mne_viz_layout.addLayout(plot_selection_layout)

        # Topomap Band Selection (NEW)
        topomap_band_layout = QHBoxLayout()
        topomap_band_layout.addWidget(QLabel("Topomap Band:"))
        
        self.topomap_band_combo = QComboBox()
        self.topomap_band_combo.addItems([
            "Alpha (8-13 Hz)", 
            "Delta (1-4 Hz)", 
            "Theta (4-8 Hz)", 
            "Beta (13-30 Hz)", 
            "Gamma (30-50 Hz)",
            "Custom Range"
        ])
        self.topomap_band_combo.setCurrentText("Alpha (8-13 Hz)")  # Default to Alpha
        self.topomap_band_combo.currentTextChanged.connect(self._on_topomap_band_changed)
        topomap_band_layout.addWidget(self.topomap_band_combo)
        
        # Custom range controls (initially hidden)
        topomap_band_layout.addWidget(QLabel("Custom:"))
        self.topomap_freq_min_spin = QSpinBox()
        self.topomap_freq_min_spin.setRange(1, 100)
        self.topomap_freq_min_spin.setValue(8)
        self.topomap_freq_min_spin.setSuffix(" Hz")
        self.topomap_freq_min_spin.setVisible(False)
        topomap_band_layout.addWidget(self.topomap_freq_min_spin)
        
        topomap_band_layout.addWidget(QLabel("-"))
        self.topomap_range_separator = topomap_band_layout.itemAt(topomap_band_layout.count()-1).widget()
        self.topomap_range_separator.setVisible(False)
        
        self.topomap_freq_max_spin = QSpinBox()
        self.topomap_freq_max_spin.setRange(1, 100)
        self.topomap_freq_max_spin.setValue(13)
        self.topomap_freq_max_spin.setSuffix(" Hz")
        self.topomap_freq_max_spin.setVisible(False)
        topomap_band_layout.addWidget(self.topomap_freq_max_spin)
        
        topomap_band_layout.addStretch()
        mne_viz_layout.addLayout(topomap_band_layout)

        # Channel selection (MOVED HERE from conversion section)
        channel_selection_layout = QHBoxLayout()
        channel_selection_layout.addWidget(QLabel("Channels to Display:"))
        
        self.selected_channels_label = QLabel("All channels")
        self.selected_channels_label.setStyleSheet("color: #CCCCCC; font-style: italic;")
        channel_selection_layout.addWidget(self.selected_channels_label)
        
        channel_selection_layout.addStretch()
        
        self.select_channels_btn = QPushButton("Select Channels")
        self.select_channels_btn.clicked.connect(self.open_channel_selection)
        self.select_channels_btn.setStyleSheet("background-color: #007ACC;")
        channel_selection_layout.addWidget(self.select_channels_btn)
        
        mne_viz_layout.addLayout(channel_selection_layout)

        # PSD Options
        psd_options_layout = QHBoxLayout()
        psd_options_layout.addWidget(QLabel("PSD Mode:"))
        
        self.psd_individual_check = QCheckBox("Show Individual Channels")
        self.psd_individual_check.setChecked(True)  # Default to individual channels
        self.psd_individual_check.setToolTip("Show each channel as a separate colored line")
        psd_options_layout.addWidget(self.psd_individual_check)
        
        # Add some spacing
        psd_options_layout.addWidget(QLabel("   "))
        
        # Info label for PSD mode
        self.psd_mode_info = QLabel("(Individual channels with colors)")
        self.psd_mode_info.setStyleSheet("color: #888888; font-style: italic; font-size: 10px;")
        psd_options_layout.addWidget(self.psd_mode_info)
        
        psd_options_layout.addStretch()
        mne_viz_layout.addLayout(psd_options_layout)
        
        # Connect checkbox to update info
        self.psd_individual_check.toggled.connect(self._update_psd_mode_info)

        mne_viz_buttons = QHBoxLayout()

        self.plot_mne_btn = QPushButton("Generate Plot")
        self.plot_mne_btn.clicked.connect(self.plot_mne_visualization)
        self.plot_mne_btn.setEnabled(False)
        mne_viz_buttons.addWidget(self.plot_mne_btn)

        self.cancel_plot_btn = QPushButton("Cancel Plot")
        self.cancel_plot_btn.clicked.connect(self.cancel_visualization)
        self.cancel_plot_btn.setEnabled(False)
        mne_viz_buttons.addWidget(self.cancel_plot_btn)

        mne_viz_layout.addLayout(mne_viz_buttons)

        # Progress bar for visualization
        self.plot_progress = QProgressBar()
        self.plot_progress.setVisible(False)
        mne_viz_layout.addWidget(self.plot_progress)

        # Plot display area with proper background and better sizing
        self.plot_display = QLabel()
        self.plot_display.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        self.plot_display.setMinimumHeight(450)  # Increased height
        self.plot_display.setMinimumWidth(600)   # Ensure minimum width
        # Use KeepAspectRatio to prevent text distortion
        self.plot_display.setScaledContents(False)
        self.plot_display.setAlignment(Qt.AlignCenter)
        self.plot_display.setText("No plot generated yet")
        self.plot_display.setWordWrap(True)
        mne_viz_layout.addWidget(self.plot_display)

        self.layout.addWidget(mne_viz_group)

    def _on_topomap_band_changed(self):
        """Handle topomap band selection change."""
        selected_band = self.topomap_band_combo.currentText()
        
        # Show/hide custom range controls
        is_custom = "Custom Range" in selected_band
        self.topomap_freq_min_spin.setVisible(is_custom)
        self.topomap_freq_max_spin.setVisible(is_custom)
        self.topomap_range_separator.setVisible(is_custom)
        
        # Update custom range values based on selected band
        if not is_custom:
            if "Alpha" in selected_band:
                self.topomap_freq_min_spin.setValue(8)
                self.topomap_freq_max_spin.setValue(13)
            elif "Delta" in selected_band:
                self.topomap_freq_min_spin.setValue(1)
                self.topomap_freq_max_spin.setValue(4)
            elif "Theta" in selected_band:
                self.topomap_freq_min_spin.setValue(4)
                self.topomap_freq_max_spin.setValue(8)
            elif "Beta" in selected_band:
                self.topomap_freq_min_spin.setValue(13)
                self.topomap_freq_max_spin.setValue(30)
            elif "Gamma" in selected_band:
                self.topomap_freq_min_spin.setValue(30)
                self.topomap_freq_max_spin.setValue(50)

    def _get_topomap_frequency_range(self) -> tuple:
        """Get the frequency range for topomap based on current selection."""
        selected_band = self.topomap_band_combo.currentText()
        
        if "Custom Range" in selected_band:
            return (self.topomap_freq_min_spin.value(), self.topomap_freq_max_spin.value())
        elif "Alpha" in selected_band:
            return (8, 13)
        elif "Delta" in selected_band:
            return (1, 4)
        elif "Theta" in selected_band:
            return (4, 8)
        elif "Beta" in selected_band:
            return (13, 30)
        elif "Gamma" in selected_band:
            return (30, 50)
        else:
            return (8, 13)  # Default to Alpha

    def setup_status_monitoring(self) -> None:
        """Set up status monitoring section."""
        status_group = QGroupBox("Operation Status")
        status_layout = QVBoxLayout(status_group)

        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
                font-family: monospace;
            }
        """)
        status_layout.addWidget(self.status_text)

        self.layout.addWidget(status_group)

    def convert_to_mne(self) -> None:
        """Convert BrainFlow data to MNE format asynchronously (ALL channels)."""
        if not self.mne_service.is_available():
            self.show_error("MNE Error", "MNE package is not installed")
            return

        # Update channel selection in case it hasn't been initialized
        self._update_channel_selection()

        # Always convert ALL available channels - selection is applied only during visualization
        if not self.channel_names:
            self.show_error("MNE Error", "No channels available. Start streaming first.")
            return

        try:
            # Get parameters
            duration_seconds = self.mne_duration_spin.value()
            convert_to_v = self.convert_to_v_check.isChecked()

            # Start conversion with ALL channels (pass None for selected_channels)
            self.current_conversion_task = self.mne_service.convert_to_mne_async(
                duration_seconds=duration_seconds,
                convert_to_v=convert_to_v,
                selected_channels=None,  # Convert ALL channels
                callback=self._conversion_callback
            )

            # Update UI state
            self.convert_to_mne_btn.setEnabled(False)
            self.cancel_conversion_btn.setEnabled(True)
            self.conversion_progress.setVisible(True)
            self.conversion_progress.setRange(0, 0)  # Indeterminate progress

            # Start status monitoring
            self.status_timer.start(100)  # Check every 100ms

            total_channels = len(self.channel_names)
            self._add_status_message(f"Starting MNE conversion with ALL {total_channels} available channels")
            self.show_status("Converting all channel data to MNE format...")

        except Exception as e:
            self.show_error("MNE Error", f"Error starting conversion: {str(e)}")
            logging.error(f"MNE conversion start error: {e}")

    def cancel_conversion(self) -> None:
        """Cancel the current MNE conversion."""
        if self.current_conversion_task:
            if self.mne_service.cancel_task(self.current_conversion_task):
                self._add_status_message(f"Cancelled conversion task: {self.current_conversion_task}")
                self.show_status("Conversion cancelled")
            else:
                self._add_status_message("Failed to cancel conversion task")

            self._reset_conversion_ui()
            self.current_conversion_task = None

    def plot_mne_visualization(self) -> None:
        """Create MNE visualization asynchronously."""
        if not self.current_conversion_task:
            self.show_error("MNE Error", "No MNE data available. Convert data first.")
            return

        # Check if conversion is complete
        status = self.mne_service.get_task_status(self.current_conversion_task)
        if not status.get("ready") or not status.get("successful"):
            self.show_error("MNE Error", "MNE conversion not complete or failed.")
            return

        # Update channel selection (in case user changed it after conversion)
        self._update_channel_selection()
        
        # If no channels selected, use all available
        if not self.selected_channels:
            if self.channel_names:
                self.selected_channels = list(range(len(self.channel_names)))
                self._update_selected_channels_label()

        try:
            # Get plot parameters
            plot_type = self.plot_type_combo.currentText()
            freq_min = self.freq_min_spin.value()
            freq_max = self.freq_max_spin.value()
            
            # Get topomap frequency range
            topomap_freq_min, topomap_freq_max = self._get_topomap_frequency_range()
            
            # Get PSD mode preference
            show_individual = self.psd_individual_check.isChecked()

            # Get current theme background color
            bg_color = "#2b2b2b"  # Dark theme background

            # Start visualization with selected channels for display
            self.current_visualization_task = self.mne_service.create_visualization_async(
                task_id=self.current_conversion_task,
                plot_type=plot_type,
                freq_min=freq_min,
                freq_max=freq_max,
                bg_color=bg_color,
                show_individual_channels=show_individual,
                selected_channels_for_display=self.selected_channels,
                topomap_freq_range=(topomap_freq_min, topomap_freq_max),  # NEW: Pass topomap frequency range
                callback=self._visualization_callback
            )

            # Update UI state
            self.plot_mne_btn.setEnabled(False)
            self.cancel_plot_btn.setEnabled(True)
            self.plot_progress.setVisible(True)
            self.plot_progress.setRange(0, 0)  # Indeterminate progress

            psd_mode = "individual" if show_individual else "averaged"
            selected_names = [self.channel_names[i] for i in self.selected_channels if i < len(self.channel_names)]
            
            # Include topomap band info in status message
            band_name = self.topomap_band_combo.currentText()
            if plot_type.lower() == "topomap":
                self._add_status_message(f"Starting {plot_type} visualization with {band_name} ({topomap_freq_min}-{topomap_freq_max} Hz) using {len(self.selected_channels)} channels: {', '.join(selected_names[:3])}{'...' if len(selected_names) > 3 else ''}")
            else:
                self._add_status_message(f"Starting {plot_type} visualization ({psd_mode}) with {len(self.selected_channels)} channels: {', '.join(selected_names[:3])}{'...' if len(selected_names) > 3 else ''}")
            
            self.show_status(f"Generating {plot_type} visualization...")

        except Exception as e:
            self.show_error("MNE Error", f"Error starting visualization: {str(e)}")
            logging.error(f"MNE visualization start error: {e}")

    def cancel_visualization(self) -> None:
        """Cancel the current visualization."""
        if self.current_visualization_task:
            if self.mne_service.cancel_task(self.current_visualization_task):
                self._add_status_message(f"Cancelled visualization task: {self.current_visualization_task}")
                self.show_status("Visualization cancelled")
            else:
                self._add_status_message("Failed to cancel visualization task")

            self._reset_visualization_ui()
            self.current_visualization_task = None

    def _conversion_callback(self, task_id: str, result: Dict[str, Any]) -> None:
        """Callback for conversion completion (called from process)."""
        # Emit signal to update UI in main thread
        self.conversion_completed.emit(task_id, result)

    def _visualization_callback(self, task_id: str, result: Dict[str, Any]) -> None:
        """Callback for visualization completion (called from process)."""
        # Emit signal to update UI in main thread
        self.visualization_completed.emit(task_id, result)

    def _on_conversion_completed(self, task_id: str, result: Dict[str, Any]) -> None:
        """Handle conversion completion in main thread."""
        if result.get("success"):
            channels_used = result.get('channels', 0)
            self._add_status_message(f"Conversion completed successfully: {task_id} (ALL {channels_used} channels converted)")
            self.show_status(f"Converted {result.get('duration', 0)}s of ALL channel data to MNE format ({channels_used} channels)")
            
            # Enable plot button and channel selection
            self.plot_mne_btn.setEnabled(True)
            if hasattr(self, 'select_channels_btn'):
                self.select_channels_btn.setEnabled(True)
        else:
            error_msg = result.get("error", "Unknown error")
            self._add_status_message(f"Conversion failed: {error_msg}")
            self.show_error("MNE Conversion Error", error_msg)

        self._reset_conversion_ui()

    def _on_visualization_completed(self, task_id: str, result: Dict[str, Any]) -> None:
        """Handle visualization completion in main thread."""
        if result.get("success"):
            self._add_status_message(f"Visualization completed: {task_id}")
            self.show_status(f"Generated {result.get('plot_type', '')} visualization")
            
            # Display the plot
            self._display_plot(result.get("plot_data"))
        else:
            error_msg = result.get("error", "Unknown error")
            self._add_status_message(f"Visualization failed: {error_msg}")
            self.show_error("MNE Visualization Error", error_msg)

        self._reset_visualization_ui()

    def _display_plot(self, plot_data: str) -> None:
        """Display the generated plot with proper scaling."""
        if plot_data:
            try:
                # Decode base64 plot data
                image_data = base64.b64decode(plot_data)
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                
                if not pixmap.isNull():
                    # Scale pixmap to fit the display area while maintaining aspect ratio
                    display_size = self.plot_display.size()
                    scaled_pixmap = pixmap.scaled(
                        display_size, 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation  # Use smooth transformation for better quality
                    )
                    
                    # Display in label
                    self.plot_display.setPixmap(scaled_pixmap)
                    self.plot_display.setText("")  # Clear text
                else:
                    self.plot_display.setText("Error: Could not load plot image")
                
            except Exception as e:
                logging.error(f"Error displaying plot: {e}")
                self.plot_display.setText(f"Error displaying plot: {str(e)}")
        else:
            self.plot_display.setText("No plot data received")

    def _check_task_status(self) -> None:
        """Check status of active tasks."""
        # Update status of conversion task
        if self.current_conversion_task:
            status = self.mne_service.get_task_status(self.current_conversion_task)
            if status:
                self._add_status_message(f"Conversion task status: {status.get('status', 'unknown')}")
        
        # Update status of visualization task
        if self.current_visualization_task:
            status = self.mne_service.get_task_status(self.current_visualization_task)
            if status:
                self._add_status_message(f"Visualization task status: {status.get('status', 'unknown')}")
        
        # Stop timer if no active tasks
        if not self.current_conversion_task and not self.current_visualization_task:
            self.status_timer.stop()

    def _reset_conversion_ui(self) -> None:
        """Reset conversion UI elements."""
        self.convert_to_mne_btn.setEnabled(True)
        self.cancel_conversion_btn.setEnabled(False)
        self.conversion_progress.setVisible(False)

    def _reset_visualization_ui(self) -> None:
        """Reset visualization UI elements."""
        self.plot_mne_btn.setEnabled(True)
        self.cancel_plot_btn.setEnabled(False)
        self.plot_progress.setVisible(False)

    def _add_status_message(self, message: str) -> None:
        """Add a status message to the status text area."""
        if hasattr(self, 'status_text'):
            import time
            timestamp = time.strftime("%H:%M:%S")
            self.status_text.append(f"[{timestamp}] {message}")

    def enable_processing(self, enabled: bool) -> None:
        """Enable or disable MNE processing controls."""
        if hasattr(self, 'convert_to_mne_btn'):
            # Always enable the button when streaming is active, regardless of channel selection
            # The button logic will handle channel selection internally
            if enabled and not self.current_conversion_task:
                self.convert_to_mne_btn.setEnabled(True)
            elif not enabled:
                self.convert_to_mne_btn.setEnabled(False)

        # Enable/disable channel selection
        if hasattr(self, 'select_channels_btn'):
            self.select_channels_btn.setEnabled(enabled)

        # Reset dependent buttons if disabling
        if not enabled:
            if hasattr(self, 'plot_mne_btn'):
                self.plot_mne_btn.setEnabled(False)
            self.current_conversion_task = None
            self.current_visualization_task = None
        
        # Update channel selection when enabling to ensure it's current
        if enabled:
            self._update_channel_selection()
            self._update_selected_channels_label()

    # API compatibility methods
    def get_mne_settings(self) -> Dict[str, Any]:
        """Get current MNE settings."""
        if not self.mne_service.is_available():
            return {"available": False}

        # Get topomap frequency range
        topomap_freq_min, topomap_freq_max = self._get_topomap_frequency_range()

        return {
            "available": True,
            "duration": self.mne_duration_spin.value() if hasattr(self, "mne_duration_spin") else 10,
            "convert_to_v": self.convert_to_v_check.isChecked() if hasattr(self, "convert_to_v_check") else True,
            "plot_type": self.plot_type_combo.currentText() if hasattr(self, "plot_type_combo") else "PSD",
            "freq_range": [
                self.freq_min_spin.value() if hasattr(self, "freq_min_spin") else 1,
                self.freq_max_spin.value() if hasattr(self, "freq_max_spin") else 50
            ],
            "topomap_band": self.topomap_band_combo.currentText() if hasattr(self, "topomap_band_combo") else "Alpha (8-13 Hz)",
            "topomap_freq_range": [topomap_freq_min, topomap_freq_max],
            "selected_channels": self.selected_channels,
            "channel_names": self.channel_names,
            "psd_individual_mode": self.psd_individual_check.isChecked() if hasattr(self, "psd_individual_check") else True
        }

    def update_mne_plot(self, plot_data: Dict[str, Any]) -> bool:
        """Update MNE plot from API call."""
        if not self.mne_service.is_available():
            return False

        try:
            plot_type = plot_data.get("type", "psd")
            
            if plot_type.lower() in ["psd", "topomap", "raw data", "spectrogram"]:
                # Set the combo box and trigger plotting
                if hasattr(self, 'plot_type_combo'):
                    index = self.plot_type_combo.findText(plot_type.title())
                    if index >= 0:
                        self.plot_type_combo.setCurrentIndex(index)
                        
                self.plot_mne_visualization()
                return True
            
            return False
            
        except Exception as e:
            self.show_error("MNE Plot Update Error", str(e))
            return False

    def closeEvent(self, event) -> None:
        """Handle panel close event."""
        # Cancel any active tasks
        if self.current_conversion_task:
            self.mne_service.cancel_task(self.current_conversion_task)
        if self.current_visualization_task:
            self.mne_service.cancel_task(self.current_visualization_task)
        
        # Stop timer
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()
        
        super().closeEvent(event)

    def open_channel_selection(self):
        """Open the channel selection dialog."""
        try:
            # Update channel information
            self._update_channel_selection()
            
            if not self.channel_names:
                self.show_error("Channel Selection", "No channels available. Start streaming first.")
                return
            
            # Create and show dialog
            dialog = ChannelSelectionDialog(
                channel_names=self.channel_names,
                selected_channels=self.selected_channels,
                parent=self
            )
            
            if dialog.exec_() == QDialog.Accepted:
                # Update selected channels
                self.selected_channels = dialog.get_selected_channels()
                self._update_selected_channels_label()
                
                self._add_status_message(f"Selected {len(self.selected_channels)} channels for MNE analysis")
                
        except Exception as e:
            self.show_error("Channel Selection Error", f"Error opening channel selection: {str(e)}")
            logging.error(f"Channel selection error: {e}")

    def _update_selected_channels_label(self):
        """Update the selected channels label."""
        if not self.selected_channels:
            self.selected_channels_label.setText("No channels selected")
            self.selected_channels_label.setStyleSheet("color: #FF6B6B; font-style: italic;")
        elif len(self.selected_channels) == len(self.channel_names):
            self.selected_channels_label.setText("All channels")
            self.selected_channels_label.setStyleSheet("color: #96CEB4; font-style: italic;")
        else:
            # Show first few channel names
            if len(self.selected_channels) <= 3:
                names = [self.channel_names[i] for i in self.selected_channels if i < len(self.channel_names)]
                text = ", ".join(names)
            else:
                names = [self.channel_names[i] for i in self.selected_channels[:3] if i < len(self.channel_names)]
                text = f"{', '.join(names)}... ({len(self.selected_channels)} total)"
            
            self.selected_channels_label.setText(text)
            self.selected_channels_label.setStyleSheet("color: #CCCCCC; font-style: italic;")

    def _update_psd_mode_info(self):
        """Update the PSD mode information label."""
        if self.psd_individual_check.isChecked():
            self.psd_mode_info.setText("(Individual channels with colors)")
        else:
            self.psd_mode_info.setText("(Average with variability band)")