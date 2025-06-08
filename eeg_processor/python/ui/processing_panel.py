from typing import Any, Optional, Dict

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
)

from .base_panel import BasePanel
from ..utils.help_system import HelpButton


class ProcessingPanel(BasePanel):
    """Panel for signal processing operations."""

    def __init__(
        self, collector_service: Any, processor_service: Any, visualization_service: Any, parent: Optional[Any] = None
    ) -> None:
        """Initialize the processing panel."""
        super().__init__(parent)
        self.collector_service = collector_service
        self.processor_service = processor_service
        self.visualization_service = visualization_service

        # Add state tracking for filters
        self.filters_applied = False

        # Setup UI components
        self.setup_filter_options()
        self.setup_metrics_section()
        self.setup_brain_map_section()

        # Add stretch to push everything to the top
        self.layout.addStretch()

    def setup_filter_options(self) -> None:
        """Set up filtering options group."""
        filter_group = QGroupBox("Filtering Options")
        filter_layout = QVBoxLayout(filter_group)

        # Bandpass filter
        bandpass_layout = QHBoxLayout()
        self.bandpass_check = QCheckBox("Bandpass Filter")
        self.bandpass_check.setChecked(True)
        # Conectar cambios a la función de actualización dinámica
        self.bandpass_check.toggled.connect(self.on_filter_option_changed)

        bandpass_low_label = QLabel("Low Cut:")
        self.bandpass_low_spin = QDoubleSpinBox()
        self.bandpass_low_spin.setRange(0.1, 100.0)
        self.bandpass_low_spin.setValue(1.0)
        self.bandpass_low_spin.setSuffix(" Hz")
        # Conectar cambios a la función de actualización dinámica
        self.bandpass_low_spin.valueChanged.connect(self.on_filter_option_changed)

        bandpass_high_label = QLabel("High Cut:")
        self.bandpass_high_spin = QDoubleSpinBox()
        self.bandpass_high_spin.setRange(0.1, 200.0)
        self.bandpass_high_spin.setValue(50.0)
        self.bandpass_high_spin.setSuffix(" Hz")
        # Conectar cambios a la función de actualización dinámica
        self.bandpass_high_spin.valueChanged.connect(self.on_filter_option_changed)

        bandpass_layout.addWidget(self.bandpass_check)
        bandpass_layout.addWidget(bandpass_low_label)
        bandpass_layout.addWidget(self.bandpass_low_spin)
        bandpass_layout.addWidget(bandpass_high_label)
        bandpass_layout.addWidget(self.bandpass_high_spin)
        bandpass_layout.addWidget(HelpButton("bandpass_filter", self))
        filter_layout.addLayout(bandpass_layout)

        # Notch filter
        notch_layout = QHBoxLayout()
        self.notch_check = QCheckBox("Notch Filter")
        self.notch_check.setChecked(True)
        # Conectar cambios a la función de actualización dinámica
        self.notch_check.toggled.connect(self.on_filter_option_changed)

        notch_type_label = QLabel("Type:")
        self.notch_type_combo = QComboBox()
        self.notch_type_combo.addItem("50 Hz", "50")
        self.notch_type_combo.addItem("60 Hz", "60")
        # Conectar cambios a la función de actualización dinámica
        self.notch_type_combo.currentIndexChanged.connect(self.on_filter_option_changed)

        notch_layout.addWidget(self.notch_check)
        notch_layout.addWidget(notch_type_label)
        notch_layout.addWidget(self.notch_type_combo)
        notch_layout.addWidget(HelpButton("notch_filter", self))
        filter_layout.addLayout(notch_layout)

        # Detrend
        detrend_layout = QHBoxLayout()
        self.detrend_check = QCheckBox("Detrend")
        self.detrend_check.setChecked(True)
        # Conectar cambios a la función de actualización dinámica
        self.detrend_check.toggled.connect(self.on_filter_option_changed)
        detrend_layout.addWidget(self.detrend_check)
        detrend_layout.addWidget(HelpButton("detrend", self))
        filter_layout.addLayout(detrend_layout)

        # Apply filter button
        apply_layout = QHBoxLayout()
        self.apply_filters_btn = QPushButton("Apply Filters to Visualization")
        self.apply_filters_btn.clicked.connect(self.apply_filters)
        self.apply_filters_btn.setEnabled(False)
        apply_layout.addWidget(self.apply_filters_btn)
        filter_layout.addLayout(apply_layout)

        self.layout.addWidget(filter_group)

    def setup_metrics_section(self) -> None:
        """Set up EEG metrics section."""
        metrics_group = QGroupBox("EEG Metrics")
        metrics_layout = QVBoxLayout(metrics_group)

        # Add help for metrics
        metrics_header_layout = QHBoxLayout()
        metrics_header_layout.addWidget(QLabel("EEG Metrics Analysis"))
        metrics_header_layout.addWidget(HelpButton("eeg_basics", self))
        metrics_header_layout.addStretch()
        metrics_layout.addLayout(metrics_header_layout)

        # Add calculate button
        metrics_update_layout = QHBoxLayout()
        self.calculate_metrics_btn = QPushButton("Calculate Metrics")
        self.calculate_metrics_btn.clicked.connect(self.calculate_metrics)
        self.calculate_metrics_btn.setEnabled(False)
        metrics_update_layout.addWidget(self.calculate_metrics_btn)
        metrics_layout.addLayout(metrics_update_layout)

        # Metrics display
        self.metrics_label = QLabel("No metrics calculated")
        metrics_layout.addWidget(self.metrics_label)

        self.layout.addWidget(metrics_group)

    def setup_brain_map_section(self) -> None:
        """Set up brain map visualization section."""
        # Add brain map button
        brain_map_layout = QHBoxLayout()
        self.brain_map_btn = QPushButton("Show Brain Map Visualization")
        self.brain_map_btn.clicked.connect(self.show_brain_map)
        self.brain_map_btn.setEnabled(False)
        brain_map_layout.addWidget(self.brain_map_btn)
        brain_map_layout.addWidget(HelpButton("brain_map", self))

        self.layout.addLayout(brain_map_layout)

        # Setup timer to check brain map status
        self.brain_map_timer = QTimer(self)
        self.brain_map_timer.timeout.connect(self.check_brain_map_status)
        self.brain_map_timer.start(1000)  # Check every second

    def check_brain_map_status(self) -> None:
        """Check if brain map visualizer needs to be restarted."""
        # Only enable the button when streaming and brain map was closed
        if (
            hasattr(self.visualization_service, "brain_map_closed")
            and self.visualization_service.brain_map_closed()
        ):
            self.brain_map_btn.setText("Reopen Brain Map Visualization")
            self.brain_map_btn.setEnabled(True)
        elif (
            not self.visualization_service.brain_map_visible()
            and hasattr(self, "processing_enabled")
            and self.processing_enabled
        ):
            # Processing is enabled but brain map is not visible and wasn't explicitly closed
            self.brain_map_btn.setText("Show Brain Map Visualization")
            self.brain_map_btn.setEnabled(True)

    def apply_filters(self) -> None:
        """Apply or remove the selected filters to visualization."""
        try:
            if not self.filters_applied:
                # Apply filters
                self.visualization_service.set_bandpass_filter(
                    self.bandpass_check.isChecked(),
                    self.bandpass_low_spin.value(),
                    self.bandpass_high_spin.value(),
                )

                self.visualization_service.set_notch_filter(
                    self.notch_check.isChecked(),
                    float(self.notch_type_combo.currentData()),
                )

                self.visualization_service.set_detrend(self.detrend_check.isChecked())

                # Update button state
                self.filters_applied = True
                self.apply_filters_btn.setText("Remove Filters from Visualization")
                self.apply_filters_btn.setStyleSheet(
                    "background-color: #AA3333; color: white;"
                )
                self.show_status("Filters applied to visualization")
            else:
                # Remove filters
                self.visualization_service.set_bandpass_filter(False, 1.0, 50.0)
                self.visualization_service.set_notch_filter(False)
                self.visualization_service.set_detrend(False)

                # Update button state
                self.filters_applied = False
                self.apply_filters_btn.setText("Apply Filters to Visualization")
                self.apply_filters_btn.setStyleSheet("")
                self.show_status("Filters removed from visualization")

        except Exception as e:
            self.show_error("Filter Error", f"Error applying filters: {str(e)}")

    def on_filter_option_changed(self) -> None:
        """Actualizar los filtros dinámicamente cuando se cambian las opciones y los filtros están aplicados."""
        # Solo actualizar si los filtros ya están aplicados
        if hasattr(self, "filters_applied") and self.filters_applied:
            try:
                # Aplicar los mismos filtros que en apply_filters, pero sin cambiar estado del botón
                self.visualization_service.set_bandpass_filter(
                    self.bandpass_check.isChecked(),
                    self.bandpass_low_spin.value(),
                    self.bandpass_high_spin.value(),
                )

                self.visualization_service.set_notch_filter(
                    self.notch_check.isChecked(),
                    float(self.notch_type_combo.currentData()),
                )

                self.visualization_service.set_detrend(self.detrend_check.isChecked())

                self.show_status("Filters updated dynamically")
            except Exception as e:
                self.show_error("Filter Error", f"Error updating filters: {str(e)}")

    def calculate_metrics(self) -> None:
        """Calculate EEG metrics from current data."""
        try:
            # Get data from collector service
            sampling_rate = self.collector_service.get_sampling_rate()
            if sampling_rate <= 0:
                self.show_error("Metrics Error", "Invalid sampling rate")
                return

            # Make sure processor is initialized
            if (
                not hasattr(self.processor_service, "processor")
                or self.processor_service.processor is None
            ):
                self.processor_service.initialize_processor(sampling_rate)
                self.show_status(
                    "Initialized processor with sampling rate " + str(sampling_rate)
                )

            # Get 4 seconds of data if available
            data, _ = self.collector_service.get_board_data(4 * sampling_rate)
            if data.size == 0:
                self.show_error("Metrics Error", "No data available")
                return

            # Get EEG channels
            eeg_channels = self.collector_service.get_eeg_channels()
            if not eeg_channels:
                self.show_error("Metrics Error", "No EEG channels available")
                return

            # Calculate metrics
            metrics = self.processor_service.get_eeg_metrics(data, eeg_channels)

            # Format and display metrics
            metrics_text = ""
            for name, value in metrics.items():
                # Handle numpy arrays by taking first value
                if hasattr(value, "__iter__"):
                    value = value[0]
                metrics_text += f"{name.capitalize()}: {value:.2f}\n"

            self.metrics_label.setText(metrics_text)
            self.show_status("EEG metrics calculated")
        except Exception as e:
            self.show_error("Metrics Error", f"Failed to calculate metrics: {str(e)}")

    def show_brain_map(self) -> None:
        """Show brain map visualization."""
        try:
            # Make sure processor is initialized before creating brain map
            sampling_rate = self.collector_service.get_sampling_rate()
            if sampling_rate <= 0:
                self.show_error("Visualization Error", "Invalid sampling rate")
                return

            # Initialize processor if not already done
            if (
                not hasattr(self.processor_service, "processor")
                or self.processor_service.processor is None
            ):
                self.processor_service.initialize_processor(sampling_rate)
                self.show_status(
                    f"Initialized processor with sampling rate {sampling_rate} Hz"
                )

            # Now create brain map visualizer with initialized processor
            success = self.visualization_service.create_brain_map_visualizer(
                self.collector_service.collector, self.processor_service.processor
            )

            if success:
                self.visualization_service.start_brain_map_visualization()
                self.show_status("Brain map visualization started")
            else:
                self.show_error(
                    "Visualization Error", "Failed to create brain map visualizer"
                )
        except Exception as e:
            self.show_error("Visualization Error", f"Error showing brain map: {e}")

    def enable_processing(self, enabled: bool) -> None:
        """Enable or disable processing controls."""
        self.processing_enabled = enabled  # Store the state for brain map checks
        self.apply_filters_btn.setEnabled(enabled)

        # Reset filters state when processing is disabled
        if not enabled and self.filters_applied:
            self.filters_applied = False
            self.apply_filters_btn.setText("Apply Filters to Visualization")
            self.apply_filters_btn.setStyleSheet("")

        self.calculate_metrics_btn.setEnabled(enabled)

        # Only enable brain map button if we're not already showing it
        if (
            not hasattr(self.visualization_service, "brain_map_visible")
            or not self.visualization_service.brain_map_visible()
        ):
            self.brain_map_btn.setEnabled(enabled)

    # Add methods for API interaction
    def _update_filter_controls(self, filter_config: Dict[str, Any]) -> bool:
        """Update filter controls from API call."""
        try:
            # Update bandpass filter controls
            if "bandpass" in filter_config:
                bp_config = filter_config["bandpass"]
                self.bandpass_check.setChecked(bp_config.get("enabled", False))
                if "low_cut" in bp_config:
                    self.bandpass_low_spin.setValue(bp_config["low_cut"])
                if "high_cut" in bp_config:
                    self.bandpass_high_spin.setValue(bp_config["high_cut"])

            # Update notch filter controls
            if "notch" in filter_config:
                notch_config = filter_config["notch"]
                self.notch_check.setChecked(notch_config.get("enabled", False))
                if "frequency" in notch_config:
                    # Find and select the appropriate frequency
                    freq = str(notch_config["frequency"])
                    for i in range(self.notch_type_combo.count()):
                        if self.notch_type_combo.itemData(i) == freq:
                            self.notch_type_combo.setCurrentIndex(i)
                            break

            # Update detrend controls
            if "detrend" in filter_config:
                self.detrend_check.setChecked(filter_config["detrend"])

            # Update button state if filters are applied
            if filter_config.get("applied", False):
                self.filters_applied = True
                self.apply_filters_btn.setText("Remove Filters from Visualization")
                self.apply_filters_btn.setStyleSheet(
                    "background-color: #AA3333; color: white;"
                )
            else:
                self.filters_applied = False
                self.apply_filters_btn.setText("Apply Filters to Visualization")
                self.apply_filters_btn.setStyleSheet("")

            return True
        except Exception as e:
            self.show_error("Filter Controls Update Error", str(e))
            return False

    def get_filter_settings(self) -> Dict[str, Any]:
        """Get current filter settings."""
        return {
            "bandpass": {
                "enabled": self.bandpass_check.isChecked(),
                "low_cut": self.bandpass_low_spin.value(),
                "high_cut": self.bandpass_high_spin.value(),
            },
            "notch": {
                "enabled": self.notch_check.isChecked(),
                "frequency": float(self.notch_type_combo.currentData()),
            },
            "detrend": self.detrend_check.isChecked(),
            "applied": self.filters_applied,
        }

    def update_metrics_display(self, metrics_text: str) -> bool:
        """Update the metrics display from API call."""
        try:
            self.metrics_label.setText(metrics_text)
            return True
        except Exception as e:
            self.show_error("Metrics Update Error", str(e))
            return False
