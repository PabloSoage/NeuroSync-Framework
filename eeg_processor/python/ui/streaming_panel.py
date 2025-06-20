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
from ..services.collector_service import CollectorService
from ..utils.help_system import HelpButton
from ..core.event_system import EventDispatcher, EventType, subscribe


class StreamingPanel(BasePanel):
    """Panel for managing data streaming options."""

    def __init__(
        self, collector_service: CollectorService, parent: Optional[Any] = None
    ) -> None:
        """Initialize the streaming panel."""
        super().__init__(parent)
        self.collector_service = collector_service

        # Import recording service for file streaming
        self.recording_service: Optional[Any] = None
        try:
            from ..services.recording_service import RecordingService

            self.recording_service = RecordingService()
        except Exception as e:
            self.recording_service = None
            logging.error(f"Could not load recording service: {e}")

        # Track active streamers
        self.active_streamers: List[Dict[str, str]] = []

        # Setup UI components
        self.setup_streamer_configuration()
        self.setup_board_configuration()

        # Add stretch to push everything to the top
        self.layout.addStretch()

        # Subscribe to API events for synchronization
        self._setup_event_listeners()

    def _setup_event_listeners(self) -> None:
        """Set up event listeners for API synchronization."""
        try:
            # Subscribe to streamer events
            subscribe(EventType.STREAMER_ADD, self._on_streamer_added_via_api)
            subscribe(EventType.STREAMER_REMOVE, self._on_streamer_removed_via_api)
            subscribe(
                EventType.DEVICE_CONFIG_RESPONSE, self._on_config_response_via_api
            )

            logging.info("Streaming panel event listeners set up successfully")
            logging.info(
                f"Subscribed to events: {[EventType.STREAMER_ADD, EventType.STREAMER_REMOVE, EventType.DEVICE_CONFIG_RESPONSE]}"
            )
        except Exception as e:
            logging.error(f"Error setting up event listeners: {e}")

    def _on_streamer_added_via_api(self, event) -> None:
        """Handle streamer added via API."""
        try:
            logging.info(f"=== STREAMER ADD EVENT RECEIVED ===")
            logging.info(f"Event source: {event.source}")
            logging.info(f"Event data: {event.data}")

            data = event.data
            streamer_params = data.get("streamer_params", "")
            streamer_type = data.get("streamer_type", "auto")
            success = data.get("success", False)

            logging.info(
                f"Parsed - params: {streamer_params}, type: {streamer_type}, success: {success}"
            )

            if not success:
                logging.warning("Event indicates failure, skipping UI update")
                return

            logging.info(f"API streamer added, updating UI: {streamer_params}")

            # Determine display text based on streamer type
            display_text = ""
            data_type = "raw"

            if streamer_type == "file":
                # Parse file streamer params (format: "file_path|data_type")
                if "|" in streamer_params:
                    file_path, data_type = streamer_params.split("|", 1)
                else:
                    file_path, data_type = streamer_params, "raw"

                data_type_label = {
                    "raw": "Raw",
                    "processed": "Processed",
                    "both": "Raw+Processed",
                }.get(data_type, data_type)
                display_text = f"File: {file_path} ({data_type_label})"

            elif streamer_type in ["network", "custom"]:
                display_text = f"{streamer_type.title()}: {streamer_params} (Raw)"
            else:
                display_text = f"Streamer: {streamer_params}"

            # Add to tracking and UI
            streamer_info = {
                "type": streamer_type,
                "params": streamer_params,
                "data_type": data_type,
                "display": display_text,
                "original_template": data.get("original_params", {}).get(
                    "template_params", {}
                ),  # Añadir parámetros originales
            }

            # Check if already exists (avoid duplicates)
            exists = any(
                s["params"] == streamer_params and s["type"] == streamer_type
                for s in self.active_streamers
            )

            if not exists:
                self.active_streamers.append(streamer_info)
                self.streamers_list.addItem(display_text)
                logging.info(f"Added streamer to UI: {display_text}")
            else:
                logging.info(f"Streamer already exists in UI: {display_text}")

            logging.info(f"=== END STREAMER ADD EVENT ===")

        except Exception as e:
            logging.error(f"Error handling API streamer add event: {e}")
            import traceback

            logging.error(f"Traceback: {traceback.format_exc()}")

    def _on_streamer_removed_via_api(self, event) -> None:
        """Handle streamer removed via API."""
        try:
            data = event.data
            streamer_params = data.get("streamer_params", "")
            streamer_type = data.get("streamer_type", "auto")
            success = data.get("success", False)

            if not success:
                return

            logging.info(f"API streamer removed, updating UI: {streamer_params}")

            # Find and remove from tracking
            for i, streamer_info in enumerate(self.active_streamers):
                if (
                    streamer_info["params"] == streamer_params
                    and streamer_info["type"] == streamer_type
                ):

                    # Remove from UI list
                    self.streamers_list.takeItem(i)
                    # Remove from tracking
                    self.active_streamers.pop(i)
                    logging.info(
                        f"Removed streamer from UI: {streamer_info['display']}"
                    )
                    break
            else:
                logging.warning(
                    f"Streamer not found in UI for removal: {streamer_params}"
                )

        except Exception as e:
            logging.error(f"Error handling API streamer remove event: {e}")

    def _on_config_response_via_api(self, event) -> None:
        """Handle config response via API."""
        try:
            data = event.data
            response = data.get("response", "")

            if response:
                logging.info(f"API config response, updating UI: {response}")
                self.config_response_text.setText(response)

        except Exception as e:
            logging.error(f"Error handling API config response event: {e}")

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

        # File path row
        file_path_layout = QHBoxLayout()
        file_path_layout.addWidget(QLabel("File Streamer:"))
        self.file_streamer_path = QLineEdit()
        self.file_streamer_path.setText("recordings/eeg_stream.csv")
        file_path_layout.addWidget(self.file_streamer_path)
        file_streamer_layout.addLayout(file_path_layout)

        # Data type row for file streamer
        file_type_layout = QHBoxLayout()
        file_type_layout.addWidget(QLabel("Data Type:"))
        self.file_data_type_combo = QComboBox()
        self.file_data_type_combo.addItem("Raw Data", "raw")
        self.file_data_type_combo.addItem("Processed Data", "processed")
        self.file_data_type_combo.addItem("Both Raw+Processed", "both")
        file_type_layout.addWidget(self.file_data_type_combo)

        file_streamer_btn = QPushButton("Add File Streamer")
        file_streamer_btn.clicked.connect(
            lambda: self.add_streamer(
                self.file_streamer_path.text(),
                streamer_type="file",
                data_type=self.file_data_type_combo.currentData(),
            )
        )
        file_type_layout.addWidget(file_streamer_btn)
        file_streamer_layout.addLayout(file_type_layout)

        streamer_layout.addLayout(file_streamer_layout)

        # Network streamer - Raw data only, simpler layout
        network_streamer_layout = QHBoxLayout()
        network_streamer_layout.addWidget(QLabel("Network Streamer (Raw):"))
        self.network_streamer_path = QLineEdit()
        self.network_streamer_path.setText("streaming_board://225.1.1.1:6677")
        network_streamer_layout.addWidget(self.network_streamer_path)

        network_streamer_btn = QPushButton("Add Network Streamer")
        network_streamer_btn.clicked.connect(
            lambda: self.add_streamer(
                self.network_streamer_path.text(), streamer_type="network"
            )
        )
        network_streamer_layout.addWidget(network_streamer_btn)

        streamer_layout.addLayout(network_streamer_layout)

        # Custom streamer - Raw data only, simpler layout
        custom_streamer_layout = QHBoxLayout()
        custom_streamer_layout.addWidget(QLabel("Custom Streamer (Raw):"))
        self.custom_streamer_path = QLineEdit()
        custom_streamer_layout.addWidget(self.custom_streamer_path)

        custom_streamer_btn = QPushButton("Add Custom Streamer")
        custom_streamer_btn.clicked.connect(
            lambda: self.add_streamer(
                self.custom_streamer_path.text(), streamer_type="custom"
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

    def add_streamer(
        self, streamer_params: str, streamer_type: str = "auto", data_type: str = "raw"
    ) -> None:
        """Add a streamer to the board (unified method like the old version)."""
        if not streamer_params:
            self.show_error("Streamer Error", "No streamer parameters specified")
            return

        try:
            # Auto-detect streamer type if not specified
            if streamer_type == "auto":
                if streamer_params.startswith("file://") or streamer_params.endswith(
                    (".csv", ".txt")
                ):
                    streamer_type = "file"
                elif any(
                    proto in streamer_params
                    for proto in ["streaming_board://", "udp://", "tcp://"]
                ):
                    streamer_type = "network"
                else:
                    streamer_type = "custom"

            logging.info(f"=== ADDING STREAMER ===")
            logging.info(f"Streamer type: {streamer_type}")
            logging.info(f"Streamer params: {streamer_params}")
            logging.info(f"Data type: {data_type}")

            success = False
            display_text = ""

            if streamer_type == "file":
                # Handle file streaming with RecordingService (no preset validation needed)
                logging.info("Processing file streamer - no preset validation required")
                success = self._add_file_streamer(streamer_params, data_type)
                if success:
                    data_type_label = {
                        "raw": "Raw",
                        "processed": "Processed",
                        "both": "Raw+Processed",
                    }.get(data_type, data_type)
                    display_text = f"File: {streamer_params} ({data_type_label})"

            elif streamer_type in ["network", "custom"]:
                # Handle network/custom streaming with BrainFlow (raw only)
                logging.info(
                    f"Processing {streamer_type} streamer - preset validation REQUIRED"
                )

                if not self.collector_service.is_connected():
                    self.show_error(
                        "Connection Error",
                        "Board must be connected to add network/custom streamer",
                    )
                    return

                logging.info(
                    f"Board is connected, starting preset validation for {streamer_type} streamer..."
                )

                # CRITICAL: Validate preset for network/custom streamers
                try:
                    logging.info("Calling _validate_streaming_board_setup()...")
                    self._validate_streaming_board_setup()
                    logging.info(
                        "Preset validation PASSED, proceeding with streamer addition"
                    )
                except Exception as validation_error:
                    logging.error(f"Preset validation FAILED: {validation_error}")
                    # If validation fails (user cancels), don't add the streamer
                    return

                # If we get here, validation passed - add the streamer
                logging.info("Attempting to add streamer to collector...")
                success = self.collector_service.add_streamer(streamer_params)

                if success:
                    display_text = f"{streamer_type.title()}: {streamer_params} (Raw)"
                    logging.info(f"Successfully added {streamer_type} streamer")
                else:
                    logging.error(
                        f"Failed to add {streamer_type} streamer to collector"
                    )

            if success:
                # Track the streamer
                streamer_info = {
                    "type": streamer_type,
                    "params": streamer_params,
                    "data_type": data_type,
                    "display": display_text,
                }
                self.active_streamers.append(streamer_info)
                self.streamers_list.addItem(display_text)
                self.show_status(f"Added {streamer_type} streamer: {streamer_params}")
                logging.info(
                    f"Streamer tracking added - Total active streamers: {len(self.active_streamers)}"
                )
            else:
                self.show_error(
                    "Streamer Error", f"Failed to add {streamer_type} streamer"
                )
                logging.error(f"Failed to add {streamer_type} streamer")

            logging.info(f"=== END ADDING STREAMER ===")

        except Exception as e:
            logging.error(f"Error adding streamer: {str(e)}")
            self.show_error("Streamer Error", f"Error adding streamer: {str(e)}")

    def _add_file_streamer(self, file_path: str, data_type: str) -> bool:
        """Add file streamer using RecordingService."""
        if not self.recording_service:
            self.show_error("Service Error", "Recording service not available")
            return False

        # Check prerequisites
        if not self.collector_service.is_connected():
            self.show_error(
                "Connection Error", "Board must be connected to add file streamer"
            )
            return False

        if not self.collector_service.is_streaming_active():
            self.show_error(
                "Streaming Error", "Board must be streaming to add file streamer"
            )
            return False

        if self.recording_service.is_recording():
            self.show_error(
                "Recording Error",
                "A file recording is already in progress. Stop current recording first.",
            )
            return False

        # Start recording
        return self.recording_service.start_recording(file_path, data_type)

    def _validate_streaming_board_setup(self) -> None:
        """Validate streaming board configuration and show warnings if needed."""
        try:
            collector = self.collector_service.collector
            if not collector:
                raise Exception("No collector available for validation")

            # Import BrainFlow presets for proper comparison
            from brainflow.board_shim import BrainFlowPresets

            # DEBUGGING: Log all collector attributes related to preset
            logging.info(f"=== PRESET VALIDATION DEBUG ===")
            logging.info(f"Collector type: {type(collector)}")
            logging.info(
                f"Collector attributes: {[attr for attr in dir(collector) if 'preset' in attr.lower()]}"
            )

            # Try multiple ways to get the preset
            current_preset = None

            # Method 1: Direct attribute
            if hasattr(collector, "preset"):
                current_preset = collector.preset
                logging.info(f"Method 1 - collector.preset: {current_preset}")

            # Method 2: getattr with default
            preset_getattr = getattr(
                collector, "preset", BrainFlowPresets.DEFAULT_PRESET.value
            )
            logging.info(
                f"Method 2 - getattr(collector, 'preset', DEFAULT): {preset_getattr}"
            )

            # Method 3: Check if collector has board_id and params to infer preset
            if hasattr(collector, "board_id"):
                logging.info(f"Collector board_id: {collector.board_id}")

            if hasattr(collector, "params"):
                logging.info(f"Collector params type: {type(collector.params)}")
                if hasattr(collector.params, "__dict__"):
                    logging.info(
                        f"Collector params attributes: {collector.params.__dict__}"
                    )

            # Use the direct attribute if available, otherwise getattr
            if current_preset is None:
                current_preset = preset_getattr

            logging.info(
                f"Final current_preset value: {current_preset} (type: {type(current_preset)})"
            )
            logging.info(
                f"Comparing with DEFAULT_PRESET: {BrainFlowPresets.DEFAULT_PRESET.value}"
            )

            # CRITICAL: Check for non-zero preset for ANY board when adding network/custom streamers
            if current_preset != BrainFlowPresets.DEFAULT_PRESET.value:
                logging.info(
                    f"NON-DEFAULT PRESET DETECTED! current_preset={current_preset}, showing reconnection dialog"
                )

                reply = QMessageBox.question(
                    self,
                    "Preset Compatibility Error",
                    f"Network and custom streamers require preset {BrainFlowPresets.DEFAULT_PRESET.value} (Default) for optimal compatibility.\n\n"
                    f"Current preset: {current_preset}\n\n"
                    f"Non-default presets can cause socket timeout errors and streaming failures.\n\n"
                    f"Do you want to disconnect and reconnect with preset {BrainFlowPresets.DEFAULT_PRESET.value}?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )

                if reply == QMessageBox.Yes:
                    logging.info("User chose to reconnect with default preset")
                    # Disconnect and reconnect with preset 0
                    self._reconnect_with_preset_zero()
                    logging.info("Reconnection completed successfully")
                else:
                    logging.info(
                        "User cancelled due to preset compatibility requirements"
                    )
                    raise Exception(
                        "User cancelled due to preset compatibility requirements"
                    )
            else:
                logging.info(
                    f"DEFAULT PRESET DETECTED - validation passed (current_preset={current_preset})"
                )

            # Additional validation for streaming boards
            from brainflow.board_shim import BoardIds

            if (
                hasattr(collector, "board_id")
                and collector.board_id == BoardIds.STREAMING_BOARD.value
            ):
                if (
                    hasattr(collector.params, "master_board")
                    and collector.params.master_board
                ):
                    master_board_id = collector.params.master_board
                    logging.info(
                        f"Streaming board validation passed: preset {current_preset}, master board {master_board_id}"
                    )

            logging.info(f"=== END PRESET VALIDATION DEBUG ===")

        except Exception as e:
            logging.error(f"Validation failed: {e}")
            raise e

    def _reconnect_with_preset_zero(self) -> None:
        """Disconnect current board and reconnect with preset 0."""
        try:
            from brainflow.board_shim import BrainFlowPresets

            # Get current connection settings
            if (
                not hasattr(self.collector_service, "collector")
                or not self.collector_service.collector
            ):
                raise Exception("No collector available for reconnection")

            collector = self.collector_service.collector
            current_board_id = collector.board_id
            current_params = collector.params

            logging.info(
                f"Reconnecting board {current_board_id} with preset {BrainFlowPresets.DEFAULT_PRESET.value}..."
            )

            # Find connection panel through parent widget hierarchy
            connection_panel = None
            parent_widget = self.parent()
            while parent_widget is not None:
                if hasattr(parent_widget, "connection_panel"):
                    connection_panel = parent_widget.connection_panel
                    break
                parent_widget = (
                    parent_widget.parent() if hasattr(parent_widget, "parent") else None
                )

            if not connection_panel:
                raise Exception("Could not find connection panel for reconnection")

            # Stop streaming if active
            was_streaming = self.collector_service.is_streaming_active()
            if was_streaming:
                logging.info("Stopping stream for reconnection...")
                self.collector_service.stop_stream()

            # Disconnect current board
            logging.info("Disconnecting current board...")
            success = self.collector_service.disconnect_from_board()
            if not success:
                raise Exception("Failed to disconnect current board")

            # Update connection panel preset to default
            logging.info("Setting preset to default in connection panel...")
            preset_combo = connection_panel.preset_combo
            for i in range(preset_combo.count()):
                if preset_combo.itemData(i) == BrainFlowPresets.DEFAULT_PRESET.value:
                    preset_combo.setCurrentIndex(i)
                    break

            # Convert BrainFlowInputParams to dictionary for reconnection
            params_dict = self._convert_params_to_dict(current_params)

            # Reconnect with default preset
            logging.info("Reconnecting with default preset...")
            success = self.collector_service.connect_to_board(
                current_board_id, params_dict, BrainFlowPresets.DEFAULT_PRESET.value
            )
            if not success:
                raise Exception("Failed to reconnect with default preset")

            # Update connection panel UI
            connection_panel.connect_btn.setEnabled(False)
            connection_panel.disconnect_btn.setEnabled(True)
            connection_panel.start_stream_btn.setEnabled(True)

            # Update board info display
            board_info = self.collector_service.get_board_info()
            if board_info:
                info_text = f"<b>Reconnected Board Information (Preset {BrainFlowPresets.DEFAULT_PRESET.value}):</b><br>"
                for key, value in board_info.items():
                    if key == "eeg_names" and isinstance(value, list):
                        info_text += f"<b>{key.replace('_', ' ').title()}:</b> {', '.join(value)}<br>"
                    elif not isinstance(value, list) or len(value) < 10:
                        info_text += (
                            f"<b>{key.replace('_', ' ').title()}:</b> {value}<br>"
                        )
                connection_panel.board_info_label.setText(info_text)

            # Restart streaming if it was active
            if was_streaming:
                logging.info("Restarting stream...")
                success = self.collector_service.start_stream()
                if success:
                    connection_panel.start_stream_btn.setEnabled(False)
                    connection_panel.stop_stream_btn.setEnabled(True)
                    logging.info("Stream restarted successfully")
                else:
                    logging.warning("Failed to restart stream after reconnection")

            self.show_status(
                f"Board reconnected with preset {BrainFlowPresets.DEFAULT_PRESET.value} for optimal streaming compatibility"
            )
            logging.info("Reconnection with default preset completed successfully")

        except Exception as e:
            error_msg = f"Failed to reconnect with default preset: {str(e)}"
            logging.error(error_msg)
            self.show_error("Reconnection Error", error_msg)
            raise

    def _convert_params_to_dict(self, params: Any) -> Dict[str, Any]:
        """Convert BrainFlowInputParams to dictionary."""
        params_dict = {}
        param_attrs = [
            "serial_port",
            "mac_address",
            "ip_address",
            "ip_port",
            "other_info",
            "serial_number",
            "file",
            "master_board",
            "timeout",
        ]

        for attr in param_attrs:
            if hasattr(params, attr):
                value = getattr(params, attr)
                if value:  # Only add non-empty values
                    params_dict[attr] = value

        return params_dict

    def delete_selected_streamer(self) -> None:
        """Delete the selected streamer (unified method like the old version)."""
        selected_item = self.streamers_list.currentItem()
        if not selected_item:
            self.show_error("Streamer Error", "No streamer selected")
            return

        try:
            selected_row = self.streamers_list.row(selected_item)
            if selected_row >= len(self.active_streamers):
                # Fallback to old behavior if active_streamers is out of sync
                streamer_params = selected_item.text()
                success = self._delete_legacy_streamer(streamer_params)
            else:
                streamer_info = self.active_streamers[selected_row]
                success = self._delete_tracked_streamer(streamer_info, selected_row)

            if success:
                self.streamers_list.takeItem(selected_row)
                if selected_row < len(self.active_streamers):
                    self.active_streamers.pop(selected_row)

        except Exception as e:
            if self.collector_service.is_connected():
                self.show_error("Streamer Error", f"Error removing streamer: {str(e)}")
            else:
                logging.warning(
                    f"Error removing streamer (board disconnected): {str(e)}"
                )

    def _delete_tracked_streamer(
        self, streamer_info: Dict[str, str], selected_row: int
    ) -> bool:
        """Delete a tracked streamer using the appropriate method."""
        streamer_type = streamer_info["type"]
        streamer_params = streamer_info["params"]

        if streamer_type == "file":
            # Stop file recording using recording service
            if self.recording_service and self.recording_service.is_recording():
                success = self.recording_service.stop_recording()
            else:
                success = True  # Already stopped

            if success:
                self.show_status(f"Removed file streamer: {streamer_params}")
            return success

        elif streamer_type in ["network", "custom"]:
            # Remove BrainFlow streamer
            if not self.collector_service.is_connected():
                logging.warning(
                    f"Board disconnected, removing {streamer_type} streamer from UI only"
                )
                self.show_status(
                    f"Removed {streamer_type} streamer from UI (board disconnected)"
                )
                return True
            else:
                success = self.collector_service.remove_streamer(streamer_params)
                if success:
                    self.show_status(
                        f"Removed {streamer_type} streamer: {streamer_params}"
                    )
                return success

        return False

    def _delete_legacy_streamer(self, streamer_params: str) -> bool:
        """Delete streamer using legacy method (for backward compatibility)."""
        if not self.collector_service.is_connected():
            logging.warning("Board disconnected, removing streamer from UI only")
            self.show_status(f"Removed streamer from UI (board disconnected)")
            return True
        else:
            success = self.collector_service.remove_streamer(streamer_params)
            if success:
                self.show_status(f"Removed streamer: {streamer_params}")
            return success

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
        self.send_config_btn.setEnabled(enabled)

        # If disabling, stop all active streamers
        if not enabled:
            self.stop_all_streamers()

    def stop_all_streamers(self) -> None:
        """Stop all active streamers."""
        try:
            # Stop recording service if active
            if self.recording_service and self.recording_service.is_recording():
                try:
                    self.recording_service.stop_recording()
                except Exception as e:
                    logging.debug(f"Error stopping recording on cleanup: {e}")

            # Clear UI regardless of board connection status
            self.streamers_list.clear()
            self.active_streamers.clear()

        except Exception as e:
            logging.error(f"Error stopping all streamers: {e}")
            # Force clear UI if there's an error
            self.streamers_list.clear()
            self.active_streamers.clear()

    def on_board_disconnected(self) -> None:
        """Handle board disconnection by cleaning up streamers."""
        try:
            logging.info("Board disconnected, cleaning up streaming panel...")
            self.stop_all_streamers()
            self.send_config_btn.setEnabled(False)
            logging.info("Streaming panel cleaned up successfully")
        except Exception as e:
            logging.error(f"Error cleaning up streaming panel on disconnect: {e}")

    # Legacy API methods for backward compatibility
    def update_streamer_list(self, streamers_list: List[str]) -> bool:
        """Update the list of streamers from the API."""
        try:
            self.streamers_list.clear()
            self.active_streamers.clear()
            for streamer in streamers_list:
                self.streamers_list.addItem(streamer)
                # Create minimal tracking info for legacy streamers
                self.active_streamers.append(
                    {
                        "type": "legacy",
                        "params": streamer,
                        "data_type": "raw",
                        "display": streamer,
                    }
                )
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
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(message, 3000)
            else:
                print(f"Status: {message}")
        except Exception as e:
            print(f"Status: {message}")
