"""
API Explorer module.

Provides an interactive GUI for exploring and testing the Input Data API in real-time.
"""

import inspect
import time
import json
from typing import Any, Dict, List, Callable, Optional, Tuple
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTreeWidget, 
    QTreeWidgetItem, QSplitter, QTextEdit, QLineEdit, QFormLayout, 
    QGroupBox, QScrollArea, QApplication, QComboBox, QSpinBox, QCheckBox,
    QTabWidget, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QSize
from PyQt5.QtGui import QFont, QColor, QTextCursor

# Use a try-except block for importing InputDataAPI
try:
    from ..data_access_api import InputDataAPI
except ImportError as e:
    print(f"Error importing InputDataAPI: {e}")
    # Create a fallback/stub InputDataAPI class if import fails
    class InputDataAPI:
        """Stub implementation if real one can't be imported"""
        @staticmethod
        def get_current_event():
            return None


class APIExplorer(QWidget):
    """
    Interactive explorer for the Input Data API.
    
    This widget provides a GUI for exploring and testing all methods
    of the InputDataAPI in real-time while the application is running.
    """
    
    def __init__(self, parent=None):
        """Initialize the API Explorer widget."""
        super().__init__(parent)
        self.setWindowTitle("Input Data API Explorer")
        self.resize(1000, 800)
        
        # Application theme colors for consistent look
        self.dark_bg = "#2D2D30"
        self.dark_frame_bg = "#252526"
        self.darker_frame_bg = "#1E1E1E"
        self.text_color = "#E0E0E0"
        self.accent_color = "#007ACC"
        self.success_color = "#5FB878"
        self.warning_color = "#FFAA33"
        self.error_color = "#FF5555"
        
        # Store references to current callback IDs for cleanup
        self.active_callbacks = []
        
        # Create UI with error handling
        try:
            self.create_ui()
            
            # Load API methods
            self.load_api_methods()
            
            # Start periodic updates for registered callbacks
            self.update_timer = QTimer(self)
            self.update_timer.timeout.connect(self.update_output)
            self.update_timer.start(100)  # Update every 100ms for more responsiveness
            
        except Exception as e:
            print(f"Error initializing API Explorer: {e}")
            import traceback
            traceback.print_exc()
            
            # Create a minimal UI to show the error
            self._create_error_ui(str(e))
    
    def _create_error_ui(self, error_message):
        """Create a minimal UI to display an error message."""
        layout = QVBoxLayout(self)
        
        error_label = QLabel("Error initializing API Explorer:")
        error_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FF5555;")
        layout.addWidget(error_label)
        
        message = QTextEdit()
        message.setReadOnly(True)
        message.setText(error_message)
        message.setStyleSheet(f"background-color: {self.dark_frame_bg}; color: {self.text_color}; border: 1px solid #555;")
        layout.addWidget(message)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        
    def create_ui(self):
        """Create the user interface."""
        self.setStyleSheet(f"""
            QWidget {{ background-color: {self.dark_bg}; color: {self.text_color}; }}
            QTreeWidget {{ background-color: {self.dark_frame_bg}; color: {self.text_color}; border: 1px solid #555; }}
            QTextEdit {{ background-color: {self.dark_frame_bg}; color: {self.text_color}; border: 1px solid #555; font-family: monospace; }}
            QGroupBox {{ border: 1px solid #555; border-radius: 3px; margin-top: 0.5em; }}
            QGroupBox::title {{ color: {self.accent_color}; subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }}
            QPushButton {{ background-color: {self.accent_color}; color: white; padding: 5px; border: none; }}
            QPushButton:hover {{ background-color: #0088CC; }}
            QPushButton:disabled {{ background-color: #555555; color: #AAAAAA; }}
            QComboBox, QSpinBox {{ background-color: {self.dark_frame_bg}; color: {self.text_color}; border: 1px solid #555; }}
            QLabel {{ color: {self.text_color}; }}
            QTabWidget::pane {{ border: 1px solid #555; }}
            QTabBar::tab {{ background-color: {self.dark_frame_bg}; color: {self.text_color}; padding: 5px 10px; }}
            QTabBar::tab:selected {{ background-color: {self.accent_color}; }}
        """)
        
        main_layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Input Data API Explorer")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #007ACC; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "This explorer allows you to test all methods of the InputDataAPI in real-time.\n"
            "Select a method from the tree to see its documentation and test it interactively."
        )
        desc_label.setStyleSheet("font-size: 12px; margin-bottom: 15px;")
        main_layout.addWidget(desc_label)
        
        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)
        
        # Left panel - Method tree
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        method_label = QLabel("Available Methods")
        method_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(method_label)
        
        self.method_tree = QTreeWidget()
        self.method_tree.setHeaderLabels(["Method"])
        self.method_tree.setMinimumWidth(200)
        self.method_tree.itemClicked.connect(self.on_method_selected)
        left_layout.addWidget(self.method_tree, 1)
        
        # Right panel - Method details and execution
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Method info section
        info_group = QGroupBox("Method Information")
        info_layout = QVBoxLayout(info_group)
        
        self.method_name_label = QLabel("Select a method")
        self.method_name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #007ACC;")
        info_layout.addWidget(self.method_name_label)
        
        self.method_doc_text = QTextEdit()
        self.method_doc_text.setReadOnly(True)
        # Improved contrast for method documentation
        self.method_doc_text.setStyleSheet(f"background-color: {self.dark_frame_bg}; color: {self.text_color}; border: 1px solid #555;")
        self.method_doc_text.setMaximumHeight(150)
        info_layout.addWidget(self.method_doc_text)
        
        right_layout.addWidget(info_group)
        
        # Parameters section
        params_group = QGroupBox("Parameters")
        self.params_layout = QFormLayout(params_group)
        self.param_widgets = {}  # Stores parameter input widgets
        
        # Add placeholder text
        self.params_placeholder = QLabel("Select a method to see its parameters")
        self.params_layout.addRow(self.params_placeholder)
        
        right_layout.addWidget(params_group)
        
        # Execute button
        self.execute_button = QPushButton("Execute Method")
        self.execute_button.setEnabled(False)
        self.execute_button.clicked.connect(self.execute_method)
        self.execute_button.setStyleSheet(f"background-color: {self.accent_color}; color: white; padding: 5px;")
        right_layout.addWidget(self.execute_button)
        
        # Results section with tabs for different views
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)
        
        # Tab widget for different result views
        self.results_tabs = QTabWidget()
        
        # Raw output tab
        self.raw_results_text = QTextEdit()
        self.raw_results_text.setReadOnly(True)
        self.raw_results_text.setStyleSheet(f"background-color: {self.darker_frame_bg}; color: {self.text_color}; font-family: monospace;")
        self.results_tabs.addTab(self.raw_results_text, "Raw Output")
        
        # Real-time tab for continuous monitoring
        self.realtime_widget = QWidget()
        realtime_layout = QVBoxLayout(self.realtime_widget)
        
        self.realtime_text = QTextEdit()
        self.realtime_text.setReadOnly(True)
        self.realtime_text.setStyleSheet(f"background-color: {self.darker_frame_bg}; color: {self.text_color}; font-family: monospace;")
        
        realtime_controls = QHBoxLayout()
        self.auto_update_check = QCheckBox("Enable automatic updates")
        self.auto_update_check.setChecked(True)
        self.auto_update_check.toggled.connect(self.toggle_auto_update)
        
        self.update_interval_spin = QSpinBox()
        self.update_interval_spin.setRange(100, 2000)
        self.update_interval_spin.setValue(500)
        self.update_interval_spin.setSingleStep(100)
        self.update_interval_spin.setSuffix(" ms")
        self.update_interval_spin.valueChanged.connect(self.set_update_interval)
        
        realtime_controls.addWidget(self.auto_update_check)
        realtime_controls.addWidget(QLabel("Update interval:"))
        realtime_controls.addWidget(self.update_interval_spin)
        realtime_controls.addStretch()
        
        realtime_layout.addLayout(realtime_controls)
        realtime_layout.addWidget(self.realtime_text)
        
        self.results_tabs.addTab(self.realtime_widget, "Real-time Monitor")
        
        # Event log tab for callback events
        self.event_log_text = QTextEdit()
        self.event_log_text.setReadOnly(True)
        self.event_log_text.setStyleSheet(f"background-color: {self.darker_frame_bg}; color: {self.text_color}; font-family: monospace;")
        
        self.results_tabs.addTab(self.event_log_text, "Event Log")
        
        results_layout.addWidget(self.results_tabs)
        right_layout.addWidget(results_group, 1)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 800])
        
        # Callback controls section
        callback_group = QGroupBox("Event Callbacks")
        callback_layout = QHBoxLayout(callback_group)
        
        self.register_callback_button = QPushButton("Register for Event Callbacks")
        self.register_callback_button.clicked.connect(self.register_callback)
        callback_layout.addWidget(self.register_callback_button)
        
        self.unregister_callbacks_button = QPushButton("Unregister All Callbacks")
        self.unregister_callbacks_button.clicked.connect(self.unregister_all_callbacks)
        self.unregister_callbacks_button.setEnabled(False)
        callback_layout.addWidget(self.unregister_callbacks_button)
        
        self.clear_log_button = QPushButton("Clear Event Log")
        self.clear_log_button.clicked.connect(lambda: self.event_log_text.clear())
        callback_layout.addWidget(self.clear_log_button)
        
        # Add clear buttons for other tabs
        self.clear_raw_button = QPushButton("Clear Raw Output")
        self.clear_raw_button.clicked.connect(lambda: self.raw_results_text.clear())
        callback_layout.addWidget(self.clear_raw_button)
        
        main_layout.addWidget(callback_group)
        
    def load_api_methods(self):
        """Load all methods from the InputDataAPI class."""
        try:
            # Clear existing items
            self.method_tree.clear()
            
            # Get all methods from InputDataAPI
            methods = inspect.getmembers(InputDataAPI, predicate=inspect.isfunction)
            
            # Group methods by category with descriptions
            categories = {
                "State Methods": {
                    "description": "Methods that return current input state information",
                    "methods": [
                        "get_active_keys",      # Get all currently active keys
                        "is_key_active",        # Check if a specific key is active
                        "get_mouse_position",   # Get current mouse coordinates
                        "get_mouse_button_state", # Check if a mouse button is pressed
                        "is_mouse_moving",      # Check if mouse is currently moving
                        "get_mouse_direction",  # Get current mouse movement direction
                        "get_metadata",         # Get all input metadata
                    ]
                },
                "Event Methods": {
                    "description": "Methods that return recent input events",
                    "methods": [
                        "get_current_event",    # Get most recent input event
                        "get_key_events",       # Get recent keyboard events
                        "get_mouse_movement_events", # Get recent mouse movement events
                        "get_mouse_button_events",   # Get recent mouse button events
                    ]
                },
                "Callback Methods": {
                    "description": "Methods for registering event callbacks",
                    "methods": [
                        "register_event_callback",   # Register for event notifications
                        "unregister_event_callback", # Unregister a callback
                    ]
                },
                "Controller Methods": {
                    "description": "Methods for controller-related information",
                    "methods": [
                        "is_controller_connected", # Check if controller is connected
                        "get_controller_name",     # Get name of connected controller
                        "get_controller_events",   # Get recent controller events
                    ]
                }
            }
            
            # Create category items with descriptions stored as data
            for category_name, category_data in categories.items():
                category_item = QTreeWidgetItem([category_name])
                category_item.setExpanded(True)
                # Store category description in user data
                category_item.setData(0, Qt.UserRole + 1, category_data["description"])
                self.method_tree.addTopLevelItem(category_item)
                
                # Add methods to this category
                for method_name in category_data["methods"]:
                    # Find the method object
                    method_obj = None
                    for name, obj in methods:
                        if name == method_name:
                            method_obj = obj
                            break
                            
                    if method_obj:
                        method_item = QTreeWidgetItem([method_name])
                        method_item.setData(0, Qt.UserRole, method_obj)
                        category_item.addChild(method_item)
            
        except Exception as e:
            print(f"Error loading API methods: {e}")
            import traceback
            traceback.print_exc()
            
            # Add an error indicator to the tree
            error_item = QTreeWidgetItem(["Error loading methods"])
            error_item.setForeground(0, QColor("#FF5555"))
            self.method_tree.addTopLevelItem(error_item)
        
    def on_method_selected(self, item, column):
        """Handle method selection in the tree."""
        try:
            # Clear results from previous method
            self.raw_results_text.clear()
            
            # Check if this is a category item
            if item.parent() is None:  # Top-level item
                # Show category description
                self.method_name_label.setText(item.text(0))
                category_desc = item.data(0, Qt.UserRole + 1)
                if category_desc:
                    self.method_doc_text.setText(category_desc)
                else:
                    self.method_doc_text.setText("Group of related API methods")
            
                # Clear parameters and disable execute button
                self.clear_params()
                self.execute_button.setEnabled(False)
                self.current_method = None
                self.current_method_name = None
                return
                
            # Get method object
            method_obj = item.data(0, Qt.UserRole)
            if not method_obj:
                # Disable execute button if no valid method
                self.execute_button.setEnabled(False)
                self.current_method = None
                self.current_method_name = None
                return
                
            # Update method information
            method_name = item.text(0)
            self.method_name_label.setText(method_name)
            
            # Get method documentation
            doc = inspect.getdoc(method_obj) or "No documentation available"
            self.method_doc_text.setText(doc)
            
            # Clear previous parameter widgets
            self.clear_params()
            
            # Get method parameters
            params = inspect.signature(method_obj).parameters
            
            if params:
                for name, param in params.items():
                    # Skip 'cls' parameter which is used for class methods
                    if name == 'cls':
                        continue
                        
                    # Create appropriate widget based on parameter type
                    widget = self.create_param_widget(name, param)
                    if widget:
                        self.params_layout.addRow(f"{name}:", widget)
                        self.param_widgets[name] = widget
            else:
                # No parameters
                self.params_placeholder.setText("This method doesn't take any parameters")
                self.params_layout.addRow(self.params_placeholder)
        
            # Enable execute button
            self.execute_button.setEnabled(True)
            self.current_method = method_obj
            self.current_method_name = method_name
        except Exception as e:
            print(f"Error selecting method: {e}")
            import traceback
            traceback.print_exc()
            
            self.method_doc_text.setText(f"Error: {str(e)}")
            self.execute_button.setEnabled(False)
            self.current_method = None
            self.current_method_name = None

    def clear_params(self):
        """Clear parameter widgets."""
        self.param_widgets = {}
        
        # Remove all widgets from layout
        while self.params_layout.rowCount() > 0:
            self.params_layout.removeRow(0)
            
        # Add placeholder back
        self.params_placeholder = QLabel("Parameters for this method")
        self.params_layout.addRow(self.params_placeholder)
        
    def create_param_widget(self, name, param):
        """Create an appropriate widget for a parameter."""
        # Default value
        default = param.default if param.default is not param.empty else None
        
        # Try to determine parameter type
        param_type = None
        if param.annotation is not param.empty:
            param_type = param.annotation
            
        # Create widget based on name and type
        if name == "max_count":
            # Number input for max_count
            widget = QSpinBox()
            widget.setMinimum(0)
            widget.setMaximum(1000)
            if default is not None:
                widget.setValue(default)
            else:
                widget.setValue(10) # Reasonable default for max_count
            return widget
            
        elif name == "callback_id":
            # Dropdown for active callback IDs
            widget = QComboBox()
            for callback_id in self.active_callbacks:
                widget.addItem(str(callback_id))
            return widget
            
        elif name == "key":
            # Dropdown for common keys
            widget = QComboBox()
            widget.setEditable(True)
            
            common_keys = [
                "w", "a", "s", "d", "Key.space", "Key.shift", 
                "Button.left", "Button.right", "1", "2", "c", "m"
            ]
            widget.addItems(common_keys)
            
            # Add active keys for more contextual options
            try:
                active_keys = InputDataAPI.get_active_keys()
                for key in active_keys:
                    if key not in common_keys:
                        widget.addItem(key)
            except:
                pass
                
            return widget
            
        elif name == "button":
            # Dropdown for mouse buttons
            widget = QComboBox()
            widget.addItems(["left", "right", "middle"])
            return widget
            
        elif name == "callback":
            # Callback is handled specially
            label = QLabel("Handled internally")
            return label
            
        else:
            # Default to text input
            widget = QLineEdit()
            if default is not None:
                widget.setText(str(default))
            return widget
    
    def get_param_value(self, name, widget):
        """Get the value from a parameter widget."""
        if isinstance(widget, QSpinBox):
            return widget.value()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        elif isinstance(widget, QLineEdit):
            # Try to convert to appropriate type
            value = widget.text()
            
            # Try to convert to number if it looks like one
            if value.isdigit():
                return int(value)
            try:
                return float(value)
            except:
                return value
        
        return None
    
    def execute_method(self):
        """Execute the currently selected method with parameters."""
        if not hasattr(self, 'current_method') or self.current_method is None:
            self.display_error("No method selected")
            return
            
        # Collect parameter values
        params = {}
        for name, widget in self.param_widgets.items():
            # Skip special case for callback
            if name == "callback":
                continue
                
            params[name] = self.get_param_value(name, widget)
            
        # Handle special case for register_event_callback
        if self.current_method_name == "register_event_callback":
            self.register_callback()
            return
            
        # Handle special case for unregister_event_callback
        if self.current_method_name == "unregister_event_callback":
            if 'callback_id' in params:
                self.unregister_callback(params['callback_id'])
            return
            
        # Execute method
        try:
            result = self.current_method(**params)
            self.display_result(result)
            
            # Also update the real-time monitor immediately
            if self.auto_update_check.isChecked():
                self.update_realtime_output()
                
        except Exception as e:
            self.display_error(str(e))
            
    def display_result(self, result):
        """Display the raw result of a method execution."""
        self.raw_results_text.setTextColor(QColor("#FFFFFF"))
        
        if result is None:
            self.raw_results_text.append(f"Result: None")
            return
            
        # Display raw result with minimal formatting
        # Just convert to string and display, no special formatting
        result_str = str(result)
        
        # For lists of objects, display them one per line for clarity
        if isinstance(result, (list, tuple)) and len(result) > 0:
            self.raw_results_text.append(f"Result (List with {len(result)} items):")
            for i, item in enumerate(result):
                self.raw_results_text.append(f"  [{i}]: {str(item)}")
        else:
            self.raw_results_text.append(f"Result: {result_str}")
            
        # Add timestamp
        self.raw_results_text.append(f"Time: {time.strftime('%H:%M:%S.%f')[:-3]}")
        
        # Scroll to bottom
        self.raw_results_text.moveCursor(QTextCursor.End)
        
    def display_error(self, error_msg):
        """Display an error message."""
        self.raw_results_text.setTextColor(QColor("#FF5555"))
        self.raw_results_text.append(f"Error: {error_msg}")
        self.raw_results_text.append(f"Time: {time.strftime('%H:%M:%S.%f')[:-3]}")
        self.raw_results_text.setTextColor(QColor("#FFFFFF"))
        
        # Scroll to bottom
        self.raw_results_text.moveCursor(QTextCursor.End)
        
    def toggle_auto_update(self, enabled):
        """Toggle automatic updates."""
        if enabled:
            # Update interval from spinbox (ms)
            interval = self.update_interval_spin.value()
            self.update_timer.start(interval)
        else:
            self.update_timer.stop()
    
    def set_update_interval(self, value):
        """Set the update interval for auto-updates."""
        if self.auto_update_check.isChecked():
            self.update_timer.start(value)
            
    def update_output(self):
        """Update the output with current data if auto-update is enabled."""
        try:
            if not self.auto_update_check.isChecked():
                return
                
            # Only update real-time tab content if it's visible
            current_tab_index = self.results_tabs.currentIndex()
            if current_tab_index == self.results_tabs.indexOf(self.realtime_widget):
                self.update_realtime_output()
                
        except Exception as e:
            print(f"Error in update_output: {e}")
            import traceback
            traceback.print_exc()
    
    def update_realtime_output(self):
        """Update the real-time monitor with current data."""
        try:
            # Clear previous content
            self.realtime_text.clear()
            
            # Safely get data, with proper exception handling for each call
            try:
                active_keys = InputDataAPI.get_active_keys()
                self.realtime_text.append(f"Active Keys: {active_keys}")
            except Exception as e:
                self.realtime_text.append(f"Error getting active keys: {e}")
                
            try:
                mouse_x, mouse_y = InputDataAPI.get_mouse_position()
                # Use string formatting that handles None values safely
                self.realtime_text.append(f"Mouse Position: ({mouse_x or 0}, {mouse_y or 0})")
            except Exception as e:
                self.realtime_text.append(f"Error getting mouse position: {e}")
                
            try:
                left = "Pressed" if InputDataAPI.get_mouse_button_state("left") else "Released"
                right = "Pressed" if InputDataAPI.get_mouse_button_state("right") else "Released"
                self.realtime_text.append(f"Mouse Buttons: Left: {left}, Right: {right}")
            except Exception as e:
                self.realtime_text.append(f"Error getting mouse button state: {e}")
                
            try:
                is_moving = InputDataAPI.is_mouse_moving()
                direction = InputDataAPI.get_mouse_direction()
                movement_text = f"Mouse Movement: {'Moving' if is_moving else 'Still'}"
                if direction:
                    movement_text += f" (Direction: {direction})"
                self.realtime_text.append(movement_text)
            except Exception as e:
                self.realtime_text.append(f"Error getting mouse movement: {e}")
                
            try:
                current_event = InputDataAPI.get_current_event()
                if current_event:
                    self.realtime_text.append("\nCurrent Event:")
                    self.realtime_text.append(f"  Type: {current_event.event_type}")
                    self.realtime_text.append(f"  Timestamp: {current_event.timestamp}")
                    
                    # Safely show event details
                    if hasattr(current_event, 'key') and current_event.key:
                        self.realtime_text.append(f"  Key: {current_event.key}")
                    
                    if hasattr(current_event, 'button_pressed') and current_event.button_pressed:
                        self.realtime_text.append(f"  Button: {current_event.button_pressed}")
                        
                    if hasattr(current_event, 'direction') and current_event.direction:
                        self.realtime_text.append(f"  Direction: {current_event.direction}")
            except Exception as e:
                self.realtime_text.append(f"Error getting current event: {e}")
            
            # Add timestamp
            self.realtime_text.append(f"\nLast Update: {time.strftime('%H:%M:%S.%f')[:-3]}")
            
        except Exception as e:
            self.realtime_text.setTextColor(QColor("#FF5555"))
            self.realtime_text.append(f"Error updating real-time display: {e}")
            self.realtime_text.setTextColor(QColor("#FFFFFF"))
            
        # Scroll to top to see the most important info first
        self.realtime_text.moveCursor(QTextCursor.Start)
    
    def callback_handler(self, event):
        """Handle event callbacks from API."""
        try:
            # Display received event in event log tab
            self.event_log_text.setTextColor(QColor("#5FB878"))  # Success color
            self.event_log_text.append(f"EVENT - Type: {event.event_type}")
            
            # Display event data as raw content
            self.event_log_text.setTextColor(QColor("#FFFFFF"))
            
            # Show key info if available
            if hasattr(event, 'key') and event.key:
                self.event_log_text.append(f"  Key: {event.key}")
                
            # Show active keys if available
            if hasattr(event, 'active_keys') and event.active_keys:
                self.event_log_text.append(f"  Active keys: {event.active_keys}")
                
            # Show mouse position if available
            if hasattr(event, 'mouse_x') and hasattr(event, 'mouse_y') and \
               event.mouse_x is not None and event.mouse_y is not None:
                self.event_log_text.append(f"  Mouse pos: ({event.mouse_x}, {event.mouse_y})")
                
            # Show direction if available
            if hasattr(event, 'direction') and event.direction:
                self.event_log_text.append(f"  Direction: {event.direction}")
                
            # Show timestamp
            self.event_log_text.append(f"  Timestamp: {event.timestamp}")
            self.event_log_text.append(f"  Time: {time.strftime('%H:%M:%S.%f')[:-3]}\n")
            
            # Switch to event log tab to show new events when they arrive
            self.results_tabs.setCurrentIndex(self.results_tabs.indexOf(self.event_log_text))
            
            # Auto-scroll to bottom to see newest events
            self.event_log_text.moveCursor(QTextCursor.End)
            
        except Exception as e:
            self.event_log_text.setTextColor(QColor("#FF5555"))
            self.event_log_text.append(f"Error processing event: {e}")
            self.event_log_text.setTextColor(QColor("#FFFFFF"))
            
    def register_callback(self):
        """Register for event callbacks."""
        try:
            callback_id = InputDataAPI.register_event_callback(self.callback_handler)
            self.active_callbacks.append(callback_id)
            
            self.event_log_text.setTextColor(QColor("#5FB878"))
            self.event_log_text.append(f"Registered event callback with ID: {callback_id}")
            self.event_log_text.append("Waiting for events...\n")
            self.event_log_text.setTextColor(QColor("#FFFFFF"))
            
            # Enable unregister button
            self.unregister_callbacks_button.setEnabled(True)
            
            # Switch to event log tab
            self.results_tabs.setCurrentIndex(self.results_tabs.indexOf(self.event_log_text))
            
        except Exception as e:
            self.display_error(f"Failed to register callback: {str(e)}")
            
    def unregister_callback(self, callback_id):
        """Unregister a specific callback."""
        try:
            success = InputDataAPI.unregister_event_callback(int(callback_id))
            
            if success:
                if callback_id in self.active_callbacks:
                    self.active_callbacks.remove(callback_id)
                    
                self.event_log_text.setTextColor(QColor("#5FB878"))
                self.event_log_text.append(f"Unregistered callback with ID: {callback_id}")
                self.event_log_text.setTextColor(QColor("#FFFFFF"))
            else:
                self.event_log_text.setTextColor(QColor("#FF5555"))
                self.event_log_text.append(f"Failed to unregister callback with ID: {callback_id}")
                self.event_log_text.setTextColor(QColor("#FFFFFF"))
                
            # Disable unregister button if no callbacks left
            if not self.active_callbacks:
                self.unregister_callbacks_button.setEnabled(False)
                
        except Exception as e:
            self.event_log_text.setTextColor(QColor("#FF5555"))
            self.event_log_text.append(f"Error unregistering callback: {e}")
            self.event_log_text.setTextColor(QColor("#FFFFFF"))
            
    def unregister_all_callbacks(self):
        """Unregister all active callbacks."""
        for callback_id in self.active_callbacks[:]:
            self.unregister_callback(callback_id)
            
    def closeEvent(self, event):
        """Handle window close event."""
        # Unregister all callbacks when window closes
        self.unregister_all_callbacks()
        event.accept()
