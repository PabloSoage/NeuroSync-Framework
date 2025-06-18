import logging
import time
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QProgressDialog
from brainflow import FilterTypes

from .widgets.ica_widget import ICAWidget
from .widgets.wavelet_widget import WaveletWidget
from .widgets.downsampling_widget import DownsamplingWidget
from .widgets.advanced_filter_widget import AdvancedFilterWidget
from ...services.advanced_processing_service import AdvancedProcessingService
from ...services.ica.export_service import ExportService
from ...services.ica.ica_process_service import ICAProcessService
from ...services.ica.ica_realtime_service import ICARealtimeService

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
        
        # Try to get processing panel reference for dynamic bandpass parameters
        self._setup_processing_panel_reference()
        
        # Create service instances
        self.processing_service = AdvancedProcessingService()
        self.processing_service.initialize(processor_service)
        
        self.export_service = ExportService()
        
        # Create ICA process service for visualization only
        self.ica_process_service = ICAProcessService()
        
        # Create ICA realtime service
        self.ica_realtime_service = ICARealtimeService()
        self.ica_realtime_service.initialize(processor_service)
        
        # Export progress handling
        self.export_progress_dialog = None
        self.export_timer = None
        
        # Connect export signals from local export service
        self.export_service.progress_updated.connect(self._update_export_progress)
        self.export_service.export_completed.connect(self._export_finished)
        
        # Connect ICA process service signals (for visualization)
        self.ica_process_service.visualization_ready.connect(self._on_visualization_ready)
        
        # Connect ICA realtime service signals
        self.ica_realtime_service.realtime_ica_updated.connect(self._on_realtime_ica_updated)
        self.ica_realtime_service.realtime_status_changed.connect(self._on_realtime_status_changed)
        self.ica_realtime_service.realtime_error.connect(self._on_realtime_error)
        
        # Connect widget signals
        self._connect_widget_signals()
        
        # Initialize channel data
        self._initialize_channel_data()
        
        # Initialize ICA process service for visualization
        if not self.ica_process_service.initialize():
            logging.warning("Failed to initialize ICA process service - visualizations will be local")

    def _connect_widget_signals(self) -> None:
        """Connect signals from widgets."""
        # ICA widget signals
        self.ica_widget.compute_requested.connect(self._handle_ica_computation)
        self.ica_widget.view_components_requested.connect(self._handle_ica_visualization)
        self.ica_widget.export_overview_requested.connect(self._handle_ica_export_overview)
        self.ica_widget.export_all_requested.connect(self._handle_ica_export_all)

        # ICA real-time signals
        self.ica_widget.realtime_start_requested.connect(self._handle_realtime_start)
        self.ica_widget.realtime_stop_requested.connect(self._handle_realtime_stop)
        self.ica_widget.realtime_interval_changed.connect(self._handle_realtime_interval_change)
        
        # Wavelet widget signals
        self.wavelet_widget.compute_requested.connect(self._handle_wavelet_computation)
        self.wavelet_widget.apply_inverse_requested.connect(self._handle_wavelet_inverse)
        # Connect dynamic update signal
        self.wavelet_widget.settings_changed.connect(self._handle_wavelet_settings_changed)
        
        # Downsampling widget signals
        self.downsampling_widget.apply_requested.connect(self._handle_downsampling)
        # Connect dynamic update signal
        self.downsampling_widget.settings_changed.connect(self._handle_downsampling_settings_changed)
        
        # Advanced filter widget signals
        self.advanced_filter_widget.apply_requested.connect(self._handle_advanced_filters)
        # Connect dynamic update signal
        self.advanced_filter_widget.settings_changed.connect(self._handle_advanced_filter_settings_changed)

    def _initialize_channel_data(self) -> None:
        """Initialize channel data from data service."""
        try:
            channel_names = self.processing_service.get_channel_names()
            
            # Update widgets with channel information
            self.ica_widget.update_channels(channel_names)
            self.wavelet_widget.update_channels(channel_names)
            self.advanced_filter_widget.update_channels(channel_names)

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

            # Compute ICA using the original local service
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
        """Handle ICA visualization request using the dedicated process for themed UI."""
        try:
            ica_components = self.processing_service.get_ica_results()
            if not ica_components:
                self.error_message.emit("ICA Error", "No ICA components available. Compute ICA first.")
                return

            # Try to use the process service for themed visualization
            if self.ica_process_service._is_initialized:
                sampling_rate = self.collector_service.get_sampling_rate()
                colormap = params.get('colormap', self.ica_widget.get_colormap())
                
                self.status_message.emit("Opening ICA visualization in dedicated process...")
                # Always use visualize_ica for manual requests (creates new window if needed)
                self.ica_process_service.visualize_ica(ica_components, sampling_rate, colormap)
            else:
                # Fallback to local visualization dialog
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

    # Real-time ICA handlers
    def _handle_realtime_start(self, params: Dict[str, Any]) -> None:
        """Handle real-time ICA start request."""
        try:
            # Validate parameters
            num_components = params["num_components"]
            selected_channels = params["selected_channels"]
            update_interval = params["update_interval"]
            
            if not selected_channels:
                self.error_message.emit("Real-time ICA Error", "Please select at least one channel")
                return
            
            if len(selected_channels) < num_components:
                self.error_message.emit(
                    "Real-time ICA Error", 
                    f"Number of selected channels ({len(selected_channels)}) must be >= number of components ({num_components})"
                )
                return

            # Start real-time ICA
            success = self.ica_realtime_service.start_realtime_ica(params)
            
            if not success:
                # Error will be emitted by the service
                return

        except Exception as e:
            self.error_message.emit("Real-time ICA Error", f"Error starting real-time ICA: {str(e)}")

    def _handle_realtime_stop(self) -> None:
        """Handle real-time ICA stop request."""
        try:
            self.ica_realtime_service.stop_realtime_ica()
            
            # Keep visualization open but stop updates
            if (self.ica_process_service._is_initialized and 
                self.ica_process_service.is_visualization_active()):
                # Don't close the visualization, just stop sending updates
                pass
                
        except Exception as e:
            self.error_message.emit("Real-time ICA Error", f"Error stopping real-time ICA: {str(e)}")

    def _handle_realtime_interval_change(self, interval: float) -> None:
        """Handle real-time interval change."""
        try:
            self.ica_realtime_service.update_interval(interval)
        except Exception as e:
            self.error_message.emit("Real-time ICA Error", f"Error updating interval: {str(e)}")

    def _on_realtime_ica_updated(self, ica_components: Dict[str, Any], message: str) -> None:
        """Handle real-time ICA update."""
        try:
            # Update visualization if process service is available
            if self.ica_process_service._is_initialized:
                sampling_rate = self.collector_service.get_sampling_rate()
                colormap = self.ica_widget.get_colormap()
                
                # Check if visualization is active - if not, create it; if yes, update it
                if self.ica_process_service.is_visualization_active():
                    # Update existing visualization
                    self.ica_process_service.visualize_ica(ica_components, sampling_rate, colormap)
                else:
                    # Create new visualization for real-time (first real-time update)
                    self.status_message.emit("Opening real-time ICA visualization...")
                    self.ica_process_service.visualize_ica(ica_components, sampling_rate, colormap)
            
            # Update status less frequently to avoid spam
            if hasattr(self, '_last_status_update'):
                if time.time() - self._last_status_update < 2.0:  # Only update every 2 seconds
                    return
            
            self.status_message.emit(message)
            self._last_status_update = time.time()
            
        except Exception as e:
            logging.error(f"Error handling real-time ICA update: {e}")

    def _on_realtime_status_changed(self, is_active: bool, message: str) -> None:
        """Handle real-time status change."""
        try:
            self.ica_widget.set_realtime_active(is_active, message)
            self.status_message.emit(message)
        except Exception as e:
            logging.error(f"Error handling real-time status change: {e}")

    def _on_realtime_error(self, error_message: str) -> None:
        """Handle real-time ICA error."""
        self.error_message.emit("Real-time ICA Error", error_message)
        # Auto-disable real-time mode on error
        self.ica_widget.set_realtime_active(False, "Error occurred")

    def _on_visualization_ready(self, success: bool, message: str) -> None:
        """Handle ICA visualization readiness from process service."""
        if success:
            self.status_message.emit(message)
        else:
            self.error_message.emit("ICA Error", message)

    def _handle_ica_export_overview(self) -> None:
        """Handle ICA overview export request using local export service."""
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
                
                # Start export process using local export service
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
        """Handle export all ICA images request using local export service."""
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
            
            # Start export process using local export service
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
            # Convert EEG channel indices to data array indices
            selected_eeg_indices = params.get("selected_channels", [])
            
            # Map EEG indices to actual data array indices
            metadata = self.processing_service._data_access_service.get_metadata()
            eeg_channels = metadata.get("eeg_channels", [])
            
            # Convert selected EEG indices to actual channel indices in data array
            actual_channel_indices = []
            
            if selected_eeg_indices:
                # Specific channels selected
                for eeg_idx in selected_eeg_indices:
                    if eeg_idx < len(eeg_channels):
                        actual_channel_idx = eeg_channels[eeg_idx]
                        actual_channel_indices.append(actual_channel_idx)
                channel_info = f"{len(selected_eeg_indices)} EEG channels"
            else:
                # No channels selected = all channels
                actual_channel_indices = []  # Empty list means all channels in processor
                channel_info = "all EEG channels"
            
            # Update params with actual channel indices
            params_with_mapped_channels = params.copy()
            params_with_mapped_channels["selected_channels"] = actual_channel_indices
            
            result = self.processing_service.apply_advanced_filters(params_with_mapped_channels)
            
            if result.get('success'):
                self.status_message.emit(
                    f"Advanced filters {'applied to' if params.get('apply') else 'removed from'} {channel_info}" if params.get('apply') else
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
            self.advanced_filter_widget.update_channels(channel_names)
            return True
        except Exception as e:
            self.error_message.emit("Channel List Update Error", str(e))
            return False

    def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        self._cleanup_export()
        self.export_service.cleanup()
        self.ica_realtime_service.cleanup()
        self.ica_process_service.cleanup()
        self.processing_service.cleanup()

    def _handle_wavelet_settings_changed(self, settings: Dict[str, Any]) -> None:
        """Handle dynamic wavelet settings change."""
        try:
            # Only update if inverse transform is applied
            if settings.get('inverse_applied', False):
                # Re-compute wavelet with new settings
                params = {
                    "wavelet_type": settings["type"],
                    "decomp_level": settings["level"],
                    "channel_selection": settings["channel"]
                }
                
                # Re-compute wavelet coefficients
                result = self.processing_service.compute_wavelet(params)
                
                if result.get('success'):
                    # Update wavelet widget with new results
                    self.wavelet_widget.set_wavelet_results(
                        result.get('coefficients'),
                        result.get('metadata')
                    )
                    
                    # Re-apply inverse transform with new coefficients
                    inverse_result = self.processing_service.apply_wavelet_inverse(True)
                    
                    if inverse_result.get('success'):
                        self.status_message.emit("Wavelet settings updated dynamically")
                    else:
                        self.error_message.emit("Wavelet Update Error", 
                                               inverse_result.get('error', "Failed to update wavelet"))
                else:
                    self.error_message.emit("Wavelet Update Error", 
                                           result.get('error', "Failed to recompute wavelet"))

        except Exception as e:
            self.error_message.emit("Wavelet Update Error", f"Error updating wavelet settings: {str(e)}")

    def _handle_downsampling_settings_changed(self, settings: Dict[str, Any]) -> None:
        """Handle dynamic downsampling settings change."""
        try:
            # Only update if downsampling is applied
            if settings.get('applied', False):
                params = {
                    "apply": True,
                    "factor": settings["factor"],
                    "operation": settings["aggregation"]
                }
                
                result = self.processing_service.apply_downsampling(params)
                
                if result.get('success'):
                    self.status_message.emit(
                        f"Downsampling settings updated dynamically (factor: {settings['factor']})"
                    )
                else:
                    self.error_message.emit("Downsampling Update Error", 
                                           result.get('error', "Failed to update downsampling"))

        except Exception as e:
            self.error_message.emit("Downsampling Update Error", f"Error updating downsampling settings: {str(e)}")

    def _handle_advanced_filter_settings_changed(self, settings: Dict[str, Any]) -> None:
        """Handle dynamic advanced filter settings change."""
        try:
            # Only update if advanced filters are applied
            if settings.get('applied', False):
                # Map EEG indices to actual data indices
                selected_eeg_indices = settings.get("selected_channels", [])
                
                metadata = self.processing_service._data_access_service.get_metadata()
                eeg_channels = metadata.get("eeg_channels", [])
                
                # Convert selected EEG indices to actual channel indices
                actual_channel_indices = []
                
                if selected_eeg_indices:
                    # Specific channels selected
                    for eeg_idx in selected_eeg_indices:
                        if eeg_idx < len(eeg_channels):
                            actual_channel_idx = eeg_channels[eeg_idx]
                            actual_channel_indices.append(actual_channel_idx)
                    channel_info = f"{len(selected_eeg_indices)} EEG channels"
                else:
                    # No channels selected = all channels
                    actual_channel_indices = []
                    channel_info = "all EEG channels"
                
                params = {
                    "apply": True,
                    "filter_type": settings["filter_type"],
                    "window_function": settings["window_function"],
                    "low_cut": settings.get("low_cut", 1.0),
                    "high_cut": settings.get("high_cut", 50.0),
                    "order": settings.get("order", 4),
                    "ripple": settings.get("ripple", 1.0),  # Add ripple parameter
                    "selected_channels": actual_channel_indices,  # Use mapped indices
                }
                
                result = self.processing_service.apply_advanced_filters(params)
                
                if result.get('success'):
                    filter_type_name = [item[0] for item in FilterTypes.__dict__.items() 
                                       if hasattr(FilterTypes, item[0]) and 
                                       getattr(FilterTypes, item[0]) == settings["filter_type"]]
                    filter_name = filter_type_name[0] if filter_type_name else "Unknown"
                    
                    self.status_message.emit(
                        f"Advanced filter settings updated dynamically (type: {filter_name}, {channel_info})"
                    )
                else:
                    self.error_message.emit("Advanced Filter Update Error", 
                                           result.get('error', "Failed to update advanced filters"))

        except Exception as e:
            self.error_message.emit("Advanced Filter Update Error", f"Error updating advanced filter settings: {str(e)}")

    def _setup_processing_panel_reference(self) -> None:
        """Setup reference to processing panel for reading basic filter parameters."""
        try:
            # Try to get processing panel from parent hierarchy
            parent = self.parent()
            while parent:
                if hasattr(parent, 'processing_panel'):
                    self.advanced_filter_widget.set_processing_panel_reference(parent.processing_panel)
                    logging.info("Advanced filter widget connected to processing panel for dynamic parameters")
                    break
                parent = parent.parent()
        except Exception as e:
            logging.debug(f"Could not setup processing panel reference: {e}")