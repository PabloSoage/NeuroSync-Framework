import logging
import threading
import time
from typing import Dict, Any, Optional, Callable, List

from ..data_access_service import DataAccessService
from ...interfaces.mne_interfaces import (
    MNERealtimeInterface,
    MNEConverterInterface,
    MNEVisualizerInterface,
    MNEResultStorageInterface,
)

# Check if MNE is available
try:
    import mne

    MNE_AVAILABLE = True
except ImportError:
    MNE_AVAILABLE = False


class MNERealtimeService(MNERealtimeInterface):
    """Service for real-time MNE processing and visualization."""

    def __init__(
        self,
        converter_service: MNEConverterInterface,
        visualizer_service: MNEVisualizerInterface,
        result_storage: MNEResultStorageInterface,
    ) -> None:
        """Initialize the real-time service."""
        self.converter_service = converter_service
        self.visualizer_service = visualizer_service
        self.result_storage = result_storage
        self.data_service = DataAccessService.get_instance()

        # Real-time session management
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._session_threads: Dict[str, threading.Thread] = {}
        self._session_stop_events: Dict[str, threading.Event] = {}
        self._session_lock = threading.RLock()

        logging.info("MNE real-time service initialized")

    def start_realtime_processing(
        self,
        update_interval_seconds: float = 2.0,
        plot_type: str = "PSD",
        duration_seconds: int = 10,
        convert_to_v: bool = True,
        selected_channels: Optional[List[int]] = None,
        visualization_params: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable] = None,
        use_filters: bool = False,
        filter_settings: Optional[Dict[str, Any]] = None,
        processor_service: Optional[Any] = None,
        use_raw_data: bool = False,
    ) -> str:
        """Start real-time MNE processing."""
        if not MNE_AVAILABLE:
            raise RuntimeError("MNE package not available")

        # Validate and adjust update interval
        if update_interval_seconds < 0.5:
            logging.warning(
                f"Update interval {update_interval_seconds}s too low, setting to 0.5s"
            )
            update_interval_seconds = 0.5
        elif update_interval_seconds > 30.0:
            logging.warning(
                f"Update interval {update_interval_seconds}s too high, setting to 30s"
            )
            update_interval_seconds = 30.0

        # Performance warnings and recommendations
        if update_interval_seconds < 1.0:
            logging.warning(
                f"High-frequency real-time mode active ({update_interval_seconds}s). "
                "Monitor CPU usage and consider fewer channels for optimal performance."
            )

        # Adaptive timeout based on update interval
        max_processing_time = max(
            update_interval_seconds * 0.8, 5.0
        )  # Leave 20% buffer, min 5s

        # Generate session ID
        session_id = f"realtime_{int(time.time() * 1000)}"

        # Prepare session configuration with performance optimizations
        session_config = {
            "session_id": session_id,
            "update_interval": update_interval_seconds,
            "plot_type": plot_type,
            "duration_seconds": duration_seconds,
            "convert_to_v": convert_to_v,
            "selected_channels": selected_channels,
            "visualization_params": visualization_params or {},
            "callback": callback,
            "start_time": time.time(),
            "update_count": 0,
            "last_update": 0,
            "status": "starting",
            "current_conversion_task": None,
            "current_visualization_task": None,
            "max_processing_time": max_processing_time,
            "performance_stats": {
                "avg_processing_time": 0.0,
                "max_processing_time_seen": 0.0,
                "timeout_count": 0,
                "success_count": 0,
            },
            # Add filter support and raw data option
            "use_filters": use_filters,
            "filter_settings": filter_settings,
            "processor_service": processor_service,
            "use_raw_data": use_raw_data,  # NEW: Option to use raw data
        }

        with self._session_lock:
            # Create stop event for this session
            stop_event = threading.Event()
            self._session_stop_events[session_id] = stop_event

            # Store session configuration
            self._active_sessions[session_id] = session_config

            # Start processing thread
            thread = threading.Thread(
                target=self._realtime_processing_loop,
                args=(session_id, stop_event),
                daemon=True,
                name=f"MNE_Realtime_{session_id}",
            )
            self._session_threads[session_id] = thread
            thread.start()

        filter_info = " with filters" if use_filters else ""
        logging.info(
            f"Started real-time MNE processing session{filter_info}: {session_id} (interval: {update_interval_seconds}s)"
        )
        return session_id

    def stop_realtime_processing(self, session_id: str) -> bool:
        """Stop real-time processing session."""
        with self._session_lock:
            if session_id not in self._active_sessions:
                return False

            # Signal thread to stop
            if session_id in self._session_stop_events:
                self._session_stop_events[session_id].set()

            # Cancel any active tasks
            session = self._active_sessions[session_id]
            if session.get("current_conversion_task"):
                self.converter_service.cancel_conversion(
                    session["current_conversion_task"]
                )
            if session.get("current_visualization_task"):
                self.visualizer_service.cancel_visualization(
                    session["current_visualization_task"]
                )

            # Update status
            session["status"] = "stopping"

            # Wait for thread to finish (with timeout)
            if session_id in self._session_threads:
                thread = self._session_threads[session_id]
                thread.join(timeout=2.0)

            # Clean up
            self._cleanup_session(session_id)

        logging.info(f"Stopped real-time MNE processing session: {session_id}")
        return True

    def update_realtime_params(self, session_id: str, params: Dict[str, Any]) -> bool:
        """Update real-time processing parameters."""
        with self._session_lock:
            if session_id not in self._active_sessions:
                return False

            session = self._active_sessions[session_id]

            # Update allowed parameters
            allowed_params = [
                "update_interval",
                "plot_type",
                "duration_seconds",
                "convert_to_v",
                "selected_channels",
                "visualization_params",
            ]

            updated_params = []
            for param in allowed_params:
                if param in params:
                    old_value = session.get(param)
                    session[param] = params[param]
                    updated_params.append(f"{param}: {old_value} -> {params[param]}")

            if updated_params:
                logging.info(
                    f"Updated parameters for real-time session {session_id}: {', '.join(updated_params)}"
                )

            return True

    def update_channels(self, session_id: str, selected_channels: List[int]) -> bool:
        """Update selected channels for real-time session."""
        with self._session_lock:
            if session_id not in self._active_sessions:
                return False

            session = self._active_sessions[session_id]
            old_channels = session.get("selected_channels", [])
            session["selected_channels"] = selected_channels

            # OPTIMIZATION: Don't need to update visualization params since we apply selection at conversion level
            # The visualization will automatically show all converted channels

            optimization_info = f"Optimized: Will convert only {len(selected_channels)} channels instead of all"
            if len(old_channels) > 0:
                optimization_info += f" (was {len(old_channels)})"

            logging.info(
                f"Updated channels for session {session_id}: {optimization_info}"
            )
            return True

    def update_visualization_params(
        self, session_id: str, viz_params: Dict[str, Any]
    ) -> bool:
        """Update only visualization parameters for real-time session."""
        with self._session_lock:
            if session_id not in self._active_sessions:
                return False

            session = self._active_sessions[session_id]

            # Merge with existing visualization params to preserve other settings
            if "visualization_params" not in session:
                session["visualization_params"] = {}

            # Update specific visualization parameters
            allowed_viz_params = [
                "plot_type",
                "freq_min",
                "freq_max",
                "show_individual_channels",
                "topomap_freq_range",
                "bg_color",
                "selected_channels_for_display",
            ]

            updated_params = []
            for param in allowed_viz_params:
                if param in viz_params:
                    old_value = session["visualization_params"].get(param)
                    session["visualization_params"][param] = viz_params[param]
                    if old_value != viz_params[param]:
                        updated_params.append(
                            f"{param}: {old_value} -> {viz_params[param]}"
                        )

            if updated_params:
                logging.info(
                    f"Updated visualization params for session {session_id}: {', '.join(updated_params)}"
                )

            return True

    def update_plot_type(self, session_id: str, plot_type: str) -> bool:
        """Update plot type for real-time session."""
        with self._session_lock:
            if session_id not in self._active_sessions:
                return False

            session = self._active_sessions[session_id]
            old_plot_type = session.get("plot_type", "Unknown")
            session["plot_type"] = plot_type

            # Also update in visualization params if they exist
            if "visualization_params" in session:
                session["visualization_params"]["plot_type"] = plot_type

            logging.info(
                f"Updated plot type for session {session_id}: {old_plot_type} -> {plot_type}"
            )
            return True

    def get_realtime_status(self, session_id: str) -> Dict[str, Any]:
        """Get real-time processing status with performance metrics."""
        with self._session_lock:
            if session_id not in self._active_sessions:
                return {"status": "not_found", "active": False}

            session = self._active_sessions[session_id]
            stats = session.get("performance_stats", {})

            return {
                "status": session["status"],
                "active": session["status"] in ["starting", "running"],
                "session_id": session_id,
                "update_count": session["update_count"],
                "last_update": session["last_update"],
                "uptime": time.time() - session["start_time"],
                "update_interval": session["update_interval"],
                "plot_type": session["plot_type"],
                "performance": {
                    "avg_processing_time": stats.get("avg_processing_time", 0.0),
                    "max_processing_time": stats.get("max_processing_time_seen", 0.0),
                    "timeout_count": stats.get("timeout_count", 0),
                    "success_count": stats.get("success_count", 0),
                    "efficiency": (
                        stats.get("avg_processing_time", 0.0)
                        / session["update_interval"]
                        if session["update_interval"] > 0
                        else 0.0
                    ),
                },
            }

    def is_realtime_active(self, session_id: str) -> bool:
        """Check if real-time processing is active."""
        status = self.get_realtime_status(session_id)
        return status.get("active", False)

    def _realtime_processing_loop(
        self, session_id: str, stop_event: threading.Event
    ) -> None:
        """Main processing loop for real-time updates with performance monitoring."""
        try:
            with self._session_lock:
                session = self._active_sessions[session_id]
                session["status"] = "running"

            logging.info(f"Started real-time processing loop for session: {session_id}")

            while not stop_event.is_set():
                cycle_start_time = time.time()

                try:
                    # Get current session config (might be updated)
                    with self._session_lock:
                        if session_id not in self._active_sessions:
                            break
                        session = self._active_sessions[session_id].copy()

                    # Check if we have enough data
                    try:
                        # Use raw data or filtered data based on session config
                        use_raw_data = session.get("use_raw_data", False)

                        if use_raw_data:
                            data, timestamps = self.data_service.get_raw_data()
                            logging.debug(
                                f"Real-time session {session_id}: Using raw data"
                            )
                        else:
                            data, timestamps = self.data_service.get_current_data()
                            logging.debug(
                                f"Real-time session {session_id}: Using potentially filtered data"
                            )

                        metadata = self.data_service.get_metadata()

                        if data.size == 0:
                            # Wait for data (adaptive wait for fast intervals)
                            wait_time = min(session["update_interval"] * 0.1, 0.5)
                            stop_event.wait(wait_time)
                            continue

                        sampling_rate = metadata.get("sampling_rate", 250)
                        samples_needed = int(
                            session["duration_seconds"] * sampling_rate
                        )

                        if data.shape[1] < samples_needed:
                            # Not enough data yet (adaptive wait)
                            wait_time = min(session["update_interval"] * 0.1, 0.5)
                            stop_event.wait(wait_time)
                            continue

                    except Exception as e:
                        logging.warning(
                            f"Error getting data for real-time session {session_id}: {e}"
                        )
                        stop_event.wait(1.0)
                        continue

                    # NOTE: Legacy filter application is still supported for backward compatibility
                    # but the preferred method is now through DataAccessService
                    use_filters = session.get("use_filters", False)
                    if (
                        use_filters
                        and session.get("filter_settings")
                        and session.get("processor_service")
                    ):
                        try:
                            processor_service = session["processor_service"]
                            filter_settings = session["filter_settings"]

                            # Apply filters to data (legacy support)
                            filtered_data = data.copy()

                            # Apply bandpass filter if enabled
                            if filter_settings.get("bandpass", {}).get(
                                "enabled", False
                            ):
                                bp = filter_settings["bandpass"]
                                filtered_data = processor_service.apply_bandpass_filter(
                                    filtered_data,
                                    bp.get("low", 1.0),
                                    bp.get("high", 50.0),
                                )

                            # Apply notch filter if enabled
                            if filter_settings.get("notch", {}).get("enabled", False):
                                notch = filter_settings["notch"]
                                filtered_data = processor_service.apply_notch_filter(
                                    filtered_data, notch.get("frequency", 50)
                                )

                            # Apply detrend if enabled
                            if filter_settings.get("detrend", False):
                                filtered_data = processor_service.apply_detrend(
                                    filtered_data
                                )

                            # Replace data with filtered data
                            data = filtered_data
                            logging.debug(
                                f"Applied legacy filters to real-time data for session {session_id}"
                            )
                        except Exception as e:
                            logging.error(
                                f"Error applying legacy filters to real-time data: {e}"
                            )
                            # Continue with unfiltered data

                    # OPTIMIZATION: Apply channel selection BEFORE conversion
                    conversion_channels = session.get("selected_channels")

                    if conversion_channels is not None and len(conversion_channels) > 0:
                        logging.debug(
                            f"Real-time optimization: Converting only {len(conversion_channels)} selected channels"
                        )
                    else:
                        logging.debug(
                            "Real-time: Converting all channels (no selection)"
                        )

                    # Start conversion with optimized channel selection
                    conversion_task = self.converter_service.convert_to_mne_async(
                        data=data,
                        metadata=metadata,
                        duration_seconds=session["duration_seconds"],
                        convert_to_v=session["convert_to_v"],
                        selected_channels=conversion_channels,
                    )

                    # Update session with current task
                    with self._session_lock:
                        if session_id in self._active_sessions:
                            self._active_sessions[session_id][
                                "current_conversion_task"
                            ] = conversion_task

                    # Wait for conversion to complete with adaptive timeout
                    max_wait_time = session["max_processing_time"]
                    wait_start = time.time()

                    while (
                        not stop_event.is_set()
                        and (time.time() - wait_start) < max_wait_time
                    ):
                        status = self.converter_service.get_conversion_status(
                            conversion_task
                        )
                        if status.get("ready"):
                            if status.get("successful"):
                                break
                            else:
                                # Conversion failed
                                logging.warning(
                                    f"Conversion failed in real-time session {session_id}"
                                )
                                break
                        # Shorter polling interval for fast real-time
                        poll_interval = min(session["update_interval"] * 0.05, 0.1)
                        stop_event.wait(poll_interval)

                    if stop_event.is_set():
                        break

                    # Check if conversion completed successfully
                    status = self.converter_service.get_conversion_status(
                        conversion_task
                    )
                    if not (status.get("ready") and status.get("successful")):
                        # Update timeout stats
                        with self._session_lock:
                            if session_id in self._active_sessions:
                                self._active_sessions[session_id]["performance_stats"][
                                    "timeout_count"
                                ] += 1

                        logging.warning(
                            f"Conversion timeout or failed in real-time session {session_id}"
                        )
                        stop_event.wait(session["update_interval"])
                        continue

                    conversion_result = self.result_storage.get_result(conversion_task)
                    if conversion_result is None:
                        logging.warning(
                            f"Conversion result is None in real-time session {session_id}"
                        )
                        stop_event.wait(session["update_interval"])
                        continue

                    # OPTIMIZATION: For visualization, since we already converted only selected channels,
                    # we want to display ALL the converted channels (no further filtering needed)
                    viz_params = session["visualization_params"].copy()
                    viz_params.pop("selected_channels_for_display", None)

                    visualization_task = (
                        self.visualizer_service.create_visualization_async(
                            mne_data=conversion_result,
                            **viz_params,
                        )
                    )

                    # Update session with current visualization task
                    with self._session_lock:
                        if session_id in self._active_sessions:
                            self._active_sessions[session_id][
                                "current_visualization_task"
                            ] = visualization_task

                    # Wait for visualization to complete
                    wait_start = time.time()

                    while (
                        not stop_event.is_set()
                        and (time.time() - wait_start) < max_wait_time
                    ):
                        status = self.visualizer_service.get_visualization_status(
                            visualization_task
                        )
                        if status.get("ready"):
                            if status.get("successful"):
                                # Get result and call callback
                                result = self.result_storage.get_result(
                                    visualization_task
                                )
                                if result and session.get("callback"):
                                    try:
                                        session["callback"](session_id, result)
                                    except Exception as e:
                                        logging.error(
                                            f"Error in real-time callback: {e}"
                                        )
                                break
                            else:
                                logging.warning(
                                    f"Visualization failed in real-time session {session_id}"
                                )
                                break
                        # Shorter polling for fast real-time
                        poll_interval = min(session["update_interval"] * 0.05, 0.1)
                        stop_event.wait(poll_interval)

                    if stop_event.is_set():
                        break

                    # Calculate processing time and update statistics
                    cycle_end_time = time.time()
                    processing_time = cycle_end_time - cycle_start_time

                    # Update session statistics
                    with self._session_lock:
                        if session_id in self._active_sessions:
                            session_ref = self._active_sessions[session_id]
                            session_ref["update_count"] += 1
                            session_ref["last_update"] = time.time()
                            session_ref["current_conversion_task"] = None
                            session_ref["current_visualization_task"] = None

                            # Update performance statistics
                            stats = session_ref["performance_stats"]
                            stats["success_count"] += 1
                            stats["max_processing_time_seen"] = max(
                                stats["max_processing_time_seen"], processing_time
                            )

                            # Rolling average of processing time
                            if stats["avg_processing_time"] == 0:
                                stats["avg_processing_time"] = processing_time
                            else:
                                alpha = 0.1  # Smoothing factor
                                stats["avg_processing_time"] = (
                                    alpha * processing_time
                                    + (1 - alpha) * stats["avg_processing_time"]
                                )

                    # Clean up old results to save memory
                    self.result_storage.remove_result(conversion_task)
                    self.result_storage.remove_result(visualization_task)

                    # Adaptive wait time - account for processing time
                    remaining_time = session["update_interval"] - processing_time
                    if remaining_time > 0:
                        stop_event.wait(remaining_time)
                    elif processing_time > session["update_interval"] * 1.5:
                        # Processing is taking too long, warn user
                        logging.warning(
                            f"Real-time processing taking {processing_time:.2f}s, "
                            f"longer than interval {session['update_interval']}s. "
                            "Consider increasing interval or reducing channels."
                        )

                except Exception as e:
                    logging.error(
                        f"Error in real-time processing loop for session {session_id}: {e}"
                    )
                    # Longer wait on error to prevent spam
                    stop_event.wait(max(session.get("update_interval", 2.0), 2.0))

        except Exception as e:
            logging.error(
                f"Critical error in real-time processing loop for session {session_id}: {e}"
            )

        finally:
            # Clean up session
            with self._session_lock:
                if session_id in self._active_sessions:
                    self._active_sessions[session_id]["status"] = "stopped"

            logging.info(f"Real-time processing loop ended for session: {session_id}")

    def _cleanup_session(self, session_id: str) -> None:
        """Clean up session resources."""
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
        if session_id in self._session_threads:
            del self._session_threads[session_id]
        if session_id in self._session_stop_events:
            del self._session_stop_events[session_id]

    def cleanup_all_sessions(self) -> None:
        """Clean up all active sessions."""
        with self._session_lock:
            session_ids = list(self._active_sessions.keys())
            for session_id in session_ids:
                self.stop_realtime_processing(session_id)

    def get_all_active_sessions(self) -> List[str]:
        """Get list of all active session IDs."""
        with self._session_lock:
            return [
                session_id
                for session_id, session in self._active_sessions.items()
                if session["status"] in ["starting", "running"]
            ]
            return [
                session_id
                for session_id, session in self._active_sessions.items()
                if session["status"] in ["starting", "running"]
            ]
