"""
Synchronization panel for the unified GUI.
"""
import logging
import time
from typing import Dict, Any, Optional
import os

from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QSpinBox, QDoubleSpinBox, QComboBox,
    QTextEdit, QProgressBar, QCheckBox, QFileDialog,
    QMessageBox, QFrame, QDialog, QTextBrowser
)


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

        # Style the button to make it look like a help icon
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
        dialog.setMinimumSize(500, 400)

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
            "sync_precision": """
                <h3>Synchronization Precision</h3>
                <p>Controls how precisely EEG and input data are aligned in time.</p>
                <p><b>Recommended precision values:</b></p>
                <ul>
                    <li><b>0.1-1ms:</b> Ultra-precise synchronization for specialized research. 
                    May cause data loss as time alignment becomes extremely strict.</li>
                    <li><b>1-10ms:</b> High precision for most research applications. 
                    Good balance between accuracy and reliability.</li>
                    <li><b>10-50ms:</b> Standard precision for BCI applications and general research.</li>
                    <li><b>50-100ms:</b> Minimum for reaction time studies and reliable correlation.</li>
                </ul>
                <p><b>Important:</b> Lower values ensure tighter synchronization but may result 
                in data loss if streams can't maintain precise timing. Higher values are more 
                forgiving but may include misaligned data.</p>
            """,
            "export_formats": """
                <h3>Export Formats</h3>
                <p>Select a format for exporting synchronized data:</p>
                <ul>
                    <li><b>HDF5:</b> Hierarchical data format. Best choice for large datasets 
                    and preserving data structure. Supports compression and metadata. 
                    Excellent for analysis with Python/MATLAB.</li>
                    
                    <li><b>EDF+:</b> European Data Format Plus. Clinical standard for EEG data. 
                    Excellent compatibility with medical and EEG analysis software. 
                    Supports annotations for events.</li>
                    
                    <li><b>BIDS:</b> Brain Imaging Data Structure. Best for sharing data and 
                    collaborative research. Creates standardized directory structure. 
                    Widely supported by neuroimaging tools.</li>
                </ul>
                <p><b>Recommended:</b> Use HDF5 for analysis, EDF+ for clinical applications, 
                or BIDS for data sharing.</p>
            """,
            "export_duration": """
                <h3>Export Duration</h3>
                <p>Specifies how many seconds of recent synchronized data to export.</p>
                <p>The system exports the most recent N seconds of data from when you click export.</p>
                <p><b>Considerations:</b></p>
                <ul>
                    <li>Longer durations include more context but create larger files</li>
                    <li>Shorter durations are more focused on recent events</li>
                    <li>Minimum recommended: 30 seconds for meaningful analysis</li>
                    <li>Maximum practical: depends on available memory and file size constraints</li>
                </ul>
            """,
            "sync_status": """
                <h3>Synchronization Status</h3>
                <p>This display shows real-time information about the synchronization process:</p>
                <ul>
                    <li><b>Sync Time:</b> How long synchronization has been running</li>
                    <li><b>Samples:</b> Number of synchronized data points collected</li>
                    <li><b>Quality:</b> Overall synchronization quality (0-100%)</li>
                </ul>
                <p><b>Quality indicators:</b></p>
                <ul>
                    <li>90-100%: Excellent synchronization</li>
                    <li>70-89%: Good synchronization</li>
                    <li>50-69%: Fair synchronization (check timing)</li>
                    <li>Below 50%: Poor synchronization (check connections)</li>
                </ul>
            """,
            "export_options": """
                <h3>Export Options</h3>
                <p><b>Include metadata:</b> Adds detailed information about the recording session, 
                device settings, and synchronization parameters to the export file. 
                <span style="color: #ff6666;"><b>Only available for HDF5, EDF, EDF+, and BIDS formats.</b></span></p>
                
                <p><b>Compress data:</b> Reduces file size by compressing the data. 
                <span style="color: #ff6666;"><b>Only available for HDF5 format.</b></span>
                Note that compression may slightly increase export time but significantly reduces storage requirements.</p>
                
                <p><b>Append to existing file:</b> Add data to existing file instead of overwriting. 
                <span style="color: #ff6666;"><b>Only available for HDF5 and CSV formats.</b></span></p>
                
                <p><b>Format capabilities:</b></p>
                <ul>
                    <li><b>HDF5:</b> Supports all options (metadata, compression, append)</li>
                    <li><b>EDF/EDF+:</b> Supports metadata only</li>
                    <li><b>BIDS:</b> Supports metadata only (creates directory structure)</li>
                    <li><b>CSV:</b> Supports append only (simple text format)</li>
                </ul>
            """,
        }

        return help_contents.get(
            topic, "<h3>Help</h3><p>No specific help available for this topic.</p>"
        )


class SynchronizationPanel(QWidget):
    """Panel for controlling data synchronization and dataset creation."""
    
    # Signals
    start_sync_requested = pyqtSignal(float)  # precision_ms
    stop_sync_requested = pyqtSignal()
    setup_recording_requested = pyqtSignal(dict)  # recording parameters
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize synchronization panel."""
        super().__init__(parent)
        
        # State tracking
        self.is_synchronizing = False
        self.sync_start_time = None
        self.last_export_path = ""
        
        self.setup_ui()
        self.setup_status_timer()
        
    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Synchronization controls
        sync_group = self.create_sync_controls()
        layout.addWidget(sync_group)
        
        # Dataset export controls
        export_group = self.create_export_controls()
        layout.addWidget(export_group)
        
        # Status display
        status_group = self.create_status_display()
        layout.addWidget(status_group)
        
        layout.addStretch()
        
        # Apply custom styling for disabled elements
        self._apply_disabled_styling()
    
    def _apply_disabled_styling(self) -> None:
        """Apply custom styling for disabled elements."""
        self.setStyleSheet("""
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
                border: 1px solid #444444;
            }
            QComboBox:disabled {
                background-color: #555555;
                color: #888888;
                border: 1px solid #444444;
            }
            QCheckBox:disabled {
                color: #888888;
            }
            QCheckBox::indicator:disabled {
                background-color: #555555;
                border: 1px solid #444444;
            }
            QDoubleSpinBox:disabled, QSpinBox:disabled {
                background-color: #555555;
                color: #888888;
                border: 1px solid #444444;
            }
        """)

    def create_sync_controls(self) -> QGroupBox:
        """Create synchronization control group."""
        group = QGroupBox("Data Synchronization")
        layout = QVBoxLayout(group)
        
        # Precision settings
        precision_layout = QHBoxLayout()
        precision_layout.addWidget(QLabel("Synchronization Precision:"))
        
        self.precision_spin = QDoubleSpinBox()
        self.precision_spin.setRange(0.1, 1000.0)
        self.precision_spin.setValue(1.0)
        self.precision_spin.setSuffix(" ms")
        self.precision_spin.setDecimals(1)
        precision_layout.addWidget(self.precision_spin)
        
        # Add help button for precision
        help_btn = HelpButton("sync_precision")
        precision_layout.addWidget(help_btn)
        
        precision_layout.addWidget(QLabel("(0.1-1000ms)"))
        precision_layout.addStretch()
        layout.addLayout(precision_layout)
        
        # Info label
        info_label = QLabel(
            "Lower precision values provide better temporal alignment but require more processing power."
        )
        info_label.setStyleSheet("color: #888888; font-style: italic;")
        layout.addWidget(info_label)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_sync_btn = QPushButton("Start Synchronization")
        self.start_sync_btn.clicked.connect(self.start_synchronization)
        self.start_sync_btn.setEnabled(False)  # Disabled until path selected
        button_layout.addWidget(self.start_sync_btn)
        
        self.stop_sync_btn = QPushButton("Stop Synchronization")
        self.stop_sync_btn.clicked.connect(self.stop_synchronization)
        self.stop_sync_btn.setEnabled(False)
        button_layout.addWidget(self.stop_sync_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        return group
    
    def create_export_controls(self) -> QGroupBox:
        """Create dataset export control group."""
        group = QGroupBox("Recording Settings")
        layout = QVBoxLayout(group)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Recording Format:"))
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["HDF5", "EDF", "EDF+", "BIDS", "CSV"])
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        format_layout.addWidget(self.format_combo)
        
        # Add help button for formats
        help_btn = HelpButton("export_formats")
        format_layout.addWidget(help_btn)
        
        format_layout.addStretch()
        layout.addLayout(format_layout)
        
        # File path selection (required before starting)
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Recording File:"))
        
        self.path_label = QLabel("No file selected (required to start)")
        self.path_label.setStyleSheet("color: #ff6666;")  # Red when not selected
        path_layout.addWidget(self.path_label)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_export_path)
        path_layout.addWidget(self.browse_btn)
        
        layout.addLayout(path_layout)
        
        # Recording options
        options_layout = QHBoxLayout()
        
        self.include_metadata_cb = QCheckBox("Include metadata")
        self.include_metadata_cb.setChecked(True)
        options_layout.addWidget(self.include_metadata_cb)
        
        self.compress_data_cb = QCheckBox("Compress data")
        self.compress_data_cb.setChecked(True)
        options_layout.addWidget(self.compress_data_cb)
        
        self.append_mode_cb = QCheckBox("Append to existing file")
        self.append_mode_cb.setChecked(False)
        self.append_mode_cb.setEnabled(False)  # Disabled by default
        self.append_mode_cb.setToolTip("Add data to existing file instead of overwriting")
        options_layout.addWidget(self.append_mode_cb)
        
        # Add help button for options
        help_btn = HelpButton("export_options")
        options_layout.addWidget(help_btn)
        
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # Recording info
        info_label = QLabel(
            "Data will be saved automatically during synchronization to the selected file."
        )
        info_label.setStyleSheet("color: #888888; font-style: italic;")
        layout.addWidget(info_label)
        
        # Format-specific info label
        self.format_info_label = QLabel("")
        self.format_info_label.setStyleSheet("color: #888888; font-style: italic;")
        layout.addWidget(self.format_info_label)
        
        # Current file size (during recording)
        self.file_size_label = QLabel("File size: 0 MB")
        self.file_size_label.setVisible(False)
        layout.addWidget(self.file_size_label)
        
        # Initialize format-specific settings
        self._update_format_specific_options()
        
        return group
    
    def create_status_display(self) -> QGroupBox:
        """Create status display group."""
        group = QGroupBox("Synchronization Status")
        layout = QVBoxLayout(group)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
                font-family: monospace;
            }
        """)
        layout.addWidget(self.status_text)
        
        # Statistics with help
        stats_layout = QHBoxLayout()
        
        self.sync_time_label = QLabel("Sync Time: 00:00:00")
        stats_layout.addWidget(self.sync_time_label)
        
        self.sample_count_label = QLabel("Samples: 0")
        stats_layout.addWidget(self.sample_count_label)
        
        self.sync_quality_label = QLabel("Quality: N/A")
        stats_layout.addWidget(self.sync_quality_label)
        
        # Add help button for status
        help_btn = HelpButton("sync_status")
        stats_layout.addWidget(help_btn)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        return group

    def setup_status_timer(self) -> None:
        """Set up status update timer."""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_display)
        self.status_timer.start(1000)  # Update every second
    
    def start_synchronization(self) -> None:
        """Start synchronization."""
        if not self.last_export_path:
            QMessageBox.warning(
                self, 
                "Recording File Required", 
                "Please select a recording file before starting synchronization."
            )
            return
        
        precision = self.precision_spin.value()
        
        # Prepare recording parameters
        recording_params = {
            'format': self.format_combo.currentText().lower(),
            'filepath': self.last_export_path,
            'include_metadata': self.include_metadata_cb.isChecked(),
            'compress_data': self.compress_data_cb.isChecked(),
            'append_mode': self.append_mode_cb.isChecked() and self.append_mode_cb.isEnabled()
        }
        
        # Emit setup first, then start (order matters!)
        self.setup_recording_requested.emit(recording_params)
        self.start_sync_requested.emit(precision)

    def stop_synchronization(self) -> None:
        """Stop synchronization."""
        self.stop_sync_requested.emit()
    
    def browse_export_path(self) -> None:
        """Browse for export file path using native OS dialog."""
        format_name = self.format_combo.currentText().lower()
        
        # Set file filter based on format
        filters = {
            'hdf5': "HDF5 files (*.h5 *.hdf5);;All files (*)",
            'edf': "EDF files (*.edf);;All files (*)",
            'edf+': "EDF+ files (*.edf);;All files (*)",
            'bids': "Directories",  # BIDS exports to directories
            'csv': "CSV files (*.csv);;All files (*)"
        }
        
        file_filter = filters.get(format_name, "All files (*)")
        
        # Use native dialog (remove DontUseNativeDialog option)
        if format_name == 'bids':
            # For BIDS, select a directory
            filepath = QFileDialog.getExistingDirectory(
                self,
                "Select BIDS Recording Directory",
                self.last_export_path or os.path.expanduser("~")
                # Remove options parameter to use native dialog
            )
        else:
            # For other formats, select a file - native dialog will add extension automatically
            filepath, selected_filter = QFileDialog.getSaveFileName(
                self,
                "Select Recording File Location",
                self.last_export_path or os.path.expanduser("~"),
                file_filter
                # Remove options parameter to use native dialog
            )
        
        if filepath:
            # Native dialog automatically adds extension if user doesn't specify one
            self.last_export_path = filepath
            
            # Update UI immediately
            self.path_label.setText(os.path.basename(filepath))
            self.path_label.setToolTip(filepath)
            self.path_label.setStyleSheet("color: #ffffff;")  # White when selected
            
            # Enable start button now that we have a path
            self.start_sync_btn.setEnabled(True)
            
            # Check if file exists for append mode (only for non-BIDS formats)
            if format_name not in ['bids']:
                if os.path.exists(filepath):
                    self.append_mode_cb.setEnabled(True)
                    self.append_mode_cb.setText(f"Append to existing file ({os.path.basename(filepath)})")
                else:
                    self.append_mode_cb.setEnabled(True)
                    self.append_mode_cb.setText("Append to existing file")
                    self.append_mode_cb.setChecked(False)
            else:
                # For BIDS, disable append mode
                self.append_mode_cb.setEnabled(False)
                self.append_mode_cb.setText("Append to existing file (not available for BIDS)")
                self.append_mode_cb.setChecked(False)

    def on_sync_started(self) -> None:
        """Handle synchronization started."""
        self.is_synchronizing = True
        self.sync_start_time = time.time()
        
        # Disable ALL controls during recording
        self.start_sync_btn.setEnabled(False)
        self.stop_sync_btn.setEnabled(True)
        self.browse_btn.setEnabled(False)
        self.format_combo.setEnabled(False)
        self.precision_spin.setEnabled(False)
        self.include_metadata_cb.setEnabled(False)
        self.compress_data_cb.setEnabled(False)
        self.append_mode_cb.setEnabled(False)
        
        # Show file size tracking
        self.file_size_label.setVisible(True)
        
        self.add_status_message(f"Recording started to: {os.path.basename(self.last_export_path)}")
        self.start_sync_btn.setText("Recording...")

    def on_sync_stopped(self) -> None:
        """Handle synchronization stopped."""
        self.is_synchronizing = False
        self.sync_start_time = None
        
        # Re-enable controls
        self.start_sync_btn.setEnabled(bool(self.last_export_path))
        self.start_sync_btn.setText("Start Synchronization")
        self.stop_sync_btn.setEnabled(False)
        self.browse_btn.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.precision_spin.setEnabled(True)
        
        # Re-enable format-specific controls
        self._update_format_specific_options()
        
        # Hide file size tracking
        self.file_size_label.setVisible(False)
        
        # Re-check append mode availability based on current format and file
        self._update_append_mode_availability()
        
        self.add_status_message("Recording stopped")

    def _update_append_mode_availability(self) -> None:
        """Update append mode checkbox availability based on current settings."""
        format_name = self.format_combo.currentText().lower()
        
        # Format-specific append support
        append_supported_formats = ['hdf5', 'csv']
        
        if format_name not in append_supported_formats:
            # Format doesn't support append mode
            self.append_mode_cb.setEnabled(False)
            self.append_mode_cb.setText(f"Append to existing file (not supported for {format_name.upper()})")
            self.append_mode_cb.setChecked(False)
            self.append_mode_cb.setStyleSheet("color: #666666;")
        elif self.last_export_path:
            # Enable for supported formats when path is selected
            self.append_mode_cb.setEnabled(True)
            self.append_mode_cb.setStyleSheet("")
            if os.path.exists(self.last_export_path):
                self.append_mode_cb.setText(f"Append to existing file ({os.path.basename(self.last_export_path)})")
            else:
                self.append_mode_cb.setText("Append to existing file")
        else:
            # No path selected
            self.append_mode_cb.setEnabled(False)
            self.append_mode_cb.setText("Append to existing file")
            self.append_mode_cb.setChecked(False)
            self.append_mode_cb.setStyleSheet("color: #666666;")

    def update_file_size(self, size_bytes: int) -> None:
        """Update file size display during recording."""
        if self.is_synchronizing:
            size_mb = size_bytes / (1024 * 1024)
            self.file_size_label.setText(f"File size: {size_mb:.1f} MB")

    def update_sync_status(self, status: Dict[str, Any]) -> None:
        """Update synchronization status display."""
        if status.get('active', False):
            sample_count = status.get('synchronized_samples', 0)
            self.sample_count_label.setText(f"Samples: {sample_count}")
            
            # Calculate sync quality
            quality = status.get('sync_quality', 0.0)
            self.sync_quality_label.setText(f"Quality: {quality:.1%}")
    
    def update_status_display(self) -> None:
        """Update status display."""
        if self.is_synchronizing and self.sync_start_time:
            elapsed = time.time() - self.sync_start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            
            self.sync_time_label.setText(f"Sync Time: {hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def add_status_message(self, message: str) -> None:
        """Add a timestamped status message."""
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
    
    def clear_status(self) -> None:
        """Clear status display."""
        self.status_text.clear()

    def _on_format_changed(self) -> None:
        """Handle format combo box change."""
        # Reset path and disable start button
        self.last_export_path = ""
        self.path_label.setText("No file selected (required to start)")
        self.path_label.setToolTip("")
        self.path_label.setStyleSheet("color: #ff6666;")
        self.start_sync_btn.setEnabled(False)
        
        # Update format-specific options
        self._update_format_specific_options()
        
        if not self.is_synchronizing:
            self._update_append_mode_availability()

    def _update_format_specific_options(self) -> None:
        """Update format-specific options and help text."""
        format_name = self.format_combo.currentText().lower()
        
        # Format-specific feature support
        format_features = {
            'hdf5': {
                'metadata': True,
                'compression': True,
                'append': True,
                'info': "HDF5 supports all features including compression and metadata."
            },
            'edf': {
                'metadata': True,
                'compression': False,
                'append': False,
                'info': "EDF format supports metadata but not compression or append mode."
            },
            'edf+': {
                'metadata': True,
                'compression': False,
                'append': False,
                'info': "EDF+ format supports metadata and events but not compression or append mode."
            },
            'bids': {
                'metadata': True,
                'compression': False,
                'append': False,
                'info': "BIDS creates a standardized directory structure with metadata files."
            },
            'csv': {
                'metadata': False,
                'compression': False,
                'append': True,
                'info': "CSV format is simple but doesn't support metadata or compression."
            }
        }
        
        features = format_features.get(format_name, {
            'metadata': False,
            'compression': False,
            'append': False,
            'info': "Unknown format capabilities."
        })
        
        # Update checkbox states and tooltips
        self.include_metadata_cb.setEnabled(features['metadata'])
        if not features['metadata']:
            self.include_metadata_cb.setChecked(False)
            self.include_metadata_cb.setToolTip("Metadata not supported for this format")
        else:
            self.include_metadata_cb.setToolTip("Include detailed recording metadata")
        
        self.compress_data_cb.setEnabled(features['compression'])
        if not features['compression']:
            self.compress_data_cb.setChecked(False)
            self.compress_data_cb.setToolTip("Compression not supported for this format")
        else:
            self.compress_data_cb.setToolTip("Compress data to reduce file size")
        
        # Update format info
        self.format_info_label.setText(features['info'])
        
        # Update visual styling for disabled checkboxes
        if not features['metadata']:
            self.include_metadata_cb.setStyleSheet("color: #666666;")
        else:
            self.include_metadata_cb.setStyleSheet("")
        
        if not features['compression']:
            self.compress_data_cb.setStyleSheet("color: #666666;")
        else:
            self.compress_data_cb.setStyleSheet("")

