"""
PS4 controller input collection module.

This module provides functionality for capturing and processing input events from
a PS4 controller using SDL2, providing a unified interface compatible with the application's
input collector framework.
"""

import time
import threading
import ctypes
import math  # Added for magnitude calculations in axis events
from typing import List, Dict, Optional, Callable, Set, Any

try:
    from sdl2 import *

    HAVE_SDL2 = True
except ImportError:
    HAVE_SDL2 = False

from ..interfaces import InputData, AbstractInputCollector


class PS4ControllerCollector(AbstractInputCollector):
    """
    Collects input events from a PS4 controller using SDL2.

    This class captures PS4 controller events, processes them,
    and provides a unified interface for accessing input state compatible
    with the input collector framework.
    """

    def __init__(self) -> None:
        """
        Initialize the PS4 controller collector.

        Sets up SDL2 and prepares for controller input capture.
        Verifies SDL2 is available and initializes internal state.
        """
        # Check if SDL2 is available
        if not HAVE_SDL2:
            raise ImportError(
                "PySDL2 is not installed. Install with 'pip install pysdl2 pysdl2-dll'"
            )

        # Button mappings for PS4 controller - defined here after SDL2 import is confirmed
        self.BUTTON_NAMES = {
            SDL_CONTROLLER_BUTTON_A: "Cross",  # Cross button
            SDL_CONTROLLER_BUTTON_B: "Circle",  # Circle button
            SDL_CONTROLLER_BUTTON_X: "Square",  # Square button
            SDL_CONTROLLER_BUTTON_Y: "Triangle",  # Triangle button
            SDL_CONTROLLER_BUTTON_BACK: "Share",  # Share button
            SDL_CONTROLLER_BUTTON_START: "Options",  # Options button
            SDL_CONTROLLER_BUTTON_LEFTSTICK: "L3",  # Left stick button
            SDL_CONTROLLER_BUTTON_RIGHTSTICK: "R3",  # Right stick button
            SDL_CONTROLLER_BUTTON_LEFTSHOULDER: "L1",  # L1 button
            SDL_CONTROLLER_BUTTON_RIGHTSHOULDER: "R1",  # R1 button
            SDL_CONTROLLER_BUTTON_DPAD_UP: "DPad_Up",  # D-pad Up
            SDL_CONTROLLER_BUTTON_DPAD_DOWN: "DPad_Down",  # D-pad Down
            SDL_CONTROLLER_BUTTON_DPAD_LEFT: "DPad_Left",  # D-pad Left
            SDL_CONTROLLER_BUTTON_DPAD_RIGHT: "DPad_Right",  # D-pad Right
            SDL_CONTROLLER_BUTTON_GUIDE: "PS",  # PS button
        }

        # Add touchpad button if available in this SDL2 version
        try:
            self.BUTTON_NAMES[SDL_CONTROLLER_BUTTON_TOUCHPAD] = "Touchpad"
        except:
            pass

        # Axis mappings for PS4 controller
        self.AXIS_NAMES = {
            SDL_CONTROLLER_AXIS_LEFTX: "LeftStick_X",
            SDL_CONTROLLER_AXIS_LEFTY: "LeftStick_Y",
            SDL_CONTROLLER_AXIS_RIGHTX: "RightStick_X",
            SDL_CONTROLLER_AXIS_RIGHTY: "RightStick_Y",
            SDL_CONTROLLER_AXIS_TRIGGERLEFT: "L2_Trigger",
            SDL_CONTROLLER_AXIS_TRIGGERRIGHT: "R2_Trigger",
        }

        # Events storage
        self.events: List[InputData] = []

        # State tracking
        self.is_capturing: bool = False
        self.event_callbacks: List[Callable[[InputData], None]] = []

        # Button state tracking
        self.button_state: Dict[str, bool] = {}

        # Axis state tracking
        self.axis_state: Dict[str, float] = {}

        # SDL controller reference
        self.controller = None
        self.sdl_initialized = False

        # Display information
        self.controller_name = "Not connected"

        # Connected controllers list - stores (index, name, is_ps4) tuples
        self.available_controllers = []

        # Tracked buttons/axes
        self.supported_inputs: List[str] = [
            "Cross",
            "Circle",
            "Square",
            "Triangle",
            "L1",
            "R1",
            "L2_Trigger",
            "R2_Trigger",
            "DPad_Up",
            "DPad_Down",
            "DPad_Left",
            "DPad_Right",
            "LeftStick_X",
            "LeftStick_Y",
            "RightStick_X",
            "RightStick_Y",
        ]

        # Thread for polling SDL events
        self.event_thread = None
        self.running = False

        # Critical missing attributes
        self.max_events: int = 50
        self.verbose: bool = False

        # For compatibility with keyboard_mouse collector
        self.keyboard_events: List[InputData] = []
        self.mouse_events: List[InputData] = []

        # Initialize SDL (don't open a controller yet)
        try:
            self.init_sdl()
        except Exception as e:
            print(f"SDL initialization failed: {e}")
            import traceback

            traceback.print_exc()
            raise

    def init_sdl(self) -> bool:
        """
        Initialize SDL2 subsystems.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if self.sdl_initialized:
            return True

        # Initialize required SDL subsystems (VIDEO is required for event loop)
        try:
            # Try to initialize with just GAMECONTROLLER first (better compatibility)
            if SDL_Init(SDL_INIT_GAMECONTROLLER) != 0:
                error = (
                    SDL_GetError().decode()
                    if hasattr(SDL_GetError(), "decode")
                    else SDL_GetError()
                )
                print(f"First SDL init attempt failed: {error}")

                # Fall back to initializing with VIDEO as well
                if SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMECONTROLLER) != 0:
                    error = (
                        SDL_GetError().decode()
                        if hasattr(SDL_GetError(), "decode")
                        else SDL_GetError()
                    )
                    error_msg = f"SDL initialization error: {error}"
                    print(error_msg)
                    raise RuntimeError(error_msg)
        except Exception as e:
            print(f"SDL initialization exception: {e}")
            import traceback

            traceback.print_exc()
            return False

        # Enable controller events
        SDL_GameControllerEventState(SDL_ENABLE)

        # Add Game Controller database for better controller support
        self._load_controller_mappings()

        # Create a hidden window to satisfy SDL requirements
        # This is needed because SDL requires a window to process events on some platforms
        try:
            self.window = SDL_CreateWindow(
                b"Hidden SDL Window",
                SDL_WINDOWPOS_UNDEFINED,
                SDL_WINDOWPOS_UNDEFINED,
                1,
                1,  # Minimal 1x1 window
                SDL_WINDOW_HIDDEN,  # Make it hidden
            )
        except Exception as e:
            print(f"Warning: Could not create hidden window: {e}")

        self.sdl_initialized = True
        return True

    def _load_controller_mappings(self) -> None:
        """Load game controller mappings to improve controller support."""
        # Try to load built-in mappings
        try:
            # Standard PS4 controller mapping for SDL2
            ps4_mapping = (
                "030000004c050000c405000000010000,PS4 Controller,"
                "a:b1,b:b2,back:b8,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,"
                "dpup:h0.1,guide:b12,leftshoulder:b4,leftstick:b10,"
                "lefttrigger:a3,leftx:a0,lefty:a1,rightshoulder:b5,"
                "rightstick:b11,righttrigger:a4,rightx:a2,righty:a5,"
                "start:b9,x:b0,y:b3"
            )
            SDL_GameControllerAddMapping(ps4_mapping.encode())

            # Newer DualSense (PS5) controller which may be detected
            dualsense_mapping = (
                "030000004c050000cc09000000010000,DualSense Wireless Controller,"
                "a:b1,b:b2,back:b8,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,"
                "dpup:h0.1,guide:b12,leftshoulder:b4,leftstick:b10,"
                "lefttrigger:a3,leftx:a0,lefty:a1,rightshoulder:b5,"
                "rightstick:b11,righttrigger:a4,rightx:a2,righty:a5,"
                "start:b9,x:b0,y:b3,misc1:b13"
            )
            SDL_GameControllerAddMapping(dualsense_mapping.encode())
        except Exception as e:
            print(f"Could not load controller mappings: {e}")

    def scan_controllers(self) -> List[Dict[str, Any]]:
        """
        Scan for available controllers.

        Returns:
            List of dictionaries containing controller information:
            [{
                "index": controller index,
                "name": controller name,
                "is_ps4": True if detected as PS4 controller
            }]
        """
        if not self.sdl_initialized and not self.init_sdl():
            return []

        # Clear previous list
        self.available_controllers = []
        controllers = []

        # Look for controllers
        num_joysticks = SDL_NumJoysticks()

        # More detailed logging to identify what's detected
        print(f"Found {num_joysticks} joystick device(s):")

        for i in range(num_joysticks):
            try:
                # First check if it's a game controller (not all joystick devices are game controllers)
                if SDL_IsGameController(i):
                    controller = SDL_GameControllerOpen(i)
                    if controller:
                        # Get controller name
                        name_ptr = SDL_GameControllerName(controller)
                        name = (
                            name_ptr.decode()
                            if name_ptr and hasattr(name_ptr, "decode")
                            else "Unknown Controller"
                        )

                        # Check if it's a PS4 controller by name
                        is_ps4 = (
                            "wireless controller" in name.lower()
                            or "dualshock" in name.lower()
                            or "ps4" in name.lower()
                        )

                        print(
                            f"  - Controller at index {i}: {name} {'(PS4)' if is_ps4 else '(Other)'}"
                        )

                        # Add to our tracking list
                        self.available_controllers.append((i, name, is_ps4))

                        # Add to return data
                        controllers.append({"index": i, "name": name, "is_ps4": is_ps4})

                        # Close the controller for now
                        SDL_GameControllerClose(controller)
                else:
                    # This is a joystick but not a game controller
                    joystick = SDL_JoystickOpen(i)
                    if joystick:
                        name_ptr = SDL_JoystickName(joystick)
                        name = (
                            name_ptr.decode()
                            if name_ptr and hasattr(name_ptr, "decode")
                            else "Unknown Device"
                        )
                        print(f"  - Non-controller joystick at index {i}: {name}")
                        SDL_JoystickClose(joystick)
                    else:
                        print(f"  - Unidentified joystick device at index {i}")
            except Exception as e:
                print(f"  - Error checking device {i}: {e}")

        # Summary for clarity
        if controllers:
            print(f"Total usable controllers found: {len(controllers)}")
        else:
            print("No usable game controllers found")

        return controllers

    def connect_to_controller(self, index: int) -> bool:
        """
        Connect to a specific controller by index.

        Args:
            index: The SDL joystick index to connect to

        Returns:
            bool: True if connection was successful, False otherwise
        """
        if not self.sdl_initialized and not self.init_sdl():
            print("Cannot connect to controller: SDL not initialized")
            return False

        # Close any existing controller
        if self.controller:
            SDL_GameControllerClose(self.controller)
            self.controller = None

        # Try to open the requested controller
        try:
            # Check if the index is valid
            num_joysticks = SDL_NumJoysticks()
            if index < 0 or index >= num_joysticks:
                print(f"Invalid controller index: {index}, max is {num_joysticks-1}")
                return False

            # Check if it's a game controller
            if not SDL_IsGameController(index):
                print(f"Device at index {index} is not a game controller")
                return False

            self.controller = SDL_GameControllerOpen(index)
            if self.controller:
                # Get controller name
                name_ptr = SDL_GameControllerName(self.controller)
                self.controller_name = (
                    name_ptr.decode()
                    if name_ptr and hasattr(name_ptr, "decode")
                    else "Unknown Controller"
                )

                print(f"Connected to controller: {self.controller_name}")
                return True
            else:
                error = (
                    SDL_GetError().decode()
                    if hasattr(SDL_GetError(), "decode")
                    else SDL_GetError()
                )
                print(f"Failed to open controller: {error}")
                return False
        except Exception as e:
            print(f"Error connecting to controller {index}: {e}")
            import traceback

            traceback.print_exc()
            return False

    def find_ps4_controller(self) -> bool:
        """
        Find and open a PS4 controller.

        Returns:
            bool: True if a controller was found and opened, False otherwise
        """
        if not self.sdl_initialized and not self.init_sdl():
            return False

        # Scan for controllers
        controllers = self.scan_controllers()

        # First try to find a PS4 controller
        for controller in controllers:
            if controller["is_ps4"]:
                return self.connect_to_controller(controller["index"])

        # If no PS4 controller, try any controller
        if controllers:
            return self.connect_to_controller(controllers[0]["index"])

        print("No controllers found")
        return False

    def start_capture(self) -> None:
        """
        Start capturing input events from the PS4 controller.

        Initializes SDL2, finds and opens a controller, and starts the event polling thread.
        """
        if self.is_capturing:
            return

        # Initialize SDL if needed
        if not self.sdl_initialized and not self.init_sdl():
            print("Failed to initialize SDL2")
            return

        # Find and open a PS4 controller if we don't already have one
        if not self.controller and not self.find_ps4_controller():
            print("No PS4 controller found")
            return

        # Clear existing state
        self.button_state.clear()
        self.axis_state.clear()

        # Initialize default state for buttons (all released)
        for btn_code, btn_name in self.BUTTON_NAMES.items():
            self.button_state[btn_name] = False

        # Initialize default state for axes (all centered)
        for axis_code, axis_name in self.AXIS_NAMES.items():
            self.axis_state[axis_name] = 0.0

        # Start event polling thread
        self.running = True
        if self.event_thread and self.event_thread.is_alive():
            # Thread already running
            pass
        else:
            self.event_thread = threading.Thread(target=self._poll_events, daemon=True)
            self.event_thread.start()

        self.is_capturing = True

        if self.verbose:
            print(f"Started capturing events from controller: {self.controller_name}")

    def stop_capture(self) -> None:
        """
        Stop capturing input events from the PS4 controller.

        Stops the event polling thread and closes the controller.
        """
        if not self.is_capturing:
            return

        # Signal the thread to stop
        self.running = False

        # Wait for the thread to finish
        if self.event_thread and self.event_thread.is_alive():
            self.event_thread.join(timeout=1.0)

        self.is_capturing = False

        if self.verbose:
            print("Stopped capturing controller events")

    def _poll_events(self) -> None:
        """
        Poll SDL events in a separate thread.

        This method runs in a separate thread and continuously polls
        SDL events, processes them, and generates InputData events.
        """
        try:
            event = SDL_Event()

            while self.running:
                # Process all pending events
                while SDL_PollEvent(ctypes.byref(event)) != 0:
                    try:
                        if event.type == SDL_CONTROLLERBUTTONDOWN:
                            self._handle_button_event(event.cbutton.button, True)
                        elif event.type == SDL_CONTROLLERBUTTONUP:
                            self._handle_button_event(event.cbutton.button, False)
                        elif event.type == SDL_CONTROLLERAXISMOTION:
                            self._handle_axis_event(event.caxis.axis, event.caxis.value)
                        elif event.type == SDL_CONTROLLERDEVICEADDED:
                            # Controller was connected
                            if not self.controller:
                                index = event.cdevice.which
                                print(f"Controller connected at index {index}")
                                self.connect_to_controller(index)
                        elif event.type == SDL_CONTROLLERDEVICEREMOVED:
                            joystick_id = event.cdevice.which
                            if (
                                self.controller
                                and joystick_id
                                == SDL_JoystickInstanceID(
                                    SDL_GameControllerGetJoystick(self.controller)
                                )
                            ):
                                # Our controller was disconnected
                                print("Controller disconnected")
                                SDL_GameControllerClose(self.controller)
                                self.controller = None
                                self.controller_name = "Disconnected"
                    except Exception as e:
                        print(f"Error processing SDL event: {e}")

                # Short sleep to avoid consuming too much CPU
                time.sleep(0.01)

        except Exception as e:
            print(f"Error in SDL event polling thread: {e}")
            import traceback

            traceback.print_exc()

    def _handle_button_event(self, button_code: int, pressed: bool) -> None:
        """
        Handle a controller button event.

        Args:
            button_code: SDL button code
            pressed: True if the button was pressed, False if released
        """
        # Get button name
        button_name = self.BUTTON_NAMES.get(button_code)
        if not button_name:
            # Unknown button
            return

        # Update button state
        old_state = self.button_state.get(button_name, False)
        if old_state == pressed:
            # State didn't change (possibly repeating event)
            return

        self.button_state[button_name] = pressed

        # Create event
        now = time.time()
        event = InputData(
            timestamp=now,
            event_type="button_press" if pressed else "button_release",
            key=button_name,
            active_keys=self.get_active_keys(),
        )

        # Process event
        self._process_event(event)

    def _handle_axis_event(self, axis_code: int, value: int) -> None:
        """
        Handle a controller axis event.

        Args:
            axis_code: SDL axis code
            value: Axis value (-32768 to 32767)
        """
        # Get axis name
        axis_name = self.AXIS_NAMES.get(axis_code)
        if not axis_name:
            # Unknown axis
            return

        # Normalize value to -1.0 to 1.0
        normalized_value = value / 32767.0 if value > 0 else value / 32768.0

        # Apply a small deadzone to avoid drift
        if abs(normalized_value) < 0.1:
            normalized_value = 0.0

        # Update axis state
        old_value = self.axis_state.get(axis_name, 0.0)
        if abs(old_value - normalized_value) < 0.05:
            # Too small a change to report
            return

        self.axis_state[axis_name] = normalized_value

        # Create event
        now = time.time()
        event = InputData(
            timestamp=now,
            event_type="axis_motion",
            key=axis_name,
            rel_x=normalized_value if "X" in axis_name else None,
            rel_y=normalized_value if "Y" in axis_name else None,
            active_keys=self.get_active_keys(),
        )

        # For joystick inputs, create direction info for visualization
        if "Stick" in axis_name:
            # Calculate stick position and direction
            if "X" in axis_name:
                # X axis - set horizontal direction
                base_name = axis_name.replace("_X", "")
                y_axis = f"{base_name}_Y"
                y_value = self.axis_state.get(y_axis, 0.0)

                # Calculate direction
                event.rel_x = normalized_value
                event.rel_y = y_value
                event.is_moving = abs(normalized_value) > 0.1 or abs(y_value) > 0.1

                # Calculate direction string (X+, X-, Y+, Y-, etc.)
                direction_parts = []
                if abs(normalized_value) > 0.1:
                    direction_parts.append("X+" if normalized_value > 0 else "X-")
                if abs(y_value) > 0.1:
                    direction_parts.append("Y+" if y_value > 0 else "Y-")

                event.direction = "".join(direction_parts) if direction_parts else None

                # Calculate magnitude
                event.speed = (
                    math.sqrt(normalized_value**2 + y_value**2)
                    if event.is_moving
                    else 0
                )

        # For trigger inputs (L2/R2), treat them specially
        if "Trigger" in axis_name:
            # Map trigger from 0.0 to 1.0 (instead of -1.0 to 1.0)
            trigger_value = (normalized_value + 1.0) / 2.0

            # Update the event
            if trigger_value > 0.1:  # Small deadzone for triggers
                # Add the trigger to active keys if it's pressed significantly
                if trigger_value > 0.5 and axis_name not in event.active_keys:
                    event.active_keys.append(axis_name)

            event.rel_x = (
                trigger_value  # Store trigger value in rel_x for visualization
            )

        # Process the event
        self._process_event(event)

    def _process_event(self, event: InputData) -> None:
        """
        Process a controller event.

        Args:
            event: The input event to process
        """
        # Store event
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]

        # Also store in keyboard_events and mouse_events for compatibility
        self.keyboard_events = self.events.copy()
        self.mouse_events = self.events.copy()

        # Notify callbacks
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in controller event callback: {e}")

    def get_input_event(self) -> InputData:
        """
        Get the most recent input event.

        Returns:
            InputData: The most recent input event, or a placeholder event if no events exist
        """
        if not self.events:
            return InputData(
                timestamp=time.time(),
                event_type="none",
                active_keys=self.get_active_keys(),
            )

        return self.events[-1]

    def get_active_keys(self) -> List[str]:
        """
        Get a list of currently active buttons.

        Returns:
            List[str]: List of active buttons
        """
        try:
            # Add pressed buttons
            active_keys = [btn for btn, pressed in self.button_state.items() if pressed]

            # Add significantly pressed triggers
            for axis_name, value in self.axis_state.items():
                if "Trigger" in axis_name and value > 0.5:
                    active_keys.append(axis_name)

            return active_keys
        except Exception as e:
            # Handle errors safely
            print(f"Error in get_active_keys: {e}")
            return []

    def on_event(self, callback: Callable[[InputData], None]) -> None:
        """
        Register a callback for input events.

        Args:
            callback: Function to be called when a new input event is processed
        """
        self.event_callbacks.append(callback)

    def remove_event_handler(self, callback: Callable[[InputData], None]) -> None:
        """
        Remove a previously registered event handler.

        Args:
            callback: The callback function to remove
        """
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)

    def set_supported_keys(self, keys: List[str]) -> None:
        """
        Set the inputs to be tracked by the collector.

        Args:
            keys: List of input names to track
        """
        self.supported_inputs = keys

    def get_events_since(self, timestamp: float) -> List[InputData]:
        """
        Get all events since a specific timestamp.

        Args:
            timestamp: Time (in seconds since epoch) to retrieve events from

        Returns:
            List[InputData]: List of input events that occurred since the given timestamp
        """
        return [e for e in self.events if e.timestamp >= timestamp]

    def clear_events(self) -> None:
        """
        Clear all stored events.

        Removes all events from the collector's event history while
        maintaining the current input state.
        """
        self.events.clear()
        self.keyboard_events.clear()
        self.mouse_events.clear()

    def __del__(self) -> None:
        """
        Cleanup SDL resources when the object is destroyed.
        """
        # Stop capturing
        self.stop_capture()

        # Close controller
        if hasattr(self, "controller") and self.controller:
            try:
                SDL_GameControllerClose(self.controller)
            except:
                pass
            self.controller = None

        # Destroy window if we created one
        if hasattr(self, "window") and self.window:
            try:
                SDL_DestroyWindow(self.window)
            except:
                pass
            self.window = None

        # Quit SDL
        if hasattr(self, "sdl_initialized") and self.sdl_initialized:
            try:
                SDL_Quit()
            except:
                pass
            self.sdl_initialized = False


# Simple utility function to check if SDL2 is available
def is_sdl2_available() -> bool:
    """
    Check if SDL2 is available.

    Returns:
        bool: True if SDL2 is available, False otherwise
    """
    try:
        from sdl2 import SDL_Init, SDL_Quit, SDL_INIT_GAMECONTROLLER

        # Try a minimal initialization to verify it works
        try:
            result = SDL_Init(SDL_INIT_GAMECONTROLLER)
            if result == 0:
                SDL_Quit()
                return True
        except:
            pass
        return False
    except ImportError:
        return False
