#!/usr/bin/env python3
"""
Run the input collector application.

This script starts the input collector application and optionally enables the web API.
"""

import argparse
import os
import sys
import threading
from typing import Dict, Any

# Add module root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Global CLI thread reference for cleanup
cli_thread = None

def parse_config() -> Dict[str, Any]:
    """
    Parse configuration from command line arguments.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    parser = argparse.ArgumentParser(description="Run the input collector")
    
    # Basic configuration
    parser.add_argument("--fullscreen", action="store_true", help="Start in fullscreen mode")
    parser.add_argument("--no-gui", action="store_true", help="Run without GUI (headless mode) using CLI instead")
    parser.add_argument("--cli", action="store_true", help="Enable CLI shell along with the GUI")
    
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

def start_cli_in_thread():
    """Start the CLI in a separate thread."""
    global cli_thread
    
    # Import CLI modules - directly use the CLI config functions
    from python.cli.cli_app import run_cli
    from python.cli.cli_config import set_gui_mode, set_cli_running

    # Set flag to indicate CLI is running with GUI
    set_gui_mode(True)
    
    # Set CLI as running
    set_cli_running(True)
    
    # Create daemon thread (will be terminated when main thread exits)
    cli_thread = threading.Thread(target=run_cli, daemon=True)
    cli_thread.start()
    print("CLI shell started in a separate thread. You can interact with both GUI and CLI simultaneously.")
    return cli_thread

def cleanup_cli_thread():
    """Clean up CLI thread on application exit."""
    global cli_thread
    if cli_thread and cli_thread.is_alive():
        try:
            # Use the CLI's own shutdown mechanism
            from python.cli.cli_config import set_cli_running, wait_for_cli_exit
            from python.cli.cli_app import shutdown_cli
            
            # Signal the CLI to shut down
            set_cli_running(False)
            
            # Call shutdown handler
            shutdown_cli()
            
            # Wait briefly for thread to terminate
            if not wait_for_cli_exit(0.5):  # 500ms timeout
                print("CLI thread did not exit cleanly, forcing exit...")
        except Exception as e:
            print(f"Error during CLI thread cleanup: {e}")

def main():
    """Run the input collector application."""
    # Parse configuration
    config = parse_config()
    
    # Initialize the data access web API if enabled
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
            # Get actual port used
            integration = get_api_integration()
            actual_port = integration.explorer.server_port or config['api_port']
            print(f"Data Access API initialized at http://{config['api_host']}:{actual_port}")
        else:
            print("Failed to initialize Data Access API")
    
    # Initialize the control web API if enabled
    if config.get("enable_control_api", False):
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
            print("Failed to initialize Control API")
    
    # Run in CLI-only mode, GUI-only mode, or both
    if config.get("no_gui", False):
        # Run in headless mode with CLI
        print("Starting Input Collector in CLI mode...")
        print("You'll be presented with an interactive shell to control the application.")
        print("Type 'help' to see available commands.")
        from python.cli.cli_app import run_cli
        run_cli()
    else:
        # Run with GUI
        print("Starting Input Collector with GUI...")
        
        # Start CLI in parallel if requested
        if config.get("cli", False):
            start_cli_in_thread()
            
        # Start the GUI (which will block until the GUI is closed)
        from python.input_collector_app import run_collector_app
        run_collector_app()
        
        # GUI has closed, clean up CLI thread if needed
        cleanup_cli_thread()

if __name__ == "__main__":
    main()
