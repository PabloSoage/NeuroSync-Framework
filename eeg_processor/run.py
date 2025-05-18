#!/usr/bin/env python
"""
EEG Processor Application

This script runs the EEG Processor application for collecting, processing, and
visualizing EEG data from various devices including g.tec unicorn.
"""

import argparse
import logging
import os
import sys
import time

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

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--enable-web-api", action="store_true")
    p.add_argument("--api-host", default="127.0.0.1")
    p.add_argument("--api-port", type=int, default=8000)
    return p.parse_args()

def main():
    """Run the EEG Processor application."""
    args=parse_args()

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

    # Initialize API after the main application has started
    if args.enable_web_api:
        from eeg_processor.python.api_integration import initialize_api, get_api_integration
        if initialize_api(host=args.api_host, port=args.api_port):
            intg = get_api_integration()
            port = intg.explorer.server_port or args.api_port
            print(f"Web API EEG Processor en http://{args.api_host}:{port}")
        else:
            print("Fallo inicializando Web API EEG Processor")
    
    # Example: register a callback for new data
    callback_id = EEGDataAPI.register_data_callback(data_callback)
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
