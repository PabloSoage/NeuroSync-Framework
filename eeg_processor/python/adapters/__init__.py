"""
Adapters package for the EEG processor.

This package contains adapters that bridge between the EEG processor's
framework-independent core and specific UI frameworks or external systems.
"""

from .qt_interaction_adapter import QtInteractionAdapter

__all__ = ['QtInteractionAdapter']
