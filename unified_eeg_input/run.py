"""
Unified EEG and Input Collector Application.

This is the main entry point for the unified application that integrates
EEG processing and input collection.
"""

import sys
from python.unified_app import UnifiedApplication


def main():
    """Run the unified application."""
    app = UnifiedApplication()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
