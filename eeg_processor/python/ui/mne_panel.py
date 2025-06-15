from typing import Any, Optional, Dict
import logging
import numpy as np

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QCheckBox,
    QComboBox,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .base_panel import BasePanel
from ..utils.help_system import HelpButton
from ..services.data_access_service import DataAccessService

# Check if MNE is available
try:
    import mne
    import matplotlib.pyplot as plt
    MNE_AVAILABLE = True
except ImportError:
    MNE_AVAILABLE = False


class MNEPanel(BasePanel):
    """Panel for MNE integration and analysis."""

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
        self.mne_raw = None
        
        # Get data access service
        self.data_service = DataAccessService.get_instance()

        # Setup UI components
        if MNE_AVAILABLE:
            self.setup_mne_conversion()
            self.setup_mne_visualization()
        else:
            self.setup_mne_not_available()

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

        mne_layout.addLayout(mne_buttons_layout)

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

        mne_viz_layout.addLayout(mne_viz_buttons)

        # Matplotlib figure for MNE plots
        self.mne_figure = Figure(figsize=(10, 8))
        self.mne_canvas = FigureCanvas(self.mne_figure)
        mne_viz_layout.addWidget(self.mne_canvas)

        self.layout.addWidget(mne_viz_group)

    def convert_to_mne(self) -> None:
        """Convert BrainFlow data to MNE format."""
        if not MNE_AVAILABLE:
            self.show_error("MNE Error", "MNE package is not installed")
            return

        try:
            # Get data from DataAccessService
            data, timestamps = self.data_service.get_current_data()
            metadata = self.data_service.get_metadata()
            
            if data.size == 0:
                self.show_error("MNE Error", "No data available. Start streaming first.")
                return

            # Get duration in seconds
            duration_seconds = self.mne_duration_spin.value()
            sampling_rate = metadata.get("sampling_rate", 250)
            samples_needed = int(duration_seconds * sampling_rate)
            
            # Get last N seconds of data
            if data.shape[1] < samples_needed:
                self.show_error("MNE Error", f"Not enough data. Need {duration_seconds}s but only have {data.shape[1]/sampling_rate:.1f}s")
                return
                
            # Extract last N seconds
            recent_data = data[:, -samples_needed:]
            
            # Get EEG channels
            eeg_channels = metadata.get("eeg_channels", [])
            if not eeg_channels:
                self.show_error("MNE Error", "No EEG channels available")
                return
                
            # Extract EEG data
            eeg_data = recent_data[eeg_channels, :]
            
            # Convert units: BrainFlow returns uV, convert to V for MNE (igual que el ejemplo)
            if self.convert_to_v_check.isChecked():
                eeg_data = eeg_data / 1000000
            
            # Create MNE objects from brainflow data arrays
            ch_types = ['eeg'] * len(eeg_channels)
            
            # Get channel names
            ch_names = metadata.get("channel_names", [])
            if len(ch_names) < len(eeg_channels):
                ch_names = [f"EEG_{i}" for i in range(len(eeg_channels))]
            else:
                ch_names = ch_names[:len(eeg_channels)]
            
            # Create MNE info object
            info = mne.create_info(ch_names=ch_names, sfreq=sampling_rate, ch_types=ch_types)
            
            # Create Raw object
            self.mne_raw = mne.io.RawArray(eeg_data, info)
            
            # Enable visualization buttons
            self.plot_mne_btn.setEnabled(True)
            
            self.show_status(f"Converted {duration_seconds}s of data to MNE format ({len(eeg_channels)} channels)")
            logging.info(f"MNE Raw object created: {self.mne_raw}")
            
        except Exception as e:
            self.show_error("MNE Error", f"Error converting to MNE format: {str(e)}")
            logging.error(f"MNE conversion error: {e}")

    def plot_mne_visualization(self) -> None:
        """Plot MNE visualizations (implementando funcionalidades reales)."""
        if not MNE_AVAILABLE or self.mne_raw is None:
            self.show_error("MNE Error", "No MNE data available. Convert data first.")
            return

        try:
            # Clear the figure
            self.mne_figure.clear()
            
            plot_type = self.plot_type_combo.currentText()
            
            if plot_type == "PSD":
                # Create PSD plot
                fmin = self.freq_min_spin.value()
                fmax = self.freq_max_spin.value()
                
                # Use MNE's compute_psd method
                psd = self.mne_raw.compute_psd(fmin=fmin, fmax=fmax, method='welch')
                
                # Plot using matplotlib
                ax = self.mne_figure.add_subplot(111)
                psd.plot(axes=ax, show=False, average=True)
                ax.set_title(f"Power Spectral Density ({fmin}-{fmax} Hz)")
                ax.set_xlabel("Frequency (Hz)")
                ax.set_ylabel("Power (V²/Hz)")
                
            elif plot_type == "Topomap":
                # Create topomap for alpha band
                freqs = np.arange(8, 13)  # Alpha band
                psd = self.mne_raw.compute_psd(fmin=8, fmax=13, method='welch')
                psd_avg = psd.get_data().mean(axis=1)
                
                # Create a basic topomap
                ax = self.mne_figure.add_subplot(111)
                # For demonstration - in real implementation would need proper electrode positions
                ax.text(0.5, 0.5, f"Alpha Power Topomap\n({len(psd_avg)} channels)", 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title("Alpha Band Power (8-13 Hz)")
                ax.axis('off')
                
            elif plot_type == "Raw Data":
                # Plot raw time series data
                ax = self.mne_figure.add_subplot(111)
                data_to_plot = self.mne_raw.get_data()
                times = self.mne_raw.times
                
                # Plot first few channels to avoid clutter
                max_channels = min(4, data_to_plot.shape[0])
                for i in range(max_channels):
                    ax.plot(times, data_to_plot[i], label=f"Channel {i}")
                
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Amplitude (V)")
                ax.set_title("Raw EEG Data")
                ax.legend()
                ax.grid(True)
                
            elif plot_type == "Spectrogram":
                # Create spectrogram for first channel
                ax = self.mne_figure.add_subplot(111)
                data_ch0 = self.mne_raw.get_data()[0]
                fs = self.mne_raw.info['sfreq']
                
                # Create spectrogram
                from scipy import signal
                f, t, Sxx = signal.spectrogram(data_ch0, fs)
                im = ax.pcolormesh(t, f, 10 * np.log10(Sxx))
                ax.set_ylabel('Frequency [Hz]')
                ax.set_xlabel('Time [s]')
                ax.set_title('Spectrogram (Channel 0)')
                self.mne_figure.colorbar(im, ax=ax, label='Power (dB)')

            # Update canvas
            self.mne_figure.tight_layout()
            self.mne_canvas.draw()

            self.show_status(f"Generated {plot_type} visualization")
            
        except Exception as e:
            self.show_error("MNE Error", f"Error creating visualization: {str(e)}")
            logging.error(f"MNE visualization error: {e}")

    def enable_processing(self, enabled: bool) -> None:
        """Enable or disable MNE processing controls."""
        if hasattr(self, 'convert_to_mne_btn'):
            self.convert_to_mne_btn.setEnabled(enabled)

        # Reset dependent buttons
        if not enabled:
            if hasattr(self, 'plot_mne_btn'):
                self.plot_mne_btn.setEnabled(False)
            self.mne_raw = None

    # Add methods for API interaction
    def get_mne_settings(self) -> Dict[str, Any]:
        """Get current MNE settings."""
        if not MNE_AVAILABLE:
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
        if not MNE_AVAILABLE:
            return False

        try:
            # Implementation for API-driven plot updates
            plot_type = plot_data.get("type", "psd")
            
            if plot_type in ["psd", "topomap", "raw", "spectrogram"]:
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