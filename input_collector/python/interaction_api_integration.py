"""
Interaction API integration for the input collector.

This module integrates the input collector's interaction API with the API Explorer,
registering its methods and handling API requests.
"""

import asyncio
import logging
import os
import sys
import time
from typing import Optional, Dict, List, Any, Callable, Union, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Try to import the API Explorer
try:
    from api_explorer import ApiExplorer

    explorer_available = True
except ImportError:
    explorer_available = False
    logger.warning("API Explorer not found. Web API will not be available.")

# Import the InputCollectorAPI
from .interaction_api import InputCollectorAPI

# Import core event system
from .core.event_system import EventType, subscribe, unsubscribe

# Import API integration for reusing event processing functions
from .api_integration import get_api_integration


class InteractionApiIntegration:
    """
    Integrates the input collector's interaction API with the API Explorer.

    This class exposes the input collector's interaction API methods through the API Explorer.
    """

    def __init__(self) -> None:
        """Initialize the API integration."""
        self.explorer: Optional[Any] = None
        self.module_id = "input_collector_control"
        self.is_registered = False

        # For storing method groups and methods when fallback is used
        self.fallback_method_groups: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.fallback_methods: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}

        # Module registration status flag
        self.module_registered = False

        # For tracking event subscriptions
        self._event_subscriptions: List[tuple[EventType, Callable]] = []
        self._pressed_buttons: Set[str] = set()

        # Reference to data API integration for reusing event processing functions
        self.data_api_integration = None

        # PS4 controller state tracking - same as in api_integration.py
        self._ps4_button_states: Dict[str, bool] = {}
        self._ps4_active_buttons: Set[str] = set()
        self._ps4_stick_states: Dict[str, Dict[str, Union[float, str]]] = {
            "left": {"x": 0.0, "y": 0.0, "direction": "center"},
            "right": {"x": 0.0, "y": 0.0, "direction": "center"},
        }
        self._ps4_trigger_states: Dict[str, float] = {"left": 0.0, "right": 0.0}

    def register_api(
        self, start_server: bool = True, host: str = "127.0.0.1", port: int = 8001
    ) -> bool:
        """
        Registers the input collector's interaction API with the Explorer.

        Args:
            start_server: Whether to launch the API Explorer server.
            host: Server host address.
            port: Server port number.

        Returns:
            True if the API was successfully registered, False otherwise.
        """
        if not explorer_available:
            return False

        try:
            # Get a reference to the ApiExplorer singleton
            explorer_instance = ApiExplorer.get_instance()
            self.explorer = explorer_instance

            # Integrate the data module and its methods first
            data_integration = get_api_integration()
            data_integration.explorer = self.explorer
            if not data_integration.module_registered:
                data_integration._register_module()
            data_integration._register_all_methods()
            data_integration._setup_websocket_events()

            # Add control methods to the same data module
            self.module_id = data_integration.module_id
            self.module_registered = True
            self._register_all_methods()

            # Register any additional websocket events (only needed once)
            self._setup_websocket_events()

            # Start the server if it's not already running
            if (
                start_server
                and hasattr(self.explorer, "start_server")
                and self.explorer is not None
                and hasattr(self.explorer, "is_running")
                and not self.explorer.is_running
            ):
                self.explorer.start_server(host=host, port=port, block=False)

            self.is_registered = True
            return True

        except Exception as e:
            logger.error(f"Error registering interaction API: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _setup_websocket_events(self) -> None:
        """Set up event handlers for websocket real-time events."""
        # Subscribe to core events for websocket forwarding
        self._subscribe_to_core_events()

    def _subscribe_to_core_events(self) -> None:
        """Subscribe to core events from event system."""
        for event_type in EventType:

            def handler(data: Any, evnt_type: EventType = event_type) -> None:
                self._handle_core_event(evnt_type, data)

            subscribe(event_type, handler)
            self._event_subscriptions.append((event_type, handler))

        logger.info("Subscribed to core events for real-time forwarding")

    def _format_mouse_event(self, event_data: Any) -> Optional[Dict]:
        """
        Format a mouse event based on its tracking mode.

        Args:
            event_data: Mouse event data

        Returns:
            Dict: Formatted event for websocket broadcast or None if error
        """
        # Reuse data_api_integration's function if available
        if self.data_api_integration and hasattr(
            self.data_api_integration, "_format_mouse_event"
        ):
            return self.data_api_integration._format_mouse_event(event_data)

        # Fallback implementation if data_api_integration is not available
        try:
            # Get the tracking mode
            mode = getattr(event_data, "mouse_tracking_mode", "joystick")
            direction_only = getattr(event_data, "direction_only", False)

            # Initialize the formatted event
            formatted_event = {
                "type": "mouse_movement",
                "timestamp": event_data.timestamp,
                "tracking_mode": mode,
                "direction_only": direction_only,
            }

            # Format based on tracking mode
            if mode == "axis" and direction_only:
                # Extract axis values
                formatted_event["north"] = getattr(event_data, "north", 0)
                formatted_event["south"] = getattr(event_data, "south", 0)
                formatted_event["east"] = getattr(event_data, "east", 0)
                formatted_event["west"] = getattr(event_data, "west", 0)

                # Generate a status string like in the GUI
                active_directions = []
                if formatted_event["north"] > 0.2:
                    active_directions.append("UP")
                if formatted_event["south"] > 0.2:
                    active_directions.append("DOWN")
                if formatted_event["east"] > 0.2:
                    active_directions.append("RIGHT")
                if formatted_event["west"] > 0.2:
                    active_directions.append("LEFT")

                formatted_event["status"] = (
                    " + ".join(active_directions) if active_directions else "NONE"
                )

            elif mode == "angle" and direction_only:
                # Extract angle value
                angle = getattr(event_data, "discrete_angle", 0)
                formatted_event["angle"] = angle

                # Determine direction name based on angle
                direction = self._angle_to_direction(angle)
                formatted_event["status"] = direction

            elif mode == "angle" and not direction_only:
                # Extract continuous angle and magnitude values
                formatted_event["angle"] = getattr(event_data, "mouse_delta_angle", 0.0)
                formatted_event["magnitude"] = getattr(
                    event_data, "mouse_delta_magnitude", 0.0
                )

                # Generate status string
                if getattr(event_data, "is_moving", False):
                    formatted_event["status"] = (
                        f"ANGLE: {formatted_event['angle']:.1f}°, MAG: {formatted_event['magnitude']:.1f}"
                    )
                else:
                    formatted_event["status"] = "IDLE"

            elif mode == "delta":
                # Extract delta values
                formatted_event["delta_x"] = getattr(event_data, "mouse_delta_x", 0)
                formatted_event["delta_y"] = getattr(event_data, "mouse_delta_y", 0)
                formatted_event["magnitude"] = getattr(
                    event_data, "mouse_delta_magnitude", 0
                )

                # Generate status string
                if getattr(event_data, "is_moving", False):
                    formatted_event["status"] = (
                        f"DELTA: {formatted_event['delta_x']:.1f}, {formatted_event['delta_y']:.1f}"
                    )
                else:
                    formatted_event["status"] = "IDLE"

            elif mode == "joystick":
                # Extract joystick values
                formatted_event["rel_x"] = getattr(event_data, "rel_x", 0)
                formatted_event["rel_y"] = getattr(event_data, "rel_y", 0)
                # Add speed value
                formatted_event["speed"] = getattr(event_data, "speed", 0)
                # Add direction information
                formatted_event["direction"] = getattr(event_data, "direction", None)

                # Generate status string
                if getattr(event_data, "is_moving", False):
                    formatted_event["status"] = (
                        f"X: {formatted_event['rel_x']:.2f}, Y: {formatted_event['rel_y']:.2f}"
                    )
                else:
                    formatted_event["status"] = "IDLE"

            # Add active keys if any
            active_keys = getattr(event_data, "active_keys", [])
            if active_keys:
                formatted_event["active_keys"] = active_keys

            return formatted_event
        except Exception as e:
            logger.error(f"Error formatting mouse event: {e}")
            return None

    def _angle_to_direction(self, angle: int) -> str:
        """Convert an angle to a human-readable direction."""
        # If data_api_integration has the function, use it
        if self.data_api_integration and hasattr(
            self.data_api_integration, "_angle_to_direction"
        ):
            return self.data_api_integration._angle_to_direction(angle)

        # Fallback implementation
        directions = {
            0: "RIGHT",
            45: "DOWN-RIGHT",
            90: "DOWN",
            135: "DOWN-LEFT",
            180: "LEFT",
            225: "UP-LEFT",
            270: "UP",
            315: "UP-RIGHT",
        }

        # Find the closest direction
        closest = min(directions.keys(), key=lambda k: abs(k - angle))
        return directions[closest]

    def _handle_core_event(self, event_type: EventType, data: Any) -> None:
        """
        Handle events from the core event system.

        Args:
            event_type: Type of event
            data: Event data
        """
        try:
            # 1) Update button state before filtering release
            if (
                event_type == EventType.INPUT
                and getattr(data, "event_type", "") == "mouse_click"
            ):
                if getattr(data, "button_pressed", None):
                    self._pressed_buttons.add(data.button_pressed)
                else:
                    btn = getattr(data, "button", None)
                    if btn:
                        self._pressed_buttons.discard(btn)

            # 2) Special handling for PS4 controller events to maintain state
            if (
                event_type == EventType.INPUT
                and hasattr(data, "event_type")
                and data.event_type in ["button_press", "button_release", "axis_motion"]
            ):
                self._update_ps4_controller_state(data)

            # 3) Skip key_release y scroll como antes...
            if (
                event_type == EventType.INPUT
                and getattr(data, "event_type", "") == "key_release"
            ):
                return

            # Skip INPUT events with key_release in a dict structure
            if (
                event_type == EventType.INPUT
                and isinstance(data, dict)
                and data.get("event_type") == "key_release"
            ):
                return

            # Skip any event with key_release regardless of structure
            if isinstance(data, dict) and "key_release" in str(data):
                return

            # Only broadcast real clicks, not release-without-button
            if (
                event_type == EventType.INPUT
                and getattr(data, "event_type", "") == "mouse_click"
                and not getattr(data, "button_pressed", None)
            ):
                return
            # Only broadcast scroll start, not scroll-stop (direction None)
            if (
                event_type == EventType.INPUT
                and getattr(data, "event_type", "") == "mouse_scroll"
                and not getattr(data, "direction", None)
            ):
                return

            # 4) Unify InputData in payload
            if event_type == EventType.INPUT and hasattr(data, "event_type"):
                # Create unified payload structure
                payload = {
                    "timestamp": getattr(data, "timestamp", time.time()),
                    "event_type": data.event_type,
                }

                # Handle PS4 controller events specifically
                is_ps4_event = data.event_type in [
                    "button_press",
                    "button_release",
                    "axis_motion",
                ]

                # Enhanced handling for PS4 controller events
                if is_ps4_event:
                    # For button events, add pressed/released button info
                    if (
                        data.event_type in ["button_press", "button_release"]
                        and hasattr(data, "key")
                        and data.key
                    ):
                        # Use button_event format for button events
                        payload["button_event"] = {
                            "button": data.key,
                            "action": (
                                "pressed"
                                if data.event_type == "button_press"
                                else "released"
                            ),
                        }

                        # Add complete PS4 state to all PS4 events
                        payload["ps4_state"] = self._get_ps4_controller_state()

                    # For axis motion events, add detailed stick/trigger info
                    elif data.event_type == "axis_motion":
                        # Complete information about which control was moved
                        self._add_ps4_control_details_to_payload(payload, data)
                else:
                    # For non-PS4 events, handle keyboard and mouse events
                    # Add the keys information for non-PS4 events
                    payload["keys"] = getattr(data, "active_keys", [])

                    # Movement subsection for mouse_move
                    if data.event_type == "mouse_move" and hasattr(
                        data, "mouse_tracking_mode"
                    ):
                        # Movement data population for mouse_move events
                        movement_data = self._format_mouse_event(data)

                        if movement_data:
                            # Extract only the movement-specific fields
                            payload["movement"] = {
                                "tracking_mode": movement_data.get("tracking_mode"),
                                "direction_only": movement_data.get("direction_only"),
                                "status": movement_data.get("status"),
                            }

                            # Add mode-specific fields
                            for key in [
                                "north",
                                "south",
                                "east",
                                "west",
                                "angle",
                                "magnitude",
                                "delta_x",
                                "delta_y",
                                "rel_x",
                                "rel_y",
                                "speed",
                                "direction",
                            ]:
                                if key in movement_data:
                                    payload["movement"][key] = movement_data[key]
                    else:
                        payload["movement"] = {}

                    # Click subsection - for non-PS4 events
                    payload["click"] = {"buttons": list(self._pressed_buttons)}

                    # Scroll subsection - only for mouse_scroll events with direction
                    if data.event_type == "mouse_scroll" and getattr(
                        data, "direction", None
                    ):
                        payload["scroll"] = {"direction": data.direction}
                    else:
                        payload["scroll"] = {}

                    # Key subsection - for keyboard events
                    payload["key"] = {}
                    if (
                        data.event_type == "key_press"
                        and hasattr(data, "key")
                        and data.key
                    ):
                        payload["key"] = {"pressed": data.key}

                # 5) Filter empty fields and add ID for all events
                self._filter_empty_fields(payload)
                payload["event_id"] = (
                    f"{str(time.time()).replace('.', '')}_{id(payload)}"
                )

                # Broadcast unified event
                self._broadcast_event(payload)
                return

            # For other event types (not InputData)
            # Create a standard event payload
            event_payload = {
                "type": event_type.name,
                "data": (
                    self._event_to_dict(data) if hasattr(data, "__dict__") else data
                ),
                "timestamp": time.time(),
            }

            # Add specific fields based on event type
            if isinstance(data, dict) and "timestamp" in data:
                event_payload["timestamp"] = data["timestamp"]

            # Broadcast the event
            self._broadcast_event(event_payload)
        except Exception as e:
            logger.error(f"Error handling core event: {e}")
            import traceback

            traceback.print_exc()

    def _update_ps4_controller_state(self, data: Any) -> None:
        """
        Update the internal PS4 controller state based on an event.

        Args:
            data: Event data for a PS4 controller event
        """
        # Handle button press events
        if data.event_type == "button_press" and getattr(data, "key", None):
            button_name = data.key
            self._ps4_button_states[button_name] = True
            self._ps4_active_buttons.add(button_name)

        # Handle button release events
        elif data.event_type == "button_release" and getattr(data, "key", None):
            button_name = data.key
            self._ps4_button_states[button_name] = False
            self._ps4_active_buttons.discard(button_name)

        # Handle axis motion events
        elif data.event_type == "axis_motion" and getattr(data, "key", None):
            key = data.key

            # Handle stick movement
            if "Left_Stick" in key:
                x_value = getattr(data, "rel_x", 0)
                y_value = getattr(data, "rel_y", 0)
                direction = "center"
                if self.data_api_integration and hasattr(
                    self.data_api_integration, "_get_stick_direction"
                ):
                    direction = self.data_api_integration._get_stick_direction(
                        x_value, y_value
                    )
                self._ps4_stick_states["left"] = {
                    "x": x_value,
                    "y": y_value,
                    "direction": direction,
                }

            elif "Right_Stick" in key:
                x_value = getattr(data, "rel_x", 0)
                y_value = getattr(data, "rel_y", 0)
                direction = "center"
                if self.data_api_integration and hasattr(
                    self.data_api_integration, "_get_stick_direction"
                ):
                    direction = self.data_api_integration._get_stick_direction(
                        x_value, y_value
                    )
                self._ps4_stick_states["right"] = {
                    "x": x_value,
                    "y": y_value,
                    "direction": direction,
                }

            # Handle trigger movement
            elif "Left_Trigger" in key:
                value = getattr(data, "rel_x", 0)
                self._ps4_trigger_states["left"] = value

            elif "Right_Trigger" in key:
                value = getattr(data, "rel_x", 0)
                self._ps4_trigger_states["right"] = value

    def _get_ps4_controller_state(self) -> Dict[str, Any]:
        """
        Get the complete current state of the PS4 controller.

        Returns:
            Dict: The current state of all PS4 controls
        """
        # Process sticks to include percentages and consistent directions
        left_stick_data = self._ps4_stick_states["left"]
        right_stick_data = self._ps4_stick_states["right"]

        # Extract values and ensure they're floats
        left_stick_x = (
            float(left_stick_data["x"])
            if isinstance(left_stick_data["x"], (int, float))
            else 0.0
        )
        left_stick_y = (
            float(left_stick_data["y"])
            if isinstance(left_stick_data["y"], (int, float))
            else 0.0
        )
        right_stick_x = (
            float(right_stick_data["x"])
            if isinstance(right_stick_data["x"], (int, float))
            else 0.0
        )
        right_stick_y = (
            float(right_stick_data["y"])
            if isinstance(right_stick_data["y"], (int, float))
            else 0.0
        )
        left_trigger_val = self._ps4_trigger_states["left"]
        right_trigger_val = self._ps4_trigger_states["right"]

        # Calculate directions
        left_direction = "center"
        right_direction = "center"
        if self.data_api_integration and hasattr(
            self.data_api_integration, "_get_stick_direction"
        ):
            left_direction = self.data_api_integration._get_stick_direction(
                left_stick_x, left_stick_y
            )
            right_direction = self.data_api_integration._get_stick_direction(
                right_stick_x, right_stick_y
            )

        return {
            "active_buttons": list(self._ps4_active_buttons),
            "sticks": {
                "left": {
                    "x": left_stick_x,
                    "y": left_stick_y,
                    "direction": left_direction,
                    "percentage_x": f"{int(abs(left_stick_x) * 100)}%",
                    "percentage_y": f"{int(abs(left_stick_y) * 100)}%",
                },
                "right": {
                    "x": right_stick_x,
                    "y": right_stick_y,
                    "direction": right_direction,
                    "percentage_x": f"{int(abs(right_stick_x) * 100)}%",
                    "percentage_y": f"{int(abs(right_stick_y) * 100)}%",
                },
            },
            "triggers": {
                "left": {
                    "value": left_trigger_val,
                    "percentage": f"{int(abs(left_trigger_val) * 100)}%",
                },
                "right": {
                    "value": right_trigger_val,
                    "percentage": f"{int(abs(right_trigger_val) * 100)}%",
                },
            },
        }

    def _add_ps4_movement_to_payload(self, payload: Dict) -> None:
        """
        Add PS4 movement data to the payload.

        Args:
            payload: The payload to update
        """
        # Include both sticks in the movement section
        left_stick = self._ps4_stick_states["left"]
        right_stick = self._ps4_stick_states["right"]

        payload["movement"] = {
            "left_stick": {
                "x": left_stick["x"],
                "y": left_stick["y"],
                "direction": left_stick["direction"],
            },
            "right_stick": {
                "x": right_stick["x"],
                "y": right_stick["y"],
                "direction": right_stick["direction"],
            },
            "left_trigger": self._ps4_trigger_states["left"],
            "right_trigger": self._ps4_trigger_states["right"],
        }

    def _add_ps4_control_details_to_payload(self, payload: Dict, data: Any) -> None:
        """
        Add PS4 control details to the payload.

        Args:
            payload: The payload to update
            data: The event data
        """
        # Identify which control this is based on the key field
        control_type = None
        control_name = None

        if hasattr(data, "key"):
            key = data.key
            if "Left_Stick" in key:
                control_type = "stick"
                control_name = "left_stick"
            elif "Right_Stick" in key:
                control_type = "stick"
                control_name = "right_stick"
            elif "Left_Trigger" in key:
                control_type = "trigger"
                control_name = "left_trigger"
            elif "Right_Trigger" in key:
                control_type = "trigger"
                control_name = "right_trigger"

        # For stick movement
        if control_type == "stick" and control_name:
            # Get X and Y values
            x_value = getattr(data, "rel_x", 0)
            y_value = getattr(data, "rel_y", 0)

            direction = "unknown"
            if self.data_api_integration and hasattr(
                self.data_api_integration, "_get_stick_direction"
            ):
                direction = self.data_api_integration._get_stick_direction(
                    x_value, y_value
                )

            # Reuse the full controller state to be consistent
            ps4_state = self._get_ps4_controller_state()

            # Add event-specific info
            payload["motion_event"] = {
                "control_type": control_type,
                "control_name": control_name,
                "x": x_value,
                "y": y_value,
                "direction": direction,
                "percentage_x": f"{int(abs(x_value) * 100)}%",
                "percentage_y": f"{int(abs(y_value) * 100)}%",
            }

            # Update stick state in the ps4_state - use simplified name for indexing
            stick_name = control_name.split("_")[0]  # Extract "left" or "right" part
            ps4_state["sticks"][stick_name] = {
                "x": x_value,
                "y": y_value,
                "direction": direction,
                "percentage_x": f"{int(abs(x_value) * 100)}%",
                "percentage_y": f"{int(abs(y_value) * 100)}%",
            }

            # Update PS4 state in the payload
            payload["ps4_state"] = ps4_state

        # For trigger movement
        elif control_type == "trigger" and control_name:
            # Get trigger value
            value = getattr(data, "rel_x", 0)
            percentage = f"{int(abs(value) * 100)}%"

            # Reuse the full controller state to be consistent
            ps4_state = self._get_ps4_controller_state()

            # Add event-specific info
            payload["motion_event"] = {
                "control_type": control_type,
                "control_name": control_name,
                "value": value,
                "percentage": percentage,
            }

            # Update trigger state in the ps4_state - use simplified name for indexing
            trigger_name = control_name.split("_")[0]  # Extract "left" or "right" part
            ps4_state["triggers"][trigger_name] = {
                "value": value,
                "percentage": percentage,
            }

            # Update PS4 state in the payload
            payload["ps4_state"] = ps4_state

    def _filter_empty_fields(self, payload: Dict) -> None:
        """
        Remove empty fields from the payload for cleaner JSON.

        Args:
            payload: The payload to filter
        """
        # Find keys with empty values
        empty_keys = []
        for key, value in payload.items():
            if isinstance(value, dict) and not value:
                empty_keys.append(key)
            elif isinstance(value, list) and not value:
                empty_keys.append(key)

        # Remove empty keys
        for key in empty_keys:
            del payload[key]

    def _event_to_dict(self, event: Any) -> Dict:
        """Convert an event object to a serializable dictionary."""
        # Reuse data_api_integration's function if available
        if self.data_api_integration and hasattr(
            self.data_api_integration, "_event_to_dict"
        ):
            return self.data_api_integration._event_to_dict(event)

        # Fallback implementation
        # Check if it's an InputData object with to_dict method
        if hasattr(event, "to_dict") and callable(getattr(event, "to_dict")):
            return event.to_dict()

        # Fall back to class name check if to_dict doesn't exist
        elif hasattr(event, "__class__") and event.__class__.__name__ == "InputData":
            # Create a dict with all non-None fields
            event_dict = {}
            for key, value in event.__dict__.items():
                if not key.startswith("_") and value is not None:
                    # Convert lists to JSON-safe lists
                    if isinstance(value, list):
                        event_dict[key] = list(
                            value
                        )  # Create a copy to avoid reference issues
                    else:
                        event_dict[key] = value
            return event_dict

        # For other objects, use generic approach
        try:
            # Try to convert to dict if possible
            if hasattr(event, "__dict__"):
                return {
                    k: v
                    for k, v in event.__dict__.items()
                    if not k.startswith("_") and v is not None
                }
            elif isinstance(event, dict):
                return event
            else:
                # Convert to string if we can't do anything else
                return {"value": str(event)}
        except:
            # Last resort - convert to string
            return {"value": str(event)}

    def _broadcast_event(self, event_dict: Dict) -> None:
        """Broadcast an event through the WebSocket connection."""
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Create broadcast coroutine
        async def broadcast() -> None:
            try:
                # Add JSON serialization check
                import json

                try:
                    # Test serialization before sending
                    json.dumps(event_dict)
                except TypeError as e:
                    # Something isn't serializable - fix problematic fields
                    logger.warning(
                        f"Event not fully serializable: {e}. Converting problematic fields."
                    )
                    event_dict_copy = event_dict.copy()
                    for key, value in event_dict_copy.items():
                        try:
                            json.dumps({key: value})
                        except:
                            # Convert problematic value to string
                            event_dict[key] = str(value)

                # Add unique ID to event to prevent WebSocket buffer issues
                # This ensures each event is uniquely identified
                event_dict["event_id"] = (
                    f"{str(time.time()).replace('.', '')}_{id(event_dict)}"
                )

                # Ensure timestamp has micro precision to avoid identical timestamps
                if "timestamp" in event_dict:
                    event_dict["timestamp"] = float(f"{event_dict['timestamp']:.6f}")

                if self.explorer is not None:
                    await self.explorer.broadcast_event(self.module_id, event_dict)
            except Exception as e:
                logger.error(f"Error in broadcast_event: {e}")
                import traceback

                traceback.print_exc()

        # Run the broadcast
        try:
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(broadcast(), loop)
            else:
                loop.run_until_complete(broadcast())
        except Exception as e:
            logger.error(f"Error in event loop: {e}")

    def _register_module(self) -> bool:
        """Register the input collector control module."""
        try:
            if hasattr(self.explorer, "register_module") and self.explorer is not None:
                self.explorer.register_module(
                    module_id=self.module_id,
                    name="Input Collector Control",
                    description="API for controlling the input collector application",
                )
                logger.info(f"Module '{self.module_id}' registered with API Explorer")
                self.module_registered = True
            else:
                self._register_module_fallback()
            return self.module_registered
        except Exception as e:
            logger.error(f"Error registering module: {e}")
            return False

    def _register_module_fallback(self) -> bool:
        """Register module using fallback mechanism if standard method isn't available."""
        logger.warning("Using fallback module registration")
        try:
            # Create modules dict if it doesn't exist
            if not hasattr(self.explorer, "modules"):
                setattr(self.explorer, "modules", {})

            # Create a router for this module
            router = None
            try:
                from fastapi import APIRouter

                router = APIRouter(
                    prefix=f"/api/{self.module_id}", tags=["Input Collector Control"]
                )

                # If explorer has an app attribute, add the router directly
                if hasattr(self.explorer, "app") and self.explorer is not None:
                    self.explorer.app.include_router(router)
            except Exception as e:
                logger.error(f"Error creating router: {e}")

            # Register module in the modules dict
            if self.explorer is not None:
                self.explorer.modules[self.module_id] = {
                    "name": "Input Collector Control",
                    "description": "API for controlling the input collector application",
                    "method_groups": {},
                    "router": router,
                }

            logger.info(
                f"Module '{self.module_id}' registered using fallback mechanism"
            )
            self.module_registered = True
            return True
        except Exception as e:
            logger.error(f"Error in fallback module registration: {e}")
            return False

    def _register_all_methods(self) -> None:
        """Register all method groups and their methods."""
        if not self.module_registered:
            logger.error("Cannot register methods - module not registered")
            return

        # Register method groups
        self._register_method_groups()

        # Register all methods within groups
        self._register_recording_methods()
        self._register_logging_methods()
        self._register_collector_methods()
        self._register_mouse_methods()
        self._register_key_methods()
        self._register_ui_methods()

    def _register_method_groups(self) -> None:
        """Register method groups for the input collector."""
        if not self.module_registered:
            logger.error("Cannot register method groups - module not registered")
            return

        groups = [
            ("recording", "Recording Control"),
            ("logging", "Logging Configuration"),
            ("collectors", "Collector Management"),
            ("mouse", "Mouse Tracking Configuration"),
            ("keys", "Key Tracking Management"),
            ("ui", "UI Control"),
        ]

        for group_id, group_name in groups:
            self._add_method_group(self.module_id, group_id, group_name)

    def _add_method_group(self, module_id: str, group_id: str, name: str) -> bool:
        """Add a method group with fallback support."""
        # First verify the module exists
        if not self.module_registered:
            logger.error(
                f"Cannot add method group {group_id} - module {module_id} not registered"
            )
            return False

        if hasattr(self.explorer, "add_method_group") and self.explorer is not None:
            try:
                self.explorer.add_method_group(module_id, group_id, name)
                return True
            except Exception as e:
                logger.error(f"Error adding method group: {e}")
                # Fall through to fallback implementation

        # Fallback implementation
        return self._add_method_group_fallback(module_id, group_id, name)

    def _add_method_group_fallback(
        self, module_id: str, group_id: str, name: str
    ) -> bool:
        """Add a method group using fallback mechanism."""
        logger.warning(f"Using fallback method for adding group {group_id}")

        # Check if modules attribute exists
        if hasattr(self.explorer, "modules") and self.explorer is not None:
            # Check if our module exists
            if module_id in self.explorer.modules:
                # Check if method_groups dict exists
                if "method_groups" not in self.explorer.modules[module_id]:
                    self.explorer.modules[module_id]["method_groups"] = {}

                # Add the method group
                self.explorer.modules[module_id]["method_groups"][group_id] = {
                    "name": name,
                    "methods": {},
                }

                logger.info(
                    f"Created method group {group_id} in {module_id} using fallback"
                )
                return True
            else:
                logger.error(f"Module {module_id} not found in ApiExplorer modules")
                return False
        else:
            # Storage in local fallback structure
            if module_id not in self.fallback_method_groups:
                self.fallback_method_groups[module_id] = {}

            self.fallback_method_groups[module_id][group_id] = {
                "name": name,
                "methods": {},
            }

            logger.info(f"Created method group {group_id} in local fallback storage")
            return True

    def _register_method(
        self,
        module_id: str,
        group_id: str,
        method_id: str,
        method_info: Dict,
        handler_function: Callable,
    ) -> None:
        """Register a method with fallback support."""
        if hasattr(self.explorer, "register_method") and self.explorer is not None:
            try:
                self.explorer.register_method(
                    module_id, group_id, method_id, method_info, handler_function
                )
                return
            except Exception as e:
                logger.error(f"Error registering method {method_id}: {e}")
                # Fall through to fallback

        # Use fallback registration
        self._register_method_fallback(
            module_id, group_id, method_id, method_info, handler_function
        )

    def _register_method_fallback(
        self,
        module_id: str,
        group_id: str,
        method_id: str,
        method_info: Dict,
        handler_function: Callable,
    ) -> None:
        """Register a method using fallback mechanism."""
        # Store in fallback structures
        if module_id not in self.fallback_methods:
            self.fallback_methods[module_id] = {}

        if group_id not in self.fallback_methods[module_id]:
            self.fallback_methods[module_id][group_id] = {}

        self.fallback_methods[module_id][group_id][method_id] = {
            "info": method_info,
            "handler": handler_function,
        }

        # Add to group for UI display
        if (
            module_id in self.fallback_method_groups
            and group_id in self.fallback_method_groups[module_id]
        ):
            self.fallback_method_groups[module_id][group_id]["methods"][
                method_id
            ] = method_info

        logger.info(
            f"Registered method {method_id} in {module_id}/{group_id} using fallback"
        )

        # Create fallback endpoint if explorer has routing capability
        if hasattr(self.explorer, "app") and self.explorer is not None:
            self._create_fallback_endpoint(
                module_id, method_id, method_info, handler_function
            )

    def _create_fallback_endpoint(
        self,
        module_id: str,
        method_id: str,
        method_info: Dict,
        handler_function: Callable,
    ) -> None:
        """Create a fallback endpoint directly in the FastAPI app."""
        try:
            # Get the path for this method
            path = f"/api/{module_id}/{method_id}"

            # Determine if GET or POST
            method_type = method_info.get("type", "GET").upper()

            # Create async wrapper
            async def endpoint_wrapper(*args: Any, **kwargs: Any) -> Any:
                result = await handler_function(*args, **kwargs)
                return result

            # Add route directly to app
            if (
                hasattr(self.explorer, "app")
                and self.explorer is not None
                and hasattr(self.explorer, "app")
            ):
                self.explorer.app.add_api_route(
                    path,
                    endpoint_wrapper,
                    methods=[method_type],
                    response_model=None,
                    tags=["Input Collector Control"],
                )

            logger.info(f"Added fallback route for {method_id} at {path}")
        except Exception as e:
            logger.error(f"Failed to add fallback route for {method_id}: {e}")

    def shutdown(self) -> None:
        """Clean up resources when shutting down."""
        # Unsubscribe from core events
        for event_type, handler in self._event_subscriptions:
            unsubscribe(event_type, handler)

        logger.info("API integration shut down")

    #
    # Method registration for different API groups
    #

    def _register_recording_methods(self) -> None:
        """Register recording control methods."""
        # start_recording method
        self._register_method(
            module_id=self.module_id,
            group_id="recording",
            method_id="start_recording",
            method_info={
                "name": "start_recording()",
                "description": "Start recording input events.",
                "type": "POST",
                "params": {},
            },
            handler_function=self._handle_start_recording,
        )

        # stop_recording method
        self._register_method(
            module_id=self.module_id,
            group_id="recording",
            method_id="stop_recording",
            method_info={
                "name": "stop_recording()",
                "description": "Stop recording input events.",
                "type": "POST",
                "params": {},
            },
            handler_function=self._handle_stop_recording,
        )

        # toggle_recording method
        self._register_method(
            module_id=self.module_id,
            group_id="recording",
            method_id="toggle_recording",
            method_info={
                "name": "toggle_recording()",
                "description": "Toggle recording state.",
                "type": "POST",
                "params": {},
            },
            handler_function=self._handle_toggle_recording,
        )

        # is_recording method
        self._register_method(
            module_id=self.module_id,
            group_id="recording",
            method_id="is_recording",
            method_info={
                "name": "is_recording()",
                "description": "Check if recording is active.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_is_recording,
        )

    def _register_logging_methods(self) -> None:
        """Register logging configuration methods."""
        # enable_json_logging method
        self._register_method(
            module_id=self.module_id,
            group_id="logging",
            method_id="enable_json_logging",
            method_info={
                "name": "enable_json_logging(enabled)",
                "description": "Enable or disable JSON logging.",
                "type": "POST",
                "params": {
                    "enabled": {
                        "type": "select",
                        "description": "<span style='color:#f0f0f0;'>Whether to enable JSON logging</span>",
                        "options": [True, False],
                        "required": True,
                        "default": True,
                    }
                },
            },
            handler_function=self._handle_enable_json_logging,
        )

        # enable_csv_logging method
        self._register_method(
            module_id=self.module_id,
            group_id="logging",
            method_id="enable_csv_logging",
            method_info={
                "name": "enable_csv_logging(enabled, filepath)",
                "description": "Enable or disable CSV logging.",
                "type": "POST",
                "params": {
                    "enabled": {
                        "type": "select",
                        "description": "<span style='color:#f0f0f0;'>Whether to enable CSV logging</span>",
                        "options": [True, False],
                        "required": True,
                        "default": True,
                    },
                    "filepath": {
                        "type": "file",
                        "description": "<span style='color:#f0f0f0;'>Path for CSV file</span>",
                        "file_filter": "CSV Files (*.csv)",
                        "default_extension": ".csv",
                        "save_mode": True,
                        "required": False,
                    },
                },
            },
            handler_function=self._handle_enable_csv_logging,
        )

        # set_csv_path method
        self._register_method(
            module_id=self.module_id,
            group_id="logging",
            method_id="set_csv_path",
            method_info={
                "name": "set_csv_path(filepath)",
                "description": "Set the CSV logging file path.",
                "type": "POST",
                "params": {
                    "filepath": {
                        "type": "file",
                        "description": "<span style='color:#f0f0f0;'>Path for CSV file</span>",
                        "file_filter": "CSV Files (*.csv)",
                        "default_extension": ".csv",
                        "save_mode": True,
                        "required": True,
                    }
                },
            },
            handler_function=self._handle_set_csv_path,
        )

        # get_logging_state method
        self._register_method(
            module_id=self.module_id,
            group_id="logging",
            method_id="get_logging_state",
            method_info={
                "name": "get_logging_state()",
                "description": "Get current logging configuration.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_get_logging_state,
        )

    def _register_collector_methods(self) -> None:
        """Register collector management methods."""
        # get_available_collectors method
        self._register_method(
            module_id=self.module_id,
            group_id="collectors",
            method_id="get_available_collectors",
            method_info={
                "name": "get_available_collectors()",
                "description": "Get list of available collectors.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_get_available_collectors,
        )

        # switch_collector method
        self._register_method(
            module_id=self.module_id,
            group_id="collectors",
            method_id="switch_collector",
            method_info={
                "name": "switch_collector(collector_type)",
                "description": "Switch to a different input collector.",
                "type": "POST",
                "params": {
                    "collector_type": {
                        "type": "select",
                        "description": "Type of collector to switch to",
                        "options": ["keyboard_mouse", "ps4_controller"],
                        "required": True,
                    }
                },
            },
            handler_function=self._handle_switch_collector,
        )

        # get_current_collector method
        self._register_method(
            module_id=self.module_id,
            group_id="collectors",
            method_id="get_current_collector",
            method_info={
                "name": "get_current_collector()",
                "description": "Get information about the current collector.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_get_current_collector,
        )

        # scan_controllers method
        self._register_method(
            module_id=self.module_id,
            group_id="collectors",
            method_id="scan_controllers",
            method_info={
                "name": "scan_controllers()",
                "description": "Scan for available controllers.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_scan_controllers,
        )

        # connect_controller method
        self._register_method(
            module_id=self.module_id,
            group_id="collectors",
            method_id="connect_controller",
            method_info={
                "name": "connect_controller(index)",
                "description": "Connect to a specific controller by index.",
                "type": "POST",
                "params": {
                    "index": {
                        "type": "number",
                        "description": "Controller index from scan_controllers()",
                        "required": True,
                    }
                },
            },
            handler_function=self._handle_connect_controller,
        )

    def _register_mouse_methods(self) -> None:
        """Register mouse tracking configuration methods."""
        # set_mouse_tracking_mode method
        self._register_method(
            module_id=self.module_id,
            group_id="mouse",
            method_id="set_mouse_tracking_mode",
            method_info={
                "name": "set_mouse_tracking_mode(mode, direction_only)",
                "description": "Set the mouse tracking mode.",
                "type": "POST",
                "params": {
                    "mode": {
                        "type": "select",
                        "description": "<span style='color:#f0f0f0;'>Tracking mode to use</span>",
                        "options": ["joystick", "delta", "angle", "axis"],
                        "required": True,
                    },
                    "direction_only": {
                        "type": "select",
                        "description": "<span style='color:#f0f0f0;'>Whether to use direction-only mode</span>",
                        "options": [True, False],
                        "required": False,
                    },
                },
            },
            handler_function=self._handle_set_mouse_tracking_mode,
        )

        # Get available tracking modes method
        self._register_method(
            module_id=self.module_id,
            group_id="mouse",
            method_id="get_available_tracking_modes",
            method_info={
                "name": "get_available_tracking_modes(direction_only)",
                "description": "Get available tracking modes based on direction-only setting.",
                "type": "GET",
                "params": {
                    "direction_only": {
                        "type": "select",
                        "description": "<span style='color:#f0f0f0;'>Direction-only mode setting</span>",
                        "options": [True, False],
                        "required": False,
                    }
                },
            },
            handler_function=self._handle_get_available_tracking_modes,
        )

        # set_mouse_settings method
        self._register_method(
            module_id=self.module_id,
            group_id="mouse",
            method_id="set_mouse_settings",
            method_info={
                "name": "set_mouse_settings(delta_smoothing, joystick_sensitivity, angle_grouping)",
                "description": "Set mouse tracking settings.",
                "type": "POST",
                "params": {
                    "delta_smoothing": {
                        "type": "range",
                        "description": "<span style='color:#f0f0f0;'>Smoothing factor for delta tracking (0-90)</span>",
                        "min": 0,
                        "max": 90,
                        "step": 1,
                        "display_value": True,
                        "display_format": "{value}/90",
                        "required": False,
                    },
                    "joystick_sensitivity": {
                        "type": "range",
                        "description": "<span style='color:#f0f0f0;'>Sensitivity for joystick tracking (10-200)</span>",
                        "min": 10,
                        "max": 200,
                        "step": 1,
                        "display_value": True,
                        "display_format": "{value}/200",
                        "required": False,
                    },
                    "angle_grouping": {
                        "type": "range",
                        "description": "<span style='color:#f0f0f0;'>Angle grouping in degrees (1-90)</span>",
                        "min": 1,
                        "max": 90,
                        "step": 1,
                        "display_value": True,
                        "display_format": "{value}° ({Math.floor(360/{value})} values)",
                        "required": False,
                    },
                },
            },
            handler_function=self._handle_set_mouse_settings,
        )

        # get_mouse_settings method
        self._register_method(
            module_id=self.module_id,
            group_id="mouse",
            method_id="get_mouse_settings",
            method_info={
                "name": "get_mouse_settings()",
                "description": "Get current mouse tracking settings.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_get_mouse_settings,
        )

    def _register_key_methods(self) -> None:
        """Register key tracking methods."""
        # get_tracked_keys method
        self._register_method(
            module_id=self.module_id,
            group_id="keys",
            method_id="get_tracked_keys",
            method_info={
                "name": "get_tracked_keys()",
                "description": "Get list of tracked keys.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_get_tracked_keys,
        )

        # toggle_edit_mode method
        self._register_method(
            module_id=self.module_id,
            group_id="keys",
            method_id="toggle_edit_mode",
            method_info={
                "name": "toggle_edit_mode()",
                "description": "Toggle key/button edit mode. Cannot be enabled during recording.",
                "type": "POST",
                "params": {},
            },
            handler_function=self._handle_toggle_edit_mode,
        )

        # is_edit_mode method
        self._register_method(
            module_id=self.module_id,
            group_id="keys",
            method_id="is_edit_mode",
            method_info={
                "name": "is_edit_mode()",
                "description": "Check if edit mode is active.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_is_edit_mode,
        )

        # add_tracked_key method
        self._register_method(
            module_id=self.module_id,
            group_id="keys",
            method_id="add_tracked_key",
            method_info={
                "name": "add_tracked_key(key)",
                "description": "Add a key to tracked keys list. Automatically enables edit mode temporarily.",
                "type": "POST",
                "params": {
                    "key": {
                        "type": "text",
                        "description": "<span style='color:#f0f0f0;'>Key to track (e.g., 'a', 'b', 'Key.space')</span>",
                        "required": True,
                    }
                },
            },
            handler_function=self._handle_add_tracked_key,
        )

        # remove_tracked_key method
        self._register_method(
            module_id=self.module_id,
            group_id="keys",
            method_id="remove_tracked_key",
            method_info={
                "name": "remove_tracked_key(key)",
                "description": "Remove a key from tracked keys list. Automatically enables edit mode temporarily.",
                "type": "POST",
                "params": {
                    "key": {
                        "type": "text",
                        "description": "<span style='color:#f0f0f0;'>Key to untrack (e.g., 'a', 'b', 'Key.space')</span>",
                        "required": True,
                    }
                },
            },
            handler_function=self._handle_remove_tracked_key,
        )

        # toggle_button_tracking method
        self._register_method(
            module_id=self.module_id,
            group_id="keys",
            method_id="toggle_button_tracking",
            method_info={
                "name": "toggle_button_tracking(button_id, track)",
                "description": "Toggle tracking for a mouse button. Automatically enables edit mode temporarily.",
                "type": "POST",
                "params": {
                    "button_id": {
                        "type": "select",
                        "description": "<span style='color:#f0f0f0;'>Button identifier</span>",
                        "options": ["Button.left", "Button.right", "Button.scroll"],
                        "required": True,
                    },
                    "track": {
                        "type": "select",
                        "description": "<span style='color:#f0f0f0;'>Whether to track the button</span>",
                        "options": [True, False],
                        "required": True,
                    },
                },
            },
            handler_function=self._handle_toggle_button_tracking,
        )

    def _register_ui_methods(self) -> None:
        """Register UI control methods."""
        # toggle_fullscreen method
        self._register_method(
            module_id=self.module_id,
            group_id="ui",
            method_id="toggle_fullscreen",
            method_info={
                "name": "toggle_fullscreen()",
                "description": "Toggle fullscreen mode.",
                "type": "POST",
                "params": {},
            },
            handler_function=self._handle_toggle_fullscreen,
        )

        # get_application_state method
        self._register_method(
            module_id=self.module_id,
            group_id="ui",
            method_id="get_application_state",
            method_info={
                "name": "get_application_state()",
                "description": "Get comprehensive application state.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_get_application_state,
        )

    #
    # API endpoint handlers
    #

    async def _handle_start_recording(self) -> Dict[str, Any]:
        """Handle start_recording API request."""
        try:
            success = InputCollectorAPI.start_recording()
            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
            }
        except Exception as e:
            logger.error(f"Error in start_recording endpoint: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_stop_recording(self) -> Dict[str, Any]:
        """Handle stop_recording API request."""
        try:
            success = InputCollectorAPI.stop_recording()
            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
            }
        except Exception as e:
            logger.error(f"Error in stop_recording endpoint: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_toggle_recording(self) -> Dict[str, Any]:
        """Handle toggle_recording API request."""
        try:
            success = InputCollectorAPI.toggle_recording()
            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
            }
        except Exception as e:
            logger.error(f"Error in toggle_recording endpoint: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_is_recording(self) -> Dict[str, Any]:
        """Handle is_recording API request."""
        try:
            recording = InputCollectorAPI.is_recording()
            return {"recording": recording}
        except Exception as e:
            logger.error(f"Error in is_recording endpoint: {e}")
            return {"recording": False, "error": str(e)}

    async def _handle_enable_json_logging(self, enabled: bool = True) -> Dict[str, Any]:
        """Handle enable_json_logging API request."""
        try:
            success = InputCollectorAPI.enable_json_logging(enabled)
            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
            }
        except Exception as e:
            logger.error(f"Error in enable_json_logging endpoint: {e}")
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_enable_csv_logging(
        self, enabled: bool = True, filepath: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle enable_csv_logging API request."""
        try:
            success = InputCollectorAPI.enable_csv_logging(enabled, filepath)
            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
            }
        except Exception as e:
            logger.error(f"Error in enable_csv_logging endpoint: {e}")
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_set_csv_path(self, filepath: str) -> Dict[str, Any]:
        """Handle set_csv_path API request."""
        try:
            success = InputCollectorAPI.set_csv_path(filepath)
            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
            }
        except Exception as e:
            logger.error(f"Error in set_csv_path endpoint: {e}")
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_get_logging_state(self) -> Dict[str, Any]:
        """Handle get_logging_state API request."""
        try:
            return InputCollectorAPI.get_logging_state()
        except Exception as e:
            logger.error(f"Error in get_logging_state endpoint: {e}")
            return {"error": str(e)}

    async def _handle_get_available_collectors(self) -> Dict[str, Any]:
        """Handle get_available_collectors API request."""
        try:
            collectors = InputCollectorAPI.get_available_collectors()
            return {"collectors": collectors}
        except Exception as e:
            logger.error(f"Error in get_available_collectors endpoint: {e}")
            return {"collectors": [], "error": str(e)}

    async def _handle_switch_collector(self, collector_type: str) -> Dict[str, Any]:
        """Handle switch_collector API request."""
        try:
            success = InputCollectorAPI.switch_collector(collector_type)
            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
            }
        except Exception as e:
            logger.error(f"Error in switch_collector endpoint: {e}")
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_get_current_collector(self) -> Dict[str, Any]:
        """Handle get_current_collector API request."""
        try:
            return InputCollectorAPI.get_current_collector()
        except Exception as e:
            logger.error(f"Error in get_current_collector endpoint: {e}")
            return {"error": str(e)}

    async def _handle_scan_controllers(self) -> Dict[str, Any]:
        """Handle scan_controllers API request."""
        try:
            controllers = InputCollectorAPI.scan_controllers()
            return {"controllers": controllers}
        except Exception as e:
            logger.error(f"Error in scan_controllers endpoint: {e}")
            return {"controllers": [], "error": str(e)}

    async def _handle_connect_controller(self, index: int) -> Dict[str, Any]:
        """Handle connect_controller API request."""
        try:
            success = InputCollectorAPI.connect_controller(index)
            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
            }
        except Exception as e:
            logger.error(f"Error in connect_controller endpoint: {e}")
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_set_mouse_tracking_mode(
        self, mode: str, direction_only: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Handle set_mouse_tracking_mode API request."""
        try:
            # Get available modes first based on requested direction_only
            available_modes = InputCollectorAPI.get_available_tracking_modes(
                direction_only if direction_only is not None else False
            )

            # Validate mode against available modes
            if mode not in available_modes:
                return {
                    "success": False,
                    "status": {
                        "success": False,
                        "message": f"Invalid tracking mode '{mode}' for direction_only={direction_only}. Valid modes: {available_modes}",
                    },
                    "available_modes": available_modes,
                }

            success = InputCollectorAPI.set_mouse_tracking_mode(mode, direction_only)

            # Get updated available modes after the operation
            updated_modes = InputCollectorAPI.get_available_tracking_modes(False)
            current_settings = InputCollectorAPI.get_mouse_settings()

            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
                "available_modes": updated_modes,
                "current_settings": current_settings,
            }
        except Exception as e:
            logger.error(f"Error in set_mouse_tracking_mode endpoint: {e}")
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_set_mouse_settings(
        self,
        delta_smoothing: Optional[float] = None,
        joystick_sensitivity: Optional[float] = None,
        angle_grouping: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Handle set_mouse_settings API request."""
        try:
            # Input validation is now handled in the InputCollectorAPI class
            success = InputCollectorAPI.set_mouse_settings(
                delta_smoothing, joystick_sensitivity, angle_grouping
            )

            # Get current settings to return updated values
            current_settings = InputCollectorAPI.get_mouse_settings()

            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
                "current_settings": current_settings,
            }
        except Exception as e:
            logger.error(f"Error in set_mouse_settings endpoint: {e}")
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_get_mouse_settings(self) -> Dict[str, Any]:
        """Handle get_mouse_settings API request."""
        try:
            return InputCollectorAPI.get_mouse_settings()
        except Exception as e:
            logger.error(f"Error in get_mouse_settings endpoint: {e}")
            return {"error": str(e)}

    async def _handle_get_available_tracking_modes(
        self, direction_only: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Handle get_available_tracking_modes API request."""
        try:
            modes = InputCollectorAPI.get_available_tracking_modes(
                direction_only if direction_only is not None else False
            )
            return {"modes": modes, "direction_only": direction_only}
        except Exception as e:
            logger.error(f"Error in get_available_tracking_modes endpoint: {e}")
            return {"error": str(e)}

    async def _handle_get_tracked_keys(self) -> Dict[str, Any]:
        """Handle get_tracked_keys API request."""
        try:
            keys = InputCollectorAPI.get_tracked_keys()
            return {"keys": keys}
        except Exception as e:
            logger.error(f"Error in get_tracked_keys endpoint: {e}")
            return {"keys": [], "error": str(e)}

    async def _handle_toggle_edit_mode(self) -> Dict[str, Any]:
        """Handle toggle_edit_mode API request."""
        try:
            success = InputCollectorAPI.toggle_edit_mode()
            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
            }
        except Exception as e:
            logger.error(f"Error in toggle_edit_mode endpoint: {e}")
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_is_edit_mode(self) -> Dict[str, Any]:
        """Handle is_edit_mode API request."""
        try:
            edit_mode = InputCollectorAPI.is_edit_mode()
            return {"edit_mode": edit_mode}
        except Exception as e:
            logger.error(f"Error in is_edit_mode endpoint: {e}")
            return {"edit_mode": False, "error": str(e)}

    async def _handle_add_tracked_key(self, key: str) -> Dict[str, Any]:
        """Handle add_tracked_key API request."""
        try:
            success = InputCollectorAPI.add_tracked_key(key)
            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
            }
        except Exception as e:
            logger.error(f"Error in add_tracked_key endpoint: {e}")
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_remove_tracked_key(self, key: str) -> Dict[str, Any]:
        """Handle remove_tracked_key API request."""
        try:
            success = InputCollectorAPI.remove_tracked_key(key)
            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
            }
        except Exception as e:
            logger.error(f"Error in remove_tracked_key endpoint: {e}")
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_toggle_button_tracking(
        self, button_id: str, track: bool
    ) -> Dict[str, Any]:
        """Handle toggle_button_tracking API request."""
        try:
            success = InputCollectorAPI.toggle_button_tracking(button_id, track)
            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
            }
        except Exception as e:
            logger.error(f"Error in toggle_button_tracking endpoint: {e}")
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_toggle_fullscreen(self) -> Dict[str, Any]:
        """Handle toggle_fullscreen API request."""
        try:
            success = InputCollectorAPI.toggle_fullscreen()
            return {
                "success": success,
                "status": InputCollectorAPI.get_last_operation_status(),
            }
        except Exception as e:
            logger.error(f"Error in toggle_fullscreen endpoint: {e}")
            return {"success": False, "status": {"message": f"Error: {str(e)}"}}

    async def _handle_get_application_state(self) -> Dict[str, Any]:
        """Handle get_application_state API request."""
        try:
            return InputCollectorAPI.get_application_state()
        except Exception as e:
            logger.error(f"Error in get_application_state endpoint: {e}")
            return {"error": str(e)}


# Module-level functions for easier access

# Create a singleton instance
_interaction_api_integration = None


def get_interaction_api_integration() -> InteractionApiIntegration:
    """Get or create the interaction API integration instance."""
    global _interaction_api_integration
    if _interaction_api_integration is None:
        _interaction_api_integration = InteractionApiIntegration()
    return _interaction_api_integration


def initialize_interaction_api(
    enable_web_api: bool = True, host: str = "127.0.0.1", port: int = 8001
) -> bool:
    """
    Initialize the interaction web API for the input collector.

    Args:
        enable_web_api: Whether to enable the web API
        host: Host to bind the server to
        port: Port to bind the server to (defaults to 8001 to avoid conflict with data access API)

    Returns:
        True if initialization was successful, False otherwise
    """
    if not enable_web_api:
        return False

    if not explorer_available:
        logger.warning("API Explorer not available. Web API will not be enabled.")
        return False

    integration = get_interaction_api_integration()
    success = integration.register_api(start_server=True, host=host, port=port)

    if success:
        logger.info(f"Interaction API initialized at http://{host}:{port}")

    return success
