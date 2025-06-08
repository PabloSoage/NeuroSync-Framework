from typing import Any, Optional, Dict

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .base_panel import BasePanel
from ..utils.help_system import HelpButton

# Check if MNE is available
try:
    import mne

    MNE_AVAILABLE = True
except ImportError:
    MNE_AVAILABLE = False


class MNEPanel(BasePanel):
    """Panel for MNE integration and analysis."""

    def __init__(
        self, collector_service: Any, processor_service: Any, parent: Optional[Any] = None
    ) -> None:
        """Initialize the MNE panel."""
        super().__init__(parent)
        self.collector_service = collector_service
        self.processor_service = processor_service
        self.mne_raw = None

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
        self.mne_duration_spin.setValue(5)
        mne_params_layout.addWidget(self.mne_duration_spin)

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

        mne_viz_buttons = QHBoxLayout()

        self.plot_mne_psd_btn = QPushButton("Plot PSD")
        self.plot_mne_psd_btn.clicked.connect(
            lambda: self.plot_mne_visualization("psd")
        )
        self.plot_mne_psd_btn.setEnabled(False)
        mne_viz_buttons.addWidget(self.plot_mne_psd_btn)

        self.plot_mne_topomap_btn = QPushButton("Plot Topomap")
        self.plot_mne_topomap_btn.clicked.connect(
            lambda: self.plot_mne_visualization("topomap")
        )
        self.plot_mne_topomap_btn.setEnabled(False)
        mne_viz_buttons.addWidget(self.plot_mne_topomap_btn)

        mne_viz_layout.addLayout(mne_viz_buttons)

        # Matplotlib figure for MNE plots
        self.mne_figure = Figure(figsize=(8, 6))
        self.mne_canvas = FigureCanvas(self.mne_figure)
        mne_viz_layout.addWidget(self.mne_canvas)

        self.layout.addWidget(mne_viz_group)

    def convert_to_mne(self) -> None:
        """Convert BrainFlow data to MNE format."""
        if not MNE_AVAILABLE:
            self.show_error("MNE Error", "MNE package is not installed")
            return

        try:
            # Implementation of MNE conversion
            seconds = self.mne_duration_spin.value()
            self.show_status(f"Converting {seconds}s of data to MNE format")

            # In a real implementation, this would get data and convert to MNE format
            self.plot_mne_psd_btn.setEnabled(True)
            self.plot_mne_topomap_btn.setEnabled(True)
        except Exception as e:
            self.show_error("MNE Error", f"Error converting to MNE format: {str(e)}")

    def plot_mne_visualization(self, plot_type: str) -> None:
        """Plot MNE visualizations."""
        if not MNE_AVAILABLE:
            return

        try:
            # Clear the figure
            self.mne_figure.clear()

            if plot_type == "psd":
                # Create PSD plot (a placeholder in this implementation)
                ax = self.mne_figure.add_subplot(111)
                ax.plot([0, 10, 20, 30], [0, 1, 0, 1])
                ax.set_title("Power Spectral Density")
                ax.set_xlabel("Frequency (Hz)")
                ax.set_ylabel("Power (dB)")
            elif plot_type == "topomap":
                # Create topomap plot (a placeholder in this implementation)
                ax = self.mne_figure.add_subplot(111)
                ax.text(
                    0.5,
                    0.5,
                    "Topomap would appear here",
                    horizontalalignment="center",
                    verticalalignment="center",
                )
                ax.set_title("Alpha Band Power Topomap")
                ax.axis("off")

            # Update canvas
            self.mne_figure.tight_layout()
            self.mne_canvas.draw()

            self.show_status(f"Generated {plot_type} visualization")
        except Exception as e:
            self.show_error("MNE Error", f"Error creating visualization: {str(e)}")

    def enable_processing(self, enabled: bool) -> None:
        """Enable or disable MNE processing controls."""
        self.convert_to_mne_btn.setEnabled(enabled)

        # Reset dependent buttons
        if not enabled:
            self.plot_mne_psd_btn.setEnabled(False)
            self.plot_mne_topomap_btn.setEnabled(False)

    # Add methods for API interaction
    def get_mne_settings(self) -> Dict[str, Any]:
        """Get current MNE settings."""
        if not MNE_AVAILABLE:
            return {"available": False}

        return {
            "available": True,
            "duration": (
                self.mne_duration_spin.value()
                if hasattr(self, "mne_duration_spin")
                else 5
            ),
        }

    def update_mne_plot(self, plot_data: Dict[str, Any]) -> bool:
        """Update MNE plot from API call."""
        if not MNE_AVAILABLE:
            return False

        try:
            # Clear the figure
            self.mne_figure.clear()

            plot_type = plot_data.get("type", "psd")
            title = plot_data.get("title", "")

            # Create a blank plot with message
            ax = self.mne_figure.add_subplot(111)
            ax.text(
                0.5,
                0.5,
                plot_data.get("message", "Plot data updated from API"),
                horizontalalignment="center",
                verticalalignment="center",
            )
            ax.set_title(title)

            if plot_type == "psd":
                ax.set_xlabel("Frequency (Hz)")
                ax.set_ylabel("Power (dB)")
            else:
                ax.axis("off")

            # Update canvas
            self.mne_figure.tight_layout()
            self.mne_canvas.draw()

            return True
        except Exception as e:
            self.show_error("MNE Plot Update Error", str(e))
            return False
