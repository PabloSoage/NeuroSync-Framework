"""
LSL Manager for handling Lab Streaming Layer operations.

This module manages LSL streams for both EEG and input data,
ensuring proper synchronization between different data sources.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from enum import Enum
import numpy as np

try:
    from pylsl import StreamInfo, StreamOutlet, StreamInlet, resolve_stream, local_clock
    LSL_AVAILABLE = True
except ImportError:
    LSL_AVAILABLE = False
    logging.warning("pylsl not available. Install with: pip install pylsl")


class StreamType(Enum):
    """Types of data streams."""
    EEG = "EEG"
    INPUT = "Input"
    MARKER = "Markers"


@dataclass
class StreamConfig:
    """Configuration for an LSL stream."""
    name: str
    type: str
    channel_count: int
    sampling_rate: float
    channel_format: str = "float32"
    source_id: str = ""


class LSLManager:
    """
    Manages LSL streams for synchronized data collection.
    
    This class handles the creation and management of LSL outlets for
    broadcasting data and inlets for receiving data from different sources.
    """
    
    def __init__(self):
        """Initialize the LSL manager."""
        if not LSL_AVAILABLE:
            raise RuntimeError("LSL is not available. Please install pylsl.")
        
        self.outlets: Dict[str, StreamOutlet] = {}
        self.inlets: Dict[str, StreamInlet] = {}
        self.stream_infos: Dict[str, StreamInfo] = {}
        self.callbacks: Dict[str, List[Callable]] = {}
        
        # Synchronization settings
        self.time_correction = 0.0
        self.last_sync_time = 0.0
        self.sync_interval = 5.0  # Sync every 5 seconds
        
        logging.info("LSL Manager initialized")
    
    def create_outlet(self, stream_id: str, config: StreamConfig) -> bool:
        """
        Create an LSL outlet for broadcasting data.
        
        Args:
            stream_id: Unique identifier for the stream
            config: Stream configuration
            
        Returns:
            bool: True if outlet created successfully
        """
        try:
            # Create stream info
            info = StreamInfo(
                name=config.name,
                type=config.type,
                channel_count=config.channel_count,
                nominal_srate=config.sampling_rate,
                channel_format=config.channel_format,
                source_id=config.source_id or stream_id
            )
            
            # Add metadata
            channels = info.desc().append_child("channels")
            for i in range(config.channel_count):
                channels.append_child("channel") \
                    .append_child_value("label", f"Ch{i+1}") \
                    .append_child_value("unit", "unknown") \
                    .append_child_value("type", config.type)
            
            # Create outlet
            outlet = StreamOutlet(info)
            self.outlets[stream_id] = outlet
            self.stream_infos[stream_id] = info
            
            logging.info(f"Created LSL outlet: {stream_id} ({config.name})")
            return True
            
        except Exception as e:
            logging.error(f"Failed to create LSL outlet {stream_id}: {e}")
            return False
    
    def create_inlet(self, stream_name: str, stream_type: str = "") -> Optional[str]:
        """
        Create an LSL inlet for receiving data.
        
        Args:
            stream_name: Name of the stream to connect to
            stream_type: Type of the stream (optional filter)
            
        Returns:
            Optional[str]: Stream ID if inlet created successfully
        """
        try:
            # Resolve stream
            logging.info(f"Resolving stream: {stream_name} (type: {stream_type})")
            
            predicates = [f"name='{stream_name}'"]
            if stream_type:
                predicates.append(f"type='{stream_type}'")
            
            streams = resolve_stream(" and ".join(predicates), timeout=5.0)
            
            if not streams:
                logging.warning(f"No streams found matching: {stream_name}")
                return None
            
            # Create inlet from first matching stream
            stream_info = streams[0]
            inlet = StreamInlet(stream_info, max_buflen=360)
            
            # Generate stream ID
            stream_id = f"{stream_name}_{stream_type}_{time.time()}"
            self.inlets[stream_id] = inlet
            
            logging.info(f"Created LSL inlet: {stream_id}")
            return stream_id
            
        except Exception as e:
            logging.error(f"Failed to create LSL inlet for {stream_name}: {e}")
            return None
    
    def push_sample(self, stream_id: str, sample: List[float], 
                    timestamp: Optional[float] = None) -> bool:
        """
        Push a sample to an outlet stream.
        
        Args:
            stream_id: ID of the outlet stream
            sample: Data sample to push
            timestamp: Optional timestamp (uses LSL clock if None)
            
        Returns:
            bool: True if sample pushed successfully
        """
        if stream_id not in self.outlets:
            logging.error(f"Outlet {stream_id} not found")
            return False
        
        try:
            outlet = self.outlets[stream_id]
            if timestamp is None:
                timestamp = local_clock()
            
            outlet.push_sample(sample, timestamp)
            return True
            
        except Exception as e:
            logging.error(f"Failed to push sample to {stream_id}: {e}")
            return False
    
    def push_chunk(self, stream_id: str, chunk: np.ndarray, 
                   timestamps: Optional[List[float]] = None) -> bool:
        """
        Push a chunk of samples to an outlet stream.
        
        Args:
            stream_id: ID of the outlet stream
            chunk: Data chunk (samples x channels)
            timestamps: Optional timestamps for each sample
            
        Returns:
            bool: True if chunk pushed successfully
        """
        if stream_id not in self.outlets:
            logging.error(f"Outlet {stream_id} not found")
            return False
        
        try:
            outlet = self.outlets[stream_id]
            
            if timestamps is None:
                # Generate timestamps based on sampling rate
                info = self.stream_infos[stream_id]
                sample_rate = info.nominal_srate()
                if sample_rate > 0:
                    now = local_clock()
                    timestamps = [now - (len(chunk) - i - 1) / sample_rate 
                                for i in range(len(chunk))]
            
            outlet.push_chunk(chunk.tolist(), timestamps)
            return True
            
        except Exception as e:
            logging.error(f"Failed to push chunk to {stream_id}: {e}")
            return False
    
    def pull_sample(self, stream_id: str, timeout: float = 0.0) -> Optional[Tuple[List[float], float]]:
        """
        Pull a sample from an inlet stream.
        
        Args:
            stream_id: ID of the inlet stream
            timeout: Timeout in seconds (0 = non-blocking)
            
        Returns:
            Optional[Tuple[List[float], float]]: Sample and timestamp if available
        """
        if stream_id not in self.inlets:
            logging.error(f"Inlet {stream_id} not found")
            return None
        
        try:
            inlet = self.inlets[stream_id]
            sample, timestamp = inlet.pull_sample(timeout)
            
            if timestamp:
                return sample, timestamp
            return None
            
        except Exception as e:
            logging.error(f"Failed to pull sample from {stream_id}: {e}")
            return None
    
    def pull_chunk(self, stream_id: str, max_samples: int = 1024) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Pull a chunk of samples from an inlet stream.
        
        Args:
            stream_id: ID of the inlet stream
            max_samples: Maximum number of samples to pull
            
        Returns:
            Optional[Tuple[np.ndarray, np.ndarray]]: Samples and timestamps if available
        """
        if stream_id not in self.inlets:
            logging.error(f"Inlet {stream_id} not found")
            return None
        
        try:
            inlet = self.inlets[stream_id]
            samples, timestamps = inlet.pull_chunk(max_samples=max_samples)
            
            if samples:
                return np.array(samples), np.array(timestamps)
            return None
            
        except Exception as e:
            logging.error(f"Failed to pull chunk from {stream_id}: {e}")
            return None
    
    def register_callback(self, stream_id: str, callback: Callable) -> bool:
        """
        Register a callback for when data is received on a stream.
        
        Args:
            stream_id: ID of the inlet stream
            callback: Function to call with (samples, timestamps)
            
        Returns:
            bool: True if callback registered successfully
        """
        if stream_id not in self.inlets:
            logging.error(f"Inlet {stream_id} not found")
            return False
        
        if stream_id not in self.callbacks:
            self.callbacks[stream_id] = []
        
        self.callbacks[stream_id].append(callback)
        return True
    
    def get_stream_info(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a stream.
        
        Args:
            stream_id: ID of the stream
            
        Returns:
            Optional[Dict[str, Any]]: Stream information if available
        """
        if stream_id in self.stream_infos:
            info = self.stream_infos[stream_id]
            return {
                'name': info.name(),
                'type': info.type(),
                'channel_count': info.channel_count(),
                'sampling_rate': info.nominal_srate(),
                'channel_format': info.channel_format(),
                'source_id': info.source_id()
            }
        
        if stream_id in self.inlets:
            inlet = self.inlets[stream_id]
            info = inlet.info()
            return {
                'name': info.name(),
                'type': info.type(),
                'channel_count': info.channel_count(),
                'sampling_rate': info.nominal_srate(),
                'channel_format': info.channel_format_string(),
                'source_id': info.source_id()
            }
        
        return None
    
    def synchronize_clocks(self) -> float:
        """
        Synchronize LSL clock with system clock.
        
        Returns:
            float: Time correction offset
        """
        lsl_time = local_clock()
        system_time = time.time()
        
        # Calculate correction (this is simplified, real implementation might need more sophisticated sync)
        self.time_correction = system_time - lsl_time
        self.last_sync_time = system_time
        
        logging.debug(f"Clock synchronization: correction = {self.time_correction:.6f}s")
        return self.time_correction
    
    def get_synchronized_timestamp(self) -> float:
        """
        Get a synchronized timestamp.
        
        Returns:
            float: Synchronized timestamp
        """
        # Re-sync if needed
        current_time = time.time()
        if current_time - self.last_sync_time > self.sync_interval:
            self.synchronize_clocks()
        
        return local_clock() + self.time_correction
    
    def cleanup(self):
        """Clean up all streams."""
        # Close outlets
        for stream_id in list(self.outlets.keys()):
            try:
                del self.outlets[stream_id]
                logging.info(f"Closed outlet: {stream_id}")
            except Exception as e:
                logging.error(f"Error closing outlet {stream_id}: {e}")
        
        # Close inlets
        for stream_id in list(self.inlets.keys()):
            try:
                del self.inlets[stream_id]
                logging.info(f"Closed inlet: {stream_id}")
            except Exception as e:
                logging.error(f"Error closing inlet {stream_id}: {e}")
        
        self.stream_infos.clear()
        self.callbacks.clear()
        
        logging.info("LSL Manager cleaned up")
