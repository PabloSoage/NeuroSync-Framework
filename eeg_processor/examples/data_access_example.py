"""
Example demonstrating how to access real-time EEG data.

This script shows how to use the EEG Data API to access data streams
and metadata in real-time.
"""

import os
import sys
import time

import numpy as np

# Add module to path for imports
current_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_path)

from python.data_access_api import EEGDataAPI

def print_metadata():
    """Print current metadata about the EEG stream."""
    metadata = EEGDataAPI.get_metadata()
    print("\nEEG Stream Metadata:")
    print("-" * 30)
    print(f"Board: {metadata.get('board_name', 'Unknown')}")
    print(f"Board ID: {metadata.get('board_id', 'Unknown')}")
    print(f"Sampling Rate: {metadata.get('sampling_rate', 0)} Hz")
    print(f"Number of EEG Channels: {len(metadata.get('eeg_channels', []))}")
    print(f"Channel Names: {', '.join(metadata.get('channel_names', []))}")
    print(f"Streaming: {'Yes' if metadata.get('streaming', False) else 'No'}")
    print(f"Last Update: {metadata.get('last_update', 0)}")
    print("-" * 30)

def print_channel_data(channel_name=None, num_samples=5):
    """Print the latest data for a specific channel."""
    if channel_name is None:
        # If no channel specified, use the first available
        channel_names = EEGDataAPI.get_channel_names()
        if not channel_names:
            print("No channels available")
            return
        channel_name = channel_names[0]
    
    # Get data for the channel
    channel_data, timestamps = EEGDataAPI.get_channel_by_name(channel_name)
    
    if channel_data.size == 0:
        print(f"No data available for channel {channel_name}")
        return
    
    # Print the latest samples
    print(f"\nLatest {min(num_samples, len(channel_data))} samples for {channel_name}:")
    print("-" * 30)
    
    for i, (value, ts) in enumerate(zip(channel_data[-num_samples:], timestamps[-num_samples:])):
        print(f"Sample {i+1}: {value:.4f} (timestamp: {ts})")
    
    print("-" * 30)

def data_callback(data, timestamps):
    """Callback that gets called when new data arrives."""
    print(f"\nNew data received: {data.shape[1]} samples across {data.shape[0]} channels")
    
    # Calculate some simple statistics
    if data.size > 0:
        mean_values = np.mean(data, axis=1)
        min_values = np.min(data, axis=1)
        max_values = np.max(data, axis=1)
        
        print("Channel statistics (mean, min, max):")
        for i in range(min(3, data.shape[0])):  # Show only first 3 channels
            print(f"Channel {i}: {mean_values[i]:.4f}, {min_values[i]:.4f}, {max_values[i]:.4f}")

def main():
    """Main example function."""
    print("EEG Data Access Example")
    print("======================")
    print("This example shows how to access real-time EEG data.")
    
    # Wait for streaming to start
    while not EEGDataAPI.is_streaming():
        print("Waiting for EEG stream to start...")
        time.sleep(1)
    
    print("\nEEG stream detected!")
    
    # Print metadata
    print_metadata()
    
    # Register callback for new data
    callback_id = EEGDataAPI.register_data_callback(data_callback)
    
    try:
        # Main loop - continuously show data
        for _ in range(10):  # Run for 10 iterations
            # Print data for a random channel
            channel_names = EEGDataAPI.get_channel_names()
            if channel_names:
                import random
                channel_name = random.choice(channel_names)
                print_channel_data(channel_name, 3)
            
            # Wait a bit
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nExample stopped by user")
    finally:
        # Unregister callback
        EEGDataAPI.unregister_data_callback(callback_id)
        print("\nExample finished")

if __name__ == "__main__":
    main()
