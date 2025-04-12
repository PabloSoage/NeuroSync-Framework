from pynput import keyboard, mouse
import time
import math
import threading
from ..interfaces import InputData, AbstractInputCollector
from typing import List, Dict, Optional, Callable, Set, Tuple

class KeyboardMouseCollector(AbstractInputCollector):
    """Collects keyboard and mouse input events using pynput"""
    
    def __init__(self):
        # Events storage
        self.keyboard_events: List[InputData] = []
        self.mouse_events: List[InputData] = []
        
        # Default supported keys - updated with requested keys
        self.supported_keys: List[str] = [
            "w", "a", "s", "d", "q", "e", "f", "m", "c", "b",
            "1", "2", "3", "4",
            "Key.space", "Key.shift",
            "Key.media_play_pause"  # Only track media play/pause key, not F9 itself
        ]
        
        # State tracking
        self.is_capturing: bool = False
        self.event_callbacks: List[Callable[[InputData], None]] = []
        
        # Key state tracking
        self.key_state: Dict[str, bool] = {}
        
        # Mouse state tracking
        self.mouse_state = {
            'last_time': time.time(),
            'last_x': 0,
            'last_y': 0,
            'movement_direction': None,
            'speed': 0,
            'speed_x': 0,
            'speed_y': 0,
            'is_moving': False,
            'movement_threshold': 1.0,
            'click_left': False,
            'click_right': False,
            'wheel_up': False,
            'wheel_down': False,
            'center_x': None,
            'center_y': None,
            'rel_x': 0,
            'rel_y': 0,
            # Add velocity tracking for better joystick behavior
            'velocity_x': 0,
            'velocity_y': 0,
            # Velocity history for smoothing
            'velocity_history_x': [0] * 5,
            'velocity_history_y': [0] * 5
        }
        
        # Screen metrics for velocity scaling
        self.screen_width = 1920
        self.screen_height = 1080
        
        # Velocity to joystick mapping parameters (no longer DPI dependent)
        self.max_velocity = 1000  # pixels per second
        self.velocity_smoothing = 0.7  # Higher = more smoothing
        
        # Critical missing attributes
        self.last_mouse_event_time = time.time()
        self.mouse_throttle_interval = 0.010  # 100fps update rate
        self.last_reset_time = time.time()
        self.max_events = 50
        self.wheel_reset_timer = None
        
        # Tracked keys set for efficient lookup
        self.tracked_keys_set = set(k.lower() for k in self.supported_keys)
        
        # Listener references
        self.keyboard_listener = None
        self.mouse_listener = None
        
        # Add a flag to track if F9 was just pressed to prevent multiple events
        self.f9_just_pressed = False
        
        # Track F9 key's state separately from other keys to prevent accidental toggling
        self.f9_key_state = False
        
        # Debug flag to control verbose logging output
        self.verbose = False
        
        # Start keyboard listener immediately for F9 control
        self.start_listeners()
    
    def start_listeners(self):
        """Start keyboard and mouse listeners - separated for reuse"""
        # Make sure we don't have duplicates
        self.stop_listeners()
        
        # Start keyboard listener - always running for F9 support
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release,
            suppress=False
        )
        
        # Start mouse listener only if we're capturing
        if self.is_capturing:
            self.mouse_listener = mouse.Listener(
                on_move=self.on_move,
                on_click=self.on_click,
                on_scroll=self.on_scroll,
                suppress=False
            )
            self.mouse_listener.daemon = True
            self.mouse_listener.start()
        
        # Always start keyboard listener for F9 support
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()
        
        if self.verbose:
            print(f"Listeners started - keyboard: {self.keyboard_listener}, mouse: {self.mouse_listener}")
    
    def stop_listeners(self):
        """Stop existing listeners if any"""
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
    
    def on_press(self, key):
        """Handle key press events"""
        try:
            # Convert key to string representation with consistent naming
            if key == keyboard.Key.space:
                key_str = "Key.space"  # Always use Key.space for consistency
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
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
                        print(f"F9 key PRESS detected - creating toggle_recording event - current capturing={self.is_capturing}")
                    
                    # Create the special toggle event with explicit flag to force the action
                    media_event = InputData(
                        timestamp=time.time(),
                        event_type="toggle_recording",  # Special event type for toggle action
                        key="Key.media_play_pause",
                        active_keys=self.get_active_keys()
                    )
                    
                    # Process this event immediately with high priority 
                    self._process_event(media_event)
                    
                # Don't continue processing F9 as a regular key
                return True
            elif key == keyboard.Key.esc:
                key_str = "Key.esc"  # Explicitly name ESC key
            elif hasattr(key, 'char'):
                key_str = key.char.lower()  # Lowercase for consistency
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
                    active_keys=self.get_active_keys()
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
            elif any(special_key in key_str.lower() for special_key in ["key.shift", "key.space"]):
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
                        mouse_x=self.mouse_state['last_x'],
                        mouse_y=self.mouse_state['last_y'],
                        direction=self.mouse_state['movement_direction'],
                        speed=self.mouse_state['speed'],
                        speed_x=self.mouse_state['speed_x'],
                        speed_y=self.mouse_state['speed_y'],
                        rel_x=self.mouse_state['rel_x'],
                        rel_y=self.mouse_state['rel_y'],
                        is_moving=self.mouse_state['is_moving']
                    )
                    
                    # Process event directly
                    self._process_event(event)
                
        except Exception as e:
            print(f"Key press error: {e}")
        
        return True  # Continue listening
    
    def on_release(self, key):
        """Handle key release events"""
        try:
            # Convert key to string representation with consistent naming
            if key == keyboard.Key.space:
                key_str = "Key.space"
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                key_str = "Key.shift"
            elif key == keyboard.Key.media_play_pause:
                key_str = "Key.media_play_pause"
            elif key == keyboard.Key.f9:
                key_str = "Key.f9"
            elif hasattr(key, 'char'):
                key_str = key.char.lower()
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
            elif any(special_key in key_str.lower() for special_key in ["key.shift", "key.space"]):
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
                    active_keys=active_keys
                )
                
                # Process event directly
                self._process_event(event)
                    
        except Exception as e:
            print(f"Key release error: {e}")
        
        return True  # Continue listening

    def on_move(self, x, y):
        """Velocity-based mouse movement handler with independent velocity tracking"""
        try:
            current_time = time.time()
            
            # Minimal throttling for responsiveness
            if current_time - self.last_mouse_event_time < self.mouse_throttle_interval:
                return
            
            # Calculate time since last update
            delta_time = current_time - self.last_mouse_event_time
            self.last_mouse_event_time = current_time
            
            # Initialize center coordinates if needed
            if self.mouse_state['center_x'] is None:
                self.mouse_state['center_x'] = self.screen_width / 2
                self.mouse_state['center_y'] = self.screen_height / 2
                self.mouse_state['last_x'] = x
                self.mouse_state['last_y'] = y
                self.mouse_state['last_time'] = current_time
                return  # Skip first reading as we have no velocity yet
            
            # Calculate real movements in pixels
            x_move = x - self.mouse_state['last_x']
            y_move = y - self.mouse_state['last_y']
            
            # Avoid division by zero
            if delta_time < 0.001:
                delta_time = 0.001
                
            # Calculate raw instantaneous velocity in pixels per second
            # This is the actual physical movement speed of the mouse cursor
            inst_velocity_x = x_move / delta_time
            inst_velocity_y = y_move / delta_time
            
            # Update velocity history
            self.mouse_state['velocity_history_x'].pop(0)
            self.mouse_state['velocity_history_x'].append(inst_velocity_x)
            self.mouse_state['velocity_history_y'].pop(0)
            self.mouse_state['velocity_history_y'].append(inst_velocity_y)
            
            # Apply exponential smoothing to velocity
            # This gives more weight to recent movements while smoothing jitter
            smooth_factor = self.velocity_smoothing
            prev_velocity_x = self.mouse_state['velocity_x']
            prev_velocity_y = self.mouse_state['velocity_y']
            
            # Calculate smoothed velocity (pixels per second)
            velocity_x = prev_velocity_x * smooth_factor + inst_velocity_x * (1 - smooth_factor)
            velocity_y = prev_velocity_y * smooth_factor + inst_velocity_y * (1 - smooth_factor)
            
            # Update state with new velocity
            self.mouse_state['velocity_x'] = velocity_x
            self.mouse_state['velocity_y'] = velocity_y
            
            # Calculate speed metrics (pixels per second)
            speed_x = abs(velocity_x)
            speed_y = abs(velocity_y)
            speed = math.sqrt(velocity_x**2 + velocity_y**2)
            
            # Determine if mouse is actually moving based on physical velocity
            is_moving = speed > 20  # pixels per second
            
            # Calculate joystick position - SEPARATE from velocity tracking
            velocity_magnitude = math.sqrt(velocity_x**2 + velocity_y**2)
            scaling_factor = min(1.0, velocity_magnitude / self.max_velocity)
            
            # If we have meaningful velocity, calculate joystick position vector
            if (velocity_magnitude > 10):  # Minimal threshold to filter noise
                # Normalize velocity vector and scale by velocity magnitude
                rel_x = (velocity_x / velocity_magnitude) * scaling_factor
                rel_y = (velocity_y / velocity_magnitude) * scaling_factor
            else:
                # No significant movement, center the joystick
                rel_x = 0
                rel_y = 0
            
            # Determine movement direction based on velocity components
            direction = None
            if is_moving:
                direction_parts = []
                if abs(velocity_x) > 20:  # Threshold for directional indicator
                    direction_parts.append("X+" if velocity_x > 0 else "X-")
                if abs(velocity_y) > 20:
                    direction_parts.append("Y+" if velocity_y > 0 else "Y-")
                direction = "".join(direction_parts) if direction_parts else None
            
            # Check if state changed from moving to not moving
            state_changed = self.mouse_state['is_moving'] != is_moving
            
            # Update state
            self.mouse_state['is_moving'] = is_moving
            self.mouse_state['last_x'] = x
            self.mouse_state['last_y'] = y
            self.mouse_state['last_time'] = current_time
            self.mouse_state['movement_direction'] = direction
            self.mouse_state['rel_x'] = rel_x
            self.mouse_state['rel_y'] = rel_y
            self.mouse_state['speed'] = speed
            self.mouse_state['speed_x'] = speed_x
            self.mouse_state['speed_y'] = speed_y
            
            # Get currently active keys - make sure to always include in events
            active_keys = self.get_active_keys()
            
            # Create event with complete information, including button states
            active_keys = self.get_active_keys()
            
            # Determine which mouse buttons are currently pressed
            button_pressed = None
            if self.mouse_state['click_left']:
                button_pressed = "Button.left"
            elif self.mouse_state['click_right']:
                button_pressed = "Button.right"
            
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
                button_pressed=button_pressed,  # Include currently pressed button
                active_keys=active_keys
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
    
    def _reset_mouse_state(self, x, y):
        """Reset mouse velocity and state"""
        current_time = time.time()
        
        # Avoid resetting too frequently
        if current_time - self.last_reset_time < 0.2:
            return
        
        self.last_reset_time = current_time
        
        # Reset state
        self.mouse_state['is_moving'] = False
        self.mouse_state['movement_direction'] = None
        self.mouse_state['rel_x'] = 0.0
        self.mouse_state['rel_y'] = 0.0
        self.mouse_state['speed'] = 0.0
        self.mouse_state['speed_x'] = 0.0
        self.mouse_state['speed_y'] = 0.0
        
        # Reset velocity
        self.mouse_state['velocity_x'] = 0.0
        self.mouse_state['velocity_y'] = 0.0
        self.mouse_state['velocity_history_x'] = [0] * 5
        self.mouse_state['velocity_history_y'] = [0] * 5
        
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
            active_keys=active_keys
        )
        self._process_event(reset_event)

    def on_click(self, x, y, button, pressed):
        """Handle mouse click events"""
        try:
            # Determine button type
            if button == mouse.Button.left:
                button_str = "Button.left"
                self.mouse_state['click_left'] = pressed
            elif button == mouse.Button.right:
                button_str = "Button.right"
                self.mouse_state['click_right'] = pressed
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
                rel_x=self.mouse_state['rel_x'],
                rel_y=self.mouse_state['rel_y'],
                direction=self.mouse_state['movement_direction'],
                speed=self.mouse_state['speed'],
                speed_x=self.mouse_state['speed_x'],
                speed_y=self.mouse_state['speed_y'],
                is_moving=self.mouse_state['is_moving'],
                active_keys=active_keys
            )
            
            # Process event
            self._process_event(event)
                
        except Exception as e:
            print(f"Mouse click error: {e}")

    def on_scroll(self, x, y, dx, dy):
        """Handle mouse scroll events"""
        try:
            # Determine scroll direction
            scroll_direction = None
            if dy > 0:
                scroll_direction = "up"
                self.mouse_state['wheel_up'] = True
                self.mouse_state['wheel_down'] = False
            elif dy < 0:
                scroll_direction = "down"
                self.mouse_state['wheel_down'] = True
                self.mouse_state['wheel_up'] = False
            
            # Get currently active keys
            active_keys = self.get_active_keys()
            
            # Create a unified event that includes mouse movement information
            # This ensures scroll events have complete mouse state
            event = InputData(
                timestamp=time.time(),
                event_type="mouse_scroll",
                mouse_x=x,
                mouse_y=y,
                direction=scroll_direction,
                rel_x=self.mouse_state['rel_x'],
                rel_y=self.mouse_state['rel_y'],
                speed=self.mouse_state['speed'],
                speed_x=self.mouse_state['speed_x'],
                speed_y=self.mouse_state['speed_y'],
                is_moving=self.mouse_state['is_moving'],
                active_keys=active_keys
            )
            
            # Process event
            self._process_event(event)
            
            # Schedule wheel reset
            if self.wheel_reset_timer:
                self.wheel_reset_timer.cancel()
                
            self.wheel_reset_timer = threading.Timer(0.1, lambda: self._reset_wheel(x, y))
            self.wheel_reset_timer.daemon = True
            self.wheel_reset_timer.start()
                
        except Exception as e:
            print(f"Mouse scroll error: {e}")
    
    def _reset_wheel(self, x, y):
        """Reset wheel state and create a visual reset event"""
        try:
            if self.mouse_state['wheel_up'] or self.mouse_state['wheel_down']:
                self.mouse_state['wheel_up'] = False
                self.mouse_state['wheel_down'] = False
                
                # Create a reset event specifically for visual feedback
                reset_event = InputData(
                    timestamp=time.time(),
                    event_type="mouse_scroll",
                    mouse_x=x,
                    mouse_y=y,
                    direction=None,
                    rel_x=self.mouse_state['rel_x'],
                    rel_y=self.mouse_state['rel_y'],
                    active_keys=self.get_active_keys()
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
    
    def _process_event(self, event: InputData):
        """Process a single event - combine mouse and keyboard information"""
        # Make sure event always includes current active keys
        if not hasattr(event, 'active_keys') or event.active_keys is None:
            event.active_keys = self.get_active_keys()
        else:
            # Replace with the full and current list
            event.active_keys = self.get_active_keys()
        
        # Store only one combined list of events - no separation by type
        # We don't store key_release events (as per requirement #2)
        if event.event_type != "key_release":
            self.mouse_events.append(event)
            if len(self.mouse_events) > self.max_events:
                self.mouse_events = self.mouse_events[-self.max_events:]

            # Keep keyboard_events in sync, but we'll primarily use mouse_events
            # This maintains compatibility with existing code that expects both
            self.keyboard_events = self.mouse_events.copy()
            
        # Immediately notify callbacks for real-time processing
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def start_capture(self):
        """Start capturing input events"""
        if self.is_capturing:
            return
        
        self.is_capturing = True
        
        # Start/restart listeners to ensure mouse is captured
        self.start_listeners()
        
        if self.verbose:
            print("Input capturing started with full keyboard and mouse monitoring")
    
    def stop_capture(self):
        """Stop capturing input events"""
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
            print("Input capturing stopped, but keyboard listener remains for F9 monitoring")
    
    def get_input_event(self) -> InputData:
        """Get the most recent input event"""
        # Only use mouse_events since they now include all event types
        if not self.mouse_events:
            # Create a blank event with current active keys
            return InputData(
                timestamp=time.time(),
                event_type="none",
                active_keys=self.get_active_keys()
            )
        
        # Return the most recent event
        return self.mouse_events[-1]
    
    def get_active_keys(self) -> List[str]:
        """Get currently pressed keys - filtered to only include tracked keys"""
        # Only return keys that are both pressed AND in the tracked keys set
        active_keys = []
        for k, v in self.key_state.items():
            if v:  # If key is pressed
                # Only include keys that are explicitly tracked
                if k.lower() in self.tracked_keys_set:
                    active_keys.append(k)
                # Or special keys that need partial matching
                elif any(special_key in k.lower() for special_key in ["key.shift", "key.space"]):
                    for tracked_key in self.tracked_keys_set:
                        if tracked_key in k.lower():
                            active_keys.append(k)
                            break
        return active_keys
    
    def on_event(self, callback: Callable[[InputData], None]):
        """Register a callback for input events"""
        self.event_callbacks.append(callback)
    
    def set_supported_keys(self, keys: List[str]):
        """Set the keys to be tracked by the collector"""
        self.supported_keys = keys
        # Update tracked keys set for efficient lookup
        self.tracked_keys_set = set(k.lower() for k in self.supported_keys)
        # Clear key state for keys no longer being tracked
        for key in list(self.key_state.keys()):
            if key.lower() not in self.tracked_keys_set:
                del self.key_state[key]
    
    def get_events_since(self, timestamp: float) -> List[InputData]:
        """Get all events since a specific timestamp"""
        # Only use mouse_events since they now include all event types
        return [e for e in self.mouse_events if e.timestamp >= timestamp]

    def clear_events(self):
        """Clear all stored events"""
        self.keyboard_events.clear()
        self.mouse_events.clear()
    
    def set_screen_dimensions(self, width: int, height: int):
        """Set screen dimensions for velocity calibration"""
        self.screen_width = width
        self.screen_height = height
        self.mouse_state['center_x'] = width / 2
        self.mouse_state['center_y'] = height / 2
        
        # Adjust max velocity based on screen dimensions
        # Decrease the base percentage from 0.4 to 0.25 for less sensitivity
        diagonal = math.sqrt(width**2 + height**2)
        self.max_velocity = diagonal * 0.25  # Reduced from 0.4 for less sensitivity        
        print(f"Screen dimensions set to {width}x{height}, max velocity: {self.max_velocity:.1f} pixels/sec")
    
    def set_joystick_sensitivity(self, sensitivity: float):
        """Set joystick sensitivity (0.1-5.0, LOWER = LESS sensitive)
        This works by dividing the base_velocity by sensitivity:
        - Lower sensitivity values (0.1-0.5) = higher max_velocity = LESS sensitive (harder to reach edge)
        - Higher sensitivity values (1.0-5.0) = lower max_velocity = MORE sensitive (easier to reach edge)
        
        Recommended values:
        - 0.25: Low sensitivity (harder to reach edge) - good for precise control
        - 1.0: Medium sensitivity
        - 3.0: High sensitivity (easier to reach edge) - good for quick movements
        """
        if 0.1 <= sensitivity <= 5.0:
            # Adjust max_velocity inversely with sensitivity
            base_velocity = math.sqrt(self.screen_width**2 + self.screen_height**2) * 0.25
            self.max_velocity = base_velocity / sensitivity
            print(f"Joystick sensitivity set to {sensitivity}, max velocity: {self.max_velocity:.1f} pixels/sec")
        else:
            print(f"Sensitivity must be between 0.1 and 5.0, got {sensitivity}")
    
    def __del__(self):
        """Ensure resources are cleaned up"""
        self.stop_listeners()