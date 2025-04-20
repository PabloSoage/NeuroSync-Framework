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
        result = {
            "event": event,
            "should_log": False,
            "display_text": "",
        }
        
        # Check for special toggle_recording event
        if event.event_type == "toggle_recording":
            if not self.f9_key_down:
                self.toggle_recording_requested.emit()
                self.f9_key_down = True
            return result
            
        # Handle F9 key release
        if event.event_type == "key_release" and event.key == "Key.media_play_pause":
            self.f9_key_down = False
            return result
        
        # Determine if we should log the event
        result["should_log"] = (
            (event.event_type == "key_press")
            or (event.event_type == "mouse_move" and event.is_moving)
            or (event.event_type == "mouse_click" and event.button_pressed is not None)
            or (event.event_type == "mouse_scroll" and event.direction is not None)
            or (event.event_type in ["button_press", "axis_motion"])
        )
        
        # Format display text based on collector type
        if collector_type == "ps4_controller":
            result["display_text"] = self._format_ps4_event_text(event)
        else:
            result["display_text"] = self._format_event_text(event)
        
        return result
    
    def _format_event_text(self, event: InputData) -> str:
        """Format keyboard/mouse event text for display."""
        # Format keyboard info
        keyboard_part = (
            f"Keys: [{', '.join(event.active_keys)}]"
            if event.active_keys
            else "Keys: []"
        )

        # Format mouse info based on tracking mode
        mouse_parts = []
        tracking_mode = getattr(event, "mouse_tracking_mode", "joystick")

        # Click info
        if event.event_type == "mouse_click" and event.button_pressed:
            mouse_parts.append(f"Click:{event.button_pressed}")
        elif hasattr(event, "button_pressed") and event.button_pressed:
            mouse_parts.append(f"Click:{event.button_pressed}")

        # Scroll info
        if event.event_type == "mouse_scroll" and event.direction:
            mouse_parts.append(f"Scroll:{event.direction}")

        # Movement info - mode specific
        if event.is_moving:
            if tracking_mode == "delta":
                if hasattr(event, "mouse_delta_x") and hasattr(event, "mouse_delta_y"):
                    mouse_parts.append(
                        f"Δx:{event.mouse_delta_x:.1f} Δy:{event.mouse_delta_y:.1f}"
                    )
                if hasattr(event, "mouse_delta_magnitude"):
                    mouse_parts.append(f"Mag:{event.mouse_delta_magnitude:.1f}")
                if event.direction:
                    mouse_parts.append(f"Dir:{event.direction}")
            elif tracking_mode == "angle":
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
            elif tracking_mode == "axis":
                if (
                    hasattr(event, "north")
                    and hasattr(event, "south")
                    and hasattr(event, "east")
                    and hasattr(event, "west")
                ):
                    mouse_parts.append(
                        f"N:{event.north:.1f} S:{event.south:.1f} E:{event.east:.1f} W:{event.west:.1f}"
                    )
            else:  # joystick mode
                if event.direction:
                    mouse_parts.append(f"Dir:{event.direction}")
                if event.speed is not None:
                    mouse_parts.append(f"Speed:{event.speed:.1f}")

        # Combine all mouse info
        mouse_part = (
            f"Mouse[{tracking_mode}]: {' | '.join(mouse_parts)}"
            if mouse_parts
            else f"Mouse[{tracking_mode}]: Idle"
        )

        return f"{keyboard_part} | {mouse_part}"
    
    def _format_ps4_event_text(self, event: InputData) -> str:
        """Format PS4 controller event text for display."""
        active_keys = (
            event.active_keys
            if hasattr(event, "active_keys") and event.active_keys
            else []
        )

        if event.event_type == "button_press":
            return f"Controller: Button {event.key} pressed | Active: {', '.join(active_keys)}"
        elif event.event_type == "button_release":
            return f"Controller: Button {event.key} released | Active: {', '.join(active_keys)}"
        elif event.event_type == "axis_motion":
            value = event.rel_x if event.rel_x is not None else event.rel_y
            if value is not None:
                if "Trigger" in event.key:
                    # For triggers, show as percentage
                    return f"Controller: {event.key} at {value*100:.0f}% | Active: {', '.join(active_keys)}"
                else:
                    # For joysticks, show as position
                    if "X" in event.key:
                        y_key = event.key.replace("_X", "_Y")
                        y_value = 0.0
                        # If we have rel_y, use it
                        if hasattr(event, "rel_y") and event.rel_y is not None:
                            y_value = event.rel_y
                            
                        direction = ""
                        if abs(value) > 0.1 or abs(y_value) > 0.1:
                            if abs(value) > 0.1:
                                direction += "X+" if value > 0 else "X-"
                            if abs(y_value) > 0.1:
                                direction += "Y+" if y_value > 0 else "Y-"
                        direction_text = f" Dir:{direction}" if direction else ""
                        return f"Controller: {event.key.replace('_X', '')} pos:({value:.2f}, {y_value:.2f}){direction_text} | Active: {', '.join(active_keys)}"
                    else:
                        return f"Controller: {event.key} at {value:.2f} | Active: {', '.join(active_keys)}"

        return f"Controller: {event.event_type} | Active: {', '.join(active_keys)}"
