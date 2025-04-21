from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, 
    QLabel, QPushButton, QComboBox,
    QCheckBox, QDoubleSpinBox
)
from PyQt5.QtCore import QTimer

from .base_panel import BasePanel
from ..utils.help_system import HelpButton

class ProcessingPanel(BasePanel):
    """Panel for signal processing operations."""
    
    def __init__(self, collector_service, processor_service, visualization_service, parent=None):
        """Initialize the processing panel."""
        super().__init__(parent)
        self.collector_service = collector_service
        self.processor_service = processor_service
        self.visualization_service = visualization_service
        
        # Setup UI components
        self.setup_filter_options()
        self.setup_metrics_section()
        self.setup_brain_map_section()
        
        # Add stretch to push everything to the top
        self.layout.addStretch()
    
    def setup_filter_options(self):
        """Set up filtering options group."""
        filter_group = QGroupBox("Filtering Options")
        filter_layout = QVBoxLayout(filter_group)
        
        # Bandpass filter
        bandpass_layout = QHBoxLayout()
        self.bandpass_check = QCheckBox("Bandpass Filter")
        self.bandpass_check.setChecked(True)
        
        bandpass_low_label = QLabel("Low Cut:")
        self.bandpass_low_spin = QDoubleSpinBox()
        self.bandpass_low_spin.setRange(0.1, 100.0)
        self.bandpass_low_spin.setValue(1.0)
        self.bandpass_low_spin.setSuffix(" Hz")

        bandpass_high_label = QLabel("High Cut:")
        self.bandpass_high_spin = QDoubleSpinBox()
        self.bandpass_high_spin.setRange(0.1, 200.0)
        self.bandpass_high_spin.setValue(50.0)
        self.bandpass_high_spin.setSuffix(" Hz")

        bandpass_layout.addWidget(self.bandpass_check)
        bandpass_layout.addWidget(bandpass_low_label)
        bandpass_layout.addWidget(self.bandpass_low_spin)
        bandpass_layout.addWidget(bandpass_high_label)
        bandpass_layout.addWidget(self.bandpass_high_spin)
        bandpass_layout.addWidget(HelpButton("bandpass_filter", self))
        filter_layout.addLayout(bandpass_layout)

        # Notch filter
        notch_layout = QHBoxLayout()
        self.notch_check = QCheckBox("Notch Filter")
        self.notch_check.setChecked(True)

        notch_type_label = QLabel("Type:")
        self.notch_type_combo = QComboBox()
        self.notch_type_combo.addItem("50 Hz", "50")
        self.notch_type_combo.addItem("60 Hz", "60")

        notch_layout.addWidget(self.notch_check)
        notch_layout.addWidget(notch_type_label)
        notch_layout.addWidget(self.notch_type_combo)
        notch_layout.addWidget(HelpButton("notch_filter", self))
        filter_layout.addLayout(notch_layout)

        # Detrend
        detrend_layout = QHBoxLayout()
        self.detrend_check = QCheckBox("Detrend")
        self.detrend_check.setChecked(True)
        detrend_layout.addWidget(self.detrend_check)
        detrend_layout.addWidget(HelpButton("detrend", self))
        filter_layout.addLayout(detrend_layout)

        # Apply filter button
        apply_layout = QHBoxLayout()
        self.apply_filters_btn = QPushButton("Apply Filters to Visualization")
        self.apply_filters_btn.clicked.connect(self.apply_filters)
        self.apply_filters_btn.setEnabled(False)
        apply_layout.addWidget(self.apply_filters_btn)
        filter_layout.addLayout(apply_layout)
        
        self.layout.addWidget(filter_group)
    
    def setup_metrics_section(self):
        """Set up EEG metrics section."""
        metrics_group = QGroupBox("EEG Metrics")
        metrics_layout = QVBoxLayout(metrics_group)

        # Add help for metrics
        metrics_header_layout = QHBoxLayout()
        metrics_header_layout.addWidget(QLabel("EEG Metrics Analysis"))
        metrics_header_layout.addWidget(HelpButton("eeg_basics", self))
        metrics_header_layout.addStretch()
        metrics_layout.addLayout(metrics_header_layout)

        # Add calculate button
        metrics_update_layout = QHBoxLayout()
        self.calculate_metrics_btn = QPushButton("Calculate Metrics")
        self.calculate_metrics_btn.clicked.connect(self.calculate_metrics)
        self.calculate_metrics_btn.setEnabled(False)
        metrics_update_layout.addWidget(self.calculate_metrics_btn)
        metrics_layout.addLayout(metrics_update_layout)

        # Metrics display
        self.metrics_label = QLabel("No metrics calculated")
        metrics_layout.addWidget(self.metrics_label)
        
        self.layout.addWidget(metrics_group)
    
    def setup_brain_map_section(self):
        """Set up brain map visualization section."""
        # Add brain map button
        brain_map_layout = QHBoxLayout()
        self.brain_map_btn = QPushButton("Show Brain Map Visualization")
        self.brain_map_btn.clicked.connect(self.show_brain_map)
        self.brain_map_btn.setEnabled(False)
        brain_map_layout.addWidget(self.brain_map_btn)
        brain_map_layout.addWidget(HelpButton("brain_map", self))
        
        self.layout.addLayout(brain_map_layout)
        
        # Setup timer to check brain map status
        self.brain_map_timer = QTimer(self)
        self.brain_map_timer.timeout.connect(self.check_brain_map_status)
        self.brain_map_timer.start(1000)  # Check every second

    def check_brain_map_status(self):
        """Check if brain map visualizer needs to be restarted."""
        # Only enable the button when streaming and brain map was closed
        if hasattr(self.visualization_service, 'brain_map_closed') and self.visualization_service.brain_map_closed():
            self.brain_map_btn.setText("Reopen Brain Map Visualization")
            self.brain_map_btn.setEnabled(True)
        elif not self.visualization_service.brain_map_visible() and hasattr(self, 'processing_enabled') and self.processing_enabled:
            # Processing is enabled but brain map is not visible and wasn't explicitly closed
            self.brain_map_btn.setText("Show Brain Map Visualization")
            self.brain_map_btn.setEnabled(True)
    
    def apply_filters(self):
        """Apply the selected filters to visualization."""
        try:
            self.visualization_service.set_bandpass_filter(
                self.bandpass_check.isChecked(),
                self.bandpass_low_spin.value(),
                self.bandpass_high_spin.value()
            )
            
            self.visualization_service.set_notch_filter(
                self.notch_check.isChecked(),
                float(self.notch_type_combo.currentData())
            )
            
            self.visualization_service.set_detrend(self.detrend_check.isChecked())
            
            self.show_status("Filters applied to visualization")
        except Exception as e:
            self.show_error("Filter Error", f"Error applying filters: {str(e)}")
    
    def calculate_metrics(self):
        """Calculate EEG metrics from current data."""
        try:
            # Get data from collector service
            sampling_rate = self.collector_service.get_sampling_rate()
            if sampling_rate <= 0:
                self.show_error("Metrics Error", "Invalid sampling rate")
                return
                
            # Make sure processor is initialized
            if not hasattr(self.processor_service, 'processor') or self.processor_service.processor is None:
                self.processor_service.initialize_processor(sampling_rate)
                self.show_status("Initialized processor with sampling rate " + str(sampling_rate))
                
            # Get 4 seconds of data if available
            data, _ = self.collector_service.get_board_data(4 * sampling_rate)
            if data.size == 0:
                self.show_error("Metrics Error", "No data available")
                return
                
            # Get EEG channels
            eeg_channels = self.collector_service.get_eeg_channels()
            if not eeg_channels:
                self.show_error("Metrics Error", "No EEG channels available")
                return
                
            # Calculate metrics
            metrics = self.processor_service.get_eeg_metrics(data, eeg_channels)
            
            # Format and display metrics
            metrics_text = ""
            for name, value in metrics.items():
                # Handle numpy arrays by taking first value
                if hasattr(value, '__iter__'):
                    value = value[0]
                metrics_text += f"{name.capitalize()}: {value:.2f}\n"
                
            self.metrics_label.setText(metrics_text)
            self.show_status("EEG metrics calculated")
        except Exception as e:
            self.show_error("Metrics Error", f"Failed to calculate metrics: {str(e)}")
    
    def show_brain_map(self):
        """Show brain map visualization."""
        try:
            # Make sure processor is initialized before creating brain map
            sampling_rate = self.collector_service.get_sampling_rate()
            if sampling_rate <= 0:
                self.show_error("Visualization Error", "Invalid sampling rate")
                return
                
            # Initialize processor if not already done
            if not hasattr(self.processor_service, 'processor') or self.processor_service.processor is None:
                self.processor_service.initialize_processor(sampling_rate)
                self.show_status(f"Initialized processor with sampling rate {sampling_rate} Hz")
            
            # Now create brain map visualizer with initialized processor
            success = self.visualization_service.create_brain_map_visualizer(
                self.collector_service.collector, 
                self.processor_service.processor
            )
            
            if success:
                self.visualization_service.start_brain_map_visualization()
                self.show_status("Brain map visualization started")
            else:
                self.show_error("Visualization Error", "Failed to create brain map visualizer")
        except Exception as e:
            self.show_error("Visualization Error", f"Error showing brain map: {e}")
    
    def enable_processing(self, enabled):
        """Enable or disable processing controls."""
        self.processing_enabled = enabled  # Store the state for brain map checks
        self.apply_filters_btn.setEnabled(enabled)
        self.calculate_metrics_btn.setEnabled(enabled)
        
        # Only enable brain map button if we're not already showing it
        if not hasattr(self.visualization_service, 'brain_map_visible') or not self.visualization_service.brain_map_visible():
            self.brain_map_btn.setEnabled(enabled)
