"""
UI manager module.

Manages the user interface components and layout for the input collector application.
"""

import time
from typing import Optional, Callable, Dict, Any, List
from PyQt5.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QCheckBox, QPushButton, QComboBox, QTextEdit, QFrame, QSlider, QLineEdit,
    QSizePolicy, QScrollArea, QFileDialog, QApplication
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QObject
from PyQt5.QtGui import QPalette, QColor, QTextCursor, QFont

from ..visualizers import KeyboardVisualizer, MouseVisualizer, MouseButtonsSelector


class UIManager(QObject):
    """
    Manages the user interface for the input collector application.
    
    This class is responsible for creating, configuring, and updating
    the user interface components.
    """
    
    # Signals for UI actions
    toggle_recording = pyqtSignal()
    toggle_json_logging = pyqtSignal(bool)
    toggle_csv_logging = pyqtSignal(bool)
    select_csv_path = pyqtSignal()
    switch_collector = pyqtSignal(str)
    scan_controllers = pyqtSignal()
    toggle_edit_mode = pyqtSignal()
    update_tracking_mode = pyqtSignal()
    set_mouse_tracking_mode = pyqtSignal(str)
    apply_mouse_settings = pyqtSignal()
    toggle_fullscreen = pyqtSignal()
    mouse_button_toggled = pyqtSignal(str, bool)
    # Remove capture_scroll_changed signal
    
    def __init__(self, main_window: QMainWindow) -> None:
        """
        Initialize the UI manager.
        
        Args:
            main_window: The main application window
        """
        super().__init__()
        self.main_window = main_window
        
        # Define theme colors
        self.dark_bg = "#2D2D30"
        self.dark_frame_bg = "#252526"
        self.text_color = "#E0E0E0"
        self.accent_color = "#007ACC"
        self.success_color = "#5FB878"
        self.warning_color = "#FFAA33"
        self.error_color = "#FF5555"
        
        # Store references to key UI components
        self.components = {}
        
        # Create UI
        self._set_dark_theme()
        self._create_ui()
    
    def _set_dark_theme(self) -> None:
        """Set the application to use a dark theme."""
        palette = QPalette()

        # Set colors
        palette.setColor(QPalette.Window, QColor(self.dark_bg))
        palette.setColor(QPalette.WindowText, QColor(self.text_color))
        palette.setColor(QPalette.Base, QColor(self.dark_frame_bg))
        palette.setColor(QPalette.AlternateBase, QColor(self.dark_bg))
        palette.setColor(QPalette.ToolTipBase, QColor(self.dark_bg))
        palette.setColor(QPalette.ToolTipText, QColor(self.text_color))
        palette.setColor(QPalette.Text, QColor(self.text_color))
        palette.setColor(QPalette.Button, QColor(self.dark_bg))
        palette.setColor(QPalette.ButtonText, QColor(self.text_color))
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(self.accent_color))
        palette.setColor(QPalette.Highlight, QColor(self.accent_color))
        palette.setColor(QPalette.HighlightedText, Qt.white)

        QApplication.setPalette(palette)

        # Set stylesheet for detailed control
        self.main_window.setStyleSheet(
            f"""
            QMainWindow, QWidget {{ background-color: {self.dark_bg}; color: {self.text_color}; }}
            QGroupBox {{
                border: 1px solid #444;
                margin-top: 0.5em;
                border-radius: 3px;
                padding: 0.5em;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: {self.text_color};
            }}
            QPushButton {{
                background-color: {self.accent_color};
                color: white;
                border: none;
                padding: 4px 8px;
                min-height: 24px;
                border-radius: 2px;
            }}
            QPushButton:pressed {{ background-color: #005599; }}
            QPushButton:hover {{ background-color: #0066aa; }}
            QPushButton:disabled {{
                background-color: #555555;
                color: #999999;
            }}
            QComboBox:disabled {{
                background-color: #444444;
                color: #888888;
                border: 1px solid #333333;
            }}
            QCheckBox:disabled {{
                color: #888888;
            }}
            QCheckBox::indicator:disabled {{
                border: 1px solid #555555;
                background-color: #444444;
            }}
            QLineEdit, QTextEdit, QListWidget, QComboBox {{
                background-color: {self.dark_frame_bg};
                color: {self.text_color};
                border: 1px solid #444;
                padding: 2px;
                border-radius: 2px;
            }}
            QTextEdit {{ font-family: 'Consolas', monospace; }}
            QComboBox::drop-down {{ border: 0px; }}
            QComboBox::down-arrow {{
                image: url(dropdown.png);
                width: 12px;
                height: 12px;
            }}
            QSlider::groove:horizontal {{
                border: 1px solid #444;
                height: 8px;
                background: {self.dark_frame_bg};
                margin: 2px 0;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {self.accent_color};
                border: none;
                width: 18px;
                margin: -2px 0;
                border-radius: 4px;
            }}
            QCheckBox::indicator {{
                width: 13px;
                height: 13px;
                border: 1px solid #444;
                border-radius: 2px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.accent_color};
            }}
            QLabel {{ color: {self.text_color}; }}
        """
        )

    def _create_ui(self) -> None:
        """Create the application UI components."""
        # Create a scroll area for the main window to enable scrolling
        self.main_scroll = QScrollArea()
        self.main_scroll.setWidgetResizable(True)
        self.main_scroll.setFrameShape(QFrame.NoFrame)
        self.main_window.setCentralWidget(self.main_scroll)
        
        # Central widget inside scroll area
        central_widget = QWidget()
        self.main_scroll.setWidget(central_widget)

        # Main layout
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(8)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Store main layout in components for easier access
        self.components['main_layout'] = self.main_layout

        # Set up control panel at top
        self._create_control_panel()
        
        # Create visualization area - the visualizers will be added later
        viz_layout = QHBoxLayout()
        self.components['viz_layout'] = viz_layout
        
        # Placeholder for keyboard visualization + mouse buttons (left side)
        self.left_viz_layout = QVBoxLayout()
        self.components['left_viz_layout'] = self.left_viz_layout
        
        # Placeholders for groups that will contain visualizers
        self.keyboard_group = QGroupBox("Keyboard Input")
        self.keyboard_layout = QVBoxLayout(self.keyboard_group)
        self.components['keyboard_group'] = self.keyboard_group
        self.components['keyboard_layout'] = self.keyboard_layout
        
        self.mouse_buttons_group = QGroupBox("Mouse Buttons")
        self.mouse_buttons_layout = QVBoxLayout(self.mouse_buttons_group)
        self.components['mouse_buttons_group'] = self.mouse_buttons_group
        self.components['mouse_buttons_layout'] = self.mouse_buttons_layout
        
        # Set a fixed height for mouse buttons
        self.mouse_buttons_group.setFixedHeight(120)
        
        # Add keyboard and mouse buttons groups to left layout
        self.left_viz_layout.addWidget(self.keyboard_group, 3)
        self.left_viz_layout.addWidget(self.mouse_buttons_group, 0)
        self.left_viz_layout.addStretch(1)
        
        # Placeholder for mouse visualization (right side)
        self.mouse_group = QGroupBox("Mouse Input")
        self.mouse_layout = QVBoxLayout(self.mouse_group)
        self.components['mouse_group'] = self.mouse_group
        self.components['mouse_layout'] = self.mouse_layout
        
        # Placeholder for PS4 controller visualization
        self.ps4_controller_group = QGroupBox("PS4 Controller")
        self.ps4_controller_layout = QVBoxLayout(self.ps4_controller_group)
        self.components['ps4_controller_group'] = self.ps4_controller_group
        self.components['ps4_controller_layout'] = self.ps4_controller_layout
        self.ps4_controller_group.setVisible(False)  # Hide by default
        
        # Add left and right sides to visualization layout
        viz_layout.addLayout(self.left_viz_layout, 55)
        viz_layout.addWidget(self.mouse_group, 45)
        
        # Add visualization layout to main layout
        self.main_layout.addLayout(viz_layout, 4)
        
        # Add other UI components (active keys, status, settings)
        self._create_active_keys_display()
        self._create_status_area()
        self._create_mouse_settings()

    def _create_control_panel(self) -> None:
        """Create the control panel with recording and collector controls."""
        # Control panel layout
        control_panel = QHBoxLayout()
        
        # Recording controls
        recording_frame = QHBoxLayout()
        
        # Record button
        self.components['record_button'] = QPushButton("Record")
        self.components['record_button'].setStyleSheet("background-color: #AA3333; color: white;")
        self.components['record_button'].clicked.connect(self._on_record_button_clicked)
        recording_frame.addWidget(self.components['record_button'])
        
        # JSON logging checkbox
        self.components['log_checkbox'] = QCheckBox("Log JSON")
        self.components['log_checkbox'].toggled.connect(lambda checked: self.toggle_json_logging.emit(checked))
        recording_frame.addWidget(self.components['log_checkbox'])
        
        # CSV logging checkbox
        self.components['csv_checkbox'] = QCheckBox("Log CSV")
        self.components['csv_checkbox'].toggled.connect(lambda checked: self.toggle_csv_logging.emit(checked))
        recording_frame.addWidget(self.components['csv_checkbox'])
        
        # CSV path controls
        self.components['csv_path_label'] = QLabel("Path:")
        recording_frame.addWidget(self.components['csv_path_label'])
        
        self.components['csv_path_field'] = QLineEdit()
        self.components['csv_path_field'].setPlaceholderText("Select CSV file location...")
        self.components['csv_path_field'].setReadOnly(True)
        recording_frame.addWidget(self.components['csv_path_field'], 1)
        
        self.components['csv_path_button'] = QPushButton("Browse...")
        self.components['csv_path_button'].clicked.connect(lambda: self.select_csv_path.emit())
        recording_frame.addWidget(self.components['csv_path_button'])
        
        # Status label
        self.components['status_label'] = QLabel("Not Recording")
        recording_frame.addWidget(self.components['status_label'])
        
        # Add recording controls to main control panel
        control_panel.addLayout(recording_frame)
        control_panel.addStretch(1)
        
        # Collector selector
        collector_layout = QHBoxLayout()
        collector_layout.addWidget(QLabel("Input:"))
        
        # Create collector selector with a default item to verify it's working
        self.components['collector_selector'] = QComboBox()
        self.components['collector_selector'].setMinimumWidth(120)
        # Add a placeholder item to verify combobox is working
        self.components['collector_selector'].addItem("Loading...", "placeholder")
        self.components['collector_selector'].currentTextChanged.connect(
            lambda text: self.switch_collector.emit(text) if text != "Loading..." else None
        )
        collector_layout.addWidget(self.components['collector_selector'])
        
        # Scan button for controllers
        self.components['scan_button'] = QPushButton("Scan")
        self.components['scan_button'].clicked.connect(lambda: self.scan_controllers.emit())
        self.components['scan_button'].setFixedWidth(60)
        # Make the scan button more visible
        self.components['scan_button'].setStyleSheet("background-color: #444466; color: white;")
        self.components['scan_button'].setToolTip("Scan for game controllers")
        collector_layout.addWidget(self.components['scan_button'])
        
        control_panel.addLayout(collector_layout)
        
        # Edit keys button
        self.components['edit_keys_button'] = QPushButton("Edit Keys")
        self.components['edit_keys_button'].clicked.connect(lambda: self.toggle_edit_mode.emit())
        self.components['edit_keys_button'].setCheckable(True)
        control_panel.addWidget(self.components['edit_keys_button'])
        
        control_panel.addStretch(1)
        
        # Mouse tracking mode controls
        mouse_mode_frame = QHBoxLayout()
        
        self.components['direction_only_check'] = QCheckBox("Dir Only")
        self.components['direction_only_check'].setChecked(True)
        self.components['direction_only_check'].toggled.connect(
            lambda: self.update_tracking_mode.emit()
        )
        mouse_mode_frame.addWidget(self.components['direction_only_check'])
        
        mouse_mode_frame.addWidget(QLabel("Mode:"))
        
        self.components['tracking_mode_combo'] = QComboBox()
        self.components['tracking_mode_combo'].addItems(["axis", "angle"])
        self.components['tracking_mode_combo'].setMinimumWidth(80)
        self.components['tracking_mode_combo'].currentTextChanged.connect(
            lambda text: self.set_mouse_tracking_mode.emit(text)
        )
        mouse_mode_frame.addWidget(self.components['tracking_mode_combo'])
        
        control_panel.addLayout(mouse_mode_frame)
        
        # Add control panel to main layout
        self.main_layout.addLayout(control_panel)
    
    def _create_active_keys_display(self) -> None:
        """Create the active keys display area."""
        active_keys_group = QGroupBox("Active Keys")
        active_keys_layout = QVBoxLayout(active_keys_group)
        self.components['active_keys_label'] = QLabel("None")
        self.components['active_keys_label'].setAlignment(Qt.AlignCenter)
        active_keys_layout.addWidget(self.components['active_keys_label'])
        self.main_layout.addWidget(active_keys_group)
    
    def _create_status_area(self) -> None:
        """Create the status area for messages."""
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        self.components['status_text'] = QTextEdit()
        self.components['status_text'].setReadOnly(True)
        self.components['status_text'].setMaximumHeight(80)
        status_layout.addWidget(self.components['status_text'])
        self.main_layout.addWidget(status_group)
    
    def _create_mouse_settings(self) -> None:
        """Create the mouse settings area."""
        self.components['mouse_settings_group'] = QGroupBox("Mouse Settings")
        settings_layout = QVBoxLayout(self.components['mouse_settings_group'])
        
        # Settings row 1
        settings_row1 = QHBoxLayout()
        
        # Delta smoothing
        delta_layout = QHBoxLayout()
        delta_layout.addWidget(QLabel("Delta Smoothing:"))
        self.components['delta_smoothing_slider'] = QSlider(Qt.Horizontal)
        self.components['delta_smoothing_slider'].setRange(0, 90)
        self.components['delta_smoothing_slider'].setValue(50)
        delta_layout.addWidget(self.components['delta_smoothing_slider'])
        settings_row1.addLayout(delta_layout)
        
        # Joystick sensitivity
        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(QLabel("Joystick Sensitivity:"))
        self.components['sensitivity_slider'] = QSlider(Qt.Horizontal)
        self.components['sensitivity_slider'].setRange(10, 200)
        self.components['sensitivity_slider'].setValue(10)
        sensitivity_layout.addWidget(self.components['sensitivity_slider'])
        settings_row1.addLayout(sensitivity_layout)
        
        settings_layout.addLayout(settings_row1)
        
        # Settings row 2
        settings_row2 = QHBoxLayout()
        
        # Angle grouping
        angle_layout = QHBoxLayout()
        angle_layout.addWidget(QLabel("Angle Grouping:"))
        self.components['angle_grouping_slider'] = QSlider(Qt.Horizontal)
        self.components['angle_grouping_slider'].setRange(1, 60)
        self.components['angle_grouping_slider'].setValue(10)
        self.components['angle_grouping_slider'].valueChanged.connect(self._update_angle_grouping_label)
        angle_layout.addWidget(self.components['angle_grouping_slider'])
        self.components['angle_grouping_label'] = QLabel("10° (36 values)")
        self.components['angle_grouping_label'].setMinimumWidth(100)
        angle_layout.addWidget(self.components['angle_grouping_label'])
        settings_row2.addLayout(angle_layout)
        
        # Add spacer to replace the checkbox
        settings_row2.addStretch(1)
        
        # Apply button
        self.components['apply_button'] = QPushButton("Apply Settings")
        self.components['apply_button'].clicked.connect(
            lambda: self.apply_mouse_settings.emit()
        )
        settings_row2.addWidget(self.components['apply_button'])
        
        settings_layout.addLayout(settings_row2)
        
        # Add settings to main layout
        self.main_layout.addWidget(self.components['mouse_settings_group'])
    
    def _update_angle_grouping_label(self) -> None:
        """Update the angle grouping label when slider changes."""
        value = self.components['angle_grouping_slider'].value()
        num_values = 360 // value if value > 0 else 360
        self.components['angle_grouping_label'].setText(f"{value}° ({num_values} values)")
    
    def set_visualizers(self, keyboard_viz: KeyboardVisualizer, 
                       mouse_viz: MouseVisualizer, 
                       mouse_buttons: MouseButtonsSelector,
                       ps4_controller_viz=None) -> None:
        """
        Add visualizers to the UI layout.
        
        Args:
            keyboard_viz: The keyboard visualizer component
            mouse_viz: The mouse visualizer component
            mouse_buttons: The mouse buttons selector component
            ps4_controller_viz: The PS4 controller visualizer component (optional)
        """
        # Add keyboard visualizer to its group
        self.components['keyboard_layout'].addWidget(keyboard_viz)
        
        # Add mouse buttons selector to its group
        self.components['mouse_buttons_layout'].addWidget(mouse_buttons)
        
        # Add mouse visualizer to its group
        self.components['mouse_layout'].addWidget(mouse_viz)
        
        # Add PS4 controller visualizer if provided
        if ps4_controller_viz is not None:
            self.components['ps4_controller_layout'].addWidget(ps4_controller_viz)

    def _on_record_button_clicked(self) -> None:
        """Handle record button clicks."""
        self.toggle_recording.emit()
    
    def update_recording_state(self, is_recording: bool) -> None:
        """
        Update UI to reflect recording state.
        
        Args:
            is_recording: Whether recording is active
        """
        record_button = self.components.get('record_button')
        status_label = self.components.get('status_label')
        
        # Get all UI components that should be disabled during recording
        edit_keys_button = self.components.get('edit_keys_button')
        collector_selector = self.components.get('collector_selector')
        scan_button = self.components.get('scan_button')
        direction_only_check = self.components.get('direction_only_check')
        tracking_mode_combo = self.components.get('tracking_mode_combo')
        
        if record_button:
            if is_recording:
                record_button.setText("Stop")
                record_button.setStyleSheet("background-color: #CC3333; color: white;")
            else:
                record_button.setText("Record")
                record_button.setStyleSheet("background-color: #AA3333; color: white;")
        
        if status_label:
            status_label.setText("RECORDING" if is_recording else "Not Recording")
        
        # Disable UI controls during recording
        if edit_keys_button:
            edit_keys_button.setEnabled(not is_recording)
        
        if collector_selector:
            collector_selector.setEnabled(not is_recording)
        
        if scan_button:
            scan_button.setEnabled(not is_recording)
            # Update button appearance based on enabled state
            if is_recording:
                scan_button.setStyleSheet("background-color: #555555; color: #999999;")
            else:
                # Restore original style based on current collector type
                collector_type = self.get_current_collector_data()
                is_keyboard_mouse = collector_type == "keyboard_mouse"
                if not is_keyboard_mouse:
                    scan_button.setStyleSheet("background-color: #5555AA; color: white; font-weight: bold;")
                else:
                    scan_button.setStyleSheet("background-color: #444466; color: white;")
        
        if direction_only_check:
            direction_only_check.setEnabled(not is_recording)
        
        if tracking_mode_combo:
            tracking_mode_combo.setEnabled(not is_recording)
    
    def update_collector_list(self, collectors: List[Dict[str, str]]) -> None:
        """
        Update the collector dropdown.
        
        Args:
            collectors: List of collector info dictionaries
        """
        print(f"UIManager: update_collector_list called with {len(collectors)} collectors")
        
        collector_selector = self.components.get('collector_selector')
        if collector_selector:
            # Verify the collector_selector is properly initialized
            print(f"UIManager: collector_selector size: {collector_selector.count()}")
            print(f"UIManager: collector_selector visible: {collector_selector.isVisible()}")
            print(f"UIManager: collector_selector enabled: {collector_selector.isEnabled()}")
            
            # Block signals to prevent triggering switch_collector during initialization
            collector_selector.blockSignals(True)
            collector_selector.clear()
            
            # Add collectors with more debug info
            for i, collector in enumerate(collectors):
                print(f"UIManager: Adding collector {i}: {collector['name']} ({collector['type']})")
                collector_selector.addItem(collector['name'], collector['type'])
            
            # Force a geometry update
            collector_selector.updateGeometry()
            collector_selector.blockSignals(False)
            
            # Verify what was added
            print(f"UIManager: After adding, collector_selector now has {collector_selector.count()} items:")
            for i in range(collector_selector.count()):
                print(f"  Item {i}: {collector_selector.itemText(i)} (data: {collector_selector.itemData(i)})")
        else:
            print("WARNING: collector_selector component not found in UIManager!")
    
    def select_collector(self, collector_type: str) -> None:
        """
        Select a collector in the UI.
        
        Args:
            collector_type: Type identifier of the collector
        """
        collector_selector = self.components.get('collector_selector')
        if collector_selector:
            print(f"UIManager: Setting current collector to: {collector_type}")
            for i in range(collector_selector.count()):
                item_data = collector_selector.itemData(i)
                print(f"UIManager: Checking item {i}: {collector_selector.itemText(i)} (data: {item_data})")
                if item_data == collector_type:
                    print(f"UIManager: Setting index to {i}")
                    collector_selector.setCurrentIndex(i)
                    break
        else:
            print("WARNING: collector_selector component not found in UIManager!")
    
    def update_ui_for_collector(self, collector_type: str, capabilities: Dict[str, Any]) -> None:
        """
        Update UI elements based on collector capabilities.
        
        Args:
            collector_type: Type of the current collector
            capabilities: Dictionary of collector capabilities
        """
        is_keyboard_mouse = collector_type == "keyboard_mouse"
        is_ps4_controller = collector_type == "ps4_controller"
        
        # Update scan button visibility and style
        scan_button = self.components.get('scan_button')
        if scan_button:
            # Always keep scan button visible but style it differently based on collector
            scan_button.setVisible(True)
            if not is_keyboard_mouse:
                # When using PS4 collector - highlight more
                scan_button.setStyleSheet("background-color: #5555AA; color: white; font-weight: bold;")
            else:
                # When using keyboard/mouse - normal style
                scan_button.setStyleSheet("background-color: #444466; color: white;")
        
        # Update mouse-specific UI elements
        mouse_tracking_supported = capabilities.get("supports_mouse_tracking", False)
        tracking_mode_combo = self.components.get('tracking_mode_combo')
        direction_only_check = self.components.get('direction_only_check')
        
        if tracking_mode_combo:
            tracking_mode_combo.setVisible(mouse_tracking_supported and is_keyboard_mouse)
        
        if direction_only_check:
            direction_only_check.setVisible(mouse_tracking_supported and is_keyboard_mouse)
        
        # Update mouse settings group visibility
        mouse_settings_group = self.components.get('mouse_settings_group')
        if mouse_settings_group:
            mouse_settings_group.setVisible(mouse_tracking_supported and is_keyboard_mouse)
            
        # Update PS4 controller group visibility
        ps4_controller_group = self.components.get('ps4_controller_group')
        if ps4_controller_group:
            # Show PS4 controller visualizer when using PS4 controller
            ps4_controller_group.setVisible(is_ps4_controller)
            
        # Update mouse group visibility
        mouse_group = self.components.get('mouse_group')
        if mouse_group:
            mouse_group.setVisible(is_keyboard_mouse)
            
        # Update viz_layout to show the right visualizer
        viz_layout = self.components.get('viz_layout')
        if viz_layout and is_ps4_controller and ps4_controller_group and mouse_group:
            # Remove mouse group and add PS4 controller group
            viz_layout.removeWidget(mouse_group)
            mouse_group.setVisible(False)
            viz_layout.addWidget(ps4_controller_group, 45)
            ps4_controller_group.setVisible(True)
        elif viz_layout and not is_ps4_controller and ps4_controller_group and mouse_group:
            # Remove PS4 controller group and add mouse group
            viz_layout.removeWidget(ps4_controller_group)
            ps4_controller_group.setVisible(False)
            viz_layout.addWidget(mouse_group, 45)
            mouse_group.setVisible(True)
    
    def set_csv_path(self, path: str) -> None:
        """
        Set the CSV path in the UI.
        
        Args:
            path: Path to the CSV file
        """
        csv_path_field = self.components.get('csv_path_field')
        if csv_path_field:
            csv_path_field.setText(path)
    
    def log_status(self, message: str, color: Optional[str] = None) -> None:
        """
        Log a message to the status area.
        
        Args:
            message: The message to log
            color: Optional color for the message
        """
        status_text = self.components.get('status_text')
        if not status_text:
            return
            
        # Get current time with millisecond precision
        current_time = time.time()
        timestamp = time.strftime("%H:%M:%S", time.localtime(current_time))
        ms = int((current_time - int(current_time)) * 1000)
        formatted_time = f"{timestamp}.{ms:03d}"

        # Format the message with HTML for color
        if color:
            html_message = f"<span style='color: #999999;'>{formatted_time} - </span><span style='color: {color};'>{message}</span>"
        else:
            html_message = (
                f"<span style='color: #999999;'>{formatted_time} - </span>{message}"
            )

        # Append the message
        status_text.append(html_message)

        # Auto-scroll to bottom
        status_text.moveCursor(QTextCursor.End)
    
    def update_active_keys_display(self, active_keys: List[str]) -> None:
        """
        Update the active keys display.
        
        Args:
            active_keys: List of currently active keys
        """
        active_keys_label = self.components.get('active_keys_label')
        if active_keys_label:
            active_keys_label.setText(", ".join(active_keys) if active_keys else "None")
    
    # Add missing methods to support InputCollectorApp
    
    def is_direction_only_mode(self) -> bool:
        """
        Check if direction-only mode is enabled.
        
        Returns:
            bool: True if direction-only mode is enabled
        """
        direction_only_check = self.components.get('direction_only_check')
        if direction_only_check:
            return direction_only_check.isChecked()
        return True  # Default to True
    
    def get_tracking_mode(self) -> str:
        """
        Get the current tracking mode.
        
        Returns:
            str: The current tracking mode
        """
        tracking_mode_combo = self.components.get('tracking_mode_combo')
        if tracking_mode_combo:
            return tracking_mode_combo.currentText()
        return "axis"  # Default to axis mode
    
    def get_angle_grouping(self) -> int:
        """
        Get the current angle grouping value.
        
        Returns:
            int: The current angle grouping value
        """
        angle_grouping_slider = self.components.get('angle_grouping_slider')
        if angle_grouping_slider:
            return angle_grouping_slider.value()
        return 10  # Default to 10 degrees
    
    def get_delta_smoothing(self) -> float:
        """
        Get the delta smoothing factor.
        
        Returns:
            float: The delta smoothing factor
        """
        delta_smoothing_slider = self.components.get('delta_smoothing_slider')
        if delta_smoothing_slider:
            return delta_smoothing_slider.value()
        return 50  # Default to 0.5 (50%)
    
    def get_joystick_sensitivity(self) -> float:
        """
        Get the joystick sensitivity value.
        
        Returns:
            float: The joystick sensitivity value
        """
        sensitivity_slider = self.components.get('sensitivity_slider')
        if sensitivity_slider:
            return sensitivity_slider.value()
        return 10  # Default to 0.1 (10%)
    
    def update_tracking_modes(self, valid_modes: List[str], current_mode: str, default_mode: str) -> None:
        """
        Update the available tracking modes in the UI.
        
        Args:
            valid_modes: List of valid tracking modes
            current_mode: The currently selected mode
            default_mode: The default mode to use if current_mode is not valid
        """
        tracking_mode_combo = self.components.get('tracking_mode_combo')
        if tracking_mode_combo:
            tracking_mode_combo.blockSignals(True)
            tracking_mode_combo.clear()
            tracking_mode_combo.addItems(valid_modes)
            
            # Set appropriate mode
            if current_mode in valid_modes:
                tracking_mode_combo.setCurrentText(current_mode)
            else:
                tracking_mode_combo.setCurrentText(default_mode)
            
            tracking_mode_combo.blockSignals(False)
    
    def get_current_collector_data(self) -> Optional[str]:
        """
        Get the data for the currently selected collector.
        
        Returns:
            Optional[str]: The collector type identifier or None if not found
        """
        collector_selector = self.components.get('collector_selector')
        if collector_selector:
            return collector_selector.currentData()
        return None
    
    def select_collector_by_type(self, collector_type: str) -> None:
        """
        Select a collector in the UI by its type.
        
        Args:
            collector_type: The type identifier of the collector to select
        """
        collector_selector = self.components.get('collector_selector')
        if collector_selector:
            for i in range(collector_selector.count()):
                if collector_selector.itemData(i) == collector_type:
                    collector_selector.setCurrentIndex(i)
                    break

    def update_edit_mode(self, enabled: bool) -> None:
        """
        Update the UI components based on edit mode state.
        
        Args:
            enabled: Whether edit mode is enabled
        """
        # Update edit keys button if it exists
        edit_keys_button = self.components.get('edit_keys_button')
        if edit_keys_button:
            edit_keys_button.setChecked(enabled)
            
            # Update button text and style based on state
            if enabled:
                edit_keys_button.setText("Finish Editing")
                edit_keys_button.setStyleSheet("background-color: #5FB878; color: white;")
            else:
                edit_keys_button.setText("Edit Keys")
                edit_keys_button.setStyleSheet("background-color: #007ACC; color: white;")
        
        # Log the edit mode state change
        self.log_status(f"Edit mode {'enabled' if enabled else 'disabled'}", 
                       "success" if enabled else "accent")
    
    def hide_recording_controls(self) -> None:
        """Hide recording controls when running in unified app."""
        # Flag to indicate we're running in unified mode
        self.in_unified_mode = True
        
        # Find and hide all recording-related controls with their actual keys
        recording_controls = [
            'record_button',      # Record button
            'log_checkbox',       # JSON logging checkbox
            'csv_checkbox',       # CSV logging checkbox
            'csv_path_field',     # CSV path edit field
            'csv_path_button',    # Browse button for CSV path
            'csv_path_label',     # "Path:" label
            'status_label'        # Recording status label
        ]
        
        # Hide components by their keys in the components dictionary
        for control_key in recording_controls:
            if control_key in self.components:
                self.components[control_key].hide()
                print(f"Hiding control: {control_key}")
            else:
                print(f"Warning: Control '{control_key}' not found in components")
        
        # Remove the direct attribute access section since these don't exist as attributes

