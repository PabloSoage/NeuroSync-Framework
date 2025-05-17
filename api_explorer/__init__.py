"""
API Explorer for modules.

This package provides a web-based interface for exploring and testing module APIs.
"""

# Import the ApiExplorer directly from the local module
from .api_explorer import ApiExplorer
from .main import run_explorer

__all__ = ['ApiExplorer', 'run_explorer']
