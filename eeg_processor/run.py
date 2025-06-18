#!/usr/bin/env python
"""
EEG Processor Application

This script runs the EEG Processor application for collecting, processing, and
visualizing EEG data from various devices including g.tec unicorn.
"""

import argparse
import logging
import sys

from PyQt5.QtWidgets import QApplication

from python.eeg_processor_app import EEGProcessorApp


def parse_args() -> argparse.Namespace:
    """Parse command line arguments for the EEG Processor application.

    Returns:
        argparse.Namespace: Parsed command line arguments including API configuration options.
    """
    p = argparse.ArgumentParser()
    p.add_argument("--enable-web-api", action="store_true")
    p.add_argument("--api-host", default="127.0.0.1")
    p.add_argument("--api-port", type=int, default=8000)

    # Add control API arguments
    p.add_argument("--enable-control-api", action="store_true")
    p.add_argument("--control-api-host", default="127.0.0.1")
    p.add_argument("--control-api-port", type=int, default=8001)
    p.add_argument(
        "--control-api-only",
        action="store_true",
        help="Only enable control API without data access API",
    )

    return p.parse_args()


def main() -> None:
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
    # Only include interaction methods if control API is NOT being used separately
    if args.enable_web_api and not args.control_api_only:
        from eeg_processor.python.api_integration import (
            initialize_api,
            get_api_integration,
        )

        # Include interaction methods only if control API is not enabled separately
        include_interaction = not args.enable_control_api

        if initialize_api(
            host=args.api_host,
            port=args.api_port,
            include_interaction=include_interaction,
        ):
            intg = get_api_integration()
            port = (
                intg.explorer.server_port
                if intg.explorer is not None and intg.explorer.server_port is not None
                else args.api_port
            )
            api_type = "data + control" if include_interaction else "data access only"
            print(
                f"Web API EEG Processor ({api_type}) en http://{args.api_host}:{port}"
            )
        else:
            print("Fallo inicializando Web API EEG Processor")

    # Initialize control API if enabled
    if args.enable_control_api:
        try:
            # For control API, use the same api_integration but with interaction methods enabled
            from eeg_processor.python.api_integration import initialize_api

            # Initialize control API with both data access and interaction methods
            if initialize_api(
                enable=True,
                host=args.control_api_host,
                port=args.control_api_port,
                include_interaction=True,  # Always include interaction methods in control API
            ):
                print(
                    f"Control API EEG Processor (data + control) en http://{args.control_api_host}:{args.control_api_port}"
                )
            else:
                print("Fallo inicializando Control API EEG Processor")

        except ImportError:
            print("API Explorer no disponible. Control API deshabilitado.")
        except Exception as e:
            print(f"Error inicializando Control API: {e}")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
