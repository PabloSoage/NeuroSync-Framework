"""
API integration for the input collector.

This module integrates the input collector with the API Explorer,
registering its methods and handling API requests.
"""

import asyncio
import logging
import math
import socket
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

# Import the InputDataAPI
from .data_access_api import InputDataAPI

# Import core event system
from .core.event_system import EventType, subscribe, unsubscribe


class InputCollectorApiIntegration:
    """
    Integrates the input collector with the API Explorer.

    This class exposes the input collector's API methods through the API Explorer.
    """

    def __init__(self) -> None:
        """Initialize the API integration."""
        self.explorer: Optional[Any] = None
        self.module_id = "input_collector"
        self.is_registered = False
        self.event_callback_id: Optional[int] = None

        # For storing method groups and methods when fallback is used
        self.fallback_method_groups: Dict[str, Dict[str, Any]] = {}
        self.fallback_methods: Dict[str, Dict[str, Any]] = {}

        # Module registration status flag
        self.module_registered = False

        # For tracking event subscriptions
        self._event_subscriptions: List[tuple[EventType, Callable]] = []
        self._pressed_buttons: Set[str] = set()

        # PS4 controller state tracking
        self._ps4_button_states: Dict[str, bool] = (
            {}
        )  # Maps button name to pressed state (True/False)
        self._ps4_active_buttons: Set[str] = set()  # Set of currently pressed buttons
        self._ps4_stick_states: Dict[str, Dict[str, Union[float, str]]] = (
            {  # Maps stick name to position data
                "left": {"x": 0.0, "y": 0.0, "direction": "center"},
                "right": {"x": 0.0, "y": 0.0, "direction": "center"},
            }
        )
        self._ps4_trigger_states: Dict[str, float] = {
            "left": 0.0,
            "right": 0.0,
        }  # Maps trigger name to value (0.0 - 1.0)

    def register_api(
        self, start_server: bool = True, host: str = "127.0.0.1", port: int = 8000
    ) -> bool:
        """
        Register the input collector's API with the Explorer.

        Args:
            start_server: Whether to start the API Explorer server
            host: Host to bind the server to
            port: Port to bind the server to

        Returns:
            True if registration was successful, False otherwise
        """
        if not explorer_available:
            return False

        try:
            # Find available port
            port = self._find_available_port(host, port)

            # Get the ApiExplorer instance
            self.explorer = ApiExplorer.get_instance()

            # Register module
            if not self._register_module():
                return False

            # Register methods
            self._register_all_methods()

            # Setup websocket events
            self._setup_websocket_events()

            # Start the server if requested
            if (
                start_server
                and hasattr(self.explorer, "start_server")
                and not self.explorer.is_running
            ):
                self.explorer.start_server(host=host, port=port, block=False)

            self.is_registered = True
            return True
        except Exception as e:
            logger.error(f"Error registering input collector API: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _find_available_port(self, host: str, port: int) -> int:
        """Find an available port, starting with the provided one."""
        if self._is_port_in_use(host, port):
            logger.info(
                f"Port {port} is already in use, looking for an alternative port..."
            )
            # Try to find a different port
            for alt_port in range(port + 1, port + 10):
                if not self._is_port_in_use(host, alt_port):
                    logger.info(f"Using alternative port {alt_port}")
                    return alt_port
            logger.warning(f"No available ports found, returning original port {port}")
        return port

    def _is_port_in_use(self, host: str, port: int) -> bool:
        """Check if a port is already in use."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

    def _register_module(self) -> bool:
        """Register the input collector module."""
        try:
            if self.explorer is not None and hasattr(self.explorer, "register_module"):
                self.explorer.register_module(
                    module_id=self.module_id,
                    name="Input Collector",
                    description="API for accessing real-time input data with minimal overhead",
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
            if self.explorer is not None and not hasattr(self.explorer, "modules"):
                setattr(self.explorer, "modules", {})

            # Create a router for this module
            router = None
            try:
                from fastapi import APIRouter

                router = APIRouter(
                    prefix=f"/api/{self.module_id}", tags=["Input Collector"]
                )

                # If explorer has an app attribute, add the router directly
                if self.explorer is not None and hasattr(self.explorer, "app"):
                    self.explorer.app.include_router(router)
            except Exception as e:
                logger.error(f"Error creating router: {e}")

            # Register module in the modules dict
            if self.explorer is not None and hasattr(self.explorer, "modules"):
                self.explorer.modules[self.module_id] = {
                    "name": "Input Collector",
                    "description": "API for accessing real-time input data with minimal overhead",
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
        self._register_state_methods()
        self._register_event_methods()
        self._register_controller_methods()
        self._register_callback_methods()

    def _register_method_groups(self) -> None:
        """Register method groups for the input collector."""
        if not self.module_registered:
            logger.error("Cannot register method groups - module not registered")
            return

        groups = [
            ("state_methods", "State Methods"),
            ("event_methods", "Event Methods"),
            ("controller_methods", "Controller Methods"),
            ("callback_methods", "Callback Methods"),
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

        if self.explorer is not None and hasattr(self.explorer, "add_method_group"):
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
        if self.explorer is not None and hasattr(self.explorer, "modules"):
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
        if self.explorer is not None and hasattr(self.explorer, "register_method"):
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
        if self.explorer is not None and hasattr(self.explorer, "app"):
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
            if self.explorer is not None and hasattr(self.explorer, "app"):
                self.explorer.app.add_api_route(
                    path,
                    endpoint_wrapper,
                    methods=[method_type],
                    response_model=None,
                    tags=["Input Collector"],
                )

            logger.info(f"Added fallback route for {method_id} at {path}")
        except Exception as e:
            logger.error(f"Failed to add fallback route for {method_id}: {e}")

    def _setup_websocket_events(self) -> None:
        """Set up event handlers for websocket real-time events."""
        # Subscribe to core events for websocket forwarding
        self._subscribe_to_core_events()

        # Legacy: still register event callback for backward compatibility
        self._register_for_events()

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
            Dict: Formatted event for websocket broadcast
        """
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
            # 1) Update button state before filtering release events
            if (
                event_type == EventType.INPUT
                and getattr(data, "event_type", "") == "mouse_click"
            ):
                if getattr(data, "button_pressed", None):
                    self._pressed_buttons.add(data.button_pressed)
                else:
                    # on release, try to use 'button' field if collector provides it
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

            # 3) Skip key_release and scroll events as before
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

            # 4) Unify InputData in payload structure
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
                        # Use button_event format para eventos de botones
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

                # 5) Add unique ID and filter empty fields for all events
                payload["event_id"] = (
                    f"{str(time.time()).replace('.', '')}_{id(payload)}"
                )
                self._filter_empty_fields(payload)

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
                direction = self._get_stick_direction(x_value, y_value)
                self._ps4_stick_states["left"] = {
                    "x": x_value,
                    "y": y_value,
                    "direction": direction,
                }

            elif "Right_Stick" in key:
                x_value = getattr(data, "rel_x", 0)
                y_value = getattr(data, "rel_y", 0)
                direction = self._get_stick_direction(x_value, y_value)
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

    def _get_stick_direction(self, x_value: float, y_value: float) -> str:
        """
        Get the direction of a stick based on its X and Y coordinates.

        Args:
            x_value: X-axis value (-1.0 to 1.0)
            y_value: Y-axis value (-1.0 to 1.0)

        Returns:
            str: Direction name
        """
        # Use a small deadzone to determine when stick is centered
        deadzone = 0.2
        if abs(x_value) < deadzone and abs(y_value) < deadzone:
            return "center"

        # Calculate the angle in degrees
        angle = math.degrees(math.atan2(-y_value, x_value))

        # Convert to positive angle (0-360)
        if angle < 0:
            angle += 360

        # Map the angle to a direction
        if 22.5 <= angle < 67.5:
            return "up-right"
        elif 67.5 <= angle < 112.5:
            return "up"
        elif 112.5 <= angle < 157.5:
            return "up-left"
        elif 157.5 <= angle < 202.5:
            return "left"
        elif 202.5 <= angle < 247.5:
            return "down-left"
        elif 247.5 <= angle < 292.5:
            return "down"
        elif 292.5 <= angle < 337.5:
            return "down-right"
        else:  # 337.5 <= angle < 22.5
            return "right"

    def _get_ps4_controller_state(self) -> Dict[str, Any]:
        """
        Get the complete current state of the PS4 controller.

        Returns:
            Dict: The current state of all PS4 controls
        """
        # Process sticks to include percentages and consistent directions
        left_stick_x = self._ps4_stick_states["left"]["x"]
        left_stick_y = self._ps4_stick_states["left"]["y"]
        right_stick_x = self._ps4_stick_states["right"]["x"]
        right_stick_y = self._ps4_stick_states["right"]["y"]
        left_trigger_val = self._ps4_trigger_states["left"]
        right_trigger_val = self._ps4_trigger_states["right"]

        # Calculate directions
        left_direction = self._get_stick_direction(
            float(left_stick_x), float(left_stick_y)
        )
        right_direction = self._get_stick_direction(
            float(right_stick_x), float(right_stick_y)
        )

        return {
            "active_buttons": list(self._ps4_active_buttons),
            "sticks": {
                "left": {
                    "x": left_stick_x,
                    "y": left_stick_y,
                    "direction": left_direction,
                    "percentage_x": f"{int(abs(float(left_stick_x)) * 100)}%",
                    "percentage_y": f"{int(abs(float(left_stick_y)) * 100)}%",
                },
                "right": {
                    "x": right_stick_x,
                    "y": right_stick_y,
                    "direction": right_direction,
                    "percentage_x": f"{int(abs(float(right_stick_x)) * 100)}%",
                    "percentage_y": f"{int(abs(float(right_stick_y)) * 100)}%",
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
            if key and "Left_Stick" in key:
                control_type = "stick"
                control_name = "left_stick"
            elif key and "Right_Stick" in key:
                control_type = "stick"
                control_name = "right_stick"
            elif key and "Left_Trigger" in key:
                control_type = "trigger"
                control_name = "left_trigger"
            elif key and "Right_Trigger" in key:
                control_type = "trigger"
                control_name = "right_trigger"

        # For stick movement
        if control_type == "stick" and control_name:
            # Get X and Y values
            x_value = getattr(data, "rel_x", 0)
            y_value = getattr(data, "rel_y", 0)
            direction = self._get_stick_direction(x_value, y_value)

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
            stick_name_parts = control_name.split("_")
            if len(stick_name_parts) > 0:
                stick_name = stick_name_parts[0]  # Extract "left" or "right" part
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
            trigger_name_parts = control_name.split("_")
            if len(trigger_name_parts) > 0:
                trigger_name = trigger_name_parts[0]  # Extract "left" or "right" part
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

    #
    # Method registration for different API groups
    #

    def _register_state_methods(self) -> None:
        """Register state-related API methods."""
        # get_active_keys method
        self._register_method(
            module_id=self.module_id,
            group_id="state_methods",
            method_id="get_active_keys",
            method_info={
                "name": "get_active_keys()",
                "description": "Get a list of currently active keys.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_get_active_keys,
        )

        # is_key_active method
        self._register_method(
            module_id=self.module_id,
            group_id="state_methods",
            method_id="is_key_active",
            method_info={
                "name": "is_key_active(key)",
                "description": "Check if a specific key is currently active.",
                "type": "GET",
                "params": {
                    "key": {
                        "type": "text",
                        "description": "Key to check",
                        "placeholder": "e.g., w, a, s, d, Key.space",
                        "required": True,
                    }
                },
            },
            handler_function=self._handle_is_key_active,
        )

        # Other state methods
        self._register_method(
            module_id=self.module_id,
            group_id="state_methods",
            method_id="get_mouse_position",
            method_info={
                "name": "get_mouse_position()",
                "description": "Get the current mouse position as [x, y] coordinates.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_get_mouse_position,
        )

        # ... other state methods (mouse button state, mouse moving, direction, metadata)
        self._register_method(
            module_id=self.module_id,
            group_id="state_methods",
            method_id="get_mouse_button_state",
            method_info={
                "name": "get_mouse_button_state(button)",
                "description": "Get the state of a specific mouse button.",
                "type": "GET",
                "params": {
                    "button": {
                        "type": "select",
                        "description": "Mouse button to check",
                        "options": ["left", "right", "middle"],
                        "required": True,
                    }
                },
            },
            handler_function=self._handle_get_mouse_button_state,
        )

        self._register_method(
            module_id=self.module_id,
            group_id="state_methods",
            method_id="is_mouse_moving",
            method_info={
                "name": "is_mouse_moving()",
                "description": "Check if the mouse is currently moving.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_is_mouse_moving,
        )

        self._register_method(
            module_id=self.module_id,
            group_id="state_methods",
            method_id="get_mouse_direction",
            method_info={
                "name": "get_mouse_direction()",
                "description": "Get the current mouse movement direction.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_get_mouse_direction,
        )

        self._register_method(
            module_id=self.module_id,
            group_id="state_methods",
            method_id="get_metadata",
            method_info={
                "name": "get_metadata()",
                "description": "Get metadata about the input collection process.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_get_metadata,
        )

    def _register_event_methods(self) -> None:
        """Register event-related API methods."""
        # get_current_event method
        self._register_method(
            module_id=self.module_id,
            group_id="event_methods",
            method_id="get_current_event",
            method_info={
                "name": "get_current_event()",
                "description": "Get the most recent input event.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_get_current_event,
        )

        # get_key_events method
        self._register_method(
            module_id=self.module_id,
            group_id="event_methods",
            method_id="get_key_events",
            method_info={
                "name": "get_key_events(max_count)",
                "description": "Get recent keyboard events.",
                "type": "GET",
                "params": {
                    "max_count": {
                        "type": "number",
                        "description": "Maximum number of events to return",
                        "placeholder": "e.g., 10",
                        "required": False,
                    }
                },
            },
            handler_function=self._handle_get_key_events,
        )

        # ... other event methods (mouse movement, mouse buttons, controller)
        self._register_method(
            module_id=self.module_id,
            group_id="event_methods",
            method_id="get_mouse_movement_events",
            method_info={
                "name": "get_mouse_movement_events(max_count)",
                "description": "Get recent mouse movement events.",
                "type": "GET",
                "params": {
                    "max_count": {
                        "type": "number",
                        "description": "Maximum number of events to return",
                        "placeholder": "e.g., 10",
                        "required": False,
                    }
                },
            },
            handler_function=self._handle_get_mouse_movement_events,
        )

        self._register_method(
            module_id=self.module_id,
            group_id="event_methods",
            method_id="get_mouse_button_events",
            method_info={
                "name": "get_mouse_button_events(max_count)",
                "description": "Get recent mouse button events.",
                "type": "GET",
                "params": {
                    "max_count": {
                        "type": "number",
                        "description": "Maximum number of events to return",
                        "placeholder": "e.g., 10",
                        "required": False,
                    }
                },
            },
            handler_function=self._handle_get_mouse_button_events,
        )

        self._register_method(
            module_id=self.module_id,
            group_id="event_methods",
            method_id="get_controller_events",
            method_info={
                "name": "get_controller_events(max_count)",
                "description": "Get recent controller events.",
                "type": "GET",
                "params": {
                    "max_count": {
                        "type": "number",
                        "description": "Maximum number of events to return",
                        "placeholder": "e.g., 10",
                        "required": False,
                    }
                },
            },
            handler_function=self._handle_get_controller_events,
        )

    def _register_controller_methods(self) -> None:
        """Register controller-related API methods."""
        # is_controller_connected method
        self._register_method(
            module_id=self.module_id,
            group_id="controller_methods",
            method_id="is_controller_connected",
            method_info={
                "name": "is_controller_connected()",
                "description": "Check if a controller is connected.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_is_controller_connected,
        )

        # get_controller_name method
        self._register_method(
            module_id=self.module_id,
            group_id="controller_methods",
            method_id="get_controller_name",
            method_info={
                "name": "get_controller_name()",
                "description": "Get the name of the connected controller.",
                "type": "GET",
                "params": {},
            },
            handler_function=self._handle_get_controller_name,
        )

    def _register_callback_methods(self) -> None:
        """Register callback-related API methods."""
        # register_event_callback method
        self._register_method(
            module_id=self.module_id,
            group_id="callback_methods",
            method_id="register_event_callback",
            method_info={
                "name": "register_event_callback()",
                "description": "Register a callback for input events. In the API Explorer, this will register a WebSocket connection.",
                "type": "POST",
                "params": {},
            },
            handler_function=self._handle_register_event_callback,
        )

        # unregister_event_callback method
        self._register_method(
            module_id=self.module_id,
            group_id="callback_methods",
            method_id="unregister_event_callback",
            method_info={
                "name": "unregister_event_callback(callback_id)",
                "description": "Unregister a previously registered callback.",
                "type": "POST",
                "params": {
                    "callback_id": {
                        "type": "number",
                        "description": "ID of the callback to unregister",
                        "placeholder": "e.g., 1",
                        "required": True,
                    }
                },
            },
            handler_function=self._handle_unregister_event_callback,
        )

    #
    # API endpoint handlers
    #

    async def _handle_get_active_keys(self) -> List[str]:
        """Handle get_active_keys API endpoint."""
        return InputDataAPI.get_active_keys()

    async def _handle_is_key_active(self, key: str) -> Dict[str, bool]:
        """Handle is_key_active API endpoint."""
        return {"active": InputDataAPI.is_key_active(key)}

    async def _handle_get_mouse_position(self) -> Dict[str, Union[int, float]]:
        """Handle get_mouse_position API endpoint."""
        x, y = InputDataAPI.get_mouse_position()
        return {"x": float(x), "y": float(y)}

    async def _handle_get_mouse_button_state(self, button: str) -> Dict[str, bool]:
        """Handle get_mouse_button_state API endpoint."""
        return {"pressed": InputDataAPI.get_mouse_button_state(button)}

    async def _handle_is_mouse_moving(self) -> Dict[str, bool]:
        """Handle is_mouse_moving API endpoint."""
        return {"moving": InputDataAPI.is_mouse_moving()}

    async def _handle_get_mouse_direction(self) -> Dict[str, Optional[str]]:
        """Handle get_mouse_direction API endpoint."""
        return {"direction": InputDataAPI.get_mouse_direction()}

    async def _handle_get_metadata(self) -> Dict[str, Any]:
        """Handle get_metadata API endpoint."""
        return InputDataAPI.get_metadata()

    async def _handle_get_current_event(self) -> Optional[Dict[str, Any]]:
        """Handle get_current_event API endpoint."""
        event = InputDataAPI.get_current_event()
        if event is None:
            return None
        # Convert event object to dictionary
        return self._event_to_dict(event)

    async def _handle_get_key_events(
        self, max_count: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Handle get_key_events API endpoint."""
        events = InputDataAPI.get_key_events(max_count or 10)
        return [self._event_to_dict(event) for event in events]

    async def _handle_get_mouse_movement_events(
        self, max_count: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Handle get_mouse_movement_events API endpoint."""
        events = InputDataAPI.get_mouse_movement_events(max_count or 10)
        return [self._event_to_dict(event) for event in events]

    async def _handle_get_mouse_button_events(
        self, max_count: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Handle get_mouse_button_events API endpoint."""
        events = InputDataAPI.get_mouse_button_events(max_count or 10)
        return [self._event_to_dict(event) for event in events]

    async def _handle_get_controller_events(
        self, max_count: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Handle get_controller_events API endpoint."""
        events = InputDataAPI.get_controller_events(max_count or 10)
        return [self._event_to_dict(event) for event in events]

    async def _handle_is_controller_connected(self) -> Dict[str, bool]:
        """Handle is_controller_connected API endpoint."""
        return {"connected": InputDataAPI.is_controller_connected()}

    async def _handle_get_controller_name(self) -> Dict[str, Optional[str]]:
        """Handle get_controller_name API endpoint."""
        return {"name": InputDataAPI.get_controller_name()}

    async def _handle_register_event_callback(self) -> Dict[str, Union[int, str]]:
        """Handle register_event_callback API endpoint."""
        # This is just a placeholder - actual WebSocket connections are handled separately
        return {"callback_id": 1, "status": "registered"}

    async def _handle_unregister_event_callback(
        self, callback_id: int
    ) -> Dict[str, Union[bool, str]]:
        """Handle unregister_event_callback API endpoint."""
        # This is just a placeholder - actual WebSocket connections are handled separately
        return {"success": True, "message": "Callback unregistered"}

    def _broadcast_event(self, event_dict: Dict) -> None:
        """Broadcast an event through the WebSocket connection."""
        if self.explorer is None or not hasattr(self.explorer, "broadcast_event"):
            logger.warning(
                "ApiExplorer does not have broadcast_event method, event not sent"
            )
            return

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

    def _create_simple_event(self, event_data: Any) -> Optional[Dict]:
        """
        Create a simplified event for websocket broadcast.

        Args:
            event_data: Event data

        Returns:
            Dict: Simplified event
        """
        try:
            # Create basic event structure
            simple_event = {
                "type": getattr(event_data, "event_type", "unknown"),
                "timestamp": getattr(event_data, "timestamp", time.time()),
            }

            # Add key info if present
            if hasattr(event_data, "key") and event_data.key:
                simple_event["key"] = event_data.key

            # Add button info if present
            if hasattr(event_data, "button_pressed") and event_data.button_pressed:
                simple_event["button"] = event_data.button_pressed

            # Add direction if present
            if hasattr(event_data, "direction") and event_data.direction:
                simple_event["direction"] = event_data.direction

            # Add active keys if any
            active_keys = getattr(event_data, "active_keys", [])
            if active_keys:
                simple_event["active_keys"] = active_keys

            return simple_event
        except Exception as e:
            logger.error(f"Error creating simple event: {e}")
            return None

    def shutdown(self) -> None:
        """Clean up resources when shutting down."""
        # Unsubscribe from core events
        for event_type, handler in self._event_subscriptions:
            unsubscribe(event_type, handler)

        # Unregister legacy callback
        if self.event_callback_id is not None:
            InputDataAPI.unregister_event_callback(self.event_callback_id)
            self.event_callback_id = None

        logger.info("API integration shut down")

    def _register_for_events(self) -> None:
        """Register for real-time events from the input collector (legacy method)."""
        callback_id = InputDataAPI.register_event_callback(self._event_callback)
        if callback_id is not None:
            self.event_callback_id = callback_id
            logger.info(f"Registered for input events with callback ID {callback_id}")

    def _event_callback(self, event: Any) -> None:
        """
        Handle input events and broadcast them through WebSocket (legacy method).

        This is kept for backward compatibility but most events are now handled
        through the core event system subscription.
        """
        # We don't need to process most events here anymore as they're handled by the core event system
        pass

    def _event_to_dict(self, event: Any) -> Dict:
        """Convert an event object to a serializable dictionary."""
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


# Module-level functions for easier access

# Create a singleton instance
_api_integration = None


def get_api_integration() -> InputCollectorApiIntegration:
    """Get or create the API integration instance."""
    global _api_integration
    if _api_integration is None:
        _api_integration = InputCollectorApiIntegration()
    return _api_integration


def initialize_api(
    enable_web_api: bool = True, host: str = "127.0.0.1", port: int = 8000
) -> bool:
    """
    Initialize the web API for the input collector.

    Args:
        enable_web_api: Whether to enable the web API
        host: Host to bind the server to
        port: Port to bind the server to

    Returns:
        True if initialization was successful, False otherwise
    """
    if not enable_web_api:
        return False

    if not explorer_available:
        logger.warning("API Explorer not available. Web API will not be enabled.")
        return False

    integration = get_api_integration()
    success = integration.register_api(start_server=True, host=host, port=port)

    return success
