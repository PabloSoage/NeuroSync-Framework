"""
Core synchronization service for coordinating EEG and input data streams.
"""
import logging
import threading
import time
from typing import Dict, Any, List, Optional, Callable

import numpy as np

from ..core.lsl_manager import LSLManager
from ..core.timing_manager import TimingManager
from ..interfaces.synchronization_interface import SynchronizationInterface


class SynchronizationService(SynchronizationInterface):
    """Main service for synchronizing EEG and input data streams."""
    
    def __init__(self):
        """Initialize synchronization service."""
        self.lsl_manager = LSLManager()
        self.timing_manager = TimingManager()
        
        # Data buffers
        self.eeg_buffer: List[Dict[str, Any]] = []
        self.input_buffer: List[Dict[str, Any]] = []
        self.synchronized_data: List[Dict[str, Any]] = []
        
        # Service state
        self.is_active = False
        self.precision_ms = 1.0
        
        # External services
        self.eeg_service = None
        self.input_service = None
        
        # Threading
        self._lock = threading.RLock()
        
        # Setup timing callbacks
        self.timing_manager.register_sync_callback(
            "sync_data", self._synchronize_data_callback
        )
        
        logging.info("Synchronization service initialized")
    
    def set_eeg_service(self, eeg_service: Any) -> None:
        """Set EEG processor service."""
        self.eeg_service = eeg_service
        logging.info("EEG service connected to synchronization")
    
    def set_input_service(self, input_service: Any) -> None:
        """Set input collector service."""
        self.input_service = input_service
        logging.info("Input service connected to synchronization")
    
    def start_synchronization(
        self, 
        precision_ms: float = 1.0,
        callback: Optional[Callable] = None
    ) -> bool:
        """Start synchronization with specified precision."""
        if self.is_active:
            return True
            
        try:
            self.precision_ms = precision_ms
            self.timing_manager.set_precision(precision_ms)
            
            # Create LSL streams
            eeg_stream = self.lsl_manager.create_eeg_stream()
            input_stream = self.lsl_manager.create_input_stream()
            
            if not eeg_stream or not input_stream:
                logging.error("Failed to create LSL streams")
                return False
            
            # Setup data collection from services
            self._setup_data_collection()
            
            # Start timing manager
            if not self.timing_manager.start_synchronization():
                logging.error("Failed to start timing manager")
                return False
            
            self.is_active = True
            logging.info(f"Synchronization started with {precision_ms}ms precision")
            
            if callback:
                callback(True, "Synchronization started successfully")
                
            return True
            
        except Exception as e:
            logging.error(f"Failed to start synchronization: {e}")
            if callback:
                callback(False, f"Failed to start: {e}")
            return False
    
    def stop_synchronization(self) -> bool:
        """Stop synchronization."""
        if not self.is_active:
            return True
            
        try:
            self.is_active = False
            
            # Stop timing manager
            self.timing_manager.stop_synchronization()
            
            # Stop LSL recording
            self.lsl_manager.stop_recording()
            
            # Cleanup data collection
            self._cleanup_data_collection()
            
            logging.info("Synchronization stopped")
            return True
            
        except Exception as e:
            logging.error(f"Failed to stop synchronization: {e}")
            return False
    
    def is_synchronizing(self) -> bool:
        """Check if synchronization is active."""
        return self.is_active
    
    def get_synchronized_data(self, duration_seconds: float) -> Dict[str, Any]:
        """Get synchronized data for specified duration."""
        with self._lock:
            current_time = time.time()
            start_time = current_time - duration_seconds
            
            # Filter data by time window
            eeg_data = [
                sample for sample in self.eeg_buffer
                if sample['timestamp'] >= start_time
            ]
            
            input_data = [
                event for event in self.input_buffer
                if event['timestamp'] >= start_time
            ]
            
            synchronized = [
                sample for sample in self.synchronized_data
                if sample['timestamp'] >= start_time
            ]
            
            return {
                'eeg_data': eeg_data,
                'input_data': input_data,
                'synchronized_data': synchronized,
                'duration': duration_seconds,
                'start_time': start_time,
                'end_time': current_time,
                'sample_count': len(synchronized)
            }
    
    def _setup_data_collection(self) -> None:
        """Setup data collection from external services."""
        if self.eeg_service:
            # Register callback with EEG service
            try:
                if hasattr(self.eeg_service, 'register_callback'):
                    self.eeg_service.register_callback(self._on_eeg_data)
                elif hasattr(self.eeg_service, 'register_local_callback'):
                    self.eeg_service.register_local_callback(self._on_eeg_data)
            except Exception as e:
                logging.error(f"Failed to register EEG callback: {e}")
        
        if self.input_service:
            # Register callback with input service
            try:
                if hasattr(self.input_service, 'register_callback'):
                    self.input_service.register_callback(self._on_input_event)
                elif hasattr(self.input_service, 'on_event'):
                    self.input_service.on_event(self._on_input_event)
            except Exception as e:
                logging.error(f"Failed to register input callback: {e}")
    
    def _cleanup_data_collection(self) -> None:
        """Cleanup data collection."""
        # Clear buffers
        with self._lock:
            self.eeg_buffer.clear()
            self.input_buffer.clear()
            self.synchronized_data.clear()
    
    def _on_eeg_data(self, data: np.ndarray, timestamps: List[int]) -> None:
        """Handle EEG data from service."""
        try:
            timestamp = time.time()
            
            # Add to buffer
            with self._lock:
                sample = {
                    'timestamp': timestamp,
                    'data': data.copy() if hasattr(data, 'copy') else data,
                    'timestamps': timestamps.copy() if hasattr(timestamps, 'copy') else timestamps,
                    'type': 'eeg'
                }
                self.eeg_buffer.append(sample)
                
                # Keep buffer size manageable (last 60 seconds)
                cutoff_time = timestamp - 60.0
                self.eeg_buffer = [
                    s for s in self.eeg_buffer 
                    if s['timestamp'] >= cutoff_time
                ]
            
            # Push to LSL
            if data.size > 0:
                # Push latest sample to LSL
                if len(data.shape) == 2 and data.shape[1] > 0:
                    latest_sample = data[:, -1]  # Get latest sample across all channels
                    self.lsl_manager.push_eeg_sample("EEG_Sync", latest_sample)
                    
        except Exception as e:
            logging.error(f"Error handling EEG data: {e}")
    
    def _on_input_event(self, event_data: Any) -> None:
        """Handle input event from service."""
        try:
            timestamp = time.time()
            
            # Convert event to string for LSL
            if hasattr(event_data, 'to_dict'):
                event_str = str(event_data.to_dict())
            else:
                event_str = str(event_data)
            
            # Add to buffer
            with self._lock:
                event = {
                    'timestamp': timestamp,
                    'data': event_data,
                    'event_string': event_str,
                    'type': 'input'
                }
                self.input_buffer.append(event)
                
                # Keep buffer size manageable
                cutoff_time = timestamp - 60.0
                self.input_buffer = [
                    e for e in self.input_buffer 
                    if e['timestamp'] >= cutoff_time
                ]
            
            # Push to LSL
            self.lsl_manager.push_input_event("Input_Events", event_str)
            
        except Exception as e:
            logging.error(f"Error handling input event: {e}")
    
    def _synchronize_data_callback(self, sync_timestamp: float) -> None:
        """Callback for data synchronization at regular intervals."""
        if not self.is_active:
            return
            
        try:
            with self._lock:
                # Find matching EEG and input data within precision window
                tolerance = self.precision_ms / 1000.0
                
                for eeg_sample in self.eeg_buffer[-10:]:  # Check last 10 EEG samples
                    eeg_time = eeg_sample['timestamp']
                    
                    # Find input events within tolerance
                    matching_events = [
                        event for event in self.input_buffer
                        if abs(event['timestamp'] - eeg_time) <= tolerance
                    ]
                    
                    if matching_events:
                        # Create synchronized sample
                        synchronized_sample = {
                            'timestamp': sync_timestamp,
                            'eeg_data': eeg_sample['data'],
                            'eeg_timestamps': eeg_sample['timestamps'],
                            'input_events': matching_events,
                            'precision_ms': self.precision_ms,
                            'sync_quality': self._calculate_sync_quality(eeg_time, matching_events)
                        }
                        
                        self.synchronized_data.append(synchronized_sample)
                        
                        # Keep synchronized data buffer manageable
                        cutoff_time = sync_timestamp - 300.0  # Keep 5 minutes
                        self.synchronized_data = [
                            s for s in self.synchronized_data
                            if s['timestamp'] >= cutoff_time
                        ]
                        
        except Exception as e:
            logging.error(f"Error in synchronization callback: {e}")
    
    def _calculate_sync_quality(self, eeg_time: float, input_events: List[Dict]) -> float:
        """Calculate synchronization quality score (0-1)."""
        if not input_events:
            return 0.0
            
        # Calculate average time difference
        time_diffs = [abs(event['timestamp'] - eeg_time) for event in input_events]
        avg_diff = sum(time_diffs) / len(time_diffs)
        
        # Convert to quality score (closer to 0 difference = higher quality)
        max_acceptable_diff = self.precision_ms / 1000.0
        quality = max(0.0, 1.0 - (avg_diff / max_acceptable_diff))
        
        return quality
    
    def get_status(self) -> Dict[str, Any]:
        """Get synchronization service status."""
        with self._lock:
            return {
                'active': self.is_active,
                'precision_ms': self.precision_ms,
                'eeg_buffer_size': len(self.eeg_buffer),
                'input_buffer_size': len(self.input_buffer),
                'synchronized_samples': len(self.synchronized_data),
                'timing_status': self.timing_manager.get_status(),
                'has_eeg_service': self.eeg_service is not None,
                'has_input_service': self.input_service is not None
            }