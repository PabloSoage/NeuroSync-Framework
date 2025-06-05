"""
Run script for the Integrated BCI System application.

This script launches the complete BCI system with integrated
EEG processing and input collection functionality.
"""

import logging
import os
import sys

from PyQt5.QtWidgets import QApplication

# Add parent directory to path to make the imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
