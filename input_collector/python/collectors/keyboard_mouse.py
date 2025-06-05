"""
Keyboard and mouse input collection module.

This module provides functionality for capturing and processing keyboard and mouse
input events using pynput, with support for velocity-based joystick-like representation
of mouse movement.
"""

import math
import threading
import time
from typing import List, Dict, Optional, Callable, Set, Any

from pynput import keyboard, mouse

from ..interfaces import InputData, AbstractInputCollector


class KeyboardMouseCollector(AbstractInputCollector):
    """
    Collects keyboard and mouse input events using pynput.

    This class captures keyboard and mouse events from the system, processes them,
    and provides a unified interface for accessing input state. It includes advanced
    features like velocity-based mouse tracking, joystick-like movement representation,
    and key state tracking.
    """

    def __init__(self) -> None:
        """
        Initialize the keyboard and mouse collector.

        Sets up internal state tracking, event buffering, and prepares listeners
        for capturing keyboard and mouse events.
        """
        # Events storage
        self.keyboard_events: List[InputData] = []
        self.mouse_events: List[InputData] = []

        # Default supported keys - updated with requested keys
        self.supported_keys: List[str] = [
            "w",
            "a",
            "s",
            "d",
            "q",
            "e",
            "f",
            "m",
            "c",
            "b",
            "1",
            "2",
            "3",
            "4",
            "Key.space",
            "Key.shift",
            "Key.media_play_pause",  # Only track media play/pause key, not F9 itself
        ]

        # State tracking
        self.is_capturing: bool = False
        self.event_callbacks: List[Callable[[InputData], None]] = []

        # Key state tracking
        self.key_state: Dict[str, bool] = {}

        # Mouse state tracking
        self.mouse_state: Dict[str, Any] = {
            "last_time": time.time(),
            "last_x": 0,
            "last_y": 0,
            "movement_direction": None,
            "speed": 0,
            "speed_x": 0,
            "speed_y": 0,
            "is_moving": False,
            "movement_threshold": 1.0,
            "click_left": False,  # State of left mouse button
            "click_right": False,  # State of right mouse button
            "wheel_up": False,
            "wheel_down": False,
            "center_x": None,
            "center_y": None,
            "rel_x": 0,
            "rel_y": 0,
            # Add velocity tracking for better joystick behavior
            "velocity_x": 0,
            "velocity_y": 0,
            # Velocity history for smoothing
            "velocity_history_x": [0] * 5,
            "velocity_history_y": [0] * 5,
            # New tracking fields for delta-based control
            "delta_x": 0,  # Raw mouse movement delta X
            "delta_y": 0,  # Raw mouse movement delta Y
            "delta_magnitude": 0,  # Total movement magnitude
            "delta_angle": 0,  # Movement angle in degrees
            "delta_history_x": [0] * 3,  # Shorter history for deltas
            "delta_history_y": [0] * 3,  # Shorter history for deltas
            "delta_smoothing": 0.5,  # Smoothing factor for delta movements
        }

        # Screen metrics for velocity scaling
        self.screen_width: int = 1920
        self.screen_height: int = 1080

        # Velocity to joystick mapping parameters (no longer DPI dependent)
        self.max_velocity: float = 1000  # pixels per second
        self.velocity_smoothing: float = 0.7  # Higher = more smoothing

        # Critical missing attributes
        self.last_mouse_event_time: float = time.time()
        self.mouse_throttle_interval: float = 0.010  # 100fps update rate
        self.last_reset_time: float = time.time()
        self.max_events: int = 50
        self.wheel_reset_timer: Optional[threading.Timer] = None

        # Tracked keys set for efficient lookup
        self.tracked_keys_set: Set[str] = set(k.lower() for k in self.supported_keys)

        # Listener references
        self.keyboard_listener: Optional[keyboard.Listener] = None
        self.mouse_listener: Optional[mouse.Listener] = None

        # Add a flag to track if F9 was just pressed to prevent multiple events
        self.f9_just_pressed: bool = False

        # Track F9 key's state separately from other keys to prevent accidental toggling
        self.f9_key_state: bool = False

        # Debug flag to control verbose logging output
        self.verbose: bool = False

        # Start keyboard listener immediately for F9 control
        self.start_listeners()

        # Tracking mode
        self.mouse_tracking_mode = "joystick"  # "joystick", "delta", "angle", or "axis"

        # Direction-only mode flag and settings
        self.direction_only = True  # Default to direction-only mode
        self.angle_grouping = 10  # Default to 10-degree grouping (36 values)

        # Add fields for direction-only modes
        self.mouse_state["discrete_angle"] = (
            0  # Discretized angle for direction-only mode
        )
        self.mouse_state["north"] = 0.0  # Membership value for north (0.0 to 1.0)
        self.mouse_state["south"] = 0.0  # Membership value for south (0.0 to 1.0)
        self.mouse_state["east"] = 0.0  # Membership value for east (0.0 to 1.0)
        self.mouse_state["west"] = 0.0  # Membership value for west (0.0 to 1.0)

    def start_listeners(self) -> None:
        """
        Start keyboard and mouse listeners.

        Creates and starts the keyboard and mouse listeners to capture input events.
        The keyboard listener is always started for F9 support, while the mouse
        listener is only started if capture is enabled.
        """
        # Make sure we don't have duplicates
        self.stop_listeners()

        # Start keyboard listener - always running for F9 support
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press, on_release=self.on_release, suppress=False
        )

        # Start mouse listener only if we're capturing
        if self.is_capturing:
            self.mouse_listener = mouse.Listener(
                on_move=self.on_move,
                on_click=self.on_click,
                on_scroll=self.on_scroll,
                suppress=False,
            )
            self.mouse_listener.daemon = True
            self.mouse_listener.start()

        # Always start keyboard listener for F9 support
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()

        if self.verbose:
            print(
                f"Listeners started - keyboard: {self.keyboard_listener}, mouse: {self.mouse_listener}"
            )

    def stop_listeners(self) -> None:
        """
        Stop existing listeners.

        Stops and cleans up any active keyboard and mouse listeners,
        and cancels any pending timers.
        """
        # Stop keyboard listener if running
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None

        # Stop mouse listener if running
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None

        # Cancel any timers
        if self.wheel_reset_timer:
            self.wheel_reset_timer.cancel()
            self.wheel_reset_timer = None

    def on_press(self, key: Any) -> bool:
        """
        Handle key press events.

        Processes keyboard press events, normalizes key representation,
        and creates InputData events accordingly.

        Args:
            key: The key that was pressed (as provided by pynput)

        Returns:
            bool: True to continue listening, False to stop
        """
        try:
            # Convert key to string representation with consistent naming
            if key == keyboard.Key.space:
                key_str = "Key.space"  # Always use Key.space for consistency
            elif (
                key == keyboard.Key.shift
                or key == keyboard.Key.shift_l
                or key == keyboard.Key.shift_r
            ):
                key_str = "Key.shift"  # All shift keys are represented as Key.shift
            elif key == keyboard.Key.media_play_pause:
                key_str = "Key.media_play_pause"
            elif key == keyboard.Key.f9:
                # F9 key is special - it's a one-shot toggle button
                # It should ALWAYS work whether recording or not

                # Only respond to initial press, not auto-repeats while held
                if not self.f9_key_state:
                    # Update F9 state to pressed
                    self.f9_key_state = True

                    if self.verbose:
                        print(
                            f"F9 key PRESS detected - creating toggle_recording event - current capturing={self.is_capturing}"
                        )

                    # Create the special toggle event with explicit flag to force the action
                    media_event = InputData(
                        timestamp=time.time(),
                        event_type="toggle_recording",  # Special event type for toggle action
                        key="Key.media_play_pause",
                        active_keys=self.get_active_keys(),
                    )

                    # Process this event immediately with high priority
                    self._process_event(media_event)

                    # FIX: No generar un evento key_press adicional para F9
                    # para evitar que se active el toggle de grabación dos veces
                    return True

                # Don't continue processing F9 as a regular key
                return True
            elif key == keyboard.Key.esc:
                key_str = "Key.esc"  # Explicitly name ESC key
            elif hasattr(key, "char"):
                key_str = (
                    key.char.lower() if key.char else str(key).lower()
                )  # Lowercase for consistency
            else:
                key_str = str(key).lower()  # Lowercase for consistency

            # If we're not recording, only handle F9 key (already handled above)
            if not self.is_capturing:
                return True  # Don't process other keys when not recording

            # Special case for F9 key to generate media_play_pause but not track F9 itself
            if key == keyboard.Key.f9:
                # Create media_play_pause event
                media_event = InputData(
                    timestamp=time.time(),
                    event_type="key_press",
                    key="Key.media_play_pause",
                    active_keys=self.get_active_keys(),
                )
                self._process_event(media_event)
                # Don't continue processing F9 as a tracked key
                return True

            # FIX: STRICT key matching to prevent ESC or other non-tracked keys
            is_tracked = False
            # First, check for exact match in tracked keys set
            if key_str.lower() in self.tracked_keys_set:
                is_tracked = True
            # Then check for special modifier keys with a more limited check pattern
            elif any(
                special_key in key_str.lower()
                for special_key in ["key.shift", "key.space"]
            ):
                # Only these specific special keys get partial matching
                for tracked_key in self.tracked_keys_set:
                    if tracked_key in key_str.lower():
                        is_tracked = True
                        break

            # Only process tracked keys - this check prevents ESC from being logged
            if is_tracked:
                # Update key state if key isn't already pressed
                # Ignore repeat key events for held keys
                if not self.key_state.get(key_str, False):
                    self.key_state[key_str] = True

                    # F9 key also handles as media play/pause
                    if key == keyboard.Key.f9:
                        self.key_state["Key.media_play_pause"] = True

                    # Get active keys (only tracked ones)
                    active_keys = self.get_active_keys()

                    # Create event with precise timestamp
                    # Include complete mouse state information
                    event = InputData(
                        timestamp=time.time(),
                        event_type="key_press",
                        key=key_str,
                        active_keys=active_keys,
                        # Add mouse information to key press events
                        mouse_x=self.mouse_state["last_x"],
                        mouse_y=self.mouse_state["last_y"],
                        direction=self.mouse_state["movement_direction"],
                        speed=self.mouse_state["speed"],
                        speed_x=self.mouse_state["speed_x"],
                        speed_y=self.mouse_state["speed_y"],
                        rel_x=self.mouse_state["rel_x"],
                        rel_y=self.mouse_state["rel_y"],
                        is_moving=self.mouse_state["is_moving"],
                    )

                    # Process event directly
                    self._process_event(event)

        except Exception as e:
            print(f"Key press error: {e}")

        return True  # Continue listening

    def on_release(self, key: Any) -> bool:
        """
        Handle key release events.

        Processes keyboard release events, normalizes key representation,
        and creates InputData events accordingly.

        Args:
            key: The key that was released (as provided by pynput)

        Returns:
            bool: True to continue listening, False to stop
        """
        try:
            # Convert key to string representation with consistent naming
            if key == keyboard.Key.space:
                key_str = "Key.space"
            elif (
                key == keyboard.Key.shift
                or key == keyboard.Key.shift_l
                or key == keyboard.Key.shift_r
            ):
                key_str = "Key.shift"
            elif key == keyboard.Key.media_play_pause:
                key_str = "Key.media_play_pause"
            elif key == keyboard.Key.f9:
                key_str = "Key.f9"
            elif hasattr(key, "char"):
                key_str = key.char.lower() if key.char else str(key).lower()
            else:
                key_str = str(key).lower()

            # Special case for F9 key - just reset its state
            if key == keyboard.Key.f9:
                # Reset F9 state so next press works
                self.f9_key_state = False
                print("F9 key released - state reset for next press")

                # Don't generate any events or continue processing
                return True

            # FIX: STRICT key matching to prevent ESC or other non-tracked keys
            is_tracked = False
            # First, check for exact match in tracked keys set
            if key_str.lower() in self.tracked_keys_set:
                is_tracked = True
            # Then check for special modifier keys with a more limited check pattern
            elif any(
                special_key in key_str.lower()
                for special_key in ["key.shift", "key.space"]
            ):
                # Only these specific special keys get partial matching
                for tracked_key in self.tracked_keys_set:
                    if tracked_key in key_str.lower():
                        is_tracked = True
                        break

            # Only process tracked keys
            if is_tracked:
                # Update key state
                if key_str in self.key_state:
                    self.key_state[key_str] = False

                # If F9 is released, also release media play/pause
                if key == keyboard.Key.f9:
                    if "Key.media_play_pause" in self.key_state:
                        self.key_state["Key.media_play_pause"] = False

                # Get active keys (only tracked ones)
                active_keys = [k for k, v in self.key_state.items() if v]

                # Create event with precise timestamp
                event = InputData(
                    timestamp=time.time(),
                    event_type="key_release",
                    key=key_str,
                    active_keys=active_keys,
                )

                # Process event directly
                self._process_event(event)

        except Exception as e:
            print(f"Key release error: {e}")

        return True  # Continue listening

    def on_move(self, x: int, y: int) -> None:
        """
        Handle mouse movement with multiple tracking modes.
        """
        try:
            current_time = time.time()

            # Minimal throttling for responsiveness
            if current_time - self.last_mouse_event_time < self.mouse_throttle_interval:
                return

            # Calculate time since last update
            delta_time = current_time - self.last_mouse_event_time
            self.last_mouse_event_time = current_time

            # Initialize center coordinates if needed
            if self.mouse_state["center_x"] is None:
                self.mouse_state["center_x"] = self.screen_width / 2
                self.mouse_state["center_y"] = self.screen_height / 2
                self.mouse_state["last_x"] = x
                self.mouse_state["last_y"] = y
                self.mouse_state["last_time"] = current_time
                return  # Skip first reading as we have no velocity yet

            # Calculate raw movements in pixels
            x_move = x - self.mouse_state["last_x"]
            y_move = y - self.mouse_state["last_y"]

            # Avoid division by zero
            if delta_time < 0.001:
                delta_time = 0.001

            # ==== DELTA-BASED TRACKING (FPS style) ====
            # Store raw deltas and update delta history
            self.mouse_state["delta_history_x"].pop(0)
            self.mouse_state["delta_history_x"].append(x_move)
            self.mouse_state["delta_history_y"].pop(0)
            self.mouse_state["delta_history_y"].append(y_move)

            # Apply smoothing to deltas
            smooth_factor = self.mouse_state["delta_smoothing"]
            smoothed_delta_x = sum(self.mouse_state["delta_history_x"]) / len(
                self.mouse_state["delta_history_x"]
            )
            smoothed_delta_y = sum(self.mouse_state["delta_history_y"]) / len(
                self.mouse_state["delta_history_y"]
            )
            self.mouse_state["delta_x"] = smoothed_delta_x
            self.mouse_state["delta_y"] = smoothed_delta_y

            # Calculate delta magnitude and angle
            delta_magnitude = math.sqrt(smoothed_delta_x**2 + smoothed_delta_y**2)
            self.mouse_state["delta_magnitude"] = delta_magnitude

            # Calculate movement angle (0 degrees is right, 90 is down)
            if abs(smoothed_delta_x) > 0.001 or abs(smoothed_delta_y) > 0.001:
                angle = math.degrees(math.atan2(smoothed_delta_y, smoothed_delta_x))
                # Convert to 0-359 range for consistency
                angle = (angle + 360) % 360
                self.mouse_state["delta_angle"] = angle

            # Process direction-only modes
            if self.direction_only:
                # Discretize angle if we have meaningful movement
                if delta_magnitude > 0.5:
                    # Calculate discrete angle based on grouping
                    angle = self.mouse_state["delta_angle"]
                    grouped_angle = (
                        int(round(angle / self.angle_grouping) * self.angle_grouping)
                        % 360
                    )
                    self.mouse_state["discrete_angle"] = grouped_angle

                    # Calculate cardinal direction membership values for axis mode
                    # Convert angle to radians for cosine calculation
                    angle_rad = math.radians(angle)

                    # Calculate membership values for each cardinal direction
                    # North = negative Y, South = positive Y, East = positive X, West = negative X

                    # Calculate raw membership values (using cosine projections)
                    north_value = max(
                        0, -math.cos(angle_rad - math.pi / 2)
                    )  # North is at 270°
                    south_value = max(
                        0, -math.cos(angle_rad + math.pi / 2)
                    )  # South is at 90°
                    east_value = max(0, math.cos(angle_rad))  # East is at 0°
                    west_value = max(0, -math.cos(angle_rad))  # West is at 180°

                    # Normalize so they sum to 1.0
                    total = north_value + south_value + east_value + west_value
                    if total > 0:
                        self.mouse_state["north"] = north_value / total
                        self.mouse_state["south"] = south_value / total
                        self.mouse_state["east"] = east_value / total
                        self.mouse_state["west"] = west_value / total

            # Determine if there's meaningful movement based on delta
            delta_is_moving = delta_magnitude > 0.5  # Very small threshold for deltas

            # ==== JOYSTICK-BASED TRACKING ====
            # Calculate raw instantaneous velocity in pixels per second
            inst_velocity_x = x_move / delta_time
            inst_velocity_y = y_move / delta_time

            # Update velocity history
            self.mouse_state["velocity_history_x"].pop(0)
            self.mouse_state["velocity_history_x"].append(inst_velocity_x)
            self.mouse_state["velocity_history_y"].pop(0)
            self.mouse_state["velocity_history_y"].append(inst_velocity_y)

            # Apply exponential smoothing to velocity
            smooth_factor = self.velocity_smoothing
            prev_velocity_x = self.mouse_state["velocity_x"]
            prev_velocity_y = self.mouse_state["velocity_y"]

            # Calculate smoothed velocity (pixels per second)
            velocity_x = prev_velocity_x * smooth_factor + inst_velocity_x * (
                1 - smooth_factor
            )
            velocity_y = prev_velocity_y * smooth_factor + inst_velocity_y * (
                1 - smooth_factor
            )

            # Update state with new velocity
            self.mouse_state["velocity_x"] = velocity_x
            self.mouse_state["velocity_y"] = velocity_y

            # Calculate speed metrics (pixels per second)
            speed_x = abs(velocity_x)
            speed_y = abs(velocity_y)
            speed = math.sqrt(velocity_x**2 + velocity_y**2)

            # Determine if mouse is actually moving based on physical velocity
            joystick_is_moving = speed > 20  # pixels per second

            # Calculate joystick position - SEPARATE from velocity tracking
            velocity_magnitude = math.sqrt(velocity_x**2 + velocity_y**2)
            scaling_factor = min(1.0, velocity_magnitude / self.max_velocity)

            # If we have meaningful velocity, calculate joystick position vector
            if velocity_magnitude > 10:  # Minimal threshold to filter noise
                # Normalize velocity vector and scale by velocity magnitude
                rel_x = (velocity_x / velocity_magnitude) * scaling_factor
                rel_y = (velocity_y / velocity_magnitude) * scaling_factor
            else:
                # No significant movement, center the joystick
                rel_x = 0
                rel_y = 0

            # ==== DETERMINE MOVEMENT ====
            # Choose which tracking mode to use for this update
            if self.mouse_tracking_mode == "delta":
                is_moving = delta_is_moving
                direction = (
                    self._get_delta_direction()
                )  # Function to determine direction from deltas
            elif self.mouse_tracking_mode == "angle":
                is_moving = (
                    joystick_is_moving  # Use joystick threshold for movement detection
                )
                direction = (
                    self._get_angle_direction()
                )  # Function to convert angle to direction
            else:  # Default joystick mode
                is_moving = joystick_is_moving
                direction = self._get_joystick_direction(velocity_x, velocity_y)

            # Check if state changed from moving to not moving
            state_changed = self.mouse_state["is_moving"] != is_moving

            # Update general state regardless of mode
            self.mouse_state["is_moving"] = is_moving
            self.mouse_state["last_x"] = x
            self.mouse_state["last_y"] = y
            self.mouse_state["last_time"] = current_time
            self.mouse_state["movement_direction"] = direction
            self.mouse_state["rel_x"] = rel_x
            self.mouse_state["rel_y"] = rel_y
            self.mouse_state["speed"] = speed
            self.mouse_state["speed_x"] = speed_x
            self.mouse_state["speed_y"] = speed_y

            # Get currently active keys
            active_keys = self.get_active_keys()

            # Determine which mouse buttons are currently pressed
            button_pressed = None
            if self.mouse_state["click_left"]:
                button_pressed = "Button.left"
            elif self.mouse_state["click_right"]:
                button_pressed = "Button.right"

            # Create event with all tracking data
            event = InputData(
                timestamp=current_time,
                event_type="mouse_move",
                mouse_x=x,
                mouse_y=y,
                direction=direction,
                speed=speed,
                speed_x=speed_x,
                speed_y=speed_y,
                rel_x=rel_x,
                rel_y=rel_y,
                is_moving=is_moving,
                button_pressed=button_pressed,
                active_keys=active_keys,
                # Add additional tracking data fields
                mouse_delta_x=self.mouse_state["delta_x"],
                mouse_delta_y=self.mouse_state["delta_y"],
                mouse_delta_magnitude=self.mouse_state["delta_magnitude"],
                mouse_delta_angle=self.mouse_state["delta_angle"],
                mouse_tracking_mode=self.mouse_tracking_mode,
                # Add direction-only fields
                direction_only=self.direction_only,
                discrete_angle=self.mouse_state["discrete_angle"],
                north=self.mouse_state["north"],
                south=self.mouse_state["south"],
                east=self.mouse_state["east"],
                west=self.mouse_state["west"],
            )

            # Process event
            self._process_event(event)

            # If mouse just stopped moving, reset velocities
            if state_changed and not is_moving:
                self._reset_mouse_state(x, y)

        except Exception as e:
            print(f"Mouse move error: {e}")
            import traceback

            traceback.print_exc()

    def _reset_mouse_state(self, x: int, y: int) -> None:
        """
        Reset mouse velocity and state.

        Resets the mouse movement state when the mouse stops moving.

        Args:
            x: The current x-coordinate of the mouse cursor
            y: The current y-coordinate of the mouse cursor
        """
        current_time = time.time()

        # Avoid resetting too frequently
        if current_time - self.last_reset_time < 0.2:
            return

        self.last_reset_time = current_time

        # Reset state
        self.mouse_state["is_moving"] = False
        self.mouse_state["movement_direction"] = None
        self.mouse_state["rel_x"] = 0.0
        self.mouse_state["rel_y"] = 0.0
        self.mouse_state["speed"] = 0.0
        self.mouse_state["speed_x"] = 0.0
        self.mouse_state["speed_y"] = 0.0

        # Reset velocity
        self.mouse_state["velocity_x"] = 0.0
        self.mouse_state["velocity_y"] = 0.0
        self.mouse_state["velocity_history_x"] = [0] * 5
        self.mouse_state["velocity_history_y"] = [0] * 5

        # Get currently active keys
        active_keys = [k for k, v in self.key_state.items() if v]

        # Send reset event
        reset_event = InputData(
            timestamp=current_time,
            event_type="mouse_move",
            mouse_x=x,
            mouse_y=y,
            direction=None,
            speed=0.0,
            speed_x=0.0,
            speed_y=0.0,
            rel_x=0.0,
            rel_y=0.0,
            is_moving=False,
            active_keys=active_keys,
        )
        self._process_event(reset_event)

    def on_click(self, x: int, y: int, button: Any, pressed: bool) -> None:
        """
        Handle mouse click events.

        Processes mouse button press and release events and creates
        corresponding InputData events.

        Args:
            x: The x-coordinate where the click occurred
            y: The y-coordinate where the click occurred
            button: The mouse button that was pressed/released
            pressed: True if the button was pressed, False if released
        """
        try:
            # Determine button type
            if button == mouse.Button.left:
                button_str = "Button.left"
                self.mouse_state["click_left"] = (
                    pressed  # Updates to True when pressed, False when released
                )
            elif button == mouse.Button.right:
                button_str = "Button.right"
                self.mouse_state["click_right"] = (
                    pressed  # Updates to True when pressed, False when released
                )
            elif button == mouse.Button.middle:
                button_str = "Button.middle"
            else:
                button_str = str(button)

            # Get currently active keys and button state
            active_keys = self.get_active_keys()

            # Create a unified event that includes mouse movement information
            # This ensures click events have complete mouse state
            event = InputData(
                timestamp=time.time(),
                event_type="mouse_click",
                mouse_x=x,
                mouse_y=y,
                button_pressed=button_str if pressed else None,
                rel_x=self.mouse_state["rel_x"],
                rel_y=self.mouse_state["rel_y"],
                direction=self.mouse_state["movement_direction"],
                speed=self.mouse_state["speed"],
                speed_x=self.mouse_state["speed_x"],
                speed_y=self.mouse_state["speed_y"],
                is_moving=self.mouse_state["is_moving"],
                active_keys=active_keys,
            )
            # expose raw button for release tracking
            event.button = button_str

            # Process event
            self._process_event(event)

        except Exception as e:
            print(f"Mouse click error: {e}")

    def on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """
        Handle mouse scroll events.

        Processes mouse wheel scrolling and creates corresponding InputData events.

        Args:
            x: The x-coordinate where the scroll occurred
            y: The y-coordinate where the scroll occurred
            dx: The horizontal scroll amount (unused)
            dy: The vertical scroll amount (positive for scroll up, negative for scroll down)
        """
        try:
            # Check if scroll wheel tracking is enabled
            is_scroll_tracked = (
                "button.scroll" in self.tracked_keys_set
                or "Button.scroll" in self.tracked_keys_set
            )

            # If scroll is not being tracked, completely ignore the event
            if not is_scroll_tracked:
                return

            # Determine scroll direction
            scroll_direction = None
            if dy > 0:
                scroll_direction = "up"
                self.mouse_state["wheel_up"] = True
                self.mouse_state["wheel_down"] = False
            elif dy < 0:
                scroll_direction = "down"
                self.mouse_state["wheel_down"] = True
                self.mouse_state["wheel_up"] = False

            # Get currently active keys
            active_keys = self.get_active_keys()

            # Add Button.scroll to active keys
            if "Button.scroll" not in active_keys:
                active_keys.append("Button.scroll")

            # Create a unified event that includes mouse movement information
            event = InputData(
                timestamp=time.time(),
                event_type="mouse_scroll",
                mouse_x=x,
                mouse_y=y,
                direction=scroll_direction,
                rel_x=self.mouse_state["rel_x"],
                rel_y=self.mouse_state["rel_y"],
                speed=self.mouse_state["speed"],
                speed_x=self.mouse_state["speed_x"],
                speed_y=self.mouse_state["speed_y"],
                is_moving=self.mouse_state["is_moving"],
                active_keys=active_keys,
            )

            # Process event
            self._process_event(event)

            # Schedule wheel reset
            if self.wheel_reset_timer:
                self.wheel_reset_timer.cancel()

            self.wheel_reset_timer = threading.Timer(
                0.1, lambda: self._reset_wheel(x, y)
            )
            self.wheel_reset_timer.daemon = True
            self.wheel_reset_timer.start()

        except Exception as e:
            print(f"Mouse scroll error: {e}")
            import traceback

            traceback.print_exc()

    def _reset_wheel(self, x: int, y: int) -> None:
        """
        Reset wheel state and create a visual reset event.

        Resets the wheel scroll state after a short delay and generates
        a reset event for visualization purposes.

        Args:
            x: The x-coordinate where the scroll occurred
            y: The y-coordinate where the scroll occurred
        """
        try:
            # Only process reset if wheel was previously active
            if self.mouse_state["wheel_up"] or self.mouse_state["wheel_down"]:
                # Reset state
                self.mouse_state["wheel_up"] = False
                self.mouse_state["wheel_down"] = False

                # Check if scroll is tracked
                is_scroll_tracked = (
                    "button.scroll" in self.tracked_keys_set
                    or "Button.scroll" in self.tracked_keys_set
                )

                # Only create reset event if scroll is tracked
                if is_scroll_tracked:
                    # Get currently active keys
                    active_keys = self.get_active_keys()

                    # Add Button.scroll to active keys to ensure the visualizer knows it's still tracked
                    if "Button.scroll" not in active_keys:
                        active_keys.append("Button.scroll")

                    # Create a reset event specifically for visual feedback
                    reset_event = InputData(
                        timestamp=time.time(),
                        event_type="mouse_scroll",
                        mouse_x=x,
                        mouse_y=y,
                        direction=None,
                        rel_x=self.mouse_state["rel_x"],
                        rel_y=self.mouse_state["rel_y"],
                        active_keys=active_keys,  # Use modified active_keys with Button.scroll
                    )
                    # Only notify callbacks, don't store this event
                    for callback in self.event_callbacks:
                        try:
                            callback(reset_event)
                        except Exception as e:
                            print(f"Reset callback error: {e}")

                self.wheel_reset_timer = None
        except Exception as e:
            print(f"Wheel reset error: {e}")

    def _process_event(self, event: InputData) -> None:
        """
        Process a single event - combine mouse and keyboard information.

        Adds the event to the event history and notifies registered callbacks.

        Args:
            event: The input event to process
        """
        # Make sure event always includes current active keys
        if not hasattr(event, "active_keys") or event.active_keys is None:
            event.active_keys = self.get_active_keys()
        else:
            # Replace with the full and current list
            event.active_keys = self.get_active_keys()

        # Store only one combined list of events - no separation by type
        # We don't store key_release events (as per requirement #2)
        if event.event_type != "key_release":
            self.mouse_events.append(event)
            if len(self.mouse_events) > self.max_events:
                self.mouse_events = self.mouse_events[-self.max_events :]

            # Keep keyboard_events in sync, but we'll primarily use mouse_events
            # This maintains compatibility with existing code that expects both
            self.keyboard_events = self.mouse_events.copy()

        # Immediately notify callbacks for real-time processing
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Callback error: {e}")

    def start_capture(self) -> None:
        """
        Start capturing input events.

        Begins the process of capturing input events from the keyboard and mouse.
        Does nothing if capture is already active.
        """
        if self.is_capturing:
            return

        self.is_capturing = True

        # Start/restart listeners to ensure mouse is captured
        self.start_listeners()

        if self.verbose:
            print("Input capturing started with full keyboard and mouse monitoring")

    def stop_capture(self) -> None:
        """
        Stop capturing input events.

        Stops the process of capturing input events from the mouse.
        The keyboard listener remains active for F9 support.
        Does nothing if capture is already stopped.
        """
        if not self.is_capturing:
            return

        self.is_capturing = False

        # Stop mouse listener to avoid unnecessary events
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None

        # Cancel any timers
        if self.wheel_reset_timer:
            self.wheel_reset_timer.cancel()
            self.wheel_reset_timer = None

        if self.verbose:
            print(
                "Input capturing stopped, but keyboard listener remains for F9 monitoring"
            )

    def get_input_event(self) -> InputData:
        """
        Get the most recent input event.

        Returns:
            InputData: The most recent input event, or a placeholder event if no events exist
        """
        # Only use mouse_events since they now include all event types
        if not self.mouse_events:
            # Create a blank event with current active keys
            return InputData(
                timestamp=time.time(),
                event_type="none",
                active_keys=self.get_active_keys(),
            )

        # Return the most recent event
        return self.mouse_events[-1]

    def get_active_keys(self) -> List[str]:
        """
        Get currently pressed keys - filtered to only include tracked keys.

        Returns:
            List[str]: List of currently pressed keys that match the tracked keys list
        """
        # Only return keys that are both pressed AND in the tracked keys set
        active_keys = []
        for k, v in self.key_state.items():
            if v:  # If key is pressed
                # Only include keys that are explicitly tracked
                if k.lower() in self.tracked_keys_set:
                    active_keys.append(k)
                # Or special keys that need partial matching
                elif any(
                    special_key in k.lower()
                    for special_key in ["key.shift", "key.space"]
                ):
                    for tracked_key in self.tracked_keys_set:
                        if tracked_key in k.lower():
                            active_keys.append(k)
                            break
        return active_keys

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

        Updates the list of keys that the collector should track and report.
        Any keys not in this list will be ignored.

        Args:
            keys: List of key identifiers to track
        """
        self.supported_keys = keys
        # Update tracked keys set for efficient lookup
        self.tracked_keys_set = set(k.lower() for k in self.supported_keys)
        # Clear key state for keys no longer being tracked
        for key in list(self.key_state.keys()):
            if key.lower() not in self.tracked_keys_set:
                del self.key_state[key]

    def get_events_since(self, timestamp: float) -> List[InputData]:
        """
        Get all events since a specific timestamp.

        Args:
            timestamp: Time (in seconds since epoch) to retrieve events from

        Returns:
            List[InputData]: List of input events that occurred since the given timestamp
        """
        # Only use mouse_events since they now include all event types
        return [e for e in self.mouse_events if e.timestamp >= timestamp]

    def clear_events(self) -> None:
        """
        Clear all stored events.

        Removes all events from the collector's event history while
        maintaining the current input state.
        """
        self.keyboard_events.clear()
        self.mouse_events.clear()

    def set_screen_dimensions(self, width: int, height: int) -> None:
        """
        Set screen dimensions for velocity calibration.

        Updates the screen dimensions used for velocity calculations and
        joystick position mapping.

        Args:
            width: Screen width in pixels
            height: Screen height in pixels
        """
        self.screen_width = width
        self.screen_height = height
        self.mouse_state["center_x"] = width / 2
        self.mouse_state["center_y"] = height / 2

        # Adjust max velocity based on screen dimensions
        # Decrease the base percentage from 0.4 to 0.25 for less sensitivity
        diagonal = math.sqrt(width**2 + height**2)
        self.max_velocity = diagonal * 0.25  # Reduced from 0.4 for less sensitivity
        print(
            f"Screen dimensions set to {width}x{height}, max velocity: {self.max_velocity:.1f} pixels/sec"
        )

    def set_joystick_sensitivity(self, sensitivity: float) -> None:
        """
        Set joystick sensitivity.

        Adjusts the sensitivity of the joystick-like mouse movement representation.
        Lower values make the joystick less sensitive (harder to reach the edge),
        while higher values make it more sensitive (easier to reach the edge).

        Args:
            sensitivity: Sensitivity value between 0.1 and 5.0
                         - 0.25: Low sensitivity (harder to reach edge)
                         - 1.0: Medium sensitivity
                         - 3.0: High sensitivity (easier to reach edge)
        """
        if 0.1 <= sensitivity <= 5.0:
            # Adjust max_velocity inversely with sensitivity
            base_velocity = (
                math.sqrt(self.screen_width**2 + self.screen_height**2) * 0.25
            )
            self.max_velocity = base_velocity / sensitivity
            print(
                f"Joystick sensitivity set to {sensitivity}, max velocity: {self.max_velocity:.1f} pixels/sec"
            )
        else:
            print(f"Sensitivity must be between 0.1 and 5.0, got {sensitivity}")

    def set_mouse_tracking_mode(
        self, mode: str, direction_only: bool = False, angle_grouping: int = 10
    ) -> None:
        """
        Set which mouse tracking mode to use.

        Args:
            mode: One of "joystick", "delta", "angle", or "axis"
            direction_only: Whether to use direction-only mode
            angle_grouping: Angle grouping in degrees (1-60)
        """
        # Define valid modes based on direction_only flag
        if direction_only:
            valid_modes = ["angle", "axis"]
        else:
            valid_modes = ["joystick", "delta", "angle"]

        if mode not in valid_modes:
            print(f"Invalid mouse tracking mode: {mode}. Must be one of {valid_modes}")
            return

        self.mouse_tracking_mode = mode
        self.direction_only = direction_only

        # Update angle grouping if provided (ensure it's in valid range)
        self.set_angle_grouping(angle_grouping)

        print(
            f"Mouse tracking mode set to {mode}"
            + (f" (direction-only)" if direction_only else "")
            + (
                f" with {self.angle_grouping}° grouping"
                if mode == "angle" and direction_only
                else ""
            )
        )

    def set_angle_grouping(self, grouping: int) -> None:
        """
        Set angle grouping for direction-only angle mode.

        Args:
            grouping: Grouping value in degrees (1-60)
        """
        # Constrain to reasonable range
        grouping = max(1, min(60, grouping))
        self.angle_grouping = grouping
        print(f"Angle grouping set to {grouping}° ({360 // grouping} discrete values)")

    def set_delta_smoothing(self, smoothing: float) -> None:
        """
        Set smoothing factor for delta-based mouse movement.

        Args:
            smoothing: Smoothing factor between 0.0 (no smoothing) and 0.9 (very smooth)
        """
        if 0.0 <= smoothing <= 0.9:
            self.mouse_state["delta_smoothing"] = smoothing
            print(f"Delta smoothing set to {smoothing}")
        else:
            print(f"Smoothing must be between 0.0 and 0.9, got {smoothing}")

    def _get_delta_direction(self) -> Optional[str]:
        """Get direction based on delta movement."""
        delta_x = self.mouse_state["delta_x"]
        delta_y = self.mouse_state["delta_y"]

        # Only report direction if there's significant movement
        if abs(delta_x) < 0.5 and abs(delta_y) < 0.5:
            return None

        direction_parts = []
        if abs(delta_x) > 0.5:
            direction_parts.append("X+" if delta_x > 0 else "X-")
        if abs(delta_y) > 0.5:
            direction_parts.append("Y+" if delta_y > 0 else "Y-")

        return "".join(direction_parts) if direction_parts else None

    def _get_angle_direction(self) -> Optional[str]:
        """Convert angle to cardinal direction."""
        angle = self.mouse_state["delta_angle"]
        magnitude = self.mouse_state["delta_magnitude"]

        # Only report direction if there's significant movement
        if magnitude < 0.5:
            return None

        # Map angle to cardinal directions but use X+/Y- format for consistency
        if -22.5 <= angle <= 22.5:
            return "X+"  # Right (East)
        elif 22.5 < angle <= 67.5:
            return "X+Y+"  # Down-right (Southeast)
        elif 67.5 < angle <= 112.5:
            return "Y+"  # Down (South)
        elif 112.5 < angle <= 157.5:
            return "X-Y+"  # Down-left (Southwest)
        elif angle > 157.5 or angle <= -157.5:
            return "X-"  # Left (West)
        elif -157.5 < angle <= -112.5:
            return "X-Y-"  # Up-left (Northwest)
        elif -112.5 < angle <= -67.5:
            return "Y-"  # Up (North)
        elif -67.5 < angle <= -22.5:
            return "X+Y-"  # Up-right (Northeast)

        return None

    def _get_joystick_direction(
        self, velocity_x: float, velocity_y: float
    ) -> Optional[str]:
        """Get direction based on joystick velocity."""
        # Only report direction if there's significant movement
        if abs(velocity_x) < 20 and abs(velocity_y) < 20:
            return None

        direction_parts = []
        if abs(velocity_x) > 20:
            direction_parts.append("X+" if velocity_x > 0 else "X-")
        if abs(velocity_y) > 20:
            direction_parts.append("Y+" if velocity_y > 0 else "Y-")

        return "".join(direction_parts) if direction_parts else None

    def get_collector_type(self) -> str:
        """
        Get the type of this collector.

        Returns:
            str: The collector type identifier
        """
        return "keyboard_mouse"

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of this collector.

        Returns:
            Dict[str, Any]: Dictionary of collector capabilities
        """
        return {
            "supports_mouse_tracking": True,
            "supports_keyboard": True,
            "supports_mouse_buttons": True,
            "supports_mouse_movement": True,
            "supports_mouse_scroll": True,
            "supports_joystick": True,
            "supported_tracking_modes": ["joystick", "delta", "angle", "axis"],
        }

    def __del__(self) -> None:
        """
        Clean up resources when the object is garbage collected.

        Ensures that all listeners and timers are properly stopped.
        """
        self.stop_listeners()
