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
        if self.eeg_app and hasattr(self.eeg_app, 'collector_service'):
            return self.eeg_app.collector_service
        return None
    
    def get_input_service(self) -> Optional[Any]:
        """Get input data access service."""
        if self.input_app and hasattr(self.input_app, 'collector_manager'):
            return self.input_app.collector_manager
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
            if self.eeg_app and hasattr(self.eeg_app, 'collector_service'):
                collector = self.eeg_app.collector_service
                status['connected'] = collector.is_connected()
                status['streaming'] = collector.is_streaming_active()
                
                if status['connected']:
                    board_info = collector.get_board_info()
                    status['board_name'] = board_info.get('board_name', '')
                    status['sampling_rate'] = collector.get_sampling_rate()
                    
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
            if self.input_app and hasattr(self.input_app, 'app_coordinator'):
                coordinator = self.input_app.app_coordinator
                status['active'] = True
                status['recording'] = coordinator.is_recording
                status['collector_type'] = coordinator.collector_manager.get_current_collector_type()
                status['active_keys'] = coordinator.collector_manager.get_active_keys()
                
        except Exception as e:
            self.logger.error(f"Error getting input status: {e}")
        
        return status
    
    def get_eeg_data(self) -> Optional[Any]:
        """Get current EEG data."""
        try:
            eeg_service = self.get_eeg_service()
            if eeg_service and hasattr(eeg_service, 'get_board_data'):
                return eeg_service.get_board_data()
        except Exception as e:
            self.logger.error(f"Error getting EEG data: {e}")
        return None
    
    def get_input_data(self) -> Optional[Any]:
        """Get current input data."""
        try:
            input_service = self.get_input_service()
            if input_service and hasattr(input_service, 'get_input_event'):
                return input_service.get_input_event()
        except Exception as e:
            self.logger.error(f"Error getting input data: {e}")
        return None
    
    def register_eeg_callback(self, callback) -> bool:
        """Register callback for EEG data updates."""
        try:
            if self.eeg_app and hasattr(self.eeg_app, 'collector_service'):
                # Register with data access service for real-time updates
                data_service = getattr(self.eeg_app, 'data_access_service', None)
                if data_service and hasattr(data_service, 'register_local_callback'):
                    data_service.register_local_callback(callback)
                    return True
        except Exception as e:
            self.logger.error(f"Error registering EEG callback: {e}")
        return False
    
    def register_input_callback(self, callback) -> bool:
        """Register callback for input data updates."""
        try:
            input_service = self.get_input_service()
            if input_service and hasattr(input_service, 'on_event'):
                input_service.on_event(callback)
                return True
        except Exception as e:
            self.logger.error(f"Error registering input callback: {e}")
        return False
    
    def emit_status_update(self, message: str) -> None:
        """Emit status update signal."""
        self.status_updated.emit({'message': message})