"""
Adapters package for the synchronization module.

Contains adapter classes that bridge between different components
and provide integration with existing applications.
"""

from .qt_integration_adapter import QtIntegrationAdapter

__all__ = [
    "QtIntegrationAdapter",
]
