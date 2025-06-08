"""
Main window for unified application.

This module provides the main application window that integrates the EEG processor
and input collector modules.
"""

from typing import Any

from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QMessageBox,
    QSplitter,
)

from .recording_panel import UnifiedRecordingPanel
from .sync_visualization_panel import SynchronizedDataVisualization
from ..utils.theme_manager import UnifiedThemeManager


class UnifiedMainWindow(QMainWindow):
    """
    Main window for the unified application.

    This class creates a UI that integrates both the EEG processor and input collector
    applications with unified recording controls.
    """

    def __init__(
        self, coordinator: Any, integration_service: Any, input_app: Any, eeg_app: Any
    ) -> None:
        """Initialize the main window."""
        super().__init__()

        # Store references
        self.coordinator = coordinator
        self.integration_service = integration_service
        self.input_app = input_app
        self.eeg_app = eeg_app

        # Set window properties
        self.setWindowTitle("Unified EEG & Input Collector")
        self.setGeometry(100, 100, 1400, 900)

        # Apply dark theme
        self.theme_manager = UnifiedThemeManager()
        self.theme_manager.apply_dark_theme(self)

        # Create UI
        self._create_ui()

        # Hide recording controls in original modules
        self._hide_original_recording_controls()

        # Connect signals
        self._connect_signals()

        # Setup timer for periodic updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui_state)
        self.update_timer.start(500)  # Update every 500ms

        # Initial UI update
        self.update_ui_state()

    def _hide_original_recording_controls(self) -> None:
        """Hide recording controls in original modules."""
        # Hide Input Collector recording controls
        if hasattr(self.input_app, "ui_manager") and hasattr(
            self.input_app.ui_manager, "hide_recording_controls"
        ):
            self.input_app.ui_manager.hide_recording_controls()

        # For EEG processor, we need to remove the recording tab
        self._hide_eeg_processor_recording_tab()

        # Get help button from recording panel and add to our unified recording panel
        self._move_help_button_to_unified_panel()

    def _hide_eeg_processor_recording_tab(self) -> None:
        """Hide the recording tab from EEG processor."""
        if hasattr(self.eeg_app, "tabs"):
            # Find the "Recording" tab
            for i in range(self.eeg_app.tabs.count()):
                if self.eeg_app.tabs.tabText(i) == "Recording":
                    # Hide the tab by removing it
                    self.eeg_app.tabs.removeTab(i)
                    break

    def _move_help_button_to_unified_panel(self) -> None:
        """Move help button from EEG processor's recording panel to unified panel."""
        if hasattr(self.eeg_app, "recording_panel") and hasattr(
            self.eeg_app.recording_panel, "help_button"
        ):
            help_button = self.eeg_app.recording_panel.help_button
            if help_button:
                # Remove it from its original location
                help_button.setParent(None)
                # Add it to our recording panel's info section
                self.recording_panel.add_help_button(help_button)

    def _create_ui(self) -> None:
        """Create the user interface."""
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Main layout
        main_layout = QVBoxLayout(main_widget)

        # Create header with title and status
        header_layout = QHBoxLayout()
        title_label = QLabel("Unified EEG & Input Collector")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        self.status_label = QLabel("Ready")
        header_layout.addWidget(self.status_label)
        main_layout.addLayout(header_layout)

        # Create recording panel
        self.recording_panel = UnifiedRecordingPanel(self.coordinator)
        main_layout.addWidget(self.recording_panel)

        # Create a splitter for the two module interfaces
        self.splitter = QSplitter(Qt.Horizontal)

        # Create tabs for each module
        self.tabs = QTabWidget()

        # Create EEG processor tab
        eeg_container = QWidget()
        eeg_layout = QVBoxLayout(eeg_container)
        eeg_layout.setContentsMargins(0, 0, 0, 0)

        # Replace the central widget of the EEG processor app
        # with its own tab widget, then add to our container
        if hasattr(self.eeg_app, "tabs"):
            eeg_layout.addWidget(self.eeg_app.tabs)
        else:
            # Fallback if the structure is different
            eeg_layout.addWidget(QLabel("EEG Processor interface not available"))

        # Create input collector tab
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)

        # Extract the input collector app's central widget
        input_central = self.input_app.centralWidget()
        if input_central:
            # Find the main layout in the input collector app
            main_layout_widget = None
            for child in input_central.children():
                if isinstance(child, QVBoxLayout) or isinstance(child, QHBoxLayout):
                    main_layout_widget = child
                    break

            # If we found the main layout, add its widgets to our container
            if main_layout_widget:
                for i in range(main_layout_widget.count()):
                    widget = main_layout_widget.itemAt(i).widget()
                    if widget:
                        input_layout.addWidget(widget)
            else:
                # If we couldn't extract widgets, add the whole central widget
                input_layout.addWidget(input_central)
        else:
            # Fallback if the structure is different
            input_layout.addWidget(QLabel("Input Collector interface not available"))

        # Create synchronized visualization tab
        self.sync_viz_panel = SynchronizedDataVisualization(self.integration_service)

        # Add tabs
        self.tabs.addTab(eeg_container, "EEG Processing")
        self.tabs.addTab(input_container, "Input Collection")
        self.tabs.addTab(self.sync_viz_panel, "Synchronized View")

        # Add tabs to main layout
        main_layout.addWidget(self.tabs)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # Connect tab change signal
        self.tabs.currentChanged.connect(self.coordinator.handle_tab_change)

        # Connect coordinator signals
        self.coordinator.status_message.connect(self.show_status)
        self.coordinator.recording_started.connect(self.on_recording_started)
        self.coordinator.recording_stopped.connect(self.on_recording_stopped)

    @pyqtSlot(str, str)
    def show_status(self, message: str, color: str = "default") -> None:
        """
        Show a status message.

        Args:
            message: Status message text
            color: Message color ('success', 'warning', 'error', or 'default')
        """
        # Update status bar
        self.statusBar().showMessage(message)

        # Update status label with color
        if color == "success":
            self.status_label.setStyleSheet("color: #5FB878;")
        elif color == "warning":
            self.status_label.setStyleSheet("color: #FFAA33;")
        elif color == "error":
            self.status_label.setStyleSheet("color: #FF5555;")
        else:
            self.status_label.setStyleSheet("color: #E0E0E0;")

        self.status_label.setText(message)

    def on_recording_started(self) -> None:
        """Handle recording started event."""
        # Update recording panel
        self.recording_panel.update_recording_state(True)

    def on_recording_stopped(self) -> None:
        """Handle recording stopped event."""
        # Update recording panel
        self.recording_panel.update_recording_state(False)

    def update_ui_state(self) -> None:
        """Update the UI state based on current system status."""
        # Update recording time if recording
        if self.coordinator.is_recording:
            recording_time = self.integration_service.get_recording_time()
            self.recording_panel.update_recording_time(recording_time)

        # Update ready state indicators
        eeg_ready = self.integration_service.get_eeg_ready_state()
        input_ready = self.integration_service.get_input_ready_state()
        self.recording_panel.update_ready_state(eeg_ready, input_ready)

    def update_recording_controls(self, is_recording: bool, is_ready: bool) -> None:
        """
        Update recording controls.

        Args:
            is_recording: Whether recording is active
            is_ready: Whether the system is ready for recording
        """
        self.recording_panel.update_recording_state(is_recording)
        self.recording_panel.update_ready_state(
            self.integration_service.get_eeg_ready_state(),
            self.integration_service.get_input_ready_state(),
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        # Stop recording if active
        if self.coordinator.is_recording:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Recording is in progress. Stop recording and exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                self.coordinator.stop_recording()
            else:
                event.ignore()
                return

        # Cleanup resources
        self.update_timer.stop()

        # Clean up synchronization resources
        if hasattr(self.integration_service, "cleanup"):
            self.integration_service.cleanup()

        # Accept the event to close the window
        event.accept()
