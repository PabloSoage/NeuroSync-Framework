"""
Example demonstrating how to access real-time input data.

This script shows how to use the Input Data API to access input events
and state in real-time.
"""

import os
import sys
import time

# Add module to path for imports
current_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_path)

from python.data_access_api import InputDataAPI


def print_input_state():
    """Print the current input state."""
    print("\nCurrent Input State:")
    print("-" * 50)
    
    # Get active keys
    active_keys = InputDataAPI.get_active_keys()
    print(f"Active Keys: {', '.join(active_keys) if active_keys else 'None'}")
    
    # Get mouse position
    mouse_x, mouse_y = InputDataAPI.get_mouse_position()
    print(f"Mouse Position: ({mouse_x}, {mouse_y})")
    
    # Get mouse button states
    left_button = "Pressed" if InputDataAPI.get_mouse_button_state("left") else "Released"
    right_button = "Pressed" if InputDataAPI.get_mouse_button_state("right") else "Released"
    print(f"Mouse Buttons: Left: {left_button}, Right: {right_button}")
    
    # Get mouse movement
    is_moving = InputDataAPI.is_mouse_moving()
    direction = InputDataAPI.get_mouse_direction()
    print(f"Mouse Movement: {'Moving' if is_moving else 'Still'}" + 
          (f" (Direction: {direction})" if direction else ""))
    
    # Get controller info
    if InputDataAPI.is_controller_connected():
        print(f"Controller: {InputDataAPI.get_controller_name()}")
    else:
        print("Controller: Not connected")
    
    print("-" * 50)


def print_recent_events():
    """Print information about recent events."""
    print("\nRecent Events:")
    print("-" * 50)
    
    # Get recent key events
    key_events = InputDataAPI.get_key_events(max_count=3)
    if key_events:
        print(f"Last {len(key_events)} Key Events:")
        for idx, event in enumerate(key_events):
            print(f"  {idx+1}. Type: {event.event_type}, Key: {event.key}, " +
                  f"Time: {event.timestamp:.3f}")
    else:
        print("No recent key events")
    
    # Get recent mouse events
    mouse_events = InputDataAPI.get_mouse_movement_events(max_count=3)
    if mouse_events:
        print(f"\nLast {len(mouse_events)} Mouse Movement Events:")
        for idx, event in enumerate(mouse_events):
            print(f"  {idx+1}. Position: ({event.mouse_x}, {event.mouse_y}), " +
                  f"Direction: {event.direction}, Time: {event.timestamp:.3f}")
    else:
        print("\nNo recent mouse movement events")
    
    print("-" * 50)


def event_callback(event):
    """Callback that gets called when new input events occur."""
    print(f"\n[CALLBACK] New event: {event.event_type}" +
          (f" - Key: {event.key}" if hasattr(event, 'key') and event.key else "") +
          (f" - Button: {event.button_pressed}" if hasattr(event, 'button_pressed') and event.button_pressed else ""))


def main():
    """Main function to demonstrate the API."""
    print("Input Data Access API Example")
    print("===========================")
    print("This example shows how to access real-time input data.")
    
    # Register for event callbacks
    callback_id = InputDataAPI.register_event_callback(event_callback)
    
    try:
        # Main loop - monitor input state
        print("\nMonitoring input state. Press Ctrl+C to exit.")
        
        for i in range(10):  # Run for 10 iterations
            print_input_state()
            print_recent_events()
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\nExample stopped by user")
    finally:
        # Unregister callback
        InputDataAPI.unregister_event_callback(callback_id)
        print("\nExample finished")


if __name__ == "__main__":
    main()
