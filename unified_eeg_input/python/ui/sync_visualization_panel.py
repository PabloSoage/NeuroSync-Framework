"""
Synchronized data visualization panel.

This module provides a UI component for visualizing synchronized EEG and input data.
"""

import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QSpinBox,
    QCheckBox, QSlider, QSplitter, QGridLayout,
    QScrollArea, QFrame, QDoubleSpinBox, QToolTip
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

class SynchronizedDataVisualization(QWidget):
    """
    Panel for visualizing synchronized EEG and input data.
    
    This widget displays real-time synchronized data from both EEG and input sources,
    allowing users to see the correlation between brain activity and user actions.
    """
    
    def __init__(self, integration_service, parent=None):
        """Initialize the visualization panel."""
        super().__init__(parent)
        
        self.integration_service = integration_service
        
        # Buffer for visualization data
        self.eeg_data_buffer = []
        self.eeg_timestamps = []
        self.input_data_buffer = []
        self.input_timestamps = []
        self.marker_data = []
        self.marker_timestamps = []
        
        # Maximum buffer size for visualization
        self.max_buffer_size = 1000
        
        # EEG channel names (will be updated based on data)
        self.eeg_channel_names = []
        
        # Channel selection (which channels to display)
        self.visible_channels = []
        
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
        if hasattr(self.integration_service, 'lsl_sync'):
            self.integration_service.lsl_sync.sync_update.connect(self.update_visualization_data)
            self.integration_service.lsl_sync.sync_tolerance_exceeded.connect(self.on_sync_tolerance_exceeded)
            
            # Initialize tolerance value from LSL sync service
            if hasattr(self.integration_service.lsl_sync, 'get_sync_tolerance'):
                self.sync_tolerance = self.integration_service.lsl_sync.get_sync_tolerance()
                self.sync_tolerance_spin.setValue(self.sync_tolerance)
        
        # Setup timer for visualization updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_plots)
        self.update_timer.start(100)  # Update every 100ms
    
    def _create_ui(self):
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
        
        # Channel selection dropdown (will be populated later)
        eeg_controls_layout.addWidget(QLabel("Channels:"), 0, 2)
        self.channel_select_combo = QComboBox()
        self.channel_select_combo.addItem("All Channels")
        self.channel_select_combo.addItem("Frontal")
        self.channel_select_combo.addItem("Central")
        self.channel_select_combo.addItem("Parietal")
        self.channel_select_combo.addItem("Occipital")
        self.channel_select_combo.currentTextChanged.connect(self.update_channel_selection)
        eeg_controls_layout.addWidget(self.channel_select_combo, 0, 3)
        
        # View options
        self.show_eeg_check = QCheckBox("Show EEG")
        self.show_eeg_check.setChecked(True)
        self.show_eeg_check.toggled.connect(self.update_plots)
        eeg_controls_layout.addWidget(self.show_eeg_check, 1, 2)
        
        self.show_input_check = QCheckBox("Show Input")
        self.show_input_check.setChecked(True)
        self.show_input_check.toggled.connect(self.update_plots)
        eeg_controls_layout.addWidget(self.show_input_check, 1, 3)
        
        self.show_markers_check = QCheckBox("Show Markers")
        self.show_markers_check.setChecked(True)
        self.show_markers_check.toggled.connect(self.update_plots)
        eeg_controls_layout.addWidget(self.show_markers_check, 2, 2)
        
        # Filter option
        self.filter_noise_check = QCheckBox("Basic Filtering")
        self.filter_noise_check.setChecked(False)
        self.filter_noise_check.toggled.connect(self.update_plots)
        eeg_controls_layout.addWidget(self.filter_noise_check, 2, 3)
        
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
        self.sync_tolerance_spin.setToolTip("Maximum allowed time offset between EEG and input data")
        self.sync_tolerance_spin.valueChanged.connect(self.update_sync_tolerance)
        sync_controls_layout.addWidget(self.sync_tolerance_spin, 0, 1)
        
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
        self.sync_status_label.setToolTip("Time difference between EEG and input data streams")
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
    
    def update_sync_tolerance(self, value):
        """Update the synchronization tolerance value."""
        self.sync_tolerance = value
        
        # Update LSL sync service if available
        if hasattr(self.integration_service, 'lsl_sync') and hasattr(self.integration_service.lsl_sync, 'set_sync_tolerance'):
            self.integration_service.lsl_sync.set_sync_tolerance(value)
    
    def on_sync_tolerance_exceeded(self, delay_ms):
        """Handle event when sync tolerance is exceeded."""
        # Update delay value
        self.sync_delay = delay_ms
        
        # Update status label with warning style
        self.sync_status_label.setText(f"{delay_ms:.2f} ms")
        self.sync_status_label.setStyleSheet("color: #FF5555; font-weight: bold;")  # Red text
        
        # Show tooltip with detailed info
        QToolTip.showText(
            self.sync_status_label.mapToGlobal(self.sync_status_label.rect().center()),
            f"Synchronization delay ({delay_ms:.2f} ms) exceeds tolerance ({self.sync_tolerance:.2f} ms)",
            self.sync_status_label
        )

    def setup_channel_selection(self):
        """Set up channel selection UI elements."""
        self.channel_selection_group = QGroupBox("Channel Selection")
        self.channel_selection_layout = QGridLayout()
        self.channel_checkboxes = []
        
        # Will be populated with checkboxes when channel names are available
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.channel_selection_layout = QGridLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)
        
        channel_selection_main_layout = QVBoxLayout()
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
        
        # Start collapsed
        self.channel_selection_group.setVisible(False)
    
    def select_all_channels(self):
        """Select all channels."""
        for checkbox in self.channel_checkboxes:
            checkbox.setChecked(True)
        self.update_visible_channels()
    
    def clear_all_channels(self):
        """Clear all channel selections."""
        for checkbox in self.channel_checkboxes:
            checkbox.setChecked(False)
        self.update_visible_channels()
    
    def update_visible_channels(self):
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
    
    def setup_plots(self):
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
        self.eeg_lines = []
        self.input_lines = []
        self.marker_lines = []
        
        # Create initial empty lines for EEG channels (8 by default)
        # The actual number will be updated when data is received
        for i in range(8):
            line, = self.ax1.plot([], [], label=f"Ch{i+1}")
            self.eeg_lines.append(line)
        
        # Create initial empty lines for input channels
        input_channel_names = ["Timestamp", "Event Type", "Key Code", "Mouse X", "Mouse Y"]
        self.input_lines = []
        
        for i, name in enumerate(input_channel_names):
            line, = self.ax2.plot([], [], label=name)
            self.input_lines.append(line)
        
        # Create legend with a reasonable number of items (prevent overcrowding)
        self.ax1.legend(loc='upper right', ncol=2, fontsize='small')
        self.ax2.legend(loc='upper right', fontsize='small')
        
        # Adjust layout
        self.figure.tight_layout()
        
        # Draw the canvas
        self.canvas.draw()
    
    def update_scale_factor(self, scale_text):
        """Update the EEG amplitude scale factor."""
        scale_map = {
            "0.1x": 0.1,
            "0.25x": 0.25,
            "0.5x": 0.5,
            "1x": 1.0,
            "2x": 2.0,
            "5x": 5.0,
            "10x": 10.0
        }
        
        self.eeg_scale_factor = scale_map.get(scale_text, 1.0)
        self.update_plots()
    
    def update_channel_mode(self, mode_text):
        """Update how channels are displayed."""
        if mode_text == "Stacked":
            self.channel_offset = 100.0
        else:  # "Overlaid"
            self.channel_offset = 0.0
        
        self.update_plots()
    
    def update_channel_selection(self, selection):
        """Update channel selection based on dropdown."""
        if selection == "All Channels":
            # Show all channel checkboxes
            self.channel_selection_group.setVisible(True)
        elif selection == "Frontal" and self.eeg_channel_names:
            # Select frontal channels (Fp1, Fp2, F3, F4, F7, F8, Fz)
            frontal_patterns = ["fp1", "fp2", "f3", "f4", "f7", "f8", "fz"]
            self._select_channels_by_pattern(frontal_patterns)
        elif selection == "Central" and self.eeg_channel_names:
            # Select central channels (C3, C4, Cz, T3, T4)
            central_patterns = ["c3", "c4", "cz", "t3", "t4"]
            self._select_channels_by_pattern(central_patterns)
        elif selection == "Parietal" and self.eeg_channel_names:
            # Select parietal channels (P3, P4, Pz)
            parietal_patterns = ["p3", "p4", "pz"]
            self._select_channels_by_pattern(parietal_patterns)
        elif selection == "Occipital" and self.eeg_channel_names:
            # Select occipital channels (O1, O2)
            occipital_patterns = ["o1", "o2"]
            self._select_channels_by_pattern(occipital_patterns)
        
        self.update_visible_channels()
    
    def _select_channels_by_pattern(self, patterns):
        """Select channels that match given patterns."""
        for i, name in enumerate(self.eeg_channel_names):
            name_lower = name.lower()
            checkbox = self.channel_checkboxes[i]
            checkbox.setChecked(any(pattern in name_lower for pattern in patterns))
    
    def _update_channel_selection_ui(self):
        """Update the channel selection UI based on available data."""
        # Clear existing checkboxes
        for i in reversed(range(self.channel_selection_layout.count())): 
            self.channel_selection_layout.itemAt(i).widget().setParent(None)
        
        self.channel_checkboxes = []
        
        # Get updated channel selection options based on channel names
        if self.eeg_channel_names:
            # Add standard groupings based on 10-20 system
            self.channel_select_combo.clear()
            self.channel_select_combo.addItem("All Channels")
            self.channel_select_combo.addItem("Frontal")
            self.channel_select_combo.addItem("Central")
            self.channel_select_combo.addItem("Parietal")
            self.channel_select_combo.addItem("Occipital")
            
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
    
    def update_visualization_data(self, data):
        """
        Update visualization data from LSL streams.
        
        Args:
            data: Dictionary with synchronized data
        """
        # Update data buffers
        eeg_data = data.get('eeg', [])
        input_data = data.get('input', [])
        markers = data.get('markers', [])
        
        # Get sync info if available
        sync_info = data.get('sync_info', {})
        if sync_info:
            self.sync_tolerance = sync_info.get('tolerance', self.sync_tolerance)
            self.sync_delay = sync_info.get('delay', self.sync_delay)
        
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
            self.eeg_data_buffer = self.eeg_data_buffer[-self.max_buffer_size:]
        if len(self.input_data_buffer) > self.max_buffer_size:
            self.input_data_buffer = self.input_data_buffer[-self.max_buffer_size:]
        if len(self.marker_data) > self.max_buffer_size:
            self.marker_data = self.marker_data[-self.max_buffer_size:]
        
        # Update status labels
        if eeg_data:
            self.eeg_status_label.setText(f"Receiving ({len(eeg_data)} samples)")
            
            # Update EEG channel names if needed
            if self.eeg_data_buffer and not self.eeg_channel_names:
                # Get the first sample to determine channel count
                first_sample = self.eeg_data_buffer[0][0]
                num_channels = len(first_sample)
                
                # Try to get channel names from LSL stream info
                try:
                    # Get EEG inlet info from LSL sync service
                    if hasattr(self.integration_service.lsl_sync, 'eeg_inlet'):
                        inlet = self.integration_service.lsl_sync.eeg_inlet
                        if inlet:
                            info = inlet.info()
                            ch_info = info.desc().child("channels")
                            
                            if ch_info.empty():
                                # No channel info, use default names
                                self.eeg_channel_names = [f"EEG{i+1}" for i in range(num_channels)]
                            else:
                                # Extract channel names from info
                                self.eeg_channel_names = []
                                for i in range(ch_info.children_count()):
                                    ch = ch_info.child(i)
                                    ch_name = ch.child_value("label")
                                    if ch_name:
                                        self.eeg_channel_names.append(ch_name)
                                    else:
                                        self.eeg_channel_names.append(f"EEG{i+1}")
                        else:
                            # No inlet, use default names
                            self.eeg_channel_names = [f"EEG{i+1}" for i in range(num_channels)]
                    else:
                        # No inlet in LSL sync service, use default names
                        self.eeg_channel_names = [f"EEG{i+1}" for i in range(num_channels)]
                    
                except Exception as e:
                    # If anything goes wrong, fall back to default names
                    print(f"Error getting channel names: {e}")
                    self.eeg_channel_names = [f"EEG{i+1}" for i in range(num_channels)]
                
                # Update the channel selection UI
                self._update_channel_selection_ui()
                
                # Update plot lines for the correct number of channels
                self._update_plot_lines()
        
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
                self.sync_status_label.setStyleSheet("color: #FF5555; font-weight: bold;")  # Red text
        
        # Update marker legend
        if markers:
            marker_text = "Recent markers: " + ", ".join(f"Marker {m[0]}" for m in markers[-5:])
            self.marker_legend_label.setText(marker_text)
    
    def _update_plot_lines(self):
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
            line, = self.ax1.plot([], [], label=name, color=colors[color_idx])
            self.eeg_lines.append(line)
        
        # Create lines for input events
        input_channel_names = ["Timestamp", "Event Type", "Key Code", "Mouse X", "Mouse Y"]
        self.input_lines = []
        
        for i, name in enumerate(input_channel_names):
            line, = self.ax2.plot([], [], label=name)
            self.input_lines.append(line)
        
        # Create legend with a reasonable number of items
        # If we have many channels, use a reduced legend
        if len(self.eeg_channel_names) > 8:
            # Create a legend with just a subset of channels to avoid overcrowding
            subset_indices = list(range(0, len(self.eeg_channel_names), len(self.eeg_channel_names) // 4))
            subset_lines = [self.eeg_lines[i] for i in subset_indices]
            self.ax1.legend(handles=subset_lines, loc='upper right', ncol=2, fontsize='small')
        else:
            self.ax1.legend(loc='upper right', ncol=2, fontsize='small')
        
        self.ax2.legend(loc='upper right', fontsize='small')
        
        # Adjust layout
        self.figure.tight_layout()
        
        # Draw the canvas
        self.canvas.draw()
    
    def apply_simple_filter(self, data):
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
    
    def update_plots(self):
        """Update the plots with current data."""
        # Skip if no data
        if not self.eeg_data_buffer and not self.input_data_buffer:
            return
        
        # Get time window in seconds
        time_window = self.time_window_spin.value()
        
        # Get the most recent timestamp
        latest_ts = max(
            self.eeg_data_buffer[-1][1] if self.eeg_data_buffer else 0,
            self.input_data_buffer[-1][1] if self.input_data_buffer else 0
        )
        
        # Calculate the start timestamp based on time window
        start_ts = latest_ts - time_window
        
        # Filter data within the time window
        eeg_data_filtered = [(d, ts) for d, ts in self.eeg_data_buffer if ts >= start_ts]
        input_data_filtered = [(d, ts) for d, ts in self.input_data_buffer if ts >= start_ts]
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
                channels_data = [self.apply_simple_filter(ch_data) for ch_data in channels_data]
            
            # Update each visible EEG channel line
            visible_channels = self.visible_channels if self.visible_channels else range(len(self.eeg_lines))
            
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
                if i < len(channels_data):
                    # Scale the data and apply offset
                    offset = i * self.channel_offset
                    # Use the scale factor to multiply the amplitude
                    scaled_data = [val * self.eeg_scale_factor + offset for val in channels_data[i]]
                    
                    # Plot the channel
                    color_idx = i % len(colors)
                    line, = self.ax1.plot(timestamps, scaled_data, 
                                         label=self.eeg_channel_names[i], 
                                         color=colors[color_idx])
                    
                    lines.append(line)
                    labels.append(self.eeg_channel_names[i])
            
            # Update EEG plot limits
            self.ax1.set_xlim(0, time_window)
            
            # Set y-axis limits based on visible channels and mode
            if self.channel_offset > 0:  # Stacked mode
                max_channels = len(visible_channels)
                self.ax1.set_ylim(-50, self.channel_offset * max_channels + 50)
            else:  # Overlaid mode
                max_val = max([max(ch_data) * self.eeg_scale_factor for ch_data in channels_data]) + 20
                min_val = min([min(ch_data) * self.eeg_scale_factor for ch_data in channels_data]) - 20
                self.ax1.set_ylim(min_val, max_val)
            
            # Create a proper legend
            if len(lines) > 8:
                # For many channels, create a reduced legend
                subset_lines = lines[::len(lines)//4]
                subset_labels = labels[::len(labels)//4]
                self.ax1.legend(subset_lines, subset_labels, loc='upper right', 
                               ncol=2, fontsize='small')
            else:
                # For fewer channels, show all in legend
                self.ax1.legend(lines, labels, loc='upper right', ncol=2, fontsize='small')
        
        # Update input plot if enabled
        if self.show_input_check.isChecked() and input_data_filtered:
            # Extract timestamps and normalize to seconds from start
            timestamps = [ts - start_ts for _, ts in input_data_filtered]
            
            # Extract relevant input channels: event type, key code, mouse x, mouse y
            input_data_arrays = [[], [], [], [], []]
            
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
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            
            # Only plot meaningful channels (Event Type, Key, X, Y)
            for i in range(1, min(5, len(input_data_arrays))):
                if i < len(input_data_arrays) and len(input_data_arrays[i]) == len(timestamps):
                    self.ax2.plot(timestamps, input_data_arrays[i], 
                                 label=input_labels[i], 
                                 color=colors[i % len(colors)])
            
            # Set x-axis limits
            self.ax2.set_xlim(0, time_window)
            
            # Add legend
            self.ax2.legend(loc='upper right', fontsize='small')
        
        # Add markers if enabled
        if self.show_markers_check.isChecked() and markers_filtered:
            # Remove any existing marker annotations
            for line in getattr(self, 'marker_lines', []):
                if isinstance(line, plt.Line2D) and line in self.ax1.lines:
                    self.ax1.lines.remove(line)
                elif hasattr(line, 'remove'):
                    line.remove()
            
            self.marker_lines = []
            
            # Add markers to both plots if they have axes
            if hasattr(self, 'ax1') and hasattr(self, 'ax2'):
                for marker, ts in markers_filtered:
                    # Normalize timestamp
                    norm_ts = ts - start_ts
                    
                    # Add marker to EEG plot
                    line1 = self.ax1.axvline(x=norm_ts, color='r', linestyle='--', alpha=0.7, linewidth=1)
                    
                    # Add marker to input plot
                    line2 = self.ax2.axvline(x=norm_ts, color='r', linestyle='--', alpha=0.7, linewidth=1)
                    
                    # Add text label on EEG plot
                    ymin, ymax = self.ax1.get_ylim()
                    text = self.ax1.text(norm_ts, ymax - (ymax-ymin)*0.05, f"M{marker}", 
                                        color='r', fontsize=8, ha='center', 
                                        bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.2'))
                    
                    # Store the lines for later removal
                    self.marker_lines.extend([line1, line2, text])
        
        # Redraw the canvas
        self.figure.tight_layout()
        self.canvas.draw()
    
    def closeEvent(self, event):
        """Handle close event."""
        # Stop the update timer
        self.update_timer.stop()
        event.accept()
