"""
Visualizer manager module.

Manages visualization components for input events.
"""

from typing import Dict, List, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget

from ..visualizers import KeyboardVisualizer, MouseVisualizer, MouseButtonsSelector
from ..interfaces import InputData


class VisualizerManager(QObject):
    """
    Manages visualization components for input events.
    
    This class is responsible for creating, configuring, and updating
    the visualization components used to display input events.
    """
    
    key_clicked = pyqtSignal(str)
    button_toggled = pyqtSignal(str, bool)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the visualizer manager.
        
        Args:
            parent: Parent widget for visualizers
        """
        super().__init__()
        
        # Create visualizers with the same parent
        self.keyboard_viz = KeyboardVisualizer(parent)
        self.mouse_viz = MouseVisualizer(parent)
        self.mouse_buttons_selector = MouseButtonsSelector(parent)
        
        # Connect signals
        self._setup_keyboard_connections()
        self.mouse_buttons_selector.button_toggled.connect(self.button_toggled)
        
        # Default edit mode to False (disabled)
        self.edit_mode_enabled = False
    
    def _setup_keyboard_connections(self) -> None:
        """Set up keyboard mouse press event handling."""
        # Save the original mouse press event method
        self.original_mouse_press = self.keyboard_viz.mousePressEvent
        
        # Create our custom handler
        def new_mouse_press(event):
            # First call the original method to preserve the base behavior
            if self.original_mouse_press:
                self.original_mouse_press(event)
            
            # Then handle our custom event - only emit key_clicked when in edit mode
            if self.edit_mode_enabled:
                try:
                    x, y = event.x(), event.y()
                    key = self.keyboard_viz.get_key_at_position(x, y)
                    if key:
                        self.key_clicked.emit(key)
                        print(f"Key clicked in edit mode: {key}")
                except Exception as e:
                    print(f"Error processing keyboard click: {e}")
        
        # Store the new method as an instance attribute so it won't be garbage collected
        self.new_mouse_press = new_mouse_press
        
        # Always install our custom handler - we'll use the edit_mode_enabled flag to control its behavior
        self.keyboard_viz.mousePressEvent = self.new_mouse_press
    
    def get_keyboard_visualizer(self) -> KeyboardVisualizer:
        """Get the keyboard visualizer."""
        return self.keyboard_viz
        
    def get_mouse_visualizer(self) -> MouseVisualizer:
        """Get the mouse visualizer."""
        return self.mouse_viz
        
    def get_mouse_buttons_selector(self) -> MouseButtonsSelector:
        """Get the mouse buttons selector."""
        return self.mouse_buttons_selector
    
    def update_for_collector(self, collector_type: str, capabilities: Dict[str, Any]) -> None:
        """
        Update visualizers based on collector type and capabilities.
        
        Args:
            collector_type: Type of the current collector
            capabilities: Dictionary of collector capabilities
        """
        # Update visualizer visibility
        self.keyboard_viz.setVisible(
            self.keyboard_viz.supports_collector(collector_type)
        )
        
        self.mouse_viz.setVisible(
            self.mouse_viz.supports_collector(collector_type)
        )
        
        self.mouse_buttons_selector.setVisible(
            self.mouse_buttons_selector.supports_collector(collector_type) and
            capabilities.get("supports_mouse_buttons", False)
        )
        
        # Update capabilities
        if hasattr(self.keyboard_viz, "set_collector_capabilities"):
            self.keyboard_viz.set_collector_capabilities(capabilities)
        
        if hasattr(self.mouse_viz, "set_collector_capabilities"):
            self.mouse_viz.set_collector_capabilities(capabilities)
            
        if hasattr(self.mouse_buttons_selector, "set_collector_capabilities"):
            self.mouse_buttons_selector.set_collector_capabilities(capabilities)
    
    def set_tracked_keys(self, keys: List[str]) -> None:
        """
        Set the keys being tracked.
        
        Args:
            keys: List of keys to track
        """
        # Añadir manejo de errores para evitar crashes
        try:
            if hasattr(self.keyboard_viz, 'set_tracked_keys'):
                self.keyboard_viz.set_tracked_keys(keys)
            
            if hasattr(self.mouse_buttons_selector, 'setTrackedButtons'):
                self.mouse_buttons_selector.setTrackedButtons(keys)
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
            
            # Update cursors based on edit mode
            self.keyboard_viz.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
            
            # Update the mode in mouse buttons selector
            if hasattr(self.mouse_buttons_selector, 'setEditMode'):
                self.mouse_buttons_selector.setEditMode(enabled)
                
            # Debug message
            print(f"Visualizer edit mode set to: {enabled}")
            
        except Exception as e:
            print(f"Error setting edit mode: {e}")
            import traceback
            traceback.print_exc()
    
    def force_update(self) -> None:
        """Force update all visualizers."""
        # Añadir manejo de errores para prevenir crashes
        try:
            if hasattr(self.keyboard_viz, 'force_update'):
                self.keyboard_viz.force_update()
            
            if hasattr(self.mouse_viz, 'force_update'):
                self.mouse_viz.force_update()
        except Exception as e:
            print(f"Error forcing update: {e}")
