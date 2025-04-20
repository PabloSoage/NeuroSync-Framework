"""
Event processor module.

Provides processing of input events for display, logging, and visualization.
"""

from typing import Dict, Any, Optional, List
from PyQt5.QtCore import QObject, pyqtSignal

from ..interfaces import InputData


class EventProcessor(QObject):
    """
    Processes input events for display and logging.
    
    This class is responsible for formatting and processing input events
    for display in the UI, logging to files, and updating visualizers.
    """
    
    # Signal when F9 key is pressed to toggle recording
    toggle_recording_requested = pyqtSignal()
    
    def __init__(self) -> None:
        """Initialize the event processor."""
        super().__init__()
        self.f9_key_down = False
    
    def process_event(self, event: InputData, collector_type: str) -> Dict[str, Any]:
        """
        Process an input event.
        
        Args:
            event: The input event to process
            collector_type: Type of collector that generated the event
            
        Returns:
            Dict[str, Any]: Processed event information
        """
        # 1. First check if this is a special event that needs special handling
        if self._is_special_event(event):
            return self._process_special_event(event)
            
        # 2. Determine if this event should be logged
        should_log = self._should_log_event(event)
        
        # 3. Format display text based on collector type
        display_text = self._format_display_text(event, collector_type)
        
        # 4. Return processed information
        return {
            "event": event,
            "should_log": should_log,
            "display_text": display_text,
        }
    
    def _is_special_event(self, event: InputData) -> bool:
        """
        Check if this is a special event that needs special handling.
        
        Args:
            event: The event to check
            
        Returns:
            bool: True if this is a special event
        """
        if event.event_type == "toggle_recording":
            return True
            
        if event.event_type == "key_release" and event.key == "Key.media_play_pause":
            return True
            
        return False
    
    def _process_special_event(self, event: InputData) -> Dict[str, Any]:
        """
        Process a special event.
        
        Args:
            event: The special event to process
            
        Returns:
            Dict[str, Any]: Processed event information
        """
        result = {
            "event": event,
            "should_log": False,
            "display_text": "",
        }
        
        if event.event_type == "toggle_recording":
            if not self.f9_key_down:
                self.toggle_recording_requested.emit()
                self.f9_key_down = True
                
        elif event.event_type == "key_release" and event.key == "Key.media_play_pause":
            self.f9_key_down = False
            
        return result
    
    def _should_log_event(self, event: InputData) -> bool:
        """
        Determine if an event should be logged.
        
        Args:
            event: The event to check
            
        Returns:
            bool: True if the event should be logged
        """
        return (
            (event.event_type == "key_press")
            or (event.event_type == "mouse_move" and event.is_moving)
            or (event.event_type == "mouse_click" and event.button_pressed is not None)
            or (event.event_type == "mouse_scroll" and event.direction is not None)
            or (event.event_type in ["button_press", "axis_motion"])
        )
    
    def _format_display_text(self, event: InputData, collector_type: str) -> str:
        """
        Format event text for display.
        
        Args:
            event: The event to format
            collector_type: Type of collector that generated the event
            
        Returns:
            str: Formatted display text
        """
        if collector_type == "ps4_controller":
            return self._format_ps4_event_text(event)
        else:
            return self._format_keyboard_mouse_event_text(event)
    
    def _format_keyboard_mouse_event_text(self, event: InputData) -> str:
        """Format keyboard/mouse event text for display."""
        # Format keyboard info
        keyboard_part = self._format_keyboard_part(event)

        # Format mouse info based on tracking mode
        mouse_part = self._format_mouse_part(event)

        return f"{keyboard_part} | {mouse_part}"
    
    def _format_keyboard_part(self, event: InputData) -> str:
        """Format the keyboard part of the display text."""
        return (
            f"Keys: [{', '.join(event.active_keys)}]"
            if event.active_keys
            else "Keys: []"
        )
    
    def _format_mouse_part(self, event: InputData) -> str:
        """Format the mouse part of the display text based on tracking mode."""
        tracking_mode = getattr(event, "mouse_tracking_mode", "joystick")
        mouse_parts = []
        
        # Add click info
        if self._has_button_press(event):
            mouse_parts.append(f"Click:{event.button_pressed}")

        # Add scroll info
        if self._has_scroll_event(event):
            mouse_parts.append(f"Scroll:{event.direction}")

        # Add movement info based on tracking mode
        if event.is_moving:
            self._add_movement_info(mouse_parts, event, tracking_mode)

        # Combine all mouse info
        return (
            f"Mouse[{tracking_mode}]: {' | '.join(mouse_parts)}"
            if mouse_parts
            else f"Mouse[{tracking_mode}]: Idle"
        )
    
    def _has_button_press(self, event: InputData) -> bool:
        """Check if event has button press information."""
        return ((event.event_type == "mouse_click" and event.button_pressed) or
                (hasattr(event, "button_pressed") and event.button_pressed))
    
    def _has_scroll_event(self, event: InputData) -> bool:
        """Check if event has scroll information."""
        return (event.event_type == "mouse_scroll" and event.direction)
    
    def _add_movement_info(self, mouse_parts: List[str], event: InputData, tracking_mode: str) -> None:
        """Add movement information to mouse parts based on tracking mode."""
        if tracking_mode == "delta":
            self._add_delta_mode_info(mouse_parts, event)
        elif tracking_mode == "angle":
            self._add_angle_mode_info(mouse_parts, event)
        elif tracking_mode == "axis":
            self._add_axis_mode_info(mouse_parts, event)
        else:  # joystick mode
            self._add_joystick_mode_info(mouse_parts, event)
    
    def _add_delta_mode_info(self, mouse_parts: List[str], event: InputData) -> None:
        """Add delta mode specific movement info."""
        if hasattr(event, "mouse_delta_x") and hasattr(event, "mouse_delta_y"):
            mouse_parts.append(
                f"Δx:{event.mouse_delta_x:.1f} Δy:{event.mouse_delta_y:.1f}"
            )
        if hasattr(event, "mouse_delta_magnitude"):
            mouse_parts.append(f"Mag:{event.mouse_delta_magnitude:.1f}")
        if event.direction:
            mouse_parts.append(f"Dir:{event.direction}")
    
    def _add_angle_mode_info(self, mouse_parts: List[str], event: InputData) -> None:
        """Add angle mode specific movement info."""
        if hasattr(event, "direction_only") and event.direction_only:
            if hasattr(event, "discrete_angle"):
                mouse_parts.append(f"Angle:{event.discrete_angle}°")
        else:
            if hasattr(event, "mouse_delta_angle"):
                mouse_parts.append(f"Angle:{event.mouse_delta_angle:.1f}°")
            if hasattr(event, "mouse_delta_magnitude"):
                mouse_parts.append(f"Mag:{event.mouse_delta_magnitude:.1f}")
                
        if event.direction:
            mouse_parts.append(f"Dir:{event.direction}")
    
    def _add_axis_mode_info(self, mouse_parts: List[str], event: InputData) -> None:
        """Add axis mode specific movement info."""
        if (
            hasattr(event, "north") and hasattr(event, "south") and
            hasattr(event, "east") and hasattr(event, "west")
        ):
            mouse_parts.append(
                f"N:{event.north:.1f} S:{event.south:.1f} E:{event.east:.1f} W:{event.west:.1f}"
            )
    
    def _add_joystick_mode_info(self, mouse_parts: List[str], event: InputData) -> None:
        """Add joystick mode specific movement info."""
        if event.direction:
            mouse_parts.append(f"Dir:{event.direction}")
        if event.speed is not None:
            mouse_parts.append(f"Speed:{event.speed:.1f}")
    
    def _format_ps4_event_text(self, event: InputData) -> str:
        """Format PS4 controller event text for display."""
        # Get active keys list or empty list if not available
        active_keys = (
            event.active_keys
            if hasattr(event, "active_keys") and event.active_keys
            else []
        )
        
        # Format text based on event type
        if event.event_type == "button_press":
            return f"Controller: Button {event.key} pressed | Active: {', '.join(active_keys)}"
        elif event.event_type == "button_release":
            return f"Controller: Button {event.key} released | Active: {', '.join(active_keys)}"
        elif event.event_type == "axis_motion":
            return self._format_axis_motion(event, active_keys)
        
        # Default format for other events
        return f"Controller: {event.event_type} | Active: {', '.join(active_keys)}"
    
    def _format_axis_motion(self, event: InputData, active_keys: List[str]) -> str:
        """Format axis motion event text for PS4 controller."""
        value = event.rel_x if event.rel_x is not None else event.rel_y
        
        if value is not None:
            if "Trigger" in event.key:
                # Format trigger value as percentage
                return f"Controller: {event.key} at {value*100:.0f}% | Active: {', '.join(active_keys)}"
            else:
                # Process joystick axis motion
                return self._format_joystick_axis(event, active_keys)
        
        return f"Controller: {event.key} motion | Active: {', '.join(active_keys)}"
    
    def _format_joystick_axis(self, event: InputData, active_keys: List[str]) -> str:
        """Format joystick axis motion text."""
        if "X" in event.key:
            base_name = event.key.replace("_X", "")
            y_key = f"{base_name}_Y"
            y_value = 0.0
            
            # Try to get Y value if available
            if hasattr(event, "rel_y") and event.rel_y is not None:
                y_value = event.rel_y
                
            # Get X value
            x_value = event.rel_x if event.rel_x is not None else 0.0
            
            # Generate direction text if there's significant movement
            direction = ""
            if abs(x_value) > 0.1 or abs(y_value) > 0.1:
                if abs(x_value) > 0.1:
                    direction += "X+" if x_value > 0 else "X-"
                if abs(y_value) > 0.1:
                    direction += "Y+" if y_value > 0 else "Y-"
                    
            direction_text = f" Dir:{direction}" if direction else ""
            return f"Controller: {base_name} pos:({x_value:.2f}, {y_value:.2f}){direction_text} | Active: {', '.join(active_keys)}"
        else:
            # Single axis value
            value = event.rel_x if event.rel_x is not None else 0.0
            return f"Controller: {event.key} at {value:.2f} | Active: {', '.join(active_keys)}"
