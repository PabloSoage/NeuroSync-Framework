import logging
import threading
import multiprocessing as mp
import queue
import time
from typing import Dict, List, Any, Tuple, Callable, Optional

import numpy as np


class DataAccessService:
    """
    Service providing real-time access to EEG data stream.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "DataAccessService":
        """Get the singleton instance of the service."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = DataAccessService()
            return cls._instance

    def __init__(self) -> None:
        """Initialize the data access service."""
        self._data_lock = threading.Lock()
        self._metadata_lock = threading.Lock()

        # Current data buffer: 2D array (channels x samples), start empty
        self._current_data = np.zeros((0, 0))
        self._timestamps: List[int] = []
        # Buffer management
        self._buffer_max_samples: Optional[int] = None
        self._default_buffer_seconds = 30  # Keep 30 seconds by default

        # Reference to collector service for direct access when needed
        self._collector_service: Optional[Any] = None

        # Board and stream metadata
        self._metadata = {
            "sampling_rate": 0,
            "eeg_channels": [],
            "channel_names": [],
            "num_channels": 0,
            "board_id": -1,
            "board_name": "",
            "streaming": False,
            "last_update": 0,
        }

        # Registered callbacks for data updates - SEPARATED BY TYPE
        self._local_callbacks: List[Optional[Callable[[np.ndarray, List[int]], None]]] = []
        self._api_callbacks: List[Optional[Callable[[np.ndarray, List[int]], None]]] = []
        self._callback_lock = threading.Lock()

        # Filter settings and processor service for optional filtering
        self._filter_settings: Optional[Dict[str, Any]] = None
        self._filters_enabled = False
        self._processor_service: Optional[Any] = None

        # MULTIPROCESSING FOR API CALLBACKS ONLY
        self._use_api_multiprocessing = False
        self._api_data_queue: Optional[mp.Queue] = None
        self._api_processed_queue: Optional[mp.Queue] = None
        self._api_process_pool: Optional[mp.pool.Pool] = None
        self._api_worker_thread: Optional[threading.Thread] = None
        self._api_stop_event = threading.Event()

        # Initialize collector reference (will be set properly when collector starts)
        self._init_collector_reference()

        logging.info("Data access service initialized with separated callback flows")

    def _init_collector_reference(self) -> None:
        """Initialize reference to collector service (if available)."""
        try:
            from .collector_service import CollectorService

            self._collector_service = CollectorService.get_instance()
            logging.info("Connected to collector service")
        except Exception as e:
            logging.debug(f"Could not connect to collector service: {e}")

    def register_local_callback(self, callback: Callable[[np.ndarray, List[int]], None]) -> int:
        """Register a callback for local app use (immediate data, no processing)."""
        with self._callback_lock:
            callback_id = len(self._local_callbacks)
            self._local_callbacks.append(callback)
            logging.info(f"Registered local callback (ID: {callback_id})")
            return callback_id

    def register_api_callback(self, callback: Callable[[np.ndarray, List[int]], None]) -> int:
        """Register a callback for API use (potentially processed data)."""
        with self._callback_lock:
            callback_id = len(self._api_callbacks)
            self._api_callbacks.append(callback)
            
            # Enable multiprocessing for API if not already enabled
            if not self._use_api_multiprocessing:
                self._enable_api_multiprocessing()
                
            logging.info(f"Registered API callback (ID: {callback_id}), multiprocessing enabled")
            return callback_id

    def register_api_callback_direct(self, callback: Callable[[np.ndarray, List[int]], None]) -> int:
        """Register a DIRECT callback for API use (immediate, no multiprocessing for low latency)."""
        with self._callback_lock:
            callback_id = len(self._api_callbacks)
            self._api_callbacks.append(callback)
            
            # DON'T enable multiprocessing for direct callbacks
            logging.info(f"Registered DIRECT API callback (ID: {callback_id}), immediate processing")
            return callback_id

    def unregister_local_callback(self, callback_id: int) -> bool:
        """Unregister a local callback."""
        with self._callback_lock:
            if 0 <= callback_id < len(self._local_callbacks):
                self._local_callbacks[callback_id] = None
                logging.info(f"Unregistered local callback (ID: {callback_id})")
                return True
            return False

    def unregister_api_callback(self, callback_id: int) -> bool:
        """Unregister an API callback."""
        with self._callback_lock:
            if 0 <= callback_id < len(self._api_callbacks):
                self._api_callbacks[callback_id] = None
                
                # Check if we still have active API callbacks
                active_api_callbacks = [cb for cb in self._api_callbacks if cb is not None]
                if not active_api_callbacks and self._use_api_multiprocessing:
                    self._disable_api_multiprocessing()
                    
                logging.info(f"Unregistered API callback (ID: {callback_id})")
                return True
            return False

    def _enable_api_multiprocessing(self) -> None:
        """Enable multiprocessing for API callbacks."""
        if self._use_api_multiprocessing:
            return
            
        try:
            self._use_api_multiprocessing = True
            
            # Create queues for inter-process communication
            self._api_data_queue = mp.Queue(maxsize=1000)
            self._api_processed_queue = mp.Queue(maxsize=500)

            # Determine number of workers based on CPU
            num_workers = max(2, min(4, mp.cpu_count() - 1))

            # Create process pool for data processing
            self._api_process_pool = mp.Pool(
                processes=num_workers,
                initializer=self._api_worker_init,
                initargs=(self._api_data_queue, self._api_processed_queue),
            )

            # Start thread to handle processed results
            self._api_stop_event.clear()
            self._api_worker_thread = threading.Thread(target=self._api_result_handler, daemon=True)
            self._api_worker_thread.start()

            logging.info(f"API multiprocessing enabled with {num_workers} workers")

        except Exception as e:
            logging.error(f"Error enabling API multiprocessing: {e}")
            self._use_api_multiprocessing = False

    def _disable_api_multiprocessing(self) -> None:
        """Disable multiprocessing for API callbacks."""
        if not self._use_api_multiprocessing:
            return
            
        try:
            self._use_api_multiprocessing = False
            
            # Stop worker thread
            self._api_stop_event.set()
            if self._api_worker_thread:
                self._api_worker_thread.join(timeout=5)
            
            # Cleanup process pool
            if self._api_process_pool:
                self._api_process_pool.terminate()
                self._api_process_pool.join()
                self._api_process_pool = None

            # Clean up queues
            if self._api_data_queue:
                try:
                    while not self._api_data_queue.empty():
                        self._api_data_queue.get_nowait()
                except:
                    pass
                self._api_data_queue = None

            if self._api_processed_queue:
                try:
                    while not self._api_processed_queue.empty():
                        self._api_processed_queue.get_nowait()
                except:
                    pass
                self._api_processed_queue = None

            logging.info("API multiprocessing disabled")

        except Exception as e:
            logging.error(f"Error disabling API multiprocessing: {e}")

    @staticmethod
    def _api_worker_init(data_queue: mp.Queue, processed_queue: mp.Queue) -> None:
        """Initialize API worker process."""
        import signal

        signal.signal(signal.SIGINT, signal.SIG_IGN)  # Ignore keyboard interrupt

        # Worker loop
        while True:
            try:
                # Get data from queue with timeout
                try:
                    data_package = data_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                if data_package is None:  # Shutdown signal
                    break

                # Process data (for now just pass through, but could add API-specific processing)
                processed_data = DataAccessService._process_api_data_chunk(data_package)

                # Send processed data back
                try:
                    processed_queue.put_nowait(processed_data)
                except queue.Full:
                    # Skip if queue is full to avoid blocking
                    pass

            except Exception as e:
                logging.error(f"Error in API worker process: {e}")

    @staticmethod
    def _process_api_data_chunk(data_package: Dict[str, Any]) -> Dict[str, Any]:
        """Process a chunk of data for API use."""
        try:
            data = data_package["data"]
            timestamps = data_package["timestamps"]
            metadata = data_package.get("metadata", {})

            # TODO: Here we can add intensive processing implementations like:
            #  - Signal filtering (bandpass, notch, etc.)
            #  - Artifact detection (eye blinks, muscle activity, electrode issues)
            #  - Data compression for transmission optimization
            #  - Real-time spectral analysis (FFT, PSD, band powers)
            #  - Signal quality assessment
            #  - Feature extraction for BCI applications
            #  - Real-time event detection
            #  - Adaptive filtering based on signal characteristics

            # processed_data = data.copy()

            # Optimization: reduce precision if necessary to save bandwidth
            # This is currently not implemented because there are no bandwidth issues,
            # thus maintaining accuracy.

            return {
                "data": data,
                "timestamps": timestamps,
                "metadata": metadata,
                "processed_at": time.time(),
                "api_processed": True,
            }

        except Exception as e:
            logging.error(f"Error processing API data chunk: {e}")
            return data_package

    def _api_result_handler(self) -> None:
        """Handle processed results from API workers."""
        while not self._api_stop_event.is_set():
            try:
                if self._api_processed_queue is None:
                    break
                    
                try:
                    processed_package = self._api_processed_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                data = processed_package["data"]
                timestamps = processed_package["timestamps"]
                chunk_size = processed_package.get("metadata", {}).get("chunk_size", data.shape[1] if data.size > 0 else 0)

                # Send to API callbacks only
                with self._callback_lock:
                    for callback in self._api_callbacks:
                        if callback is not None:
                            try:
                                # Send raw data - API will apply filters if needed
                                callback(data, timestamps)
                                logging.debug(f"Sent processed chunk of {chunk_size} samples to API callback")
                            except Exception as e:
                                logging.error(f"Error in API callback: {e}")

            except Exception as e:
                logging.error(f"Error in API result handler: {e}")
                time.sleep(0.1)

    def set_filter_processor(self, processor_service: Any) -> None:
        """Set the processor service for applying filters."""
        self._processor_service = processor_service
        logging.info("Filter processor service set for DataAccessService")

    def enable_filters(
        self, enabled: bool, filter_settings: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Enable or disable filters for data served by this service.

        Args:
            enabled: Whether to enable filters
            filter_settings: Filter configuration (if None, will use existing settings)
        """
        with self._data_lock:
            self._filters_enabled = enabled
            if filter_settings is not None:
                self._filter_settings = filter_settings

        action = "enabled" if enabled else "disabled"
        logging.info(f"DataAccessService filters {action}")

    def update_filter_settings(self, filter_settings: Dict[str, Any]) -> None:
        """Update filter settings."""
        with self._data_lock:
            self._filter_settings = filter_settings
        logging.debug("DataAccessService filter settings updated")

    def _apply_filters_if_enabled(self, data: np.ndarray) -> np.ndarray:
        """Apply filters to data if enabled and processor is available."""
        if not self._filters_enabled or not self._processor_service or not self._filter_settings:
            return data

        if data.size == 0:
            return data

        try:
            # Apply filters to the CHUNK, not the entire buffer
            filtered_data = data.copy()
            
            logging.debug(f"Applying filters to chunk shape {data.shape}")
            
            # Initialize processor if not already done
            if not hasattr(self._processor_service, 'processor') or self._processor_service.processor is None:
                # Try to get sampling rate from metadata
                sampling_rate = self._metadata.get("sampling_rate", 250)
                if sampling_rate > 0:
                    self._processor_service.initialize_processor(int(sampling_rate))
                    logging.info(f"Auto-initialized processor with sampling rate {sampling_rate} Hz for filtering")
                else:
                    logging.warning("Cannot initialize processor: no valid sampling rate")
                    return data
            
            # Apply bandpass filter if enabled
            if self._filter_settings.get("bandpass", {}).get("enabled", False):
                bp = self._filter_settings["bandpass"]
                low_cut = bp.get("low_cut", bp.get("low", 1.0))
                high_cut = bp.get("high_cut", bp.get("high", 50.0))
                logging.debug(f"Applying bandpass filter {low_cut}-{high_cut} Hz to chunk")
                filtered_data = self._processor_service.apply_bandpass_filter(
                    filtered_data, low_cut, high_cut
                )
                
            # Apply notch filter if enabled
            if self._filter_settings.get("notch", {}).get("enabled", False):
                notch = self._filter_settings["notch"]
                freq = notch.get("frequency", 50)
                logging.debug(f"Applying notch filter {freq} Hz to chunk")
                filtered_data = self._processor_service.apply_notch_filter(
                    filtered_data, freq
                )
                
            # Apply detrend if enabled
            if self._filter_settings.get("detrend", False):
                logging.debug("Applying detrend to chunk")
                filtered_data = self._processor_service.apply_detrend(filtered_data)
                
            logging.debug("Filters applied successfully to chunk in DataAccessService")
            return filtered_data
            
        except Exception as e:
            logging.error(f"Error applying filters to chunk in DataAccessService: {e}")
            return data

    def update_data(self, data: np.ndarray, timestamps: List[int]) -> None:
        """Update the current data buffer with automatic truncation."""
        with self._data_lock:
            # Append new data to buffer
            if (
                self._current_data.size == 0
                or self._current_data.shape[0] != data.shape[0]
            ):
                # Initialize or reset buffer if channel count changes
                self._current_data = data.copy()
                self._timestamps = timestamps.copy()
            else:
                # Concatenate along time axis
                self._current_data = np.concatenate((self._current_data, data), axis=1)
                self._timestamps.extend(timestamps)
            
            # LIMIT buffer size to prevent infinite growth
            if self._buffer_max_samples and self._current_data.shape[1] > self._buffer_max_samples:
                # Keep only the most recent samples
                keep_samples = self._buffer_max_samples
                self._current_data = self._current_data[:, -keep_samples:]
                self._timestamps = self._timestamps[-keep_samples:]
                logging.debug(f"Buffer truncated to {keep_samples} samples")

        # Notify callbacks with separated flows
        self._notify_callbacks(data, timestamps)

    def _notify_callbacks(self, data: np.ndarray, timestamps: List[int]) -> None:
        """Notify all registered callbacks with separated processing."""
        # IMMEDIATE notification for local callbacks (no processing delay)
        with self._callback_lock:
            for callback in self._local_callbacks:
                if callback is not None:
                    try:
                        # Send raw data immediately for local app responsiveness
                        callback(data, timestamps)
                        logging.debug("Sent immediate raw data to local callback")
                    except Exception as e:
                        logging.error(f"Error in local data callback: {e}")

        # API callbacks handling - check if multiprocessing is enabled
        if self._api_callbacks and any(cb is not None for cb in self._api_callbacks):
            if self._use_api_multiprocessing and self._api_data_queue is not None:
                # Use multiprocessing (existing implementation)
                self._notify_api_callbacks_multiprocessing(data, timestamps)
            else:
                # DIRECT callbacks for low latency (new implementation)
                self._notify_api_callbacks_direct(data, timestamps)

    def _notify_api_callbacks_direct(self, data: np.ndarray, timestamps: List[int]) -> None:
        """Notify API callbacks directly for low latency."""
        with self._callback_lock:
            for callback in self._api_callbacks:
                if callback is not None:
                    try:
                        # Send raw data immediately - API will handle filtering if needed
                        callback(data, timestamps)
                        logging.debug(f"Sent {data.shape[1]} samples to API callback DIRECTLY (low latency)")
                    except Exception as e:
                        logging.error(f"Error in direct API callback: {e}")

    def _notify_api_callbacks_multiprocessing(self, data: np.ndarray, timestamps: List[int]) -> None:
        """Notify API callbacks through multiprocessing (existing implementation)."""
        try:
            data_package = {
                "data": data,
                "timestamps": timestamps,
                "metadata": {
                    "timestamp": time.time(),
                    "sampling_rate": self._metadata.get("sampling_rate", 250),
                    "chunk_size": data.shape[1] if data.size > 0 else 0,
                },
            }
            
            # Non-blocking send to queue
            try:
                self._api_data_queue.put_nowait(data_package)
                logging.debug(f"Queued {data.shape[1]} samples for API multiprocessing")
            except queue.Full:
                # If queue is full, try to make space but don't lose all data
                dropped_count = 0
                while dropped_count < 3:
                    try:
                        old_package = self._api_data_queue.get_nowait()
                        dropped_count += 1
                        logging.warning(f"Dropped old API data package ({dropped_count}/3)")
                    except queue.Empty:
                        break
                
                # Try to queue new data
                try:
                    self._api_data_queue.put_nowait(data_package)
                    logging.debug(f"Queued {data.shape[1]} samples after dropping {dropped_count} old packages")
                except queue.Full:
                    logging.warning("API queue still full, dropping current data package")
                    
        except Exception as e:
            logging.error(f"Error queuing data for API multiprocessing: {e}")

    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update stream metadata."""
        with self._metadata_lock:
            self._metadata.update(metadata)
            # Initialize buffer max length when sampling_rate is first known
            sr = self._metadata.get("sampling_rate", 0)
            if sr and not self._buffer_max_samples:
                # Calculate buffer size: sampling_rate * buffer_seconds
                if isinstance(sr, (int, float)):
                    self._buffer_max_samples = int(sr) * self._default_buffer_seconds
                    logging.info(f"Buffer size set to {self._buffer_max_samples} samples ({self._default_buffer_seconds}s at {sr}Hz)")

    def get_current_data(self) -> Tuple[np.ndarray, List[int]]:
        """Get the current data and timestamps, optionally filtered."""
        with self._data_lock:
            raw_data = self._current_data.copy()
            timestamps = self._timestamps.copy()
            
            # Apply filters if enabled - but only to recent data for efficiency
            if self._filters_enabled and raw_data.size > 0:
                logging.debug("DataAccessService: Applying filters to current data")
                
                # For large buffers, only filter recent data to avoid performance issues
                if raw_data.shape[1] > 5000:  # If buffer is large
                    # Filter only the last 5000 samples and use cached older data
                    recent_samples = 5000
                    recent_data = raw_data[:, -recent_samples:]
                    filtered_recent = self._apply_filters_if_enabled(recent_data)
                    
                    # For demo purposes, just return the filtered recent data
                    # In production, you'd want to cache filtered older data
                    filtered_data = filtered_recent
                    filtered_timestamps = timestamps[-recent_samples:]
                else:
                    # Small buffer, filter everything
                    filtered_data = self._apply_filters_if_enabled(raw_data)
                    filtered_timestamps = timestamps
                
                if not np.array_equal(filtered_data, raw_data[:, -filtered_data.shape[1]:]):
                    logging.debug("DataAccessService: Data was successfully filtered")
                else:
                    logging.debug("DataAccessService: Data was not changed by filters")
                    
                return filtered_data, filtered_timestamps
            else:
                logging.debug("DataAccessService: Returning raw data (filters disabled)")
                return raw_data, timestamps

    def get_raw_data(self) -> Tuple[np.ndarray, List[int]]:
        """Get the current raw data and timestamps without any filtering."""
        with self._data_lock:
            return self._current_data.copy(), self._timestamps.copy()

    def get_metadata(self) -> Dict[str, Any]:
        """Get the current stream metadata."""
        with self._metadata_lock:
            metadata = self._metadata.copy()

            # If we have a collector service and metadata is missing critical info, try to get it directly
            if self._collector_service and (
                metadata.get("sampling_rate", 0) == 0
                or not metadata.get("channel_names")
            ):
                self._update_metadata_from_collector(metadata)

            return metadata

    def _update_metadata_from_collector(self, metadata: Dict[str, Any]) -> None:
        """Update metadata from collector if available."""
        try:
            # Get active collector
            collector = self._get_active_collector()
            if not collector:
                return

            # Update sampling rate if missing
            if metadata.get("sampling_rate", 0) == 0 and hasattr(
                collector, "sampling_rate"
            ):
                metadata["sampling_rate"] = collector.sampling_rate

            # Update channel names if missing
            if not metadata.get("channel_names") and hasattr(collector, "eeg_names"):
                metadata["channel_names"] = collector.eeg_names

            # Update EEG channels if missing
            if not metadata.get("eeg_channels") and hasattr(collector, "eeg_channels"):
                metadata["eeg_channels"] = collector.eeg_channels

            # Update board info if missing
            if metadata.get("board_id", -1) == -1 and hasattr(collector, "board_id"):
                metadata["board_id"] = collector.board_id

            # Update board name if missing
            if not metadata.get("board_name") and hasattr(collector, "device_name"):
                metadata["board_name"] = collector.device_name

            # Update preset if missing
            if not metadata.get("preset") and hasattr(collector, "preset"):
                metadata["preset"] = collector.preset

            # Update streaming status
            if hasattr(collector, "is_streaming"):
                metadata["streaming"] = collector.is_streaming

            # Store the entire board_info for convenience if available
            if hasattr(collector, "get_device_info") or hasattr(
                collector, "get_board_info"
            ):
                try:
                    if hasattr(collector, "get_device_info"):
                        metadata["board_info"] = collector.get_device_info()
                    elif hasattr(collector, "get_board_info"):
                        metadata["board_info"] = collector.get_board_info()
                except Exception as e:
                    logging.debug(f"Error getting board info: {e}")
        except Exception as e:
            logging.debug(f"Error updating metadata from collector: {e}")

    def _get_active_collector(self) -> Optional[Any]:
        """Get the active collector from collector service."""
        if not self._collector_service:
            return None

        try:
            # Different possible attribute names in collector service
            if hasattr(self._collector_service, "collector"):
                return self._collector_service.collector
            elif hasattr(self._collector_service, "active_collector"):
                return self._collector_service.active_collector

            # Try to get from collectors dict
            if hasattr(self._collector_service, "_collectors"):
                collectors = self._collector_service._collectors
                active_id = getattr(
                    self._collector_service, "_active_collector_id", None
                )
                if active_id and active_id in collectors:
                    return collectors[active_id]
        except Exception as e:
            logging.debug(f"Error getting active collector: {e}")

        return None

    def get_channel_data(self, channel_index: int) -> Tuple[np.ndarray, List[int]]:
        """Get data for a specific channel, optionally filtered."""
        with self._data_lock:
            if (
                self._current_data.size == 0
                or channel_index >= self._current_data.shape[0]
            ):
                return np.array([]), []

            raw_data = self._current_data.copy()
            timestamps = self._timestamps.copy()

            # Apply filters if enabled
            if self._filters_enabled and raw_data.size > 0:
                filtered_data = self._apply_filters_if_enabled(raw_data)
                return filtered_data[channel_index].copy(), timestamps
            else:
                return raw_data[channel_index].copy(), timestamps

    def get_channel_names(self) -> List[str]:
        """Get names of all channels."""
        with self._metadata_lock:
            names = self._metadata.get("channel_names", [])
            if isinstance(names, list):
                names = names.copy()
            else:
                names = []

            # If names are empty, try to get from collector
            if not names:
                collector = self._get_active_collector()
                if collector and hasattr(collector, "eeg_names"):
                    eeg_names = collector.eeg_names
                    if isinstance(eeg_names, list):
                        names = eeg_names

                # If still empty, try to generate generic names based on channels
                if not names:
                    eeg_channels = self._metadata.get("eeg_channels", [])
                    if eeg_channels and isinstance(eeg_channels, list):
                        names = [f"CH{i+1}" for i in range(len(eeg_channels))]

            return names

    def get_sampling_rate(self) -> float:
        """Get the sampling rate."""
        with self._metadata_lock:
            rate = self._metadata.get("sampling_rate", 0)
            if not isinstance(rate, (int, float)):
                rate = 0

            # If rate is 0, try to get directly from collector
            if rate == 0:
                collector = self._get_active_collector()
                if collector and hasattr(collector, "sampling_rate"):
                    collector_rate = collector.sampling_rate
                    if isinstance(collector_rate, (int, float)):
                        rate = float(collector_rate)
                        # Update metadata for future calls
                        self._metadata["sampling_rate"] = rate

            return float(rate)

    def is_streaming(self) -> bool:
        """Check if streaming is active."""
        with self._metadata_lock:
            streaming = self._metadata.get("streaming", False)
            if not isinstance(streaming, bool):
                streaming = False

            # If not streaming according to metadata, check directly
            if not streaming:
                collector = self._get_active_collector()
                if collector and hasattr(collector, "is_streaming"):
                    collector_streaming = collector.is_streaming
                    if isinstance(collector_streaming, bool):
                        streaming = collector_streaming
                        # Update metadata
                        self._metadata["streaming"] = streaming

            return streaming

    def register_callback(
        self, callback: Callable[[np.ndarray, List[int]], None]
    ) -> int:
        """Register a callback function (defaults to local callback for backward compatibility)."""
        return self.register_local_callback(callback)

    def unregister_callback(self, callback_id: int) -> bool:
        """Unregister a callback (tries local first for backward compatibility)."""
        return self.unregister_local_callback(callback_id)
        return self.register_local_callback(callback)

    def unregister_callback(self, callback_id: int) -> bool:
        """Unregister a callback (tries local first for backward compatibility)."""
        return self.unregister_local_callback(callback_id)
