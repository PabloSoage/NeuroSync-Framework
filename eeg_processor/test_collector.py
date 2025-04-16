"""
Test script for EEG Collector.

This script demonstrates how to use the EEGCollector class directly.
It sets up a synthetic board, collects data, and saves it to a file.
"""

import os
import sys
import time

# Add the parent directory to the path so imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from eeg_processor.python.collectors.eeg_collector import EEGCollector
from brainflow.board_shim import BoardIds, BrainFlowPresets

def main():
    print("Starting EEG Collector test...")
    
    # Create collector with synthetic board
    collector = EEGCollector(board_id=BoardIds.SYNTHETIC_BOARD.value)
    
    try:
        # Prepare and start stream
        print("Preparing session...")
        collector.prepare_session()
        
        print("Starting data stream...")
        collector.start_stream()
        
        # Collect data for 5 seconds
        print("Collecting data for 5 seconds...")
        for i in range(5):
            time.sleep(1)
            print(f"  {i+1} seconds elapsed")
            
            # Get current data
            data, timestamps = collector.get_data(250)  # Get 1 second of data at 250Hz
            print(f"  Data shape: {data.shape}")
            
            # Add a marker
            if i == 2:
                collector.insert_marker(i+1)
                print("  Marker inserted")
        
        # Save data
        output_file = "eeg_test_data.csv"
        print(f"Saving data to {output_file}...")
        collector.save_data(output_file)
        
        # Stop and clean up
        print("Stopping stream...")
        collector.stop_stream()
        
        print("Releasing session...")
        collector.release_session()
        
        print("Test completed successfully!")
        print(f"Data saved to {os.path.abspath(output_file)}")
        
    except Exception as e:
        print(f"Error during test: {e}")
        # Clean up if error occurs
        if collector.is_streaming:
            collector.stop_stream()
        collector.release_session()

if __name__ == "__main__":
    main()
