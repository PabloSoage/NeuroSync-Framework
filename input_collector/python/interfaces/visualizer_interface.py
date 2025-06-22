"""
Interfaces for input visualization.

This module defines interfaces for visualizing input data from different collectors.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, Dict

from .collector_interface import InputData


class AbstractVisualizer(ABC):
    """
    Abstract interface for input visualizers.

    This abstract class defines the interface that all visualizers should implement.
    Visualizers are responsible for displaying input events and states visually.
    """

    @abstractmethod
    def update(self, input_data: Optional[InputData] = None) -> None:
        """
        Update the visualization based on input data.

        Args:
            input_data: Input event data containing state information
        """
        pass

    @abstractmethod
    def force_update(self) -> None:
        """
        Force a redraw of the visualization.
        """
        pass

    def set_collector_capabilities(self, capabilities: Dict[str, Any]) -> None:
        """
        Configure the visualizer based on collector capabilities.

        Args:
            capabilities: Dictionary of collector capabilities
        """
        pass

    def set_edit_mode(self, enabled: bool) -> None:
        """
        Enable or disable edit mode for the visualizer.

        Args:
            enabled: Whether edit mode should be enabled
        """
        pass

    def supports_collector(self, collector_type: str) -> bool:
        """
        Check if this visualizer supports a specific collector type.

        Args:
            collector_type: The type of collector to check

        Returns:
            bool: True if supported, False otherwise
        """
        return True
