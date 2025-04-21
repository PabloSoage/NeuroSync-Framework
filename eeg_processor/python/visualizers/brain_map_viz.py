import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
import sys
import os

# Fix imports to work both when imported and when run directly
try:
    # When imported as part of the package
    from ..collectors.eeg_collector import EEGCollector
    from ..processors.signal_processor import SignalProcessor
except ImportError:
    # When run directly, use absolute imports
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from collectors.eeg_collector import EEGCollector
    from processors.signal_processor import SignalProcessor

import pyqtgraph as pg
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QFont, QColor, QPainter, QPainterPath, QPen, QBrush


class BrainMapVisualizer:
    """
    Brain topographic visualization for EEG signal quality.
    
    Displays electrode positions on a 2D brain map and 
    represents signal quality with color indicators.
    """

    def __init__(self, collector: EEGCollector, processor: SignalProcessor):
        """
        Initialize the brain map visualizer.

        Args:
            collector: EEG data collector
            processor: Signal processor
        """
        self.collector = collector
        self.processor = processor
        
        # Debug checks for collector and processor
        if self.collector is None:
            logging.error("Collector is None!")
        else:
            logging.info(f"Collector methods: {dir(self.collector)}")
        
        if self.processor is None:
            logging.error("Processor is None!")
        else:
            logging.info(f"Processor methods: {dir(self.processor)}")
        
        # Check specifically for the required methods
        has_get_data = hasattr(self.collector, 'get_data')
        has_quality_method = hasattr(self.processor, 'get_all_channels_quality')
        logging.info(f"Collector has get_data: {has_get_data}")
        logging.info(f"Processor has get_all_channels_quality: {has_quality_method}")
        
        # Aumentar la frecuencia de actualización para que sea más rápido que el EEGVisualizer
        self.update_speed_ms = 100  # Más rápido que antes (200ms)
        
        # Indicadores para depuración
        self.update_count = 0
        self.last_quality_values = {}
        
        self.timer = None
        
        # Add window size to match EEGVisualizer
        self.window_size = 4  # Display 4 seconds of data like EEGVisualizer
        self.num_points = int(self.window_size * self.collector.sampling_rate)
        
        # Store EEG channels directly like EEGVisualizer does
        self.eeg_channels = collector.get_eeg_channels()
        
        # Processing options - MAKE EXACTLY THE SAME as EEGVisualizer
        self.apply_bandpass = False  # Changed from True to False to match EEGVisualizer
        self.bandpass_low = 1.0
        self.bandpass_high = 30.0
        self.apply_notch = True
        self.apply_detrend = True
        
        # Create visualization window
        self.setup_ui()
        
        # Identify electrode positions
        self.identify_electrode_positions()
        
        logging.info("Brain map visualizer initialized")
        
    def setup_ui(self):
        """Set up the user interface."""
        # Create window
        self.win = pg.GraphicsLayoutWidget()
        self.win.setWindowTitle("EEG Signal Quality Map")
        self.win.resize(800, 800)
        
        # Set up close event handler to detect when window is closed
        self.win.closeEvent = self.handle_close_event
        
        # Create a single plot item
        self.plot = pg.PlotItem()
        self.win.addItem(self.plot)
        self.plot.hideAxis('left')
        self.plot.hideAxis('bottom')
        self.plot.setAspectLocked(True)
        self.plot.setTitle("EEG Signal Quality by Electrode", size="14pt")
        self.plot.setRange(xRange=(-1.4, 1.4), yRange=(-1.4, 1.4))
        
        # Create view
        self.view = self.plot.getViewBox()
        
        # For brain regions
        self.region_items = []
        
        # For electrodes
        self.scatter = pg.ScatterPlotItem()
        self.plot.addItem(self.scatter)
        
        # For electrode labels
        self.labels = []
        
        # Draw brain outline first (bottom layer)
        self.draw_brain_outlines()
        
        # Draw quality legend
        self.add_quality_legend()
        
    def handle_close_event(self, event):
        """Handle window close event to properly stop updates when closed."""
        self.stop()  # Stop the timer
        self.was_closed = True  # Flag to track if window was closed by user
        logging.info("Brain map visualization window closed by user")
        event.accept()
        
    def add_quality_legend(self):
        """Add a legend for signal quality."""
        # Create legend in top right corner
        legend_rect = pg.QtWidgets.QGraphicsRectItem(0.6, -1.2, 0.7, 0.5)
        legend_rect.setBrush(pg.mkBrush(30, 30, 30, 180))  # Semi-transparent dark background
        legend_rect.setPen(pg.mkPen(200, 200, 200, 150))   # Light border
        self.view.addItem(legend_rect)
        
        # Add title
        legend_title = pg.TextItem("Signal Quality", anchor=(0, 0))
        legend_title.setPos(0.7, -1.1)
        legend_title.setColor(QColor(255, 255, 255))
        font = QFont()
        font.setBold(True)
        legend_title.setFont(font)
        self.view.addItem(legend_title)
        
        # Match EEGVisualizer colors exactly (with five levels)
        quality_indicators = [
            {"label": "Excellent", "color": (0, 128, 0)},      # Dark green
            {"label": "Good", "color": (144, 238, 144)},       # Light green
            {"label": "Fair", "color": (255, 255, 0)},         # Yellow
            {"label": "Poor", "color": (255, 165, 0)},         # Orange
            {"label": "Bad", "color": (255, 0, 0)}             # Red
        ]
        
        # Add dots and labels
        for i, indicator in enumerate(quality_indicators):
            # Add color dot
            dot = pg.ScatterPlotItem()
            dot_y = -1.1 + (i * 0.15)  # Adjusted spacing
            dot.addPoints([{'pos': (0.75, dot_y), 'size': 12, 'brush': pg.mkBrush(indicator["color"])}])
            self.view.addItem(dot)
            
            # Add label
            text = pg.TextItem(indicator["label"], anchor=(0, 0.5))
            text.setPos(0.85, dot_y)
            text.setColor(QColor(255, 255, 255))
            self.view.addItem(text)
    
    def draw_brain_outlines(self):
        """Draw head and brain region outlines."""
        # Create a clean head outline (circle)
        head_circle = pg.QtWidgets.QGraphicsEllipseItem(-1, -1, 2, 2)
        head_circle.setPen(pg.mkPen(QColor(150, 150, 150), width=2))
        head_circle.setBrush(pg.mkBrush(QColor(70, 70, 70, 40)))  # Very transparent
        self.view.addItem(head_circle)
        
        # Draw centerlines (cross)
        center_line_v = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen(QColor(150, 150, 150, 100), style=Qt.DashLine))
        center_line_h = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen(QColor(150, 150, 150, 100), style=Qt.DashLine))
        self.plot.addItem(center_line_v)
        self.plot.addItem(center_line_h)
        
        # Draw a nose marker
        nose_coords = [QPointF(0, 1), QPointF(0, 1.15), QPointF(0, 1)]
        nose_item = self.create_region_item(nose_coords, QColor(150, 150, 150, 150), QColor(150, 150, 150))
        self.view.addItem(nose_item)
        
        # Create brain regions (slightly transparent)
        self.create_brain_regions()
        
        # Add orientation labels
        self.add_orientation_label("Front", 0, 1.25)
        self.add_orientation_label("Back", 0, -1.25)
        self.add_orientation_label("Left", -1.25, 0)
        self.add_orientation_label("Right", 1.25, 0)
        
    def create_brain_regions(self):
        """Create the different brain regions with appropriate coloring."""
        # Define major regions - each with a list of points to define the shape
        
        # Frontal lobe (blue)
        frontal_region = [
            (-0.5, 0.87), (-0.3, 0.95), (0, 1), (0.3, 0.95), (0.5, 0.87),
            (0.7, 0.7), (0.85, 0.4), (0.85, 0.2), (0, 0.2), (-0.85, 0.2),
            (-0.85, 0.4), (-0.7, 0.7)
        ]
        frontal_item = self.create_region_item(frontal_region, QColor(100, 140, 220, 80), QColor(140, 180, 255, 100))
        self.view.addItem(frontal_item)
        self.region_items.append(frontal_item)
        
        # Central region (green)
        central_region = [
            (-0.85, 0.2), (0, 0.2), (0.85, 0.2), 
            (0.85, -0.2), (0, -0.2), (-0.85, -0.2)
        ]
        central_item = self.create_region_item(central_region, QColor(100, 200, 120, 80), QColor(140, 220, 160, 100))
        self.view.addItem(central_item)
        self.region_items.append(central_item)
        
        # Parietal lobe (yellow)
        parietal_region = [
            (-0.85, -0.2), (0, -0.2), (0.85, -0.2),
            (0.7, -0.6), (0, -0.7), (-0.7, -0.6)
        ]
        parietal_item = self.create_region_item(parietal_region, QColor(230, 200, 100, 80), QColor(250, 220, 140, 100))
        self.view.addItem(parietal_item)
        self.region_items.append(parietal_item)
        
        # Occipital lobe (pink/purple)
        occipital_region = [
            (-0.7, -0.6), (0, -0.7), (0.7, -0.6),
            (0.3, -0.95), (0, -1), (-0.3, -0.95)
        ]
        occipital_item = self.create_region_item(occipital_region, QColor(200, 120, 200, 80), QColor(230, 150, 230, 100))
        self.view.addItem(occipital_item)
        self.region_items.append(occipital_item)
        
    def create_region_item(self, points, fill_color, border_color):
        """Create a QGraphicsPathItem for a brain region."""
        # Create a path for the region
        path = QPainterPath()
        
        # Convert points to QPointF objects for floating point precision
        qpoints = []
        for point in points:
            if isinstance(point, tuple):
                qpoints.append(QPointF(point[0], point[1]))
            else:
                qpoints.append(QPointF(point.x(), point.y()))
                
        # Start path
        if len(qpoints) > 0:
            path.moveTo(qpoints[0])
            for point in qpoints[1:]:
                path.lineTo(point)
            path.closeSubpath()
        
        # Create path item
        item = pg.QtWidgets.QGraphicsPathItem(path)
        item.setBrush(pg.mkBrush(fill_color))
        item.setPen(pg.mkPen(border_color, width=1.5))
        
        return item
        
    def add_orientation_label(self, text, x, y):
        """Add an orientation label at the specified position."""
        label = pg.TextItem(text, anchor=(0.5, 0.5))
        label.setPos(x, y)
        label.setColor(QColor(200, 200, 200))
        self.view.addItem(label)
        
    def identify_electrode_positions(self):
        """Identify electrode positions based on channel names from the collector."""
        # Create standard electrode positions based on international 10-20/10-10 system
        self.standard_positions = self.create_standard_positions()
        
        self.electrode_positions = {}
        self.electrode_quality = {}
        self.electrode_regions = {}
        
        # Define brain regions by position ranges for color coding
        region_ranges = {
            "frontal": lambda x, y: y >= 0.2,  # Front (blue)
            "central": lambda x, y: y < 0.2 and y > -0.2,  # Middle (green)
            "parietal": lambda x, y: y <= -0.2 and y > -0.6,  # Lower middle (yellow)
            "occipital": lambda x, y: y <= -0.6,  # Bottom (pink/purple)
        }
        
        try:
            # Debug logging to trace the execution flow
            logging.info("Starting electrode position identification...")
            
            # Check if the collector has EEG channel info
            has_eeg_names = hasattr(self.collector, 'eeg_names') and self.collector.eeg_names
            has_eeg_channels = hasattr(self.collector, 'eeg_channels') and self.collector.eeg_channels
            
            logging.info(f"Collector has eeg_names: {has_eeg_names}, has_eeg_channels: {has_eeg_channels}")
            
            # Get channel names if available
            if has_eeg_names:
                logging.info(f"EEG names from collector: {self.collector.eeg_names}")
                # Create positions for each named electrode
                for i, name in enumerate(self.collector.eeg_names):
                    if not name or not isinstance(name, str):
                        continue
                        
                    name = name.strip().upper()  # Normalize name
                    logging.info(f"Processing electrode: {name}")
                    
                    # Try exact match with standard positions
                    if name in self.standard_positions:
                        pos = self.standard_positions[name]
                        self.electrode_positions[name] = pos
                        self.electrode_quality[name] = 0.0  # CAMBIO: Changed from 0.5 to 0.0 (worst quality) to match EEGVisualizer
                        logging.info(f"Found standard position for {name}: {pos}")
                        
                        # Determine region based on y-coordinate
                        for region, check_func in region_ranges.items():
                            if check_func(pos[0], pos[1]):
                                self.electrode_regions[name] = region
                                break
                        else:
                            self.electrode_regions[name] = "other"
                    else:
                        # Try to find closest match if exact match fails
                        logging.debug(f"No exact position match for {name}, trying approximate matching...")
                        matched_name = self._find_best_electrode_match(name)
                        if matched_name:
                            pos = self.standard_positions[matched_name]
                            self.electrode_positions[name] = pos
                            self.electrode_quality[name] = 0.0  # CAMBIO: Changed from 0.5 to 0.0
                            logging.info(f"Found approximate match {matched_name} for {name}: {pos}")
                            
                            # Determine region based on y-coordinate
                            for region, check_func in region_ranges.items():
                                if check_func(pos[0], pos[1]):
                                    self.electrode_regions[name] = region
                                    break
                            else:
                                self.electrode_regions[name] = "other"
                        else:
                            # No match found - use circular arrangement
                            angle = 2 * np.pi * i / max(len(self.collector.eeg_names), 1)
                            x = 0.7 * np.cos(angle)
                            y = 0.7 * np.sin(angle)
                            self.electrode_positions[name] = (x, y)
                            self.electrode_quality[name] = 0.0  # CAMBIO: Changed from 0.5 to 0.0
                            logging.info(f"Using circular position for {name}: ({x:.2f}, {y:.2f})")
            else:
                # No named channels - create default positions
                logging.info("No channel names available, creating default positions")
                self._create_default_positions()
                
            # If we didn't identify any positions, use defaults
            if not self.electrode_positions:
                logging.warning("No electrode positions were identified, using defaults")
                self._create_default_positions()
                
            # Final logging of the results
            logging.info(f"Identified {len(self.electrode_positions)} electrode positions")
            logging.info(f"Electrode positions: {self.electrode_positions}")
            
            # Force an initial update of the display after position identification
            self.update_electrode_display()
            
        except Exception as e:
            logging.error(f"Error identifying electrode positions: {e}", exc_info=True)
            # Create default positions as a fallback
            self._create_default_positions()
    
    def create_standard_positions(self):
        """Create standardized electrode positions based on the 10-20/10-10 systems."""
        # Define positions matching the reference image layout
        positions = {
            # Prefrontal (Fp) - top row
            "FP1": (-0.25, 0.95), "FPZ": (0, 0.95), "FP2": (0.25, 0.95),
            
            # Anterior-Frontal (AF) - row 2
            "AF7": (-0.5, 0.8), "AF3": (-0.25, 0.8), "AFZ": (0, 0.8), 
            "AF4": (0.25, 0.8), "AF8": (0.5, 0.8),
            
            # Frontal (F) - row 3
            "F9": (-0.85, 0.6), "F7": (-0.7, 0.6), "F5": (-0.5, 0.6), "F3": (-0.3, 0.6), 
            "F1": (-0.15, 0.6), "FZ": (0, 0.6), "F2": (0.15, 0.6), "F4": (0.3, 0.6),
            "F6": (0.5, 0.6), "F8": (0.7, 0.6), "F10": (0.85, 0.6),
            
            # Fronto-central (FC) - row 4
            "FT9": (-0.9, 0.4), "FT7": (-0.75, 0.4), "FC5": (-0.55, 0.4), "FC3": (-0.35, 0.4),
            "FC1": (-0.18, 0.4), "FCZ": (0, 0.4), "FC2": (0.18, 0.4), "FC4": (0.35, 0.4),
            "FC6": (0.55, 0.4), "FT8": (0.75, 0.4), "FT10": (0.9, 0.4),
            
            # Central (C) - row 5 (middle row)
            "T7": (-0.85, 0), "C5": (-0.6, 0), "C3": (-0.4, 0), "C1": (-0.2, 0),
            "CZ": (0, 0), "C2": (0.2, 0), "C4": (0.4, 0), "C6": (0.6, 0), "T8": (0.85, 0),
            
            # Centro-parietal (CP) - row 6
            "TP9": (-0.9, -0.4), "TP7": (-0.75, -0.4), "CP5": (-0.55, -0.4), "CP3": (-0.35, -0.4),
            "CP1": (-0.18, -0.4), "CPZ": (0, -0.4), "CP2": (0.18, -0.4), "CP4": (0.35, -0.4),
            "CP6": (0.55, -0.4), "TP8": (0.75, -0.4), "TP10": (0.9, -0.4),
            
            # Parietal (P) - row 7
            "P9": (-0.85, -0.6), "P7": (-0.7, -0.6), "P5": (-0.5, -0.6), "P3": (-0.3, -0.6),
            "P1": (-0.15, -0.6), "PZ": (0, -0.6), "P2": (0.15, -0.6), "P4": (0.3, -0.6),
            "P6": (0.5, -0.6), "P8": (0.7, -0.6), "P10": (0.85, -0.6),
            
            # Parieto-occipital (PO) - row 8
            "PO7": (-0.5, -0.8), "PO3": (-0.25, -0.8), "POZ": (0, -0.8), 
            "PO4": (0.25, -0.8), "PO8": (0.5, -0.8),
            
            # Occipital (O) - bottom row
            "O1": (-0.25, -0.95), "OZ": (0, -0.95), "O2": (0.25, -0.95),
            
            # Reference landmarks
            "NZ": (0, 1.1), # Nasion
            "IZ": (0, -1.1), # Inion
            "LPA": (-1.1, 0), "RPA": (1.1, 0) # Pre-auricular points
        }
        
        # Add aliases for compatibility with older naming conventions
        aliases = {
            "T3": "T7", "T4": "T8", "T5": "P7", "T6": "P8",
            "A1": "LPA", "A2": "RPA", "M1": "LPA", "M2": "RPA",
            "FP1": "FP1", "FPZ": "FPZ", "FP2": "FP2" # Add mixed case variations
        }
        
        # Add aliases to position map
        for alias, standard in aliases.items():
            if standard in positions:
                positions[alias] = positions[standard]
        
        # Handle common g.tec channel names
        for i in range(1, 9):
            positions[f"CH{i}"] = positions.get(self._map_gtec_channel(i), (0, 0))
        
        return positions
    
    def _map_gtec_channel(self, channel_num):
        """Map g.tec channel numbers to standard positions."""
        # Common mapping for g.tec Unicorn
        mapping = {
            1: "FP1", 2: "FP2", 3: "F3", 4: "F4",
            5: "C3", 6: "C4", 7: "P3", 8: "P4"
        }
        return mapping.get(channel_num, f"CH{channel_num}")
    
    def _find_best_electrode_match(self, name: str) -> str:
        """
        Find the best match for an electrode name in the standard positions.
        
        Args:
            name: Electrode name to match
            
        Returns:
            Matched standard name or empty string if no match found
        """
        name = name.upper()  # Ensure uppercase for comparison
        
        # Direct match
        if name in self.standard_positions:
            return name
        
        # Check for common aliases like "Ch1" -> "FP1"
        if name.startswith('CH'):
            try:
                ch_num = int(name[2:])
                return self._map_gtec_channel(ch_num)
            except:
                pass
        
        # Direct match without considering case
        for std_name in self.standard_positions:
            if std_name.upper() == name:
                return std_name
        
        # Partial match - look for name fragments
        for std_name in self.standard_positions:
            if name in std_name.upper() or std_name.upper() in name:
                return std_name
        
        # Look for position patterns like "F3" in other names
        for letter in ['F', 'C', 'P', 'O', 'T']:
            for number in range(1, 11):
                pattern = f"{letter}{number}"
                if pattern in name:
                    if pattern in self.standard_positions:
                        return pattern
        
        return ""
        
    def start(self):
        """Start the visualizer."""
        try:
            # Make sure we have at least some electrode positions
            if not self.electrode_positions:
                logging.warning("No electrode positions detected, creating defaults")
                self._create_default_positions()
            
            # Reset closed flag when starting
            self.was_closed = False
            
            # Show the window
            self.win.show()
            
            # Force an initial update
            self.update_electrode_display()
            
            # Start the update timer with explicit 
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_quality_map)
            self.timer.start(self.update_speed_ms)
            
            # Forzar una actualización inmediata
            # Important: Call this manually to ensure first update works
            QTimer.singleShot(500, self.update_quality_map)
            
            logging.info("Brain map visualizer started with update timer")
        except Exception as e:
            logging.error(f"Error starting brain map visualizer: {e}", exc_info=True)
        
    def stop(self):
        """Stop the visualizer."""
        if self.timer:
            self.timer.stop()
        logging.info("Brain map visualizer stopped")
        
    def is_visible(self):
        """Check if the visualization window is visible."""
        return self.win.isVisible()
        
    def close(self):
        """Close the visualization window."""
        self.stop()
        self.win.close()
        
    def update_quality_map(self):
        """Update the signal quality map."""
        try:
            # Only update if window is visible
            if not self.is_visible():
                return
                
            # Incrementar contador para debug
            self.update_count += 1
            logging.info(f"Brain Map update #{self.update_count} started")
            
            # More detailed diagnostics for missing methods
            if not hasattr(self.collector, 'get_data'):
                logging.error("Collector missing get_data method")
                return
                
            if not hasattr(self.processor, 'get_all_channels_quality'):
                logging.error("Processor missing get_all_channels_quality method")
                # Create a fallback if method is missing
                if hasattr(self.processor, 'get_signal_quality'):
                    logging.info("Using fallback quality calculation with get_signal_quality")
                    # Get the data anyway
                    data, _ = self.collector.get_data(self.num_points)
                    
                    if data.size == 0:
                        logging.warning("No data available for quality calculation")
                        return
                        
                    # Apply filters as normal
                    data_copy = data.copy()
                    if self.apply_bandpass:
                        data_copy = self.processor.bandpass_filter(data_copy, self.bandpass_low, self.bandpass_high, 4)
                    if self.apply_notch:
                        data_copy = self.processor.remove_environmental_noise(data_copy)
                    if self.apply_detrend:
                        data_copy = self.processor.detrend(data_copy)
                    
                    # Calculate qualities manually using get_signal_quality for each channel
                    quality_dict = {}
                    for ch_idx in self.eeg_channels:
                        try:
                            quality = self.processor.get_signal_quality(data_copy, ch_idx)
                            quality_dict[ch_idx] = quality
                        except Exception as channel_error:
                            logging.error(f"Error calculating quality for channel {ch_idx}: {channel_error}")
                            quality_dict[ch_idx] = 0.0
                    
                    # Log calculated values
                    logging.info(f"BrainMap - Manual quality calculation: {quality_dict}")
                    
                    # Update electrode qualities
                    for i, ch_idx in enumerate(self.eeg_channels):
                        if i < len(self.collector.eeg_names):
                            ch_name = self.collector.eeg_names[i].upper()
                            if ch_name in self.electrode_positions:
                                quality = quality_dict.get(ch_idx, 0.0)
                                # Update directly
                                self.electrode_quality[ch_name] = quality
                                logging.info(f"Updated electrode {ch_name} quality to {quality}")
                    
                    # Update display
                    self.update_electrode_display()
                    return
                else:
                    logging.error("No fallback quality calculation method available")
                    return
            
            # Original method if both methods exist
            # Verificar precondiciones
            if not hasattr(self.collector, 'get_data') or not hasattr(self.processor, 'get_all_channels_quality'):
                logging.warning("Collector or processor missing required methods")
                return
                
            # Obtener datos
            data, _ = self.collector.get_data(self.num_points)
            
            if data.size == 0:
                logging.warning("No data available for brain map update")
                return
                
            # Procesar datos exactamente como en EEGVisualizer
            data_copy = data.copy()
            
            if self.apply_bandpass:
                data_copy = self.processor.bandpass_filter(
                    data_copy, self.bandpass_low, self.bandpass_high, 4
                )
            if self.apply_notch:
                data_copy = self.processor.remove_environmental_noise(data_copy)
            if self.apply_detrend:
                data_copy = self.processor.detrend(data_copy)
                
            # Calcular calidad directamente como lo hace EEGVisualizer
            quality_dict = self.processor.get_all_channels_quality(data_copy, self.eeg_channels)
            
            # Mostrar los valores de calidad calculados
            logging.info(f"BrainMap - Calculated quality values: {quality_dict}")
            
            # Actualizar calidades de electrodos directamente
            for i, ch_idx in enumerate(self.eeg_channels):
                if i < len(self.collector.eeg_names):
                    ch_name = self.collector.eeg_names[i].upper()
                    if ch_name in self.electrode_positions:
                        quality = quality_dict.get(ch_idx, 0.0)
                        # Actualizar directamente
                        self.electrode_quality[ch_name] = quality
                        logging.info(f"Updated electrode {ch_name} quality to {quality}")
            
            # Actualizar visualización
            self.update_electrode_display()
            
            # Forzar repintado
            self.plot.update()
            
        except Exception as e:
            logging.error(f"Error in update_quality_map: {e}", exc_info=True)

    def update_electrode_display(self):
        """Update the electrode visualization with quality indicators."""
        try:
            # Clear previous labels
            for label in self.labels:
                self.plot.removeItem(label)
            self.labels = []
            
            # Log current quality values for debugging
            logging.info(f"Current quality values: {self.electrode_quality}")
            
            if not self.electrode_positions:
                logging.warning("No electrode positions to display")
                return
                
            # Define quality colors
            quality_colors = [
                (255, 0, 0),      # Red (bad quality)
                (255, 165, 0),    # Orange (poor quality)
                (255, 255, 0),    # Yellow (fair quality)
                (144, 238, 144),  # Light green (good quality)
                (0, 128, 0)       # Dark green (excellent quality)
            ]
            
            # Prepare data for scatter plot
            positions = []
            brushes = []
            sizes = []
            
            # Process each electrode
            for name, pos in self.electrode_positions.items():
                # Check for valid position
                if not isinstance(pos, tuple) or len(pos) != 2:
                    continue
                    
                positions.append(pos)
                
                # Get quality value directly from electrode_quality
                quality = self.electrode_quality.get(name, 0.0)
                
                # Map quality to color index - exactly like in EEGVisualizer
                color_idx = min(int(quality * len(quality_colors)), len(quality_colors) - 1)
                
                # Log quality and color assignment
                logging.info(f"Electrode {name} quality={quality:.2f}, color_idx={color_idx}")
                
                # Assign size and color
                sizes.append(15)
                brushes.append(pg.mkBrush(quality_colors[color_idx]))
                
                # Create label
                label = pg.TextItem(name, anchor=(0.5, 0.5))
                label.setPos(pos[0], pos[1])
                label.setColor(QColor('white'))
                font = QFont()
                font.setBold(True)
                font.setPointSize(8)
                label.setFont(font)
                self.plot.addItem(label)
                self.labels.append(label)
            
            # Update scatter plot
            if positions:
                scatter_points = []
                for i, pos in enumerate(positions):
                    scatter_points.append({
                        'pos': pos,
                        'size': sizes[i] if i < len(sizes) else 15,
                        'brush': brushes[i] if i < len(brushes) else pg.mkBrush(255, 0, 0)
                    })
                    
                # Clear and add points
                self.scatter.clear()
                self.scatter.addPoints(scatter_points)
                logging.info(f"Updated scatter plot with {len(scatter_points)} points")
            
        except Exception as e:
            logging.error(f"Error in update_electrode_display: {e}", exc_info=True)
    
    def _create_default_positions(self):
        """Create default electrode positions when detection fails."""
        logging.info("Creating default electrode positions")
        # Standard 10-20 positions for common setups
        default_names = ["Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8", 
                         "T3", "C3", "Cz", "C4", "T4", 
                         "T5", "P3", "Pz", "P4", "T6", 
                         "O1", "Oz", "O2"]
        
        # Only use first 8 positions if we don't have many channels
        if hasattr(self.collector, 'eeg_channels') and len(self.collector.eeg_channels) <= 8:
            default_names = default_names[:8]
        
        for i, name in enumerate(default_names):
            if name in self.standard_positions:
                pos = self.standard_positions[name]
                logging.debug(f"Added default position for {name}: {pos}")
            else:
                # Create a circular arrangement if standard position not found
                angle = 2 * np.pi * i / len(default_names)
                pos = (0.7 * np.cos(angle), 0.7 * np.sin(angle))
                logging.debug(f"Created circular position for {name}: {pos}")
                
            self.electrode_positions[name] = pos
            self.electrode_quality[name] = 0.0  # CAMBIO: Changed from 0.5 to 0.0 to match EEGVisualizer
            self.electrode_regions[name] = "other"
    
    # Add methods to configure filters similar to EEGVisualizer
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
