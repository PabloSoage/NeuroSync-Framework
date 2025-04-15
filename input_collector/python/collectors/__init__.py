"""
Input collectors package.

This package provides implementations of various input collectors
that capture and process input from different devices.
"""

from .keyboard_mouse import KeyboardMouseCollector

# Try to import PS4 controller support, but don't fail if dependencies are missing
try:
    from .ps4_controller import PS4ControllerCollector, is_sdl2_available

    # Verify SDL2 is properly loaded - more thorough check
    sdl_available = is_sdl2_available()
    if not sdl_available:
        print(
            "SDL2 detected but could not be properly initialized. PS4 controller support will be disabled."
        )
except ImportError as e:
    # Print detailed information about the import failure
    print(f"PS4 controller support disabled: {e}")
    print(
        "To enable PS4 controller support, install required packages with:\n"
        "pip install pysdl2 pysdl2-dll"
    )

    # Define a function to check SDL2 availability that always returns False
    def is_sdl2_available():
        return False


__all__ = ["KeyboardMouseCollector"]
