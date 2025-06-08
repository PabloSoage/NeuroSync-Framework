from typing import Any, Optional, List, Dict

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QListWidget,
    QLineEdit,
    QTextEdit,
)

from .base_panel import BasePanel
from ..utils.help_system import HelpButton


class StreamingPanel(BasePanel):
    """Panel for managing data streaming options."""

    def __init__(self, collector_service: Any, parent: Optional[Any] = None) -> None:
        """Initialize the streaming panel."""
        super().__init__(parent)
        self.collector_service = collector_service

        # Setup UI components
        self.setup_streamer_configuration()
        self.setup_board_configuration()

        # Add stretch to push everything to the top
        self.layout.addStretch()

    def setup_streamer_configuration(self) -> None:
        """Set up streamer configuration group."""
        streamer_group = QGroupBox("Streamer Configuration")
        streamer_layout = QVBoxLayout(streamer_group)

        # Add help button for streamers
        streamer_header_layout = QHBoxLayout()
        streamer_header_layout.addWidget(QLabel("Data Streaming Options"))
        streamer_header_layout.addWidget(HelpButton("streamers", self))
        streamer_header_layout.addStretch()
        streamer_layout.addLayout(streamer_header_layout)

        # File streamer
        file_streamer_layout = QHBoxLayout()
        file_streamer_layout.addWidget(QLabel("File Streamer:"))
        self.file_streamer_path = QLineEdit()
        self.file_streamer_path.setText("file://eeg_stream.csv:w")
        file_streamer_layout.addWidget(self.file_streamer_path)

        file_streamer_btn = QPushButton("Add File Streamer")
        file_streamer_btn.clicked.connect(
            lambda: self.add_streamer(self.file_streamer_path.text())
        )
        file_streamer_layout.addWidget(file_streamer_btn)

        streamer_layout.addLayout(file_streamer_layout)

        # Network streamer
        network_streamer_layout = QHBoxLayout()
        network_streamer_layout.addWidget(QLabel("Network Streamer:"))
        self.network_streamer_path = QLineEdit()
        self.network_streamer_path.setText("streaming_board://225.1.1.1:6677")
        network_streamer_layout.addWidget(self.network_streamer_path)

        network_streamer_btn = QPushButton("Add Network Streamer")
        network_streamer_btn.clicked.connect(
            lambda: self.add_streamer(self.network_streamer_path.text())
        )
        network_streamer_layout.addWidget(network_streamer_btn)

        streamer_layout.addLayout(network_streamer_layout)

        # Custom streamer
        custom_streamer_layout = QHBoxLayout()
        custom_streamer_layout.addWidget(QLabel("Custom Streamer:"))
        self.custom_streamer_path = QLineEdit()
        custom_streamer_layout.addWidget(self.custom_streamer_path)

        custom_streamer_btn = QPushButton("Add Custom Streamer")
        custom_streamer_btn.clicked.connect(
            lambda: self.add_streamer(self.custom_streamer_path.text())
        )
        custom_streamer_layout.addWidget(custom_streamer_btn)

        streamer_layout.addLayout(custom_streamer_layout)

        # Current streamers list
        streamers_label = QLabel("Active Streamers:")
        streamer_layout.addWidget(streamers_label)

        self.streamers_list = QListWidget()
        streamer_layout.addWidget(self.streamers_list)

        # Delete streamer button
        delete_streamer_btn = QPushButton("Delete Selected Streamer")
        delete_streamer_btn.clicked.connect(self.delete_selected_streamer)
        streamer_layout.addWidget(delete_streamer_btn)

        self.layout.addWidget(streamer_group)

    def setup_board_configuration(self) -> None:
        """Set up board configuration section."""
        config_group = QGroupBox("Board Configuration")
        config_layout = QVBoxLayout(config_group)

        # Add help button for board configuration
        config_header_layout = QHBoxLayout()
        config_header_layout.addWidget(QLabel("Board Commands Configuration"))
        config_header_layout.addWidget(HelpButton("board_config", self))
        config_header_layout.addStretch()
        config_layout.addLayout(config_header_layout)

        # Config command
        config_cmd_layout = QHBoxLayout()
        config_cmd_layout.addWidget(QLabel("Config Command:"))
        self.config_cmd_edit = QLineEdit()
        config_cmd_layout.addWidget(self.config_cmd_edit)

        self.send_config_btn = QPushButton("Send Config")
        self.send_config_btn.clicked.connect(self.send_board_config)
        config_cmd_layout.addWidget(self.send_config_btn)

        config_layout.addLayout(config_cmd_layout)

        # Config response
        config_layout.addWidget(QLabel("Response:"))
        self.config_response_text = QTextEdit()
        self.config_response_text.setReadOnly(True)
        config_layout.addWidget(self.config_response_text)

        self.layout.addWidget(config_group)

    def add_streamer(self, streamer_params: str) -> None:
        """Add a streamer to the board."""
        if not streamer_params:
            self.show_error("Streamer Error", "No streamer parameters specified")
            return

        try:
            success = self.collector_service.add_streamer(streamer_params)

            if success:
                self.streamers_list.addItem(streamer_params)
                self.show_status(f"Added streamer: {streamer_params}")
            else:
                self.show_error("Streamer Error", "Failed to add streamer")
        except Exception as e:
            self.show_error("Streamer Error", f"Error adding streamer: {str(e)}")

    def delete_selected_streamer(self) -> None:
        """Delete the selected streamer."""
        selected = self.streamers_list.currentItem()
        if not selected:
            self.show_error("Streamer Error", "No streamer selected")
            return

        try:
            streamer_params = selected.text()
            success = self.collector_service.remove_streamer(streamer_params)

            if success:
                self.streamers_list.takeItem(self.streamers_list.row(selected))
                self.show_status(f"Removed streamer: {streamer_params}")
            else:
                self.show_error("Streamer Error", "Failed to remove streamer")
        except Exception as e:
            self.show_error("Streamer Error", f"Error removing streamer: {str(e)}")

    def send_board_config(self) -> None:
        """Send configuration to the board."""
        config_cmd = self.config_cmd_edit.text()
        if not config_cmd:
            self.show_error("Config Error", "No command specified")
            return

        try:
            response = self.collector_service.config_device(config_cmd)
            self.config_response_text.setText(response)
            self.show_status(f"Config command sent: {config_cmd}")
        except Exception as e:
            self.show_error("Config Error", f"Error sending configuration: {str(e)}")

    def enable_streaming(self, enabled: bool) -> None:
        """Enable or disable streaming controls."""
        # Enable/disable all buttons and inputs related to streaming
        self.send_config_btn.setEnabled(enabled)

    # Add methods for API interaction
    def update_streamer_list(self, streamers_list: List[str]) -> bool:
        """Update the list of streamers from the API."""
        try:
            self.streamers_list.clear()
            for streamer in streamers_list:
                self.streamers_list.addItem(streamer)
            return True
        except Exception as e:
            self.show_error("Streamer List Update Error", str(e))
            return False

    def update_config_response(self, response_text: str) -> bool:
        """Update the configuration response text from the API."""
        try:
            self.config_response_text.setText(response_text)
            return True
        except Exception as e:
            self.show_error("Config Response Update Error", str(e))
            return False

    def get_streamer_params(self) -> Dict[str, str]:
        """Get currently configured streamer parameters."""
        return {
            "file": self.file_streamer_path.text(),
            "network": self.network_streamer_path.text(),
            "custom": self.custom_streamer_path.text(),
        }

    def get_active_streamers(self) -> List[str]:
        """Get list of currently active streamers."""
        streamers = []
        for i in range(self.streamers_list.count()):
            streamers.append(self.streamers_list.item(i).text())
        return streamers
