import logging
import time
from typing import Dict, Any, Optional, Callable, List, Tuple
import numpy as np

from ...interfaces.mne_interfaces import MNEVisualizerInterface, MNEProcessManagerInterface, MNEResultStorageInterface

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


class MNEVisualizerService(MNEVisualizerInterface):
    """Service for creating MNE visualizations."""
    
    def __init__(
        self, 
        process_manager: MNEProcessManagerInterface,
        result_storage: MNEResultStorageInterface
    ) -> None:
        """Initialize the visualizer service."""
        self.process_manager = process_manager
        self.result_storage = result_storage
        self._completion_callbacks: Dict[str, Callable] = {}
        
        logging.info("MNE visualizer service initialized")
    
    def create_visualization_async(
        self,
        mne_data: Dict[str, Any],
        plot_type: str,
        freq_min: int = 1,
        freq_max: int = 50,
        bg_color: str = "#2b2b2b",
        show_individual_channels: bool = True,
        selected_channels_for_display: Optional[List[int]] = None,
        topomap_freq_range: Optional[Tuple[int, int]] = None,
        callback: Optional[Callable] = None
    ) -> str:
        """Create MNE visualization asynchronously."""
        if not MNE_AVAILABLE:
            raise RuntimeError("MNE package not available")
        
        if not self.process_manager.is_available():
            raise RuntimeError("Process manager not available")
        
        if not mne_data.get("success"):
            raise ValueError("Invalid MNE data provided")
        
        # Generate task ID
        task_id = f"viz_{plot_type}_{int(time.time() * 1000)}"
        
        # Store callback if provided
        if callback:
            self._completion_callbacks[task_id] = callback
        
        # Submit visualization task with specific task ID
        returned_task_id = self.process_manager.submit_task(
            _create_visualization_worker,
            mne_data["raw_data"], mne_data["info"], plot_type, freq_min, freq_max, 
            bg_color, show_individual_channels, selected_channels_for_display, topomap_freq_range,
            task_id=task_id,
            callback=lambda result: self._handle_visualization_complete(task_id, result, callback)
        )
        
        # Ensure the returned task ID matches what we expect
        assert returned_task_id == task_id, f"Task ID mismatch: expected {task_id}, got {returned_task_id}"
        
        logging.info(f"Started MNE visualization task: {task_id}")
        return task_id
    
    def get_visualization_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a visualization task."""
        return self.process_manager.get_task_status(task_id)
    
    def cancel_visualization(self, task_id: str) -> bool:
        """Cancel a visualization task."""
        success = self.process_manager.cancel_task(task_id)
        if success:
            # Clean up callback
            if task_id in self._completion_callbacks:
                del self._completion_callbacks[task_id]
            logging.info(f"Cancelled visualization task: {task_id}")
        return success
    
    def _handle_visualization_complete(self, task_id: str, result: Dict[str, Any], callback: Optional[Callable]) -> None:
        """Handle completion of visualization task."""
        # Store result
        self.result_storage.store_result(task_id, result)
        
        # Call callback if provided
        if callback:
            try:
                callback(task_id, result)
            except Exception as e:
                logging.error(f"Error in visualization callback: {e}")
        
        # Clean up callback
        if task_id in self._completion_callbacks:
            del self._completion_callbacks[task_id]
        
        logging.info(f"Visualization task completed: {task_id}")


def _create_visualization_worker(
    raw_data: np.ndarray,
    info: Any,
    plot_type: str,
    freq_min: int,
    freq_max: int,
    bg_color: str,
    show_individual_channels: bool = True,
    selected_channels_for_display: Optional[List[int]] = None,
    topomap_freq_range: Optional[Tuple[int, int]] = None
) -> Dict[str, Any]:
    """Worker function to create MNE visualizations."""
    try:
        import mne
        import numpy as np
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
        
        # Create Raw object with converted channels
        raw_all_converted = mne.io.RawArray(raw_data, info)
        
        # Apply channel selection for display if specified
        if selected_channels_for_display is not None:
            # Validate channel indices against converted data
            max_converted_channels = len(raw_all_converted.ch_names)
            valid_channels = [ch for ch in selected_channels_for_display if 0 <= ch < max_converted_channels]
            
            if not valid_channels:
                # If no valid channels, use all converted
                raw = raw_all_converted
                display_info = f"all {max_converted_channels} converted channels (invalid selection)"
            else:
                # Create subset with selected channels from converted data
                channel_names_to_pick = [raw_all_converted.ch_names[i] for i in valid_channels]
                raw = raw_all_converted.pick_channels(channel_names_to_pick, ordered=True)
                display_info = f"{len(valid_channels)} of {max_converted_channels} converted channels"
        else:
            # Use all converted channels
            raw = raw_all_converted
            display_info = f"all {len(raw_all_converted.ch_names)} converted channels"
        
        # Calculate figure size based on plot type to maintain aspect ratio
        if plot_type.lower() in ["psd", "spectrogram"]:
            figsize = (12, 7)
        elif plot_type.lower() == "raw data":
            figsize = (14, 6)
        else:
            figsize = (10, 8)
        
        # Create figure with proper background and size
        fig, ax = plt.subplots(figsize=figsize, facecolor=bg_color)
        ax.set_facecolor(bg_color)
        
        if plot_type.lower() == "psd":
            # Create PSD plot with toggle option
            psd = raw.compute_psd(fmin=freq_min, fmax=freq_max, method='welch')
            
            if show_individual_channels:
                # Individual channels mode
                psd_data = psd.get_data()
                freqs = psd.freqs
                
                ax.clear()
                ax.set_facecolor('#1a1a1a')
                
                # Generate distinct colors for each channel
                n_channels = len(raw.ch_names)
                if n_channels <= 10:
                    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
                             '#DDA0DD', '#F39C12', '#E74C3C', '#9B59B6', '#1ABC9C']
                else:
                    import matplotlib.cm as cm
                    colormap = cm.get_cmap('tab20')
                    if n_channels > 20:
                        colormap = cm.get_cmap('viridis')
                    colors = [colormap(i / n_channels) for i in range(n_channels)]
                    colors = ['#{:02x}{:02x}{:02x}'.format(
                        int(c[0]*255), int(c[1]*255), int(c[2]*255)) for c in colors]
                
                # Plot each channel with its own color
                for i, channel_name in enumerate(raw.ch_names):
                    color = colors[i % len(colors)]
                    ax.plot(freqs, psd_data[i], 
                           color=color, 
                           label=channel_name,
                           linewidth=1.5, 
                           alpha=0.8)
                
                ax.set_title(f"Power Spectral Density ({freq_min}-{freq_max} Hz) - {display_info}", 
                            color='white', fontweight='bold', pad=20)
                ax.set_xlabel("Frequency (Hz)", color='white', fontweight='bold')
                ax.set_ylabel("Power (V²/Hz)", color='white', fontweight='bold')
                
                # Handle legend based on channel count
                if n_channels <= 8:
                    legend = ax.legend(loc='upper right', fancybox=True, shadow=True, 
                                     framealpha=0.8, facecolor='#2a2a2a', edgecolor='#666666',
                                     fontsize=8)
                    for text in legend.get_texts():
                        text.set_color('white')
                elif n_channels <= 16:
                    legend = ax.legend(loc='upper right', fancybox=True, shadow=True, 
                                     framealpha=0.8, facecolor='#2a2a2a', edgecolor='#666666',
                                     fontsize=7, ncol=2)
                    for text in legend.get_texts():
                        text.set_color('white')
                else:
                    ax.text(0.98, 0.98, f'{n_channels} channels', 
                           transform=ax.transAxes, ha='right', va='top',
                           color='white', fontsize=10, 
                           bbox=dict(boxstyle='round', facecolor='#2a2a2a', alpha=0.8))
                
                ax.grid(True, alpha=0.4, color='#888888', linestyle='-', linewidth=0.5)
                ax.tick_params(colors='#CCCCCC', which='both')
                
            else:
                # MNE native averaged mode
                psd_fig = psd.plot(
                    axes=ax, 
                    show=False, 
                    average=True,
                    color='#00D4FF',
                    alpha=0.8,
                    spatial_colors=False
                )
                
                ax.set_title(f"Power Spectral Density - Average ({freq_min}-{freq_max} Hz) - {display_info}", 
                            color='white', fontweight='bold', pad=20)
                ax.set_xlabel("Frequency (Hz)", color='white', fontweight='bold')
                ax.set_ylabel("Power (V²/Hz)", color='white', fontweight='bold')
                ax.grid(True, alpha=0.4, color='#888888', linestyle='-', linewidth=0.5)
                ax.tick_params(colors='#CCCCCC', which='both')
                ax.set_facecolor('#1a1a1a')
        
        elif plot_type.lower() == "topomap":
            try:
                n_channels = len(raw.ch_names)
                
                # Get frequency range for topomap
                if topomap_freq_range is not None:
                    topo_freq_min, topo_freq_max = topomap_freq_range
                else:
                    topo_freq_min, topo_freq_max = 8, 13
                
                band_name = _get_band_name(topo_freq_min, topo_freq_max)
                
                if n_channels == 1:
                    # Single channel case
                    psd = raw.compute_psd(fmin=topo_freq_min, fmax=topo_freq_max, method='welch')
                    psd_avg = psd.get_data().mean(axis=1)[0]
                    
                    ax.clear()
                    ax.set_facecolor('#1a1a1a')
                    
                    circle = plt.Circle((0.5, 0.5), 0.3, color=plt.cm.plasma(0.8), alpha=0.8)
                    ax.add_patch(circle)
                    
                    ax.text(0.5, 0.5, f"{raw.ch_names[0]}\n{psd_avg:.2e}", 
                           ha='center', va='center', color='white', fontweight='bold',
                           fontsize=14)
                    
                    ax.set_xlim(0, 1)
                    ax.set_ylim(0, 1)
                    ax.set_title(f"{band_name} Power ({topo_freq_min}-{topo_freq_max} Hz) - {display_info}", 
                               color='white', fontweight='bold', pad=20)
                    ax.set_xticks([])
                    ax.set_yticks([])
                    ax.set_aspect('equal')
                    
                else:
                    # Multiple channels - grid layout
                    psd = raw.compute_psd(fmin=topo_freq_min, fmax=topo_freq_max, method='welch')
                    psd_avg = psd.get_data().mean(axis=1)
                    
                    if n_channels <= 4:
                        rows, cols = 2, 2
                    elif n_channels <= 9:
                        rows, cols = 3, 3
                    elif n_channels <= 16:
                        rows, cols = 4, 4
                    else:
                        rows = int(np.ceil(np.sqrt(n_channels)))
                        cols = int(np.ceil(n_channels / rows))
                    
                    fig.clear()
                    fig, axes = plt.subplots(rows, cols, figsize=figsize, facecolor=bg_color)
                    if rows * cols == 1:
                        axes = [axes]
                    elif rows == 1 or cols == 1:
                        axes = axes.flatten()
                    else:
                        axes = axes.flatten()
                    
                    for i, power in enumerate(psd_avg):
                        if i < len(axes):
                            ax_sub = axes[i]
                            ax_sub.set_facecolor('#1a1a1a')
                            
                            color_intensity = power / np.max(psd_avg) if np.max(psd_avg) > 0 else 0.5
                            colors = plt.cm.plasma(color_intensity)
                            circle = plt.Circle((0.5, 0.5), 0.4, color=colors, alpha=0.8)
                            ax_sub.add_patch(circle)
                            
                            ax_sub.set_xlim(0, 1)
                            ax_sub.set_ylim(0, 1)
                            ax_sub.set_title(f"{raw.ch_names[i]}\n{power:.2e}", 
                                           color='white', fontsize=9)
                            ax_sub.set_xticks([])
                            ax_sub.set_yticks([])
                            ax_sub.set_aspect('equal')
                    
                    for i in range(len(psd_avg), len(axes)):
                        axes[i].set_visible(False)
                    
                    fig.suptitle(f"{band_name} Power ({topo_freq_min}-{topo_freq_max} Hz) - {display_info}", 
                               color='white', fontweight='bold', fontsize=14)
                    
            except Exception as e:
                ax.text(0.5, 0.5, f"Topomap Visualization\n\nError: {str(e)}", 
                       ha='center', va='center', transform=ax.transAxes, 
                       color='white', fontsize=12)
                ax.set_title(f"Band Power Visualization - {display_info}", color='white', fontweight='bold')
                ax.axis('off')
                ax.set_facecolor('#1a1a1a')
            
        elif plot_type.lower() == "raw data":
            # Plot raw time series data
            data_to_plot = raw.get_data()
            times = raw.times
            
            max_channels = data_to_plot.shape[0]
            
            # Generate colors
            if max_channels <= 10:
                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
                         '#DDA0DD', '#F39C12', '#E74C3C', '#9B59B6', '#1ABC9C']
            else:
                import matplotlib.cm as cm
                colormap = cm.get_cmap('tab20')
                if max_channels > 20:
                    colormap = cm.get_cmap('viridis')
                colors = [colormap(i / max_channels) for i in range(max_channels)]
                colors = ['#{:02x}{:02x}{:02x}'.format(
                    int(c[0]*255), int(c[1]*255), int(c[2]*255)) for c in colors]

            # Calculate offset
            data_range = np.ptp(data_to_plot)
            if data_range > 0:
                channel_offset = data_range / max_channels * 1.5
            else:
                channel_offset = np.std(data_to_plot) * 3
                if channel_offset == 0:
                    channel_offset = 1e-6

            for i in range(max_channels):
                color = colors[i % len(colors)]
                offset = i * channel_offset
                channel_name = raw.ch_names[i] if i < len(raw.ch_names) else f'Ch {i}'
                
                ax.plot(times, data_to_plot[i] + offset, 
                       label=channel_name,
                       color=color, linewidth=1.0, alpha=0.9)

            ax.set_xlabel("Time (s)", color='white', fontweight='bold')
            ax.set_ylabel("Amplitude (V) + offset", color='white', fontweight='bold')
            ax.set_title(f"Raw EEG Data - {display_info}", color='white', fontweight='bold', pad=20)
            
            # Handle legend
            if max_channels <= 8:
                legend = ax.legend(loc='upper right', fancybox=True, shadow=True, 
                                 framealpha=0.8, facecolor='#2a2a2a', edgecolor='#666666',
                                 fontsize=8)
                for text in legend.get_texts():
                    text.set_color('white')
            elif max_channels <= 16:
                legend = ax.legend(loc='upper right', fancybox=True, shadow=True, 
                                 framealpha=0.8, facecolor='#2a2a2a', edgecolor='#666666',
                                 fontsize=7, ncol=2)
                for text in legend.get_texts():
                    text.set_color('white')
            else:
                ax.text(0.98, 0.98, f'{max_channels} channels', 
                       transform=ax.transAxes, ha='right', va='top',
                       color='white', fontsize=10, 
                       bbox=dict(boxstyle='round', facecolor='#2a2a2a', alpha=0.8))

            ax.grid(True, alpha=0.3, color='#666666', linestyle='-', linewidth=0.5)
            ax.set_facecolor('#1a1a1a')
            ax.tick_params(colors='#CCCCCC', which='both')
            
        elif plot_type.lower() == "spectrogram":
            # Spectrogram
            data_ch0 = raw.get_data()[0]
            fs = raw.info['sfreq']
            
            from scipy import signal
            f, t, Sxx = signal.spectrogram(data_ch0, fs)
            
            im = ax.pcolormesh(t, f, 10 * np.log10(Sxx), cmap='viridis')
            ax.set_ylabel('Frequency [Hz]', color='white')
            ax.set_xlabel('Time [s]', color='white')
            
            first_channel_name = raw.ch_names[0] if len(raw.ch_names) > 0 else "Channel 0"
            ax.set_title(f'Spectrogram ({first_channel_name}) - {display_info}', color='white')
            
            cbar = fig.colorbar(im, ax=ax)
            cbar.set_label('Power (dB)', color='white')
            cbar.ax.yaxis.set_tick_params(color='white')
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
            
            ax.set_facecolor(bg_color)
            ax.tick_params(colors='white')
        
        # Set tick colors for non-spectrogram plots
        if plot_type.lower() != "spectrogram":
            ax.tick_params(colors='#CCCCCC', which='both', labelsize=10)
        
        # Ensure tight layout
        plt.tight_layout(pad=2.0)
        
        # Convert plot to base64
        buffer = BytesIO()
        fig.savefig(buffer, format='png', 
                   facecolor=bg_color, 
                   edgecolor='none', 
                   bbox_inches='tight',
                   dpi=200,
                   pad_inches=0.2)
        buffer.seek(0)
        plot_data = base64.b64encode(buffer.read()).decode()
        buffer.close()
        
        plt.close(fig)
        
        # Reset matplotlib settings
        matplotlib.rcParams.update(matplotlib.rcParamsDefault)
        
        return {
            "success": True,
            "plot_type": plot_type,
            "plot_data": plot_data,
            "freq_range": [freq_min, freq_max],
            "topomap_freq_range": topomap_freq_range,
            "individual_channels": show_individual_channels,
            "displayed_channels": len(raw.ch_names),
            "display_info": display_info
        }
        
    except Exception as e:
        # Reset matplotlib settings on error
        try:
            matplotlib.rcParams.update(matplotlib.rcParamsDefault)
        except:
            pass
        return {
            "success": False,
            "error": str(e)
        }


def _get_band_name(freq_min: int, freq_max: int) -> str:
    """Get the name of the frequency band based on frequency range."""
    bands = [
        ("Delta", 1, 4),
        ("Theta", 4, 8), 
        ("Alpha", 8, 13),
        ("Beta", 13, 30),
        ("Gamma", 30, 50)
    ]
    
    for band_name, band_min, band_max in bands:
        if freq_min == band_min and freq_max == band_max:
            return band_name
    
    return f"Custom Band"
