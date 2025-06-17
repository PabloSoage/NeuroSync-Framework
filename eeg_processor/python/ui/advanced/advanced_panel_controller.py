import logging
import multiprocessing as mp
import queue
import threading
import time
from typing import Any, Dict, List, Optional, Callable

import numpy as np
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QProgressDialog

from .widgets.ica_widget import ICAWidget
from .widgets.wavelet_widget import WaveletWidget
from .widgets.downsampling_widget import DownsamplingWidget
from .widgets.advanced_filter_widget import AdvancedFilterWidget
from ...services.data_access_service import DataAccessService


class AdvancedPanelController(QObject):
    """
    Controller for coordinating advanced processing widgets.
    
    This controller manages the interaction between different advanced processing
    widgets and handles the complex operations like ICA computation and export.
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
        
        # Get data access service
        self.data_access_service = DataAccessService.get_instance()
        self.data_access_service.set_filter_processor(self.processor_service)
        
        # Export process management
        self.export_process = None
        self.export_queue = None
        self.export_timer = None
        self.export_progress_dialog = None
        
        # Connect export signals
        self.export_progress.connect(self._update_export_progress)
        self.export_finished.connect(self._export_finished)
        
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
            metadata = self.data_access_service.get_metadata()
            channel_names = metadata.get("channel_names", [])
            eeg_channels = metadata.get("eeg_channels", [])

            # Generate default channel names if needed
            if not channel_names and eeg_channels:
                channel_names = [f"CH{i+1}" for i in range(len(eeg_channels))]
            elif not channel_names and not eeg_channels:
                # Try to get from collector service directly
                if hasattr(self.collector_service, 'get_eeg_channels'):
                    eeg_channels = self.collector_service.get_eeg_channels()
                    if eeg_channels:
                        channel_names = [f"CH{i+1}" for i in range(len(eeg_channels))]

            # Update widgets with channel information
            self.ica_widget.update_channels(channel_names)
            self.wavelet_widget.update_channels(channel_names)

        except Exception as e:
            logging.debug(f"Error initializing channel data: {e}")

    def _handle_ica_computation(self, params: Dict[str, Any]) -> None:
        """Handle ICA computation request."""
        try:
            # Get current data
            data, _ = self.data_access_service.get_current_data()
            if data.size == 0:
                self.error_message.emit("ICA Error", "No data available for ICA computation")
                return

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
            
            # Extract selected channels
            ica_data = data[selected_channels, :]
            
            # Ensure we have enough data
            min_samples = max(num_components * 100, 1000)
            if ica_data.shape[1] < min_samples:
                self.error_message.emit("ICA Error", f"Need at least {min_samples} samples for reliable ICA")
                return
            
            # Check minimum channels requirement
            if ica_data.shape[0] < 2:
                self.error_message.emit("ICA Error", "Need at least 2 channels for ICA")
                return
            
            if ica_data.shape[0] < 8:
                reply = QMessageBox.question(
                    self.parent(), 
                    "ICA Warning", 
                    f"ICA works best with at least 8-16 channels. You have {ica_data.shape[0]} channels.\n"
                    "Results may not be meaningful. Continue anyway?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return

            # Initialize processor if needed
            sampling_rate = self.collector_service.get_sampling_rate()
            if sampling_rate > 0 and (not hasattr(self.processor_service, "processor") or 
                                      self.processor_service.processor is None):
                self.processor_service.initialize_processor(sampling_rate)

            # Compute ICA
            w, k, a, s = self.processor_service.perform_ica(ica_data, num_components)
            
            if w is not None:
                ica_components = {
                    "w": w, "k": k, "a": a, "s": s,
                    "selected_channels": selected_channels,
                    "num_components": num_components
                }
                
                # Update ICA widget with results
                self.ica_widget.set_ica_results(ica_components)
                
                self.status_message.emit(
                    f"ICA computed successfully with {num_components} components on {len(selected_channels)} channels"
                )
            else:
                self.error_message.emit("ICA Error", "Failed to compute ICA components")

        except Exception as e:
            self.error_message.emit("ICA Error", f"Error computing ICA: {str(e)}")

    def _handle_ica_visualization(self, params: Dict[str, Any]) -> None:
        """Handle ICA visualization request."""
        try:
            ica_components = self.ica_widget.get_ica_results()
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
            ica_components = self.ica_widget.get_ica_results()
            if not ica_components:
                self.error_message.emit("Export Error", "No ICA components available")
                return

            # Open file save dialog
            filename, _ = QFileDialog.getSaveFileName(
                self.parent(), "Save ICA Overview", "ica_overview.png", "PNG files (*.png)"
            )
            
            if filename:
                # Start export process
                export_data = {
                    'ica_components': ica_components,
                    'colormap': self.ica_widget.get_colormap(),
                    'sampling_rate': self.collector_service.get_sampling_rate(),
                    'filename': filename
                }
                self._start_export_process(export_data, 'single_overview')
                
        except Exception as e:
            self.error_message.emit("Export Error", f"Error exporting overview: {str(e)}")

    def _handle_ica_export_all(self) -> None:
        """Handle export all ICA images request."""
        try:
            ica_components = self.ica_widget.get_ica_results()
            if not ica_components:
                self.error_message.emit("Export Error", "No ICA components available")
                return

            # Open directory selection dialog
            directory = QFileDialog.getExistingDirectory(
                self.parent(), "Select Directory to Save ICA Images", ""
            )
            
            if not directory:
                return

            # Prepare data for export process
            export_data = {
                'ica_components': ica_components,
                'colormap': self.ica_widget.get_colormap(),
                'sampling_rate': self.collector_service.get_sampling_rate(),
                'directory': directory
            }

            # Start export in separate process
            self._start_export_process(export_data, 'all_images')

        except Exception as e:
            self.error_message.emit("Export Error", f"Error starting export: {str(e)}")

    def _handle_ica_export_overview_with_colormap(self, colormap: str) -> None:
        """Handle ICA overview export request with specific colormap."""
        try:
            ica_components = self.ica_widget.get_ica_results()
            if not ica_components:
                self.error_message.emit("Export Error", "No ICA components available")
                return

            # Open file save dialog
            filename, _ = QFileDialog.getSaveFileName(
                self.parent(), "Save ICA Overview", "ica_overview.png", "PNG files (*.png)"
            )
            
            if filename:
                # Start export process with specified colormap
                export_data = {
                    'ica_components': ica_components,
                    'colormap': colormap,
                    'sampling_rate': self.collector_service.get_sampling_rate(),
                    'filename': filename
                }
                self._start_export_process(export_data, 'enhanced_overview')
                
        except Exception as e:
            self.error_message.emit("Export Error", f"Error exporting overview: {str(e)}")

    def _handle_ica_export_all_with_colormap(self, colormap: str) -> None:
        """Handle export all ICA images request with specific colormap."""
        try:
            ica_components = self.ica_widget.get_ica_results()
            if not ica_components:
                self.error_message.emit("Export Error", "No ICA components available")
                return

            # Open directory selection dialog
            directory = QFileDialog.getExistingDirectory(
                self.parent(), "Select Directory to Save ICA Images", ""
            )
            
            if not directory:
                return

            # Prepare data for export process with specified colormap
            export_data = {
                'ica_components': ica_components,
                'colormap': colormap,
                'sampling_rate': self.collector_service.get_sampling_rate(),
                'directory': directory
            }

            # Start export in separate process
            self._start_export_process(export_data, 'enhanced_all_images')

        except Exception as e:
            self.error_message.emit("Export Error", f"Error starting export: {str(e)}")

    def _handle_wavelet_computation(self, params: Dict[str, Any]) -> None:
        """Handle wavelet computation request."""
        try:
            # Get current data
            data, _ = self.data_access_service.get_current_data()
            if data.size == 0:
                self.error_message.emit("Wavelet Error", "No data available for wavelet computation")
                return

            # Extract parameters
            wavelet_type = params["wavelet_type"]
            decomp_level = params["decomp_level"]
            channel_selection = params["channel_selection"]

            # Select data for wavelet analysis
            if channel_selection < data.shape[0]:
                wavelet_data = data[channel_selection:channel_selection+1, :]
            else:
                self.error_message.emit("Wavelet Error", "Selected channel not available")
                return

            # Initialize processor if needed
            sampling_rate = self.collector_service.get_sampling_rate()
            if sampling_rate > 0 and (not hasattr(self.processor_service, "processor") or 
                                      self.processor_service.processor is None):
                self.processor_service.initialize_processor(sampling_rate)

            # Compute wavelet coefficients
            coefficients, metadata = self.processor_service.compute_wavelet_coefficients(
                wavelet_data, wavelet_type, decomp_level
            )

            if coefficients is not None:
                # Update wavelet widget with results
                self.wavelet_widget.set_wavelet_results(coefficients, metadata)
                
                # Store in data access service for stream processing
                self.data_access_service._wavelet_coefficients = coefficients
                self.data_access_service._wavelet_metadata = metadata
                
                self.status_message.emit("Wavelet transform computed successfully")
            else:
                self.error_message.emit("Wavelet Error", "Failed to compute wavelet transform")

        except Exception as e:
            self.error_message.emit("Wavelet Error", f"Error computing wavelet transform: {str(e)}")

    def _handle_wavelet_inverse(self, apply: bool) -> None:
        """Handle wavelet inverse transform request."""
        try:
            if not self.wavelet_widget.has_wavelet_results():
                self.error_message.emit("Wavelet Error", "No wavelet coefficients available. Compute wavelet first.")
                return

            if apply:
                # Apply inverse wavelet transform to the stream
                processing_settings = {
                    "wavelet": {
                        "inverse_enabled": True,
                    }
                }
                
                self.data_access_service.enable_advanced_processing(True, processing_settings)
                self.status_message.emit("Inverse wavelet transform applied to data stream")
                
            else:
                # Remove inverse wavelet transform
                self.data_access_service.enable_advanced_processing(False)
                self.status_message.emit("Inverse wavelet transform removed from data stream")

        except Exception as e:
            self.error_message.emit("Wavelet Error", f"Error applying inverse wavelet: {str(e)}")

    def _handle_downsampling(self, params: Dict[str, Any]) -> None:
        """Handle downsampling request."""
        try:
            apply = params["apply"]
            
            if apply:
                # Apply downsampling to the stream
                processing_settings = {
                    "downsampling": {
                        "enabled": True,
                        "factor": params["factor"],
                        "operation": params["operation"],
                    }
                }
                
                self.data_access_service.enable_advanced_processing(True, processing_settings)
                self.status_message.emit(f"Downsampling (factor {params['factor']}) applied to data stream")
                
            else:
                # Remove downsampling
                self.data_access_service.enable_advanced_processing(False)
                self.status_message.emit("Downsampling removed from data stream")

        except Exception as e:
            self.error_message.emit("Downsampling Error", f"Error applying downsampling: {str(e)}")

    def _handle_advanced_filters(self, params: Dict[str, Any]) -> None:
        """Handle advanced filters request."""
        try:
            apply = params["apply"]
            
            if apply:
                # Apply advanced filters to the stream
                processing_settings = {
                    "advanced_filters": {
                        "enabled": True,
                        "filter_type": params["filter_type"],
                        "low_cut": params.get("low_cut", 1.0),
                        "high_cut": params.get("high_cut", 50.0),
                        "order": params.get("order", 4),
                    }
                }
                
                self.data_access_service.enable_advanced_processing(True, processing_settings)
                self.status_message.emit(f"Advanced filters applied to data stream")
                
            else:
                # Remove advanced filters
                self.data_access_service.enable_advanced_processing(False)
                self.status_message.emit("Advanced filters removed from data stream")

        except Exception as e:
            self.error_message.emit("Filtering Error", f"Error applying advanced filters: {str(e)}")

    def _start_export_process(self, export_data: Dict[str, Any], export_type: str):
        """Start the export process with progress monitoring."""
        try:
            # Create progress dialog
            self.export_progress_dialog = QProgressDialog(
                "Exporting ICA images...", "Cancel", 0, 100, self.parent()
            )
            self.export_progress_dialog.setWindowTitle("Export Progress")
            self.export_progress_dialog.setModal(True)
            self.export_progress_dialog.canceled.connect(self._cancel_export)
            self.export_progress_dialog.show()

            # Create queue for communication with process
            self.export_queue = mp.Queue()

            # Start export process
            self.export_process = mp.Process(
                target=_export_worker_process,
                args=(export_data, export_type, self.export_queue)
            )
            self.export_process.start()

            # Start timer to monitor progress
            self.export_timer = QTimer()
            self.export_timer.timeout.connect(self._check_export_progress)
            self.export_timer.start(100)  # Check every 100ms

            self.status_message.emit("Export started in background process...")

        except Exception as e:
            self.error_message.emit("Export Error", f"Error starting export process: {str(e)}")
            self._cleanup_export()

    def _check_export_progress(self):
        """Check export progress from the worker process."""
        try:
            while not self.export_queue.empty():
                try:
                    message = self.export_queue.get_nowait()
                    
                    if message['type'] == 'progress':
                        self.export_progress.emit(message['percent'], message['status'])
                    elif message['type'] == 'finished':
                        self.export_finished.emit(message['success'], message['message'])
                        return
                    elif message['type'] == 'error':
                        self.export_finished.emit(False, f"Export error: {message['error']}")
                        return
                        
                except queue.Empty:
                    break
                    
            # Check if process is still alive
            if self.export_process and not self.export_process.is_alive():
                # Process finished but no final message received
                self.export_finished.emit(False, "Export process ended unexpectedly")
                
        except Exception as e:
            logging.error(f"Error checking export progress: {e}")
            self.export_finished.emit(False, f"Error monitoring export: {str(e)}")

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
        if self.export_process and self.export_process.is_alive():
            self.export_process.terminate()
            self.export_process.join(timeout=5)
            if self.export_process.is_alive():
                self.export_process.kill()
        
        self._cleanup_export()
        self.status_message.emit("Export cancelled")

    def _cleanup_export(self):
        """Clean up export process resources."""
        if self.export_timer:
            self.export_timer.stop()
            self.export_timer = None
            
        if self.export_progress_dialog:
            self.export_progress_dialog.close()
            self.export_progress_dialog = None
            
        if self.export_process:
            if self.export_process.is_alive():
                self.export_process.join(timeout=1)
            self.export_process = None
            
        if self.export_queue:
            # Clean up queue
            try:
                while not self.export_queue.empty():
                    self.export_queue.get_nowait()
            except:
                pass
            self.export_queue = None

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
        """Cleanup controller resources."""
        self._cleanup_export()


# Worker functions for export (moved from advanced_panel.py)
def _export_worker_process(export_data: Dict[str, Any], export_type: str, progress_queue: mp.Queue):
    """Worker process for exporting ICA images."""
    try:
        # Configure matplotlib for non-GUI use
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        import os

        if export_type == 'all_images':
            _export_all_images_worker(export_data, progress_queue)
        elif export_type == 'enhanced_all_images':
            _export_enhanced_all_images_worker(export_data, progress_queue)
        elif export_type == 'single_component':
            _export_single_component_worker(export_data, progress_queue)
        elif export_type == 'single_matrix':
            _export_single_matrix_worker(export_data, progress_queue)
        elif export_type == 'single_overview':
            _export_single_overview_worker(export_data, progress_queue)
        elif export_type == 'enhanced_overview':
            _export_enhanced_overview_worker(export_data, progress_queue)
        else:
            progress_queue.put({
                'type': 'error',
                'error': f'Unknown export type: {export_type}'
            })

    except Exception as e:
        progress_queue.put({
            'type': 'error',
            'error': str(e)
        })


def _export_single_overview_worker(export_data: Dict[str, Any], progress_queue: mp.Queue):
    """Worker function to export a single overview."""
    try:
        progress_queue.put({
            'type': 'progress',
            'percent': 50,
            'status': 'Creating overview...'
        })

        ica_components = export_data['ica_components']
        colormap = export_data['colormap']
        sampling_rate = export_data['sampling_rate']
        filename = export_data['filename']

        _create_complete_overview_figure_worker(ica_components, colormap, sampling_rate, filename)

        progress_queue.put({
            'type': 'finished',
            'success': True,
            'message': f"ICA overview exported to {filename}"
        })

    except Exception as e:
        progress_queue.put({
            'type': 'error',
            'error': str(e)
        })


def _export_enhanced_overview_worker(export_data: Dict[str, Any], progress_queue: mp.Queue):
    """Worker function to export an enhanced overview with detailed components."""
    try:
        progress_queue.put({
            'type': 'progress',
            'percent': 25,
            'status': 'Creating enhanced overview...'
        })

        ica_components = export_data['ica_components']
        colormap = export_data['colormap']
        sampling_rate = export_data['sampling_rate']
        filename = export_data['filename']

        _create_enhanced_overview_figure_worker(ica_components, colormap, sampling_rate, filename, progress_queue)

        progress_queue.put({
            'type': 'finished',
            'success': True,
            'message': f"Enhanced ICA overview exported to {filename}"
        })

    except Exception as e:
        progress_queue.put({
            'type': 'error',
            'error': str(e)
        })


def _export_all_images_worker(export_data: Dict[str, Any], progress_queue: mp.Queue):
    """Worker function to export all ICA images."""
    import matplotlib.pyplot as plt
    import numpy as np
    import os

    try:
        ica_components = export_data['ica_components']
        colormap = export_data['colormap']
        sampling_rate = export_data['sampling_rate']
        directory = export_data['directory']

        num_components = ica_components["num_components"]
        current_step = 0

        # Step 1: Save the complete overview
        progress_queue.put({
            'type': 'progress',
            'percent': int((current_step / total_steps) * 100),
            'status': 'Creating complete overview...'
        })

        overview_path = os.path.join(directory, "ica_complete_overview.png")
        _create_complete_overview_figure_worker(ica_components, colormap, sampling_rate, overview_path)
        current_step += 1

        # Step 2: Save individual component plots
        if "s" in ica_components:
            s_data = ica_components["s"]
            time_vec = np.linspace(0, s_data.shape[1] / sampling_rate, s_data.shape[1])
            
            for i in range(s_data.shape[0]):
                progress_queue.put({
                    'type': 'progress',
                    'percent': int((current_step / total_steps) * 100),
                    'status': f'Exporting component {i+1}/{s_data.shape[0]}...'
                })

                fig_comp, ax = plt.subplots(1, 1, figsize=(12, 6))
                ax.plot(time_vec, s_data[i, :], linewidth=1.2, color='#1f77b4')
                ax.set_title(f"Independent Component {i+1}", fontsize=14, fontweight='bold')
                ax.set_xlabel("Time (s)", fontsize=12)
                ax.set_ylabel("Amplitude", fontsize=12)
                ax.grid(True, alpha=0.3)
                
                # Add statistics
                data_mean = np.mean(s_data[i, :])
                data_std = np.std(s_data[i, :])
                data_min = np.min(s_data[i, :])
                data_max = np.max(s_data[i, :])
                stats_text = f"Mean: {data_mean:.4f} | Std: {data_std:.4f} | Min: {data_min:.4f} | Max: {data_max:.4f}"
                ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10, 
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
                
                plt.tight_layout()
                
                comp_path = os.path.join(directory, f"ica_component_{i+1}.png")
                fig_comp.savefig(comp_path, dpi=300, bbox_inches='tight')
                plt.close(fig_comp)
                current_step += 1

        # Step 3: Save matrix details
        for matrix_name, matrix_key in [("mixing", "a"), ("unmixing", "w")]:
            if matrix_key in ica_components:
                progress_queue.put({
                    'type': 'progress',
                    'percent': int((current_step / total_steps) * 100),
                    'status': f'Exporting {matrix_name} matrix...'
                })

                matrix_data = ica_components[matrix_key]
                
                fig_matrix, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
                
                # Matrix heatmap
                im = ax1.imshow(matrix_data, aspect="auto", cmap=colormap, interpolation='nearest')
                title = f"{'Mixing' if matrix_key == 'a' else 'Unmixing'} Matrix ({matrix_key.upper()})"
                ax1.set_title(title, fontsize=14, fontweight='bold')
                ax1.set_xlabel("Components" if matrix_key == "a" else "Channels", fontsize=12)
                ax1.set_ylabel("Channels" if matrix_key == "a" else "Components", fontsize=12)
                
                # Add colorbar
                cbar = plt.colorbar(im, ax=ax1, shrink=0.8)
                cbar.set_label('Weight', fontsize=12)
                
                # Matrix statistics histogram
                ax2.hist(matrix_data.flatten(), bins=30, alpha=0.7, color='skyblue', edgecolor='black')
                ax2.set_title("Weight Distribution", fontsize=14, fontweight='bold')
                ax2.set_xlabel("Weight Value", fontsize=12)
                ax2.set_ylabel("Frequency", fontsize=12)
                ax2.grid(True, alpha=0.3)
                
                # Add statistics
                stats_text = f"Shape: {matrix_data.shape}\n"
                stats_text += f"Mean: {np.mean(matrix_data):.4f}\n"
                stats_text += f"Std: {np.std(matrix_data):.4f}\n"
                stats_text += f"Min: {np.min(matrix_data):.4f}\n"
                stats_text += f"Max: {np.max(matrix_data):.4f}"
                
                ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes, fontsize=10,
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
                
                plt.tight_layout()
                
                matrix_path = os.path.join(directory, f"ica_{matrix_name}_matrix.png")
                fig_matrix.savefig(matrix_path, dpi=300, bbox_inches='tight')
                plt.close(fig_matrix)
                current_step += 1

        # Export completed successfully
        progress_queue.put({
            'type': 'finished',
            'success': True,
            'message': f"All ICA images exported successfully to {directory}"
        })

    except Exception as e:
        progress_queue.put({
            'type': 'error',
            'error': str(e)
        })


def _export_enhanced_all_images_worker(export_data: Dict[str, Any], progress_queue: mp.Queue):
    """Worker function to export all ICA images with enhanced detail."""
    import matplotlib.pyplot as plt
    import numpy as np
    import os

    try:
        ica_components = export_data['ica_components']
        colormap = export_data['colormap']
        sampling_rate = export_data['sampling_rate']
        directory = export_data['directory']

        num_components = ica_components["num_components"]
        
        # Calculate total steps for progress (overview + components + matrices)
        total_steps = 1 + num_components + 2
        current_step = 0

        # Step 1: Save the overview
        progress_queue.put({
            'type': 'progress',
            'percent': int((current_step / total_steps) * 100),
            'status': 'Creating overview...'
        })

        overview_path = os.path.join(directory, "ica_overview.png")
        _create_enhanced_overview_figure_worker(ica_components, colormap, sampling_rate, overview_path)
        current_step += 1

        # Step 2: Save component plots (with PSD)
        if "s" in ica_components:
            s_data = ica_components["s"]
            time_vec = np.linspace(0, s_data.shape[1] / sampling_rate, s_data.shape[1])
            
            for i in range(s_data.shape[0]):
                progress_queue.put({
                    'type': 'progress',
                    'percent': int((current_step / total_steps) * 100),
                    'status': f'Exporting component {i+1}/{s_data.shape[0]}...'
                })

                # Create component plot (time series + PSD)
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9))
                
                # Time series plot
                ax1.plot(time_vec, s_data[i, :], linewidth=1.5, color='#1f77b4', alpha=0.8)
                ax1.set_title(f"Independent Component {i+1} - Time Series", fontsize=16, fontweight='bold')
                ax1.set_xlabel("Time (s)", fontsize=14)
                ax1.set_ylabel("Amplitude", fontsize=14)
                ax1.grid(True, alpha=0.3)
                ax1.tick_params(axis='both', which='major', labelsize=12)
                
                # Add statistics
                data_mean = np.mean(s_data[i, :])
                data_std = np.std(s_data[i, :])
                data_min = np.min(s_data[i, :])
                data_max = np.max(s_data[i, :])
                stats_text = f"Mean: {data_mean:.4f} | Std: {data_std:.4f} | Min: {data_min:.4f} | Max: {data_max:.4f}"
                ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, fontsize=10,
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
                
                # Power spectral density
                if sampling_rate > 0:
                    try:
                        from scipy import signal
                        freqs, psd = signal.welch(s_data[i, :], sampling_rate, nperseg=min(len(s_data[i, :])//4, 1024))
                        ax2.semilogy(freqs, psd, color='#ff7f0e', linewidth=1.5)
                        ax2.set_title(f"Component {i+1} - Power Spectral Density", fontsize=16, fontweight='bold')
                        ax2.set_xlabel("Frequency (Hz)", fontsize=14)
                        ax2.set_ylabel("Power/Frequency (dB/Hz)", fontsize=14)
                        ax2.grid(True, alpha=0.3)
                        ax2.tick_params(axis='both', which='major', labelsize=12)
                        ax2.set_xlim(0, min(50, sampling_rate/2))
                    except ImportError:
                        ax2.text(0.5, 0.5, "Scipy not available\nCannot compute PSD", 
                                transform=ax2.transAxes, ha='center', va='center', fontsize=14)
                        ax2.set_title(f"Component {i+1} - Power Spectral Density", fontsize=16)
                else:
                    ax2.text(0.5, 0.5, "Cannot compute PSD\n(sampling rate unknown)", 
                            transform=ax2.transAxes, ha='center', va='center', fontsize=14)
                    ax2.set_title(f"Component {i+1} - Power Spectral Density", fontsize=16)
                
                plt.tight_layout()
                
                comp_path = os.path.join(directory, f"ica_component_{i+1}.png")
                fig.savefig(comp_path, dpi=300, bbox_inches='tight')
                plt.close(fig)
                current_step += 1

        # Step 3: Save matrix
        for matrix_name, matrix_key in [("mixing", "a"), ("unmixing", "w")]:
            if matrix_key in ica_components:
                progress_queue.put({
                    'type': 'progress',
                    'percent': int((current_step / total_steps) * 100),
                    'status': f'Exporting {matrix_name} matrix...'
                })

                matrix_data = ica_components[matrix_key]
                
                fig_matrix, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
                
                # Matrix heatmap
                im = ax1.imshow(matrix_data, aspect="auto", cmap=colormap, interpolation='nearest')
                title = f"{'Mixing' if matrix_key == 'a' else 'Unmixing'} Matrix ({matrix_key.upper()})"
                ax1.set_title(title, fontsize=14, fontweight='bold')
                ax1.set_xlabel("Components" if matrix_key == "a" else "Channels", fontsize=12)
                ax1.set_ylabel("Channels" if matrix_key == "a" else "Components", fontsize=12)
                
                # Add colorbar
                cbar = plt.colorbar(im, ax=ax1, shrink=0.8)
                cbar.set_label('Weight', fontsize=12)
                
                # Matrix statistics histogram
                ax2.hist(matrix_data.flatten(), bins=30, alpha=0.7, color='skyblue', edgecolor='black')
                ax2.set_title("Weight Distribution", fontsize=14, fontweight='bold')
                ax2.set_xlabel("Weight Value", fontsize=12)
                ax2.set_ylabel("Frequency", fontsize=12)
                ax2.grid(True, alpha=0.3)
                
                # Add statistics
                stats_text = f"Shape: {matrix_data.shape}\n"
                stats_text += f"Mean: {np.mean(matrix_data):.4f}\n"
                stats_text += f"Std: {np.std(matrix_data):.4f}\n"
                stats_text += f"Min: {np.min(matrix_data):.4f}\n"
                stats_text += f"Max: {np.max(matrix_data):.4f}"
                
                ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes, fontsize=10,
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
                
                plt.tight_layout()
                
                matrix_path = os.path.join(directory, f"ica_{matrix_name}_matrix.png")
                fig_matrix.savefig(matrix_path, dpi=300, bbox_inches='tight')
                plt.close(fig_matrix)
                current_step += 1

        # Export completed successfully
        progress_queue.put({
            'type': 'finished',
            'success': True,
            'message': f"All ICA images exported successfully to {directory}"
        })

    except Exception as e:
        progress_queue.put({
            'type': 'error',
            'error': str(e)
        })


def _create_complete_overview_figure_worker(ica_components, colormap, sampling_rate, save_path):
    """Create a complete overview figure showing ALL components in worker process."""
    import matplotlib.pyplot as plt
    import numpy as np
    
    num_components = ica_components["num_components"]
    
    # Create overview with all components
    # Calculate layout: matrices + all components in a grid
    cols = 4  # 4 columns for better layout
    matrix_slots = 2  # 2 slots for matrices
    total_plots = matrix_slots + num_components
    rows = int(np.ceil(total_plots / cols))
    
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 3))
    if rows == 1:
        axes = axes.reshape(1, -1)
    axes = axes.flatten()
    
    fig.suptitle(f"Complete ICA Analysis - {num_components} Components", fontsize=16)
    
    plot_idx = 0
    
    # Plot mixing matrix (A)
    if "a" in ica_components and plot_idx < len(axes):
        im1 = axes[plot_idx].imshow(ica_components["a"], aspect="auto", cmap=colormap)
        axes[plot_idx].set_title("Mixing Matrix (A)")
        axes[plot_idx].set_xlabel("Components")
        axes[plot_idx].set_ylabel("Channels")
        plt.colorbar(im1, ax=axes[plot_idx], shrink=0.6)
        plot_idx += 1

    # Plot unmixing matrix (W)
    if "w" in ica_components and plot_idx < len(axes):
        im2 = axes[plot_idx].imshow(ica_components["w"], aspect="auto", cmap=colormap)
        axes[plot_idx].set_title("Unmixing Matrix (W)")
        axes[plot_idx].set_xlabel("Channels")
        axes[plot_idx].set_ylabel("Components")
        plt.colorbar(im2, ax=axes[plot_idx], shrink=0.6)
        plot_idx += 1

    # Plot ALL independent components
    if "s" in ica_components:
        s_data = ica_components["s"]
        time_vec = np.linspace(0, s_data.shape[1] / sampling_rate, s_data.shape[1])
        
        for i in range(min(num_components, s_data.shape[0])):
            if plot_idx < len(axes):
                axes[plot_idx].plot(time_vec, s_data[i, :], linewidth=1.2, color='#1f77b4')
                axes[plot_idx].set_title(f"IC {i+1}")
                axes[plot_idx].set_xlabel("Time (s)")
                axes[plot_idx].set_ylabel("Amplitude")
                axes[plot_idx].grid(True, alpha=0.3)
                plot_idx += 1

    # Hide unused subplots
    for i in range(plot_idx, len(axes)):
        axes[i].set_visible(False)

    plt.tight_layout()
    fig.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


def _create_enhanced_overview_figure_worker(ica_components, colormap, sampling_rate, save_path, progress_queue=None):
    """Create an enhanced overview figure with detailed components and matrices."""
    import matplotlib.pyplot as plt
    import numpy as np
    
    num_components = ica_components["num_components"]
    
    if progress_queue:
        progress_queue.put({
            'type': 'progress',
            'percent': 50,
            'status': 'Generating overview plots...'
        })
    
    # Calculate layout: matrices + all components in a 4-column grid
    cols = 4  # 4 columns for better horizontal layout
    matrix_slots = 2  # 2 slots for matrices
    total_plots = matrix_slots + num_components
    rows = int(np.ceil(total_plots / cols))
    
    # Create figure
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 3))
    if rows == 1:
        axes = axes.reshape(1, -1)
    axes = axes.flatten()
    
    fig.suptitle(f"Enhanced ICA Analysis - {num_components} Components", fontsize=16, fontweight='bold')
    
    plot_idx = 0
    
    # Plot mixing matrix (A) in first slot
    if "a" in ica_components and plot_idx < len(axes):
        im1 = axes[plot_idx].imshow(ica_components["a"], aspect="auto", cmap=colormap)
        axes[plot_idx].set_title("Mixing Matrix (A)", fontsize=12, fontweight='bold')
        axes[plot_idx].set_xlabel("Components")
        axes[plot_idx].set_ylabel("Channels")
        plt.colorbar(im1, ax=axes[plot_idx], shrink=0.6)
        plot_idx += 1

    # Plot unmixing matrix (W) in second slot
    if "w" in ica_components and plot_idx < len(axes):
        im2 = axes[plot_idx].imshow(ica_components["w"], aspect="auto", cmap=colormap)
        axes[plot_idx].set_title("Unmixing Matrix (W)", fontsize=12, fontweight='bold')
        axes[plot_idx].set_xlabel("Channels")
        axes[plot_idx].set_ylabel("Components")
        plt.colorbar(im2, ax=axes[plot_idx], shrink=0.6)
        plot_idx += 1

    # Plot components
    if "s" in ica_components:
        s_data = ica_components["s"]
        time_vec = np.linspace(0, s_data.shape[1] / sampling_rate, s_data.shape[1])
        
        for i in range(min(num_components, s_data.shape[0])):
            if plot_idx < len(axes):
                axes[plot_idx].plot(time_vec, s_data[i, :], linewidth=1.5, color='#1f77b4', alpha=0.8)
                axes[plot_idx].set_title(f"Independent Component {i+1}", fontsize=12, fontweight='bold')
                axes[plot_idx].set_xlabel("Time (s)", fontsize=10)
                axes[plot_idx].set_ylabel("Amplitude", fontsize=10)
                axes[plot_idx].grid(True, alpha=0.3)
                
                # Set reasonable y-limits
                data_std = np.std(s_data[i, :])
                data_mean = np.mean(s_data[i, :])
                axes[plot_idx].set_ylim(data_mean - 3*data_std, data_mean + 3*data_std)
                
                # Add compact statistics
                stats_text = f"μ={data_mean:.3f}, σ={data_std:.3f}"
                axes[plot_idx].text(0.02, 0.98, stats_text, transform=axes[plot_idx].transAxes, fontsize=8,
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
                
                axes[plot_idx].tick_params(axis='both', which='major', labelsize=9)
                plot_idx += 1

    # Hide unused subplots
    for i in range(plot_idx, len(axes)):
        axes[i].set_visible(False)

    if progress_queue:
        progress_queue.put({
            'type': 'progress',
            'percent': 90,
            'status': 'Finalizing overview...'
        })

    plt.tight_layout()
    fig.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
