from typing import Optional

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea


class BasePanel(QWidget):
    """
    Base class for UI panels.

    This class provides common functionality and signals for all UI panels.
    """

    # Define signals for communication with main app
    status_message = pyqtSignal(str)
    error_message = pyqtSignal(str, str)  # title, message

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the base panel."""
        super().__init__(parent)

        # Create main layout for the panel
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.NoFrame)  # Remove frame border

        # Create content widget that will be inside the scroll area
        self.content_widget = QWidget()
        self.layout = QVBoxLayout(self.content_widget)

        # Set appropriate spacing
        self.layout.setSpacing(10)

        # Add the content widget to the scroll area
        scroll_area.setWidget(self.content_widget)

        # Add scroll area to the main layout
        main_layout.addWidget(scroll_area)

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
