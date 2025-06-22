"""
PS4 controller input collection module.

This module provides functionality for capturing and processing PS4 controller
inputs using SDL2, with support for buttons, analog sticks and triggers.
"""

import threading
import time
from typing import List, Dict, Any, Callable, Set, Optional, Tuple

import sdl2
import sdl2.ext

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
        self.stick_positions: Dict[str, Tuple[float, float]] = {
            "left": (0.0, 0.0),
            "right": (0.0, 0.0),
        }

        # Trigger values
        self.trigger_values: Dict[str, float] = {"left": 0.0, "right": 0.0}

        # Previous values to track threshold crossings
        self.previous_trigger_values: Dict[str, float] = {"left": 0.0, "right": 0.0}
        self.previous_stick_positions: Dict[str, Tuple[float, float]] = {
            "left": (0.0, 0.0),
            "right": (0.0, 0.0),
        }

        # Threading for event processing
        self.event_thread: Optional[threading.Thread] = None
        self.event_stop_event: threading.Event = threading.Event()

        # Thread safety
        self.event_lock: threading.Lock = threading.Lock()

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
                | sdl2.SDL_INIT_EVENTS
            )
            if result != 0:
                error = sdl2.SDL_GetError().decode()
                print(f"Error initializing SDL2: {error}")
                return False

            # Enable controller events
            sdl2.SDL_GameControllerEventState(sdl2.SDL_ENABLE)
            sdl2.SDL_JoystickEventState(sdl2.SDL_ENABLE)

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

        # Reset connection state
        self.controller_index = -1

        # Make sure we have a controller connection
        if not self.controller:
            self.connect_to_first_available()

        # Start event processing thread if not started
        if not self.event_thread or not self.event_thread.is_alive():
            self.event_stop_event.clear()
            self.event_thread = threading.Thread(target=self._event_loop, daemon=True)
            self.event_thread.start()

        print("PS4 controller capture started")

    def stop_capture(self) -> None:
        """
        Stop capturing controller input events.

        Stops the process of capturing input events from the controller.
        """
        if not self.is_capturing:
            return

        self.is_capturing = False

        # Stop event thread
        if self.event_thread and self.event_thread.is_alive():
            self.event_stop_event.set()
            # Give the thread a moment to stop
            self.event_thread.join(timeout=1.0)

        # Process any remaining SDL events to clear the queue
        self._clear_sdl_event_queue()

        # Force refresh SDL2 subsystems to detect reconnected controllers
        self._refresh_sdl_subsystems()

        print("PS4 controller capture stopped")

    def _refresh_sdl_subsystems(self) -> None:
        """Force refresh SDL2 subsystems to detect reconnected controllers."""
        try:
            # Close existing connections first
            if self.controller:
                sdl2.SDL_GameControllerClose(self.controller)
                self.controller = None

            if self.joystick:
                sdl2.SDL_JoystickClose(self.joystick)
                self.joystick = None

            # Reset controller index
            self.controller_index = -1

            # Quit and reinitialize the joystick/gamecontroller subsystems
            sdl2.SDL_QuitSubSystem(
                sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER
            )

            # Small delay to ensure cleanup
            time.sleep(0.1)

            # Reinitialize
            result = sdl2.SDL_InitSubSystem(
                sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER
            )
            if result == 0:
                # Re-enable events
                sdl2.SDL_GameControllerEventState(sdl2.SDL_ENABLE)
                sdl2.SDL_JoystickEventState(sdl2.SDL_ENABLE)
            else:
                error = sdl2.SDL_GetError().decode()
                print(f"Error reinitializing SDL2 subsystems: {error}")

        except Exception as e:
            print(f"Error refreshing SDL subsystems: {e}")

    def _clear_sdl_event_queue(self) -> None:
        """Clear SDL event queue to prevent stale events."""
        try:
            # Pump events and clear the queue
            sdl2.SDL_PumpEvents()
            event = sdl2.SDL_Event()
            # Process all pending events without acting on them
            while sdl2.SDL_PollEvent(event):
                pass
        except Exception as e:
            print(f"Error clearing SDL event queue: {e}")

    def _event_loop(self) -> None:
        """Main event loop that processes SDL2 events."""
        last_scan_time = 0.0
        scan_interval = 1.0  # Scan for controllers every second

        while not self.event_stop_event.is_set() and self.is_capturing:
            try:
                # Process SDL events
                event = sdl2.SDL_Event()

                # Check for events with a short timeout
                has_event = sdl2.SDL_WaitEventTimeout(event, 16)  # 16ms timeout (~60Hz)

                if has_event:
                    self._process_sdl_event(event)

                # Periodically check for controller connection/disconnection
                current_time = time.time()
                if current_time - last_scan_time > scan_interval:
                    last_scan_time = current_time

                    if self.controller:
                        # Check if current controller is still attached
                        if not sdl2.SDL_GameControllerGetAttached(self.controller):
                            self._on_controller_disconnected()
                    else:
                        # Try to find and connect to a controller
                        self._try_connect_without_blocking()

            except Exception as e:
                print(f"Error in event loop: {e}")
                # Brief pause before continuing to avoid tight error loops
                time.sleep(0.1)

    def _try_connect_without_blocking(self) -> None:
        """Try to connect to a controller without blocking the event loop."""
        try:
            # Force SDL to detect new devices more aggressively
            sdl2.SDL_GameControllerUpdate()
            sdl2.SDL_JoystickUpdate()

            # Force event processing to detect new devices
            sdl2.SDL_PumpEvents()

            controllers = self.scan_controllers()
            if controllers and not self.controller:
                # Removed the print statement to reduce spam in logs
                self.connect_to_controller(controllers[0]["index"])
        except Exception as e:
            print(f"Error in non-blocking connect: {e}")

    def _process_sdl_event(self, event: sdl2.SDL_Event) -> None:
        """Process a single SDL2 event."""
        if event.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
            self._handle_button_event(event.cbutton, True)
        elif event.type == sdl2.SDL_CONTROLLERBUTTONUP:
            self._handle_button_event(event.cbutton, False)
        elif event.type == sdl2.SDL_CONTROLLERAXISMOTION:
            self._handle_axis_event(event.caxis)
        elif event.type == sdl2.SDL_CONTROLLERDEVICEADDED:
            print(f"Controller device added: {event.cdevice.which}")
            if not self.controller:
                # Small delay to ensure the device is ready
                threading.Timer(
                    0.1, lambda: self.connect_to_controller(event.cdevice.which)
                ).start()
        elif event.type == sdl2.SDL_CONTROLLERDEVICEREMOVED:
            print(f"Controller device removed: {event.cdevice.which}")
            if self.controller and event.cdevice.which == self.controller_index:
                self._on_controller_disconnected()
        elif event.type == sdl2.SDL_JOYBUTTONDOWN:
            # Handle touchpad and other special buttons
            self._handle_joystick_button_event(event.jbutton, True)
        elif event.type == sdl2.SDL_JOYBUTTONUP:
            self._handle_joystick_button_event(event.jbutton, False)

    def _handle_button_event(
        self, button_event: sdl2.SDL_ControllerButtonEvent, is_pressed: bool
    ) -> None:
        """Handle controller button events."""
        if not self.controller:
            return

        # Map SDL button codes to our button names
        button_mapping = {
            sdl2.SDL_CONTROLLER_BUTTON_Y: "triangle",
            sdl2.SDL_CONTROLLER_BUTTON_B: "circle",
            sdl2.SDL_CONTROLLER_BUTTON_A: "cross",
            sdl2.SDL_CONTROLLER_BUTTON_X: "square",
            sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP: "dpad_up",
            sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN: "dpad_down",
            sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT: "dpad_left",
            sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT: "dpad_right",
            sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER: "l1",
            sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER: "r1",
            sdl2.SDL_CONTROLLER_BUTTON_BACK: "share",
            sdl2.SDL_CONTROLLER_BUTTON_START: "options",
            sdl2.SDL_CONTROLLER_BUTTON_LEFTSTICK: "left_stick",
            sdl2.SDL_CONTROLLER_BUTTON_RIGHTSTICK: "right_stick",
            sdl2.SDL_CONTROLLER_BUTTON_GUIDE: "ps",
        }

        button_name = button_mapping.get(button_event.button)
        if button_name:
            # Update button state
            self.button_states[button_name] = is_pressed

            # Create event
            event = InputData(
                timestamp=time.time(),
                event_type="button_press" if is_pressed else "button_release",
                key=button_name,
                active_keys=self.get_active_keys(),
            )

            # Process event
            self._process_event(event)

    def _handle_joystick_button_event(
        self, button_event: sdl2.SDL_JoyButtonEvent, is_pressed: bool
    ) -> None:
        """Handle joystick button events (for touchpad and other special buttons)."""
        if not self.joystick:
            return

        # Check for touchpad button on common indices
        if button_event.button in [13, 14, 15, 16, 17, 18]:
            # Verify this isn't a d-pad conflict
            dpad_conflict = any(
                [
                    self.button_states.get("dpad_up", False),
                    self.button_states.get("dpad_down", False),
                    self.button_states.get("dpad_left", False),
                    self.button_states.get("dpad_right", False),
                ]
            )

            if not dpad_conflict:
                # Update touchpad state
                self.button_states["touchpad"] = is_pressed

                # Create event
                event = InputData(
                    timestamp=time.time(),
                    event_type="button_press" if is_pressed else "button_release",
                    key="touchpad",
                    active_keys=self.get_active_keys(),
                )

                # Process event
                self._process_event(event)

    def _handle_axis_event(self, axis_event: sdl2.SDL_ControllerAxisEvent) -> None:
        """Handle controller axis motion events."""
        if not self.controller:
            return

        # Apply deadzone
        def apply_deadzone(value, deadzone=0.15):
            normalized = value / 32767.0
            if abs(normalized) < deadzone:
                return 0.0
            return normalized

        def apply_trigger_deadzone(value, deadzone=500):
            if value < deadzone:
                return 0.0
            return float(value)

        # Handle different axis types
        if axis_event.axis == sdl2.SDL_CONTROLLER_AXIS_LEFTX:
            # Left stick X
            normalized_value = apply_deadzone(axis_event.value)
            old_pos = self.stick_positions["left"]
            self.stick_positions["left"] = (normalized_value, old_pos[1])

            event = InputData(
                timestamp=time.time(),
                event_type="axis_motion",
                key="Left_Stick_X",
                rel_x=normalized_value,
                rel_y=old_pos[1],
                active_keys=self.get_active_keys(),
            )
            self._process_event(event)

        elif axis_event.axis == sdl2.SDL_CONTROLLER_AXIS_LEFTY:
            # Left stick Y
            normalized_value = apply_deadzone(axis_event.value)
            old_pos = self.stick_positions["left"]
            self.stick_positions["left"] = (old_pos[0], normalized_value)

            event = InputData(
                timestamp=time.time(),
                event_type="axis_motion",
                key="Left_Stick_Y",  # Fixed: Should be Y for Y axis
                rel_x=old_pos[0],
                rel_y=normalized_value,
                active_keys=self.get_active_keys(),
            )
            self._process_event(event)

        elif axis_event.axis == sdl2.SDL_CONTROLLER_AXIS_RIGHTX:
            # Right stick X
            normalized_value = apply_deadzone(axis_event.value)
            old_pos = self.stick_positions["right"]
            self.stick_positions["right"] = (normalized_value, old_pos[1])

            event = InputData(
                timestamp=time.time(),
                event_type="axis_motion",
                key="Right_Stick_X",
                rel_x=normalized_value,
                rel_y=old_pos[1],
                active_keys=self.get_active_keys(),
            )
            self._process_event(event)

        elif axis_event.axis == sdl2.SDL_CONTROLLER_AXIS_RIGHTY:
            # Right stick Y
            normalized_value = apply_deadzone(axis_event.value)
            old_pos = self.stick_positions["right"]
            self.stick_positions["right"] = (old_pos[0], normalized_value)

            event = InputData(
                timestamp=time.time(),
                event_type="axis_motion",
                key="Right_Stick_Y",  # Fixed: Should be Y for Y axis
                rel_x=old_pos[0],
                rel_y=normalized_value,
                active_keys=self.get_active_keys(),
            )
            self._process_event(event)

        elif axis_event.axis == sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT:
            # Left trigger
            filtered_value = apply_trigger_deadzone(axis_event.value)
            normalized_value = filtered_value / 32767.0
            self.trigger_values["left"] = filtered_value

            event = InputData(
                timestamp=time.time(),
                event_type="axis_motion",
                key="Left_Trigger",
                rel_x=normalized_value,
                active_keys=self.get_active_keys(),
            )
            self._process_event(event)

        elif axis_event.axis == sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT:
            # Right trigger
            filtered_value = apply_trigger_deadzone(axis_event.value)
            normalized_value = filtered_value / 32767.0
            self.trigger_values["right"] = filtered_value

            event = InputData(
                timestamp=time.time(),
                event_type="axis_motion",
                key="Right_Trigger",
                rel_x=normalized_value,
                active_keys=self.get_active_keys(),
            )
            self._process_event(event)

    def scan_controllers(self) -> List[Dict[str, Any]]:
        """
        Scan for available controllers.

        Returns:
            List[Dict[str, Any]]: List of controller information dictionaries
        """
        controllers = []

        try:
            # More aggressive device detection
            sdl2.SDL_PumpEvents()
            sdl2.SDL_GameControllerUpdate()
            sdl2.SDL_JoystickUpdate()

            # Process any pending device events
            event = sdl2.SDL_Event()
            device_events_found = 0
            while sdl2.SDL_PollEvent(event):
                if event.type in [
                    sdl2.SDL_CONTROLLERDEVICEADDED,
                    sdl2.SDL_CONTROLLERDEVICEREMOVED,
                ]:
                    device_events_found += 1

            if device_events_found > 0:
                print(f"Processed {device_events_found} device event(s) during scan")

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

            # Only log if we found controllers or if we're actively looking
            if controllers:
                print(f"Found {len(controllers)} controller(s)")

        except Exception as e:
            print(f"Error scanning controllers: {e}")

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

            # Verify the controller index is valid
            if not sdl2.SDL_IsGameController(controller_index):
                print(
                    f"Controller index {controller_index} is not a valid game controller"
                )
                return False

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
            self.stick_positions = {"left": (0.0, 0.0), "right": (0.0, 0.0)}
            self.trigger_values = {"left": 0.0, "right": 0.0}

            print(f"Connected to controller: {self.controller_name}")

            # Create a connection event if we're capturing
            if self.is_capturing:
                event = InputData(
                    timestamp=time.time(),
                    event_type="controller_connected",
                    key=self.controller_name,
                    active_keys=[],
                )
                self._process_event(event)

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
        self.stick_positions = {"left": (0.0, 0.0), "right": (0.0, 0.0)}
        self.trigger_values = {"left": 0.0, "right": 0.0}
        self.controller_index = -1

        # Create a disconnection event only if we're capturing
        if self.is_capturing:
            event = InputData(
                timestamp=time.time(),
                event_type="controller_disconnected",
                active_keys=[],
            )
            self._process_event(event)

            # Don't start automatic reconnection if we're still capturing
            # Let the main event loop handle it
        else:
            # Only try reconnection if we're not in the middle of stopping
            threading.Thread(target=self._try_reconnect, daemon=True).start()

    def _try_reconnect(self) -> None:
        """Try to reconnect to a controller periodically."""
        attempts = 0
        max_attempts = 5  # Reduced attempts since main loop will also try

        while attempts < max_attempts and not self.controller:
            attempts += 1
            print(
                f"Attempting to reconnect to controller ({attempts}/{max_attempts})..."
            )

            # Force refresh before attempting
            try:
                sdl2.SDL_PumpEvents()
                sdl2.SDL_GameControllerUpdate()
                sdl2.SDL_JoystickUpdate()
            except:
                pass

            if self.connect_to_first_available():
                print("Controller reconnected")
                return

            # Wait before retrying
            time.sleep(2)

        if not self.controller:
            print("Failed to reconnect to controller after multiple attempts")

    def _process_event(self, event: InputData) -> None:
        """
        Process a controller event with thread safety.

        Args:
            event: The controller event to process
        """
        # Thread-safe event processing
        with self.event_lock:
            # Add to event history
            self.controller_events.append(event)
            if len(self.controller_events) > self.max_events:
                self.controller_events = self.controller_events[-self.max_events :]

        # Notify callbacks - do this outside the lock to avoid deadlocks
        # Make a copy of callbacks to avoid issues if list is modified during iteration
        callbacks_copy = list(self.event_callbacks)
        for callback in callbacks_copy:
            try:
                # Use threading to ensure callback doesn't block the polling thread
                threading.Thread(
                    target=self._safe_callback, args=(callback, event), daemon=True
                ).start()
            except Exception as e:
                print(f"Error starting callback thread: {e}")

    def _safe_callback(
        self, callback: Callable[[InputData], None], event: InputData
    ) -> None:
        """
        Execute callback safely in a separate thread.

        Args:
            callback: The callback function to execute
            event: The event to pass to the callback
        """
        try:
            callback(event)
        except Exception as e:
            print(f"Error in event callback: {e}")

    def get_input_event(self) -> InputData:
        """
        Get the most recent input event with thread safety.

        Returns:
            InputData: The most recent input event, or a placeholder event if no events exist
        """
        with self.event_lock:
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
        Get all events since a specific timestamp with thread safety.

        Args:
            timestamp: Time (in seconds since epoch) to retrieve events from

        Returns:
            List[InputData]: List of input events that occurred since the given timestamp
        """
        with self.event_lock:
            return [e for e in self.controller_events if e.timestamp >= timestamp]

    def clear_events(self) -> None:
        """Clear all stored events with thread safety."""
        with self.event_lock:
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
            # Stop capture first
            self.stop_capture()

            # Close controller connections
            if self.controller:
                sdl2.SDL_GameControllerClose(self.controller)
                self.controller = None

            if self.joystick:
                sdl2.SDL_JoystickClose(self.joystick)
                self.joystick = None

            # Quit SDL2 subsystems if they were initialized
            try:
                sdl2.SDL_QuitSubSystem(
                    sdl2.SDL_INIT_JOYSTICK
                    | sdl2.SDL_INIT_GAMECONTROLLER
                    | sdl2.SDL_INIT_HAPTIC
                )
            except:
                pass

        except Exception:
            # Silently handle any cleanup errors
            pass
