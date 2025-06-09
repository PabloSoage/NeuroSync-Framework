"""
Application package for Input Collector.

Contains the main application coordinator that acts as the central mediator
between different components, handling high-level business logic and
coordinating interactions between collectors, UI, logging, and processing.
"""

from .app_coordinator import AppCoordinator

__all__ = [
    "AppCoordinator",
]
