import logging
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
    QComboBox,
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
        file_streamer_layout = QVBoxLayout()
        
        # File path input
        file_path_layout = QHBoxLayout()
        file_path_layout.addWidget(QLabel("File Streamer:"))
        self.file_streamer_path = QLineEdit()
        self.file_streamer_path.setText("recordings/eeg_stream.csv")
        file_path_layout.addWidget(self.file_streamer_path)
        file_streamer_layout.addLayout(file_path_layout)

        # Data type selection for file streamer
        file_data_type_layout = QHBoxLayout()
        file_data_type_layout.addWidget(QLabel("Data Type:"))
        self.file_data_type_combo = QComboBox()
        self.file_data_type_combo.addItem("Raw Data", "raw")
        self.file_data_type_combo.addItem("Processed Data (if filters enabled)", "processed")
        self.file_data_type_combo.addItem("Both Raw and Processed", "both")
        file_data_type_layout.addWidget(self.file_data_type_combo)
        file_streamer_layout.addLayout(file_data_type_layout)

        # Add file streamer button
        file_streamer_btn = QPushButton("Add File Streamer")
        file_streamer_btn.clicked.connect(
            lambda: self.add_file_streamer(
                self.file_streamer_path.text(),
                self.file_data_type_combo.currentData()
            )
        )
        file_streamer_layout.addWidget(file_streamer_btn)

        streamer_layout.addLayout(file_streamer_layout)

        # Network streamer
        network_streamer_layout = QVBoxLayout()
        
        # Network parameters input
        network_params_layout = QHBoxLayout()
        network_params_layout.addWidget(QLabel("Network Streamer:"))
        self.network_streamer_path = QLineEdit()
        self.network_streamer_path.setText("streaming_board://225.1.1.1:6677")
        network_params_layout.addWidget(self.network_streamer_path)
        network_streamer_layout.addLayout(network_params_layout)

        # Data type selection for network streamer
        network_data_type_layout = QHBoxLayout()
        network_data_type_layout.addWidget(QLabel("Data Type:"))
        self.network_data_type_combo = QComboBox()
        self.network_data_type_combo.addItem("Raw Data", "raw")
        self.network_data_type_combo.addItem("Processed Data (if filters enabled)", "processed")
        network_data_type_layout.addWidget(self.network_data_type_combo)
        network_streamer_layout.addLayout(network_data_type_layout)

        # Add network streamer button
        network_streamer_btn = QPushButton("Add Network Streamer")
        network_streamer_btn.clicked.connect(
            lambda: self.add_network_streamer(
                self.network_streamer_path.text(),
                self.network_data_type_combo.currentData()
            )
        )
        network_streamer_layout.addWidget(network_streamer_btn)

        streamer_layout.addLayout(network_streamer_layout)

        # Custom streamer
        custom_streamer_layout = QVBoxLayout()
        
        # Custom parameters input
        custom_params_layout = QHBoxLayout()
        custom_params_layout.addWidget(QLabel("Custom Streamer:"))
        self.custom_streamer_path = QLineEdit()
        custom_params_layout.addWidget(self.custom_streamer_path)
        custom_streamer_layout.addLayout(custom_params_layout)

        # Data type selection for custom streamer
        custom_data_type_layout = QHBoxLayout()
        custom_data_type_layout.addWidget(QLabel("Data Type:"))
        self.custom_data_type_combo = QComboBox()
        self.custom_data_type_combo.addItem("Raw Data", "raw")
        self.custom_data_type_combo.addItem("Processed Data (if filters enabled)", "processed")
        custom_data_type_layout.addWidget(self.custom_data_type_combo)
        custom_streamer_layout.addLayout(custom_data_type_layout)

        # Add custom streamer button
        custom_streamer_btn = QPushButton("Add Custom Streamer")
        custom_streamer_btn.clicked.connect(
            lambda: self.add_custom_streamer(
                self.custom_streamer_path.text(),
                self.custom_data_type_combo.currentData()
            )
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

    def add_file_streamer(self, file_path: str, data_type: str = "raw") -> None:
        """Add a file streamer using the recording service."""
        if not file_path:
            self.show_error("Streamer Error", "No file path specified")
            return

        if not self.recording_service:
            self.show_error("Service Error", "Recording service not available")
            return

        try:
            # Check if we can start streaming - board must be connected and streaming
            if not self.collector_service.is_connected():
                self.show_error("Connection Error", "Board must be connected to add file streamer")
                return
                
            if not self.collector_service.is_streaming_active():
                self.show_error("Streaming Error", "Board must be streaming to add file streamer")
                return

            # Check if already recording
            if self.recording_service.is_recording():
                self.show_error("Recording Error", "A file recording is already in progress. Stop current recording first.")
                return

            # Start file recording with specified data type
            success = self.recording_service.start_recording(file_path, data_type)

            if success:
                data_type_label = {
                    "raw": "Raw",
                    "processed": "Processed", 
                    "both": "Raw+Processed"
                }.get(data_type, data_type)
                
                streamer_info = {
                    "type": "file",
                    "params": file_path,
                    "data_type": data_type,
                    "display": f"File: {file_path} ({data_type_label})"
                }
                self.active_streamers.append(streamer_info)
                self.streamers_list.addItem(streamer_info["display"])
                self.show_status(f"Added file streamer: {file_path} (type: {data_type_label})")
            else:
                self.show_error("Streamer Error", "Failed to start file recording")

        except Exception as e:
            self.show_error("Streamer Error", f"Error adding file streamer: {str(e)}")

    def add_network_streamer(self, streamer_params: str, data_type: str = "raw") -> None:
        """Add a network streamer using BrainFlow's streaming functionality."""
        if not streamer_params:
            self.show_error("Streamer Error", "No network parameters specified")
            return

        try:
            # Check if collector is available and connected
            if not self.collector_service.is_connected():
                self.show_error("Connection Error", "Board must be connected to add network streamer")
                return

            # Validate streaming board setup
            collector = self.collector_service.collector
            if collector and hasattr(collector, 'board_id'):
                from brainflow.board_shim import BoardIds
                
                # Check if this is a streaming board configuration
                if collector.board_id == BoardIds.STREAMING_BOARD.value:
                    # For streaming boards receiving data, processed data may cause issues
                    if data_type == "processed":
                        reply = QMessageBox.question(
                            self, 
                            "Streaming Board Warning",
                            "You are trying to add a processed data streamer on a streaming board.\n\n"
                            "This may cause connection issues if the sender and receiver are not perfectly synchronized.\n\n"
                            "For streaming boards, it's recommended to use 'Raw Data' and apply processing locally.\n\n"
                            "Do you want to continue anyway?",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.No
                        )
                        
                        if reply == QMessageBox.No:
                            return
                
                # Check if we're setting up a sender (has master_board parameter)
                if hasattr(collector.params, 'master_board') and collector.params.master_board:
                    master_board_id = collector.params.master_board
                    current_preset = getattr(collector, 'preset', 0)
                    
                    # Warn about preset compatibility
                    if current_preset != 0:  # Non-default preset
                        reply = QMessageBox.question(
                            self,
                            "Preset Compatibility Warning", 
                            f"You are using preset {current_preset} with master board {master_board_id}.\n\n"
                            "Make sure the receiving streaming board uses the same preset, "
                            "otherwise you may get socket timeout errors.\n\n"
                            "Do you want to continue?",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.Yes
                        )
                        
                        if reply == QMessageBox.No:
                            return

            # For processed data, we need a custom implementation using DataAccessService
            if data_type == "processed":
                success = self._add_data_access_network_streamer(streamer_params, data_type)
            else:
                # Use traditional BrainFlow streamer for raw data
                success = self.collector_service.add_streamer(streamer_params)

            if success:
                data_type_label = "Processed" if data_type == "processed" else "Raw"
                
                streamer_info = {
                    "type": "network",
                    "params": streamer_params,
                    "data_type": data_type,
                    "display": f"Network: {streamer_params} ({data_type_label})"
                }
                self.active_streamers.append(streamer_info)
                self.streamers_list.addItem(streamer_info["display"])
                self.show_status(f"Added network streamer: {streamer_params} (type: {data_type_label})")
            else:
                self.show_error("Streamer Error", "Failed to add network streamer")

        except Exception as e:
            self.show_error("Streamer Error", f"Error adding network streamer: {str(e)}")

    def add_custom_streamer(self, streamer_params: str, data_type: str = "raw") -> None:
        """Add a custom streamer."""
        if not streamer_params:
            self.show_error("Streamer Error", "No custom parameters specified")
            return

        try:
            # Determine streamer type based on parameters
            if streamer_params.startswith("file://"):
                # Handle as file streamer
                file_path = streamer_params.replace("file://", "").split(":")[0]
                self.add_file_streamer(file_path, data_type)
                return
            elif any(proto in streamer_params for proto in ["://", "udp://", "tcp://"]):
                # Handle as network streamer
                self.add_network_streamer(streamer_params, data_type)
                return
            else:
                # Try as BrainFlow streamer
                if data_type == "processed":
                    success = self._add_data_access_custom_streamer(streamer_params, data_type)
                else:
                    success = self.collector_service.add_streamer(streamer_params)
                
                if success:
                    data_type_label = "Processed" if data_type == "processed" else "Raw"
                    
                    streamer_info = {
                        "type": "custom",
                        "params": streamer_params,
                        "data_type": data_type,
                        "display": f"Custom: {streamer_params} ({data_type_label})"
                    }
                    self.active_streamers.append(streamer_info)
                    self.streamers_list.addItem(streamer_info["display"])
                    self.show_status(f"Added custom streamer: {streamer_params} (type: {data_type_label})")
                else:
                    self.show_error("Streamer Error", "Failed to add custom streamer")

        except Exception as e:
            self.show_error("Streamer Error", f"Error adding custom streamer: {str(e)}")

    def _add_data_access_network_streamer(self, streamer_params: str, data_type: str) -> bool:
        """Add a network streamer that uses DataAccessService for processed data."""
        try:
            # Import DataAccessService
            from ..services.data_access_service import DataAccessService
            
            # Get data access service
            data_service = DataAccessService.get_instance()
            
            # Create a network streamer using our custom implementation
            streamer = DataAccessNetworkStreamer(streamer_params, data_type, data_service)
            
            # Start the streamer
            success = streamer.start()
            
            if success:
                # Store the streamer reference for later cleanup
                if not hasattr(self, '_data_access_streamers'):
                    self._data_access_streamers = []
                self._data_access_streamers.append(streamer)
                
            return success
            
        except Exception as e:
            logging.error(f"Error creating DataAccess network streamer: {e}")
            return False

    def _add_data_access_custom_streamer(self, streamer_params: str, data_type: str) -> bool:
        """Add a custom streamer that uses DataAccessService for processed data."""
        try:
            # Import DataAccessService
            from ..services.data_access_service import DataAccessService
            
            # Get data access service
            data_service = DataAccessService.get_instance()
            
            # Create a custom streamer using our implementation
            streamer = DataAccessCustomStreamer(streamer_params, data_type, data_service)
            
            # Start the streamer
            success = streamer.start()
            
            if success:
                # Store the streamer reference for later cleanup
                if not hasattr(self, '_data_access_streamers'):
                    self._data_access_streamers = []
                self._data_access_streamers.append(streamer)
                
            return success
            
        except Exception as e:
            logging.error(f"Error creating DataAccess custom streamer: {e}")
            return False

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
            data_type = streamer_info.get("data_type", "raw")

            success = False

            if streamer_type == "file":
                # Stop file recording using recording service
                if self.recording_service and self.recording_service.is_recording():
                    success = self.recording_service.stop_recording()
                else:
                    success = True  # Already stopped or not recording

            elif streamer_type in ["network", "custom"]:
                # Check if this is a DataAccess streamer or traditional BrainFlow streamer
                if data_type == "processed" and hasattr(self, '_data_access_streamers'):
                    # Find and stop the DataAccess streamer
                    for i, streamer in enumerate(self._data_access_streamers):
                        if streamer.params == streamer_params:
                            success = streamer.stop()
                            if success:
                                self._data_access_streamers.pop(i)
                            break
                else:
                    # Check if collector is available before trying to remove streamer
                    if not self.collector_service.is_connected():
                        logging.warning(f"Board disconnected, removing {streamer_type} streamer from UI only")
                        success = True  # Just remove from UI since board is gone
                    else:
                        # Remove traditional BrainFlow streamer
                        success = self.collector_service.remove_streamer(streamer_params)

            if success:
                # Remove from UI and tracking
                self.streamers_list.takeItem(selected_row)
                self.active_streamers.pop(selected_row)
                self.show_status(f"Removed {streamer_type} streamer: {streamer_params}")
            else:
                # Don't show error dialog if board is disconnected
                if self.collector_service.is_connected():
                    self.show_error("Streamer Error", f"Failed to remove {streamer_type} streamer")
                else:
                    logging.warning(f"Could not remove {streamer_type} streamer: board disconnected")
                    # Force remove from UI anyway
                    self.streamers_list.takeItem(selected_row)
                    self.active_streamers.pop(selected_row)
                    self.show_status(f"Removed {streamer_type} streamer from UI (board disconnected)")

        except Exception as e:
            # Don't show error dialog if board is disconnected
            if self.collector_service.is_connected():
                self.show_error("Streamer Error", f"Error removing streamer: {str(e)}")
            else:
                logging.warning(f"Error removing streamer (board disconnected): {str(e)}")

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
        try:
            # Stop all DataAccess streamers first
            if hasattr(self, '_data_access_streamers'):
                for streamer in self._data_access_streamers:
                    try:
                        streamer.stop()
                    except Exception as e:
                        logging.error(f"Error stopping DataAccess streamer: {e}")
                self._data_access_streamers.clear()

            # Stop recording service if active
            if self.recording_service and self.recording_service.is_recording():
                try:
                    self.recording_service.stop_recording()
                except Exception as e:
                    logging.debug(f"Error stopping recording on cleanup: {e}")

            # If board is disconnected, just clear the UI without trying to stop streamers
            if not self.collector_service.is_connected():
                logging.info("Board disconnected, clearing streamers from UI only")
                # Clear all streamers from UI
                self.streamers_list.clear()
                self.active_streamers.clear()
                return

            # Stop traditional streamers using the UI method
            while self.active_streamers:
                # Select first item and delete it (but skip file streamers, already handled)
                if self.streamers_list.count() > 0:
                    # Check if it's a file streamer (already stopped above)
                    if self.active_streamers[0]["type"] == "file":
                        # Just remove from UI since recording is already stopped
                        self.streamers_list.takeItem(0)
                        self.active_streamers.pop(0)
                    else:
                        # Use the delete method for network/custom streamers
                        self.streamers_list.setCurrentRow(0)
                        self.delete_selected_streamer()
                else:
                    break
                    
        except Exception as e:
            logging.error(f"Error stopping all streamers: {e}")
            # Force clear UI if there's an error
            self.streamers_list.clear()
            self.active_streamers.clear()
            if hasattr(self, '_data_access_streamers'):
                self._data_access_streamers.clear()

    def on_board_disconnected(self) -> None:
        """Handle board disconnection by cleaning up streamers."""
        try:
            logging.info("Board disconnected, cleaning up streaming panel...")
            
            # Stop all streamers silently
            if hasattr(self, '_data_access_streamers'):
                for streamer in self._data_access_streamers:
                    try:
                        streamer.stop()
                    except Exception as e:
                        logging.debug(f"Error stopping DataAccess streamer on disconnect: {e}")
                self._data_access_streamers.clear()

            # Stop recording service if active
            if self.recording_service and self.recording_service.is_recording():
                try:
                    self.recording_service.stop_recording()
                except Exception as e:
                    logging.debug(f"Error stopping recording on disconnect: {e}")

            # Clear UI
            self.streamers_list.clear()
            self.active_streamers.clear()
            
            # Disable controls
            self.send_config_btn.setEnabled(False)
            
            logging.info("Streaming panel cleaned up successfully")
            
        except Exception as e:
            logging.error(f"Error cleaning up streaming panel on disconnect: {e}")

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


# Custom streamer classes that use DataAccessService
class DataAccessNetworkStreamer:
    """Network streamer that uses DataAccessService for data."""
    
    def __init__(self, params: str, data_type: str, data_service: Any):
        self.params = params
        self.data_type = data_type
        self.data_service = data_service
        self.running = False
        self.callback_id = None
        
        # Parse network parameters
        self._parse_params(params)
        
    def _parse_params(self, params: str) -> None:
        """Parse network parameters from string."""
        # Example: "streaming_board://225.1.1.1:6677"
        # For now, just store the full params - real implementation would parse IP/port
        self.target_address = params
        logging.info(f"Network streamer configured for: {params}")
        
    def start(self) -> bool:
        """Start the network streaming."""
        try:
            # Register callback with DataAccessService
            self.callback_id = self.data_service.register_local_callback(self._on_data)
            self.running = True
            logging.info(f"Started DataAccess network streamer: {self.params} (type: {self.data_type})")
            return True
        except Exception as e:
            logging.error(f"Error starting network streamer: {e}")
            return False
            
    def stop(self) -> bool:
        """Stop the network streaming."""
        try:
            if self.callback_id is not None:
                self.data_service.unregister_local_callback(self.callback_id)
                self.callback_id = None
            self.running = False
            logging.info(f"Stopped DataAccess network streamer: {self.params}")
            return True
        except Exception as e:
            logging.error(f"Error stopping network streamer: {e}")
            return False
            
    def _on_data(self, data: Any, timestamps: Any) -> None:
        """Handle new data from DataAccessService."""
        try:
            if not self.running:
                return
                
            # Get the appropriate data based on type
            if self.data_type == "processed":
                # Use get_current_data which returns processed data if filters enabled
                stream_data, stream_timestamps = self.data_service.get_current_data()
            else:
                # Use get_raw_data for raw data
                stream_data, stream_timestamps = self.data_service.get_raw_data()
                
            # Here you would implement the actual network transmission
            # For now, just log the data size
            if hasattr(stream_data, 'shape') and stream_data.size > 0:
                logging.debug(f"Network streaming {self.data_type} data: {stream_data.shape} to {self.target_address}")
                
        except Exception as e:
            logging.error(f"Error in network streamer data callback: {e}")


class DataAccessCustomStreamer:
    """Custom streamer that uses DataAccessService for data."""
    
    def __init__(self, params: str, data_type: str, data_service: Any):
        self.params = params
        self.data_type = data_type
        self.data_service = data_service
        self.running = False
        self.callback_id = None
        
    def start(self) -> bool:
        """Start the custom streaming."""
        try:
            # Register callback with DataAccessService
            self.callback_id = self.data_service.register_local_callback(self._on_data)
            self.running = True
            logging.info(f"Started DataAccess custom streamer: {self.params} (type: {self.data_type})")
            return True
        except Exception as e:
            logging.error(f"Error starting custom streamer: {e}")
            return False
            
    def stop(self) -> bool:
        """Stop the custom streaming."""
        try:
            if self.callback_id is not None:
                self.data_service.unregister_local_callback(self.callback_id)
                self.callback_id = None
            self.running = False
            logging.info(f"Stopped DataAccess custom streamer: {self.params}")
            return True
        except Exception as e:
            logging.error(f"Error stopping custom streamer: {e}")
            return False
            
    def _on_data(self, data: Any, timestamps: Any) -> None:
        """Handle new data from DataAccessService."""
        try:
            if not self.running:
                return
                
            # Get the appropriate data based on type
            if self.data_type == "processed":
                # Use get_current_data which returns processed data if filters enabled
                stream_data, stream_timestamps = self.data_service.get_current_data()
            else:
                # Use get_raw_data for raw data
                stream_data, stream_timestamps = self.data_service.get_raw_data()
                
            # Here you would implement the actual custom streaming logic
            # For now, just log the data size
            if hasattr(stream_data, 'shape') and stream_data.size > 0:
                logging.debug(f"Custom streaming {self.data_type} data: {stream_data.shape} with params {self.params}")
                
        except Exception as e:
            logging.error(f"Error in custom streamer data callback: {e}")