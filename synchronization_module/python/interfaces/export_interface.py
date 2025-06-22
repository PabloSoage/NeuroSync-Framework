"""
Interfaces for dataset export operations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import numpy as np


class DatasetExporterInterface(ABC):
    """Interface for dataset exporters."""
    
    @abstractmethod
    def export_dataset(
        self, 
        eeg_data: np.ndarray,
        input_events: Dict[str, Any],
        metadata: Dict[str, Any],
        filepath: str
    ) -> bool:
        """Export synchronized dataset."""
        pass
    
    @abstractmethod
    def validate_data(
        self, 
        eeg_data: np.ndarray,
        input_events: Dict[str, Any]
    ) -> bool:
        """Validate data before export."""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats."""
        pass


class MetadataInterface(ABC):
    """Interface for metadata management."""
    
    @abstractmethod
    def generate_metadata(
        self,
        eeg_info: Dict[str, Any],
        input_info: Dict[str, Any],
        sync_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive metadata."""
        pass
    
    @abstractmethod
    def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate metadata structure."""
        pass