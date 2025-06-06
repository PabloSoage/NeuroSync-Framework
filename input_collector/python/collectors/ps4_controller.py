"""
PS4 controller input collection module.

This module provides functionality for capturing and processing PS4 controller
inputs using SDL2, with support for buttons, analog sticks and triggers.
"""

import threading
import time
from typing import List, Dict, Any, Callable, Set, Optional

import sdl2
import sdl2.ext
from PyQt5.QtCore import QTimer

from ..interfaces import InputData, AbstractInputCollector


def is_sdl2_available() -> bool:
    """Check if SDL2 is properly installed and initialized."""
    try:
        # Try to initialize SDL2 with video subsystem which is less problematic
        # than joystick subsystems for initial testing
        if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
            return False
        sdl2.SDL_Quit()
        return True
    except:
        return False


class PS4ControllerCollector(AbstractInputCollector):
    """
    Collects input events from a PS4 controller using SDL2.

    This class captures controller events from the system, processes them,
    and provides a unified interface for accessing controller state.
    """

    def __init__(self) -> None:
        """
        Initialize the PS4 controller collector.

        Sets up internal state tracking and prepares SDL2 for controller input.
        """
        # Events storage
        self.controller_events: List[InputData] = []

        # Internal state
        self.is_capturing: bool = False
        self.event_callbacks: List[Callable[[InputData], None]] = []
        self.controller = None
        self.joystick = None
        self.controller_name = "PS4 Controller"  # Default name
        self.controller_index = -1  # Default to no controller

        # Button states
        self.button_states: Dict[str, bool] = {}

        # Stick positions
        self.stick_positions: Dict[str, tuple] = {"left": (0, 0), "right": (0, 0)}

        # Trigger values
        self.trigger_values: Dict[str, float] = {"left": 0, "right": 0}

        # Polling timer
        self.polling_timer: Optional[QTimer] = None

        # Update rate limit
        self.last_update_time: float = 0
        self.update_interval = 1 / 60  # 60 Hz update rate

        # Max events and tracked keys
        self.max_events = 50
        self.tracked_keys_set: Set[str] = set()
        self.supported_keys: List[str] = [
            "cross",
            "circle",
            "square",
            "triangle",
            "dpad_up",
            "dpad_down",
            "dpad_left",
            "dpad_right",
            "l1",
            "r1",
            "share",
            "options",
            "ps",
            "touchpad",
            "left_stick",
            "right_stick",
        ]

        # Initialize SDL2
        self.initialize_sdl()

    def initialize_sdl(self) -> bool:
        """
        Initialize SDL2 for controller support.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            result = sdl2.SDL_Init(
                sdl2.SDL_INIT_JOYSTICK
                | sdl2.SDL_INIT_GAMECONTROLLER
                | sdl2.SDL_INIT_HAPTIC
            )
            if result != 0:
                error = sdl2.SDL_GetError().decode()
                print(f"Error initializing SDL2: {error}")
                return False
            return True
        except Exception as e:
            print(f"Exception initializing SDL2: {e}")
            return False

    def start_capture(self) -> None:
        """
        Start capturing controller input events.

        Begins the process of capturing input events from the controller.
        """
        if self.is_capturing:
            return

        self.is_capturing = True

        # Make sure we have a controller connection
        if not self.controller:
            self.connect_to_first_available()

        # Start polling timer if not started
        if not self.polling_timer:
            self.polling_timer = QTimer()
            self.polling_timer.setInterval(16)  # ~60 fps
            self.polling_timer.timeout.connect(self.poll_events)
            self.polling_timer.start()

        print("PS4 controller capture started")

    def stop_capture(self) -> None:
        """
        Stop capturing controller input events.

        Stops the process of capturing input events from the controller.
        """
        if not self.is_capturing:
            return

        self.is_capturing = False

        # Stop polling timer
        if self.polling_timer:
            self.polling_timer.stop()
            self.polling_timer = None

        print("PS4 controller capture stopped")

    def poll_events(self) -> None:
        """Poll for controller events and update state."""
        # Skip if not capturing
        if not self.is_capturing:
            return

        # Rate limit updates
        current_time = time.time()
        if current_time - self.last_update_time < self.update_interval:
            return
        self.last_update_time = current_time

        # Process SDL events
        sdl2.SDL_PumpEvents()

        # Check if controller is still connected
        if self.controller and not sdl2.SDL_GameControllerGetAttached(self.controller):
            self._on_controller_disconnected()
            return

        # Try to reconnect if no controller
        if not self.controller:
            if not self.connect_to_first_available():
                return

        # Process controller inputs
        self._process_button_inputs()
        self._process_stick_inputs()
        self._process_trigger_inputs()

    def _process_button_inputs(self) -> None:
        """Process button inputs and emit events for changes."""
        if not self.controller:
            return

        button_mapping = {
            "triangle": sdl2.SDL_CONTROLLER_BUTTON_Y,
            "circle": sdl2.SDL_CONTROLLER_BUTTON_B,
            "cross": sdl2.SDL_CONTROLLER_BUTTON_A,
            "square": sdl2.SDL_CONTROLLER_BUTTON_X,
            "dpad_up": sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP,
            "dpad_down": sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN,
            "dpad_left": sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT,
            "dpad_right": sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT,
            "l1": sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER,
            "r1": sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER,
            "share": sdl2.SDL_CONTROLLER_BUTTON_BACK,
            "options": sdl2.SDL_CONTROLLER_BUTTON_START,
            "left_stick": sdl2.SDL_CONTROLLER_BUTTON_LEFTSTICK,
            "right_stick": sdl2.SDL_CONTROLLER_BUTTON_RIGHTSTICK,
            "ps": sdl2.SDL_CONTROLLER_BUTTON_GUIDE,
        }

        for button_name, sdl_button in button_mapping.items():
            current_state = bool(
                sdl2.SDL_GameControllerGetButton(self.controller, sdl_button)
            )
            previous_state = self.button_states.get(button_name, False)

            # If state changed, create an event
            if current_state != previous_state:
                self.button_states[button_name] = current_state

                # Create event
                event = InputData(
                    timestamp=time.time(),
                    event_type="button_press" if current_state else "button_release",
                    key=button_name,
                    active_keys=self.get_active_keys(),
                )

                # Process event
                self._process_event(event)

        # Process touchpad button with special handling
        self._process_touchpad_button()

    def _process_touchpad_button(self) -> None:
        """Detect touchpad press using various methods."""
        if not self.controller or not self.joystick:
            return

        touchpad_pressed = False

        # Method 1: Try MISC1 button (common for PS4 touchpad)
        try:
            touchpad_pressed = bool(
                sdl2.SDL_GameControllerGetButton(
                    self.controller, sdl2.SDL_CONTROLLER_BUTTON_MISC1
                )
            )
        except:
            pass

        # Method 2: Try raw joystick access for common touchpad button indices
        if not touchpad_pressed:
            num_buttons = sdl2.SDL_JoystickNumButtons(self.joystick)
            for button_idx in [13, 14, 15, 16, 17, 18]:
                if button_idx < num_buttons:
                    try:
                        if sdl2.SDL_JoystickGetButton(self.joystick, button_idx):
                            # Check this isn't a d-pad false positive
                            dpad_conflict = any(
                                [
                                    self.button_states.get("dpad_up", False),
                                    self.button_states.get("dpad_down", False),
                                    self.button_states.get("dpad_left", False),
                                    self.button_states.get("dpad_right", False),
                                ]
                            )

                            if not dpad_conflict:
                                touchpad_pressed = True
                                break
                    except:
                        pass

        # Method 3: Try constant index 15 (sometimes used for touchpad)
        if not touchpad_pressed:
            try:
                touchpad_pressed = bool(
                    sdl2.SDL_GameControllerGetButton(self.controller, 15)
                )
            except:
                pass

        # Update state and emit event if changed
        previous_state = self.button_states.get("touchpad", False)
        if touchpad_pressed != previous_state:
            self.button_states["touchpad"] = touchpad_pressed

            # Create event
            event = InputData(
                timestamp=time.time(),
                event_type="button_press" if touchpad_pressed else "button_release",
                key="touchpad",
                active_keys=self.get_active_keys(),
            )

            # Process event
            self._process_event(event)

    def _process_stick_inputs(self) -> None:
        """Process analog stick inputs."""
        if not self.controller:
            return

        # Get left stick position
        left_x = (
            sdl2.SDL_GameControllerGetAxis(
                self.controller, sdl2.SDL_CONTROLLER_AXIS_LEFTX
            )
            / 32767.0
        )
        left_y = (
            sdl2.SDL_GameControllerGetAxis(
                self.controller, sdl2.SDL_CONTROLLER_AXIS_LEFTY
            )
            / 32767.0
        )

        # Get right stick position
        right_x = (
            sdl2.SDL_GameControllerGetAxis(
                self.controller, sdl2.SDL_CONTROLLER_AXIS_RIGHTX
            )
            / 32767.0
        )
        right_y = (
            sdl2.SDL_GameControllerGetAxis(
                self.controller, sdl2.SDL_CONTROLLER_AXIS_RIGHTY
            )
            / 32767.0
        )

        # Apply deadzone
        def apply_deadzone(value, deadzone=0.15):
            if abs(value) < deadzone:
                return 0.0
            return value

        left_x = apply_deadzone(left_x)
        left_y = apply_deadzone(left_y)
        right_x = apply_deadzone(right_x)
        right_y = apply_deadzone(right_y)

        # Check for significant changes
        prev_left = self.stick_positions["left"]
        prev_right = self.stick_positions["right"]

        # Left stick changed significantly
        if abs(left_x - prev_left[0]) > 0.05 or abs(left_y - prev_left[1]) > 0.05:
            self.stick_positions["left"] = (left_x, left_y)

            # Create event - only X axis for consistency with InputData structure
            event = InputData(
                timestamp=time.time(),
                event_type="axis_motion",
                key="Left_Stick_X",
                rel_x=left_x,
                rel_y=left_y,
                active_keys=self.get_active_keys(),
            )

            # Process event
            self._process_event(event)

        # Right stick changed significantly
        if abs(right_x - prev_right[0]) > 0.05 or abs(right_y - prev_right[1]) > 0.05:
            self.stick_positions["right"] = (right_x, right_y)

            # Create event - only X axis for consistency with InputData structure
            event = InputData(
                timestamp=time.time(),
                event_type="axis_motion",
                key="Right_Stick_X",
                rel_x=right_x,
                rel_y=right_y,
                active_keys=self.get_active_keys(),
            )

            # Process event
            self._process_event(event)

    def _process_trigger_inputs(self) -> None:
        """Process trigger inputs."""
        if not self.controller:
            return

        # Get trigger values
        left_trigger = sdl2.SDL_GameControllerGetAxis(
            self.controller, sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT
        )
        right_trigger = sdl2.SDL_GameControllerGetAxis(
            self.controller, sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT
        )

        # Apply deadzone
        def apply_deadzone(value, deadzone=1000):
            if value < deadzone:
                return 0
            return value

        left_trigger = apply_deadzone(left_trigger)
        right_trigger = apply_deadzone(right_trigger)

        # Check for significant changes
        prev_left = self.trigger_values["left"]
        prev_right = self.trigger_values["right"]

        # Left trigger changed significantly
        if abs(left_trigger - prev_left) > 1000:
            self.trigger_values["left"] = left_trigger

            # Create event
            event = InputData(
                timestamp=time.time(),
                event_type="axis_motion",
                key="Left_Trigger",
                rel_x=left_trigger / 32767.0,
                active_keys=self.get_active_keys(),
            )

            # Process event
            self._process_event(event)

        # Right trigger changed significantly
        if abs(right_trigger - prev_right) > 1000:
            self.trigger_values["right"] = right_trigger

            # Create event
            event = InputData(
                timestamp=time.time(),
                event_type="axis_motion",
                key="Right_Trigger",
                rel_x=right_trigger / 32767.0,
                active_keys=self.get_active_keys(),
            )

            # Process event
            self._process_event(event)

    def scan_controllers(self) -> List[Dict[str, Any]]:
        """
        Scan for available controllers.

        Returns:
            List[Dict[str, Any]]: List of controller information dictionaries
        """
        controllers = []

        # Refresh SDL state
        sdl2.SDL_GameControllerUpdate()

        # Check for controllers
        num_joysticks = sdl2.SDL_NumJoysticks()
        for i in range(num_joysticks):
            if sdl2.SDL_IsGameController(i):
                name = sdl2.SDL_GameControllerNameForIndex(i)
                if name:
                    name = name.decode("utf-8", errors="replace")
                else:
                    name = f"Controller {i}"

                # Check if this is a PS4 controller
                is_ps4 = (
                    "ps4" in name.lower()
                    or "dualshock" in name.lower()
                    or "playstation" in name.lower()
                )

                controllers.append({"index": i, "name": name, "is_ps4": is_ps4})

        return controllers

    def connect_to_first_available(self) -> bool:
        """
        Connect to the first available controller.

        Returns:
            bool: True if successful, False otherwise
        """
        controllers = self.scan_controllers()
        if controllers:
            return self.connect_to_controller(controllers[0]["index"])
        return False

    def connect_to_controller(self, controller_index: int) -> bool:
        """
        Connect to a specific controller.

        Args:
            controller_index: SDL2 index of the controller

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Close existing controller
            if self.controller:
                sdl2.SDL_GameControllerClose(self.controller)
                self.controller = None

            if self.joystick:
                sdl2.SDL_JoystickClose(self.joystick)
                self.joystick = None

            # Open the controller
            self.controller = sdl2.SDL_GameControllerOpen(controller_index)
            if not self.controller:
                error = sdl2.SDL_GetError().decode()
                print(f"Error opening controller: {error}")
                return False

            # Also open as joystick for raw access
            self.joystick = sdl2.SDL_JoystickOpen(controller_index)
            if not self.joystick:
                error = sdl2.SDL_GetError().decode()
                print(f"Error opening joystick: {error}")
                sdl2.SDL_GameControllerClose(self.controller)
                self.controller = None
                return False

            # Get controller name
            name = sdl2.SDL_GameControllerName(self.controller)
            if name:
                self.controller_name = name.decode("utf-8", errors="replace")
            else:
                self.controller_name = f"Controller {controller_index}"

            self.controller_index = controller_index

            # Reset all state
            self.button_states = {}
            self.stick_positions = {"left": (0, 0), "right": (0, 0)}
            self.trigger_values = {"left": 0, "right": 0}

            print(f"Connected to controller: {self.controller_name}")
            return True

        except Exception as e:
            print(f"Exception connecting to controller: {e}")

            # Clean up
            if self.controller:
                sdl2.SDL_GameControllerClose(self.controller)
                self.controller = None

            if self.joystick:
                sdl2.SDL_JoystickClose(self.joystick)
                self.joystick = None

            return False

    def _on_controller_disconnected(self) -> None:
        """Handle controller disconnection."""
        print("Controller disconnected")

        # Clean up
        if self.controller:
            sdl2.SDL_GameControllerClose(self.controller)
            self.controller = None

        if self.joystick:
            sdl2.SDL_JoystickClose(self.joystick)
            self.joystick = None

        # Reset states
        self.button_states = {}
        self.stick_positions = {"left": (0, 0), "right": (0, 0)}
        self.trigger_values = {"left": 0, "right": 0}

        # Create a disconnection event
        event = InputData(
            timestamp=time.time(), event_type="controller_disconnected", active_keys=[]
        )

        # Process event
        self._process_event(event)

        # Try to reconnect
        threading.Thread(target=self._try_reconnect, daemon=True).start()

    def _try_reconnect(self) -> None:
        """Try to reconnect to a controller periodically."""
        attempts = 0
        max_attempts = 10

        while attempts < max_attempts:
            attempts += 1
            print(
                f"Attempting to reconnect to controller ({attempts}/{max_attempts})..."
            )

            if self.connect_to_first_available():
                print("Controller reconnected")

                # Create a connection event
                event = InputData(
                    timestamp=time.time(),
                    event_type="controller_connected",
                    key=self.controller_name,
                    active_keys=[],
                )

                # Process event
                self._process_event(event)
                return

            # Wait before retrying
            time.sleep(1)

        print("Failed to reconnect to controller after multiple attempts")

    def _process_event(self, event: InputData) -> None:
        """
        Process a controller event.

        Args:
            event: The controller event to process
        """
        # Add to event history
        self.controller_events.append(event)
        if len(self.controller_events) > self.max_events:
            self.controller_events = self.controller_events[-self.max_events :]

        # Notify callbacks
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event callback: {e}")

    def get_input_event(self) -> InputData:
        """
        Get the most recent input event.

        Returns:
            InputData: The most recent input event, or a placeholder event if no events exist
        """
        if not self.controller_events:
            return InputData(
                timestamp=time.time(),
                event_type="none",
                active_keys=self.get_active_keys(),
            )

        return self.controller_events[-1]

    def on_event(self, callback: Callable[[InputData], None]) -> None:
        """
        Register a callback for input events.

        Args:
            callback: Function to be called when a new input event is processed
        """
        self.event_callbacks.append(callback)

    def set_supported_keys(self, keys: List[str]) -> None:
        """
        Set the keys to be tracked by the collector.

        Args:
            keys: List of key identifiers to track
        """
        self.supported_keys = keys
        # Update tracked keys set for efficient lookup
        self.tracked_keys_set = set(k.lower() for k in self.supported_keys)

    def get_events_since(self, timestamp: float) -> List[InputData]:
        """
        Get all events since a specific timestamp.

        Args:
            timestamp: Time (in seconds since epoch) to retrieve events from

        Returns:
            List[InputData]: List of input events that occurred since the given timestamp
        """
        return [e for e in self.controller_events if e.timestamp >= timestamp]

    def clear_events(self) -> None:
        """Clear all stored events."""
        self.controller_events.clear()

    def get_active_keys(self) -> List[str]:
        """
        Get a list of currently active buttons.

        Returns:
            List[str]: List of active buttons
        """
        active_keys = []

        # Add pressed buttons to active keys list
        for button, is_pressed in self.button_states.items():
            if is_pressed:
                # Only include buttons that are being tracked
                if button.lower() in self.tracked_keys_set:
                    active_keys.append(button)

        return active_keys

    def get_collector_type(self) -> str:
        """
        Get the type of this collector.

        Returns:
            str: The collector type identifier
        """
        return "ps4_controller"

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of this collector.

        Returns:
            Dict[str, Any]: Dictionary of collector capabilities
        """
        return {
            "supports_mouse_tracking": False,
            "supports_keyboard": False,
            "supports_mouse_buttons": False,
            "supports_mouse_movement": False,
            "supports_mouse_scroll": False,
            "supports_joystick": True,  # It has joystick-like controls
            "supports_triggers": True,  # It has analog triggers
            "supports_ps4": True,  # It's a PS4 controller
            "supported_tracking_modes": [],
        }

    def __del__(self) -> None:
        """Clean up SDL2 resources."""
        try:
            # Stop polling
            if self.polling_timer:
                self.polling_timer.stop()
                self.polling_timer = None

            # Close controller
            if self.controller:
                sdl2.SDL_GameControllerClose(self.controller)
                self.controller = None

            # Close joystick
            if self.joystick:
                sdl2.SDL_JoystickClose(self.joystick)
                self.joystick = None
        except:
            pass
