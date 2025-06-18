import logging
import multiprocessing as mp
import queue
import threading
import time
from typing import Any, Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal


class ExportService(QObject):
    """
    Service for exporting analysis results to various formats.
    
    This service manages the export processes and provides progress tracking.
    """
    
    # Signals for progress and completion
    progress_updated = pyqtSignal(int, str)
    export_completed = pyqtSignal(bool, str)

    def __init__(self) -> None:
        """Initialize the export service."""
        super().__init__()
        
        # Export process resources
        self._export_process = None
        self._export_queue = None
        
        # Export state
        self._is_exporting = False

    def export_ica_overview(
        self, 
        ica_components: Dict[str, Any], 
        colormap: str,
        sampling_rate: float,
        filename: str
    ) -> None:
        """
        Export ICA overview to file.
        
        Args:
            ica_components: Dictionary with ICA components
            colormap: Matplotlib colormap to use
            sampling_rate: Sampling rate of the data
            filename: Path to save the file
        """
        # Prepare export data
        export_data = {
            'ica_components': ica_components,
            'colormap': colormap,
            'sampling_rate': sampling_rate,
            'filename': filename
        }
        
        # Start export process
        self._start_export_process(export_data, 'enhanced_overview')

    def export_ica_components(
        self, 
        ica_components: Dict[str, Any], 
        colormap: str,
        sampling_rate: float,
        directory: str
    ) -> None:
        """
        Export all ICA components to directory.
        
        Args:
            ica_components: Dictionary with ICA components
            colormap: Matplotlib colormap to use
            sampling_rate: Sampling rate of the data
            directory: Directory to save the files
        """
        # Prepare export data
        export_data = {
            'ica_components': ica_components,
            'colormap': colormap,
            'sampling_rate': sampling_rate,
            'directory': directory
        }
        
        # Start export process
        self._start_export_process(export_data, 'enhanced_all_images')

    def check_export_progress(self) -> None:
        """Check progress from the export process."""
        try:
            if not self._export_queue or not self._is_exporting:
                return
                
            while not self._export_queue.empty():
                try:
                    message = self._export_queue.get_nowait()
                    
                    if message['type'] == 'progress':
                        self.progress_updated.emit(message['percent'], message['status'])
                    elif message['type'] == 'finished':
                        self.export_completed.emit(message['success'], message['message'])
                        return
                    elif message['type'] == 'error':
                        self.export_completed.emit(False, f"Export error: {message['error']}")
                        return
                        
                except queue.Empty:
                    break
                    
            # Check if process is still alive
            if self._export_process and not self._export_process.is_alive():
                # Process finished but no final message received
                self.export_completed.emit(False, "Export process ended unexpectedly")
                
        except Exception as e:
            logging.error(f"Error checking export progress: {e}")
            self.export_completed.emit(False, f"Error monitoring export: {str(e)}")

    def cancel_export(self) -> None:
        """Cancel the current export process."""
        if self._export_process and self._export_process.is_alive():
            self._export_process.terminate()
            self._export_process.join(timeout=5)
            if self._export_process.is_alive():
                self._export_process.kill()
        
        self._is_exporting = False

    def cleanup(self) -> None:
        """Clean up export process resources."""
        self.cancel_export()
        
        if self._export_queue:
            # Clean up queue
            try:
                while not self._export_queue.empty():
                    self._export_queue.get_nowait()
            except:
                pass
            self._export_queue = None

    def _start_export_process(self, export_data: Dict[str, Any], export_type: str) -> None:
        """Start the export process.
        
        Args:
            export_data: Data to export
            export_type: Type of export operation
        """
        try:
            # Clean up any previous export
            self.cleanup()
            
            # Create queue for communication with process
            self._export_queue = mp.Queue()
            
            # Set export state
            self._is_exporting = True

            # Start export process
            self._export_process = mp.Process(
                target=_export_worker_process,
                args=(export_data, export_type, self._export_queue)
            )
            self._export_process.start()

        except Exception as e:
            logging.error(f"Error starting export process: {e}")
            self.export_completed.emit(False, f"Failed to start export: {str(e)}")


# Worker functions for export
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
        
        # Calculate total steps (overview + matrices + components)
        total_steps = 1 + 2 + (ica_components["s"].shape[0] if "s" in ica_components else 0)
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