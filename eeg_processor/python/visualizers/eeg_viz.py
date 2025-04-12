import numpy as np
import logging
from typing import List, Optional, Tuple

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from brainflow.data_filter import DataFilter, FilterTypes, DetrendOperations

from ..collectors.eeg_collector import EEGCollector
from ..processors.signal_processor import SignalProcessor


class EEGVisualizer:
    """
    Visualizer for EEG data using PyQtGraph.
    
    This class provides real-time visualization of EEG data with various display options.
    """
    
    def __init__(self, collector: EEGCollector, processor: SignalProcessor):
        """
        Initialize the EEG visualizer.
        
        Args:
            collector: EEG data collector
            processor: Signal processor for data filtering
        """
        self.collector = collector
        self.processor = processor
        self.sampling_rate = collector.sampling_rate
        self.eeg_channels = collector.get_eeg_channels()
        self.num_channels = len(self.eeg_channels)
        self.update_speed_ms = 50
        self.window_size = 4  # Display 4 seconds of data
        self.num_points = int(self.window_size * self.sampling_rate)
        
        # Data for plotting
        self.time_vector = np.linspace(0, self.window_size, self.num_points)
        
        # Processing options
        self.apply_bandpass = False
        self.bandpass_low = 1.0
        self.bandpass_high = 30.0
        self.apply_notch = True
        self.apply_detrend = True
        
        # Setup UI elements
        self.setup_ui()
        
        logging.info("EEG visualizer initialized")
        
    def setup_ui(self):
        """Set up the user interface for the visualizer."""
        self.win = pg.GraphicsLayoutWidget(title="EEG Data Visualization")
        self.win.resize(1000, 600)
        self.win.setWindowTitle('Real-time EEG Visualization')
        
        # Create plots for each EEG channel
        self.plots = []
        self.curves = []
        
        for i in range(self.num_channels):
            plot = self.win.addPlot(row=i, col=0)
            plot.showAxis('left', True)
            plot.setMenuEnabled('left', False)
            
            if i == 0:
                plot.setTitle('EEG Channels')
            else:
                plot.hideAxis('top')
                
            if i == self.num_channels - 1:
                plot.setLabel('bottom', 'Time', 's')
            else:
                plot.hideAxis('bottom')
            
            # Add channel labels
            ch_name = f"Channel {self.eeg_channels[i]}"
            plot.setLabel('left', ch_name)
            
            # Add curve for the data
            curve = plot.plot(pen=pg.mkPen(color=(i * 50 % 255, 255 - i * 30 % 255, i * 20 % 255), width=1))
            self.plots.append(plot)
            self.curves.append(curve)
        
        # Add FFT plot
        self.fft_plot = self.win.addPlot(row=0, col=1, rowspan=self.num_channels//2)
        self.fft_plot.setTitle('Power Spectrum')
        self.fft_plot.setLabel('bottom', 'Frequency', 'Hz')
        self.fft_plot.setLabel('left', 'Power', 'µV²/Hz')
        self.fft_plot.setLogMode(x=False, y=True)  # Log scale for power
        self.fft_curves = []
        
        for i in range(min(self.num_channels, 4)):  # Limit to 4 channels for clarity
            curve = self.fft_plot.plot(pen=pg.mkPen(color=(i * 50 % 255, 255 - i * 30 % 255, i * 20 % 255), width=2))
            self.fft_curves.append(curve)
        
        # Add band power indicator
        self.band_plot = self.win.addPlot(row=self.num_channels//2, col=1, rowspan=self.num_channels//2)
        self.band_plot.setTitle('Band Powers')
        self.band_plot.setLabel('bottom', 'Band')
        self.band_plot.setLabel('left', 'Power', 'dB')
        
        self.bands = ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma']
        self.band_ranges = [(1, 4), (4, 8), (8, 13), (13, 30), (30, 50)]
        self.bar_graph = pg.BarGraphItem(x=range(len(self.bands)), height=[0]*len(self.bands), 
                                         width=0.6, brush='b')
        self.band_plot.addItem(self.bar_graph)
        self.band_plot.setXRange(-0.5, len(self.bands) - 0.5)
        
        # Set axis labels
        ax = self.band_plot.getAxis('bottom')
        ax.setTicks([list(enumerate(self.bands))])
        
        # Show the window
        self.win.show()
        
        # Setup timer for updating the plots
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        
    def start(self):
        """Start updating the visualizer."""
        self.timer.start(self.update_speed_ms)
        logging.info("EEG visualizer started")
        
    def stop(self):
        """Stop updating the visualizer."""
        self.timer.stop()
        logging.info("EEG visualizer stopped")
        
    def update_plots(self):
        """Update all plots with new data."""
        try:
            # Get the latest data
            data, timestamps = self.collector.get_data(self.num_points)
            
            if data.size == 0 or len(self.eeg_channels) == 0:
                return
                
            # Process data for display
            data_to_plot = data.copy()
            
            # Apply pre-processing if needed
            if self.apply_bandpass:
                data_to_plot = self.processor.bandpass_filter(
                    data_to_plot, self.bandpass_low, self.bandpass_high, 4)
            
            if self.apply_notch:
                # Remove 50Hz noise (adjust to 60Hz if needed)
                data_to_plot = self.processor.remove_environmental_noise(data_to_plot)
                
            if self.apply_detrend:
                data_to_plot = self.processor.detrend(data_to_plot)
                
            # Update time series plots
            for i, channel in enumerate(self.eeg_channels):
                if i < len(self.curves):
                    channel_data = data_to_plot[channel][-self.num_points:]
                    if len(channel_data) > 0:
                        self.curves[i].setData(
                            self.time_vector[-len(channel_data):], 
                            channel_data
                        )
            
            # Update FFT plots (for first few channels)
            nfft = DataFilter.get_nearest_power_of_two(self.sampling_rate)
            for i, channel in enumerate(self.eeg_channels):
                if i < len(self.fft_curves):
                    channel_data = data_to_plot[channel][-self.num_points:]
                    if len(channel_data) > 0:
                        psd = DataFilter.get_psd_welch(
                            channel_data, 
                            nfft, 
                            nfft // 2,
                            self.sampling_rate, 
                            WindowOperations.HANNING.value
                        )
                        freq = np.linspace(0, self.sampling_rate / 2, len(psd))
                        self.fft_curves[i].setData(freq, psd)
            
            # Update band powers
            if len(self.eeg_channels) > 0:
                # Use first channel for band powers
                channel = self.eeg_channels[0]
                channel_data = data_to_plot[channel][-self.num_points:]
                if len(channel_data) > 0:
                    powers = []
                    for low, high in self.band_ranges:
                        band_power = self.processor.get_band_power(
                            data_to_plot[[channel]], low, high)[0]
                        powers.append(10 * np.log10(band_power))  # Convert to dB
                    self.bar_graph.setOpts(height=powers)
            
        except Exception as e:
            logging.error(f"Error updating plots: {e}")
    
    def set_bandpass_filter(self, enabled: bool, low_freq: float = 1.0, high_freq: float = 30.0):
        """
        Set bandpass filter parameters.
        
        Args:
            enabled: Whether to enable the bandpass filter
            low_freq: Lower cutoff frequency
            high_freq: Higher cutoff frequency
        """
        self.apply_bandpass = enabled
        self.bandpass_low = low_freq
        self.bandpass_high = high_freq
        
    def set_notch_filter(self, enabled: bool):
        """
        Set notch filter for power line noise.
        
        Args:
            enabled: Whether to enable the notch filter
        """
        self.apply_notch = enabled
        
    def set_detrend(self, enabled: bool):
        """
        Set detrending option.
        
        Args:
            enabled: Whether to enable detrending
        """
        self.apply_detrend = enabled
