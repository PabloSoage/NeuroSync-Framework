"""
Unified Application for EEG Processing and Input Collection.

This module integrates the EEG processor and input collector applications
into a single unified interface.
"""

import sys

from PyQt5.QtWidgets import QApplication

import eeg_processor.python.eeg_processor_app as eeg_processor_app

# Import from both modules
import input_collector.python.input_collector_app as input_collector_app
from .app.unified_app_coordinator import UnifiedAppCoordinator
from .services.integration_service import IntegrationService

# Import the unified components
from .ui.main_window import UnifiedMainWindow


class UnifiedApplication:
    """
    Unified application combining EEG processing and input collection.

    This class initializes both modules and sets up the integration layer.
    """

    def __init__(self):
        """Initialize the unified application."""
        # Create Qt application
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")

        # Initialize services from both modules
        self._initialize_services()

        # Create the integration service
        self.integration_service = IntegrationService(
            self.input_collector_components, self.eeg_processor_components
        )

        # Create application coordinator
        self.coordinator = UnifiedAppCoordinator(self.integration_service)

        # Create main window
        self.main_window = UnifiedMainWindow(
            self.coordinator,
            self.integration_service,
            self.input_collector_components["app"],
            self.eeg_processor_components["app"],
        )

        # Connect the coordinator to the UI
        self.coordinator.set_main_window(self.main_window)

    def _initialize_services(self):
        """Initialize services from both modules."""
        # Initialize Input Collector components
        self.input_collector_components = self._initialize_input_collector()

        # Initialize EEG Processor components
        self.eeg_processor_components = self._initialize_eeg_processor()

    def _initialize_input_collector(self):
        """
        Initialize input collector components.

        Returns:
            dict: Dictionary containing input collector components
        """
        # Create input collector app without showing the window
        input_app = input_collector_app.InputCollectorApp()

        # Extract key components
        return {
            "app": input_app,
            "collector_manager": input_app.collector_manager,
            "logging_manager": input_app.logging_manager,
            "ui_manager": input_app.ui_manager,
            "app_coordinator": input_app.app_coordinator,
            "event_processor": input_app.event_processor,
        }

    def _initialize_eeg_processor(self):
        """
        Initialize EEG processor components.

        Returns:
            dict: Dictionary containing EEG processor components
        """
        # Create EEG processor app without showing the window
        eeg_app = eeg_processor_app.EEGProcessorApp()

        # Extract key components
        return {
            "app": eeg_app,
            "collector_service": eeg_app.collector_service,
            "processor_service": eeg_app.processor_service,
            "visualization_service": eeg_app.visualization_service,
            "recording_service": eeg_app.recording_service,
        }

    def run(self):
        """
        Run the unified application.

        Returns:
            int: Application exit code
        """
        # Show the main window
        self.main_window.show()

        # Run the application
        return self.app.exec_()
