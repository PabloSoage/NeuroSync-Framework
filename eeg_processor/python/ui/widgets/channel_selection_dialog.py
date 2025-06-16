from typing import List

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QDialogButtonBox,
    QScrollArea,
    QFrame,
    QGridLayout,
)


class ChannelSelectionDialog(QDialog):
    """Reusable dialog for selecting EEG channels."""

    def __init__(
        self, channel_names: List[str], selected_channels: List[int] = None, parent=None
    ):
        """Initialize the channel selection dialog."""
        super().__init__(parent)
        self.channel_names = channel_names
        self.selected_channels = selected_channels or list(range(len(channel_names)))
        self.checkboxes = []

        self.setup_ui()
        self.apply_dark_theme()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Select EEG Channels")
        self.setModal(True)
        self.resize(400, 500)

        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("Select channels to include in analysis:")
        title_label.setStyleSheet(
            "font-weight: bold; font-size: 12px; margin-bottom: 10px;"
        )
        layout.addWidget(title_label)

        # Selection controls
        controls_layout = QHBoxLayout()

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        controls_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all)
        controls_layout.addWidget(deselect_all_btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Scrollable area for checkboxes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(300)

        # Container widget for checkboxes
        container_widget = QFrame()
        container_layout = QGridLayout(container_widget)

        # Create checkboxes for each channel
        for i, channel_name in enumerate(self.channel_names):
            checkbox = QCheckBox(f"{channel_name}")
            checkbox.setChecked(i in self.selected_channels)
            checkbox.toggled.connect(self.update_info_label)
            self.checkboxes.append(checkbox)

            # Arrange in 2 columns
            row = i // 2
            col = i % 2
            container_layout.addWidget(checkbox, row, col)

        scroll_area.setWidget(container_widget)
        layout.addWidget(scroll_area)

        # Info label
        self.info_label = QLabel()
        self.update_info_label()
        layout.addWidget(self.info_label)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def apply_dark_theme(self):
        """Apply dark theme styling to the dialog."""
        self.setStyleSheet(
            """
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
            }
            QCheckBox {
                color: #ffffff;
                background-color: transparent;
                spacing: 8px;
                padding: 4px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #555555;
                border-radius: 3px;
                background-color: #3a3a3a;
            }
            QCheckBox::indicator:checked {
                background-color: #007ACC;
                border-color: #007ACC;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #1e90ff;
                border-color: #1e90ff;
            }
            QCheckBox::indicator:hover {
                border-color: #777777;
                background-color: #4a4a4a;
            }
            QPushButton {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #505050;
                border-color: #777777;
            }
            QPushButton:pressed {
                background-color: #353535;
            }
            QScrollArea {
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #1e1e1e;
            }
            QFrame {
                background-color: #1e1e1e;
                border: none;
            }
        """
        )

    def select_all(self):
        """Select all channels."""
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)

    def deselect_all(self):
        """Deselect all channels."""
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)

    def update_info_label(self):
        """Update the info label with selection count."""
        selected_count = sum(1 for cb in self.checkboxes if cb.isChecked())
        total_count = len(self.checkboxes)
        self.info_label.setText(f"Selected: {selected_count} of {total_count} channels")

    def get_selected_channels(self) -> List[int]:
        """Get the list of selected channel indices."""
        return [i for i, cb in enumerate(self.checkboxes) if cb.isChecked()]
