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
    QTabWidget, QPushButton, QLabel, QGroupBox, QCheckBox, QComboBox,
    QSplitter, QMessageBox, QScrollArea, QSizePolicy, QFrame,
    QFileDialog, QLineEdit, QRadioButton  # Added QFileDialog, QLineEdit, QRadioButton
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPalette, QIcon

# Import from EEG processor module
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "eeg_processor"))
from eeg_processor.python.eeg_processor_app import EEGProcessorApp

# Import from input collector module
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "input_collector"))
from input_collector.python.input_collector_app import InputCollectorApp

# Import the LSL synchronization module
from lsl_synchronizer import (
    LSLEEGPublisher, LSLInputPublisher, LSLMarkerPublisher, 
    LSLDataReceiver, DatasetExporter, LSLSynchronizerWidget
)

# Add missing import
import os.path

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
        self.is_synchronized = False
        
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
        
        # Create recordings directory if it doesn't exist - MOVED UP BEFORE _init_ui()
        self.recordings_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings")
        os.makedirs(self.recordings_dir, exist_ok=True)
        
        # LSL synchronization components
        self.eeg_publisher = None
        self.input_publisher = LSLInputPublisher()
        self.marker_publisher = LSLMarkerPublisher()
        self.lsl_receiver = LSLDataReceiver()
        self.dataset_exporter = DatasetExporter(self.lsl_receiver)
        
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
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: {self.dark_frame_bg};
                width: 12px;
                margin: 12px 0 12px 0;
            }}
            QScrollBar::handle:vertical {{
                background: #666;
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::add-line:vertical {{
                border: none;
                background: none;
                height: 12px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }}
            QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 12px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }}
            QScrollBar:horizontal {{
                background: {self.dark_frame_bg};
                height: 12px;
                margin: 0 12px 0 12px;
            }}
            QScrollBar::handle:horizontal {{
                background: #666;
                min-width: 20px;
                border-radius: 3px;
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
        self._create_synchronization_tab()  # New tab for LSL synchronization
        
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
        
        # Add file path selection controls
        file_path_layout = QHBoxLayout()
        file_path_layout.addWidget(QLabel("Recording Directory:"))
        
        self.record_file_edit = QLineEdit()
        self.record_file_edit.setReadOnly(True)
        # Set a default recording path
        self.record_file_edit.setText(self.recordings_dir)
        file_path_layout.addWidget(self.record_file_edit, 1)  # Give it more space
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_record_path)
        file_path_layout.addWidget(self.browse_btn)
        
        control_layout.addLayout(file_path_layout)

        # Helper text to explain session folder creation
        session_info_label = QLabel("Recordings are saved in session folders within this directory")
        session_info_label.setStyleSheet("color: #999; font-size: 10px;")
        control_layout.addWidget(session_info_label)
        
        # Add checkboxes for module recording options
        options_layout = QHBoxLayout()
        
        # EEG options
        eeg_options = QHBoxLayout()
        eeg_options.addWidget(QLabel("EEG Options:"))
        
        self.save_eeg_check = QCheckBox("Save EEG Data")
        self.save_eeg_check.setChecked(True)
        eeg_options.addWidget(self.save_eeg_check)
        
        # Add EEG raw/processed option
        self.eeg_raw_radio = QRadioButton("Raw Data")
        self.eeg_raw_radio.setChecked(True)
        eeg_options.addWidget(self.eeg_raw_radio)
        
        self.eeg_processed_radio = QRadioButton("Processed Data")
        eeg_options.addWidget(self.eeg_processed_radio)
        
        # Add Both option for recording both raw and processed data
        self.eeg_both_radio = QRadioButton("Both")
        eeg_options.addWidget(self.eeg_both_radio)
        
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
        
        # Add input format options
        self.input_json_check = QCheckBox("JSON Format")
        self.input_json_check.setChecked(False)  # Changed from True to False - unchecked by default
        input_options.addWidget(self.input_json_check)
        
        self.input_csv_check = QCheckBox("CSV Format")
        self.input_csv_check.setChecked(True)
        input_options.addWidget(self.input_csv_check)
        
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

    def browse_record_path(self):
        """Browse for a directory to save recordings."""
        # Get directory for saving session
        directory = QFileDialog.getExistingDirectory(
            self, "Select Recording Directory", self.recordings_dir
        )
        
        if (directory):
            # Update the recordings directory
            self.recordings_dir = directory
            
            # Update the text field with the base path
            default_path = self.recordings_dir
            self.record_file_edit.setText(default_path)
            
            logging.info(f"Recording directory set to: {directory}")
            logging.info(f"Recording base filename: {os.path.basename(default_path)}")

    def _create_eeg_tab(self):
        """Create the EEG processor tab with scrollability."""
        # Create the EEG processor app instance first
        self.eeg_processor_app = EEGProcessorApp()
        
        # Create a scroll area to contain the EEG processor app
        self.eeg_container = QWidget()
        eeg_layout = QVBoxLayout(self.eeg_container)
        eeg_layout.setContentsMargins(0, 0, 0, 0)
        eeg_layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create container for the EEG processor app
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.addWidget(self.eeg_processor_app)
        
        # Add widget to scroll area
        scroll_area.setWidget(scroll_widget)
        
        # Add scroll area to the container
        eeg_layout.addWidget(scroll_area)
        
        # Add to tabs
        self.tabs.addTab(self.eeg_container, "EEG Processing")
        
        # Hide the file selection controls in EEG processor
        if hasattr(self.eeg_processor_app, 'record_file_edit'):
            self.eeg_processor_app.record_file_edit.setVisible(False)
        if hasattr(self.eeg_processor_app, 'record_group'):
            # Hide the "Save to file:" label and browse button
            for child in self.eeg_processor_app.record_group.children():
                if isinstance(child, QLabel) and "Save to file:" in child.text():
                    child.setVisible(False)
                elif isinstance(child, QPushButton) and "Browse" in child.text():
                    child.setVisible(False)
                
            # Hide the "Data type:" label and all radio buttons
            for child in self.eeg_processor_app.record_group.children():
                if isinstance(child, QLabel) and "Data type:" in child.text():
                    child.setVisible(False)
                elif isinstance(child, QRadioButton):
                    child.setVisible(False)
    
    def _create_input_tab(self):
        """Create the input collector tab with scrollability."""
        # Create the input collector app instance first
        self.input_collector_app = InputCollectorApp()
        
        # Explicitly remove Button.scroll from tracked keys by default
        if hasattr(self.input_collector_app, 'tracked_keys'):
            # Filter out Button.scroll from tracked keys
            self.input_collector_app.tracked_keys = [
                key for key in self.input_collector_app.tracked_keys 
                if key.lower() != "button.scroll" and key.lower() != "scrollwheel"
            ]
            
            # Update collector's tracked keys
            if hasattr(self.input_collector_app, 'collector_manager'):
                self.input_collector_app.collector_manager.set_tracked_keys(self.input_collector_app.tracked_keys)
                
            # Update visualizers with the new key set
            if hasattr(self.input_collector_app, 'visualizer_manager'):
                self.input_collector_app.visualizer_manager.set_tracked_keys(self.input_collector_app.tracked_keys)
        
        # Create a scroll area to contain the Input collector app
        self.input_container = QWidget()
        input_layout = QVBoxLayout(self.input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create container for the input collector app
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.addWidget(self.input_collector_app)
        
        # Add widget to scroll area
        scroll_area.setWidget(scroll_widget)
        
        # Add scroll area to the container
        input_layout.addWidget(scroll_area)
        
        # Add to tabs
        self.tabs.addTab(self.input_container, "Input Collection")
        
        # Hide the JSON and CSV logging checkboxes
        if hasattr(self.input_collector_app, 'log_checkbox'):
            self.input_collector_app.log_checkbox.setVisible(False)
        if hasattr(self.input_collector_app, 'csv_checkbox'):
            self.input_collector_app.csv_checkbox.setVisible(False)
        
        # Hide the CSV path field and browse button
        if hasattr(self.input_collector_app, 'csv_path_field'):
            self.input_collector_app.csv_path_field.setVisible(False)
        if hasattr(self.input_collector_app, 'csv_path_button'):
            self.input_collector_app.csv_path_button.setVisible(False)
        
        # Also hide any "Path:" label
        for child in self.input_collector_app.children():
            if isinstance(child, QLabel) and "Path:" in child.text():
                child.setVisible(False)
    
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
    
    def _create_synchronization_tab(self):
        """Create the LSL synchronization tab."""
        self.sync_container = QWidget()
        sync_layout = QVBoxLayout(self.sync_container)
        
        # Add synchronization settings
        settings_group = QGroupBox("LSL Synchronization Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # Add sync mode options
        sync_mode_layout = QHBoxLayout()
        sync_mode_layout.addWidget(QLabel("Synchronization Mode:"))
        
        self.realtime_sync_radio = QRadioButton("Real-time")
        self.realtime_sync_radio.setChecked(True)
        self.realtime_sync_radio.toggled.connect(self._update_sync_mode)
        sync_mode_layout.addWidget(self.realtime_sync_radio)
        
        self.offline_sync_radio = QRadioButton("Offline (Post-processing)")
        self.offline_sync_radio.toggled.connect(self._update_sync_mode)
        sync_mode_layout.addWidget(self.offline_sync_radio)
        
        sync_mode_layout.addStretch(1)
        settings_layout.addLayout(sync_mode_layout)
        
        # Add sync precision option
        precision_layout = QHBoxLayout()
        precision_layout.addWidget(QLabel("Synchronization Precision (ms):"))
        
        self.sync_precision_combo = QComboBox()
        self.sync_precision_combo.addItems(["1", "5", "10", "25", "50", "100"])
        self.sync_precision_combo.setCurrentIndex(2)  # Default to 10ms
        precision_layout.addWidget(self.sync_precision_combo)
        
        precision_layout.addStretch(1)
        settings_layout.addLayout(precision_layout)
        
        # Add dataset format options
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Dataset Format:"))
        
        self.dataset_format_combo = QComboBox()
        self.dataset_format_combo.addItems(["HDF5", "EDF+", "CSV", "BIDS"])
        format_layout.addWidget(self.dataset_format_combo)
        
        format_layout.addStretch(1)
        settings_layout.addLayout(format_layout)
        
        sync_layout.addWidget(settings_group)
        
        # Create LSL synchronizer widget
        self.lsl_sync_widget = LSLSynchronizerWidget()
        self.lsl_sync_widget.status_message.connect(self.show_status_message)
        sync_layout.addWidget(self.lsl_sync_widget)
        
        # Add to tabs
        self.tabs.addTab(self.sync_container, "LSL Synchronization")
    
    def _update_sync_mode(self):
        """Update synchronization mode based on radio button selection."""
        if self.realtime_sync_radio.isChecked():
            logging.info("Switching to real-time synchronization mode")
            # Update UI components for real-time mode
            if hasattr(self.lsl_sync_widget, 'set_realtime_mode'):
                self.lsl_sync_widget.set_realtime_mode(True)
        else:
            logging.info("Switching to offline synchronization mode")
            # Update UI components for offline mode
            if hasattr(self.lsl_sync_widget, 'set_realtime_mode'):
                self.lsl_sync_widget.set_realtime_mode(False)
    
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
        self.recording_started.connect(self._start_lsl_synchronization)
        self.recording_stopped.connect(self._stop_eeg_recording)
        self.recording_stopped.connect(self._stop_input_recording)
        self.recording_stopped.connect(self._stop_lsl_synchronization)
        
        # Hide/disable original recording buttons in EEG app
        if hasattr(self.eeg_processor_app, 'start_record_btn'):
            self.eeg_processor_app.start_record_btn.setVisible(False)
        if hasattr(self.eeg_processor_app, 'stop_record_btn'):
            self.eeg_processor_app.stop_record_btn.setVisible(False)
        
        # Hide record button in input collector app
        # First find the actual record button from the UI
        if hasattr(self.input_collector_app, 'record_button'):
            self.input_collector_app.record_button.setVisible(False)
        
        # Hide raw/processed radio buttons in EEG app since we control them from integrated app
        if hasattr(self.eeg_processor_app, 'raw_radio'):
            self.eeg_processor_app.raw_radio.setVisible(False)
        if hasattr(self.eeg_processor_app, 'processed_radio'):
            self.eeg_processor_app.processed_radio.setVisible(False)
        if hasattr(self.eeg_processor_app, 'both_radio'):
            self.eeg_processor_app.both_radio.setVisible(False)
            
        # Connect to input events to send to LSL in real-time
        if hasattr(self.input_collector_app, 'collector_manager'):
            # Hook directly into the collector's event system
            for collector_name, collector in self.input_collector_app.collector_manager.collectors.items():
                if hasattr(collector, 'on_event'):
                    collector.on_event(self._on_input_event)
                    logging.info(f"Connected LSL publisher to {collector_name} input events")
            
            # Also connect to the collector manager's active collector
            active_collector = self.input_collector_app.collector_manager.get_current_collector()
            if active_collector and hasattr(active_collector, 'on_event'):
                active_collector.on_event(self._on_input_event)
                logging.info(f"Connected LSL publisher to active collector input events")
    
    def _on_input_event(self, input_data):
        """Handle input events from collectors and send to LSL stream."""
        if self.input_publisher and self.is_synchronized:
            try:
                # Extract essential data from the input event
                event_data = {
                    'timestamp': input_data.timestamp,
                    'event_type': input_data.event_type,
                    'key': input_data.key if hasattr(input_data, 'key') else None,
                    'mouse_x': input_data.mouse_x if hasattr(input_data, 'mouse_x') else None,
                    'mouse_y': input_data.mouse_y if hasattr(input_data, 'mouse_y') else None,
                    'button_pressed': input_data.button_pressed if hasattr(input_data, 'button_pressed') else None,
                    'direction': input_data.direction if hasattr(input_data, 'direction') else None,
                    'active_keys': input_data.active_keys if hasattr(input_data, 'active_keys') else []
                }
                
                # Send to LSL stream
                if event_data['event_type'] != 'none':  # Skip empty/none events
                    self.input_publisher.send_event(event_data)
                    
                    # Create markers for special events (key presses, mouse clicks)
                    if self.marker_publisher:
                        if event_data['event_type'] == 'key_press':
                            self.marker_publisher.send_marker('key', event_data['key'])
                        elif event_data['event_type'] == 'mouse_click':
                            self.marker_publisher.send_marker('mouse', event_data['button_pressed'])
                
            except Exception as e:
                # Log error but don't crash
                logging.error(f"Error sending input event to LSL: {e}")
                import traceback
                traceback.print_exc()
    
    def _update_status(self):
        """Update status information."""
        # Update EEG status
        is_eeg_connected = False
        is_eeg_streaming = False
        
        # Check EEG collector connection status
        if hasattr(self.eeg_processor_app, 'collector_service') and self.eeg_processor_app.collector_service:
            has_collector = hasattr(self.eeg_processor_app.collector_service, 'collector') and self.eeg_processor_app.collector_service.collector is not None
            is_eeg_connected = has_collector
            
            # Check streaming status
            if has_collector and hasattr(self.eeg_processor_app, 'is_streaming'):
                is_eeg_streaming = self.eeg_processor_app.is_streaming
                
                # Initialize or update EEG publisher if streaming started
                if is_eeg_streaming and not self.eeg_publisher:
                    self._initialize_eeg_publisher()
        
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
    
    def _initialize_eeg_publisher(self):
        """Initialize the EEG publisher for LSL synchronization."""
        try:
            if hasattr(self.eeg_processor_app, 'collector_service') and self.eeg_processor_app.collector_service:
                collector = self.eeg_processor_app.collector_service.collector
                
                if collector:
                    # Get EEG board information
                    board_id = collector.get_board_id() if hasattr(collector, 'get_board_id') else 0
                    # Get a more descriptive device name and avoid "UnknownEEG"
                    device_name = "BrainFlow"
                    if hasattr(collector, 'get_device_name') and collector.get_device_name():
                        device_name = collector.get_device_name()
                    elif hasattr(collector, 'board_id'):
                        # Try to get a better name based on board_id
                        from brainflow.board_shim import BoardShim
                        try:
                            board_descr = BoardShim.get_board_descr(collector.board_id)
                            if board_descr and 'name' in board_descr:
                                device_name = board_descr['name']
                        except:
                            pass
                    
                    # Get actual sampling rate from the headset
                    sampling_rate = collector.get_sampling_rate() if hasattr(collector, 'get_sampling_rate') else 250.0
                    num_channels = collector.get_eeg_channel_count() if hasattr(collector, 'get_eeg_channel_count') else 8
                    
                    # Log the actual sampling rate
                    logging.info(f"EEG device sampling rate: {sampling_rate} Hz")
                    
                    # Create better channel names if available
                    channel_names = None
                    if hasattr(collector, 'get_eeg_names'):
                        channel_names = collector.get_eeg_names()
                        
                    # Create EEG publisher with improved naming
                    from lsl_synchronizer import create_eeg_publisher
                    self.eeg_publisher = create_eeg_publisher(
                        device_name=device_name,
                        board_id=board_id,
                        num_channels=num_channels,
                        sampling_rate=sampling_rate
                    )
                    
                    logging.info(f"Initialized EEG LSL publisher for {device_name} with {num_channels} channels at {sampling_rate}Hz")
                    
                    # Register a data callback on the collector to receive EEG data
                    if hasattr(collector, 'register_data_callback'):
                        collector.register_data_callback(self._on_eeg_data)
                        logging.info("Registered EEG data callback")
                    
                    # Register a processing callback on the processor service if available
                    if hasattr(self.eeg_processor_app, 'processor_service') and self.eeg_processor_app.processor_service:
                        # This is a hack to intercept processed data - normally would use a proper event system
                        original_apply_all_filters = self.eeg_processor_app.processor_service.apply_all_filters
                        
                        def intercepted_apply_filters(data, filters_config):
                            result = original_apply_all_filters(data, filters_config)
                            # Send processed data to LSL
                            try:
                                if self.is_synchronized and self.eeg_publisher:
                                    # Only send when synchronized and publisher exists
                                    if isinstance(result, tuple) and len(result) > 0:
                                        self.eeg_publisher.send_eeg_data(result[0])
                                        logging.debug(f"Sent processed EEG data to LSL")
                                    elif hasattr(result, 'shape'):
                                        self.eeg_publisher.send_eeg_data(result)
                                        logging.debug(f"Sent processed EEG data to LSL")
                            except Exception as e:
                                logging.error(f"Error sending processed EEG data to LSL: {e}")
                            return result
                        
                        # Replace the original method with our interceptor
                        self.eeg_processor_app.processor_service.apply_all_filters = intercepted_apply_filters
                        logging.info("Intercepted filter application for LSL publishing")
                        
                    # Set up a timer to periodically fetch and send data to ensure continuous flow
                    # Calculate optimal timer interval based on the headset's sampling rate
                    # We'll use a timer interval that gives us about 10 samples per batch
                    # to balance between latency and efficiency
                    samples_per_batch = 10
                    timer_interval_ms = max(4, int(1000 / (sampling_rate / samples_per_batch)))
                    
                    # Create and start the timer
                    self.eeg_data_timer = QTimer(self)
                    self.eeg_data_timer.timeout.connect(self._fetch_and_send_eeg_data)
                    self.eeg_data_timer.start(timer_interval_ms)
                    
                    logging.info(f"Established EEG data timer for LSL streaming at {1000/timer_interval_ms:.1f} Hz")
                    logging.info(f"Expected samples per batch: ~{samples_per_batch}")
                else:
                    logging.warning("Cannot initialize EEG publisher: No collector available")
        
        except Exception as e:
            logging.error(f"Error initializing EEG publisher: {e}")
            import traceback
            traceback.print_exc()
    
    def _fetch_and_send_eeg_data(self):
        """Periodically fetch and send EEG data to the LSL stream."""
        if not self.is_synchronized or not self.eeg_publisher:
            return
            
        try:
            # Only proceed if we have the required services and they're accessible
            if (hasattr(self.eeg_processor_app, 'collector_service') and 
                    self.eeg_processor_app.collector_service and 
                    self.eeg_processor_app.collector_service.collector):
                
                collector = self.eeg_processor_app.collector_service.collector
                
                # Get the most recent EEG data (about 250ms worth)
                sampling_rate = collector.get_sampling_rate() if hasattr(collector, 'get_sampling_rate') else 250
                samples_to_get = int(sampling_rate * 0.25)  # 250ms worth of data
                
                # Ensure we get at least one sample
                if samples_to_get < 1:
                    samples_to_get = 1
                
                data = None
                timestamps = None
                
                if hasattr(collector, 'get_current_board_data'):
                    # Try get_current_board_data method first
                    data = collector.get_current_board_data(samples_to_get)
                elif hasattr(collector, 'get_board_data'):
                    # Fall back to get_board_data
                    data = collector.get_board_data(samples_to_get)
                else:
                    # Try get_data which returns (data, timestamps)
                    try:
                        data, timestamps = collector.get_data(samples_to_get)
                    except Exception as e:
                        logging.debug(f"Error getting data: {e}")
                
                if data is not None and hasattr(data, 'size') and data.size > 0:
                    # Make sure data is 2D
                    if len(data.shape) == 1:
                        # Single sample, reshape to 2D
                        data = data.reshape(-1, 1)  # Channels x 1 sample
                    
                    # Get EEG channels if possible
                    eeg_channels = None
                    if hasattr(collector, 'get_eeg_channels'):
                        try:
                            eeg_channels = collector.get_eeg_channels()
                        except:
                            pass
                    
                    # If we have EEG channels, extract only those channels
                    if eeg_channels is not None:
                        # Check if we need to extract specific channels
                        if len(eeg_channels) < data.shape[0]:
                            # Extract only EEG channels
                            data = data[eeg_channels, :]
                    
                    # Send each sample to LSL
                    if len(data.shape) == 2:
                        # For multiple samples (channels x samples), send each sample
                        num_samples = data.shape[1]
                        
                        if num_samples > 0:
                            if num_samples == 1:
                                # Single sample case
                                sample = data[:, 0]
                                self.eeg_publisher.send_eeg_data(sample)
                                logging.debug(f"Sent single EEG sample: shape {sample.shape}")
                            else:
                                # More efficient to send as chunk for multiple samples
                                # Note: LSL expects (samples x channels) but BrainFlow gives (channels x samples)
                                # So we need to transpose
                                chunk_data = data.T  # Transpose to (samples x channels)
                                self.eeg_publisher.send_eeg_chunk(chunk_data)
                                logging.debug(f"Sent EEG data chunk: shape {chunk_data.shape}")
                                
                        # Log occasionally to indicate data is flowing
                        if hasattr(self, '_last_eeg_log_time'):
                            if time.time() - self._last_eeg_log_time > 5.0:  # Log every 5 seconds
                                logging.info(f"Streaming EEG data to LSL: {data.shape[0]} channels, {num_samples} samples")
                                self._last_eeg_log_time = time.time()
                        else:
                            self._last_eeg_log_time = time.time()
                            logging.info(f"Started streaming EEG data to LSL")
        
        except Exception as e:
            # Log errors but don't crash
            logging.error(f"Error in EEG data timer: {e}")
    
    def _on_eeg_data(self, data, timestamp=None):
        """Callback for EEG data to send to LSL."""
        if self.eeg_publisher and self.is_synchronized:
            try:
                # Log that the callback was triggered
                logging.debug(f"EEG data callback triggered with data shape: {data.shape if hasattr(data, 'shape') else 'unknown'}")
                
                # Send data to LSL stream - make sure data is not empty
                if data is not None and hasattr(data, 'size') and data.size > 0:
                    self.eeg_publisher.send_eeg_data(data, timestamp)
            except Exception as e:
                # Log error but don't raise to avoid disrupting the EEG processor
                logging.error(f"Error sending EEG data to LSL: {e}")
                import traceback
                traceback.print_exc()
    
    def toggle_recording(self):
        """Toggle recording state for both EEG and input collection."""
        if not self.is_recording:
            # Start recording
            if not self.eeg_ready:
                QMessageBox.warning(self, "Cannot Start Recording",
                                   "EEG must be connected and streaming before recording can start.")
                return
                
            # Create recordings directory for this session
            session_timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.session_dir = os.path.join(self.recordings_dir, f"session_{session_timestamp}")
            os.makedirs(self.session_dir, exist_ok=True)
            logging.info(f"Created session directory: {self.session_dir}")
            
            self.is_recording = True
            self.record_button.setText("Stop Recording")
            self.record_button.setStyleSheet("background-color: #CC3333;")
            self.record_status_label.setText("RECORDING")
            
            # Start session timer
            self.session_start_time = time.time()
            self.session_timer.start()
            
            # Emit signal to start recording in both modules
            self.recording_started.emit()
            
            logging.info("Recording started")
            
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
            
            logging.info("Recording stopped")
            
            # Show message about where recordings were saved
            if hasattr(self, 'session_dir') and os.path.exists(self.session_dir):
                QMessageBox.information(self, "Recording Complete", 
                                      f"Recordings have been saved to:\n{self.session_dir}")
    
    def _start_eeg_recording(self):
        """Start recording in the EEG processor app."""
        if not self.save_eeg_check.isChecked():
            logging.info("EEG recording disabled by user")
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
            
            # Save to session directory if available
            if hasattr(self, 'session_dir') and os.path.exists(self.session_dir):
                # Use the base path from the UI and add timestamp
                base_path = os.path.splitext(self.record_file_edit.text())[0]
                filename = os.path.join(self.session_dir, f"{os.path.basename(base_path)}_eeg_{timestamp}.csv")
            else:
                # Use the base path from the UI and add timestamp
                base_path = os.path.splitext(self.record_file_edit.text())[0]
                filename = f"{base_path}_eeg_{timestamp}.csv"
            
            # Set the filename in the EEG processor app record_file_edit if exists
            if hasattr(self.eeg_processor_app, 'record_file_edit'):
                self.eeg_processor_app.record_file_edit.setText(filename)
            
            # Determine data type based on radio buttons
            data_type = "raw"
            if self.eeg_processed_radio.isChecked():
                data_type = "processed"
            elif self.eeg_both_radio.isChecked():
                data_type = "both"
            
            # Start recording using the collector directly
            if hasattr(self.eeg_processor_app, 'collector'):
                self.eeg_processor_app.collector.start_continuous_recording(filename, data_type)
                
                # Log appropriate message based on data type
                if data_type == "both":
                    logging.info(f"Started EEG recording to {filename} (both raw and processed data)")
                else:
                    logging.info(f"Started EEG recording to {filename} ({data_type} data)")
            else:
                logging.error("Failed to start EEG recording: No collector available")
            
        except Exception as e:
            logging.error(f"Error starting EEG recording: {e}")
            import traceback
            traceback.print_exc()
    
    def _stop_eeg_recording(self):
        """Stop recording in the EEG processor app."""
        try:
            # Stop recording using the collector directly
            if hasattr(self.eeg_processor_app, 'collector'):
                if hasattr(self.eeg_processor_app.collector, 'stop_continuous_recording'):
                    self.eeg_processor_app.collector.stop_continuous_recording()
                    logging.info("Stopped EEG recording")
                else:
                    logging.error("EEG collector does not have stop_continuous_recording method")
            else:
                logging.error("Failed to stop EEG recording: No collector available")
            
        except Exception as e:
            logging.error(f"Error stopping EEG recording: {e}")
            import traceback
            traceback.print_exc()
    
    def _start_input_recording(self):
        """Start recording in the input collector app."""
        if not self.save_input_check.isChecked():
            logging.info("Input recording disabled by user")
            return
            
        try:
            # Generate a timestamp for the filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            # Save to session directory if available
            if hasattr(self, 'session_dir') and os.path.exists(self.session_dir):
                base_path = os.path.splitext(self.record_file_edit.text())[0]
                filename_base = os.path.join(self.session_dir, os.path.basename(base_path))
            else:
                base_path = os.path.splitext(self.record_file_edit.text())[0]
                filename_base = base_path
            
            # Set up JSON logging if enabled
            if self.input_json_check.isChecked():
                json_filename = f"{filename_base}_input_{timestamp}.json"
                
                # Enable JSON logging with LSL integration
                if hasattr(self.input_collector_app, 'logging_manager'):
                    self.input_collector_app.logging_manager.set_json_logging(True)
                    self.input_collector_app.logging_manager.json_logger.set_filepath(json_filename)
                    
                    # Register LSL callback with JSON logger
                    self.input_collector_app.logging_manager.json_logger.set_lsl_publisher(self.input_publisher)
                
                logging.info(f"Input JSON logging to: {json_filename}")
            else:
                # Disable JSON logging
                if hasattr(self.input_collector_app, 'logging_manager'):
                    self.input_collector_app.logging_manager.set_json_logging(False)
            
            # Set up CSV logging if enabled
            if self.input_csv_check.isChecked():
                csv_filename = f"{filename_base}_input_{timestamp}.csv"
                
                # Enable CSV logging with LSL integration
                if hasattr(self.input_collector_app, 'logging_manager'):
                    self.input_collector_app.logging_manager.set_csv_logging(True)
                    self.input_collector_app.logging_manager.csv_logger.set_filepath(csv_filename)
                    
                    # Register LSL callback with CSV logger
                    self.input_collector_app.logging_manager.csv_logger.set_lsl_publisher(self.input_publisher)
                
                logging.info(f"Input CSV logging to: {csv_filename}")
            else:
                # Disable CSV logging
                if hasattr(self.input_collector_app, 'logging_manager'):
                    self.input_collector_app.logging_manager.set_csv_logging(False)
            
            # Start recording in input collector
            if hasattr(self.input_collector_app, 'app_coordinator'):
                # Use app coordinator to start recording
                self.input_collector_app.app_coordinator.start_recording()
                logging.info("Started input recording via coordinator")
            elif hasattr(self.input_collector_app, 'toggle_recording'):
                # Direct method call if available
                self.input_collector_app.toggle_recording()
                logging.info("Started input recording via direct method")
            else:
                logging.debug("Could not find recording method in input collector")
            
        except Exception as e:
            logging.error(f"Error starting input recording: {e}")
            import traceback
            traceback.print_exc()
    
    def _stop_input_recording(self):
        """Stop recording in the input collector app."""
        try:
            # Stop recording in input collector
            if hasattr(self.input_collector_app, 'app_coordinator'):
                # Use app coordinator to stop recording
                self.input_collector_app.app_coordinator.stop_recording()
                logging.info("Stopped input recording via coordinator")
            elif hasattr(self.input_collector_app, 'toggle_recording') and self.input_collector_app.is_recording:
                # Direct method call if available and currently recording
                self.input_collector_app.toggle_recording()
                logging.info("Stopped input recording via direct method")
            else:
                logging.debug("Could not find recording stop method in input collector")
            
            # Wait a moment for recording to complete
            QApplication.processEvents()
            
            # Disable logging if it was enabled
            if hasattr(self.input_collector_app, 'logging_manager'):
                # Unregister LSL callbacks
                if hasattr(self.input_collector_app.logging_manager, 'json_logger'):
                    self.input_collector_app.logging_manager.json_logger.set_lsl_publisher(None)
                if hasattr(self.input_collector_app.logging_manager, 'csv_logger'):
                    self.input_collector_app.logging_manager.csv_logger.set_lsl_publisher(None)
            
        except Exception as e:
            logging.error(f"Error stopping input recording: {e}")
            import traceback
            traceback.print_exc()
    
    def _start_lsl_synchronization(self):
        """Start LSL synchronization for recording."""
        try:
            # Set synchronization flag
            self.is_synchronized = True
            
            # Start data collection in LSL receiver
            sync_window_ms = int(self.sync_precision_combo.currentText())
            sync_window_sec = sync_window_ms / 1000.0
            
            self.lsl_receiver.start_collection(buffer_duration=60.0)  # Keep 1 minute of data in buffer
            
            # If using the LSL sync widget, update its state
            if hasattr(self, 'lsl_sync_widget'):
                self.lsl_sync_widget.start_synchronization()
            
            # Create a marker indicating recording start
            if self.marker_publisher:
                self.marker_publisher.send_marker("recording", "start")
            
            logging.info(f"LSL synchronization started with {sync_window_ms}ms precision window")
            
        except Exception as e:
            logging.error(f"Error starting LSL synchronization: {e}")
            self.is_synchronized = False
    
    def _stop_lsl_synchronization(self):
        """Stop LSL synchronization and export synchronized dataset."""
        try:
            # Create a marker indicating recording stop
            if self.marker_publisher:
                self.marker_publisher.send_marker("recording", "stop")
            
            # Clear synchronization flag
            self.is_synchronized = False
            
            # Get format for dataset export
            export_format = self.dataset_format_combo.currentText()
            
            # Generate timestamp for filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            # Export synchronized data
            if hasattr(self, 'session_dir'):
                if export_format == "HDF5":
                    filename = os.path.join(self.session_dir, f"synchronized_data_{timestamp}.h5")
                    
                    # Add metadata about the recording
                    metadata = {
                        'timestamp': timestamp,
                        'eeg_device': self.eeg_publisher.device_name if self.eeg_publisher else "Unknown",
                        'sync_precision_ms': self.sync_precision_combo.currentText()
                    }
                    
                    success = self.dataset_exporter.export_to_hdf5(filename, metadata)
                    if success:
                        logging.info(f"Exported synchronized data to HDF5: {filename}")
                    else:
                        logging.error("Failed to export synchronized data to HDF5")
                
                elif export_format == "CSV":
                    eeg_filename = os.path.join(self.session_dir, f"synchronized_eeg_{timestamp}.csv")
                    events_filename = os.path.join(self.session_dir, f"synchronized_events_{timestamp}.csv")
                    
                    success = self.dataset_exporter.export_to_csv(eeg_filename, events_filename)
                    if success:
                        logging.info(f"Exported synchronized data to CSV: {eeg_filename} and {events_filename}")
                    else:
                        logging.error("Failed to export synchronized data to CSV")
                
                elif export_format == "EDF+":
                    filename = os.path.join(self.session_dir, f"synchronized_eeg_{timestamp}.edf")
                    
                    success = self.dataset_exporter.export_to_edf(filename)
                    if success:
                        logging.info(f"Exported synchronized data to EDF+: {filename}")
                    else:
                        logging.error("Failed to export synchronized data to EDF+")
                
                elif export_format == "BIDS":
                    logging.warning("BIDS export not fully implemented yet, falling back to HDF5")
                    filename = os.path.join(self.session_dir, f"synchronized_data_{timestamp}.h5")
                    
                    success = self.dataset_exporter.export_to_hdf5(filename)
                    if success:
                        logging.info(f"Exported synchronized data to HDF5: {filename}")
                    else:
                        logging.error("Failed to export synchronized data to HDF5")
            
            # Stop the LSL receiver
            self.lsl_receiver.stop_collection()
            
            # If using the LSL sync widget, update its state
            if hasattr(self, 'lsl_sync_widget'):
                self.lsl_sync_widget.stop_synchronization()
            
            logging.info("LSL synchronization stopped and data exported")
            
        except Exception as e:
            logging.error(f"Error stopping LSL synchronization: {e}")
            import traceback
            traceback.print_exc()
    
    def _ensure_input_log_file(self):
        """Ensure that the input collector has a log file open."""
        try:
            if not hasattr(self.input_collector_app, 'log_file') or not self.input_collector_app.log_file:
                # Create timestamp for filename
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(self.recordings_dir, f"input_recording_{timestamp}.json")
                
                # Force log file creation
                self.input_collector_app.log_to_file = True
                self.input_collector_app.log_file = open(filename, "w")
                logging.info(f"Created input log file: {filename}")
        except Exception as e:
            logging.error(f"Error creating input log file: {e}")
            import traceback
            traceback.print_exc()
    
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
    
    def show_status_message(self, message):
        """Show a status message in the status bar."""
        self.statusBar().showMessage(message)
    
    def closeEvent(self, event):
        """Handle application close event."""
        # Stop recording if active
        if self.is_recording:
            self.toggle_recording()
        
        # Stop LSL synchronization if active
        if self.is_synchronized:
            self._stop_lsl_synchronization()
            
        # Close EEG connection if active
        if self.is_eeg_connected:
            try:
                if hasattr(self.eeg_processor_app, 'disconnect_board'):
                    self.eeg_processor_app.disconnect_board()
            except Exception as e:
                logging.error(f"Error disconnecting EEG board: {e}")
        
        # Accept the close event
        event.accept()
