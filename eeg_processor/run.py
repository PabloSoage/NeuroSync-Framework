"""
EEG Processor Application

This script runs the EEG Processor application for collecting, processing, and
visualizing EEG data from various devices including g.tec unicorn.
"""

import argparse
import logging
import os
import sys
import threading
from typing import Dict, Any

from PyQt5.QtWidgets import QApplication

# Global CLI thread reference for cleanup
cli_thread = None

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eeg_processor.python.eeg_processor_app import EEGProcessorApp


def parse_config() -> Dict[str, Any]:
    """
    Parse configuration from command line arguments.

    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    parser = argparse.ArgumentParser(description="Run the EEG Processor")

    # Basic configuration
    parser.add_argument(
        "--fullscreen", action="store_true", help="Start in fullscreen mode"
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run without GUI (headless mode) using CLI instead",
    )
    parser.add_argument(
        "--cli", action="store_true", help="Enable CLI shell along with the GUI"
    )

    # Logging configuration
    parser.add_argument(
        "--logging",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Set logging level (default: info)",
    )

    # Data API configuration
    parser.add_argument("--enable-web-api", action="store_true", help="Enable the data access web API")
    parser.add_argument("--api-host", default="127.0.0.1", help="Host for the web API")
    parser.add_argument("--api-port", type=int, default=8000, help="Port for the web API")

    # Control API configuration
    parser.add_argument("--enable-control-api", action="store_true", help="Enable the control web API")
    parser.add_argument("--control-api-host", default="127.0.0.1", help="Host for the control API")
    parser.add_argument("--control-api-port", type=int, default=8001, help="Port for the control API")
    parser.add_argument(
        "--control-api-only",
        action="store_true",
        help="Only enable control API without data access API",
    )

    # Parse arguments and convert to dictionary
    args = parser.parse_args()
    return vars(args)


def start_cli_in_thread() -> threading.Thread:
    """Start the CLI in a separate thread."""
    global cli_thread

    # Import CLI modules - directly use the CLI config functions
    from eeg_processor.python.cli.cli_app import run_cli
    from eeg_processor.python.cli.cli_config import set_gui_mode, set_cli_running

    # Set flag to indicate CLI is running with GUI
    set_gui_mode(True)

    # Set CLI as running
    set_cli_running(True)

    # Create daemon thread (will be terminated when main thread exits)
    cli_thread = threading.Thread(target=run_cli, daemon=True)
    cli_thread.start()
    print(
        "CLI shell started in a separate thread. You can interact with both GUI and CLI simultaneously."
    )
    return cli_thread


def cleanup_cli_thread() -> None:
    """Clean up CLI thread on application exit."""
    global cli_thread
    if cli_thread and cli_thread.is_alive():
        try:
            # Use the CLI's own shutdown mechanism
            from eeg_processor.python.cli.cli_config import set_cli_running, wait_for_cli_exit
            from eeg_processor.python.cli.cli_app import shutdown_cli

            # Signal the CLI to shut down
            set_cli_running(False)

            # Call shutdown handler
            shutdown_cli()

            # Wait briefly for thread to terminate
            if not wait_for_cli_exit(0.5):  # 500ms timeout
                print("CLI thread did not exit cleanly, forcing exit...")
        except Exception as e:
            print(f"Error during CLI thread cleanup: {e}")


def main() -> None:
    """Run the EEG Processor application."""
    # Parse configuration
    config = parse_config()

    # Map string level to logging constants
    logging_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    # Configure logging - only to console by default, file logging controlled by UI
    logging.basicConfig(
        level=logging_levels[config.get("logging", "info")],
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Only console logging by default
    )

    # Initialize data access API if enabled
    if config.get("enable_web_api", False) and not config.get("control_api_only", False):
        from eeg_processor.python.api_integration import (
            initialize_api,
            get_api_integration,
        )

        # Include interaction methods only if control API is not enabled separately
        include_interaction = not config.get("enable_control_api", False)

        if initialize_api(
            host=config.get("api_host", "127.0.0.1"),
            port=config.get("api_port", 8000),
            include_interaction=include_interaction,
        ):
            intg = get_api_integration()
            port = (
                intg.explorer.server_port
                if intg.explorer is not None and intg.explorer.server_port is not None
                else config.get("api_port", 8000)
            )
            api_type = "data + control" if include_interaction else "data access only"
            print(
                f"Web API EEG Processor ({api_type}) at http://{config.get('api_host', '127.0.0.1')}:{port}"
            )
        else:
            print("Failed to initialize Web API EEG Processor")

    # Initialize control API if enabled
    if config.get("enable_control_api", False):
        try:
            # For control API, use the same api_integration but with interaction methods enabled
            from eeg_processor.python.api_integration import initialize_api

            # Initialize control API with both data access and interaction methods
            if initialize_api(
                enable=True,
                host=config.get("control_api_host", "127.0.0.1"),
                port=config.get("control_api_port", 8001),
                include_interaction=True,  # Always include interaction methods in control API
            ):
                print(
                    f"Control API EEG Processor (data + control) at http://{config.get('control_api_host', '127.0.0.1')}:{config.get('control_api_port', 8001)}"
                )
            else:
                print("Failed to initialize Control API EEG Processor")

        except ImportError:
            print("API Explorer not available. Control API disabled.")
        except Exception as e:
            print(f"Error initializing Control API: {e}")

    # Run in CLI-only mode, GUI-only mode, or both
    if config.get("no_gui", False):
        # Run in headless mode with CLI
        print("Starting EEG Processor in CLI mode...")
        print(
            "You'll be presented with an interactive shell to control the application."
        )
        print("Type 'help' to see available commands.")
        from eeg_processor.python.cli.cli_app import run_cli

        run_cli()
    else:
        # Run with GUI
        print("Starting EEG Processor with GUI...")

        # Start CLI in parallel if requested
        if config.get("cli", False):
            start_cli_in_thread()

        # Create and start the GUI application
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        ex = EEGProcessorApp()
        
        if config.get("fullscreen", False):
            ex.showFullScreen()
        else:
            ex.show()

        # Run the GUI (blocks until GUI is closed)
        try:
            result = app.exec_()
        except KeyboardInterrupt:
            print("\nReceived Ctrl+C, shutting down...")
            result = 0

        # GUI has closed, clean up CLI thread if needed
        cleanup_cli_thread()
        
        # Don't call sys.exit() to avoid terminal closure
        print("Application shutting down...")


if __name__ == "__main__":
    main()