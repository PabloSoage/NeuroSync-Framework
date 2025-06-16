from typing import Any, Optional, Dict, List, Tuple
import logging
import base64

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QPushButton, QSpinBox, QCheckBox, QComboBox, QProgressBar
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPixmap


class MNEVisualizationWidget(QWidget):
    """Widget specialized for MNE visualization operations."""
    
    # Signals
    visualization_requested = pyqtSignal(dict)  # Emit visualization parameters
    visualization_cancelled = pyqtSignal()
    channel_selection_requested = pyqtSignal(str)  # visualization
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the MNE visualization widget."""
        super().__init__(parent)
        self.setup_ui()
        self.reset_state()
        
    def setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        
        # Visualization group
        viz_group = QGroupBox("MNE Visualization")
        viz_layout = QVBoxLayout(viz_group)
        
        # Plot selection
        self._setup_plot_selection(viz_layout)
        
        # Topomap band selection
        self._setup_topomap_controls(viz_layout)
        
        # Channel selection
        self._setup_channel_selection(viz_layout)
        
        # PSD options
        self._setup_psd_options(viz_layout)
        
        # Control buttons
        self._setup_visualization_controls(viz_layout)
        
        # Progress bar
        self.plot_progress = QProgressBar()
        self.plot_progress.setVisible(False)
        viz_layout.addWidget(self.plot_progress)
        
        # Plot display
        self._setup_plot_display(viz_layout)
        
        layout.addWidget(viz_group)
        
    def _setup_plot_selection(self, layout: QVBoxLayout) -> None:
        """Setup plot type and frequency selection."""
        plot_layout = QHBoxLayout()
        
        plot_layout.addWidget(QLabel("Plot Type:"))
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["PSD", "Topomap", "Raw Data", "Spectrogram"])
        plot_layout.addWidget(self.plot_type_combo)
        
        plot_layout.addWidget(QLabel("Freq Range:"))
        self.freq_min_spin = QSpinBox()
        self.freq_min_spin.setRange(1, 100)
        self.freq_min_spin.setValue(1)
        self.freq_min_spin.setSuffix(" Hz")
        plot_layout.addWidget(self.freq_min_spin)
        
        self.freq_max_spin = QSpinBox()
        self.freq_max_spin.setRange(1, 100)
        self.freq_max_spin.setValue(50)
        self.freq_max_spin.setSuffix(" Hz")
        plot_layout.addWidget(self.freq_max_spin)
        
        layout.addLayout(plot_layout)
        
    def _setup_topomap_controls(self, layout: QVBoxLayout) -> None:
        """Setup topomap band selection."""
        topomap_layout = QHBoxLayout()
        topomap_layout.addWidget(QLabel("Topomap Band:"))
        
        self.topomap_band_combo = QComboBox()
        self.topomap_band_combo.addItems([
            "Alpha (8-13 Hz)", "Delta (1-4 Hz)", "Theta (4-8 Hz)", 
            "Beta (13-30 Hz)", "Gamma (30-50 Hz)", "Custom Range"
        ])
        self.topomap_band_combo.setCurrentText("Alpha (8-13 Hz)")
        self.topomap_band_combo.currentTextChanged.connect(self._on_topomap_band_changed)
        topomap_layout.addWidget(self.topomap_band_combo)
        
        # Custom range controls
        topomap_layout.addWidget(QLabel("Custom:"))
        self.topomap_freq_min_spin = QSpinBox()
        self.topomap_freq_min_spin.setRange(1, 100)
        self.topomap_freq_min_spin.setValue(8)
        self.topomap_freq_min_spin.setSuffix(" Hz")
        self.topomap_freq_min_spin.setVisible(False)
        topomap_layout.addWidget(self.topomap_freq_min_spin)
        
        self.topomap_range_label = QLabel("-")
        self.topomap_range_label.setVisible(False)
        topomap_layout.addWidget(self.topomap_range_label)
        
        self.topomap_freq_max_spin = QSpinBox()
        self.topomap_freq_max_spin.setRange(1, 100)
        self.topomap_freq_max_spin.setValue(13)
        self.topomap_freq_max_spin.setSuffix(" Hz")
        self.topomap_freq_max_spin.setVisible(False)
        topomap_layout.addWidget(self.topomap_freq_max_spin)
        
        topomap_layout.addStretch()
        layout.addLayout(topomap_layout)
        
    def _setup_channel_selection(self, layout: QVBoxLayout) -> None:
        """Setup channel selection for visualization."""
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("Channels to Display:"))
        
        self.selected_channels_label = QLabel("All channels")
        self.selected_channels_label.setStyleSheet("color: #CCCCCC; font-style: italic;")
        channel_layout.addWidget(self.selected_channels_label)
        channel_layout.addStretch()
        
        self.select_channels_btn = QPushButton("Select Channels")
        self.select_channels_btn.clicked.connect(
            lambda: self.channel_selection_requested.emit("visualization")
        )
        self.select_channels_btn.setStyleSheet("background-color: #007ACC;")
        channel_layout.addWidget(self.select_channels_btn)
        
        layout.addLayout(channel_layout)
        
    def _setup_psd_options(self, layout: QVBoxLayout) -> None:
        """Setup PSD visualization options."""
        psd_layout = QHBoxLayout()
        psd_layout.addWidget(QLabel("PSD Mode:"))
        
        self.psd_individual_check = QCheckBox("Show Individual Channels")
        self.psd_individual_check.setChecked(True)
        self.psd_individual_check.setToolTip("Show each channel as a separate colored line")
        self.psd_individual_check.toggled.connect(self._update_psd_mode_info)
        psd_layout.addWidget(self.psd_individual_check)
        
        psd_layout.addWidget(QLabel("   "))
        
        self.psd_mode_info = QLabel("(Individual channels with colors)")
        self.psd_mode_info.setStyleSheet("color: #888888; font-style: italic; font-size: 10px;")
        psd_layout.addWidget(self.psd_mode_info)
        psd_layout.addStretch()
        
        layout.addLayout(psd_layout)
        
    def _setup_visualization_controls(self, layout: QVBoxLayout) -> None:
        """Setup visualization control buttons."""
        buttons_layout = QHBoxLayout()
        
        self.plot_btn = QPushButton("Generate Plot")
        self.plot_btn.clicked.connect(self._request_visualization)
        buttons_layout.addWidget(self.plot_btn)
        
        self.cancel_plot_btn = QPushButton("Cancel Plot")
        self.cancel_plot_btn.clicked.connect(self.visualization_cancelled.emit)
        self.cancel_plot_btn.setEnabled(False)
        buttons_layout.addWidget(self.cancel_plot_btn)
        
        layout.addLayout(buttons_layout)
        
    def _setup_plot_display(self, layout: QVBoxLayout) -> None:
        """Setup plot display area."""
        self.plot_display = QLabel()
        self.plot_display.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        self.plot_display.setMinimumHeight(450)
        self.plot_display.setMinimumWidth(600)
        self.plot_display.setScaledContents(False)
        self.plot_display.setAlignment(Qt.AlignCenter)
        self.plot_display.setText("No plot generated yet")
        self.plot_display.setWordWrap(True)
        layout.addWidget(self.plot_display)
        
    def _on_topomap_band_changed(self) -> None:
        """Handle topomap band selection change."""
        selected_band = self.topomap_band_combo.currentText()
        is_custom = "Custom Range" in selected_band
        
        # Show/hide custom controls
        self.topomap_freq_min_spin.setVisible(is_custom)
        self.topomap_freq_max_spin.setVisible(is_custom)
        self.topomap_range_label.setVisible(is_custom)
        
        # Update values for predefined bands
        if not is_custom:
            freq_ranges = {
                "Alpha": (8, 13), "Delta": (1, 4), "Theta": (4, 8),
                "Beta": (13, 30), "Gamma": (30, 50)
            }
            
            for band, (min_freq, max_freq) in freq_ranges.items():
                if band in selected_band:
                    self.topomap_freq_min_spin.setValue(min_freq)
                    self.topomap_freq_max_spin.setValue(max_freq)
                    break
                    
    def _update_psd_mode_info(self) -> None:
        """Update PSD mode information."""
        if self.psd_individual_check.isChecked():
            self.psd_mode_info.setText("(Individual channels with colors)")
        else:
            self.psd_mode_info.setText("(Average with variability band)")
            
    def _request_visualization(self) -> None:
        """Request visualization with current parameters."""
        params = self.get_visualization_parameters()
        self.visualization_requested.emit(params)
        
    def get_visualization_parameters(self) -> Dict[str, Any]:
        """Get current visualization parameters."""
        topomap_freq_min, topomap_freq_max = self._get_topomap_frequency_range()
        
        return {
            "plot_type": self.plot_type_combo.currentText(),
            "freq_min": self.freq_min_spin.value(),
            "freq_max": self.freq_max_spin.value(),
            "show_individual_channels": self.psd_individual_check.isChecked(),
            "topomap_freq_range": (topomap_freq_min, topomap_freq_max),
            "bg_color": "#2b2b2b"
        }
        
    def _get_topomap_frequency_range(self) -> Tuple[int, int]:
        """Get topomap frequency range."""
        selected_band = self.topomap_band_combo.currentText()
        
        if "Custom Range" in selected_band:
            return (self.topomap_freq_min_spin.value(), self.topomap_freq_max_spin.value())
        
        freq_ranges = {
            "Alpha": (8, 13), "Delta": (1, 4), "Theta": (4, 8),
            "Beta": (13, 30), "Gamma": (30, 50)
        }
        
        for band, freq_range in freq_ranges.items():
            if band in selected_band:
                return freq_range
                
        return (8, 13)  # Default to Alpha
        
    def set_visualization_state(self, visualizing: bool) -> None:
        """Set visualization state."""
        self.plot_btn.setEnabled(not visualizing)
        self.cancel_plot_btn.setEnabled(visualizing)
        self.plot_progress.setVisible(visualizing)
        
        if visualizing:
            self.plot_progress.setRange(0, 0)  # Indeterminate
            
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the widget."""
        self.plot_btn.setEnabled(enabled)
        self.select_channels_btn.setEnabled(enabled)
        
    def update_channel_info(self, channel_info: str) -> None:
        """Update channel information display."""
        self.selected_channels_label.setText(channel_info)
        
    def display_plot(self, plot_data: str) -> None:
        """Display the generated plot."""
        if plot_data:
            try:
                image_data = base64.b64decode(plot_data)
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                
                if not pixmap.isNull():
                    display_size = self.plot_display.size()
                    scaled_pixmap = pixmap.scaled(
                        display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    self.plot_display.setPixmap(scaled_pixmap)
                    self.plot_display.setText("")
                else:
                    self.plot_display.setText("Error: Could not load plot image")
                    
            except Exception as e:
                logging.error(f"Error displaying plot: {e}")
                self.plot_display.setText(f"Error displaying plot: {str(e)}")
        else:
            self.plot_display.setText("No plot data received")
            
    def reset_state(self) -> None:
        """Reset widget to initial state."""
        self.set_visualization_state(False)
        self.set_enabled(False)
        self.plot_display.clear()
        self.plot_display.setText("No plot generated yet")
