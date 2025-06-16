import logging
import threading
import time
from typing import Dict, Any, Optional, Callable, List

from ...interfaces.mne_interfaces import (
    MNERealtimeInterface,
    MNEConverterInterface,
    MNEVisualizerInterface,
    MNEResultStorageInterface,
)
from ..data_access_service import DataAccessService

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
    ) -> str:
        """Start real-time MNE processing."""
        if not MNE_AVAILABLE:
            raise RuntimeError("MNE package not available")

        # Generate session ID
        session_id = f"realtime_{int(time.time() * 1000)}"

        # Prepare session configuration
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
                name=f"MNE_Realtime_{session_id}"
            )
            self._session_threads[session_id] = thread
            thread.start()

        logging.info(f"Started real-time MNE processing session: {session_id}")
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
                self.converter_service.cancel_conversion(session["current_conversion_task"])
            if session.get("current_visualization_task"):
                self.visualizer_service.cancel_visualization(session["current_visualization_task"])

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
                "update_interval", "plot_type", "duration_seconds",
                "convert_to_v", "selected_channels", "visualization_params"
            ]
            
            updated_params = []
            for param in allowed_params:
                if param in params:
                    old_value = session.get(param)
                    session[param] = params[param]
                    updated_params.append(f"{param}: {old_value} -> {params[param]}")

            if updated_params:
                logging.info(f"Updated parameters for real-time session {session_id}: {', '.join(updated_params)}")
            
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
            
            logging.info(f"Updated channels for session {session_id}: {optimization_info}")
            return True

    def update_visualization_params(self, session_id: str, viz_params: Dict[str, Any]) -> bool:
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
                "plot_type", "freq_min", "freq_max", "show_individual_channels",
                "topomap_freq_range", "bg_color", "selected_channels_for_display"
            ]
            
            updated_params = []
            for param in allowed_viz_params:
                if param in viz_params:
                    old_value = session["visualization_params"].get(param)
                    session["visualization_params"][param] = viz_params[param]
                    if old_value != viz_params[param]:
                        updated_params.append(f"{param}: {old_value} -> {viz_params[param]}")
            
            if updated_params:
                logging.info(f"Updated visualization params for session {session_id}: {', '.join(updated_params)}")
            
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
            
            logging.info(f"Updated plot type for session {session_id}: {old_plot_type} -> {plot_type}")
            return True

    def get_realtime_status(self, session_id: str) -> Dict[str, Any]:
        """Get real-time processing status."""
        with self._session_lock:
            if session_id not in self._active_sessions:
                return {"status": "not_found", "active": False}

            session = self._active_sessions[session_id]
            return {
                "status": session["status"],
                "active": session["status"] in ["starting", "running"],
                "session_id": session_id,
                "update_count": session["update_count"],
                "last_update": session["last_update"],
                "uptime": time.time() - session["start_time"],
                "update_interval": session["update_interval"],
                "plot_type": session["plot_type"],
            }

    def is_realtime_active(self, session_id: str) -> bool:
        """Check if real-time processing is active."""
        status = self.get_realtime_status(session_id)
        return status.get("active", False)

    def _realtime_processing_loop(self, session_id: str, stop_event: threading.Event) -> None:
        """Main processing loop for real-time updates."""
        try:
            with self._session_lock:
                session = self._active_sessions[session_id]
                session["status"] = "running"

            logging.info(f"Started real-time processing loop for session: {session_id}")

            while not stop_event.is_set():
                try:
                    # Get current session config (might be updated)
                    with self._session_lock:
                        if session_id not in self._active_sessions:
                            break
                        session = self._active_sessions[session_id].copy()

                    # Check if we have enough data
                    try:
                        data, timestamps = self.data_service.get_current_data()
                        metadata = self.data_service.get_metadata()
                        
                        if data.size == 0:
                            # Wait for data
                            stop_event.wait(0.5)
                            continue

                        sampling_rate = metadata.get("sampling_rate", 250)
                        samples_needed = int(session["duration_seconds"] * sampling_rate)
                        
                        if data.shape[1] < samples_needed:
                            # Not enough data yet
                            stop_event.wait(0.5)
                            continue

                    except Exception as e:
                        logging.warning(f"Error getting data for real-time session {session_id}: {e}")
                        stop_event.wait(1.0)
                        continue

                    # OPTIMIZATION: Apply channel selection BEFORE conversion
                    # This saves processing time and memory by only converting selected channels
                    conversion_channels = session.get("selected_channels")
                    
                    # If we have channel selection, use it directly for conversion
                    # This way we only convert the channels we actually want to visualize
                    if conversion_channels is not None and len(conversion_channels) > 0:
                        logging.debug(f"Real-time optimization: Converting only {len(conversion_channels)} selected channels")
                    else:
                        # No selection means convert all channels
                        logging.debug("Real-time: Converting all channels (no selection)")

                    # Start conversion with optimized channel selection
                    conversion_task = self.converter_service.convert_to_mne_async(
                        data=data,
                        metadata=metadata,
                        duration_seconds=session["duration_seconds"],
                        convert_to_v=session["convert_to_v"],
                        selected_channels=conversion_channels,  # Apply selection at conversion level
                    )

                    # Update session with current task
                    with self._session_lock:
                        if session_id in self._active_sessions:
                            self._active_sessions[session_id]["current_conversion_task"] = conversion_task

                    # Wait for conversion to complete
                    max_wait_time = 30.0  # Maximum wait time in seconds
                    wait_start = time.time()
                    
                    while not stop_event.is_set() and (time.time() - wait_start) < max_wait_time:
                        status = self.converter_service.get_conversion_status(conversion_task)
                        if status.get("ready"):
                            if status.get("successful"):
                                break
                            else:
                                # Conversion failed
                                logging.warning(f"Conversion failed in real-time session {session_id}")
                                stop_event.wait(session["update_interval"])
                                continue
                        stop_event.wait(0.1)

                    if stop_event.is_set():
                        break

                    # Check if conversion completed successfully
                    status = self.converter_service.get_conversion_status(conversion_task)
                    if not (status.get("ready") and status.get("successful")):
                        logging.warning(f"Conversion timeout or failed in real-time session {session_id}")
                        stop_event.wait(session["update_interval"])
                        continue

                    # OPTIMIZATION: For visualization, since we already converted only selected channels,
                    # we want to display ALL the converted channels (no further filtering needed)
                    viz_params = session["visualization_params"].copy()
                    
                    # Set selected_channels_for_display to None to show all converted channels
                    # This is optimal because we already filtered at conversion time
                    viz_params["selected_channels_for_display"] = None
                    
                    # Remove any conflicting channel selection parameters
                    viz_params.pop("selected_channels_for_display", None)

                    visualization_task = self.visualizer_service.create_visualization_async(
                        mne_data=self.result_storage.get_result(conversion_task),
                        **viz_params
                    )

                    # Update session with current visualization task
                    with self._session_lock:
                        if session_id in self._active_sessions:
                            self._active_sessions[session_id]["current_visualization_task"] = visualization_task

                    # Wait for visualization to complete
                    wait_start = time.time()
                    
                    while not stop_event.is_set() and (time.time() - wait_start) < max_wait_time:
                        status = self.visualizer_service.get_visualization_status(visualization_task)
                        if status.get("ready"):
                            if status.get("successful"):
                                # Get result and call callback
                                result = self.result_storage.get_result(visualization_task)
                                if result and session.get("callback"):
                                    try:
                                        session["callback"](session_id, result)
                                    except Exception as e:
                                        logging.error(f"Error in real-time callback: {e}")
                                break
                            else:
                                logging.warning(f"Visualization failed in real-time session {session_id}")
                                break
                        stop_event.wait(0.1)

                    if stop_event.is_set():
                        break

                    # Update session statistics
                    with self._session_lock:
                        if session_id in self._active_sessions:
                            self._active_sessions[session_id]["update_count"] += 1
                            self._active_sessions[session_id]["last_update"] = time.time()
                            self._active_sessions[session_id]["current_conversion_task"] = None
                            self._active_sessions[session_id]["current_visualization_task"] = None

                    # Clean up old results to save memory
                    self.result_storage.remove_result(conversion_task)
                    self.result_storage.remove_result(visualization_task)

                    # Wait for next update
                    stop_event.wait(session["update_interval"])

                except Exception as e:
                    logging.error(f"Error in real-time processing loop for session {session_id}: {e}")
                    stop_event.wait(2.0)

        except Exception as e:
            logging.error(f"Critical error in real-time processing loop for session {session_id}: {e}")

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
                session_id for session_id, session in self._active_sessions.items()
                if session["status"] in ["starting", "running"]
            ]
            return [
                session_id for session_id, session in self._active_sessions.items()
                if session["status"] in ["starting", "running"]
            ]
