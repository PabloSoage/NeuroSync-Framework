"""
Services package for input collector.

Contains service layer components that provide business logic and application
functionality to different layers of the system. Includes interaction services
for controlling application behavior and data access services for real-time
input data retrieval, both designed as singleton services to ensure consistent
state management and efficient resource utilization across the application.
"""

from .data_access_service import DataAccessService
from .interaction_service import InteractionService

__all__ = [
    "DataAccessService",
    "InteractionService",
]
