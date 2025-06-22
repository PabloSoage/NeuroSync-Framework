"""
Lab Streaming Layer (LSL) management for data synchronization.
"""
import logging
import threading
import time
from typing import Dict, Any, List, Optional, Callable

import numpy as np

try:
    import pylsl
    LSL_AVAILABLE = True
except ImportError:
    LSL_AVAILABLE = False
    logging.warning("pylsl not available. LSL functionality will be disabled.")

from ..interfaces.synchronization_interface import LSLStreamInterface


class LSLManager(LSLStreamInterface):
    """Manages LSL streams for synchronization."""
    
    def __init__(self):
        """Initialize LSL manager."""
        self.streams: Dict[str, Any] = {}
        self.outlets: Dict[str, Any] = {}
        self.inlets: Dict[str, Any] = {}
        self._running = False
        self._lock = threading.RLock()
        
        if not LSL_AVAILABLE:
            logging.error("LSL not available. Cannot initialize LSLManager.")
            
    def create_eeg_stream(
        self, 
        name: str = "EEG_Sync",
        channel_count: int = 8,
        sampling_rate: float = 250.0
    ) -> Optional[Any]:
        """Create EEG LSL stream."""
        if not LSL_AVAILABLE:
            return None
            
        try:
            info = pylsl.StreamInfo(
                name=name,
                type='EEG',
                channel_count=channel_count,
                nominal_srate=sampling_rate,
                channel_format=pylsl.cf_float32,
                source_id=f'{name}_source'
            )
            
            # Add metadata
            channels = info.desc().append_child('channels')
            for i in range(channel_count):
                ch = channels.append_child('channel')
                ch.append_child_value('label', f'Ch{i+1}')
                ch.append_child_value('unit', 'microvolts')
                ch.append_child_value('type', 'EEG')
            
            outlet = pylsl.StreamOutlet(info)
            self.outlets[name] = outlet
            
            logging.info(f"Created EEG LSL stream: {name}")
            return outlet
            
        except Exception as e:
            logging.error(f"Failed to create EEG stream: {e}")
            return None
    
    def create_input_stream(
        self, 
        name: str = "Input_Events",
        sampling_rate: float = 1000.0
    ) -> Optional[Any]:
        """Create input events LSL stream."""
        if not LSL_AVAILABLE:
            return None
            
        try:
            info = pylsl.StreamInfo(
                name=name,
                type='Markers',
                channel_count=1,
                nominal_srate=sampling_rate,
                channel_format=pylsl.cf_string,
                source_id=f'{name}_source'
            )
            
            outlet = pylsl.StreamOutlet(info)
            self.outlets[name] = outlet
            
            logging.info(f"Created input events LSL stream: {name}")
            return outlet
            
        except Exception as e:
            logging.error(f"Failed to create input stream: {e}")
            return None
    
    def push_eeg_sample(self, stream_name: str, sample: np.ndarray) -> None:
        """Push EEG sample to stream."""
        if not LSL_AVAILABLE or stream_name not in self.outlets:
            return
            
        try:
            outlet = self.outlets[stream_name]
            outlet.push_sample(sample.tolist())
        except Exception as e:
            logging.error(f"Failed to push EEG sample: {e}")
    
    def push_input_event(self, stream_name: str, event_data: str) -> None:
        """Push input event to stream."""
        if not LSL_AVAILABLE or stream_name not in self.outlets:
            return
            
        try:
            outlet = self.outlets[stream_name]
            outlet.push_sample([event_data])
        except Exception as e:
            logging.error(f"Failed to push input event: {e}")
    
    def create_stream(
        self, 
        name: str, 
        stream_type: str, 
        channel_count: int,
        nominal_srate: float
    ) -> Any:
        """Create generic LSL stream."""
        if not LSL_AVAILABLE:
            return None
            
        try:
            info = pylsl.StreamInfo(
                name=name,
                type=stream_type,
                channel_count=channel_count,
                nominal_srate=nominal_srate,
                channel_format=pylsl.cf_float32,
                source_id=f'{name}_source'
            )
            
            outlet = pylsl.StreamOutlet(info)
            self.outlets[name] = outlet
            return outlet
            
        except Exception as e:
            logging.error(f"Failed to create stream {name}: {e}")
            return None
    
    def push_sample(self, stream: Any, sample: np.ndarray) -> None:
        """Push sample to stream."""
        try:
            if isinstance(sample, np.ndarray):
                stream.push_sample(sample.tolist())
            else:
                stream.push_sample(sample)
        except Exception as e:
            logging.error(f"Failed to push sample: {e}")
    
    def resolve_streams(self, stream_type: str) -> List[Any]:
        """Resolve streams of specified type."""
        if not LSL_AVAILABLE:
            return []
            
        try:
            streams = pylsl.resolve_stream('type', stream_type)
            return streams
        except Exception as e:
            logging.error(f"Failed to resolve streams: {e}")
            return []
    
    def start_recording(self, stream_types: List[str]) -> bool:
        """Start recording from specified stream types."""
        if not LSL_AVAILABLE:
            return False
            
        try:
            self._running = True
            for stream_type in stream_types:
                streams = self.resolve_streams(stream_type)
                for stream_info in streams:
                    inlet = pylsl.StreamInlet(stream_info)
                    self.inlets[f"{stream_type}_{stream_info.name()}"] = inlet
                    
            logging.info(f"Started recording from {len(self.inlets)} streams")
            return True
            
        except Exception as e:
            logging.error(f"Failed to start recording: {e}")
            return False
    
    def stop_recording(self) -> None:
        """Stop recording."""
        self._running = False
        self.inlets.clear()
        logging.info("Stopped LSL recording")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_recording()
        self.outlets.clear()
        self.streams.clear()