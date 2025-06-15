from typing import Any, Optional, Dict
import logging
import base64
from io import BytesIO

from PyQt5 import QtCore
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QProgressBar,
    QTextEdit,
)
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap
import numpy as np

from .base_panel import BasePanel
from ..utils.help_system import HelpButton
from ..services.mne_service import MNEService

# Check if MNE is available
try:
    import mne
    MNE_AVAILABLE = True
except ImportError:
    MNE_AVAILABLE = False


class MNEPanel(BasePanel):
    """Panel for MNE integration and analysis."""

    # Custom signals for async operations
    conversion_completed = pyqtSignal(str, dict)  # task_id, result
    visualization_completed = pyqtSignal(str, dict)  # task_id, result

    def __init__(
        self,
        collector_service: Any,
        processor_service: Any,
        parent: Optional[Any] = None,
    ) -> None:
        """Initialize the MNE panel."""
        super().__init__(parent)
        self.collector_service = collector_service
        self.processor_service = processor_service
        
        # Get MNE service
        self.mne_service = MNEService.get_instance()
        
        # Current task tracking
        self.current_conversion_task: Optional[str] = None
        self.current_visualization_task: Optional[str] = None
        
        # Setup UI components
        if self.mne_service.is_available():
            self.setup_mne_conversion()
            self.setup_mne_visualization()
            self.setup_status_monitoring()
            
            # Start MNE service
            self.mne_service.start_service()
        else:
            self.setup_mne_not_available()

        # Connect signals
        self.conversion_completed.connect(self._on_conversion_completed)
        self.visualization_completed.connect(self._on_visualization_completed)

        # Setup timer for checking task status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._check_task_status)

        # Add stretch to push everything to the top
        self.layout.addStretch()

    def setup_mne_not_available(self) -> None:
        """Show warning when MNE is not installed."""
        warning_label = QLabel(
            "MNE package is not installed. Please install it using: pip install mne"
        )
        warning_label.setStyleSheet("color: #FFAA33; font-weight: bold;")
        self.layout.addWidget(warning_label)

    def setup_mne_conversion(self) -> None:
        """Set up MNE conversion section."""
        mne_group = QGroupBox("Convert to MNE Format")
        mne_layout = QVBoxLayout(mne_group)

        # Add help button for MNE
        mne_header_layout = QHBoxLayout()
        mne_header_layout.addWidget(QLabel("MNE Integration"))
        mne_header_layout.addWidget(HelpButton("mne", self))
        mne_header_layout.addStretch()
        mne_layout.addLayout(mne_header_layout)

        # Add description
        mne_layout.addWidget(
            QLabel("Convert BrainFlow data to MNE format for advanced analysis")
        )

        # MNE Parameters
        mne_params_layout = QHBoxLayout()
        mne_params_layout.addWidget(QLabel("Data Duration (seconds):"))
        self.mne_duration_spin = QSpinBox()
        self.mne_duration_spin.setRange(1, 60)
        self.mne_duration_spin.setValue(10)
        mne_params_layout.addWidget(self.mne_duration_spin)
        
        # Add unit conversion option
        mne_params_layout.addWidget(QLabel("Auto Convert to V:"))
        self.convert_to_v_check = QCheckBox()
        self.convert_to_v_check.setChecked(True)
        mne_params_layout.addWidget(self.convert_to_v_check)

        mne_layout.addLayout(mne_params_layout)

        # MNE Control buttons
        mne_buttons_layout = QHBoxLayout()

        self.convert_to_mne_btn = QPushButton("Convert to MNE")
        self.convert_to_mne_btn.clicked.connect(self.convert_to_mne)
        self.convert_to_mne_btn.setEnabled(False)
        mne_buttons_layout.addWidget(self.convert_to_mne_btn)

        self.cancel_conversion_btn = QPushButton("Cancel")
        self.cancel_conversion_btn.clicked.connect(self.cancel_conversion)
        self.cancel_conversion_btn.setEnabled(False)
        mne_buttons_layout.addWidget(self.cancel_conversion_btn)

        mne_layout.addLayout(mne_buttons_layout)

        # Progress bar for conversion
        self.conversion_progress = QProgressBar()
        self.conversion_progress.setVisible(False)
        mne_layout.addWidget(self.conversion_progress)

        self.layout.addWidget(mne_group)

    def setup_mne_visualization(self) -> None:
        """Set up MNE visualization section."""
        mne_viz_group = QGroupBox("MNE Visualization")
        mne_viz_layout = QVBoxLayout(mne_viz_group)

        # Plot selection
        plot_selection_layout = QHBoxLayout()
        plot_selection_layout.addWidget(QLabel("Plot Type:"))
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["PSD", "Topomap", "Raw Data", "Spectrogram"])
        plot_selection_layout.addWidget(self.plot_type_combo)
        
        # Frequency range for PSD
        plot_selection_layout.addWidget(QLabel("Freq Range:"))
        self.freq_min_spin = QSpinBox()
        self.freq_min_spin.setRange(1, 100)
        self.freq_min_spin.setValue(1)
        self.freq_min_spin.setSuffix(" Hz")
        plot_selection_layout.addWidget(self.freq_min_spin)
        
        self.freq_max_spin = QSpinBox()
        self.freq_max_spin.setRange(1, 100)
        self.freq_max_spin.setValue(50)
        self.freq_max_spin.setSuffix(" Hz")
        plot_selection_layout.addWidget(self.freq_max_spin)
        
        mne_viz_layout.addLayout(plot_selection_layout)

        mne_viz_buttons = QHBoxLayout()

        self.plot_mne_btn = QPushButton("Generate Plot")
        self.plot_mne_btn.clicked.connect(self.plot_mne_visualization)
        self.plot_mne_btn.setEnabled(False)
        mne_viz_buttons.addWidget(self.plot_mne_btn)

        self.cancel_plot_btn = QPushButton("Cancel Plot")
        self.cancel_plot_btn.clicked.connect(self.cancel_visualization)
        self.cancel_plot_btn.setEnabled(False)
        mne_viz_buttons.addWidget(self.cancel_plot_btn)

        mne_viz_layout.addLayout(mne_viz_buttons)

        # Progress bar for visualization
        self.plot_progress = QProgressBar()
        self.plot_progress.setVisible(False)
        mne_viz_layout.addWidget(self.plot_progress)

        # Plot display area with improved styling - use scaled contents to fill space
        self.plot_display = QLabel()
        self.plot_display.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        self.plot_display.setMinimumHeight(400)
        self.plot_display.setMinimumWidth(500)
        # Enable scaled contents to fill the available space
        self.plot_display.setScaledContents(True)
        self.plot_display.setAlignment(QtCore.Qt.AlignCenter)
        self.plot_display.setText("No plot generated yet")
        self.plot_display.setWordWrap(True)
        mne_viz_layout.addWidget(self.plot_display)

        self.layout.addWidget(mne_viz_group)

    def setup_status_monitoring(self) -> None:
        """Set up status monitoring section."""
        status_group = QGroupBox("Operation Status")
        status_layout = QVBoxLayout(status_group)

        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
                font-family: monospace;
            }
        """)
        status_layout.addWidget(self.status_text)

        self.layout.addWidget(status_group)

    def convert_to_mne(self) -> None:
        """Convert BrainFlow data to MNE format asynchronously."""
        if not self.mne_service.is_available():
            self.show_error("MNE Error", "MNE package is not installed")
            return

        try:
            # Get parameters
            duration_seconds = self.mne_duration_spin.value()
            convert_to_v = self.convert_to_v_check.isChecked()

            # Start conversion
            self.current_conversion_task = self.mne_service.convert_to_mne_async(
                duration_seconds=duration_seconds,
                convert_to_v=convert_to_v,
                callback=self._conversion_callback
            )

            # Update UI state
            self.convert_to_mne_btn.setEnabled(False)
            self.cancel_conversion_btn.setEnabled(True)
            self.conversion_progress.setVisible(True)
            self.conversion_progress.setRange(0, 0)  # Indeterminate progress

            # Start status monitoring
            self.status_timer.start(100)  # Check every 100ms

            self._add_status_message(f"Starting MNE conversion (Task: {self.current_conversion_task})")
            self.show_status("Converting data to MNE format...")

        except Exception as e:
            self.show_error("MNE Error", f"Error starting conversion: {str(e)}")
            logging.error(f"MNE conversion start error: {e}")

    def cancel_conversion(self) -> None:
        """Cancel the current MNE conversion."""
        if self.current_conversion_task:
            if self.mne_service.cancel_task(self.current_conversion_task):
                self._add_status_message(f"Cancelled conversion task: {self.current_conversion_task}")
                self.show_status("Conversion cancelled")
            else:
                self._add_status_message("Failed to cancel conversion task")

            self._reset_conversion_ui()
            self.current_conversion_task = None

    def plot_mne_visualization(self) -> None:
        """Create MNE visualization asynchronously."""
        if not self.current_conversion_task:
            self.show_error("MNE Error", "No MNE data available. Convert data first.")
            return

        # Check if conversion is complete
        status = self.mne_service.get_task_status(self.current_conversion_task)
        if not status.get("ready") or not status.get("successful"):
            self.show_error("MNE Error", "MNE conversion not complete or failed.")
            return

        try:
            # Get plot parameters
            plot_type = self.plot_type_combo.currentText()
            freq_min = self.freq_min_spin.value()
            freq_max = self.freq_max_spin.value()

            # Get current theme background color
            bg_color = "#2b2b2b"  # Dark theme background

            # Start visualization
            self.current_visualization_task = self.mne_service.create_visualization_async(
                task_id=self.current_conversion_task,
                plot_type=plot_type,
                freq_min=freq_min,
                freq_max=freq_max,
                bg_color=bg_color,
                callback=self._visualization_callback
            )

            # Update UI state
            self.plot_mne_btn.setEnabled(False)
            self.cancel_plot_btn.setEnabled(True)
            self.plot_progress.setVisible(True)
            self.plot_progress.setRange(0, 0)  # Indeterminate progress

            self._add_status_message(f"Starting {plot_type} visualization (Task: {self.current_visualization_task})")
            self.show_status(f"Generating {plot_type} visualization...")

        except Exception as e:
            self.show_error("MNE Error", f"Error starting visualization: {str(e)}")
            logging.error(f"MNE visualization start error: {e}")

    def cancel_visualization(self) -> None:
        """Cancel the current visualization."""
        if self.current_visualization_task:
            if self.mne_service.cancel_task(self.current_visualization_task):
                self._add_status_message(f"Cancelled visualization task: {self.current_visualization_task}")
                self.show_status("Visualization cancelled")
            else:
                self._add_status_message("Failed to cancel visualization task")

            self._reset_visualization_ui()
            self.current_visualization_task = None

    def _conversion_callback(self, task_id: str, result: Dict[str, Any]) -> None:
        """Callback for conversion completion (called from process)."""
        # Emit signal to update UI in main thread
        self.conversion_completed.emit(task_id, result)

    def _visualization_callback(self, task_id: str, result: Dict[str, Any]) -> None:
        """Callback for visualization completion (called from process)."""
        # Emit signal to update UI in main thread
        self.visualization_completed.emit(task_id, result)

    def _on_conversion_completed(self, task_id: str, result: Dict[str, Any]) -> None:
        """Handle conversion completion in main thread."""
        if result.get("success"):
            self._add_status_message(f"Conversion completed successfully: {task_id}")
            self.show_status(f"Converted {result.get('duration', 0)}s of data to MNE format ({result.get('channels', 0)} channels)")
            
            # Enable plot button
            self.plot_mne_btn.setEnabled(True)
        else:
            error_msg = result.get("error", "Unknown error")
            self._add_status_message(f"Conversion failed: {error_msg}")
            self.show_error("MNE Conversion Error", error_msg)

        self._reset_conversion_ui()

    def _on_visualization_completed(self, task_id: str, result: Dict[str, Any]) -> None:
        """Handle visualization completion in main thread."""
        if result.get("success"):
            self._add_status_message(f"Visualization completed: {task_id}")
            self.show_status(f"Generated {result.get('plot_type', '')} visualization")
            
            # Display the plot
            self._display_plot(result.get("plot_data"))
        else:
            error_msg = result.get("error", "Unknown error")
            self._add_status_message(f"Visualization failed: {error_msg}")
            self.show_error("MNE Visualization Error", error_msg)

        self._reset_visualization_ui()

    def _display_plot(self, plot_data: str) -> None:
        """Display the generated plot with proper scaling to fill available space."""
        if plot_data:
            try:
                # Decode base64 plot data
                image_data = base64.b64decode(plot_data)
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                
                if not pixmap.isNull():
                    # Get current display area size
                    display_size = self.plot_display.size()
                    
                    # Calculate the available area (minus padding and borders)
                    available_width = max(display_size.width() - 12, 300)  # Account for padding and border
                    available_height = max(display_size.height() - 12, 200)
                    
                    # Scale the pixmap to fill most of the available space while maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(
                        available_width,
                        available_height,
                        QtCore.Qt.KeepAspectRatio,
                        QtCore.Qt.SmoothTransformation
                    )
                    
                    # If the scaled image is still quite small compared to available space,
                    # scale it up more aggressively
                    if (scaled_pixmap.width() < available_width * 0.7 and 
                        scaled_pixmap.height() < available_height * 0.7):
                        
                        # Scale up to use at least 80% of available space
                        target_width = int(available_width * 0.9)
                        target_height = int(available_height * 0.9)
                        
                        scaled_pixmap = pixmap.scaled(
                            target_width,
                            target_height,
                            QtCore.Qt.KeepAspectRatio,
                            QtCore.Qt.SmoothTransformation
                        )
                    
                    # Set the scaled pixmap
                    self.plot_display.setPixmap(scaled_pixmap)
                    self.plot_display.setText("")  # Clear text
                    
                    # Since we're using setScaledContents(True), the label will automatically
                    # scale the image to fit its full size while maintaining aspect ratio
                    
                else:
                    self.plot_display.setText("Error: Could not load image data")
                
            except Exception as e:
                logging.error(f"Error displaying plot: {e}")
                self.plot_display.setText(f"Error displaying plot: {str(e)}")
        else:
            self.plot_display.setText("No plot data received")

    def _check_task_status(self) -> None:
        """Check status of active tasks."""
        # Update status of conversion task
        if self.current_conversion_task:
            status = self.mne_service.get_task_status(self.current_conversion_task)
            if status:
                self._add_status_message(f"Conversion task status: {status.get('status', 'unknown')}")
        
        # Update status of visualization task
        if self.current_visualization_task:
            status = self.mne_service.get_task_status(self.current_visualization_task)
            if status:
                self._add_status_message(f"Visualization task status: {status.get('status', 'unknown')}")
        
        # Stop timer if no active tasks
        if not self.current_conversion_task and not self.current_visualization_task:
            self.status_timer.stop()

    def _reset_conversion_ui(self) -> None:
        """Reset conversion UI elements."""
        self.convert_to_mne_btn.setEnabled(True)
        self.cancel_conversion_btn.setEnabled(False)
        self.conversion_progress.setVisible(False)

    def _reset_visualization_ui(self) -> None:
        """Reset visualization UI elements."""
        self.plot_mne_btn.setEnabled(True)
        self.cancel_plot_btn.setEnabled(False)
        self.plot_progress.setVisible(False)

    def _add_status_message(self, message: str) -> None:
        """Add a status message to the status text area."""
        if hasattr(self, 'status_text'):
            import time
            timestamp = time.strftime("%H:%M:%S")
            self.status_text.append(f"[{timestamp}] {message}")

    def enable_processing(self, enabled: bool) -> None:
        """Enable or disable MNE processing controls."""
        if hasattr(self, 'convert_to_mne_btn'):
            # Only enable if not currently processing
            if enabled and not self.current_conversion_task:
                self.convert_to_mne_btn.setEnabled(True)
            elif not enabled:
                self.convert_to_mne_btn.setEnabled(False)

        # Reset dependent buttons if disabling
        if not enabled:
            if hasattr(self, 'plot_mne_btn'):
                self.plot_mne_btn.setEnabled(False)
            self.current_conversion_task = None
            self.current_visualization_task = None

    # API compatibility methods
    def get_mne_settings(self) -> Dict[str, Any]:
        """Get current MNE settings."""
        if not self.mne_service.is_available():
            return {"available": False}

        return {
            "available": True,
            "duration": self.mne_duration_spin.value() if hasattr(self, "mne_duration_spin") else 10,
            "convert_to_v": self.convert_to_v_check.isChecked() if hasattr(self, "convert_to_v_check") else True,
            "plot_type": self.plot_type_combo.currentText() if hasattr(self, "plot_type_combo") else "PSD",
            "freq_range": [
                self.freq_min_spin.value() if hasattr(self, "freq_min_spin") else 1,
                self.freq_max_spin.value() if hasattr(self, "freq_max_spin") else 50
            ]
        }

    def update_mne_plot(self, plot_data: Dict[str, Any]) -> bool:
        """Update MNE plot from API call."""
        if not self.mne_service.is_available():
            return False

        try:
            plot_type = plot_data.get("type", "psd")
            
            if plot_type.lower() in ["psd", "topomap", "raw data", "spectrogram"]:
                # Set the combo box and trigger plotting
                if hasattr(self, 'plot_type_combo'):
                    index = self.plot_type_combo.findText(plot_type.title())
                    if index >= 0:
                        self.plot_type_combo.setCurrentIndex(index)
                        
                self.plot_mne_visualization()
                return True
            
            return False
            
        except Exception as e:
            self.show_error("MNE Plot Update Error", str(e))
            return False

    def closeEvent(self, event) -> None:
        """Handle panel close event."""
        # Cancel any active tasks
        if self.current_conversion_task:
            self.mne_service.cancel_task(self.current_conversion_task)
        if self.current_visualization_task:
            self.mne_service.cancel_task(self.current_visualization_task)
        
        # Stop timer
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()
        
        super().closeEvent(event)