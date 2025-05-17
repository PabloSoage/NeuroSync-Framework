#!/usr/bin/env python3
"""
Run the input collector application.

This script starts the input collector application and optionally enables the web API.
"""

import sys
import os
import argparse
from typing import Dict, Any
import json

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
    
    # Web API configuration
    parser.add_argument("--enable-web-api", action="store_true", help="Enable the web API")
    parser.add_argument("--api-host", default="127.0.0.1", help="Host for the web API")
    parser.add_argument("--api-port", type=int, default=8000, help="Port for the web API")
    
    # Parse arguments and convert to dictionary
    args = parser.parse_args()
    return vars(args)

def main():
    """Run the input collector application."""
    # Parse configuration
    config = parse_config()
    
    # Import here to avoid circular imports
    from python.input_collector_app import run_collector_app
    
    # Initialize the web API if enabled
    if config.get("enable_web_api", False):
        # Import the API integration
        from python.api_integration import initialize_api, get_api_integration
        
        # Initialize the API
        api_initialized = initialize_api(
            enable_web_api=True,
            host=config.get("api_host", "127.0.0.1"),
            port=config.get("api_port", 8000)
        )
        
        if api_initialized:
            # Obtener puerto real usado
            integration = get_api_integration()
            actual_port = integration.explorer.server_port or config['api_port']
            print(f"Web API initialized at http://{config['api_host']}:{actual_port}")
        else:
            print("Failed to initialize Web API")
    
    # Run the collector application
    run_collector_app()

if __name__ == "__main__":
    main()
