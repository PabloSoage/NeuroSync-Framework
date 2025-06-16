import time
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QTextEdit, QLabel


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

        # Real-time status info
        self.realtime_info = QLabel("Real-time Mode: Inactive")
        self.realtime_info.setStyleSheet(
            "color: #888888; font-weight: bold; padding: 5px;"
        )
        status_layout.addWidget(self.realtime_info)

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

    def update_realtime_status(self, status_info: Dict[str, Any]) -> None:
        """Update real-time status information."""
        if status_info.get("active", False):
            update_count = status_info.get("update_count", 0)
            uptime = status_info.get("uptime", 0)
            plot_type = status_info.get("plot_type", "Unknown")

            self.realtime_info.setText(
                f"Real-time Mode: Active | Updates: {update_count} | "
                f"Uptime: {uptime:.1f}s | Plot: {plot_type} | ⚡ Optimized"
            )
            self.realtime_info.setStyleSheet(
                "color: #00CC88; font-weight: bold; padding: 5px;"
            )
        else:
            self.realtime_info.setText("Real-time Mode: Inactive")
            self.realtime_info.setStyleSheet(
                "color: #888888; font-weight: bold; padding: 5px;"
            )

    def add_channel_update_message(self, old_count: int, new_count: int) -> None:
        """Add a special message for channel updates."""
        if old_count != new_count:
            emoji = "📈" if new_count > old_count else "📉"
            self.add_status_message(f"{emoji} Channel selection changed: {old_count} → {new_count}")

    def add_optimization_message(self, channels_selected: int, total_channels: int) -> None:
        """Add optimization information message."""
        if channels_selected < total_channels:
            percentage_saved = ((total_channels - channels_selected) / total_channels * 100)
            self.add_status_message(
                f"⚡ Optimization: Processing {channels_selected}/{total_channels} channels "
                f"({percentage_saved:.1f}% less computation)"
            )
        else:
            self.add_status_message(f"ℹ️ Processing all {total_channels} channels")
