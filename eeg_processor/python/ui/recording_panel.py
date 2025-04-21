from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QFileDialog,
    QRadioButton, QSpinBox, QLineEdit
)
from PyQt5.QtCore import pyqtSignal

from .base_panel import BasePanel
from ..utils.help_system import HelpButton

class RecordingPanel(BasePanel):
    """Panel for data recording operations."""
    
    # Define signals specific to recording panel
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    
    def __init__(self, collector_service, recording_service, parent=None):
        """Initialize the recording panel."""
        super().__init__(parent)
        self.collector_service = collector_service
        self.recording_service = recording_service
        
        # Setup UI components
        self.setup_recording_options()
        
        # Add stretch to push everything to the top
        self.layout.addStretch()
    
    def setup_recording_options(self):
        """Set up recording options group."""
        self.record_group = QGroupBox("Recording Options")
        record_layout = QVBoxLayout(self.record_group)
        
        # Add help button for recording
        record_header_layout = QHBoxLayout()
        record_header_layout.addWidget(QLabel("Data Recording Settings"))
        record_header_layout.addWidget(HelpButton("recording", self))
        record_header_layout.addStretch()
        record_layout.addLayout(record_header_layout)
        
        # File selection
        file_layout = QHBoxLayout()
        file_label = QLabel("Save to file:")
        self.record_file_edit = QLineEdit()
        self.record_file_edit.setText("recordings/eeg_recording.csv")
        file_browse_btn = QPushButton("Browse")
        file_browse_btn.clicked.connect(self.browse_record_file)
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.record_file_edit)
        file_layout.addWidget(file_browse_btn)
        record_layout.addLayout(file_layout)

        # Record type
        type_layout = QHBoxLayout()
        type_label = QLabel("Data type:")
        self.raw_radio = QRadioButton("Raw")
        self.raw_radio.setChecked(True)
        self.processed_radio = QRadioButton("Processed")
        self.both_radio = QRadioButton("Both")
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.raw_radio)
        type_layout.addWidget(self.processed_radio)
        type_layout.addWidget(self.both_radio)
        record_layout.addLayout(type_layout)
        
        # Record control
        record_control_layout = QHBoxLayout()
        self.start_record_btn = QPushButton("Start Recording")
        self.start_record_btn.clicked.connect(self.start_recording)
        self.start_record_btn.setEnabled(False)
        self.stop_record_btn = QPushButton("Stop Recording")
        self.stop_record_btn.clicked.connect(self.stop_recording)
        self.stop_record_btn.setEnabled(False)
        record_control_layout.addWidget(self.start_record_btn)
        record_control_layout.addWidget(self.stop_record_btn)
        record_layout.addLayout(record_control_layout)
        
        # Add marker
        marker_layout = QHBoxLayout()
        marker_label = QLabel("Marker:")
        self.marker_value_spin = QSpinBox()
        self.marker_value_spin.setRange(1, 255)
        self.marker_value_spin.setValue(1)
        self.add_marker_btn = QPushButton("Add Marker")
        self.add_marker_btn.clicked.connect(self.add_marker)
        self.add_marker_btn.setEnabled(False)
        marker_layout.addWidget(marker_label)
        marker_layout.addWidget(self.marker_value_spin)
        marker_layout.addWidget(self.add_marker_btn)
        record_layout.addLayout(marker_layout)
        
        # Recording status
        status_layout = QHBoxLayout()
        status_label = QLabel("Recording Status:")
        self.recording_status_label = QLabel("Not recording")
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.recording_status_label)
        record_layout.addLayout(status_layout)
        
        # Save current data
        save_layout = QHBoxLayout()
        self.save_data_btn = QPushButton("Save Current Data")
        self.save_data_btn.clicked.connect(self.save_current_data)
        self.save_data_btn.setEnabled(False)
        save_layout.addWidget(self.save_data_btn)
        record_layout.addLayout(save_layout)
        
        self.layout.addWidget(self.record_group)
    
    def browse_record_file(self):
        """Browse for a file to save the recording."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Recording File", "", "CSV files (*.csv);; All Files (*)"
        )
        if filename:
            self.record_file_edit.setText(filename)
    
    def start_recording(self):
        """Start recording data to file."""
        try:
            filename = self.record_file_edit.text()
            if not filename:
                self.show_error("Recording Error", "Please specify a file path for recording")
                return
            
            # Determine data type
            if self.both_radio.isChecked():
                data_type = "both"
            elif self.processed_radio.isChecked():
                data_type = "processed"
            else:
                data_type = "raw"
            
            # Start recording through service
            success = self.recording_service.start_recording(
                self.collector_service.collector, filename, data_type
            )
            
            if success:
                # Update UI
                self.start_record_btn.setEnabled(False)
                self.stop_record_btn.setEnabled(True)
                self.add_marker_btn.setEnabled(True)
                
                # Emit signal
                self.recording_started.emit()
                
                self.show_status(f"Recording to {filename}")
            else:
                self.show_error("Recording Error", "Failed to start recording")
        except Exception as e:
            self.show_error("Recording Error", f"Failed to start recording: {str(e)}")
    
    def stop_recording(self):
        """Stop recording and save data to file."""
        try:
            success = self.recording_service.stop_recording(self.collector_service.collector)
            
            if success:
                # Update UI
                self.start_record_btn.setEnabled(True)
                self.stop_record_btn.setEnabled(False)
                self.add_marker_btn.setEnabled(False)
                self.recording_status_label.setText("Not recording")
                
                # Emit signal
                self.recording_stopped.emit()
                
                self.show_status("Recording stopped and saved")
            else:
                self.show_error("Recording Error", "Failed to stop recording")
        except Exception as e:
            self.show_error("Recording Error", f"Failed to stop recording: {str(e)}")
    
    def add_marker(self):
        """Add a marker to the data stream."""
        try:
            marker_value = self.marker_value_spin.value()
            success = self.recording_service.insert_marker(
                self.collector_service.collector, marker_value
            )
            
            if success:
                self.show_status(f"Marker {marker_value} added")
            else:
                self.show_error("Marker Error", "Failed to add marker")
        except Exception as e:
            self.show_error("Marker Error", f"Failed to add marker: {str(e)}")
    
    def save_current_data(self):
        """Save current data to file."""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Data", "", "CSV files (*.csv)"
            )
            
            if filename and self.collector_service.collector:
                data_type = "processed" if self.processed_radio.isChecked() else "raw"
                self.collector_service.collector.save_data(filename, data_type)
                self.show_status(f"Data saved to {filename}")
        except Exception as e:
            self.show_error("Save Error", f"Failed to save data: {str(e)}")
    
    def enable_recording(self, enabled):
        """Enable or disable recording controls."""
        self.start_record_btn.setEnabled(enabled)
        self.save_data_btn.setEnabled(enabled)
    
    def update_recording_status(self, status_text):
        """Update the recording status label."""
        self.recording_status_label.setText(status_text)
