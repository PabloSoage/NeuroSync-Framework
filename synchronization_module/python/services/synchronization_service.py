"""
Core synchronization service for coordinating EEG and input data streams.
"""
import logging
import threading
import time
import multiprocessing as mp
from queue import Queue, Empty
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
        
        # Callback IDs for cleanup
        self.eeg_callback_id = None
        self.input_callback_id = None
        
        # Threading
        self._lock = threading.RLock()
        
        # EEG metadata for LSL stream creation
        self.eeg_metadata = {}
        
        # Background processing for performance
        self._processing_queue = Queue(maxsize=1000)
        self._processing_thread = None
        self._stop_processing = threading.Event()
        
        # Setup timing callbacks
        self.timing_manager.register_sync_callback(
            "sync_data", self._synchronize_data_callback
        )
        
        logging.info("Synchronization service initialized")
    
    def set_eeg_service(self, eeg_service: Any) -> None:
        """Set EEG processor service."""
        self.eeg_service = eeg_service
        
        # Get EEG metadata for LSL stream creation
        try:
            if hasattr(eeg_service, 'get_metadata'):
                self.eeg_metadata = eeg_service.get_metadata()
            elif hasattr(eeg_service, 'metadata'):
                self.eeg_metadata = eeg_service.metadata
            
            logging.info(f"EEG service connected: {self.eeg_metadata.get('num_channels', 'unknown')} channels")
        except Exception as e:
            logging.warning(f"Could not get EEG metadata: {e}")
        
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
            
            # Use more conservative timing for UI responsiveness
            actual_precision = max(precision_ms, 10.0)  # Minimum 10ms for UI
            self.timing_manager.set_precision(actual_precision)
            
            # Get actual EEG metadata
            channel_count = 8  # Default
            sampling_rate = 250.0  # Default
            
            if self.eeg_metadata:
                channel_count = self.eeg_metadata.get('num_channels', 8)
                sampling_rate = float(self.eeg_metadata.get('sampling_rate', 250))
                
                # Fallback: try to get from channel names
                if channel_count == 0:
                    channel_names = self.eeg_metadata.get('channel_names', [])
                    if channel_names:
                        channel_count = len(channel_names)
                
                logging.info(f"Using EEG metadata: {channel_count} channels, {sampling_rate} Hz")
            
            # Create LSL streams with correct parameters
            eeg_stream = self.lsl_manager.create_eeg_stream(
                name="EEG_Sync",
                channel_count=channel_count,
                sampling_rate=sampling_rate
            )
            input_stream = self.lsl_manager.create_input_stream()
            
            if not eeg_stream or not input_stream:
                logging.error("Failed to create LSL streams")
                return False
            
            # Start background processing thread
            self._start_background_processing()
            
            # Setup data collection from services
            self._setup_data_collection()
            
            # Start timing manager
            if not self.timing_manager.start_synchronization():
                logging.error("Failed to start timing manager")
                return False
            
            self.is_active = True
            logging.info(f"Synchronization started with {precision_ms}ms precision ({actual_precision}ms actual)")
            
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
            
            # Stop background processing
            self._stop_background_processing()
            
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
    
    def _start_background_processing(self) -> None:
        """Start background processing thread."""
        if self._processing_thread is not None:
            return
            
        self._stop_processing.clear()
        self._processing_thread = threading.Thread(
            target=self._background_processor,
            daemon=True
        )
        self._processing_thread.start()
        logging.info("Background processing started")
    
    def _stop_background_processing(self) -> None:
        """Stop background processing thread."""
        if self._processing_thread is None:
            return
            
        self._stop_processing.set()
        
        # Signal the processing thread to wake up
        try:
            self._processing_queue.put(None, timeout=1.0)
        except:
            pass
            
        if self._processing_thread.is_alive():
            self._processing_thread.join(timeout=2.0)
        
        self._processing_thread = None
        logging.info("Background processing stopped")
    
    def _background_processor(self) -> None:
        """Background processing thread for handling data without blocking UI."""
        while not self._stop_processing.is_set():
            try:
                # Wait for data with timeout
                item = self._processing_queue.get(timeout=1.0)
                
                if item is None:  # Shutdown signal
                    break
                
                # Process the item
                if item['type'] == 'eeg_data':
                    self._process_eeg_data_background(item)
                elif item['type'] == 'input_event':
                    self._process_input_event_background(item)
                
            except Empty:
                continue
            except Exception as e:
                logging.error(f"Error in background processor: {e}")
    
    def _process_eeg_data_background(self, item: Dict[str, Any]) -> None:
        """Process EEG data in background thread."""
        try:
            data = item['data']
            timestamp = item['timestamp']
            
            # Add to buffer
            with self._lock:
                sample = {
                    'timestamp': timestamp,
                    'data': data,
                    'timestamps': item.get('timestamps', []),
                    'type': 'eeg'
                }
                self.eeg_buffer.append(sample)
                
                # Keep buffer size manageable (last 60 seconds)
                cutoff_time = timestamp - 60.0
                self.eeg_buffer = [
                    s for s in self.eeg_buffer 
                    if s['timestamp'] >= cutoff_time
                ]
            
            # Push to LSL only if data is correct shape
            if data.size > 0 and len(data.shape) == 2:
                # Get the correct number of channels for LSL
                expected_channels = self.eeg_metadata.get('num_channels', 8)
                
                if data.shape[0] == expected_channels and data.shape[1] > 0:
                    # Push latest sample
                    latest_sample = data[:, -1]
                    self.lsl_manager.push_eeg_sample("EEG_Sync", latest_sample)
                elif data.shape[1] > 0:
                    # Adjust channel count if mismatch
                    if data.shape[0] > expected_channels:
                        # Take first N channels
                        adjusted_data = data[:expected_channels, -1]
                    else:
                        # Pad with zeros
                        adjusted_data = np.zeros(expected_channels)
                        adjusted_data[:data.shape[0]] = data[:, -1]
                    
                    self.lsl_manager.push_eeg_sample("EEG_Sync", adjusted_data)
                    
        except Exception as e:
            logging.error(f"Error processing EEG data in background: {e}")
    
    def _process_input_event_background(self, item: Dict[str, Any]) -> None:
        """Process input event in background thread."""
        try:
            event_data = item['data']
            timestamp = item['timestamp']
            event_str = item['event_str']
            
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
            logging.error(f"Error processing input event in background: {e}")
    
    def is_synchronizing(self) -> bool:
        """Check if synchronization is active."""
        return self.is_active
    
    def get_synchronized_data(self, duration_seconds: float) -> Dict[str, Any]:
        """Get synchronized data for specified duration."""
        with self._lock:
            current_time = time.time()
            start_time = current_time - duration_seconds
            
            # Filter data by time window
            synchronized = [
                sample for sample in self.synchronized_data
                if sample['timestamp'] >= start_time
            ]
            
            # Convert to proper format for dataset export
            if synchronized:
                # Create EEG data matrix from synchronized samples
                eeg_samples = []
                for s in synchronized:
                    if 'eeg_data' in s and s['eeg_data'].size > 0:
                        eeg_samples.append(s['eeg_data'])
                
                if eeg_samples:
                    # Concatenate all EEG samples
                    try:
                        eeg_matrix = np.concatenate(eeg_samples, axis=1)
                    except ValueError as e:
                        logging.warning(f"Error concatenating EEG data: {e}")
                        # Fallback: use the largest consistent shape
                        max_channels = max(data.shape[0] for data in eeg_samples)
                        consistent_samples = []
                        for data in eeg_samples:
                            if data.shape[0] == max_channels:
                                consistent_samples.append(data)
                        
                        if consistent_samples:
                            eeg_matrix = np.concatenate(consistent_samples, axis=1)
                        else:
                            eeg_matrix = np.array([])
                else:
                    eeg_matrix = np.array([])
                
                # Create input events list
                input_events = []
                for s in synchronized:
                    if 'input_events' in s:
                        for event in s['input_events']:
                            try:
                                event_type = 'input'
                                event_value = str(event.get('data', ''))
                                
                                # Try to extract event type from data
                                if hasattr(event.get('data'), 'event_type'):
                                    event_type = event.get('data').event_type
                                elif 'event_string' in event:
                                    event_str = event['event_string']
                                    if ':' in event_str:
                                        event_type = event_str.split(':', 1)[0]
                                        event_value = event_str.split(':', 1)[1] if len(event_str.split(':', 1)) > 1 else ''
                                
                                input_events.append({
                                    'timestamp': event['timestamp'],
                                    'type': event_type,
                                    'data': event_value
                                })
                            except Exception as e:
                                logging.warning(f"Error processing input event for export: {e}")
                
                # Add metadata from EEG service
                metadata = {
                    'duration': duration_seconds,
                    'start_time': start_time,
                    'end_time': current_time,
                    'sample_count': len(synchronized),
                    'precision_ms': self.precision_ms
                }
                
                # Add EEG metadata
                if self.eeg_metadata:
                    metadata.update({
                        'sampling_rate': self.eeg_metadata.get('sampling_rate', 250),
                        'channel_names': self.eeg_metadata.get('channel_names', []),
                        'num_channels': self.eeg_metadata.get('num_channels', 0),
                        'board_name': self.eeg_metadata.get('board_name', '')
                    })
                
                return {
                    'eeg_data': eeg_matrix,
                    'input_events': {'events': input_events},
                    'metadata': metadata,
                    'sync_info': {
                        'precision_ms': self.precision_ms,
                        'sync_quality': self._calculate_overall_sync_quality(synchronized),
                        'eeg_info': self.eeg_metadata,
                        'input_info': {}
                    }
                }
            else:
                return {
                    'eeg_data': np.array([]),
                    'input_events': {'events': []},
                    'metadata': {'duration': duration_seconds, 'sample_count': 0},
                    'sync_info': {'precision_ms': self.precision_ms, 'sync_quality': 0.0}
                }
    
    def _setup_data_collection(self) -> None:
        """Setup data collection from external services."""
        if self.eeg_service:
            try:
                from eeg_processor.python.services.data_access_service import DataAccessService
                data_service = DataAccessService.get_instance()
                
                if hasattr(data_service, 'register_local_callback'):
                    self.eeg_callback_id = data_service.register_local_callback(self._on_eeg_data)
                    logging.info("Registered EEG local callback")
                
            except Exception as e:
                logging.error(f"Failed to register EEG callback: {e}")
        
        if self.input_service:
            try:
                from input_collector.python.services.data_access_service import DataAccessService
                data_service = DataAccessService.get_instance()
                
                if hasattr(data_service, 'register_callback'):
                    self.input_callback_id = data_service.register_callback(self._on_input_event)
                    logging.info("Registered input callback")
                
            except Exception as e:
                logging.error(f"Failed to register input callback: {e}")
    
    def _cleanup_data_collection(self) -> None:
        """Cleanup data collection."""
        # Unregister callbacks
        if self.eeg_callback_id is not None:
            try:
                from eeg_processor.python.services.data_access_service import DataAccessService
                data_service = DataAccessService.get_instance()
                if hasattr(data_service, 'unregister_local_callback'):
                    data_service.unregister_local_callback(self.eeg_callback_id)
                    logging.info("Unregistered EEG callback")
            except Exception as e:
                logging.error(f"Error unregistering EEG callback: {e}")
        
        if self.input_callback_id is not None:
            try:
                from input_collector.python.services.data_access_service import DataAccessService
                data_service = DataAccessService.get_instance()
                if hasattr(data_service, 'unregister_callback'):
                    data_service.unregister_callback(self.input_callback_id)
                    logging.info("Unregistered input callback")
            except Exception as e:
                logging.error(f"Error unregistering input callback: {e}")
        
        # Clear buffers
        with self._lock:
            self.eeg_buffer.clear()
            self.input_buffer.clear()
            self.synchronized_data.clear()
    
    def _on_eeg_data(self, data: np.ndarray, timestamps: List[int]) -> None:
        """Handle EEG data from service - queue for background processing."""
        try:
            if not self.is_active:
                return
                
            # Queue for background processing instead of processing immediately
            item = {
                'type': 'eeg_data',
                'data': data.copy() if hasattr(data, 'copy') else data,
                'timestamps': timestamps.copy() if hasattr(timestamps, 'copy') else timestamps,
                'timestamp': time.time()
            }
            
            # Non-blocking queue put
            try:
                self._processing_queue.put_nowait(item)
            except:
                # Queue full, skip this sample to avoid blocking
                pass
                
        except Exception as e:
            logging.error(f"Error handling EEG data: {e}")
    
    def _on_input_event(self, event_data: Any) -> None:
        """Handle input event from service - queue for background processing."""
        try:
            if not self.is_active:
                return
                
            # Convert event to string for LSL
            if hasattr(event_data, 'to_dict'):
                event_str = str(event_data.to_dict())
            elif hasattr(event_data, 'event_type'):
                event_str = f"{event_data.event_type}:{getattr(event_data, 'data', '')}"
            else:
                event_str = str(event_data)
            
            # Queue for background processing
            item = {
                'type': 'input_event',
                'data': event_data,
                'event_str': event_str,
                'timestamp': time.time()
            }
            
            # Non-blocking queue put
            try:
                self._processing_queue.put_nowait(item)
            except:
                # Queue full, skip this event to avoid blocking
                pass
                
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
                
                # Check recent EEG samples
                recent_eeg = self.eeg_buffer[-5:] if len(self.eeg_buffer) > 0 else []
                
                for eeg_sample in recent_eeg:
                    eeg_time = eeg_sample['timestamp']
                    
                    # Find input events within tolerance
                    matching_events = [
                        event for event in self.input_buffer
                        if abs(event['timestamp'] - eeg_time) <= tolerance
                    ]
                    
                    # Only create synchronized sample if we have input events
                    # OR if we want to keep EEG-only samples (for continuous recording)
                    if matching_events or len(self.input_buffer) == 0:
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
            # If no input events, quality depends on whether we expect them
            # For continuous EEG recording without input, this might be normal
            return 0.5  # Neutral quality when no input events
            
        # Calculate average time difference
        time_diffs = [abs(event['timestamp'] - eeg_time) for event in input_events]
        avg_diff = sum(time_diffs) / len(time_diffs)
        
        # Convert to quality score (closer to 0 difference = higher quality)
        max_acceptable_diff = self.precision_ms / 1000.0
        quality = max(0.0, 1.0 - (avg_diff / max_acceptable_diff))
        
        return quality
    
    def _calculate_overall_sync_quality(self, synchronized_samples: List[Dict]) -> float:
        """Calculate overall synchronization quality."""
        if not synchronized_samples:
            return 0.0
        
        qualities = [s.get('sync_quality', 0.0) for s in synchronized_samples]
        return sum(qualities) / len(qualities)
    
    def get_status(self) -> Dict[str, Any]:
        """Get synchronization service status."""
        with self._lock:
            # Calculate actual sync quality from recent samples
            recent_samples = self.synchronized_data[-100:] if self.synchronized_data else []
            sync_quality = self._calculate_overall_sync_quality(recent_samples)
            
            return {
                'active': self.is_active,
                'precision_ms': self.precision_ms,
                'eeg_buffer_size': len(self.eeg_buffer),
                'input_buffer_size': len(self.input_buffer),
                'synchronized_samples': len(self.synchronized_data),
                'sync_quality': sync_quality,
                'timing_status': self.timing_manager.get_status(),
                'has_eeg_service': self.eeg_service is not None,
                'has_input_service': self.input_service is not None
            }
    
    def cleanup(self) -> None:
        """Clean up synchronization service resources."""
        try:
            # Stop synchronization if active
            if self.is_active:
                self.stop_synchronization()
            
            # Stop background processing
            self._stop_background_processing()
            
            # Cleanup timing manager
            if hasattr(self.timing_manager, 'cleanup'):
                self.timing_manager.cleanup()
            
            # Cleanup LSL manager
            if hasattr(self.lsl_manager, 'cleanup'):
                self.lsl_manager.cleanup()
            
            # Clear references
            self.eeg_service = None
            self.input_service = None
            
            logging.info("Synchronization service cleaned up")
            
        except Exception as e:
            logging.error(f"Error during synchronization service cleanup: {e}")