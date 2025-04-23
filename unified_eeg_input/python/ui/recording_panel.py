"""
Unified recording panel.

This module provides a unified recording control panel for both EEG and input data.
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QFileDialog, QCheckBox,
    QComboBox, QSpinBox, QLineEdit
)
from PyQt5.QtCore import Qt, QTimer


class UnifiedRecordingPanel(QWidget):
    """
    Unified recording panel for controlling combined recordings.
    
    This panel provides controls to start/stop recordings for both
    EEG and input data with configurable options.
    """
    
    def __init__(self, coordinator, parent=None):
        """Initialize the recording panel."""
        super().__init__(parent)
        
        self.coordinator = coordinator
        self.recording = False
        
        # Create the UI
        self._create_ui()
        
        # Initialize state
        self.update_recording_state(False)
        self.update_ready_state(False, True)
    
    def _create_ui(self):
        """Create the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        
        # Create recording group
        recording_group = QGroupBox("Unified Recording Controls")
        recording_layout = QVBoxLayout(recording_group)
        
        # Row 1: Recording options
        options_layout = QHBoxLayout()
        
        # EEG recording options
        eeg_options_group = QGroupBox("EEG Recording")
        eeg_layout = QVBoxLayout(eeg_options_group)
        
        # EEG enable checkbox
        self.record_eeg_check = QCheckBox("Record EEG Data")
        self.record_eeg_check.setChecked(True)
        eeg_layout.addWidget(self.record_eeg_check)
        
        # EEG data type
        eeg_type_layout = QHBoxLayout()
        eeg_type_layout.addWidget(QLabel("Data Type:"))
        self.eeg_data_type_combo = QComboBox()
        self.eeg_data_type_combo.addItem("Raw", "raw")
        self.eeg_data_type_combo.addItem("Processed", "processed")
        self.eeg_data_type_combo.addItem("Both", "both")
        eeg_type_layout.addWidget(self.eeg_data_type_combo)
        eeg_layout.addLayout(eeg_type_layout)
        
        # Add EEG status indicator
        eeg_status_layout = QHBoxLayout()
        eeg_status_layout.addWidget(QLabel("EEG Ready:"))
        self.eeg_ready_indicator = QLabel("●")
        self.eeg_ready_indicator.setStyleSheet("color: #FF5555; font-size: 16px;")  # Red by default
        eeg_status_layout.addWidget(self.eeg_ready_indicator)
        eeg_status_layout.addStretch()
        eeg_layout.addLayout(eeg_status_layout)
        
        options_layout.addWidget(eeg_options_group)
        
        # Input recording options
        input_options_group = QGroupBox("Input Recording")
        input_layout = QVBoxLayout(input_options_group)
        
        # Input enable checkbox
        self.record_input_check = QCheckBox("Record Input Data")
        self.record_input_check.setChecked(True)
        input_layout.addWidget(self.record_input_check)
        
        # Input format options
        input_format_layout = QHBoxLayout()
        self.input_csv_check = QCheckBox("CSV")
        self.input_csv_check.setChecked(True)
        self.input_json_check = QCheckBox("JSON")
        self.input_json_check.setChecked(False)
        input_format_layout.addWidget(QLabel("Format:"))
        input_format_layout.addWidget(self.input_csv_check)
        input_format_layout.addWidget(self.input_json_check)
        input_layout.addLayout(input_format_layout)
        
        # Add Input status indicator
        input_status_layout = QHBoxLayout()
        input_status_layout.addWidget(QLabel("Input Ready:"))
        self.input_ready_indicator = QLabel("●")
        self.input_ready_indicator.setStyleSheet("color: #5FB878; font-size: 16px;")  # Green by default
        input_status_layout.addWidget(self.input_ready_indicator)
        input_status_layout.addStretch()
        input_layout.addLayout(input_status_layout)
        
        options_layout.addWidget(input_options_group)
        
        # Storage options
        storage_options_group = QGroupBox("Storage Options")
        storage_layout = QVBoxLayout(storage_options_group)
        
        # Directory selection
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Save to:"))
        self.save_dir_edit = QLineEdit()
        self.save_dir_edit.setPlaceholderText("Default: ./recordings/session_timestamp")
        dir_layout.addWidget(self.save_dir_edit)
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_save_directory)
        dir_layout.addWidget(self.browse_btn)
        storage_layout.addLayout(dir_layout)
        
        options_layout.addWidget(storage_options_group)
        
        recording_layout.addLayout(options_layout)
        
        # Row 2: Recording controls
        controls_layout = QHBoxLayout()
        
        # Recording status
        status_layout = QVBoxLayout()
        status_layout.addWidget(QLabel("Recording Status:"))
        self.recording_status = QLabel("Not Recording")
        self.recording_status.setStyleSheet("font-weight: bold; color: #AAAAAA;")
        status_layout.addWidget(self.recording_status)
        controls_layout.addLayout(status_layout)
        
        # Recording time
        time_layout = QVBoxLayout()
        time_layout.addWidget(QLabel("Recording Time:"))
        self.recording_time = QLabel("00:00")
        self.recording_time.setStyleSheet("font-weight: bold; font-size: 16px;")
        time_layout.addWidget(self.recording_time)
        controls_layout.addLayout(time_layout)
        
        # Marker controls
        marker_layout = QVBoxLayout()
        marker_sub_layout = QHBoxLayout()
        marker_sub_layout.addWidget(QLabel("Marker:"))
        self.marker_value = QSpinBox()
        self.marker_value.setRange(1, 99)
        self.marker_value.setValue(1)
        marker_sub_layout.addWidget(self.marker_value)
        self.add_marker_btn = QPushButton("Add Marker")
        self.add_marker_btn.clicked.connect(self.add_marker)
        self.add_marker_btn.setEnabled(False)
        marker_sub_layout.addWidget(self.add_marker_btn)
        marker_layout.addLayout(marker_sub_layout)
        controls_layout.addLayout(marker_layout)
        
        # Record button
        self.record_btn = QPushButton("Start Recording")
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setStyleSheet("font-weight: bold; font-size: 16px; background-color: #007ACC; color: white; min-height: 40px;")
        controls_layout.addWidget(self.record_btn)
        
        recording_layout.addLayout(controls_layout)
        
        # Add recording group to main layout
        layout.addWidget(recording_group)
    
    def browse_save_directory(self):
        """Open a dialog to select a save directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Save Directory",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if directory:
            self.save_dir_edit.setText(directory)
    
    def toggle_recording(self):
        """Toggle recording state."""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """Start recording with current settings."""
        # Get recording configuration
        config = {
            'record_eeg': self.record_eeg_check.isChecked(),
            'record_input': self.record_input_check.isChecked(),
            'eeg_data_type': self.eeg_data_type_combo.currentData(),
            'input_csv': self.input_csv_check.isChecked(),
            'input_json': self.input_json_check.isChecked(),
            'save_directory': self.save_dir_edit.text()
        }
        
        # Check if at least one recording type is enabled
        if not config['record_eeg'] and not config['record_input']:
            self.coordinator.status_message.emit("Please enable at least one recording type", "warning")
            return
        
        # Check if input format is selected when input recording is enabled
        if config['record_input'] and not (config['input_csv'] or config['input_json']):
            self.coordinator.status_message.emit("Please select at least one input format (CSV or JSON)", "warning")
            return
        
        # Start recording through coordinator
        self.coordinator.start_recording(config)
    
    def stop_recording(self):
        """Stop current recording."""
        self.coordinator.stop_recording()
    
    def add_marker(self):
        """Add a marker to the recording."""
        marker_value = self.marker_value.value()
        self.coordinator.add_marker(marker_value)
        
        # Increment marker value for convenience
        self.marker_value.setValue(marker_value + 1)
    
    def update_recording_state(self, is_recording):
        """
        Update the UI to reflect recording state.
        
        Args:
            is_recording: Whether recording is active
        """
        self.recording = is_recording
        
        if is_recording:
            # Update button
            self.record_btn.setText("Stop Recording")
            self.record_btn.setStyleSheet("font-weight: bold; font-size: 16px; background-color: #AA3333; color: white; min-height: 40px;")
            
            # Update status
            self.recording_status.setText("Recording")
            self.recording_status.setStyleSheet("font-weight: bold; color: #5FB878;")
            
            # Enable marker button
            self.add_marker_btn.setEnabled(True)
            
            # Disable configuration options
            self.record_eeg_check.setEnabled(False)
            self.record_input_check.setEnabled(False)
            self.eeg_data_type_combo.setEnabled(False)
            self.input_csv_check.setEnabled(False)
            self.input_json_check.setEnabled(False)
            self.save_dir_edit.setEnabled(False)
            self.browse_btn.setEnabled(False)
        else:
            # Update button
            self.record_btn.setText("Start Recording")
            self.record_btn.setStyleSheet("font-weight: bold; font-size: 16px; background-color: #007ACC; color: white; min-height: 40px;")
            
            # Update status
            self.recording_status.setText("Not Recording")
            self.recording_status.setStyleSheet("font-weight: bold; color: #AAAAAA;")
            
            # Disable marker button
            self.add_marker_btn.setEnabled(False)
            
            # Reset recording time
            self.recording_time.setText("00:00")
            
            # Enable configuration options
            self.record_eeg_check.setEnabled(True)
            self.record_input_check.setEnabled(True)
            self.eeg_data_type_combo.setEnabled(True)
            self.input_csv_check.setEnabled(True)
            self.input_json_check.setEnabled(True)
            self.save_dir_edit.setEnabled(True)
            self.browse_btn.setEnabled(True)
    
    def update_recording_time(self, seconds):
        """
        Update the displayed recording time.
        
        Args:
            seconds: Recording time in seconds
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        self.recording_time.setText(f"{minutes:02d}:{secs:02d}")
    
    def update_ready_state(self, eeg_ready, input_ready):
        """
        Update ready state indicators.
        
        Args:
            eeg_ready: Whether EEG system is ready
            input_ready: Whether input system is ready
        """
        # Update EEG ready indicator
        if eeg_ready:
            self.eeg_ready_indicator.setStyleSheet("color: #5FB878; font-size: 16px;")  # Green
        else:
            self.eeg_ready_indicator.setStyleSheet("color: #FF5555; font-size: 16px;")  # Red
            
        # Update Input ready indicator
        if input_ready:
            self.input_ready_indicator.setStyleSheet("color: #5FB878; font-size: 16px;")  # Green
        else:
            self.input_ready_indicator.setStyleSheet("color: #FF5555; font-size: 16px;")  # Red
        
        # Enable or disable record button based on at least one system ready
        # and appropriate recording options checked
        enable_record = False
        
        if eeg_ready and self.record_eeg_check.isChecked():
            enable_record = True
        
        if input_ready and self.record_input_check.isChecked():
            enable_record = True
        
        # Don't disable the button during recording
        if not self.recording:
            self.record_btn.setEnabled(enable_record)
