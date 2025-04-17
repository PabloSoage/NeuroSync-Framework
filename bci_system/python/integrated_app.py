"""
Integrated BCI System application.

This module combines EEG processing and input collection into a single
synchronized application for brain-computer interface research.
"""

import os
import sys
import time
import logging
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QPushButton, QLabel, QGroupBox, QCheckBox,
    QSplitter, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPalette, QIcon

# Import from EEG processor module
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "eeg_processor"))
from eeg_processor.python.eeg_processor_app import EEGProcessorApp

# Import from input collector module
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "input_collector"))
from input_collector.python.input_collector_app import InputCollectorApp


class IntegratedBCIApp(QMainWindow):
    """
    Integrated Brain-Computer Interface application.
    
    This class combines EEG processing and input collection into a single
    synchronized application interface with shared controls for recording.
    """
    
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    
    def __init__(self):
        """Initialize the integrated application."""
        super().__init__()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        
        # Window properties
        self.setWindowTitle("BCI System")
        self.setGeometry(50, 50, 1400, 900)
        
        # State variables
        self.is_recording = False
        self.is_eeg_connected = False
        self.is_eeg_streaming = False
        self.eeg_ready = False
        self.input_ready = True  # Input is always ready initially
        
        # Define app theme colors
        self.dark_bg = "#2D2D30"
        self.dark_frame_bg = "#252526" 
        self.text_color = "#E0E0E0"
        self.accent_color = "#007ACC"
        self.success_color = "#5FB878"
        self.warning_color = "#FFAA33"
        self.error_color = "#FF5555"
        
        # Set application style
        self._set_dark_theme()
        
        # Setup UI components
        self._init_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Status update timer
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(500)  # Update every 500ms
        
        # Update initial status
        self._update_status()
        
        logging.info("Integrated BCI application initialized")
    
    def _set_dark_theme(self):
        """Set the application to use a dark theme."""
        palette = QPalette()
        
        # Set colors
        palette.setColor(QPalette.Window, QColor(self.dark_bg))
        palette.setColor(QPalette.WindowText, QColor(self.text_color))
        palette.setColor(QPalette.Base, QColor(self.dark_frame_bg))
        palette.setColor(QPalette.AlternateBase, QColor(self.dark_bg))
        palette.setColor(QPalette.ToolTipBase, QColor(self.dark_bg))
        palette.setColor(QPalette.ToolTipText, QColor(self.text_color))
        palette.setColor(QPalette.Text, QColor(self.text_color))
        palette.setColor(QPalette.Button, QColor(self.dark_bg))
        palette.setColor(QPalette.ButtonText, QColor(self.text_color))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(self.accent_color))
        palette.setColor(QPalette.Highlight, QColor(self.accent_color))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        QApplication.setPalette(palette)
        
        # Set stylesheet for detailed control
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {self.dark_bg}; color: {self.text_color}; }}
            QGroupBox {{
                border: 1px solid #444;
                margin-top: 0.5em;
                border-radius: 3px;
                padding: 0.5em;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: {self.text_color};
            }}
            QPushButton {{
                background-color: {self.accent_color};
                color: white;
                border: none;
                padding: 4px 8px;
                min-height: 24px;
                border-radius: 2px;
            }}
            QPushButton:pressed {{ background-color: #005599; }}
            QPushButton:hover {{ background-color: #0066aa; }}
            QPushButton:disabled {{
                background-color: #555555;
                color: #999999;
            }}
            QLineEdit, QTextEdit, QListWidget, QComboBox {{
                background-color: {self.dark_frame_bg};
                color: {self.text_color};
                border: 1px solid #444;
                padding: 2px;
                border-radius: 2px;
            }}
            QTextEdit {{ font-family: 'Consolas', monospace; }}
            QTabWidget::pane {{ 
                border: 1px solid #444;
                background: {self.dark_bg};
                top: -1px;
            }}
            QTabBar::tab {{
                background: {self.dark_frame_bg};
                color: {self.text_color};
                border: 1px solid #444;
                border-bottom-color: {self.dark_bg}; 
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 120px;
                padding: 5px;
            }}
            QTabBar::tab:selected, QTabBar::tab:hover {{
                background: {self.accent_color};
            }}
            QTabBar::tab:selected {{
                border-bottom-color: {self.accent_color};
            }}
            QCheckBox::indicator {{
                width: 13px;
                height: 13px;
                border: 1px solid #444;
                border-radius: 2px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.accent_color};
            }}
        """)
    
    def _init_ui(self):
        """Initialize user interface components."""
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main layout
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Shared controls
        self._create_shared_controls(main_layout)
        
        # Tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, 1)
        
        # Create tabs
        self._create_eeg_tab()
        self._create_input_tab()
        self._create_integrated_tab()
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def _create_shared_controls(self, parent_layout):
        """Create shared controls that affect both modules."""
        control_group = QGroupBox("BCI System Controls")
        control_layout = QVBoxLayout(control_group)
        
        # Status and controls layout
        status_layout = QHBoxLayout()
        
        # Connection status
        connection_layout = QHBoxLayout()
        connection_layout.addWidget(QLabel("EEG:"))
        self.eeg_status_label = QLabel("Not connected")
        self.eeg_status_label.setStyleSheet(f"color: {self.warning_color};")
        connection_layout.addWidget(self.eeg_status_label)
        
        connection_layout.addSpacing(20)
        
        connection_layout.addWidget(QLabel("Input:"))
        self.input_status_label = QLabel("Ready")
        self.input_status_label.setStyleSheet(f"color: {self.success_color};")
        connection_layout.addWidget(self.input_status_label)
        
        status_layout.addLayout(connection_layout)
        status_layout.addStretch(1)
        
        # Recording controls
        record_layout = QHBoxLayout()
        self.record_button = QPushButton("Start Recording")
        self.record_button.setMinimumWidth(150)
        self.record_button.setStyleSheet(f"background-color: #228822;")
        self.record_button.clicked.connect(self.toggle_recording)
        record_layout.addWidget(self.record_button)
        
        self.record_status_label = QLabel("Not Recording")
        record_layout.addWidget(self.record_status_label)
        
        # Session timer
        record_layout.addSpacing(20)
        record_layout.addWidget(QLabel("Session:"))
        self.session_timer_label = QLabel("00:00:00")
        record_layout.addWidget(self.session_timer_label)
        
        status_layout.addLayout(record_layout)
        
        control_layout.addLayout(status_layout)
        
        # Add checkboxes for module recording options
        options_layout = QHBoxLayout()
        
        # EEG options
        eeg_options = QHBoxLayout()
        eeg_options.addWidget(QLabel("EEG Options:"))
        
        self.save_eeg_check = QCheckBox("Save EEG Data")
        self.save_eeg_check.setChecked(True)
        eeg_options.addWidget(self.save_eeg_check)
        
        self.visualize_eeg_check = QCheckBox("Show Visualizers")
        self.visualize_eeg_check.setChecked(True) 
        eeg_options.addWidget(self.visualize_eeg_check)
        
        eeg_options.addStretch(1)
        options_layout.addLayout(eeg_options)
        
        # Spacer
        options_layout.addSpacing(40)
        
        # Input options
        input_options = QHBoxLayout()
        input_options.addWidget(QLabel("Input Options:"))
        
        self.save_input_check = QCheckBox("Save Input Data") 
        self.save_input_check.setChecked(True)
        input_options.addWidget(self.save_input_check)
        
        self.visualize_input_check = QCheckBox("Show Visualizers")
        self.visualize_input_check.setChecked(True)
        input_options.addWidget(self.visualize_input_check)
        
        input_options.addStretch(1)
        options_layout.addLayout(input_options)
        
        control_layout.addLayout(options_layout)
        
        # Session timer
        self.session_start_time = 0
        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self._update_session_time)
        self.session_timer.setInterval(1000)  # Update every second
        
        parent_layout.addWidget(control_group)
    
    def _create_eeg_tab(self):
        """Create the EEG processor tab."""
        # Embed EEG processor app
        self.eeg_container = QWidget()
        eeg_layout = QVBoxLayout(self.eeg_container)
        eeg_layout.setContentsMargins(0, 0, 0, 0)
        
        self.eeg_processor_app = EEGProcessorApp()
        eeg_layout.addWidget(self.eeg_processor_app)
        
        # Add to tabs
        self.tabs.addTab(self.eeg_container, "EEG Processing")
    
    def _create_input_tab(self):
        """Create the input collector tab."""
        # Embed input collector app
        self.input_container = QWidget()
        input_layout = QVBoxLayout(self.input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.input_collector_app = InputCollectorApp()
        input_layout.addWidget(self.input_collector_app)
        
        # Add to tabs
        self.tabs.addTab(self.input_container, "Input Collection")
    
    def _create_integrated_tab(self):
        """Create the integrated view tab."""
        self.integrated_container = QWidget()
        integrated_layout = QVBoxLayout(self.integrated_container)
        
        # Create a splitter for resizable sections
        splitter = QSplitter(Qt.Vertical)
        
        # Upper section - can show minimized EEG visualization
        eeg_section = QWidget()
        eeg_section_layout = QVBoxLayout(eeg_section)
        eeg_section_layout.addWidget(QLabel("EEG Visualization:"))
        
        # Here you would add minimized EEG visualizations
        # For now, just add a placeholder
        eeg_viz_placeholder = QLabel("EEG visualization will appear here when recording starts")
        eeg_viz_placeholder.setAlignment(Qt.AlignCenter)
        eeg_viz_placeholder.setStyleSheet(f"background-color: {self.dark_frame_bg}; padding: 40px;")
        eeg_section_layout.addWidget(eeg_viz_placeholder)
        
        splitter.addWidget(eeg_section)
        
        # Lower section - can show minimized input visualization
        input_section = QWidget()
        input_section_layout = QVBoxLayout(input_section)
        input_section_layout.addWidget(QLabel("Input Visualization:"))
        
        # Here you would add minimized input visualizations
        # For now, just add a placeholder
        input_viz_placeholder = QLabel("Input visualization will appear here when recording starts")
        input_viz_placeholder.setAlignment(Qt.AlignCenter)
        input_viz_placeholder.setStyleSheet(f"background-color: {self.dark_frame_bg}; padding: 40px;")
        input_section_layout.addWidget(input_viz_placeholder)
        
        splitter.addWidget(input_section)
        
        # Set default sizes
        splitter.setSizes([int(self.height() * 0.5), int(self.height() * 0.5)])
        
        integrated_layout.addWidget(splitter)
        
        # Add to tabs
        self.tabs.addTab(self.integrated_container, "Integrated View")
    
    def _connect_signals(self):
        """Connect signals between components."""
        # Connect signals from the EEG processor app
        if hasattr(self.eeg_processor_app, 'connect_btn'):
            self.eeg_processor_app.connect_btn.clicked.connect(self._on_eeg_connection_change)
        if hasattr(self.eeg_processor_app, 'disconnect_btn'):
            self.eeg_processor_app.disconnect_btn.clicked.connect(self._on_eeg_connection_change)
        if hasattr(self.eeg_processor_app, 'start_stream_btn'):
            self.eeg_processor_app.start_stream_btn.clicked.connect(self._on_eeg_stream_change)
        if hasattr(self.eeg_processor_app, 'stop_stream_btn'):
            self.eeg_processor_app.stop_stream_btn.clicked.connect(self._on_eeg_stream_change)
        
        # Connect recording signals to both apps
        self.recording_started.connect(self._start_eeg_recording)
        self.recording_started.connect(self._start_input_recording)
        self.recording_stopped.connect(self._stop_eeg_recording)
        self.recording_stopped.connect(self._stop_input_recording)
        
        # Disable original recording buttons
        if hasattr(self.eeg_processor_app, 'start_record_btn'):
            self.eeg_processor_app.start_record_btn.setVisible(False)
        if hasattr(self.eeg_processor_app, 'stop_record_btn'):
            self.eeg_processor_app.stop_record_btn.setVisible(False)
        
        # Disable original input collector record button
        if hasattr(self.input_collector_app, 'record_button'):
            original_record_btn = self.input_collector_app.findChild(QPushButton, 'record_button')
            if original_record_btn:
                original_record_btn.setVisible(False)
    
    def _update_status(self):
        """Update status information."""
        # Update EEG status
        is_eeg_connected = False
        is_eeg_streaming = False
        
        # Check EEG collector connection status
        if hasattr(self.eeg_processor_app, 'collector') and self.eeg_processor_app.collector:
            is_eeg_connected = True
            
            # Check streaming status
            if hasattr(self.eeg_processor_app, 'is_streaming'):
                is_eeg_streaming = self.eeg_processor_app.is_streaming
        
        # Update status indicators
        if is_eeg_connected:
            if is_eeg_streaming:
                self.eeg_status_label.setText("Streaming")
                self.eeg_status_label.setStyleSheet(f"color: {self.success_color};")
                self.eeg_ready = True
            else:
                self.eeg_status_label.setText("Connected")
                self.eeg_status_label.setStyleSheet(f"color: {self.accent_color};")
                self.eeg_ready = False
        else:
            self.eeg_status_label.setText("Not Connected")
            self.eeg_status_label.setStyleSheet(f"color: {self.warning_color};")
            self.eeg_ready = False
        
        # Store state
        self.is_eeg_connected = is_eeg_connected
        self.is_eeg_streaming = is_eeg_streaming
        
        # Update input collector status
        is_input_ready = True  # Input collector is always ready for recording
        
        # Check if input collector is in recording state
        is_input_recording = False
        if hasattr(self.input_collector_app, 'is_recording'):
            is_input_recording = self.input_collector_app.is_recording
        
        if is_input_recording:
            self.input_status_label.setText("Recording")
            self.input_status_label.setStyleSheet(f"color: {self.success_color};")
        else:
            self.input_status_label.setText("Ready")
            self.input_status_label.setStyleSheet(f"color: {self.success_color};")
        
        self.input_ready = is_input_ready
        
        # Update recording button state
        self.record_button.setEnabled(self.eeg_ready and self.input_ready)
        
        # If we're in recording state but one of the systems isn't ready anymore, stop recording
        if self.is_recording and not (self.eeg_ready and self.input_ready):
            self.toggle_recording()
            QMessageBox.warning(self, "Recording Stopped", 
                               "Recording has been stopped because EEG stream was disconnected.")
    
    def toggle_recording(self):
        """Toggle recording state for both EEG and input collection."""
        if not self.is_recording:
            # Start recording
            if not self.eeg_ready:
                QMessageBox.warning(self, "Cannot Start Recording",
                                   "EEG must be connected and streaming before recording can start.")
                return
                
            self.is_recording = True
            self.record_button.setText("Stop Recording")
            self.record_button.setStyleSheet("background-color: #CC3333;")
            self.record_status_label.setText("RECORDING")
            
            # Start session timer
            self.session_start_time = time.time()
            self.session_timer.start()
            
            # Emit signal to start recording in both modules
            self.recording_started.emit()
            
        else:
            # Stop recording
            self.is_recording = False
            self.record_button.setText("Start Recording")
            self.record_button.setStyleSheet("background-color: #228822;")
            self.record_status_label.setText("Not Recording")
            
            # Stop session timer
            self.session_timer.stop()
            
            # Emit signal to stop recording in both modules
            self.recording_stopped.emit()
    
    def _start_eeg_recording(self):
        """Start recording in the EEG processor app."""
        if not self.save_eeg_check.isChecked():
            return
            
        try:
            # Check if EEG processor app has a collector and is streaming
            if not (hasattr(self.eeg_processor_app, 'collector') and 
                    self.eeg_processor_app.collector and 
                    self.eeg_processor_app.is_streaming):
                logging.warning("EEG processor not ready for recording")
                return
                
            # Generate a timestamp for the filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"eeg_recording_{timestamp}.csv"
            
            # Set the filename in the EEG processor app
            if hasattr(self.eeg_processor_app, 'record_file_edit'):
                self.eeg_processor_app.record_file_edit.setText(filename)
            
            # Start recording
            if hasattr(self.eeg_processor_app, 'start_recording'):
                self.eeg_processor_app.start_recording()
            else:
                # Fallback if direct method access is not available
                if hasattr(self.eeg_processor_app, 'collector'):
                    data_type = "raw"  # Default to raw data
                    self.eeg_processor_app.collector.start_continuous_recording(filename, data_type)
            
            logging.info(f"Started EEG recording to {filename}")
            
        except Exception as e:
            logging.error(f"Error starting EEG recording: {e}")
    
    def _stop_eeg_recording(self):
        """Stop recording in the EEG processor app."""
        try:
            # Stop recording
            if hasattr(self.eeg_processor_app, 'stop_recording'):
                self.eeg_processor_app.stop_recording()
            else:
                # Fallback if direct method access is not available
                if hasattr(self.eeg_processor_app, 'collector'):
                    self.eeg_processor_app.collector.stop_continuous_recording()
            
            logging.info("Stopped EEG recording")
            
        except Exception as e:
            logging.error(f"Error stopping EEG recording: {e}")
    
    def _start_input_recording(self):
        """Start recording in the input collector app."""
        if not self.save_input_check.isChecked():
            return
            
        try:
            # Start recording in input collector
            if not self.input_collector_app.is_recording:
                self.input_collector_app._toggle_recording()
            
            logging.info("Started input recording")
            
        except Exception as e:
            logging.error(f"Error starting input recording: {e}")
    
    def _stop_input_recording(self):
        """Stop recording in the input collector app."""
        try:
            # Stop recording in input collector
            if self.input_collector_app.is_recording:
                self.input_collector_app._toggle_recording()
            
            logging.info("Stopped input recording")
            
        except Exception as e:
            logging.error(f"Error stopping input recording: {e}")
    
    def _update_session_time(self):
        """Update the session timer display."""
        if self.is_recording and self.session_start_time > 0:
            elapsed = int(time.time() - self.session_start_time)
            hours = elapsed // 3600
            minutes = (elapsed % 3600) // 60
            seconds = elapsed % 60
            self.session_timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def _on_eeg_connection_change(self):
        """Handle changes in the EEG connection state."""
        # Just trigger a status update
        QTimer.singleShot(100, self._update_status)
    
    def _on_eeg_stream_change(self):
        """Handle changes in the EEG streaming state."""
        # Just trigger a status update
        QTimer.singleShot(100, self._update_status)
    
    def closeEvent(self, event):
        """Handle application close event."""
        # Stop recording if active
        if self.is_recording:
            self.toggle_recording()
        
        # Close EEG connection if active
        if self.is_eeg_connected:
            try:
                if hasattr(self.eeg_processor_app, 'disconnect_board'):
                    self.eeg_processor_app.disconnect_board()
            except Exception as e:
                logging.error(f"Error disconnecting EEG board: {e}")
        
        # Accept the close event
        event.accept()
