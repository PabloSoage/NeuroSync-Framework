#!/usr/bin/env python
"""
EEG Processor Application

This script runs the EEG Processor application for collecting, processing, and
visualizing EEG data from various devices including g.tec unicorn.
"""

import logging
import os
import sys

from PyQt5.QtWidgets import QApplication

# Add the parent directory to the path to allow importing the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eeg_processor.python.eeg_processor_app import EEGProcessorApp


def main():
    """Run the EEG Processor application."""
    # Configure logging - only to console by default, file logging controlled by UI
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()  # Only console logging by default
        ]
    )
    
    # Create and start the application
    app = QApplication(sys.argv)
    ex = EEGProcessorApp()
    ex.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
