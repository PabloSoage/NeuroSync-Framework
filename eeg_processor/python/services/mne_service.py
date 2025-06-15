import logging
import multiprocessing as mp
import queue
import time
from typing import Dict, Any, Optional, Tuple, Callable
import numpy as np

from .data_access_service import DataAccessService

# Check if MNE is available
try:
    import mne
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for processes
    import matplotlib.pyplot as plt
    from scipy import signal
    MNE_AVAILABLE = True
except ImportError:
    MNE_AVAILABLE = False


class MNEService:
    """
    Service for MNE-Python operations using multiprocessing.
    
    This service handles heavy MNE computations in separate processes
    to prevent UI freezing.
    """
    
    _instance: Optional["MNEService"] = None
    _lock = mp.Lock()
    
    @classmethod
    def get_instance(cls) -> "MNEService":
        """Get the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = MNEService()
            return cls._instance
    
    def __init__(self) -> None:
        """Initialize the MNE service."""
        if MNEService._instance is not None:
            raise RuntimeError("MNEService is a singleton. Use get_instance()")
            
        self.data_service = DataAccessService.get_instance()
        
        # Process management
        self._process_pool: Optional[mp.Pool] = None
        self._active_tasks: Dict[str, mp.pool.AsyncResult] = {}
        
        # Results storage
        self._results: Dict[str, Any] = {}
        
        # Callbacks for completion
        self._completion_callbacks: Dict[str, Callable] = {}
        
        logging.info("MNE Service initialized")
    
    def is_available(self) -> bool:
        """Check if MNE is available."""
        return MNE_AVAILABLE
    
    def start_service(self) -> None:
        """Start the MNE service with process pool."""
        if not MNE_AVAILABLE:
            logging.warning("MNE not available, service not started")
            return
            
        if self._process_pool is None:
            # Create process pool with 2 workers for MNE operations
            self._process_pool = mp.Pool(
                processes=2,
                initializer=_mne_worker_init
            )
            logging.info("MNE service started with process pool")
    
    def stop_service(self) -> None:
        """Stop the MNE service and cleanup resources."""
        if self._process_pool is not None:
            # Cancel active tasks
            for task_id, async_result in self._active_tasks.items():
                try:
                    async_result.terminate()
                except:
                    pass
            
            self._active_tasks.clear()
            
            # Terminate process pool
            self._process_pool.terminate()
            self._process_pool.join()
            self._process_pool = None
            
            logging.info("MNE service stopped")
    
    def convert_to_mne_async(
        self, 
        duration_seconds: int,
        convert_to_v: bool = True,
        callback: Optional[Callable] = None
    ) -> str:
        """
        Convert BrainFlow data to MNE format asynchronously.
        
        Args:
            duration_seconds: Duration of data to convert
            convert_to_v: Whether to convert units from µV to V
            callback: Callback function to call when conversion completes
            
        Returns:
            Task ID for tracking the operation
        """
        if not MNE_AVAILABLE or self._process_pool is None:
            raise RuntimeError("MNE service not available or not started")
        
        # Get current data and metadata
        data, timestamps = self.data_service.get_current_data()
        metadata = self.data_service.get_metadata()
        
        if data.size == 0:
            raise ValueError("No data available. Start streaming first.")
        
        # Generate task ID
        task_id = f"convert_{int(time.time() * 1000)}"
        
        # Submit task to process pool
        async_result = self._process_pool.apply_async(
            _convert_to_mne_worker,
            args=(data, metadata, duration_seconds, convert_to_v),
            callback=lambda result: self._handle_conversion_complete(task_id, result, callback)
        )
        
        # Store task
        self._active_tasks[task_id] = async_result
        if callback:
            self._completion_callbacks[task_id] = callback
        
        logging.info(f"Started MNE conversion task: {task_id}")
        return task_id
    
    def create_visualization_async(
        self,
        task_id: str,
        plot_type: str,
        freq_min: int = 1,
        freq_max: int = 50,
        bg_color: str = "#2b2b2b",
        callback: Optional[Callable] = None
    ) -> str:
        """
        Create MNE visualization asynchronously.
        
        Args:
            task_id: Task ID of the MNE conversion result to use
            plot_type: Type of plot to create
            freq_min: Minimum frequency for PSD plots
            freq_max: Maximum frequency for PSD plots
            bg_color: Background color for the plot
            callback: Callback function to call when plotting completes
            
        Returns:
            Task ID for tracking the operation
        """
        if not MNE_AVAILABLE or self._process_pool is None:
            raise RuntimeError("MNE service not available or not started")
        
        # Check if conversion result exists
        if task_id not in self._results:
            raise ValueError(f"No MNE conversion result found for task {task_id}")
        
        mne_data = self._results[task_id]
        if not mne_data.get("success"):
            raise ValueError(f"MNE conversion failed for task {task_id}")
        
        # Generate visualization task ID
        viz_task_id = f"viz_{plot_type}_{int(time.time() * 1000)}"
        
        # Submit visualization task
        async_result = self._process_pool.apply_async(
            _create_visualization_worker,
            args=(mne_data["raw_data"], mne_data["info"], plot_type, freq_min, freq_max, bg_color),
            callback=lambda result: self._handle_visualization_complete(viz_task_id, result, callback)
        )
        
        # Store task
        self._active_tasks[viz_task_id] = async_result
        if callback:
            self._completion_callbacks[viz_task_id] = callback
        
        logging.info(f"Started MNE visualization task: {viz_task_id}")
        return viz_task_id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a task.
        
        Args:
            task_id: Task ID to check
            
        Returns:
            Dictionary with task status information
        """
        if task_id in self._active_tasks:
            async_result = self._active_tasks[task_id]
            return {
                "status": "running" if not async_result.ready() else "completed",
                "ready": async_result.ready(),
                "successful": async_result.successful() if async_result.ready() else None
            }
        elif task_id in self._results:
            return {
                "status": "completed",
                "ready": True,
                "successful": self._results[task_id].get("success", False)
            }
        else:
            return {
                "status": "not_found",
                "ready": False,
                "successful": False
            }
    
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the result of a completed task.
        
        Args:
            task_id: Task ID to get result for
            
        Returns:
            Result dictionary or None if not found
        """
        return self._results.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel an active task.
        
        Args:
            task_id: Task ID to cancel
            
        Returns:
            True if task was cancelled, False otherwise
        """
        if task_id in self._active_tasks:
            try:
                async_result = self._active_tasks[task_id]
                async_result.terminate()
                del self._active_tasks[task_id]
                if task_id in self._completion_callbacks:
                    del self._completion_callbacks[task_id]
                logging.info(f"Cancelled MNE task: {task_id}")
                return True
            except Exception as e:
                logging.error(f"Error cancelling task {task_id}: {e}")
        return False
    
    def _handle_conversion_complete(self, task_id: str, result: Dict[str, Any], callback: Optional[Callable]) -> None:
        """Handle completion of MNE conversion task."""
        # Store result
        self._results[task_id] = result
        
        # Remove from active tasks
        if task_id in self._active_tasks:
            del self._active_tasks[task_id]
        
        # Call callback if provided
        if callback:
            try:
                callback(task_id, result)
            except Exception as e:
                logging.error(f"Error in MNE conversion callback: {e}")
        
        # Clean up callback
        if task_id in self._completion_callbacks:
            del self._completion_callbacks[task_id]
        
        logging.info(f"MNE conversion task completed: {task_id}")
    
    def _handle_visualization_complete(self, task_id: str, result: Dict[str, Any], callback: Optional[Callable]) -> None:
        """Handle completion of MNE visualization task."""
        # Store result
        self._results[task_id] = result
        
        # Remove from active tasks
        if task_id in self._active_tasks:
            del self._active_tasks[task_id]
        
        # Call callback if provided
        if callback:
            try:
                callback(task_id, result)
            except Exception as e:
                logging.error(f"Error in MNE visualization callback: {e}")
        
        # Clean up callback
        if task_id in self._completion_callbacks:
            del self._completion_callbacks[task_id]
        
        logging.info(f"MNE visualization task completed: {task_id}")
    
    def cleanup(self) -> None:
        """Cleanup resources when shutting down."""
        self.stop_service()


# Worker functions for multiprocessing

def _mne_worker_init() -> None:
    """Initialize MNE worker process."""
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _convert_to_mne_worker(
    data: np.ndarray,
    metadata: Dict[str, Any],
    duration_seconds: int,
    convert_to_v: bool
) -> Dict[str, Any]:
    """
    Worker function to convert BrainFlow data to MNE format.
    
    Args:
        data: EEG data array
        metadata: Stream metadata
        duration_seconds: Duration to convert
        convert_to_v: Whether to convert units
        
    Returns:
        Dictionary with conversion result
    """
    try:
        import mne
        
        sampling_rate = metadata.get("sampling_rate", 250)
        samples_needed = int(duration_seconds * sampling_rate)
        
        # Check if we have enough data
        if data.shape[1] < samples_needed:
            return {
                "success": False,
                "error": f"Not enough data. Need {duration_seconds}s but only have {data.shape[1]/sampling_rate:.1f}s"
            }
        
        # Extract last N seconds
        recent_data = data[:, -samples_needed:]
        
        # Get EEG channels
        eeg_channels = metadata.get("eeg_channels", [])
        if not eeg_channels:
            return {
                "success": False,
                "error": "No EEG channels available"
            }
        
        # Extract EEG data
        eeg_data = recent_data[eeg_channels, :]
        
        # Convert units if requested
        if convert_to_v:
            eeg_data = eeg_data / 1000000  # µV to V
        
        # Create channel info
        ch_types = ['eeg'] * len(eeg_channels)
        ch_names = metadata.get("channel_names", [])
        if len(ch_names) < len(eeg_channels):
            ch_names = [f"EEG_{i}" for i in range(len(eeg_channels))]
        else:
            ch_names = ch_names[:len(eeg_channels)]
        
        # Create MNE info object
        info = mne.create_info(ch_names=ch_names, sfreq=sampling_rate, ch_types=ch_types)
        
        return {
            "success": True,
            "raw_data": eeg_data,
            "info": info,
            "duration": duration_seconds,
            "channels": len(eeg_channels),
            "sampling_rate": sampling_rate,
            "converted_to_v": convert_to_v
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _create_visualization_worker(
    raw_data: np.ndarray,
    info: Any,
    plot_type: str,
    freq_min: int,
    freq_max: int,
    bg_color: str
) -> Dict[str, Any]:
    """
    Worker function to create MNE visualizations.
    
    Args:
        raw_data: EEG data array
        info: MNE info object
        plot_type: Type of plot to create
        freq_min: Minimum frequency
        freq_max: Maximum frequency
        bg_color: Background color
        
    Returns:
        Dictionary with visualization result
    """
    try:
        import mne
        import matplotlib.pyplot as plt
        import matplotlib
        from io import BytesIO
        import base64
        
        # Set matplotlib style for dark theme
        plt.style.use('dark_background')
        
        # Create Raw object
        raw = mne.io.RawArray(raw_data, info)
        
        # Create figure with dark background
        fig, ax = plt.subplots(figsize=(10, 8), facecolor=bg_color)
        ax.set_facecolor(bg_color)
        
        if plot_type.lower() == "psd":
            # Create PSD plot
            psd = raw.compute_psd(fmin=freq_min, fmax=freq_max, method='welch')
            psd.plot(axes=ax, show=False, average=True)
            ax.set_title(f"Power Spectral Density ({freq_min}-{freq_max} Hz)", color='white')
            ax.set_xlabel("Frequency (Hz)", color='white')
            ax.set_ylabel("Power (V²/Hz)", color='white')
            
        elif plot_type.lower() == "topomap":
            # Create topomap for alpha band
            psd = raw.compute_psd(fmin=8, fmax=13, method='welch')
            psd_avg = psd.get_data().mean(axis=1)
            
            # Simple representation since we don't have electrode positions
            ax.text(0.5, 0.5, f"Alpha Power Topomap\n({len(psd_avg)} channels)", 
                   ha='center', va='center', transform=ax.transAxes, color='white')
            ax.set_title("Alpha Band Power (8-13 Hz)", color='white')
            ax.axis('off')
            
        elif plot_type.lower() == "raw data":
            # Plot raw time series data
            data_to_plot = raw.get_data()
            times = raw.times
            
            # Plot first few channels to avoid clutter
            max_channels = min(4, data_to_plot.shape[0])
            colors = plt.cm.tab10(np.linspace(0, 1, max_channels))
            
            for i in range(max_channels):
                ax.plot(times, data_to_plot[i], label=f"Channel {i}", color=colors[i])
            
            ax.set_xlabel("Time (s)", color='white')
            ax.set_ylabel("Amplitude (V)", color='white')
            ax.set_title("Raw EEG Data", color='white')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
        elif plot_type.lower() == "spectrogram":
            # Create spectrogram for first channel
            data_ch0 = raw.get_data()[0]
            fs = raw.info['sfreq']
            
            from scipy import signal
            f, t, Sxx = signal.spectrogram(data_ch0, fs)
            im = ax.pcolormesh(t, f, 10 * np.log10(Sxx), cmap='viridis')
            ax.set_ylabel('Frequency [Hz]', color='white')
            ax.set_xlabel('Time [s]', color='white')
            ax.set_title('Spectrogram (Channel 0)', color='white')
            cbar = fig.colorbar(im, ax=ax)
            cbar.set_label('Power (dB)', color='white')
            cbar.ax.yaxis.set_tick_params(color='white')
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        
        # Set tick colors
        ax.tick_params(colors='white')
        
        # Convert plot to base64 string
        buffer = BytesIO()
        fig.savefig(buffer, format='png', facecolor=bg_color, edgecolor='none', bbox_inches='tight')
        buffer.seek(0)
        plot_data = base64.b64encode(buffer.read()).decode()
        buffer.close()
        
        plt.close(fig)
        
        return {
            "success": True,
            "plot_type": plot_type,
            "plot_data": plot_data,
            "freq_range": [freq_min, freq_max]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
