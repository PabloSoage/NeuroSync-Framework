import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from ps4_event_collector import PS4EventCollector
from ps4_visualizer_ui import PS4ControllerWidget
from ps4_event_logger import PS4EventLogger

class PS4ControllerApp(QMainWindow):
    """Main application for PS4 controller visualization"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize components
        self.controller_widget = PS4ControllerWidget()
        self.event_collector = PS4EventCollector()
        self.event_logger = PS4EventLogger()
        
        # Set up UI
        self.setup_ui()
        
        # Connect signals
        self.connect_signals()
        
        # Set up update timer
        self.setup_timer()
        
    def setup_ui(self):
        """Set up the user interface"""
        self.setWindowTitle("PS4 Controller Visualizer")
        self.setGeometry(100, 100, 1400, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        
        # Left side - Controller visualization
        left_panel = QVBoxLayout()
        
        # Control buttons panel
        control_panel = QHBoxLayout()
        
        # Toggle image mode button
        self.toggle_button = QPushButton("Switch to Drawn Mode" if self.controller_widget.image_mode else "Switch to Image Mode")
        self.toggle_button.clicked.connect(self.toggle_display_mode)
        if not self.controller_widget.images_loaded:
            self.toggle_button.setEnabled(False)
            self.toggle_button.setText("Images Not Available")
        control_panel.addWidget(self.toggle_button)
        
        # Edit mode button
        self.edit_button = QPushButton("Enter Edit Mode")
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        if not self.controller_widget.images_loaded:
            self.edit_button.setEnabled(False)
        control_panel.addWidget(self.edit_button)
        
        # Save positions button
        self.save_button = QPushButton("Save Positions")
        self.save_button.clicked.connect(self.save_positions)
        self.save_button.setEnabled(False)
        control_panel.addWidget(self.save_button)
        
        left_panel.addLayout(control_panel)
        
        # Instructions for edit mode
        self.instructions_label = QLabel("")
        self.instructions_label.setStyleSheet("color: blue;")
        left_panel.addWidget(self.instructions_label)
        
        # Controller widget
        left_panel.addWidget(QLabel("PS4 Controller"))
        left_panel.addWidget(self.controller_widget)
        
        # Connection status
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        left_panel.addWidget(self.status_label)
        
        # Mode status
        mode_text = "Image Mode" if self.controller_widget.image_mode else "Drawn Mode"
        if not self.controller_widget.images_loaded:
            mode_text += " (Images not loaded - using fallback)"
        self.mode_label = QLabel(f"Display Mode: {mode_text}")
        left_panel.addWidget(self.mode_label)
        
        # Right side - Log display
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("Real-time Logs (JSON)"))
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMinimumWidth(500)
        self.log_display.setStyleSheet("background-color: black; color: green; font-family: monospace;")
        right_panel.addWidget(self.log_display)
        
        # Connect logger to display
        self.event_logger.set_display(self.log_display)
        
        # Clear logs button
        clear_button = QPushButton("Clear Logs")
        clear_button.clicked.connect(self.event_logger.clear_logs)
        right_panel.addWidget(clear_button)
        
        layout.addLayout(left_panel)
        layout.addLayout(right_panel)
    
    def connect_signals(self):
        """Connect signals from event collector to handler methods"""
        self.event_collector.button_changed.connect(self.on_button_changed)
        self.event_collector.stick_moved.connect(self.on_stick_moved)
        self.event_collector.trigger_changed.connect(self.on_trigger_changed)
        self.event_collector.controller_connected.connect(self.on_controller_connected)
        self.event_collector.controller_disconnected.connect(self.on_controller_disconnected)
        
    def setup_timer(self):
        """Set up timer for controller updates"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.event_collector.update)
        self.timer.start(16)  # ~60 FPS
    
    def on_button_changed(self, button_name, is_pressed):
        """Handle button change events from controller"""
        # Update button states in widget
        self.controller_widget.button_states[button_name] = is_pressed
        self.controller_widget.update()
        
        # Log the event
        self.event_logger.log_button_event(button_name, is_pressed)
    
    def on_stick_moved(self, stick_name, x, y):
        """Handle stick movement events from controller"""
        # Update stick position in widget
        self.controller_widget.stick_positions[stick_name] = (x, y)
        self.controller_widget.update()
        
        # Log the event
        self.event_logger.log_stick_event(stick_name, x, y)
    
    def on_trigger_changed(self, trigger_name, value):
        """Handle trigger change events from controller"""
        # Update trigger value in widget
        raw_value = int(value * 32767)  # Convert back to raw value
        self.controller_widget.trigger_values[trigger_name] = raw_value
        self.controller_widget.update()
        
        # Log the event
        self.event_logger.log_trigger_event(trigger_name, value)
    
    def on_controller_connected(self, name, index):
        """Handle controller connection event"""
        self.status_label.setText(f"Status: Connected - {name}")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        
        # Log the event
        self.event_logger.log_connection_event(True, name, index)
    
    def on_controller_disconnected(self):
        """Handle controller disconnection event"""
        self.status_label.setText("Status: Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        
        # Log the event
        self.event_logger.log_connection_event(False)
        
    def toggle_display_mode(self):
        """Toggle between image and drawn display modes"""
        new_mode = self.controller_widget.toggle_image_mode()
        mode_text = "Image Mode" if new_mode else "Drawn Mode"
        self.mode_label.setText(f"Display Mode: {mode_text}")
        self.toggle_button.setText("Switch to Drawn Mode" if new_mode else "Switch to Image Mode")
        
        # When switching to drawn mode, exit edit mode first if it's active
        if not new_mode and self.controller_widget.edit_mode:
            self.toggle_edit_mode()
            
        # Show/hide edit buttons based on mode
        self.edit_button.setVisible(new_mode)
        self.save_button.setVisible(new_mode)
        
        # Log the event
        self.event_logger.log_display_mode_change(mode_text)
    
    def toggle_edit_mode(self):
        """Toggle edit mode for positioning elements"""
        edit_mode = self.controller_widget.toggle_edit_mode()
        
        if edit_mode:
            self.edit_button.setText("Exit Edit Mode")
            self.save_button.setEnabled(True)
            self.instructions_label.setText(
                "Edit Mode: Drag elements to reposition them.\n"
                "By default, moving one element moves its entire group.\n"
                "Hold SHIFT while dragging to move individual elements."
            )
            self.event_logger.log_edit_mode_event(True)
        else:
            self.edit_button.setText("Enter Edit Mode")
            self.save_button.setEnabled(False)
            self.instructions_label.setText("")
            self.event_logger.log_edit_mode_event(False)
    
    def save_positions(self):
        """Save current positions to JSON file"""
        if self.controller_widget.save_positions_to_json():
            QMessageBox.information(self, "Success", "Positions saved successfully!")
            self.event_logger.log_positions_saved(str(self.controller_widget.positions_file))
        else:
            QMessageBox.warning(self, "Error", "Failed to save positions!")
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.event_collector.cleanup()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PS4ControllerApp()
    window.show()
    sys.exit(app.exec_())
