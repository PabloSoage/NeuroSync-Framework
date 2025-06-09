"""
Collectors package for input collection.

Contains input event collectors for various devices including keyboard/mouse
and game controllers, along with a central manager for coordinating between
different collectors and handling their lifecycle and capabilities.
"""

from .collector_manager import CollectorManager
from .keyboard_mouse import KeyboardMouseCollector

# Try to import PS4 controller with graceful fallback
try:
    from .ps4_controller import PS4ControllerCollector, is_sdl2_available

    __all__ = [
        "CollectorManager",
        "KeyboardMouseCollector",
        "PS4ControllerCollector",
        "is_sdl2_available",
    ]
except ImportError:
    # PS4 controller not available (SDL2 dependency missing)
    __all__ = [
        "CollectorManager",
        "KeyboardMouseCollector",
    ]
