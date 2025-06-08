"""
Synchronized data visualization panel.

This module provides a UI component for visualizing synchronized EEG and input data.
"""

from typing import Optional, List, Dict, Any, Tuple

import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QGridLayout,
    QScrollArea,
    QFrame,
    QDoubleSpinBox,
    QToolTip,
    QDialog,
    QTextBrowser,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# Use a consistent help button style similar to the one in UnifiedRecordingPanel
class HelpButton(QPushButton):
    """Custom button for showing help tooltips."""

    def __init__(self, help_topic: str, parent: Optional[QWidget] = None) -> None:
        """
        Initialize help button.

        Args:
            help_topic: Topic identifier or help text content
            parent: Parent widget
        """
        super().__init__(parent)
        self.help_topic = help_topic
        self.setText("?")
        self.setFixedSize(20, 20)
        self.setToolTip("Click for help")

        # Style the button to make it look like a help icon (same as in recording_panel)
        self.setStyleSheet(
            """
            QPushButton {
                border-radius: 10px;
                background-color: #007ACC;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #009AEE;
            }
        """
        )

        # Connect the clicked signal to show help
        self.clicked.connect(self.show_help)

    def show_help(self) -> None:
        """Show help dialog with help text."""
        # Create a non-modal dialog to avoid alert sound
        dialog = QDialog(self.parent())
        dialog.setWindowTitle("Help")
        dialog.setMinimumSize(400, 300)

        # Use a text browser for rich text support
        text_browser = QTextBrowser(dialog)
        text_browser.setOpenExternalLinks(True)

        # Get help content based on topic
        content = self._get_help_content(self.help_topic)
        text_browser.setHtml(content)

        # Set up layout
        layout = QVBoxLayout(dialog)
        layout.addWidget(text_browser)

        # Add close button
        close_button = QPushButton("Close", dialog)
        close_button.clicked.connect(dialog.accept)
        close_button.setMaximumWidth(100)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        # Show as non-modal dialog to avoid alert sound
        dialog.setModal(False)
        dialog.show()

    def _get_help_content(self, topic: str) -> str:
        """
        Get help content based on topic.

        Args:
            topic: Help topic identifier

        Returns:
            str: HTML content for help
        """
        help_contents = {
            "eeg_display": """
                <h3>EEG Display Settings</h3>
                <p>This section allows you to configure how EEG data is displayed:</p>
                <ul>
                    <li><b>Time Window:</b> Sets the time range shown in the plot (in seconds).
                    Larger values show more data but with less detail.</li>
                    <li><b>Scale:</b> Adjusts the amplitude scaling of EEG signals.
                    Increase for small signals, decrease for large signals.</li>
                    <li><b>Channel Mode:</b>
                        <ul>
                            <li><i>Stacked:</i> Shows each channel separated vertically</li>
                            <li><i>Overlaid:</i> Shows all channels on the same axis for easier comparison</li>
                        </ul>
                    </li>
                    <li><b>Show EEG/Input/Markers:</b> Toggle visibility of different data types</li>
                    <li><b>Basic Filtering:</b> Applies a simple moving average filter to reduce noise</li>
                </ul>
                <p>Use the <b>Channel Selection</b> button to choose which EEG channels to display.</p>
            """,
            "time_window": """
                <h3>Time Window</h3>
                <p>Sets the time range shown in the EEG plot (in seconds).</p>
                <p>Larger values show more data history but with less detail. Smaller values show more detailed
                waveforms but less context.</p>
            """,
            "scale": """
                <h3>Scale Factor</h3>
                <p>Adjusts the amplitude scaling of EEG signals.</p>
                <p>Increase the scale for small signals that are hard to see. Decrease for large signals that go off the screen.</p>
            """,
            "channel_mode": """
                <h3>Channel Display Mode</h3>
                <ul>
                    <li><b>Stacked:</b> Shows each channel separated vertically with space between them.
                    Better for seeing individual channel activity.</li>
                    <li><b>Overlaid:</b> Shows all channels on the same axis. Better for comparing relative amplitudes
                    and timing between channels.</li>
                </ul>
            """,
            "filtering": """
                <h3>Basic Filtering</h3>
                <p>Applies a simple moving average filter to reduce high-frequency noise in the EEG signal.</p>
                <p>This is a basic filter suitable for visualization purposes. For more advanced signal processing,
                use the dedicated processing tools in the EEG Processing tab.</p>
            """,
            "sync_tolerance": """
                <h3>Synchronization Tolerance</h3>
                <p>Sets the maximum allowed time difference between EEG and input signals.</p>
                <p><b>Recommended tolerance values:</b></p>
                <ul>
                    <li><b>1ms or lower:</b> Ultra-precise synchronization for specialized research. May cause data loss as time alignment becomes extremely strict.</li>
                    <li><b>10ms:</b> Standard research-grade synchronization, balancing precision with practicality.</li>
                    <li><b>50ms:</b> Good for most BCI applications and general research.</li>
                    <li><b>100ms:</b> Minimum for reaction time studies and reliable correlation between signals.</li>
                </ul>
                <p>Lower values ensure tighter synchronization but may result in data loss if streams can't maintain precise timing.</p>
                <p>Higher values are more forgiving but may include misaligned data.</p>
            """,
            "export_formats": """
                <h3>Export Formats</h3>
                <p>Select a format for exporting synchronized data:</p>
                <ul>
                    <li><b>CSV:</b> Simple spreadsheet format. Good for basic analysis and compatibility.
                    Creates separate files for EEG, input, and merged data.</li>
                    <li><b>HDF5:</b> Hierarchical data format. Best for large datasets and preserving
                    structure. Requires h5py package.</li>
                    <li><b>EDF:</b> European Data Format. Standard for clinical EEG. Good for
                    EEG-specific analysis tools. Requires MNE package.</li>
                    <li><b>BIDS:</b> Brain Imaging Data Structure. Best for sharing data and collaborative
                    research. Creates standardized directory structure. Requires MNE and MNE-BIDS packages.</li>
                </ul>
            """,
            "channel_selection": """
                <h3>Channel Selection</h3>
                <p>Select which EEG channels to display in the visualization.</p>
                <p>The available channels depend on your connected EEG device.</p>
                <p>Selecting fewer channels can make the visualization clearer and more focused on regions of interest.</p>
                <p>Use the <b>Select All</b> and <b>Clear All</b> buttons to quickly manage your channel selection.</p>
            """,
        }

        return help_contents.get(
            topic, "<h3>Help</h3><p>No specific help available for this topic.</p>"
        )


class SynchronizedDataVisualization(QWidget):
    """
    Panel for visualizing synchronized EEG and input data.

    This widget displays real-time synchronized data from both EEG and input sources,
    allowing users to see the correlation between brain activity and user actions.
    """

    def __init__(self, integration_service: Any, parent: Optional[QWidget] = None) -> None:
        """Initialize the visualization panel."""
        super().__init__(parent)

        self.integration_service = integration_service

        # Buffer for visualization data
        self.eeg_data_buffer: List[Tuple[List[float], float]] = []
        self.eeg_timestamps: List[float] = []
        self.input_data_buffer: List[Tuple[List[float], float]] = []
        self.input_timestamps: List[float] = []
        self.marker_data: List[Tuple[str, float]] = []
        self.marker_timestamps: List[float] = []

        # Maximum buffer size for visualization
        self.max_buffer_size = 1000

        # EEG channel names (will be updated based on data)
        self.eeg_channel_names: List[str] = []

        # Channel selection (which channels to display)
        self.visible_channels: List[int] = []

        # Scale factor for EEG amplitude
        self.eeg_scale_factor = 1.0

        # Offset between channels (for display clarity)
        self.channel_offset = 100.0

        # Synchronization status
        self.sync_tolerance = 10.0  # Default 10ms
        self.sync_delay = 0.0

        # Create the UI
        self._create_ui()

        # Connect signals
        if hasattr(self.integration_service, "lsl_sync"):
            self.integration_service.lsl_sync.sync_update.connect(
                self.update_visualization_data
            )
            self.integration_service.lsl_sync.sync_tolerance_exceeded.connect(
                self.on_sync_tolerance_exceeded
            )

            # Initialize tolerance value from LSL sync service
            if hasattr(self.integration_service.lsl_sync, "get_sync_tolerance"):
                self.sync_tolerance = (
                    self.integration_service.lsl_sync.get_sync_tolerance()
                )
                self.sync_tolerance_spin.setValue(self.sync_tolerance)

        # Setup timer for visualization updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_plots)
        self.update_timer.start(100)  # Update every 100ms

    def _create_ui(self) -> None:
        """Create the user interface."""
        # Main layout
        layout = QVBoxLayout(self)

        # Title and controls section
        header_layout = QHBoxLayout()
        title_label = QLabel("Synchronized Data Visualization")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # EEG Controls Group
        eeg_controls_group = QGroupBox("EEG Display")
        eeg_controls_layout = QGridLayout()

        # Time window control
        eeg_controls_layout.addWidget(QLabel("Time Window:"), 0, 0)
        self.time_window_spin = QSpinBox()
        self.time_window_spin.setRange(1, 60)
        self.time_window_spin.setValue(10)  # Default 10 seconds
        self.time_window_spin.setSuffix(" sec")
        self.time_window_spin.valueChanged.connect(self.update_plots)
        eeg_controls_layout.addWidget(self.time_window_spin, 0, 1)

        # Scale factor control
        eeg_controls_layout.addWidget(QLabel("Scale:"), 1, 0)
        self.scale_combo = QComboBox()
        scale_options = ["0.1x", "0.25x", "0.5x", "1x", "2x", "5x", "10x"]
        self.scale_combo.addItems(scale_options)
        self.scale_combo.setCurrentText("1x")
        self.scale_combo.currentTextChanged.connect(self.update_scale_factor)
        eeg_controls_layout.addWidget(self.scale_combo, 1, 1)

        # Channel display mode
        eeg_controls_layout.addWidget(QLabel("Channel Mode:"), 2, 0)
        self.channel_mode_combo = QComboBox()
        self.channel_mode_combo.addItems(["Stacked", "Overlaid"])
        self.channel_mode_combo.currentTextChanged.connect(self.update_channel_mode)
        eeg_controls_layout.addWidget(self.channel_mode_combo, 2, 1)

        # View options
        self.show_eeg_check = QCheckBox("Show EEG")
        self.show_eeg_check.setChecked(True)
        self.show_eeg_check.toggled.connect(self.update_plots)
        eeg_controls_layout.addWidget(self.show_eeg_check, 0, 3)

        self.show_input_check = QCheckBox("Show Input")
        self.show_input_check.setChecked(True)
        self.show_input_check.toggled.connect(self.update_plots)
        eeg_controls_layout.addWidget(self.show_input_check, 1, 3)

        self.show_markers_check = QCheckBox("Show Markers")
        self.show_markers_check.setChecked(True)
        self.show_markers_check.toggled.connect(self.update_plots)
        eeg_controls_layout.addWidget(self.show_markers_check, 2, 3)

        # Filter option
        self.filter_noise_check = QCheckBox("Basic Filtering")
        self.filter_noise_check.setChecked(False)
        self.filter_noise_check.toggled.connect(self.update_plots)
        eeg_controls_layout.addWidget(self.filter_noise_check, 0, 4)

        # Add single help button for all EEG display settings
        eeg_help_btn = HelpButton("eeg_display", self)
        eeg_controls_layout.addWidget(eeg_help_btn, 0, 5)

        # Toggle channel selection button
        self.toggle_channel_selection_btn = QPushButton("Channel Selection")
        self.toggle_channel_selection_btn.clicked.connect(
            self.toggle_channel_selection_panel
        )
        eeg_controls_layout.addWidget(self.toggle_channel_selection_btn, 1, 4)

        eeg_controls_group.setLayout(eeg_controls_layout)

        # Add controls group to header layout
        header_layout.addWidget(eeg_controls_group)

        # Sync Controls Group
        sync_controls_group = QGroupBox("Synchronization")
        sync_controls_layout = QGridLayout()

        # Sync tolerance control
        sync_controls_layout.addWidget(QLabel("Tolerance:"), 0, 0)
        self.sync_tolerance_spin = QDoubleSpinBox()
        self.sync_tolerance_spin.setRange(0.1, 1000.0)
        self.sync_tolerance_spin.setValue(self.sync_tolerance)  # Default 10ms
        self.sync_tolerance_spin.setSuffix(" ms")
        self.sync_tolerance_spin.setToolTip(
            "Maximum allowed time offset between EEG and input data"
        )
        self.sync_tolerance_spin.valueChanged.connect(self.update_sync_tolerance)
        sync_controls_layout.addWidget(self.sync_tolerance_spin, 0, 1)

        # Add help button for sync tolerance
        sync_tolerance_help = HelpButton("sync_tolerance", self)
        sync_controls_layout.addWidget(sync_tolerance_help, 0, 2)

        # Dataset format selector
        sync_controls_layout.addWidget(QLabel("Export Format:"), 1, 0)
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["CSV", "HDF5", "EDF", "BIDS"])
        sync_controls_layout.addWidget(self.export_format_combo, 1, 1)

        # Add help button for export formats
        export_format_help = HelpButton("export_formats", self)
        sync_controls_layout.addWidget(export_format_help, 1, 2)

        sync_controls_group.setLayout(sync_controls_layout)
        header_layout.addWidget(sync_controls_group)

        layout.addLayout(header_layout)

        # Create matplotlib figure for plotting
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)

        # Set up the plots
        self.setup_plots()

        # Add canvas to layout
        layout.addWidget(self.canvas)

        # Add legend and status
        bottom_layout = QHBoxLayout()

        # Status indicators
        status_layout = QGridLayout()

        # EEG status
        status_layout.addWidget(QLabel("EEG Status:"), 0, 0)
        self.eeg_status_label = QLabel("No data")
        status_layout.addWidget(self.eeg_status_label, 0, 1)

        # Input status
        status_layout.addWidget(QLabel("Input Status:"), 1, 0)
        self.input_status_label = QLabel("No data")
        status_layout.addWidget(self.input_status_label, 1, 1)

        # Sync status
        status_layout.addWidget(QLabel("Sync Delay:"), 2, 0)
        self.sync_status_label = QLabel("N/A")
        self.sync_status_label.setToolTip(
            "Time difference between EEG and input data streams"
        )
        status_layout.addWidget(self.sync_status_label, 2, 1)

        # Add layouts to bottom layout
        bottom_layout.addLayout(status_layout)
        bottom_layout.addStretch()

        # Legend for markers
        self.marker_legend_frame = QFrame()
        self.marker_legend_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        marker_legend_layout = QVBoxLayout(self.marker_legend_frame)

        marker_title = QLabel("Recent Markers:")
        marker_title.setStyleSheet("font-weight: bold;")
        marker_legend_layout.addWidget(marker_title)

        self.marker_legend_label = QLabel("No markers")
        self.marker_legend_label.setWordWrap(True)
        marker_legend_layout.addWidget(self.marker_legend_label)
        bottom_layout.addWidget(self.marker_legend_frame)

        layout.addLayout(bottom_layout)

        # Setup channel selection group box that appears below the plot
        self.setup_channel_selection()
        layout.addWidget(self.channel_selection_group)
        self.channel_selection_group.setVisible(False)  # Start collapsed

    def toggle_channel_selection_panel(self) -> None:
        """Toggle visibility of the channel selection panel."""
        self.channel_selection_group.setVisible(
            not self.channel_selection_group.isVisible()
        )

        # Update button text
        if self.channel_selection_group.isVisible():
            self.toggle_channel_selection_btn.setText("Hide Channel Selection")
        else:
            self.toggle_channel_selection_btn.setText("Channel Selection")

    def setup_channel_selection(self) -> None:
        """Set up channel selection UI elements."""
        self.channel_selection_group = QGroupBox("Channel Selection")
        self.channel_selection_layout = QGridLayout()
        self.channel_checkboxes: List[QCheckBox] = []

        # Will be populated with checkboxes when channel names are available
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.channel_selection_layout = QGridLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)

        channel_selection_main_layout = QVBoxLayout()

        # Add help button for channel selection
        channel_help_layout = QHBoxLayout()
        channel_help_layout.addWidget(QLabel("Select channels to display:"))

        channel_selection_help = HelpButton("channel_selection", self)
        channel_help_layout.addWidget(channel_selection_help)
        channel_help_layout.addStretch()

        channel_selection_main_layout.addLayout(channel_help_layout)
        channel_selection_main_layout.addWidget(scroll_area)

        # Control buttons
        channel_button_layout = QHBoxLayout()

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_channels)
        channel_button_layout.addWidget(select_all_btn)

        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(self.clear_all_channels)
        channel_button_layout.addWidget(clear_all_btn)

        channel_selection_main_layout.addLayout(channel_button_layout)
        self.channel_selection_group.setLayout(channel_selection_main_layout)

    def select_all_channels(self) -> None:
        """Select all channels."""
        for checkbox in self.channel_checkboxes:
            checkbox.setChecked(True)
        self.update_visible_channels()

    def clear_all_channels(self) -> None:
        """Clear all channel selections."""
        for checkbox in self.channel_checkboxes:
            checkbox.setChecked(False)
        self.update_visible_channels()

    def update_visible_channels(self) -> None:
        """Update which channels are visible based on checkbox selection."""
        self.visible_channels = []
        for i, checkbox in enumerate(self.channel_checkboxes):
            if checkbox.isChecked():
                self.visible_channels.append(i)

        # Make sure we have at least one channel visible
        if not self.visible_channels and self.channel_checkboxes:
            self.channel_checkboxes[0].setChecked(True)
            self.visible_channels.append(0)

        self.update_plots()

    def update_sync_tolerance(self, value: float) -> None:
        """Update the synchronization tolerance value."""
        self.sync_tolerance = value

        # Update LSL sync service if available
        if hasattr(self.integration_service, "lsl_sync") and hasattr(
            self.integration_service.lsl_sync, "set_sync_tolerance"
        ):
            self.integration_service.lsl_sync.set_sync_tolerance(value)

    def on_sync_tolerance_exceeded(self, delay_ms: float) -> None:
        """Handle event when sync tolerance is exceeded."""
        # Update delay value
        self.sync_delay = delay_ms

        # Update status label with warning style
        self.sync_status_label.setText(f"{delay_ms:.2f} ms")
        self.sync_status_label.setStyleSheet(
            "color: #FF5555; font-weight: bold;"
        )  # Red text

        # Show tooltip with detailed info
        QToolTip.showText(
            self.sync_status_label.mapToGlobal(self.sync_status_label.rect().center()),
            f"Synchronization delay ({delay_ms:.2f} ms) exceeds tolerance ({self.sync_tolerance:.2f} ms)",
            self.sync_status_label,
        )

    def setup_plots(self) -> None:
        """Set up the matplotlib plots."""
        # Clear any existing plots
        self.figure.clear()

        # Create subplots
        self.ax1 = self.figure.add_subplot(211)  # EEG plot
        self.ax2 = self.figure.add_subplot(212)  # Input plot

        # Configure EEG plot
        self.ax1.set_title("EEG Data")
        self.ax1.set_xlabel("Time (s)")
        self.ax1.set_ylabel("Amplitude (μV)")
        self.ax1.grid(True)

        # Configure Input plot
        self.ax2.set_title("Input Events")
        self.ax2.set_xlabel("Time (s)")
        self.ax2.set_ylabel("Value")
        self.ax2.grid(True)

        # Initialize empty plots
        self.eeg_lines: List[Any] = []
        self.input_lines: List[Any] = []
        self.marker_lines: List[Any] = []

        # Create initial empty lines
        # These will be replaced when actual data is available
        default_channel_names = ["Ch1", "Ch2", "Ch3", "Ch4", "Ch5", "Ch6", "Ch7", "Ch8"]
        for name in default_channel_names:
            (line,) = self.ax1.plot([], [], label=name)
            self.eeg_lines.append(line)

        # Create initial empty lines for input channels
        input_channel_names = [
            "Timestamp",
            "Event Type",
            "Key Code",
            "Mouse X",
            "Mouse Y",
        ]

        for name in input_channel_names:
            (line,) = self.ax2.plot([], [], label=name)
            self.input_lines.append(line)

        # Create legend with a reasonable number of items
        self.ax1.legend(loc="upper right", ncol=2, fontsize="small")
        self.ax2.legend(loc="upper right", fontsize="small")

        # Adjust layout
        self.figure.tight_layout()

        # Draw the canvas
        self.canvas.draw()

    def update_scale_factor(self, scale_text: str) -> None:
        """Update the EEG amplitude scale factor."""
        scale_map = {
            "0.1x": 0.1,
            "0.25x": 0.25,
            "0.5x": 0.5,
            "1x": 1.0,
            "2x": 2.0,
            "5x": 5.0,
            "10x": 10.0,
        }

        self.eeg_scale_factor = scale_map.get(scale_text, 1.0)
        self.update_plots()

    def update_channel_mode(self, mode_text: str) -> None:
        """Update how channels are displayed."""
        if mode_text == "Stacked":
            self.channel_offset = 100.0
        else:  # "Overlaid"
            self.channel_offset = 0.0

        self.update_plots()

    def update_channel_selection(self, selection: Any) -> None:
        """Update channel selection based on dropdown."""
        # This method now only handles updating visible channels from checkboxes
        self.update_visible_channels()

    def update_visualization_data(self, data: Dict[str, Any]) -> None:
        """
        Update visualization data from LSL streams.

        Args:
            data: Dictionary with synchronized data
        """
        # Update data buffers
        eeg_data = data.get("eeg", [])
        input_data = data.get("input", [])
        markers = data.get("markers", [])

        # Get sync info if available
        sync_info = data.get("sync_info", {})
        if sync_info:
            self.sync_tolerance = sync_info.get("tolerance", self.sync_tolerance)
            self.sync_delay = sync_info.get("delay", self.sync_delay)

        # Process EEG data
        for sample, ts in eeg_data:
            self.eeg_data_buffer.append((sample, ts))

        # Process input data
        for sample, ts in input_data:
            self.input_data_buffer.append((sample, ts))

        # Process markers
        for marker, ts in markers:
            self.marker_data.append((marker, ts))

        # Trim buffers if they exceed max size
        if len(self.eeg_data_buffer) > self.max_buffer_size:
            self.eeg_data_buffer = self.eeg_data_buffer[-self.max_buffer_size :]
        if len(self.input_data_buffer) > self.max_buffer_size:
            self.input_data_buffer = self.input_data_buffer[-self.max_buffer_size :]
        if len(self.marker_data) > self.max_buffer_size:
            self.marker_data = self.marker_data[-self.max_buffer_size :]

        # Update status labels
        if eeg_data:
            self.eeg_status_label.setText(f"Receiving ({len(eeg_data)} samples)")

            # Update EEG channel names if needed
            if self.eeg_data_buffer and not self.eeg_channel_names:
                self._update_eeg_channel_names()

        if input_data:
            self.input_status_label.setText(f"Receiving ({len(input_data)} samples)")

        # Calculate sync delay if both streams have data
        if eeg_data and input_data:
            # Get most recent timestamps
            latest_eeg_ts = eeg_data[-1][1]
            latest_input_ts = input_data[-1][1]

            # Calculate delay in milliseconds
            delay_ms = abs(latest_eeg_ts - latest_input_ts) * 1000
            self.sync_delay = delay_ms

            # Update sync status label
            if delay_ms <= self.sync_tolerance:
                # Within tolerance - good
                self.sync_status_label.setText(f"{delay_ms:.2f} ms")
                self.sync_status_label.setStyleSheet("color: #5FB878;")  # Green text
            else:
                # Outside tolerance - warning
                self.sync_status_label.setText(f"{delay_ms:.2f} ms")
                self.sync_status_label.setStyleSheet(
                    "color: #FF5555; font-weight: bold;"
                )  # Red text

        # Update marker legend
        if markers:
            marker_text = "Recent markers: " + ", ".join(
                f"Marker {m[0]}" for m in markers[-5:]
            )
            self.marker_legend_label.setText(marker_text)

    def _update_eeg_channel_names(self) -> None:
        """Update EEG channel names from multiple possible sources."""
        # First try to directly get channel names from LSL stream info
        if hasattr(self.integration_service, "lsl_sync") and hasattr(
            self.integration_service.lsl_sync, "eeg_inlet"
        ):
            try:
                inlet = self.integration_service.lsl_sync.eeg_inlet
                if inlet:
                    info = inlet.info()
                    ch_info = info.desc().child("channels")

                    if not ch_info.empty():
                        channel_names = []
                        for i in range(ch_info.child_count()):
                            ch = ch_info.child(i)
                            ch_name = ch.child_value("label")
                            if ch_name:
                                channel_names.append(ch_name)

                        if channel_names:
                            self.eeg_channel_names = channel_names
                            self._update_channel_selection_ui()
                            self._update_plot_lines()
                            return
            except Exception as e:
                print(f"Error getting channel names from LSL: {e}")

        # Try to get from EEG collector service
        try:
            collector_service = self.integration_service.eeg_processor.get(
                "collector_service"
            )
            if collector_service and hasattr(collector_service, "collector"):
                collector = collector_service.collector

                # Try different methods to get channel names
                if hasattr(collector, "eeg_names") and collector.eeg_names:
                    # Most direct method - collector already has eeg_names property
                    self.eeg_channel_names = collector.eeg_names
                elif hasattr(collector, "get_device_info"):
                    # Try to get from device info
                    device_info = collector.get_device_info()
                    if "eeg_names" in device_info and device_info["eeg_names"]:
                        self.eeg_channel_names = device_info["eeg_names"]
                elif hasattr(collector, "get_board_info"):
                    # Legacy method - try board info
                    board_info = collector.get_board_info()
                    if "eeg_names" in board_info and board_info["eeg_names"]:
                        self.eeg_channel_names = board_info["eeg_names"]
                elif hasattr(collector_service, "get_board_description"):
                    # Try to get from board description
                    board_desc = collector_service.get_board_description()
                    if "eeg_names" in board_desc and board_desc["eeg_names"]:
                        self.eeg_channel_names = board_desc["eeg_names"]

                # If we found channel names through any method
                if self.eeg_channel_names:
                    self._update_channel_selection_ui()
                    self._update_plot_lines()
                    return
        except Exception as e:
            print(f"Error getting channel names from collector: {e}")

        # If we got here, we haven't been able to find channel names yet

        # Fall back to using data dimensions
        if self.eeg_data_buffer:
            try:
                first_sample = self.eeg_data_buffer[0][0]
                num_channels = len(first_sample)
                self.eeg_channel_names = [f"EEG{i+1}" for i in range(num_channels)]
                self._update_channel_selection_ui()
                self._update_plot_lines()
                return
            except Exception as e:
                print(f"Error getting channel count from data: {e}")

        # Ultimate fallback - if nothing else worked, use default names
        self.eeg_channel_names = [f"Ch{i+1}" for i in range(8)]  # Assume 8 channels
        self._update_channel_selection_ui()
        self._update_plot_lines()

    def _update_channel_selection_ui(self) -> None:
        """Update the channel selection UI based on available data."""
        # Clear existing checkboxes
        for i in reversed(range(self.channel_selection_layout.count())):
            widget = self.channel_selection_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.channel_checkboxes = []

        # Get updated channel selection options based on channel names
        if self.eeg_channel_names:
            # Create channel checkboxes in a grid layout
            # We'll create a 4-column grid
            cols = 4
            for i, name in enumerate(self.eeg_channel_names):
                row, col = divmod(i, cols)
                checkbox = QCheckBox(name)
                checkbox.setChecked(True)  # Default to all checked
                checkbox.toggled.connect(self.update_visible_channels)
                self.channel_checkboxes.append(checkbox)
                self.channel_selection_layout.addWidget(checkbox, row, col)

            # Set all channels as visible initially
            self.visible_channels = list(range(len(self.eeg_channel_names)))

            # Make sure the channel selection group is visible if we have channels
            if (
                not self.channel_selection_group.isVisible()
                and len(self.eeg_channel_names) > 0
            ):
                self.channel_selection_group.setVisible(True)
                self.toggle_channel_selection_btn.setText("Hide Channel Selection")

    def _update_plot_lines(self) -> None:
        """Update plot lines based on current channel names."""
        # Clear the figure and recreate
        self.figure.clear()

        # Create subplots
        self.ax1 = self.figure.add_subplot(211)  # EEG plot
        self.ax2 = self.figure.add_subplot(212)  # Input plot

        # Configure EEG plot
        self.ax1.set_title("EEG Data")
        self.ax1.set_xlabel("Time (s)")
        self.ax1.set_ylabel("Amplitude (μV)")
        self.ax1.grid(True)

        # Configure Input plot
        self.ax2.set_title("Input Events")
        self.ax2.set_xlabel("Time (s)")
        self.ax2.set_ylabel("Value")
        self.ax2.grid(True)

        # Initialize EEG lines
        self.eeg_lines = []
        colors = plt.cm.tab10.colors  # Use a colormap for distinguishing channels

        for i, name in enumerate(self.eeg_channel_names):
            # Use color cycling for channels
            color_idx = i % len(colors)
            (line,) = self.ax1.plot([], [], label=name, color=colors[color_idx])
            self.eeg_lines.append(line)

        # Create lines for input events
        input_channel_names = [
            "Timestamp",
            "Event Type",
            "Key Code",
            "Mouse X",
            "Mouse Y",
        ]
        self.input_lines = []

        for i, name in enumerate(input_channel_names):
            (line,) = self.ax2.plot([], [], label=name)
            self.input_lines.append(line)

        # Create legend with a reasonable number of items
        # If we have many channels, use a reduced legend
        if len(self.eeg_channel_names) > 8:
            # Create a legend with just a subset of channels to avoid overcrowding
            subset_indices = list(
                range(0, len(self.eeg_channel_names), len(self.eeg_channel_names) // 4)
            )
            subset_lines = [
                self.eeg_lines[i] for i in subset_indices if i < len(self.eeg_lines)
            ]
            subset_labels = [
                self.eeg_channel_names[i]
                for i in subset_indices
                if i < len(self.eeg_channel_names)
            ]
            self.ax1.legend(
                subset_lines, subset_labels, loc="upper right", ncol=2, fontsize="small"
            )
        else:
            self.ax1.legend(loc="upper right", ncol=2, fontsize="small")

        self.ax2.legend(loc="upper right", fontsize="small")

        # Adjust layout
        self.figure.tight_layout()

        # Draw the canvas
        self.canvas.draw()

    def apply_simple_filter(self, data: np.ndarray) -> np.ndarray:
        """
        Apply a simple filter to EEG data to remove noise.

        Args:
            data: EEG data array

        Returns:
            Filtered data
        """
        # Simple moving average filter
        window_size = 5
        if len(data) < window_size:
            return data

        filtered_data = np.zeros_like(data)
        for i in range(len(data)):
            start_idx = max(0, i - window_size // 2)
            end_idx = min(len(data), i + window_size // 2 + 1)
            filtered_data[i] = np.mean(data[start_idx:end_idx])

        return filtered_data

    def update_plots(self) -> None:
        """Update the plots with current data."""
        # Skip if no data
        if not self.eeg_data_buffer and not self.input_data_buffer:
            return

        # Get time window in seconds
        time_window = self.time_window_spin.value()

        # Get the most recent timestamp
        latest_ts = max(
            self.eeg_data_buffer[-1][1] if self.eeg_data_buffer else 0,
            self.input_data_buffer[-1][1] if self.input_data_buffer else 0,
        )

        # Calculate the start timestamp based on time window
        start_ts = latest_ts - time_window

        # Filter data within the time window
        eeg_data_filtered = [
            (d, ts) for d, ts in self.eeg_data_buffer if ts >= start_ts
        ]
        input_data_filtered = [
            (d, ts) for d, ts in self.input_data_buffer if ts >= start_ts
        ]
        markers_filtered = [(m, ts) for m, ts in self.marker_data if ts >= start_ts]

        # Update EEG plot if enabled and we have data
        if self.show_eeg_check.isChecked() and eeg_data_filtered and self.eeg_lines:
            # Extract timestamps and normalize to seconds from start
            timestamps = [ts - start_ts for _, ts in eeg_data_filtered]

            # Extract channel data - transpose the data matrix
            channels_data = []
            for ch_idx in range(len(self.eeg_channel_names)):
                try:
                    ch_data = [sample[ch_idx] for sample, _ in eeg_data_filtered]
                    channels_data.append(ch_data)
                except IndexError:
                    # Handle case where sample doesn't have enough channels
                    channels_data.append([0] * len(timestamps))

            # Apply filtering if enabled
            if self.filter_noise_check.isChecked():
                channels_data = [
                    self.apply_simple_filter(ch_data) for ch_data in channels_data
                ]

            # Update each visible EEG channel line
            visible_channels = (
                self.visible_channels
                if self.visible_channels
                else range(len(self.eeg_lines))
            )

            # Clear axis if we're redrawing
            self.ax1.cla()
            self.ax1.set_title("EEG Data")
            self.ax1.set_xlabel("Time (s)")
            self.ax1.set_ylabel("Amplitude (μV)")
            self.ax1.grid(True)

            # Draw new lines for each visible channel
            colors = plt.cm.tab10.colors
            lines = []
            labels = []

            for i in visible_channels:
                if i < len(channels_data) and len(channels_data[i]) > 0:
                    # Scale the data and apply offset
                    offset = i * self.channel_offset
                    # Use the scale factor to multiply the amplitude
                    scaled_data = [
                        val * self.eeg_scale_factor + offset for val in channels_data[i]
                    ]

                    # Plot the channel
                    color_idx = i % len(colors)
                    (line,) = self.ax1.plot(
                        timestamps,
                        scaled_data,
                        label=self.eeg_channel_names[i],
                        color=colors[color_idx],
                    )

                    lines.append(line)
                    labels.append(self.eeg_channel_names[i])

            # Update EEG plot limits
            self.ax1.set_xlim(0, time_window)

            # Set y-axis limits based on visible channels and mode
            if self.channel_offset > 0:  # Stacked mode
                max_channels = len(visible_channels)
                self.ax1.set_ylim(-50, self.channel_offset * max_channels + 50)
            else:  # Overlaid mode
                # Find max and min of visible channels
                if channels_data and any(len(ch) > 0 for ch in channels_data):
                    all_values = []
                    for i in visible_channels:
                        if i < len(channels_data) and channels_data[i]:
                            all_values.extend(
                                [
                                    val * self.eeg_scale_factor
                                    for val in channels_data[i]
                                ]
                            )

                    if all_values:
                        margin = (max(all_values) - min(all_values)) * 0.1  # 10% margin
                        self.ax1.set_ylim(
                            min(all_values) - margin, max(all_values) + margin
                        )

            # Create a proper legend using visible channels
            if len(lines) > 8:
                # For many channels, create a reduced legend
                subset_indices = list(range(0, len(lines), max(1, len(lines) // 4)))
                subset_lines = [lines[i] for i in subset_indices if i < len(lines)]
                subset_labels = [labels[i] for i in subset_indices if i < len(labels)]
                self.ax1.legend(
                    subset_lines,
                    subset_labels,
                    loc="upper right",
                    ncol=2,
                    fontsize="small",
                )
            else:
                # For fewer channels, show all in legend
                self.ax1.legend(
                    lines, labels, loc="upper right", ncol=2, fontsize="small"
                )

        # Update input plot if enabled
        if self.show_input_check.isChecked() and input_data_filtered:
            # Extract timestamps and normalize to seconds from start
            timestamps = [ts - start_ts for _, ts in input_data_filtered]

            # Extract relevant input channels: event type, key code, mouse x, mouse y
            input_data_arrays: List[List[float]] = [[], [], [], [], []]

            for sample, _ in input_data_filtered:
                # Extract data for the first 5 channels (timestamp, event, key, x, y)
                for i in range(5):
                    if i < len(sample):
                        input_data_arrays[i].append(sample[i])
                    else:
                        input_data_arrays[i].append(0)

            # Clear axis
            self.ax2.cla()
            self.ax2.set_title("Input Events")
            self.ax2.set_xlabel("Time (s)")
            self.ax2.set_ylabel("Value")
            self.ax2.grid(True)

            # Draw new lines for input data
            input_labels = ["Timestamp", "Event Type", "Key Code", "Mouse X", "Mouse Y"]
            colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

            # Only plot meaningful channels (Event Type, Key, X, Y)
            for i in range(1, min(5, len(input_data_arrays))):
                if i < len(input_data_arrays) and len(input_data_arrays[i]) == len(
                    timestamps
                ):
                    self.ax2.plot(
                        timestamps,
                        input_data_arrays[i],
                        label=input_labels[i],
                        color=colors[i % len(colors)],
                    )

            # Set x-axis limits
            self.ax2.set_xlim(0, time_window)

            # Add legend
            self.ax2.legend(loc="upper right", fontsize="small")

        # Add markers if enabled
        if self.show_markers_check.isChecked() and markers_filtered:
            # Remove any existing marker annotations
            for line in getattr(self, "marker_lines", []):
                if isinstance(line, plt.Line2D) and line in self.ax1.lines:
                    self.ax1.lines.remove(line)
                elif hasattr(line, "remove"):
                    line.remove()

            self.marker_lines = []

            # Add markers to both plots if they have axes
            if hasattr(self, "ax1") and hasattr(self, "ax2"):
                for marker, ts in markers_filtered:
                    # Normalize timestamp
                    norm_ts = ts - start_ts

                    # Add marker to EEG plot
                    line1 = self.ax1.axvline(
                        x=norm_ts, color="r", linestyle="--", alpha=0.7, linewidth=1
                    )

                    # Add marker to input plot
                    line2 = self.ax2.axvline(
                        x=norm_ts, color="r", linestyle="--", alpha=0.7, linewidth=1
                    )

                    # Add text label on EEG plot
                    ymin, ymax = self.ax1.get_ylim()
                    text = self.ax1.text(
                        norm_ts,
                        ymax - (ymax - ymin) * 0.05,
                        f"M{marker}",
                        color="r",
                        fontsize=8,
                        ha="center",
                        bbox=dict(
                            facecolor="white", alpha=0.7, boxstyle="round,pad=0.2"
                        ),
                    )

                    # Store the lines for later removal
                    self.marker_lines.extend([line1, line2, text])

        # Redraw the canvas
        self.figure.tight_layout()
        self.canvas.draw()

    def closeEvent(self, event: Any) -> None:
        """Handle close event."""
        # Stop the update timer
        self.update_timer.stop()
        event.accept()
