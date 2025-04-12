import os
import sys
import time
import logging
from typing import Dict, List, Any, Optional
import json

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                           QComboBox, QPushButton, QLabel, QGroupBox, QCheckBox,
                           QSpinBox, QDoubleSpinBox, QFileDialog, QTabWidget,
                           QRadioButton, QSlider, QMessageBox)
from PyQt5.QtCore import Qt, QTimer

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, LogLevels
from brainflow.data_filter import FilterTypes, AggOperations, WindowOperations, WaveletTypes

from .collectors.eeg_collector import EEGCollector
from .processors.signal_processor import SignalProcessor
from .visualizers.eeg_viz import EEGVisualizer


class EEGProcessorApp(QMainWindow):
    """
    Main application for EEG data collection, processing and visualization.
    
    This class provides a GUI for interacting with BrainFlow and managing EEG data.
    """
    
    def __init__(self):
        """Initialize the EEG processor application."""
        super().__init__()
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        BoardShim.enable_dev_board_logger()
        
        self.setWindowTitle("EEG Processor")
        self.setGeometry(100, 100, 1200, 800)
        
        # Data handling objects
        self.collector = None
        self.processor = None
        self.visualizer = None
        
        # Application state
        self.is_streaming = False
        self.is_recording = False
        self.record_filename = ""
        self.start_time = 0
        
        # Initialize UI
        self.setup_ui()
        
        # Timer for updating status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Update every second
        
        logging.info("EEG Processor application initialized")
        
    def setup_ui(self):
        """Set up the user interface."""
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create tabs
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # Connection tab
        connection_tab = QWidget()
        tabs.addTab(connection_tab, "Connection")
        self.setup_connection_tab(connection_tab)
        
        # Processing tab
        processing_tab = QWidget()
        tabs.addTab(processing_tab, "Processing")
        self.setup_processing_tab(processing_tab)
        
        # Recording tab
        recording_tab = QWidget()
        tabs.addTab(recording_tab, "Recording")
        self.setup_recording_tab(recording_tab)
        
        # Status bar for showing current status
        self.statusBar().showMessage("Ready")
        
    def setup_connection_tab(self, tab):
        """Set up the connection tab."""
        layout = QVBoxLayout(tab)
        
        # Board selection
        board_group = QGroupBox("Board Selection")
        board_layout = QVBoxLayout(board_group)
        
        board_type_layout = QHBoxLayout()
        board_type_label = QLabel("Board Type:")
        self.board_type_combo = QComboBox()
        
        # Add supported boards
        self.board_type_combo.addItem("Synthetic Board", BoardIds.SYNTHETIC_BOARD)
        self.board_type_combo.addItem("Unicorn Board", BoardIds.UNICORN_BOARD)
        self.board_type_combo.addItem("Playback File Board", BoardIds.PLAYBACK_FILE_BOARD)
        self.board_type_combo.addItem("Streaming Board", BoardIds.STREAMING_BOARD)
        
        self.board_type_combo.currentIndexChanged.connect(self.on_board_type_changed)
        
        board_type_layout.addWidget(board_type_label)
        board_type_layout.addWidget(self.board_type_combo)
        board_layout.addLayout(board_type_layout)
        
        # Parameters group
        param_group = QGroupBox("Board Parameters")
        param_layout = QVBoxLayout(param_group)
        
        # Serial port (for boards that need it)
        serial_layout = QHBoxLayout()
        serial_label = QLabel("Serial Port:")
        self.serial_edit = QtWidgets.QLineEdit()
        serial_layout.addWidget(serial_label)
        serial_layout.addWidget(self.serial_edit)
        param_layout.addLayout(serial_layout)
        
        # File for playback board
        file_layout = QHBoxLayout()
        file_label = QLabel("File Path:")
        self.file_edit = QtWidgets.QLineEdit()
        file_browse_btn = QPushButton("Browse")
        file_browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(file_browse_btn)
        param_layout.addLayout(file_layout)
        
        # Master board (for playback/streaming boards)
        master_layout = QHBoxLayout()
        master_label = QLabel("Master Board:")
        self.master_combo = QComboBox()
        self.master_combo.addItem("Synthetic Board", BoardIds.SYNTHETIC_BOARD)
        self.master_combo.addItem("Unicorn Board", BoardIds.UNICORN_BOARD)
        master_layout.addWidget(master_label)
        master_layout.addWidget(self.master_combo)
        param_layout.addLayout(master_layout)
        
        # IP settings (for streaming board)
        ip_layout = QHBoxLayout()
        ip_label = QLabel("IP Address:")
        self.ip_edit = QtWidgets.QLineEdit()
        self.ip_edit.setText("225.1.1.1")  # Default multicast address
        ip_port_label = QLabel("Port:")
        self.ip_port_spin = QSpinBox()
        self.ip_port_spin.setRange(1000, 65535)
        self.ip_port_spin.setValue(6677)  # Default port
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_edit)
        ip_layout.addWidget(ip_port_label)
        ip_layout.addWidget(self.ip_port_spin)
        param_layout.addLayout(ip_layout)
        
        # Add parameter group to layout
        board_layout.addWidget(param_group)
        
        # Connection control
        control_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_board)
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_board)
        self.disconnect_btn.setEnabled(False)
        control_layout.addWidget(self.connect_btn)
        control_layout.addWidget(self.disconnect_btn)
        board_layout.addLayout(control_layout)
        
        # Stream control
        stream_layout = QHBoxLayout()
        self.start_stream_btn = QPushButton("Start Stream")
        self.start_stream_btn.clicked.connect(self.start_stream)
        self.start_stream_btn.setEnabled(False)
        self.stop_stream_btn = QPushButton("Stop Stream")
        self.stop_stream_btn.clicked.connect(self.stop_stream)
        self.stop_stream_btn.setEnabled(False)
        stream_layout.addWidget(self.start_stream_btn)
        stream_layout.addWidget(self.stop_stream_btn)
        board_layout.addLayout(stream_layout)
        
        # Board info
        info_group = QGroupBox("Board Information")
        info_layout = QVBoxLayout(info_group)
        self.board_info_label = QLabel("No board connected")
        info_layout.addWidget(self.board_info_label)
        
        # Add groups to tab
        layout.addWidget(board_group)
        layout.addWidget(info_group)
        layout.addStretch()
        
        # Initially hide parameters that aren't needed
        self.on_board_type_changed()
        
    def setup_processing_tab(self, tab):
        """Set up the processing tab."""
        layout = QVBoxLayout(tab)
        
        # Filtering options
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
        filter_layout.addLayout(notch_layout)
        
        # Denoising
        denoise_layout = QHBoxLayout()
        self.denoise_check = QCheckBox("Wavelet Denoising")
        self.denoise_check.setChecked(False)
        
        wavelet_label = QLabel("Wavelet Type:")
        self.wavelet_combo = QComboBox()
        self.wavelet_combo.addItem("DB4", WaveletTypes.DB4)
        self.wavelet_combo.addItem("DB6", WaveletTypes.DB6)
        self.wavelet_combo.addItem("BIOR3_9", WaveletTypes.BIOR3_9)
        
        denoise_layout.addWidget(self.denoise_check)
        denoise_layout.addWidget(wavelet_label)
        denoise_layout.addWidget(self.wavelet_combo)
        filter_layout.addLayout(denoise_layout)
        
        # Detrend
        detrend_layout = QHBoxLayout()
        self.detrend_check = QCheckBox("Detrend")
        self.detrend_check.setChecked(True)
        detrend_layout.addWidget(self.detrend_check)
        filter_layout.addLayout(detrend_layout)
        
        # Apply filter button
        apply_layout = QHBoxLayout()
        self.apply_filters_btn = QPushButton("Apply Filters to Visualization")
        self.apply_filters_btn.clicked.connect(self.apply_filters)
        self.apply_filters_btn.setEnabled(False)
        apply_layout.addWidget(self.apply_filters_btn)
        filter_layout.addLayout(apply_layout)
        
        # EEG Metrics
        metrics_group = QGroupBox("EEG Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        
        metrics_update_layout = QHBoxLayout()
        self.calculate_metrics_btn = QPushButton("Calculate Metrics")
        self.calculate_metrics_btn.clicked.connect(self.calculate_metrics)
        self.calculate_metrics_btn.setEnabled(False)
        metrics_update_layout.addWidget(self.calculate_metrics_btn)
        metrics_layout.addLayout(metrics_update_layout)
        
        # Metrics display
        self.metrics_label = QLabel("No metrics calculated")
        metrics_layout.addWidget(self.metrics_label)
        
        # Add groups to tab
        layout.addWidget(filter_group)
        layout.addWidget(metrics_group)
        layout.addStretch()
        
    def setup_recording_tab(self, tab):
        """Set up the recording tab."""
        layout = QVBoxLayout(tab)
        
        # Recording options
        record_group = QGroupBox("Recording Options")
        record_layout = QVBoxLayout(record_group)
        
        # File selection
        file_layout = QHBoxLayout()
        file_label = QLabel("Save to file:")
        self.record_file_edit = QtWidgets.QLineEdit()
        self.record_file_edit.setText(os.path.join(os.getcwd(), "eeg_recording.csv"))
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
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.raw_radio)
        type_layout.addWidget(self.processed_radio)
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
        
        # Add to layout
        layout.addWidget(record_group)
        layout.addStretch()
        
    def on_board_type_changed(self):
        """Handle board type selection changes."""
        board_id = self.board_type_combo.currentData()
        
        # Hide all parameter fields initially
        self.serial_edit.setEnabled(False)
        self.file_edit.setEnabled(False)
        self.master_combo.setEnabled(False)
        self.ip_edit.setEnabled(False)
        self.ip_port_spin.setEnabled(False)
        
        # Enable relevant fields based on board type
        if board_id == BoardIds.UNICORN_BOARD:
            self.serial_edit.setEnabled(True)
        elif board_id == BoardIds.PLAYBACK_FILE_BOARD:
            self.file_edit.setEnabled(True)
            self.master_combo.setEnabled(True)
        elif board_id == BoardIds.STREAMING_BOARD:
            self.ip_edit.setEnabled(True)
            self.ip_port_spin.setEnabled(True)
            self.master_combo.setEnabled(True)
            
    def browse_file(self):
        """Browse for a file for playback board."""
        filename, _ = QFileDialog.getOpenFileName(self, "Select Data File", "", "CSV files (*.csv)")
        if filename:
            self.file_edit.setText(filename)
            
    def browse_record_file(self):
        """Browse for a file to save recorded data."""
        filename, _ = QFileDialog.getSaveFileName(self, "Save Recording", "", "CSV files (*.csv)")
        if filename:
            self.record_file_edit.setText(filename)
            
    def connect_board(self):
        """Connect to the selected EEG board."""
        try:
            board_id = self.board_type_combo.currentData()
            params = BrainFlowInputParams()
            
            # Set parameters based on board type
            if board_id == BoardIds.UNICORN_BOARD:
                params.serial_port = self.serial_edit.text()
            elif board_id == BoardIds.PLAYBACK_FILE_BOARD:
                params.file = self.file_edit.text()
                params.master_board = self.master_combo.currentData()
            elif board_id == BoardIds.STREAMING_BOARD:
                params.ip_address = self.ip_edit.text()
                params.ip_port = self.ip_port_spin.value()
                params.master_board = self.master_combo.currentData()
                
            # Create collector
            self.collector = EEGCollector(board_id, params)
            self.collector.prepare_session()
            
            # Create processor
            self.processor = SignalProcessor(self.collector.sampling_rate)
            
            # Update UI
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.start_stream_btn.setEnabled(True)
            self.save_data_btn.setEnabled(True)
            
            # Update board info
            board_info = self.collector.get_board_info()
            info_text = f"Connected to {board_info['board_name']}\n"
            info_text += f"Sampling Rate: {board_info['sampling_rate']} Hz\n"
            info_text += f"EEG Channels: {len(board_info['eeg_channels'])}"
            self.board_info_label.setText(info_text)
            
            self.statusBar().showMessage("Board connected successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to board: {str(e)}")
            logging.error(f"Connection error: {e}")
            
    def disconnect_board(self):
        """Disconnect from the EEG board."""
        try:
            if self.is_streaming:
                self.stop_stream()
                
            if self.collector:
                self.collector.release_session()
                self.collector = None
                self.processor = None
                self.visualizer = None
            
            # Update UI
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.start_stream_btn.setEnabled(False)
            self.stop_stream_btn.setEnabled(False)
            self.start_record_btn.setEnabled(False)
            self.stop_record_btn.setEnabled(False)
            self.add_marker_btn.setEnabled(False)
            self.save_data_btn.setEnabled(False)
            self.apply_filters_btn.setEnabled(False)
            self.calculate_metrics_btn.setEnabled(False)
            
            # Update info
            self.board_info_label.setText("No board connected")
            self.statusBar().showMessage("Board disconnected")
            
        except Exception as e:
            QMessageBox.warning(self, "Disconnection Error", f"Error during disconnection: {str(e)}")
            logging.error(f"Disconnection error: {e}")
            
    def start_stream(self):
        """Start streaming data from the board."""
        try:
            if self.collector and not self.is_streaming:
                self.collector.start_stream()
                self.is_streaming = True
                
                # Create visualizer
                if not self.visualizer:
                    self.visualizer = EEGVisualizer(self.collector, self.processor)
                    self.apply_filters()  # Apply initial filter settings
                self.visualizer.start()
                
                # Update UI
                self.start_stream_btn.setEnabled(False)
                self.stop_stream_btn.setEnabled(True)
                self.start_record_btn.setEnabled(True)
                self.add_marker_btn.setEnabled(True)
                self.apply_filters_btn.setEnabled(True)
                self.calculate_metrics_btn.setEnabled(True)
                
                self.statusBar().showMessage("Streaming started")
                
        except Exception as e:
            QMessageBox.critical(self, "Streaming Error", f"Failed to start streaming: {str(e)}")
            logging.error(f"Streaming error: {e}")
            
    def stop_stream(self):
        """Stop streaming data from the board."""
        try:
            if self.collector and self.is_streaming:
                if self.is_recording:
                    self.stop_recording()
                    
                self.collector.stop_stream()
                self.is_streaming = False
                
                if self.visualizer:
                    self.visualizer.stop()
                
                # Update UI
                self.start_stream_btn.setEnabled(True)
                self.stop_stream_btn.setEnabled(False)
                self.start_record_btn.setEnabled(False)
                self.stop_record_btn.setEnabled(False)
                self.add_marker_btn.setEnabled(False)
                
                self.statusBar().showMessage("Streaming stopped")
                
        except Exception as e:
            QMessageBox.warning(self, "Streaming Error", f"Error stopping stream: {str(e)}")
            logging.error(f"Error stopping stream: {e}")
            
    def start_recording(self):
        """Start recording data to file."""
        if not self.collector or not self.is_streaming:
            return
            
        self.record_filename = self.record_file_edit.text()
        if not self.record_filename:
            QMessageBox.warning(self, "Recording Error", "Please specify a file path for recording")
            return
            
        self.is_recording = True
        self.start_time = int(round(time.time() * 1000))  # Start time in ms
        
        # Update UI
        self.start_record_btn.setEnabled(False)
        self.stop_record_btn.setEnabled(True)
        self.recording_status_label.setText("Recording...")
        
        self.statusBar().showMessage(f"Recording to {self.record_filename}")
        
    def stop_recording(self):
        """Stop recording and save data to file."""
        if not self.is_recording:
            return
            
        try:
            data_type = 'processed' if self.processed_radio.isChecked() else 'raw'
            self.collector.save_data(self.record_filename, data_type)
            
            self.is_recording = False
            
            # Update UI
            self.start_record_btn.setEnabled(True)
            self.stop_record_btn.setEnabled(False)
            self.recording_status_label.setText("Not recording")
            
            duration = (int(round(time.time() * 1000)) - self.start_time) / 1000  # Duration in seconds
            self.statusBar().showMessage(f"Recording saved: {duration:.1f}s")
            
        except Exception as e:
            QMessageBox.critical(self, "Recording Error", f"Failed to save recording: {str(e)}")
            logging.error(f"Recording error: {e}")
            
    def add_marker(self):
        """Add a marker to the data stream."""
        if not self.collector or not self.is_streaming:
            return
            
        marker_value = self.marker_value_spin.value()
        self.collector.insert_marker(marker_value)
        self.statusBar().showMessage(f"Marker {marker_value} added")
        
    def save_current_data(self):
        """Save current data to file."""
        if not self.collector:
            return
            
        try:
            filename, _ = QFileDialog.getSaveFileName(self, "Save Data", "", "CSV files (*.csv)")
            if filename:
                data_type = 'processed' if self.processed_radio.isChecked() else 'raw'
                self.collector.save_data(filename, data_type)
                self.statusBar().showMessage(f"Data saved to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save data: {str(e)}")
            logging.error(f"Save error: {e}")
            
    def apply_filters(self):
        """Apply the selected filters to visualization."""
        if not self.visualizer:
            return
            
        self.visualizer.set_bandpass_filter(
            self.bandpass_check.isChecked(),
            self.bandpass_low_spin.value(),
            self.bandpass_high_spin.value()
        )
        self.visualizer.set_notch_filter(self.notch_check.isChecked())
        self.visualizer.set_detrend(self.detrend_check.isChecked())
        
        self.statusBar().showMessage("Filters applied to visualization")
        
    def calculate_metrics(self):
        """Calculate EEG metrics from the current data."""
        if not self.collector or not self.processor or not self.is_streaming:
            return
            
        try:
            data, _ = self.collector.get_data(4 * self.collector.sampling_rate)  # Get 4 seconds of data
            if data.size == 0:
                return
                
            metrics = self.processor.get_eeg_metrics(data, self.collector.get_eeg_channels())
            
            # Update display
            metrics_text = f"Mindfulness: {metrics['mindfulness']:.2f}\n"
            metrics_text += f"Concentration: {metrics['concentration']:.2f}\n"
            metrics_text += f"Relaxation: {metrics['relaxation']:.2f}\n"
            metrics_text += f"Restfulness: {metrics['restfulness']:.2f}"
            self.metrics_label.setText(metrics_text)
            
            self.statusBar().showMessage("EEG metrics calculated")
            
        except Exception as e:
            QMessageBox.warning(self, "Metrics Error", f"Failed to calculate metrics: {str(e)}")
            logging.error(f"Metrics error: {e}")
    
    def update_status(self):
        """Update status information."""
        if self.is_recording:
            duration = (int(round(time.time() * 1000)) - self.start_time) / 1000  # Duration in seconds
            self.recording_status_label.setText(f"Recording... ({duration:.1f}s)")
    
    def closeEvent(self, event):
        """Handle application close event."""
        if self.collector:
            try:
                if self.is_streaming:
                    self.collector.stop_stream()
                self.collector.release_session()
            except Exception as e:
                logging.error(f"Error during shutdown: {e}")
        
        event.accept()
