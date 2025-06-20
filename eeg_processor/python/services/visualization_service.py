import logging
from typing import Any, Dict, Optional

from ..visualizers.brain_map_viz import BrainMapVisualizer
from ..visualizers.eeg_viz import MultiSignalVisualizer


class VisualizationService:
    """
    Service for managing visualization components.

    This service handles all visualization operations including EEG waveforms
    and brain maps.
    """

    def __init__(self) -> None:
        """Initialize the visualization service."""
        self.eeg_visualizer: Optional[MultiSignalVisualizer] = None
        self.brain_map_visualizer: Optional[BrainMapVisualizer] = None

    def create_eeg_visualizer(self, collector: Any, processor: Any) -> bool:
        """
        Create EEG visualizer.

        Args:
            collector: EEG collector instance
            processor: Signal processor instance

        Returns:
            True if visualizer was created successfully
        """
        try:
            # CACHE MANAGEMENT: Check if we need to clear cache due to board/preset change
            should_clear_cache = False

            if self.eeg_visualizer is not None and hasattr(
                self.eeg_visualizer, "collector"
            ):

                old_collector = self.eeg_visualizer.collector
                old_preset = getattr(old_collector, "preset", None)
                old_board_id = getattr(old_collector, "board_id", None)

                new_preset = getattr(collector, "preset", None)
                new_board_id = getattr(collector, "board_id", None)

                # Clear cache if board or preset changed
                if old_preset != new_preset or old_board_id != new_board_id:
                    should_clear_cache = True
                    logging.info(
                        f"Board/preset changed: {old_board_id}/{old_preset} -> {new_board_id}/{new_preset}"
                    )

            # Clear cache if needed
            if should_clear_cache:
                from ..visualizers.eeg_viz import MultiSignalVisualizer

                MultiSignalVisualizer._clear_cache()
                logging.info("Cleared visualizer cache due to board/preset change")

            # CACHING: Don't destroy existing visualizer if same collector AND same preset
            if (
                self.eeg_visualizer is not None
                and hasattr(self.eeg_visualizer, "collector")
                and self.eeg_visualizer.collector == collector
            ):

                # Same collector, reuse existing visualizer but create new window
                logging.info("Reusing existing visualizer for same collector")
                if hasattr(self.eeg_visualizer, "main_widget"):
                    self.eeg_visualizer.main_widget.show()
                return True

            # Different collector or no existing visualizer
            from ..visualizers.eeg_viz import MultiSignalVisualizer

            self.eeg_visualizer = MultiSignalVisualizer(collector, processor)
            self.visualization_active = True
            logging.info("EEG visualizer created successfully")
            return True
        except Exception as e:
            logging.error(f"Error creating EEG visualizer: {e}")
            return False

    def create_brain_map_visualizer(self, collector: Any, processor: Any) -> bool:
        """
        Create a brain map visualizer.

        Args:
            collector: The data collector object
            processor: The signal processor object

        Returns:
            True if visualizer was created successfully, False otherwise
        """
        try:
            # Handle case where processor is None but we need one
            if processor is None:
                try:
                    from ..processors.signal_processor import SignalProcessor

                    # Try to create a basic processor if possible
                    if (
                        hasattr(collector, "sampling_rate")
                        and collector.sampling_rate > 0
                    ):
                        processor = SignalProcessor(collector.sampling_rate)
                        logging.info(
                            f"Created fallback signal processor with sampling rate {collector.sampling_rate}Hz"
                        )
                    else:
                        logging.warning(
                            "Cannot create fallback processor: no sampling rate available"
                        )
                        return False
                except Exception as e:
                    logging.error(f"Could not create processor for brain map: {e}")
                    return False

            # Create the brain map visualizer with our prepared processor
            self.brain_map_visualizer = BrainMapVisualizer(collector, processor)
            return True
        except Exception as e:
            logging.error(f"Brain map visualizer creation error: {e}")
            return False

    def start_eeg_visualization(self) -> bool:
        """
        Start the EEG visualization.

        Returns:
            True if visualization started successfully, False otherwise
        """
        if not self.eeg_visualizer:
            return False

        try:
            self.eeg_visualizer.start()
            return True
        except Exception as e:
            logging.error(f"EEG visualization start error: {e}")
            return False

    def stop_eeg_visualization(self) -> bool:
        """
        Stop EEG visualization - now preserves cache.

        Returns:
            True if visualization was stopped successfully
        """
        try:
            if self.eeg_visualizer:
                # Just stop the timer, don't destroy the visualizer
                self.eeg_visualizer.stop()

                # Hide the window instead of destroying it
                if hasattr(self.eeg_visualizer, "main_widget"):
                    self.eeg_visualizer.main_widget.hide()

                self.visualization_active = False
                logging.info("EEG visualization stopped (cached)")
                return True
            return False
        except Exception as e:
            logging.error(f"Error stopping EEG visualization: {e}")
            return False

    def destroy_eeg_visualizer(self) -> bool:
        """
        Completely destroy EEG visualizer and clear cache.
        Called when collector disconnects.

        Returns:
            True if visualizer was destroyed successfully
        """
        try:
            if self.eeg_visualizer:
                # Properly cleanup for disconnect (this clears cache)
                self.eeg_visualizer.cleanup_for_disconnect()
                self.eeg_visualizer = None

                self.visualization_active = False
                logging.info("EEG visualizer destroyed and cache cleared")
                return True
            return False
        except Exception as e:
            logging.error(f"Error destroying EEG visualizer: {e}")
            return False

    def start_brain_map_visualization(self) -> bool:
        """
        Start the brain map visualization.

        Returns:
            True if visualization started successfully, False otherwise
        """
        if not self.brain_map_visualizer:
            return False

        try:
            self.brain_map_visualizer.start()
            return True
        except Exception as e:
            logging.error(f"Brain map visualization start error: {e}")
            return False

    def stop_brain_map_visualization(self) -> bool:
        """
        Stop the brain map visualization and close the window.

        Returns:
            True if visualization stopped successfully, False otherwise
        """
        if not self.brain_map_visualizer:
            return False

        try:
            # Stop the timer and close the window
            self.brain_map_visualizer.close()
            return True
        except Exception as e:
            logging.error(f"Brain map visualization stop error: {e}")
            return False

    def visualization_visible(self) -> bool:
        """
        Check if EEG visualization is currently visible.

        Returns:
            True if visualization is visible, False otherwise
        """
        return self.eeg_visualizer is not None and self.eeg_visualizer.is_visible()

    def visualization_closed(self) -> bool:
        """
        Check if visualization window is closed.

        Returns:
            True if visualization window is closed or doesn't exist
        """
        if not self.eeg_visualizer:
            return True

        try:
            # Check if window exists and is visible
            if hasattr(self.eeg_visualizer, "main_widget"):
                return not self.eeg_visualizer.main_widget.isVisible()
            return True
        except:
            return True

    def brain_map_visible(self) -> bool:
        """
        Check if brain map visualization is currently visible.

        Returns:
            True if visualization is visible, False otherwise
        """
        return (
            self.brain_map_visualizer is not None
            and self.brain_map_visualizer.is_visible()
        )

    def brain_map_closed(self) -> bool:
        """
        Check if brain map visualization was closed by user.

        Returns:
            True if visualization was closed, False otherwise
        """
        return (
            self.brain_map_visualizer is not None
            and hasattr(self.brain_map_visualizer, "visualization_closed")
            and self.brain_map_visualizer.visualization_closed()
        )

    def set_bandpass_filter(
        self, enabled: bool, low_cutoff: float, high_cutoff: float
    ) -> bool:
        """
        Configure bandpass filter settings for visualization.

        Args:
            enabled: Whether the filter is enabled
            low_cutoff: Low cutoff frequency in Hz
            high_cutoff: High cutoff frequency in Hz

        Returns:
            True if settings were applied successfully, False otherwise
        """
        success = True

        # Store settings for internal use (e.g., MNE notifications)
        self.bandpass_enabled = enabled
        self.bandpass_low = low_cutoff
        self.bandpass_high = high_cutoff

        # Note: Visualizers now get filtered data from DataAccessService
        # No need to configure filters on individual visualizers
        logging.info(
            f"Filter settings stored: bandpass {enabled} ({low_cutoff}-{high_cutoff}Hz)"
        )

        return success

    def set_notch_filter(self, enabled: bool, frequency: float = 50.0) -> bool:
        """
        Configure notch filter settings for visualization.

        Args:
            enabled: Whether the filter is enabled
            frequency: Notch frequency in Hz

        Returns:
            True if settings were applied successfully, False otherwise
        """
        success = True

        # Store settings for internal use (e.g., MNE notifications)
        self.notch_enabled = enabled
        self.notch_freq = frequency

        # Note: Visualizers now get filtered data from DataAccessService
        # No need to configure filters on individual visualizers
        logging.info(f"Filter settings stored: notch {enabled} ({frequency}Hz)")

        return success

    def set_detrend(self, enabled: bool) -> bool:
        """
        Configure detrend settings for visualization.

        Args:
            enabled: Whether detrending is enabled

        Returns:
            True if settings were applied successfully, False otherwise
        """
        success = True

        # Store settings for internal use (e.g., MNE notifications)
        self.detrend_enabled = enabled

        # Note: Visualizers now get filtered data from DataAccessService
        # No need to configure filters on individual visualizers
        logging.info(f"Filter settings stored: detrend {enabled}")

        return success

    def update_plots(self) -> bool:
        """
        Update the visualization plots.

        Returns:
            True if plots were updated successfully, False otherwise
        """
        if not self.eeg_visualizer:
            return False

        try:
            self.eeg_visualizer.update_plots()
            return True
        except Exception as e:
            logging.error(f"Updating plots error: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up visualization resources."""
        try:
            if self.eeg_visualizer:
                self.eeg_visualizer.stop()
                self.eeg_visualizer = None

            if self.brain_map_visualizer:
                if hasattr(self.brain_map_visualizer, "close"):
                    self.brain_map_visualizer.close()
                self.brain_map_visualizer = None
        except Exception as e:
            logging.error(f"Visualization cleanup error: {e}")

    def are_filters_applied(self) -> bool:
        """Check if filters are currently applied to visualizations."""
        return (
            hasattr(self, "bandpass_enabled")
            and self.bandpass_enabled
            or hasattr(self, "notch_enabled")
            and self.notch_enabled
            or hasattr(self, "detrend_enabled")
            and self.detrend_enabled
        )

    def get_filter_settings(self) -> Dict[str, Any]:
        """Get current filter settings."""
        return {
            "bandpass": {
                "enabled": getattr(self, "bandpass_enabled", False),
                "low": getattr(self, "bandpass_low", 1.0),
                "high": getattr(self, "bandpass_high", 50.0),
            },
            "notch": {
                "enabled": getattr(self, "notch_enabled", False),
                "frequency": getattr(self, "notch_freq", 50.0),
            },
            "detrend": getattr(self, "detrend_enabled", False),
        }
