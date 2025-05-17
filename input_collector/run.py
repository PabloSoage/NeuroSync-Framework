#!/usr/bin/env python3
"""
Input Collector Application

This script launches the Input Collector application for real-time keyboard
and mouse input collection, visualization, and logging.

Features:
- Collects keyboard and mouse inputs in real-time
- Visualizes inputs with customizable visualizers
- Logs inputs to JSON and CSV formats
- Provides low-overhead real-time data access API
- Includes API Explorer (press F1) for testing the data access API
"""

import sys
import os
import traceback

# Add module root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

def run_with_error_handling():
    """Run the application with error handling."""
    try:
        from python.input_collector_app import run_collector_app
        
        # Display banner
        print("=" * 60)
        print("Input Collector Application")
        print("=" * 60)
        print("Press F9 to start/stop recording")
        print("Press F11 to toggle fullscreen")
        print("Press F1 to open the API Explorer")
        print("=" * 60)
        
        # Run the application
        run_collector_app()
    except Exception as e:
        print(f"ERROR: Application crashed: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")  # Keep console open to see the error
        sys.exit(1)

if __name__ == "__main__":
    run_with_error_handling()
