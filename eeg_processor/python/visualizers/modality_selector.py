import logging
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QWidget,
)

from .multi_modality_viz import MultiModalityVisualizer
from ..collectors.eeg_collector import EEGCollector


class ModalitySelector(QDialog):
    """
    Dialog for selecting which modalities to visualize.

    This class provides a UI for selecting and launching visualizations
    for different signal modalities (EEG, EMG, ECG, etc.).
    """

    def __init__(
        self, collector: EEGCollector, parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize the modality selector dialog.

        Args:
            collector: Data collector with access to signals
            parent: Parent widget
        """
        super().__init__(parent)
        self.collector = collector
        self.visualizer = MultiModalityVisualizer(collector)

        self.setWindowTitle("Signal Modality Selector")
        self.setMinimumSize(400, 300)

        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel("Select signal modalities to visualize:")
        layout.addWidget(instructions)

        # Modality list
        self.modality_list = QListWidget()
        layout.addWidget(self.modality_list)

        # Populate the list with available modalities
        self.populate_modality_list()

        # Buttons
        button_layout = QHBoxLayout()

        self.visualize_btn = QPushButton("Visualize Selected")
        self.visualize_btn.clicked.connect(self.visualize_selected)
        button_layout.addWidget(self.visualize_btn)

        self.close_all_btn = QPushButton("Close All Windows")
        self.close_all_btn.clicked.connect(self.close_all_windows)
        button_layout.addWidget(self.close_all_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def populate_modality_list(self) -> None:
        """Populate the list with available modalities."""
        self.modality_list.clear()

        modalities = self.visualizer.get_available_modalities()
        modality_names = {
            "eeg": "EEG - Electroencephalography",
            "emg": "EMG - Electromyography",
            "ecg": "ECG - Electrocardiography",
            "eog": "EOG - Electrooculography",
            "eda": "EDA - Electrodermal Activity",
            "ppg": "PPG - Photoplethysmography",
            "accel": "Accelerometer",
            "gyro": "Gyroscope",
        }

        for modality in modalities:
            item = QListWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)

            # Use descriptive name if available
            display_name = modality_names.get(modality, modality.upper())
            item.setText(display_name)
            item.setData(Qt.UserRole, modality)  # Store the actual modality key

            # Check if window is already open
            if self.visualizer.is_window_open(modality):
                item.setCheckState(Qt.Checked)

            self.modality_list.addItem(item)

    def visualize_selected(self) -> None:
        """Visualize selected modalities."""
        for i in range(self.modality_list.count()):
            item = self.modality_list.item(i)
            modality = item.data(Qt.UserRole)

            if item.checkState() == Qt.Checked:
                # Create visualization if not already open
                if not self.visualizer.is_window_open(modality):
                    self.visualizer.create_visualization(modality)
            else:
                # Close visualization if it's open
                if modality in self.visualizer.windows:
                    try:
                        # Stop the timer
                        if "timer" in self.visualizer.channel_types[modality]:
                            self.visualizer.channel_types[modality]["timer"].stop()
                        # Close the window
                        self.visualizer.windows[modality].close()
                        # Remove from windows dict
                        del self.visualizer.windows[modality]
                    except Exception as e:
                        logging.error(f"Error closing {modality} window: {e}")

        # Update the list to reflect current state
        self.populate_modality_list()

    def close_all_windows(self) -> None:
        """Close all visualization windows."""
        self.visualizer.close_all()
        self.populate_modality_list()  # Update list
