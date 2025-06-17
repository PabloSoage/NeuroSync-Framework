"""
Run script for the Integrated BCI System application.

This script launches the complete BCI system with integrated
EEG processing and input collection functionality.
"""

import logging
import sys

from PyQt5.QtWidgets import QApplication

# Import the integrated app
from integrated_app import IntegratedBCIApp

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and run the application
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle("Fusion")

    # Create the main window
    main_window = IntegratedBCIApp()
    main_window.show()

    # Start the application
    sys.exit(app.exec_())
