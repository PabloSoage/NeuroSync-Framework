"""
Keyboard visualization module.

This module provides visualization components for keyboard input events,
displaying a virtual keyboard with key highlight states.
"""
import tkinter as tk
from typing import Dict, Set, List

from ..interfaces import InputData


class KeyboardVisualizer:
    """
    Visualizes keyboard input events with a virtual keyboard display.
    
    This class creates a visual representation of a keyboard and highlights keys
    based on their state (pressed, tracked, etc.). It provides real-time visual
    feedback for keyboard input events.
    """
    
    DEFAULT_KEYBOARD_LAYOUT: List[List[str]] = [
        ["Esc", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"],
        ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "Backspace"],
        ["Tab", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]", "\\"],
        ["Caps", "A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'", "Enter"],
        ["Shift", "Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "Shift"],
        ["Ctrl", "Win", "Alt", "Space", "Alt", "Menu", "Ctrl"]
    ]
    
    def __init__(self, parent_frame: tk.Frame) -> None:
        """
        Initialize the keyboard visualizer.
        
        Creates a virtual keyboard visualization inside the provided parent frame.
        
        Args:
            parent_frame: Tkinter frame to contain the keyboard visualization
        """
        # Define dark theme colors
        self.dark_bg: str = "#2D2D30"
        self.dark_frame_bg: str = "#252526"
        self.key_bg: str = "#3E3E42"
        self.key_text: str = "#E0E0E0"
        self.tracked_key_bg: str = "#444466"
        self.active_key_bg: str = "#007ACC"
        self.secondary_key_bg: str = "#5FB878"
        self.record_key_bg: str = "#AA3333"
        
        # Store parent frame for resizing
        self.parent_frame = parent_frame
        
        # Create a responsive frame to contain the keyboard
        self.frame: tk.Frame = tk.Frame(parent_frame, bg=self.dark_frame_bg)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        self.key_buttons: Dict[str, tk.Button] = {}
        self.active_keys: Set[str] = set()
        self.tracked_keys: Set[str] = set()  # Set of tracked keys for special highlighting
        
        # Inner frame for the keyboard that will be centered
        self.keyboard_frame: tk.Frame = tk.Frame(self.frame, bg=self.dark_frame_bg)
        self.keyboard_frame.pack(expand=True, fill=tk.BOTH)
        
        # Track size
        self.current_width = 0
        self.current_height = 0
        
        # Create keyboard layout
        self._create_keyboard()
        
        # Update size initially
        self.update_size()
        
        # Set up resize event handling
        self.frame.bind("<Configure>", self.on_frame_resize)
    
    def on_frame_resize(self, event) -> None:
        """
        Handle frame resize events.
        
        Args:
            event: The resize event
        """
        # Always update on resize events, especially fullscreen transitions
        self.frame.after_cancel(getattr(self, '_resize_id', 'dummy'))
        self._resize_id = self.frame.after(50, self.update_size)
    
    def update_size(self) -> None:
        """
        Update keyboard size based on parent frame size.
        
        Adjusts the keyboard layout to fit the current frame dimensions.
        """
        # Get current frame size
        width = self.parent_frame.winfo_width()
        height = self.parent_frame.winfo_height()
        
        # Only update if we have a valid size
        if width > 100 and height > 100:
            self.current_width = width
            self.current_height = height
            
            # Scale font and key sizes based on available space
            frame_width = max(350, min(width - 20, 550))
            
            # Calculate key sizes - more responsive to different sizes
            key_width = max(3, int(frame_width / 90))  # Reduced divisor for smaller keys
            key_height = max(1, int(height / 210))     # Add height calculation 
            
            # Adjust font size more dynamically based on available space
            font_size = max(7, min(9, int(frame_width / 55)))  # Slightly smaller font
            
            # Update all keys
            for key_name, button in self.key_buttons.items():
                # Calculate width based on key type
                if key_name in ["space", "key.space"]:
                    button.config(width=key_width * 4)  # Spacebar wider
                elif key_name in ["backspace", "enter"]:
                    button.config(width=key_width * 2)  # These keys moderately wider
                elif key_name in ["shift", "tab"]:
                    button.config(width=int(key_width * 1.5))  # These keys slightly wider
                else:
                    button.config(width=key_width)  # Standard keys
                
                # Set consistent height for all keys
                button.config(height=key_height, font=("Segoe UI", font_size))
    
    def set_tracked_keys(self, keys: List[str]) -> None:
        """
        Set the list of tracked keys to highlight differently.
        
        Args:
            keys: List of key names to track and highlight
        """
        # Store the raw tracked keys for exact matching
        self.tracked_keys = {k.lower() for k in keys}
        # Update the visual appearance of all keys
        self._update_buttons()
    
    def _create_keyboard(self) -> None:
        """
        Create the keyboard layout.
        
        Builds the visual keyboard layout with buttons for each key.
        """
        # Use a frame that centers the keyboard
        center_frame = tk.Frame(self.keyboard_frame, bg=self.dark_frame_bg)
        center_frame.pack(expand=True, fill=tk.BOTH)
        
        for row_idx, row in enumerate(self.DEFAULT_KEYBOARD_LAYOUT):
            row_frame = tk.Frame(center_frame, bg=self.dark_frame_bg)
            row_frame.pack(pady=1)
            
            for key_label in row:
                # Create a button for each key with minimal initial width
                width = 4 if key_label not in ["Space", "Backspace", "Enter", "Shift", "Tab"] else 6
                
                # Modern, flat look for keys
                btn = tk.Button(
                    row_frame, 
                    text=key_label,
                    width=width,
                    height=1,
                    relief=tk.FLAT,
                    bd=0,
                    bg=self.key_bg,
                    fg=self.key_text,
                    activebackground="#505054",
                    activeforeground="#FFFFFF",
                    font=("Segoe UI", 8)
                )
                btn.pack(side=tk.LEFT, padx=1, pady=0)  # Minimal padding
                
                # Store the button reference with lowercase key name
                key_lower = key_label.lower()
                self.key_buttons[key_lower] = btn
                
                # Create special mappings for special keys
                if key_label == "Space":
                    self.key_buttons["key.space"] = btn
                    self.key_buttons["space"] = btn
                    self.key_buttons[" "] = btn
                    # Make space bar look different
                    btn.config(bg="#464649")  # Slightly different color for spacebar
                elif key_label == "Shift":
                    # Only if this is the first Shift key, assume it's the left one
                    if "key.shift" not in self.key_buttons:
                        self.key_buttons["key.shift"] = btn
                        self.key_buttons["key.shift_l"] = btn
                    else:
                        # This is the right shift
                        self.key_buttons["key.shift_r"] = btn
                elif key_label == "F9":
                    # Map media_play_pause to F9 button with special highlighting
                    self.key_buttons["key.media_play_pause"] = btn
                    self.key_buttons["key.f9"] = btn
                    # Change the label to indicate its special function - bolder text
                    btn.config(text="F9\n(REC)", 
                              font=("Segoe UI", 8, "bold"),
                              bg=self.record_key_bg,  # Red color for recording key
                              fg="#FFFFFF",          # White text
                              relief=tk.FLAT)        # Flat modern relief
    
    def update(self, input_data: InputData) -> None:
        """
        Update the keyboard visualization based on input data.
        
        Updates the visual state of the keyboard based on the input event,
        highlighting pressed keys and tracking active keys.
        
        Args:
            input_data: Input event data containing active keys and event information
        """
        # Check for valid active_keys array
        if not hasattr(input_data, 'active_keys') or input_data.active_keys is None:
            return
        
        # Clear previous active keys and use the ones from the event (if provided)
        self.active_keys.clear()
        
        # Process active keys directly from the event (real-time state)
        for key in input_data.active_keys:
            norm_key = key.lower()
            
            # Normalize representation of special keys
            if norm_key == "key.space" or norm_key == " " or norm_key == "space":
                norm_key = "key.space"
            elif "key.shift" in norm_key or norm_key in ["key.shift", "key.shift_l", "key.shift_r"]:
                norm_key = "key.shift"
            
            # Add to active keys set
            self.active_keys.add(norm_key)
        
        # Update button appearance immediately
        self._update_buttons()
    
    def _update_buttons(self) -> None:
        """
        Update the appearance of all keys based on their state.
        
        Updates the visual styling of keys based on whether they are
        tracked, active, or in their default state.
        """
        # First reset all buttons to default state
        for key_name, button in self.key_buttons.items():
            # Special handling for F9/record key
            if key_name in ["key.media_play_pause", "key.f9", "f9"]:
                button.config(relief=tk.FLAT, bg=self.record_key_bg)
            elif key_name == "space" or key_name == "key.space" or key_name == " ":
                button.config(relief=tk.FLAT, bg="#464649")  # Spacebar color
            else:
                button.config(relief=tk.FLAT, bg=self.key_bg)
        
        # Highlight tracked keys with a subtle background
        for tracked_key in self.tracked_keys:
            tracked_key_lower = tracked_key.lower()
            
            # Handle special cases for exact matching
            if tracked_key_lower == "key.space":
                if "key.space" in self.key_buttons:
                    self.key_buttons["key.space"].config(bg="#464660")  # Subtle tracked color for space
            elif tracked_key_lower == "key.shift":
                if "key.shift" in self.key_buttons:
                    # Left shift
                    self.key_buttons["key.shift"].config(bg=self.tracked_key_bg)
                # Also highlight right shift if it exists
                if "key.shift_r" in self.key_buttons:
                    self.key_buttons["key.shift_r"].config(bg=self.tracked_key_bg)
            elif tracked_key_lower == "key.media_play_pause":
                if "key.media_play_pause" in self.key_buttons:
                    # Keep recording button red but brighter
                    self.key_buttons["key.media_play_pause"].config(bg="#BB4444")
            else:
                # For regular keys, track only exact matches
                if tracked_key_lower in self.key_buttons:
                    self.key_buttons[tracked_key_lower].config(bg=self.tracked_key_bg)
        
        # Highlight active keys
        for active_key in self.active_keys:
            active_key_lower = active_key.lower()
            
            # Handle special cases for Space and Shift
            if active_key_lower in ["key.space", "space", " "]:
                if "key.space" in self.key_buttons:
                    self.key_buttons["key.space"].config(relief=tk.SUNKEN, bg=self.active_key_bg)
            elif active_key_lower in ["key.shift", "key.shift_l", "key.shift_r"]:
                # Highlight both shift keys if any shift is pressed
                if "key.shift" in self.key_buttons:
                    self.key_buttons["key.shift"].config(relief=tk.SUNKEN, bg=self.active_key_bg)
                if "key.shift_r" in self.key_buttons:
                    self.key_buttons["key.shift_r"].config(relief=tk.SUNKEN, bg=self.active_key_bg)
            elif active_key_lower == "key.media_play_pause":
                if "key.media_play_pause" in self.key_buttons:
                    self.key_buttons["key.media_play_pause"].config(relief=tk.SUNKEN, bg="#FF5555")
            else:
                # For regular keys
                if active_key_lower in self.key_buttons:
                    is_tracked = active_key_lower in self.tracked_keys
                    bg_color = self.active_key_bg if is_tracked else self.secondary_key_bg
                    self.key_buttons[active_key_lower].config(relief=tk.SUNKEN, bg=bg_color)
    
    def get_frame(self) -> tk.Frame:
        """
        Get the tk Frame containing the keyboard visualization.
        
        Returns:
            tk.Frame: The frame containing the keyboard visualization
        """
        return self.frame
    
    def force_update(self) -> None:
        """
        Force a size update regardless of change detection.
        
        Used when transitioning between fullscreen and normal modes.
        """
        self.current_width = 0  # Reset size tracking to force update
        self.current_height = 0
        self.update_size()  # Update immediately