"""
Run the integrated BCI system.

This script launches the integrated application that combines 
EEG processing and input collection.
"""

import os
import sys
from pathlib import Path

# Add the current directory to the path so we can import our modules
current_dir = str(Path(__file__).parent)
sys.path.append(current_dir)

from python.integrated_app import IntegratedBCIApp
from PyQt5.QtWidgets import QApplication

def main():
    """Run the integrated BCI system application."""
    app = QApplication(sys.argv)
    window = IntegratedBCIApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
