#!/usr/bin/env python3
"""
Command Line Interface for Input Collector.

This script provides a standalone CLI for interacting with the Input Collector.
"""

import os
import sys

# Add module root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

def main():
    """Run the Input Collector CLI."""
    print("Starting Input Collector CLI...")
    print("Initializing headless mode...")
    
    # Set headless mode
    from python.cli.cli_app import headless_mode
    globals()['python.cli.cli_app.headless_mode'] = True
    
    # Initialize APIs if specified
    import argparse
    parser = argparse.ArgumentParser(description="Run the Input Collector CLI")
    parser.add_argument("--enable-web-api", action="store_true", help="Enable the data access web API")
    parser.add_argument("--enable-control-api", action="store_true", help="Enable the control web API") 
    args = parser.parse_args()
    
    if args.enable_web_api:
        from python.api_integration import initialize_api
        api_initialized = initialize_api(enable_web_api=True)
        if api_initialized:
            print("Data Access API initialized")
    
    if args.enable_control_api:
        from python.interaction_api_integration import initialize_interaction_api
        control_api_initialized = initialize_interaction_api(enable_web_api=True)
        if control_api_initialized:
            print("Control API initialized")
    
    # Run the CLI shell
    from python.cli.cli_app import run_cli
    run_cli()

if __name__ == "__main__":
    main()
