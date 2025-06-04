"""
Visualizer manager module.

Manages visualization components for input events.
"""

from typing import Dict, List, Any, Optional

from PyQt5.QtCore import QObject, pyqtSignal, Qt, QEvent
from PyQt5.QtWidgets import QWidget

from ..visualizers import KeyboardVisualizer, MouseVisualizer, MouseButtonsSelector, PS4ControllerVisualizer


# Note: We don't import the interfaces for inheritance to avoid metaclass conflicts

class VisualizerManager(QObject):  # Only inherit from QObject
    """
    Manages visualization components for input events.
    
    This class is responsible for creating, configuring, and updating
    the visualization components used to display input events.
    
    This class implements AbstractVisualizerProvider and AbstractVisualizerController
    interfaces implicitly to avoid metaclass conflicts with Qt.
    """
    
    # Signal emitted when a key is clicked in edit mode
    key_clicked = pyqtSignal(str)
    
    # Signal emitted when a button tracking state is toggled
    button_toggled = pyqtSignal(str, bool)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the visualizer manager.
        
        Args:
            parent: Parent widget for visualizers
        """
        super().__init__()
        
        # Default edit mode to False (disabled) - MOVED BEFORE setup_keyboard_connections
        self.edit_mode_enabled = False
        
        # Create visualizers with the same parent
        self.keyboard_viz = KeyboardVisualizer(parent)
        self.mouse_viz = MouseVisualizer(parent)
        self.mouse_buttons_selector = MouseButtonsSelector(parent)
        self.ps4_controller_viz = PS4ControllerVisualizer(parent)
        
        # Connect signals
        self._setup_keyboard_connections()
        self.mouse_buttons_selector.button_toggled.connect(self.button_toggled)
    
    def _setup_keyboard_connections(self) -> None:
        """Set up keyboard mouse press event handling."""
        try:
            # Create a better keyboard event filter that keeps a reference to self
            # instead of just edit_mode_enabled which may not update
            self.keyboard_event_filter = KeyboardEventFilter(self)
            
            # Install the event filter on the keyboard visualizer
            if self.keyboard_viz:
                self.keyboard_viz.installEventFilter(self.keyboard_event_filter)
                # Enable mouse tracking for hover effects
                self.keyboard_viz.setMouseTracking(True)
                print("Keyboard event filter installed successfully")
            else:
                print("Cannot install event filter: keyboard_viz is None")
        
        except Exception as e:
            print(f"Major error setting up keyboard connections: {e}")
            import traceback
            traceback.print_exc()
    
    # Implementation of AbstractVisualizerProvider methods
    
    def get_keyboard_visualizer(self) -> KeyboardVisualizer:
        """Get the keyboard visualizer component."""
        return self.keyboard_viz
        
    def get_mouse_visualizer(self) -> MouseVisualizer:
        """Get the mouse visualizer component."""
        return self.mouse_viz
        
    def get_mouse_buttons_selector(self) -> MouseButtonsSelector:
        """Get the mouse buttons selector component."""
        return self.mouse_buttons_selector
    
    def get_ps4_controller_visualizer(self) -> PS4ControllerVisualizer:
        """Get the PS4 controller visualizer component."""
        return self.ps4_controller_viz
    
    # Implementation of AbstractVisualizerController methods
    
    def update_for_collector(self, collector_type: str, capabilities: Dict[str, Any]) -> None:
        """
        Update visualizers based on collector type and capabilities.
        
        Args:
            collector_type: Type of the current collector
            capabilities: Dictionary of collector capabilities
        """
        # Check if we're using PS4 controller
        is_ps4_controller = collector_type == "ps4_controller"
        
        # Update visualizer visibility - completely hide keyboard/mouse elements when using PS4
        self.keyboard_viz.setVisible(
            self.keyboard_viz.supports_collector(collector_type) and 
            not is_ps4_controller  # Hide keyboard when using PS4 controller
        )
        
        self.mouse_viz.setVisible(
            self.mouse_viz.supports_collector(collector_type) and
            not is_ps4_controller  # Hide mouse when using PS4 controller
        )
        
        self.mouse_buttons_selector.setVisible(
            self.mouse_buttons_selector.supports_collector(collector_type) and
            capabilities.get("supports_mouse_buttons", False) and
            not is_ps4_controller  # Hide mouse buttons when using PS4 controller
        )
        
        # Show PS4 controller visualizer only when using PS4 controller
        self.ps4_controller_viz.setVisible(is_ps4_controller)
        
        # Update capabilities
        if hasattr(self.keyboard_viz, "set_collector_capabilities"):
            self.keyboard_viz.set_collector_capabilities(capabilities)
        
        if hasattr(self.mouse_viz, "set_collector_capabilities"):
            self.mouse_viz.set_collector_capabilities(capabilities)
            
        if hasattr(self.mouse_buttons_selector, "set_collector_capabilities"):
            self.mouse_buttons_selector.set_collector_capabilities(capabilities)
            
        if hasattr(self.ps4_controller_viz, "set_collector_capabilities"):
            self.ps4_controller_viz.set_collector_capabilities(capabilities)
    
    def set_tracked_keys(self, keys: List[str]) -> None:
        """
        Set the keys being tracked.
        
        Args:
            keys: List of keys to track
        """
        try:
            if hasattr(self.keyboard_viz, 'set_tracked_keys'):
                self.keyboard_viz.set_tracked_keys(keys)
            
            if hasattr(self.mouse_buttons_selector, 'setTrackedButtons'):
                self.mouse_buttons_selector.setTrackedButtons(keys)
                
            if hasattr(self.ps4_controller_viz, 'set_tracked_keys'):
                self.ps4_controller_viz.set_tracked_keys(keys)
        except Exception as e:
            print(f"Error setting tracked keys: {e}")
    
    def set_scroll_tracking(self, enabled: bool) -> None:
        """
        Set whether to track mouse scroll events.
        
        Args:
            enabled: Whether to track scroll events
        """
        self.mouse_buttons_selector.setScrollTracking(enabled)
    
    def set_edit_mode(self, enabled: bool) -> None:
        """
        Set edit mode for visualizers.
        
        Args:
            enabled: Whether edit mode is enabled
        """
        try:
            # Store the edit mode state
            self.edit_mode_enabled = enabled
            print(f"VisualizerManager.set_edit_mode({enabled}) - Flag updated")
            
            # Update the cursor according to mode
            if self.keyboard_viz:
                self.keyboard_viz.setCursor(
                    Qt.PointingHandCursor if enabled else Qt.ArrowCursor
                )
                
                # Propagate edit mode state if supported
                if hasattr(self.keyboard_viz, 'set_edit_mode'):
                    self.keyboard_viz.set_edit_mode(enabled)
            
            # Update mouse buttons selector
            if self.mouse_buttons_selector:
                if hasattr(self.mouse_buttons_selector, 'setEditMode'):
                    self.mouse_buttons_selector.setEditMode(enabled)
                    
            # Update PS4 controller visualizer
            if self.ps4_controller_viz:
                self.ps4_controller_viz.setCursor(
                    Qt.PointingHandCursor if enabled else Qt.ArrowCursor
                )
                if hasattr(self.ps4_controller_viz, 'set_edit_mode'):
                    self.ps4_controller_viz.set_edit_mode(enabled)
            
            # Force an update to reflect visual changes
            self.force_update()
            
            print(f"Edit mode set to {enabled} (using event filter approach)")
            
        except Exception as e:
            print(f"Error setting edit mode: {e}")
            import traceback
            traceback.print_exc()
    
    def force_update(self) -> None:
        """Force update all visualizers."""
        try:
            if hasattr(self.keyboard_viz, 'force_update'):
                self.keyboard_viz.force_update()
            
            if hasattr(self.mouse_viz, 'force_update'):
                self.mouse_viz.force_update()
                
            if hasattr(self.mouse_buttons_selector, 'update'):
                self.mouse_buttons_selector.update()
                
            if hasattr(self.ps4_controller_viz, 'force_update'):
                self.ps4_controller_viz.force_update()
                
        except Exception as e:
            print(f"Error forcing visualizer updates: {e}")


# Define KeyboardEventFilter as a separate class for clarity
class KeyboardEventFilter(QObject):
    """Event filter for keyboard visualizer click handling."""
    
    def __init__(self, visualizer_manager):
        """
        Initialize the keyboard event filter.
        
        Args:
            visualizer_manager: Reference to the visualizer manager
        """
        super().__init__()
        self.visualizer_manager = visualizer_manager
    
    def eventFilter(self, obj, event):
        """
        Filter keyboard mouse events.
        
        Args:
            obj: Object that the event was sent to
            event: The event
            
        Returns:
            bool: True if event was handled, False otherwise
        """
        # Only process mouse press events when in edit mode
        if event.type() == QEvent.MouseButtonPress:
            # Check edit mode from visualizer_manager, not a stored variable
            if self.visualizer_manager.edit_mode_enabled:
                try:
                    # Get the keyboard visualizer from manager
                    keyboard_viz = self.visualizer_manager.keyboard_viz
                    
                    if keyboard_viz:
                        # Get key at click position
                        key = keyboard_viz.get_key_at_position(event.x(), event.y())
                        if key:
                            print(f"Key clicked in event filter: {key}, emitting signal")
                            # Emit the key_clicked signal
                            self.visualizer_manager.key_clicked.emit(key)
                            return True  # Event handled
                except Exception as e:
                    print(f"Error in keyboard event filter: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Pass event to standard event processing
        return False  # Let the event continue
