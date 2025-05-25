#!/usr/bin/env python
"""
EEG Processor Application

This script runs the EEG Processor application for collecting, processing, and
visualizing EEG data from various devices including g.tec unicorn.
"""

import argparse
import logging
import os
import sys

from PyQt5.QtWidgets import QApplication

# Add the parent directory to the path to allow importing the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eeg_processor.python.eeg_processor_app import EEGProcessorApp

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--enable-web-api", action="store_true")
    p.add_argument("--api-host", default="127.0.0.1")
    p.add_argument("--api-port", type=int, default=8000)
    
    # Add control API arguments
    p.add_argument("--enable-control-api", action="store_true")
    p.add_argument("--control-api-host", default="127.0.0.1")
    p.add_argument("--control-api-port", type=int, default=8001)
    p.add_argument("--control-api-only", action="store_true", help="Only enable control API without data access API")
    
    return p.parse_args()

def main():
    """Run the EEG Processor application."""
    args = parse_args()

    # Configure logging - only to console by default, file logging controlled by UI
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Only console logging by default
    )

    # Create and start the application
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ex = EEGProcessorApp()
    ex.show()

    # Initialize data access API after the main application has started
    if args.enable_web_api and not args.control_api_only:
        from eeg_processor.python.api_integration import initialize_api, get_api_integration
        if initialize_api(host=args.api_host, port=args.api_port):
            intg = get_api_integration()
            port = intg.explorer.server_port or args.api_port
            print(f"Web API EEG Processor en http://{args.api_host}:{port}")
        else:
            print("Fallo inicializando Web API EEG Processor")
    
    # Initialize control API if enabled
    if args.enable_control_api:
        try:
            # Import API Explorer for control API
            from api_explorer import ApiExplorer
            
            # Get a new API Explorer instance for control API
            control_explorer = ApiExplorer()
            
            # Initialize and register control API
            from eeg_processor.python.interaction_api_integration import EEGProcessorInteractionApiIntegration
            control_integration = EEGProcessorInteractionApiIntegration.get_instance()
            
            # Register the control API module (includes both control and data access methods)
            control_integration.register_api_methods(control_explorer)
            
            # Start the control API server
            control_explorer.start_server(
                host=args.control_api_host, 
                port=args.control_api_port, 
                block=False
            )
            
            print(f"Control API EEG Processor en http://{args.control_api_host}:{args.control_api_port}")
            
        except ImportError:
            print("API Explorer no disponible. Control API deshabilitado.")
        except Exception as e:
            print(f"Error inicializando Control API: {e}")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
