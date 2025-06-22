"""
Main synchronization application module.

This module provides the entry point for the synchronization application,
coordinating EEG and input data synchronization with dataset creation.
"""
import sys
import logging
from typing import Optional

from PyQt5.QtWidgets import QApplication

from .ui.unified_app import UnifiedApp


class SynchronizationApp:
    """
    Main application class for the synchronization system.
    
    This class coordinates the unified interface and manages the
    application lifecycle.
    """
    
    def __init__(self):
        """Initialize the synchronization application."""
        self.app: Optional[QApplication] = None
        self.main_window: Optional[UnifiedApp] = None
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def initialize(self) -> bool:
        """
        Initialize the application.
        
        Returns:
            True if initialization successful
        """
        try:
            # Create QApplication if it doesn't exist
            if QApplication.instance() is None:
                self.app = QApplication(sys.argv)
                self.app.setStyle("Fusion")
            else:
                self.app = QApplication.instance()
            
            # Create main window
            self.main_window = UnifiedApp()
            
            self.logger.info("Synchronization application initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}")
            return False
    
    def run(self) -> int:
        """
        Run the application.
        
        Returns:
            Application exit code
        """
        try:
            if not self.main_window:
                if not self.initialize():
                    return 1
            
            # Show main window
            self.main_window.show()
            
            # Run application event loop
            if self.app:
                return self.app.exec_()
            else:
                self.logger.error("No QApplication instance available")
                return 1
                
        except Exception as e:
            self.logger.error(f"Error running application: {e}")
            return 1
    
    def shutdown(self) -> None:
        """Shutdown the application."""
        try:
            if self.main_window:
                self.main_window.close()
                self.main_window = None
            
            if self.app:
                self.app.quit()
            
            self.logger.info("Synchronization application shutdown")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


def run_synchronization_app() -> int:
    """
    Run the synchronization application.
    
    Returns:
        Application exit code
    """
    app = SynchronizationApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(run_synchronization_app())