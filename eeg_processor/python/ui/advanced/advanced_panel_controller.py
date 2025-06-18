import logging
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QProgressDialog

from .widgets.ica_widget import ICAWidget
from .widgets.wavelet_widget import WaveletWidget
from .widgets.downsampling_widget import DownsamplingWidget
from .widgets.advanced_filter_widget import AdvancedFilterWidget
from ...services.advanced_processing_service import AdvancedProcessingService
from ...services.export_service import ExportService


class AdvancedPanelController(QObject):
    """
    Coordinator for advanced processing panel.
    
    This class connects UI widgets with the underlying services and handles the 
    user interaction flow, delegating the actual processing to services.
    """
    
    # Signals for communication with parent panel
    status_message = pyqtSignal(str)
    error_message = pyqtSignal(str, str)
    
    # Export signals
    export_progress = pyqtSignal(int, str)
    export_finished = pyqtSignal(bool, str)

    def __init__(
        self,
        ica_widget: ICAWidget,
        wavelet_widget: WaveletWidget,
        downsampling_widget: DownsamplingWidget,
        advanced_filter_widget: AdvancedFilterWidget,
        collector_service: Any,
        processor_service: Any,
        parent: Optional[Any] = None,
    ) -> None:
        """Initialize the controller."""
        super().__init__(parent)
        
        # Store widget references
        self.ica_widget = ica_widget
        self.wavelet_widget = wavelet_widget
        self.downsampling_widget = downsampling_widget
        self.advanced_filter_widget = advanced_filter_widget
        
        # Store service references
        self.collector_service = collector_service
        self.processor_service = processor_service
        
        # Create service instances
        self.processing_service = AdvancedProcessingService()
        self.processing_service.initialize(processor_service)
        
        self.export_service = ExportService()
        
        # Export progress handling
        self.export_progress_dialog = None
        self.export_timer = None
        
        # Connect export signals
        self.export_service.progress_updated.connect(self._update_export_progress)
        self.export_service.export_completed.connect(self._export_finished)
        
        # Connect widget signals
        self._connect_widget_signals()
        
        # Initialize channel data
        self._initialize_channel_data()

    def _connect_widget_signals(self) -> None:
        """Connect signals from widgets."""
        # ICA widget signals
        self.ica_widget.compute_requested.connect(self._handle_ica_computation)
        self.ica_widget.view_components_requested.connect(self._handle_ica_visualization)
        self.ica_widget.export_overview_requested.connect(self._handle_ica_export_overview)
        self.ica_widget.export_all_requested.connect(self._handle_ica_export_all)
        
        # Wavelet widget signals
        self.wavelet_widget.compute_requested.connect(self._handle_wavelet_computation)
        self.wavelet_widget.apply_inverse_requested.connect(self._handle_wavelet_inverse)
        
        # Downsampling widget signals
        self.downsampling_widget.apply_requested.connect(self._handle_downsampling)
        
        # Advanced filter widget signals
        self.advanced_filter_widget.apply_requested.connect(self._handle_advanced_filters)

    def _initialize_channel_data(self) -> None:
        """Initialize channel data from data service."""
        try:
            channel_names = self.processing_service.get_channel_names()
            
            # Update widgets with channel information
            self.ica_widget.update_channels(channel_names)
            self.wavelet_widget.update_channels(channel_names)

        except Exception as e:
            logging.debug(f"Error initializing channel data: {e}")

    def _handle_ica_computation(self, params: Dict[str, Any]) -> None:
        """Handle ICA computation request."""
        try:
            # Validate parameters
            num_components = params["num_components"]
            selected_channels = params["selected_channels"]
            
            if not selected_channels:
                self.error_message.emit("ICA Error", "Please select at least one channel")
                return
            
            if len(selected_channels) < num_components:
                self.error_message.emit(
                    "ICA Error", 
                    f"Number of selected channels ({len(selected_channels)}) must be >= number of components ({num_components})"
                )
                return
            
            # Check selected channels vs. component count
            if len(selected_channels) < 8:
                reply = QMessageBox.question(
                    self.parent(), 
                    "ICA Warning", 
                    f"ICA works best with at least 8-16 channels. You have {len(selected_channels)} channels.\n"
                    "Results may not be meaningful. Continue anyway?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return

            # Get sampling rate
            sampling_rate = self.collector_service.get_sampling_rate()
            if sampling_rate <= 0:
                self.error_message.emit("ICA Error", "Invalid sampling rate")
                return

            # Compute ICA using the service
            result = self.processing_service.compute_ica(params)
            
            if result.get('success'):
                # Update ICA widget with results
                self.ica_widget.set_ica_results(result.get('components'))
                
                self.status_message.emit(
                    f"ICA computed successfully with {num_components} components on {len(selected_channels)} channels"
                )
            else:
                self.error_message.emit("ICA Error", result.get('error', "Failed to compute ICA components"))

        except Exception as e:
            self.error_message.emit("ICA Error", f"Error computing ICA: {str(e)}")

    def _handle_ica_visualization(self, params: Dict[str, Any]) -> None:
        """Handle ICA visualization request."""
        try:
            ica_components = self.processing_service.get_ica_results()
            if not ica_components:
                self.error_message.emit("ICA Error", "No ICA components available. Compute ICA first.")
                return

            # Create visualization dialog
            from .dialogs.ica_visualization_dialog import ICAVisualizationDialog
            
            dialog = ICAVisualizationDialog(
                ica_components=ica_components,
                sampling_rate=self.collector_service.get_sampling_rate(),
                parent=self.parent()
            )
            
            # Connect export signals from dialog
            dialog.export_overview_requested.connect(self._handle_ica_export_overview)
            dialog.export_all_requested.connect(self._handle_ica_export_all)
            
            dialog.show()
            
            num_components = ica_components["num_components"]
            selected_channels = ica_components["selected_channels"]
            self.status_message.emit(
                f"ICA components visualization displayed - {num_components} components in scrollable view"
            )

        except Exception as e:
            self.error_message.emit("ICA Error", f"Error displaying ICA components: {str(e)}")

    def _handle_ica_export_overview(self) -> None:
        """Handle ICA overview export request."""
        try:
            ica_components = self.processing_service.get_ica_results()
            if not ica_components:
                self.error_message.emit("Export Error", "No ICA components available")
                return

            # Open file save dialog
            filename, _ = QFileDialog.getSaveFileName(
                self.parent(), "Save ICA Overview", "ica_overview.png", "PNG files (*.png)"
            )
            
            if filename:
                # Create progress dialog
                self.export_progress_dialog = QProgressDialog(
                    "Exporting ICA overview...", "Cancel", 0, 100, self.parent()
                )
                self.export_progress_dialog.setWindowTitle("Export Progress")
                self.export_progress_dialog.setModal(True)
                self.export_progress_dialog.canceled.connect(self._cancel_export)
                self.export_progress_dialog.show()
                
                # Start export process
                self.export_service.export_ica_overview(
                    ica_components,
                    self.ica_widget.get_colormap(),
                    self.collector_service.get_sampling_rate(),
                    filename
                )
                
                # Start timer to monitor progress
                self.export_timer = QTimer()
                self.export_timer.timeout.connect(self.export_service.check_export_progress)
                self.export_timer.start(100)  # Check every 100ms
                
        except Exception as e:
            self.error_message.emit("Export Error", f"Error exporting overview: {str(e)}")

    def _handle_ica_export_all(self) -> None:
        """Handle export all ICA images request."""
        try:
            ica_components = self.processing_service.get_ica_results()
            if not ica_components:
                self.error_message.emit("Export Error", "No ICA components available")
                return

            # Open directory selection dialog
            directory = QFileDialog.getExistingDirectory(
                self.parent(), "Select Directory to Save ICA Images", ""
            )
            
            if not directory:
                return

            # Create progress dialog
            self.export_progress_dialog = QProgressDialog(
                "Exporting ICA components...", "Cancel", 0, 100, self.parent()
            )
            self.export_progress_dialog.setWindowTitle("Export Progress")
            self.export_progress_dialog.setModal(True)
            self.export_progress_dialog.canceled.connect(self._cancel_export)
            self.export_progress_dialog.show()
            
            # Start export process
            self.export_service.export_ica_components(
                ica_components,
                self.ica_widget.get_colormap(),
                self.collector_service.get_sampling_rate(),
                directory
            )
            
            # Start timer to monitor progress
            self.export_timer = QTimer()
            self.export_timer.timeout.connect(self.export_service.check_export_progress)
            self.export_timer.start(100)  # Check every 100ms

        except Exception as e:
            self.error_message.emit("Export Error", f"Error starting export: {str(e)}")
    
    def _handle_ica_export_overview_with_colormap(self, colormap: str) -> None:
        """Handle ICA overview export request with specific colormap."""
        try:
            ica_components = self.processing_service.get_ica_results()
            if not ica_components:
                self.error_message.emit("Export Error", "No ICA components available")
                return

            # Open file save dialog
            filename, _ = QFileDialog.getSaveFileName(
                self.parent(), "Save ICA Overview", "ica_overview.png", "PNG files (*.png)"
            )
            
            if filename:
                # Create progress dialog
                self.export_progress_dialog = QProgressDialog(
                    "Exporting ICA overview...", "Cancel", 0, 100, self.parent()
                )
                self.export_progress_dialog.setWindowTitle("Export Progress")
                self.export_progress_dialog.setModal(True)
                self.export_progress_dialog.canceled.connect(self._cancel_export)
                self.export_progress_dialog.show()
                
                # Start export process with specified colormap
                self.export_service.export_ica_overview(
                    ica_components,
                    colormap,  # Use the provided colormap instead of widget's default
                    self.collector_service.get_sampling_rate(),
                    filename
                )
                
                # Start timer to monitor progress
                self.export_timer = QTimer()
                self.export_timer.timeout.connect(self.export_service.check_export_progress)
                self.export_timer.start(100)  # Check every 100ms
                
        except Exception as e:
            self.error_message.emit("Export Error", f"Error exporting overview: {str(e)}")

    def _handle_ica_export_all_with_colormap(self, colormap: str) -> None:
        """Handle export all ICA images request with specific colormap."""
        try:
            ica_components = self.processing_service.get_ica_results()
            if not ica_components:
                self.error_message.emit("Export Error", "No ICA components available")
                return

            # Open directory selection dialog
            directory = QFileDialog.getExistingDirectory(
                self.parent(), "Select Directory to Save ICA Images", ""
            )
            
            if not directory:
                return

            # Create progress dialog
            self.export_progress_dialog = QProgressDialog(
                "Exporting ICA components...", "Cancel", 0, 100, self.parent()
            )
            self.export_progress_dialog.setWindowTitle("Export Progress")
            self.export_progress_dialog.setModal(True)
            self.export_progress_dialog.canceled.connect(self._cancel_export)
            self.export_progress_dialog.show()
            
            # Start export process with specified colormap
            self.export_service.export_ica_components(
                ica_components,
                colormap,  # Use the provided colormap instead of widget's default
                self.collector_service.get_sampling_rate(),
                directory
            )
            
            # Start timer to monitor progress
            self.export_timer = QTimer()
            self.export_timer.timeout.connect(self.export_service.check_export_progress)
            self.export_timer.start(100)  # Check every 100ms

        except Exception as e:
            self.error_message.emit("Export Error", f"Error starting export: {str(e)}")

    def _handle_wavelet_computation(self, params: Dict[str, Any]) -> None:
        """Handle wavelet computation request."""
        try:
            result = self.processing_service.compute_wavelet(params)
            
            if result.get('success'):
                # Update wavelet widget with results
                self.wavelet_widget.set_wavelet_results(
                    result.get('coefficients'),
                    result.get('metadata')
                )
                self.status_message.emit("Wavelet transform computed successfully")
            else:
                self.error_message.emit("Wavelet Error", result.get('error', "Failed to compute wavelet transform"))

        except Exception as e:
            self.error_message.emit("Wavelet Error", f"Error computing wavelet transform: {str(e)}")

    def _handle_wavelet_inverse(self, apply: bool) -> None:
        """Handle wavelet inverse transform request."""
        try:
            if not self.wavelet_widget.has_wavelet_results():
                self.error_message.emit("Wavelet Error", "No wavelet coefficients available. Compute wavelet first.")
                return

            result = self.processing_service.apply_wavelet_inverse(apply)
            
            if result.get('success'):
                self.status_message.emit(
                    "Inverse wavelet transform applied to data stream" if apply else 
                    "Inverse wavelet transform removed from data stream"
                )
            else:
                self.error_message.emit("Wavelet Error", result.get('error', "Failed to apply inverse wavelet"))

        except Exception as e:
            self.error_message.emit("Wavelet Error", f"Error applying inverse wavelet: {str(e)}")

    def _handle_downsampling(self, params: Dict[str, Any]) -> None:
        """Handle downsampling request."""
        try:
            result = self.processing_service.apply_downsampling(params)
            
            if result.get('success'):
                self.status_message.emit(
                    f"Downsampling (factor {params['factor']}) applied to data stream" if params.get('apply') else
                    "Downsampling removed from data stream"
                )
            else:
                self.error_message.emit("Downsampling Error", result.get('error', "Failed to apply downsampling"))

        except Exception as e:
            self.error_message.emit("Downsampling Error", f"Error applying downsampling: {str(e)}")

    def _handle_advanced_filters(self, params: Dict[str, Any]) -> None:
        """Handle advanced filters request."""
        try:
            result = self.processing_service.apply_advanced_filters(params)
            
            if result.get('success'):
                self.status_message.emit(
                    "Advanced filters applied to data stream" if params.get('apply') else
                    "Advanced filters removed from data stream"
                )
            else:
                self.error_message.emit("Filtering Error", result.get('error', "Failed to apply advanced filters"))

        except Exception as e:
            self.error_message.emit("Filtering Error", f"Error applying advanced filters: {str(e)}")

    def _update_export_progress(self, percent: int, status: str):
        """Update the progress dialog."""
        if self.export_progress_dialog:
            self.export_progress_dialog.setValue(percent)
            self.export_progress_dialog.setLabelText(status)

    def _export_finished(self, success: bool, message: str):
        """Handle export completion."""
        self._cleanup_export()
        
        if success:
            self.status_message.emit(message)
        else:
            self.error_message.emit("Export Error", message)

    def _cancel_export(self):
        """Cancel the export process."""
        self.export_service.cancel_export()
        self._cleanup_export()
        self.status_message.emit("Export cancelled")

    def _cleanup_export(self):
        """Clean up export resources."""
        if self.export_timer:
            self.export_timer.stop()
            self.export_timer = None
            
        if self.export_progress_dialog:
            self.export_progress_dialog.close()
            self.export_progress_dialog = None

    def enable_processing(self, enabled: bool) -> None:
        """Enable or disable advanced processing controls."""
        self.ica_widget.set_enabled(enabled)
        self.wavelet_widget.set_enabled(enabled)
        self.downsampling_widget.set_enabled(enabled)
        self.advanced_filter_widget.set_enabled(enabled)

        # Update channel data when processing is enabled
        if enabled:
            self._initialize_channel_data()

    def update_channel_lists(self, channel_names: List[str]) -> bool:
        """Update channel selection from API call."""
        try:
            self.ica_widget.update_channels(channel_names)
            self.wavelet_widget.update_channels(channel_names)
            return True
        except Exception as e:
            self.error_message.emit("Channel List Update Error", str(e))
            return False

    def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        self._cleanup_export()
        self.export_service.cleanup()
        self.processing_service.cleanup()