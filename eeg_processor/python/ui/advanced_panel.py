import logging
from typing import Any, Optional, Dict, List

import numpy as np
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QGridLayout, QMessageBox, QWidget, QDoubleSpinBox, QFileDialog,
)
from brainflow.data_filter import (
    FilterTypes,
    AggOperations,
    WindowOperations,
    WaveletTypes,
)

from .base_panel import BasePanel
from ..utils.help_system import HelpButton


class AdvancedProcessingPanel(BasePanel):
    """Panel for advanced signal processing operations."""

    def __init__(
        self,
        collector_service: Any,
        processor_service: Any,
        parent: Optional[Any] = None,
    ) -> None:
        """Initialize the advanced processing panel."""
        super().__init__(parent)
        self.collector_service = collector_service
        self.processor_service = processor_service

        # Get DataAccessService instance for advanced processing
        from ..services.data_access_service import DataAccessService
        self.data_access_service = DataAccessService.get_instance()

        # Set processor service in data access service
        self.data_access_service.set_filter_processor(self.processor_service)

        # Channel management
        self.channel_names: List[str] = []
        self.ica_selected_channels: List[int] = []

        # State tracking
        self.ica_computed = False
        self.ica_components = None
        self.wavelet_computed = False
        self.wavelet_coefficients = None
        self.wavelet_metadata = None
        self.advanced_filters_applied = False
        self.downsampling_applied = False

        # Setup UI components
        self.setup_ica_section()
        self.setup_wavelet_section()
        self.setup_downsampling_section()
        self.setup_advanced_filtering_section()

        # Initialize channel data
        self._initialize_channel_data()

        # Add stretch to push everything to the top
        self.layout.addStretch()

    def setup_ica_section(self) -> None:
        """Set up ICA section."""
        ica_group = QGroupBox("Independent Component Analysis (ICA)")
        ica_layout = QVBoxLayout(ica_group)

        # Add help button for ICA
        ica_header_layout = QHBoxLayout()
        ica_header_layout.addWidget(QLabel("ICA Configuration"))
        ica_header_layout.addWidget(HelpButton("ica", self))
        ica_header_layout.addStretch()
        ica_layout.addLayout(ica_header_layout)

        # ICA Parameters
        ica_params_layout = QVBoxLayout()
        
        # Number of components
        components_layout = QHBoxLayout()
        components_layout.addWidget(QLabel("Number of Components:"))
        self.ica_components_spin = QSpinBox()
        self.ica_components_spin.setRange(1, 16)
        self.ica_components_spin.setValue(2)
        components_layout.addWidget(self.ica_components_spin)
        components_layout.addStretch()
        ica_params_layout.addLayout(components_layout)

        # Channel selection - SIMPLIFIED approach
        channel_layout = QVBoxLayout()
        channel_layout.addWidget(QLabel("Channel Selection:"))
        
        # Channel selection button and info
        channel_selection_layout = QHBoxLayout()
        self.ica_channel_select_btn = QPushButton("Select Channels")
        self.ica_channel_select_btn.clicked.connect(self._open_ica_channel_selection)
        channel_selection_layout.addWidget(self.ica_channel_select_btn)
        
        self.ica_channel_info_label = QLabel("All channels")
        self.ica_channel_info_label.setStyleSheet("color: #AAAAAA; font-style: italic;")
        channel_selection_layout.addWidget(self.ica_channel_info_label)
        channel_selection_layout.addStretch()
        
        channel_layout.addLayout(channel_selection_layout)
        ica_params_layout.addLayout(channel_layout)
        
        ica_layout.addLayout(ica_params_layout)

        # ICA Control buttons (REMOVED colormap and export from here)
        ica_buttons_layout = QHBoxLayout()
        self.compute_ica_btn = QPushButton("Compute ICA")
        self.compute_ica_btn.clicked.connect(self.compute_ica)
        self.compute_ica_btn.setEnabled(False)
        ica_buttons_layout.addWidget(self.compute_ica_btn)

        self.view_ica_components_btn = QPushButton("View ICA Components")
        self.view_ica_components_btn.clicked.connect(self.view_ica_components)
        self.view_ica_components_btn.setEnabled(False)
        ica_buttons_layout.addWidget(self.view_ica_components_btn)

        ica_layout.addLayout(ica_buttons_layout)

        self.layout.addWidget(ica_group)

    def setup_wavelet_section(self) -> None:
        """Set up wavelet transform section."""
        wavelet_group = QGroupBox("Wavelet Transforms")
        wavelet_layout = QVBoxLayout(wavelet_group)

        # Add help button for Wavelet
        wavelet_header_layout = QHBoxLayout()
        wavelet_header_layout.addWidget(QLabel("Wavelet Analysis"))
        wavelet_header_layout.addWidget(HelpButton("wavelet", self))
        wavelet_header_layout.addStretch()
        wavelet_layout.addLayout(wavelet_header_layout)

        # Wavelet Parameters
        wavelet_params_layout = QGridLayout()

        wavelet_params_layout.addWidget(QLabel("Wavelet Type:"), 0, 0)
        self.wavelet_type_combo = QComboBox()
        self.wavelet_type_combo.addItem("DB4", WaveletTypes.DB4)
        self.wavelet_type_combo.addItem("DB5", WaveletTypes.DB5)
        self.wavelet_type_combo.addItem("DB6", WaveletTypes.DB6)
        self.wavelet_type_combo.addItem("BIOR3_9", WaveletTypes.BIOR3_9)
        self.wavelet_type_combo.addItem("HAAR", WaveletTypes.HAAR)
        wavelet_params_layout.addWidget(self.wavelet_type_combo, 0, 1)

        wavelet_params_layout.addWidget(QLabel("Decomposition Level:"), 0, 2)
        self.wavelet_level_spin = QSpinBox()
        self.wavelet_level_spin.setRange(1, 8)
        self.wavelet_level_spin.setValue(3)
        wavelet_params_layout.addWidget(self.wavelet_level_spin, 0, 3)

        wavelet_params_layout.addWidget(QLabel("Channel:"), 1, 0)
        self.wavelet_channel_combo = QComboBox()
        # Channels will be populated when connected to a board
        wavelet_params_layout.addWidget(self.wavelet_channel_combo, 1, 1)

        wavelet_layout.addLayout(wavelet_params_layout)

        # Wavelet Control buttons
        wavelet_buttons_layout = QHBoxLayout()
        self.compute_wavelet_btn = QPushButton("Compute Wavelet Transform")
        self.compute_wavelet_btn.clicked.connect(self.compute_wavelet)
        self.compute_wavelet_btn.setEnabled(False)
        wavelet_buttons_layout.addWidget(self.compute_wavelet_btn)

        self.inverse_wavelet_btn = QPushButton("Apply Inverse Transform")
        self.inverse_wavelet_btn.clicked.connect(self.apply_inverse_wavelet)
        self.inverse_wavelet_btn.setEnabled(False)
        wavelet_buttons_layout.addWidget(self.inverse_wavelet_btn)

        wavelet_layout.addLayout(wavelet_buttons_layout)

        self.layout.addWidget(wavelet_group)

    def setup_downsampling_section(self) -> None:
        """Set up downsampling section."""
        downsample_group = QGroupBox("Downsampling")
        downsample_layout = QVBoxLayout(downsample_group)

        # Add help button for Downsampling
        downsample_header_layout = QHBoxLayout()
        downsample_header_layout.addWidget(QLabel("Downsampling Configuration"))
        downsample_header_layout.addWidget(HelpButton("downsampling", self))
        downsample_header_layout.addStretch()
        downsample_layout.addLayout(downsample_header_layout)

        # Downsampling Parameters
        downsample_params_layout = QHBoxLayout()

        downsample_params_layout.addWidget(QLabel("Factor:"))
        self.downsample_factor_spin = QSpinBox()
        self.downsample_factor_spin.setRange(2, 10)
        self.downsample_factor_spin.setValue(2)
        downsample_params_layout.addWidget(self.downsample_factor_spin)

        downsample_params_layout.addWidget(QLabel("Aggregation Method:"))
        self.downsample_agg_combo = QComboBox()
        self.downsample_agg_combo.addItem("Mean", AggOperations.MEAN)
        self.downsample_agg_combo.addItem("Median", AggOperations.MEDIAN)
        self.downsample_agg_combo.addItem("Each", AggOperations.EACH)
        downsample_params_layout.addWidget(self.downsample_agg_combo)

        downsample_layout.addLayout(downsample_params_layout)

        # Downsampling Control buttons
        downsample_buttons_layout = QHBoxLayout()
        self.apply_downsample_btn = QPushButton("Apply Downsampling")
        self.apply_downsample_btn.clicked.connect(self.apply_downsampling)
        self.apply_downsample_btn.setEnabled(False)
        downsample_buttons_layout.addWidget(self.apply_downsample_btn)

        downsample_layout.addLayout(downsample_buttons_layout)

        self.layout.addWidget(downsample_group)

    def setup_advanced_filtering_section(self) -> None:
        """Set up advanced filtering section."""
        adv_filter_group = QGroupBox("Advanced Filtering Options")
        adv_filter_layout = QVBoxLayout(adv_filter_group)

        # Filter Type Selection
        filter_type_layout = QHBoxLayout()
        filter_type_layout.addWidget(QLabel("Filter Type:"))
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItem("Butterworth", FilterTypes.BUTTERWORTH)
        self.filter_type_combo.addItem("Chebyshev Type 1", FilterTypes.CHEBYSHEV_TYPE_1)
        self.filter_type_combo.addItem("Bessel", FilterTypes.BESSEL)
        self.filter_type_combo.addItem(
            "Butterworth Zero Phase", FilterTypes.BUTTERWORTH_ZERO_PHASE
        )
        filter_type_layout.addWidget(self.filter_type_combo)

        filter_type_layout.addWidget(QLabel("Window Function:"))
        self.window_function_combo = QComboBox()
        self.window_function_combo.addItem("Hanning", WindowOperations.HANNING)
        self.window_function_combo.addItem("Hamming", WindowOperations.HAMMING)
        self.window_function_combo.addItem(
            "Blackman Harris", WindowOperations.BLACKMAN_HARRIS
        )
        self.window_function_combo.addItem("No Window", WindowOperations.NO_WINDOW)
        filter_type_layout.addWidget(self.window_function_combo)

        adv_filter_layout.addLayout(filter_type_layout)

        # Apply Advanced Filtering
        filter_buttons_layout = QHBoxLayout()
        self.apply_adv_filter_btn = QPushButton("Apply Advanced Filters")
        self.apply_adv_filter_btn.clicked.connect(self.apply_advanced_filters)
        self.apply_adv_filter_btn.setEnabled(False)
        filter_buttons_layout.addWidget(self.apply_adv_filter_btn)

        adv_filter_layout.addLayout(filter_buttons_layout)

        self.layout.addWidget(adv_filter_group)

    def _initialize_channel_data(self) -> None:
        """Initialize channel data from data service."""
        try:
            metadata = self.data_access_service.get_metadata()
            self.channel_names = metadata.get("channel_names", [])
            eeg_channels = metadata.get("eeg_channels", [])

            # Generate default channel names if needed
            if not self.channel_names and eeg_channels:
                self.channel_names = [f"CH{i+1}" for i in range(len(eeg_channels))]
            elif not self.channel_names and not eeg_channels:
                # Try to get from collector service directly
                if hasattr(self.collector_service, 'get_eeg_channels'):
                    eeg_channels = self.collector_service.get_eeg_channels()
                    if eeg_channels:
                        self.channel_names = [f"CH{i+1}" for i in range(len(eeg_channels))]

            # Initialize selected channels (all by default)
            if not self.ica_selected_channels and self.channel_names:
                self.ica_selected_channels = list(range(len(self.channel_names)))

            self._update_ica_channel_display()

        except Exception as e:
            logging.debug(f"Error initializing channel data: {e}")

    def _open_ica_channel_selection(self) -> None:
        """Open channel selection dialog for ICA."""
        if not self.channel_names:
            self.show_error(
                "Channel Selection", "No channels available. Start streaming first."
            )
            return

        from .mne.widgets.channel_selection_dialog import ChannelSelectionDialog
        from PyQt5.QtWidgets import QDialog

        dialog = ChannelSelectionDialog(
            channel_names=self.channel_names,
            selected_channels=self.ica_selected_channels,
            parent=self,
        )
        dialog.setWindowTitle("Select Channels for ICA Analysis")

        if dialog.exec_() == QDialog.Accepted:
            self.ica_selected_channels = dialog.get_selected_channels()
            self._update_ica_channel_display()
            self.show_status(
                f"Selected {len(self.ica_selected_channels)} channels for ICA"
            )

    def _update_ica_channel_display(self) -> None:
        """Update the ICA channel selection display."""
        if not self.channel_names:
            self.ica_channel_info_label.setText("No channels available")
            self.ica_channel_select_btn.setEnabled(False)
            return
        
        self.ica_channel_select_btn.setEnabled(True)
        
        if not self.ica_selected_channels:
            self.ica_channel_info_label.setText("No channels selected")
        elif len(self.ica_selected_channels) == len(self.channel_names):
            self.ica_channel_info_label.setText("All channels selected")
        else:
            count = len(self.ica_selected_channels)
            total = len(self.channel_names)
            self.ica_channel_info_label.setText(f"{count}/{total} channels selected")

    def compute_ica(self) -> None:
        """Compute ICA components."""
        try:
            # Get current data
            data, _ = self.data_access_service.get_current_data()
            if data.size == 0:
                self.show_error("ICA Error", "No data available for ICA computation")
                return

            # Get number of components and channels
            num_components = self.ica_components_spin.value()
            
            # Use selected channels or all if none selected
            if not self.ica_selected_channels:
                self.show_error("ICA Error", "Please select at least one channel")
                return
            
            # Extract selected channels
            if len(self.ica_selected_channels) < num_components:
                self.show_error("ICA Error", f"Number of selected channels ({len(self.ica_selected_channels)}) must be >= number of components ({num_components})")
                return
            
            ica_data = data[self.ica_selected_channels, :]
            selected_channels = self.ica_selected_channels.copy()

            # Ensure we have enough data
            min_samples = max(num_components * 100, 1000)
            if ica_data.shape[1] < min_samples:
                self.show_error("ICA Error", f"Need at least {min_samples} samples for reliable ICA")
                return
            
            # Check minimum channels requirement
            if ica_data.shape[0] < 2:
                self.show_error("ICA Error", "Need at least 2 channels for ICA")
                return
            
            if ica_data.shape[0] < 8:
                reply = QMessageBox.question(
                    self, 
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
                self.ica_components = {
                    "w": w, "k": k, "a": a, "s": s,
                    "selected_channels": selected_channels,
                    "num_components": num_components
                }
                self.ica_computed = True
                self.view_ica_components_btn.setEnabled(True)
                
                self.show_status(f"ICA computed successfully with {num_components} components on {len(selected_channels)} channels")
            else:
                self.show_error("ICA Error", "Failed to compute ICA components")

        except Exception as e:
            self.show_error("ICA Error", f"Error computing ICA: {str(e)}")

    def view_ica_components(self) -> None:
        """View ICA components in a scrollable 2-column layout."""
        try:
            if not self.ica_computed or self.ica_components is None:
                self.show_error("ICA Error", "No ICA components available. Compute ICA first.")
                return

            # Create a new dialog window for the ICA visualization
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QWidget, QHBoxLayout
            from PyQt5.QtCore import Qt
            
            dialog = QDialog(self)
            # Move the analysis info to the window title
            num_components = self.ica_components["num_components"]
            selected_channels = self.ica_components["selected_channels"]
            dialog.setWindowTitle(f"ICA Components Visualization - {num_components} Components on {len(selected_channels)} Channels")
            dialog.setModal(False)  # Allow interaction with main window
            dialog.resize(1400, 1000)  # Increased size: wider and taller for better visibility
            
            # Store dialog reference for component detail windows
            self.ica_dialog = dialog
            
            # Create main layout
            main_layout = QVBoxLayout(dialog)
            
            # Add export controls at the top
            export_layout = QHBoxLayout()
            
            # Colormap selection
            export_layout.addWidget(QLabel("Colormap:"))
            self.ica_colormap_combo = QComboBox()
            self.ica_colormap_combo.addItem("Viridis", "viridis")
            self.ica_colormap_combo.addItem("Plasma", "plasma")
            self.ica_colormap_combo.addItem("Inferno", "inferno")
            self.ica_colormap_combo.addItem("Magma", "magma")
            self.ica_colormap_combo.addItem("Coolwarm", "coolwarm")
            self.ica_colormap_combo.addItem("RdBu", "RdBu")
            self.ica_colormap_combo.addItem("Spectral", "Spectral")
            self.ica_colormap_combo.addItem("Jet", "jet")
            # Connect to update visualization when colormap changes
            self.ica_colormap_combo.currentTextChanged.connect(lambda: self._refresh_ica_visualization())
            export_layout.addWidget(self.ica_colormap_combo)
            
            export_layout.addStretch()
            
            # Export buttons
            export_overview_btn = QPushButton("Export Overview")
            export_overview_btn.clicked.connect(self._export_ica_overview)
            export_layout.addWidget(export_overview_btn)
            
            export_all_btn = QPushButton("Export All Images")
            export_all_btn.clicked.connect(self._export_all_ica_images)
            export_layout.addWidget(export_all_btn)
            
            main_layout.addLayout(export_layout)
            
            # Create scroll area
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
            # Create scrollable widget with fixed size
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)
            scroll_layout.setContentsMargins(0, 0, 0, 0)
            
            # Store references for refresh functionality
            self.ica_scroll_widget = scroll_widget
            self.ica_scroll_layout = scroll_layout
            
            # Create the visualization
            self._create_ica_visualization_content()
            
            # Set the scroll widget
            scroll_area.setWidget(scroll_widget)
            main_layout.addWidget(scroll_area)
            
            # Add instruction label
            instruction_label = QLabel("Use mouse wheel to scroll • Click on any plot to view details • Export functions in the toolbar above")
            instruction_label.setStyleSheet("color: #666666; font-style: italic; padding: 5px;")
            instruction_label.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(instruction_label)
            
            # Show the dialog
            dialog.show()
            
            self.show_status(f"ICA components visualization displayed - {num_components} components in scrollable view")

        except Exception as e:
            self.show_error("ICA Error", f"Error displaying ICA components: {str(e)}")

    def _create_ica_visualization_content(self):
        """Create the actual ICA visualization content."""
        # Get component data
        num_components = self.ica_components["num_components"]
        selected_channels = self.ica_components["selected_channels"]
        
        # Import matplotlib with Qt5 backend
        import matplotlib
        matplotlib.use('Qt5Agg')
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        
        # Get selected colormap
        colormap = self.ica_colormap_combo.currentData()
        
        # Calculate number of rows needed (2 columns fixed + matrices at top)
        plots_per_row = 2
        matrix_rows = 1  # One row for both matrices side by side
        component_rows = int(np.ceil(num_components / plots_per_row))
        total_rows = matrix_rows + component_rows
        
        # Fixed subplot height - maintain this regardless of number of components
        subplot_height = 4.0  # inches per subplot row
        figure_width = 12
        total_figure_height = total_rows * subplot_height
        
        # Create the matplotlib figure with FIXED size - don't let it resize
        fig = plt.figure(figsize=(figure_width, total_figure_height))
        
        # Store figure reference for export functionality
        self.ica_figure = fig
        
        plot_idx = 1  # matplotlib subplot indices start at 1
        
        # First row: Mixing and Unmixing matrices side by side
        if "a" in self.ica_components:
            ax1 = fig.add_subplot(total_rows, 2, plot_idx)
            im1 = ax1.imshow(self.ica_components["a"], aspect="auto", cmap=colormap)
            ax1.set_title("Mixing Matrix (A)\n(Click to view details)", fontsize=14)
            ax1.set_xlabel("Components")
            ax1.set_ylabel("Channels")
            plt.colorbar(im1, ax=ax1, shrink=0.6)
            # Add click functionality for mixing matrix
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
            # Add click functionality for unmixing matrix
            ax2.set_picker(True)
            ax2.matrix_type = "unmixing"
            plot_idx += 1

        # Plot independent components in 2-column layout
        if "s" in self.ica_components:
            s_data = self.ica_components["s"]
            sampling_rate = self.collector_service.get_sampling_rate()
            time_vec = np.linspace(0, s_data.shape[1] / sampling_rate, s_data.shape[1])
            
            for i in range(min(num_components, s_data.shape[0])):
                # Calculate row and column for this component
                component_row = (i // plots_per_row) + matrix_rows  # Add matrix_rows offset
                component_col = (i % plots_per_row)
                
                # Calculate subplot index (row, col) -> index
                subplot_idx = (component_row * 2) + component_col + 1
                
                ax = fig.add_subplot(total_rows, 2, subplot_idx)
                ax.plot(time_vec, s_data[i, :], linewidth=1.2, color='#1f77b4')
                ax.set_title(f"Independent Component {i+1}\n(Click to view details)", fontsize=14, fontweight='bold')
                ax.set_xlabel("Time (s)", fontsize=12)
                ax.set_ylabel("Amplitude", fontsize=12)
                ax.grid(True, alpha=0.3)
                
                # Set reasonable y-limits to avoid extreme scaling
                data_std = np.std(s_data[i, :])
                data_mean = np.mean(s_data[i, :])
                ax.set_ylim(data_mean - 3*data_std, data_mean + 3*data_std)
                
                # Improve tick formatting
                ax.tick_params(axis='both', which='major', labelsize=10)
                
                # Add click functionality for components
                ax.set_picker(True)
                ax.component_index = i
                ax.component_data = s_data[i, :]
                ax.time_vector = time_vec

        # Adjust layout with proper spacing - this is key for maintaining subplot sizes
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
                    # Component plot clicked
                    self._show_component_detail(ax.component_index, ax.component_data, ax.time_vector)
                elif hasattr(ax, 'matrix_type'):
                    # Matrix plot clicked
                    self._show_matrix_detail(ax.matrix_type)
        
        # Connect the click event
        fig.canvas.mpl_connect('button_press_event', on_plot_click)
        
        # Create canvas with FIXED size
        canvas = FigureCanvas(fig)
        # Store canvas reference
        self.ica_canvas = canvas
        
        # IMPORTANT: Set minimum size to maintain figure dimensions
        canvas_height = int(total_figure_height * 100)  # Convert inches to pixels (approx)
        canvas.setMinimumHeight(canvas_height)
        canvas.setMinimumWidth(int(figure_width * 100))
        
        # Add canvas to scroll layout
        self.ica_scroll_layout.addWidget(canvas)
        
        # CRITICAL: Set the scroll widget's minimum size to match canvas
        self.ica_scroll_widget.setMinimumHeight(canvas_height + 20)  # Add some padding
        self.ica_scroll_widget.setMinimumWidth(int(figure_width * 100) + 20)

    def _refresh_ica_visualization(self):
        """Refresh the ICA visualization with new colormap."""
        try:
            # Clear the existing layout
            for i in reversed(range(self.ica_scroll_layout.count())):
                child = self.ica_scroll_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            # Recreate the visualization
            self._create_ica_visualization_content()
            
        except Exception as e:
            self.show_error("Refresh Error", f"Error refreshing visualization: {str(e)}")

    def _export_ica_overview(self):
        """Export only the overview figure."""
        try:
            # Open file save dialog
            from PyQt5.QtWidgets import QFileDialog
            filename, _ = QFileDialog.getSaveFileName(
                self.ica_dialog, "Save ICA Overview", "ica_overview.png", "PNG files (*.png)"
            )
            
            if filename:
                self.ica_figure.savefig(filename, dpi=300, bbox_inches='tight')
                self.show_status(f"ICA overview exported to {filename}")
                
        except Exception as e:
            self.show_error("Export Error", f"Error exporting overview: {str(e)}")

    def _export_all_ica_images(self):
        """Export all ICA images to a directory."""
        try:
            # Open directory selection dialog
            directory = QFileDialog.getExistingDirectory(
                self.ica_dialog, "Select Directory to Save ICA Images", ""
            )
            
            if not directory:
                return

            import matplotlib
            matplotlib.use('Agg')  # Use non-GUI backend for saving
            import matplotlib.pyplot as plt
            import os

            num_components = self.ica_components["num_components"]
            selected_channels = self.ica_components["selected_channels"]
            colormap = self.ica_colormap_combo.currentData()

            # Save the complete overview (including all components)
            overview_path = os.path.join(directory, "ica_complete_overview.png")
            self._create_complete_overview_figure(colormap, overview_path)

            # Save individual component plots
            if "s" in self.ica_components:
                s_data = self.ica_components["s"]
                sampling_rate = self.collector_service.get_sampling_rate()
                time_vec = np.linspace(0, s_data.shape[1] / sampling_rate, s_data.shape[1])
                
                for i in range(s_data.shape[0]):
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

            # Save matrix details
            for matrix_name, matrix_key in [("mixing", "a"), ("unmixing", "w")]:
                if matrix_key in self.ica_components:
                    matrix_data = self.ica_components[matrix_key]
                    
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

            # Reset matplotlib backend
            matplotlib.use('Qt5Agg')
            
            self.show_status(f"All ICA images exported successfully to {directory}")

        except Exception as e:
            self.show_error("Export Error", f"Error exporting all ICA images: {str(e)}")

    def _create_complete_overview_figure(self, colormap, save_path):
        """Create a complete overview figure showing ALL components."""
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        num_components = self.ica_components["num_components"]
        
        # Create a comprehensive overview with all components
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
        if "a" in self.ica_components and plot_idx < len(axes):
            im1 = axes[plot_idx].imshow(self.ica_components["a"], aspect="auto", cmap=colormap)
            axes[plot_idx].set_title("Mixing Matrix (A)")
            axes[plot_idx].set_xlabel("Components")
            axes[plot_idx].set_ylabel("Channels")
            plt.colorbar(im1, ax=axes[plot_idx], shrink=0.6)
            plot_idx += 1

        # Plot unmixing matrix (W)
        if "w" in self.ica_components and plot_idx < len(axes):
            im2 = axes[plot_idx].imshow(self.ica_components["w"], aspect="auto", cmap=colormap)
            axes[plot_idx].set_title("Unmixing Matrix (W)")
            axes[plot_idx].set_xlabel("Channels")
            axes[plot_idx].set_ylabel("Components")
            plt.colorbar(im2, ax=axes[plot_idx], shrink=0.6)
            plot_idx += 1

        # Plot ALL independent components
        if "s" in self.ica_components:
            s_data = self.ica_components["s"]
            sampling_rate = self.collector_service.get_sampling_rate()
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

    def _show_component_detail(self, component_index: int, component_data: np.ndarray, time_vector: np.ndarray) -> None:
        """Show detailed view of a single ICA component."""
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            
            # Create detail dialog
            detail_dialog = QDialog(self.ica_dialog)
            detail_dialog.setWindowTitle(f"ICA Component {component_index + 1} - Detailed View")
            detail_dialog.resize(1200, 700)
            
            layout = QVBoxLayout(detail_dialog)
            
            # Add controls at the top
            controls_layout = QHBoxLayout()
            
            # Frequency range controls
            controls_layout.addWidget(QLabel("PSD Frequency Range:"))
            
            self.freq_min_spin = QDoubleSpinBox()
            self.freq_min_spin.setRange(0.1, 100.0)
            self.freq_min_spin.setValue(1.0)
            self.freq_min_spin.setSuffix(" Hz")
            controls_layout.addWidget(QLabel("Min:"))
            controls_layout.addWidget(self.freq_min_spin)
            
            self.freq_max_spin = QDoubleSpinBox()
            self.freq_max_spin.setRange(1.0, 200.0)
            self.freq_max_spin.setValue(50.0)
            self.freq_max_spin.setSuffix(" Hz")
            controls_layout.addWidget(QLabel("Max:"))
            controls_layout.addWidget(self.freq_max_spin)
            
            update_freq_btn = QPushButton("Update PSD Range")
            controls_layout.addWidget(update_freq_btn)
            
            controls_layout.addStretch()
            
            # Export this component button
            export_component_btn = QPushButton("Export This Component")
            export_component_btn.clicked.connect(lambda: self._export_single_component(component_index, component_data, time_vector))
            controls_layout.addWidget(export_component_btn)
            
            layout.addLayout(controls_layout)
            
            # Create larger figure for component
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9))
            
            # Store figure reference for export
            self.detail_figure = fig
            self.detail_component_index = component_index
            self.detail_component_data = component_data
            self.detail_time_vector = time_vector
            
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
            
            # Initial power spectral density
            def update_psd():
                ax2.clear()
                from scipy import signal
                sampling_rate = self.collector_service.get_sampling_rate()
                if sampling_rate > 0:
                    freqs, psd = signal.welch(component_data, sampling_rate, nperseg=min(len(component_data)//4, 1024))
                    ax2.semilogy(freqs, psd, color='#ff7f0e', linewidth=1.5)
                    ax2.set_title(f"Component {component_index + 1} - Power Spectral Density", fontsize=16, fontweight='bold')
                    ax2.set_xlabel("Frequency (Hz)", fontsize=14)
                    ax2.set_ylabel("Power/Frequency (dB/Hz)", fontsize=14)
                    ax2.grid(True, alpha=0.3)
                    ax2.tick_params(axis='both', which='major', labelsize=12)
                    
                    # Set frequency range
                    freq_min = self.freq_min_spin.value()
                    freq_max = self.freq_max_spin.value()
                    ax2.set_xlim(freq_min, min(freq_max, sampling_rate/2))
                else:
                    ax2.text(0.5, 0.5, "Cannot compute PSD\n(sampling rate unknown)", 
                            transform=ax2.transAxes, ha='center', va='center', fontsize=14)
                    ax2.set_title(f"Component {component_index + 1} - Power Spectral Density", fontsize=16)
                
                fig.canvas.draw()
            
            # Initial PSD
            update_psd()
            
            # Connect frequency update button
            update_freq_btn.clicked.connect(update_psd)
            
            plt.tight_layout()
            
            # Create canvas and add to dialog
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)
            
            # Show detail dialog
            detail_dialog.show()
            
        except Exception as e:
            self.show_error("Component Detail Error", f"Error showing component detail: {str(e)}")

    def _export_single_component(self, component_index, component_data, time_vector):
        """Export a single component figure."""
        try:
            # Open file save dialog
            from PyQt5.QtWidgets import QFileDialog
            filename, _ = QFileDialog.getSaveFileName(
                self, f"Save Component {component_index + 1}", 
                f"ica_component_{component_index + 1}.png", "PNG files (*.png)"
            )
            
            if filename:
                self.detail_figure.savefig(filename, dpi=300, bbox_inches='tight')
                self.show_status(f"Component {component_index + 1} exported to {filename}")
                
        except Exception as e:
            self.show_error("Export Error", f"Error exporting component: {str(e)}")

    def _show_matrix_detail(self, matrix_type: str) -> None:
        """Show detailed view of mixing or unmixing matrix."""
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
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
            detail_dialog = QDialog(self.ica_dialog)
            detail_dialog.setWindowTitle(f"{title} - Detailed View")
            detail_dialog.resize(1200, 600)
            
            layout = QVBoxLayout(detail_dialog)
            
            # Add controls at the top
            controls_layout = QHBoxLayout()
            
            # Colormap selection (MOVED HERE from main panel)
            controls_layout.addWidget(QLabel("Colormap:"))
            matrix_colormap_combo = QComboBox()
            matrix_colormap_combo.addItem("Viridis", "viridis")
            matrix_colormap_combo.addItem("Plasma", "plasma")
            matrix_colormap_combo.addItem("Inferno", "inferno")
            matrix_colormap_combo.addItem("Magma", "magma")
            matrix_colormap_combo.addItem("Coolwarm", "coolwarm")
            matrix_colormap_combo.addItem("RdBu", "RdBu")
            matrix_colormap_combo.addItem("Spectral", "Spectral")
            matrix_colormap_combo.addItem("Jet", "jet")
            # Set to match main colormap
            current_colormap = self.ica_colormap_combo.currentData()
            for i in range(matrix_colormap_combo.count()):
                if matrix_colormap_combo.itemData(i) == current_colormap:
                    matrix_colormap_combo.setCurrentIndex(i)
                    break
            controls_layout.addWidget(matrix_colormap_combo)
            
            controls_layout.addStretch()
            
            # Export matrix button
            export_matrix_btn = QPushButton("Export This Matrix")
            export_matrix_btn.clicked.connect(lambda: self._export_single_matrix(matrix_type, matrix_data, matrix_colormap_combo.currentData()))
            controls_layout.addWidget(export_matrix_btn)
            
            layout.addLayout(controls_layout)
            
            # Create figure with better proportions
            fig = plt.figure(figsize=(16, 7))
            
            # Store references for export and update
            self.matrix_detail_figure = fig
            self.matrix_detail_data = matrix_data
            self.matrix_detail_type = matrix_type
            
            def update_matrix_plot():
                fig.clear()
                
                # Create custom subplot layout - matrix gets more width
                ax1 = plt.subplot2grid((1, 3), (0, 0), colspan=2)  # Matrix takes 2/3 of width
                ax2 = plt.subplot2grid((1, 3), (0, 2), colspan=1)  # Histogram takes 1/3 of width
                
                current_colormap = matrix_colormap_combo.currentData()
                
                # Matrix heatmap
                im = ax1.imshow(matrix_data, aspect="auto", cmap=current_colormap, interpolation='nearest')
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
                
                fig.canvas.draw()
            
            # Initial plot
            update_matrix_plot()
            
            # Connect colormap changes
            matrix_colormap_combo.currentTextChanged.connect(lambda: update_matrix_plot())
            
            # Create canvas and add to dialog
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)
            
            # Show detail dialog
            detail_dialog.show()
            
        except Exception as e:
            self.show_error("Matrix Detail Error", f"Error showing matrix detail: {str(e)}")

    def _export_single_matrix(self, matrix_type, matrix_data, colormap):
        """Export a single matrix figure."""
        try:
            # Open file save dialog
            from PyQt5.QtWidgets import QFileDialog
            filename, _ = QFileDialog.getSaveFileName(
                self, f"Save {matrix_type.title()} Matrix", 
                f"ica_{matrix_type}_matrix.png", "PNG files (*.png)"
            )
            
            if filename:
                self.matrix_detail_figure.savefig(filename, dpi=300, bbox_inches='tight')
                self.show_status(f"{matrix_type.title()} matrix exported to {filename}")
                
        except Exception as e:
            self.show_error("Export Error", f"Error exporting matrix: {str(e)}")

    def compute_wavelet(self) -> None:
        """Compute wavelet transform."""
        try:
            # Get current data
            data, _ = self.data_access_service.get_current_data()
            if data.size == 0:
                self.show_error("Wavelet Error", "No data available for wavelet computation")
                return

            # Get wavelet parameters
            wavelet_type = self.wavelet_type_combo.currentData()
            decomp_level = self.wavelet_level_spin.value()
            channel_selection = self.wavelet_channel_combo.currentData()

            # Select data for wavelet analysis
            if channel_selection < data.shape[0]:
                wavelet_data = data[channel_selection:channel_selection+1, :]
            else:
                self.show_error("Wavelet Error", "Selected channel not available")
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
                self.wavelet_coefficients = coefficients
                self.wavelet_metadata = metadata
                self.wavelet_computed = True
                self.inverse_wavelet_btn.setEnabled(True)
                self.inverse_wavelet_btn.setText("Apply Inverse Transform")
                
                # Store in data access service for stream processing
                self.data_access_service._wavelet_coefficients = coefficients
                self.data_access_service._wavelet_metadata = metadata
                
                self.show_status("Wavelet transform computed successfully")
            else:
                self.show_error("Wavelet Error", "Failed to compute wavelet transform")

        except Exception as e:
            self.show_error("Wavelet Error", f"Error computing wavelet transform: {str(e)}")

    def apply_inverse_wavelet(self) -> None:
        """Apply or remove inverse wavelet transform."""
        try:
            if not self.wavelet_computed or self.wavelet_coefficients is None:
                self.show_error("Wavelet Error", "No wavelet coefficients available. Compute wavelet first.")
                return

            current_text = self.inverse_wavelet_btn.text()
            
            if current_text == "Apply Inverse Transform":
                # Apply inverse wavelet transform to the stream
                processing_settings = {
                    "wavelet": {
                        "inverse_enabled": True,
                    }
                }
                
                self.data_access_service.enable_advanced_processing(True, processing_settings)
                
                self.inverse_wavelet_btn.setText("Remove Inverse Transform")
                self.inverse_wavelet_btn.setStyleSheet("background-color: #AA3333; color: white;")
                self.show_status("Inverse wavelet transform applied to data stream")
                
            else:
                # Remove inverse wavelet transform
                self.data_access_service.enable_advanced_processing(False)
                
                self.inverse_wavelet_btn.setText("Apply Inverse Transform")
                self.inverse_wavelet_btn.setStyleSheet("")
                self.show_status("Inverse wavelet transform removed from data stream")

        except Exception as e:
            self.show_error("Wavelet Error", f"Error applying inverse wavelet: {str(e)}")

    def apply_downsampling(self) -> None:
        """Apply or remove downsampling to data stream."""
        try:
            current_text = self.apply_downsample_btn.text()
            
            if current_text == "Apply Downsampling":
                # Apply downsampling to the stream
                processing_settings = {
                    "downsampling": {
                        "enabled": True,
                        "factor": self.downsample_factor_spin.value(),
                        "operation": self.downsample_agg_combo.currentData(),
                    }
                }
                
                self.data_access_service.enable_advanced_processing(True, processing_settings)
                self.downsampling_applied = True
                
                self.apply_downsample_btn.setText("Remove Downsampling")
                self.apply_downsample_btn.setStyleSheet("background-color: #AA3333; color: white;")
                self.show_status(f"Downsampling (factor {self.downsample_factor_spin.value()}) applied to data stream")
                
            else:
                # Remove downsampling
                self.data_access_service.enable_advanced_processing(False)
                self.downsampling_applied = False
                
                self.apply_downsample_btn.setText("Apply Downsampling")
                self.apply_downsample_btn.setStyleSheet("")
                self.show_status("Downsampling removed from data stream")

        except Exception as e:
            self.show_error("Downsampling Error", f"Error applying downsampling: {str(e)}")

    def apply_advanced_filters(self) -> None:
        """Apply or remove advanced filters to data stream."""
        try:
            current_text = self.apply_adv_filter_btn.text()
            
            if current_text == "Apply Advanced Filters":
                # Apply advanced filters to the stream
                processing_settings = {
                    "advanced_filters": {
                        "enabled": True,
                        "filter_type": self.filter_type_combo.currentData(),
                        "low_cut": 1.0,  # Could be made configurable
                        "high_cut": 50.0,  # Could be made configurable
                        "order": 4,
                    }
                }
                
                self.data_access_service.enable_advanced_processing(True, processing_settings)
                self.advanced_filters_applied = True
                
                self.apply_adv_filter_btn.setText("Remove Advanced Filters")
                self.apply_adv_filter_btn.setStyleSheet("background-color: #AA3333; color: white;")
                
                filter_name = self.filter_type_combo.currentText()
                self.show_status(f"Advanced filters ({filter_name}) applied to data stream")
                
            else:
                # Remove advanced filters
                self.data_access_service.enable_advanced_processing(False)
                self.advanced_filters_applied = False
                
                self.apply_adv_filter_btn.setText("Apply Advanced Filters")
                self.apply_adv_filter_btn.setStyleSheet("")
                self.show_status("Advanced filters removed from data stream")

        except Exception as e:
            self.show_error("Filtering Error", f"Error applying advanced filters: {str(e)}")

    def compute_ica(self) -> None:
        """Compute ICA components."""
        try:
            # Get current data
            data, _ = self.data_access_service.get_current_data()
            if data.size == 0:
                self.show_error("ICA Error", "No data available for ICA computation")
                return

            # Get number of components and channels
            num_components = self.ica_components_spin.value()
            
            # Use selected channels or all if none selected
            if not self.ica_selected_channels:
                self.show_error("ICA Error", "Please select at least one channel")
                return
            
            # Extract selected channels
            if len(self.ica_selected_channels) < num_components:
                self.show_error("ICA Error", f"Number of selected channels ({len(self.ica_selected_channels)}) must be >= number of components ({num_components})")
                return
            
            ica_data = data[self.ica_selected_channels, :]
            selected_channels = self.ica_selected_channels.copy()

            # Ensure we have enough data
            min_samples = max(num_components * 100, 1000)
            if ica_data.shape[1] < min_samples:
                self.show_error("ICA Error", f"Need at least {min_samples} samples for reliable ICA")
                return
            
            # Check minimum channels requirement
            if ica_data.shape[0] < 2:
                self.show_error("ICA Error", "Need at least 2 channels for ICA")
                return
            
            if ica_data.shape[0] < 8:
                reply = QMessageBox.question(
                    self, 
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
                self.ica_components = {
                    "w": w, "k": k, "a": a, "s": s,
                    "selected_channels": selected_channels,
                    "num_components": num_components
                }
                self.ica_computed = True
                self.view_ica_components_btn.setEnabled(True)
                
                self.show_status(f"ICA computed successfully with {num_components} components on {len(selected_channels)} channels")
            else:
                self.show_error("ICA Error", "Failed to compute ICA components")

        except Exception as e:
            self.show_error("ICA Error", f"Error computing ICA: {str(e)}")

    def update_channel_lists(self, channel_names: List[str]) -> bool:
        """Update channel selection dropdowns from API call."""
        try:
            self.channel_names = channel_names.copy()
            
            # Reset ICA selected channels to all channels
            self.ica_selected_channels = list(range(len(self.channel_names)))
            self._update_ica_channel_display()
            
            # Update wavelet channel combo (existing functionality)
            current_wavelet_ch = self.wavelet_channel_combo.currentData()
            self.wavelet_channel_combo.clear()

            # Add channel options to wavelet combo
            for i, name in enumerate(channel_names):
                self.wavelet_channel_combo.addItem(name, i)

            # Try to restore previous selection for wavelet
            if current_wavelet_ch is not None:
                for i in range(self.wavelet_channel_combo.count()):
                    if self.wavelet_channel_combo.itemData(i) == current_wavelet_ch:
                        self.wavelet_channel_combo.setCurrentIndex(i)
                        break

            return True
        except Exception as e:
            self.show_error("Channel List Update Error", str(e))
            return False

    def enable_processing(self, enabled: bool) -> None:
        """Enable or disable advanced processing controls."""
        self.compute_ica_btn.setEnabled(enabled)
        self.compute_wavelet_btn.setEnabled(enabled)
        self.apply_downsample_btn.setEnabled(enabled)
        self.apply_adv_filter_btn.setEnabled(enabled)

        # Update channel data when processing is enabled
        if enabled:
            self._initialize_channel_data()

        # Reset dependent buttons and state when processing is disabled
        if not enabled:
            self.view_ica_components_btn.setEnabled(False)
            self.inverse_wavelet_btn.setEnabled(False)
            
            # Reset button states
            if self.downsampling_applied:
                self.apply_downsample_btn.setText("Apply Downsampling")
                self.apply_downsample_btn.setStyleSheet("")
                self.downsampling_applied = False
                
            if self.advanced_filters_applied:
                self.apply_adv_filter_btn.setText("Apply Advanced Filters")
                self.apply_adv_filter_btn.setStyleSheet("")
                self.advanced_filters_applied = False
                
            # Reset computed states
            self.ica_computed = False
            self.ica_components = None
            self.wavelet_computed = False
            self.wavelet_coefficients = None
            self.wavelet_metadata = None

    def get_ica_settings(self) -> Dict[str, Any]:
        """Get current ICA settings."""
        return {
            "components": self.ica_components_spin.value(),
            "channels": self.ica_selected_channels,
            "use_all_channels": len(self.ica_selected_channels) == len(self.channel_names) if self.channel_names else True,
        }

    def get_wavelet_settings(self) -> Dict[str, Any]:
        """Get current wavelet settings."""
        return {
            "type": self.wavelet_type_combo.currentData(),
            "level": self.wavelet_level_spin.value(),
            "channel": self.wavelet_channel_combo.currentData(),
        }

    def get_downsample_settings(self) -> Dict[str, Any]:
        """Get current downsample settings."""
        return {
            "factor": self.downsample_factor_spin.value(),
            "aggregation": self.downsample_agg_combo.currentData(),
        }

    def get_advanced_filter_settings(self) -> Dict[str, Any]:
        """Get current advanced filter settings."""
        return {
            "filter_type": self.filter_type_combo.currentData(),
            "window_function": self.window_function_combo.currentData(),
        }
