import json
from datetime import datetime
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import Qt

class PS4EventLogger:
    """Handles logging of PS4 controller events"""
    
    def __init__(self, log_display=None):
        """Initialize the event logger
        
        Args:
            log_display: QTextEdit to display logs (optional)
        """
        self.log_display = log_display
        self.log_history = []
    
    def set_display(self, log_display):
        """Set the log display widget
        
        Args:
            log_display: QTextEdit widget to display logs
        """
        self.log_display = log_display
    
    def clear_logs(self):
        """Clear log history and display"""
        self.log_history = []
        if self.log_display:
            self.log_display.clear()
    
    def log_event(self, event_type, data):
        """Log an event with timestamp
        
        Args:
            event_type: Type of event (string)
            data: Event data (dict)
        
        Returns:
            The log entry as a dict
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "data": data
        }
        
        self.log_history.append(log_entry)
        self._display_log(log_entry)
        
        return log_entry
    
    def log_button_event(self, button_name, is_pressed):
        """Log a button press/release event
        
        Args:
            button_name: Name of the button
            is_pressed: True if pressed, False if released
        """
        return self.log_event("button_change", {button_name: is_pressed})
    
    def log_stick_event(self, stick_name, x, y):
        """Log an analog stick movement event
        
        Args:
            stick_name: 'left' or 'right'
            x: X-axis position (-1.0 to 1.0)
            y: Y-axis position (-1.0 to 1.0)
        """
        return self.log_event(f"{stick_name}_stick", {"x": x, "y": y})
    
    def log_trigger_event(self, trigger_name, value):
        """Log a trigger pressure event
        
        Args:
            trigger_name: 'left' or 'right'
            value: Trigger pressure (0.0 to 1.0)
        """
        return self.log_event(f"{trigger_name}_trigger", {"value": value})
    
    def log_connection_event(self, connected, name=None, index=None):
        """Log a controller connection/disconnection event
        
        Args:
            connected: True if connected, False if disconnected
            name: Controller name (if connected)
            index: Controller index (if connected)
        """
        if connected:
            return self.log_event("controller_connected", {"name": name, "index": index})
        else:
            return self.log_event("controller_disconnected", {})
    
    def log_display_mode_change(self, mode):
        """Log a display mode change event
        
        Args:
            mode: New display mode
        """
        return self.log_event("display_mode_changed", {"mode": mode})
    
    def log_edit_mode_event(self, enabled):
        """Log an edit mode change event
        
        Args:
            enabled: True if edit mode was enabled, False if disabled
        """
        if enabled:
            return self.log_event("edit_mode_enabled", {})
        else:
            return self.log_event("edit_mode_disabled", {})
    
    def log_positions_saved(self, file_path):
        """Log a positions saved event
        
        Args:
            file_path: Path to saved positions file
        """
        return self.log_event("positions_saved", {"file": str(file_path)})
    
    def _display_log(self, log_entry):
        """Display a log entry in the log display widget
        
        Args:
            log_entry: Log entry dict
        """
        if not self.log_display:
            return
            
        json_str = json.dumps(log_entry, indent=2)
        self.log_display.append(json_str)
        self.log_display.append("-" * 50)
        
        # Auto-scroll to bottom
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def export_logs(self, file_path):
        """Export logs to a file
        
        Args:
            file_path: Path to save logs
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(self.log_history, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting logs: {e}")
            return False
    
    def get_log_history(self):
        """Get the full log history
        
        Returns:
            List of log entries
        """
        return self.log_history.copy()
