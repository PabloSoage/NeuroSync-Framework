"""
Qt integration adapter for unified application.

This adapter bridges between the unified application and the individual
EEG processor and input collector applications.
"""
import logging
from typing import Optional, Any, Dict

from PyQt5.QtCore import QObject, pyqtSignal


class QtIntegrationAdapter(QObject):
    """
    Adapter for integrating EEG Processor and Input Collector applications.
    
    This adapter provides a unified interface for accessing data and services
    from both applications while maintaining their independence.
    """
    
    # Signals for status updates
    status_updated = pyqtSignal(dict)
    
    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the integration adapter."""
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__)
        
        # Application references
        self.eeg_app: Optional[Any] = None
        self.input_app: Optional[Any] = None
        self.sync_service: Optional[Any] = None
        
        self.logger.info("Qt integration adapter initialized")
    
    def set_eeg_app(self, eeg_app: Any) -> None:
        """Set EEG processor application reference."""
        self.eeg_app = eeg_app
        self.logger.info("EEG application set")
    
    def set_input_app(self, input_app: Any) -> None:
        """Set input collector application reference."""
        self.input_app = input_app
        self.logger.info("Input application set")
    
    def set_sync_service(self, sync_service: Any) -> None:
        """Set synchronization service reference."""
        self.sync_service = sync_service
        self.logger.info("Sync service set")
    
    def get_eeg_service(self) -> Optional[Any]:
        """Get EEG data access service."""
        try:
            # Try to get DataAccessService directly
            from eeg_processor.python.services.data_access_service import DataAccessService
            return DataAccessService.get_instance()
        except Exception as e:
            self.logger.error(f"Failed to get EEG data service: {e}")
            return None
    
    def get_input_service(self) -> Optional[Any]:
        """Get input data access service."""
        try:
            # Try to get DataAccessService directly
            from input_collector.python.services.data_access_service import DataAccessService
            return DataAccessService.get_instance()
        except Exception as e:
            self.logger.error(f"Failed to get input data service: {e}")
            return None
    
    def get_eeg_status(self) -> Dict[str, Any]:
        """Get EEG processor status."""
        status = {
            'connected': False,
            'streaming': False,
            'board_name': '',
            'sampling_rate': 0
        }
        
        try:
            eeg_service = self.get_eeg_service()
            if eeg_service:
                metadata = eeg_service.get_metadata()
                
                # Check if connected based on board_id and streaming status
                board_id = metadata.get('board_id', -1)
                is_streaming = eeg_service.is_streaming()
                
                status['connected'] = board_id != -1
                status['streaming'] = is_streaming
                status['board_name'] = metadata.get('board_name', '')
                status['sampling_rate'] = eeg_service.get_sampling_rate()
                
                # Additional check: if we're getting data, we're definitely connected
                try:
                    current_data, _ = eeg_service.get_current_data()
                    if current_data.size > 0:
                        status['connected'] = True
                        # If we have data and streaming is True, we're actively streaming
                        if is_streaming:
                            status['streaming'] = True
                except:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Error getting EEG status: {e}")
        
        return status
    
    def get_input_status(self) -> Dict[str, Any]:
        """Get input collector status."""
        status = {
            'active': False,
            'recording': False,
            'collector_type': '',
            'active_keys': []
        }
        
        try:
            input_service = self.get_input_service()
            if input_service:
                metadata = input_service.get_metadata()
                last_update = metadata.get('last_update', 0)
                
                # Consider active if we've received events recently (within last 30 seconds)
                import time
                current_time = time.time()
                status['active'] = (current_time - last_update) < 30.0
                status['recording'] = last_update > 0
                status['collector_type'] = metadata.get('collector_type', '')
                status['active_keys'] = input_service.get_active_keys()
                
        except Exception as e:
            self.logger.error(f"Error getting input status: {e}")
        
        return status
    
    def get_eeg_data(self) -> Optional[Any]:
        """Get current EEG data."""
        try:
            eeg_service = self.get_eeg_service()
            if eeg_service:
                return eeg_service.get_current_data()
        except Exception as e:
            self.logger.error(f"Error getting EEG data: {e}")
        return None
    
    def get_input_data(self) -> Optional[Any]:
        """Get current input data."""
        try:
            input_service = self.get_input_service()
            if input_service:
                return input_service.get_current_event()
        except Exception as e:
            self.logger.error(f"Error getting input data: {e}")
        return None
    
    def register_eeg_callback(self, callback) -> bool:
        """Register callback for EEG data updates."""
        try:
            eeg_service = self.get_eeg_service()
            if eeg_service and hasattr(eeg_service, 'register_local_callback'):
                eeg_service.register_local_callback(callback)
                return True
        except Exception as e:
            self.logger.error(f"Error registering EEG callback: {e}")
        return False
    
    def register_input_callback(self, callback) -> bool:
        """Register callback for input data updates."""
        try:
            input_service = self.get_input_service()
            if input_service and hasattr(input_service, 'register_callback'):
                input_service.register_callback(callback)
                return True
        except Exception as e:
            self.logger.error(f"Error registering input callback: {e}")
        return False
    
    def emit_status_update(self, message: str) -> None:
        """Emit status update signal."""
        self.status_updated.emit({'message': message})