import time
from typing import Optional

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QTextEdit


class MNEStatusWidget(QWidget):
    """Widget specialized for MNE operation status monitoring."""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the MNE status widget."""
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)

        # Status group
        status_group = QGroupBox("Operation Status")
        status_layout = QVBoxLayout(status_group)

        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
                font-family: monospace;
            }
        """
        )
        status_layout.addWidget(self.status_text)

        layout.addWidget(status_group)

    def add_status_message(self, message: str) -> None:
        """Add a timestamped status message."""
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")

    def clear_status(self) -> None:
        """Clear all status messages."""
        self.status_text.clear()
