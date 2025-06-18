from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QScrollArea,
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
)

import numpy as np


class ICAVisualizationDialog(QDialog):
    """
    Dialog for visualizing ICA components.
    
    This dialog provides a scrollable view of ICA components with export capabilities.
    """
    
    # Signals for export requests
    export_overview_requested = pyqtSignal()
    export_all_requested = pyqtSignal()

    def __init__(
        self,
        ica_components: Dict[str, Any],
        sampling_rate: float,
        parent: Optional[Any] = None,
    ) -> None:
        """Initialize the ICA visualization dialog."""
        super().__init__(parent)
        
        self.ica_components = ica_components
        self.sampling_rate = sampling_rate
        
        self._setup_ui()
        self._create_visualization()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        # Setup dialog properties
        num_components = self.ica_components["num_components"]
        selected_channels = self.ica_components["selected_channels"]
        self.setWindowTitle(
            f"ICA Components Visualization - {num_components} Components on {len(selected_channels)} Channels"
        )
        self.setModal(False)
        self.resize(1400, 1000)
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Add export controls at the top
        export_layout = QHBoxLayout()
        
        # Colormap selection
        export_layout.addWidget(QLabel("Colormap:"))
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItem("Viridis", "viridis")
        self.colormap_combo.addItem("Plasma", "plasma")
        self.colormap_combo.addItem("Inferno", "inferno")
        self.colormap_combo.addItem("Magma", "magma")
        self.colormap_combo.addItem("Coolwarm", "coolwarm")
        self.colormap_combo.addItem("RdBu", "RdBu")
        self.colormap_combo.addItem("Spectral", "Spectral")
        self.colormap_combo.addItem("Jet", "jet")
        self.colormap_combo.currentTextChanged.connect(self._refresh_visualization)
        export_layout.addWidget(self.colormap_combo)
        
        export_layout.addStretch()
        
        # Export buttons
        export_overview_btn = QPushButton("Export Overview")
        export_overview_btn.clicked.connect(self._request_export_overview)
        export_layout.addWidget(export_overview_btn)
        
        export_all_btn = QPushButton("Export All Images")
        export_all_btn.clicked.connect(self._request_export_all)
        export_layout.addWidget(export_all_btn)
        
        main_layout.addLayout(export_layout)
        
        # Create scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create scrollable widget
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        # Set the scroll widget
        self.scroll_area.setWidget(self.scroll_widget)
        main_layout.addWidget(self.scroll_area)
        
        # Add instruction label
        instruction_label = QLabel(
            "Use mouse wheel to scroll • Click on any plot to view details • Export functions in the toolbar above"
        )
        instruction_label.setStyleSheet("color: #666666; font-style: italic; padding: 5px;")
        instruction_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(instruction_label)

    def _create_visualization(self) -> None:
        """Create the ICA visualization content."""
        # Import matplotlib with Qt5 backend
        import matplotlib
        matplotlib.use('Qt5Agg')
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        
        # Get component data
        num_components = self.ica_components["num_components"]
        
        # Get selected colormap
        colormap = self.colormap_combo.currentData()
        
        # Calculate layout
        plots_per_row = 2
        matrix_rows = 1
        component_rows = int(np.ceil(num_components / plots_per_row))
        total_rows = matrix_rows + component_rows
        
        # Create figure
        subplot_height = 4.0
        figure_width = 12
        total_figure_height = total_rows * subplot_height
        
        fig = plt.figure(figsize=(figure_width, total_figure_height))
        self.figure = fig
        
        plot_idx = 1
        
        # Plot matrices
        if "a" in self.ica_components:
            ax1 = fig.add_subplot(total_rows, 2, plot_idx)
            im1 = ax1.imshow(self.ica_components["a"], aspect="auto", cmap=colormap)
            ax1.set_title("Mixing Matrix (A)\n(Click to view details)", fontsize=14)
            ax1.set_xlabel("Components")
            ax1.set_ylabel("Channels")
            plt.colorbar(im1, ax=ax1, shrink=0.6)
            ax1.set_picker(True)
            ax1.matrix_type = "mixing"
            plot_idx += 1

        if "w" in self.ica_components:
            ax2 = fig.add_subplot(total_rows, 2, plot_idx)
            im2 = ax2.imshow(self.ica_components["w"], aspect="auto", cmap=colormap)
            ax2.set_title("Unmixing Matrix (W)\n(Click to view details)", fontsize=14)
            ax2.set_xlabel("Channels")
            ax2.set_ylabel("Components")
            plt.colorbar(im2, ax=ax2, shrink=0.6)
            ax2.set_picker(True)
            ax2.matrix_type = "unmixing"
            plot_idx += 1

        # Plot components
        if "s" in self.ica_components:
            s_data = self.ica_components["s"]
            time_vec = np.linspace(0, s_data.shape[1] / self.sampling_rate, s_data.shape[1])
            
            for i in range(min(num_components, s_data.shape[0])):
                component_row = (i // plots_per_row) + matrix_rows
                component_col = (i % plots_per_row)
                subplot_idx = (component_row * 2) + component_col + 1
                
                ax = fig.add_subplot(total_rows, 2, subplot_idx)
                ax.plot(time_vec, s_data[i, :], linewidth=1.2, color='#1f77b4')
                ax.set_title(f"Independent Component {i+1}\n(Click to view details)", fontsize=14, fontweight='bold')
                ax.set_xlabel("Time (s)", fontsize=12)
                ax.set_ylabel("Amplitude", fontsize=12)
                ax.grid(True, alpha=0.3)
                
                # Set reasonable y-limits
                data_std = np.std(s_data[i, :])
                data_mean = np.mean(s_data[i, :])
                ax.set_ylim(data_mean - 3*data_std, data_mean + 3*data_std)
                
                ax.tick_params(axis='both', which='major', labelsize=10)
                
                # Add click functionality
                ax.set_picker(True)
                ax.component_index = i
                ax.component_data = s_data[i, :]
                ax.time_vector = time_vec

        # Adjust layout
        plt.subplots_adjust(
            left=0.08, right=0.95, 
            top=0.95, bottom=0.05,
            hspace=0.3, wspace=0.25
        )
        
        # Add click event handler
        def on_plot_click(event):
            if event.inaxes is not None:
                ax = event.inaxes
                if hasattr(ax, 'component_index'):
                    self._show_component_detail(ax.component_index, ax.component_data, ax.time_vector)
                elif hasattr(ax, 'matrix_type'):
                    self._show_matrix_detail(ax.matrix_type)
        
        fig.canvas.mpl_connect('button_press_event', on_plot_click)
        
        # Create canvas
        canvas = FigureCanvas(fig)
        self.canvas = canvas
        
        # Set canvas size
        canvas_height = int(total_figure_height * 100)
        canvas.setMinimumHeight(canvas_height)
        canvas.setMinimumWidth(int(figure_width * 100))
        
        # Add to layout
        self.scroll_layout.addWidget(canvas)
        
        # Set scroll widget size
        self.scroll_widget.setMinimumHeight(canvas_height + 20)
        self.scroll_widget.setMinimumWidth(int(figure_width * 100) + 20)

    def _refresh_visualization(self) -> None:
        """Refresh the visualization with new colormap."""
        try:
            # Clear existing layout
            for i in reversed(range(self.scroll_layout.count())):
                child = self.scroll_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            # Recreate visualization
            self._create_visualization()
            
        except Exception as e:
            print(f"Error refreshing visualization: {e}")

    def _show_component_detail(self, component_index: int, component_data: np.ndarray, time_vector: np.ndarray) -> None:
        """Show detailed view of a component."""
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            
            # Create detail dialog
            detail_dialog = QDialog(self)
            detail_dialog.setWindowTitle(f"Component {component_index + 1} - Detail View")
            detail_dialog.setModal(False)
            detail_dialog.resize(1000, 700)
            
            layout = QVBoxLayout(detail_dialog)
            
            # Create export button
            export_layout = QHBoxLayout()
            export_btn = QPushButton("Export Component")
            export_btn.clicked.connect(lambda: self._export_single_component(
                component_index, component_data, time_vector
            ))
            export_layout.addWidget(export_btn)
            export_layout.addStretch()
            layout.addLayout(export_layout)
            
            # Create detailed plot
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # Time series plot
            ax1.plot(time_vector, component_data, linewidth=1.5, color='#1f77b4', alpha=0.8)
            ax1.set_title(f"Independent Component {component_index + 1} - Time Series", 
                         fontsize=16, fontweight='bold')
            ax1.set_xlabel("Time (s)", fontsize=12)
            ax1.set_ylabel("Amplitude", fontsize=12)
            ax1.grid(True, alpha=0.3)
            
            # Add statistics
            data_mean = np.mean(component_data)
            data_std = np.std(component_data)
            data_min = np.min(component_data)
            data_max = np.max(component_data)
            stats_text = f"Mean: {data_mean:.4f} | Std: {data_std:.4f} | Min: {data_min:.4f} | Max: {data_max:.4f}"
            ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, fontsize=10,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            # Power spectral density
            if self.sampling_rate > 0:
                try:
                    from scipy import signal
                    freqs, psd = signal.welch(component_data, self.sampling_rate, 
                                            nperseg=min(len(component_data)//4, 1024))
                    ax2.semilogy(freqs, psd, color='#ff7f0e', linewidth=1.5)
                    ax2.set_title(f"Component {component_index + 1} - Power Spectral Density", 
                                 fontsize=16, fontweight='bold')
                    ax2.set_xlabel("Frequency (Hz)", fontsize=12)
                    ax2.set_ylabel("Power/Frequency (dB/Hz)", fontsize=12)
                    ax2.grid(True, alpha=0.3)
                    ax2.set_xlim(0, min(50, self.sampling_rate/2))
                except ImportError:
                    ax2.text(0.5, 0.5, "Scipy not available\nCannot compute PSD", 
                            transform=ax2.transAxes, ha='center', va='center', fontsize=14)
                    ax2.set_title(f"Component {component_index + 1} - Power Spectral Density", fontsize=16)
            else:
                ax2.text(0.5, 0.5, "Cannot compute PSD\n(sampling rate unknown)", 
                        transform=ax2.transAxes, ha='center', va='center', fontsize=14)
                ax2.set_title(f"Component {component_index + 1} - Power Spectral Density", fontsize=16)
            
            plt.tight_layout()
            
            # Add to dialog
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)
            
            detail_dialog.show()
            
        except Exception as e:
            print(f"Error showing component detail: {e}")

    def _show_matrix_detail(self, matrix_type: str) -> None:
        """Show detailed view of a matrix."""
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            
            # Get matrix data
            if matrix_type == "mixing":
                matrix_data = self.ica_components["a"]
                title = "Mixing Matrix (A)"
                xlabel = "Components"
                ylabel = "Channels"
                description = "How components combine to form channels"
            else:  # unmixing
                matrix_data = self.ica_components["w"]
                title = "Unmixing Matrix (W)"
                xlabel = "Channels"
                ylabel = "Components"
                description = "How to extract components from channels"
            
            # Create detail dialog
            detail_dialog = QDialog(self)
            detail_dialog.setWindowTitle(f"{title} - Detail View")
            detail_dialog.setModal(False)
            detail_dialog.resize(1200, 600)
            
            layout = QVBoxLayout(detail_dialog)
            
            # Create export controls layout
            export_layout = QHBoxLayout()
            
            # Add colormap selection to detail dialog
            export_layout.addWidget(QLabel("Colormap:"))
            detail_colormap_combo = QComboBox()
            detail_colormap_combo.addItem("Viridis", "viridis")
            detail_colormap_combo.addItem("Plasma", "plasma")
            detail_colormap_combo.addItem("Inferno", "inferno")
            detail_colormap_combo.addItem("Magma", "magma")
            detail_colormap_combo.addItem("Coolwarm", "coolwarm")
            detail_colormap_combo.addItem("RdBu", "RdBu")
            detail_colormap_combo.addItem("Spectral", "Spectral")
            detail_colormap_combo.addItem("Jet", "jet")
            
            # Set current colormap from main dialog
            current_colormap = self.colormap_combo.currentData()
            for i in range(detail_colormap_combo.count()):
                if detail_colormap_combo.itemData(i) == current_colormap:
                    detail_colormap_combo.setCurrentIndex(i)
                    break
            
            export_layout.addWidget(detail_colormap_combo)
            export_layout.addStretch()
            
            # Export button
            export_btn = QPushButton(f"Export {matrix_type.title()} Matrix")
            export_btn.clicked.connect(lambda: self._export_single_matrix_with_colormap(
                matrix_type, matrix_data, detail_colormap_combo.currentData()
            ))
            export_layout.addWidget(export_btn)
            layout.addLayout(export_layout)
            
            # Create detailed plot with initial colormap
            def create_matrix_plot(colormap_name):
                # Clear existing plot if any
                for i in reversed(range(layout.count())):
                    item = layout.itemAt(i)
                    if item and item.widget() and hasattr(item.widget(), 'figure'):
                        item.widget().setParent(None)
                
                fig = plt.figure(figsize=(14, 6))
                
                # Create custom subplot layout
                ax1 = plt.subplot2grid((1, 3), (0, 0), colspan=2)  # Matrix takes 2/3 of width
                ax2 = plt.subplot2grid((1, 3), (0, 2), colspan=1)  # Histogram takes 1/3 of width
                
                # Matrix heatmap
                im = ax1.imshow(matrix_data, aspect="auto", cmap=colormap_name, interpolation='nearest')
                ax1.set_title(f"{title}\n{description}", fontsize=14, fontweight='bold')
                ax1.set_xlabel(xlabel, fontsize=12)
                ax1.set_ylabel(ylabel, fontsize=12)
                
                # Add colorbar
                cbar = plt.colorbar(im, ax=ax1, shrink=0.8)
                cbar.set_label('Weight', fontsize=12)
                
                # Add value annotations if matrix is small enough
                if matrix_data.shape[0] <= 8 and matrix_data.shape[1] <= 8:
                    for i in range(matrix_data.shape[0]):
                        for j in range(matrix_data.shape[1]):
                            ax1.text(j, i, f'{matrix_data[i, j]:.3f}', 
                                    ha='center', va='center', color='white', fontsize=10)
                
                # Matrix statistics
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
                
                # Add to dialog
                canvas = FigureCanvas(fig)
                layout.addWidget(canvas)
                
                return canvas
            
            # Create initial plot
            canvas = create_matrix_plot(current_colormap)
            
            # Connect colormap change to update plot
            def on_colormap_change():
                create_matrix_plot(detail_colormap_combo.currentData())
                # Update export function with new colormap
                export_btn.clicked.disconnect()
                export_btn.clicked.connect(lambda: self._export_single_matrix_with_colormap(
                    matrix_type, matrix_data, detail_colormap_combo.currentData()
                ))
            
            detail_colormap_combo.currentTextChanged.connect(on_colormap_change)
            
            detail_dialog.show()
            
        except Exception as e:
            print(f"Error showing matrix detail: {e}")

    def _request_export_overview(self) -> None:
        """Request export overview with current colormap."""
        try:
            from PyQt5.QtWidgets import QFileDialog, QProgressDialog, QApplication
            from PyQt5.QtCore import QTimer
            
            ica_components = self.ica_components
            if not ica_components:
                return

            # Open file save dialog
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save ICA Overview", "ica_overview.png", "PNG files (*.png)"
            )
            
            if filename:
                # Create progress dialog
                progress_dialog = QProgressDialog(
                    "Exporting ICA overview...", "Cancel", 0, 100, self
                )
                progress_dialog.setWindowTitle("Export Progress")
                progress_dialog.setModal(True)
                progress_dialog.show()
                
                # Use the worker process for export with current colormap
                export_data = {
                    'ica_components': ica_components,
                    'colormap': self.colormap_combo.currentData(),
                    'sampling_rate': self.sampling_rate,
                    'filename': filename
                }
                
                # Import worker functions directly with correct path
                import multiprocessing as mp
                from ....services.ica.export_service import _export_enhanced_overview_worker
                
                # Create a simple queue for this export
                progress_queue = mp.Queue()
                
                # Update progress to 25%
                progress_dialog.setValue(25)
                QApplication.processEvents()
                
                # Run export in separate process
                process = mp.Process(target=_export_enhanced_overview_worker, 
                                   args=(export_data, progress_queue))
                process.start()
                
                # Monitor progress
                def check_progress():
                    if not progress_queue.empty():
                        try:
                            result = progress_queue.get_nowait()
                            if result['type'] == 'finished':
                                progress_dialog.setValue(100)
                                if result['success']:
                                    progress_dialog.setLabelText("Overview exported successfully!")
                                else:
                                    progress_dialog.setLabelText(f"Export failed: {result.get('message', 'Unknown error')}")
                                QTimer.singleShot(1000, progress_dialog.close)
                                return
                            elif result['type'] == 'progress':
                                progress_dialog.setValue(result['percent'])
                                progress_dialog.setLabelText(result['status'])
                            elif result['type'] == 'error':
                                progress_dialog.setValue(100)
                                progress_dialog.setLabelText(f"Export failed: {result.get('error', 'Unknown error')}")
                                QTimer.singleShot(1000, progress_dialog.close)
                                return
                        except:
                            pass
                    
                    if process.is_alive():
                        QTimer.singleShot(100, check_progress)
                    else:
                        progress_dialog.setValue(100)
                        progress_dialog.setLabelText("Export completed")
                        QTimer.singleShot(1000, progress_dialog.close)
                
                check_progress()
                    
        except Exception as e:
            print(f"Error exporting overview: {e}")

    def _request_export_all(self) -> None:
        """Request export all with current colormap."""
        try:
            from PyQt5.QtWidgets import QFileDialog, QProgressDialog, QApplication
            from PyQt5.QtCore import QTimer
            
            ica_components = self.ica_components
            if not ica_components:
                return

            # Open directory selection dialog
            directory = QFileDialog.getExistingDirectory(
                self, "Select Directory to Save ICA Images", ""
            )
            
            if not directory:
                return

            # Create progress dialog
            progress_dialog = QProgressDialog(
                "Exporting ICA components...", "Cancel", 0, 100, self
            )
            progress_dialog.setWindowTitle("Export Progress")
            progress_dialog.setModal(True)
            progress_dialog.show()
            
            # Use the worker process for export with current colormap
            export_data = {
                'ica_components': ica_components,
                'colormap': self.colormap_combo.currentData(),
                'sampling_rate': self.sampling_rate,
                'directory': directory
            }
            
            # Import worker functions directly with correct path
            import multiprocessing as mp
            from ....services.ica.export_service import _export_enhanced_all_images_worker
            
            # Create a simple queue for this export
            progress_queue = mp.Queue()
            
            # Update progress to 5%
            progress_dialog.setValue(5)
            QApplication.processEvents()
            
            # Run export in separate process
            process = mp.Process(target=_export_enhanced_all_images_worker, 
                               args=(export_data, progress_queue))
            process.start()
            
            # Monitor progress
            def check_progress():
                if not progress_queue.empty():
                    try:
                        result = progress_queue.get_nowait()
                        if result['type'] == 'finished':
                            progress_dialog.setValue(100)
                            if result['success']:
                                progress_dialog.setLabelText("All images exported successfully!")
                            else:
                                progress_dialog.setLabelText(f"Export failed: {result.get('message', 'Unknown error')}")
                            QTimer.singleShot(1000, progress_dialog.close)
                            return
                        elif result['type'] == 'progress':
                            progress_dialog.setValue(result['percent'])
                            progress_dialog.setLabelText(result['status'])
                        elif result['type'] == 'error':
                            progress_dialog.setValue(100)
                            progress_dialog.setLabelText(f"Export failed: {result.get('error', 'Unknown error')}")
                            QTimer.singleShot(1000, progress_dialog.close)
                            return
                    except:
                        pass
                
                if process.is_alive():
                    QTimer.singleShot(100, check_progress)
                else:
                    progress_dialog.setValue(100)
                    progress_dialog.setLabelText("Export completed")
                    QTimer.singleShot(1000, progress_dialog.close)
            
            check_progress()
                
        except Exception as e:
            print(f"Error exporting all images: {e}")

    def _export_single_component(self, component_index: int, component_data: np.ndarray, time_vector: np.ndarray) -> None:
        """Export a single component to file with progress feedback."""
        try:
            from PyQt5.QtWidgets import QFileDialog, QProgressDialog, QApplication
            from PyQt5.QtCore import QTimer
            
            filename, _ = QFileDialog.getSaveFileName(
                self, f"Save Component {component_index + 1}", 
                f"ica_component_{component_index + 1}.png", "PNG files (*.png)"
            )
            
            if filename:
                # Create progress dialog
                progress_dialog = QProgressDialog(
                    f"Exporting component {component_index + 1}...", 
                    "Cancel", 0, 100, self
                )
                progress_dialog.setWindowTitle("Export Progress")
                progress_dialog.setModal(True)
                progress_dialog.show()
                
                # Use the worker process for export with current colormap
                export_data = {
                    'component_index': component_index,
                    'component_data': component_data,
                    'time_vector': time_vector,
                    'sampling_rate': self.sampling_rate,
                    'filename': filename,
                    'colormap': self.colormap_combo.currentData()
                }
                
                # Import worker functions directly
                import multiprocessing as mp
                
                # Create a simple queue for this single export
                progress_queue = mp.Queue()
                
                # Update progress to 50%
                progress_dialog.setValue(50)
                QApplication.processEvents()
                
                # Run export in separate process
                process = mp.Process(target=self._export_single_component_worker, 
                                   args=(export_data, progress_queue))
                process.start()
                
                # Monitor progress
                def check_progress():
                    if not progress_queue.empty():
                        try:
                            result = progress_queue.get_nowait()
                            if result['type'] == 'finished':
                                progress_dialog.setValue(100)
                                if result['success']:
                                    progress_dialog.setLabelText(f"Component {component_index + 1} exported successfully!")
                                else:
                                    progress_dialog.setLabelText(f"Export failed: {result.get('message', 'Unknown error')}")
                                QTimer.singleShot(1000, progress_dialog.close)
                                return
                            elif result['type'] == 'progress':
                                progress_dialog.setValue(result['percent'])
                                progress_dialog.setLabelText(result['status'])
                        except:
                            pass
                    
                    if process.is_alive():
                        QTimer.singleShot(100, check_progress)
                    else:
                        progress_dialog.setValue(100)
                        progress_dialog.setLabelText("Export completed")
                        QTimer.singleShot(1000, progress_dialog.close)
                
                check_progress()
                    
        except Exception as e:
            print(f"Error exporting component: {e}")

    def _export_single_matrix_with_colormap(self, matrix_type: str, matrix_data: np.ndarray, colormap: str) -> None:
        """Export a single matrix to file with specified colormap and progress feedback."""
        try:
            from PyQt5.QtWidgets import QFileDialog, QProgressDialog, QApplication
            from PyQt5.QtCore import QTimer
            
            filename, _ = QFileDialog.getSaveFileName(
                self, f"Save {matrix_type.title()} Matrix", 
                f"ica_{matrix_type}_matrix.png", "PNG files (*.png)"
            )
            
            if filename:
                # Create progress dialog
                progress_dialog = QProgressDialog(
                    f"Exporting {matrix_type} matrix...", 
                    "Cancel", 0, 100, self
                )
                progress_dialog.setWindowTitle("Export Progress")
                progress_dialog.setModal(True)
                progress_dialog.show()
                
                # Use the worker process for export
                export_data = {
                    'matrix_type': matrix_type,
                    'matrix_data': matrix_data,
                    'colormap': colormap,
                    'filename': filename
                }
                
                # Import worker functions directly
                import multiprocessing as mp
                
                # Create a simple queue for this single export
                progress_queue = mp.Queue()
                
                # Update progress to 50%
                progress_dialog.setValue(50)
                QApplication.processEvents()
                
                # Run export in separate process
                process = mp.Process(target=self._export_single_matrix_worker, 
                                   args=(export_data, progress_queue))
                process.start()
                
                # Monitor progress
                def check_progress():
                    if not progress_queue.empty():
                        try:
                            result = progress_queue.get_nowait()
                            if result['type'] == 'finished':
                                progress_dialog.setValue(100)
                                if result['success']:
                                    progress_dialog.setLabelText(f"{matrix_type.title()} matrix exported successfully!")
                                else:
                                    progress_dialog.setLabelText(f"Export failed: {result.get('message', 'Unknown error')}")
                                QTimer.singleShot(1000, progress_dialog.close)
                                return
                            elif result['type'] == 'progress':
                                progress_dialog.setValue(result['percent'])
                                progress_dialog.setLabelText(result['status'])
                        except:
                            pass
                    
                    if process.is_alive():
                        QTimer.singleShot(100, check_progress)
                    else:
                        progress_dialog.setValue(100)
                        progress_dialog.setLabelText("Export completed")
                        QTimer.singleShot(1000, progress_dialog.close)
                
                check_progress()
                    
        except Exception as e:
            print(f"Error exporting matrix: {e}")

    @staticmethod
    def _export_single_component_worker(export_data, progress_queue):
        """Worker function to export a single component."""
        try:
            # Configure matplotlib for non-GUI use
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np

            component_index = export_data['component_index']
            component_data = export_data['component_data']
            time_vector = export_data['time_vector']
            sampling_rate = export_data['sampling_rate']
            filename = export_data['filename']
            colormap = export_data.get('colormap', 'viridis')

            progress_queue.put({
                'type': 'progress',
                'percent': 50,
                'status': f'Exporting component {component_index + 1}...'
            })

            # Create larger figure for component
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9))
            
            # Main time series plot
            ax1.plot(time_vector, component_data, linewidth=1.5, color='#1f77b4', alpha=0.8)
            ax1.set_title(f"Independent Component {component_index + 1} - Time Series", fontsize=16, fontweight='bold')
            ax1.set_xlabel("Time (s)", fontsize=14)
            ax1.set_ylabel("Amplitude", fontsize=14)
            ax1.grid(True, alpha=0.3)
            ax1.tick_params(axis='both', which='major', labelsize=12)
            
            # Add statistics text
            data_mean = np.mean(component_data)
            data_std = np.std(component_data)
            data_min = np.min(component_data)
            data_max = np.max(component_data)
            stats_text = f"Mean: {data_mean:.4f} | Std: {data_std:.4f} | Min: {data_min:.4f} | Max: {data_max:.4f}"
            ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, fontsize=10, 
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            # Power spectral density
            if sampling_rate > 0:
                try:
                    from scipy import signal
                    freqs, psd = signal.welch(component_data, sampling_rate, nperseg=min(len(component_data)//4, 1024))
                    ax2.semilogy(freqs, psd, color='#ff7f0e', linewidth=1.5)
                    ax2.set_title(f"Component {component_index + 1} - Power Spectral Density", fontsize=16, fontweight='bold')
                    ax2.set_xlabel("Frequency (Hz)", fontsize=14)
                    ax2.set_ylabel("Power/Frequency (dB/Hz)", fontsize=14)
                    ax2.grid(True, alpha=0.3)
                    ax2.tick_params(axis='both', which='major', labelsize=12)
                    ax2.set_xlim(0, min(50, sampling_rate/2))
                except ImportError:
                    ax2.text(0.5, 0.5, "Scipy not available\nCannot compute PSD", 
                            transform=ax2.transAxes, ha='center', va='center', fontsize=14)
                    ax2.set_title(f"Component {component_index + 1} - Power Spectral Density", fontsize=16)
            else:
                ax2.text(0.5, 0.5, "Cannot compute PSD\n(sampling rate unknown)", 
                        transform=ax2.transAxes, ha='center', va='center', fontsize=14)
                ax2.set_title(f"Component {component_index + 1} - Power Spectral Density", fontsize=16)
            
            plt.tight_layout()
            fig.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close(fig)

            progress_queue.put({
                'type': 'finished',
                'success': True,
                'message': f"Component {component_index + 1} exported to {filename}"
            })

        except Exception as e:
            progress_queue.put({
                'type': 'error',
                'error': str(e)
            })

    @staticmethod
    def _export_single_matrix_worker(export_data, progress_queue):
        """Worker function to export a single matrix."""
        try:
            # Configure matplotlib for non-GUI use
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np

            matrix_type = export_data['matrix_type']
            matrix_data = export_data['matrix_data']
            colormap = export_data['colormap']
            filename = export_data['filename']

            progress_queue.put({
                'type': 'progress',
                'percent': 50,
                'status': f'Exporting {matrix_type} matrix...'
            })

            # Get matrix info
            if matrix_type == "mixing":
                title = "Mixing Matrix (A)"
                xlabel = "Components"
                ylabel = "Channels"
                description = "How components combine to form channels"
            else:  # unmixing
                title = "Unmixing Matrix (W)"
                xlabel = "Channels"
                ylabel = "Components"
                description = "How to extract components from channels"

            # Create figure with better proportions
            fig = plt.figure(figsize=(16, 7))
            
            # Create custom subplot layout
            ax1 = plt.subplot2grid((1, 3), (0, 0), colspan=2)  # Matrix takes 2/3 of width
            ax2 = plt.subplot2grid((1, 3), (0, 2), colspan=1)  # Histogram takes 1/3 of width
            
            # Matrix heatmap
            im = ax1.imshow(matrix_data, aspect="auto", cmap=colormap, interpolation='nearest')
            ax1.set_title(f"{title}\n{description}", fontsize=12, fontweight='bold')
            ax1.set_xlabel(xlabel, fontsize=12)
            ax1.set_ylabel(ylabel, fontsize=12)
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax1, shrink=0.8)
            cbar.set_label('Weight', fontsize=12)
            
            # Add value annotations if matrix is small enough
            if matrix_data.shape[0] <= 8 and matrix_data.shape[1] <= 8:
                for i in range(matrix_data.shape[0]):
                    for j in range(matrix_data.shape[1]):
                        ax1.text(j, i, f'{matrix_data[i, j]:.3f}', 
                                ha='center', va='center', color='white', fontsize=10)
            
            # Matrix statistics
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
            
            # Better spacing
            plt.subplots_adjust(left=0.08, right=0.95, bottom=0.1, top=0.85, wspace=0.3)
            
            fig.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close(fig)

            progress_queue.put({
                'type': 'finished',
                'success': True,
                'message': f"{matrix_type.title()} matrix exported to {filename}"
            })

        except Exception as e:
            progress_queue.put({
                'type': 'error',
                'error': str(e)
            })
