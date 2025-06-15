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
        import numpy as np  # Add explicit numpy import
        import matplotlib.pyplot as plt
        import matplotlib
        from io import BytesIO
        import base64
        
        # Set high DPI for better quality
        matplotlib.rcParams['figure.dpi'] = 150
        matplotlib.rcParams['savefig.dpi'] = 200
        
        # Configure matplotlib for dark theme with better contrast
        plt.style.use('dark_background')
        
        # Override some style settings for better contrast
        matplotlib.rcParams.update({
            'text.color': '#FFFFFF',
            'axes.labelcolor': '#FFFFFF',
            'axes.edgecolor': '#CCCCCC',
            'xtick.color': '#CCCCCC',
            'ytick.color': '#CCCCCC',
            'grid.color': '#555555',
            'font.size': 11,
            'axes.titlesize': 13,
            'axes.labelsize': 11,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10,
            'figure.titlesize': 14
        })
        
        # Create Raw object
        raw = mne.io.RawArray(raw_data, info)
        
        # Calculate figure size based on plot type to maintain aspect ratio
        if plot_type.lower() in ["psd", "spectrogram"]:
            # For frequency domain plots, use wider aspect ratio
            figsize = (12, 7)
        elif plot_type.lower() == "raw data":
            # For time series, use wider format
            figsize = (14, 6)
        else:
            # For topomaps and other plots
            figsize = (10, 8)
        
        # Create figure with proper background and size
        fig, ax = plt.subplots(figsize=figsize, facecolor=bg_color)
        ax.set_facecolor(bg_color)
        
        if plot_type.lower() == "psd":
            # Create PSD plot using MNE's plotting with better contrast
            psd = raw.compute_psd(fmin=freq_min, fmax=freq_max, method='welch')
            
            # Use MNE's plot function but customize colors
            psd_fig = psd.plot(
                axes=ax, 
                show=False, 
                average=True,
                color='#00D4FF',  # Bright cyan for better contrast
                alpha=0.8,
                spatial_colors=False
            )
            
            # Enhance the plot appearance
            ax.set_title(f"Power Spectral Density ({freq_min}-{freq_max} Hz)", 
                        color='white', fontweight='bold', pad=20)
            ax.set_xlabel("Frequency (Hz)", color='white', fontweight='bold')
            ax.set_ylabel("Power (V²/Hz)", color='white', fontweight='bold')
            
            # Improve grid and ticks
            ax.grid(True, alpha=0.4, color='#888888', linestyle='-', linewidth=0.5)
            ax.tick_params(colors='#CCCCCC', which='both')
            
            # Set background
            ax.set_facecolor('#1a1a1a')
            
        elif plot_type.lower() == "topomap":
            # For topomap, we need to check if we have electrode positions
            try:
                # Try to create a simple topomap if we have enough channels
                if len(raw.ch_names) >= 4:
                    psd = raw.compute_psd(fmin=8, fmax=13, method='welch')
                    psd_avg = psd.get_data().mean(axis=1)
                    
                    # Create a simple grid layout for channels
                    n_channels = len(psd_avg)
                    
                    # Create a simple 2D layout
                    if n_channels <= 4:
                        rows, cols = 2, 2
                    elif n_channels <= 9:
                        rows, cols = 3, 3
                    else:
                        rows = int(np.ceil(np.sqrt(n_channels)))
                        cols = int(np.ceil(n_channels / rows))
                    
                    # Create subplot grid
                    fig.clear()
                    fig, axes = plt.subplots(rows, cols, figsize=figsize, facecolor=bg_color)
                    if rows * cols == 1:
                        axes = [axes]
                    elif rows == 1 or cols == 1:
                        axes = axes.flatten()
                    else:
                        axes = axes.flatten()
                    
                    # Plot each channel's power
                    for i, power in enumerate(psd_avg):
                        if i < len(axes):
                            ax = axes[i]
                            ax.set_facecolor('#1a1a1a')
                            
                            # Create a simple power visualization
                            colors = plt.cm.plasma(power / np.max(psd_avg))
                            circle = plt.Circle((0.5, 0.5), 0.4, color=colors, alpha=0.8)
                            ax.add_patch(circle)
                            
                            ax.set_xlim(0, 1)
                            ax.set_ylim(0, 1)
                            ax.set_title(f"{raw.ch_names[i]}\n{power:.2e}", 
                                       color='white', fontsize=9)
                            ax.set_xticks([])
                            ax.set_yticks([])
                            ax.set_aspect('equal')
                    
                    # Hide unused subplots
                    for i in range(len(psd_avg), len(axes)):
                        axes[i].set_visible(False)
                    
                    fig.suptitle("Alpha Band Power (8-13 Hz)", color='white', fontweight='bold', fontsize=14)
                    
                else:
                    # Fallback for few channels
                    ax.text(0.5, 0.5, f"Alpha Power Visualization\n({len(raw.ch_names)} channels)\n\nNeed electrode positions for\nproper topographic map", 
                           ha='center', va='center', transform=ax.transAxes, 
                           color='white', fontsize=12, fontweight='bold')
                    ax.set_title("Alpha Band Power (8-13 Hz)", color='white', fontweight='bold')
                    ax.axis('off')
                    ax.set_facecolor('#1a1a1a')
                    
            except Exception as e:
                # Simple fallback
                ax.text(0.5, 0.5, f"Topomap Visualization\n\nError: {str(e)}", 
                       ha='center', va='center', transform=ax.transAxes, 
                       color='white', fontsize=12)
                ax.set_title("Alpha Band Power (8-13 Hz)", color='white', fontweight='bold')
                ax.axis('off')
                ax.set_facecolor('#1a1a1a')
            
        elif plot_type.lower() == "raw data":
            # Plot raw time series data using MNE's approach but with better colors
            data_to_plot = raw.get_data()
            times = raw.times
            
            # Show ALL EEG channels instead of limiting to 6
            max_channels = data_to_plot.shape[0]  # Show all available channels
            
            # Generate enough distinct colors for all channels
            if max_channels <= 10:
                # Use predefined colors for small number of channels
                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
                         '#DDA0DD', '#F39C12', '#E74C3C', '#9B59B6', '#1ABC9C']
            else:
                # Generate colors using colormap for many channels
                import matplotlib.cm as cm
                colormap = cm.get_cmap('tab20')  # Good for up to 20 distinct colors
                if max_channels > 20:
                    colormap = cm.get_cmap('viridis')  # Continuous colormap for many channels
                colors = [colormap(i / max_channels) for i in range(max_channels)]
                # Convert to hex strings
                colors = ['#{:02x}{:02x}{:02x}'.format(
                    int(c[0]*255), int(c[1]*255), int(c[2]*255)) for c in colors]

            # Calculate appropriate offset between channels for better visualization
            data_range = np.ptp(data_to_plot)  # Peak-to-peak range of all data
            if data_range > 0:
                # Use a reasonable offset based on the data range
                channel_offset = data_range / max_channels * 1.5
            else:
                # Fallback offset if data is flat
                channel_offset = np.std(data_to_plot) * 3
                if channel_offset == 0:
                    channel_offset = 1e-6  # Very small fallback

            for i in range(max_channels):
                color = colors[i % len(colors)]
                # Apply offset to separate channels visually
                offset = i * channel_offset
                
                # Get channel name from raw object (MNE preserves channel names)
                channel_name = raw.ch_names[i] if i < len(raw.ch_names) else f'Ch {i}'
                
                ax.plot(times, data_to_plot[i] + offset, 
                       label=channel_name,  # Use actual channel name
                       color=color, linewidth=1.0, alpha=0.9)

            ax.set_xlabel("Time (s)", color='white', fontweight='bold')
            ax.set_ylabel("Amplitude (V) + offset", color='white', fontweight='bold')
            ax.set_title(f"Raw EEG Data ({max_channels} channels)", color='white', fontweight='bold', pad=20)
            
            # Improve legend for many channels
            if max_channels <= 8:
                # Show legend for few channels
                legend = ax.legend(loc='upper right', fancybox=True, shadow=True, 
                                 framealpha=0.8, facecolor='#2a2a2a', edgecolor='#666666',
                                 fontsize=8)
                for text in legend.get_texts():
                    text.set_color('white')
            elif max_channels <= 16:
                # Two column legend for medium number of channels
                legend = ax.legend(loc='upper right', fancybox=True, shadow=True, 
                                 framealpha=0.8, facecolor='#2a2a2a', edgecolor='#666666',
                                 fontsize=7, ncol=2)
                for text in legend.get_texts():
                    text.set_color('white')
            else:
                # No legend for many channels, just show count in title
                ax.text(0.98, 0.98, f'{max_channels} channels', 
                       transform=ax.transAxes, ha='right', va='top',
                       color='white', fontsize=10, 
                       bbox=dict(boxstyle='round', facecolor='#2a2a2a', alpha=0.8))

            ax.grid(True, alpha=0.3, color='#666666', linestyle='-', linewidth=0.5)
            ax.set_facecolor('#1a1a1a')
            ax.tick_params(colors='#CCCCCC', which='both')
            
        elif plot_type.lower() == "spectrogram":
            # Restore the simpler spectrogram logic from the previous version
            data_ch0 = raw.get_data()[0]
            fs = raw.info['sfreq']
            
            from scipy import signal
            # Use the same parameters as before - this is the key difference
            f, t, Sxx = signal.spectrogram(data_ch0, fs)
            
            # Use the original approach without extra enhancements
            im = ax.pcolormesh(t, f, 10 * np.log10(Sxx), cmap='viridis')
            ax.set_ylabel('Frequency [Hz]', color='white')
            ax.set_xlabel('Time [s]', color='white')
            ax.set_title('Spectrogram (Channel 0)', color='white')
            
            # Simple colorbar like in the original
            cbar = fig.colorbar(im, ax=ax)
            cbar.set_label('Power (dB)', color='white')
            cbar.ax.yaxis.set_tick_params(color='white')
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
            
            # Keep the original background and tick settings
            ax.set_facecolor(bg_color)
            ax.tick_params(colors='white')
        
        # Set tick colors and improve overall appearance (except for spectrogram)
        if plot_type.lower() != "spectrogram":
            ax.tick_params(colors='#CCCCCC', which='both', labelsize=10)
        
        # Ensure tight layout
        plt.tight_layout(pad=2.0)
        
        # Convert plot to base64 string with high quality
        buffer = BytesIO()
        fig.savefig(buffer, format='png', 
                   facecolor=bg_color, 
                   edgecolor='none', 
                   bbox_inches='tight',
                   dpi=200,  # High DPI for quality
                   pad_inches=0.2)
        buffer.seek(0)
        plot_data = base64.b64encode(buffer.read()).decode()
        buffer.close()
        
        plt.close(fig)
        
        # Reset matplotlib settings to defaults
        matplotlib.rcParams.update(matplotlib.rcParamsDefault)
        
        return {
            "success": True,
            "plot_type": plot_type,
            "plot_data": plot_data,
            "freq_range": [freq_min, freq_max]
        }
        
    except Exception as e:
        # Reset matplotlib settings on error too
        try:
            matplotlib.rcParams.update(matplotlib.rcParamsDefault)
        except:
            pass
        return {
            "success": False,
            "error": str(e)
        }
