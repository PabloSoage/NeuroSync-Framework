from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import pyqtSignal

class BasePanel(QWidget):
    """
    Base class for UI panels.
    
    This class provides common functionality and signals for all UI panels.
    """
    
    # Define signals for communication with main app
    status_message = pyqtSignal(str)
    error_message = pyqtSignal(str, str)  # title, message
    
    def __init__(self, parent=None):
        """Initialize the base panel."""
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
    
    def show_status(self, message: str) -> None:
        """
        Emit a status message signal.
        
        Args:
            message: Status message to show
        """
        self.status_message.emit(message)
    
    def show_error(self, title: str, message: str) -> None:
        """
        Emit an error message signal.
        
        Args:
            title: Error message title
            message: Error message content
        """
        self.error_message.emit(title, message)
