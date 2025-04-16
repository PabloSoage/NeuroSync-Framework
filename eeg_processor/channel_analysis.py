"""
Script to analyze and understand the CH_0 channel in synthetic board data.

This script connects to the synthetic board, collects data for a few seconds,
and analyzes the CH_0 channel to understand its pattern and purpose.
"""

import os
import time
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    # Initialize parameters for synthetic board
    params = BrainFlowInputParams()
    board_id = BoardIds.SYNTHETIC_BOARD
    
    # Connect to board
    logging.info("Connecting to synthetic board...")
    board = BoardShim(board_id, params)
    
    try:
        # Prepare and start session
        board.prepare_session()
        board.start_stream()
        
        # Collect data
        logging.info("Collecting data for 5 seconds...")
        time.sleep(5)
        
        # Get data
        data = board.get_board_data()
        
        # Get channel information
        logging.info(f"Data shape: {data.shape}")
        eeg_channels = BoardShim.get_eeg_channels(board_id)
        timestamp_channel = BoardShim.get_timestamp_channel(board_id)
        marker_channel = BoardShim.get_marker_channel(board_id)
        
        logging.info(f"EEG channels: {eeg_channels}")
        logging.info(f"Timestamp channel: {timestamp_channel}")
        logging.info(f"Marker channel: {marker_channel}")
        
        # Analyze CH_0 channel
        ch0_data = data[0]
        logging.info(f"CH_0 data shape: {ch0_data.shape}")
        logging.info(f"CH_0 min: {np.min(ch0_data)}, max: {np.max(ch0_data)}")
        logging.info(f"CH_0 first 10 values: {ch0_data[:10]}")
        
        # Calculate differences between consecutive values to understand pattern
        diff = np.diff(ch0_data)
        logging.info(f"CH_0 differences (first 10): {diff[:10]}")
        unique_diffs = np.unique(diff)
        logging.info(f"Unique differences in CH_0: {unique_diffs}")
        
        # Create plots for visualization
        plt.figure(figsize=(12, 8))
        
        # Plot CH_0 values
        plt.subplot(2, 1, 1)
        plt.plot(ch0_data[:250])
        plt.title('CH_0 Channel Values (First 250 samples)')
        plt.xlabel('Sample Index')
        plt.ylabel('Value')
        
        # Plot differences
        plt.subplot(2, 1, 2)
        plt.plot(diff[:250])
        plt.title('CH_0 Differences Between Consecutive Values')
        plt.xlabel('Sample Index')
        plt.ylabel('Difference')
        
        plt.tight_layout()
        plt.savefig('ch0_analysis.png')
        logging.info("Plot saved to ch0_analysis.png")
        
        # Also create a CSV with all data
        df = pd.DataFrame(data.T)
        df.columns = [f'Channel_{i}' for i in range(data.shape[0])]
        df.to_csv('channel_data.csv', index=False)
        logging.info("Data saved to channel_data.csv")
        
        # Print some statistics for other channels too
        for i, channel in enumerate(eeg_channels[:5]):  # First 5 EEG channels
            ch_data = data[channel]
            logging.info(f"Channel {channel} min: {np.min(ch_data)}, max: {np.max(ch_data)}")
            logging.info(f"Channel {channel} first 5 values: {ch_data[:5]}")
        
    finally:
        # Clean up
        logging.info("Stopping stream and releasing session...")
        board.stop_stream()
        board.release_session()
    
    logging.info("Analysis completed.")

if __name__ == "__main__":
    main()
