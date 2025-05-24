"""
Qt Interaction Adapter module.

This module provides an adapter that bridges between the UI framework (PyQt5) 
and the framework-independent interaction service layer.
"""

from typing import Dict, List, Any, Optional, Tuple, Set, Callable

from PyQt5.QtCore import QMetaObject, Qt, QObject, pyqtSlot, QTimer, QEventLoop
import threading
import logging

class QtInteractionAdapter:
    """
    Adapter for PyQt5 UI components to the interaction service.
    
    This adapter ensures that all UI framework-specific operations 
    are performed in a thread-safe manner and properly isolated from
    the core service layer.
    """
    
    def __init__(self):
        """Initialize the adapter."""
        self.app_coordinator = None
        self.ui_manager = None
        self.logging_manager = None
        self.collector_manager = None
        self.event_processor = None
        
        # Lock for thread safety on operations
        self._lock = threading.Lock()
        
        logging.info("Qt interaction adapter created")
    
    def initialize(self, app_coordinator, ui_manager, logging_manager, 
                 collector_manager, event_processor) -> bool:
        """
        Initialize the adapter with application components.
        
        Args:
            app_coordinator: Application coordinator
            ui_manager: UI manager for the application
            logging_manager: Logging manager
            collector_manager: Collector manager
            event_processor: Event processor
            
        Returns:
            bool: True if initialization was successful
        """
        self.app_coordinator = app_coordinator
        self.ui_manager = ui_manager
        self.logging_manager = logging_manager
        self.collector_manager = collector_manager
        self.event_processor = event_processor
        
        logging.info("Qt interaction adapter initialized")
        return True
    
    def _execute_safely(self, func, *args, **kwargs):
        """
        Execute a function in a thread-safe manner.
        
        This method ensures that UI operations are executed in the main thread.
        
        Args:
            func: Function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function call
        """
        # If we're already in the main thread, execute directly
        if threading.current_thread() is self.app_coordinator.thread():
            return func(*args, **kwargs)
        
        # If we're not in the main thread, use Qt's event system
        result = [None]
        error = [None]
        completed = threading.Event()
        
        def callback():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                error[0] = e
            finally:
                completed.set()
        
        # Use QTimer single shot to execute in the main thread
        QTimer.singleShot(0, callback)
        
        # Wait for completion with timeout
        if not completed.wait(timeout=5.0):
            logging.error("Operation timed out when executing safely")
            raise TimeoutError("Operation timed out")
        
        # Raise any errors that occurred
        if error[0]:
            raise error[0]
            
        return result[0]
    
    #
    # Recording control methods
    #
    
    def start_recording(self) -> bool:
        """
        Start recording inputs.
        
        Returns:
            bool: True if recording started successfully
        """
        try:
            # Check if app_coordinator exists
            if not self.app_coordinator:
                logging.error("Cannot start recording: app_coordinator not initialized")
                return False
                
            # Check if already recording
            if self.is_recording():
                logging.info("Already recording, no action taken")
                return True
                
            # Start recording safely in main thread
            def start():
                if self.app_coordinator.edit_mode:
                    return False
                if not self.app_coordinator.is_recording:
                    self.app_coordinator._start_recording()
                return True
                
            return self._execute_safely(start)
        except Exception as e:
            logging.error(f"Error starting recording: {e}")
            return False
    
    def stop_recording(self) -> bool:
        """
        Stop recording inputs.
        
        Returns:
            bool: True if recording stopped successfully
        """
        try:
            # Check if app_coordinator exists
            if not self.app_coordinator:
                logging.error("Cannot stop recording: app_coordinator not initialized")
                return False
                
            # Check if already stopped
            if not self.is_recording():
                logging.info("Not recording, no action taken")
                return True
                
            # Stop recording safely in main thread
            def stop():
                if self.app_coordinator.is_recording:
                    self.app_coordinator._stop_recording()
                return True
                
            return self._execute_safely(stop)
        except Exception as e:
            logging.error(f"Error stopping recording: {e}")
            return False
    
    def toggle_recording(self) -> Tuple[bool, bool]:
        """
        Toggle recording state.
        
        Returns:
            Tuple[bool, bool]: (success, is_recording_after_toggle)
        """
        try:
            # Check if app_coordinator exists
            if not self.app_coordinator:
                logging.error("Cannot toggle recording: app_coordinator not initialized")
                return False, False
            
            # Toggle recording safely in main thread
            def toggle():
                self.app_coordinator.toggle_recording()
                return True, self.app_coordinator.is_recording
                
            return self._execute_safely(toggle)
        except Exception as e:
            logging.error(f"Error toggling recording: {e}")
            return False, False
    
    def is_recording(self) -> bool:
        """
        Check if recording is active.
        
        Returns:
            bool: True if recording is active
        """
        if not self.app_coordinator:
            return False
        return self.app_coordinator.is_recording
    
    #
    # UI methods
    #
    
    def set_csv_path(self, filepath: str) -> bool:
        """
        Set the CSV log file path.
        
        Args:
            filepath: Path for the CSV file
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.logging_manager:
                logging.error("Cannot set CSV path: logging_manager not initialized")
                return False
                
            # Set CSV path safely
            def set_path():
                self.logging_manager.csv_logger.set_filepath(filepath)
                self.ui_manager.set_csv_path(filepath)
                return True
                
            return self._execute_safely(set_path)
        except Exception as e:
            logging.error(f"Error setting CSV path: {e}")
            return False
    
    def scan_controllers(self) -> List[Dict[str, Any]]:
        """
        Scan for available controllers.
        
        Returns:
            List of controller information dictionaries
        """
        try:
            if not self.collector_manager:
                logging.error("Cannot scan controllers: collector_manager not initialized")
                return []
                
            # Get PS4 collector
            ps4_collector = self.collector_manager.get_collector("ps4_controller")
            if not ps4_collector:
                logging.error("Cannot scan controllers: PS4 collector not available")
                return []
                
            # Scan controllers safely
            def scan():
                return ps4_collector.scan_controllers()
                
            return self._execute_safely(scan)
        except Exception as e:
            logging.error(f"Error scanning controllers: {e}")
            return []
    
    def connect_controller(self, index: int) -> bool:
        """
        Connect to a specific controller by index.
        
        Args:
            index: Controller index from scan_controllers()
            
        Returns:
            bool: True if connection successful
        """
        try:
            if not self.collector_manager:
                logging.error("Cannot connect controller: collector_manager not initialized")
                return False
                
            # Get PS4 collector
            ps4_collector = self.collector_manager.get_collector("ps4_controller")
            if not ps4_collector:
                logging.error("Cannot connect controller: PS4 collector not available")
                return False
                
            # Connect controller safely
            def connect():
                return ps4_collector.connect_to_controller(index)
                
            return self._execute_safely(connect)
        except Exception as e:
            logging.error(f"Error connecting controller: {e}")
            return False
    
    def switch_collector(self, collector_type: str) -> bool:
        """
        Switch to a different input collector.
        
        Args:
            collector_type: The type identifier for the collector
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.app_coordinator:
                logging.error("Cannot switch collector: app_coordinator not initialized")
                return False
                
            # Switch collector safely
            def switch():
                self.app_coordinator.switch_collector(collector_type)
                return True
                
            return self._execute_safely(switch)
        except Exception as e:
            logging.error(f"Error switching collector: {e}")
            return False
    
    def set_mouse_tracking_mode(self, mode: str, direction_only: bool = None) -> bool:
        """
        Set mouse tracking mode.
        
        Args:
            mode: Tracking mode ('joystick', 'delta', 'angle', 'axis')
            direction_only: Whether to use direction-only mode
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.app_coordinator or not self.ui_manager:
                logging.error("Cannot set mouse tracking mode: required components not initialized")
                return False
                
            # Set tracking mode safely
            def set_mode():
                # Handle direction_only parameter if provided
                if direction_only is not None:
                    current_dir_only = self.ui_manager.is_direction_only_mode()
                    if direction_only != current_dir_only:
                        self.ui_manager.set_direction_only_checkbox(direction_only)
                        # This will trigger an update of available modes
                
                # Set the tracking mode in UI
                self.ui_manager.set_tracking_mode(mode)
                
                # Apply mode to collector via app coordinator
                self.app_coordinator.set_mouse_tracking_mode(mode)
                return True
                
            return self._execute_safely(set_mode)
        except Exception as e:
            logging.error(f"Error setting mouse tracking mode: {e}")
            return False
    
    def set_mouse_settings(self, delta_smoothing: Optional[float] = None, 
                         joystick_sensitivity: Optional[float] = None,
                         angle_grouping: Optional[int] = None) -> bool:
        """
        Set mouse tracking settings.
        
        Args:
            delta_smoothing: Smoothing factor for delta tracking (0-100)
            joystick_sensitivity: Sensitivity for joystick tracking (0-100)
            angle_grouping: Angle grouping in degrees (1-60)
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.app_coordinator or not self.ui_manager:
                logging.error("Cannot set mouse settings: required components not initialized")
                return False
                
            # Set mouse settings safely
            def set_settings():
                # Update UI sliders
                if delta_smoothing is not None:
                    delta_slider = self.ui_manager.components.get('delta_slider')
                    if delta_slider:
                        delta_slider.setValue(int(delta_smoothing))
                
                if joystick_sensitivity is not None:
                    joystick_slider = self.ui_manager.components.get('joystick_slider')
                    if joystick_slider:
                        joystick_slider.setValue(int(joystick_sensitivity))
                
                if angle_grouping is not None:
                    angle_slider = self.ui_manager.components.get('angle_slider')
                    if angle_slider:
                        angle_slider.setValue(int(angle_grouping))
                
                # Apply settings via app coordinator
                self.app_coordinator.apply_mouse_settings()
                return True
                
            return self._execute_safely(set_settings)
        except Exception as e:
            logging.error(f"Error setting mouse settings: {e}")
            return False
    
    def get_mouse_settings(self) -> Dict[str, Any]:
        """
        Get current mouse tracking settings.
        
        Returns:
            Dict with current mouse settings
        """
        try:
            if not self.ui_manager:
                logging.error("Cannot get mouse settings: ui_manager not initialized")
                return {}
                
            # Dictionary to store settings
            settings = {}
            
            # Get settings directly from UI manager (thread-safe read operation)
            settings["tracking_mode"] = self.ui_manager.get_tracking_mode()
            settings["direction_only"] = self.ui_manager.is_direction_only_mode()
            settings["delta_smoothing"] = self.ui_manager.get_delta_smoothing()
            settings["joystick_sensitivity"] = self.ui_manager.get_joystick_sensitivity()
            settings["angle_grouping"] = self.ui_manager.get_angle_grouping()
            
            # Determine available tracking modes based on direction_only
            if settings["direction_only"]:
                settings["available_tracking_modes"] = ["axis", "angle"]
            else:
                settings["available_tracking_modes"] = ["joystick", "delta", "angle"]
                
            return settings
        except Exception as e:
            logging.error(f"Error getting mouse settings: {e}")
            return {}
    
    def get_tracked_keys(self) -> List[str]:
        """
        Get list of tracked keys.
        
        Returns:
            List of tracked keys
        """
        if not self.app_coordinator:
            return []
        return self.app_coordinator.get_tracked_keys()
    
    def toggle_edit_mode(self) -> Tuple[bool, bool]:
        """
        Toggle key/button edit mode.
        
        Returns:
            Tuple[bool, bool]: (success, is_edit_mode_after_toggle)
        """
        try:
            if not self.app_coordinator:
                logging.error("Cannot toggle edit mode: app_coordinator not initialized")
                return False, False
                
            # Check if recording is active
            if self.app_coordinator.is_recording:
                logging.warning("Cannot toggle edit mode while recording")
                return False, self.app_coordinator.edit_mode
                
            # Toggle edit mode safely
            def toggle():
                prev_state = self.app_coordinator.edit_mode
                self.app_coordinator.toggle_edit_mode()
                return self.app_coordinator.edit_mode != prev_state, self.app_coordinator.edit_mode
                
            return self._execute_safely(toggle)
        except Exception as e:
            logging.error(f"Error toggling edit mode: {e}")
            return False, False
    
    def is_edit_mode(self) -> bool:
        """
        Check if edit mode is active.
        
        Returns:
            bool: True if edit mode is active
        """
        if not self.app_coordinator:
            return False
        return self.app_coordinator.edit_mode
    
    def add_tracked_key(self, key: str) -> bool:
        """
        Add a key to tracked keys.
        
        Args:
            key: Key to add for tracking
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.app_coordinator:
                logging.error("Cannot add tracked key: app_coordinator not initialized")
                return False
                
            # Check if already in tracked keys
            current_keys = self.app_coordinator.get_tracked_keys()
            if key in current_keys:
                logging.info(f"Key {key} is already tracked")
                return True
                
            # Add key safely via handle_key_edit
            def add_key():
                # Store previous edit mode state
                was_in_edit_mode = self.app_coordinator.edit_mode
                
                # Enable edit mode temporarily if needed
                if not was_in_edit_mode:
                    self.app_coordinator.toggle_edit_mode()
                
                # Add the key
                self.app_coordinator.handle_key_edit(key)
                
                # Check if added successfully
                added = key in self.app_coordinator.get_tracked_keys()
                
                # Restore previous edit mode if needed
                if not was_in_edit_mode and self.app_coordinator.edit_mode:
                    self.app_coordinator.toggle_edit_mode()
                
                return added
                
            return self._execute_safely(add_key)
        except Exception as e:
            logging.error(f"Error adding tracked key: {e}")
            return False
    
    def remove_tracked_key(self, key: str) -> bool:
        """
        Remove a key from tracked keys.
        
        Args:
            key: Key to remove from tracking
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.app_coordinator:
                logging.error("Cannot remove tracked key: app_coordinator not initialized")
                return False
                
            # Check if key is tracked
            current_keys = self.app_coordinator.get_tracked_keys()
            if key not in current_keys:
                logging.info(f"Key {key} is not tracked")
                return False
                
            # Don't allow removing F9/media_play_pause
            if key.lower() == "key.media_play_pause".lower():
                logging.warning("Cannot remove F9/media_play_pause key (required for recording toggle)")
                return False
                
            # Remove key safely via handle_key_edit
            def remove_key():
                # Store previous edit mode state
                was_in_edit_mode = self.app_coordinator.edit_mode
                
                # Enable edit mode temporarily if needed
                if not was_in_edit_mode:
                    self.app_coordinator.toggle_edit_mode()
                
                # Remove the key
                self.app_coordinator.handle_key_edit(key)
                
                # Check if removed successfully
                removed = key not in self.app_coordinator.get_tracked_keys()
                
                # Restore previous edit mode if needed
                if not was_in_edit_mode and self.app_coordinator.edit_mode:
                    self.app_coordinator.toggle_edit_mode()
                
                return removed
                
            return self._execute_safely(remove_key)
        except Exception as e:
            logging.error(f"Error removing tracked key: {e}")
            return False
    
    def toggle_button_tracking(self, button_id: str, track: bool) -> bool:
        """
        Toggle tracking for a mouse button.
        
        Args:
            button_id: Button identifier
            track: Whether to track the button
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.app_coordinator:
                logging.error("Cannot toggle button tracking: app_coordinator not initialized")
                return False
                
            # Get current tracked keys
            tracked_keys = self.app_coordinator.get_tracked_keys()
            is_currently_tracked = button_id in tracked_keys
            
            # If current state already matches desired state, do nothing
            if is_currently_tracked == track:
                action = "tracked" if track else "not tracked"
                logging.info(f"Button {button_id} is already {action}")
                return True
                
            # Toggle button tracking safely
            def toggle_button():
                # Store previous edit mode state
                was_in_edit_mode = self.app_coordinator.edit_mode
                
                # Enable edit mode temporarily if needed
                if not was_in_edit_mode:
                    self.app_coordinator.toggle_edit_mode()
                
                # Toggle the button
                self.app_coordinator.handle_button_edit(button_id, track)
                
                # Check if toggled successfully
                toggled = bool(button_id in self.app_coordinator.get_tracked_keys()) == track
                
                # Restore previous edit mode if needed
                if not was_in_edit_mode and self.app_coordinator.edit_mode:
                    self.app_coordinator.toggle_edit_mode()
                
                return toggled
                
            return self._execute_safely(toggle_button)
        except Exception as e:
            logging.error(f"Error toggling button tracking: {e}")
            return False
    
    def toggle_fullscreen(self) -> bool:
        """
        Toggle fullscreen mode.
        
        Returns:
            bool: True if successful
        """
        try:
            if not self.ui_manager:
                logging.error("Cannot toggle fullscreen: ui_manager not initialized")
                return False
                
            # Toggle fullscreen safely
            def toggle():
                self.ui_manager.toggle_fullscreen.emit()
                return True
                
            return self._execute_safely(toggle)
        except Exception as e:
            logging.error(f"Error toggling fullscreen: {e}")
            return False
