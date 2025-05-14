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
from eeg_processor.python.data_access_api import EEGDataAPI


def run_example_data_access():
    """Example of accessing data through the API."""
    
    # Get current data
    data, timestamps = EEGDataAPI.get_current_data()
    if data.size > 0:
        print(f"Got data with shape: {data.shape}")
        
    # Get metadata
    metadata = EEGDataAPI.get_metadata()
    print(f"Sampling rate: {metadata.get('sampling_rate')} Hz")
    print(f"Channel names: {metadata.get('channel_names')}")
    
    # Get a specific channel by name
    channel_names = EEGDataAPI.get_channel_names()
    if channel_names:
        first_channel = channel_names[0]
        channel_data, ts = EEGDataAPI.get_channel_by_name(first_channel)
        if channel_data.size > 0:
            print(f"Channel {first_channel} latest value: {channel_data[-1]}")

def data_callback(data, timestamps):
    """Callback that gets called when new data arrives."""
    print(f"New data received: {data.shape[1]} samples")

def main():
    """Run the EEG Processor application."""
    # Configure logging - only to console by default, file logging controlled by UI
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Only console logging by default
    )

    # Create and start the application
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ex = EEGProcessorApp()
    ex.show()
    
    # Example: register a callback for new data
    callback_id = EEGDataAPI.register_data_callback(data_callback)
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
