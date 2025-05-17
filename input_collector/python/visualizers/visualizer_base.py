"""
Base class for input visualizers.

This module provides a base implementation for input visualizers,
implementing the common functionality required by the AbstractVisualizer interface.
"""

from typing import Optional, Any, Dict

from PyQt5.QtWidgets import QWidget

from ..interfaces.collector_interface import InputData


# Note: We don't inherit from AbstractVisualizer to avoid metaclass conflicts
class BaseVisualizer(QWidget):
    """
    Base implementation for input visualizers.
    
    This class provides a foundation for building input visualizers with common
    functionality already implemented. It implements the AbstractVisualizer interface
    without directly inheriting from it to avoid metaclass conflicts.
    """
    
    def __init__(self, parent=None) -> None:
        """Initialize the base visualizer."""
        super().__init__(parent)
        self.capabilities = {}
        self.edit_mode = False
        self.supported_collectors = ["keyboard_mouse", "ps4_controller"]  # Default to supporting all
    
    def update(self, input_data: Optional[InputData] = None) -> None:
        """
        Update the visualization based on input data.
        
        Args:
            input_data: Input event data containing state information
        """
        # Base implementation - subclasses should override
        super().update()
    
    def force_update(self) -> None:
        """Force a complete redraw of the visualization."""
        self.update()
    
    def set_collector_capabilities(self, capabilities: Dict[str, Any]) -> None:
        """
        Configure the visualizer based on collector capabilities.
        
        Args:
            capabilities: Dictionary of collector capabilities
        """
        self.capabilities = capabilities
    
    def set_edit_mode(self, enabled: bool) -> None:
        """
        Enable or disable edit mode for the visualizer.
        
        Args:
            enabled: Whether edit mode should be enabled
        """
        self.edit_mode = enabled
    
    def supports_collector(self, collector_type: str) -> bool:
        """
        Check if this visualizer supports a specific collector type.
        
        Args:
            collector_type: The type of collector to check
            
        Returns:
            bool: True if supported, False otherwise
        """
        return collector_type in self.supported_collectors
