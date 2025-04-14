"""
Mouse visualization module.

This module provides visualization components for mouse input events,
displaying mouse movement and button states in a joystick-like interface.
"""
import math
import time
import tkinter as tk
from typing import Optional

from ..interfaces import InputData


class MouseVisualizer:
    """
    Visualizes mouse input events with joystick-like representation.
    
    This class creates a visual representation of mouse movement and input state
    using a joystick-like display. It shows movement direction, speed, mouse button
    states, and scroll events in real-time.
    """
    
    def __init__(self, parent_frame: tk.Frame) -> None:
        """
        Initialize the mouse visualizer.
        
        Creates a mouse visualization interface inside the provided parent frame.
        
        Args:
            parent_frame: Tkinter frame to contain the mouse visualization
        """
        # Use dark theme colors
        self.dark_bg: str = "#2D2D30"
        self.dark_frame_bg: str = "#252526"
        self.text_color: str = "#E0E0E0"
        self.accent_color: str = "#007ACC"
        self.highlight_color: str = "#3E3E42"
        
        self.frame: tk.Frame = tk.Frame(parent_frame, bg=self.dark_frame_bg)
        
        # Use grid layout with fixed sizes for better stability
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_rowconfigure(1, weight=0)
        self.frame.grid_rowconfigure(2, weight=0)
        
        # Fixed size canvas for drawing - INCREASE WIDTH to 340
        self.canvas_width: int = 340  # Was 300, now wider to fit text
        self.canvas_height: int = 300
        
        # Create a fixed-size frame to contain the canvas
        self.canvas_container: tk.Frame = tk.Frame(
            self.frame, 
            width=self.canvas_width,
            height=self.canvas_height,
            bg=self.dark_frame_bg
        )
        self.canvas_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.canvas_container.grid_propagate(False)
        self.canvas_container.pack_propagate(False)
        
        # Canvas for drawing with fixed size - update colors for dark theme
        self.canvas: tk.Canvas = tk.Canvas(
            self.canvas_container,
            width=self.canvas_width,
            height=self.canvas_height,
            bg=self.dark_bg,  # Dark background
            bd=0,            # No border for clean look
            relief=tk.FLAT,  # Flat relief for modern appearance
            highlightthickness=0  # Remove highlight border
        )
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")
        
        # Pre-create commonly used display objects to avoid recreation
        self.joystick_handle: Optional[int] = None
        self.direction_line: Optional[int] = None
        self.wheel_indicator: Optional[int] = None
        self.coordinate_text: Optional[int] = None
        
        # Create fixed-size text frame to prevent layout shifts - match the canvas width
        text_frame: tk.Frame = tk.Frame(self.frame, height=30, width=self.canvas_width, bg=self.dark_frame_bg)
        text_frame.grid(row=1, column=0, sticky="ew", padx=5)
        text_frame.grid_propagate(False)
        text_frame.pack_propagate(False)
        
        # Static text label for status - using label for better performance
        self.info_var: tk.StringVar = tk.StringVar(value="Mouse: Not moving")
        self.info_label: tk.Label = tk.Label(
            text_frame,
            textvariable=self.info_var,
            anchor="w",
            bg=self.dark_bg,
            fg=self.text_color,  # Light text color for contrast
            height=1,
            width=48  # Increased width to match canvas width
        )
        self.info_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Create another fixed-size frame for button status
        button_frame: tk.Frame = tk.Frame(self.frame, height=30, width=self.canvas_width, bg=self.dark_frame_bg)
        button_frame.grid(row=2, column=0, sticky="ew", padx=5)
        button_frame.grid_propagate(False)
        button_frame.pack_propagate(False)
        
        # Button status label
        self.button_var: tk.StringVar = tk.StringVar(value="Buttons: None")
        self.button_label: tk.Label = tk.Label(
            button_frame,
            textvariable=self.button_var,
            anchor="w",
            bg=self.dark_bg,
            fg=self.text_color,  # Light text color
            height=1,
            width=48  # Increased width
        )
        self.button_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Mouse state
        self.mouse_x: float = 150
        self.mouse_y: float = 150
        self.rel_x: float = 0
        self.rel_y: float = 0
        self.movement_direction: Optional[str] = None
        self.left_button_pressed: bool = False
        self.right_button_pressed: bool = False
        self.middle_button_pressed: bool = False
        self.is_moving: bool = False
        self.speed: float = 0
        self.speed_x: float = 0
        self.speed_y: float = 0
        self.wheel_direction: Optional[str] = None
        
        # Add delta tracking fields
        self.delta_x: float = 0
        self.delta_y: float = 0
        self.delta_magnitude: float = 0
        self.delta_angle: float = 0
        self.tracking_mode: str = "joystick"
        
        # Canvas center coordinates
        self.center_x: float = self.canvas_width / 2
        self.center_y: float = self.canvas_height / 2
        
        # Performance settings
        self.last_ui_update: float = 0
        self.ui_update_interval: float = 0.033  # 30fps is plenty for UI
        self.redraw_needed: bool = True
        self.last_status_update: float = 0
        self.status_update_interval: float = 0.1  # Update status text less frequently
        
        # Set up the background elements that rarely change
        self._setup_background()
        
        # Initial drawing
        self._draw()
    
    def _setup_background(self) -> None:
        """
        Set up the static background elements.
        
        Creates the static visual elements of the mouse visualization interface
        to avoid redrawing them on every update.
        """
        # Clear canvas
        self.canvas.delete("all")
        
        # Calculate joystick circle radius - REDUCED SIZE to fit better
        radius = min(self.canvas_width, self.canvas_height) * 0.25  # Reduced from 0.3 to 0.25
        
        # Draw joystick area background - updated for dark theme
        self.canvas.create_oval(
            self.center_x - radius, self.center_y - radius,
            self.center_x + radius, self.center_y + radius,
            fill="#1E1E1E",           # Darker inner circle
            outline=self.accent_color, # Blue accent outline
            width=1,                  # Thinner line for modern look
            tags=("background",)
        )
        
        # Draw coordinate axes - softer grid lines
        self.canvas.create_line(
            self.center_x - radius, self.center_y,
            self.center_x + radius, self.center_y,
            fill="#555555",       # Subtle gray
            dash=(4, 4),          # Dashed line
            tags=("background",)
        )
        self.canvas.create_line(
            self.center_x, self.center_y - radius,
            self.center_x, self.center_y + radius,
            fill="#555555",       # Subtle gray
            dash=(4, 4),          # Dashed line
            tags=("background",)
        )
        
        # Draw center indicator - more subtle center point
        self.canvas.create_oval(
            self.center_x - 5, self.center_y - 5,
            self.center_x + 5, self.center_y + 5,
            fill="#3E3E42",       # Slightly lighter than background
            outline="#555555",    # Gray outline
            tags=("background",)
        )
        
        # Draw labels for axes with new tag and corrected formatting
        # Use "axis_labels" tag instead of "background" to prevent style overrides
        self.canvas.create_text(
            self.center_x + radius + 15, self.center_y, 
            text="X+", 
            fill="#FFFFFF",       # Bright white for visibility
            tags=("axis_labels",),
            font=("Consolas", 11, "bold")  # Fixed font format, slightly bigger
        )
        self.canvas.create_text(
            self.center_x - radius - 15, self.center_y, 
            text="X-", 
            fill="#FFFFFF",
            tags=("axis_labels",),
            font=("Consolas", 11, "bold")
        )
        self.canvas.create_text(
            self.center_x, self.center_y - radius - 15, 
            text="Y-", 
            fill="#FFFFFF",
            tags=("axis_labels",),
            font=("Consolas", 11, "bold")
        )
        self.canvas.create_text(
            self.center_x, self.center_y + radius + 15, 
            text="Y+", 
            fill="#FFFFFF",
            tags=("axis_labels",),
            font=("Consolas", 11, "bold")
        )
        
        # Create coordinate text item with updated position and color
        self.coordinate_text = self.canvas.create_text(
            self.center_x, self.center_y + radius + 35,  # Moved down slightly
            text="Rel: (0.00, 0.00)",
            fill=self.text_color,     # Light text color
            tags=("dynamic",),
            font=("Consolas", 9)      # Monospaced font for better readability
        )
        
        # Create placeholders for dynamic elements
        self.joystick_handle = self.canvas.create_oval(
            self.center_x - 10, self.center_y - 10,
            self.center_x + 10, self.center_y + 10,
            fill=self.accent_color,   # Blue accent color for handle
            outline="#FFFFFF",        # White outline
            width=1,                  # Thin outline
            tags=("dynamic",)
        )
        
        self.direction_line = self.canvas.create_line(
            self.center_x, self.center_y,
            self.center_x, self.center_y,
            fill="#5FB878",          # Green for direction line
            width=2,                 # Line thickness
            arrow=tk.LAST,          
            tags=("dynamic",),
            state=tk.HIDDEN
        )
        
        self.wheel_indicator = self.canvas.create_polygon(
            self.center_x - 10, self.center_y - 15,
            self.center_x, self.center_y - 30,
            self.center_x + 10, self.center_y - 15,
            fill="#5FB878",          # Green for scroll up
            outline="#FFFFFF",       # White outline 
            width=1,                 # Thin outline
            tags=("dynamic",),
            state=tk.HIDDEN
        )
    
    def update(self, input_data: InputData) -> None:
        """
        Update the mouse visualization based on input data.
        
        Processes input events to update the visual state of the mouse visualization.
        
        Args:
            input_data: Input event data containing mouse state information
        """
        # Always update state
        state_changed: bool = False
        
        # Handle mouse click events
        if input_data.event_type == "mouse_click":
            old_button_state = (self.left_button_pressed, self.right_button_pressed, self.middle_button_pressed)
            
            if input_data.button_pressed:
                if "left" in input_data.button_pressed.lower():
                    self.left_button_pressed = True
                elif "right" in input_data.button_pressed.lower():
                    self.right_button_pressed = True
                elif "middle" in input_data.button_pressed.lower():
                    self.middle_button_pressed = True
            else:
                # Button release
                if input_data.mouse_x is not None:  # Make sure it's a valid click event
                    # Check which button was released (by string match)
                    if "left" in str(input_data):
                        self.left_button_pressed = False
                    elif "right" in str(input_data):
                        self.right_button_pressed = False
                    elif "middle" in str(input_data):
                        self.middle_button_pressed = False
                    else:
                        # If we can't determine, reset all buttons
                        self.left_button_pressed = False
                        self.right_button_pressed = False
                        self.middle_button_pressed = False
            
            # Check if buttons changed            
            new_button_state = (self.left_button_pressed, self.right_button_pressed, self.middle_button_pressed)
            if old_button_state != new_button_state:
                state_changed = True
                self.redraw_needed = True
        
        # Handle mouse scroll events
        if input_data.event_type == "mouse_scroll":
            old_wheel = self.wheel_direction
            self.wheel_direction = input_data.direction  # Will be None when reset
            
            if old_wheel != self.wheel_direction:
                state_changed = True
                self.redraw_needed = True
                
                # Ensure visual update even when direction is None (reset)
                if self.wheel_direction is None:
                    self._update_status_text()
                    self._draw()
        
        # Handle actual coordinates and movement state
        if input_data.rel_x is not None and input_data.rel_y is not None:
            # Only consider significant changes to avoid excessive redraws
            if abs(self.rel_x - input_data.rel_x) > 0.01 or abs(self.rel_y - input_data.rel_y) > 0.01:
                self.rel_x = input_data.rel_x
                self.rel_y = input_data.rel_y
                self.redraw_needed = True
        
        # Update movement state
        if input_data.event_type == "mouse_move":
            old_movement = self.is_moving
            old_direction = self.movement_direction
            
            self.movement_direction = input_data.direction
            if input_data.is_moving is not None:
                self.is_moving = input_data.is_moving
            
            # Update speeds if provided and movement is happening
            if self.is_moving and input_data.speed is not None:
                self.speed = input_data.speed
                if input_data.speed_x is not None:
                    self.speed_x = input_data.speed_x
                if input_data.speed_y is not None:
                    self.speed_y = input_data.speed_y
            
            # Check if movement status changed
            if old_movement != self.is_moving or old_direction != self.movement_direction:
                state_changed = True
        
        # Update with delta tracking data if available
        if hasattr(input_data, 'mouse_delta_x') and input_data.mouse_delta_x is not None:
            self.delta_x = input_data.mouse_delta_x
        if hasattr(input_data, 'mouse_delta_y') and input_data.mouse_delta_y is not None:
            self.delta_y = input_data.mouse_delta_y
        if hasattr(input_data, 'mouse_delta_magnitude') and input_data.mouse_delta_magnitude is not None:
            self.delta_magnitude = input_data.mouse_delta_magnitude
        if hasattr(input_data, 'mouse_delta_angle') and input_data.mouse_delta_angle is not None:
            self.delta_angle = input_data.mouse_delta_angle
        if hasattr(input_data, 'mouse_tracking_mode') and input_data.mouse_tracking_mode is not None:
            self.tracking_mode = input_data.mouse_tracking_mode
        
        # Update display text, but don't do it too often to avoid performance issues
        current_time = time.time()
        if state_changed or current_time - self.last_status_update > self.status_update_interval:
            self._update_status_text()
            self.last_status_update = current_time
        
        # Only redraw at a limited rate if needed
        if self.redraw_needed and current_time - self.last_ui_update > self.ui_update_interval:
            self._draw()
            self.last_ui_update = current_time
            self.redraw_needed = False
    
    def _update_status_text(self) -> None:
        """
        Update status text with minimal processing.
        
        Updates the status text labels to reflect the current mouse state.
        """
        # Update info text based on tracking mode
        if self.tracking_mode == "delta":
            status_text = f"Mouse: {'Moving' if self.is_moving else 'Not moving'}"
            if self.is_moving:
                status_text += f" | Δx:{self.delta_x:.1f} Δy:{self.delta_y:.1f}"
                status_text += f" | Mag:{self.delta_magnitude:.1f}"
            if self.movement_direction:
                status_text += f" | Dir:{self.movement_direction}"
            if self.wheel_direction:
                status_text += f" | Wheel:{self.wheel_direction}"
        elif self.tracking_mode == "angle":
            status_text = f"Mouse: {'Moving' if self.is_moving else 'Not moving'}"
            if self.is_moving:
                status_text += f" | Angle:{self.delta_angle:.1f}° Mag:{self.delta_magnitude:.1f}"
            if self.movement_direction:
                status_text += f" | Dir:{self.movement_direction}"
            if self.wheel_direction:
                status_text += f" | Wheel:{self.wheel_direction}"
        else:  # joystick mode
            status_text = f"Mouse: {'Moving' if self.is_moving else 'Not moving'}"
            if self.movement_direction and self.is_moving:
                status_text += f" | Dir:{self.movement_direction}"
            if self.is_moving:
                status_text += f" | Speed:{self.speed:.1f}"
            if self.wheel_direction:
                status_text += f" | Wheel:{self.wheel_direction}"
        
        # Update button text
        button_states = []
        if self.left_button_pressed:
            button_states.append("Left")
        if self.right_button_pressed:
            button_states.append("Right")
        if self.middle_button_pressed:
            button_states.append("Middle")
        
        button_text = "Buttons: " + (", ".join(button_states) if button_states else "None")
        
        # Update the StringVars which is more efficient than updating text widgets
        self.info_var.set(status_text)
        self.button_var.set(button_text)
    
    def _draw(self) -> None:
        """
        Draw the mouse visualization with joystick-like representation.
        
        Updates the dynamic visual elements of the mouse visualization
        based on the current state.
        """
        try:
            # Only update dynamic elements, not the whole canvas
            # Calculate joystick circle radius (use fixed percentage of the canvas)
            radius = min(self.canvas_width, self.canvas_height) * 0.25  # Reduced from 0.3 to 0.25
            
            # Calculate joystick position
            joystick_x = self.center_x + (self.rel_x * radius)
            joystick_y = self.center_y + (self.rel_y * radius)
            
            # Update joystick handle position (don't recreate it)
            handle_radius = radius * 0.1  # 10% of the circle radius
            
            # Calculate joystick magnitude (distance from center)
            joystick_magnitude = math.sqrt(self.rel_x**2 + self.rel_y**2)
            
            # Visual indicator for when at the edge
            if (joystick_magnitude > 0.95):  # Close to the edge
                # Use a fixed handle size at the edge for stability
                edge_color = "#402020"  # Dark red tint for the background in dark mode
                self.canvas.itemconfig("background", fill=edge_color)
                
                # Make the handle slightly larger at the edge
                handle_radius *= 1.2
                
                # Make the handle brighter at the edge
                handle_outline_width = 2
                handle_outline_color = "#FF5555"  # Brighter red in dark theme
            else:
                # Normal background and handle
                self.canvas.itemconfig("background", fill="#1E1E1E")  # Dark background
                handle_outline_width = 1
                handle_outline_color = "#FFFFFF"  # White outline
            
            # Update handle position and appearance
            self.canvas.coords(
                self.joystick_handle,
                joystick_x - handle_radius, joystick_y - handle_radius,
                joystick_x + handle_radius, joystick_y + handle_radius
            )
            
            self.canvas.itemconfig(
                self.joystick_handle, 
                outline=handle_outline_color,
                width=handle_outline_width
            )
            
            # Update handle color based on button state - more vibrant colors for dark theme
            handle_fill = "#FF5555" if self.left_button_pressed else \
                          "#5555FF" if self.right_button_pressed else \
                          "#AA55AA" if self.middle_button_pressed else \
                          self.accent_color
            self.canvas.itemconfig(self.joystick_handle, fill=handle_fill)
            
            # Update direction line if moving
            if self.is_moving and self.movement_direction:
                self.canvas.coords(
                    self.direction_line,
                    self.center_x, self.center_y,
                    joystick_x, joystick_y
                )
                self.canvas.itemconfig(self.direction_line, state=tk.NORMAL)
            else:
                self.canvas.itemconfig(self.direction_line, state=tk.HIDDEN)
            
            # Update wheel indicator if needed
            if self.wheel_direction:
                wheel_y_offset = -15 if self.wheel_direction == "up" else 15
                wheel_color = "#5FB878" if self.wheel_direction == "up" else "#FF5555"
                
                self.canvas.coords(
                    self.wheel_indicator,
                    joystick_x - 10, joystick_y + wheel_y_offset,
                    joystick_x, joystick_y + wheel_y_offset * 2,
                    joystick_x + 10, joystick_y + wheel_y_offset
                )
                self.canvas.itemconfig(
                    self.wheel_indicator, 
                    fill=wheel_color,
                    state=tk.NORMAL
                )
            else:
                self.canvas.itemconfig(self.wheel_indicator, state=tk.HIDDEN)
            
            # Update coordinate text based on tracking mode
            if self.tracking_mode == "delta":
                self.canvas.itemconfig(
                    self.coordinate_text,
                    text=f"Delta: ({self.delta_x:.2f}, {self.delta_y:.2f})"
                )
            elif self.tracking_mode == "angle":
                self.canvas.itemconfig(
                    self.coordinate_text,
                    text=f"Angle: {self.delta_angle:.1f}° Mag: {self.delta_magnitude:.1f}"
                )
            else:  # joystick mode
                self.canvas.itemconfig(
                    self.coordinate_text,
                    text=f"Rel: ({self.rel_x:.2f}, {self.rel_y:.2f})"
                )
        except Exception as e:
            print(f"Error drawing mouse viz: {e}")
    
    def get_frame(self) -> tk.Frame:
        """
        Get the tk Frame containing the mouse visualization.
        
        Returns:
            tk.Frame: The frame containing the mouse visualization
        """
        return self.frame