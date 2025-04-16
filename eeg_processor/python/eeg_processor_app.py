import logging
import os
import time

import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QLabel,
    QGroupBox,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QFileDialog,
    QTabWidget,
    QRadioButton,
    QMessageBox,
    QGridLayout,
    QScrollArea,
)
from PyQt5.QtGui import QColor, QPalette, QFont
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import (
    DataFilter,
    FilterTypes,
    AggOperations,
    WindowOperations,
    WaveletTypes,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .collectors.eeg_collector import EEGCollector
from .processors.signal_processor import SignalProcessor
from .visualizers.eeg_viz import EEGVisualizer

# Importar la nueva clase BoardConfiguration
from .collectors.board_configuration import BoardConfiguration

# Importar la nueva clase BrainMapVisualizer
from .visualizers.brain_map_viz import BrainMapVisualizer

# Importar las clases del sistema de ayuda
from .utils.help_system import HelpButton, show_help_topic, show_eeg_concepts_help

# Check if MNE is available
try:
    import mne

    MNE_AVAILABLE = True
except ImportError:
    MNE_AVAILABLE = False
    logging.warning("MNE package not found. MNE integration will be disabled.")


class EEGProcessorApp(QMainWindow):
    """
    Main application for EEG data collection, processing and visualization.

    This class provides a GUI for interacting with BrainFlow and managing EEG data.
    """

    def __init__(self):
        """Initialize the EEG processor application."""
        super().__init__()

        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        BoardShim.enable_dev_board_logger()

        # Define app theme colors
        self.dark_bg = "#2D2D30"
        self.dark_frame_bg = "#252526"
        self.text_color = "#E0E0E0"
        self.accent_color = "#007ACC"
        self.success_color = "#5FB878"
        self.warning_color = "#FFAA33"
        self.error_color = "#FF5555"

        self.setWindowTitle("EEG Processor")
        self.setGeometry(100, 100, 1200, 800)

        # Set application style
        self._set_dark_theme()

        # Data handling objects
        self.collector = None
        self.processor = None
        self.visualizer = None

        # Application state
        self.is_streaming = False
        self.is_recording = False
        self.record_filename = ""
        self.start_time = 0

        # Initialize UI
        self.setup_ui()

        # Timer for updating status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Update every second

        logging.info("EEG Processor application initialized")

    def _set_dark_theme(self):
        """Set the application to use a dark theme."""
        palette = QPalette()

        # Set colors
        palette.setColor(QPalette.Window, QColor(self.dark_bg))
        palette.setColor(QPalette.WindowText, QColor(self.text_color))
        palette.setColor(QPalette.Base, QColor(self.dark_frame_bg))
        palette.setColor(QPalette.AlternateBase, QColor(self.dark_bg))
        palette.setColor(QPalette.ToolTipBase, QColor(self.dark_bg))
        palette.setColor(QPalette.ToolTipText, QColor(self.text_color))
        palette.setColor(QPalette.Text, QColor(self.text_color))
        palette.setColor(QPalette.Button, QColor(self.dark_bg))
        palette.setColor(QPalette.ButtonText, QColor(self.text_color))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(self.accent_color))
        palette.setColor(QPalette.Highlight, QColor(self.accent_color))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

        self.setPalette(palette)

        # Set stylesheet for detailed control
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{ background-color: {self.dark_bg}; color: {self.text_color}; }}
            QGroupBox {{
                border: 1px solid #444;
                margin-top: 0.5em;
                border-radius: 3px;
                padding: 0.5em;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: {self.text_color};
            }}
            QPushButton {{
                background-color: {self.accent_color};
                color: white;
                border: none;
                padding: 4px 8px;
                min-height: 24px;
                border-radius: 2px;
            }}
            QPushButton:pressed {{ background-color: #005599; }}
            QPushButton:hover {{ background-color: #0066aa; }}
            QPushButton:disabled {{
                background-color: #555555;
                color: #999999;
            }}
            QLineEdit, QTextEdit, QListWidget, QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {self.dark_frame_bg};
                color: {self.text_color};
                border: 1px solid #444;
                padding: 2px;
                border-radius: 2px;
            }}
            QTextEdit {{ font-family: 'Consolas', monospace; }}
            QComboBox::drop-down {{ border: 0px; }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
            QSlider::groove:horizontal {{
                border: 1px solid #444;
                height: 8px;
                background: {self.dark_frame_bg};
                margin: 2px 0;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {self.accent_color};
                border: none;
                width: 18px;
                margin: -2px 0;
                border-radius: 4px;
            }}
            QCheckBox::indicator {{
                width: 13px;
                height: 13px;
                border: 1px solid #444;
                border-radius: 2px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.accent_color};
            }}
            QTabWidget::pane {{
                border: 1px solid #444;
                background-color: {self.dark_bg};
            }}
            QTabBar::tab {{
                background-color: {self.dark_frame_bg};
                color: {self.text_color};
                padding: 6px 12px;
                margin-right: 2px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.accent_color};
            }}
            QTabBar::tab:!selected {{
                margin-top: 2px;
            }}
            QScrollArea, QScrollBar {{
                background-color: {self.dark_frame_bg};
                border: 1px solid #444;
            }}
            QLabel {{ color: {self.text_color}; }}
            QRadioButton::indicator {{
                width: 13px;
                height: 13px;
                border-radius: 7px;
                border: 1px solid #444;
            }}
            QRadioButton::indicator:checked {{
                background-color: {self.accent_color};
            }}
        """
        )

    def setup_ui(self):
        """Set up the user interface."""
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Añadir un botón de ayuda general en la parte superior
        help_header_layout = QHBoxLayout()
        app_title_label = QLabel("EEG Processor")
        app_title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        help_header_layout.addWidget(app_title_label)
        help_header_layout.addStretch()
        
        # Botón de ayuda general que abre la ayuda completa
        help_btn = QPushButton("Help")
        help_btn.clicked.connect(lambda: show_eeg_concepts_help(self))
        help_btn.setStyleSheet("background-color: #007ACC;")
        help_header_layout.addWidget(help_btn)
        
        main_layout.addLayout(help_header_layout)

        # Create tabs
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # Connection tab
        connection_tab = QWidget()
        tabs.addTab(connection_tab, "Connection")
        self.setup_connection_tab(connection_tab)

        # Processing tab
        processing_tab = QWidget()
        tabs.addTab(processing_tab, "Processing")
        self.setup_processing_tab(processing_tab)

        # Recording tab
        recording_tab = QWidget()
        tabs.addTab(recording_tab, "Recording")
        self.setup_recording_tab(recording_tab)

        # Streaming tab - new
        streaming_tab = QWidget()
        tabs.addTab(streaming_tab, "Streaming")
        self.setup_streaming_tab(streaming_tab)

        # Advanced Processing tab (new)
        advanced_tab = QWidget()
        tabs.addTab(advanced_tab, "Advanced Processing")
        self.setup_advanced_processing_tab(advanced_tab)

        # MNE Integration tab (new)
        if MNE_AVAILABLE:
            mne_tab = QWidget()
            tabs.addTab(mne_tab, "MNE Integration")
            self.setup_mne_tab(mne_tab)

        # Status bar for showing current status
        self.statusBar().showMessage("Ready")

    def setup_connection_tab(self, tab):
        """Set up the connection tab."""
        layout = QVBoxLayout(tab)

        # Visualization control
        visualization_group = QGroupBox("Visualization Control")
        visualization_layout = QVBoxLayout(visualization_group)

        # Añadir botón de ayuda a la visualización
        viz_help_layout = QHBoxLayout()
        self.show_viz_btn = QPushButton("Show Visualization Window")
        self.show_viz_btn.clicked.connect(self.show_visualization)
        self.show_viz_btn.setEnabled(False)
        self.show_viz_btn.setStyleSheet("font-weight: bold; padding: 6px;")
        viz_help_layout.addWidget(self.show_viz_btn)
        viz_help_layout.addWidget(HelpButton("eeg_visualization", self))
        visualization_layout.addLayout(viz_help_layout)

        # Board selection
        board_group = QGroupBox("Board Selection")
        board_layout = QVBoxLayout(board_group)

        # Board type organization - new grouped approach
        board_type_layout = QVBoxLayout()
        board_type_label_layout = QHBoxLayout()
        board_type_label = QLabel("Select Board:")
        board_type_label_layout.addWidget(board_type_label)
        board_type_label_layout.addWidget(HelpButton("board_selection", self))
        board_type_layout.addLayout(board_type_label_layout)
        
        # Get board groups from the helper class
        self.board_groups = BoardConfiguration.get_all_boards()
        
        # Create a combo box for board selection
        self.board_type_combo = QComboBox()
        for name, board_id in self.board_groups:
            self.board_type_combo.addItem(name, board_id)
            
        # Filter functionality for easier board selection
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter:")
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setPlaceholderText("Type to filter boards...")
        self.filter_edit.textChanged.connect(self.filter_boards)
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_edit)
        
        board_type_layout.addLayout(filter_layout)
        board_type_layout.addWidget(self.board_type_combo)
        
        # Connect signal after adding all items
        self.board_type_combo.currentIndexChanged.connect(self.on_board_type_changed)
        
        board_layout.addLayout(board_type_layout)

        # Parameters group
        self.param_group = QGroupBox("Board Parameters")
        param_layout = QVBoxLayout(self.param_group)

        # Añadir botón de ayuda para los parámetros de conexión
        param_help_layout = QHBoxLayout()
        param_help_layout.addWidget(QLabel("Connection Parameters"))
        param_help_layout.addWidget(HelpButton("connection_params", self))
        param_help_layout.addStretch()
        param_layout.addLayout(param_help_layout)

        # Create all parameter fields
        self.param_fields = {}
        
        # Serial port
        serial_layout = self._create_param_field("serial_port", "Serial Port:", param_layout)
        
        # IP fields
        ip_layout = self._create_param_field("ip_address", "IP Address:", param_layout)
        ip_port_layout = self._create_param_field("ip_port", "IP Port:", param_layout, is_numeric=True)
        
        # MAC Address
        mac_layout = self._create_param_field("mac_address", "MAC Address:", param_layout)
        
        # Serial Number
        serial_number_layout = self._create_param_field("serial_number", "Serial Number:", param_layout)
        
        # File for playback board
        file_layout = QHBoxLayout()
        file_label = QLabel("File Path:")
        self.param_fields["file"] = QtWidgets.QLineEdit()
        file_browse_btn = QPushButton("Browse")
        file_browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.param_fields["file"])
        file_layout.addWidget(file_browse_btn)
        param_layout.addLayout(file_layout)

        # Master board (for playback/streaming boards)
        master_layout = QHBoxLayout()
        master_label = QLabel("Master Board:")
        self.param_fields["master_board"] = QComboBox()
        
        # Add boards to master board dropdown
        for name, board_id in self.board_groups:
            self.param_fields["master_board"].addItem(name, board_id)
            
        master_layout.addWidget(master_label)
        master_layout.addWidget(self.param_fields["master_board"])
        param_layout.addLayout(master_layout)
        
        # Other Info
        other_info_layout = self._create_param_field("other_info", "Other Info:", param_layout)
        
        # Timeout
        timeout_layout = self._create_param_field("timeout", "Timeout (ms):", param_layout, is_numeric=True)
        
        # Preset selection
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Data Preset:")
        self.preset_combo = QComboBox()
        
        # Add presets
        preset_info = BoardConfiguration.get_preset_info()
        for preset_val, preset_desc in preset_info.items():
            self.preset_combo.addItem(preset_desc, preset_val)
            
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(HelpButton("preset_selection", self))
        param_layout.addLayout(preset_layout)

        # Add parameter group to layout
        board_layout.addWidget(self.param_group)

        # Connection control
        control_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_board)
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_board)
        self.disconnect_btn.setEnabled(False)
        control_layout.addWidget(self.connect_btn)
        control_layout.addWidget(self.disconnect_btn)
        board_layout.addLayout(control_layout)

        # Stream control
        stream_layout = QHBoxLayout()
        self.start_stream_btn = QPushButton("Start Stream")
        self.start_stream_btn.clicked.connect(self.start_stream)
        self.start_stream_btn.setEnabled(False)
        self.stop_stream_btn = QPushButton("Stop Stream")
        self.stop_stream_btn.clicked.connect(self.stop_stream)
        self.stop_stream_btn.setEnabled(False)
        stream_layout.addWidget(self.start_stream_btn)
        stream_layout.addWidget(self.stop_stream_btn)
        stream_layout.addWidget(HelpButton("streaming", self))
        board_layout.addLayout(stream_layout)

        # Board info
        info_group = QGroupBox("Board Information")
        info_layout = QVBoxLayout(info_group)
        
        # Create a scrollable area for board info
        info_scroll = QScrollArea()
        info_scroll.setWidgetResizable(True)
        info_widget = QWidget()
        info_scroll_layout = QVBoxLayout(info_widget)
        
        self.board_info_label = QLabel("No board connected")
        self.board_info_label.setWordWrap(True)
        info_scroll_layout.addWidget(self.board_info_label)
        info_scroll_layout.addStretch()
        
        info_scroll.setWidget(info_widget)
        info_layout.addWidget(info_scroll)

        # Add groups to tab
        layout.addWidget(visualization_group)
        layout.addWidget(board_group)
        layout.addWidget(info_group)
        layout.addStretch()

        # Initially update visible parameters based on selected board
        self.on_board_type_changed()
        
    def _create_param_field(self, param_name, label_text, parent_layout, is_numeric=False):
        """Helper method to create parameter input fields"""
        layout = QHBoxLayout()
        label = QLabel(label_text)
        
        if is_numeric:
            field = QSpinBox()
            field.setRange(0, 65535)
            if param_name == "ip_port":
                field.setValue(6677)  # Default port
            elif param_name == "timeout":
                field.setValue(15000)  # Default timeout
        else:
            field = QtWidgets.QLineEdit()
            if param_name == "ip_address":
                field.setText("225.1.1.1")  # Default multicast address
                
        layout.addWidget(label)
        layout.addWidget(field)
        parent_layout.addLayout(layout)
        
        self.param_fields[param_name] = field
        return layout
        
    def filter_boards(self):
        """Filter the boards in the dropdown based on search text"""
        filter_text = self.filter_edit.text().lower()
        self.board_type_combo.clear()
        
        for name, board_id in self.board_groups:
            if filter_text in name.lower():
                self.board_type_combo.addItem(name, board_id)
                
        # If no matching boards, show a message
        if self.board_type_combo.count() == 0:
            self.board_type_combo.addItem("No matching boards", -1)

    def on_board_type_changed(self):
        """Handle board type selection changes."""
        board_id = self.board_type_combo.currentData()
        if board_id is None:
            return
            
        # Even if board ID is -1 (for no matching boards), continue to show message
        # but don't treat it as an error case
        
        try:
            # Get requirements for this board
            requirements = BoardConfiguration.get_board_requirements(board_id)
            
            # Show/hide parameters based on requirements
            for param, required in requirements.items():
                if param in self.param_fields:
                    self.param_fields[param].setEnabled(required)
                    
                    # Add visual cue for required fields
                    if required:
                        if isinstance(self.param_fields[param], QComboBox):
                            self.param_fields[param].setStyleSheet("border: 1px solid #E0A030;")
                        else:
                            self.param_fields[param].setStyleSheet("border: 1px solid #E0A030; background-color: rgba(224, 160, 48, 0.1);")
                    else:
                        if isinstance(self.param_fields[param], QComboBox):
                            self.param_fields[param].setStyleSheet("")
                        else:
                            self.param_fields[param].setStyleSheet("background-color: #252526;")
            
            # Show board description if available
            try:
                preset = self.preset_combo.currentData()
                if (preset is None) or (preset == -1):
                    preset = BrainFlowPresets.DEFAULT_PRESET.value
                    
                # For synthetic board and special boards, use our overridden get_board_description
                description = BoardConfiguration.get_board_description(board_id, preset)
                
                if isinstance(description, dict):
                    desc_text = f"<b>Selected Board:</b> {description.get('name', f'Board ID {board_id}')}<br>"
                    
                    if "sampling_rate" in description:
                        desc_text += f"<b>Sampling Rate:</b> {description['sampling_rate']} Hz<br>"
                        
                    if "eeg_channels" in description:
                        if isinstance(description["eeg_channels"], list):
                            desc_text += f"<b>EEG Channels:</b> {len(description['eeg_channels'])}<br>"
                        else:
                            desc_text += f"<b>EEG Channels:</b> {description['eeg_channels']}<br>"
                        
                    if "eeg_names" in description:
                        if isinstance(description["eeg_names"], str):
                            eeg_names = description["eeg_names"].split(",")
                        else:
                            eeg_names = description["eeg_names"]
                        desc_text += f"<b>Channel Names:</b> {', '.join(eeg_names)}<br>"
                    
                    # Add other channel types
                    for ch_type in ["emg", "ecg", "eog", "eda", "accel", "gyro", "ppg"]:
                        key = f"{ch_type}_channels"
                        if key in description and description[key]:
                            desc_text += f"<b>{ch_type.upper()} Channels:</b> {len(description[key])}<br>"
                    
                    self.board_info_label.setText(desc_text)
                else:
                    # Fallback for when description is not a dict
                    if board_id == BoardIds.SYNTHETIC_BOARD.value:
                        desc_text = "<b>Selected Board:</b> Synthetic Board<br>"
                        desc_text += "<b>Sampling Rate:</b> 250 Hz<br>"
                        desc_text += "<b>EEG Channels:</b> 16<br>"
                        desc_text += "<b>Channel Names:</b> Fp1, Fp2, C3, C4, etc.<br>"
                        self.board_info_label.setText(desc_text)
                    else:
                        self.board_info_label.setText(f"Selected board ID: {board_id}")
            except Exception as e:
                # Special handling for synthetic and other special boards
                if board_id == BoardIds.SYNTHETIC_BOARD.value:
                    desc_text = "<b>Selected Board:</b> Synthetic Board<br>"
                    desc_text += "<b>Sampling Rate:</b> 250 Hz<br>" 
                    desc_text += "<b>EEG Channels:</b> 16<br>"
                    desc_text += "<b>Channel Names:</b> Fp1, Fp2, C3, C4, etc.<br>"
                    self.board_info_label.setText(desc_text)
                elif board_id == BoardIds.PLAYBACK_FILE_BOARD.value:
                    desc_text = "<b>Selected Board:</b> Playback File Board<br>"
                    desc_text += "<b>Info:</b> Parameters depend on the file content<br>"
                    self.board_info_label.setText(desc_text)
                elif board_id == BoardIds.STREAMING_BOARD.value:
                    desc_text = "<b>Selected Board:</b> Streaming Board<br>"
                    desc_text += "<b>Info:</b> Parameters depend on the master board<br>"
                    self.board_info_label.setText(desc_text)
                else:
                    self.board_info_label.setText(f"Selected board ID: {board_id}")
                logging.debug(f"Error getting board description: {e}")
                
        except Exception as e:
            logging.error(f"Error in board type changed: {e}")
            self.board_info_label.setText(f"Selected board ID: {board_id}")

    def setup_processing_tab(self, tab):
        """Set up the processing tab."""
        layout = QVBoxLayout(tab)

        # Filtering options
        filter_group = QGroupBox("Filtering Options")
        filter_layout = QVBoxLayout(filter_group)

        # Bandpass filter
        bandpass_layout = QHBoxLayout()
        self.bandpass_check = QCheckBox("Bandpass Filter")
        self.bandpass_check.setChecked(True)
        bandpass_low_label = QLabel("Low Cut:")
        self.bandpass_low_spin = QDoubleSpinBox()
        self.bandpass_low_spin.setRange(0.1, 100.0)
        self.bandpass_low_spin.setValue(1.0)
        self.bandpass_low_spin.setSuffix(" Hz")

        bandpass_high_label = QLabel("High Cut:")
        self.bandpass_high_spin = QDoubleSpinBox()
        self.bandpass_high_spin.setRange(0.1, 200.0)
        self.bandpass_high_spin.setValue(50.0)
        self.bandpass_high_spin.setSuffix(" Hz")

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

        notch_type_label = QLabel("Type:")
        self.notch_type_combo = QComboBox()
        self.notch_type_combo.addItem("50 Hz", "50")
        self.notch_type_combo.addItem("60 Hz", "60")

        notch_layout.addWidget(self.notch_check)
        notch_layout.addWidget(notch_type_label)
        notch_layout.addWidget(self.notch_type_combo)
        notch_layout.addWidget(HelpButton("notch_filter", self))
        filter_layout.addLayout(notch_layout)

        # Denoising
        denoise_layout = QHBoxLayout()
        self.denoise_check = QCheckBox("Wavelet Denoising")
        self.denoise_check.setChecked(False)

        wavelet_label = QLabel("Wavelet Type:")
        self.wavelet_combo = QComboBox()
        self.wavelet_combo.addItem("DB4", WaveletTypes.DB4)
        self.wavelet_combo.addItem("DB6", WaveletTypes.DB6)
        self.wavelet_combo.addItem("BIOR3_9", WaveletTypes.BIOR3_9)

        denoise_layout.addWidget(self.denoise_check)
        denoise_layout.addWidget(wavelet_label)
        denoise_layout.addWidget(self.wavelet_combo)
        denoise_layout.addWidget(HelpButton("denoising", self))
        filter_layout.addLayout(denoise_layout)

        # Detrend
        detrend_layout = QHBoxLayout()
        self.detrend_check = QCheckBox("Detrend")
        self.detrend_check.setChecked(True)
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

        # Añadir botón para visualización de mapa cerebral
        brain_map_layout = QHBoxLayout()
        self.brain_map_btn = QPushButton("Show Brain Map Visualization")
        self.brain_map_btn.clicked.connect(self.show_brain_map)
        self.brain_map_btn.setEnabled(False)  # Habilitado solo cuando haya datos EEG
        brain_map_layout.addWidget(self.brain_map_btn)
        brain_map_layout.addWidget(HelpButton("brain_map", self))
        filter_layout.addLayout(brain_map_layout)

        # EEG Metrics
        metrics_group = QGroupBox("EEG Metrics")
        metrics_layout = QVBoxLayout(metrics_group)

        # Agregar ayuda para métricas EEG
        metrics_header_layout = QHBoxLayout()
        metrics_header_layout.addWidget(QLabel("EEG Metrics Analysis"))
        metrics_header_layout.addWidget(HelpButton("eeg_basics", self))
        metrics_header_layout.addStretch()
        metrics_layout.addLayout(metrics_header_layout)

        metrics_update_layout = QHBoxLayout()
        self.calculate_metrics_btn = QPushButton("Calculate Metrics")
        self.calculate_metrics_btn.clicked.connect(self.calculate_metrics)
        self.calculate_metrics_btn.setEnabled(False)
        metrics_update_layout.addWidget(self.calculate_metrics_btn)
        metrics_layout.addLayout(metrics_update_layout)

        # Metrics display
        self.metrics_label = QLabel("No metrics calculated")
        metrics_layout.addWidget(self.metrics_label)

        # Add groups to tab
        layout.addWidget(filter_group)
        layout.addWidget(metrics_group)
        layout.addStretch()

    def setup_recording_tab(self, tab):
        """Set up the recording tab."""
        layout = QVBoxLayout(tab)

        # Recording options
        record_group = QGroupBox("Recording Options")
        record_layout = QVBoxLayout(record_group)

        # Añadir botón de ayuda para grabación
        record_header_layout = QHBoxLayout()
        record_header_layout.addWidget(QLabel("Data Recording Settings"))
        record_header_layout.addWidget(HelpButton("recording", self))
        record_header_layout.addStretch()
        record_layout.addLayout(record_header_layout)

        # File selection
        file_layout = QHBoxLayout()
        file_label = QLabel("Save to file:")
        self.record_file_edit = QtWidgets.QLineEdit()
        self.record_file_edit.setText(os.path.join(os.getcwd(), "eeg_recording.csv"))
        file_browse_btn = QPushButton("Browse")
        file_browse_btn.clicked.connect(self.browse_record_file)
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.record_file_edit)
        file_layout.addWidget(file_browse_btn)
        record_layout.addLayout(file_layout)

        # Record type
        type_layout = QHBoxLayout()
        type_label = QLabel("Data type:")
        self.raw_radio = QRadioButton("Raw")
        self.raw_radio.setChecked(True)
        self.processed_radio = QRadioButton("Processed")
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.raw_radio)
        type_layout.addWidget(self.processed_radio)
        record_layout.addLayout(type_layout)

        # Record control
        record_control_layout = QHBoxLayout()
        self.start_record_btn = QPushButton("Start Recording")
        self.start_record_btn.clicked.connect(self.start_recording)
        self.start_record_btn.setEnabled(False)
        self.stop_record_btn = QPushButton("Stop Recording")
        self.stop_record_btn.clicked.connect(self.stop_recording)
        self.stop_record_btn.setEnabled(False)
        record_control_layout.addWidget(self.start_record_btn)
        record_control_layout.addWidget(self.stop_record_btn)
        record_layout.addLayout(record_control_layout)

        # Add marker
        marker_layout = QHBoxLayout()
        marker_label = QLabel("Marker:")
        self.marker_value_spin = QSpinBox()
        self.marker_value_spin.setRange(1, 255)
        self.marker_value_spin.setValue(1)
        self.add_marker_btn = QPushButton("Add Marker")
        self.add_marker_btn.clicked.connect(self.add_marker)
        self.add_marker_btn.setEnabled(False)
        marker_layout.addWidget(marker_label)
        marker_layout.addWidget(self.marker_value_spin)
        marker_layout.addWidget(self.add_marker_btn)
        record_layout.addLayout(marker_layout)

        # Recording status
        status_layout = QHBoxLayout()
        status_label = QLabel("Recording Status:")
        self.recording_status_label = QLabel("Not recording")
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.recording_status_label)
        record_layout.addLayout(status_layout)

        # Save current data
        save_layout = QHBoxLayout()
        self.save_data_btn = QPushButton("Save Current Data")
        self.save_data_btn.clicked.connect(self.save_current_data)
        self.save_data_btn.setEnabled(False)
        save_layout.addWidget(self.save_data_btn)
        record_layout.addLayout(save_layout)

        # Add to layout
        layout.addWidget(record_group)
        layout.addStretch()

    def setup_advanced_processing_tab(self, tab):
        """Set up the advanced processing tab with additional signal processing features."""
        layout = QVBoxLayout(tab)

        # ICA Section
        ica_group = QGroupBox("Independent Component Analysis (ICA)")
        ica_layout = QVBoxLayout(ica_group)

        # Añadir botón de ayuda para ICA
        ica_header_layout = QHBoxLayout()
        ica_header_layout.addWidget(QLabel("ICA Configuration"))
        ica_header_layout.addWidget(HelpButton("ica", self))
        ica_header_layout.addStretch()
        ica_layout.addLayout(ica_header_layout)

        # ICA Parameters
        ica_params_layout = QHBoxLayout()
        ica_params_layout.addWidget(QLabel("Number of Components:"))
        self.ica_components_spin = QSpinBox()
        self.ica_components_spin.setRange(1, 10)
        self.ica_components_spin.setValue(2)
        ica_params_layout.addWidget(self.ica_components_spin)

        ica_params_layout.addWidget(QLabel("Channel:"))
        self.ica_channel_combo = QComboBox()
        self.ica_channel_combo.addItem(
            "All Channels", -1
        )  # Special value for all channels
        # Channels will be populated when connected to a board
        ica_params_layout.addWidget(self.ica_channel_combo)

        ica_layout.addLayout(ica_params_layout)

        # ICA Controls
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

        # Wavelet Transform Section
        wavelet_group = QGroupBox("Wavelet Transforms")
        wavelet_layout = QVBoxLayout(wavelet_group)

        # Añadir botón de ayuda para Wavelet
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
        self.wavelet_type_combo.addItem("DB6", WaveletTypes.DB6)
        self.wavelet_type_combo.addItem("DB5", WaveletTypes.DB5)
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

        # Wavelet Controls
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

        # Downsampling Section
        downsample_group = QGroupBox("Downsampling")
        downsample_layout = QVBoxLayout(downsample_group)

        # Añadir botón de ayuda para Downsampling
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

        # Downsampling Controls
        downsample_buttons_layout = QHBoxLayout()
        self.apply_downsample_btn = QPushButton("Apply Downsampling")
        self.apply_downsample_btn.clicked.connect(self.apply_downsampling)
        self.apply_downsample_btn.setEnabled(False)
        downsample_buttons_layout.addWidget(self.apply_downsample_btn)

        downsample_layout.addLayout(downsample_buttons_layout)

        # Advanced Filtering Section
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

        # Add all groups to main layout
        layout.addWidget(ica_group)
        layout.addWidget(wavelet_group)
        layout.addWidget(downsample_group)
        layout.addWidget(adv_filter_group)
        layout.addStretch()

    def setup_mne_tab(self, tab):
        """Set up the MNE integration tab if MNE is available."""
        layout = QVBoxLayout(tab)

        if not MNE_AVAILABLE:
            layout.addWidget(
                QLabel(
                    "MNE package is not installed. Please install it to use this feature."
                )
            )
            return

        # MNE conversion section
        mne_group = QGroupBox("Convert to MNE Format")
        mne_layout = QVBoxLayout(mne_group)

        # Añadir botón de ayuda para MNE
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

        # MNE Controls
        mne_buttons_layout = QHBoxLayout()

        self.convert_to_mne_btn = QPushButton("Convert to MNE")
        self.convert_to_mne_btn.clicked.connect(self.convert_to_mne)
        self.convert_to_mne_btn.setEnabled(False)
        mne_buttons_layout.addWidget(self.convert_to_mne_btn)

        mne_layout.addLayout(mne_buttons_layout)

        # MNE Visualization Options
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

        # Add all groups to main layout
        layout.addWidget(mne_group)
        layout.addWidget(mne_viz_group)
        layout.addStretch()

        # Store MNE objects
        self.mne_raw = None

    def setup_streaming_tab(self, tab):
        """Set up the streaming tab for advanced streaming options."""
        layout = QVBoxLayout(tab)
        
        # Streamer configuration
        streamer_group = QGroupBox("Streamer Configuration")
        streamer_layout = QVBoxLayout(streamer_group)
        
        # Añadir botón de ayuda para streamers
        streamer_header_layout = QHBoxLayout()
        streamer_header_layout.addWidget(QLabel("Data Streaming Options"))
        streamer_header_layout.addWidget(HelpButton("streamers", self))
        streamer_header_layout.addStretch()
        streamer_layout.addLayout(streamer_header_layout)
        
        # File streamer
        file_streamer_layout = QHBoxLayout()
        file_streamer_layout.addWidget(QLabel("File Streamer:"))
        self.file_streamer_path = QtWidgets.QLineEdit()
        self.file_streamer_path.setText("file://eeg_stream.csv:w")
        file_streamer_layout.addWidget(self.file_streamer_path)
        
        file_streamer_btn = QPushButton("Add File Streamer")
        file_streamer_btn.clicked.connect(lambda: self.add_streamer(self.file_streamer_path.text()))
        file_streamer_layout.addWidget(file_streamer_btn)
        
        streamer_layout.addLayout(file_streamer_layout)
        
        # Network streamer
        network_streamer_layout = QHBoxLayout()
        network_streamer_layout.addWidget(QLabel("Network Streamer:"))
        self.network_streamer_path = QtWidgets.QLineEdit()
        self.network_streamer_path.setText("streaming_board://225.1.1.1:6677")
        network_streamer_layout.addWidget(self.network_streamer_path)
        
        network_streamer_btn = QPushButton("Add Network Streamer")
        network_streamer_btn.clicked.connect(lambda: self.add_streamer(self.network_streamer_path.text()))
        network_streamer_layout.addWidget(network_streamer_btn)
        
        streamer_layout.addLayout(network_streamer_layout)
        
        # Custom streamer
        custom_streamer_layout = QHBoxLayout()
        custom_streamer_layout.addWidget(QLabel("Custom Streamer:"))
        self.custom_streamer_path = QtWidgets.QLineEdit()
        custom_streamer_layout.addWidget(self.custom_streamer_path)
        
        custom_streamer_btn = QPushButton("Add Custom Streamer")
        custom_streamer_btn.clicked.connect(lambda: self.add_streamer(self.custom_streamer_path.text()))
        custom_streamer_layout.addWidget(custom_streamer_btn)
        
        streamer_layout.addLayout(custom_streamer_layout)
        
        # Current streamers list
        streamers_label = QLabel("Active Streamers:")
        streamer_layout.addWidget(streamers_label)
        
        self.streamers_list = QtWidgets.QListWidget()
        streamer_layout.addWidget(self.streamers_list)
        
        # Delete streamer button
        delete_streamer_btn = QPushButton("Delete Selected Streamer")
        delete_streamer_btn.clicked.connect(self.delete_selected_streamer)
        streamer_layout.addWidget(delete_streamer_btn)
        
        # Board configuration section
        config_group = QGroupBox("Board Configuration")
        config_layout = QVBoxLayout(config_group)
        
        # Añadir botón de ayuda para configuración de placa
        config_header_layout = QHBoxLayout()
        config_header_layout.addWidget(QLabel("Board Commands Configuration"))
        config_header_layout.addWidget(HelpButton("board_config", self))
        config_header_layout.addStretch()
        config_layout.addLayout(config_header_layout)
        
        # Config command
        config_cmd_layout = QHBoxLayout()
        config_cmd_layout.addWidget(QLabel("Config Command:"))
        self.config_cmd_edit = QtWidgets.QLineEdit()
        config_cmd_layout.addWidget(self.config_cmd_edit)
        
        send_config_btn = QPushButton("Send Config")
        send_config_btn.clicked.connect(self.send_board_config)
        config_cmd_layout.addWidget(send_config_btn)
        
        config_layout.addLayout(config_cmd_layout)
        
        # Config response
        config_layout.addWidget(QLabel("Response:"))
        self.config_response_text = QtWidgets.QTextEdit()
        self.config_response_text.setReadOnly(True)
        config_layout.addWidget(self.config_response_text)
        
        # Add to main layout
        layout.addWidget(streamer_group)
        layout.addWidget(config_group)
        layout.addStretch()

    # New methods for the advanced features

    def compute_ica(self):
        """Compute ICA components for the selected channel."""
        if not self.collector or not self.processor or not self.is_streaming:
            return

        try:
            # Get data
            data, _ = self.collector.get_data(
                5 * self.collector.sampling_rate
            )  # Get 5 seconds of data
            if data.size == 0:
                return

            # Get selected channel or use all channels
            selected_index = self.ica_channel_combo.currentIndex()
            if selected_index == 0:  # All channels option
                # Use all EEG channels
                channels_for_ica = self.collector.get_eeg_channels()
                ica_data = data[channels_for_ica]
            else:
                channel = self.ica_channel_combo.currentData()
                ica_data = data[channel : channel + 1]  # Keep as 2D array

            # Reshape data for ICA if needed
            samples_per_channel = ica_data.shape[1]
            num_components = min(self.ica_components_spin.value(), ica_data.shape[0])

            # Compute ICA
            w, k, a, s = self.processor.perform_ica(ica_data, num_components)

            # Store ICA results
            self.ica_results = {
                "w": w,
                "k": k,
                "a": a,
                "s": s,
                "original_data": ica_data,
                "num_components": num_components,
            }

            # Enable viewing components
            self.view_ica_components_btn.setEnabled(True)

            self.statusBar().showMessage(
                f"ICA computed with {num_components} components"
            )

        except Exception as e:
            QMessageBox.warning(self, "ICA Error", f"Error calculating ICA: {str(e)}")
            logging.error(f"ICA error: {e}")

    def view_ica_components(self):
        """Show ICA components in a separate window."""
        if not hasattr(self, "ica_results") or not self.ica_results:
            return

        try:
            # Create dialog for ICA visualization
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("ICA Components")
            dialog.setMinimumSize(800, 600)

            layout = QVBoxLayout(dialog)

            # Create matplotlib figure
            fig = Figure(figsize=(8, 6))
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)

            s = self.ica_results["s"]
            num_components = self.ica_results["num_components"]

            # Plot each component
            for i in range(num_components):
                ax = fig.add_subplot(num_components, 1, i + 1)
                ax.plot(s[i])
                ax.set_title(f"Component {i+1}")
                if i < num_components - 1:
                    ax.set_xticks([])

            fig.tight_layout()
            canvas.draw()

            # Add close button
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.close)
            layout.addWidget(close_button)

            # Show dialog
            dialog.exec_()

        except Exception as e:
            QMessageBox.warning(
                self,
                "Visualization Error",
                f"Error visualizing ICA components: {str(e)}",
            )
            logging.error(f"ICA visualization error: {e}")

    def compute_wavelet(self):
        """Compute wavelet transform for the selected channel."""
        if not self.collector or not self.processor or not self.is_streaming:
            return

        try:
            # Get data
            data, _ = self.collector.get_data(
                4 * self.collector.sampling_rate
            )  # Get 4 seconds of data
            if data.size == 0:
                return

            # Get selected channel
            channel = self.wavelet_channel_combo.currentData()
            wavelet_data = data[channel]

            # Get wavelet parameters
            wavelet_type = self.wavelet_type_combo.currentData()
            decomposition_level = self.wavelet_level_spin.value()

            # Compute wavelet transform
            wavelet_coeffs, lengths = DataFilter.perform_wavelet_transform(
                wavelet_data, wavelet_type, decomposition_level
            )

            # Store wavelet results for potential inverse transform
            self.wavelet_results = {
                "coeffs": wavelet_coeffs,
                "lengths": lengths,
                "original_data": wavelet_data,
                "wavelet_type": wavelet_type,
                "level": decomposition_level,
            }

            # Enable inverse button
            self.inverse_wavelet_btn.setEnabled(True)

            # Show wavelet coefficients in a dialog
            self._show_wavelet_coefficients()

            self.statusBar().showMessage(
                f"Wavelet transform computed with {wavelet_type} wavelet"
            )

        except Exception as e:
            QMessageBox.warning(
                self, "Wavelet Error", f"Error computing wavelet transform: {str(e)}"
            )
            logging.error(f"Wavelet error: {e}")

    def _show_wavelet_coefficients(self):
        """Show wavelet coefficients in a dialog."""
        if not hasattr(self, "wavelet_results") or not self.wavelet_results:
            return

        try:
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Wavelet Coefficients")
            dialog.setMinimumSize(800, 600)

            layout = QVBoxLayout(dialog)

            # Create matplotlib figure
            fig = Figure(figsize=(8, 6))
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)

            # Extract coefficient blocks
            coeffs = self.wavelet_results["coeffs"]
            lengths = self.wavelet_results["lengths"]
            level = self.wavelet_results["level"]

            ax = fig.add_subplot(111)
            ax.plot(coeffs)

            # Mark boundaries between coefficient blocks with vertical lines
            cumsum = 0
            for i, length in enumerate(lengths):
                cumsum += length
                ax.axvline(x=cumsum, color="r", linestyle="--")
                if i == 0:
                    ax.text(
                        cumsum / 2, ax.get_ylim()[1] * 0.9, f"A({level})", ha="center"
                    )
                else:
                    ax.text(
                        (cumsum + cumsum - lengths[i]) / 2,
                        ax.get_ylim()[1] * 0.9,
                        f"D({level-i+1})",
                        ha="center",
                    )

            ax.set_title("Wavelet Coefficients")
            ax.set_xlabel("Coefficient Index")
            ax.set_ylabel("Value")

            fig.tight_layout()
            canvas.draw()

            # Add close button
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.close)
            layout.addWidget(close_button)

            # Show dialog
            dialog.exec_()

        except Exception as e:
            QMessageBox.warning(
                self,
                "Visualization Error",
                f"Error visualizing wavelet coefficients: {str(e)}",
            )
            logging.error(f"Wavelet visualization error: {e}")

    def apply_inverse_wavelet(self):
        """Apply inverse wavelet transform with the stored coefficients."""
        if not hasattr(self, "wavelet_results") or not self.wavelet_results:
            QMessageBox.warning(
                self, "Wavelet Error", "No wavelet transform data available"
            )
            return

        try:
            # Apply inverse wavelet transform
            orig_data = self.wavelet_results["original_data"]
            coeffs = self.wavelet_results["coeffs"]
            lengths = self.wavelet_results["lengths"]
            wavelet_type = self.wavelet_results["wavelet_type"]
            level = self.wavelet_results["level"]

            # Create coefficient tuple in required format
            coeffs_tuple = (coeffs, lengths)

            # Apply inverse transform
            reconstructed = DataFilter.perform_inverse_wavelet_transform(
                coeffs_tuple, orig_data.shape[0], wavelet_type, level
            )

            # Display comparison of original and reconstructed signal
            self._show_wavelet_reconstruction(orig_data, reconstructed)

            self.statusBar().showMessage("Inverse wavelet transform applied")

        except Exception as e:
            QMessageBox.warning(
                self,
                "Wavelet Error",
                f"Error applying inverse wavelet transform: {str(e)}",
            )
            logging.error(f"Inverse wavelet error: {e}")

    def _show_wavelet_reconstruction(self, original, reconstructed):
        """Show comparison between original and reconstructed signal."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Signal Reconstruction")
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout(dialog)

        # Create matplotlib figure
        fig = Figure(figsize=(8, 6))
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)

        # Plot original and reconstructed signals
        ax1 = fig.add_subplot(211)
        ax1.plot(original)
        ax1.set_title("Original Signal")
        ax1.set_xticks([])

        ax2 = fig.add_subplot(212)
        ax2.plot(reconstructed)
        ax2.set_title("Reconstructed Signal")

        fig.tight_layout()
        canvas.draw()

        # Add close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)

        # Show dialog
        dialog.exec_()

    def apply_downsampling(self):
        """Apply downsampling to EEG data."""
        if not self.collector or not self.processor or not self.is_streaming:
            return

        try:
            # Get data
            data, _ = self.collector.get_data(
                4 * self.collector.sampling_rate
            )  # Get 4 seconds of data
            if data.size == 0:
                return

            # Get downsampling parameters
            factor = self.downsample_factor_spin.value()
            operation = self.downsample_agg_combo.currentData()

            # Apply downsampling
            downsampled_data = self.processor.perform_downsampling(
                data, factor, operation
            )
            self.collector.set_processed_data(downsampled_data)

            # Calculate new sampling rate
            new_sampling_rate = self.collector.sampling_rate / factor

            # Display results
            self._show_downsampling_results(
                data, downsampled_data, factor, new_sampling_rate
            )

            self.statusBar().showMessage(
                f"Data downsampled by factor {factor}, new rate: {new_sampling_rate:.1f} Hz"
            )

        except Exception as e:
            QMessageBox.warning(
                self, "Downsampling Error", f"Error applying downsampling: {str(e)}"
            )
            logging.error(f"Downsampling error: {e}")

    def _show_downsampling_results(self, original, downsampled, factor, new_rate):
        """Show comparison between original and downsampled data."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Downsampling Results")
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout(dialog)

        # Create information label
        info_text = (
            f"Original sampling rate: {self.collector.sampling_rate} Hz\n"
            f"New sampling rate: {new_rate:.1f} Hz\n"
            f"Downsampling factor: {factor}"
        )
        layout.addWidget(QLabel(info_text))

        # Create matplotlib figure
        fig = Figure(figsize=(8, 5))
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)

        # Select first EEG channel for visualization
        channel = self.collector.get_eeg_channels()[0]

        # Plot original and downsampled signals
        ax1 = fig.add_subplot(211)
        ax1.plot(original[channel][:500])  # Show just a portion for clarity
        ax1.set_title("Original Signal")
        ax1.set_xticks([])

        ax2 = fig.add_subplot(212)
        ax2.plot(downsampled[channel][: 500 // factor])
        ax2.set_title("Downsampled Signal")

        fig.tight_layout()
        canvas.draw()

        # Add buttons
        buttons_layout = QHBoxLayout()

        # Save downsampled data button
        save_btn = QPushButton("Save Downsampled Data")
        save_btn.clicked.connect(lambda: self._save_downsampled_data(downsampled))
        buttons_layout.addWidget(save_btn)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        buttons_layout.addWidget(close_button)

        layout.addLayout(buttons_layout)

        # Show dialog
        dialog.exec_()

    def _save_downsampled_data(self, downsampled):
        """Save downsampled data to a file."""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Downsampled Data", "", "CSV files (*.csv)"
            )
            if filename:
                DataFilter.write_file(downsampled, filename, "w")
                self.statusBar().showMessage(f"Downsampled data saved to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save data: {str(e)}")
            logging.error(f"Save error: {e}")

    def apply_advanced_filters(self):
        """Apply advanced filtering options."""
        if not self.collector or not self.processor or not self.is_streaming:
            return

        try:
            # Get data
            data, _ = self.collector.get_data(4 * self.collector.sampling_rate)
            if data.size == 0:
                return

            # Get filter parameters
            filter_type = self.filter_type_combo.currentData()

            # Process the data
            filtered_data = data.copy()

            # Apply a bandpass filter with the selected filter type
            for channel in self.collector.get_eeg_channels():
                DataFilter.perform_bandpass(
                    filtered_data[channel],
                    self.collector.sampling_rate,
                    1.0,
                    50.0,
                    4,
                    filter_type,
                    0,
                )

            # Store the filtered data
            self.collector.set_processed_data(filtered_data)

            # Update visualization if running
            if self.visualizer:
                self.visualizer.update_plots()

            self.statusBar().showMessage(
                f"Advanced filters applied with filter type: {filter_type}"
            )

        except Exception as e:
            QMessageBox.warning(
                self, "Filtering Error", f"Error applying advanced filters: {str(e)}"
            )
            logging.error(f"Advanced filtering error: {e}")

    def convert_to_mne(self):
        """Convert BrainFlow data to MNE format."""
        if not MNE_AVAILABLE:
            QMessageBox.warning(self, "MNE Error", "MNE package is not installed")
            return

        if not self.collector or not self.processor or not self.is_streaming:
            return

        try:
            # Get data
            seconds = self.mne_duration_spin.value()
            data, _ = self.collector.get_data(seconds * self.collector.sampling_rate)
            if data.size == 0:
                return

            # Get EEG channels and names
            eeg_channels = self.collector.get_eeg_channels()
            eeg_data = data[eeg_channels, :]

            # Convert from microvolts to volts for MNE
            eeg_data = eeg_data / 1000000

            # Get channel names (or use generic ones if not available)
            try:
                ch_names = BoardShim.get_eeg_names(self.collector.board_id)
            except:
                ch_names = [f"EEG {i+1}" for i in range(len(eeg_channels))]

            # Create MNE info object
            sampling_rate = self.collector.sampling_rate
            ch_types = ["eeg"] * len(eeg_channels)
            info = mne.create_info(
                ch_names=ch_names, sfreq=sampling_rate, ch_types=ch_types
            )

            # Create Raw object
            self.mne_raw = mne.io.RawArray(eeg_data, info)

            # Enable visualization buttons
            self.plot_mne_psd_btn.setEnabled(True)
            self.plot_mne_topomap_btn.setEnabled(True)

            self.statusBar().showMessage(
                f"Data converted to MNE format: {seconds}s at {sampling_rate}Hz"
            )

        except Exception as e:
            QMessageBox.warning(
                self, "MNE Error", f"Error converting to MNE format: {str(e)}"
            )
            logging.error(f"MNE conversion error: {e}")

    def plot_mne_visualization(self, plot_type):
        """Plot MNE visualizations."""
        if not MNE_AVAILABLE or self.mne_raw is None:
            return

        try:
            # Clear the figure
            self.mne_figure.clear()

            if plot_type == "psd":
                # Create PSD plot
                ax = self.mne_figure.add_subplot(111)
                self.mne_raw.plot_psd(ax=ax, fmax=100, show=False)
                ax.set_title("Power Spectral Density")

            elif plot_type == "topomap":
                # For topomap we need channel locations
                # Use default 10-20 system for visualization
                montage = mne.channels.make_standard_montage("standard_1020")
                self.mne_raw.set_montage(montage)

                # Calculate PSDs for topomap
                psds, freqs = mne.time_frequency.psd_welch(
                    self.mne_raw, fmin=0, fmax=100, n_fft=256
                )

                # Find indices for frequency bands
                freq_idx = np.searchsorted(freqs, [8, 13])[0]  # Alpha band

                # Plot topomap
                ax = self.mne_figure.add_subplot(111)
                mne.viz.plot_topomap(
                    np.mean(psds[:, :, freq_idx], axis=1),
                    self.mne_raw.info,
                    axes=ax,
                    show=False,
                )
                ax.set_title("Alpha Band Power Topomap")

            # Update canvas
            self.mne_figure.tight_layout()
            self.mne_canvas.draw()

        except Exception as e:
            QMessageBox.warning(
                self, "MNE Error", f"Error creating MNE visualization: {str(e)}"
            )
            logging.error(f"MNE visualization error: {e}")

    def connect_board(self):
        """Connect to the selected EEG board."""
        try:
            board_id = self.board_type_combo.currentData()
            if board_id is None:
                QMessageBox.warning(self, "Connection Error", "Please select a valid board")
                return
            
            # Get selected preset
            preset = self.preset_combo.currentData()
            if preset is None:
                preset = BrainFlowPresets.DEFAULT_PRESET

            # Collect parameters from input fields
            params_dict = {}
            for param_name, field in self.param_fields.items():
                if isinstance(field, QComboBox):
                    params_dict[param_name] = field.currentData()
                elif isinstance(field, QSpinBox):
                    params_dict[param_name] = field.value()
                else:
                    params_dict[param_name] = field.text()

            # Create input parameters
            params = BoardConfiguration.create_input_params(board_id, params_dict)

            # Special handling for synthetic board
            if board_id == BoardIds.SYNTHETIC_BOARD.value:
                logging.info("Connecting to synthetic board")
                # No special parameters needed
            
            # Create collector
            self.collector = EEGCollector(board_id, params, preset)
            self.collector.prepare_session()

            # Create processor
            self.processor = SignalProcessor(self.collector.sampling_rate)

            # Update UI
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.start_stream_btn.setEnabled(True)
            self.stop_stream_btn.setEnabled(False)
            self.save_data_btn.setEnabled(True)
            self.show_viz_btn.setEnabled(False)

            # Update board info
            board_info = self.collector.get_board_info()
            rich_info = "<b>Connected Board Information:</b><br>"
            rich_info += f"<b>Name:</b> {board_info['board_name']}<br>"
            rich_info += f"<b>Board ID:</b> {board_info['board_id']}<br>"
            rich_info += f"<b>Preset:</b> {preset}<br>"
            rich_info += f"<b>Sampling Rate:</b> {board_info['sampling_rate']} Hz<br>"
            rich_info += f"<b>EEG Channels:</b> {len(board_info['eeg_channels'])}<br>"
            
            # Add channel names if available
            if 'eeg_names' in board_info and board_info['eeg_names']:
                rich_info += f"<b>Channel Names:</b> {', '.join(board_info['eeg_names'])}<br>"
                
            # Add info about other available channels
            channel_types = [
                ('emg', 'EMG'), ('ecg', 'ECG'), ('eog', 'EOG'), ('eda', 'EDA'),
                ('ppg', 'PPG'), ('accel', 'Accelerometer'), ('gyro', 'Gyroscope')
            ]
            
            for key, label in channel_types:
                ch_key = f"{key}_channels"
                if ch_key in board_info and board_info[ch_key]:
                    rich_info += f"<b>{label} Channels:</b> {len(board_info[ch_key])}<br>"
            
            self.board_info_label.setText(rich_info)
            self.statusBar().showMessage("Board connected successfully")

        except Exception as e:
            QMessageBox.critical(
                self, "Connection Error", f"Failed to connect to board: {str(e)}"
            )
            logging.error(f"Connection error: {e}")

    def disconnect_board(self):
        """Disconnect from the EEG board."""
        try:
            if self.is_streaming:
                self.stop_stream()

            if self.collector:
                self.collector.release_session()
                self.collector = None
                self.processor = None
                self.visualizer = None

            # Update UI
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.start_stream_btn.setEnabled(False)
            self.stop_stream_btn.setEnabled(False)
            self.start_record_btn.setEnabled(False)
            self.stop_record_btn.setEnabled(False)
            self.add_marker_btn.setEnabled(False)
            self.save_data_btn.setEnabled(False)
            self.apply_filters_btn.setEnabled(False)
            self.calculate_metrics_btn.setEnabled(False)
            self.show_viz_btn.setEnabled(False)  # Asegurar que está desactivado
            self.brain_map_btn.setEnabled(False)  # Deshabilitar botón del mapa cerebral

            # Update info
            self.board_info_label.setText("No board connected")
            self.statusBar().showMessage("Board disconnected")

        except Exception as e:
            QMessageBox.warning(
                self, "Disconnection Error", f"Error during disconnection: {str(e)}"
            )
            logging.error(f"Disconnection error: {e}")

    def start_stream(self):
        """Start streaming data from the board."""
        try:
            if self.collector and not self.is_streaming:
                self.collector.start_stream()
                self.is_streaming = True

                # Create visualizer
                if not self.visualizer:
                    self.visualizer = EEGVisualizer(self.collector, self.processor)
                    self.apply_filters()  # Apply initial filter settings
                self.visualizer.start()

                # Update UI
                self.start_stream_btn.setEnabled(False)
                self.stop_stream_btn.setEnabled(True)
                self.start_record_btn.setEnabled(True)
                self.add_marker_btn.setEnabled(True)
                self.apply_filters_btn.setEnabled(True)
                self.calculate_metrics_btn.setEnabled(True)
                self.brain_map_btn.setEnabled(True)  # Habilitar el botón del mapa cerebral

                # Update visualization button state - debe estar deshabilitado porque la ventana está visible
                self.show_viz_btn.setEnabled(False)
                self.show_viz_btn.setStyleSheet("font-weight: bold; padding: 6px;")

                # Enable advanced processing buttons
                self.compute_ica_btn.setEnabled(True)
                self.compute_wavelet_btn.setEnabled(True)
                self.apply_downsample_btn.setEnabled(True)
                self.apply_adv_filter_btn.setEnabled(True)

                # Enable MNE buttons if available
                if MNE_AVAILABLE:
                    self.convert_to_mne_btn.setEnabled(True)

                # Populate channel selection dropdowns
                self._populate_channel_dropdowns()

                self.statusBar().showMessage("Streaming started")

        except Exception as e:
            QMessageBox.critical(
                self, "Streaming Error", f"Failed to start streaming: {str(e)}"
            )
            logging.error(f"Streaming error: {e}")

    def stop_stream(self):
        """Stop streaming data from the board."""
        try:
            if self.collector and self.is_streaming:
                if self.is_recording:
                    self.stop_recording()

                self.collector.stop_stream()
                self.is_streaming = False

                if self.visualizer:
                    self.visualizer.stop()

                # Cerrar también el mapa cerebral si está abierto
                if hasattr(self, 'brain_map_viz') and self.brain_map_viz.is_visible():
                    self.brain_map_viz.close()

                # Update UI
                self.start_stream_btn.setEnabled(True)
                self.stop_stream_btn.setEnabled(False)
                self.start_record_btn.setEnabled(False)
                self.stop_record_btn.setEnabled(False)
                self.add_marker_btn.setEnabled(False)
                self.show_viz_btn.setEnabled(
                    False
                )  # Al parar el stream ya no se puede mostrar la visualización
                self.apply_filters_btn.setEnabled(
                    False
                )  # Deshabilitar filtros si no hay stream
                self.calculate_metrics_btn.setEnabled(
                    False
                )  # Deshabilitar cálculo de métricas sin stream
                self.brain_map_btn.setEnabled(False)  # Deshabilitar botón del mapa cerebral

                # Disable advanced processing buttons
                self.compute_ica_btn.setEnabled(False)
                self.compute_wavelet_btn.setEnabled(False)
                self.apply_downsample_btn.setEnabled(False)
                self.apply_adv_filter_btn.setEnabled(False)

                # Disable MNE buttons if available
                if MNE_AVAILABLE:
                    self.convert_to_mne_btn.setEnabled(False)

                self.statusBar().showMessage("Streaming stopped")

        except Exception as e:
            QMessageBox.warning(
                self, "Streaming Error", f"Error stopping stream: {str(e)}"
            )
            logging.error(f"Error stopping stream: {e}")

    def update_status(self):
        """Update status information."""
        if self.is_recording:
            duration = (
                int(round(time.time() * 1000)) - self.start_time
            ) / 1000  # Duration in seconds
            self.recording_status_label.setText(f"Recording... ({duration:.1f}s)")

        # Check if visualization window was closed and update button state
        if self.is_streaming and self.visualizer:
            if not self.visualizer.is_visible():
                # Si el stream está activo pero la ventana está cerrada, permitir reabrirla
                self.show_viz_btn.setEnabled(True)
                # Make the button more noticeable when the window is closed
                self.show_viz_btn.setStyleSheet(
                    "font-weight: bold; background-color: #4CAF50; color: white; padding: 6px;"
                )
            else:
                # Si la ventana está visible, no se necesita el botón
                self.show_viz_btn.setEnabled(False)
                self.show_viz_btn.setStyleSheet("font-weight: bold; padding: 6px;")
        elif not self.is_streaming:
            # Si no hay stream, desactivar el botón
            self.show_viz_btn.setEnabled(False)
            self.show_viz_btn.setStyleSheet("font-weight: bold; padding: 6px;")

    def show_visualization(self):
        """Show the EEG visualization if it was closed."""
        if self.is_streaming and self.collector and self.processor:
            if not self.visualizer or not self.visualizer.is_visible():
                # Create new visualizer or restart if it was closed
                self.visualizer = EEGVisualizer(self.collector, self.processor)
                self.apply_filters()  # Apply filter settings
                self.visualizer.start()
                self.show_viz_btn.setEnabled(False)
                self.show_viz_btn.setStyleSheet("font-weight: bold; padding: 6px;")
                self.statusBar().showMessage("Visualization window reopened")

    def closeEvent(self, event):
        """Handle application close event."""
        if self.collector:
            try:
                if self.is_streaming:
                    self.collector.stop_stream()
                self.collector.release_session()
            except Exception as e:
                logging.error(f"Error during shutdown: {e}")

        event.accept()

    def apply_filters(self):
        """Apply the selected filters to visualization."""
        if not self.visualizer:
            return

        self.visualizer.set_bandpass_filter(
            self.bandpass_check.isChecked(),
            self.bandpass_low_spin.value(),
            self.bandpass_high_spin.value(),
        )
        self.visualizer.set_notch_filter(self.notch_check.isChecked())
        self.visualizer.set_detrend(self.detrend_check.isChecked())

        self.statusBar().showMessage("Filters applied to visualization")

    def calculate_metrics(self):
        """Calculate EEG metrics from the current data."""
        if not self.collector or not self.processor or not self.is_streaming:
            return

        try:
            data, _ = self.collector.get_data(
                4 * self.collector.sampling_rate
            )  # Get 4 seconds of data
            if data.size == 0:
                return

            metrics = self.processor.get_eeg_metrics(
                data, self.collector.get_eeg_channels()
            )

            # Update display
            metrics_text = f"Mindfulness: {metrics['mindfulness']:.2f}\n"
            metrics_text += f"Concentration: {metrics['concentration']:.2f}\n"
            metrics_text += f"Relaxation: {metrics['relaxation']:.2f}\n"
            metrics_text += f"Restfulness: {metrics['restfulness']:.2f}"
            self.metrics_label.setText(metrics_text)

            self.statusBar().showMessage("EEG metrics calculated")

        except Exception as e:
            QMessageBox.warning(
                self, "Metrics Error", f"Failed to calculate metrics: {str(e)}"
            )
            logging.error(f"Metrics error: {e}")

    def start_recording(self):
        """Start recording data to file."""
        if not self.collector or not self.is_streaming:
            return

        self.record_filename = self.record_file_edit.text()
        if not self.record_filename:
            QMessageBox.warning(
                self, "Recording Error", "Please specify a file path for recording"
            )
            return

        self.is_recording = True
        self.start_time = int(round(time.time() * 1000))  # Start time in ms

        # Update UI
        self.start_record_btn.setEnabled(False)
        self.stop_record_btn.setEnabled(True)
        self.recording_status_label.setText("Recording...")

        self.statusBar().showMessage(f"Recording to {self.record_filename}")

    def stop_recording(self):
        """Stop recording and save data to file."""
        if not self.is_recording:
            return

        try:
            data_type = "processed" if self.processed_radio.isChecked() else "raw"
            self.collector.save_data(self.record_filename, data_type)

            self.is_recording = False

            # Update UI
            self.start_record_btn.setEnabled(True)
            self.stop_record_btn.setEnabled(False)
            self.recording_status_label.setText("Not recording")

            duration = (
                int(round(time.time() * 1000)) - self.start_time
            ) / 1000  # Duration in seconds
            self.statusBar().showMessage(f"Recording saved: {duration:.1f}s")

        except Exception as e:
            QMessageBox.critical(
                self, "Recording Error", f"Failed to save recording: {str(e)}"
            )
            logging.error(f"Recording error: {e}")

    def add_marker(self):
        """Add a marker to the data stream."""
        if not self.collector or not self.is_streaming:
            return

        marker_value = self.marker_value_spin.value()
        self.collector.insert_marker(marker_value)
        self.statusBar().showMessage(f"Marker {marker_value} added")

    def save_current_data(self):
        """Save current data to file."""
        if not self.collector:
            return

        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Data", "", "CSV files (*.csv)"
            )
            if filename:
                data_type = "processed" if self.processed_radio.isChecked() else "raw"
                self.collector.save_data(filename, data_type)
                self.statusBar().showMessage(f"Data saved to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save data: {str(e)}")
            logging.error(f"Save error: {e}")

    def _populate_channel_dropdowns(self):
        """Populate channel selection dropdowns with available channels."""
        if not self.collector:
            return

        # Get EEG channels
        eeg_channels = self.collector.get_eeg_channels()
        
        # Clear wavelet channel combo
        self.wavelet_channel_combo.clear()
        
        # Add all channel types to dropdown
        channel_types = [
            ('eeg', 'EEG'), ('emg', 'EMG'), ('ecg', 'ECG'), ('eog', 'EOG'), 
            ('eda', 'EDA'), ('ppg', 'PPG'), ('accel', 'Accel'), ('gyro', 'Gyro')
        ]
        
        for type_key, type_label in channel_types:
            channels = self.collector.get_channel_by_type(type_key)
            if channels:
                for i, channel in enumerate(channels):
                    label = f"{type_label} {i+1}"
                    # Use EEG channel names if available
                    if type_key == 'eeg' and hasattr(self.collector, 'eeg_names') and i < len(self.collector.eeg_names):
                        label += f" ({self.collector.eeg_names[i]})"
                    self.wavelet_channel_combo.addItem(f"{label} - Ch{channel}", channel)

        # Clear and populate ICA channel combo
        self.ica_channel_combo.clear()
        self.ica_channel_combo.addItem("All Channels", -1)
        
        # Add all channel types to ICA dropdown similarly
        for type_key, type_label in channel_types:
            channels = self.collector.get_channel_by_type(type_key)
            if channels:
                for i, channel in enumerate(channels):
                    label = f"{type_label} {i+1}"
                    if type_key == 'eeg' and hasattr(self.collector, 'eeg_names') and i < len(self.collector.eeg_names):
                        label += f" ({self.collector.eeg_names[i]})"
                    self.ica_channel_combo.addItem(f"{label} - Ch{channel}", channel)

    # Add a method to handle preset changes
    def change_preset(self):
        """Handle preset change for the current board."""
        if not self.collector:
            return
            
        try:
            new_preset = self.preset_combo.currentData()
            success = self.collector.set_preset(new_preset)
            
            if success:
                # Update board info display
                board_info = self.collector.get_board_info()
                rich_info = "<b>Board Information (Updated):</b><br>"
                rich_info += f"<b>Name:</b> {board_info['board_name']}<br>"
                rich_info += f"<b>Board ID:</b> {board_info['board_id']}<br>"
                rich_info += f"<b>Preset:</b> {new_preset}<br>"
                rich_info += f"<b>Sampling Rate:</b> {board_info['sampling_rate']} Hz<br>"
                rich_info += f"<b>EEG Channels:</b> {len(board_info['eeg_channels'])}<br>"
                
                # Update channel names if available
                if 'eeg_names' in board_info and board_info['eeg_names']:
                    rich_info += f"<b>Channel Names:</b> {', '.join(board_info['eeg_names'])}<br>"
                    
                self.board_info_label.setText(rich_info)
                self.statusBar().showMessage(f"Preset changed to {new_preset}")
                
                # Update processor with new sampling rate
                self.processor = SignalProcessor(self.collector.sampling_rate)
                
                # Re-populate channel dropdowns
                self._populate_channel_dropdowns()
            else:
                self.statusBar().showMessage("Failed to change preset")
        except Exception as e:
            QMessageBox.warning(
                self, "Preset Error", f"Error changing preset: {str(e)}"
            )
            logging.error(f"Preset change error: {e}")
            
    # Add a tab for config and streaming options
    def setup_streaming_tab(self, tab):
        """Set up the streaming tab for advanced streaming options."""
        layout = QVBoxLayout(tab)
        
        # Streamer configuration
        streamer_group = QGroupBox("Streamer Configuration")
        streamer_layout = QVBoxLayout(streamer_group)
        
        # Añadir botón de ayuda para streamers
        streamer_header_layout = QHBoxLayout()
        streamer_header_layout.addWidget(QLabel("Data Streaming Options"))
        streamer_header_layout.addWidget(HelpButton("streamers", self))
        streamer_header_layout.addStretch()
        streamer_layout.addLayout(streamer_header_layout)
        
        # File streamer
        file_streamer_layout = QHBoxLayout()
        file_streamer_layout.addWidget(QLabel("File Streamer:"))
        self.file_streamer_path = QtWidgets.QLineEdit()
        self.file_streamer_path.setText("file://eeg_stream.csv:w")
        file_streamer_layout.addWidget(self.file_streamer_path)
        
        file_streamer_btn = QPushButton("Add File Streamer")
        file_streamer_btn.clicked.connect(lambda: self.add_streamer(self.file_streamer_path.text()))
        file_streamer_layout.addWidget(file_streamer_btn)
        
        streamer_layout.addLayout(file_streamer_layout)
        
        # Network streamer
        network_streamer_layout = QHBoxLayout()
        network_streamer_layout.addWidget(QLabel("Network Streamer:"))
        self.network_streamer_path = QtWidgets.QLineEdit()
        self.network_streamer_path.setText("streaming_board://225.1.1.1:6677")
        network_streamer_layout.addWidget(self.network_streamer_path)
        
        network_streamer_btn = QPushButton("Add Network Streamer")
        network_streamer_btn.clicked.connect(lambda: self.add_streamer(self.network_streamer_path.text()))
        network_streamer_layout.addWidget(network_streamer_btn)
        
        streamer_layout.addLayout(network_streamer_layout)
        
        # Custom streamer
        custom_streamer_layout = QHBoxLayout()
        custom_streamer_layout.addWidget(QLabel("Custom Streamer:"))
        self.custom_streamer_path = QtWidgets.QLineEdit()
        custom_streamer_layout.addWidget(self.custom_streamer_path)
        
        custom_streamer_btn = QPushButton("Add Custom Streamer")
        custom_streamer_btn.clicked.connect(lambda: self.add_streamer(self.custom_streamer_path.text()))
        custom_streamer_layout.addWidget(custom_streamer_btn)
        
        streamer_layout.addLayout(custom_streamer_layout)
        
        # Current streamers list
        streamers_label = QLabel("Active Streamers:")
        streamer_layout.addWidget(streamers_label)
        
        self.streamers_list = QtWidgets.QListWidget()
        streamer_layout.addWidget(self.streamers_list)
        
        # Delete streamer button
        delete_streamer_btn = QPushButton("Delete Selected Streamer")
        delete_streamer_btn.clicked.connect(self.delete_selected_streamer)
        streamer_layout.addWidget(delete_streamer_btn)
        
        # Board configuration section
        config_group = QGroupBox("Board Configuration")
        config_layout = QVBoxLayout(config_group)
        
        # Añadir botón de ayuda para configuración de placa
        config_header_layout = QHBoxLayout()
        config_header_layout.addWidget(QLabel("Board Commands Configuration"))
        config_header_layout.addWidget(HelpButton("board_config", self))
        config_header_layout.addStretch()
        config_layout.addLayout(config_header_layout)
        
        # Config command
        config_cmd_layout = QHBoxLayout()
        config_cmd_layout.addWidget(QLabel("Config Command:"))
        self.config_cmd_edit = QtWidgets.QLineEdit()
        config_cmd_layout.addWidget(self.config_cmd_edit)
        
        send_config_btn = QPushButton("Send Config")
        send_config_btn.clicked.connect(self.send_board_config)
        config_cmd_layout.addWidget(send_config_btn)
        
        config_layout.addLayout(config_cmd_layout)
        
        # Config response
        config_layout.addWidget(QLabel("Response:"))
        self.config_response_text = QtWidgets.QTextEdit()
        self.config_response_text.setReadOnly(True)
        config_layout.addWidget(self.config_response_text)
        
        # Add to main layout
        layout.addWidget(streamer_group)
        layout.addWidget(config_group)
        layout.addStretch()

    def browse_file(self):
        """Browse for a file for playback board."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Data File", "", "CSV files (*.csv);; All Files (*)"
        )
        if filename:
            self.param_fields["file"].setText(filename)

    def browse_record_file(self):
        """Browse for a file to save the recording."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Recording File", "", "CSV files (*.csv);; All Files (*)"
        )
        if filename:
            self.record_file_edit.setText(filename)

    def show_brain_map(self):
        """Mostrar visualización del mapa cerebral."""
        if not self.collector or not self.processor or not self.is_streaming:
            QMessageBox.warning(self, "Visualization Error", "No EEG data available. Start streaming first.")
            return

        try:
            # Inicializar o mostrar visualizador de mapa cerebral
            if not hasattr(self, 'brain_map_viz') or not self.brain_map_viz.is_visible():
                self.brain_map_viz = BrainMapVisualizer(self.collector, self.processor)
                self.brain_map_viz.start()
            else:
                # Si ya existe, traerlo al frente
                self.brain_map_viz.win.raise_()

            self.statusBar().showMessage("Brain map visualization opened")

        except Exception as e:
            QMessageBox.critical(self, "Visualization Error", f"Error showing brain map: {e}")
            logging.error(f"Brain map visualization error: {e}")

    # Methods for streaming tab
    def add_streamer(self, streamer_params):
        """Add a streamer to the board."""
        if not self.collector:
            QMessageBox.warning(self, "Streamer Error", "No board connected")
            return
            
        try:
            self.collector.add_streamer(streamer_params)
            # Add to list
            self.streamers_list.addItem(streamer_params)
            self.statusBar().showMessage(f"Added streamer: {streamer_params}")
        except Exception as e:
            QMessageBox.warning(self, "Streamer Error", f"Error adding streamer: {str(e)}")
            logging.error(f"Streamer error: {e}")
            
    def delete_selected_streamer(self):
        """Delete the selected streamer."""
        if not self.collector:
            return
            
        selected = self.streamers_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Streamer Error", "No streamer selected")
            return
            
        streamer_params = selected.text()
        try:
            self.collector.remove_streamer(streamer_params)
            # Remove from list
            self.streamers_list.takeItem(self.streamers_list.row(selected))
            self.statusBar().showMessage(f"Deleted streamer: {streamer_params}")
        except Exception as e:
            QMessageBox.warning(self, "Streamer Error", f"Error deleting streamer: {str(e)}")
            logging.error(f"Streamer deletion error: {e}")
            
    def send_board_config(self):
        """Send configuration to the board."""
        if not self.collector:
            QMessageBox.warning(self, "Config Error", "No board connected")
            return
            
        config_cmd = self.config_cmd_edit.text()
        if not config_cmd:
            QMessageBox.warning(self, "Config Error", "No command specified")
            return
            
        try:
            response = self.collector.config_board(config_cmd)
            self.config_response_text.setText(response)
            self.statusBar().showMessage(f"Config command sent: {config_cmd}")
        except Exception as e:
            logging.error(f"Config error: {e}")
            QMessageBox.warning(self, "Config Error", f"Error sending config: {str(e)}")
