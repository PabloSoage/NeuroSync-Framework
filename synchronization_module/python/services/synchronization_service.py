"""
Core synchronization service for coordinating EEG and input data streams.
"""
import logging
import threading
import time
import os  # Add missing import
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
        
        # Continuous recording
        self.recording_params = None
        self.recording_file = None
        self.current_file_size = 0
        self.last_save_time = 0
        self.save_interval = 5.0  # Save every 5 seconds
        
        # Synchronization start time
        self.sync_start_time = None
        
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
            # Method 1: Get from DataAccessService (most reliable)
            metadata = {}
            try:
                from eeg_processor.python.services.data_access_service import DataAccessService
                data_access = DataAccessService.get_instance()
                metadata = data_access.get_metadata()
                logging.info(f"Got metadata from DataAccessService: {list(metadata.keys())}")
            except Exception as e:
                logging.warning(f"Could not get metadata from DataAccessService: {e}")
            
            # Method 2: Get from collector service directly - THIS IS THE KEY PART
            if not metadata.get('channel_names') or len(metadata.get('channel_names', [])) == 0:
                try:
                    from eeg_processor.python.services.collector_service import CollectorService
                    collector_service = CollectorService.get_instance()
                    if collector_service.collector:
                        collector = collector_service.collector
                        
                        # Get device info which contains all the channel information
                        device_info = collector.get_device_info()
                        logging.info(f"Device info from collector: {list(device_info.keys())}")
                        
                        # Build complete channel names like RecordingFileWriter does
                        if hasattr(collector, 'num_rows'):
                            complete_channel_names = self._build_complete_channel_names_from_collector(collector)
                            metadata['channel_names'] = complete_channel_names
                            logging.info(f"Built complete channel names: {len(complete_channel_names)} names")
                            logging.info(f"First 10 names: {complete_channel_names[:10]}")
                        
                        # Update other metadata
                        metadata.update({
                            'sampling_rate': device_info.get('sampling_rate', 250),
                            'board_name': device_info.get('board_name', 'Unknown'),
                            'board_id': device_info.get('board_id', -1),
                            'preset': device_info.get('preset', 0),
                            'num_channels': device_info.get('num_rows', 0),
                            'eeg_channels': device_info.get('eeg_channels', []),
                        })
                        
                except Exception as e:
                    logging.warning(f"Could not get metadata from CollectorService: {e}")
            
            self.eeg_metadata = metadata
            
            # Log the final metadata we'll use
            channel_count = len(metadata.get('channel_names', []))
            board_name = metadata.get('board_name', 'Unknown')
            sampling_rate = metadata.get('sampling_rate', 250)
            
            logging.info(f"EEG service connected: {channel_count} channels from {board_name} at {sampling_rate}Hz")
            if channel_count > 0:
                logging.info(f"Channel names: {metadata.get('channel_names', [])[:5]}...")  # Log first 5
            
        except Exception as e:
            logging.warning(f"Could not get EEG metadata: {e}")
            self.eeg_metadata = {}
        
        logging.info("EEG service connected to synchronization")

    def _build_complete_channel_names_from_collector(self, collector: Any) -> List[str]:
        """Build complete channel names list exactly like RecordingFileWriter does."""
        try:
            column_names = []
            num_rows = collector.num_rows
            
            # Get channel types and names (following RecordingFileWriter.generate_column_names)
            channel_types = getattr(collector, 'channel_types', {})
            eeg_names = getattr(collector, 'eeg_names', [])
            
            logging.info(f"Building names for {num_rows} channels")
            logging.info(f"Channel types available: {list(channel_types.keys())}")
            logging.info(f"EEG names available: {len(eeg_names)} names")
            
            # Generate names for each channel following the exact same logic as RecordingFileWriter
            for i in range(num_rows):
                # Check if it's a timestamp channel (usually penultimate)
                if hasattr(collector, 'timestamp_channel') and i == collector.timestamp_channel:
                    column_names.append("Timestamp")
                # Check if it's a marker channel (usually last)
                elif hasattr(collector, 'marker_channel') and i == collector.marker_channel:
                    column_names.append("Marker")
                # EEG channels
                elif i in channel_types.get('eeg', []):
                    eeg_index = channel_types['eeg'].index(i)
                    if eeg_index < len(eeg_names):
                        column_names.append(f"EEG_{eeg_names[eeg_index]}")
                    else:
                        column_names.append(f"EEG_{eeg_index}")
                # EMG channels  
                elif i in channel_types.get('emg', []):
                    emg_index = channel_types['emg'].index(i)
                    column_names.append(f"EMG_{emg_index}")
                # ECG channels
                elif i in channel_types.get('ecg', []):
                    ecg_index = channel_types['ecg'].index(i)
                    column_names.append(f"ECG_{ecg_index}")
                # EOG channels
                elif i in channel_types.get('eog', []):
                    eog_index = channel_types['eog'].index(i)
                    column_names.append(f"EOG_{eog_index}")
                # EDA channels
                elif i in channel_types.get('eda', []):
                    eda_index = channel_types['eda'].index(i)
                    column_names.append(f"EDA_{eda_index}")
                # PPG channels
                elif i in channel_types.get('ppg', []):
                    ppg_index = channel_types['ppg'].index(i)
                    column_names.append(f"PPG_{ppg_index}")
                # Accelerometer channels
                elif i in channel_types.get('accel', []):
                    accel_index = channel_types['accel'].index(i)
                    accel_names = ["X", "Y", "Z"]
                    axis_name = accel_names[accel_index % 3] if accel_index < 3 else str(accel_index)
                    column_names.append(f"ACCEL_{axis_name}")
                # Gyroscope channels
                elif i in channel_types.get('gyro', []):
                    gyro_index = channel_types['gyro'].index(i)
                    gyro_names = ["X", "Y", "Z"]
                    axis_name = gyro_names[gyro_index % 3] if gyro_index < 3 else str(gyro_index)
                    column_names.append(f"GYRO_{axis_name}")
                # Temperature channels
                elif i in channel_types.get('temperature', []):
                    temp_index = channel_types['temperature'].index(i)
                    column_names.append(f"TEMP_{temp_index}")
                # Resistance channels
                elif i in channel_types.get('resistance', []):
                    res_index = channel_types['resistance'].index(i)
                    column_names.append(f"RES_{res_index}")
                else:
                    # Handle CH_0 for sample counter (first channel)
                    if i == 0:
                        column_names.append("CH_0")
                    else:
                        column_names.append(f"CH_{i}")
            
            logging.info(f"Built {len(column_names)} channel names from collector")
            return column_names
            
        except Exception as e:
            logging.error(f"Error building channel names: {e}")
            # Fallback to generic names
            return [f"CH_{i}" for i in range(getattr(collector, 'num_rows', 32))]
    
    def set_input_service(self, input_service: Any) -> None:
        """Set input collector service."""
        self.input_service = input_service
        logging.info("Input service connected to synchronization")
    
    def setup_continuous_recording(self, recording_params: dict) -> None:
        """Setup continuous recording parameters."""
        self.recording_params = recording_params
        logging.info(f"Continuous recording configured: {recording_params['format']} to {recording_params['filepath']}")
    
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
            actual_precision = max(precision_ms, 10.0) # Minimum 10ms for UI
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
            
            # Initialize recording file
            if not self._initialize_recording_file():
                logging.error("Failed to initialize recording file")
                if callback:
                    callback(False, "Failed to initialize recording file")
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
            self.last_save_time = time.time()
            self.sync_start_time = time.time()
            
            # Start periodic saving
            self.timing_manager.register_sync_callback(
                "save_data", self._periodic_save_callback
            )
            
            logging.info(f"Synchronization and recording started")
            
            if callback:
                callback(True, "Recording started successfully")
                
            return True
            
        except Exception as e:
            logging.error(f"Failed to start synchronization: {e}")
            if callback:
                callback(False, f"Failed to start: {e}")
            return False
    
    def _initialize_recording_file(self) -> bool:
        """Initialize the recording file."""
        try:
            if not self.recording_params:
                logging.error("No recording parameters configured")
                return False
            
            filepath = self.recording_params['filepath']
            format_name = self.recording_params['format']
            append_mode = self.recording_params.get('append_mode', False)
            
            # Ensure directory exists
            directory = os.path.dirname(filepath)
            if directory:
                os.makedirs(directory, exist_ok=True)
            
            # For HDF5, we can open the file for incremental writing
            if format_name == 'hdf5':
                mode = 'a' if append_mode and os.path.exists(filepath) else 'w'
                try:
                    import h5py
                    self.recording_file = h5py.File(filepath, mode)
                    
                    # Create/get groups
                    if 'eeg' not in self.recording_file:
                        self.recording_file.create_group('eeg')
                    if 'events' not in self.recording_file:
                        self.recording_file.create_group('events')
                    if 'metadata' not in self.recording_file:
                        self.recording_file.create_group('metadata')
                    
                    logging.info(f"Initialized HDF5 recording file: {filepath}")
                    return True
                    
                except ImportError:
                    logging.error("h5py not available for HDF5 recording")
                    return False
                except Exception as e:
                    logging.error(f"Error opening HDF5 file: {e}")
                    return False
            
            # For other formats, we'll accumulate data and save periodically
            self.recording_file = filepath
            logging.info(f"Configured recording to: {filepath}")
            return True
            
        except Exception as e:
            logging.error(f"Error initializing recording file: {e}")
            return False

    def _periodic_save_callback(self, sync_timestamp: float) -> None:
        """Periodic save callback for continuous recording."""
        try:
            current_time = time.time()
            
            # Save every N seconds
            if current_time - self.last_save_time >= self.save_interval:
                self._save_current_data()
                self.last_save_time = current_time
                
        except Exception as e:
            logging.error(f"Error in periodic save: {e}")

    def _save_current_data(self) -> None:
        """Save current synchronized data to file."""
        try:
            if not self.recording_params or not self.recording_file:
                return
            
            format_name = self.recording_params['format']
            
            if format_name == 'hdf5' and hasattr(self.recording_file, 'create_dataset'):
                self._save_to_hdf5()
            else:
                # For EDF/BIDS, accumulate data and save when stopped
                pass
                
        except Exception as e:
            logging.error(f"Error saving current data: {e}")

    def _save_to_hdf5(self) -> None:
        """Save data incrementally to HDF5 file."""
        try:
            with self._lock:
                if not self.synchronized_data:
                    return
                
                # Get recent data (last 5 seconds)
                current_time = time.time()
                recent_data = [
                    s for s in self.synchronized_data 
                    if current_time - s['timestamp'] <= 5.0
                ]
                
                if not recent_data:
                    return
                
                # Prepare EEG data
                eeg_samples = []
                timestamps = []
                
                for sample in recent_data:
                    if 'eeg_data' in sample and sample['eeg_data'].size > 0:
                        eeg_samples.append(sample['eeg_data'])
                        timestamps.append(sample['timestamp'])
                
                if eeg_samples:
                    # Create timestamped dataset name
                    dataset_name = f"data_{int(current_time)}"
                    
                    # Save EEG data
                    eeg_group = self.recording_file['eeg']
                    if dataset_name not in eeg_group:
                        eeg_matrix = np.concatenate(eeg_samples, axis=1)
                        eeg_group.create_dataset(
                            dataset_name, 
                            data=eeg_matrix,
                            compression='gzip' if self.recording_params.get('compress_data') else None
                        )
                        eeg_group.create_dataset(f"{dataset_name}_timestamps", data=timestamps)
                
                # Save events
                events_to_save = []
                for sample in recent_data:
                    if 'input_events' in sample:
                        events_to_save.extend(sample['input_events'])
                
                if events_to_save:
                    events_group = self.recording_file['events']
                    event_dataset_name = f"events_{int(current_time)}"
                    
                    if event_dataset_name not in events_group:
                        # Convert events to structured format
                        event_times = [e['timestamp'] for e in events_to_save]
                        event_types = [str(e.get('type', '')).encode('utf-8') for e in events_to_save]
                        event_data = [str(e.get('data', '')).encode('utf-8') for e in events_to_save]
                        
                        events_group.create_dataset(f"{event_dataset_name}_times", data=event_times)
                        events_group.create_dataset(f"{event_dataset_name}_types", data=event_types)
                        events_group.create_dataset(f"{event_dataset_name}_data", data=event_data)
                
                # Update file size
                self.recording_file.flush()
                self.current_file_size = os.path.getsize(self.recording_params['filepath'])
                
        except Exception as e:
            logging.error(f"Error saving to HDF5: {e}")

    def get_current_file_size(self) -> int:
        """Get current file size in bytes."""
        try:
            if self.recording_params and os.path.exists(self.recording_params['filepath']):
                return os.path.getsize(self.recording_params['filepath'])
            return self.current_file_size
        except:
            return 0

    def stop_synchronization(self) -> bool:
        """Stop synchronization."""
        if not self.is_active:
            return True
            
        try:
            # Save any remaining data
            if self.recording_params:
                self._finalize_recording()
            
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

    def _finalize_recording(self) -> None:
        """Finalize recording and close files."""
        try:
            format_name = self.recording_params['format']
            
            if format_name == 'hdf5' and hasattr(self.recording_file, 'close'):
                # Save final metadata
                self._save_final_metadata()
                self.recording_file.close()
                logging.info("HDF5 recording finalized")
                
            elif format_name in ['edf', 'edf+']:
                # Save accumulated data to EDF
                self._save_to_edf()
                
            elif format_name == 'bids':
                # Save accumulated data to BIDS
                self._save_to_bids()
            
            elif format_name == 'csv':
                # Save accumulated data to CSV (THIS WAS MISSING!)
                self._save_to_csv()
            
            self.recording_file = None
            self.recording_params = None
            
        except Exception as e:
            logging.error(f"Error finalizing recording: {e}")

    def _save_final_metadata(self) -> None:
        """Save final metadata to recording file."""
        try:
            if not hasattr(self.recording_file, 'create_dataset'):
                return
                
            metadata_group = self.recording_file['metadata']
            
            # Add final recording metadata
            if 'recording_duration' not in metadata_group:
                duration = time.time() - (self.sync_start_time or time.time())
                metadata_group.create_dataset('recording_duration', data=duration)
            
            if 'total_samples' not in metadata_group:
                metadata_group.create_dataset('total_samples', data=len(self.synchronized_data))
            
            # Add EEG metadata
            if self.eeg_metadata:
                for key, value in self.eeg_metadata.items():
                    if key not in metadata_group:
                        try:
                            if isinstance(value, (str, bytes)):
                                metadata_group.create_dataset(key, data=value.encode('utf-8') if isinstance(value, str) else value)
                            elif isinstance(value, (int, float)):
                                metadata_group.create_dataset(key, data=value)
                            elif isinstance(value, (list, np.ndarray)):
                                metadata_group.create_dataset(key, data=value)
                        except Exception as e:
                            logging.warning(f"Could not save metadata key '{key}': {e}")
            
        except Exception as e:
            logging.error(f"Error saving final metadata: {e}")

    def _save_to_edf(self) -> None:
        """Save accumulated data to EDF format."""
        try:
            # Get all synchronized data
            sync_data = self.get_synchronized_data(3600)  # Last hour
            
            if sync_data['eeg_data'].size > 0:
                from ..exporters.export_manager import ExportManager
                export_manager = ExportManager()
                
                # Update metadata with important timestamps
                updated_metadata = sync_data['metadata'].copy()
                updated_metadata['start_timestamp'] = self.sync_start_time
                
                # Ensure we have valid channel names
                if 'channel_names' in updated_metadata and not updated_metadata['channel_names']:
                    updated_metadata['channel_names'] = [f'Ch{i+1}' for i in range(sync_data['eeg_data'].shape[0])]
                
                # Add subject and recording info
                filename = os.path.basename(self.recording_params['filepath'])
                updated_metadata['subject_id'] = os.path.splitext(filename)[0]
                updated_metadata['session_id'] = time.strftime('%Y%m%d', time.localtime(self.sync_start_time))
                
                logging.info(f"Exporting EDF with {sync_data['eeg_data'].shape[1]} samples and {len(sync_data['input_events'].get('events', []))} events")
                
                success = export_manager.export_dataset(
                    format_name='edf',
                    eeg_data=sync_data['eeg_data'],
                    input_events=sync_data['input_events'],
                    metadata=updated_metadata,
                    filepath=self.recording_params['filepath']
                )
                
                if success:
                    logging.info(f"Successfully exported EDF file to {self.recording_params['filepath']}")
                else:
                    logging.error("Failed to export EDF file")
        except Exception as e:
            logging.error(f"Error saving to EDF: {e}")

    def _save_to_bids(self) -> None:
        """Save accumulated data to BIDS format."""
        try:
            # Get all synchronized data
            sync_data = self.get_synchronized_data(3600)  # Last hour
            
            if sync_data['eeg_data'].size > 0:
                from ..exporters.export_manager import ExportManager
                export_manager = ExportManager()
                
                # Update metadata with important timestamps
                updated_metadata = sync_data['metadata'].copy()
                updated_metadata['start_timestamp'] = self.sync_start_time
                
                # Add required BIDS fields
                updated_metadata['subject_id'] = '001'  # Default subject ID
                updated_metadata['session_id'] = '001'  # Default session ID
                updated_metadata['task'] = 'bci'  # Task name
                
                # Ensure we have valid channel names
                if 'channel_names' in updated_metadata and not updated_metadata['channel_names']:
                    updated_metadata['channel_names'] = [f'EEG{i+1:03d}' for i in range(sync_data['eeg_data'].shape[0])]
                    
                logging.info(f"Exporting BIDS dataset with {sync_data['eeg_data'].shape[1]} samples and {len(sync_data['input_events'].get('events', []))} events")
                
                success = export_manager.export_dataset(
                    format_name='bids',
                    eeg_data=sync_data['eeg_data'],
                    input_events=sync_data['input_events'],
                    metadata=updated_metadata,
                    filepath=self.recording_params['filepath']
                )
                
                if success:
                    logging.info(f"Successfully exported BIDS dataset to {self.recording_params['filepath']}")
                else:
                    logging.error("Failed to export BIDS dataset")
        except Exception as e:
            logging.error(f"Error saving to BIDS: {e}")

    def _save_to_csv(self) -> None:
        """Save accumulated data to CSV format."""
        try:
            # Get all synchronized data
            sync_data = self.get_synchronized_data(3600)  # Last hour
            
            if sync_data['eeg_data'].size > 0:
                from ..exporters.export_manager import ExportManager
                export_manager = ExportManager()
                
                # Update metadata with important timestamps and EEG info
                updated_metadata = sync_data['metadata'].copy()
                updated_metadata['start_timestamp'] = self.sync_start_time
                
                # CRITICAL: Ensure we pass the real EEG metadata with correct channel names
                if self.eeg_metadata:
                    # Add all EEG metadata, especially channel names
                    updated_metadata.update({
                        'board_name': self.eeg_metadata.get('board_name', 'Unknown'),
                        'board_id': self.eeg_metadata.get('board_id', -1),
                        'preset': self.eeg_metadata.get('preset', 0),
                        'channel_names': self.eeg_metadata.get('channel_names', []),
                        'sampling_rate': self.eeg_metadata.get('sampling_rate', 250),
                        'num_channels': self.eeg_metadata.get('num_channels', sync_data['eeg_data'].shape[0]),
                        'eeg_channels': self.eeg_metadata.get('eeg_channels', []),
                    })
                    
                    logging.info(f"Using EEG metadata with {len(updated_metadata.get('channel_names', []))} channel names")
                
                # Ensure we have valid channel names matching the EEG data structure  
                channel_names = updated_metadata.get('channel_names', [])
                if not channel_names or len(channel_names) != sync_data['eeg_data'].shape[0]:
                    # Generate fallback names if metadata is missing
                    logging.warning(f"Channel names mismatch: have {len(channel_names)}, need {sync_data['eeg_data'].shape[0]}")
                    num_channels = sync_data['eeg_data'].shape[0]
                    fallback_names = []
                    for i in range(num_channels):
                        if i == 0:
                            fallback_names.append("CH_0")
                        elif i < num_channels - 2:
                            fallback_names.append(f"EEG_Ch{i}")
                        elif i == num_channels - 2:
                            fallback_names.append("Timestamp")
                        else:
                            fallback_names.append("Marker")
                    updated_metadata['channel_names'] = fallback_names
                
                # Add recording session info
                filename = os.path.basename(self.recording_params['filepath'])
                updated_metadata['created_by'] = 'BCI Dataset Creator'
                updated_metadata['sync_method'] = 'LSL'
                
                logging.info(f"Exporting CSV with {sync_data['eeg_data'].shape[1]} samples and {len(sync_data['input_events'].get('events', []))} events")
                logging.info(f"Final channel names: {updated_metadata.get('channel_names', [])[:5]}...")
                
                success = export_manager.export_dataset(
                    format_name='csv',
                    eeg_data=sync_data['eeg_data'],
                    input_events=sync_data['input_events'],
                    metadata=updated_metadata,
                    filepath=self.recording_params['filepath']
                )
                
                if success:
                    logging.info(f"Successfully exported CSV file to {self.recording_params['filepath']}")
                else:
                    logging.error("Failed to export CSV file")
            else:
                logging.warning("No EEG data available for CSV export")
        except Exception as e:
            logging.error(f"Error saving to CSV: {e}")

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

            logging.info(f"Getting synchronized data: {len(self.synchronized_data)} total samples, {len(synchronized)} in time window")
            logging.info(f"EEG buffer size: {len(self.eeg_buffer)}, Input buffer size: {len(self.input_buffer)}")
            
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
                        'board_name': self.eeg_metadata.get('board_name', ''),
                        'num_channels': self.eeg_metadata.get('num_channels', 0),
                        'start_timestamp': self.sync_start_time  # Add start timestamp for EDF
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
            
            logging.info(f"Received EEG data: shape={data.shape}, timestamps={len(timestamps)}")
                
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
                logging.debug("EEG data queued for processing")
            except:
                # Queue full, skip this sample to avoid blocking
                logging.warning("Processing queue full, skipping EEG sample")
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