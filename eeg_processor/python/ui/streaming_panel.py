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
    QMessageBox,
)

from .base_panel import BasePanel
from ..utils.help_system import HelpButton


class StreamingPanel(BasePanel):
    """Panel for managing data streaming options."""

    def __init__(self, collector_service: Any, parent: Optional[Any] = None) -> None:
        """Initialize the streaming panel."""
        super().__init__(parent)
        self.collector_service = collector_service
        
        # Import recording service for file streaming
        try:
            from ..services.recording_service import RecordingService
            self.recording_service = RecordingService()
        except Exception as e:
            self.recording_service = None
            self.show_error("Import Error", f"Could not load recording service: {e}")

        # Track active streamers
        self.active_streamers: List[Dict[str, str]] = []

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
        self.file_streamer_path.setText("recordings/eeg_stream.csv")
        file_streamer_layout.addWidget(self.file_streamer_path)

        file_streamer_btn = QPushButton("Add File Streamer")
        file_streamer_btn.clicked.connect(
            lambda: self.add_file_streamer(self.file_streamer_path.text())
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
            lambda: self.add_network_streamer(self.network_streamer_path.text())
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
            lambda: self.add_custom_streamer(self.custom_streamer_path.text())
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

    def add_file_streamer(self, file_path: str) -> None:
        """Add a file streamer using the recording service."""
        if not file_path:
            self.show_error("Streamer Error", "No file path specified")
            return

        if not self.recording_service:
            self.show_error("Service Error", "Recording service not available")
            return

        try:
            # FIXED: Check if we can start streaming - board must be connected and streaming
            if not self.collector_service.is_connected():
                self.show_error("Connection Error", "Board must be connected to add file streamer")
                return
                
            if not self.collector_service.is_streaming_active():
                self.show_error("Streaming Error", "Board must be streaming to add file streamer")
                return

            # FIXED: Use the correct method name and pass the collector service
            success = self.recording_service.start_recording(
                self.collector_service, file_path, "raw"
            )

            if success:
                streamer_info = {
                    "type": "file",
                    "params": file_path,
                    "display": f"File: {file_path}"
                }
                self.active_streamers.append(streamer_info)
                self.streamers_list.addItem(streamer_info["display"])
                self.show_status(f"Added file streamer: {file_path}")
            else:
                self.show_error("Streamer Error", "Failed to start file recording")

        except Exception as e:
            self.show_error("Streamer Error", f"Error adding file streamer: {str(e)}")

    def add_network_streamer(self, streamer_params: str) -> None:
        """Add a network streamer using BrainFlow's streaming functionality."""
        if not streamer_params:
            self.show_error("Streamer Error", "No network parameters specified")
            return

        try:
            # Check if collector is available and connected
            if not self.collector_service.is_connected():
                self.show_error("Connection Error", "Board must be connected to add network streamer")
                return

            # Try to add the streamer through BrainFlow
            success = self.collector_service.add_streamer(streamer_params)

            if success:
                streamer_info = {
                    "type": "network",
                    "params": streamer_params,
                    "display": f"Network: {streamer_params}"
                }
                self.active_streamers.append(streamer_info)
                self.streamers_list.addItem(streamer_info["display"])
                self.show_status(f"Added network streamer: {streamer_params}")
            else:
                self.show_error("Streamer Error", "Failed to add network streamer")

        except Exception as e:
            self.show_error("Streamer Error", f"Error adding network streamer: {str(e)}")

    def add_custom_streamer(self, streamer_params: str) -> None:
        """Add a custom streamer."""
        if not streamer_params:
            self.show_error("Streamer Error", "No custom parameters specified")
            return

        try:
            # Determine streamer type based on parameters
            if streamer_params.startswith("file://"):
                # Handle as file streamer
                file_path = streamer_params.replace("file://", "").split(":")[0]
                self.add_file_streamer(file_path)
                return
            elif any(proto in streamer_params for proto in ["://", "udp://", "tcp://"]):
                # Handle as network streamer
                self.add_network_streamer(streamer_params)
                return
            else:
                # Try as BrainFlow streamer
                success = self.collector_service.add_streamer(streamer_params)
                
                if success:
                    streamer_info = {
                        "type": "custom",
                        "params": streamer_params,
                        "display": f"Custom: {streamer_params}"
                    }
                    self.active_streamers.append(streamer_info)
                    self.streamers_list.addItem(streamer_info["display"])
                    self.show_status(f"Added custom streamer: {streamer_params}")
                else:
                    self.show_error("Streamer Error", "Failed to add custom streamer")

        except Exception as e:
            self.show_error("Streamer Error", f"Error adding custom streamer: {str(e)}")

    def delete_selected_streamer(self) -> None:
        """Delete the selected streamer."""
        selected_item = self.streamers_list.currentItem()
        if not selected_item:
            self.show_error("Streamer Error", "No streamer selected")
            return

        try:
            selected_row = self.streamers_list.row(selected_item)
            if selected_row >= len(self.active_streamers):
                self.show_error("Streamer Error", "Invalid streamer selection")
                return

            streamer_info = self.active_streamers[selected_row]
            streamer_type = streamer_info["type"]
            streamer_params = streamer_info["params"]

            success = False

            if streamer_type == "file":
                # Stop file recording
                if self.recording_service and self.recording_service.is_recording():
                    success = self.recording_service.stop_recording(self.collector_service)
                else:
                    success = True  # Already stopped or not recording

            elif streamer_type in ["network", "custom"]:
                # Remove BrainFlow streamer
                success = self.collector_service.remove_streamer(streamer_params)

            if success:
                # Remove from UI and tracking
                self.streamers_list.takeItem(selected_row)
                self.active_streamers.pop(selected_row)
                self.show_status(f"Removed {streamer_type} streamer: {streamer_params}")
            else:
                self.show_error("Streamer Error", f"Failed to remove {streamer_type} streamer")

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

        # If disabling, stop all active streamers
        if not enabled:
            self.stop_all_streamers()

    def stop_all_streamers(self) -> None:
        """Stop all active streamers."""
        while self.active_streamers:
            # Select first item and delete it
            if self.streamers_list.count() > 0:
                self.streamers_list.setCurrentRow(0)
                self.delete_selected_streamer()
            else:
                break

    def get_active_streamers(self) -> List[str]:
        """Get list of currently active streamers."""
        return [streamer["display"] for streamer in self.active_streamers]

    def show_error(self, title: str, message: str) -> None:
        """Show error message to user."""
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.exec_()
        except Exception as e:
            print(f"Error showing message box: {e}")

    def show_status(self, message: str) -> None:
        """Show status message to user."""
        try:
            # Try to send to status bar if parent has one
            if hasattr(self.parent(), 'statusBar'):
                self.parent().statusBar().showMessage(message, 3000)
            else:
                print(f"Status: {message}")
        except Exception as e:
            print(f"Status: {message}")
