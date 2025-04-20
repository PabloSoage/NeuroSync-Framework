"""
Collectors package for input collection.

This package provides classes for collecting input events from various devices.
"""

from .keyboard_mouse import KeyboardMouseCollector
from .collector_manager import CollectorManager

# Export classes in the package namespace
__all__ = ["KeyboardMouseCollector", "CollectorManager"]

# Optionally try to import PS4 controller
try:
    from .ps4_controller import PS4ControllerCollector, is_sdl2_available
    __all__.append("PS4ControllerCollector")
except ImportError:
    # PS4 controller not available
    pass
