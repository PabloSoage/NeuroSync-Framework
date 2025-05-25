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
    
    # Add interaction API arguments
    p.add_argument("--enable-interaction-api", action="store_true")
    p.add_argument("--interaction-api-host", default="127.0.0.1")
    p.add_argument("--interaction-api-port", type=int, default=8001)
    
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
    if args.enable_web_api:
        from eeg_processor.python.api_integration import initialize_api, get_api_integration
        if initialize_api(host=args.api_host, port=args.api_port):
            intg = get_api_integration()
            port = intg.explorer.server_port or args.api_port
            print(f"Web API EEG Processor en http://{args.api_host}:{port}")
        else:
            print("Fallo inicializando Web API EEG Processor")
    
    # Initialize interaction API if enabled
    if args.enable_interaction_api:
        try:
            # Import API Explorer for interaction API
            from api_explorer import ApiExplorer
            
            # Get a new API Explorer instance for interaction API
            interaction_explorer = ApiExplorer()
            
            # Initialize and register interaction API
            from eeg_processor.python.interaction_api_integration import EEGProcessorInteractionApiIntegration
            interaction_integration = EEGProcessorInteractionApiIntegration.get_instance()
            
            # Register the interaction API module
            interaction_integration.register_api_methods(interaction_explorer)
            
            # Start the interaction API server
            interaction_explorer.start_server(
                host=args.interaction_api_host, 
                port=args.interaction_api_port, 
                block=False
            )
            
            print(f"Interaction API EEG Processor en http://{args.interaction_api_host}:{args.interaction_api_port}")
            
        except ImportError:
            print("API Explorer no disponible. Interaction API deshabilitado.")
        except Exception as e:
            print(f"Error inicializando Interaction API: {e}")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
