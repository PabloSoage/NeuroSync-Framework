"""
Synchronization panel for the unified GUI.
"""
import logging
import time
from typing import Dict, Any, Optional

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
                device settings, and synchronization parameters to the export file. Recommended 
                for research and documentation purposes.</p>
                
                <p><b>Compress data:</b> Reduces file size by compressing the data. 
                Recommended for large datasets. Note that compression may slightly increase 
                export time but significantly reduces storage requirements.</p>
            """
        }

        return help_contents.get(
            topic, "<h3>Help</h3><p>No specific help available for this topic.</p>"
        )


class SynchronizationPanel(QWidget):
    """Panel for controlling data synchronization and dataset creation."""
    
    # Signals
    start_sync_requested = pyqtSignal(float)  # precision_ms
    stop_sync_requested = pyqtSignal()
    export_dataset_requested = pyqtSignal(dict)  # export parameters
    
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
        group = QGroupBox("Dataset Export")
        layout = QVBoxLayout(group)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Export Format:"))
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["HDF5", "EDF+", "BIDS"])
        format_layout.addWidget(self.format_combo)
        
        # Add help button for formats
        help_btn = HelpButton("export_formats")
        format_layout.addWidget(help_btn)
        
        format_layout.addStretch()
        layout.addLayout(format_layout)
        
        # Duration settings
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Export Duration:"))
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 3600)
        self.duration_spin.setValue(60)
        self.duration_spin.setSuffix(" seconds")
        duration_layout.addWidget(self.duration_spin)
        
        # Add help button for duration
        help_btn = HelpButton("export_duration")
        duration_layout.addWidget(help_btn)
        
        duration_layout.addWidget(QLabel("(last N seconds)"))
        duration_layout.addStretch()
        layout.addLayout(duration_layout)
        
        # File path selection
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Export Path:"))
        
        self.path_label = QLabel("No path selected")
        self.path_label.setStyleSheet("color: #888888;")
        path_layout.addWidget(self.path_label)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_export_path)
        path_layout.addWidget(self.browse_btn)
        
        layout.addLayout(path_layout)
        
        # Export options
        options_layout = QHBoxLayout()
        
        self.include_metadata_cb = QCheckBox("Include metadata")
        self.include_metadata_cb.setChecked(True)
        options_layout.addWidget(self.include_metadata_cb)
        
        self.compress_data_cb = QCheckBox("Compress data")
        self.compress_data_cb.setChecked(True)
        options_layout.addWidget(self.compress_data_cb)
        
        # Add help button for options
        help_btn = HelpButton("export_options")
        options_layout.addWidget(help_btn)
        
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # Export button
        self.export_btn = QPushButton("Export Dataset")
        self.export_btn.clicked.connect(self.export_dataset)
        self.export_btn.setEnabled(False)
        layout.addWidget(self.export_btn)
        
        # Export progress
        self.export_progress = QProgressBar()
        self.export_progress.setVisible(False)
        layout.addWidget(self.export_progress)
        
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
        precision = self.precision_spin.value()
        self.start_sync_requested.emit(precision)
    
    def stop_synchronization(self) -> None:
        """Stop synchronization."""
        self.stop_sync_requested.emit()
    
    def browse_export_path(self) -> None:
        """Browse for export file path."""
        format_name = self.format_combo.currentText().lower()
        
        # Set file filter based on format
        filters = {
            'hdf5': "HDF5 files (*.h5 *.hdf5)",
            'edf+': "EDF+ files (*.edf)",
            'bids': "All files (*)"
        }
        
        file_filter = filters.get(format_name, "All files (*)")
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Select Export Location",
            self.last_export_path,
            file_filter
        )
        
        if filepath:
            self.last_export_path = filepath
            self.path_label.setText(filepath)
            self.path_label.setStyleSheet("color: #ffffff;")
            self.export_btn.setEnabled(self.is_synchronizing)
    
    def export_dataset(self) -> None:
        """Export synchronized dataset."""
        if not self.last_export_path:
            QMessageBox.warning(self, "Export Error", "Please select an export path first.")
            return
        
        export_params = {
            'format': self.format_combo.currentText().lower(),
            'filepath': self.last_export_path,
            'duration_seconds': self.duration_spin.value(),
            'include_metadata': self.include_metadata_cb.isChecked(),
            'compress_data': self.compress_data_cb.isChecked()
        }
        
        self.export_dataset_requested.emit(export_params)
    
    def on_sync_started(self) -> None:
        """Handle synchronization started."""
        self.is_synchronizing = True
        self.sync_start_time = time.time()
        
        self.start_sync_btn.setEnabled(False)
        self.stop_sync_btn.setEnabled(True)
        self.export_btn.setEnabled(bool(self.last_export_path))
        
        self.add_status_message("Synchronization started")
    
    def on_sync_stopped(self) -> None:
        """Handle synchronization stopped."""
        self.is_synchronizing = False
        self.sync_start_time = None
        
        self.start_sync_btn.setEnabled(True)
        self.stop_sync_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        
        self.add_status_message("Synchronization stopped")
    
    def on_export_started(self) -> None:
        """Handle export started."""
        self.export_progress.setVisible(True)
        self.export_progress.setRange(0, 0)  # Indeterminate
        self.export_btn.setEnabled(False)
        
        self.add_status_message("Dataset export started...")
    
    def on_export_finished(self, success: bool, message: str) -> None:
        """Handle export finished."""
        self.export_progress.setVisible(False)
        self.export_btn.setEnabled(self.is_synchronizing and bool(self.last_export_path))
        
        if success:
            self.add_status_message(f"Export completed: {message}")
            QMessageBox.information(self, "Export Success", "Dataset exported successfully!")
        else:
            self.add_status_message(f"Export failed: {message}")
            QMessageBox.warning(self, "Export Error", f"Export failed: {message}")
    
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