import logging
from typing import Optional, Any

from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer, pyqtSlot
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTabWidget,
    QMessageBox,
)
from brainflow.board_shim import BoardShim

# Import adapters
from .adapters.qt_interaction_adapter import QtInteractionAdapter

# Import services
from .services.collector_service import CollectorService
from .services.processor_service import ProcessorService
from .services.recording_service import RecordingService
from .services.visualization_service import VisualizationService

# Import UI components
from .ui.advanced_panel import AdvancedProcessingPanel
from .ui.connection_panel import ConnectionPanel
from .ui.mne_panel import MNEPanel
from .ui.processing_panel import ProcessingPanel
from .ui.recording_panel import RecordingPanel
from .ui.streaming_panel import StreamingPanel

# Import utils
from .utils.help_system import show_eeg_concepts_help
from .utils.theme_manager import ThemeManager


class EEGProcessorApp(QMainWindow):
    """
    Main application for EEG data collection, processing and visualization.

    This class coordinates UI components and services but delegates specific
    responsibilities to specialized classes.
    """

    def __init__(self) -> None:
        """Initialize the EEG processor application."""
        super().__init__()

        BoardShim.enable_dev_board_logger()

        # Setup theme
        self.theme_manager = ThemeManager()
        self.theme_manager.apply_dark_theme(self)

        self.setWindowTitle("EEG Processor")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize services
        self.collector_service = CollectorService.get_instance()
        self.processor_service = ProcessorService()
        self.visualization_service = VisualizationService()
        self.recording_service = RecordingService()

        # Initialize MNE service
        self.mne_service: Optional["MNEService"] = None
        try:
            from .services.mne_service import MNEService

            self.mne_service = MNEService.get_instance()
        except ImportError:
            self.mne_service = None
            logging.warning("MNE service not available")

        # Initialize Qt interaction adapter
        self.qt_adapter = QtInteractionAdapter(self)

        # Application state
        self.is_streaming = False

        # Initialize UI
        self.setup_ui()

        # Timer for updating status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Update every second

        logging.info("EEG Processor application initialized")

    def setup_ui(self) -> None:
        """Set up the user interface."""
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Add help header
        help_header_layout = QHBoxLayout()
        app_title_label = QLabel("EEG Processor")
        app_title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        help_header_layout.addWidget(app_title_label)
        help_header_layout.addStretch()

        help_btn = QPushButton("Help")
        help_btn.clicked.connect(lambda: show_eeg_concepts_help(self))
        help_btn.setStyleSheet("background-color: #007ACC;")
        help_header_layout.addWidget(help_btn)

        main_layout.addLayout(help_header_layout)

        # Create tabs
        self.tabs = QTabWidget()
        # Ensure proper sizing policy for tab widget
        self.tabs.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        main_layout.addWidget(self.tabs)

        # Create UI components and connect them to services
        self.connection_panel = ConnectionPanel(
            self.collector_service, self.visualization_service
        )
        self.processing_panel = ProcessingPanel(
            self.collector_service, self.processor_service, self.visualization_service
        )
        self.recording_panel = RecordingPanel(
            self.collector_service, self.recording_service
        )
        self.streaming_panel = StreamingPanel(self.collector_service)
        self.advanced_panel = AdvancedProcessingPanel(
            self.collector_service, self.processor_service
        )

        # Check if MNE is available
        try:
            import mne

            # Add visualization_service parameter to MNEPanel instantiation
            self.mne_panel = MNEPanel(
                self.collector_service,
                self.processor_service,
                visualization_service=self.visualization_service,
            )
            mne_available = True
        except ImportError:
            mne_available = False
            logging.warning("MNE package not found. MNE integration will be disabled.")

        # Add panels to tabs
        self.tabs.addTab(self.connection_panel, "Connection")
        self.tabs.addTab(self.processing_panel, "Processing")
        self.tabs.addTab(self.recording_panel, "Recording")
        self.tabs.addTab(self.streaming_panel, "Streaming")
        self.tabs.addTab(self.advanced_panel, "Advanced Processing")
        if mne_available:
            self.tabs.addTab(self.mne_panel, "MNE Integration")

        # Connect signals from each panel to handle app-level state
        self.connect_panel_signals()

        # Status bar for showing current status
        self.statusBar().showMessage("Ready")

    def connect_panel_signals(self) -> None:
        """Connect signals from UI components to handle application state."""
        # Connection panel signals
        self.connection_panel.stream_started.connect(self.on_stream_started)
        self.connection_panel.stream_stopped.connect(self.on_stream_stopped)
        self.connection_panel.board_connected.connect(self.on_board_connected)
        self.connection_panel.board_disconnected.connect(self.on_board_disconnected)

        # Recording panel signals
        self.recording_panel.recording_started.connect(self.on_recording_started)
        self.recording_panel.recording_stopped.connect(self.on_recording_stopped)

        # Connect status messages from all panels
        for panel in [
            self.connection_panel,
            self.processing_panel,
            self.recording_panel,
            self.streaming_panel,
            self.advanced_panel,
        ]:
            panel.status_message.connect(self.show_status_message)
            panel.error_message.connect(self.show_error_message)

        # Add MNE panel if available
        if hasattr(self, "mne_panel"):
            self.mne_panel.status_message.connect(self.show_status_message)
            self.mne_panel.error_message.connect(self.show_error_message)

        # Setup event system subscriptions for API synchronization
        self._setup_api_event_subscriptions()

    def _setup_api_event_subscriptions(self) -> None:
        """Setup subscriptions for API-generated events."""
        try:
            from .core.event_system import EventDispatcher, EventType

            event_dispatcher = EventDispatcher.get_instance()

            # Subscribe to events that need app-level handling
            event_dispatcher.subscribe(
                EventType.STREAM_START, self._handle_api_stream_start
            )
            event_dispatcher.subscribe(
                EventType.STREAM_STOP, self._handle_api_stream_stop
            )
            event_dispatcher.subscribe(
                EventType.BOARD_CONNECT, self._handle_api_board_connect
            )
            event_dispatcher.subscribe(
                EventType.BOARD_DISCONNECT, self._handle_api_board_disconnect
            )

        except Exception as e:
            logging.error(f"Error setting up API event subscriptions: {e}")

    @pyqtSlot()
    def _handle_api_stream_start(self, event: Any) -> None:
        """Handle stream start from API with thread safety."""
        # Use Qt's thread-safe mechanism to update GUI
        QTimer.singleShot(0, self.on_stream_started)

    @pyqtSlot()
    def _handle_api_stream_stop(self, event: Any) -> None:
        """Handle stream stop from API with thread safety."""
        QTimer.singleShot(0, self.on_stream_stopped)

    @pyqtSlot()
    def _handle_api_board_connect(self, event: Any) -> None:
        """Handle board connect from API with thread safety."""
        QTimer.singleShot(0, self.on_board_connected)

    @pyqtSlot()
    def _handle_api_board_disconnect(self, event: Any) -> None:
        """Handle board disconnect from API with thread safety."""
        QTimer.singleShot(0, self.on_board_disconnected)

    def update_status(self) -> None:
        """Update status information periodically."""
        # Get status from recording service
        if self.recording_service.is_recording():
            duration = self.recording_service.get_recording_duration()
            self.recording_panel.update_recording_status(
                f"Recording... ({duration:.1f}s)"
            )

        # Check visualization status
        if self.visualization_service.visualization_closed() and self.is_streaming:
            self.connection_panel.update_visualization_button(True)
        elif self.visualization_service.visualization_visible() and self.is_streaming:
            self.connection_panel.update_visualization_button(False)

    def on_stream_started(self) -> None:
        """Handle stream started event."""
        self.is_streaming = True
        self.recording_panel.enable_recording(True)
        self.processing_panel.enable_processing(True)
        self.advanced_panel.enable_processing(True)
        if hasattr(self, "mne_panel"):
            self.mne_panel.enable_processing(True)

    def on_stream_stopped(self) -> None:
        """Handle stream stopped event."""
        self.is_streaming = False
        self.recording_panel.enable_recording(False)
        self.processing_panel.enable_processing(False)
        self.advanced_panel.enable_processing(False)
        if hasattr(self, "mne_panel"):
            self.mne_panel.enable_processing(False)

    def on_board_connected(self) -> None:
        """Handle board connected event."""
        # Enable streaming controls but not recording yet
        self.connection_panel.enable_streaming(True)
        self.streaming_panel.enable_streaming(True)

    def on_board_disconnected(self) -> None:
        """Handle board disconnected event."""
        self.is_streaming = False
        # Disable all controls that need a board connection
        self.connection_panel.enable_streaming(False)
        self.recording_panel.enable_recording(False)
        self.processing_panel.enable_processing(False)
        self.streaming_panel.enable_streaming(False)
        self.advanced_panel.enable_processing(False)
        if hasattr(self, "mne_panel"):
            self.mne_panel.enable_processing(False)

    def on_recording_started(self) -> None:
        """Handle recording started event."""
        pass  # Any app-level changes needed when recording starts

    def on_recording_stopped(self) -> None:
        """Handle recording stopped event."""
        pass  # Any app-level changes needed when recording stops

    def show_status_message(self, message: str) -> None:
        """Show a status message."""
        self.statusBar().showMessage(message)

    def show_error_message(self, title: str, message: str) -> None:
        """Show an error message box."""
        QMessageBox.critical(self, title, message)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle application close event."""
        # Clean up advanced panel ICA processes first
        if hasattr(self, "advanced_panel") and hasattr(self.advanced_panel, "controller"):
            try:
                # Check if controller has ICA process service and clean it up
                if hasattr(self.advanced_panel.controller, 'ica_process_service'):
                    self.advanced_panel.controller.ica_process_service.cleanup()
                    logging.info("ICA process service cleaned up")
            except Exception as e:
                logging.error(f"Error cleaning up ICA process service: {e}")
        
        # Clean up other resources
        self.collector_service.cleanup()
        self.visualization_service.cleanup()
        self.recording_service.cleanup()

        # Clean up MNE service
        if self.mne_service:
            self.mne_service.cleanup()

        # Clean up Qt adapter
        if hasattr(self, "qt_adapter"):
            del self.qt_adapter

        event.accept()
