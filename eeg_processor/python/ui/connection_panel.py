from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QLineEdit,
    QFileDialog,
    QScrollArea,
    QWidget,
)

from .base_panel import BasePanel
from ..collectors.board_configuration import BoardConfiguration
from ..utils.help_system import HelpButton


class ConnectionPanel(BasePanel):
    """Panel for managing board connections and streaming."""

    # Define signals specific to connection panel
    board_connected = pyqtSignal()
    board_disconnected = pyqtSignal()
    stream_started = pyqtSignal()
    stream_stopped = pyqtSignal()

    def __init__(self, collector_service, visualization_service, parent=None):
        """Initialize the connection panel."""
        super().__init__(parent)
        self.collector_service = collector_service
        self.visualization_service = visualization_service

        # Setup UI components
        self.setup_visualization_control()
        self.setup_board_selection()
        self.setup_board_info()

        # Initially update visible parameters based on selected board
        self.on_board_type_changed()

    def setup_visualization_control(self):
        """Set up visualization control group."""
        visualization_group = QGroupBox("Visualization Control")
        visualization_layout = QVBoxLayout(visualization_group)

        # Add help button to visualization
        viz_help_layout = QHBoxLayout()
        self.show_viz_btn = QPushButton("Show Visualization Window")
        self.show_viz_btn.clicked.connect(self.show_visualization)
        self.show_viz_btn.setEnabled(False)
        self.show_viz_btn.setStyleSheet("font-weight: bold; padding: 6px;")
        viz_help_layout.addWidget(self.show_viz_btn)
        viz_help_layout.addWidget(HelpButton("eeg_visualization", self))
        visualization_layout.addLayout(viz_help_layout)

        # Add to main layout
        self.layout.addWidget(visualization_group)

    def setup_board_selection(self):
        """Set up board selection group."""
        board_group = QGroupBox("Board Selection")
        board_layout = QVBoxLayout(board_group)

        # Board type organization
        board_type_layout = QVBoxLayout()
        board_type_label_layout = QHBoxLayout()
        board_type_label = QLabel("Select Board:")
        board_type_label_layout.addWidget(board_type_label)
        board_type_label_layout.addWidget(HelpButton("board_selection", self))
        board_type_layout.addLayout(board_type_label_layout)

        # Get board groups from BoardConfiguration
        self.board_groups = BoardConfiguration.get_all_boards()

        # Create combo box for board selection
        self.board_type_combo = QComboBox()
        for name, board_id in self.board_groups:
            self.board_type_combo.addItem(name, board_id)

        # Filter functionality for easier board selection
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter:")
        self.filter_edit = QLineEdit()
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

        # Connection parameters header with help button
        param_help_layout = QHBoxLayout()
        param_help_layout.addWidget(QLabel("Connection Parameters"))
        param_help_layout.addWidget(HelpButton("connection_params", self))
        param_help_layout.addStretch()
        param_layout.addLayout(param_help_layout)

        # Create parameter fields
        self.param_fields = {}

        # Serial port
        serial_layout = QHBoxLayout()
        serial_label = QLabel("Serial Port:")
        self.param_fields["serial_port"] = QLineEdit()
        serial_layout.addWidget(serial_label)
        serial_layout.addWidget(self.param_fields["serial_port"])
        param_layout.addLayout(serial_layout)

        # IP fields
        ip_layout = QHBoxLayout()
        ip_label = QLabel("IP Address:")
        self.param_fields["ip_address"] = QLineEdit()
        self.param_fields["ip_address"].setText("225.1.1.1")  # Default
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.param_fields["ip_address"])
        param_layout.addLayout(ip_layout)

        ip_port_layout = QHBoxLayout()
        ip_port_label = QLabel("IP Port:")
        self.param_fields["ip_port"] = QSpinBox()
        self.param_fields["ip_port"].setRange(0, 65535)
        self.param_fields["ip_port"].setValue(6677)  # Default
        ip_port_layout.addWidget(ip_port_label)
        ip_port_layout.addWidget(self.param_fields["ip_port"])
        param_layout.addLayout(ip_port_layout)

        # MAC Address
        mac_layout = QHBoxLayout()
        mac_label = QLabel("MAC Address:")
        self.param_fields["mac_address"] = QLineEdit()
        mac_layout.addWidget(mac_label)
        mac_layout.addWidget(self.param_fields["mac_address"])
        param_layout.addLayout(mac_layout)

        # Serial Number
        serial_num_layout = QHBoxLayout()
        serial_num_label = QLabel("Serial Number:")
        self.param_fields["serial_number"] = QLineEdit()
        serial_num_layout.addWidget(serial_num_label)
        serial_num_layout.addWidget(self.param_fields["serial_number"])
        param_layout.addLayout(serial_num_layout)

        # File for playback board
        file_layout = QHBoxLayout()
        file_label = QLabel("File Path:")
        self.param_fields["file"] = QLineEdit()
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
        other_info_layout = QHBoxLayout()
        other_info_label = QLabel("Other Info:")
        self.param_fields["other_info"] = QLineEdit()
        other_info_layout.addWidget(other_info_label)
        other_info_layout.addWidget(self.param_fields["other_info"])
        param_layout.addLayout(other_info_layout)

        # Timeout
        timeout_layout = QHBoxLayout()
        timeout_label = QLabel("Timeout (ms):")
        self.param_fields["timeout"] = QSpinBox()
        self.param_fields["timeout"].setRange(0, 100000)
        self.param_fields["timeout"].setValue(15000)  # Default
        timeout_layout.addWidget(timeout_label)
        timeout_layout.addWidget(self.param_fields["timeout"])
        param_layout.addLayout(timeout_layout)

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

        # Add board group to main layout
        self.layout.addWidget(board_group)

    def setup_board_info(self):
        """Set up board information group."""
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

        # Add to main layout
        self.layout.addWidget(info_group)

    def on_board_type_changed(self):
        """Handle board type selection changes."""
        board_id = self.board_type_combo.currentData()
        if board_id is None:
            return

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
                            self.param_fields[param].setStyleSheet(
                                "border: 1px solid #E0A030;"
                            )
                        else:
                            self.param_fields[param].setStyleSheet(
                                "border: 1px solid #E0A030; background-color: rgba(224, 160, 48, 0.1);"
                            )
                    else:
                        if isinstance(self.param_fields[param], QComboBox):
                            self.param_fields[param].setStyleSheet("")
                        else:
                            self.param_fields[param].setStyleSheet(
                                "background-color: #252526;"
                            )

            # Get and display board description
            try:
                preset = self.preset_combo.currentData()
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
                        if isinstance(description["eeg_names"], list):
                            eeg_names = description["eeg_names"]
                        else:
                            eeg_names = str(description["eeg_names"]).split(",")
                        desc_text += f"<b>Channel Names:</b> {', '.join(eeg_names)}<br>"

                    self.board_info_label.setText(desc_text)
                else:
                    self.board_info_label.setText(f"Selected board ID: {board_id}")

            except Exception as e:
                self.board_info_label.setText(f"Selected board ID: {board_id}")
                self.show_status(f"Could not get board description: {str(e)}")

        except Exception as e:
            self.show_error(
                "Board Selection Error", f"Error updating board parameters: {str(e)}"
            )

    def filter_boards(self):
        """Filter the boards in the dropdown based on search text."""
        filter_text = self.filter_edit.text().lower()
        self.board_type_combo.clear()

        for name, board_id in self.board_groups:
            if filter_text in name.lower():
                self.board_type_combo.addItem(name, board_id)

        # If no matching boards, show a message
        if self.board_type_combo.count() == 0:
            self.board_type_combo.addItem("No matching boards", -1)

    def browse_file(self):
        """Browse for a file for playback board."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Data File", "", "CSV files (*.csv);; All Files (*)"
        )
        if filename:
            self.param_fields["file"].setText(filename)

    def connect_board(self):
        """Connect to the selected EEG board."""
        try:
            board_id = self.board_type_combo.currentData()
            selected_board_name = self.board_type_combo.currentText()

            # Debug logging to see what board ID we're getting
            self.show_status(f"Connecting to {selected_board_name}, ID: {board_id}")

            # Fix validation to ensure synthetic board (ID=0) isn't rejected
            # Original condition rejected board_id == -1, but synthetic board is 0
            if board_id is None:
                self.show_error("Connection Error", "Please select a valid board")
                return

            # Get selected preset
            preset = self.preset_combo.currentData()

            # Build parameters dictionary from UI fields
            params = {}
            for param_name, field in self.param_fields.items():
                if isinstance(field, QComboBox):
                    if field.isEnabled() and field.currentData() is not None:
                        params[param_name] = field.currentData()
                elif isinstance(field, QSpinBox):
                    if field.isEnabled():
                        params[param_name] = field.value()
                else:  # QLineEdit
                    if field.isEnabled() and field.text():
                        params[param_name] = field.text()

            # Connect using the service
            success = self.collector_service.connect_to_board(board_id, params, preset)

            if success:
                # Update UI
                self.connect_btn.setEnabled(False)
                self.disconnect_btn.setEnabled(True)
                self.start_stream_btn.setEnabled(True)

                # Update board info display
                board_info = self.collector_service.get_board_info()
                if board_info:
                    info_text = "<b>Connected Board Information:</b><br>"
                    for key, value in board_info.items():
                        if key == "eeg_names" and isinstance(value, list):
                            info_text += f"<b>{key.replace('_', ' ').title()}:</b> {', '.join(value)}<br>"
                        elif (
                            not isinstance(value, list) or len(value) < 10
                        ):  # Don't show long lists
                            info_text += (
                                f"<b>{key.replace('_', ' ').title()}:</b> {value}<br>"
                            )
                    self.board_info_label.setText(info_text)

                # Emit signal
                self.board_connected.emit()
                self.show_status("Board connected successfully")
            else:
                self.show_error("Connection Error", "Failed to connect to board")

        except Exception as e:
            self.show_error("Connection Error", f"Failed to connect to board: {str(e)}")

    def disconnect_board(self):
        """Disconnect from the EEG board."""
        try:
            if self.collector_service.is_streaming_active():
                self.stop_stream()

            success = self.collector_service.disconnect_from_board()

            if success:
                # Update UI
                self.connect_btn.setEnabled(True)
                self.disconnect_btn.setEnabled(False)
                self.start_stream_btn.setEnabled(False)
                self.stop_stream_btn.setEnabled(False)
                self.show_viz_btn.setEnabled(False)

                # Reset board info
                self.board_info_label.setText("No board connected")

                # Emit signal
                self.board_disconnected.emit()
                self.show_status("Board disconnected")
            else:
                self.show_error(
                    "Disconnection Error", "Failed to disconnect from board"
                )

        except Exception as e:
            self.show_error(
                "Disconnection Error", f"Error during disconnection: {str(e)}"
            )

    def start_stream(self):
        """Start streaming data from the board."""
        try:
            success = self.collector_service.start_stream()

            if success:
                # Initialize the processor service with the board's sampling rate
                sampling_rate = self.collector_service.get_sampling_rate()
                if sampling_rate > 0:
                    # Remove reference to non-existent collector_service.processor_service
                    try:
                        # Import processor service if needed
                        from ..services.processor_service import ProcessorService

                        # Initialize processor service
                        processor_service = (
                            self.processor_service
                            if hasattr(self, "processor_service")
                            else ProcessorService()
                        )
                        processor_service.initialize_processor(sampling_rate)

                        # Create visualizer with the processor
                        self.visualization_service.create_eeg_visualizer(
                            self.collector_service.collector,
                            processor_service.processor,
                        )

                        # Save processor service for future use
                        self.processor_service = processor_service
                    except Exception as e:
                        # Fallback approach - create visualizer without processor
                        self.show_status(
                            f"Note: Signal processing unavailable - {str(e)}"
                        )
                        self.visualization_service.create_eeg_visualizer(
                            self.collector_service.collector, None
                        )
                else:
                    # Create visualizer without processor
                    self.visualization_service.create_eeg_visualizer(
                        self.collector_service.collector, None
                    )

                # Start visualization
                self.visualization_service.start_eeg_visualization()

                # Update UI
                self.start_stream_btn.setEnabled(False)
                self.stop_stream_btn.setEnabled(True)
                self.show_viz_btn.setEnabled(False)

                # Emit signal
                self.stream_started.emit()
                self.show_status("Streaming started")
            else:
                self.show_error("Streaming Error", "Failed to start streaming")

        except Exception as e:
            self.show_error("Streaming Error", f"Error starting stream: {str(e)}")

    def stop_stream(self):
        """Stop streaming data from the board."""
        try:
            success = self.collector_service.stop_stream()

            if success:
                # Stop visualization if running
                self.visualization_service.stop_eeg_visualization()

                # Update UI
                self.start_stream_btn.setEnabled(True)
                self.stop_stream_btn.setEnabled(False)
                self.show_viz_btn.setEnabled(False)

                # Emit signal
                self.stream_stopped.emit()
                self.show_status("Streaming stopped")
            else:
                self.show_error("Streaming Error", "Failed to stop streaming")

        except Exception as e:
            self.show_error("Streaming Error", f"Error stopping stream: {str(e)}")

    def show_visualization(self):
        """Show the EEG visualization if it was closed."""
        try:
            if self.visualization_service.visualization_closed():
                # Recreate and restart visualization
                success = self.visualization_service.create_eeg_visualizer(
                    self.collector_service.collector,
                    None,  # We'll initialize the processor later
                )

                if success:
                    self.visualization_service.start_eeg_visualization()
                    self.show_viz_btn.setEnabled(False)
                    self.show_status("Visualization window reopened")
                else:
                    self.show_error(
                        "Visualization Error", "Failed to create visualization"
                    )

        except Exception as e:
            self.show_error(
                "Visualization Error", f"Error showing visualization: {str(e)}"
            )

    def update_visualization_button(self, enabled):
        """Update the state of the visualization button."""
        self.show_viz_btn.setEnabled(enabled)
        if enabled:
            self.show_viz_btn.setStyleSheet(
                "font-weight: bold; background-color: #4CAF50; color: white; padding: 6px;"
            )
        else:
            self.show_viz_btn.setStyleSheet("font-weight: bold; padding: 6px;")

    def enable_streaming(self, enabled):
        """Enable or disable streaming controls."""
        self.start_stream_btn.setEnabled(enabled)
        self.stop_stream_btn.setEnabled(False)

    # Add methods for API interaction
    def _update_connection_state(self, connected):
        """Update connection state from API call."""
        try:
            self.connect_btn.setEnabled(not connected)
            self.disconnect_btn.setEnabled(connected)

            # Enable/disable start stream button if connected
            self.start_stream_btn.setEnabled(connected)

            return True
        except Exception as e:
            self.show_error("Connection State Update Error", str(e))
            return False

    def _update_streaming_state(self, streaming):
        """Update streaming state from API call."""
        try:
            self.start_stream_btn.setEnabled(not streaming)
            self.stop_stream_btn.setEnabled(streaming)

            # Enable/disable visualization button based on streaming state
            self.show_viz_btn.setEnabled(
                not streaming
                and hasattr(self, "visualization_service")
                and self.visualization_service.visualization_closed()
            )

            return True
        except Exception as e:
            self.show_error("Streaming State Update Error", str(e))
            return False

    def _update_params_from_dict(self, params):
        """Update connection parameters from dictionary."""
        try:
            # Set field values if they exist in the params dictionary
            for param_name, value in params.items():
                if param_name in self.param_fields:
                    field = self.param_fields[param_name]

                    if isinstance(field, QComboBox):
                        # For combo boxes, set by data value
                        for i in range(field.count()):
                            if field.itemData(i) == value:
                                field.setCurrentIndex(i)
                                break
                    elif isinstance(field, QSpinBox):
                        # For spinboxes, set value directly
                        field.setValue(int(value))
                    else:
                        # For text fields (QLineEdit), set text
                        field.setText(str(value))

            return True
        except Exception as e:
            self.show_error("Parameter Update Error", str(e))
            return False

    def get_connection_settings(self):
        """Get current connection settings."""
        settings = {
            "board_id": self.board_type_combo.currentData(),
            "preset": self.preset_combo.currentData(),
            "params": {},
        }

        # Get parameter values
        for param_name, field in self.param_fields.items():
            if field.isEnabled():
                if isinstance(field, QComboBox):
                    settings["params"][param_name] = field.currentData()
                elif isinstance(field, QSpinBox):
                    settings["params"][param_name] = field.value()
                else:  # QLineEdit
                    settings["params"][param_name] = field.text()

        return settings
