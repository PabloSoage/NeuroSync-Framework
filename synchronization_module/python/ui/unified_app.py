"""
Unified GUI application combining EEG Processor and Input Collector.

This module provides the main application window that integrates both
EEG processing and input collection functionalities with synchronization
capabilities.
"""
import sys
import logging
from typing import Optional, Any

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QWidget, QApplication,
    QMenuBar, QStatusBar, QMessageBox, QHBoxLayout, QPushButton, QLabel
)

from input_collector.python.input_collector_app import InputCollectorApp
from eeg_processor.python.eeg_processor_app import EEGProcessorApp

# Import synchronization components
from .synchronization_panel import SynchronizationPanel
from ..services.synchronization_service import SynchronizationService
from ..services.dataset_service import DatasetService
from ..adapters.qt_integration_adapter import QtIntegrationAdapter


class ExportWorker(QThread):
    """Worker thread for dataset export to avoid UI blocking."""
    
    export_finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, dataset_service, sync_data, filepath, format_name, metadata):
        super().__init__()
        self.dataset_service = dataset_service
        self.sync_data = sync_data
        self.filepath = filepath
        self.format_name = format_name
        self.metadata = metadata
    
    def run(self):
        """Run export in background thread."""
        try:
            success = self.dataset_service.export_dataset(
                self.sync_data,
                self.filepath,
                self.format_name,
                self.metadata
            )
            
            if success:
                self.export_finished.emit(True, "Export completed successfully")
            else:
                self.export_finished.emit(False, "Export failed")
                
        except Exception as e:
            self.export_finished.emit(False, f"Export error: {e}")


class UnifiedApp(QMainWindow):
    """
    Main unified application combining EEG Processor and Input Collector.
    
    This application provides tabs for EEG processing, input collection,
    and synchronization/dataset creation.
    """
    
    # Signals for application events
    synchronization_started = pyqtSignal(float)  # precision_ms
    synchronization_stopped = pyqtSignal()
    dataset_exported = pyqtSignal(str, bool)  # filepath, success
    
    def __init__(self):
        """Initialize the unified application."""
        super().__init__()
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Application state
        self.is_synchronizing = False
        self.synchronization_precision = 1.0
        self.export_worker = None
        
        # Initialize services
        self._init_services()
        
        # Initialize UI
        self._init_ui()
        
        # Initialize adapters
        self._init_adapters()
        
        # Setup connections
        self._setup_connections()
        
        self.logger.info("Unified application initialized successfully")
    
    def _init_services(self) -> None:
        """Initialize core services."""
        try:
            # Initialize synchronization service
            self.sync_service = SynchronizationService()
            
            # Initialize dataset service
            self.dataset_service = DatasetService()
            
            self.logger.info("Core services initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            raise
    
    def _init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("BCI Dataset Creator - Unified Interface")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create status bar at the top
        self._create_status_header()
        main_layout.addWidget(self.status_header)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_tabs()
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Apply dark theme
        self._apply_dark_theme()
    
    def _create_status_header(self) -> None:
        """Create status header with sync controls."""
        self.status_header = QWidget()
        layout = QHBoxLayout(self.status_header)
        
        # Status labels
        self.eeg_status_label = QLabel("EEG: Disconnected")
        self.eeg_status_label.setStyleSheet("color: #FF5555; font-weight: bold;")
        layout.addWidget(self.eeg_status_label)
        
        self.input_status_label = QLabel("Input: Ready")
        self.input_status_label.setStyleSheet("color: #5FB878; font-weight: bold;")
        layout.addWidget(self.input_status_label)
        
        layout.addStretch()
        
        # Sync status
        self.sync_status_label = QLabel("Sync: Inactive")
        self.sync_status_label.setStyleSheet("color: #888888; font-weight: bold;")
        layout.addWidget(self.sync_status_label)
        
        # Quick sync button
        self.quick_sync_btn = QPushButton("Quick Sync")
        self.quick_sync_btn.clicked.connect(self._toggle_quick_sync)
        self.quick_sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #007ACC;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
        """)
        layout.addWidget(self.quick_sync_btn)
    
    def _create_tabs(self) -> None:
        """Create application tabs."""
        try:
            # EEG Processor tab
            self.eeg_app = EEGProcessorApp()
            self.eeg_app.setParent(self)  # Embed in our app
            self.tab_widget.addTab(self.eeg_app, "EEG Processor")
            
            # Input Collector tab
            self.input_app = InputCollectorApp()
            self.input_app.setParent(self)  # Embed in our app
            self.tab_widget.addTab(self.input_app, "Input Collector")
            
            # Synchronization tab
            self.sync_panel = SynchronizationPanel()
            self.tab_widget.addTab(self.sync_panel, "Synchronization & Datasets")
            
            self.logger.info("Application tabs created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to create tabs: {e}")
            # Create fallback minimal interface
            self._create_fallback_interface()
    
    def _create_fallback_interface(self) -> None:
        """Create fallback interface if main apps fail to load."""
        error_widget = QWidget()
        layout = QVBoxLayout(error_widget)
        
        error_label = QLabel("Error: Failed to load application components")
        error_label.setStyleSheet("color: #FF5555; font-size: 14px; font-weight: bold;")
        layout.addWidget(error_label)
        
        # Still add synchronization panel
        try:
            self.sync_panel = SynchronizationPanel()
            self.tab_widget.addTab(self.sync_panel, "Synchronization")
        except Exception as e:
            self.logger.error(f"Failed to create sync panel: {e}")
        
        self.tab_widget.addTab(error_widget, "Error")
    
    def _init_adapters(self) -> None:
        """Initialize adapter components."""
        try:
            self.qt_adapter = QtIntegrationAdapter(self)
            
            # Connect adapters to applications if they exist
            if hasattr(self, 'eeg_app'):
                self.qt_adapter.set_eeg_app(self.eeg_app)
            
            if hasattr(self, 'input_app'):
                self.qt_adapter.set_input_app(self.input_app)
            
            # Connect adapter to sync service
            self.qt_adapter.set_sync_service(self.sync_service)
            
            self.logger.info("Adapters initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize adapters: {e}")
    
    def _setup_connections(self) -> None:
        """Setup signal connections."""
        try:
            # Connect synchronization panel signals
            if hasattr(self, 'sync_panel'):
                self.sync_panel.start_sync_requested.connect(self._start_synchronization)
                self.sync_panel.stop_sync_requested.connect(self._stop_synchronization)
                self.sync_panel.export_dataset_requested.connect(self._export_dataset)
            
            # Connect adapter signals
            if hasattr(self, 'qt_adapter'):
                self.qt_adapter.status_updated.connect(self._update_status_display)
            
            # Setup update timer for status
            self.status_timer = QTimer()
            self.status_timer.timeout.connect(self._update_status)
            self.status_timer.start(1000)  # Update every second
            
            self.logger.info("Signal connections established")
            
        except Exception as e:
            self.logger.error(f"Failed to setup connections: {e}")
    
    def _create_menu_bar(self) -> None:
        """Create application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('&File')
        
        # Export action
        export_action = file_menu.addAction('&Export Dataset...')
        export_action.triggered.connect(self._show_export_dialog)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = file_menu.addAction('E&xit')
        exit_action.triggered.connect(self.close)
        
        # Sync menu
        sync_menu = menubar.addMenu('&Sync')
        
        start_sync_action = sync_menu.addAction('&Start Synchronization')
        start_sync_action.triggered.connect(lambda: self._start_synchronization(1.0))
        
        stop_sync_action = sync_menu.addAction('S&top Synchronization')
        stop_sync_action.triggered.connect(self._stop_synchronization)
        
        # Help menu
        help_menu = menubar.addMenu('&Help')
        
        about_action = help_menu.addAction('&About')
        about_action.triggered.connect(self._show_about)
    
    def _apply_dark_theme(self) -> None:
        """Apply dark theme to the application."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2D2D30;
                color: #E0E0E0;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #252526;
            }
            QTabBar::tab {
                background-color: #3E3E42;
                color: #E0E0E0;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #007ACC;
                color: #FFFFFF;
            }
            QTabBar::tab:hover {
                background-color: #5FB878;
            }
            QStatusBar {
                background-color: #007ACC;
                color: #FFFFFF;
            }
            QMenuBar {
                background-color: #2D2D30;
                color: #E0E0E0;
            }
            QMenuBar::item:selected {
                background-color: #007ACC;
            }
            QMenu {
                background-color: #2D2D30;
                color: #E0E0E0;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #007ACC;
            }
        """)
    
    def _start_synchronization(self, precision_ms: float) -> None:
        """Start synchronization with specified precision."""
        if self.is_synchronizing:
            return
        
        try:
            # Set EEG service from adapter
            if hasattr(self, 'qt_adapter'):
                eeg_service = self.qt_adapter.get_eeg_service()
                input_service = self.qt_adapter.get_input_service()
                
                if eeg_service:
                    self.sync_service.set_eeg_service(eeg_service)
                if input_service:
                    self.sync_service.set_input_service(input_service)
            
            # Start synchronization
            success = self.sync_service.start_synchronization(precision_ms)
            
            if success:
                self.is_synchronizing = True
                self.synchronization_precision = precision_ms
                self.synchronization_started.emit(precision_ms)
                
                # Update UI
                self.sync_status_label.setText(f"Sync: Active ({precision_ms}ms)")
                self.sync_status_label.setStyleSheet("color: #5FB878; font-weight: bold;")
                self.quick_sync_btn.setText("Stop Sync")
                
                # Update sync panel if it exists
                if hasattr(self, 'sync_panel'):
                    self.sync_panel.on_sync_started()
                
                self.status_bar.showMessage(f"Synchronization started with {precision_ms}ms precision")
                self.logger.info(f"Synchronization started with {precision_ms}ms precision")
            else:
                self._show_error("Synchronization Error", "Failed to start synchronization")
                
        except Exception as e:
            self.logger.error(f"Error starting synchronization: {e}")
            self._show_error("Synchronization Error", f"Error starting synchronization: {e}")
    
    def _stop_synchronization(self) -> None:
        """Stop synchronization."""
        if not self.is_synchronizing:
            return
        
        try:
            success = self.sync_service.stop_synchronization()
            
            if success:
                self.is_synchronizing = False
                self.synchronization_stopped.emit()
                
                # Update UI
                self.sync_status_label.setText("Sync: Inactive")
                self.sync_status_label.setStyleSheet("color: #888888; font-weight: bold;")
                self.quick_sync_btn.setText("Quick Sync")
                
                # Update sync panel if it exists
                if hasattr(self, 'sync_panel'):
                    self.sync_panel.on_sync_stopped()
                
                self.status_bar.showMessage("Synchronization stopped")
                self.logger.info("Synchronization stopped")
            else:
                self._show_error("Synchronization Error", "Failed to stop synchronization")
                
        except Exception as e:
            self.logger.error(f"Error stopping synchronization: {e}")
            self._show_error("Synchronization Error", f"Error stopping synchronization: {e}")
    
    def _toggle_quick_sync(self) -> None:
        """Toggle quick synchronization."""
        if self.is_synchronizing:
            self._stop_synchronization()
        else:
            self._start_synchronization(1.0)  # Default 1ms precision
    
    def _export_dataset(self, params: dict) -> None:
        """Export synchronized dataset in background thread."""
        try:
            # Show that export is starting
            if hasattr(self, 'sync_panel'):
                self.sync_panel.on_export_started()
            
            # Get synchronized data
            duration = params.get('duration_seconds', 30)
            sync_data = self.sync_service.get_synchronized_data(duration)
            
            if not sync_data or sync_data.get('metadata', {}).get('sample_count', 0) == 0:
                self._show_error("Export Error", "No synchronized data available. Make sure synchronization is active and data is being collected.")
                if hasattr(self, 'sync_panel'):
                    self.sync_panel.on_export_finished(False, "No data available")
                return
            
            # Prepare export metadata
            export_metadata = params.get('metadata', {})
            export_metadata.update({
                'export_params': params,
                'include_metadata': params.get('include_metadata', True),
                'compress_data': params.get('compress_data', True)
            })
            
            # Start export in background thread
            self.export_worker = ExportWorker(
                self.dataset_service,
                sync_data,
                params.get('filepath', 'dataset.h5'),
                params.get('format', 'hdf5'),
                export_metadata
            )
            
            self.export_worker.export_finished.connect(self._on_export_finished)
            self.export_worker.start()
            
            self.status_bar.showMessage("Exporting dataset...")
            self.logger.info(f"Started dataset export to {params.get('filepath')}")
            
        except Exception as e:
            self.logger.error(f"Error starting dataset export: {e}")
            self._show_error("Export Error", f"Error starting dataset export: {e}")
            
            # Update sync panel
            if hasattr(self, 'sync_panel'):
                self.sync_panel.on_export_finished(False, f"Export error: {e}")
    
    def _on_export_finished(self, success: bool, message: str) -> None:
        """Handle export finished signal."""
        try:
            if success:
                self.status_bar.showMessage(f"Dataset exported successfully")
                self.logger.info(f"Dataset export completed: {message}")
            else:
                self.status_bar.showMessage(f"Dataset export failed")
                self.logger.error(f"Dataset export failed: {message}")
            
            # Update sync panel
            if hasattr(self, 'sync_panel'):
                self.sync_panel.on_export_finished(success, message)
            
            # Emit signal
            self.dataset_exported.emit("", success)
            
            # Clean up worker
            if self.export_worker:
                self.export_worker.deleteLater()
                self.export_worker = None
                
        except Exception as e:
            self.logger.error(f"Error handling export finished signal: {e}")
    
    def _show_export_dialog(self) -> None:
        """Show export dialog."""
        if hasattr(self, 'sync_panel'):
            # Switch to sync tab and trigger export
            self.tab_widget.setCurrentWidget(self.sync_panel)
            # The sync panel handles the export dialog
    
    def _update_status(self) -> None:
        """Update status information."""
        try:
            # Update EEG status
            if hasattr(self, 'qt_adapter'):
                eeg_status = self.qt_adapter.get_eeg_status()
                if eeg_status.get('connected', False):
                    if eeg_status.get('streaming', False):
                        self.eeg_status_label.setText("EEG: Streaming")
                        self.eeg_status_label.setStyleSheet("color: #5FB878; font-weight: bold;")
                    else:
                        self.eeg_status_label.setText("EEG: Connected")
                        self.eeg_status_label.setStyleSheet("color: #FFAA33; font-weight: bold;")
                else:
                    self.eeg_status_label.setText("EEG: Disconnected")
                    self.eeg_status_label.setStyleSheet("color: #FF5555; font-weight: bold;")
                
                # Update input status
                input_status = self.qt_adapter.get_input_status()
                if input_status.get('active', False):
                    if input_status.get('recording', False):
                        self.input_status_label.setText("Input: Recording")
                        self.input_status_label.setStyleSheet("color: #5FB878; font-weight: bold;")
                    else:
                        self.input_status_label.setText("Input: Active")
                        self.input_status_label.setStyleSheet("color: #FFAA33; font-weight: bold;")
                else:
                    self.input_status_label.setText("Input: Ready")
                    self.input_status_label.setStyleSheet("color: #888888; font-weight: bold;")
            
            # Update sync panel status
            if hasattr(self, 'sync_panel') and self.is_synchronizing:
                sync_status = self.sync_service.get_status()
                self.sync_panel.update_sync_status(sync_status)
                
        except Exception as e:
            self.logger.error(f"Error updating status: {e}")
    
    def _update_status_display(self, status_info: dict) -> None:
        """Update status display from adapter."""
        message = status_info.get('message', '')
        if message:
            self.status_bar.showMessage(message)
    
    def _show_error(self, title: str, message: str) -> None:
        """Show error message."""
        QMessageBox.critical(self, title, message)
    
    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(self, "About BCI Dataset Creator",
                         "BCI Dataset Creator v1.0\n\n"
                         "A unified application for collecting and synchronizing\n"
                         "EEG and input data for Brain-Computer Interface research.\n\n"
                         "Combines EEG Processor and Input Collector with\n"
                         "Lab Streaming Layer (LSL) synchronization.")
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle application close event."""
        try:
            # Stop synchronization if active
            if self.is_synchronizing:
                self._stop_synchronization()
            
            # Clean up services
            if hasattr(self, 'sync_service'):
                self.sync_service.cleanup()
            
            if hasattr(self, 'dataset_service'):
                self.dataset_service.cleanup()
            
            # Close embedded applications
            if hasattr(self, 'eeg_app'):
                self.eeg_app.close()
            
            if hasattr(self, 'input_app'):
                self.input_app.close()
            
            self.logger.info("Unified application closed")
            event.accept()
            
        except Exception as e:
            self.logger.error(f"Error during close: {e}")
            event.accept()


def run_unified_app() -> None:
    """Run the unified application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Create and show main window
    main_window = UnifiedApp()
    main_window.show()
    
    # Run application
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_unified_app()