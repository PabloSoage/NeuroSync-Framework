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
    QTabWidget, QPushButton, QLabel, QGroupBox, QCheckBox, QSplitter, 
    QMessageBox, QFileDialog, QRadioButton
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPalette

# Import from EEG processor module
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "eeg_processor"))
from eeg_processor.python.eeg_processor_app import EEGProcessorApp

# Import from input collector module
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "input_collector"))
from input_collector.python.input_collector_app import InputCollectorApp

# Import our modules using absolute imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # Add parent directory to path
from bci_system.python.interfaces import IEEGModule, IInputModule
from bci_system.python.adapters import EEGModuleAdapter, InputModuleAdapter
from bci_system.python.managers import RecordingManager
from bci_system.python.events import EventSystem, EventTypes
from bci_system.python.ui import UIFactory


class IntegratedBCIApp(QMainWindow):
    """
    Integrated Brain-Computer Interface application.
    
    This class follows SOLID principles by:
    - Single Responsibility: Coordinates modules but delegates specific tasks
    - Open/Closed: Uses interfaces for extension without modification
    - Liskov Substitution: Works with any class implementing the module interfaces
    - Interface Segregation: Uses specific interfaces for different module types
    - Dependency Inversion: Depends on abstractions, not concrete implementations
    """
    
    def __init__(self):
        """Initialize the integrated application."""
        super().__init__()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        
        # Window properties
        self.setWindowTitle("BCI System")
        self.setGeometry(50, 50, 1400, 900)
        
        # Create event system
        self.events = EventSystem()
        
        # Create recordings directory
        self.recordings_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings")
        os.makedirs(self.recordings_dir, exist_ok=True)
        
        # Create recording manager
        self.recording_manager = RecordingManager(self.recordings_dir)
        
        # Set application style
        self._set_dark_theme()
        
        # Create and initialize modules
        self._init_modules()
        
        # Setup UI components
        self._init_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Status update timer
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(500)  # Update every 500ms
        
        # Session timer
        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self._update_session_time)
        self.session_timer.setInterval(1000)  # Update every second
        
        # Update initial status
        self._update_status()
        
        logging.info("Integrated BCI application initialized")
    
    def _set_dark_theme(self):
        """Set the application to use a dark theme."""
        palette = QPalette()
        
        # Set colors
        palette.setColor(QPalette.Window, QColor(UIFactory.DARK_BG))
        palette.setColor(QPalette.WindowText, QColor(UIFactory.TEXT_COLOR))
        palette.setColor(QPalette.Base, QColor(UIFactory.DARK_FRAME_BG))
        palette.setColor(QPalette.AlternateBase, QColor(UIFactory.DARK_BG))
        palette.setColor(QPalette.ToolTipBase, QColor(UIFactory.DARK_BG))
        palette.setColor(QPalette.ToolTipText, QColor(UIFactory.TEXT_COLOR))
        palette.setColor(QPalette.Text, QColor(UIFactory.TEXT_COLOR))
        palette.setColor(QPalette.Button, QColor(UIFactory.DARK_BG))
        palette.setColor(QPalette.ButtonText, QColor(UIFactory.TEXT_COLOR))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(UIFactory.ACCENT_COLOR))
        palette.setColor(QPalette.Highlight, QColor(UIFactory.ACCENT_COLOR))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        QApplication.setPalette(palette)
        
        # Set stylesheet for detailed control
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {UIFactory.DARK_BG}; color: {UIFactory.TEXT_COLOR}; }}
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
                color: {UIFactory.TEXT_COLOR};
            }}
            QPushButton {{
                background-color: {UIFactory.ACCENT_COLOR};
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
                background-color: {UIFactory.DARK_FRAME_BG};
                color: {UIFactory.TEXT_COLOR};
                border: 1px solid #444;
                padding: 2px;
                border-radius: 2px;
            }}
            QTextEdit {{ font-family: 'Consolas', monospace; }}
            QTabWidget::pane {{ 
                border: 1px solid #444;
                background: {UIFactory.DARK_BG};
                top: -1px;
            }}
            QTabBar::tab {{
                background: {UIFactory.DARK_FRAME_BG};
                color: {UIFactory.TEXT_COLOR};
                border: 1px solid #444;
                border-bottom-color: {UIFactory.DARK_BG}; 
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 120px;
                padding: 5px;
            }}
            QTabBar::tab:selected, QTabBar::tab:hover {{
                background: {UIFactory.ACCENT_COLOR};
            }}
            QTabBar::tab:selected {{
                border-bottom-color: {UIFactory.ACCENT_COLOR};
            }}
            QCheckBox::indicator {{
                width: 13px;
                height: 13px;
                border: 1px solid #444;
                border-radius: 2px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {UIFactory.ACCENT_COLOR};
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: {UIFactory.DARK_FRAME_BG};
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
                background: {UIFactory.DARK_FRAME_BG};
                height: 12px;
                margin: 0 12px 0 12px;
            }}
            QScrollBar::handle:horizontal {{
                background: #666;
                min-width: 20px;
                border-radius: 3px;
            }}
        """)
    
    def _init_modules(self):
        """Initialize application modules."""
        # Create module instances
        self.eeg_processor = EEGProcessorApp()
        self.input_collector = InputCollectorApp()
        
        # Create adapters
        self.eeg_module = EEGModuleAdapter(self.eeg_processor)
        self.input_module = InputModuleAdapter(self.input_collector)
        
        # Register modules with the recording manager
        self.recording_manager.register_module(self.eeg_module, {"enabled": True, "data_type": "raw"})
        self.recording_manager.register_module(self.input_module, {"enabled": True, "json": False, "csv": True})
        
        # Hide original recording buttons in EEG app
        if hasattr(self.eeg_processor, 'start_record_btn'):
            self.eeg_processor.start_record_btn.setVisible(False)
        if hasattr(self.eeg_processor, 'stop_record_btn'):
            self.eeg_processor.stop_record_btn.setVisible(False)
        
        # Hide raw/processed radio buttons in EEG app
        if hasattr(self.eeg_processor, 'raw_radio'):
            self.eeg_processor.raw_radio.setVisible(False)
        if hasattr(self.eeg_processor, 'processed_radio'):
            self.eeg_processor.processed_radio.setVisible(False)
        if hasattr(self.eeg_processor, 'both_radio'):
            self.eeg_processor.both_radio.setVisible(False)
        
        # Hide record button in input collector
        if hasattr(self.input_collector, 'record_button'):
            self.input_collector.record_button.setVisible(False)
            
        # Hide JSON and CSV checkboxes in input collector
        if hasattr(self.input_collector, 'log_checkbox'):
            self.input_collector.log_checkbox.setVisible(False)
        if hasattr(self.input_collector, 'csv_checkbox'):
            self.input_collector.csv_checkbox.setVisible(False)
        
        # Hide path field and browse button in input collector
        if hasattr(self.input_collector, 'csv_path_field'):
            self.input_collector.csv_path_field.setVisible(False)
        if hasattr(self.input_collector, 'csv_path_button'):
            self.input_collector.csv_path_button.setVisible(False)
        if hasattr(self.input_collector, 'csv_path_label'):
            self.input_collector.csv_path_label.setVisible(False)
    
    def _init_ui(self):
        """Initialize user interface components."""
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main layout
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create shared controls section
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
        # Use UI factory to create control panel
        control_group, control_layout = UIFactory.create_control_panel("BCI System Controls")
        
        # Status and controls layout
        status_layout = QHBoxLayout()
        
        # Connection status
        status_widget, _, self.status_labels = UIFactory.create_status_display({
            "EEG": "Not Connected",
            "Input": "Ready"
        })
        status_layout.addWidget(status_widget)
        status_layout.addStretch(1)
        
        # Set initial colors
        self.status_labels["EEG"].setStyleSheet(f"color: {UIFactory.WARNING_COLOR};")
        self.status_labels["Input"].setStyleSheet(f"color: {UIFactory.SUCCESS_COLOR};")
        
        # Recording controls
        record_widget, _, self.record_button, self.record_status_label = UIFactory.create_recording_controls()
        status_layout.addWidget(record_widget)
        
        # Connect record button
        self.record_button.clicked.connect(self.toggle_recording)
        
        # Session timer display
        timer_layout = QHBoxLayout()
        timer_layout.addWidget(QLabel("Session:"))
        self.session_timer_label = QLabel("00:00:00")
        timer_layout.addWidget(self.session_timer_label)
        status_layout.addLayout(timer_layout)
        
        control_layout.addLayout(status_layout)
        
        # Add file path selection controls
        _, file_layout, self.record_file_edit, self.browse_btn = UIFactory.create_file_selector(
            "Recording Directory:"
        )
        self.record_file_edit.setText(self.recordings_dir)
        self.browse_btn.clicked.connect(self.browse_record_path)
        control_layout.addLayout(file_layout)

        # Helper text to explain session folder creation
        session_info_label = QLabel("Recordings are saved in session folders within this directory")
        session_info_label.setStyleSheet("color: #999; font-size: 10px;")
        control_layout.addWidget(session_info_label)
        
        # Create options layout
        options_layout = QHBoxLayout()
        
        # EEG options
        eeg_options_group, eeg_options_layout, self.eeg_checkboxes = UIFactory.create_option_group(
            "EEG Options:", 
            {"save": "Save EEG Data", "visualize": "Show Visualizers"}
        )
        
        # Default checkboxes to checked
        for checkbox in self.eeg_checkboxes.values():
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._on_eeg_options_changed)
            
        # Add EEG data type radio buttons
        eeg_type_group, _, self.eeg_type_radios = UIFactory.create_radio_group(
            "Data Type:",
            {"raw": "Raw Data", "processed": "Processed Data", "both": "Both"}
        )
        self.eeg_type_radios["raw"].setChecked(True)
        
        # Connect radio button signals
        for radio in self.eeg_type_radios.values():
            radio.toggled.connect(self._on_eeg_data_type_changed)
            
        eeg_options_layout.addWidget(eeg_type_group)
        options_layout.addWidget(eeg_options_group)
        
        # Spacer
        options_layout.addSpacing(20)
        
        # Input options
        input_options_group, input_options_layout, self.input_checkboxes = UIFactory.create_option_group(
            "Input Options:", 
            {"save": "Save Input Data", "visualize": "Show Visualizers"}
        )
        
        # Default checkboxes to checked
        for checkbox in self.input_checkboxes.values():
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._on_input_options_changed)
        
        # Add input format options
        input_format_group, _, self.input_format_checkboxes = UIFactory.create_option_group(
            "Format:",
            {"json": "JSON", "csv": "CSV"}
        )
        self.input_format_checkboxes["csv"].setChecked(True)
        
        # Connect format checkbox signals
        for checkbox in self.input_format_checkboxes.values():
            checkbox.toggled.connect(self._on_input_format_changed)
        
        input_options_layout.addWidget(input_format_group)
        options_layout.addWidget(input_options_group)
        
        control_layout.addLayout(options_layout)
        
        # Add to parent layout
        parent_layout.addWidget(control_group)
    
    def _create_eeg_tab(self):
        """Create the EEG processor tab with scrollability."""
        # Create scrollable container for the EEG processor app
        eeg_scroll = UIFactory.create_scrollable_container(self.eeg_processor)
        
        # Add to tabs
        self.tabs.addTab(eeg_scroll, "EEG Processing")
    
    def _create_input_tab(self):
        """Create the input collector tab with scrollability."""
        # Create scrollable container for the input collector app
        input_scroll = UIFactory.create_scrollable_container(self.input_collector)
        
        # Add to tabs
        self.tabs.addTab(input_scroll, "Input Collection")
    
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
        
        # Placeholder for EEG visualization
        eeg_viz_placeholder = QLabel("EEG visualization will appear here when recording starts")
        eeg_viz_placeholder.setAlignment(Qt.AlignCenter)
        eeg_viz_placeholder.setStyleSheet(f"background-color: {UIFactory.DARK_FRAME_BG}; padding: 40px;")
        eeg_section_layout.addWidget(eeg_viz_placeholder)
        
        splitter.addWidget(eeg_section)
        
        # Lower section - can show minimized input visualization
        input_section = QWidget()
        input_section_layout = QVBoxLayout(input_section)
        input_section_layout.addWidget(QLabel("Input Visualization:"))
        
        # Placeholder for input visualization
        input_viz_placeholder = QLabel("Input visualization will appear here when recording starts")
        input_viz_placeholder.setAlignment(Qt.AlignCenter)
        input_viz_placeholder.setStyleSheet(f"background-color: {UIFactory.DARK_FRAME_BG}; padding: 40px;")
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
        if hasattr(self.eeg_processor, 'connect_btn'):
            self.eeg_processor.connect_btn.clicked.connect(self._on_eeg_connection_change)
        if hasattr(self.eeg_processor, 'disconnect_btn'):
            self.eeg_processor.disconnect_btn.clicked.connect(self._on_eeg_connection_change)
        if hasattr(self.eeg_processor, 'start_stream_btn'):
            self.eeg_processor.start_stream_btn.clicked.connect(self._on_eeg_stream_change)
        if hasattr(self.eeg_processor, 'stop_stream_btn'):
            self.eeg_processor.stop_stream_btn.clicked.connect(self._on_eeg_stream_change)

        # Subscribe to events
        self.events.subscribe(EventTypes.RECORDING_STARTED, self._on_recording_started)
        self.events.subscribe(EventTypes.RECORDING_STOPPED, self._on_recording_stopped)
        self.events.subscribe(EventTypes.EEG_CONNECTED, self._update_status)
        self.events.subscribe(EventTypes.EEG_DISCONNECTED, self._update_status)
        self.events.subscribe(EventTypes.EEG_STREAM_STARTED, self._update_status)
        self.events.subscribe(EventTypes.EEG_STREAM_STOPPED, self._update_status)
    
    def _on_eeg_options_changed(self, checked):
        """Handle changes to EEG options."""
        # Update recording manager options for EEG module
        eeg_options = self.recording_manager.module_options.get(self.eeg_module, {})
        eeg_options["enabled"] = self.eeg_checkboxes["save"].isChecked()
        self.recording_manager.set_module_options(self.eeg_module, eeg_options)
        
        # Toggle EEG visualizations if needed
        if self.eeg_checkboxes["visualize"].isChecked() != checked:
            self.eeg_module.show_visualization(self.eeg_checkboxes["visualize"].isChecked())
            
        # Emit event to notify other components
        self.events.emit(EventTypes.UI_SETTINGS_CHANGED)
    
    def _on_eeg_data_type_changed(self, checked):
        """Handle changes to EEG data type."""
        if not checked:
            # Only process when a radio button is checked
            return
            
        # Determine selected data type
        data_type = "raw"  # Default
        for key, radio in self.eeg_type_radios.items():
            if radio.isChecked():
                data_type = key
                break
                
        # Update recording manager options for EEG module
        eeg_options = self.recording_manager.module_options.get(self.eeg_module, {})
        eeg_options["data_type"] = data_type
        self.recording_manager.set_module_options(self.eeg_module, eeg_options)
        
        # Emit event to notify other components
        self.events.emit(EventTypes.UI_SETTINGS_CHANGED)
    
    def _on_input_options_changed(self, checked):
        """Handle changes to input options."""
        # Update recording manager options for input module
        input_options = self.recording_manager.module_options.get(self.input_module, {})
        input_options["enabled"] = self.input_checkboxes["save"].isChecked()
        self.recording_manager.set_module_options(self.input_module, input_options)
        
        # Toggle input visualizations if needed
        if self.input_checkboxes["visualize"].isChecked() != checked:
            self.input_module.show_visualization(self.input_checkboxes["visualize"].isChecked())
            
        # Emit event to notify other components
        self.events.emit(EventTypes.UI_SETTINGS_CHANGED)
    
    def _on_input_format_changed(self, checked):
        """Handle changes to input format options."""
        # Update recording manager options for input module
        input_options = self.recording_manager.module_options.get(self.input_module, {})
        input_options["json"] = self.input_format_checkboxes["json"].isChecked()
        input_options["csv"] = self.input_format_checkboxes["csv"].isChecked()
        self.recording_manager.set_module_options(self.input_module, input_options)
        
        # Emit event to notify other components
        self.events.emit(EventTypes.UI_SETTINGS_CHANGED)
    
    def browse_record_path(self):
        """Browse for a directory to save recordings."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Recording Directory", self.recordings_dir
        )
        
        if directory:
            # Update recording manager with new directory
            self.recording_manager.update_base_directory(directory)
            
            # Update UI
            self.recordings_dir = directory
            self.record_file_edit.setText(directory)
            
            logging.info(f"Recording directory set to: {directory}")
    
    def _update_status(self):
        """Update status information."""
        # Update EEG status
        eeg_status = "Not Connected"
        eeg_status_color = UIFactory.WARNING_COLOR
        
        if self.eeg_module.is_connected():
            if self.eeg_module.is_streaming():
                eeg_status = "Streaming"
                eeg_status_color = UIFactory.SUCCESS_COLOR
            else:
                eeg_status = "Connected"
                eeg_status_color = UIFactory.ACCENT_COLOR
                
        self.status_labels["EEG"].setText(eeg_status)
        self.status_labels["EEG"].setStyleSheet(f"color: {eeg_status_color};")
        
        # Update Input status
        input_status = "Ready"
        input_status_color = UIFactory.SUCCESS_COLOR
        
        if self.input_module.is_recording_active():
            input_status = "Recording"
            
        self.status_labels["Input"].setText(input_status)
        self.status_labels["Input"].setStyleSheet(f"color: {input_status_color};")
        
        # Update recording button
        self.record_button.setEnabled(self.eeg_module.is_streaming())
        
        # If recording is active, update session info and recording status
        if self.recording_manager.is_recording:
            session_info = self.recording_manager.get_session_info()
            self.record_status_label.setText("RECORDING")
            
            # If EEG stream stopped during recording, stop recording
            if not self.eeg_module.is_streaming() and self.eeg_module.is_connected():
                self.toggle_recording()
                QMessageBox.warning(
                    self, 
                    "Recording Stopped", 
                    "Recording has been stopped because EEG stream was disconnected."
                )
    
    def _update_session_time(self):
        """Update the session timer display."""
        if self.recording_manager.is_recording:
            session_info = self.recording_manager.get_session_info()
            elapsed = int(session_info["duration"])
            hours = elapsed // 3600
            minutes = (elapsed % 3600) // 60
            seconds = elapsed % 60
            self.session_timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def toggle_recording(self):
        """Toggle recording state."""
        if not self.recording_manager.is_recording:
            # Start recording
            if not self.eeg_module.is_streaming():
                QMessageBox.warning(
                    self, 
                    "Cannot Start Recording",
                    "EEG must be connected and streaming before recording can start."
                )
                return
                
            # Start recording
            if self.recording_manager.start_recording():
                self.record_button.setText("Stop Recording")
                self.record_button.setStyleSheet("background-color: #CC3333;")
                self.record_status_label.setText("RECORDING")
                
                # Start session timer
                self.session_timer.start()
                
                # Emit event
                self.events.emit(EventTypes.RECORDING_STARTED)
                
                logging.info("Recording started")
            else:
                QMessageBox.critical(
                    self, 
                    "Recording Error",
                    "Failed to start recording. Check the logs for details."
                )
                
        else:
            # Stop recording
            if self.recording_manager.stop_recording():
                self.record_button.setText("Start Recording")
                self.record_button.setStyleSheet("background-color: #228822;")
                self.record_status_label.setText("Not Recording")
                
                # Stop session timer
                self.session_timer.stop()
                self.session_timer_label.setText("00:00:00")
                
                # Emit event
                self.events.emit(EventTypes.RECORDING_STOPPED)
                
                # Show success message with session directory
                QMessageBox.information(
                    self, 
                    "Recording Complete", 
                    f"Recordings have been saved to:\n{self.recording_manager.session_directory}"
                )
                
                logging.info("Recording stopped")
            else:
                QMessageBox.warning(
                    self, 
                    "Recording Warning",
                    "Some errors occurred while stopping the recording. Check the logs for details."
                )
    
    def _on_recording_started(self):
        """Handle recording started event."""
        # Additional actions when recording starts
        pass
    
    def _on_recording_stopped(self):
        """Handle recording stopped event."""
        # Additional actions when recording stops
        pass
    
    def _on_eeg_connection_change(self):
        """Handle EEG connection state change."""
        # Check connection status and emit appropriate events
        if self.eeg_module.is_connected():
            self.events.emit(EventTypes.EEG_CONNECTED)
        else:
            self.events.emit(EventTypes.EEG_DISCONNECTED)
            
        # Update status
        self._update_status()
    
    def _on_eeg_stream_change(self):
        """Handle EEG streaming state change."""
        # Check streaming status and emit appropriate events
        if self.eeg_module.is_streaming():
            self.events.emit(EventTypes.EEG_STREAM_STARTED)
        else:
            self.events.emit(EventTypes.EEG_STREAM_STOPPED)
            
        # Update status
        self._update_status()
    
    def closeEvent(self, event):
        """Handle application close event."""
        # Stop recording if active
        if self.recording_manager.is_recording:
            self.recording_manager.stop_recording()
        
        # Disconnect from EEG device if connected
        if self.eeg_module.is_connected():
            self.eeg_module.disconnect_from_device()
        
        # Accept the close event
        event.accept()
