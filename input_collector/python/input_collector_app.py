"""
Input collector application module.

This module provides the main application for collecting, visualizing, and
logging keyboard and mouse inputs in real-time with a graphical user interface.
"""
import json
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import List, Dict, Optional, Any

from .collectors import KeyboardMouseCollector
from .interfaces import InputData
from .visualizers import KeyboardVisualizer, MouseVisualizer


class InputCollectorApp:
    """
    Main application for input collection and visualization.
    
    This class provides a graphical user interface for collecting, visualizing,
    and logging keyboard and mouse inputs in real-time. It integrates the
    input collector and visualizers into a cohesive application.
    """
    
    def __init__(self, root: Optional[tk.Tk] = None) -> None:
        """
        Initialize the application.
        
        Creates the application window, sets up the UI components, and initializes
        the input collector and visualizers.
        
        Args:
            root: Optional root tkinter window. If not provided, a new one is created.
        """
        # Define app theme colors
        self.dark_bg: str = "#2D2D30"
        self.dark_frame_bg: str = "#252526"
        self.text_color: str = "#E0E0E0"
        self.accent_color: str = "#007ACC"
        self.success_color: str = "#5FB878"
        self.warning_color: str = "#FFAA33"
        self.error_color: str = "#FF5555"
        
        # Create root window if not provided
        if root is None:
            self.root: tk.Tk = tk.Tk()
            self.root.title("Input Collector")
            self.root.geometry("800x700")
            self.root.configure(bg=self.dark_frame_bg)  # Set window background color
            
            # Configure global ttk style for dark theme
            self.style: ttk.Style = ttk.Style(self.root)
            self._configure_styles()
            
            self.owns_root: bool = True
        else:
            self.root = root
            self.owns_root = False
        
        # Create collector
        self.collector: KeyboardMouseCollector = KeyboardMouseCollector()
        
        # Enable verbose logging if needed
        # self.collector.verbose = True  # Uncomment for detailed logging
        
        # Control whether to log F3/recording control events to the UI and file logs
        self.log_control_events: bool = False
        
        # Application state
        self.is_recording: bool = False
        self.log_to_file: bool = False
        self.log_file: Optional[Any] = None
        
        # UI components
        self.record_button: Optional[tk.Button] = None
        self.status_label: Optional[ttk.Label] = None
        self.log_checkbox: Optional[ttk.Checkbutton] = None
        self.log_var: Optional[tk.BooleanVar] = None
        self.key_entry: Optional[tk.Entry] = None
        self.key_listbox: Optional[tk.Listbox] = None
        self.status_text: Optional[scrolledtext.ScrolledText] = None
        self.active_keys_label: Optional[ttk.Label] = None
        self.keyboard_viz: Optional[KeyboardVisualizer] = None
        self.mouse_viz: Optional[MouseVisualizer] = None
        
        # Create UI
        self._create_ui()
        
        # Connect collector callbacks
        self.collector.on_event(self._handle_input_event)
        
        # Set tracked keys based on requirements - remove F3 from tracked keys
        self.tracked_keys: List[str] = [
            "w", "a", "s", "d", "q", "e", "f", "m", "c", "b",
            "1", "2", "3", "4",
            "Key.space", "Key.shift", 
            "Key.media_play_pause"
        ]
        self.collector.set_supported_keys(self.tracked_keys)
        self._update_key_list()
        
        # Set the tracked keys in the keyboard visualizer for highlighting
        self.keyboard_viz.set_tracked_keys(self.tracked_keys)
        
        # Set screen dimensions for velocity-based joystick control
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.collector.set_screen_dimensions(screen_width, screen_height)
        
        # Set joystick sensitivity - LOWER value = LESS sensitive
        self.collector.set_joystick_sensitivity(0.1)
        
        # IMPORTANT: Initialize mouse tracking mode to match UI defaults
        self._set_mouse_tracking_mode(self.tracking_mode_var.get())
        
        # Bind global keyboard shortcuts for recording control
        self.root.bind("<F9>", self._toggle_recording_key)  # F9 key
        self.root.bind("<space>", self._toggle_recording_key)  # Space key 
        
        # Ensure the app captures keyboard events regardless of focus
        self.root.bind_all("<Key>", self._capture_keyboard_focus)
        
        # Start periodic UI updates
        self._schedule_ui_update()

        # Debug - print recognized key names
        print("Recognized Tkinter key names:")
        for name in self.root.tk.call("event", "info"):
            if name.startswith("<Key"):
                print(f"  {name}")
    
    def _configure_styles(self) -> None:
        """
        Configure ttk styles for dark theme.
        
        Sets up the visual styling for all ttk widgets used in the application
        to maintain a consistent dark theme appearance.
        """
        # For Windows, we need to use 'clam' theme to properly customize ttk widgets
        self.style.theme_use('clam')
        
        self.style.configure("TFrame", background=self.dark_frame_bg)
        self.style.configure("TLabel", background=self.dark_frame_bg, foreground=self.text_color)
        
        # Style for standard buttons - fix background colors
        self.style.configure("TButton", 
                            background=self.accent_color,  # Blue background
                            foreground="#FFFFFF",         # White text
                            relief=tk.FLAT,
                            borderwidth=1,
                            padding=4)
        
        # Button when pressed (active)
        self.style.map("TButton",
                      background=[('active', '#0066aa'), ('pressed', '#005599')],
                      relief=[('pressed', 'sunken')])
        
        # Special style for the record button
        self.style.configure("Record.TButton", 
                           background="#AA3333",  # Red background
                           foreground="#FFFFFF")  # White text
        
        # Record button when pressed
        self.style.map("Record.TButton",
                      background=[('active', '#BB4444'), ('pressed', '#992222')])
        
        # Style for checkbuttons
        self.style.configure("TCheckbutton", 
                            background=self.dark_frame_bg,
                            foreground=self.text_color)
        
        # Fix checkbutton indicator colors
        self.style.map("TCheckbutton",
                      indicatorcolor=[('selected', '#5FB878'), ('!selected', self.dark_bg)],
                      indicatorbackground=[('selected', self.dark_bg), ('!selected', self.dark_bg)],
                      background=[('active', self.dark_frame_bg)],
                      foreground=[('active', self.text_color)])
        
        # Style for frames and labelframes
        self.style.configure("TLabelframe", 
                           background=self.dark_frame_bg,
                           foreground=self.text_color,
                           bordercolor="#444444")
        
        self.style.configure("TLabelframe.Label", 
                           background=self.dark_frame_bg,
                           foreground=self.text_color)
        
        # Fix separator color
        self.style.configure("TSeparator",
                            background="#444444")
    
    def _create_ui(self) -> None:
        """
        Create the application UI.
        
        Builds the complete user interface with all controls, visualizers,
        and information displays arranged in a grid layout.
        """
        # Configure root window to use grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Main frame using grid instead of pack
        main_frame = ttk.Frame(self.root, padding=10, style="TFrame")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure main frame rows and columns
        main_frame.grid_columnconfigure(0, weight=1)
        
        row_index = 0
        
        # Control panel - make it stand out with a subtle border
        control_frame = ttk.Frame(main_frame, style="TFrame")
        control_frame.grid(row=row_index, column=0, sticky="ew", pady=8)
        control_frame['padding'] = (10, 5, 10, 5)  # Add internal padding
        row_index += 1
        
        # Record button with reliable tk.Button
        self.record_button = tk.Button(
            control_frame,
            text="Start Recording",
            command=self._toggle_recording,
            bg="#AA3333",  # Red background
            fg="#FFFFFF",  # White text
            relief=tk.FLAT,
            padx=8,
            pady=4,
            activebackground="#CC3333",
            activeforeground="#FFFFFF",
            bd=0,
            font=("Segoe UI", 9)
        )
        self.record_button.pack(side=tk.LEFT, padx=8)
        
        # Log to file checkbox with improved style
        self.log_var = tk.BooleanVar(value=False)
        self.log_checkbox = ttk.Checkbutton(
            control_frame, 
            text="Log to File",
            variable=self.log_var,
            command=self._toggle_logging,
            style="TCheckbutton"
        )
        self.log_checkbox.pack(side=tk.LEFT, padx=8)
        
        # Status label with better text
        self.status_label = ttk.Label(
            control_frame, 
            text="Not Recording",
            style="TLabel"
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Separator - make it more subtle
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
        
        # Key tracking frame - improved layout (KEEP ONLY THIS INSTANCE)
        key_frame = ttk.Frame(control_frame, style="TFrame")
        key_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(key_frame, text="Key:", style="TLabel").pack(side=tk.LEFT)
        
        # Create a dark theme entry for key input
        self.key_entry = tk.Entry(
            key_frame, 
            width=10, 
            bg=self.dark_bg,
            fg=self.text_color,
            insertbackground=self.text_color,  # Cursor color
            relief=tk.FLAT,
            bd=1,
        )
        self.key_entry.pack(side=tk.LEFT, padx=5)
        
        # Replace ttk buttons with tk buttons for more reliable styling
        add_button = tk.Button(
            key_frame, 
            text="Add Key", 
            command=self._add_key,
            bg=self.accent_color,
            fg="#FFFFFF",
            relief=tk.FLAT,
            padx=8,
            pady=2,
            activebackground="#0066aa",
            activeforeground="#FFFFFF",
            bd=0
        )
        add_button.pack(side=tk.LEFT, padx=4)
        
        remove_button = tk.Button(
            key_frame, 
            text="Remove Key", 
            command=self._remove_key,
            bg=self.accent_color,
            fg="#FFFFFF",
            relief=tk.FLAT,
            padx=8, 
            pady=2,
            activebackground="#0066aa",
            activeforeground="#FFFFFF",
            bd=0
        )
        remove_button.pack(side=tk.LEFT, padx=4)
        
        # Add mouse tracking mode controls after key tracking frame
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
        
        # Mouse tracking mode frame
        mouse_mode_frame = ttk.Frame(control_frame, style="TFrame")
        mouse_mode_frame.pack(side=tk.LEFT, fill=tk.X)
        
        # Direction Only Mode checkbox
        self.direction_only_var = tk.BooleanVar(value=True)  # Enabled by default
        self.direction_only_cb = ttk.Checkbutton(
            mouse_mode_frame, 
            text="Direction Only",
            variable=self.direction_only_var,
            command=self._update_tracking_modes,
            style="TCheckbutton"
        )
        self.direction_only_cb.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(mouse_mode_frame, text="Mouse Mode:", style="TLabel").pack(side=tk.LEFT, padx=5)
        
        # Create a dropdown for tracking modes
        self.tracking_mode_var = tk.StringVar(value="angle")  # Default to angle when direction only
        self.tracking_dropdown = tk.OptionMenu(
            mouse_mode_frame, 
            self.tracking_mode_var, 
            "angle", "axis",  # Start with direction-only modes
            command=self._set_mouse_tracking_mode
        )
        self.tracking_dropdown.config(
            bg=self.dark_bg,
            fg=self.text_color,
            activebackground=self.accent_color,
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            highlightthickness=0,
            bd=1
        )
        self.tracking_dropdown["menu"].config(
            bg=self.dark_bg,
            fg=self.text_color,
            activebackground=self.accent_color,
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
        )
        self.tracking_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Visualization area with grid layout - add some breathing room
        viz_frame = ttk.Frame(main_frame, style="TFrame")
        viz_frame.grid(row=row_index, column=0, sticky="nsew", pady=8)
        row_index += 1
        
        # Configure viz frame to resize properly
        viz_frame.grid_columnconfigure(0, weight=1)
        viz_frame.grid_columnconfigure(1, weight=1)
        viz_frame.grid_rowconfigure(0, weight=1)
        
        # Create visualization frames with grid - better titles for sections
        left_frame = ttk.LabelFrame(viz_frame, text="Keyboard Input", style="TLabelframe")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5)
        
        right_frame = ttk.LabelFrame(viz_frame, text="Mouse Input", style="TLabelframe")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5)
        
        # Configure frames to resize properly
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)
        
        # Create visualizers
        self.keyboard_viz = KeyboardVisualizer(left_frame)
        self.keyboard_viz.get_frame().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self.mouse_viz = MouseVisualizer(right_frame)
        self.mouse_viz.get_frame().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Active keys display - improved appearance
        active_keys_frame = ttk.LabelFrame(main_frame, text="Active Keys", style="TLabelframe")
        active_keys_frame.grid(row=row_index, column=0, sticky="ew", pady=5)
        row_index += 1
        
        active_keys_frame.grid_columnconfigure(0, weight=1)
        self.active_keys_label = ttk.Label(
            active_keys_frame, 
            text="None", 
            anchor="center",
            style="TLabel"
        )
        self.active_keys_label.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Key list with dark theme
        key_list_frame = ttk.LabelFrame(main_frame, text="Tracked Keys", style="TLabelframe")
        key_list_frame.grid(row=row_index, column=0, sticky="ew", pady=5)
        row_index += 1
        
        key_list_frame.grid_columnconfigure(0, weight=1)
        
        # Dark-themed listbox
        self.key_listbox = tk.Listbox(
            key_list_frame, 
            height=5,
            bg=self.dark_bg,
            fg=self.text_color,
            selectbackground=self.accent_color,
            selectforeground="#FFFFFF",
            relief=tk.FLAT,
            borderwidth=1,
            highlightthickness=0
        )
        self.key_listbox.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Status area with improved styling
        status_frame = ttk.Frame(main_frame, style="TFrame")
        status_frame.grid(row=row_index, column=0, sticky="ew", pady=5)
        row_index += 1
        
        status_frame.grid_columnconfigure(0, weight=1)
        
        # Dark theme scrolledtext for logs with syntax highlighting
        self.status_text = scrolledtext.ScrolledText(
            status_frame, 
            height=6,
            bg=self.dark_bg,
            fg=self.text_color,
            insertbackground=self.text_color,
            selectbackground=self.accent_color,
            selectforeground="#FFFFFF",
            relief=tk.FLAT,
            borderwidth=1,
            highlightthickness=0,
            font=("Consolas", 9),  # Monospaced font for better log readability
            padx=5,
            pady=5
        )
        self.status_text.grid(row=0, column=0, sticky="ew")
        self.status_text.config(state=tk.DISABLED)
        
        # Mouse settings section
        mouse_settings_frame = ttk.LabelFrame(main_frame, text="Mouse Settings", style="TLabelframe")
        mouse_settings_frame.grid(row=row_index, column=0, sticky="ew", pady=5)
        row_index += 1
        
        # Configure settings frame
        mouse_settings_frame.grid_columnconfigure(0, weight=1)
        mouse_settings_frame.grid_columnconfigure(1, weight=1)
        
        # Delta smoothing slider
        delta_frame = ttk.Frame(mouse_settings_frame, style="TFrame")
        delta_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        ttk.Label(delta_frame, text="Delta Smoothing:", style="TLabel").pack(side=tk.LEFT, padx=5)
        
        self.delta_smoothing_var = tk.DoubleVar(value=0.5)
        delta_smoothing_slider = ttk.Scale(
            delta_frame,
            from_=0.0,
            to=0.9,
            orient=tk.HORIZONTAL,
            variable=self.delta_smoothing_var,
            command=lambda x: None  # Will be applied on button press
        )
        delta_smoothing_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Joystick sensitivity slider
        joystick_frame = ttk.Frame(mouse_settings_frame, style="TFrame")
        joystick_frame.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        ttk.Label(joystick_frame, text="Joystick Sensitivity:", style="TLabel").pack(side=tk.LEFT, padx=5)
        
        self.sensitivity_var = tk.DoubleVar(value=0.1)
        sensitivity_slider = ttk.Scale(
            joystick_frame,
            from_=0.1,
            to=2.0,
            orient=tk.HORIZONTAL,
            variable=self.sensitivity_var,
            command=lambda x: None  # Will be applied on button press
        )
        sensitivity_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Add Angle Grouping slider (for angle mode)
        angle_frame = ttk.Frame(mouse_settings_frame, style="TFrame")
        angle_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        ttk.Label(angle_frame, text="Angle Grouping:", style="TLabel").pack(side=tk.LEFT, padx=5)
        
        self.angle_grouping_var = tk.IntVar(value=10)  # Default to 10 degrees (36 values)
        
        # Create a frame for the slider and its value display
        angle_slider_frame = ttk.Frame(angle_frame, style="TFrame")
        angle_slider_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Create the slider
        angle_grouping_slider = ttk.Scale(
            angle_slider_frame,
            from_=1,
            to=60,
            orient=tk.HORIZONTAL,
            variable=self.angle_grouping_var,
            command=self._update_angle_grouping_display
        )
        angle_grouping_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Add a label to display current value and resulting number of angles
        self.angle_grouping_display = ttk.Label(
            angle_slider_frame, 
            text="10° (36 values)", 
            style="TLabel",
            width=15
        )
        self.angle_grouping_display.pack(side=tk.LEFT, padx=5)
        
        # Add a frame for scroll checkbox
        scroll_frame = ttk.Frame(mouse_settings_frame, style="TFrame")
        scroll_frame.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        # Add Capture Scroll checkbox
        self.capture_scroll_var = tk.BooleanVar(value=False)  # Default to False
        self.capture_scroll_cb = ttk.Checkbutton(
            scroll_frame, 
            text="Capture Scroll Data",
            variable=self.capture_scroll_var,
            style="TCheckbutton"
        )
        self.capture_scroll_cb.pack(side=tk.LEFT, padx=5)
        
        # Apply button
        apply_button = tk.Button(
            mouse_settings_frame,
            text="Apply Settings",
            command=self._apply_mouse_settings,
            bg=self.accent_color,
            fg="#FFFFFF",
            relief=tk.FLAT,
            padx=8,
            pady=2,
            activebackground="#0066aa",
            activeforeground="#FFFFFF",
            bd=0
        )
        apply_button.grid(row=1, column=1, sticky="e", padx=10, pady=5)
        
        # Configure main_frame rows to resize properly
        main_frame.grid_rowconfigure(1, weight=1)  # Make viz_frame expandable
    
    def _toggle_recording(self) -> None:
        """
        Toggle recording state.
        
        Starts or stops the recording of input events based on the current state.
        Updates UI elements to reflect the new state.
        """
        if self.is_recording:
            # Stop recording
            print("Stopping recording...")
            self.collector.stop_capture()
            self.is_recording = False
            self.record_button.config(text="Start Recording")
            self.status_label.config(text="Not Recording")
            self._log_status("Recording stopped", color=self.warning_color)
            if self.log_file:
                self.log_file.write(f"{{\n\"event\": \"recording_stopped\",\n\"timestamp\": {time.time()}\n}}\n")
            print("Recording stopped, UI updated")
        else:
            # Start recording
            print("Starting recording...")
            self.collector.start_capture()
            self.is_recording = True
            self.record_button.config(text="Stop Recording")
            self.status_label.config(text="RECORDING")
            self._log_status("Recording started", color=self.success_color)
            if self.log_file:
                self.log_file.write(f"{{\n\"event\": \"recording_started\",\n\"timestamp\": {time.time()}\n}}\n")
            print("Recording started, UI updated")
        
        # Force update the UI immediately to reflect the change
        self.root.update_idletasks()
    
    def _toggle_logging(self) -> None:
        """
        Toggle logging to file.
        
        Starts or stops logging input events to a file based on the
        current state of the log checkbox.
        """
        self.log_to_file = self.log_var.get()
        if self.log_to_file:
            # Open log file with correct timestamp
            current_time = time.time()
            timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime(current_time))
            filename = f"input_log_{timestamp}.json"
            self.log_file = open(filename, "w")
            self._log_status(f"Logging to {filename}")
        else:
            # Close log file
            if self.log_file:
                self.log_file.close()
                self.log_file = None
                self._log_status("Logging to file stopped")
    
    def _handle_input_event(self, event: InputData) -> None:
        """
        Handle input events from the collector with unified logging.
        
        Processes input events from the collector, updates visualizers,
        and logs events to the UI and file if appropriate.
        
        Args:
            event: The input event to handle
        """
        # Check for special toggle_recording event type first (for F9 key)
        if event.event_type == "toggle_recording":
            current_state = "RECORDING" if self.is_recording else "NOT RECORDING"
            if self.collector.verbose:
                print(f"*** DEBUG: Received toggle_recording event, current state: {current_state} ***")
            
            # Only log to application logs if control event logging is enabled
            if self.log_control_events:
                self._log_status(f"Recording {'stopped' if self.is_recording else 'started'} via F9 key")
            
            # CRITICAL FIX: Explicitly start recording if not recording
            if not self.is_recording:
                if self.collector.verbose:
                    print("*** DEBUG: FORCIBLY STARTING recording from F9 key ***")
                # Full restart of collector to fix synchronization issues
                self.collector.stop_capture()  # Make sure it's truly stopped
                time.sleep(0.1)  # Small delay to let things settle
                self.collector.start_capture()  # Restart properly
                self.is_recording = True
                self.record_button.config(text="Stop Recording")
                self.status_label.config(text="RECORDING")
                
                # Only log to status area if control event logging is enabled
                if self.log_control_events:
                    self._log_status("Recording started via F9 key")
                
                # Always log to file if file logging is enabled
                if self.log_file:
                    self.log_file.write(f"{{\n\"event\": \"recording_started\",\n\"timestamp\": {time.time()}\n}}\n")
            else:
                if self.collector.verbose:
                    print("*** DEBUG: FORCIBLY STOPPING recording from F9 key ***")
                # Stop recording
                self.collector.stop_capture()
                self.is_recording = False
                self.record_button.config(text="Start Recording")
                self.status_label.config(text="Not Recording")
                
                # Only log to status area if control event logging is enabled
                if self.log_control_events:
                    self._log_status("Recording stopped via F9 key")
                
                # Always log to file if file logging is enabled
                if self.log_file:
                    self.log_file.write(f"{{\n\"event\": \"recording_stopped\",\n\"timestamp\": {time.time()}\n}}\n")
            
            # Force update UI
            self.root.update_idletasks()
            
            # Highlight the F9 key in the keyboard visualizer
            temp_press_event = InputData(
                timestamp=event.timestamp,
                event_type="key_press",
                key="Key.media_play_pause",
                active_keys=event.active_keys or []
            )
            self.keyboard_viz.update(temp_press_event)
            
            # Don't process this event any further
            return

        # Don't log events if we're not recording (requirement #3)
        if not self.is_recording:
            # Still update visualizers, but don't log anything
            if event.event_type in ["key_press", "key_release"]:
                self.keyboard_viz.update(event)
            elif event.event_type in ["mouse_move", "mouse_click", "mouse_scroll"]:
                self.mouse_viz.update(event)
            
            # Update active keys display (faster than waiting for scheduled update)
            self._update_active_keys_display()
            return

        # Don't process key_release events for logging (requirement #2)
        if event.event_type == "key_release":
            # Only update the visualizer
            self.keyboard_viz.update(event)
            self._update_active_keys_display()
            return

        # Handle regular media_play_pause key (from actual media key)
        if (event.event_type == "key_press" and 
            event.key and "media_play_pause" in event.key.lower()):
            # Add debug logging to understand when this is called
            print(f"Media play/pause key press detected in event handler: {event.key}")
            # Directly call the toggle method that updates both UI and recording state
            self._toggle_recording()
            
            # Update keyboard visualizer to show the key as pressed anyway
            self.keyboard_viz.update(event)
            
            # No need to process this event further
            return
        
        # Update visualizers immediately for real-time display
        if event.event_type in ["key_press", "key_release"]:
            self.keyboard_viz.update(event)
        elif event.event_type in ["mouse_move", "mouse_click", "mouse_scroll"]:
            self.mouse_viz.update(event)
        
        # Update active keys display (faster than waiting for scheduled update)
        self._update_active_keys_display()
        
        # Log to the UI when recording is active
        # Consider mouse clicks and scrolls as significant events that should be logged
        # regardless of movement
        should_log = (
            (event.event_type == "key_press") or
            (event.event_type == "mouse_move" and event.is_moving) or
            (event.event_type == "mouse_click") or
            (event.event_type == "mouse_scroll") or
            (event.button_pressed is not None)  # Always log when a button is pressed
        )
        
        if self.is_recording and should_log:
            event_text = self._format_event_text(event)
            self._log_status(event_text)
            
            # Log to file if enabled
            if self.log_file:
                self._log_event_to_file(event)
    
    def _format_event_text(self, event: InputData) -> str:
        """
        Format event text for UI display based on tracking mode.
        
        Converts an input event into a human-readable string for display in the UI,
        with information relevant to the current tracking mode.
        
        Args:
            event: The input event to format
            
        Returns:
            str: Formatted text representation of the event
        """
        # Format keyboard info - make it stand out
        keyboard_part = f"Keys: [{', '.join(event.active_keys)}]" if event.active_keys else "Keys: []"
        
        # Format mouse info based on tracking mode
        mouse_parts = []
        tracking_mode = getattr(event, 'mouse_tracking_mode', 'joystick')
        
        # Click info - common to all modes
        if event.event_type == "mouse_click" and event.button_pressed:
            mouse_parts.append(f"Click:{event.button_pressed}")
        elif hasattr(event, 'button_pressed') and event.button_pressed:
            mouse_parts.append(f"Click:{event.button_pressed}")
        
        # Scroll info - common to all modes
        if event.event_type == "mouse_scroll" and event.direction:
            mouse_parts.append(f"Scroll:{event.direction}")
        
        # Movement info - mode specific
        if event.is_moving:
            if tracking_mode == "delta":
                # Delta mode shows raw deltas and magnitude
                if hasattr(event, 'mouse_delta_x') and hasattr(event, 'mouse_delta_y'):
                    mouse_parts.append(f"Δx:{event.mouse_delta_x:.1f} Δy:{event.mouse_delta_y:.1f}")
                if hasattr(event, 'mouse_delta_magnitude'):
                    mouse_parts.append(f"Mag:{event.mouse_delta_magnitude:.1f}")
                if event.direction:
                    mouse_parts.append(f"Dir:{event.direction}")
            elif tracking_mode == "angle":
                # Angle mode shows angle and magnitude
                if hasattr(event, 'mouse_delta_angle'):
                    mouse_parts.append(f"Angle:{event.mouse_delta_angle:.1f}°")
                if hasattr(event, 'mouse_delta_magnitude'):
                    mouse_parts.append(f"Mag:{event.mouse_delta_magnitude:.1f}")
                if event.direction:
                    mouse_parts.append(f"Dir:{event.direction}")
            else:  # joystick mode
                # Joystick shows direction, rel position, and speed
                if event.direction:
                    mouse_parts.append(f"Dir:{event.direction}")
                if event.speed is not None:
                    mouse_parts.append(f"Speed:{event.speed:.1f}")
                if event.rel_x is not None and event.rel_y is not None:
                    mouse_parts.append(f"Rel:({event.rel_x:.2f},{event.rel_y:.2f})")
        
        # Combine all mouse info
        mouse_part = f"Mouse[{tracking_mode}]: {' | '.join(mouse_parts)}" if mouse_parts else f"Mouse[{tracking_mode}]: Idle"
        
        return f"{keyboard_part} | {mouse_part}"

    def _log_event_to_file(self, event: InputData) -> None:
        """
        Log event to file with a simplified, uniform format.
        
        Creates clean, consistent logs that are easy to process for machine learning
        or pattern recognition, with just the essential data for each tracking mode.
        
        Args:
            event: The input event to log
        """
        try:
            # Determine current tracking mode
            tracking_mode = getattr(event, 'mouse_tracking_mode', 'joystick')
            
            # Convert scroll direction to numeric value (1=up, 0=null, -1=down)
            scroll_value = 0  # Default (null)
            if event.event_type == "mouse_scroll" and event.direction is not None:
                if event.direction == "up":
                    scroll_value = 1
                elif event.direction == "down":
                    scroll_value = -1
            
            # Create a simplified log structure
            clean_log = {
                "timestamp": event.timestamp,
                "mode": tracking_mode,
                "keyboard": {
                    "keys": event.active_keys or []
                },
                "mouse": {
                    "buttons": [event.button_pressed] if event.button_pressed else []
                }
            }

            # Only include scroll_direction if capture_scroll is enabled
            if self.capture_scroll_var.get() or scroll_value != 0:
                clean_log["mouse"]["scroll_direction"] = scroll_value
            
            # Add only the relevant data for the current tracking mode
            if tracking_mode == "joystick":
                clean_log["mouse"]["speed_x"] = event.speed_x if hasattr(event, 'speed_x') and event.speed_x is not None else 0.0
                clean_log["mouse"]["speed_y"] = event.speed_y if hasattr(event, 'speed_y') and event.speed_y is not None else 0.0
            
            elif tracking_mode == "delta":
                clean_log["mouse"]["delta_x"] = event.mouse_delta_x if hasattr(event, 'mouse_delta_x') and event.mouse_delta_x is not None else 0.0
                clean_log["mouse"]["delta_y"] = event.mouse_delta_y if hasattr(event, 'mouse_delta_y') and event.mouse_delta_y is not None else 0.0
            
            elif tracking_mode == "angle":
                # Handle direction-only angle mode differently
                if hasattr(event, 'direction_only') and event.direction_only:
                    clean_log["mouse"]["discrete_angle"] = event.discrete_angle if hasattr(event, 'discrete_angle') else 0
                else:
                    clean_log["mouse"]["angle"] = event.mouse_delta_angle if hasattr(event, 'mouse_delta_angle') and event.mouse_delta_angle is not None else 0.0
                    clean_log["mouse"]["magnitude"] = event.mouse_delta_magnitude if hasattr(event, 'mouse_delta_magnitude') and event.mouse_delta_magnitude is not None else 0.0
            
            elif tracking_mode == "axis":
                # Axis mode includes membership values for cardinal directions
                clean_log["mouse"]["north"] = event.north if hasattr(event, 'north') else 0.0
                clean_log["mouse"]["south"] = event.south if hasattr(event, 'south') else 0.0
                clean_log["mouse"]["east"] = event.east if hasattr(event, 'east') else 0.0
                clean_log["mouse"]["west"] = event.west if hasattr(event, 'west') else 0.0
            
            # Write the clean log to file and flush immediately
            self.log_file.write(json.dumps(clean_log) + "\n")
            self.log_file.flush()
        except Exception as e:
            print(f"Error logging to file: {e}")
    
    def _add_key(self) -> None:
        """
        Add a key to the tracked keys list.
        
        Takes the key entered in the key entry field and adds it to the
        list of tracked keys if it's not already there.
        """
        key = self.key_entry.get().strip()
        if key and key not in self.tracked_keys:
            self.tracked_keys.append(key)
            self.collector.set_supported_keys(self.tracked_keys)
            self._update_key_list()
            self.key_entry.delete(0, tk.END)
            self._log_status(f"Added key: {key}")
    
    def _remove_key(self) -> None:
        """
        Remove a key from the tracked keys list.
        
        Removes the currently selected key from the tracked keys list.
        """
        selection = self.key_listbox.curselection()
        if selection:
            index = selection[0]
            key = self.key_listbox.get(index)
            self.tracked_keys.remove(key)
            self.collector.set_supported_keys(self.tracked_keys)
            self._update_key_list()
            self._log_status(f"Removed key: {key}")
    
    def _update_key_list(self) -> None:
        """
        Update the key list display.
        
        Updates the listbox to show the current list of tracked keys.
        """
        self.key_listbox.delete(0, tk.END)
        for key in self.tracked_keys:
            self.key_listbox.insert(tk.END, key)
    
    def _log_status(self, message: str, color: Optional[str] = None) -> None:
        """
        Log a message to the status area.
        
        Adds a timestamped message to the status text area with optional 
        color formatting.
        
        Args:
            message: The message to log
            color: Optional color for the message (as a hex string)
        """
        self.status_text.config(state=tk.NORMAL)
        
        # Fix the timestamp format - strftime doesn't support microseconds with %f
        current_time = time.time()
        timestamp = time.strftime('%H:%M:%S', time.localtime(current_time))
        ms = int((current_time - int(current_time)) * 1000)
        formatted_time = f"{timestamp}.{ms:03d}"
        
        # Add timestamp in muted color
        self.status_text.insert(tk.END, formatted_time, "timestamp")
        self.status_text.insert(tk.END, " - ", "timestamp")
        
        # Use color tags for different message types if color provided
        if color:
            self.status_text.insert(tk.END, f"{message}\n", "colored")
            self.status_text.tag_config("colored", foreground=color)
        else:
            self.status_text.insert(tk.END, f"{message}\n")
            
        # Configure timestamp tag with muted color
        self.status_text.tag_config("timestamp", foreground="#999999")
        
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
    
    def _update_active_keys_display(self) -> None:
        """
        Update the active keys display.
        
        Updates the label showing the currently pressed keys.
        """
        active_keys = self.collector.get_active_keys()
        if active_keys:
            # Filter to only show tracked keys
            tracked_active = [k for k in active_keys if any(
                k.lower() == tracked.lower() or k.lower().endswith(tracked.lower()) 
                for tracked in self.tracked_keys
            )]
            self.active_keys_label.config(text=", ".join(tracked_active))
        else:
            self.active_keys_label.config(text="None")
    
    def _schedule_ui_update(self) -> None:
        """
        Schedule periodic UI updates.
        
        Sets up a recurring timer to update the UI components regularly.
        """
        self._update_active_keys_display()
        # Schedule next update in 100ms
        self.root.after(100, self._schedule_ui_update)
    
    def run(self) -> None:
        """
        Run the application main loop.
        
        Starts the application's main event loop.
        """
        if self.owns_root:
            # Set up cleanup on window close
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
            
            # Start main loop
            self.root.mainloop()
    
    def _on_close(self) -> None:
        """
        Handle window close event.
        
        Performs cleanup operations when the application window is closed.
        """
        if self.is_recording:
            self.collector.stop_capture()
        if self.log_file:
            self.log_file.close()
        self.root.destroy()
    
    def get_collector(self) -> KeyboardMouseCollector:
        """
        Get the input collector instance.
        
        Returns:
            KeyboardMouseCollector: The active input collector instance
        """
        return self.collector

    def _toggle_recording_key(self, event: Optional[tk.Event] = None) -> str:
        """
        Toggle recording state via keyboard shortcut.
        
        Handles keyboard shortcut events for toggling recording state.
        
        Args:
            event: The keyboard event that triggered the toggle
            
        Returns:
            str: "break" to prevent further processing of the event
        """
        # This is used for tkinter key events (like F9 direct from the window)
        # Since we're already handling F9 in the collector, we only need this
        # for other keys like space
        
        # Prevent F9 from causing double-toggling by checking the key
        if hasattr(event, 'keysym') and event.keysym == 'F9':
            # The pynput handler will take care of this one
            return "break"
        
        print(f"Toggle recording via keyboard shortcut: {event}")
        
        # Toggle recording
        self._toggle_recording()
        
        # Prevent further processing of this event
        return "break"

    def _capture_keyboard_focus(self, event: Optional[tk.Event] = None) -> bool:
        """
        Ensure the app receives keyboard events regardless of focus.
        
        Makes sure the application window keeps focus to capture keyboard events.
        
        Args:
            event: The keyboard event that might have changed focus
            
        Returns:
            bool: True to continue processing the event
        """
        # If not already capturing, move focus back to the main window
        # which has the keyboard bindings
        if not self.is_recording:
            self.root.focus_set()
        return True

    def _set_mouse_tracking_mode(self, mode: str) -> None:
        """
        Change the mouse tracking mode.
        
        Args:
            mode: The tracking mode to use
        """
        # Update the tracking mode
        self.tracking_mode_var.set(mode)
        
        # Pass the direction-only flag and angle grouping if applicable
        direction_only = self.direction_only_var.get()
        angle_grouping = self.angle_grouping_var.get()
        
        self.collector.set_mouse_tracking_mode(mode, direction_only, angle_grouping)
        self._log_status(f"Mouse tracking mode set to: {mode}", color=self.accent_color)
        
        # Update display properties based on mode
        if mode == "axis":
            self._log_status("Axis mode shows membership values for N, S, E, W directions", color="#AAAAAA")
        elif mode == "angle" and direction_only:
            self._log_status(f"Angle mode using {angle_grouping}° grouping ({360 // angle_grouping} values)", color="#AAAAAA")

    def _apply_mouse_settings(self) -> None:
        """
        Apply the current mouse settings.
        """
        # Apply delta smoothing
        smoothing = self.delta_smoothing_var.get()
        self.collector.set_delta_smoothing(smoothing)
        self._log_status(f"Delta smoothing set to: {smoothing:.2f}")
        
        # Apply joystick sensitivity
        sensitivity = self.sensitivity_var.get()
        self.collector.set_joystick_sensitivity(sensitivity)
        self._log_status(f"Joystick sensitivity set to: {sensitivity:.2f}")
        
        # Apply angle grouping
        angle_grouping = self.angle_grouping_var.get()
        self.collector.set_angle_grouping(angle_grouping)
        self._log_status(f"Angle grouping set to: {angle_grouping}° ({360 // angle_grouping} values)")
        
        # Log scroll capture status
        self._log_status(f"Scroll data capture: {'Enabled' if self.capture_scroll_var.get() else 'Disabled'}")
        
        # Re-apply current tracking mode to ensure all settings are updated
        self._set_mouse_tracking_mode(self.tracking_mode_var.get())

    def _update_tracking_modes(self) -> None:
        """
        Update available tracking modes based on the Direction Only checkbox.
        """
        # Get current tracking mode
        current_mode = self.tracking_mode_var.get()
        
        # Clear current menu
        menu = self.tracking_dropdown["menu"]
        menu.delete(0, "end")
        
        # Add appropriate modes based on checkbox state
        if self.direction_only_var.get():
            # Direction-only modes
            for mode in ["angle", "axis"]:
                menu.add_command(label=mode, 
                                 command=lambda m=mode: self.tracking_mode_var.set(m) or self._set_mouse_tracking_mode(m))
            
            # Make sure the current mode is valid for direction-only
            if current_mode not in ["angle", "axis"]:
                self.tracking_mode_var.set("angle")
                self._set_mouse_tracking_mode("angle")
        else:
            # Standard modes
            for mode in ["joystick", "delta", "angle"]:
                menu.add_command(label=mode, 
                                 command=lambda m=mode: self.tracking_mode_var.set(m) or self._set_mouse_tracking_mode(m))
            
            # Make sure the current mode is valid for standard
            if current_mode not in ["joystick", "delta", "angle"]:
                self.tracking_mode_var.set("joystick")
                self._set_mouse_tracking_mode("joystick")

    def _update_angle_grouping_display(self, *args) -> None:
        """
        Update the display showing current angle grouping and resulting number of values.
        """
        grouping = self.angle_grouping_var.get()
        num_values = 360 // grouping if grouping > 0 else 360
        self.angle_grouping_display.config(text=f"{grouping}° ({num_values} values)")

def run_collector_app() -> InputCollectorApp:
    """
    Run the input collector application.
    
    Creates and runs the input collector application as a standalone program.
    
    Returns:
        InputCollectorApp: The input collector application instance
    """
    app = InputCollectorApp()
    app.run()
    return app