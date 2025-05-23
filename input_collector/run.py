#!/usr/bin/env python3
"""
Run the input collector application.

This script starts the input collector application and optionally enables the web API.
"""

import argparse
import os
import sys
from typing import Dict, Any

# Add module root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

def parse_config() -> Dict[str, Any]:
    """
    Parse configuration from command line arguments.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    parser = argparse.ArgumentParser(description="Run the input collector")
    
    # Basic configuration
    parser.add_argument("--fullscreen", action="store_true", help="Start in fullscreen mode")
    
    # Data API configuration
    parser.add_argument("--enable-web-api", action="store_true", help="Enable the data access web API")
    parser.add_argument("--api-host", default="127.0.0.1", help="Host for the web API")
    parser.add_argument("--api-port", type=int, default=8000, help="Port for the web API")
    
    # Control API configuration
    parser.add_argument("--enable-control-api", action="store_true", help="Enable the control web API")
    parser.add_argument("--control-api-host", default="127.0.0.1", help="Host for the control API")
    parser.add_argument("--control-api-port", type=int, default=8001, help="Port for the control API")
    
    # Parse arguments and convert to dictionary
    args = parser.parse_args()
    return vars(args)

def main():
    """Run the input collector application."""
    # Parse configuration
    config = parse_config()
    
    # Debug output to confirm flag detection
    print(f"Configuration: web_api={config.get('enable_web_api', False)}, control_api={config.get('enable_control_api', False)}")
    
    # Initialize the data access web API if enabled
    if config.get("enable_web_api", False):
        try:
            print("Attempting to initialize Data Access Web API...")
            
            # Import the API integration
            from python.api_integration import initialize_api, get_api_integration
            
            # Initialize the API
            api_initialized = initialize_api(
                enable_web_api=True,
                host=config.get("api_host", "127.0.0.1"),
                port=config.get("api_port", 8000)
            )
            
            if api_initialized:
                # Get actual port used
                integration = get_api_integration()
                actual_port = integration.explorer.server_port or config['api_port']
                print(f"Data Access API initialized at http://{config['api_host']}:{actual_port}")
            else:
                print("Failed to initialize Data Access API - returned False")
        except Exception as e:
            print(f"Error initializing Data Access API: {e}")
            import traceback
            traceback.print_exc()
    
    # Initialize the control web API if enabled
    if config.get("enable_control_api", False):
        try:
            print("Attempting to initialize Control API...")
            
            # Import the interaction API integration
            from python.interaction_api_integration import initialize_interaction_api
            
            # Initialize the interaction API
            control_api_initialized = initialize_interaction_api(
                enable_web_api=True,
                host=config.get("control_api_host", "127.0.0.1"),
                port=config.get("control_api_port", 8001)
            )
            
            if control_api_initialized:
                print(f"Control API initialized at http://{config['control_api_host']}:{config['control_api_port']}")
            else:
                print("Failed to initialize Control API - returned False")
        except Exception as e:
            print(f"Error initializing Control API: {e}")
            import traceback
            traceback.print_exc()
    
    # Run the collector application
    run_collector_app()

if __name__ == "__main__":
    main()
