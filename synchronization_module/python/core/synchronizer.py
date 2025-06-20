"""
Main synchronizer that coordinates EEG and input data streams.

This module is responsible for synchronizing data from multiple sources
and preparing it for storage in various formats.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from collections import deque

from .lsl_manager import LSLManager, StreamConfig, StreamType


@dataclass
class SyncConfig:
    """Configuration for synchronization."""
    sync_precision_ms: float = 1.0  # Synchronization precision in milliseconds
    buffer_duration_s: float = 30.0  # Buffer duration in seconds
    interpolation_method: str = "linear"  # Method for aligning timestamps
    max_latency_ms: float = 100.0  # Maximum acceptable latency
    
    
@dataclass 
class SynchronizedData:
    """Container for synchronized data from multiple streams."""
    timestamp: float
    eeg_data: Optional[np.ndarray] = None
    input_events: List[Dict[str, Any]] = field(default_factory=list)
    markers: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataSynchronizer:
    """
    Synchronizes data from EEG and input streams.
    
    This class manages the temporal alignment of data from different sources,
    ensuring that all data is properly synchronized before storage.
    """
    
    def __init__(self, config: SyncConfig):
        """Initialize the synchronizer."""
        self.config = config
        self.lsl_manager = LSLManager()
        
        # Data buffers for each stream type
        self.eeg_buffer = deque(maxlen=int(config.buffer_duration_s * 1000))  # Assuming ~1kHz max
        self.input_buffer = deque(maxlen=10000)  # Large buffer for input events
        self.marker_buffer = deque(maxlen=1000)
        
        # Stream metadata
        self.stream_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Synchronization state
        self.is_synchronizing = False
        self.sync_thread: Optional[threading.Thread] = None
        self.sync_lock = threading.Lock()
        
        # Callbacks for synchronized data
        self.sync_callbacks: List[Callable[[SynchronizedData], None]] = []
        
        # Statistics
        self.stats = {
            'eeg_samples_received': 0,
            'input_events_received': 0,
            'markers_received': 0,
            'sync_packages_created': 0,
            'sync_errors': 0
        }
        
        logging.info(f"Data Synchronizer initialized with precision: {config.sync_precision_ms}ms")
    
    def setup_eeg_stream(self, stream_name: str, channel_count: int, 
                        sampling_rate: float) -> bool:
        """
        Set up EEG data stream.
        
        Args:
            stream_name: Name of the EEG stream
            channel_count: Number of EEG channels
            sampling_rate: Sampling rate in Hz
            
        Returns:
            bool: True if stream set up successfully
        """
        config = StreamConfig(
            name=stream_name,
            type=StreamType.EEG.value,
            channel_count=channel_count,
            sampling_rate=sampling_rate,
            channel_format="float32"
        )
        
        success = self.lsl_manager.create_outlet("eeg_stream", config)
        
        if success:
            self.stream_metadata["eeg"] = {
                'channel_count': channel_count,
                'sampling_rate': sampling_rate,
                'stream_name': stream_name
            }
            logging.info(f"EEG stream setup: {channel_count} channels @ {sampling_rate}Hz")
        
        return success
    
    def setup_input_stream(self, stream_name: str) -> bool:
        """
        Set up input event stream.
        
        Args:
            stream_name: Name of the input stream
            
        Returns:
            bool: True if stream set up successfully
        """
        # Input events are sent as JSON strings with timestamp
        config = StreamConfig(
            name=stream_name,
            type=StreamType.INPUT.value,
            channel_count=1,  # Single channel for JSON event data
            sampling_rate=0.0,  # Irregular rate
            channel_format="string"
        )
        
        success = self.lsl_manager.create_outlet("input_stream", config)
        
        if success:
            self.stream_metadata["input"] = {
                'stream_name': stream_name
            }
            logging.info(f"Input stream setup: {stream_name}")
        
        return success
    
    def start_synchronization(self) -> bool:
        """
        Start the synchronization process.
        
        Returns:
            bool: True if synchronization started successfully
        """
        if self.is_synchronizing:
            logging.warning("Synchronization already running")
            return False
        
        try:
            self.is_synchronizing = True
            self.sync_thread = threading.Thread(target=self._synchronization_loop)
            self.sync_thread.daemon = True
            self.sync_thread.start()
            
            logging.info("Synchronization started")
            return True
            
        except Exception as e:
            logging.error(f"Failed to start synchronization: {e}")
            self.is_synchronizing = False
            return False
    
    def stop_synchronization(self):
        """Stop the synchronization process."""
        self.is_synchronizing = False
        
        if self.sync_thread:
            self.sync_thread.join(timeout=5.0)
            self.sync_thread = None
        
        logging.info("Synchronization stopped")
    
    def _synchronization_loop(self):
        """Main synchronization loop running in separate thread."""
        sync_interval = self.config.sync_precision_ms / 1000.0  # Convert to seconds
        next_sync_time = time.time()
        
        while self.is_synchronizing:
            try:
                current_time = time.time()
                
                # Wait for next sync interval
                sleep_time = next_sync_time - current_time
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                # Perform synchronization
                self._perform_synchronization(current_time)
                
                # Schedule next sync
                next_sync_time += sync_interval
                
                # Handle drift
                if next_sync_time < current_time:
                    next_sync_time = current_time + sync_interval
                    
            except Exception as e:
                logging.error(f"Error in synchronization loop: {e}")
                self.stats['sync_errors'] += 1
                time.sleep(sync_interval)
    
    def _perform_synchronization(self, sync_time: float):
        """
        Perform synchronization of all data streams.
        
        Args:
            sync_time: Current synchronization timestamp
        """
        with self.sync_lock:
            # Create synchronized data package
            sync_data = SynchronizedData(timestamp=sync_time)
            
            # Get EEG data for this time window
            sync_data.eeg_data = self._get_synchronized_eeg_data(sync_time)
            
            # Get input events for this time window
            sync_data.input_events = self._get_synchronized_input_events(sync_time)
            
            # Get markers for this time window
            sync_data.markers = self._get_synchronized_markers(sync_time)
            
            # Add metadata
            sync_data.metadata = {
                'sync_precision_ms': self.config.sync_precision_ms,
                'stream_metadata': self.stream_metadata,
                'timestamp_iso': datetime.fromtimestamp(sync_time).isoformat()
            }
            
            # Notify callbacks
            for callback in self.sync_callbacks:
                try:
                    callback(sync_data)
                except Exception as e:
                    logging.error(f"Error in sync callback: {e}")
            
            self.stats['sync_packages_created'] += 1
    
    def _get_synchronized_eeg_data(self, target_time: float) -> Optional[np.ndarray]:
        """
        Get EEG data synchronized to target timestamp.
        
        Args:
            target_time: Target timestamp
            
        Returns:
            Optional[np.ndarray]: Synchronized EEG data
        """
        if not self.eeg_buffer:
            return None
        
        # Find samples within sync window
        window_start = target_time - (self.config.sync_precision_ms / 2000.0)
        window_end = target_time + (self.config.sync_precision_ms / 2000.0)
        
        synchronized_samples = []
        
        for sample, timestamp in self.eeg_buffer:
            if window_start <= timestamp <= window_end:
                synchronized_samples.append(sample)
        
        if synchronized_samples:
            return np.array(synchronized_samples)
        
        # If no exact match, interpolate
        return self._interpolate_eeg_data(target_time)
    
    def _interpolate_eeg_data(self, target_time: float) -> Optional[np.ndarray]:
        """
        Interpolate EEG data for target timestamp.
        
        Args:
            target_time: Target timestamp
            
        Returns:
            Optional[np.ndarray]: Interpolated EEG data
        """
        if len(self.eeg_buffer) < 2:
            return None
        
        # Find surrounding samples
        before_sample = None
        after_sample = None
        
        for i, (sample, timestamp) in enumerate(self.eeg_buffer):
            if timestamp <= target_time:
                before_sample = (sample, timestamp)
            elif timestamp > target_time and after_sample is None:
                after_sample = (sample, timestamp)
                break
        
        if before_sample and after_sample:
            # Linear interpolation
            t1, t2 = before_sample[1], after_sample[1]
            alpha = (target_time - t1) / (t2 - t1)
            
            interpolated = (1 - alpha) * before_sample[0] + alpha * after_sample[0]
            return np.array([interpolated])
        
        return None
    
    def _get_synchronized_input_events(self, target_time: float) -> List[Dict[str, Any]]:
        """
        Get input events within sync window.
        
        Args:
            target_time: Target timestamp
            
        Returns:
            List[Dict[str, Any]]: Input events within window
        """
        window_start = target_time - (self.config.sync_precision_ms / 2000.0)
        window_end = target_time + (self.config.sync_precision_ms / 2000.0)
        
        events = []
        for event, timestamp in self.input_buffer:
            if window_start <= timestamp <= window_end:
                events.append({
                    'event': event,
                    'timestamp': timestamp,
                    'latency_ms': (timestamp - target_time) * 1000
                })
        
        return events
    
    def _get_synchronized_markers(self, target_time: float) -> List[Dict[str, Any]]:
        """
        Get markers within sync window.
        
        Args:
            target_time: Target timestamp
            
        Returns:
            List[Dict[str, Any]]: Markers within window
        """
        window_start = target_time - (self.config.sync_precision_ms / 2000.0)
        window_end = target_time + (self.config.sync_precision_ms / 2000.0)
        
        markers = []
        for marker, timestamp in self.marker_buffer:
            if window_start <= timestamp <= window_end:
                markers.append({
                    'marker': marker,
                    'timestamp': timestamp,
                    'latency_ms': (timestamp - target_time) * 1000
                })
        
        return markers
    
    def add_eeg_data(self, data: np.ndarray, timestamp: float):
        """
        Add EEG data to buffer.
        
        Args:
            data: EEG data array
            timestamp: Data timestamp
        """
        with self.sync_lock:
            self.eeg_buffer.append((data, timestamp))
            self.stats['eeg_samples_received'] += 1
            
            # Push to LSL if outlet exists
            if "eeg_stream" in self.lsl_manager.outlets:
                self.lsl_manager.push_sample("eeg_stream", data.tolist(), timestamp)
    
    def add_input_event(self, event: Dict[str, Any], timestamp: float):
        """
        Add input event to buffer.
        
        Args:
            event: Input event data
            timestamp: Event timestamp
        """
        with self.sync_lock:
            self.input_buffer.append((event, timestamp))
            self.stats['input_events_received'] += 1
            
            # Push to LSL if outlet exists
            if "input_stream" in self.lsl_manager.outlets:
                import json
                event_json = json.dumps(event)
                self.lsl_manager.push_sample("input_stream", [event_json], timestamp)
    
    def add_marker(self, marker: Any, timestamp: float):
        """
        Add marker to buffer.
        
        Args:
            marker: Marker data
            timestamp: Marker timestamp
        """
        with self.sync_lock:
            self.marker_buffer.append((marker, timestamp))
            self.stats['markers_received'] += 1
    
    def register_sync_callback(self, callback: Callable[[SynchronizedData], None]):
        """
        Register callback for synchronized data.
        
        Args:
            callback: Function to call with synchronized data
        """
        self.sync_callbacks.append(callback)
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get synchronization statistics.
        
        Returns:
            Dict[str, int]: Statistics dictionary
        """
        return self.stats.copy()
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_synchronization()
        self.lsl_manager.cleanup()
        
        # Clear buffers
        self.eeg_buffer.clear()
        self.input_buffer.clear()
        self.marker_buffer.clear()
        
        logging.info("Data Synchronizer cleaned up")
